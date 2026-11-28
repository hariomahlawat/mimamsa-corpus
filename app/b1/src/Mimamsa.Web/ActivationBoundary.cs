// C16 CP-1 review C16-CP1-01/03, extended in C16 Stage 3 (S3-D) to every surface: the response boundary when the
// activation journal manages the site. One ActivationBoundary per knowledge generation (GenerationSlot).
//
// HANDLER TIME. Eligibility.Boundary (the single eligibility decision every surface already asks) calls Excluded()
// for each (doc id, copy sha) a handler considers, so graph, reasoning, Commander, statutes, library, relations,
// Studio, PDF, admin and the search engine's hidden-document predicate (hence facets and totals) all leave excluded
// copies out while the response is built. Within one request the signed state is read ONCE (cached on the request),
// so a library or search request does not re-read the store per document; the final check below re-reads it.
//
// LINEARISATION. A buffered response is linearised at its FINAL CHECK, which runs after the handler has enumerated
// page text and serialised the body into a buffer and immediately before a single byte is committed to the client:
//   - if the signed exclusion state the final check reads already contains an exclusion for any copy the response
//     touched or names, nothing of the buffer is sent (content-free 404 for document surfaces, 503 "results changed"
//     for the others) - the response is ordered AFTER the acceptance;
//   - otherwise the buffer is sent whole - the response is ordered BEFORE any acceptance the check did not see.
// So a response that commits after an exclusion has been accepted (and is visible in the store) never carries the
// excluded content. The final check re-reads the CURRENT state (never the state at pin time) and fails closed if the
// store is unreadable. Exclusion acceptance (ActivationEngine.AcceptExclusion) is a separate process; its visibility
// point is the store's ACCEPTED.json write.
// Copies a response touched or names: every (doc_id, sha) the handler let into the response through Eligibility
// ("touched", which includes every document a count or facet was computed over), plus - for Boundary routes - every
// JSON string value in the buffered body equal to a served doc_id or to a held copy's sha256 (so variants, summaries
// and any future field are covered without per-handler code). BoundaryPrivate routes (Studio: the user's own working
// documents and notes) are checked on the touched set only: a citation of an unavailable source keeps the author's own
// stored reference fields in the content-free "source no longer available" form (C15), which is not corpus content.
//
// STREAMING (PDF Range, BoundaryStreaming). The handler checks before the first byte and re-reads the CURRENT state
// immediately before each slice is handed to the transport (ExcludedNow). After an acceptance becomes visible at most
// the slice already handed over (bounded by Mimamsa:Delivery:Slice) plus what the transport has queued can still
// reach the client; the connection is then reset. Bytes already sent cannot be recalled: no retroactive recall is
// claimed.
using System.Collections.Concurrent;
using System.Text.Json;
using Mimamsa.Core.Activation;
using Mimamsa.Core.Generation;

namespace Mimamsa.Web;

public sealed class ActivationBoundary(ActivationParticipant participant, GenerationStore generation, string? testPauseDir)
{
    public const string PinKey = "mimamsa.activation.pin";
    const string TouchedKey = "mimamsa.activation.touched";
    const string SnapshotKey = "mimamsa.activation.snapshot";
    readonly Dictionary<string, string> _copyOfDoc = generation.Documents.Values.ToDictionary(d => d.DocId, d => d.CopySha, StringComparer.Ordinal);
    readonly Dictionary<string, List<string>> _docsOfCopy = generation.Documents.Values.Select(d => (d.CopySha, d.DocId))
        .Concat(generation.HeldCopies.Values.Select(h => (h.Sha, h.DocId)))
        .GroupBy(x => x.Item1, StringComparer.Ordinal).ToDictionary(g => g.Key, g => g.Select(x => x.Item2).Distinct().ToList(), StringComparer.Ordinal);

    /// The request whose handler is running on this async flow (set by the activation middleware). Eligibility asks the
    /// boundary without an HttpContext parameter; outside a request the boundary answers "excluded" (fail closed).
    public static readonly AsyncLocal<HttpContext?> Request = new();

    static ConcurrentDictionary<(string, string?), byte> Touched(HttpContext ctx) =>
        (ConcurrentDictionary<(string, string?), byte>)(ctx.Items[TouchedKey] ??= new ConcurrentDictionary<(string, string?), byte>());

