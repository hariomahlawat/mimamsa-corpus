// C16 B06 / I-6: read-only, signature-verified reader of the Python ExclusionStore's latest EFFECTIVE state
// (reference: mimamsa_contract/exclusions.py ExclusionStore.load_latest + effective_state).
//
// The .NET app did not read the signed store before (PolicyStore comment, conflict X7). This reader never writes the
// store. It fails closed (Health != HEALTHY: no pins, no responses, no transitions) when:
//   MISSING        the store directory or its ACCEPTED record is absent (Python load_latest refuses the same way);
//   UNREADABLE     ACCEPTED or a pair is unparseable, altered (digest) or the history is inconsistent;
//   BAD_SIGNATURE  the accepted update does not verify against the trust list (purpose 'register');
//   REGRESSED      the accepted sequence is below the highest sequence this site has seen or applied (high-water
//                  file, the EXCLUSION_LATCH first sequence, and the caller's recorded sequence from the journal), or
//                  an identity excluded before is no longer excluded without a signed readmission after it.
// Monotone tombstones are folded over the accepted history exactly as effective_state does: anything ever withdrawn
// or restricted stays denied unless a later accepted update readmits that exact identity. The store is never restored
// from backup (architecture section 10); the high-water file lives in the site's activation state, not in the store.
using System.Security.Cryptography;
using System.Text;
using System.Text.Json.Nodes;

namespace Mimamsa.Core.Activation;

public enum ExclusionHealth { HEALTHY, MISSING, UNREADABLE, BAD_SIGNATURE, REGRESSED }

public sealed class EffectiveExclusions
{
    public long Sequence { get; init; }
    public IReadOnlySet<string> WithdrawnDocIds { get; init; } = new HashSet<string>();
    public IReadOnlySet<string> WithdrawnShas { get; init; } = new HashSet<string>();
    public IReadOnlySet<string> RestrictedDocIds { get; init; } = new HashSet<string>();
    public IReadOnlySet<string> RestrictedShas { get; init; } = new HashSet<string>();
    /// Identities readmitted by an update with sequence > key (used for the monotone check).
    internal IReadOnlyList<(long seq, HashSet<string> docs, HashSet<string> shas)> Readmissions { get; init; } = [];

    public static readonly EffectiveExclusions Empty = new();

    public bool IsExcluded(string docId, string? sha = null) =>
        WithdrawnDocIds.Contains(docId) || RestrictedDocIds.Contains(docId) ||
        (sha is not null && (WithdrawnShas.Contains(sha) || RestrictedShas.Contains(sha)));
}

public sealed record ExclusionSnapshot(ExclusionHealth Health, long? Sequence, string Detail, EffectiveExclusions? State)
{
    public bool Healthy => Health == ExclusionHealth.HEALTHY;
}

public sealed class ExclusionReaderOptions
{
    public required string StoreDir { get; init; }
    public required string TrustListPath { get; init; }
    /// Site-local high-water file (outside the store; never part of a backup restore of the store).
    public required string HighWaterPath { get; init; }
    public bool Production { get; init; } = true;
    public Func<DateOnly> Today { get; init; } = () => DateOnly.FromDateTime(DateTime.UtcNow);
}

public sealed class ExclusionReader
{
    readonly ExclusionReaderOptions _o;
    readonly object _gate = new();
    readonly Dictionary<string, bool> _sigCache = new(StringComparer.Ordinal);
    EffectiveExclusions? _last;
    long _maxSeen;

    public ExclusionReader(ExclusionReaderOptions o) { _o = o; }

    public string StoreDir => _o.StoreDir;
    string LatchPath => Path.Combine(Path.GetDirectoryName(Path.GetFullPath(_o.StoreDir))!, "EXCLUSION_LATCH");

    /// Read the latest effective state. `recordedSequence` is the highest exclusion sequence the site has recorded
    /// (applied to a generation or written into an OPEN journal record); a store behind it is REGRESSED.
    public ExclusionSnapshot Read(long recordedSequence = 0)
    {
        lock (_gate)
        {
            var snap = ReadCore(recordedSequence);
            if (snap.Healthy)
            {
                _last = snap.State;
                if (snap.Sequence > _maxSeen) _maxSeen = snap.Sequence!.Value;
                PersistHighWater(_maxSeen);
            }
            return snap;
        }
    }

