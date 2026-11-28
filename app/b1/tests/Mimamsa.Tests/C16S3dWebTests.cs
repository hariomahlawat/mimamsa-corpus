// C16 Tranche B Stage 3 (S3-D): the web service under the activation journal, end to end, in a REAL Kestrel process
// over a copy of the SYN site (its two real generations), a disposable c16s3d_* database, a development-signed
// exclusion store and the real authenticated control channel. FIXTURE acceptance (SG-5): the generations' staging markers
// are the B06 harness's unbound simulation markers; nothing here closes a gate on real data.
//
//   swap       a target that fails to load leaves the old generation serving with nothing journaled; a real
//              activation swaps IN PROCESS while readers run (no mixed generation in any response; an in-flight request
//              paused across the swap is answered wholly from its own generation); the old generation is released when
//              that request ends; memory is measured through /api/diag/memory; a rollback swap.
//   boundary   every surface CP-1 refused, with a document-id exclusion (judgment syn-j-allow) and a copy-hash exclusion
//              (statute syn-s-act's copy) accepted while requests on each route are PAUSED after their handler (or, for
//              Range delivery, after the first slice); every paused response is withheld or content-free, Range stops
//              after the slice already handed over (bounded drain); afterwards every surface leaves both copies out.
//   facets     search totals and facets after the exclusion are counted over the surviving results only.
using System.Collections.Concurrent;
using System.Net;
using System.Net.Http.Json;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json.Nodes;
using Mimamsa.Core.Activation;
using Mimamsa.Core.Generation;
using Mimamsa.Tests.Activation;
using Npgsql;

namespace Mimamsa.Tests;

/// Disposable S3-D databases: prefix c16s3d_ only (guarded); pool size 10 or less.
static class S3dPg
{
    static string AppDsn => Environment.GetEnvironmentVariable("MIMAMSA_TEST_DB") ?? throw new InvalidOperationException("MIMAMSA_TEST_DB is required");
    static string AdminBase => Environment.GetEnvironmentVariable("MIMAMSA_TEST_PG_ADMIN") is { Length: > 0 } a ? a : AppDsn;
    public static string OwnerDsn(string db) => new NpgsqlConnectionStringBuilder(AppDsn) { Database = db, MaxPoolSize = 10 }.ConnectionString;
    static string AdminDsn(string db) => new NpgsqlConnectionStringBuilder(AdminBase) { Database = db, MaxPoolSize = 2 }.ConnectionString;
    static void Guard(string name)
    {
        if (!name.StartsWith("c16s3d_", StringComparison.Ordinal) || name.Any(ch => !(char.IsAsciiLetterLower(ch) || char.IsAsciiDigit(ch) || ch == '_')))
            throw new InvalidOperationException("only disposable c16s3d_ databases may be created or dropped");
    }
    static async Task ExecAsync(string dsn, string sql)
    {
        await using var c = new NpgsqlConnection(dsn);
        await c.OpenAsync();
        await using var cmd = new NpgsqlCommand(sql, c);
        await cmd.ExecuteNonQueryAsync();
    }
    public static async Task CreateAsync(string name)
    {
        Guard(name);
        var owner = new NpgsqlConnectionStringBuilder(AppDsn).Username!;
        await ExecAsync(AdminDsn("postgres"), $"CREATE DATABASE \"{name}\" OWNER \"{owner}\"");
    }
    public static async Task DropAsync(string name)
    {
        Guard(name);
        NpgsqlConnection.ClearAllPools();
        await ExecAsync(AdminDsn("postgres"), $"DROP DATABASE IF EXISTS \"{name}\" WITH (FORCE)");
    }
}

public class C16S3dWebTests
{
    const string G1 = "R13-syn-fixture-20261125-00000001", G2 = "R13-syn-fixture-20261125-00000002";
    const string DocA = "syn-j-allow", Statute = "syn-s-act";

    static async Task<(HttpClient c, string csrf)> Login(Cp1Web w, string user)
    {
        var c = new HttpClient(new HttpClientHandler { UseCookies = true, CookieContainer = new CookieContainer(), AllowAutoRedirect = false }) { BaseAddress = new Uri(w.Base) };
        var r = await c.PostAsJsonAsync("/api/login", new { username = user, password = $"{user}-password-1" });
        r.EnsureSuccessStatusCode();
        return (c, (string)JsonNode.Parse(await r.Content.ReadAsStringAsync())!["csrf"]!);
    }

