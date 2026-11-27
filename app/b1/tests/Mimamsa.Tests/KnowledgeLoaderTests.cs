// C16 B03: the restricted knowledge-row loader against a live PostgreSQL, on a disposable database (c16b03_kr_*) with
// a disposable loader role (c16b03_krl_*). The database carries site data, the I-3 `site` schema and an active kr_1
// with `knowledge` views. Every refusal must drop the staging schema and leave site, public, knowledge and kr_1
// byte-identical (ordered dumps).
using System.Text;
using System.Text.Json.Nodes;
using Mimamsa.Core.Knowledge;
using Npgsql;

namespace Mimamsa.Tests;

public sealed class KrDbFixture : IAsyncLifetime
{
    public string Db { get; } = "c16b03_kr_" + TestPg.Rand();
    public string Role { get; } = "c16b03_krl_" + TestPg.Rand();
    readonly string _password = TestPg.Secret();
    public string LoaderDsn => TestPg.RoleDsn(Db, Role, _password);
    public NpgsqlDataSource Owner { get; private set; } = null!;
    public KnowledgeSources Sources { get; private set; } = null!;
    public static readonly string[] Watched = ["public", "site", "knowledge", "kr_1"];

    public async Task InitializeAsync()
    {
        try { await InitAsync(); }
        catch { await DisposeAsync(); throw; }   // xunit does not dispose a fixture whose initialisation failed
    }

    async Task InitAsync()
    {
        await TestPg.CreateDbAsync(Db);
        await using (var admin = NpgsqlDataSource.Create(TestPg.AdminDsn("postgres")))
            await KnowledgeLoaderRole.EnsureAsync(admin, Role, _password);
        Owner = NpgsqlDataSource.Create(TestPg.OwnerDsn(Db));
        await KnowledgeLoaderRole.HardenDatabaseAsync(Owner, Role);
        await TestPg.SeedSiteAsync(Owner);
        await new SiteSchemaMigration(Owner).ForwardAsync();
        Sources = KnowledgeRowsTests.FixtureSources(Syn.Gen);
        var r = await Loader().LoadAsync(Release(1, Sources));
        Assert.True(r.Ok, string.Join("; ", r.Issues));
        await KnowledgeRowLoader.PromoteAsync(Owner, 1);
    }

    public async Task DisposeAsync()
    {
        if (Owner is not null) await Owner.DisposeAsync();
        try { await TestPg.DropDbAsync(Db); } catch (Exception e) { Console.Error.WriteLine($"c16b03 cleanup {Db}: {e.GetType().Name}"); }
        try { await TestPg.DropRoleAsync(Role); } catch (Exception e) { Console.Error.WriteLine($"c16b03 cleanup {Role}: {e.GetType().Name}"); }
    }

    public KnowledgeRowLoader Loader(Func<string, long, Task>? onRow = null, Func<NpgsqlConnection, string, Task>? beforeVerify = null) =>
        new(Owner, LoaderDsn) { LoaderRole = Role, OnRowWritten = onRow, BeforeVerify = beforeVerify };

    public static KnowledgeLoadRequest Release(long n, KnowledgeSources src, Action<Dictionary<string, byte[]>, List<DeclaredTable>>? mutate = null)
    {
        var tables = KnowledgeRows.Derive(src).SelectMany(c => c.Tables).ToList();
        var files = tables.ToDictionary(t => t.Spec.Table, t => t.Bytes);
        var declared = tables.Select(t => new DeclaredTable(t.Spec.Table, t.RowCount, t.RowsSha256)).ToList();
        mutate?.Invoke(files, declared);
        return new KnowledgeLoadRequest { ReleaseSequence = n, Files = files, Declared = declared, Sources = src };
    }

    public async Task<(List<string> schemas, List<KeyValuePair<string, string>> dump)> SnapshotAsync()
    {
        await using var c = await Owner.OpenConnectionAsync();
        return (await SchemaDump.SchemasAsync(c), (await SchemaDump.DumpSchemasAsync(c, Watched)).ToList());
    }
}

[CollectionDefinition("c16b03-kr")]
public class KrCollection : ICollectionFixture<KrDbFixture>;

