using System.Diagnostics;
using Mimamsa.Core.Delivery;
using Mimamsa.Core.Identity;
using Npgsql;

namespace Mimamsa.Tests;

/// C16 (PR #80 connection-exhaustion investigation). The 10k web benchmark stalled because sign-in held a pooled
/// connection across the password hash and then asked for a second one (AuditAsync): concurrent sign-ins at the pool
/// size each held one connection and waited for another until the pool timeout. And every closed HTTP connection ran a
/// ledger drain transaction (site-wide credit lock) even when it had never reserved credit.
[Collection("service")]
public class ConnectionPoolTests
{
    static string Dsn => Environment.GetEnvironmentVariable("MIMAMSA_TEST_DB") ?? throw new InvalidOperationException("MIMAMSA_TEST_DB is required");

    /// Many more concurrent sign-ins than pooled connections (successful, wrong-password and unknown-user) all complete,
    /// none with pool exhaustion, well inside the pool timeout.
    [Fact]
    public async Task ConcurrentSignInsNeverExhaustASmallPool()
    {
        var b = new NpgsqlConnectionStringBuilder(Dsn) { MaxPoolSize = 2, Timeout = 10 };
        await using var ds = new NpgsqlDataSourceBuilder(b.ConnectionString).Build();
        var id = new IdentityStore(ds) { Throttle = new LoginThrottle { PerUsername = 10_000, PerSource = 10_000 } };
        await id.EnsureSchemaAsync();
        var user = "pool-" + Guid.NewGuid().ToString("N")[..10];
        Assert.True(await id.CreateUserAsync(user, "User", "pool-password-1"));
        var other = "pool-" + Guid.NewGuid().ToString("N")[..10];   // wrong passwords go to another account (lockout)
        Assert.True(await id.CreateUserAsync(other, "User", "pool-password-2"));
        var sw = Stopwatch.StartNew();
        var outcomes = await Task.WhenAll(Enumerable.Range(0, 24).Select(i => Task.Run(() => (i % 3) switch
        {
            0 => id.LoginDetailedAsync(user, "pool-password-1", "10.1.0." + i),
            1 => id.LoginDetailedAsync(other, "wrong-" + i, "10.1.0." + i),
            _ => id.LoginDetailedAsync("nobody-" + i, "x", "10.1.0." + i),
        })));
        Assert.True(sw.Elapsed < TimeSpan.FromSeconds(60), $"sign-ins took {sw.Elapsed}");   // 24 full-cost hashes; the pool timeout is 10 s
        Assert.True(outcomes.Count(o => o.outcome == IdentityStore.LoginOutcome.Ok) == 8, string.Join(",", outcomes.Select(o => o.outcome)));
        Assert.All(outcomes.Where((_, i) => i % 3 != 0), o => Assert.NotEqual(IdentityStore.LoginOutcome.Ok, o.outcome));
    }

    /// A connection that never reserved credit has nothing to drain: its drain returns without touching the database
    /// (here the data source points at a closed port, so any connection attempt would throw).
    [Fact]
    public async Task DrainingAConnectionThatNeverReservedTouchesNoDatabase()
    {
        await using var dead = new NpgsqlDataSourceBuilder("Host=127.0.0.1;Port=1;Username=x;Password=x;Database=x;Timeout=2").Build();
        var ledger = new CreditLedger(dead, new CreditConfig(8L << 20, 256L << 10, 1024));
        var drained = await ledger.DrainConnectionAsync(CreditLedger.ConnPoolId(ledger.InstanceId, "conn-never-reserved"), "test");
        Assert.Empty(drained);
    }

    /// The other side: once a reservation has been attempted on a pool, its drain does reach the database (here it
    /// must fail against the closed port rather than silently skip).
    [Fact]
    public async Task DrainingAConnectionThatReservedStillRunsTheDrain()
    {
        await using var dead = new NpgsqlDataSourceBuilder("Host=127.0.0.1;Port=1;Username=x;Password=x;Database=x;Timeout=2").Build();
        var ledger = new CreditLedger(dead, new CreditConfig(8L << 20, 256L << 10, 1024));
        var pool = CreditLedger.ConnPoolId(ledger.InstanceId, "conn-reserved");
        await Assert.ThrowsAnyAsync<Exception>(() => ledger.TryReserveAsync(pool, 1024, "s-x", "doc", new string('a', 64), 0, 1024));
        await Assert.ThrowsAnyAsync<Exception>(() => ledger.DrainConnectionAsync(pool, "test"));
    }
}
