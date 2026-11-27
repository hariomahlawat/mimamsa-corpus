// Passage embeddings for the active generation over a persistent, incremental VectorStore (C15 WP2).
// Only passages whose (model, max tokens, text) is not already in the store are embedded; the store is checkpointed
// during long runs (an interrupted run resumes) and published atomically. Vectors of the previous generation are kept
// (bounded) so a rollback does not re-embed. Brute-force cosine (vectors are normalised): exact, deterministic.
// Eligibility is applied INSIDE the scan, so withdrawn or ineligible passages neither appear nor consume depth.
using System.Diagnostics;
using System.Security.Cryptography;
using System.Text;
using Mimamsa.Core.Search;

namespace Mimamsa.Hybrid;

public sealed class DenseIndex : ISemanticScorer, IDisposable
{
    readonly E5Embedder _emb;
    readonly float[] _vec;   // N * Dim, in passage-index order of the active generation
    readonly int _dim;
    public int Count { get; }
    public string Description { get; }
    public TimeSpan BuildTime { get; }
    public int Reused { get; }
    public int Embedded { get; }
    public string? StoreIssue { get; }

    DenseIndex(E5Embedder emb, float[] vec, int n, TimeSpan t, string modelLabel, int reused, int embedded, string? issue)
    {
        _emb = emb; _vec = vec; _dim = emb.Dim; Count = n; BuildTime = t; Reused = reused; Embedded = embedded; StoreIssue = issue;
        Description = $"{modelLabel} ({emb.Device})";
    }

    public static string StorePath(string cacheDir, E5Embedder emb) => Path.Combine(cacheDir, $"{emb.ModelSha256[..12]}.mvs");

    public static DenseIndex Build(SearchIndex ix, string generationId, E5Embedder emb, string? cacheDir, string modelLabel,
                                   int maxPassageTokens = 256, int batch = 16, Action<string>? log = null, int checkpointEvery = 2000)
    {
        var sw = Stopwatch.StartNew();
        int n = ix.Passages.Count, d = emb.Dim;
        string? path = cacheDir is null ? null : StorePath(cacheDir, emb);
        var store = path is null ? new VectorStore(d) : VectorStore.Load(path, d);
        string? issue = store.LoadIssue is null or "missing" ? null : store.LoadIssue;
        if (issue is not null) log?.Invoke($"hybrid: vector store not used ({issue}); rebuilding");
        var previous = store.Count;
        var keys = new UInt128[n];
        var missing = new List<int>();
        for (int i = 0; i < n; i++)
        {
            keys[i] = VectorStore.Key(emb.ModelSha256, maxPassageTokens, emb.PassagePrefix + ix.Passages[i].Text);
            if (!store.TryGet(keys[i], out _)) missing.Add(i);
        }
        int reused = n - missing.Count;
        log?.Invoke($"hybrid: {reused}/{n} passage vectors reused from the store; {missing.Count} to embed");
        // keep the previous generation's vectors (rollback without re-embedding), bounded to the current size
        var keep = new HashSet<UInt128>(keys);
        int sinceCheckpoint = 0;
        for (int s = 0; s < missing.Count; s += batch)
        {
            var idx = missing.Skip(s).Take(batch).ToList();
            var e = emb.Embed(idx.Select(i => emb.PassagePrefix + ix.Passages[i].Text).ToList(), maxPassageTokens);
            for (int j = 0; j < idx.Count; j++) store.Put(keys[idx[j]], e[j]);
            sinceCheckpoint += idx.Count;
            if (path is not null && sinceCheckpoint >= checkpointEvery)
            {
                try { store.Save(path, keys.Where(k => store.TryGet(k, out _))); }
                catch (IOException ex) { log?.Invoke($"hybrid: checkpoint not saved ({ex.GetType().Name}); continuing"); }
                sinceCheckpoint = 0;
                log?.Invoke($"hybrid: embedded {s + idx.Count}/{missing.Count} new passages (checkpoint saved)");
            }
        }
        var vec = new float[(long)n * d <= int.MaxValue ? n * d : throw new InvalidOperationException("vector set too large for one array")];
        for (int i = 0; i < n; i++) { store.TryGet(keys[i], out var v); Array.Copy(v, 0, vec, i * d, d); }
        // Persist only when something changed: new vectors, a store that failed its check, or old entries to prune.
        // (Passages with identical text share one key, so the store's count is compared with the DISTINCT key count.)
        bool prune = previous > 2 * keep.Count;
        if (path is not null && (missing.Count > 0 || issue is not null || prune))
        {
            var retained = prune ? keep.AsEnumerable() : keys.Concat(StoreKeysNotIn(store, keep));
            try { store.Save(path, retained); }
            catch (IOException ex) { log?.Invoke($"hybrid: vector store not saved ({ex.GetType().Name}); vectors are in memory and will be re-saved later"); }
        }
        log?.Invoke($"hybrid: {n} passages ready in {sw.Elapsed.TotalSeconds:0.0} s ({emb.Device}); embedded {missing.Count}, reused {reused}");
        return new DenseIndex(emb, vec, n, sw.Elapsed, modelLabel, reused, missing.Count, issue);
    }

    static IEnumerable<UInt128> StoreKeysNotIn(VectorStore s, HashSet<UInt128> keep) => s.Keys().Where(k => !keep.Contains(k));

    public IReadOnlyList<(int Passage, double Score)> TopK(string query, int k) => TopK(query, k, null);

    /// Top-k by cosine similarity among passages for which `include` is true (all when null); ties by index.
    public IReadOnlyList<(int Passage, double Score)> TopK(string query, int k, Func<int, bool>? include)
    {
        if (string.IsNullOrWhiteSpace(query) || Count == 0 || k <= 0) return Array.Empty<(int, double)>();
        var q = _emb.EmbedQuery(query);
        int d = _dim;
        var scores = new float[Count];
        Parallel.For(0, Count, i =>
        {
            if (include is not null && !include(i)) { scores[i] = float.NegativeInfinity; return; }
            float s = 0; int o = i * d;
            for (int j = 0; j < d; j++) s += q[j] * _vec[o + j];
            scores[i] = s;
        });
        return Enumerable.Range(0, Count).Where(i => !float.IsNegativeInfinity(scores[i]))
            .OrderByDescending(i => scores[i]).ThenBy(i => i).Take(k)
            .Select(i => (i, (double)scores[i])).ToList();
    }

    /// Identity of the passage set and how it is embedded (reported; the store itself is keyed per passage).
    internal static string Fingerprint(SearchIndex ix, int maxTokens)
    {
        using var h = IncrementalHash.CreateHash(HashAlgorithmName.SHA256);
        h.AppendData(Encoding.UTF8.GetBytes($"e5|passage:|{maxTokens}|"));
        foreach (var p in ix.Passages) h.AppendData(Encoding.UTF8.GetBytes(p.DocId + "\u0001" + p.Text + "\u0002"));
        return Convert.ToHexStringLower(h.GetHashAndReset());
    }

    public void Dispose() => _emb.Dispose();
}
