using Mimamsa.Core.Identity;

namespace Mimamsa.Tests;

/// Codex review of PR #70: the sign-in throttle must not retain buckets for usernames and sources that are never seen
/// again, and sweeping must not lose failures recorded concurrently.
public class LoginThrottleRetentionTests
{
    sealed class Clock { public DateTime T = new(2026, 11, 27, 0, 0, 0, DateTimeKind.Utc); }

    [Fact]
    public void ExpiredBucketsAreSweptAway()
    {
        var clock = new Clock();
        var t = new LoginThrottle { Now = () => clock.T, Window = TimeSpan.FromMinutes(5), SweepInterval = TimeSpan.FromMinutes(1) };
        for (int i = 0; i < 2000; i++) t.RecordFailure($"nobody-{i}", $"10.1.{i / 250}.{i % 250}");
        Assert.True(t.TrackedKeys >= 2000);
        clock.T = clock.T.AddMinutes(6);                       // every earlier attempt has left the window
        t.RecordFailure("late", "10.9.9.9");
        Assert.Equal(2, t.TrackedKeys);
    }

    [Fact]
    public void KeysStillInTheWindowAreKeptAndStillThrottle()
    {
        var clock = new Clock();
        var t = new LoginThrottle { Now = () => clock.T, PerUsername = 3, Window = TimeSpan.FromMinutes(5), SweepInterval = TimeSpan.Zero };
        for (int i = 0; i < 3; i++) t.RecordFailure("alice", null);
        clock.T = clock.T.AddMinutes(1);
        t.RecordFailure("someone-else", null);                // forces a sweep while alice's attempts are still recent
        Assert.False(t.Allowed("alice", null));
        clock.T = clock.T.AddMinutes(5);
        Assert.True(t.Allowed("alice", null));
    }

    [Fact]
    public async Task ConcurrentFailuresAreNotLostToTheSweep()
    {
        const int threads = 8, perThread = 500, total = threads * perThread;
        var now = new DateTime(2026, 11, 27, 0, 0, 0, DateTimeKind.Utc);
        // the sweep runs on every call (SweepInterval zero), racing the additions to the same bucket
        var t = new LoginThrottle { Now = () => now, PerUsername = total, Window = TimeSpan.FromMinutes(5), SweepInterval = TimeSpan.Zero };
        await Task.WhenAll(Enumerable.Range(0, threads).Select(k => Task.Run(() =>
        {
            for (int i = 0; i < perThread; i++) { t.RecordFailure("target", null); if (i % 7 == 0) t.RecordFailure($"noise-{k}-{i}", null); }
        })));
        Assert.False(t.Allowed("target", null));               // all `total` failures are still counted
    }
}
