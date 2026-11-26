// Sign-in throttling (C14 F15). Sliding windows of FAILED attempts per username and per source address, held in
// memory for the single serving instance. A throttled attempt is refused before any password work and is not
// distinguishable by account existence: the same limits apply to unknown usernames.
using System.Collections.Concurrent;

namespace Mimamsa.Core.Identity;

public sealed class LoginThrottle
{
    public int PerUsername { get; init; } = 10;
    public int PerSource { get; init; } = 30;
    public TimeSpan Window { get; init; } = TimeSpan.FromMinutes(5);
    public Func<DateTime> Now { get; init; } = () => DateTime.UtcNow;

    readonly ConcurrentDictionary<string, Queue<DateTime>> _user = new(), _source = new();

    static int Count(ConcurrentDictionary<string, Queue<DateTime>> map, string key, DateTime cutoff)
    {
        if (!map.TryGetValue(key, out var q)) return 0;
        lock (q) { while (q.Count > 0 && q.Peek() < cutoff) q.Dequeue(); return q.Count; }
    }

    static void Add(ConcurrentDictionary<string, Queue<DateTime>> map, string key, DateTime at)
    {
        var q = map.GetOrAdd(key, _ => new Queue<DateTime>());
        lock (q) q.Enqueue(at);
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
    }

    /// Admin unlock also clears the username window (the source window is left alone).
    public void Clear(string username) => _user.TryRemove(username, out _);
}
