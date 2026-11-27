// C16 WP04 (ADR-0008): generation text store. Page and passage text of the ACTIVE generation is either held in memory
// (`memory`, the B1 reference behaviour) or read on demand from a persistent, generation-scoped SQLite file (`disk`).
// Callers are unchanged: they read PageText.Text and Passage.Text, which resolve through a per-document DocumentText
// handle. Only text moves to disk; document, page and passage identity (ids, pages, offsets, labels) stays in memory.
//
// Layout under the store root (default <site>/text-store, configurable):
//   <generation>/text.sqlite    the verified derivative bytes of every accepted document (exactly the importer's
//                               derived/<text_sha256>.txt), page byte ranges, passage anchors, text assessment and the
//                               derived-stage load issues
//   <generation>/MANIFEST.json  format, generation, source digest, counts, file size and SHA-256
//   .building-<generation>-<id>/   a store being built (never opened; removed at the next start)
//   .quarantine-<generation>-<utc>/ a published store that failed verification (kept for inspection)
//
// Integrity (fail closed):
//   * build: the same checks GenerationStore applies in memory mode (derivative hash, page markers, passage hashes);
//   * open: manifest, size, SHA-256 (VerifyOnOpen), quick_check, format, generation, source digest and counts;
//   * first use of a document's text: its stored bytes are re-hashed against the derivative text_sha256 recorded by
//     the generation, and a 128-bit SHA-256 prefix of every page range is taken from those verified bytes;
//   * every later page read from disk is checked against that page hash before it is decoded or cached.
// Withdrawal and eligibility are unchanged: text is reachable only through DocumentRecord objects, which every route
// obtains through the existing eligibility decision. The store adds no route and no lookup by document id.
using System.Collections.Concurrent;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using Microsoft.Data.Sqlite;

namespace Mimamsa.Core.Generation;

public sealed record TextStoreOptions
{
    /// "memory" (reference: all text held) or "disk" (text read on demand from the generation's verified store).
    public string Store { get; init; } = "memory";
    /// Store root; default <site>/text-store.
    public string? Dir { get; init; }
    /// Bytes of decoded page text (UTF-16) kept in the bounded LRU cache.
    public long CacheBytes { get; init; } = 64L << 20;
    /// Hash the whole store file against its manifest and run PRAGMA quick_check before serving it.
    public bool VerifyOnOpen { get; init; } = true;
    /// A published store that fails verification is quarantined and rebuilt (true) or start-up is refused (false).
    public bool RebuildOnFailure { get; init; } = true;
    /// Published stores of other generations kept for rollback (newest first).
    public int KeepPrevious { get; init; } = 2;
    /// How long to wait for another process that is opening or building in the same store root.
    public TimeSpan LockTimeout { get; init; } = TimeSpan.FromMinutes(30);
    /// TEST ONLY: throw after writing this many documents, simulating a crash during a build.
    public int? FailAfterDocuments { get; init; }

    public static TextStoreOptions Memory { get; } = new();
}

/// Numbers only (no text): what the store has read and cached.
public sealed record TextStoreStats(string Kind, long CacheHits, long CacheMisses, long CachedChars, long CacheBudgetChars,
                                    long DocumentsVerified, long PageReads, long BytesRead, long FileBytes);

public interface ITextStore
{
    string Kind { get; }
    /// Published store directory in use (disk), else null.
    string? StorePath { get; }
    TextStoreStats Stats();
}

public sealed class TextIntegrityException(string message) : Exception(message);

/// Per-document text source for lazily resolved PageText and Passage objects.
public abstract class DocumentText
{
    internal abstract string Page(int page);
    internal string Slice(int page, int start, int end) => Page(page)[start..end];
}

public sealed class MemoryTextStore : ITextStore
{
    public static MemoryTextStore Instance { get; } = new();
    public string Kind => "memory";
    public string? StorePath => null;
    public TextStoreStats Stats() => new("memory", 0, 0, 0, 0, 0, 0, 0, 0);
}

/// One accepted derivative as GenerationStore verified it: what memory mode attaches and disk mode persists.
internal sealed record DerivedText(DocumentRecord Doc, string DerivativeId, string TextSha, string PipelineName, string PipelineVersion,
                                   bool QuotingPermitted, byte[] Bytes, List<(PageText Page, int ByteStart, int ByteLen)> Pages, List<Passage> Passages);

/// Bounded, thread-safe LRU of decoded page strings, sharded to keep reader contention low. Budget in UTF-16 chars.
internal sealed class TextCache
{
    sealed class Shard
    {
        public readonly object Lock = new();
        public readonly Dictionary<long, LinkedListNode<(long key, string text)>> Map = new();
        public readonly LinkedList<(long key, string text)> Lru = new();
        public long Used;
    }

    readonly Shard[] _shards;
    readonly long _perShard;
    public long Hits, Misses;
    public long Budget { get; }

