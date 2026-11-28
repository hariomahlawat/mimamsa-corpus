// C16 B06 / I-4: the single-writer lock of the activation journal (interface B06 section 2).
//
// Three parts:
//  - LOCK.guard: an exclusive OS file lock held only for short critical sections. Every journal append, every
//    effect, lock acquisition and exclusion acceptance runs under it, so a check of the lock record and the action it
//    authorises are atomic with respect to every other writer (this is "the same lock" exclusion acceptance takes).
//  - LOCK.json: the lock record {writer_id, pid, session, epoch, heartbeat, held}. The epoch only increases; it is
//    the fencing token carried in every journal record and control message.
//  - lease/<epoch>.live: an OS file lock held by the holder of that epoch for its whole lifetime. The OS releases it
//    when the process dies, which is how a dead holder is recognised without trusting pids.
// Contention: a live holder with a fresh heartbeat blocks other writers (LOCK_CONTENDED). A dead holder, or one whose
// heartbeat is older than StaleAfterSeconds, is taken over with epoch + 1, and the new writer must recover before any
// transition. The old writer's actions are refused (NOT_LOCK_HOLDER) because its epoch/session no longer match the
// record, checked under the guard at every append and effect.
// An optional external lock (PostgreSQL advisory lock, PgAdvisoryLock) is taken in addition; losing it (database
// session dropped) makes every later effect fail.
using System.Text.Json.Nodes;

namespace Mimamsa.Core.Activation;

public interface IExternalWriterLock : IDisposable
{
    /// Take the lock; when `takeover` is true the previous holder's session may be terminated first.
    bool TryAcquire(bool takeover);
    /// Throws when the lock has been lost (session dropped or terminated).
    void Verify();
}

public sealed record LockRecord(string? WriterId, int Pid, string? Session, long Epoch, long Heartbeat, bool Held);

public sealed class WriterLease : IDisposable
{
    readonly SiteLayout _site;
    readonly Func<long> _clock;
    readonly long _staleAfter;
    readonly IExternalWriterLock? _external;
    FileStream? _live;
    public string WriterId { get; }
    public string Session { get; } = Guid.NewGuid().ToString("N");
    public long Epoch { get; private set; }
    public bool Dead { get; private set; }

    public WriterLease(SiteLayout site, string writerId, Func<long> clock, long staleAfterSeconds, IExternalWriterLock? external = null)
    {
        if (writerId.Length is < 3 or > 120) throw new ArgumentException("writer id length");
        _site = site; WriterId = writerId; _clock = clock; _staleAfter = staleAfterSeconds; _external = external;
    }

    public static TimeSpan GuardTimeout { get; set; } = TimeSpan.FromSeconds(10);

    /// Run `body` under the exclusive guard. Contention beyond GuardTimeout is LOCK_CONTENDED.
    public static T UnderGuard<T>(SiteLayout site, Func<T> body, TimeSpan? timeout = null)
    {
        Directory.CreateDirectory(site.JournalDir);
        var deadline = DateTime.UtcNow + (timeout ?? GuardTimeout);
        FileStream? g = null;
        while (g is null)
        {
            try { g = new FileStream(site.LockGuardPath, FileMode.OpenOrCreate, FileAccess.ReadWrite, FileShare.None, 1, FileOptions.None); }
            catch (IOException) when (DateTime.UtcNow < deadline) { Thread.Sleep(15); }
            catch (IOException) { throw new ActivationRefused("LOCK_CONTENDED", "the journal guard is held by another writer"); }
        }
        using (g) return body();
    }

    public static LockRecord? ReadRecord(SiteLayout site)
    {
        var b = DurableFile.ReadIfExists(site.LockRecordPath);
        if (b is null) return null;
        var o = CanonicalJson.ParseStrict(b);
        return new LockRecord((string?)o["writer_id"], (int)(long)o["pid"]!, (string?)o["session"], (long)o["epoch"]!, (long)o["heartbeat"]!, (bool)o["held"]!);
    }

    static void WriteRecord(SiteLayout site, LockRecord r) =>
        DurableFile.WriteAtomic(site.LockRecordPath, CanonicalJson.Bytes(new JsonObject
        {
            ["writer_id"] = r.WriterId, ["pid"] = r.Pid, ["session"] = r.Session, ["epoch"] = r.Epoch, ["heartbeat"] = r.Heartbeat, ["held"] = r.Held,
        }));

    public static long CurrentEpoch(SiteLayout site) => ReadRecord(site)?.Epoch ?? 0;

