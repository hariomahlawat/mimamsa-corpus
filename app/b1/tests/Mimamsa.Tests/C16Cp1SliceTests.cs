// C16 Tranche B CP-1: the serving journey of the integrated, explicitly DEGRADED vertical slice (FIXTURE acceptance
// only). It runs ONLY when the slice driver (app/b1/build/c16_cp1_slice.py) has prepared an isolated development site
// and points MIMAMSA_CP1_CONTEXT at it; otherwise it does nothing (the ordinary suite is unaffected).
//
// On that site and on DISPOSABLE c16cp1_* databases (never an operational one) it runs, with each stream's own code:
//   B03  the I-3 migration on a CLONED database; the restricted loader stages, verifies (typed rows, counts, digests,
//        full re-derivation) the knowledge rows AND the graph rows of both generations through the one typed loader;
//   B04  the shipped (prebuilt) text store is adopted (2.1 source digest), the lexical index file is checked;
//   B06  the journal is initialised on G1 and ACTIVATES G2 with Mimamsa:Activation:Enabled in a real Kestrel process
//        (authenticated control channel, PostgreSQL advisory lock, knowledge views repointed in DB_APPLIED);
// and checks: only admitted or independently established copies are visible; an exclusion accepted AFTER activation is
// enforced at the response boundary (search, document, text, citation, permalink) without a restart; a rollback works.
// Results go to the context's results file for the driver (which computes the outcome with the reference rule).
using System.Diagnostics;
using System.Net;
using System.Net.Http.Json;
using System.Security.Cryptography;
using System.Text.Json.Nodes;
using Mimamsa.Core.Activation;
using Mimamsa.Core.Generation;
using Mimamsa.Core.Knowledge;
using Npgsql;

namespace Mimamsa.Tests;

/// Disposable CP-1 databases and roles: prefix c16cp1_ only (guarded).
static class Cp1Pg
{
    static string AppDsn => Environment.GetEnvironmentVariable("MIMAMSA_TEST_DB") ?? throw new InvalidOperationException("MIMAMSA_TEST_DB is required");
    static string AdminBase => Environment.GetEnvironmentVariable("MIMAMSA_TEST_PG_ADMIN") is { Length: > 0 } a ? a : AppDsn;
    public static string OwnerRole => new NpgsqlConnectionStringBuilder(AppDsn).Username!;
    public static string OwnerDsn(string db, int pool = 4) => new NpgsqlConnectionStringBuilder(AppDsn) { Database = db, MaxPoolSize = pool }.ConnectionString;
    public static string AdminDsn(string db) => new NpgsqlConnectionStringBuilder(AdminBase) { Database = db, MaxPoolSize = 2 }.ConnectionString;
    public static string RoleDsn(string db, string role, string pw) =>
        new NpgsqlConnectionStringBuilder(AppDsn) { Database = db, Username = role, Password = pw, MaxPoolSize = 2 }.ConnectionString;

    public static void Guard(string name)
    {
        if (!name.StartsWith("c16cp1_", StringComparison.Ordinal) || name.Any(ch => !(char.IsAsciiLetterLower(ch) || char.IsAsciiDigit(ch) || ch == '_')))
            throw new InvalidOperationException("only disposable c16cp1_ objects may be created or dropped");
    }

    public static async Task ExecAsync(string dsn, string sql)
    {
        await using var c = new NpgsqlConnection(dsn);
        await c.OpenAsync();
        await using var cmd = new NpgsqlCommand(sql, c);
        await cmd.ExecuteNonQueryAsync();
    }

    public static async Task CreateDbAsync(string name, string? template = null)
    {
        Guard(name); if (template is not null) Guard(template);
        NpgsqlConnection.ClearAllPools();
        await ExecAsync(AdminDsn("postgres"), $"CREATE DATABASE \"{name}\" OWNER \"{OwnerRole}\"" + (template is null ? "" : $" TEMPLATE \"{template}\""));
    }

    public static async Task DropDbAsync(string name) { Guard(name); NpgsqlConnection.ClearAllPools(); await ExecAsync(AdminDsn("postgres"), $"DROP DATABASE IF EXISTS \"{name}\" WITH (FORCE)"); }
    public static async Task DropRoleAsync(string role) { Guard(role); NpgsqlConnection.ClearAllPools(); await ExecAsync(AdminDsn("postgres"), $"DROP ROLE IF EXISTS \"{role}\""); }
}

