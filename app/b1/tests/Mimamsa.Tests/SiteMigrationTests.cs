// C16 B03 / I-3 (SG-2): the additive copy-and-verify migration, demonstrated ONLY on cloned databases. A disposable
// source database (c16b03_src_*) is seeded through the application's own stores; each test runs on a clone made with
// CREATE DATABASE ... TEMPLATE (never from an operational database) and checks, by ordered dumps, that the old schema
// and all site data are preserved through forward migration, compatibility use, a crash mid-migration and rollback.
using Mimamsa.Core.Identity;
using Mimamsa.Core.Knowledge;
using Npgsql;

namespace Mimamsa.Tests;

public sealed class MigrationSourceFixture : IAsyncLifetime
{
    public string Source { get; } = "c16b03_src_" + TestPg.Rand();
    public List<KeyValuePair<string, string>> SourceDump { get; private set; } = [];
    readonly List<string> _clones = [];

    public async Task InitializeAsync()
    {
        try
        {
            await TestPg.CreateDbAsync(Source);
            await using (var ds = NpgsqlDataSource.Create(TestPg.OwnerDsn(Source))) await TestPg.SeedSiteAsync(ds);
            SourceDump = await DumpAsync(Source, "public");
        }
        catch { await DisposeAsync(); throw; }   // xunit does not dispose a fixture whose initialisation failed
    }

    public async Task DisposeAsync()
    {
        foreach (var c in _clones.Append(Source))
            try { await TestPg.DropDbAsync(c); } catch (Exception e) { Console.Error.WriteLine($"c16b03 cleanup {c}: {e.GetType().Name}"); }
    }

    public async Task<string> CloneAsync()
    {
        var name = "c16b03_clone_" + TestPg.Rand();
        await TestPg.CreateDbAsync(name, template: Source);
        _clones.Add(name);
        return name;
    }

    public static async Task<List<KeyValuePair<string, string>>> DumpAsync(string db, params string[] schemas)
    {
        await using var c = new NpgsqlConnection(TestPg.OwnerDsn(db));
        await c.OpenAsync();
        return (await SchemaDump.DumpSchemasAsync(c, schemas)).ToList();
    }

    public static async Task<List<string>> SchemasAsync(string db)
    {
        await using var c = new NpgsqlConnection(TestPg.OwnerDsn(db));
        await c.OpenAsync();
        return await SchemaDump.SchemasAsync(c);
    }
}

[CollectionDefinition("c16b03-migration")]
public class MigrationCollection : ICollectionFixture<MigrationSourceFixture>;

[Collection("c16b03-migration")]
public class SiteMigrationTests(MigrationSourceFixture f)
{
    static readonly string[] SiteTables = ["app_sessions", "app_users", "audit_log", "credit_instances", "credit_pools", "credit_reservations",
        "graph_edge_reviews", "serving_policy", "studio_documents", "studio_notes", "studio_versions", "vault_copies", "withdrawals"];

