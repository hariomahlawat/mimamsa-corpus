// C16 Stage 3 S3-B (B04, B10): VECTOR_PACK verification of a centrally built MIMVEC01 pack against the verified
// generation and the installed, verified model. The site NEVER embeds the corpus: the only embedding here is ONE
// passage-sized input per sampled passage (VECTOR_SPOT_REEMBED), bounded by the sample size.
//   VECTOR_TRAILER            MIMVEC01 magic, shape and SHA-256 trailer (streamed; the file is not held in memory);
//   VECTOR_KEYS_RECOMPUTED    every key recomputed from the site's verified passage text, the pinned model sha and the
//                             pack params (max tokens, passage prefix): no key outside that set (a vector cannot attach to
//                             the wrong text or model) and every indexed passage has one (FULL service);
//   SOURCE_DIGEST_EQUALS_SITE the 2.1 vector_pack_source_digest of the recomputed key set equals the declared one;
//   RESULT_DIGEST             digests.vector_pack_digest over the entries (sorted by key bytes) equals result_digest;
//   VECTOR_SPOT_REEMBED       a stratified seeded sample (strata: passage length band) is re-embedded with the installed
//                             model and compared component-wise; the max absolute difference must be within tolerance.
// Reference: mimamsa_contract.c16.verification (check_vector_pack, vector_pack_source_digest, vector_key).
using System.Buffers.Binary;
using System.Diagnostics;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json.Nodes;
using Mimamsa.Core.Generation;
using Mimamsa.Core.Search;

namespace Mimamsa.Core.ComponentVerification;

/// The installed embedding model as the verifier sees it. `Embed` receives the full embedding input (prefix included)
/// and returns the L2-normalised vector; implementations embed exactly that one input (Mimamsa.Hybrid.E5Embedder).
public interface IPassageEmbedder
{
    string ModelSha256 { get; }
    int Dim { get; }
    float[] EmbedOne(string input, int maxTokens);
}

/// The pack's parameters sidecar (accelerators/vectors/<model sha>.params.json), bound by the signed inventory.
public sealed record VectorPackParams(string ModelSha256, int Dim, int MaxTokens, string PassagePrefix, string QueryPrefix)
{
    public const string Format = "mimamsa-vector-pack-params/2.1";

    public static VectorPackParams Parse(byte[] json)
    {
        var o = JsonNode.Parse(json)!.AsObject();
        if ((string?)o["format"] != Format) throw new FormatException("vector pack params format");
        if ((string?)o["pooling"] != "mean" || o["normalised"]?.GetValue<bool>() != true) throw new FormatException("vector pack params pooling");
        return new((string)o["model_sha256"]!, (int)o["dim"]!, (int)o["max_tokens"]!, (string)o["passage_prefix"]!, (string)o["query_prefix"]!);
    }

    public JsonObject ToJson() => new()
    {
        ["dim"] = Dim, ["format"] = Format, ["max_tokens"] = MaxTokens, ["model_sha256"] = ModelSha256, ["normalised"] = true,
        ["passage_prefix"] = PassagePrefix, ["pooling"] = "mean", ["query_prefix"] = QueryPrefix,
    };
}

/// MIMVEC01 on disk: "MIMVEC01" | int32 dim | int64 count | count x (16-byte key | dim x float32) | SHA-256 trailer.
public sealed class VectorPackFile
{
    public static readonly byte[] Magic = Encoding.ASCII.GetBytes("MIMVEC01");
    const int Head = 8 + 4 + 8;
    public string Path { get; }
    public int Dim { get; }
    public long Count { get; }
    readonly Dictionary<UInt128, long> _offsets;   // key -> record offset
    VectorPackFile(string path, int dim, long count, Dictionary<UInt128, long> offsets) { Path = path; Dim = dim; Count = count; _offsets = offsets; }

    public IReadOnlyCollection<UInt128> Keys => _offsets.Keys;
    public bool Contains(UInt128 k) => _offsets.ContainsKey(k);

