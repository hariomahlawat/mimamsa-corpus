// Passage embeddings for the active generation, computed once and cached on disk keyed by
// (generation id, model SHA-256, passage fingerprint). A cache whose key or fingerprint differs is ignored and
// rebuilt, never trusted. Brute-force cosine (vectors are normalised): exact, deterministic, no ANN approximation.
using System.Diagnostics;
using System.Security.Cryptography;
using System.Text;
using Mimamsa.Core.Search;

namespace Mimamsa.Hybrid;

public sealed class DenseIndex : ISemanticScorer, IDisposable
{
    readonly E5Embedder _emb;
    readonly float[] _vec;   // N * Dim
    public int Count { get; }
    public string Description { get; }
    public TimeSpan BuildTime { get; }
    public bool FromCache { get; }

    DenseIndex(E5Embedder emb, float[] vec, int n, bool fromCache, TimeSpan t, string modelLabel)
    {
        _emb = emb; _vec = vec; Count = n; FromCache = fromCache; BuildTime = t;
        Description = $"{modelLabel} ({emb.Device})";
    }

    public static DenseIndex Build(SearchIndex ix, string generationId, E5Embedder emb, string? cacheDir, string modelLabel,
                                   int maxPassageTokens = 256, int batch = 16, Action<string>? log = null)
    {
        var sw = Stopwatch.StartNew();
        int n = ix.Passages.Count, d = E5Embedder.Dim;
        var fp = Fingerprint(ix, maxPassageTokens);
        string? file = cacheDir is null ? null : Path.Combine(cacheDir, $"{Safe(generationId)}.{emb.ModelSha256[..12]}.{fp[..16]}.emb");
        if (file is not null && File.Exists(file))
        {
            var bytes = File.ReadAllBytes(file);
            if (bytes.Length == n * d * 4)
            {
                var v = new float[n * d];
                Buffer.BlockCopy(bytes, 0, v, 0, bytes.Length);
                log?.Invoke($"hybrid: loaded {n} passage vectors from cache in {sw.ElapsedMilliseconds} ms");
                return new DenseIndex(emb, v, n, true, sw.Elapsed, modelLabel);
            }
        }
        var vec = new float[n * d];
        for (int s = 0; s < n; s += batch)
        {
            var texts = Enumerable.Range(s, Math.Min(batch, n - s)).Select(i => "passage: " + ix.Passages[i].Text).ToList();
            var e = emb.Embed(texts, maxPassageTokens);
            for (int i = 0; i < e.Length; i++) Array.Copy(e[i], 0, vec, (s + i) * d, d);
            if (log is not null && (s / batch) % 200 == 0) log($"hybrid: embedded {s + e.Length}/{n} passages");
        }
        if (file is not null)
        {
            Directory.CreateDirectory(cacheDir!);
            var bytes = new byte[vec.Length * 4];
            Buffer.BlockCopy(vec, 0, bytes, 0, bytes.Length);
            var tmp = file + ".tmp";
            File.WriteAllBytes(tmp, bytes);
            File.Move(tmp, file, true);
        }
        log?.Invoke($"hybrid: embedded {n} passages in {sw.Elapsed.TotalSeconds:0.0} s ({emb.Device})");
        return new DenseIndex(emb, vec, n, false, sw.Elapsed, modelLabel);
    }

    public IReadOnlyList<(int Passage, double Score)> TopK(string query, int k)
    {
        if (string.IsNullOrWhiteSpace(query) || Count == 0) return Array.Empty<(int, double)>();
        var q = _emb.EmbedQuery(query);
        int d = E5Embedder.Dim;
        var scores = new float[Count];
        Parallel.For(0, Count, i =>
        {
            float s = 0; int o = i * d;
            for (int j = 0; j < d; j++) s += q[j] * _vec[o + j];
            scores[i] = s;
        });
        return Enumerable.Range(0, Count).OrderByDescending(i => scores[i]).ThenBy(i => i).Take(k)
            .Select(i => (i, (double)scores[i])).ToList();
    }

    /// Identity of the passage set and how it is embedded; any change invalidates the cache.
    internal static string Fingerprint(SearchIndex ix, int maxTokens)
    {
        using var h = IncrementalHash.CreateHash(HashAlgorithmName.SHA256);
        h.AppendData(Encoding.UTF8.GetBytes($"e5|passage:|{maxTokens}|"));
        foreach (var p in ix.Passages) h.AppendData(Encoding.UTF8.GetBytes(p.DocId + "\u0001" + p.Text + "\u0002"));
        return Convert.ToHexStringLower(h.GetHashAndReset());
    }

    static string Safe(string s) => new(s.Select(c => char.IsLetterOrDigit(c) || c is '-' or '_' ? c : '_').ToArray());

    public void Dispose() => _emb.Dispose();
}
