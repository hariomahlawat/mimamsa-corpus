// C15 WP1 (ADR-0007): incremental indexing. Each document's passage tokens are cached under (doc_id, derivative_id) in
// <index root>/forward-cache.sqlite. A build for a new generation tokenises only documents whose derivative is new or
// changed and reads the rest from the cache; the postings it produces are identical either way (same passage order,
// same term groups and positions). The cache is an accelerator, not a source of truth: an entry whose passage anchors
// do not match the document exactly is ignored and rewritten, and an unreadable cache file is deleted and rebuilt.
using System.Text;
using Microsoft.Data.Sqlite;
using Mimamsa.Core.Generation;

namespace Mimamsa.Core.Search;

internal sealed class ForwardCache : IDisposable
{
    public const string File = "forward-cache.sqlite";
    readonly SqliteConnection _c;
    SqliteTransaction? _tx;
    int _pending;
    public int Hits, Misses;
    readonly HashSet<(string, string)> _used = new();

    ForwardCache(SqliteConnection c) => _c = c;

    public static ForwardCache Open(string root, Action<string>? log)
    {
        var path = Path.Combine(root, File);
        for (int attempt = 0; ; attempt++)
        {
            var c = new SqliteConnection(new SqliteConnectionStringBuilder { DataSource = path, Mode = SqliteOpenMode.ReadWriteCreate, Pooling = false }.ToString());
            try
            {
                c.Open();
                Exec(c, "PRAGMA journal_mode = WAL; PRAGMA synchronous = NORMAL;" +
                        "CREATE TABLE IF NOT EXISTS fwd(doc_id TEXT NOT NULL, derivative_id TEXT NOT NULL, format TEXT NOT NULL, tokens BLOB NOT NULL, PRIMARY KEY(doc_id, derivative_id));");
                if ((string?)new SqliteCommand("PRAGMA quick_check", c).ExecuteScalar() != "ok") throw new InvalidDataException("forward cache quick_check failed");
                return new ForwardCache(c);
            }
            catch (Exception e) when (attempt == 0 && e is SqliteException or InvalidDataException)
            {
                c.Dispose(); SqliteConnection.ClearAllPools();
                log?.Invoke($"search index: forward cache unusable ({e.GetType().Name}); recreating");
                foreach (var f in new[] { path, path + "-wal", path + "-shm" }) if (System.IO.File.Exists(f)) System.IO.File.Delete(f);
            }
        }
    }

    static void Exec(SqliteConnection c, string sql) { using var cmd = new SqliteCommand(sql, c); cmd.ExecuteNonQuery(); }

    /// Tokens for the document's ordered passages, from the cache when it holds an exactly matching entry.
    public SearchIndex.PassageTokens[] Get(DocumentRecord d, IReadOnlyList<Passage> ordered)
    {
        _used.Add((d.DocId, d.DerivativeId ?? ""));
        using (var cmd = new SqliteCommand("SELECT tokens FROM fwd WHERE doc_id = $d AND derivative_id = $v AND format = $f", _c, _tx))
        {
            cmd.Parameters.AddWithValue("$d", d.DocId); cmd.Parameters.AddWithValue("$v", d.DerivativeId ?? ""); cmd.Parameters.AddWithValue("$f", IndexStore.FormatVersion);
            if (cmd.ExecuteScalar() is byte[] blob && TryDecode(blob, ordered) is { } cached) { Hits++; return cached; }
        }
        Misses++;
        var fresh = ordered.Select(SearchIndex.Tokenise).ToArray();
        _tx ??= _c.BeginTransaction();
        using (var cmd = new SqliteCommand("INSERT OR REPLACE INTO fwd VALUES($d,$v,$f,$t)", _c, _tx))
        {
            cmd.Parameters.AddWithValue("$d", d.DocId); cmd.Parameters.AddWithValue("$v", d.DerivativeId ?? "");
            cmd.Parameters.AddWithValue("$f", IndexStore.FormatVersion); cmd.Parameters.AddWithValue("$t", Encode(ordered, fresh));
            cmd.ExecuteNonQuery();
        }
        if (++_pending >= 500) Commit();
        return fresh;
    }

    void Commit() { _tx?.Commit(); _tx?.Dispose(); _tx = null; _pending = 0; }