    ExclusionSnapshot ReadCore(long recorded)
    {
        var dir = _o.StoreDir;
        if (!Directory.Exists(dir)) return new(ExclusionHealth.MISSING, null, "exclusion store directory missing", null);
        var accPath = Path.Combine(dir, "ACCEPTED.json");
        if (!File.Exists(accPath)) return new(ExclusionHealth.MISSING, null, "exclusion store has no accepted state", null);
        JsonObject acc;
        long seq;
        byte[] accBytes;
        try
        {
            accBytes = DurableFile.ReadShared(accPath);
            acc = CanonicalJson.ParseStrict(accBytes).AsObject();
            seq = (long)acc["sequence"]!;
        }
        catch (Exception e) when (e is IOException or FormatException or InvalidOperationException or System.Text.Json.JsonException or NullReferenceException)
        { return new(ExclusionHealth.UNREADABLE, null, "ACCEPTED record unreadable", null); }

        try
        {
            var digest = (string)acc["digest"]!;
            byte[] trustBytes;
            try { trustBytes = DurableFile.ReadShared(_o.TrustListPath); }
            catch (Exception e) when (e is IOException or UnauthorizedAccessException) { return new(ExclusionHealth.BAD_SIGNATURE, seq, "trust list missing", null); }
            // Unchanged store and trust list since the last successful parse: reuse it (the regression checks below
            // still run on every read). The fingerprint covers ACCEPTED, the trust list and every pair file's name,
            // length and write time.
            var fp = Fingerprint(dir, accBytes, trustBytes);
            EffectiveExclusions state;
            if (fp == _fp && _fpState is not null) state = _fpState;
            else
            {
            var (data, sig) = Pair(dir, seq, digest);
            TrustList trust;
            try { trust = TrustList.Parse(trustBytes); }
            catch (Exception) { return new(ExclusionHealth.BAD_SIGNATURE, seq, "trust list invalid", null); }
            var cacheKey = CanonicalJson.Sha256Hex(data) + ":" + CanonicalJson.Sha256Hex(sig) + ":" + trust.Sequence;
            if (!_sigCache.TryGetValue(cacheKey, out var ok))
            {
                ok = trust.VerifyDetached(data, sig, "register", _o.Production, _o.Today()) is not null;
                _sigCache[cacheKey] = ok;
            }
            if (!ok) return new(ExclusionHealth.BAD_SIGNATURE, seq, "accepted exclusion update not signed by a trusted register key", null);
            var latest = CanonicalJson.ParseStrict(data).AsObject();
            if ((string?)latest["record_kind"] != "exclusion_update" || (long)latest["sequence"]! != seq)
                return new(ExclusionHealth.UNREADABLE, seq, "accepted update does not match its sequence", null);
            var regJson = (string)latest["register_json"]!;
            if (CanonicalJson.Sha256Hex(Encoding.UTF8.GetBytes(regJson)) != (string)latest["register_sha256"]!)
                return new(ExclusionHealth.UNREADABLE, seq, "register_sha256 does not match register_json", null);

            // History consistency (effective_state): strictly increasing sequences, head = accepted record, every
            // stored pair within the accepted range listed.
            var hist = acc["history"]?.AsArray() ?? throw new FormatException("no history");
            var seqs = hist.Select(h => (long)h!.AsArray()[0]!).ToList();
            if (seqs.Count == 0 || !seqs.SequenceEqual(seqs.Distinct().Order()) || seqs[^1] != seq || (string)hist[^1]!.AsArray()[1]! != digest)
                return new(ExclusionHealth.UNREADABLE, seq, "acceptance history inconsistent (order or head mismatch)", null);
            var pairs = Path.Combine(dir, "pairs");
            var onDisk = Directory.Exists(pairs)
                ? Directory.GetFiles(pairs, "*.json").Select(Path.GetFileNameWithoutExtension).Where(s => s!.All(char.IsAsciiDigit)).Select(s => long.Parse(s!)).Where(s => s <= seq).ToHashSet()
                : [];
            if (!onDisk.IsSubsetOf(seqs)) return new(ExclusionHealth.UNREADABLE, seq, "stored pair within the accepted range missing from the history", null);

            var docs = new HashSet<string>(StringComparer.Ordinal); var shas = new HashSet<string>(StringComparer.Ordinal);
            var rdocs = new HashSet<string>(StringComparer.Ordinal); var rshas = new HashSet<string>(StringComparer.Ordinal);
            var readm = new List<(long, HashSet<string>, HashSet<string>)>();
            foreach (var h in hist)
            {
                var e = h!.AsArray();
                long hs = (long)e[0]!; var hd = (string)e[1]!;
                var u = CanonicalJson.ParseStrict(Pair(dir, hs, hd).data).AsObject();
                var rmDocs = new HashSet<string>(StringComparer.Ordinal); var rmShas = new HashSet<string>(StringComparer.Ordinal);
                var lifted = new HashSet<string>(StringComparer.Ordinal);
                foreach (var w in u["readmissions"]?.AsArray() ?? [])
                {
                    var wo = w!.AsObject();
                    var d = (string?)wo["doc_id"]; var s = (string?)wo["source_copy_sha256"];
                    if (d is not null) { docs.Remove(d); rmDocs.Add(d); }
                    if (s is not null) { shas.Remove(s); rmShas.Add(s); }
                    if (wo["restriction_id"] is not null)
                    {
                        if (d is not null) { rdocs.Remove(d); lifted.Add(d); }
                        if (s is not null) { rshas.Remove(s); lifted.Add(s); }
                    }
                }
                readm.Add((hs, rmDocs, rmShas));
                foreach (var w in u["withdrawals"]!.AsArray())
                {
                    var wo = w!.AsObject();
                    if ((string?)wo["doc_id"] is { } d) docs.Add(d);
                    if ((string?)wo["source_copy_sha256"] is { } s) shas.Add(s);
                }
                var (regDocs, regShas) = ParseRegister((string)u["register_json"]!);
                rdocs.UnionWith(regDocs.Where(d => !lifted.Contains(d)));
                rshas.UnionWith(regShas.Where(s => !lifted.Contains(s)));
            }
            state = new EffectiveExclusions
            {
                Sequence = seq, WithdrawnDocIds = docs, WithdrawnShas = shas, RestrictedDocIds = rdocs, RestrictedShas = rshas, Readmissions = readm,
            };
            _fp = fp; _fpState = state;
            }

            long floor = Math.Max(Math.Max(recorded, ReadHighWater()), Math.Max(_maxSeen, ReadLatchFirst()));
            if (seq < floor) return new(ExclusionHealth.REGRESSED, seq, $"exclusion store sequence {seq} is behind the recorded sequence {floor}", null);
            if (_last is { } prev && !Monotone(prev, state))
                return new(ExclusionHealth.REGRESSED, seq, "exclusion state shrank without a signed readmission", null);
            return new(ExclusionHealth.HEALTHY, seq, "ok", state);
        }
        catch (Exception e) when (e is IOException or FormatException or InvalidOperationException or System.Text.Json.JsonException or NullReferenceException or UnauthorizedAccessException or ArgumentException)
        { return new(ExclusionHealth.UNREADABLE, seq, "exclusion store unreadable: " + e.GetType().Name, null); }
    }

