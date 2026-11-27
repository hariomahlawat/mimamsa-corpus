// Sign-in throttling (C14 F15). Sliding windows of FAILED attempts per username and per source address, held in
// memory for the single serving instance. A throttled attempt is refused before any password work and is not
// distinguishable by account existence: the same limits apply to unknown usernames.
//
// Retention is bounded (Codex review of PR #70): buckets whose attempts have all left the window are swept away, at
// most once per SweepInterval and whenever the tracked keys exceed MaxTrackedKeys, so failed sign-ins with ever-new
// usernames cannot grow memory for the life of the server. A swept bucket is marked dead under its lock before it is
// removed, so a concurrent failure that raced the removal retries into a fresh bucket instead of being lost.
using System.Collections.Concurrent;

namespace Mimamsa.Core.Identity;

public sealed class LoginThrottle
{
    public int PerUsername { get; init; } = 10;
    public int PerSource { get; init; } = 30;
    public TimeSpan Window { get; init; } = TimeSpan.FromMinutes(5);
    public Func<DateTime> Now { get; init; } = () => DateTime.UtcNow;
    public TimeSpan SweepInterval { get; init; } = TimeSpan.FromMinutes(1);
    public int MaxTrackedKeys { get; init; } = 50_000;

    sealed class Bucket { public readonly Queue<DateTime> Q = new(); public bool Dead; }

    readonly ConcurrentDictionary<string, Bucket> _user = new(), _source = new();
    long _lastSweepTicks;

    /// Keys currently held (usernames plus sources); for tests and diagnostics.
    public int TrackedKeys => _user.Count + _source.Count;

    static int Count(ConcurrentDictionary<string, Bucket> map, string key, DateTime cutoff)
    {
        if (!map.TryGetValue(key, out var b)) return 0;
        lock (b) { while (b.Q.Count > 0 && b.Q.Peek() < cutoff) b.Q.Dequeue(); return b.Dead ? 0 : b.Q.Count; }
    }

    static void Add(ConcurrentDictionary<string, Bucket> map, string key, DateTime at)
    {
        while (true)
        {
            var b = map.GetOrAdd(key, _ => new Bucket());
            lock (b) { if (!b.Dead) { b.Q.Enqueue(at); return; } }
            // the bucket was swept between GetOrAdd and the lock: its entry is gone, so the next GetOrAdd makes a new one
        }
    }

    static void Sweep(ConcurrentDictionary<string, Bucket> map, DateTime cutoff)
    {
        foreach (var (key, b) in map)
            lock (b)
            {
                while (b.Q.Count > 0 && b.Q.Peek() < cutoff) b.Q.Dequeue();
                if (b.Q.Count == 0) { b.Dead = true; map.TryRemove(new KeyValuePair<string, Bucket>(key, b)); }
            }
    }

    void MaybeSweep(DateTime now)
    {
        long last = Interlocked.Read(ref _lastSweepTicks);
        bool due = now.Ticks - last >= SweepInterval.Ticks || TrackedKeys > MaxTrackedKeys;
        if (!due || Interlocked.CompareExchange(ref _lastSweepTicks, now.Ticks, last) != last) return;   // one sweeper at a time
        var cutoff = now - Window;
        Sweep(_user, cutoff);
        Sweep(_source, cutoff);
    }

    public bool Allowed(string username, string? source)
    {
        var cutoff = Now() - Window;
        if (Count(_user, username, cutoff) >= PerUsername) return false;
        return source is null || Count(_source, source, cutoff) < PerSource;
    }

    public void RecordFailure(string username, string? source)
    {
        var now = Now();
        Add(_user, username, now);
        if (source is not null) Add(_source, source, now);
        MaybeSweep(now);
    }

    /// Admin unlock also clears the username window (the source window is left alone).
    public void Clear(string username)
    {
        if (_user.TryRemove(username, out var b)) lock (b) b.Dead = true;
    }
}