    /// Streams the file: trailer, shape, duplicate keys. Null + why when it does not verify.
    public static VectorPackFile? Open(string path, out string? why)
    {
        why = null;
        if (!File.Exists(path)) { why = "missing"; return null; }
        using var f = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read, 1 << 20);
        long len = f.Length;
        if (len < Head + 32) { why = "not a MIMVEC01 vector store"; return null; }
        var head = new byte[Head];
        f.ReadExactly(head);
        if (!head.AsSpan(0, 8).SequenceEqual(Magic)) { why = "not a MIMVEC01 vector store"; return null; }
        int dim = BinaryPrimitives.ReadInt32LittleEndian(head.AsSpan(8));
        long n = BinaryPrimitives.ReadInt64LittleEndian(head.AsSpan(12));
        long rec = 16 + 4L * dim;
        if (dim <= 0 || n < 0 || Head + n * rec + 32 != len) { why = $"shape mismatch (dim {dim}, count {n})"; return null; }
        using var sha = IncrementalHash.CreateHash(HashAlgorithmName.SHA256);
        sha.AppendData(head);
        var offsets = new Dictionary<UInt128, long>((int)Math.Min(n, int.MaxValue));
        var buf = new byte[rec];
        for (long i = 0; i < n; i++)
        {
            f.ReadExactly(buf);
            sha.AppendData(buf);
            var k = BinaryPrimitives.ReadUInt128LittleEndian(buf);
            if (!offsets.TryAdd(k, Head + i * rec)) { why = "duplicate key in the vector store"; return null; }
        }
        var trailer = new byte[32];
        f.ReadExactly(trailer);
        if (!sha.GetHashAndReset().AsSpan().SequenceEqual(trailer)) { why = "SHA-256 trailer does not verify"; return null; }
        return new VectorPackFile(path, dim, n, offsets);
    }

    public float[] Read(UInt128 key)
    {
        using var f = new FileStream(Path, FileMode.Open, FileAccess.Read, FileShare.Read);
        return ReadAt(f, _offsets[key]);
    }

    /// Vectors of the given keys, in order, into dest (keys.Count x Dim), through one stream.
    public void ReadInto(IReadOnlyList<UInt128> keys, float[] dest)
    {
        using var f = new FileStream(Path, FileMode.Open, FileAccess.Read, FileShare.Read, 1 << 16);
        for (int i = 0; i < keys.Count; i++) Array.Copy(ReadAt(f, _offsets[keys[i]]), 0, dest, (long)i * Dim, Dim);
    }

    float[] ReadAt(FileStream f, long off)
    {
        var b = new byte[4 * Dim];
        f.Position = off + 16;
        f.ReadExactly(b);
        var v = new float[Dim];
        for (int i = 0; i < Dim; i++) v[i] = BinaryPrimitives.ReadSingleLittleEndian(b.AsSpan(4 * i));
        return v;
    }

    /// digests.vector_pack_digest: sha256 over (key LE bytes + vector bytes) in ascending key-byte order.
    public string ResultDigest()
    {
        var order = _offsets.Select(kv => (Bytes: KeyBytes(kv.Key), kv.Value)).ToList();
        order.Sort((a, b) => a.Bytes.AsSpan().SequenceCompareTo(b.Bytes));
        using var f = new FileStream(Path, FileMode.Open, FileAccess.Read, FileShare.Read, 1 << 16);
        using var sha = IncrementalHash.CreateHash(HashAlgorithmName.SHA256);
        var rec = new byte[16 + 4 * Dim];
        foreach (var (_, off) in order) { f.Position = off; f.ReadExactly(rec); sha.AppendData(rec); }
        return Convert.ToHexStringLower(sha.GetHashAndReset());
    }

    public static byte[] KeyBytes(UInt128 k) { var b = new byte[16]; BinaryPrimitives.WriteUInt128LittleEndian(b, k); return b; }

    /// Central writer: entries in ascending key-byte order (canonical), then the trailer. Atomic (temp + rename).
    public static void Write(string path, int dim, IEnumerable<(UInt128 Key, float[] Vector)> entries)
    {
        var list = entries.Select(e => (Bytes: KeyBytes(e.Key), e.Vector)).ToList();
        list.Sort((a, b) => a.Bytes.AsSpan().SequenceCompareTo(b.Bytes));
        Directory.CreateDirectory(System.IO.Path.GetDirectoryName(System.IO.Path.GetFullPath(path))!);
        var tmp = $"{path}.{Environment.ProcessId}.{Guid.NewGuid():N}.tmp";
        using (var fs = new FileStream(tmp, FileMode.CreateNew, FileAccess.Write))
        using (var sha = IncrementalHash.CreateHash(HashAlgorithmName.SHA256))
        {
            void W(ReadOnlySpan<byte> b) { fs.Write(b); sha.AppendData(b); }
            W(Magic);
            Span<byte> b4 = stackalloc byte[4]; BinaryPrimitives.WriteInt32LittleEndian(b4, dim); W(b4);
            Span<byte> b8 = stackalloc byte[8]; BinaryPrimitives.WriteInt64LittleEndian(b8, list.Count); W(b8);
            var rec = new byte[16 + 4 * dim];
            foreach (var (kb, v) in list)
            {
                if (v.Length != dim) throw new ArgumentException("dimension mismatch");
                kb.CopyTo(rec, 0);
                for (int i = 0; i < dim; i++) BinaryPrimitives.WriteSingleLittleEndian(rec.AsSpan(16 + 4 * i), v[i]);
                W(rec);
            }
            fs.Write(sha.GetHashAndReset());
            fs.Flush(true);
        }
        File.Move(tmp, path, true);
    }
}