    string? _fp;
    EffectiveExclusions? _fpState;

    static string Fingerprint(string dir, byte[] acc, byte[] trust)
    {
        var sb = new StringBuilder(CanonicalJson.Sha256Hex(acc)).Append('|').Append(CanonicalJson.Sha256Hex(trust));
        var pairs = Path.Combine(dir, "pairs");
        if (Directory.Exists(pairs))
            foreach (var f in new DirectoryInfo(pairs).GetFiles().OrderBy(f => f.Name, StringComparer.Ordinal))
                sb.Append('|').Append(f.Name).Append(':').Append(f.Length).Append(':').Append(f.LastWriteTimeUtc.Ticks);
        return sb.ToString();
    }

    /// Every identity excluded in `prev` is still excluded in `next`, unless an update with a sequence above prev's
    /// readmits that exact identity.
    static bool Monotone(EffectiveExclusions prev, EffectiveExclusions next)
    {
        if (next.Sequence < prev.Sequence) return false;
        var rd = next.Readmissions.Where(r => r.seq > prev.Sequence).SelectMany(r => r.docs).ToHashSet(StringComparer.Ordinal);
        var rs = next.Readmissions.Where(r => r.seq > prev.Sequence).SelectMany(r => r.shas).ToHashSet(StringComparer.Ordinal);
        return prev.WithdrawnDocIds.Concat(prev.RestrictedDocIds).All(d => next.WithdrawnDocIds.Contains(d) || next.RestrictedDocIds.Contains(d) || rd.Contains(d))
            && prev.WithdrawnShas.Concat(prev.RestrictedShas).All(s => next.WithdrawnShas.Contains(s) || next.RestrictedShas.Contains(s) || rs.Contains(s));
    }