    [Fact]
    public async Task ForwardCopiesAndVerifiesThenRollsBackWithTheOldSchemaUnchanged()
    {
        var db = await f.CloneAsync();
        var publicBefore = await MigrationSourceFixture.DumpAsync(db, "public");
        Assert.Equal(f.SourceDump, publicBefore);                                   // the clone is the source

        await using var ds = NpgsqlDataSource.Create(TestPg.OwnerDsn(db));
        var mig = new SiteSchemaMigration(ds);
        Assert.Equal("NOT_APPLIED", await mig.StatusAsync());
        var report = await mig.ForwardAsync();
        Assert.Equal("APPLIED", await mig.StatusAsync());
        Assert.Equal(SiteTables, report.Tables.Select(t => t.Table).Order(StringComparer.Ordinal));
        Assert.Equal(["graph_edges", "graph_generation", "graph_nodes"], report.LeftInPlace.Order(StringComparer.Ordinal));
        Assert.All(report.Tables, t => Assert.Equal(t.OldDigest, t.NewDigest));
        Assert.Contains(report.Tables, t => t.Table == "app_users" && t.Rows == 2);
        Assert.Contains(report.Tables, t => t.Table == "app_sessions" && t.Rows == 1);
        Assert.Contains(report.Tables, t => t.Table == "withdrawals" && t.Rows == 1);
        Assert.Contains(report.Tables, t => t.Table == "studio_documents" && t.Rows == 1);
        Assert.Contains(report.Tables, t => t.Table == "audit_log" && t.Rows >= 2);

        // additive: the old schema is byte-identical, the new schemas exist, and the copies equal the old tables
        Assert.Equal(publicBefore, await MigrationSourceFixture.DumpAsync(db, "public"));
        var schemas = await MigrationSourceFixture.SchemasAsync(db);
        Assert.Contains("site", schemas); Assert.Contains("knowledge", schemas);
        Assert.Empty(await mig.DivergedTablesAsync());
        await Assert.ThrowsAsync<SiteMigrationException>(() => mig.ForwardAsync());   // never applied twice

        // the copies have their own sequences, positioned at the old values; foreign keys point at the copies
        await using (var c = await ds.OpenConnectionAsync())
        {
            await using var q = new NpgsqlCommand("""
                SELECT (SELECT last_value FROM site.audit_log_id_seq) = (SELECT last_value FROM public.audit_log_id_seq),
                       pg_get_expr(d.adbin, d.adrelid) LIKE '%site.audit_log_id_seq%',
                       (SELECT count(*) FROM pg_constraint k WHERE k.conrelid = 'site.app_sessions'::regclass AND k.contype = 'f' AND k.confrelid = 'site.app_users'::regclass),
                       (SELECT count(*) FROM pg_constraint k WHERE k.conrelid = 'site.studio_versions'::regclass AND k.contype = 'f' AND k.confrelid = 'site.studio_documents'::regclass),
                       has_schema_privilege('public', 'site', 'USAGE')
                FROM pg_attrdef d JOIN pg_attribute a ON a.attrelid = d.adrelid AND a.attnum = d.adnum
                WHERE d.adrelid = 'site.audit_log'::regclass AND a.attname = 'id'
                """, c);
            await using var r = await q.ExecuteReaderAsync();
            Assert.True(await r.ReadAsync());
            Assert.True(r.GetBoolean(0)); Assert.True(r.GetBoolean(1)); Assert.Equal(1L, r.GetInt64(2)); Assert.Equal(1L, r.GetInt64(3)); Assert.False(r.GetBoolean(4));
        }

        // compatibility: the unchanged application keeps working against the old tables (default search_path)
        var id = new IdentityStore(ds);
        await id.EnsureSchemaAsync();
        Assert.True(await id.CreateUserAsync("c16b03-after", "User", "c16b03-password-3", 100_000));
        Assert.NotNull(await id.LoginAsync("c16b03-after", "c16b03-password-3"));
        Assert.Equal(3, await id.UserCountAsync());
        Assert.Contains("app_users", await mig.DivergedTablesAsync());               // written on the old side only
        var publicBeforeRollback = await MigrationSourceFixture.DumpAsync(db, "public");

        // rollback: the new schemas go, the old schema (with the compatibility-window writes) is unchanged
        await mig.RollbackAsync();
        Assert.Equal("NOT_APPLIED", await mig.StatusAsync());
        schemas = await MigrationSourceFixture.SchemasAsync(db);
        Assert.DoesNotContain("site", schemas); Assert.DoesNotContain("knowledge", schemas);
        Assert.Equal(publicBeforeRollback, await MigrationSourceFixture.DumpAsync(db, "public"));
        Assert.Equal(f.SourceDump, await MigrationSourceFixture.DumpAsync(f.Source, "public"));   // the source was never touched

        // and the migration can be applied again after a rollback
        var again = await mig.ForwardAsync();
        Assert.Contains(again.Tables, t => t.Table == "app_users" && t.Rows == 3);
        await mig.RollbackAsync();
    }

