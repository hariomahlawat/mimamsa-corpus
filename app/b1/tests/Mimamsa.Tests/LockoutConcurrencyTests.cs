using Mimamsa.Core.Identity;
using Npgsql;

namespace Mimamsa.Tests;

/// Codex review of PR #70: overlapping failed logins must not lose an increment, so the LockThreshold-th failure
/// always locks the account, and exactly one lockout is audited per lock. Uses the disposable MIMAMSA_TEST_DB.
// Same collection as the service fixture: it resets app_users in the shared MIMAMSA_TEST_DB, so these tests must not
// run in parallel with it.
[Collection("service")]
public class LockoutConcurrencyTests
{
    static NpgsqlDataSource Db() => new NpgsqlDataSourceBuilder(Environment.GetEnvironmentVariable("MIMAMSA_TEST_DB")
        ?? throw new InvalidOperationException("MIMAMSA_TEST_DB is required")).Build();

    [Fact]
    public async Task ConcurrentFailuresAlwaysReachTheLock()
    {
        await using var ds = Db();
        // throttling is opened wide so that only the lockout counter is under test
        var id = new IdentityStore(ds) { Throttle = new LoginThrottle { PerUsername = 10_000, PerSource = 10_000 } };
        await id.EnsureSchemaAsync();
        for (int round = 0; round < 20; round++)
        {
            var user = "race-" + Guid.NewGuid().ToString("N")[..10];
            Assert.True(await id.CreateUserAsync(user, "User", "correct-horse"));
            var outcomes = await Task.WhenAll(Enumerable.Range(0, IdentityStore.LockThreshold)
                .Select(i => Task.Run(() => id.LoginDetailedAsync(user, "wrong-" + i, "10.0.0." + i))));
            await using var c = await ds.OpenConnectionAsync();
            await using var q = new NpgsqlCommand("""
                SELECT u.failed_count, u.locked_until > now(),
                       (SELECT count(*) FROM audit_log a WHERE a.action = 'lockout' AND a.object = u.user_id)
                FROM app_users u WHERE u.username = $1
                """, c);
            q.Parameters.AddWithValue(user);
            await using var r = await q.ExecuteReaderAsync();
            Assert.True(await r.ReadAsync());
            Assert.Equal(IdentityStore.LockThreshold, r.GetInt32(0));
            Assert.True(r.GetBoolean(1), $"round {round}: {IdentityStore.LockThreshold} overlapping failures did not lock the account");
            Assert.Equal(1L, r.GetInt64(2));
            Assert.Contains(outcomes, o => o.outcome == IdentityStore.LoginOutcome.Locked);
        }
    }
}