    static (byte[] data, byte[] sig) Pair(string dir, long seq, string digest)
    {
        var stem = Path.Combine(dir, "pairs", seq.ToString("D8"));
        var data = DurableFile.ReadShared(stem + ".json");
        var sig = DurableFile.ReadShared(stem + ".sig");
        if (CanonicalJson.Sha256Hex(data) != digest) throw new FormatException("accepted exclusion pair altered");
        return (data, sig);
    }

    /// Restricted-material register (restricted.py register_from_bytes): items with restriction_id, source_sha256,
    /// optional derived_sha256 and doc_id. A malformed register makes the whole store unreadable (fail closed).
    static (HashSet<string> docs, HashSet<string> shas) ParseRegister(string json)
    {
        var items = CanonicalJson.ParseStrict(Encoding.UTF8.GetBytes(json))["items"]!.AsArray();
        if (items.Count == 0) throw new FormatException("register has no items");
        var docs = new HashSet<string>(StringComparer.Ordinal); var shas = new HashSet<string>(StringComparer.Ordinal);
        foreach (var it in items)
        {
            var o = it!.AsObject();
            _ = (string)o["restriction_id"]!;
            var src = ((string)o["source_sha256"]!).ToLowerInvariant();
            if (src.Length != 64 || !src.All(c => c is >= '0' and <= '9' or >= 'a' and <= 'f')) throw new FormatException("malformed source_sha256");
            shas.Add(src);
            foreach (var d in o["derived_sha256"]?.AsArray() ?? []) shas.Add(((string)d!).ToLowerInvariant());
            if ((string?)o["doc_id"] is { Length: > 0 } did) docs.Add(did);
        }
        return (docs, shas);
    }

    long ReadHighWater()
    {
        try { return File.Exists(_o.HighWaterPath) ? (long)CanonicalJson.ParseStrict(DurableFile.ReadShared(_o.HighWaterPath))["sequence"]! : 0; }
        catch (Exception) { return long.MaxValue; }   // an unreadable high-water mark fails closed (REGRESSED)
    }

    long ReadLatchFirst()
    {
        try { return File.Exists(LatchPath) ? (long?)CanonicalJson.ParseStrict(DurableFile.ReadShared(LatchPath))["first_sequence"] ?? 0 : 0; }
        catch (Exception) { return long.MaxValue; }
    }

    static readonly object HighWaterGate = new();

    /// Several readers (the web process, the tool) may raise the mark at once. It only ever moves up; a replace that
    /// loses a race with another reader's replace is retried, and if it still fails the in-memory mark (and the site's
    /// recorded sequence) keep protecting this process until the next read persists it.
    void PersistHighWater(long seq)
    {
        lock (HighWaterGate)
        {
            for (int attempt = 0; attempt < 5; attempt++)
            {
                if (seq <= ReadHighWater()) return;
                try
                {
                    Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(_o.HighWaterPath))!);
                    DurableFile.WriteAtomic(_o.HighWaterPath, CanonicalJson.Bytes(new JsonObject { ["sequence"] = seq }));
                    return;
                }
                catch (Exception e) when (e is IOException or UnauthorizedAccessException) { Thread.Sleep(10); }
            }
        }
    }
}