    /// Handler-time check (and record) against the request's snapshot of the signed state; fail closed without a pin or
    /// a readable store.
    public bool Excluded(HttpContext ctx, string docId, string? sha)
    {
        if (ctx.Items[PinKey] is not ReaderPin) return true;
        EffectiveExclusions state;
        if (ctx.Items[SnapshotKey] is EffectiveExclusions cached) state = cached;
        else
        {
            try { state = participant.CurrentExclusions(); }
            catch (ActivationRefused) { return true; }
            ctx.Items[SnapshotKey] = state;
        }
        if (state.IsExcluded(docId, sha)) return true;
        Touched(ctx).TryAdd((docId, sha), 0);   // only what the handler let into the response is re-checked at commit
        return false;
    }

    /// Eligibility.Boundary for this generation: the current request's check, or excluded outside a request.
    public bool ExcludedForCurrentRequest(string docId, string? sha) => Request.Value is { } ctx ? Excluded(ctx, docId, sha) : true;

    /// Streaming: re-read the CURRENT state now (never the request's snapshot); fail closed.
    public bool ExcludedNow(HttpContext ctx, string docId, string? sha)
    {
        if (ctx.Items[PinKey] is not ReaderPin) return true;
        try { return participant.CurrentExclusions().IsExcluded(docId, sha); }
        catch (ActivationRefused) { return true; }
    }

    bool AnyExcluded(HttpContext ctx, IReadOnlyCollection<(string doc, string? sha)> items)
    {
        if (items.Count == 0) return false;
        if (ctx.Items[PinKey] is not ReaderPin pin) return true;
        try { return participant.Respond(pin, items, x => x.doc, x => x.sha).Count != items.Count; }
        catch (ActivationRefused) { return true; }
    }

    /// Every copy the buffered body names (exact JSON string matches against served doc ids and held copy hashes).
    public List<(string doc, string? sha)> Named(ReadOnlySpan<byte> body)
    {
        var found = new HashSet<(string, string?)>();
        if (body.IsEmpty) return [];
        try
        {
            var r = new Utf8JsonReader(body, new JsonReaderOptions { CommentHandling = JsonCommentHandling.Skip });
            while (r.Read())
            {
                if (r.TokenType != JsonTokenType.String && r.TokenType != JsonTokenType.PropertyName) continue;
                var s = r.GetString();
                if (s is null) continue;
                if (_copyOfDoc.TryGetValue(s, out var sha)) found.Add((s, sha));
                if (_docsOfCopy.TryGetValue(s, out var docs)) foreach (var d in docs) found.Add((d, s));
            }
        }
        catch (JsonException) { found.Add(("\u0000unparseable", null)); }   // not JSON: never released under activation
        return found.ToList();
    }

    /// The final check: true when the buffered response may be committed now. `scanBody` is false for BoundaryPrivate
    /// routes (touched set only, see the header).
    public bool MayCommit(HttpContext ctx, ReadOnlySpan<byte> body, bool scanBody = true)
    {
        var all = new HashSet<(string, string?)>(Touched(ctx).Keys);
        if (scanBody)
        {
            var named = Named(body);
            if (named.Any(x => x.doc == "\u0000unparseable")) return false;
            all.UnionWith(named);
        }
        return !AnyExcluded(ctx, all.ToList());
    }

    /// Test-only pause (Mimamsa:Test:Enabled and Mimamsa:Test:PauseDir): a request carrying X-Mimamsa-Test-Pause: <token>
    /// writes <token>.paused after its handler ran (streaming: after its first slice) and waits for <token>.release.
    public async Task TestPauseAsync(HttpContext ctx)
    {
        if (testPauseDir is null || ctx.Request.Headers["X-Mimamsa-Test-Pause"].ToString() is not { Length: > 0 } token) return;
        if (token.Any(c => !(char.IsAsciiLetterOrDigit(c) || c is '-' or '_'))) return;
        Directory.CreateDirectory(testPauseDir);
        await File.WriteAllTextAsync(Path.Combine(testPauseDir, token + ".paused"), "paused");
        var release = Path.Combine(testPauseDir, token + ".release");
        for (int i = 0; i < 1200 && !File.Exists(release); i++) await Task.Delay(100);
    }
}