    /// True when the process holding `epoch` is still alive (its OS lease lock cannot be taken).
    static bool LeaseAlive(SiteLayout site, long epoch)
    {
        var p = Path.Combine(site.LeaseDir, epoch + ".live");
        if (!File.Exists(p)) return false;
        try { using var f = new FileStream(p, FileMode.Open, FileAccess.ReadWrite, FileShare.None); return false; }
        catch (IOException) { return true; }
        catch (UnauthorizedAccessException) { return true; }
    }

    /// Acquire the lock. Returns true when this was a takeover (or the site was not OPEN): the caller must recover
    /// before any transition (`onMustRecover` runs under the guard and marks the site RECOVERING).
    public bool Acquire(Action onMustRecover)
    {
        if (Dead) throw new ActivationRefused("NOT_LOCK_HOLDER", "this writer process is dead");
        return UnderGuard(_site, () =>
        {
            var rec = ReadRecord(_site);
            bool takeover = false;
            if (rec is { Held: true } && rec.Session != Session)
            {
                bool alive = LeaseAlive(_site, rec.Epoch);
                bool fresh = _clock() - rec.Heartbeat < _staleAfter;
                if (alive && fresh) throw new ActivationRefused("LOCK_CONTENDED", "a live writer holds the activation lock");
                takeover = true;
            }
            if (_external is not null && !_external.TryAcquire(takeover))
                throw new ActivationRefused("LOCK_CONTENDED", "the database advisory lock is held by another session");
            long epoch = (rec?.Epoch ?? 0) + 1;
            Directory.CreateDirectory(_site.LeaseDir);
            _live?.Dispose();
            _live = new FileStream(Path.Combine(_site.LeaseDir, epoch + ".live"), FileMode.Create, FileAccess.ReadWrite, FileShare.None, 1, FileOptions.None);
            WriteRecord(_site, new LockRecord(WriterId, Environment.ProcessId, Session, epoch, _clock(), true));
            Epoch = epoch;
            CleanOldLeases(epoch);
            bool mustRecover = takeover || _site.ReadMarker() != SiteState.OPEN;
            if (mustRecover) onMustRecover();
            return mustRecover;
        });
    }

    void CleanOldLeases(long current)
    {
        foreach (var f in Directory.GetFiles(_site.LeaseDir, "*.live"))
        {
            if (long.TryParse(Path.GetFileNameWithoutExtension(f), out var e) && e < current)
                try { File.Delete(f); } catch (IOException) { } catch (UnauthorizedAccessException) { }
        }
    }

    /// Holder check (call under the guard): record names this session and epoch, this process's lease is open, the
    /// heartbeat is fresh and the external lock (if any) is still held.
    public void EnsureHolderUnderGuard()
    {
        var rec = ReadRecord(_site);
        if (Dead || _live is null || rec is null || !rec.Held || rec.Session != Session || rec.Epoch != Epoch)
            throw new ActivationRefused("NOT_LOCK_HOLDER", "this writer does not hold the activation lock");
        if (_clock() - rec.Heartbeat >= _staleAfter)
            throw new ActivationRefused("NOT_LOCK_HOLDER", "this writer's heartbeat is stale (it may have been taken over)");
        try { _external?.Verify(); }
        catch (Exception e) when (e is not ActivationRefused) { throw new ActivationRefused("LOCK_LOST", "the database advisory lock was lost: " + e.GetType().Name); }
    }

    public bool IsHolder()
    {
        try { UnderGuard(_site, () => { EnsureHolderUnderGuard(); return true; }); return true; }
        catch (ActivationRefused) { return false; }
    }

    /// Run an authorised action: holder check and action atomically under the guard.
    public T Authorised<T>(Func<T> body) => UnderGuard(_site, () => { EnsureHolderUnderGuard(); return body(); });
    public void Authorised(Action body) => Authorised(() => { body(); return 0; });

    public void Heartbeat() => Authorised(() =>
    {
        var rec = ReadRecord(_site)!;
        WriteRecord(_site, rec with { Heartbeat = _clock() });
    });

    public void Release()
    {
        try
        {
            UnderGuard(_site, () =>
            {
                var rec = ReadRecord(_site);
                if (rec is { Held: true } && rec.Session == Session) WriteRecord(_site, rec with { Held = false, WriterId = null, Session = null });
                return 0;
            });
        }
        finally { _live?.Dispose(); _live = null; _external?.Dispose(); }
    }

    /// Test harness only (scenario op process_die): the process is gone; the OS releases its lease lock, nothing else.
    public void SimulateDeath() { Dead = true; _live?.Dispose(); _live = null; _external?.Dispose(); }

    public void Dispose() { _live?.Dispose(); _live = null; _external?.Dispose(); }
}