public static class VectorPackVerifier
{
    public static readonly string[] Required = ["VECTOR_TRAILER", "VECTOR_KEYS_RECOMPUTED", "VECTOR_SPOT_REEMBED", "SOURCE_DIGEST_EQUALS_SITE", "RESULT_DIGEST"];
    public const string Spot = "VECTOR_SPOT_REEMBED";
    public const string SourceFormat = "mimamsa-vector-pack-source/2.1";

    /// VectorStore.Key: first 16 bytes of SHA-256("<model sha>|<max tokens>|<input>") as a little-endian UInt128.
    public static UInt128 Key(string modelSha256, int maxTokens, string input) =>
        BinaryPrimitives.ReadUInt128LittleEndian(SHA256.HashData(Encoding.UTF8.GetBytes($"{modelSha256}|{maxTokens}|{input}")));

    /// The embedding inputs of the generation's indexed passages, in index order (what DenseIndex embeds).
    public static List<(Passage Passage, string Input)> Inputs(GenerationStore g, VectorPackParams p) =>
        SearchIndex.IndexedDocuments(g).SelectMany(SearchIndex.OrderedPassages).Select(x => (x, p.PassagePrefix + x.Text)).ToList();

    public static string SourceDigest(string modelSha256, int maxTokens, IEnumerable<UInt128> keys)
    {
        var sb = new StringBuilder();
        sb.Append(SourceFormat).Append('\n').Append("M\t").Append(modelSha256).Append('\n').Append("T\t").Append(maxTokens).Append('\n');
        var sorted = keys.Distinct().Select(VectorPackFile.KeyBytes).ToList();
        sorted.Sort((a, b) => a.AsSpan().SequenceCompareTo(b));
        foreach (var k in sorted) sb.Append("K\t").Append(Convert.ToHexStringLower(k)).Append('\n');
        return Convert.ToHexStringLower(SHA256.HashData(Encoding.ASCII.GetBytes(sb.ToString())));
    }

    public static double MaxAbsDifference(float[] a, float[] b)
    {
        if (a.Length != b.Length || a.Length == 0) return double.PositiveInfinity;
        double m = 0;
        for (int i = 0; i < a.Length; i++) m = Math.Max(m, Math.Abs((double)a[i] - b[i]));
        return m;
    }

