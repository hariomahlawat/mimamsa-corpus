// C16 B03 test support: disposable PostgreSQL databases and roles (prefix c16b03_), never the operational databases.
//   MIMAMSA_TEST_DB        Npgsql DSN of the application role (owner of the disposable databases; the activator here)
//   MIMAMSA_TEST_PG_ADMIN  optional DSN of a role with CREATEDB and CREATEROLE (default: MIMAMSA_TEST_DB, which is a
//                          superuser in CI); used only to create/drop c16b03_* databases and roles
using System.Security.Cryptography;
using Mimamsa.Core.Delivery;
using Mimamsa.Core.Graph;
using Mimamsa.Core.Identity;
using Mimamsa.Core.Studio;
using Npgsql;

namespace Mimamsa.Tests;

public static class TestPg
{
    static string AppDsn => Environment.GetEnvironmentVariable("MIMAMSA_TEST_DB") ?? throw new InvalidOperationException("MIMAMSA_TEST_DB is required");
    static string AdminBase => Environment.GetEnvironmentVariable("MIMAMSA_TEST_PG_ADMIN") is { Length: > 0 } a ? a : AppDsn;

    public static string OwnerRole => new NpgsqlConnectionStringBuilder(AppDsn).Username!;
    public static string OwnerDsn(string db) => new NpgsqlConnectionStringBuilder(AppDsn) { Database = db, MaxPoolSize = 4 }.ConnectionString;
    public static string AdminDsn(string db) => new NpgsqlConnectionStringBuilder(AdminBase) { Database = db, MaxPoolSize = 2 }.ConnectionString;
    public static string RoleDsn(string db, string role, string password) =>
        new NpgsqlConnectionStringBuilder(AppDsn) { Database = db, Username = role, Password = password, MaxPoolSize = 2 }.ConnectionString;

    public static string Rand() => Convert.ToHexString(RandomNumberGenerator.GetBytes(5)).ToLowerInvariant();
    public static string Secret() => Convert.ToBase64String(RandomNumberGenerator.GetBytes(24));

    public static async Task ExecAsync(string dsn, string sql)
    {
        await using var c = new NpgsqlConnection(dsn);
        await c.OpenAsync();
        await using var cmd = new NpgsqlCommand(sql, c);
        await cmd.ExecuteNonQueryAsync();
    }

    static void Guard(string name)
    {
        if (!name.StartsWith("c16b03_", StringComparison.Ordinal) || name.Any(ch => !(char.IsAsciiLetterLower(ch) || char.IsAsciiDigit(ch) || ch == '_')))
            throw new InvalidOperationException("only disposable c16b03_ objects may be created or dropped by these tests");
    }

    public static async Task CreateDbAsync(string name, string? template = null)
    {
        Guard(name);
        if (template is not null) Guard(template);
        NpgsqlConnection.ClearAllPools();
        var sql = $"CREATE DATABASE \"{name}\" OWNER \"{OwnerRole}\"" + (template is null ? "" : $" TEMPLATE \"{template}\"");
        for (int attempt = 0; ; attempt++)
        {
            try { await ExecAsync(AdminDsn("postgres"), sql); return; }
            catch (PostgresException e) when (e.SqlState == "55006" && attempt < 5)   // template still in use: wait for pooled sessions to close
            {
                await ExecAsync(AdminDsn("postgres"), $"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '{template}' AND pid <> pg_backend_pid()");
                await Task.Delay(200);
            }
        }
    }

    public static async Task DropDbAsync(string name)
    {
        Guard(name);
        NpgsqlConnection.ClearAllPools();
        await ExecAsync(AdminDsn("postgres"), $"DROP DATABASE IF EXISTS \"{name}\" WITH (FORCE)");
    }

    public static async Task DropRoleAsync(string role)
    {
        Guard(role);
        NpgsqlConnection.ClearAllPools();
        await ExecAsync(AdminDsn("postgres"), $"DROP ROLE IF EXISTS \"{role}\"");
    }

    /// Site data written through the application's own stores (and SQL for tables without a simple API): users,
    /// sessions, audit, vault copies, withdrawals, serving policy, studio, credits, a published graph and a review row.
    public static async Task SeedSiteAsync(NpgsqlDataSource ds)
    {
        var id = new IdentityStore(ds);
        await id.EnsureSchemaAsync();
        await id.CreateUserAsync("c16b03-admin", "Admin", "c16b03-password-1", 100_000);
        await id.CreateUserAsync("c16b03-reader", "User", "c16b03-password-2", 100_000);
        Assert.NotNull(await id.LoginAsync("c16b03-reader", "c16b03-password-2"));
        await id.AuditAsync("c16b03-admin", "test.seed", "x'); DROP TABLE app_users; --", "unicode न्याय \U0001F600");
        var pol = new PolicyStore(ds);
        await pol.EnsureSchemaAsync();
        await pol.SyncCopiesAsync([("doc-a", new string('a', 64), 10), ("doc-b", new string('b', 64), 20)]);
        await using (var c = await ds.OpenConnectionAsync())
        await using (var cmd = new NpgsqlCommand($"""
            UPDATE vault_copies SET state='withdrawn' WHERE doc_id='doc-b';
            INSERT INTO withdrawals(doc_id, copy_sha256, reason, actor, epoch) VALUES ('doc-b', '{new string('b', 64)}', 'test withdrawal', 'c16b03-admin', 2);
            UPDATE serving_policy SET epoch = 2, digest = 'state-2';
            {CreditLedger.Schema}
            INSERT INTO credit_pools(pool_id, cap) VALUES ('site', 1000), ('conn', 50);
            """, c))
            await cmd.ExecuteNonQueryAsync();
        var studio = new StudioStore(ds);
        await studio.EnsureSchemaAsync();
        await studio.CreateAsync("c16b03-reader", "Draft memo", "memo");
        var graph = new GraphStore(ds);
        await graph.EnsureSchemaAsync();
        await graph.PublishAsync(GraphBuilder.Build(Syn.Gen) with { GenerationId = "c16b03-gen" });
        await using (var c = await ds.OpenConnectionAsync())
        await using (var cmd = new NpgsqlCommand("INSERT INTO graph_edge_reviews(edge_id, review_state, reviewer, note) VALUES ('E-test', 'UNREVIEWED', 'nobody', 'seed')", c))
            await cmd.ExecuteNonQueryAsync();
    }
}
