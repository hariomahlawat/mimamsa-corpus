// C16 S3-C (B07 database setup, I-3 migration gate; B08 database part). Live PostgreSQL, DISPOSABLE c16s3c_ databases
// and roles only (created and dropped here; never an operational database):
//   - db-setup: restricted roles, the B03 2.1 hardening (REVOKE CREATE ON SCHEMA public / TEMPORARY / CREATE / CONNECT
//     FROM PUBLIC), explicit application-role grants, and the probe matrix (catalogue checks plus real attempts)
//   - migrate-clone: copy-and-verify on a CLONE only, old schema unchanged, rollback demonstrated; destructive plans and
//     non-clones refused before anything runs; non-disposable names refused
//   - backup/restore of the site schema with pg_dump/pg_restore (when MIMAMSA_PG_BIN names the PostgreSQL client tools):
//     ordered table digests equal after a restore onto a fresh hardened database
using System.Text;
using System.Text.Json.Nodes;
using Mimamsa.Core.Install;
using Mimamsa.Core.Knowledge;
using Mimamsa.Tests.Activation;
using Npgsql;

namespace Mimamsa.Tests.Install;

public class SiteDatabaseInstallTests
{
    static (int code, JsonObject o) Cli(params string[] args)
    {
        var sw = new StringWriter();
        int c = InstallCli.Run(args, sw);
        return (c, JsonNode.Parse(sw.ToString())!.AsObject());
    }

    static string Env(string label, string value)
    {
        var name = "S3C_TEST_" + label.ToUpperInvariant() + "_" + S3cPg.Rand().ToUpperInvariant();
        Environment.SetEnvironmentVariable(name, value);
        return name;
    }

    static string WriteConfig(InstallConfig c, string dir)
    {
        var p = Path.Combine(dir, "install.json");
        File.WriteAllBytes(p, c.SourceBytes);
        return p;
    }

    static async Task<List<KeyValuePair<string, string>>> Dump(string db, params string[] schemas)
    {
        await using var c = new NpgsqlConnection(S3cPg.OwnerDsn(db));
        await c.OpenAsync();
        return (await SchemaDump.DumpSchemasAsync(c, schemas)).ToList();
    }

    static async Task<bool> DbExists(string db)
    {
        await using var c = new NpgsqlConnection(S3cPg.AdminDsn("postgres"));
        await c.OpenAsync();
        await using var q = new NpgsqlCommand("SELECT 1 FROM pg_database WHERE datname = $1", c);
        q.Parameters.AddWithValue(db);
        return await q.ExecuteScalarAsync() is not null;
    }