    /// Verifies `packPath` (+ params) for `g`. `embedder` null => VECTOR_SPOT_REEMBED NOT_RUN (the pack is not VERIFIED).
    /// `expectedModelSha256` is the release's model_sha256 for the pack (required_models); a different installed model or
    /// params model refuses (mismatched model and pack).
    public static ComponentEvidence Verify(GenerationStore g, string packPath, byte[] paramsJson, string expectedModelSha256, string declaredResultDigest,
                                           string declaredSourceDigest, string releaseId, IPassageEmbedder? embedder, EffectiveSample? spot)
    {
        var ev = new ComponentEvidence("VECTOR_PACK");
        var sw = Stopwatch.StartNew();
        VectorPackParams p;
        try { p = VectorPackParams.Parse(paramsJson); }
        catch (Exception e) when (e is FormatException or System.Text.Json.JsonException or InvalidOperationException or NullReferenceException)
        { ev.Fail("VECTOR_KEYS_RECOMPUTED", "vector pack params unreadable: " + e.Message); return ev; }
        if (p.ModelSha256 != expectedModelSha256) ev.Fail("VECTOR_KEYS_RECOMPUTED", "the pack's model is not the model the release requires");
        if (embedder is not null && (embedder.ModelSha256 != expectedModelSha256 || embedder.Dim != p.Dim))
            ev.Fail(Spot, "the installed model is not the pack's model (model and pack mismatch)");
        var file = VectorPackFile.Open(packPath, out var why);
        ev.TimingsMs["trailer"] = sw.ElapsedMilliseconds;
        if (file is null) { ev.Fail("VECTOR_TRAILER", why!); ev.NotRun(Spot, "pack failed its trailer"); return ev; }
        ev.Pass("VECTOR_TRAILER");
        if (file.Dim != p.Dim) ev.Fail("VECTOR_KEYS_RECOMPUTED", "pack dimension differs from its params");
        sw.Restart();
        var inputs = Inputs(g, p);
        var keyOf = new Dictionary<UInt128, (Passage Passage, string Input)>();
        foreach (var x in inputs) keyOf.TryAdd(Key(expectedModelSha256, p.MaxTokens, x.Input), x);
        int foreign = file.Keys.Count(k => !keyOf.ContainsKey(k));
        int missing = keyOf.Keys.Count(k => !file.Contains(k));
        if (foreign > 0) ev.Fail("VECTOR_KEYS_RECOMPUTED", $"{foreign} vector keys belong to no verified passage of this generation and model");
        if (missing > 0) ev.Fail("VECTOR_KEYS_RECOMPUTED", $"{missing} indexed passages have no vector");
        ev.Pass("VECTOR_KEYS_RECOMPUTED");
        var src = SourceDigest(expectedModelSha256, p.MaxTokens, keyOf.Keys);
        if (src == declaredSourceDigest) ev.Pass("SOURCE_DIGEST_EQUALS_SITE"); else ev.Fail("SOURCE_DIGEST_EQUALS_SITE", "the pack was not built for this generation's passages");
        if (file.ResultDigest() == declaredResultDigest) ev.Pass("RESULT_DIGEST"); else ev.Fail("RESULT_DIGEST", "vector_pack_digest differs from the declared result_digest");
        ev.TimingsMs["keys_and_digests"] = sw.ElapsedMilliseconds;
        ev.Facts["keys"] = keyOf.Count; ev.Facts["entries"] = file.Count; ev.Facts["passages"] = inputs.Count; ev.Facts["dim"] = file.Dim;
        ev.Facts["source_digest"] = src;
        if (embedder is null) { ev.NotRun(Spot, "no installed, verified model to re-embed with (lexical-only)"); return ev; }
        if (ev.Checks.GetValueOrDefault(Spot) == "FAIL") return ev;
        if (spot is null) { ev.NotRun(Spot, GraphVerifier.NotRunInProduction); return ev; }
        sw.Restart();
        var strata = new Dictionary<string, List<string>>(StringComparer.Ordinal);
        var byHex = new Dictionary<string, UInt128>(StringComparer.Ordinal);
        foreach (var (k, x) in keyOf)
        {
            if (!file.Contains(k)) continue;
            var hex = Convert.ToHexStringLower(VectorPackFile.KeyBytes(k));
            byHex[hex] = k;
            var band = $"len{Math.Min(Encoding.UTF8.GetByteCount(x.Input) / 512, 7)}";
            (strata.TryGetValue(band, out var l) ? l : strata[band] = []).Add(hex);
        }
        var chosen = strata.Count == 0 ? [] : B04Sampling.Stratified(releaseId, Spot, strata, spot.Size);
        double worst = 0, tol = spot.Tolerance ?? 0;
        bool ok = chosen.Count > 0;
        foreach (var hex in chosen)
        {
            var k = byHex[hex];
            var fresh = embedder.EmbedOne(keyOf[k].Input, p.MaxTokens);
            var d = MaxAbsDifference(file.Read(k), fresh);
            worst = Math.Max(worst, d);
            if (!(d <= tol)) ok = false;
        }
        ev.TimingsMs["spot_reembed"] = sw.ElapsedMilliseconds;
        var s = spot.ToJson();
        s["selection"] = "DETERMINISTIC_STRATIFIED_SEEDED_BY_RELEASE_ID"; s["unit"] = "passage (one query-sized embed each)"; s["population"] = byHex.Count;
        s["selected"] = chosen.Count; s["max_abs_difference"] = worst; s["seed"] = releaseId;
        ev.Samples[Spot] = s;
        if (ok) ev.Pass(Spot); else ev.Fail(Spot, $"a sampled vector differs from a fresh embedding beyond the tolerance (max {worst:E3})");
        return ev;
    }
}
