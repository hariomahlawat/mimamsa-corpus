// C15 WP1 (ADR-0007): generation-scoped persistent search index with atomic publication, integrity verification,
// crash recovery and retention for rollback.
//
// Layout under the index root (default <site>/search-index, configurable):
//   <generation>/search.sqlite   postings, vocabulary, per-document and per-passage metadata
//   <generation>/MANIFEST.json   format, generation, source digest, counts, file size and SHA-256
//   .building-<generation>-<id>/ an index being built (never opened for serving; removed at the next start)
//   .quarantine-<generation>-<utc>/  a published index that failed verification (kept for inspection)
// An index is served only after its manifest, SHA-256 (when VerifyOnOpen), SQLite quick_check, format, generation,
// source digest and counts all match the generation being served. Otherwise it is quarantined and rebuilt from the
// verified generation, or start-up is refused when RebuildOnFailure is false (fail closed either way).
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using Microsoft.Data.Sqlite;
using Mimamsa.Core.Generation;

namespace Mimamsa.Core.Search;

public sealed record SearchIndexOptions
{
    /// Bytes of decoded posting lists kept in the LRU cache.
    public long CacheBytes { get; init; } = 128L << 20;
    /// Hash the whole index file against its manifest and run PRAGMA quick_check before serving it.
    public bool VerifyOnOpen { get; init; } = true;
    /// A published index that fails verification is quarantined and rebuilt (true) or start-up is refused (false).
    public bool RebuildOnFailure { get; init; } = true;
    /// Published indexes of other generations kept for rollback (newest first).
    public int KeepPrevious { get; init; } = 2;
    /// Passages tokenised before their postings are spilled to a run (bounds build memory).
    public int BuildChunkPassages { get; init; } = 100_000;
    /// How long to wait for another process that is opening or building in the same index root.
    public TimeSpan LockTimeout { get; init; } = TimeSpan.FromMinutes(30);
    /// Incremental builds: reuse cached passage tokens of unchanged documents (forward-cache.sqlite under the root).
    public bool UseForwardCache { get; init; } = true;
    /// TEST ONLY: throw after writing this many vocabulary rows, simulating a crash during a build.
    public int? FailAfterTerms { get; init; }
    /// C16 B02: a pinned build time written as built_utc instead of the wall clock, so that a central build produces
    /// byte-identical indexes from the same inputs. Null (the default) keeps the existing behaviour.
    public DateTimeOffset? BuildTimeUtc { get; init; }
}

public sealed class IndexIntegrityException(string message) : Exception(message);

internal sealed class IndexStore(string root, SearchIndexOptions options, Action<string>? log)
{
    public const string DbFile = "search.sqlite", ManifestFile = "MANIFEST.json";
    /// Bump when tokenisation, encoding or schema changes: every existing index is then rebuilt.
    public const string FormatVersion = "mimamsa-search-index/1";

    void Log(string m) => log?.Invoke(m);

    string BuiltUtc => options.BuildTimeUtc is { } t ? t.UtcDateTime.ToString("O") : DateTime.UtcNow.ToString("O");

    static string Safe(string generation) => string.Concat(generation.Select(c => char.IsLetterOrDigit(c) || c is '-' or '_' or '.' ? c : '_'));

    /// Identity of the indexed content: documents, derivatives, copies and passage anchors (not the text itself, which
    /// the derivative id already fixes) plus the index format. A different digest means the index must be rebuilt.
    internal static string SourceDigest(IReadOnlyList<DocumentRecord> docs)
    {
        using var h = IncrementalHash.CreateHash(HashAlgorithmName.SHA256);
        void Add(string s) => h.AppendData(Encoding.UTF8.GetBytes(s + "\n"));
        Add(FormatVersion);
        foreach (var d in docs)
        {
            Add($"D\t{d.DocId}\t{d.DerivativeId}\t{d.CopySha}");
            foreach (var p in SearchIndex.OrderedPassages(d)) Add($"P\t{p.PassageId}\t{p.Page}\t{p.CharStart}\t{p.CharEnd}\t{p.Length}");
        }
        return Convert.ToHexString(h.GetHashAndReset()).ToLowerInvariant();
    }

