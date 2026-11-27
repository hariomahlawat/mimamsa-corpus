// C15 WP1 (ADR-0007): postings persisted in SQLite, read on demand. The vocabulary (term -> ordinal, df) is held in
// memory because prefix expansion and the speller enumerate it; posting lists are loaded per term through a bounded,
// thread-safe LRU cache. Encoding (all unsigned LEB128 varints): per posting [delta passage][position count]
// [first position][position deltas...]; passages ascend, positions ascend (as built), so decoding reproduces the B1 lists.
using Microsoft.Data.Sqlite;

namespace Mimamsa.Core.Search;

internal sealed class SqlitePostingTable : PostingTable
{
    readonly string _cs;
    readonly Dictionary<string, (int ord, int df)> _vocab;
    readonly string[] _keys;
    readonly long _budget;
    readonly object _lock = new();
    readonly LinkedList<(string term, List<SearchIndex.Posting> list, long cost)> _lru = new();
    readonly Dictionary<string, LinkedListNode<(string term, List<SearchIndex.Posting> list, long cost)>> _cached = new(StringComparer.Ordinal);
    long _used;
    public long CacheHits, CacheMisses;

    SqlitePostingTable(string cs, string[] keys, Dictionary<string, (int, int)> vocab, long budget)
    { _cs = cs; _keys = keys; _vocab = vocab; _budget = budget; }

    public static string ReadOnlyConnectionString(string dbPath) =>
        new SqliteConnectionStringBuilder { DataSource = dbPath, Mode = SqliteOpenMode.ReadOnly, Pooling = true, Cache = SqliteCacheMode.Private }.ToString();

    public static SqlitePostingTable Open(string dbPath, long cacheBytes)
    {
        var cs = ReadOnlyConnectionString(dbPath);
        using var c = new SqliteConnection(cs);
        c.Open();
        int n = Convert.ToInt32(new SqliteCommand("SELECT count(*) FROM terms", c).ExecuteScalar());
        var keys = new string[n];
        var vocab = new Dictionary<string, (int, int)>(n, StringComparer.Ordinal);
        using (var r = new SqliteCommand("SELECT ord, term, df FROM terms ORDER BY ord", c).ExecuteReader())
            while (r.Read())
            {
                int ord = r.GetInt32(0);
                if (ord != vocab.Count) throw new InvalidDataException("index vocabulary ordinals are not contiguous");
                var t = r.GetString(1);
                keys[ord] = t; vocab[t] = (ord, r.GetInt32(2));
            }
        return new SqlitePostingTable(cs, keys, vocab, cacheBytes);
    }

    public override IEnumerable<string> Keys => _keys;
    public override int Count => _keys.Length;
    public override int Df(string term) => _vocab.TryGetValue(term, out var v) ? v.df : 0;

    public override bool TryGetValue(string term, out List<SearchIndex.Posting> list)
    {
        if (!_vocab.TryGetValue(term, out var v)) { list = null!; return false; }
        lock (_lock)
            if (_cached.TryGetValue(term, out var node)) { _lru.Remove(node); _lru.AddFirst(node); CacheHits++; list = node.Value.list; return true; }
        byte[] blob;
        using (var c = new SqliteConnection(_cs))
        {
            c.Open();
            using var cmd = new SqliteCommand("SELECT postings FROM terms WHERE ord = $o", c);
            cmd.Parameters.AddWithValue("$o", v.ord);
            blob = (byte[])cmd.ExecuteScalar()!;
        }
        list = Decode(blob, v.df, out long positions);
        long cost = 48L * list.Count + 4 * positions + 64;
        lock (_lock)
        {
            CacheMisses++;
            if (_cached.TryGetValue(term, out var existing)) { list = existing.Value.list; return true; }   // another reader won
            if (cost <= _budget)
            {
                _cached[term] = _lru.AddFirst((term, list, cost));
                _used += cost;
                while (_used > _budget && _lru.Last is { } last) { _lru.RemoveLast(); _cached.Remove(last.Value.term); _used -= last.Value.cost; }
            }
        }
        return true;
    }

    public (long used, long budget, int entries) CacheState { get { lock (_lock) return (_used, _budget, _cached.Count); } }

    // ------------------------------------------------------------------ encoding
    internal static byte[] Encode(List<SearchIndex.Posting> list)
    {
        var buf = new MemoryStream(list.Count * 6);
        int prevP = 0;
        foreach (var x in list)
        {
            Put(buf, (uint)(x.P - prevP)); prevP = x.P;
            Put(buf, (uint)x.Pos.Length);
            int prev = 0;
            for (int i = 0; i < x.Pos.Length; i++) { Put(buf, (uint)(x.Pos[i] - prev)); prev = x.Pos[i]; }
        }
        return buf.ToArray();
    }

    static void Put(Stream s, uint v) { while (v >= 0x80) { s.WriteByte((byte)(v | 0x80)); v >>= 7; } s.WriteByte((byte)v); }

    static uint Get(ReadOnlySpan<byte> b, ref int i)
    {
        uint v = 0; int shift = 0;
        while (true)
        {
            if (i >= b.Length || shift > 28) throw new InvalidDataException("corrupt postings");
            byte x = b[i++];
            v |= (uint)(x & 0x7F) << shift;
            if (x < 0x80) return v;
            shift += 7;
        }
    }

    internal static List<SearchIndex.Posting> Decode(ReadOnlySpan<byte> b, int df, out long positions)
    {
        var list = new List<SearchIndex.Posting>(df);
        int i = 0, p = 0; positions = 0;
        for (int k = 0; k < df; k++)
        {
            p += (int)Get(b, ref i);
            int n = (int)Get(b, ref i);
            if (n <= 0 || n > 1_000_000) throw new InvalidDataException("corrupt postings");
            var pos = new int[n];
            int prev = 0;
            for (int j = 0; j < n; j++) { prev += (int)Get(b, ref i); pos[j] = prev; }
            positions += n;
            list.Add(new SearchIndex.Posting(p, pos));
        }
        if (i != b.Length) throw new InvalidDataException("corrupt postings (trailing bytes)");
        return list;
    }
}