    [Fact]
    public async Task Db_setup_hardening_probe_matrix_and_the_clone_only_copy_and_verify_migration()
    {
        if (!S3cPg.Available) return;
        var r = S3cPg.Rand();
        string prefix = $"c16s3c_{r}_", app = prefix + "app", clone = prefix + "clone", clone2 = prefix + "clone2";
        var roles = SiteRoles.For(prefix);
        var b = S3cDirs.New("db");
        try
        {
            var cfg = S3cDirs.Config(b, db: app, prefix: prefix);
            var cf = WriteConfig(cfg, b);
            var admin = Env("admin", S3cPg.AdminDsn("postgres"));
            var owner = Env("owner", S3cPg.OwnerDsn("postgres"));
            var secrets = Path.Combine(b, "secrets");

            // fresh database, roles, hardening, explicit grants, probe matrix
            var (code, o) = Cli("db-setup", "--config", cf, "--admin-env", admin, "--owner-env", owner, "--secrets", secrets, "--create-db");
            Assert.True(code == 0, o.ToJsonString());
            Assert.True((bool)o["probe"]!["all_ok"]!, o.ToJsonString());
            Assert.Equal(3, Directory.GetFiles(secrets, "*.pw").Length);
            Assert.DoesNotContain(File.ReadAllText(Directory.GetFiles(secrets)[0]).Trim(), o.ToJsonString());   // secrets never printed
            // the application's own site data in the old (public) schema
            await using (var ds = NpgsqlDataSource.Create(S3cPg.OwnerDsn(app))) await TestPg.SeedSiteAsync(ds);
            var publicBefore = await Dump(app, "public");
            // re-run (upgrade): idempotent, re-asserts the hardening over the new tables
            (code, o) = Cli("db-setup", "--config", cf, "--admin-env", admin, "--owner-env", owner, "--secrets", secrets);
            Assert.True(code == 0 && (bool)o["probe"]!["all_ok"]!, o.ToJsonString());

            // a destructive plan is refused before ANY database work (no clone is even created)
            var plan = Path.Combine(b, "plan.json");
            File.WriteAllText(plan, new JsonObject { ["steps"] = new JsonArray(new JsonObject { ["id"] = "drop-old", ["kind"] = "COPY_AND_VERIFY", ["sql"] = "ALTER TABLE public.app_users DROP COLUMN role" }) }.ToJsonString());
            (code, o) = Cli("migrate-clone", "--config", cf, "--admin-env", admin, "--owner-env", owner, "--source", app, "--clone", clone2, "--plan", plan);
            Assert.Equal(2, code); Assert.Equal("MIGRATION_DESTRUCTIVE", (string?)o["code"]);
            Assert.False(await DbExists(clone2));
            File.WriteAllText(plan, new JsonObject { ["steps"] = new JsonArray(new JsonObject { ["id"] = "x", ["kind"] = "DESTRUCTIVE" }) }.ToJsonString());
            Assert.Equal("MIGRATION_DESTRUCTIVE", (string?)Cli("migrate-clone", "--config", cf, "--admin-env", admin, "--owner-env", owner, "--source", app, "--clone", clone2, "--plan", plan).o["code"]);
            // a non-disposable database name is refused
            Assert.Equal("DATABASE_NOT_DISPOSABLE", (string?)Cli("migrate-clone", "--config", cf, "--admin-env", admin, "--owner-env", owner, "--source", "mimamsa_b1", "--clone", clone2).o["code"]);
            // the migration refuses to run on a database that is not an installer clone (the source itself)
            await using (var ds = NpgsqlDataSource.Create(S3cPg.OwnerDsn(app)))
                Assert.Equal("MIGRATION_NOT_ON_CLONE", (await Assert.ThrowsAsync<DatabaseSetupException>(() => SiteDatabaseSetup.MigrateCloneAsync(ds, SiteDatabaseSetup.BuiltInPlan))).Code);
            Assert.Equal(publicBefore, await Dump(app, "public"));

            // the I-3 migration on a CLONE: forward, verify, ROLLBACK, verify, forward; old schema unchanged throughout
            (code, o) = Cli("migrate-clone", "--config", cf, "--admin-env", admin, "--owner-env", owner, "--source", app, "--clone", clone, "--secrets", secrets);
            Assert.True(code == 0, o.ToJsonString());
            Assert.True((bool)o["rollback_demonstrated"]! && (bool)o["old_schema_unchanged"]!);
            Assert.True((bool)o["probe"]!["all_ok"]!, o["probe"]!.ToJsonString());
            Assert.Contains(o["probe"]!["probes"]!.AsArray(), p => ((string?)p!["probe"])!.Contains("USAGE on schema site") && (bool)p["ok"]!);
            Assert.Equal(publicBefore, await Dump(app, "public"));      // the source was never touched
            Assert.Equal(publicBefore, await Dump(clone, "public"));    // the clone's old schema is unchanged too
            Assert.NotEmpty(await Dump(clone, "site"));

            // SQL classification (unit level)
            Assert.Empty(SiteDatabaseSetup.PlanIssues([new("add", SiteDatabaseSetup.MigrationKind.ADDITIVE, "CREATE TABLE site.x(id int REFERENCES site.y(id) ON DELETE CASCADE ON UPDATE NO ACTION)")]));
            foreach (var bad in new[] { "TRUNCATE site.a", "DELETE FROM site.a", "UPDATE site.a SET x = 1", "ALTER TABLE site.a RENAME TO b", "ALTER TABLE a ALTER COLUMN b TYPE text", "DROP SCHEMA public CASCADE", "ALTER SCHEMA site RENAME TO old" })
                Assert.NotEmpty(SiteDatabaseSetup.PlanIssues([new("m", SiteDatabaseSetup.MigrationKind.ADDITIVE, bad)]));
            Assert.NotEmpty(SiteDatabaseSetup.PlanIssues([new("unregistered", SiteDatabaseSetup.MigrationKind.COPY_AND_VERIFY)]));
        }
        finally
        {
            foreach (var d in new[] { clone2, clone, app }) try { await S3cPg.DropDbAsync(d); } catch (Exception e) { Console.Error.WriteLine("cleanup " + d + ": " + e.GetType().Name); }
            foreach (var role in roles.All) try { await S3cPg.DropRoleAsync(role); } catch (Exception e) { Console.Error.WriteLine("cleanup role: " + e.GetType().Name); }
            S3cDirs.Delete(b);
        }
    }