[Collection("c16b03-kr")]
public class KnowledgeLoaderTests(KrDbFixture f)
{
    static byte[] Rep(byte[] d, string a, string b)
    {
        var s = Encoding.UTF8.GetString(d); int i = s.IndexOf(a, StringComparison.Ordinal);
        Assert.True(i >= 0, a);
        return Encoding.UTF8.GetBytes(s[..i] + b + s[(i + a.Length)..]);
    }

    async Task<KnowledgeLoadResult> Refused(KnowledgeLoadRequest req, string code, KnowledgeRowLoader? loader = null)
    {
        var before = await f.SnapshotAsync();
        var r = await (loader ?? f.Loader()).LoadAsync(req);
        Assert.False(r.Ok);
        Assert.True(r.Codes.Contains(code), $"want {code}, got [{string.Join("; ", r.Issues)}]");
        Assert.DoesNotContain(r.Codes, c => c == "KR_STAGING_DROP_FAILED");
        var after = await f.SnapshotAsync();
        Assert.DoesNotContain(after.schemas, s => s.StartsWith($"kr_{req.ReleaseSequence}", StringComparison.Ordinal));
        Assert.Equal(before.schemas, after.schemas);
        Assert.Equal(before.dump, after.dump);       // site, public, knowledge and the active kr_1: byte-identical
        Assert.Contains(after.dump, kv => kv.Key.StartsWith("site.app_users", StringComparison.Ordinal));
        Assert.Contains(after.dump, kv => kv.Key.StartsWith("kr_1.graph_edges", StringComparison.Ordinal));
        return r;
    }

    // ------------------------------------------------------------------ success

    [Fact]
    public async Task LoadVerifiesEveryTableAndLeavesTheLoaderWithoutPrivileges()
    {
        var req = KrDbFixture.Release(5, f.Sources);
        var before = await f.SnapshotAsync();
        var r = await f.Loader().LoadAsync(req);
        try
        {
            Assert.True(r.Ok, string.Join("; ", r.Issues));
            Assert.Equal(9, r.Verified.Count);
            await using var c = await f.Owner.OpenConnectionAsync();
            foreach (var t in KnowledgeAllowlist.Tables)
            {
                var (bytes, count) = await KnowledgeRowLoader.ExportAsync(c, null, "kr_5_staging", t);
                Assert.True(bytes.AsSpan().SequenceEqual(req.Files[t.Table]), t.Table);
                Assert.Equal(req.Declared.Single(d => d.Table == t.Table).RowCount, count);
            }
            await using var q = new NpgsqlCommand("""
                SELECT has_schema_privilege($1, 'kr_5_staging', 'USAGE'), has_table_privilege($1, 'kr_5_staging.candidates', 'INSERT'),
                       has_schema_privilege($1, 'kr_1', 'USAGE'), has_schema_privilege($1, 'site', 'USAGE'), has_schema_privilege($1, 'knowledge', 'USAGE')
                """, c);
            q.Parameters.AddWithValue(f.Role);
            await using (var rd = await q.ExecuteReaderAsync())
            {
                Assert.True(await rd.ReadAsync());
                for (int i = 0; i < 5; i++) Assert.False(rd.GetBoolean(i), $"loader privilege {i} remains after the load");
            }
            var after = await f.SnapshotAsync();
            Assert.Equal(before.dump, after.dump);                      // a successful load touches only its staging schema
        }
        finally { await f.Loader().DropStaleStagingAsync(); }
        Assert.DoesNotContain("kr_5_staging", (await f.SnapshotAsync()).schemas);
    }

    [Fact]
    public async Task KnowledgeViewsPointAtTheActiveSchema()
    {
        await using var c = await f.Owner.OpenConnectionAsync();
        foreach (var t in KnowledgeAllowlist.Tables)
        {
            var (viaView, n) = await KnowledgeRowLoader.ExportAsync(c, null, "knowledge", t);
            var (direct, _) = await KnowledgeRowLoader.ExportAsync(c, null, "kr_1", t);
            Assert.True(viaView.AsSpan().SequenceEqual(direct), t.Table);
            Assert.True(n > 0, t.Table);
        }
        await Assert.ThrowsAsync<InvalidOperationException>(() => KnowledgeRowLoader.PromoteAsync(f.Owner, 1));   // no staging for 1
    }

    // ------------------------------------------------------------------ the eight arch §7 failure tests