/// One real Mimamsa.Web process on the slice site with activation enabled.
sealed class Cp1Web : IAsyncDisposable
{
    public readonly List<string> Log = new();
    Process? _p;
    public string Base { get; private set; } = "";

    public static async Task<Cp1Web> StartAsync(Dictionary<string, string> env)
    {
        var w = new Cp1Web();
        var l = new System.Net.Sockets.TcpListener(IPAddress.Loopback, 0); l.Start(); int port = ((IPEndPoint)l.LocalEndpoint).Port; l.Stop();
        w.Base = $"http://127.0.0.1:{port}";
        var psi = ServiceFixture.ServiceStartInfo(Path.Combine(AppContext.BaseDirectory, "Mimamsa.Web.dll"), ServiceFixture.WebDir());
        psi.Environment["ASPNETCORE_URLS"] = w.Base;
        foreach (var (k, v) in env) psi.Environment[k] = v;
        w._p = Process.Start(psi)!;
        w._p.OutputDataReceived += (_, e) => { if (e.Data is not null) lock (w.Log) w.Log.Add(e.Data); };
        w._p.ErrorDataReceived += (_, e) => { if (e.Data is not null) lock (w.Log) w.Log.Add(e.Data); };
        w._p.BeginOutputReadLine(); w._p.BeginErrorReadLine();
        using var h = new HttpClient();
        for (int i = 0; i < 240; i++)
        {
            if (w._p.HasExited) throw new InvalidOperationException("service exited: " + string.Join("\n", w.Log));
            try { if ((await h.GetAsync(w.Base + "/health")).IsSuccessStatusCode) return w; } catch (HttpRequestException) { }
            await Task.Delay(250);
        }
        throw new TimeoutException("service did not become healthy");
    }

    public async Task<HttpClient> LoginAsync(string user)
    {
        var c = new HttpClient(new HttpClientHandler { UseCookies = true, CookieContainer = new CookieContainer(), AllowAutoRedirect = false }) { BaseAddress = new Uri(Base) };
        var r = await c.PostAsJsonAsync("/api/login", new { username = user, password = $"{user}-password-1" });
        r.EnsureSuccessStatusCode();
        return c;
    }

    public bool Logged(string s) { lock (Log) return Log.Any(l => l.Contains(s, StringComparison.Ordinal)); }

    public async ValueTask DisposeAsync()
    {
        try { _p?.Kill(true); _p?.WaitForExit(10_000); } catch { }
        await Task.CompletedTask;
    }
}

