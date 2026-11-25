// Platform-neutral serving core: content-addressed vault, per-request authorization, eligibility state with a
// writer-priority guard (withdrawal fence), and strict single-range parsing. No ASP.NET or OS dependency.
using System.Security.Cryptography;
using Npgsql;

namespace MimamsaPoc.Core;

public sealed record Principal(string UserId, string SessionId, bool IsAdmin);
public sealed record CopyInfo(string DocId, string Sha256, long Length);

/// Content-addressed store: <root>/<aa>/<sha256>.pdf. Bytes are verified against the address on registration.
public sealed class Vault
{
    public string Root { get; }
    public Vault(string root) { Root = Path.GetFullPath(root); }
    public string PathFor(string sha) =>
        sha.Length == 64 && sha.All(Uri.IsHexDigit) ? Path.Combine(Root, sha[..2], sha + ".pdf") : throw new ArgumentException("bad address");

    public static string Sha256File(string path)
    {
        using var f = File.OpenRead(path);
        return Convert.ToHexString(SHA256.HashData(f)).ToLowerInvariant();
    }

    /// Copy a file into the vault iff its content hash equals the expected address.
    public bool Import(string source, string expectedSha)
    {
        if (Sha256File(source) != expectedSha) return false;
        var dst = PathFor(expectedSha);
        Directory.CreateDirectory(Path.GetDirectoryName(dst)!);
        if (!File.Exists(dst)) File.Copy(source, dst);
        return Sha256File(dst) == expectedSha;
    }

    /// Stage an immutable byte slice (prepared outside the guard).
    public async Task<byte[]> ReadSliceAsync(string sha, long offset, int count)
    {
        var buf = new byte[count];
        await using var f = new FileStream(PathFor(sha), FileMode.Open, FileAccess.Read, FileShare.Read, 1, FileOptions.Asynchronous);
        f.Position = offset;
        int read = 0;
        while (read < count) { int n = await f.ReadAsync(buf.AsMemory(read, count - read)); if (n == 0) throw new IOException("short read"); read += n; }
        return buf;
    }
}

/// Per-request authentication and ownership/authorization from the database (no caching between requests).
public sealed class AuthStore
{
    private readonly NpgsqlDataSource _db;
    public AuthStore(NpgsqlDataSource db) { _db = db; }

    public const string Schema = """
        CREATE TABLE IF NOT EXISTS poc_sessions(token_sha256 text PRIMARY KEY, user_id text NOT NULL, session_id text NOT NULL,
          is_admin boolean NOT NULL DEFAULT false, expires_at timestamptz NOT NULL);
        CREATE TABLE IF NOT EXISTS poc_grants(user_id text, doc_id text, PRIMARY KEY (user_id, doc_id));
        CREATE TABLE IF NOT EXISTS vault_copies(doc_id text, copy_sha256 text, length bigint NOT NULL,
          state text NOT NULL DEFAULT 'eligible' CHECK (state IN ('eligible','withdrawn')), fence_seq bigint NOT NULL DEFAULT 0,
          PRIMARY KEY (doc_id, copy_sha256));
        CREATE TABLE IF NOT EXISTS serving_policy(id int PRIMARY KEY CHECK (id = 1), epoch bigint NOT NULL, digest text NOT NULL);
        INSERT INTO serving_policy VALUES (1, 1, 'state-1') ON CONFLICT DO NOTHING;
        """;

    public static string Hash(string token) => Convert.ToHexString(SHA256.HashData(System.Text.Encoding.UTF8.GetBytes(token))).ToLowerInvariant();

    public async Task<Principal?> AuthenticateAsync(string? bearer)
    {
        if (string.IsNullOrEmpty(bearer) || bearer.Length > 200) return null;
        await using var c = await _db.OpenConnectionAsync();
        await using var q = new NpgsqlCommand("SELECT user_id, session_id, is_admin FROM poc_sessions WHERE token_sha256=$1 AND expires_at > now()", c);
        q.Parameters.AddWithValue(Hash(bearer));
        await using var r = await q.ExecuteReaderAsync();
        return await r.ReadAsync() ? new Principal(r.GetString(0), r.GetString(1), r.GetBoolean(2)) : null;
    }