    [Fact]
    public Task F1_UnknownTable() => Refused(KrDbFixture.Release(2, f.Sources, (files, decl) =>
    {
        files["app_users"] = "{\"user_id\":\"u-x\"}\n"u8.ToArray();
        decl.Add(new DeclaredTable("app_users", 1, CanonicalJson.Sha256Hex(files["app_users"])));
    }), "KR_ROWS_TABLE_NOT_ALLOWLISTED");

    [Fact]
    public Task F2_ExtraColumn() => Refused(KrDbFixture.Release(2, f.Sources, (files, _) =>
        files["candidates"] = Rep(files["candidates"], "\"candidate_id\"", "\"extra\":\"x\",\"candidate_id\"")), "KR_ROWS_TYPE");

    [Fact]
    public Task F3_WrongType() => Refused(KrDbFixture.Release(2, f.Sources, (files, _) =>
        files["document_identities"] = Rep(files["document_identities"], "\"quoting_permitted\":true", "\"quoting_permitted\":\"yes\"")), "KR_ROWS_TYPE");

    [Fact]
    public Task F4_DuplicateKey() => Refused(KrDbFixture.Release(2, f.Sources, (files, _) =>
    {
        var d = files["graph_nodes"];
        files["graph_nodes"] = [.. d, .. d.AsSpan(0, Array.IndexOf(d, (byte)'\n') + 1)];
    }), "KR_ROWS_DUPLICATE_KEY");

    [Fact]
    public Task F5_CountMismatchDeclared() => Refused(KrDbFixture.Release(2, f.Sources, (_, decl) =>
    {
        int i = decl.FindIndex(d => d.Table == "evidence_anchors");
        decl[i] = decl[i] with { RowCount = decl[i].RowCount + 1 };
    }), "KR_ROWS_COUNT_MISMATCH");

    [Fact]
    public Task F5_CountMismatchAfterCopy() => Refused(KrDbFixture.Release(2, f.Sources), "KR_ROWS_COUNT_MISMATCH",
        f.Loader(beforeVerify: async (c, s) =>
        {
            await using var cmd = new NpgsqlCommand($"DELETE FROM {s}.candidates WHERE candidate_id = (SELECT min(candidate_id) FROM {s}.candidates)", c);
            Assert.Equal(1, await cmd.ExecuteNonQueryAsync());
        }));

    [Fact]
    public Task F6_DigestMismatchDeclared() => Refused(KrDbFixture.Release(2, f.Sources, (_, decl) =>
    {
        int i = decl.FindIndex(d => d.Table == "taxonomy_nodes");
        decl[i] = decl[i] with { RowsSha256 = new string('0', 64) };
    }), "KR_ROWS_DIGEST_MISMATCH");

    [Fact]
    public Task F6_DigestMismatchAfterCopy() => Refused(KrDbFixture.Release(2, f.Sources), "KR_ROWS_DIGEST_MISMATCH",
        f.Loader(beforeVerify: async (c, s) =>
        {
            await using var cmd = new NpgsqlCommand($"UPDATE {s}.graph_nodes SET label = label || ' (changed)' WHERE id = (SELECT min(id) FROM {s}.graph_nodes)", c);
            Assert.Equal(1, await cmd.ExecuteNonQueryAsync());
        }));

    [Fact]
    public async Task F7_RowNotDerivableFromTheRecords()
    {
        var spec = KnowledgeAllowlist.Find("corpus_admissions")!;
        var r = await Refused(KrDbFixture.Release(2, f.Sources, (files, decl) =>
        {
            var rows = Encoding.UTF8.GetString(files["corpus_admissions"]).Split('\n').Where(l => l.Length > 0).Select(l => JsonNode.Parse(l)!.AsObject()).ToList();
            rows[0]["application_eligible"] = !rows[0]["application_eligible"]!.GetValue<bool>();
            files["corpus_admissions"] = KnowledgeRows.RowFileBytes(spec, rows);
            int i = decl.FindIndex(d => d.Table == "corpus_admissions");
            decl[i] = decl[i] with { RowsSha256 = CanonicalJson.Sha256Hex(files["corpus_admissions"]) };   // consistent manifest: only re-derivation can tell
        }), "KR_ROWS_REDERIVE_MISMATCH");
        Assert.DoesNotContain(r.Codes, c => c is "KR_ROWS_DIGEST_MISMATCH" or "KR_ROWS_COUNT_MISMATCH" or "KR_ROWS_TYPE");
        // and a graph row that the application's GraphBuilder would not produce
        await Refused(KrDbFixture.Release(2, f.Sources, (files, decl) =>
        {
            var gs = KnowledgeAllowlist.Find("graph_edges")!;
            var rows = Encoding.UTF8.GetString(files["graph_edges"]).Split('\n').Where(l => l.Length > 0).Select(l => JsonNode.Parse(l)!.AsObject()).ToList();
            rows[0]["has_legal_effect"] = !rows[0]["has_legal_effect"]!.GetValue<bool>();
            files["graph_edges"] = KnowledgeRows.RowFileBytes(gs, rows);
            int i = decl.FindIndex(d => d.Table == "graph_edges");
            decl[i] = decl[i] with { RowsSha256 = CanonicalJson.Sha256Hex(files["graph_edges"]) };
        }), "KR_ROWS_REDERIVE_MISMATCH");
    }