    public TextCache(long budgetChars, int shards = 16)
    {
        Budget = Math.Max(0, budgetChars);
        _shards = Enumerable.Range(0, shards).Select(_ => new Shard()).ToArray();
        _perShard = Budget / shards;
    }

    Shard For(long key) => _shards[(int)((ulong)(key * unchecked((long)0x9E3779B97F4A7C15)) >> 60) % _shards.Length];

    public bool TryGet(long key, out string text)
    {
        var s = For(key);
        lock (s.Lock)
            if (s.Map.TryGetValue(key, out var n)) { s.Lru.Remove(n); s.Lru.AddFirst(n); Interlocked.Increment(ref Hits); text = n.Value.text; return true; }
        Interlocked.Increment(ref Misses);
        text = null!;
        return false;
    }

    public void Add(long key, string text)
    {
        if (text.Length > _perShard) return;   // larger than a shard's budget: served, not cached
        var s = For(key);
        lock (s.Lock)
        {
            if (s.Map.ContainsKey(key)) return;
            s.Map[key] = s.Lru.AddFirst((key, text));
            s.Used += text.Length;
            while (s.Used > _perShard && s.Lru.Last is { } last)
            {
                s.Lru.RemoveLast(); s.Map.Remove(last.Value.key); s.Used -= last.Value.text.Length;
            }
        }
    }

    public long Used { get { long u = 0; foreach (var s in _shards) lock (s.Lock) u += s.Used; return u; } }

    /// Drops one entry (used when a document fails verification, so no cached page of it is ever served again).
    public void Remove(long key)
    {
        var s = _shards[(int)((ulong)key % (ulong)_shards.Length)];
        lock (s.Lock)
            if (s.Map.Remove(key, out var node)) { s.Lru.Remove(node); s.Used -= node.Value.text.Length; }
    }
}

public sealed class DiskTextStore : ITextStore, IDisposable
{
    public const string DbFile = "text.sqlite", ManifestFile = "MANIFEST.json";
    /// Bump when the schema or the page/passage derivation changes: every existing store is then rebuilt.
    public const string FormatVersion = "mimamsa-text-store/1";

    readonly string _db;
    readonly string _cs;
    readonly TextCache _cache;
    readonly ConcurrentBag<SqliteConnection> _pool = new();
    long _verified, _pageReads, _bytesRead;
    bool _disposed;

    public string Kind => "disk";
    public string? StorePath { get; }
    public long FileBytes { get; }

    DiskTextStore(string dir, long cacheBytes)
    {
        StorePath = dir;
        _db = Path.Combine(dir, DbFile);
        _cs = new SqliteConnectionStringBuilder { DataSource = _db, Mode = SqliteOpenMode.ReadOnly, Pooling = false, Cache = SqliteCacheMode.Private }.ToString();
        _cache = new TextCache(cacheBytes / 2);
        FileBytes = new FileInfo(_db).Length;
    }

    public TextStoreStats Stats() => new("disk", Interlocked.Read(ref _cache.Hits), Interlocked.Read(ref _cache.Misses), _cache.Used, _cache.Budget,
                                         Interlocked.Read(ref _verified), Interlocked.Read(ref _pageReads), Interlocked.Read(ref _bytesRead), FileBytes);

    public void Dispose()
    {
        _disposed = true;
        while (_pool.TryTake(out var c)) c.Dispose();
    }

    // ------------------------------------------------------------------ reads
    SqliteConnection Rent()
    {
        ObjectDisposedException.ThrowIf(_disposed, this);
        if (_pool.TryTake(out var c)) return c;
        c = new SqliteConnection(_cs);
        c.Open();
        return c;
    }

    void Return(SqliteConnection c)
    {
        if (_disposed || _pool.Count >= 64) c.Dispose(); else _pool.Add(c);
    }

    byte[] ReadRange(long di, long start, int length)
    {
        var c = Rent();
        try
        {
            using var blob = new SqliteBlob(c, "texts", "bytes", di, readOnly: true);
            if (start < 0 || start + length > blob.Length) throw new TextIntegrityException("text store: page range outside the stored derivative");
            var buf = new byte[length];
            blob.Position = start;
            blob.ReadExactly(buf);
            Interlocked.Add(ref _bytesRead, length);
            return buf;
        }
        finally { Return(c); }
    }

    byte[] ReadAll(long di, out long length)
    {
        var c = Rent();
        try
        {
            using var blob = new SqliteBlob(c, "texts", "bytes", di, readOnly: true);
            length = blob.Length;
            var buf = new byte[blob.Length];
            blob.ReadExactly(buf);
            Interlocked.Add(ref _bytesRead, buf.Length);
            return buf;
        }
        finally { Return(c); }
    }

    static byte[] PageHash(ReadOnlySpan<byte> b) => SHA256.HashData(b)[..16];