    /// Returns the eligible copy only if the principal holds a grant for the document; otherwise null
    /// (callers answer 404 so that existence and size are not disclosed).
    public async Task<CopyInfo?> AuthorizedCopyAsync(Principal p, string docId, string? sha)
    {
        await using var c = await _db.OpenConnectionAsync();
        await using var q = new NpgsqlCommand(
            """
            SELECT v.doc_id, v.copy_sha256, v.length FROM vault_copies v JOIN poc_grants g ON g.doc_id = v.doc_id AND g.user_id = $1
            WHERE v.doc_id = $2 AND v.state = 'eligible' AND ($3::text IS NULL OR v.copy_sha256 = $3) ORDER BY v.copy_sha256 LIMIT 1
            """, c);
        q.Parameters.AddWithValue(p.UserId); q.Parameters.AddWithValue(docId);
        q.Parameters.Add(new NpgsqlParameter { Value = (object?)sha ?? DBNull.Value, NpgsqlDbType = NpgsqlTypes.NpgsqlDbType.Text });
        await using var r = await q.ExecuteReaderAsync();
        return await r.ReadAsync() ? new CopyInfo(r.GetString(0), r.GetString(1), r.GetInt64(2)) : null;
    }
}

/// In-memory mirror of copy eligibility and of the durable policy witness (epoch, digest), plus the
/// writer-priority guard. Readers (byte handoff) hold the read lock only for the synchronous, non-blocking
/// acceptance of an already staged slice. ReaderWriterLockSlim blocks new readers once a writer waits, so a
/// withdrawal cannot starve behind handoffs.
/// Withdrawal protocol (Serving §6/§10, oracle model):
///   1. write lock: Pending = true, copy marked closed, emit ADMIT  -> no new reservation/enter from here on
///   2. durable CAS on serving_policy (epoch+1, new digest) together with vault_copies.state='withdrawn'
///   3. write lock: Epoch/Digest = committed values, Pending = false, emit FENCE (after the durable commit)
/// If step 2 fails the route stays closed and Pending stays true (fail closed: no protected handoff at all).
public sealed class ServingState
{
    private readonly ReaderWriterLockSlim _guard = new(LockRecursionPolicy.NoRecursion);
    private readonly HashSet<string> _withdrawn = new();
    public long Epoch { get; private set; }
    public string Digest { get; private set; } = "";
    public bool Pending { get; private set; }

    public void Load(IEnumerable<string> withdrawnKeys, long epoch, string digest)
    {
        _guard.EnterWriteLock();
        try { foreach (var k in withdrawnKeys) _withdrawn.Add(k); Epoch = epoch; Digest = digest; }
        finally { _guard.ExitWriteLock(); }
    }
    public static string Key(string docId, string sha) => docId + "|" + sha;

    /// Evaluate `body` under the read guard with a consistent view of (pending, epoch, eligibility).
    public T UnderReadGuard<T>(Func<bool /*eligible*/, T> body, string docId, string sha)
    {
        _guard.EnterReadLock();
        try { return body(!Pending && !_withdrawn.Contains(Key(docId, sha))); }
        finally { _guard.ExitReadLock(); }
    }

    public async Task<(long epoch, string digest)> WithdrawAsync(string docId, string sha,
        Func<Task<(long epoch, string digest)>> durableCas, Action emitAdmit, Action<long, string> emitFence)
    {
        _guard.EnterWriteLock();
        try { Pending = true; _withdrawn.Add(Key(docId, sha)); emitAdmit(); }
        finally { _guard.ExitWriteLock(); }
        var (e, d) = await durableCas();      // throws -> Pending stays true: fail closed
        _guard.EnterWriteLock();
        try { Epoch = e; Digest = d; Pending = false; emitFence(e, d); }
        finally { _guard.ExitWriteLock(); }
        return (e, d);
    }
}

public enum RangeParse { Ok, Missing, Malformed, MultiRange, TooLarge, Unsatisfiable }

public static class ByteRange
{
    /// Accept only a single explicit "bytes=a-b" range (no suffix/open-ended, no multi-range).
    public static RangeParse Parse(string? header, long length, long maxLen, out long start, out long end)
    {
        start = end = -1;
        if (string.IsNullOrWhiteSpace(header)) return RangeParse.Missing;
        var h = header.Trim();
        if (!h.StartsWith("bytes=", StringComparison.Ordinal)) return RangeParse.Malformed;
        var spec = h[6..];
        if (spec.Contains(',')) return RangeParse.MultiRange;
        var parts = spec.Split('-');
        if (parts.Length != 2 || parts[0].Length == 0 || parts[1].Length == 0) return RangeParse.Malformed;
        if (!long.TryParse(parts[0], System.Globalization.NumberStyles.None, null, out start) ||
            !long.TryParse(parts[1], System.Globalization.NumberStyles.None, null, out end) || end < start) return RangeParse.Malformed;
        if (start >= length || end >= length) return RangeParse.Unsatisfiable;
        if (end - start + 1 > maxLen) return RangeParse.TooLarge;
        return RangeParse.Ok;
    }
}