    [Fact]
    public Task F8_InterruptedLoad() => Refused(KrDbFixture.Release(2, f.Sources), "KR_LOAD_INTERRUPTED",
        f.Loader(onRow: (table, i) => table == "graph_edges" && i == 3 ? throw new IOException("simulated interruption mid-COPY") : Task.CompletedTask));

    [Fact]
    public Task F8_LoaderBackendKilledMidCopy() => Refused(KrDbFixture.Release(2, f.Sources), "KR_LOAD_INTERRUPTED",
        f.Loader(onRow: async (table, i) =>
        {
            if (table != "evidence_anchors" || i != 2) return;
            await TestPg.ExecAsync(TestPg.AdminDsn(f.Db), $"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE usename = '{f.Role}' AND datname = '{f.Db}'");
            await Task.Delay(100);
        }));

    [Fact]
    public async Task F8_StaleStagingFromACrashIsDroppedAndNeverReused()
    {
        // a crash after the DDL leaves an empty or partial staging schema: the next load (or startup recovery) drops it
        await TestPg.ExecAsync(TestPg.OwnerDsn(f.Db), "CREATE SCHEMA kr_7_staging; CREATE TABLE kr_7_staging.candidates(candidate_id text); INSERT INTO kr_7_staging.candidates VALUES ('left-over')");
        await TestPg.ExecAsync(TestPg.OwnerDsn(f.Db), "CREATE SCHEMA kr_8_staging");
        var before = await f.SnapshotAsync();
        var dropped = await f.Loader().DropStaleStagingAsync();
        Assert.Equal(["kr_7_staging", "kr_8_staging"], dropped.Order());
        var after = await f.SnapshotAsync();
        Assert.Equal(before.dump, after.dump);
        Assert.DoesNotContain(after.schemas, s => s.EndsWith("_staging", StringComparison.Ordinal));

        await TestPg.ExecAsync(TestPg.OwnerDsn(f.Db), "CREATE SCHEMA kr_7_staging; CREATE TABLE kr_7_staging.candidates(candidate_id text); INSERT INTO kr_7_staging.candidates VALUES ('left-over')");
        var r = await f.Loader().LoadAsync(KrDbFixture.Release(7, f.Sources));
        try
        {
            Assert.True(r.Ok, string.Join("; ", r.Issues));
            await using var c = await f.Owner.OpenConnectionAsync();
            await using var q = new NpgsqlCommand("SELECT count(*) FROM kr_7_staging.candidates WHERE candidate_id = 'left-over'", c);
            Assert.Equal(0L, await q.ExecuteScalarAsync());
        }
        finally { await f.Loader().DropStaleStagingAsync(); }
    }

    // ------------------------------------------------------------------ restricted role