public class C16Cp1SliceTests
{
    static JsonObject Obj(string path) => JsonNode.Parse(File.ReadAllText(path))!.AsObject();
    static string Sha(string path) => Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path))).ToLowerInvariant();

    [Fact]
    public async Task C16Cp1VerticalSlice()
    {
        var ctxPath = Environment.GetEnvironmentVariable("MIMAMSA_CP1_CONTEXT");
        if (string.IsNullOrEmpty(ctxPath)) return;   // only the slice driver runs this journey
        var ctx = Obj(ctxPath);
        string S(string k) => (string)ctx[k]!;
        string site = S("site"), work = S("work"), g1 = S("g1"), g2 = S("g2");
        string docA = S("admitted_doc"), docB = S("held_doc"), docE = S("c16_only_doc"), legacy = S("legacy_doc");
        var seq = ctx["release_sequence"]!.AsObject().ToDictionary(kv => kv.Key, kv => (long)kv.Value!, StringComparer.Ordinal);
        var checks = new JsonObject();
        void Check(string name, bool ok, string? detail = null)
        {
            checks[name] = detail is null ? ok : new JsonObject { ["ok"] = ok, ["detail"] = detail };
            Assert.True(ok, name + (detail is null ? "" : ": " + detail));
        }
        var results = new JsonObject { ["acceptance_level"] = "FIXTURE (SG-5) CP-1 slice; closes no FG-* gate on real data", ["checks"] = checks };

        var r = Convert.ToHexString(RandomNumberGenerator.GetBytes(4)).ToLowerInvariant();
        string src = "c16cp1_src_" + r, app = "c16cp1_app_" + r, role = "c16cp1_krl_" + r;
        var webs = new List<Cp1Web>();
        ActivationEngine? eng = null;
        try
        {
            // ---------------------------------------------------------------- B03: migration on a CLONED disposable DB
            await Cp1Pg.CreateDbAsync(src);
            await using (var ds = NpgsqlDataSource.Create(Cp1Pg.OwnerDsn(src))) await TestPg.SeedSiteAsync(ds);
            await Cp1Pg.CreateDbAsync(app, template: src);
            await using var owner = NpgsqlDataSource.Create(Cp1Pg.OwnerDsn(app));
            List<KeyValuePair<string, string>> publicBefore;
            await using (var c = await owner.OpenConnectionAsync()) publicBefore = (await SchemaDump.DumpSchemasAsync(c, ["public"])).ToList();
            var mig = new SiteSchemaMigration(owner);
            var report = await mig.ForwardAsync();
            Check("b03_migration_applied_on_clone", await mig.StatusAsync() == "APPLIED" && report.Tables.All(t => t.OldDigest == t.NewDigest), $"{report.Tables.Count} tables copied and verified");
            await using (var c = await owner.OpenConnectionAsync())
                Check("b03_migration_public_unchanged", publicBefore.SequenceEqual(await SchemaDump.DumpSchemasAsync(c, ["public"])));
            results["migration"] = new JsonObject { ["version"] = report.Version, ["tables"] = report.Tables.Count, ["left_in_place"] = string.Join(",", report.LeftInPlace) };

            // ---------------------------------------------------------------- B03: restricted loader, both generations
            var pw = Convert.ToBase64String(RandomNumberGenerator.GetBytes(24));
            await using (var adm = NpgsqlDataSource.Create(Cp1Pg.AdminDsn(app))) await KnowledgeLoaderRole.EnsureAsync(adm, role, pw);
            await KnowledgeLoaderRole.HardenDatabaseAsync(owner, role);
            var loader = new KnowledgeRowLoader(owner, Cp1Pg.RoleDsn(app, role, pw)) { LoaderRole = role };
            var loads = new JsonObject();
            var componentResults = new JsonObject();
            var layout = new SiteLayout(site);
            var cat = new GenerationCatalog(layout);
            // ---------------------------------------------------------------- staging (Core owner of C16_VERIFIED.json):
            // B03 rows + graph through the restricted loader, B04 text store adoption and lexical index file checks
            foreach (var gid in new[] { g1, g2 })
            {
                Check($"not_installed_before_staging_{gid}", !cat.Installed().Contains(gid));
                var tlog = new List<string>();
                var rep = await GenerationStaging.VerifyAndStageAsync(layout, gid, loader, Path.Combine(work, $"verify-text-{r}-{gid}"), tlog.Add);
                Check($"staging_verified_and_marked_{gid}", rep.Ok && cat.Installed().Contains(gid), string.Join("; ", rep.Issues));
                Check($"b03_loader_rows_and_graph_{gid}", rep.Components["KNOWLEDGE_ROWS"] == "VERIFIED" && rep.Components["GRAPH"] == "VERIFIED");
                Check($"b04_text_store_adopted_{gid}", rep.TextStoreOrigin == "adopted" && rep.Components["TEXT_STORE"] == "VERIFIED", string.Join(" | ", tlog));
                Check($"b04_lexical_index_sha_and_quick_check_{gid}", rep.Components["LEXICAL_INDEX"] == "VERIFIED");
                Check($"no_vector_pack_{gid}", rep.Components["VECTOR_PACK"] == "MISSING" && rep.DeclaredServiceLevel == "DEGRADED_LEXICAL_ONLY");
                loads[gid] = new JsonObject { ["tables"] = new JsonArray(rep.LoadedTables.Select(t => (JsonNode)t).ToArray()) };
                if (gid == g2) foreach (var (k, v) in rep.Components) componentResults[k] = v;
            }
            results["loads"] = loads;
            results["component_results"] = componentResults;
            results["component_checks_not_run"] = "GRAPH_STRUCTURAL_RECHECK, SAMPLED_REBUILD_PARITY, SAMPLED_POSTINGS_REDERIVE, SAMPLED_QUERY_PARITY (UNCALIBRATED sizes; B04 .NET verifiers not built); GRAPH and KNOWLEDGE_ROWS verified by the loader's full re-derivation instead";

            // ---------------------------------------------------------------- B06: initialise on G1 (lexical-only: NO model)
            var reader = ActivationCli.Reader(layout, production: false);
            var snap = reader.Read();
            Check("b06_exclusion_reader_healthy_development_trust", snap.Healthy, snap.Health + " " + snap.Detail);
            layout.Initialise(g1, null, snap.Sequence!.Value);   // 2.1 K2: a lexical-only site has NO model
            Check("b06_no_model_installed", layout.ReadPointer("MODELS") is null && !Directory.Exists(layout.ModelsDir) && cat.IsLexicalOnly(g1) && cat.IsLexicalOnly(g2));
            Directory.CreateDirectory(Path.GetDirectoryName(layout.ChannelKeyPath)!);
            File.WriteAllBytes(layout.ChannelKeyPath, RandomNumberGenerator.GetBytes(32));
            var pipe = "mimamsa-cp1-" + r;
            var pg = new PgAdvisoryLock(Cp1Pg.OwnerDsn(app));
            var kdb = new KnowledgeActivationDatabase(() => pg.Connection, gid => seq[gid]);
            eng = new ActivationEngine(new ActivationEngineOptions
            {
                Site = layout, WriterId = "cp1-activator", Database = kdb, Exclusions = reader, ExternalLock = pg, Log = _ => { },
            });
            eng.AcquireLock();
            kdb.EnsureSchema(g1);
            if (eng.NeedsRecovery()) eng.Recover();
            Check("b06_initialised_on_g1", layout.ReadPointer("KNOWLEDGE") == g1 && kdb.KnowledgeSchema() == KnowledgeAllowlist.ActiveSchema(seq[g1]), kdb.KnowledgeSchema());

            Dictionary<string, string> WebEnv(string textDir) => new()
            {
                ["Mimamsa__Site"] = site, ["Mimamsa__Db"] = Cp1Pg.OwnerDsn(app, 8), ["Mimamsa__Test__Enabled"] = "true",
                ["Mimamsa__Test__Users__0"] = "reader:User:reader-password-1", ["Mimamsa__RestrictedRegister"] = S("register"),
                ["Mimamsa__Activation__Enabled"] = "true", ["Mimamsa__Activation__DevelopmentTrust"] = "true",
                ["Mimamsa__Activation__Pipe"] = pipe, ["Mimamsa__Activation__KeyFile"] = layout.ChannelKeyPath,
                ["Mimamsa__Text__Store"] = "disk", ["Mimamsa__Text__Dir"] = textDir, ["Mimamsa__Search__Engine"] = "memory",
                ["Mimamsa__Test__PauseDir"] = Path.Combine(work, "pause-" + r),   // test-only pause hook (C16-CP1-03)
            };
            async Task<Cp1Web> Web(string name) { var w = await Cp1Web.StartAsync(WebEnv(Path.Combine(work, $"web-text-{r}-{name}"))); webs.Add(w); return w; }
            static async Task<HttpStatusCode> St(HttpClient c, string url) => (await c.GetAsync(url)).StatusCode;

            var w1 = await Web("1");
            var c1 = await w1.LoginAsync("reader");
            Check("web_g1_serves_legacy", await St(c1, $"/api/documents/{legacy}") == HttpStatusCode.OK);
            Check("web_g1_does_not_have_admitted_copy", await St(c1, $"/api/documents/{docA}") == HttpStatusCode.NotFound);

            // ---------------------------------------------------------------- B06: ACTIVATE G2 (journal, channel, DB_APPLIED)
            eng.Options.Participant = new PipeParticipantLink(new ControlChannelOptions { PipeName = pipe, Secret = ControlChannelOptions.LoadSecret(layout.ChannelKeyPath) });
            var txn = eng.Transition("KNOWLEDGE", g2);
            Check("b06_activated_g2", layout.ReadPointer("KNOWLEDGE") == g2 && layout.ReadMarker() == SiteState.OPEN, txn);
            Check("b06_db_applied_views_on_kr_g2", kdb.KnowledgeSchema() == KnowledgeAllowlist.ActiveSchema(seq[g2]) && kdb.Views() == g2, kdb.KnowledgeSchema());
            await using (var c = await owner.OpenConnectionAsync())
            await using (var q = new NpgsqlCommand("SELECT count(*) FROM knowledge.document_identities", c))
                Check("b03_rows_visible_through_knowledge_views", (long)(await q.ExecuteScalarAsync())! == 3);
            // no in-process swap in this slice: the old process stops serving (fail closed) until it is restarted
            Check("web_old_process_fails_closed_after_switch", await St(c1, $"/api/documents/{legacy}") == HttpStatusCode.ServiceUnavailable);
            await w1.DisposeAsync();

            var w2 = await Web("2");
            Check("b04_web_process_adopted_shipped_text_store", w2.Logged("adopted shipped store") && !w2.Logged("built and published"));
            var c2 = await w2.LoginAsync("reader");
            var search = JsonNode.Parse(await c2.GetStringAsync("/api/search?q=" + Uri.EscapeDataString(S("admitted_query"))))!;
            var hits = search["passages"]!.AsArray().Select(p => (string)p!["doc_id"]!).ToHashSet();
            Check("web_g2_search_finds_admitted_copy", hits.Contains(docA), string.Join(",", hits));
            Check("degraded_lexical_only_no_semantic", (string?)search["run"]!["semantic"] == "not part of B1" && (string?)search["mode"] is "lexical" or "identifier",
                  $"{search["mode"]} / {search["run"]!["semantic"]}");
            Check("web_g2_admitted_text", await St(c2, $"/api/documents/{docA}/text") == HttpStatusCode.OK);
            Check("web_g2_admitted_citation", await St(c2, $"/api/documents/{docA}/citation?page=1") == HttpStatusCode.OK);
            var shaA = (string)JsonNode.Parse(await c2.GetStringAsync($"/api/documents/{docA}/text"))!["copy_sha256"]!;
            var cite = JsonNode.Parse(await c2.GetStringAsync($"/api/cite?doc={docA}&sha={shaA}&page=1"))!;
            Check("web_g2_admitted_permalink", (string?)cite["state"] == "CITED_COPY_ELIGIBLE", (string?)cite["state"]);
            Check("web_g2_held_copy_not_visible", await St(c2, $"/api/documents/{docB}") == HttpStatusCode.NotFound);
            Check("web_g2_c16_only_copy_not_visible", await St(c2, $"/api/documents/{Uri.EscapeDataString(docE)}") == HttpStatusCode.NotFound);
            Check("web_g2_legacy_visible", await St(c2, $"/api/documents/{legacy}") == HttpStatusCode.OK);
            var heldSearch = JsonNode.Parse(await c2.GetStringAsync("/api/search?q=" + Uri.EscapeDataString("Synthetic held writ petition")))!;
            Check("web_g2_search_never_returns_held_copy", heldSearch["passages"]!.AsArray().All(p => (string)p!["doc_id"]! != docB));

            // ---------------------------------------------------------------- C16-CP1-01: surfaces not behind the boundary are refused
            foreach (var url in new[] { "/api/graph/stats", "/api/graph/resolve?doc=" + legacy, "/api/reasoning/rule-gate", "/api/commander/domains",
                                        "/api/statutes", "/api/library", $"/api/documents/{legacy}/relations", "/api/studio/documents", "/api/studio/templates",
                                        "/api/studio/notes", $"/api/v2/documents/{legacy}/pdf-meta", "/api/admin/overview" })
            {
                var resp = await c2.GetAsync(url);
                var body = await resp.Content.ReadAsStringAsync();
                Check("refused_under_activation " + url.Split('?')[0], resp.StatusCode == HttpStatusCode.ServiceUnavailable
                      && body.Contains("not_available_under_activation") && !body.Contains(legacy) && !body.Contains(docA), $"{(int)resp.StatusCode} {body[..Math.Min(body.Length, 80)]}");
            }
            Check("route_inventory_startup_self_check", w2.Logged("route inventory complete"));

            // a statute with printed headings (sections surface) and its copy hash
            string statute = S("statute_doc");
            var secBefore = JsonNode.Parse(await c2.GetStringAsync($"/api/documents/{statute}/sections"))!;
            Check("statute_has_headings_before_withdrawal", secBefore["sections"] is JsonArray sa && sa.Count > 0);
            var statuteSha = (string)JsonNode.Parse(await c2.GetStringAsync($"/api/documents/{statute}/text"))!["copy_sha256"]!;
            var statutePage1 = (string)JsonNode.Parse(await c2.GetStringAsync($"/api/documents/{statute}/text"))!["pages"]![0]!["text"]!;
            var aPage1 = (string)JsonNode.Parse(await c2.GetStringAsync($"/api/documents/{docA}/text"))!["pages"]![0]!["text"]!;
            var statuteQuery = string.Join(" ", statutePage1.Split((char[]?)null, StringSplitOptions.RemoveEmptyEntries).Where(w => w.All(char.IsLetter) && w.Length > 3).Take(3));
            var statuteHits = JsonNode.Parse(await c2.GetStringAsync("/api/search?q=" + Uri.EscapeDataString(statuteQuery)))!["passages"]!.AsArray();
            Check("statute_found_by_search_before_withdrawal", statuteHits.Any(p => (string)p!["doc_id"]! == statute), statuteQuery);

            // ---------------------------------------------------------------- C16-CP1-03: requests PAUSED after their handler ran
            // (initial eligibility passed, page text enumerated, JSON serialised), then the withdrawal is accepted, then released
            var paused = new Dictionary<string, string>
            {
                ["p-text"] = $"/api/documents/{docA}/text", ["p-citation"] = $"/api/documents/{docA}/citation?page=1",
                ["p-cite"] = $"/api/cite?doc={docA}&sha={shaA}&page=1", ["p-doc"] = $"/api/documents/{docA}",
                ["p-search"] = "/api/search?q=" + Uri.EscapeDataString(S("admitted_query")),
                ["p-sections"] = $"/api/documents/{statute}/sections", ["p-statute-text"] = $"/api/documents/{statute}/text",
                ["p-statute-search"] = "/api/search?q=" + Uri.EscapeDataString(statuteQuery),
            };
            foreach (var (_, url) in paused) Check("before_withdrawal_200 " + url.Split('?')[0], await St(c2, url) == HttpStatusCode.OK);
            var pending = paused.ToDictionary(kv => kv.Key, kv =>
            {
                var m = new HttpRequestMessage(HttpMethod.Get, kv.Value);
                m.Headers.Add("X-Mimamsa-Test-Pause", kv.Key + "-" + r);
                return c2.SendAsync(m);
            });
            var pdir = Path.Combine(work, "pause-" + r);
            for (int i = 0; i < 600 && !paused.Keys.All(k => File.Exists(Path.Combine(pdir, $"{k}-{r}.paused"))); i++) await Task.Delay(100);
            Check("requests_paused_after_their_handler", paused.Keys.All(k => File.Exists(Path.Combine(pdir, $"{k}-{r}.paused"))));

            // ---------------------------------------------------------------- exclusion AFTER activation: A by doc id, the statute by copy hash
            var insp = new SiteInspector(layout, reader);
            ActivationEngine.AcceptExclusion(layout, insp, () =>
            {
                var psi = new ProcessStartInfo(S("python")) { RedirectStandardOutput = true, RedirectStandardError = true, UseShellExecute = false };
                foreach (var a in new[] { "-I", S("driver"), "exclude", "--site", site, "--sequence", (snap.Sequence!.Value + 1).ToString(), "--doc", docA, "--sha", statuteSha })
                    psi.ArgumentList.Add(a);
                using var p = Process.Start(psi)!;
                var o = p.StandardOutput.ReadToEnd() + p.StandardError.ReadToEnd();
                p.WaitForExit();
                if (p.ExitCode != 0) throw new InvalidOperationException("exclusion append failed: " + o);
            });
            Check("b06_exclusion_accepted_and_applied", reader.Read().Sequence == snap.Sequence + 1 && layout.ReadApplied()[g2] == snap.Sequence + 1);
            foreach (var k in paused.Keys) File.WriteAllText(Path.Combine(pdir, $"{k}-{r}.release"), "go");
            bool ContentFree(string body) => !body.Contains(docA) && !body.Contains(statute) && !body.Contains(aPage1[..Math.Min(30, aPage1.Length)])
                                             && !body.Contains(statutePage1[..Math.Min(30, statutePage1.Length)]) && !body.Contains(shaA) && !body.Contains(statuteSha);
            foreach (var (k, t) in pending)
            {
                var resp = await t;
                var body = await resp.Content.ReadAsStringAsync();
                Check("linearised_after_acceptance " + k, resp.StatusCode is HttpStatusCode.NotFound or HttpStatusCode.ServiceUnavailable && ContentFree(body),
                      $"{(int)resp.StatusCode} {body[..Math.Min(body.Length, 120)]}");
            }

            // ---------------------------------------------------------------- every boundary surface after acceptance, both exclusion kinds
            foreach (var (name, url) in new[] {
                ("doc_id document", $"/api/documents/{docA}"), ("doc_id text", $"/api/documents/{docA}/text"), ("doc_id sections", $"/api/documents/{docA}/sections"),
                ("doc_id citation", $"/api/documents/{docA}/citation?page=1"), ("doc_id permalink", $"/api/cite?doc={docA}&sha={shaA}&page=1"),
                ("copy_hash document", $"/api/documents/{statute}"), ("copy_hash text", $"/api/documents/{statute}/text"),
                ("copy_hash sections", $"/api/documents/{statute}/sections"), ("copy_hash citation", $"/api/documents/{statute}/citation?page=1"),
                ("copy_hash permalink", $"/api/cite?doc={statute}&sha={statuteSha}&page=1") })
            {
                var resp = await c2.GetAsync(url);
                var body = await resp.Content.ReadAsStringAsync();
                Check("boundary_withheld " + name, resp.StatusCode == HttpStatusCode.NotFound && ContentFree(body), $"{(int)resp.StatusCode}");
            }
            foreach (var q in new[] { S("admitted_query"), statuteQuery })
            {
                var resp = await c2.GetAsync("/api/search?q=" + Uri.EscapeDataString(q));
                var body = await resp.Content.ReadAsStringAsync();
                Check("boundary_search_filtered " + q, resp.StatusCode == HttpStatusCode.OK && ContentFree(body), $"{(int)resp.StatusCode}");
            }
            Check("boundary_leaves_other_copies", await St(c2, $"/api/documents/{legacy}") == HttpStatusCode.OK);

            // ---------------------------------------------------------------- ROLLBACK to G1
            var rtxn = eng.Transition("KNOWLEDGE", g1, "ROLLBACK");
            Check("b06_rollback_to_g1", layout.ReadPointer("KNOWLEDGE") == g1 && kdb.KnowledgeSchema() == KnowledgeAllowlist.ActiveSchema(seq[g1]) && kdb.Views() == g1, rtxn);
            Check("web_g2_process_fails_closed_after_rollback", await St(c2, $"/api/documents/{legacy}") == HttpStatusCode.ServiceUnavailable);
            await w2.DisposeAsync();
            var w3 = await Web("3");
            var c3 = await w3.LoginAsync("reader");
            Check("web_after_rollback_serves_g1", await St(c3, $"/api/documents/{legacy}") == HttpStatusCode.OK
                                                 && await St(c3, $"/api/documents/{docA}") == HttpStatusCode.NotFound);
            var j = eng.Inspector.Journal();
            results["journal_steps"] = new JsonArray(j.Entries.Select(e => (JsonNode)e.Step).ToArray());
            results["transactions"] = new JsonArray(txn, rtxn);
            results["publication_rows"] = kdb.PublicationCount();
            results["embedder_calls"] = 0;   // no embedder is configured in the slice; the degraded checks above prove lexical-only
            results["web_logs_text_store"] = new JsonArray(w2.Log.Where(l => l.Contains("text store:")).Select(l => (JsonNode)l).ToArray());
            File.WriteAllText(S("results"), results.ToJsonString(new System.Text.Json.JsonSerializerOptions { WriteIndented = true }));
        }
        finally
        {
            foreach (var w in webs) await w.DisposeAsync();
            try { eng?.ReleaseLock(); } catch { }
            eng?.Dispose();
            NpgsqlConnection.ClearAllPools();
            foreach (var db in new[] { app, src }) try { await Cp1Pg.DropDbAsync(db); } catch (Exception e) { Console.Error.WriteLine($"cp1 cleanup {db}: {e.GetType().Name}"); }
            try { await Cp1Pg.DropRoleAsync(role); } catch (Exception e) { Console.Error.WriteLine($"cp1 cleanup role: {e.GetType().Name}"); }
        }
    }
}