    /// Lazy text of one document: page byte ranges are held; bytes are verified on first use and then read per page.
    sealed class DiskDocumentText : DocumentText
    {
        readonly DiskTextStore _store;
        readonly long _di;
        readonly string _docId, _textSha;
        readonly long _bytes;
        readonly Dictionary<int, int> _slot;
        readonly long[] _start; readonly int[] _len, _chars;
        byte[]? _hashes;
        // ChatGPT review of PR #80 (P1): once a document fails, nothing of it is served again, cached pages included.
        // The flag is published before the cache is invalidated and is checked before and after every cache hit.
        volatile bool _failed;
        readonly object _lock = new();

        public DiskDocumentText(DiskTextStore store, long di, string docId, string textSha, long bytes, List<(int page, long start, int len, int chars)> pages)
        {
            _store = store; _di = di; _docId = docId; _textSha = textSha; _bytes = bytes;
            _slot = new Dictionary<int, int>(pages.Count);
            _start = new long[pages.Count]; _len = new int[pages.Count]; _chars = new int[pages.Count];
            for (int i = 0; i < pages.Count; i++) { _slot[pages[i].page] = i; _start[i] = pages[i].start; _len[i] = pages[i].len; _chars[i] = pages[i].chars; }
        }

        string Decode(int slot, ReadOnlySpan<byte> b)
        {
            var s = Encoding.UTF8.GetString(b);
            if (s.Length != _chars[slot]) Fail("decoded page length differs");
            return s;
        }

        void Fail(string why)
        {
            _failed = true;
            for (int i = 0; i < _start.Length; i++) _store._cache.Remove(Key(i));
            throw new TextIntegrityException($"text store: {_docId}: {why}; text withheld");
        }

        long Key(int slot) => (_di << 20) | (uint)slot;

        void ThrowIfFailed()
        {
            if (_failed) throw new TextIntegrityException($"text store: {_docId}: failed verification earlier; text withheld");
        }

        /// Verifies the whole derivative against the generation's text_sha256 once; returns the requested page if read.
        string? Verify(int wantSlot)
        {
            lock (_lock)
            {
                ThrowIfFailed();
                if (_hashes is not null) return null;
                var all = _store.ReadAll(_di, out var length);
                if (length != _bytes || Convert.ToHexString(SHA256.HashData(all)).ToLowerInvariant() != _textSha)
                    Fail("stored derivative differs from the generation's text_sha256");
                var h = new byte[_start.Length * 16];
                for (int i = 0; i < _start.Length; i++)
                {
                    if (_start[i] < 0 || _start[i] + _len[i] > all.Length) Fail("page range outside the derivative");
                    PageHash(all.AsSpan((int)_start[i], _len[i])).CopyTo(h, i * 16);
                }
                var text = Decode(wantSlot, all.AsSpan((int)_start[wantSlot], _len[wantSlot]));
                Volatile.Write(ref _hashes, h);
                Interlocked.Increment(ref _store._verified);
                return text;
            }
        }

        internal override string Page(int page)
        {
            if (!_slot.TryGetValue(page, out var slot)) throw new KeyNotFoundException($"page {page} has no text");
            long key = Key(slot);
            ThrowIfFailed();
            if (_store._cache.TryGet(key, out var cached)) { ThrowIfFailed(); return cached; }
            var hashes = Volatile.Read(ref _hashes);
            string text;
            if (hashes is null && Verify(slot) is { } first) text = first;
            else
            {
                ThrowIfFailed();
                hashes = Volatile.Read(ref _hashes)!;
                var b = _store.ReadRange(_di, _start[slot], _len[slot]);
                if (!PageHash(b).AsSpan().SequenceEqual(hashes.AsSpan(slot * 16, 16))) Fail($"page {page} differs from its verified hash");
                text = Decode(slot, b);
            }
            Interlocked.Increment(ref _store._pageReads);
            _store._cache.Add(key, text);
            if (_failed) { _store._cache.Remove(key); ThrowIfFailed(); }   // a failure published while this page was read
            return text;
        }
    }

    // ------------------------------------------------------------------ open or build
    static string Safe(string generation) => string.Concat(generation.Select(c => char.IsLetterOrDigit(c) || c is '-' or '_' or '.' ? c : '_'));