    /// Exclusive, cross-process lock on the index root for the whole open/build: a second service starting against the
    /// same root waits instead of deleting the first one's in-progress build or racing to publish. The OS releases it
    /// if the holder crashes, which is when the leftover .building directory becomes safe to delete.
    FileStream AcquireLock()
    {
        var path = Path.Combine(root, ".lock");
        var until = DateTime.UtcNow + options.LockTimeout;
        while (true)
        {
            try { return new FileStream(path, FileMode.OpenOrCreate, FileAccess.ReadWrite, FileShare.None); }
            catch (IOException) when (DateTime.UtcNow < until) { Thread.Sleep(250); }
            catch (IOException e) { throw new IndexIntegrityException($"search index root is locked by another process ({e.Message})"); }
        }
    }

    public string OpenOrBuild(GenerationStore g, SearchIndex ix)
    {
        Directory.CreateDirectory(root);
        using var held = AcquireLock();
        CleanStaleBuilds();
        var docs = SearchIndex.IndexedDocuments(g);
        var digest = SourceDigest(docs);
        var dir = Path.Combine(root, Safe(g.GenerationId));
        if (Directory.Exists(dir))
        {
            var why = Verify(dir, g.GenerationId, digest, options.VerifyOnOpen);
            if (why is null)
            {
                Load(dir, g, docs, ix);
                Retain(dir);
                Log($"search index: opened {dir}");
                return dir;
            }
            Log($"search index: {dir} failed verification: {why}");
            if (!options.RebuildOnFailure) throw new IndexIntegrityException($"search index failed verification: {why}");
            Quarantine(dir, g.GenerationId);
        }
        Build(g, docs, digest, ix, dir);
        Retain(dir);
        return dir;
    }

    void CleanStaleBuilds()
    {
        foreach (var d in Directory.GetDirectories(root, ".building-*"))
        {
            Log($"search index: removing interrupted build {Path.GetFileName(d)}");
            SqliteConnection.ClearAllPools();
            Directory.Delete(d, true);
        }
    }

    void Quarantine(string dir, string generation)
    {
        SqliteConnection.ClearAllPools();
        var q = Path.Combine(root, $".quarantine-{Safe(generation)}-{DateTime.UtcNow:yyyyMMddTHHmmssfff}");
        Directory.Move(dir, q);
        Log($"search index: quarantined to {Path.GetFileName(q)}");
        foreach (var old in Directory.GetDirectories(root, ".quarantine-*").OrderByDescending(Directory.GetCreationTimeUtc).Skip(2))
            Directory.Delete(old, true);
    }

    /// C15 security review L6: retention deletes only directories whose manifest names this index format, never other
    /// data that happens to sit under a misconfigured index root.
    static bool IsOwnIndex(string dir)
    {
        try { return System.Text.Json.Nodes.JsonNode.Parse(File.ReadAllText(Path.Combine(dir, ManifestFile)))?["format"]?.GetValue<string>() is { } f && f.StartsWith("mimamsa-search-index/", StringComparison.Ordinal); }
        catch { return false; }
    }

    void Retain(string current)
    {
        var others = Directory.GetDirectories(root).Where(d => !Path.GetFileName(d).StartsWith('.') && !string.Equals(d, current, StringComparison.OrdinalIgnoreCase)
                                                             && File.Exists(Path.Combine(d, ManifestFile)) && IsOwnIndex(d))
            .OrderByDescending(d => File.GetLastWriteTimeUtc(Path.Combine(d, ManifestFile))).ToList();
        foreach (var d in others.Skip(Math.Max(0, options.KeepPrevious)))
        {
            Log($"search index: removing old generation index {Path.GetFileName(d)}");
            Directory.Delete(d, true);
        }
    }

