// Platform-neutral serving primitives, refactored from app/poc/p1_hosting/core/Serving.cs (R2-N01) for B1:
//  - Vault uses the contract layout vault/sha256/<aa>/<sha256> written by app/importer (write-once, read-only).
//  - ServingState (writer-priority withdrawal fence) and ByteRange are unchanged in behaviour.
using System.Security.Cryptography;

namespace Mimamsa.Core.Delivery;

/// Content-addressed vault written by the importer: <site>/vault/sha256/<aa>/<sha256>. Read-only for the service.
public sealed class Vault
{
    public string Root { get; }
    public Vault(string siteRoot) { Root = Path.GetFullPath(Path.Combine(siteRoot, "vault", "sha256")); }

    public string PathFor(string sha) =>
        ServingState.CanonicalSha(sha) is { } s ? Path.Combine(Root, s[..2], s) : throw new ArgumentException("bad address");

    public static string Sha256File(string path)
    {
        using var f = File.OpenRead(path);
        return Convert.ToHexString(SHA256.HashData(f)).ToLowerInvariant();
    }

    /// True when the stored object exists and re-hashes to its address (checked once per copy at load).
    public bool Verify(string sha, out long length)
    {
        length = 0;
        var p = PathFor(sha);
        if (!File.Exists(p)) return false;
        length = new FileInfo(p).Length;
        return Sha256File(p) == sha;
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

/// In-memory mirror of copy eligibility and of the durable policy witness (epoch, digest), plus the writer-priority
/// guard. Readers (byte handoff, search filtering, document access) take the read lock briefly; ReaderWriterLockSlim
/// blocks new readers once a writer waits, so a withdrawal cannot starve.
/// Withdrawal protocol (Serving §6/§10):
///   1. write lock: Pending = true, copy marked closed, emit ADMIT  -> no new reservation/enter from here on
///   2. durable CAS on serving_policy (epoch+1, new digest) together with vault_copies.state='withdrawn'
///   3. write lock: Epoch/Digest = committed values, Pending = false, emit FENCE (after the durable commit)
/// If step 2 fails the route stays closed and Pending stays true (fail closed).
public sealed class ServingState
{
    private readonly ReaderWriterLockSlim _guard = new(LockRecursionPolicy.NoRecursion);
    private readonly HashSet<string> _withdrawn = new();
    private readonly HashSet<string> _withdrawnDocs = new();
    public long Epoch { get; private set; }
    public string Digest { get; private set; } = "";
    public bool Pending { get; private set; }

    public void Load(IEnumerable<(string docId, string sha)> withdrawn, long epoch, string digest)
    {
        _guard.EnterWriteLock();
        try
        {
            foreach (var (d, s) in withdrawn) { _withdrawn.Add(Key(d, s)); _withdrawnDocs.Add(d); }
            Epoch = epoch; Digest = digest;
        }
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

    /// Canonical copy identity: lower-case 64-hex sha256, else null (callers reject with a typed error).
    public static string? CanonicalSha(string? sha)
    {
        if (sha is null) return null;
        var t = sha.Trim().ToLowerInvariant();
        return t.Length == 64 && t.All(ch => ch is >= '0' and <= '9' or >= 'a' and <= 'f') ? t : null;
    }

    public bool IsWithdrawn(string docId, string sha)
    {
        _guard.EnterReadLock();
        try { return _withdrawn.Contains(Key(docId, sha)); } finally { _guard.ExitReadLock(); }
    }

    /// Any copy of the document withdrawn (search, document and citation surfaces treat the document as unavailable).
    public bool IsDocWithdrawn(string docId)
    {
        _guard.EnterReadLock();
        try { return _withdrawnDocs.Contains(docId); } finally { _guard.ExitReadLock(); }
    }

    /// Withdrawal is per DOCUMENT: every copy of the doc_id (current and earlier editions) is fenced at once.
    /// Byte-identical copies held under another doc_id are separate documents and are not affected.
    /// `durableCas` returns changed=false when the row was already withdrawn (idempotent, no epoch bump).
    /// `onFenced` runs after FENCE and before the caller acknowledges (used to cut in-flight egress).
    public async Task<(long epoch, string digest, bool changed)> WithdrawAsync(string docId, IReadOnlyCollection<string> shas,
        Func<Task<(long epoch, string digest, bool changed)>> durableCas, Action emitAdmit, Action<long, string> emitFence,
        Action? onFenced = null)
    {
        await _policyGate.WaitAsync();
        try
        {
            _guard.EnterWriteLock();
            try { Pending = true; foreach (var sha in shas) _withdrawn.Add(Key(docId, sha)); _withdrawnDocs.Add(docId); emitAdmit(); }
            finally { _guard.ExitWriteLock(); }
            var (e, d, changed) = await durableCas();      // throws -> Pending stays true: fail closed
            _guard.EnterWriteLock();
            try
            {
                if (changed && e >= Epoch) { Epoch = e; Digest = d; emitFence(e, d); }
                Pending = false;
            }
            finally { _guard.ExitWriteLock(); }
            onFenced?.Invoke();
            return (e, d, changed);
        }
        finally { _policyGate.Release(); }
    }

    /// Codex review of PR #70: every policy operation (withdrawal or reinstatement) runs to completion, durable commit
    /// AND mirror update, before the next one starts. Without this, a reinstatement whose durable commit had finished
    /// but whose mirror update was delayed could clear the fence of a withdrawal committed after it and roll the epoch
    /// back, leaving the document served while its rows say withdrawn. The mirror also never moves the epoch backwards.
    private readonly SemaphoreSlim _policyGate = new(1, 1);

    /// Reinstatement (C14, owner policy). The reverse order of WithdrawAsync: the durable CAS commits FIRST (copy rows
    /// eligible, epoch+1) and only then is the in-memory mirror relaxed under the write lock, so a failed commit leaves
    /// the document withdrawn (fail closed). Renewed eligibility verification is the caller's precondition.
    public async Task<(long epoch, string digest, bool changed)> ReinstateAsync(string docId,
        Func<Task<(long epoch, string digest, bool changed, List<string> shas)>> durableCas)
    {
        await _policyGate.WaitAsync();
        try
        {
            var (e, d, changed, shas) = await durableCas();
            if (!changed) return (e, d, false);
            _guard.EnterWriteLock();
            try
            {
                foreach (var sha in shas) _withdrawn.Remove(Key(docId, sha));
                if (!_withdrawn.Any(k => k.StartsWith(docId + "|", StringComparison.Ordinal))) _withdrawnDocs.Remove(docId);
                if (e >= Epoch) { Epoch = e; Digest = d; }
            }
            finally { _guard.ExitWriteLock(); }
            return (e, d, true);
        }
        finally { _policyGate.Release(); }
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