    static string FileSha(string path)
    {
        using var f = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read, 1 << 20);
        return Convert.ToHexString(SHA256.HashData(f)).ToLowerInvariant();
    }

    static string Sha(byte[] b) => Convert.ToHexString(SHA256.HashData(b)).ToLowerInvariant();

    /// Identity of the text the store holds for this generation: the store format, generation id, generation.json
    /// (servable derivatives), derived_text.jsonl (derivatives, text_sha256, pages, passages and their hashes) and the
    /// documents loaded in order with their copies. Any difference means the store must be rebuilt.
    internal static string SourceDigest(string generation, string gdir, IEnumerable<DocumentRecord> docs)
    {
        using var h = IncrementalHash.CreateHash(HashAlgorithmName.SHA256);
        void Add(string s) => h.AppendData(Encoding.UTF8.GetBytes(s + "\n"));
        Add(FormatVersion); Add(generation);
        foreach (var f in new[] { "generation.json", Path.Combine("records", "derived_text.jsonl") })
        {
            var p = Path.Combine(gdir, f);
            if (!File.Exists(p)) { Add($"{f}\tabsent"); continue; }
            using var s = new FileStream(p, FileMode.Open, FileAccess.Read, FileShare.Read, 1 << 20);
            Add($"{f}\t{Convert.ToHexString(SHA256.HashData(s)).ToLowerInvariant()}");
        }
        foreach (var d in docs) Add($"D\t{d.DocId}\t{d.CopySha}");
        return Convert.ToHexString(h.GetHashAndReset()).ToLowerInvariant();
    }

    sealed class Lock(string root, TimeSpan timeout) : IDisposable
    {
        readonly FileStream _f = Acquire(root, timeout);
        static FileStream Acquire(string root, TimeSpan timeout)
        {
            var path = Path.Combine(root, ".lock");
            var until = DateTime.UtcNow + timeout;
            while (true)
            {
                try { return new FileStream(path, FileMode.OpenOrCreate, FileAccess.ReadWrite, FileShare.None); }
                catch (IOException) when (DateTime.UtcNow < until) { Thread.Sleep(250); }
                catch (IOException e) { throw new TextIntegrityException($"text store root is locked by another process ({e.Message})"); }
            }
        }
        public void Dispose() => _f.Dispose();
    }

    /// Opens the verified store of this generation, or builds, verifies and atomically publishes one first, then
    /// attaches lazy text to `docs`. `derived` yields the verified derivatives (only enumerated for a build);
    /// `issue` receives the derived-stage load issues in the order the build recorded them.
    internal static DiskTextStore OpenOrBuild(string root, TextStoreOptions o, string generation, string digest,
        Dictionary<string, DocumentRecord> docs, Func<Action<string>, IEnumerable<DerivedText>> derived, Action<string, int> issue, Action<string>? log)
    {
        Directory.CreateDirectory(root);
        using var held = new Lock(root, o.LockTimeout);
        foreach (var d in Directory.GetDirectories(root, ".building-*"))
        {
            log?.Invoke($"text store: removing interrupted build {Path.GetFileName(d)}");
            Directory.Delete(d, true);
        }
        var dir = Path.Combine(root, Safe(generation));
        if (Directory.Exists(dir))
        {
            var why = Verify(dir, generation, digest, o.VerifyOnOpen);
            Loaded? loaded = null;
            if (why is null)
                try { loaded = ReadMetadata(dir, docs); }
                catch (Exception e) when (e is TextIntegrityException or SqliteException or InvalidCastException or FormatException or JsonException
                                              or InvalidOperationException or NullReferenceException or ArgumentException)
                { why = "metadata unreadable: " + e.Message; }
            // ChatGPT review of PR #80 (P1, P2): the store's own manifest and digest are locally writable, so they are never
            // the authority. Every reopen re-derives each document's metadata from the generation's records and source
            // derivative files (the same ReadDerived rule as the memory store, one document at a time) and requires the
            // store to match it exactly: derivative identity and text_sha256, quoting, pages and their byte ranges, passages
            // and their offsets, the text assessment, and which derivatives are available with which load issues. Any
            // difference quarantines the store (or refuses it), whatever VerifyOnOpen says.
            var bindWatch = System.Diagnostics.Stopwatch.StartNew();
            if (loaded is not null && Bind(loaded, derived) is { } mismatch) { loaded = null; why = "store differs from the generation's records: " + mismatch; }
            var bindMs = bindWatch.ElapsedMilliseconds;
            if (loaded is not null)
            {
                var store = new DiskTextStore(dir, o.CacheBytes);
                store.Attach(loaded, issue);
                Retain(root, dir, o.KeepPrevious, log);
                log?.Invoke($"text store: opened {dir} (bound {loaded.Docs.Count} documents to the generation's records in {bindMs} ms)");
                return store;
            }
            log?.Invoke($"text store: {dir} failed verification: {why}");
            if (!o.RebuildOnFailure) throw new TextIntegrityException($"text store failed verification: {why}");
            var q = Path.Combine(root, $".quarantine-{Safe(generation)}-{DateTime.UtcNow:yyyyMMddTHHmmssfff}");
            Directory.Move(dir, q);
            log?.Invoke($"text store: quarantined to {Path.GetFileName(q)}");
            foreach (var old in Directory.GetDirectories(root, ".quarantine-*").OrderByDescending(Directory.GetCreationTimeUtc).Skip(2))
                Directory.Delete(old, true);
        }
        Build(root, o, generation, digest, dir, derived, log);
        var built = ReadMetadata(dir, docs);
        var s = new DiskTextStore(dir, o.CacheBytes);
        s.Attach(built, issue);
        Retain(root, dir, o.KeepPrevious, log);
        return s;
    }

    static bool IsOwnStore(string dir)
    {
        try { return JsonNode.Parse(File.ReadAllText(Path.Combine(dir, ManifestFile)))?["format"]?.GetValue<string>() is { } f && f.StartsWith("mimamsa-text-store/", StringComparison.Ordinal); }
        catch { return false; }
    }

    static void Retain(string root, string current, int keep, Action<string>? log)
    {
        var others = Directory.GetDirectories(root).Where(d => !Path.GetFileName(d).StartsWith('.') && !string.Equals(d, current, StringComparison.OrdinalIgnoreCase) && IsOwnStore(d))
            .OrderByDescending(d => File.GetLastWriteTimeUtc(Path.Combine(d, ManifestFile))).ToList();
        foreach (var d in others.Skip(Math.Max(0, keep)))
        {
            log?.Invoke($"text store: removing old generation store {Path.GetFileName(d)}");
            try { Directory.Delete(d, true); } catch (IOException e) { log?.Invoke($"text store: could not remove {Path.GetFileName(d)} ({e.Message})"); }
        }
    }

    /// Null when the published store at `dir` may be served for this generation and source; otherwise the reason.
    internal static string? Verify(string dir, string generation, string digest, bool full)
    {
        try
        {
            var mf = Path.Combine(dir, ManifestFile); var db = Path.Combine(dir, DbFile);
            if (!File.Exists(mf)) return "manifest missing";
            if (!File.Exists(db)) return "store file missing";
            var m = JsonNode.Parse(File.ReadAllText(mf))!.AsObject();
            if ((string?)m["format"] != FormatVersion) return "format version differs";
            if ((string?)m["generation"] != generation) return "generation differs";
            if ((string?)m["source_digest"] != digest) return "source digest differs (documents or derivatives changed)";
            if ((long?)m["file_bytes"] != new FileInfo(db).Length) return "store file size differs from manifest";
            if (full && (string?)m["file_sha256"] != FileSha(db)) return "store file SHA-256 differs from manifest";
            using var c = new SqliteConnection(new SqliteConnectionStringBuilder { DataSource = db, Mode = SqliteOpenMode.ReadOnly, Pooling = false }.ToString());
            c.Open();
            if (full && (string?)new SqliteCommand("PRAGMA quick_check", c).ExecuteScalar() != "ok") return "SQLite quick_check failed";
            string Meta(string k) => (string)new SqliteCommand($"SELECT value FROM meta WHERE key = '{k}'", c).ExecuteScalar()!;
            if (Meta("format") != FormatVersion || Meta("source_digest") != digest || Meta("generation") != generation) return "store metadata differs from manifest";
            foreach (var (k, table) in new[] { ("documents", "docs"), ("pages", "pages"), ("passages", "passages"), ("documents", "texts") })
                if (Convert.ToInt64(new SqliteCommand($"SELECT count(*) FROM {table}", c).ExecuteScalar()) != (long?)m[k]) return $"{table} count differs from manifest";
            return null;
        }
        catch (Exception e) when (e is SqliteException or IOException or JsonException or InvalidOperationException or FormatException or InvalidCastException or NullReferenceException)
        {
            return "unreadable: " + e.GetType().Name;
        }
    }

    // ------------------------------------------------------------------ metadata (no text read)
    sealed record LoadedDoc(long Di, DocumentRecord Doc, string DerivativeId, string TextSha, string PipelineName, string PipelineVersion, bool Quoting,
                            long Bytes, TextAssessment Assessment, List<(int page, long start, int len, int chars, string method, bool low, double? ocr)> Pages,
                            List<(string id, int page, int cs, int ce, string? label)> Passages);
    sealed record Loaded(List<LoadedDoc> Docs, List<(string code, int count)> Issues);

    /// Reads and checks every metadata row before anything is attached, so a bad store is quarantined, never half-used.
    static Loaded ReadMetadata(string dir, Dictionary<string, DocumentRecord> docs)
    {
        using var c = new SqliteConnection(new SqliteConnectionStringBuilder { DataSource = Path.Combine(dir, DbFile), Mode = SqliteOpenMode.ReadOnly, Pooling = false }.ToString());
        c.Open();
        var list = new List<LoadedDoc>();
        var byDi = new Dictionary<long, LoadedDoc>();
        var seen = new HashSet<string>(StringComparer.Ordinal);
        using (var r = new SqliteCommand("SELECT di, doc_id, derivative_id, text_sha256, pipeline_name, pipeline_version, quoting_permitted, bytes, assessment FROM docs ORDER BY di", c).ExecuteReader())
            while (r.Read())
            {
                var id = r.GetString(1);
                if (!docs.TryGetValue(id, out var d)) throw new TextIntegrityException($"store names a document the generation does not serve ({id})");
                if (!seen.Add(id)) throw new TextIntegrityException($"store holds two derivatives for {id}");
                var a = JsonNode.Parse(r.GetString(8))!.AsObject();
                var ld = new LoadedDoc(r.GetInt64(0), d, r.GetString(2), r.GetString(3), r.GetString(4), r.GetString(5), r.GetInt64(6) != 0, r.GetInt64(7),
                    new TextAssessment((string)a["language"]!, (string)a["reliability"]!, (string)a["basis"]!, (int)a["deva_words"]!, (double)a["ratio"]!), new(), new());
                list.Add(ld); byDi[ld.Di] = ld;
            }
        using (var r = new SqliteCommand("SELECT di, page, byte_start, byte_len, char_len, method, low_confidence, ocr_confidence FROM pages ORDER BY id", c).ExecuteReader())
            while (r.Read())
            {
                if (!byDi.TryGetValue(r.GetInt64(0), out var ld)) throw new TextIntegrityException("page row without a document");
                ld.Pages.Add((r.GetInt32(1), r.GetInt64(2), r.GetInt32(3), r.GetInt32(4), r.GetString(5), r.GetInt64(6) != 0, r.IsDBNull(7) ? null : r.GetDouble(7)));
            }
        using (var r = new SqliteCommand("SELECT di, passage_id, page, char_start, char_end, paragraph_label FROM passages ORDER BY id", c).ExecuteReader())
            while (r.Read())
            {
                if (!byDi.TryGetValue(r.GetInt64(0), out var ld)) throw new TextIntegrityException("passage row without a document");
                ld.Passages.Add((r.GetString(1), r.GetInt32(2), r.GetInt32(3), r.GetInt32(4), r.IsDBNull(5) ? null : r.GetString(5)));
            }
        foreach (var ld in list)
        {
            var pages = new Dictionary<int, int>(ld.Pages.Count);
            foreach (var p in ld.Pages)
                if (!pages.TryAdd(p.page, p.chars) || p.start < 0 || p.len < 0 || p.start + p.len > ld.Bytes)
                    throw new TextIntegrityException($"duplicate page or page range outside the derivative for {ld.Doc.DocId}");
            foreach (var p in ld.Passages)
                if (!pages.TryGetValue(p.page, out var chars) || p.cs < 0 || p.ce < p.cs || p.ce > chars)
                    throw new TextIntegrityException($"passage anchor outside its page for {ld.Doc.DocId}");
        }
        var issues = new List<(string, int)>();
        var raw = (string?)new SqliteCommand("SELECT value FROM meta WHERE key = 'issues'", c).ExecuteScalar() ?? "{}";
        foreach (var (k, v) in JsonNode.Parse(raw)!.AsObject()) issues.Add((k, (int)v!));
        return new Loaded(list, issues);
    }

    void Attach(Loaded l, Action<string, int> issue)
    {
        foreach (var ld in l.Docs)
        {
            var d = ld.Doc;
            if (d.DerivativeId is not null || d.Pages.Count > 0 || d.Passages.Count > 0) throw new InvalidOperationException("document text attached twice");
            var src = new DiskDocumentText(this, ld.Di, d.DocId, ld.TextSha, ld.Bytes, ld.Pages.Select(p => (p.page, p.start, p.len, p.chars)).ToList());
            d.DerivativeId = ld.DerivativeId; d.DerivativeTextSha = ld.TextSha; d.PipelineName = ld.PipelineName; d.PipelineVersion = ld.PipelineVersion;
            d.QuotingPermitted = ld.Quoting;
            foreach (var p in ld.Pages) d.Pages[p.page] = new PageText(p.page, src, p.chars, p.method, p.low, p.ocr);
            foreach (var p in ld.Passages) d.Passages.Add(new Passage(d.DocId, p.id, p.page, p.cs, p.ce, p.label, src));
            d.TextAssessment = ld.Assessment;
        }
        foreach (var (code, n) in l.Issues) issue(code, n);
    }

    /// Null when the stored metadata equals a fresh derivation from the generation's records and source files; else why.
    /// Text bytes are not compared here: they are hashed on first use against the text_sha256 bound by this check.
    static string? Bind(Loaded l, Func<Action<string>, IEnumerable<DerivedText>> derived)
    {
        var issues = new List<(string code, int count)>();
        void Issue(string code)
        {
            int i = issues.FindIndex(x => x.code == code);
            if (i < 0) issues.Add((code, 1)); else issues[i] = (code, issues[i].count + 1);
        }
        int n = 0;
        var stored = l.Docs.Select(x => x.Doc).ToHashSet();
        foreach (var t in derived(Issue))
        {
            var id = t.Doc.DocId;
            if (!stored.Contains(t.Doc)) return $"{id} is available in the generation but not in the store";
            if (n >= l.Docs.Count) return $"document order differs at {id}";
            var ld = l.Docs[n++];
            if (!ReferenceEquals(ld.Doc, t.Doc)) return $"{ld.Doc.DocId} is in the store but not available in the generation";
            if (ld.DerivativeId != t.DerivativeId || ld.TextSha != t.TextSha || ld.PipelineName != t.PipelineName || ld.PipelineVersion != t.PipelineVersion)
                return $"derivative identity of {id}";
            if (ld.Quoting != t.QuotingPermitted) return $"quoting permission of {id}";
            if (ld.Bytes != t.Bytes.Length) return $"derivative length of {id}";
            if (ld.Pages.Count != t.Pages.Count) return $"page count of {id}";
            for (int i = 0; i < t.Pages.Count; i++)
            {
                var (pg, bs, bl) = t.Pages[i]; var sp = ld.Pages[i];
                if (sp.page != pg.Page || sp.start != bs || sp.len != bl || sp.chars != pg.Length || sp.method != pg.Method || sp.low != pg.LowConfidence || !Nullable.Equals(sp.ocr, pg.OcrConfidence))
                    return $"page {pg.Page} of {id}";
            }
            if (ld.Passages.Count != t.Passages.Count) return $"passage count of {id}";
            for (int i = 0; i < t.Passages.Count; i++)
            {
                var p = t.Passages[i]; var sp = ld.Passages[i];
                if (sp.id != p.PassageId || sp.page != p.Page || sp.cs != p.CharStart || sp.ce != p.CharEnd || sp.label != p.ParagraphLabel)
                    return $"passage {p.PassageId} of {id}";
            }
            if (Assess(t) != ld.Assessment) return $"text assessment of {id}";
        }
        if (n != l.Docs.Count) return $"{l.Docs[n].Doc.DocId} is in the store but not available in the generation";
        if (!issues.SequenceEqual(l.Issues)) return "derivative availability or load issues";
        return null;
    }

    static TextAssessment Assess(DerivedText t) => TextQuality.Assess(t.Pages.Select(p => p.Page).OrderBy(p => p.Page).Select(p => p.Text));

    // ------------------------------------------------------------------ build and publish
    static void Exec(SqliteConnection c, string sql, SqliteTransaction? t = null) { using var cmd = new SqliteCommand(sql, c, t); cmd.ExecuteNonQuery(); }

    static void Build(string root, TextStoreOptions o, string generation, string digest, string target,
        Func<Action<string>, IEnumerable<DerivedText>> derived, Action<string>? log)
    {
        var sw = System.Diagnostics.Stopwatch.StartNew();
        var tmp = Path.Combine(root, $".building-{Safe(generation)}-{Guid.NewGuid():N}");
        Directory.CreateDirectory(tmp);
        var db = Path.Combine(tmp, DbFile);
        var issues = new JsonObject();
        long nDocs = 0, nPages = 0, nPassages = 0, textBytes = 0;
        using (var c = new SqliteConnection(new SqliteConnectionStringBuilder { DataSource = db, Mode = SqliteOpenMode.ReadWriteCreate, Pooling = false }.ToString()))
        {
            c.Open();
            Exec(c, "PRAGMA journal_mode = OFF; PRAGMA synchronous = OFF; PRAGMA page_size = 8192;");
            Exec(c, "CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);" +
                    "CREATE TABLE docs(di INTEGER PRIMARY KEY, doc_id TEXT NOT NULL UNIQUE, derivative_id TEXT NOT NULL, text_sha256 TEXT NOT NULL, pipeline_name TEXT NOT NULL," +
                    " pipeline_version TEXT NOT NULL, quoting_permitted INTEGER NOT NULL, bytes INTEGER NOT NULL, assessment TEXT NOT NULL);" +
                    "CREATE TABLE texts(di INTEGER PRIMARY KEY, bytes BLOB NOT NULL);" +
                    "CREATE TABLE pages(id INTEGER PRIMARY KEY, di INTEGER NOT NULL, page INTEGER NOT NULL, byte_start INTEGER NOT NULL, byte_len INTEGER NOT NULL," +
                    " char_len INTEGER NOT NULL, method TEXT NOT NULL, low_confidence INTEGER NOT NULL, ocr_confidence REAL);" +
                    "CREATE TABLE passages(id INTEGER PRIMARY KEY, di INTEGER NOT NULL, passage_id TEXT NOT NULL, page INTEGER NOT NULL, char_start INTEGER NOT NULL," +
                    " char_end INTEGER NOT NULL, paragraph_label TEXT);");
            var tx = c.BeginTransaction();
            SqliteCommand Cmd(string sql, params string[] ps)
            {
                var cmd = new SqliteCommand(sql, c, tx);
                foreach (var p in ps) cmd.Parameters.Add(new SqliteParameter(p, null));
                return cmd;
            }
            var insDoc = Cmd("INSERT INTO docs VALUES($a,$b,$c,$d,$e,$f,$g,$h,$i)", "$a", "$b", "$c", "$d", "$e", "$f", "$g", "$h", "$i");
            var insText = Cmd("INSERT INTO texts VALUES($a,$b)", "$a", "$b");
            var insPage = Cmd("INSERT INTO pages(di,page,byte_start,byte_len,char_len,method,low_confidence,ocr_confidence) VALUES($a,$b,$c,$d,$e,$f,$g,$h)", "$a", "$b", "$c", "$d", "$e", "$f", "$g", "$h");
            var insPass = Cmd("INSERT INTO passages(di,passage_id,page,char_start,char_end,paragraph_label) VALUES($a,$b,$c,$d,$e,$f)", "$a", "$b", "$c", "$d", "$e", "$f");
            void Run(SqliteCommand cmd, params object?[] v) { for (int i = 0; i < v.Length; i++) cmd.Parameters[i].Value = v[i] ?? DBNull.Value; cmd.ExecuteNonQuery(); }
            void Issue(string code) => issues[code] = ((int?)issues[code] ?? 0) + 1;
            foreach (var t in derived(Issue))
            {
                long di = nDocs;
                var a = Assess(t);
                var aj = new JsonObject { ["language"] = a.DetectedLanguage, ["reliability"] = a.Reliability, ["basis"] = a.Basis, ["deva_words"] = a.DevanagariWords, ["ratio"] = a.SignatureRatio };
                Run(insDoc, di, t.Doc.DocId, t.DerivativeId, t.TextSha, t.PipelineName, t.PipelineVersion, t.QuotingPermitted ? 1 : 0, (long)t.Bytes.Length, aj.ToJsonString());
                Run(insText, di, t.Bytes);
                foreach (var (p, bs, bl) in t.Pages)
                {
                    // The stored range must decode to exactly the page text GenerationStore verified.
                    if (Encoding.UTF8.GetString(t.Bytes, bs, bl) != p.Text) throw new TextIntegrityException($"text store build: page {p.Page} of {t.Doc.DocId} does not round-trip");
                    Run(insPage, di, p.Page, (long)bs, bl, p.Length, p.Method, p.LowConfidence ? 1 : 0, p.OcrConfidence);
                }
                foreach (var p in t.Passages) Run(insPass, di, p.PassageId, p.Page, p.CharStart, p.CharEnd, p.ParagraphLabel);
                nDocs++; nPages += t.Pages.Count; nPassages += t.Passages.Count; textBytes += t.Bytes.Length;
                if (o.FailAfterDocuments is { } fail && nDocs >= fail) throw new IOException("TEST: simulated crash during text store build");
                if (nDocs % 200 == 0)
                {
                    tx.Commit(); tx.Dispose(); tx = c.BeginTransaction();
                    foreach (var cmd in new[] { insDoc, insText, insPage, insPass }) cmd.Transaction = tx;
                }
            }
            foreach (var (k, v) in new Dictionary<string, string> { ["format"] = FormatVersion, ["generation"] = generation, ["source_digest"] = digest,
                                                                     ["issues"] = issues.ToJsonString(), ["built_utc"] = DateTime.UtcNow.ToString("O") })
                Run(Cmd("INSERT INTO meta VALUES($a,$b)", "$a", "$b"), k, v);
            tx.Commit(); tx.Dispose();
            foreach (var cmd in new[] { insDoc, insText, insPage, insPass }) cmd.Dispose();
            Exec(c, "PRAGMA journal_mode = DELETE;");
        }
        using (var f = new FileStream(db, FileMode.Open, FileAccess.ReadWrite)) f.Flush(true);
        var manifest = new JsonObject
        {
            ["format"] = FormatVersion, ["generation"] = generation, ["source_digest"] = digest,
            ["documents"] = nDocs, ["pages"] = nPages, ["passages"] = nPassages, ["text_bytes"] = textBytes,
            ["file_bytes"] = new FileInfo(db).Length, ["file_sha256"] = FileSha(db), ["built_utc"] = DateTime.UtcNow.ToString("O"),
        };
        var mtmp = Path.Combine(tmp, ManifestFile + ".tmp");
        using (var f = new FileStream(mtmp, FileMode.CreateNew, FileAccess.Write))
        { var b = Encoding.UTF8.GetBytes(manifest.ToJsonString(new JsonSerializerOptions { WriteIndented = true })); f.Write(b); f.Flush(true); }
        File.Move(mtmp, Path.Combine(tmp, ManifestFile));
        var why = Verify(tmp, generation, digest, full: true);
        if (why is not null) throw new TextIntegrityException($"newly built text store failed verification: {why}");
        Directory.Move(tmp, target);   // atomic rename on the same volume: the store becomes visible complete or not at all
        log?.Invoke($"text store: built and published {target} ({nDocs} documents, {nPages} pages, {nPassages} passages, {textBytes / 1048576.0:0.0} MB text; {sw.ElapsedMilliseconds} ms)");
    }
}