    // ------------------------------------------------------------------ verification
    /// Null when the published index at `dir` may be served for this generation and source; otherwise the reason.
    internal static string? Verify(string dir, string generation, string digest, bool full)
    {
        try
        {
            var mf = Path.Combine(dir, ManifestFile); var db = Path.Combine(dir, DbFile);
            if (!File.Exists(mf)) return "manifest missing";
            if (!File.Exists(db)) return "index file missing";
            var m = JsonNode.Parse(File.ReadAllText(mf))!.AsObject();
            if ((string?)m["format"] != FormatVersion) return "format version differs";
            if ((string?)m["generation"] != generation) return "generation differs";
            if ((string?)m["source_digest"] != digest) return "source digest differs (documents or passages changed)";
            if ((long?)m["file_bytes"] != new FileInfo(db).Length) return "index file size differs from manifest";
            if (full && (string?)m["file_sha256"] != FileSha(db)) return "index file SHA-256 differs from manifest";
            using var c = new SqliteConnection(SqlitePostingTable.ReadOnlyConnectionString(db));
            c.Open();
            if (full && (string?)new SqliteCommand("PRAGMA quick_check", c).ExecuteScalar() != "ok") return "SQLite quick_check failed";
            string Meta(string k) => (string)new SqliteCommand($"SELECT value FROM meta WHERE key = '{k}'", c).ExecuteScalar()!;
            if (Meta("source_digest") != digest || Meta("generation") != generation) return "index metadata differs from manifest";
            foreach (var (k, table) in new[] { ("documents", "docs"), ("terms", "terms") })
                if (Convert.ToInt64(new SqliteCommand($"SELECT count(*) FROM {table}", c).ExecuteScalar()) != (long?)m[k]) return $"{k} count differs from manifest";
            if (long.Parse(Meta("passages")) != (long?)m["passages"]) return "passages count differs from manifest";
            return null;
        }
        catch (Exception e) when (e is SqliteException or IOException or JsonException or InvalidOperationException or FormatException or InvalidCastException or NullReferenceException)
        {
            return "unreadable: " + e.GetType().Name;
        }
        finally { SqliteConnection.ClearAllPools(); }
    }