    [Fact]
    public async Task LoaderRoleCannotEscapeItsStagingSchema()
    {
        var allowed = new List<string>();
        var codes = new List<string>();
        bool probed = false;
        var loader = f.Loader(onRow: async (table, i) =>
        {
            if (probed) return;
            probed = true;
            string[] probes =
            [
                "SELECT count(*) FROM site.app_users", "SELECT count(*) FROM public.app_users", "SELECT count(*) FROM knowledge.document_identities",
                "SELECT count(*) FROM kr_1.document_identities", "SELECT count(*) FROM kr_3_staging.taxonomy_nodes",
                "INSERT INTO site.audit_log(action) VALUES ('x')", "INSERT INTO public.audit_log(action) VALUES ('x')",
                "UPDATE kr_3_staging.taxonomy_nodes SET label = 'x'", "DELETE FROM kr_3_staging.taxonomy_nodes", "TRUNCATE kr_3_staging.taxonomy_nodes",
                "CREATE TABLE kr_3_staging.x(a int)", "CREATE TABLE public.x(a int)", "CREATE TEMP TABLE x(a int)", "CREATE SCHEMA x",
                "CREATE FUNCTION kr_3_staging.f() RETURNS int LANGUAGE sql AS 'SELECT 1'", "CREATE FUNCTION public.f() RETURNS int LANGUAGE sql AS 'SELECT 1'",
                "CREATE FUNCTION pg_temp.f() RETURNS int LANGUAGE sql AS 'SELECT 1'",
                "CREATE TRIGGER t BEFORE INSERT ON kr_3_staging.taxonomy_nodes FOR EACH ROW EXECUTE FUNCTION suppress_redundant_updates_trigger()",
                "CREATE RULE r AS ON INSERT TO kr_3_staging.taxonomy_nodes DO INSTEAD NOTHING", "ALTER TABLE kr_3_staging.taxonomy_nodes ADD COLUMN x int",
                "DROP TABLE kr_3_staging.taxonomy_nodes", "CREATE EXTENSION pgcrypto",
                "CREATE EXTENSION IF NOT EXISTS pg_trgm", $"SET ROLE \"{TestPg.OwnerRole}\"", $"SET SESSION AUTHORIZATION \"{TestPg.OwnerRole}\"",
                $"ALTER ROLE \"{f.Role}\" SUPERUSER", $"ALTER ROLE \"{f.Role}\" CREATEDB", "SELECT pg_read_file('postgresql.conf')",
                "COPY (SELECT 1) TO 'c16b03_probe.txt'", "ALTER SCHEMA kr_3_staging RENAME TO x",
            ];
            await using var c = new NpgsqlConnection(f.LoaderDsn);
            await c.OpenAsync();
            await using (var lt = new NpgsqlCommand("SET lock_timeout = '5s'", c)) await lt.ExecuteNonQueryAsync();
            foreach (var p in probes)
            {
                try { await using var cmd = new NpgsqlCommand(p, c); await cmd.ExecuteNonQueryAsync(); allowed.Add(p); }
                catch (PostgresException e) { codes.Add(e.SqlState); }
                catch (Exception e) { codes.Add(e.GetType().Name + ":" + p); throw; }
            }
            // positive control: the role does hold its one grant (INSERT on its staging tables), so the probes are meaningful
            await using var ok = new NpgsqlCommand("SELECT has_table_privilege(current_user, 'kr_3_staging.taxonomy_nodes', 'INSERT')", c);
            Assert.True((bool)(await ok.ExecuteScalarAsync())!);
        });
        var r = await loader.LoadAsync(KrDbFixture.Release(3, f.Sources));
        try
        {
            Assert.True(probed);
            Assert.True(codes.Count + allowed.Count == 30, string.Join(",", codes) + " | " + string.Join("; ", r.Issues));
            Assert.True(allowed.Count == 0, "the loader role was allowed: " + string.Join(" | ", allowed));
            Assert.True(codes.Count(c => c == "42501") >= 25, string.Join(",", codes));   // insufficient_privilege
            Assert.True(r.Ok, string.Join("; ", r.Issues));
        }
        finally { await f.Loader().DropStaleStagingAsync(); }
    }

