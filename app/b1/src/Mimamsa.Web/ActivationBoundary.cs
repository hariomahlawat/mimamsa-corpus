// C16 CP-1 review C16-CP1-01/03: the response boundary when the activation journal manages the site.
//
// LINEARISATION. A response is linearised at its FINAL CHECK, which runs after the handler has enumerated page text and
// serialised JSON into a buffer and immediately before a single byte is committed to the client:
//   - if the signed exclusion state the final check reads already contains an exclusion for any copy the response names,
//     nothing of the buffer is sent (content-free 404, or 503 for search) - the response is ordered AFTER the acceptance;
//   - otherwise the buffer is sent whole - the response is ordered BEFORE any acceptance the check did not see.
// So a response that commits after an exclusion has been accepted (and is visible in the store) never carries the
// excluded content. The final check re-reads the CURRENT state (never the state at pin time) and fails closed if the
// store is unreadable. Exclusion acceptance (ActivationEngine.AcceptExclusion) is a separate process; its visibility
// point is the store's ACCEPTED.json write.
// Copies named by a response: every (doc_id, sha) the handler asked about through BoundaryExcluded ("touched"), plus every
// JSON string value in the buffered body equal to a served doc_id or to a held copy's sha256 (so variants, summaries and
// any future field are covered without per-handler code).
// Streaming PDF/Range delivery is Refused under activation (ActivationRouteInventory), so no streamed bytes are emitted
// here; when it is brought behind the boundary it keeps the existing bounded-drain semantics, and bytes already sent
// cannot be recalled (no retroactive recall is claimed).
using System.Collections.Concurrent;
using System.Text.Json;
using Mimamsa.Core.Activation;
using Mimamsa.Core.Generation;

namespace Mimamsa.Web;

public sealed class ActivationBoundary(ActivationParticipant participant, GenerationStore generation, string? testPauseDir)
{
    public const string PinKey = "mimamsa.activation.pin";
    const string TouchedKey = "mimamsa.activation.touched";
    readonly Dictionary<string, string> _copyOfDoc = generation.Documents.Values.ToDictionary(d => d.DocId, d => d.CopySha, StringComparer.Ordinal);
    readonly Dictionary<string, List<string>> _docsOfCopy = generation.Documents.Values.Select(d => (d.CopySha, d.DocId))
        .Concat(generation.HeldCopies.Values.Select(h => (h.Sha, h.DocId)))
        .GroupBy(x => x.Item1, StringComparer.Ordinal).ToDictionary(g => g.Key, g => g.Select(x => x.Item2).Distinct().ToList(), StringComparer.Ordinal);

    static ConcurrentBag<(string, string?)> Touched(HttpContext ctx) =>
        (ConcurrentBag<(string, string?)>)(ctx.Items[TouchedKey] ??= new ConcurrentBag<(string, string?)>());

    /// Handler-time check (and record) against the CURRENT state; fail closed without a pin or a readable store.
    public bool Excluded(HttpContext ctx, string docId, string? sha)
    {
        Touched(ctx).Add((docId, sha));
        return AnyExcluded(ctx, [(docId, sha)]);
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

    /// The final check: true when the buffered response may be committed now.
    public bool MayCommit(HttpContext ctx, ReadOnlySpan<byte> body)
    {
        var named = Named(body);
        if (named.Any(x => x.doc == "\u0000unparseable")) return false;
        var all = named.Concat(Touched(ctx)).Distinct().ToList();
        return !AnyExcluded(ctx, all);
    }

    /// Test-only pause (Mimamsa:Test:Enabled and Mimamsa:Test:PauseDir): a request carrying X-Mimamsa-Test-Pause: <token>
    /// writes <token>.paused after its handler ran and waits for <token>.release before the final check.
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