    /// Removes entries for documents/derivatives the just-built generation does not use (bounded growth).
    public int Prune()
    {
        Commit();
        var stale = new List<(string, string)>();
        using (var r = new SqliteCommand("SELECT doc_id, derivative_id FROM fwd", _c).ExecuteReader())
            while (r.Read()) { var k = (r.GetString(0), r.GetString(1)); if (!_used.Contains(k)) stale.Add(k); }
        using var tx = _c.BeginTransaction();
        foreach (var (d, v) in stale)
        {
            using var cmd = new SqliteCommand("DELETE FROM fwd WHERE doc_id = $d AND derivative_id = $v", _c, tx);
            cmd.Parameters.AddWithValue("$d", d); cmd.Parameters.AddWithValue("$v", v); cmd.ExecuteNonQuery();
        }
        tx.Commit();
        return stale.Count;
    }

    public void Dispose() { Commit(); _c.Dispose(); }

    // ------------------------------------------------------------------ encoding
    static void PutU(Stream s, uint v) { while (v >= 0x80) { s.WriteByte((byte)(v | 0x80)); v >>= 7; } s.WriteByte((byte)v); }
    static void PutS(Stream s, string t) { var b = Encoding.UTF8.GetBytes(t); PutU(s, (uint)b.Length); s.Write(b); }
    static uint GetU(byte[] b, ref int i) { uint v = 0; int sh = 0; while (true) { byte x = b[i++]; v |= (uint)(x & 0x7F) << sh; if (x < 0x80) return v; sh += 7; if (sh > 28) throw new InvalidDataException(); } }
    static string GetS(byte[] b, ref int i) { int n = (int)GetU(b, ref i); var s = Encoding.UTF8.GetString(b, i, n); i += n; return s; }

    static byte[] Encode(IReadOnlyList<Passage> ordered, SearchIndex.PassageTokens[] t)
    {
        var s = new MemoryStream();
        PutU(s, (uint)ordered.Count);
        for (int k = 0; k < ordered.Count; k++)
        {
            var p = ordered[k]; var x = t[k];
            PutS(s, p.PassageId); PutU(s, (uint)p.Page); PutU(s, (uint)p.CharStart); PutU(s, (uint)p.CharEnd); PutU(s, (uint)p.Text.Length);
            PutU(s, (uint)x.Len); PutU(s, (uint)x.Army); PutU(s, (uint)x.Navy); PutU(s, (uint)x.Air); PutU(s, (uint)x.Groups.Length);
            foreach (var (term, pos) in x.Groups)
            {
                PutS(s, term); PutU(s, (uint)pos.Length);
                int prev = 0; foreach (var q in pos) { PutU(s, (uint)(q - prev)); prev = q; }
            }
        }
        return s.ToArray();
    }

    /// Null unless the entry describes exactly these passages (id, page, offsets, text length) and decodes completely.
    static SearchIndex.PassageTokens[]? TryDecode(byte[] b, IReadOnlyList<Passage> ordered)
    {
        try
        {
            int i = 0;
            if ((int)GetU(b, ref i) != ordered.Count) return null;
            var res = new SearchIndex.PassageTokens[ordered.Count];
            for (int k = 0; k < ordered.Count; k++)
            {
                var p = ordered[k];
                if (GetS(b, ref i) != p.PassageId || GetU(b, ref i) != p.Page || GetU(b, ref i) != p.CharStart || GetU(b, ref i) != p.CharEnd || GetU(b, ref i) != p.Text.Length) return null;
                int len = (int)GetU(b, ref i), army = (int)GetU(b, ref i), navy = (int)GetU(b, ref i), air = (int)GetU(b, ref i), ng = (int)GetU(b, ref i);
                var groups = new (string, int[])[ng];
                for (int gI = 0; gI < ng; gI++)
                {
                    var term = GetS(b, ref i); int n = (int)GetU(b, ref i);
                    var pos = new int[n]; int prev = 0;
                    for (int j = 0; j < n; j++) { prev += (int)GetU(b, ref i); pos[j] = prev; }
                    groups[gI] = (term, pos);
                }
                res[k] = new SearchIndex.PassageTokens(len, groups, army, navy, air);
            }
            return i == b.Length ? res : null;
        }
        catch (Exception e) when (e is InvalidDataException or IndexOutOfRangeException or ArgumentException) { return null; }
    }
}