    [Fact]
    public async Task PrivilegedLoaderConnectionIsRefusedBeforeAnythingIsCreated()
    {
        // the application role (database owner) presented as the loader: refused, fail closed
        var asOwner = new KnowledgeRowLoader(f.Owner, TestPg.OwnerDsn(f.Db)) { LoaderRole = TestPg.OwnerRole };
        await Refused(KrDbFixture.Release(2, f.Sources), "KR_LOADER_ROLE_PRIVILEGED", asOwner);
        // the right role name, but a connection that authenticates as someone else
        var mismatch = new KnowledgeRowLoader(f.Owner, TestPg.OwnerDsn(f.Db)) { LoaderRole = f.Role };
        var r = await Refused(KrDbFixture.Release(2, f.Sources), "KR_LOADER_ROLE_PRIVILEGED", mismatch);
        Assert.Contains(r.Issues, i => i.Message.Contains("does not authenticate"));
        // a loader role that was given access to site
        await TestPg.ExecAsync(TestPg.OwnerDsn(f.Db), $"GRANT USAGE ON SCHEMA site TO \"{f.Role}\"");
        try { await Refused(KrDbFixture.Release(2, f.Sources), "KR_LOADER_ROLE_PRIVILEGED"); }
        finally { await TestPg.ExecAsync(TestPg.OwnerDsn(f.Db), $"REVOKE USAGE ON SCHEMA site FROM \"{f.Role}\""); }
    }

    [Fact]
    public async Task StagingTamperedWithATriggerIsRefused()
    {
        await Refused(KrDbFixture.Release(2, f.Sources), "KR_STAGING_TAMPERED", f.Loader(beforeVerify: async (c, s) =>
        {
            await using var cmd = new NpgsqlCommand($"CREATE TRIGGER t BEFORE UPDATE ON {s}.candidates FOR EACH ROW EXECUTE FUNCTION suppress_redundant_updates_trigger()", c);
            await cmd.ExecuteNonQueryAsync();
        }));
    }

    // ------------------------------------------------------------------ hostile values

    [Fact]
    public async Task SqlTextInAValueIsInertData()
    {
        const string hostile = "x'); DROP TABLE site.app_users; DROP SCHEMA kr_1 CASCADE; --";
        var ids = f.Sources.Identities.Select(i => i.DeepClone().AsObject()).ToList();
        ids[0]["doc_id"] = hostile;
        var src = new KnowledgeSources
        {
            Identities = ids, Anchors = f.Sources.Anchors, Relationships = f.Sources.Relationships, Taxonomy = f.Sources.Taxonomy,
            Admissions = f.Sources.Admissions, Candidates = f.Sources.Candidates, ProvisionVersions = f.Sources.ProvisionVersions, Graph = f.Sources.Graph,
        };
        var before = await f.SnapshotAsync();
        var r = await f.Loader().LoadAsync(KrDbFixture.Release(6, src));
        try
        {
            Assert.True(r.Ok, string.Join("; ", r.Issues));
            await using var c = await f.Owner.OpenConnectionAsync();
            await using var q = new NpgsqlCommand("SELECT count(*) FROM kr_6_staging.document_identities WHERE doc_id = $1", c);
            q.Parameters.AddWithValue(hostile);
            Assert.Equal(1L, await q.ExecuteScalarAsync());
            Assert.Equal(before.dump, (await f.SnapshotAsync()).dump);
        }
        finally { await f.Loader().DropStaleStagingAsync(); }
    }

    [Theory]
    [InlineData("nul", "KR_ROWS_TYPE")]
    [InlineData("non-nfc", "KR_ROWS_NOT_CANONICAL")]
    [InlineData("oversized", "KR_ROWS_OVERSIZED")]
    [InlineData("reviewed-edge", "KR_ROWS_TYPE")]
    public Task HostileRowValuesAreRejectedBeforeCopy(string kind, string code) => Refused(KrDbFixture.Release(2, f.Sources, (files, _) =>
    {
        switch (kind)
        {
            case "nul": files["candidates"] = Rep(files["candidates"], "\"status\":\"", "\"status\":\"\\u0000"); break;
            case "non-nfc": files["candidates"] = Rep(files["candidates"], "\"status\":\"", "\"status\":\"é"); break;
            case "oversized": files["candidates"] = [.. Encoding.UTF8.GetBytes("{\"candidate_id\":\"" + new string('z', KnowledgeAllowlist.MaxRowBytes) + "\"}\n"), .. files["candidates"]]; break;
            case "reviewed-edge":
                var s = Encoding.UTF8.GetString(files["graph_edges"]);
                var v = KnowledgeAllowlist.BuilderVerification.First(b => s.Contains($"\"verification\":\"{b}\""));
                files["graph_edges"] = Rep(files["graph_edges"], $"\"verification\":\"{v}\"", "\"verification\":\"LEGAL_REVIEWED\"");
                break;
        }
    }), code);
}
