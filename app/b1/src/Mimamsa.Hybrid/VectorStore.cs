// C15 WP2: persistent, incremental passage-vector store (one file per embedding model).
//
// Each vector is keyed by a 128-bit prefix of SHA-256(model sha | max tokens | embedding input text), so a passage is
// embedded once and reused by every later generation that holds the same text; only new or changed passages are
// embedded (incremental). Format (little-endian):
//   "MIMVEC01" | int32 dim | int64 count | count x (16-byte key | dim x float32) | 32-byte SHA-256 of all preceding bytes
// The trailer is verified on load; a store that fails the check is ignored and rebuilt, never trusted. Publication is
// atomic (write to a temporary file, then replace), and long embedding runs checkpoint periodically, so an interrupted
// run resumes from the last checkpoint. The store holds vectors only, never eligibility: withdrawn or ineligible
// passages are excluded at query time by the caller's predicate.
using System.Buffers.Binary;
using System.Security.Cryptography;
using System.Text;

namespace Mimamsa.Hybrid;

public sealed class VectorStore
{
    static readonly byte[] Magic = Encoding.ASCII.GetBytes("MIMVEC01");
    public int Dim { get; }
    readonly Dictionary<UInt128, float[]> _map = new();
    public int Count => _map.Count;
    public string? LoadIssue { get; private set; }

    public VectorStore(int dim) { Dim = dim; }

    public static UInt128 Key(string modelSha256, int maxTokens, string input)
    {
        var h = SHA256.HashData(Encoding.UTF8.GetBytes($"{modelSha256}|{maxTokens}|{input}"));
        return BinaryPrimitives.ReadUInt128LittleEndian(h);
    }

    public bool TryGet(UInt128 key, out float[] v) => _map.TryGetValue(key, out v!);
    public IEnumerable<UInt128> Keys() => _map.Keys;
    public void Put(UInt128 key, float[] v) { if (v.Length != Dim) throw new ArgumentException("dimension mismatch"); _map[key] = v; }

    /// Load and verify. Returns an empty store (with LoadIssue set) when the file is missing, truncated, of another
    /// dimension or fails the SHA-256 trailer check.
    public static VectorStore Load(string path, int dim)
    {
        var s = new VectorStore(dim);
        if (!File.Exists(path)) { s.LoadIssue = "missing"; return s; }
        var bytes = File.ReadAllBytes(path);
        const int head = 8 + 4 + 8;
        if (bytes.Length < head + 32 || !bytes.AsSpan(0, 8).SequenceEqual(Magic)) { s.LoadIssue = "not a vector store"; return s; }
        var body = bytes.AsSpan(0, bytes.Length - 32);
        if (!SHA256.HashData(body).AsSpan().SequenceEqual(bytes.AsSpan(bytes.Length - 32))) { s.LoadIssue = "integrity check failed (SHA-256 trailer)"; return s; }
        int d = BinaryPrimitives.ReadInt32LittleEndian(bytes.AsSpan(8));
        long n = BinaryPrimitives.ReadInt64LittleEndian(bytes.AsSpan(12));
        long rec = 16 + 4L * d;
        if (d != dim || head + n * rec != body.Length) { s.LoadIssue = $"shape mismatch (dim {d}, count {n})"; return s; }
        for (long i = 0; i < n; i++)
        {
            int o = (int)(head + i * rec);
            var key = BinaryPrimitives.ReadUInt128LittleEndian(bytes.AsSpan(o, 16));
            var v = new float[d];
            Buffer.BlockCopy(bytes, o + 16, v, 0, d * 4);
            s._map[key] = v;
        }
        return s;
    }

    /// Atomic publish of the given keys (and their vectors) to `path`.
    public void Save(string path, IEnumerable<UInt128> keys)
    {
        var list = keys.Distinct().Where(_map.ContainsKey).ToList();
        Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(path))!);
        // unique per writer: two processes publishing at once never share a temporary file (last complete file wins)
        var tmp = $"{path}.{Environment.ProcessId}.{Guid.NewGuid():N}.tmp";
        using (var fs = new FileStream(tmp, FileMode.Create, FileAccess.Write, FileShare.None))
        using (var sha = IncrementalHash.CreateHash(HashAlgorithmName.SHA256))
        {
            void W(ReadOnlySpan<byte> b) { fs.Write(b); sha.AppendData(b); }
            W(Magic);
            Span<byte> b4 = stackalloc byte[4]; BinaryPrimitives.WriteInt32LittleEndian(b4, Dim); W(b4);
            Span<byte> b8 = stackalloc byte[8]; BinaryPrimitives.WriteInt64LittleEndian(b8, list.Count); W(b8);
            var rec = new byte[16 + 4 * Dim];
            foreach (var k in list)
            {
                BinaryPrimitives.WriteUInt128LittleEndian(rec.AsSpan(0, 16), k);
                Buffer.BlockCopy(_map[k], 0, rec, 16, 4 * Dim);
                W(rec);
            }
            fs.Write(sha.GetHashAndReset());
            fs.Flush(true);
        }
        try { File.Move(tmp, path, true); }
        catch { try { File.Delete(tmp); } catch { /* best effort */ } throw; }
    }
}