    [Fact]
    public async Task Site_schema_backup_and_restore_onto_a_fresh_hardened_database()
    {
        if (!S3cPg.Available || Environment.GetEnvironmentVariable("MIMAMSA_PG_BIN") is not { Length: > 0 }) return;
        var r = S3cPg.Rand();
        string prefix = $"c16s3c_{r}_", src = prefix + "src", clone = prefix + "site", target = prefix + "rst";
        var roles = SiteRoles.For(prefix);
        var b = S3cDirs.New("dbbk");
        using var fx = FixtureSite.Simple("s3c-dbbk", "G1");
        try
        {
            var admin = Env("admin", S3cPg.AdminDsn("postgres"));
            var owner = Env("owner", S3cPg.OwnerDsn("postgres"));
            var secrets = Path.Combine(b, "secrets");
            // source: seeded, cloned, migrated (site schema), hardened
            await S3cPg.CreateDbAsync(src);
            await using (var ds = NpgsqlDataSource.Create(S3cPg.OwnerDsn(src))) await TestPg.SeedSiteAsync(ds);
            var cfg = S3cDirs.Config(Path.Combine(b, "a"), site: fx.Root, db: clone, prefix: prefix);
            InstallLayout.Create(cfg, null, "test");
            var cf = WriteConfig(cfg, b);
            await using (var adm = NpgsqlDataSource.Create(S3cPg.AdminDsn("postgres")))
                await SiteDatabaseSetup.CloneAsync(adm, src, clone, S3cPg.OwnerRole, "c16s3c_");
            await using (var ds = NpgsqlDataSource.Create(S3cPg.OwnerDsn(clone)))
                await new SiteSchemaMigration(ds).ForwardAsync();
            var (code, o) = Cli("db-setup", "--config", cf, "--admin-env", admin, "--owner-env", owner, "--secrets", secrets);
            Assert.True(code == 0, o.ToJsonString());
            var siteBefore = await Dump(clone, "site");

            // backup as the BACKUP role (SELECT only on site)
            var key = Path.Combine(b, "backup.key");
            Assert.Equal(0, Cli("new-key", "--out", key).code);
            var backupDsn = Env("backup", S3cPg.RoleDsn("postgres", roles.Backup, File.ReadAllText(Path.Combine(secrets, roles.Backup + ".pw")).Trim()));
            (code, o) = Cli("backup", "--config", cf, "--key", key, "--db-env", backupDsn);
            Assert.True(code == 0, o.ToJsonString());
            var bdir = (string)o["path"]!;

            // restore onto a FRESH hardened database and a clean layout
            var tcfg = S3cDirs.Config(Path.Combine(b, "t"), db: target, prefix: prefix);
            var tcf = Path.Combine(b, "target.json"); File.WriteAllBytes(tcf, tcfg.SourceBytes);
            Assert.Equal(0, Cli("install-layout", "--config", tcf).code);
            (code, o) = Cli("db-setup", "--config", tcf, "--admin-env", admin, "--owner-env", owner, "--secrets", secrets, "--create-db");
            Assert.True(code == 0, o.ToJsonString());
            (code, o) = Cli("restore", "--config", tcf, "--key", key, "--backup", bdir, "--db-env", owner, "--secrets", secrets);
            Assert.True(code == 0, o.ToJsonString());
            Assert.True((bool)o["probe"]!["all_ok"]!, o["probe"]!.ToJsonString());
            Assert.Equal(siteBefore, await Dump(target, "site"));                // every site table identical (ordered dumps)
            await using (var c = new NpgsqlConnection(S3cPg.OwnerDsn(target)))
            {
                await c.OpenAsync();
                await using var q = new NpgsqlCommand("SELECT count(*) FROM pg_namespace WHERE nspname LIKE 'kr\\_%' OR nspname = 'knowledge'", c);
                Assert.Equal(0L, (long)(await q.ExecuteScalarAsync())!);       // knowledge is never restored from a backup
            }
            // a second restore onto the now non-empty database is refused
            Assert.Equal("TARGET_NOT_CLEAN", (string?)Cli("restore", "--config", tcf, "--key", key, "--backup", bdir, "--db-env", owner).o["code"]);
            // a wrong key never reaches the database
            var wrong = Path.Combine(b, "wrong.key"); Cli("new-key", "--out", wrong);
            Assert.Equal("BACKUP_WRONG_KEY", (string?)Cli("restore", "--config", tcf, "--key", wrong, "--backup", bdir, "--db-env", owner).o["code"]);
        }
        finally
        {
            foreach (var d in new[] { target, clone, src }) try { await S3cPg.DropDbAsync(d); } catch (Exception e) { Console.Error.WriteLine("cleanup " + d + ": " + e.GetType().Name); }
            foreach (var role in roles.All) try { await S3cPg.DropRoleAsync(role); } catch (Exception e) { Console.Error.WriteLine("cleanup role: " + e.GetType().Name); }
            S3cDirs.Delete(b);
        }
    }
}