    static string FileSha(string path)
    {
        using var f = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read, 1 << 20);
        return Convert.ToHexString(SHA256.HashData(f)).ToLowerInvariant();
    }

    // ------------------------------------------------------------------ load (no tokenisation)
    void Load(string dir, GenerationStore g, List<DocumentRecord> docs, SearchIndex ix)
    {
        foreach (var a in g.Abbreviations) ix.Abbrev.TryAdd(a.Code, a);
        using var c = new SqliteConnection(SqlitePostingTable.ReadOnlyConnectionString(Path.Combine(dir, DbFile)));
        c.Open();
        using var r = new SqliteCommand("SELECT di, doc_id, service, lens FROM docs ORDER BY di", c).ExecuteReader();
        int di = 0;
        while (r.Read())
        {
            var d = docs[di];
            if (r.GetInt32(0) != di || r.GetString(1) != d.DocId) throw new IndexIntegrityException("document order differs from the index");
            var lens = DecodeInts((byte[])r[3]);
            var ps = SearchIndex.OrderedPassages(d).ToList();
            if (lens.Length != ps.Count) throw new IndexIntegrityException($"passage count differs for {d.DocId}");
            var idx = new int[ps.Count];
            for (int k = 0; k < ps.Count; k++) { idx[k] = ix.Passages.Count; ix.AddPassage(ps[k], di, lens[k]); }
            ix.AddDocument(d, idx, r.IsDBNull(2) ? null : r.GetString(2));
            di++;
        }
        if (di != docs.Count) throw new IndexIntegrityException("document count differs from the index");
        SqliteConnection.ClearPool(c);
    }

    // ------------------------------------------------------------------ build and publish
    void Build(GenerationStore g, List<DocumentRecord> docs, string digest, SearchIndex ix, string target)
    {
        var sw = System.Diagnostics.Stopwatch.StartNew();
        var tmp = Path.Combine(root, $".building-{Safe(g.GenerationId)}-{Guid.NewGuid():N}");
        Directory.CreateDirectory(tmp);
        var db = Path.Combine(tmp, DbFile);
        var runsPath = Path.Combine(tmp, "runs.sqlite");

        // 1. Tokenise in chunks of BuildChunkPassages passages; each chunk's postings go to a run table and are released,
        //    so build memory is bounded by the chunk, not the corpus. Ordinals follow global first occurrence.
        var vocab = new Dictionary<string, int>(StringComparer.Ordinal);
        var terms = new List<string>();
        var dfs = new List<int>();
        int chunk = 0;
        string cacheNote = "forward cache off";
        using (var runs = OpenWrite(runsPath))
        {
            Exec(runs, "CREATE TABLE runs(ord INTEGER NOT NULL, chunk INTEGER NOT NULL, df INTEGER NOT NULL, last_p INTEGER NOT NULL, blob BLOB NOT NULL, PRIMARY KEY(ord, chunk)) WITHOUT ROWID;");
            void Flush(Dictionary<string, List<SearchIndex.Posting>> part)
            {
                if (part.Count == 0) return;
                using var tx = runs.BeginTransaction();
                using var cmd = new SqliteCommand("INSERT INTO runs VALUES($o,$c,$d,$l,$b)", runs, tx);
                var po = cmd.Parameters.Add("$o", SqliteType.Integer); var pc = cmd.Parameters.Add("$c", SqliteType.Integer);
                var pd = cmd.Parameters.Add("$d", SqliteType.Integer); var pl = cmd.Parameters.Add("$l", SqliteType.Integer); var pb = cmd.Parameters.Add("$b", SqliteType.Blob);
                foreach (var (term, list) in part)   // insertion order = first occurrence within the chunk
                {
                    if (!vocab.TryGetValue(term, out var o)) { o = terms.Count; vocab[term] = o; terms.Add(term); dfs.Add(0); }
                    dfs[o] += list.Count;
                    po.Value = o; pc.Value = chunk; pd.Value = list.Count; pl.Value = list[^1].P; pb.Value = SqlitePostingTable.Encode(list);
                    cmd.ExecuteNonQuery();
                }
                tx.Commit();
                chunk++;
            }
            if (options.UseForwardCache)
            {
                using var fc = ForwardCache.Open(root, log);
                Flush(SearchIndex.BuildPostings(g, ix, fc.Get, Flush, options.BuildChunkPassages));
                int pruned = fc.Prune();
                cacheNote = $"forward cache {fc.Hits} documents reused, {fc.Misses} tokenised, {pruned} stale entries pruned";
            }
            else Flush(SearchIndex.BuildPostings(g, ix, null, Flush, options.BuildChunkPassages));
        }
        SqliteConnection.ClearAllPools();
        long tokenMs = sw.ElapsedMilliseconds;

        // 2. Merge runs into the published table in ordinal order. Each run's first posting is absolute; it is rebased
        //    onto the previous run's last passage and the rest of the run's bytes are copied unchanged.
        using (var c = OpenWrite(db))
        {
            Exec(c, "CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);" +
                    "CREATE TABLE docs(di INTEGER PRIMARY KEY, doc_id TEXT NOT NULL, derivative_id TEXT, service TEXT, lens BLOB NOT NULL);" +
                    "CREATE TABLE terms(ord INTEGER PRIMARY KEY, term TEXT NOT NULL, df INTEGER NOT NULL, postings BLOB NOT NULL);");
            using (var t = c.BeginTransaction())
            {
                foreach (var (k, v) in new Dictionary<string, string> { ["format"] = FormatVersion, ["generation"] = g.GenerationId, ["source_digest"] = digest,
                                                                         ["passages"] = ix.N.ToString(), ["built_utc"] = BuiltUtc })
                    Insert(c, t, "INSERT INTO meta VALUES($a,$b)", k, v);
                for (int d = 0; d < ix.Docs.Count; d++)
                    Insert(c, t, "INSERT INTO docs VALUES($a,$b,$c,$d,$e)", d, ix.Docs[d].DocId, ix.Docs[d].DerivativeId, ix.Service[d],
                           EncodeInts(ix.DocPassages[d].Select(ix.LenOf).ToArray()));
                t.Commit();
            }
            using var runs = new SqliteConnection(SqlitePostingTable.ReadOnlyConnectionString(runsPath));
            runs.Open();
            var tx = c.BeginTransaction();
            var cmd = new SqliteCommand("INSERT INTO terms VALUES($o,$t,$d,$p)", c, tx);
            var po = cmd.Parameters.Add("$o", SqliteType.Integer); var pt = cmd.Parameters.Add("$t", SqliteType.Text);
            var pd = cmd.Parameters.Add("$d", SqliteType.Integer); var pp = cmd.Parameters.Add("$p", SqliteType.Blob);
            using (var r = new SqliteCommand("SELECT ord, last_p, blob FROM runs ORDER BY ord, chunk", runs).ExecuteReader())
            {
                var buf = new MemoryStream();
                int cur = -1, prevLast = 0, written = 0;
                void Emit()
                {
                    po.Value = cur; pt.Value = terms[cur]; pd.Value = dfs[cur]; pp.Value = buf.ToArray();
                    cmd.ExecuteNonQuery();
                    written++;
                    if (options.FailAfterTerms is { } fail && written >= fail) throw new IOException("TEST: simulated crash during index build");
                    if (written % 50_000 == 0) { tx.Commit(); tx.Dispose(); tx = c.BeginTransaction(); cmd.Transaction = tx; }
                }
                while (r.Read())
                {
                    int ord = r.GetInt32(0);
                    var blob = (byte[])r[2];
                    if (ord != cur)
                    {
                        if (cur >= 0) Emit();
                        if (ord != cur + 1) throw new IndexIntegrityException("run ordinals are not contiguous");
                        cur = ord; buf.SetLength(0);
                        buf.Write(blob);
                    }
                    else
                    {
                        int i = 0; uint first = 0; int shift = 0;
                        while (true) { byte x = blob[i++]; first |= (uint)(x & 0x7F) << shift; if (x < 0x80) break; shift += 7; }
                        uint rebased = first - (uint)prevLast;
                        while (rebased >= 0x80) { buf.WriteByte((byte)(rebased | 0x80)); rebased >>= 7; }
                        buf.WriteByte((byte)rebased);
                        buf.Write(blob, i, blob.Length - i);
                    }
                    prevLast = r.GetInt32(1);
                }
                if (cur >= 0) Emit();
                if (written != terms.Count) throw new IndexIntegrityException("merged term count differs from the vocabulary");
            }
            tx.Commit(); tx.Dispose();
            Exec(c, "PRAGMA journal_mode = DELETE; VACUUM;");
        }
        SqliteConnection.ClearAllPools();
        File.Delete(runsPath);
        using (var f = new FileStream(db, FileMode.Open, FileAccess.ReadWrite)) f.Flush(true);
        var manifest = new JsonObject
        {
            ["format"] = FormatVersion, ["generation"] = g.GenerationId, ["source_digest"] = digest,
            ["documents"] = ix.Docs.Count, ["passages"] = ix.N, ["terms"] = terms.Count,
            ["file_bytes"] = new FileInfo(db).Length, ["file_sha256"] = FileSha(db),
            ["built_utc"] = BuiltUtc,
        };
        var mtmp = Path.Combine(tmp, ManifestFile + ".tmp");
        using (var f = new FileStream(mtmp, FileMode.CreateNew, FileAccess.Write))
        { var b = Encoding.UTF8.GetBytes(manifest.ToJsonString(new JsonSerializerOptions { WriteIndented = true })); f.Write(b); f.Flush(true); }
        File.Move(mtmp, Path.Combine(tmp, ManifestFile));
        var why = Verify(tmp, g.GenerationId, digest, full: true);
        if (why is not null) throw new IndexIntegrityException($"newly built search index failed verification: {why}");
        Directory.Move(tmp, target);   // atomic rename on the same volume: the index becomes visible complete or not at all
        Log($"search index: built and published {target} ({ix.Docs.Count} documents, {ix.N} passages, {terms.Count} terms, {chunk} runs; tokens {tokenMs} ms ({cacheNote}), total {sw.ElapsedMilliseconds} ms)");
    }

    static SqliteConnection OpenWrite(string path)
    {
        var c = new SqliteConnection(new SqliteConnectionStringBuilder { DataSource = path, Mode = SqliteOpenMode.ReadWriteCreate, Pooling = false }.ToString());
        c.Open();
        Exec(c, "PRAGMA journal_mode = OFF; PRAGMA synchronous = OFF; PRAGMA page_size = 8192;");
        return c;
    }

    static void Exec(SqliteConnection c, string sql) { using var cmd = new SqliteCommand(sql, c); cmd.ExecuteNonQuery(); }

    static void Insert(SqliteConnection c, SqliteTransaction t, string sql, params object?[] values)
    {
        using var cmd = new SqliteCommand(sql, c, t);
        string[] names = { "$a", "$b", "$c", "$d", "$e" };
        for (int i = 0; i < values.Length; i++) cmd.Parameters.AddWithValue(names[i], values[i] ?? DBNull.Value);
        cmd.ExecuteNonQuery();
    }

    static byte[] EncodeInts(int[] v)
    {
        var s = new MemoryStream(v.Length * 2);
        foreach (var x in v) { uint u = (uint)x; while (u >= 0x80) { s.WriteByte((byte)(u | 0x80)); u >>= 7; } s.WriteByte((byte)u); }
        return s.ToArray();
    }

    static int[] DecodeInts(byte[] b)
    {
        var res = new List<int>();
        int i = 0;
        while (i < b.Length)
        {
            uint v = 0; int shift = 0;
            while (true) { byte x = b[i++]; v |= (uint)(x & 0x7F) << shift; if (x < 0x80) break; shift += 7; if (shift > 28 || i >= b.Length) throw new IndexIntegrityException("corrupt passage lengths"); }
            res.Add((int)v);
        }
        return res.ToArray();
    }
}