    [Fact]
    public async Task TheSiteSchemaServesTheApplicationAndRollbackRefusesToLoseItsWrites()
    {
        var db = await f.CloneAsync();
        await using (var ds = NpgsqlDataSource.Create(TestPg.OwnerDsn(db))) await new SiteSchemaMigration(ds).ForwardAsync();
        var publicAfterMigration = await MigrationSourceFixture.DumpAsync(db, "public");

        // an application connection whose search_path is the new schema reads and writes the copies
        var siteDsn = new NpgsqlConnectionStringBuilder(TestPg.OwnerDsn(db)) { SearchPath = "site" }.ConnectionString;
        await using (var site = NpgsqlDataSource.Create(siteDsn))
        {
            var id = new IdentityStore(site);
            await id.EnsureSchemaAsync();
            Assert.Equal(2, await id.UserCountAsync());
            Assert.NotNull(await id.LoginAsync("c16b03-admin", "c16b03-password-1"));            // copied password hash still verifies
            Assert.True(await id.CreateUserAsync("c16b03-site-only", "User", "c16b03-password-4", 100_000));
            await id.AuditAsync("c16b03-admin", "test.site", null, null);                       // the copy's own audit sequence
        }
        Assert.Equal(publicAfterMigration, await MigrationSourceFixture.DumpAsync(db, "public"));   // the old schema did not see those writes

        await using var ds2 = NpgsqlDataSource.Create(TestPg.OwnerDsn(db));
        var mig = new SiteSchemaMigration(ds2);
        var e = await Assert.ThrowsAsync<SiteMigrationException>(() => mig.RollbackAsync());
        Assert.Equal("SITE_ROLLBACK_WOULD_LOSE_WRITES", e.Code);
        Assert.Contains("site", await MigrationSourceFixture.SchemasAsync(db));
    }

    [Theory]
    [InlineData("exception")]
    [InlineData("backend-killed")]
    public async Task CrashMidMigrationLeavesNothingAndARetrySucceeds(string how)
    {
        var db = await f.CloneAsync();
        var publicBefore = await MigrationSourceFixture.DumpAsync(db, "public");
        await using var ds = NpgsqlDataSource.Create(TestPg.OwnerDsn(db));
        int copied = 0;
        var crashing = new SiteSchemaMigration(ds)
        {
            AfterTableCopied = async (table, conn) =>
            {
                if (++copied != 3) return;
                if (how == "exception") throw new IOException("simulated crash mid-migration");
                await TestPg.ExecAsync(TestPg.AdminDsn(db), $"SELECT pg_terminate_backend({conn.ProcessID})");
                await Task.Delay(100);
            },
        };
        await Assert.ThrowsAnyAsync<Exception>(() => crashing.ForwardAsync());
        NpgsqlConnection.ClearAllPools();
        var schemas = await MigrationSourceFixture.SchemasAsync(db);
        Assert.DoesNotContain("site", schemas); Assert.DoesNotContain("knowledge", schemas);
        Assert.Equal(publicBefore, await MigrationSourceFixture.DumpAsync(db, "public"));

        await using var ds2 = NpgsqlDataSource.Create(TestPg.OwnerDsn(db));
        var mig = new SiteSchemaMigration(ds2);
        Assert.Equal("NOT_APPLIED", await mig.StatusAsync());
        var report = await mig.ForwardAsync();
        Assert.Equal(SiteTables.Length, report.Tables.Count);
        Assert.Empty(await mig.DivergedTablesAsync());
        await mig.RollbackAsync();
        Assert.Equal(publicBefore, await MigrationSourceFixture.DumpAsync(db, "public"));
    }

    [Fact]
    public async Task RollbackAlsoDropsKnowledgeSchemasLoadedAfterTheMigration()
    {
        var db = await f.CloneAsync();
        await using var ds = NpgsqlDataSource.Create(TestPg.OwnerDsn(db));
        var mig = new SiteSchemaMigration(ds);
        await mig.ForwardAsync();
        await TestPg.ExecAsync(TestPg.OwnerDsn(db), "CREATE SCHEMA kr_4; CREATE TABLE kr_4.candidates(candidate_id text); CREATE SCHEMA kr_5_staging; CREATE VIEW knowledge.candidates AS SELECT * FROM kr_4.candidates");
        var publicBefore = await MigrationSourceFixture.DumpAsync(db, "public");
        await mig.RollbackAsync();
        var schemas = await MigrationSourceFixture.SchemasAsync(db);
        Assert.DoesNotContain(schemas, s => s is "site" or "knowledge" or "kr_4" or "kr_5_staging");
        Assert.Equal(publicBefore, await MigrationSourceFixture.DumpAsync(db, "public"));
        Assert.Equal(f.SourceDump, publicBefore);
    }
}