    static async Task<HttpResponseMessage> Post(HttpClient c, string csrf, string url, object body)
    {
        var m = new HttpRequestMessage(HttpMethod.Post, url) { Content = JsonContent.Create(body) };
        m.Headers.Add("X-CSRF-Token", csrf);
        return await c.SendAsync(m);
    }

    static string Gen(HttpResponseMessage r) => r.Headers.TryGetValues("X-Mimamsa-Generation", out var v) ? v.Single() : "";

    [Fact]
    public async Task InProcessSwapAndTheBoundaryOnEverySurface()
    {
        var r = Convert.ToHexString(RandomNumberGenerator.GetBytes(4)).ToLowerInvariant();
        var db = "c16s3d_web_" + r;
        var site = Syn.CopySite();
        var work = Path.Combine(TestDirs.Base, "s3d-web-" + r);
        Directory.CreateDirectory(work);
        Cp1Web? web = null;
        ActivationEngine? eng = null;
        var evidence = new JsonObject { ["acceptance_level"] = "FIXTURE (SG-5): SYN site copy, simulation-unbound staging markers, development keys; no gate closed on real data" };
        var checks = new JsonObject();
        void Check(string name, bool ok, string? detail = null)
        {
            checks[name] = detail is null ? ok : new JsonObject { ["ok"] = ok, ["detail"] = detail };
            Assert.True(ok, name + (detail is null ? "" : ": " + detail));
        }
        try
        {
            await S3dPg.CreateAsync(db);
            // ------------------------------------------------------------ activation site on the copy: G1 active, lexical-only
            var layout = new SiteLayout(site);
            Directory.CreateDirectory(layout.StateDir);
            File.WriteAllText(Path.Combine(layout.StateDir, StagingMarker.SimulationFlag), "S3-D web journey (B06 harness markers)");
            var cat = new GenerationCatalog(layout);
            cat.StageGeneration(G1, 0, lexicalOnly: true);
            cat.StageGeneration(G2, 0, lexicalOnly: true);
            var key = new DevRegisterKey();
            Directory.CreateDirectory(Path.GetDirectoryName(layout.TrustListPath)!);
            File.WriteAllBytes(layout.TrustListPath, DevRegisterKey.TrustList((key, ["register"], false)));
            Directory.CreateDirectory(layout.ExclusionsDir);
            var store = new DevExclusionStore(layout.ExclusionsDir, key);
            layout.Initialise(G1, null, store.Append([]));
            var fdb = new FileActivationDatabase(layout.FileDbPath);
            fdb.Initialise(G1);
            Directory.CreateDirectory(Path.GetDirectoryName(layout.ChannelKeyPath)!);
            File.WriteAllBytes(layout.ChannelKeyPath, RandomNumberGenerator.GetBytes(32));
            var reader = ActivationCli.Reader(layout, production: false);
            var pipe = "mimamsa-s3d-" + r;

            var pauseDir = Path.Combine(work, "pause");
            web = await Cp1Web.StartAsync(new Dictionary<string, string>
            {
                ["Mimamsa__Site"] = site, ["Mimamsa__Db"] = S3dPg.OwnerDsn(db), ["Mimamsa__Test__Enabled"] = "true",
                ["Mimamsa__Test__Users__0"] = "reader:User:reader-password-1", ["Mimamsa__Test__Users__1"] = "admin:Admin:admin-password-1",
                ["Mimamsa__RestrictedRegister"] = ServiceFixture.RegisterPath, ["Mimamsa__Login__ThrottlePerSource"] = "1000",
                ["Mimamsa__Activation__Enabled"] = "true", ["Mimamsa__Activation__DevelopmentTrust"] = "true",
                ["Mimamsa__Activation__Pipe"] = pipe, ["Mimamsa__Activation__KeyFile"] = layout.ChannelKeyPath,
                ["Mimamsa__Text__Store"] = "disk", ["Mimamsa__Text__Dir"] = Path.Combine(work, "text"),
                ["Mimamsa__Search__Engine"] = "disk", ["Mimamsa__Search__IndexDir"] = Path.Combine(work, "index"),
                ["Mimamsa__Test__PauseDir"] = pauseDir, ["Mimamsa__Diagnostics__Enabled"] = "true",
                ["Mimamsa__Delivery__MaxRange"] = "4096", ["Mimamsa__Delivery__Slice"] = "256",
            });
            // the writer lock is taken once the service is up (its heartbeat goes stale after 30 s)
            eng = new ActivationEngine(new ActivationEngineOptions { Site = layout, WriterId = "s3d-web", Database = fdb, Exclusions = reader, Production = false, Log = _ => { } });
            eng.AcquireLock();
            if (eng.NeedsRecovery()) eng.Recover();
            eng.Options.Participant = new PipeParticipantLink(new ControlChannelOptions { PipeName = pipe, Secret = ControlChannelOptions.LoadSecret(layout.ChannelKeyPath) });
            var (rc, rcsrf) = await Login(web, "reader");
            var (ac, acsrf) = await Login(web, "admin");
            var rel = new Dictionary<string, string>
            {
                [G1] = (string)JsonNode.Parse(File.ReadAllText(Path.Combine(site, "generations", G1, "release", "RELEASE.json")))!["release_id"]!,
                [G2] = (string)JsonNode.Parse(File.ReadAllText(Path.Combine(site, "generations", G2, "release", "RELEASE.json")))!["release_id"]!,
            };
            var s0 = await rc.GetAsync("/api/session");
            Check("serves_g1_at_start", s0.StatusCode == HttpStatusCode.OK && Gen(s0) == G1);
            async Task<JsonObject> Diag() => JsonNode.Parse(await (await rc.GetAsync("/api/diag/memory?gc=1")).Content.ReadAsStringAsync())!.AsObject();

            // ------------------------------------------------------------ swap 1: the target fails to load -> old keeps serving
            var gj = Path.Combine(site, "generations", G2, "generation.json");
            File.Move(gj, gj + ".hidden");
            int journalBefore = eng.Inspector.Journal().Entries.Count;
            var failing = Task.Run(() => Assert.Throws<ActivationRefused>(() => eng.Transition("KNOWLEDGE", G2)));
            var during = new List<HttpStatusCode>();
            while (!failing.IsCompleted) { during.Add((await rc.GetAsync("/api/library")).StatusCode); }
            var refusal = await failing;
            File.Move(gj + ".hidden", gj);
            Check("load_failure_refused_before_begin", refusal.Code == "PARTICIPANT_NOT_PREPARED" && eng.Inspector.Journal().Entries.Count == journalBefore
                  && layout.ReadPointer("KNOWLEDGE") == G1, refusal.Code);
            var afterFail = await rc.GetAsync("/api/library");
            Check("load_failure_old_generation_kept_serving", during.All(s => s == HttpStatusCode.OK) && afterFail.StatusCode == HttpStatusCode.OK && Gen(afterFail) == G1,
                  $"{during.Count} requests during the failed load: {string.Join(",", during.Distinct())}");

            // ------------------------------------------------------------ swap 2: real activation with readers and an in-flight request
            var mem1 = await Diag();
            var inflight = new HttpRequestMessage(HttpMethod.Get, "/api/library");
            inflight.Headers.Add("X-Mimamsa-Test-Pause", "inflight-" + r);
            var inflightTask = rc.SendAsync(inflight);
            for (int i = 0; i < 300 && !File.Exists(Path.Combine(pauseDir, $"inflight-{r}.paused")); i++) await Task.Delay(50);
            Check("inflight_request_paused_on_g1", File.Exists(Path.Combine(pauseDir, $"inflight-{r}.paused")));
            var stop = new CancellationTokenSource();
            var observations = new ConcurrentBag<(string url, HttpStatusCode status, string header, string? bodyRelease, string? state)>();
            var loops = Enumerable.Range(0, 4).Select(i => Task.Run(async () =>
            {
                var urls = new[] { "/api/session", "/api/library", "/api/search?q=decision", "/api/statutes" };
                int k = i;
                while (!stop.IsCancellationRequested)
                {
                    var url = urls[k++ % urls.Length];
                    var resp = await rc.GetAsync(url);
                    var body = JsonNode.Parse(await resp.Content.ReadAsStringAsync());
                    string? release = url switch
                    {
                        "/api/session" => (string?)body?["release"]?["release_id"],
                        "/api/library" => (string?)body?["release"]?["release_id"],
                        "/api/search?q=decision" => (string?)body?["run"]?["release_id"],
                        _ => null,
                    };
                    observations.Add((url, resp.StatusCode, Gen(resp), release, (string?)body?["state"]));
                }
            })).ToList();
            await Task.Delay(300);
            var txn = await Task.Run(() => eng.Transition("KNOWLEDGE", G2));
            var afterSwap = await rc.GetAsync("/api/session");
            Check("swapped_in_process_to_g2", afterSwap.StatusCode == HttpStatusCode.OK && Gen(afterSwap) == G2
                  && web.Logged("target loaded and verified beside the serving generation"), txn);
            await Task.Delay(300);
            stop.Cancel();
            await Task.WhenAll(loops);
            var mem2 = await Diag();   // G1 still resident: the paused request holds it
            Check("old_generation_kept_while_inflight_request_runs", !web.Logged("previous generation released"));
            File.WriteAllText(Path.Combine(pauseDir, $"inflight-{r}.release"), "go");
            var inflightResp = await inflightTask;
            var inflightBody = JsonNode.Parse(await inflightResp.Content.ReadAsStringAsync())!;
            Check("inflight_request_answered_wholly_from_g1", inflightResp.StatusCode == HttpStatusCode.OK && Gen(inflightResp) == G1
                  && (string?)inflightBody["release"]!["release_id"] == rel[G1], $"{(int)inflightResp.StatusCode} {Gen(inflightResp)}");
            for (int i = 0; i < 100 && !web.Logged("previous generation released"); i++) await Task.Delay(50);
            Check("old_generation_released_after_last_pin", web.Logged("previous generation released"));
            var mem3 = await Diag();
            var obs = observations.ToList();
            var ok = obs.Where(o => o.status == HttpStatusCode.OK).ToList();
            var mixed = ok.Where(o => o.bodyRelease is not null && rel[o.header] != o.bodyRelease).ToList();
            Check("concurrent_readers_never_mixed", obs.Count > 20 && mixed.Count == 0 && ok.Any(o => o.header == G1) && ok.Any(o => o.header == G2)
                  && obs.All(o => o.status == HttpStatusCode.OK || (o.status == HttpStatusCode.ServiceUnavailable && o.state == "activation_not_serving")),
                  $"{obs.Count} responses, {ok.Count} ok, {mixed.Count} mixed, 503 {obs.Count(o => o.status == HttpStatusCode.ServiceUnavailable)}");
            evidence["swap"] = new JsonObject
            {
                ["requests_during_failed_load"] = during.Count, ["concurrent_responses"] = obs.Count, ["ok"] = ok.Count,
                ["ok_g1"] = ok.Count(o => o.header == G1), ["ok_g2"] = ok.Count(o => o.header == G2),
                ["not_serving_503_during_switch"] = obs.Count(o => o.status == HttpStatusCode.ServiceUnavailable), ["mixed"] = mixed.Count,
                ["memory_mb"] = new JsonObject
                {
                    ["engines"] = "disk text store + disk index (required in activation mode)",
                    ["one_resident_before_swap"] = mem1.DeepClone(), ["two_resident_inflight_pinned"] = mem2.DeepClone(), ["one_resident_after_release"] = mem3.DeepClone(),
                },
            };

            // ------------------------------------------------------------ boundary: baseline on G2
            var aText = JsonNode.Parse(await rc.GetStringAsync($"/api/documents/{DocA}/text"))!;
            var sText = JsonNode.Parse(await rc.GetStringAsync($"/api/documents/{Statute}/text"))!;
            string shaA = (string)aText["copy_sha256"]!, shaS = (string)sText["copy_sha256"]!;
            var shaAr1 = (string)Syn.Map["j_allow_r1_copy"]!;
            bool ContentFree(string body) => !body.Contains(DocA) && !body.Contains(Statute) && !body.Contains(shaA) && !body.Contains(shaS) && !body.Contains(shaAr1);
            var section = (string?)JsonNode.Parse(await rc.GetStringAsync($"/api/documents/{Statute}/sections"))!["sections"]?.AsArray().FirstOrDefault()?["number"] ?? "1";
            var nodeA = (string)JsonNode.Parse(await rc.GetStringAsync($"/api/graph/resolve?doc={DocA}"))!["node_id"]!;
            var domain = (string)JsonNode.Parse(await rc.GetStringAsync("/api/commander/domains"))!["domains"]![0]!["id"]!;
            // a path that ends at A's node: from one of its neighbours (else from the statute's instrument node)
            var nodeA0 = JsonNode.Parse(await rc.GetStringAsync($"/api/graph/node?id={Uri.EscapeDataString(nodeA)}"))!;
            var pathFrom = nodeA0["edges"]!.AsArray().Select(e => (string?)e!["from"]!["id"] == nodeA ? (string?)e["to"]!["id"] : (string?)e["from"]!["id"]).FirstOrDefault()
                           ?? (string)JsonNode.Parse(await rc.GetStringAsync($"/api/graph/resolve?doc={Statute}"))!["node_id"]!;
            var pathUrl = $"/api/graph/path?from={Uri.EscapeDataString(pathFrom)}&to={Uri.EscapeDataString(nodeA)}";
            var library0 = JsonNode.Parse(await rc.GetStringAsync("/api/library"))!;
            var overview0 = JsonNode.Parse(await ac.GetStringAsync("/api/admin/overview"))!;
            var graph0 = JsonNode.Parse(await rc.GetStringAsync("/api/graph/stats"))!;
            var statutes0 = await rc.GetStringAsync("/api/statutes");
            Check("baseline_statutes_list_the_statute", statutes0.Contains(Statute));
            // a Studio working document and a note citing both copies
            var sd = JsonNode.Parse(await (await Post(rc, rcsrf, "/api/studio/documents", new { title = "S3-D brief", template = "blank" })).Content.ReadAsStringAsync())!;
            var sid = (string)sd["id"]!;
            var saved = await Post(rc, rcsrf, $"/api/studio/documents/{sid}/save", new
            {
                base_version = (int)sd["version"]!, title = "S3-D brief", state = "draft",
                blocks = new object[]
                {
                    new { type = "text", origin = "user", text = "Working notes." },
                    new { type = "citation", doc_id = DocA, copy = shaA[..12], page = 1 },
                    new { type = "citation", doc_id = Statute, copy = shaS[..12], page = 1 },
                },
            });
            Check("baseline_studio_document_saved", saved.StatusCode == HttpStatusCode.OK, $"{(int)saved.StatusCode}");
            Check("baseline_studio_note_saved", (await Post(rc, rcsrf, "/api/studio/notes", new { text = "see the judgment", ref_doc = DocA, ref_copy = shaA[..12], ref_page = 1 })).StatusCode == HttpStatusCode.Created);
            var studio0 = JsonNode.Parse(await rc.GetStringAsync($"/api/studio/documents/{sid}"))!;
            Check("baseline_studio_citations_available", studio0["blocks"]!.AsArray().Where(b => (string?)b!["type"] == "citation").All(b => (bool?)b!["available"] == true && b["title"] is not null));
            var meta = JsonNode.Parse(await rc.GetStringAsync($"/api/v2/documents/{DocA}/pdf-meta"))!;
            long lenA = (long)meta["length"]!;
            int want = (int)Math.Min(lenA, 4096);
            Check("baseline_range_has_several_slices", want > 512, $"copy length {lenA}");
            async Task<(HttpStatusCode status, long declared, long got)> Range(HttpClient c, string? pause)
            {
                var m = new HttpRequestMessage(HttpMethod.Get, $"/api/v2/documents/{DocA}/copies/{shaA}/range");
                m.Headers.Range = new System.Net.Http.Headers.RangeHeaderValue(0, want - 1);
                if (pause is not null) m.Headers.Add("X-Mimamsa-Test-Pause", pause);
                using var resp = await c.SendAsync(m, HttpCompletionOption.ResponseHeadersRead);
                long got = 0;
                try
                {
                    await using var st = await resp.Content.ReadAsStreamAsync();
                    var buf = new byte[1024];
                    int n;
                    while ((n = await st.ReadAsync(buf)) > 0) got += n;
                }
                catch (Exception e) when (e is IOException or HttpRequestException) { }
                return (resp.StatusCode, resp.Content.Headers.ContentLength ?? -1, got);
            }
            var range0 = await Range(rc, null);
            Check("baseline_range_206_complete", range0.status == HttpStatusCode.PartialContent && range0.got == want, $"{range0.status} {range0.got}/{want}");
            var search0 = JsonNode.Parse(await rc.GetStringAsync("/api/search?q=" + Uri.EscapeDataString("decision") + "&page_size=50"))!;

            // ------------------------------------------------------------ paused requests on every newly enabled route
            var paused = new Dictionary<string, (HttpClient c, string url, bool touches)>
            {
                ["graph-stats"] = (rc, "/api/graph/stats", true),
                ["graph-resolve"] = (rc, $"/api/graph/resolve?doc={DocA}", true),
                ["graph-node"] = (rc, $"/api/graph/node?id={Uri.EscapeDataString(nodeA)}", true),
                ["graph-path"] = (rc, pathUrl, true),
                ["reasoning-assess"] = (rc, $"/api/reasoning/assess?kind=temporal&doc={Statute}&section={Uri.EscapeDataString(section)}", true),
                ["reasoning-rule-gate"] = (rc, "/api/reasoning/rule-gate", false),
                ["commander-domains"] = (rc, "/api/commander/domains", false),
                ["commander-domain"] = (rc, $"/api/commander/domains/{domain}", false),
                ["statutes"] = (rc, "/api/statutes", true),
                ["library"] = (rc, "/api/library", true),
                ["relations"] = (rc, $"/api/documents/{Statute}/relations", true),
                ["studio-document"] = (rc, $"/api/studio/documents/{sid}", true),
                ["studio-versions"] = (rc, $"/api/studio/documents/{sid}/versions", false),
                ["studio-export"] = (rc, $"/api/studio/documents/{sid}/export?format=md", true),
                ["studio-documents"] = (rc, "/api/studio/documents", false),
                ["studio-notes"] = (rc, "/api/studio/notes", true),
                ["studio-templates"] = (rc, "/api/studio/templates", false),
                ["pdf-meta"] = (rc, $"/api/v2/documents/{DocA}/pdf-meta", true),
                ["admin-overview"] = (ac, "/api/admin/overview", true),
                ["admin-withdraw-scope"] = (ac, $"/api/admin/withdraw-scope?doc_id={DocA}", true),
                ["admin-audit"] = (ac, "/api/admin/audit", false),
                ["search"] = (rc, "/api/search?q=decision", true),
            };
            foreach (var (name, (c, url, _)) in paused)
            {
                var resp = await c.GetAsync(url);
                Check("before_exclusion_200 " + name, resp.StatusCode == HttpStatusCode.OK, $"{(int)resp.StatusCode} {url}");
            }
            var pending = paused.ToDictionary(kv => kv.Key, kv =>
            {
                var m = new HttpRequestMessage(HttpMethod.Get, kv.Value.url);
                m.Headers.Add("X-Mimamsa-Test-Pause", $"p-{kv.Key}-{r}");
                return kv.Value.c.SendAsync(m);
            });
            var rangePaused = Range(rc, $"p-range-{r}");
            var tokens = paused.Keys.Select(k => $"p-{k}-{r}").Append($"p-range-{r}").ToList();
            for (int i = 0; i < 600 && !tokens.All(t => File.Exists(Path.Combine(pauseDir, t + ".paused"))); i++) await Task.Delay(50);
            Check("requests_paused_after_their_handler_or_first_slice", tokens.All(t => File.Exists(Path.Combine(pauseDir, t + ".paused"))),
                  string.Join(",", tokens.Where(t => !File.Exists(Path.Combine(pauseDir, t + ".paused")))));

            // ------------------------------------------------------------ the signed exclusion: doc id A, copy hash of the statute
            var insp = new SiteInspector(layout, reader);
            long seqBefore = reader.Read().Sequence!.Value;
            ActivationEngine.AcceptExclusion(layout, insp, () => store.Append([DocA], withdrawnCopyShas: [shaS]));
            Check("exclusion_accepted_and_applied", reader.Read().Sequence == seqBefore + 1 && layout.ReadApplied()[G2] == seqBefore + 1);
            foreach (var t in tokens) File.WriteAllText(Path.Combine(pauseDir, t + ".release"), "go");
            foreach (var (name, task) in pending)
            {
                var resp = await task;
                var body = await resp.Content.ReadAsStringAsync();
                bool withheld = resp.StatusCode is HttpStatusCode.NotFound or HttpStatusCode.ServiceUnavailable;
                Check("linearised_after_acceptance " + name, ContentFree(body) && (!paused[name].touches || withheld), $"{(int)resp.StatusCode} {body[..Math.Min(body.Length, 100)]}");
            }
            var rangeResult = await rangePaused;
            Check("linearised_after_acceptance range (bounded drain)", rangeResult.status == HttpStatusCode.PartialContent && rangeResult.declared == want
                  && rangeResult.got < want && rangeResult.got <= 256, $"{rangeResult.got} of {want} bytes before the reset; slice 256");

            // ------------------------------------------------------------ every surface after acceptance, both exclusion kinds
            foreach (var (name, url, status) in new[]
            {
                ("doc_id graph-resolve", $"/api/graph/resolve?doc={DocA}", HttpStatusCode.NotFound),
                ("doc_id graph-node", $"/api/graph/node?id={Uri.EscapeDataString(nodeA)}", HttpStatusCode.NotFound),
                ("copy_hash reasoning-assess", $"/api/reasoning/assess?kind=temporal&doc={Statute}&section={Uri.EscapeDataString(section)}", HttpStatusCode.NotFound),
                ("copy_hash relations", $"/api/documents/{Statute}/relations", HttpStatusCode.NotFound),
                ("doc_id pdf-meta", $"/api/v2/documents/{DocA}/pdf-meta", HttpStatusCode.NotFound),
                ("copy_hash pdf-meta", $"/api/v2/documents/{Statute}/pdf-meta", HttpStatusCode.NotFound),
                ("doc_id range", $"/api/v2/documents/{DocA}/copies/{shaA}/range", HttpStatusCode.NotFound),
                ("graph-stats", "/api/graph/stats", HttpStatusCode.OK), ("graph-path", pathUrl, HttpStatusCode.OK),
                ("statutes", "/api/statutes", HttpStatusCode.OK), ("library", "/api/library", HttpStatusCode.OK),
                ("commander-domain", $"/api/commander/domains/{domain}", HttpStatusCode.OK), ("rule-gate", "/api/reasoning/rule-gate", HttpStatusCode.OK),
                ("studio-export", $"/api/studio/documents/{sid}/export?format=md", HttpStatusCode.OK), ("studio-notes", "/api/studio/notes", HttpStatusCode.OK),
            })
            {
                var m = new HttpRequestMessage(HttpMethod.Get, url);
                if (name == "doc_id range") m.Headers.Range = new System.Net.Http.Headers.RangeHeaderValue(0, 99);
                var resp = await rc.SendAsync(m);
                var body = await resp.Content.ReadAsStringAsync();
                Check("after_acceptance " + name, resp.StatusCode == status && ContentFree(body), $"{(int)resp.StatusCode} {body[..Math.Min(body.Length, 100)]}");
            }
            // counts never include the excluded copies (library, admin overview, graph statistics)
            var library1 = JsonNode.Parse(await rc.GetStringAsync("/api/library"))!;
            Check("library_count_excludes_both", (int)library1["documents"]! == (int)library0["documents"]! - 2, $"{library0["documents"]} -> {library1["documents"]}");
            var ov1 = await ac.GetAsync("/api/admin/overview");
            var ov1Body = await ov1.Content.ReadAsStringAsync();
            Check("admin_overview_counts_exclude_both", ov1.StatusCode == HttpStatusCode.OK && ContentFree(ov1Body)
                  && (int)JsonNode.Parse(ov1Body)!["verified"]!["documents"]! == (int)overview0["verified"]!["documents"]! - 2);
            var graph1 = JsonNode.Parse(await rc.GetStringAsync("/api/graph/stats"))!;
            Check("graph_stats_do_not_count_excluded", (int)graph1["nodes"]! < (int)graph0["nodes"]! && (int)graph1["edges"]! <= (int)graph0["edges"]!, $"{graph0["nodes"]} -> {graph1["nodes"]}");
            // Studio: the content-free C15 form for both citations; the export and note carry no source-derived text
            var studio1 = JsonNode.Parse(await rc.GetStringAsync($"/api/studio/documents/{sid}"))!;
            var cites = studio1["blocks"]!.AsArray().Where(b => (string?)b!["type"] == "citation").ToList();
            Check("studio_citations_show_source_no_longer_available", cites.Count == 2 && cites.All(b => (bool?)b!["available"] == false
                  && (string?)b["notice"] == Mimamsa.Web.Api.SourceUnavailable && b["title"] is null && b["citation"] is null && b["permalink"] is null));
            var export1 = await rc.GetStringAsync($"/api/studio/documents/{sid}/export?format=html");
            Check("studio_export_content_free", export1.Contains(System.Net.WebUtility.HtmlEncode(Mimamsa.Web.Api.SourceUnavailable)) && ContentFree(export1));
            var notes1 = JsonNode.Parse(await rc.GetStringAsync("/api/studio/notes"))!["notes"]!.AsArray();
            Check("studio_note_reference_unavailable", notes1.All(n => n!["reference"] is null || (bool?)n["reference"]!["available"] == false));
            // admin: scope and reinstatement name nothing about an excluded copy; an audit row naming it loses its object
            Check("admin_withdraw_scope_excluded", (await ac.GetAsync($"/api/admin/withdraw-scope?doc_id={DocA}")).StatusCode == HttpStatusCode.NotFound);
            var wd = await Post(ac, acsrf, "/api/admin/withdraw", new { doc_id = DocA, reason = "S3-D local withdrawal after the signed exclusion" });
            Check("admin_local_withdrawal_still_possible", wd.StatusCode == HttpStatusCode.OK, $"{(int)wd.StatusCode}");
            var audit = await ac.GetAsync("/api/admin/audit");
            var auditBody = await audit.Content.ReadAsStringAsync();
            Check("admin_audit_row_of_excluded_copy_redacted", audit.StatusCode == HttpStatusCode.OK && ContentFree(auditBody)
                  && JsonNode.Parse(auditBody)!["rows"]!.AsArray().Any(x => (string?)x!["action"] == "withdraw" && x["object"] is null));
            var rein = await Post(ac, acsrf, "/api/admin/reinstate", new { doc_id = DocA, reason = "S3-D reinstatement attempt" });
            var reinBody = await rein.Content.ReadAsStringAsync();
            Check("admin_reinstate_cannot_override_signed_exclusion", rein.StatusCode == HttpStatusCode.NotFound && ContentFree(reinBody), $"{(int)rein.StatusCode}");
            // facets and totals are counted over the surviving results only
            var search1 = JsonNode.Parse(await rc.GetStringAsync("/api/search?q=" + Uri.EscapeDataString("decision") + "&page_size=50"))!;
            int Facet(JsonNode s, string facet, string value) => s["facets"]?[facet]?.AsArray().Where(v => (string?)v!["value"] == value).Select(v => (int)v!["count"]!).FirstOrDefault() ?? 0;
            var hitDocs0 = search0["documents"]!.AsObject().Select(kv => kv.Key).ToHashSet();
            var hitDocs1 = search1["documents"]!.AsObject().Select(kv => kv.Key).ToHashSet();
            int removed = new[] { DocA, Statute }.Count(hitDocs0.Contains);
            Check("search_totals_recounted", (int)search1["total_documents"]! == (int)search0["total_documents"]! - removed && !hitDocs1.Contains(DocA) && !hitDocs1.Contains(Statute)
                  && ContentFree(search1.ToJsonString()), $"{search0["total_documents"]} -> {search1["total_documents"]} (removed {removed})");
            var facetTypes = search0["facets"]!["type"]!.AsArray().Select(v => (string)v!["value"]!).ToList();
            var typeOf = search0["documents"]!.AsObject().ToDictionary(kv => kv.Key, kv => (string?)kv.Value!["type"]);
            Check("search_facets_recounted_exactly", facetTypes.All(t => Facet(search1, "type", t) == Facet(search0, "type", t)
                  - new[] { DocA, Statute }.Count(d => hitDocs0.Contains(d) && typeOf[d] == t)) && search1["facets"]!.AsObject().Count == 4,
                  string.Join(";", facetTypes.Select(t => $"{t}:{Facet(search0, "type", t)}->{Facet(search1, "type", t)}")));
            evidence["boundary"] = new JsonObject
            {
                ["doc_id_exclusion"] = DocA, ["copy_hash_exclusion"] = $"{Statute} current copy", ["paused_routes"] = paused.Count + 1,
                ["range_bytes_after_acceptance"] = rangeResult.got, ["range_requested"] = want, ["slice"] = 256,
                ["library_documents"] = $"{library0["documents"]} -> {library1["documents"]}", ["search_total_documents"] = $"{search0["total_documents"]} -> {search1["total_documents"]}",
            };

            // ------------------------------------------------------------ swap 3: rollback to G1 in process; the exclusion holds there too
            var g1Statute = GenerationStore.Load(site, generationId: G1).Documents.GetValueOrDefault(Statute)?.CopySha;
            var rtxn = await Task.Run(() => eng.Transition("KNOWLEDGE", G1, "ROLLBACK"));
            var rb = await rc.GetAsync("/api/session");
            Check("rollback_swapped_in_process_to_g1", rb.StatusCode == HttpStatusCode.OK && Gen(rb) == G1, rtxn);
            Check("rollback_doc_id_exclusion_holds_on_g1", (await rc.GetAsync($"/api/documents/{DocA}")).StatusCode == HttpStatusCode.NotFound
                  && (await rc.GetAsync($"/api/graph/resolve?doc={DocA}")).StatusCode == HttpStatusCode.NotFound);
            var stG1 = (await rc.GetAsync($"/api/documents/{Statute}")).StatusCode;
            Check("rollback_copy_hash_exclusion_applies_to_that_copy_only", g1Statute == shaS ? stG1 == HttpStatusCode.NotFound : stG1 == HttpStatusCode.OK,
                  $"G1 statute copy {(g1Statute == shaS ? "is" : "is not")} the excluded copy; {(int)stG1}");
            Check("route_inventory_startup_self_check", web.Logged("route inventory complete"));
            evidence["checks"] = checks;
            S3dEvidence.Write("web_journey.json", evidence);
        }
        finally
        {
            if (web is not null) await web.DisposeAsync();
            try { eng?.ReleaseLock(); } catch { }
            eng?.Dispose();
            NpgsqlConnection.ClearAllPools();
            try { await S3dPg.DropAsync(db); } catch (Exception e) { Console.Error.WriteLine("s3d cleanup: " + e.GetType().Name); }
            TestDirs.Delete(site);
            TestDirs.Delete(work);
        }
    }
}
