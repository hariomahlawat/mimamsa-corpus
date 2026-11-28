// Mimamsa B1 research service: ASP.NET Core (.NET 10 LTS) on Kestrel. Windows Service lifetime when started by the
// SCM (AD-1); console otherwise. Platform-neutral rules live in Mimamsa.Core; this project binds HTTP, cookies,
// static files and the Kestrel protected-delivery transport (AD-6). Loopback-only unless an operator configures
// otherwise; TLS is not configured in B1 (open item, see docs/architecture/b1/B1_PROTOTYPE.md).
using System.Collections.Concurrent;
using Microsoft.AspNetCore.Server.Kestrel.Transport.Sockets;
using Mimamsa.Core.Delivery;
using Mimamsa.Core.Generation;
using Mimamsa.Core.Identity;
using Mimamsa.Core.Search;
using Mimamsa.Web;
using Npgsql;

var builder = WebApplication.CreateBuilder(args);
var conf = builder.Configuration;
var cs = conf["Mimamsa:Db"] is { Length: > 0 } dsn ? dsn : throw new InvalidOperationException("Mimamsa:Db (PostgreSQL connection string) is required");

// ---- CLI: create a local account (password from MIMAMSA_NEW_PASSWORD or stdin; never from the command line)
if (args.Length >= 3 && args[0] == "--add-user")
{
    var ds0 = new NpgsqlDataSourceBuilder(cs).Build();
    var id0 = new IdentityStore(ds0);
    await id0.EnsureSchemaAsync();
    var pw = Environment.GetEnvironmentVariable("MIMAMSA_NEW_PASSWORD") ?? Console.ReadLine() ?? "";
    Console.WriteLine(await id0.CreateUserAsync(args[1], args[2], pw) ? "created" : "exists");
    return 0;
}

builder.Host.UseWindowsService(o => o.ServiceName = "MimamsaB1");
builder.Logging.ClearProviders();
builder.Logging.AddSimpleConsole(o => { o.SingleLine = true; o.TimestampFormat = "O"; });
// Content-free logs: framework request logging (which includes paths and query strings) is suppressed; the only
// request log is RequestLog below (method, route template, status, elapsed). Search text is never logged.
builder.Logging.AddFilter("Microsoft.AspNetCore", LogLevel.Warning);
builder.Logging.AddFilter("Microsoft.Hosting", LogLevel.Information);

bool testMode = conf.GetValue("Mimamsa:Test:Enabled", false);
var site = conf["Mimamsa:Site"] ?? throw new InvalidOperationException("Mimamsa:Site (importer site root) is required");
var credit = new CreditConfig(conf.GetValue<long>("Mimamsa:Credit:SiteCap", 8L << 20), conf.GetValue<long>("Mimamsa:Credit:ConnCap", 256L << 10),
                              conf.GetValue<long>("Mimamsa:Credit:HeaderAllowance", 1024));
var delivery = new DeliveryConfig(conf.GetValue("Mimamsa:Delivery:MaxRange", 64 * 1024), conf.GetValue("Mimamsa:Delivery:Slice", 64 * 1024 - 1024),
                                  (int)credit.HeaderAllowance, conf.GetValue("Mimamsa:Delivery:DrainGraceMs", 250), testMode,
                                  conf.GetValue("Mimamsa:Test:PauseMs", 1500), conf.GetValue("Mimamsa:Delivery:MaxStreamsPerSession", 6));
var reconcileMinAge = TimeSpan.FromSeconds(testMode ? conf.GetValue("Mimamsa:Test:ReconcileMinAgeSec", 5) : Math.Max(30, conf.GetValue("Mimamsa:Reconcile:MinAgeSec", 30)));
int listenSndBuf = conf.GetValue("Mimamsa:Transport:ListenSendBufferBytes", 32 * 1024);

var dataSource = new NpgsqlDataSourceBuilder(cs).Build();
var vault = new Vault(site);
// C16 WP04 (ADR-0008): Mimamsa:Text:Store = memory (all page and passage text held; the reference) | disk (text read on
// demand from a verified, generation-scoped SQLite store under Mimamsa:Text:Dir, default <site>/text-store, built and
// published atomically on the first start of a generation). Output is identical; only memory, start-up and disk differ.
var textOptions = new TextStoreOptions
{
    Store = conf["Mimamsa:Text:Store"] is { Length: > 0 } tstore ? tstore : "memory",
    Dir = conf["Mimamsa:Text:Dir"] is { Length: > 0 } tdir ? tdir : null,
    CacheBytes = conf.GetValue("Mimamsa:Text:CacheMb", 64L) << 20,
    VerifyOnOpen = conf.GetValue("Mimamsa:Text:VerifyOnOpen", true),
    RebuildOnFailure = conf.GetValue("Mimamsa:Text:RebuildOnFailure", true),
    KeepPrevious = conf.GetValue("Mimamsa:Text:KeepPrevious", 2),
};
if (textOptions.Store is not ("memory" or "disk")) throw new InvalidOperationException("Mimamsa:Text:Store must be 'memory' or 'disk'");
// C16 Stage 3 (S3-D): with the activation journal the process swaps generations in process and keeps at most two
// resident (GenerationHost). That bound only holds memory when page text and postings stay on disk, so activation mode
// REQUIRES the disk text store and the disk index; it refuses to start otherwise.
bool activationConf = conf.GetValue("Mimamsa:Activation:Enabled", false);
if (activationConf && (textOptions.Store != "disk" || (conf["Mimamsa:Search:Engine"] ?? "memory") != "disk"))
    throw new InvalidOperationException("Mimamsa:Activation:Enabled requires Mimamsa:Text:Store=disk and Mimamsa:Search:Engine=disk (in-process generation swap with at most two generations resident)");
var loadSw = System.Diagnostics.Stopwatch.StartNew();
var generation = GenerationStore.Load(site, vault, textOptions, Console.WriteLine);
var generationLoadMs = loadSw.ElapsedMilliseconds;
var state = new ServingState();
var policy = new PolicyStore(dataSource);
// C14 F15: the lock duration is fixed at 5 minutes except in test mode, where journeys may shorten it.
var identity = new IdentityStore(dataSource)
{
    LockDuration = testMode && conf.GetValue<int?>("Mimamsa:Test:LockSeconds") is int ls ? TimeSpan.FromSeconds(ls) : TimeSpan.FromMinutes(5),
    Throttle = new LoginThrottle
    {
        PerUsername = Math.Max(6, conf.GetValue("Mimamsa:Login:ThrottlePerUsername", 10)),
        PerSource = Math.Max(6, conf.GetValue("Mimamsa:Login:ThrottlePerSource", 30)),
        Window = TimeSpan.FromSeconds(Math.Max(10, conf.GetValue("Mimamsa:Login:ThrottleWindowSec", 300))),
    },
};
var ledger = new CreditLedger(dataSource, credit);
// Restricted-material register re-check (review F16): ON by default and fail closed. The service refuses to start
// unless Mimamsa:RestrictedRegister names a readable register whose SHA-256 equals the one pinned by the active
// release. Only test mode may switch it off, and only explicitly (Mimamsa:Test:AllowNoRegister=true).
RestrictedRegister register;
if (testMode && conf.GetValue("Mimamsa:Test:AllowNoRegister", false)) register = RestrictedRegister.Empty;
else register = RestrictedRegister.LoadRequired(conf["Mimamsa:RestrictedRegister"], generation.Release.RegisterSha256);
var eligibility = new Eligibility(generation, state, register, vault);
var phase = System.Diagnostics.Stopwatch.StartNew();
// C15 WP1 (ADR-0007): Mimamsa:Search:Engine = memory (B1 in-process index) | disk (persistent SQLite index under
// Mimamsa:Search:IndexDir, default <site>/search-index: built, verified and published atomically on first start of a
// generation, verified and reopened afterwards). Results are identical; only memory, start-up and persistence differ.
var searchEngine = conf["Mimamsa:Search:Engine"] ?? "memory";
SearchIndex OpenIndex(GenerationStore g) => searchEngine switch
{
    "memory" => SearchIndex.Build(g),
    "disk" => SearchIndex.Open(g, conf["Mimamsa:Search:IndexDir"] is { Length: > 0 } idir ? idir : Path.Combine(site, "search-index"),
        new SearchIndexOptions
        {
            CacheBytes = conf.GetValue("Mimamsa:Search:CacheMb", 128L) << 20,
            VerifyOnOpen = conf.GetValue("Mimamsa:Search:VerifyOnOpen", true),
            RebuildOnFailure = conf.GetValue("Mimamsa:Search:RebuildOnFailure", true),
            KeepPrevious = conf.GetValue("Mimamsa:Search:KeepPrevious", 2),
        }, Console.WriteLine),
    _ => throw new InvalidOperationException("Mimamsa:Search:Engine must be 'memory' or 'disk'"),
};
var index = OpenIndex(generation);
var indexBuildMs = phase.ElapsedMilliseconds;
// The search engine reaches eligibility through a box (not a captured top-level local), so a generation released after an
// in-process swap (C16 Stage 3) is not kept alive by this lambda. Behaviour is unchanged.
var appBox = new System.Runtime.CompilerServices.StrongBox<AppServices?>();
static Func<string, bool> HiddenVia(System.Runtime.CompilerServices.StrongBox<AppServices?> box) => docId => box.Value!.VisibleDocument(docId) is null;
// C14 S4 hybrid-retrieval PoC: off unless Mimamsa:Hybrid:Enabled=true. The model directory and its pinned SHA-256
// are required when enabled; a mismatch stops start-up. No network access at run time.
ISemanticScorer? semantic = null;
Mimamsa.Hybrid.E5Embedder? embedder = null;   // C16 Stage 3: shared by the generations of an in-process swap
long hybridMs = 0;
if (conf.GetValue("Mimamsa:Hybrid:Enabled", false))
{
    phase.Restart();
    var emb = embedder = new Mimamsa.Hybrid.E5Embedder(conf["Mimamsa:Hybrid:ModelDir"] ?? throw new InvalidOperationException("Mimamsa:Hybrid:ModelDir is required when hybrid is enabled"),
        conf.GetValue("Mimamsa:Hybrid:Threads", 0), conf.GetValue("Mimamsa:Hybrid:Cuda", false),
        conf["Mimamsa:Hybrid:ModelSha256"] ?? throw new InvalidOperationException("Mimamsa:Hybrid:ModelSha256 is required when hybrid is enabled"));
    semantic = Mimamsa.Hybrid.DenseIndex.Build(index, generation.GenerationId, emb, conf["Mimamsa:Hybrid:CacheDir"], conf["Mimamsa:Hybrid:ModelLabel"] ?? "multilingual-e5-small@614241f6",
        conf.GetValue("Mimamsa:Hybrid:PassageTokens", 256), log: Console.WriteLine);
    hybridMs = phase.ElapsedMilliseconds;
}
// C15 WP2: optional cross-encoder rerank stage (off unless Mimamsa:Hybrid:Reranker:Enabled=true; pinned SHA-256 required).
IReranker? reranker = null;
if (conf.GetValue("Mimamsa:Hybrid:Reranker:Enabled", false))
    reranker = new Mimamsa.Hybrid.CrossEncoder(
        conf["Mimamsa:Hybrid:Reranker:ModelDir"] ?? throw new InvalidOperationException("Mimamsa:Hybrid:Reranker:ModelDir is required when the reranker is enabled"),
        conf["Mimamsa:Hybrid:Reranker:OnnxFile"] ?? "onnx/model.onnx",
        conf["Mimamsa:Hybrid:Reranker:Sha256"] ?? throw new InvalidOperationException("Mimamsa:Hybrid:Reranker:Sha256 is required when the reranker is enabled"),
        conf.GetValue("Mimamsa:Hybrid:Threads", 0)) { MaxTokens = conf.GetValue("Mimamsa:Hybrid:Reranker:MaxTokens", 256) };
var search = new SearchService(index, HiddenVia(appBox))
{
    HideChipsOfHiddenDocuments = activationConf,   // C16 Stage 3: false (unchanged) unless activation is enabled
    Semantic = semantic,
    Reranker = reranker,
    // C15 WP2/WP7: provision-heading boost for procedural plain-language queries (see ProvisionHeadings).
    Headings = conf.GetValue("Mimamsa:Search:ProvisionHeadings", true) ? ProvisionHeadings.Build(index) : null,
    // MinSimilarity: a passage enters through the dense layer only at or above this cosine similarity. The value is
    // calibrated on the C14 walkthrough queries over the real sample (HybridBench calibrate), never on oracle data.
    Hybrid = new HybridOptions(conf.GetValue("Mimamsa:Hybrid:LexicalDepth", 200), conf.GetValue("Mimamsa:Hybrid:DenseDepth", 100), conf.GetValue("Mimamsa:Hybrid:RrfK", 60),
                               conf.GetValue("Mimamsa:Hybrid:MinSimilarity", 0.0), conf.GetValue("Mimamsa:Hybrid:Reranker:Pool", 30), conf.GetValue("Mimamsa:Hybrid:Reranker:Admit", 0.0)),
};
var app0 = new AppServices
{
    Generation = generation, Search = search, State = state, Policy = policy, Identity = identity, Ledger = ledger, Vault = vault,
    Eligible = eligibility, TestMode = testMode, SecureCookies = conf.GetValue("Mimamsa:SecureCookies", false),
    Studio = new Mimamsa.Core.Studio.StudioStore(dataSource), Commander = new Mimamsa.Core.Commander.TocCommanderSource(generation),
};
appBox.Value = app0;
var active = new ActiveStreams();
var pendingDrains = new ConcurrentDictionary<string, DateTime>();
long maxResponseWire = delivery.MaxRange + (long)Math.Ceiling(delivery.MaxRange / (double)delivery.Slice) * credit.HeaderAllowance;
var slots = new ResponseSlots((int)Math.Max(1, credit.SiteCap / maxResponseWire));
// C16 Stage 3: under activation each request gets the AppServices of the generation its pin names (GenerationHost);
// default mode keeps the one process-wide AppServices.
GenerationHost? host = null;
if (activationConf)
    builder.Services.AddHttpContextAccessor().AddScoped(sp =>
        sp.GetRequiredService<IHttpContextAccessor>().HttpContext?.Items[GenerationHost.SlotKey] is GenerationSlot gs ? gs.Services!
        : host?.Current?.Services ?? throw new InvalidOperationException("no generation is being served"))
        .AddSingleton(delivery).AddSingleton(slots).AddSingleton(active);
else builder.Services.AddSingleton(app0).AddSingleton(delivery).AddSingleton(slots).AddSingleton(active);

builder.WebHost.UseSockets(o =>
{
    if (listenSndBuf > 0)
        o.CreateBoundListenSocket = ep => { var s = SocketTransportOptions.CreateDefaultBoundListenSocket(ep); s.SendBufferSize = listenSndBuf; return s; };
});
builder.WebHost.ConfigureKestrel(k =>
{
    k.AddServerHeader = false;
    k.Limits.MaxConcurrentConnections = conf.GetValue<long>("Mimamsa:Transport:MaxConcurrentConnections", 1000);
    k.Limits.MaxResponseBufferSize = 64 * 1024;
    k.Limits.MaxRequestBodySize = 64 * 1024;
    k.ConfigureEndpointDefaults(lo => lo.Use(next => async conn =>
    {
        active.ConnectionOpened(conn);
        try { await next(conn); }
        finally
        {
            var pool = CreditLedger.ConnPoolId(ledger.InstanceId, conn.ConnectionId);
            var ended = DateTime.UtcNow;
            pendingDrains[pool] = ended;
            var lep = conn.LocalEndPoint; var rep = conn.RemoteEndPoint;
            _ = Task.Run(async () =>
            {
                try
                {
                    var (proof, evidence) = await DrainProbe.AwaitDrainAsync(lep, rep, delivery.DrainGraceMs);
                    foreach (var (id, _) in await ledger.DrainConnectionAsync(pool, $"kestrel connection {conn.ConnectionId} ended {ended:O}; {evidence}"))
                        DeliveryTrace.Emit("prove_release", "drain_probe", new { attempt = id.ToString(), proof, evidence });
                }
                catch (Exception) { }
                finally { pendingDrains.TryRemove(pool, out _); slots.ReleaseFor(conn.ConnectionId); active.ConnectionDrained(conn.ConnectionId); }
            });
        }
    }));
});

var app = builder.Build();
var log = app.Services.GetRequiredService<ILoggerFactory>().CreateLogger("mimamsa");

// ---- start-up: schemas, single serving instance, policy mirror, bootstrap accounts (test mode only)
await identity.EnsureSchemaAsync();
await policy.EnsureSchemaAsync();
await app0.Studio.EnsureSchemaAsync();
var instanceLockConn = await dataSource.OpenConnectionAsync();
await using (var lk = new NpgsqlCommand("SELECT pg_try_advisory_lock(hashtext('mimamsa-b1-serving-instance'))", instanceLockConn))
{
    bool got = false;
    for (int i = 0; i < 50 && !got; i++) { got = (bool)(await lk.ExecuteScalarAsync())!; if (!got) await Task.Delay(200); }
    if (!got) throw new InvalidOperationException("another serving instance holds the instance lock; refusing to start (single-instance constraint, review F10)");
}
if (testMode && conf.GetValue("Mimamsa:Test:ResetState", false))
{
    // TEST ONLY: disposable database state for repeatable journeys (accounts, sessions, withdrawals, policy witness)
    await using var c = await dataSource.OpenConnectionAsync();
    await using var cmd = new NpgsqlCommand("TRUNCATE app_sessions, app_users, audit_log, withdrawals, vault_copies, studio_versions, studio_documents, studio_notes; UPDATE serving_policy SET epoch = 1, digest = 'state-1'", c);
    await cmd.ExecuteNonQueryAsync();
}
await ledger.InitAsync(resetForTest: testMode && conf.GetValue("Mimamsa:Test:ResetLedger", false));
await policy.SyncCopiesAsync(generation.Documents.Values.Select(d => (d.DocId, d.CopySha, d.CopyBytes))
    .Concat(generation.HeldCopies.Values.Where(h => !generation.Documents.ContainsKey(h.DocId) || generation.Documents[h.DocId].CopySha != h.Sha)
                                        .Select(h => (h.DocId, h.Sha, h.Bytes))));
var (withdrawn, epoch, digest) = await policy.LoadAsync();
state.Load(withdrawn, epoch, digest);
// C15 WP3: derive the generation's legal knowledge graph, publish it atomically (skipped when the identical graph is
// already published) and verify it. A failure leaves the graph routes unavailable (503); the rest of the service is
// unaffected. Eligibility is applied per request, never baked into the stored graph.
try
{
    phase.Restart();
    var graph = Mimamsa.Core.Graph.GraphBuilder.Build(generation);
    var graphDb = new Mimamsa.Core.Graph.GraphStore(dataSource);
    await graphDb.EnsureSchemaAsync();
    var published = await graphDb.PublishAsync(graph);
    var (ok, detail) = await graphDb.VerifyAsync(graph);
    if (ok) { app0.Graph = graph; app0.GraphDb = graphDb; }
    log.LogInformation("legal knowledge graph {State}: {Detail} ({Ms} ms)", ok ? (published ? "published" : "already published") : "FAILED VERIFICATION", detail, phase.ElapsedMilliseconds);
}
catch (Exception ex) { log.LogWarning("legal knowledge graph not available: {Error}", ex.GetType().Name); }
DeliveryTrace.Start(testMode ? conf["Mimamsa:Trace:Path"] : null);
DeliveryTrace.Emit("boot", "witness", new { epoch = state.Epoch, digest = state.Digest, instance = ledger.InstanceId });
if (testMode)
    foreach (var spec in conf.GetSection("Mimamsa:Test:Users").Get<string[]>() ?? Array.Empty<string>())
    {
        var parts = spec.Split(':', 3);
        await identity.CreateUserAsync(parts[0], parts[1], parts[2], iterations: 100_000);
    }
else if (await identity.UserCountAsync() == 0)
    log.LogWarning("no accounts exist; create one with: Mimamsa.Web --add-user <name> Admin (password on stdin)");
log.LogInformation("generation {Gen} loaded: {Docs} documents, {Passages} passages indexed, load issues {Issues}",
    generation.GenerationId, generation.Documents.Count, index.N, generation.LoadIssues.Count == 0 ? "none" : string.Join(",", generation.LoadIssues.Select(kv => kv.Key + "=" + kv.Value)));
log.LogInformation("text store: {Kind}{Path}", generation.Text.Kind, generation.Text.StorePath is { } tpath ? " at " + tpath : "");
log.LogInformation("start-up phases: generation load and re-hash {LoadMs} ms, index build {IndexMs} ms, hybrid {HybridMs} ms, process {ProcMs} ms",
    generationLoadMs, indexBuildMs, hybridMs, (long)(DateTime.Now - System.Diagnostics.Process.GetCurrentProcess().StartTime).TotalMilliseconds);
// C14 S4: numbers-only process diagnostics for benchmarks. Off unless Mimamsa:Diagnostics:Enabled=true; returns no
// content, ids or queries. ?gc=1 forces a full blocking compacting GC first (to separate retention from leaks).
// Integration hardening: unauthenticated, so answered only to loopback callers (a LAN caller could otherwise force
// blocking full GCs with ?gc=1); a warning is logged whenever it is enabled.
Func<object?> textStats = () => generation.Text.Stats();   // C16 Stage 3: the current generation's under activation
if (conf.GetValue("Mimamsa:Diagnostics:Enabled", false))
{
    app.Logger.LogWarning("diagnostics endpoint /api/diag/memory is enabled (loopback callers only; benchmarks only)");
    app.MapGet("/api/diag/memory", (HttpContext ctx) =>
    {
        if (ctx.Connection.RemoteIpAddress is not { } ip || !System.Net.IPAddress.IsLoopback(ip)) return Results.NotFound();
        if (ctx.Request.Query["gc"] == "1")
        {
            System.Runtime.GCSettings.LargeObjectHeapCompactionMode = System.Runtime.GCLargeObjectHeapCompactionMode.CompactOnce;
            GC.Collect(GC.MaxGeneration, GCCollectionMode.Forced, blocking: true, compacting: true);
            GC.WaitForPendingFinalizers();
            GC.Collect(GC.MaxGeneration, GCCollectionMode.Forced, blocking: true, compacting: true);
        }
        var gi = GC.GetGCMemoryInfo();
        var p = System.Diagnostics.Process.GetCurrentProcess();
        return Results.Json(new
        {
            working_set_mb = Math.Round(p.WorkingSet64 / 1048576.0, 1), private_mb = Math.Round(p.PrivateMemorySize64 / 1048576.0, 1),
            managed_heap_mb = Math.Round(GC.GetTotalMemory(false) / 1048576.0, 1), gc_heap_size_mb = Math.Round(gi.HeapSizeBytes / 1048576.0, 1),
            gc_committed_mb = Math.Round(gi.TotalCommittedBytes / 1048576.0, 1), gc_fragmented_mb = Math.Round(gi.FragmentedBytes / 1048576.0, 1),
            gc_server = System.Runtime.GCSettings.IsServerGC, gc_count_gen2 = GC.CollectionCount(2), cpu_s = Math.Round(p.TotalProcessorTime.TotalSeconds, 2),
            threads = p.Threads.Count, text_store = textStats(),
        });
    });
}
_ = Task.Run(async () => { while (true) { try { await ledger.HeartbeatAsync(); } catch { } await Task.Delay(2000); } });
_ = Task.Run(async () =>
{
    while (true)
    {
        await Task.Delay(1000);
        try { await ledger.ReconcilePriorInstancesAsync(reconcileMinAge, DrainProbe.SocketSafe); } catch { }
    }
});

// ---- middleware: content-free request log, security headers, cache policy
app.Use(async (ctx, next) =>
{
    var sw = System.Diagnostics.Stopwatch.StartNew();
    var h = ctx.Response.Headers;
    h["X-Content-Type-Options"] = "nosniff";
    h["Referrer-Policy"] = "no-referrer";
    h["X-Frame-Options"] = "DENY";
    h["Cross-Origin-Opener-Policy"] = "same-origin";
    h["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()";
    h["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; style-src 'self'; img-src 'self' data: blob:; " +
                                   "font-src 'self'; worker-src 'self' blob:; connect-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'";
    var path = ctx.Request.Path.Value ?? "";
    bool isStatic = path.StartsWith("/assets/") || path.StartsWith("/vendor/");
    if (!isStatic) { h.CacheControl = "no-store"; h.Pragma = "no-cache"; }
    else h.CacheControl = "no-cache";
    // C14 F05: every API response names the serving-policy epoch at the moment it is sent, so the client notices a
    // withdrawal on its next request and re-checks the documents it has open.
    if (path.StartsWith("/api/")) ctx.Response.OnStarting(() => { ctx.Response.Headers["X-Mimamsa-Policy-Epoch"] = state.Epoch.ToString(System.Globalization.CultureInfo.InvariantCulture); return Task.CompletedTask; });
    // ChatGPT review of PR #80 (P1): a document whose stored text fails an integrity check is withheld with a controlled,
    // content-free response; nothing partial or cached of it is sent, and the log names only the route.
    try { await next(); }
    catch (TextIntegrityException) when (!ctx.Response.HasStarted)
    {
        log.LogWarning("text integrity failure on {Path}; document text withheld", ctx.GetEndpoint() is RouteEndpoint re ? re.RoutePattern.RawText : "unrouted");
        ctx.Response.Clear();
        ctx.Response.Headers.CacheControl = "no-store";
        ctx.Response.StatusCode = 503;
        await ctx.Response.WriteAsJsonAsync(new { state = "integrity_failure", notice = "The text of this document failed an integrity check and is withheld. The original can still be checked by an administrator." });
    }
    var ep = ctx.GetEndpoint() as RouteEndpoint;
    var route = ep?.RoutePattern.RawText ?? (isStatic ? "static" : "spa");
    if (!isStatic) log.LogInformation("request {Method} {Route} {Status} {Ms}ms", ctx.Request.Method, route, ctx.Response.StatusCode, sw.ElapsedMilliseconds);
});

// ---- C16 B06 (OFF unless Mimamsa:Activation:Enabled=true): the service as an activation PARTICIPANT.
// It serves the authenticated local control channel, refuses /api requests (503) while a transition or recovery is in
// progress, while the signed exclusion store is unhealthy, or while this process is not on the journal head, and pins
// {knowledge, model, exclusion sequence} per request.
// C16 Stage 3 (S3-D): IN-PROCESS GENERATION SWAP. Each served knowledge generation lives in a GenerationSlot; PREPARE
// loads and verifies the target's slot beside the serving one (old generation keeps serving), OPEN switches atomically,
// every request is pinned to the slot of its pin, and a previous slot is released when its last request goes. At most
// two slots are resident (disk text store and disk index required; see GenerationHost). The response boundary covers
// every surface (ActivationRouteInventory, ActivationBoundary); facets and totals are counted over surviving results.
bool activationEnabled = false;
if (activationConf)
{
    var actSite = new Mimamsa.Core.Activation.SiteLayout(site);
    var actInsp = new Mimamsa.Core.Activation.SiteInspector(actSite,
        Mimamsa.Core.Activation.ActivationCli.Reader(actSite, production: !conf.GetValue("Mimamsa:Activation:DevelopmentTrust", false)));
    var participant = new Mimamsa.Core.Activation.ActivationParticipant(actInsp);
    // 2.1 lexical-only releases: the semantic path (query embedding, dense candidates) runs only when this request's
    // pin allows it; otherwise search is lexical only.
    var semanticForRequest = new AsyncLocal<bool?>();
    var testPause = conf.GetValue("Mimamsa:Test:Enabled", false) && conf["Mimamsa:Test:PauseDir"] is { Length: > 0 } pd ? pd : null;
    var studio = app0.Studio;
    var secureCookies = conf.GetValue("Mimamsa:SecureCookies", false);
    var allowNoRegister = testMode && conf.GetValue("Mimamsa:Test:AllowNoRegister", false);

    // Boundary wiring of one generation's services: the single eligibility decision asks the boundary (so every surface
    // and the search engine's hidden-document predicate filter excluded copies), and the handlers' explicit checks.
    static void Wire(AppServices s, ActivationBoundary b, AsyncLocal<bool?> semantic)
    {
        s.Eligible.Boundary = b.ExcludedForCurrentRequest;
        s.ActivationExcluded = b.Excluded;
        s.ActivationExcludedNow = b.ExcludedNow;
        s.ActivationStreamPause = b.TestPauseAsync;
        s.Search.SemanticAllowed = () => semantic.Value ?? false;
    }
    static Action ReleaseOf(SearchIndex ix, GenerationStore g) => () => { ix.Release(); (g.Text as IDisposable)?.Dispose(); };

    // Load and verify one generation's services beside the serving ones (PREPARE / OPEN of a non-resident target). Any
    // failure throws: the host keeps no slot and the participant refuses (fail closed).
    GenerationSlot LoadSlot(string genId)
    {
        var g = GenerationStore.Load(site, vault, textOptions, Console.WriteLine, generationId: genId);
        SearchIndex? ix = null;
        try
        {
            if (g.GenerationId != genId) throw new InvalidOperationException("loaded another generation");
            var reg = allowNoRegister ? RestrictedRegister.Empty : RestrictedRegister.LoadRequired(conf["Mimamsa:RestrictedRegister"], g.Release.RegisterSha256);
            var elig = new Eligibility(g, state, reg, vault);
            ix = OpenIndex(g);
            ISemanticScorer? sem = embedder is null ? null : Mimamsa.Hybrid.DenseIndex.Build(ix, g.GenerationId, embedder, conf["Mimamsa:Hybrid:CacheDir"],
                conf["Mimamsa:Hybrid:ModelLabel"] ?? "multilingual-e5-small@614241f6", conf.GetValue("Mimamsa:Hybrid:PassageTokens", 256), log: Console.WriteLine);
            var box = new System.Runtime.CompilerServices.StrongBox<AppServices?>();
            var ss = new SearchService(ix, HiddenVia(box))
            {
                Semantic = sem, Reranker = reranker, HideChipsOfHiddenDocuments = true,
                Headings = conf.GetValue("Mimamsa:Search:ProvisionHeadings", true) ? ProvisionHeadings.Build(ix) : null,
                Hybrid = new HybridOptions(conf.GetValue("Mimamsa:Hybrid:LexicalDepth", 200), conf.GetValue("Mimamsa:Hybrid:DenseDepth", 100), conf.GetValue("Mimamsa:Hybrid:RrfK", 60),
                                           conf.GetValue("Mimamsa:Hybrid:MinSimilarity", 0.0), conf.GetValue("Mimamsa:Hybrid:Reranker:Pool", 30), conf.GetValue("Mimamsa:Hybrid:Reranker:Admit", 0.0)),
            };
            var svc = box.Value = new AppServices
            {
                Generation = g, Search = ss, State = state, Policy = policy, Identity = identity, Ledger = ledger, Vault = vault,
                Eligible = elig, TestMode = testMode, SecureCookies = secureCookies, Studio = studio, Commander = new Mimamsa.Core.Commander.TocCommanderSource(g),
            };
            policy.SyncCopiesAsync(g.Documents.Values.Select(d => (d.DocId, d.CopySha, d.CopyBytes))
                .Concat(g.HeldCopies.Values.Where(h => !g.Documents.ContainsKey(h.DocId) || g.Documents[h.DocId].CopySha != h.Sha).Select(h => (h.DocId, h.Sha, h.Bytes))))
                .GetAwaiter().GetResult();
            // the graph is part of the verified services: a target whose graph does not publish and verify is refused
            var graph = Mimamsa.Core.Graph.GraphBuilder.Build(g);
            var graphDb = new Mimamsa.Core.Graph.GraphStore(dataSource);
            graphDb.EnsureSchemaAsync().GetAwaiter().GetResult();
            graphDb.PublishAsync(graph).GetAwaiter().GetResult();
            var (ok, _) = graphDb.VerifyAsync(graph).GetAwaiter().GetResult();
            if (!ok) throw new InvalidOperationException("graph failed verification");
            svc.Graph = graph; svc.GraphDb = graphDb;
            var b = new ActivationBoundary(participant, g, testPause);
            Wire(svc, b, semanticForRequest);
            return new GenerationSlot { Id = genId, Services = svc, Boundary = b, OnRelease = ReleaseOf(ix, g), Payload = g };
        }
        catch
        {
            ix?.Release();
            (g.Text as IDisposable)?.Dispose();
            throw;
        }
    }

    host = new GenerationHost(LoadSlot)
    {
        MaxResident = 2,
        BudgetWait = TimeSpan.FromSeconds(Math.Max(0, conf.GetValue("Mimamsa:Activation:SwapBudgetWaitSec", 30))),
        Log = m => log.LogInformation("{Message}", m),
    };
    // The generation loaded at start-up is the first slot (the journal head when the site is OPEN).
    var initialBoundary = new ActivationBoundary(participant, generation, testPause);
    Wire(app0, initialBoundary, semanticForRequest);
    host.Install(new GenerationSlot { Id = generation.GenerationId, Services = app0, Boundary = initialBoundary, OnRelease = ReleaseOf(index, generation), Payload = generation });
    host.AttachTo(participant);
    participant.LoadHead();
    var channel = new Mimamsa.Core.Activation.ControlChannelServer(new Mimamsa.Core.Activation.ControlChannelOptions
    {
        PipeName = conf["Mimamsa:Activation:Pipe"] is { Length: > 0 } pn ? pn : "mimamsa-activation",
        Secret = Mimamsa.Core.Activation.ControlChannelOptions.LoadSecret(conf["Mimamsa:Activation:KeyFile"] is { Length: > 0 } kf ? kf : actSite.ChannelKeyPath),
    }, participant) { Log = m => log.LogWarning("{Message}", m) };
    channel.Start();
    app.Lifetime.ApplicationStopping.Register(() => channel.DisposeAsync().AsTask().Wait(2000));
    log.LogInformation("activation participant enabled (serving: {Serving}, semantic search: {Semantic}, in-process swap: on, resident limit {Limit})",
        participant.IsServing(), participant.SemanticSearchAvailable(), host.MaxResident);
    var h = host;
    textStats = () => h.Current?.Services?.Generation.Text.Stats();
    activationEnabled = true;
    app.Use(async (ctx, next) =>
    {
        // non-API paths are the static UI (wwwroot assets, SPA shell, /health): no document-derived content
        if (!ctx.Request.Path.StartsWithSegments("/api")) { await next(); return; }
        var cls = ActivationRouteInventory.Classify(ctx.GetEndpoint());
        Mimamsa.Core.Activation.ReaderPin pin;
        try { pin = participant.Pin(); }
        catch (Mimamsa.Core.Activation.ActivationRefused)
        {
            ctx.Response.StatusCode = 503;
            ctx.Response.Headers.RetryAfter = "5";
            await ctx.Response.WriteAsJsonAsync(new { state = "activation_not_serving" });
            return;
        }
        // the request is pinned to exactly the slot of its pin: no request mixes generations
        var slot = h.Acquire(pin.Knowledge);
        if (slot is null)
        {
            participant.Unpin(pin);
            ctx.Response.StatusCode = 503;
            ctx.Response.Headers.RetryAfter = "1";
            await ctx.Response.WriteAsJsonAsync(new { state = "activation_not_serving" });
            return;
        }
        ctx.Items[ActivationBoundary.PinKey] = pin;
        ctx.Items[GenerationHost.SlotKey] = slot;
        ActivationBoundary.Request.Value = ctx;
        semanticForRequest.Value = pin.SemanticSearch;
        ctx.Response.Headers["X-Mimamsa-Generation"] = slot.Id;   // content-free: which generation answered
        try
        {
            if (cls == RouteClass.Refused)
            {
                ctx.Response.StatusCode = 503;
                ctx.Response.Headers.CacheControl = "no-store";
                await ctx.Response.WriteAsJsonAsync(new { state = "not_available_under_activation" });
                return;
            }
            if (cls is not (RouteClass.Boundary or RouteClass.BoundaryPrivate)) { await next(); return; }   // ContentFree, ProtectiveAction, BoundaryStreaming
            var original = ctx.Response.Body;
            using var buffer = new MemoryStream();
            ctx.Response.Body = buffer;
            try { await next(); }
            finally { ctx.Response.Body = original; }
            await slot.Boundary!.TestPauseAsync(ctx);
            if (slot.Boundary.MayCommit(ctx, buffer.GetBuffer().AsSpan(0, (int)buffer.Length), scanBody: cls == RouteClass.Boundary))
            {
                ctx.Response.ContentLength = buffer.Length;
                buffer.Position = 0;
                await buffer.CopyToAsync(original);
                return;
            }
            // linearised after an exclusion acceptance: nothing of the buffered response is sent
            var path = ctx.Request.Path;
            bool document = path.StartsWithSegments("/api/documents") || path.StartsWithSegments("/api/cite") || path.StartsWithSegments("/api/v2");
            ctx.Response.Clear();
            ctx.Response.Headers.CacheControl = "no-store";
            ctx.Response.Headers["X-Mimamsa-Generation"] = slot.Id;
            if (!document) ctx.Response.Headers.RetryAfter = "1";
            ctx.Response.StatusCode = document ? 404 : 503;
            await ctx.Response.WriteAsJsonAsync(document ? new { state = "unavailable", notice = Api.NotAvailable }
                                                         : (object)new { state = "results_changed", notice = "Results changed while the request ran; try again." });
        }
        finally
        {
            ActivationBoundary.Request.Value = null;
            h.ReleaseLease(slot);
            participant.Unpin(pin);
        }
    });
}

app.UseDefaultFiles();
var types = new Microsoft.AspNetCore.StaticFiles.FileExtensionContentTypeProvider();
types.Mappings[".mjs"] = "text/javascript"; types.Mappings[".bcmap"] = "application/octet-stream";
types.Mappings[".pfb"] = "application/octet-stream"; types.Mappings[".icc"] = "application/vnd.iccprofile"; types.Mappings[".wasm"] = "application/wasm";
app.UseStaticFiles(new StaticFileOptions { ServeUnknownFileTypes = false, ContentTypeProvider = types });
Api.Map(app);
ProtectedDelivery.Map(app);
app.MapFallback(async ctx =>
{
    if (ctx.Request.Path.StartsWithSegments("/api")) { ctx.Response.StatusCode = 404; return; }
    ctx.Response.ContentType = "text/html; charset=utf-8";
    await ctx.Response.SendFileAsync(Path.Combine(app.Environment.WebRootPath, "index.html"));
});
if (activationEnabled)
{
    // C16-CP1-01: every mapped endpoint must be classified before the activation-managed service may start.
    var unclassified = ActivationRouteInventory.Unclassified(((IEndpointRouteBuilder)app).DataSources.SelectMany(d => d.Endpoints));
    if (unclassified.Count > 0)
    {
        log.LogCritical("activation: unclassified routes {Routes}; refusing to start", string.Join(", ", unclassified));
        return 3;
    }
    log.LogInformation("activation: route inventory complete ({Count} classified routes)", ActivationRouteInventory.Routes.Count);
    // C16 Stage 3: drop every start-up reference to the first generation, so that once it is swapped out and its last
    // request is gone, the GenerationHost's release frees it (the host's slot is then its only owner).
    generation = null!; index = null!; app0 = null!; search = null!; eligibility = null!; appBox = null!; semantic = null;
}
app.Run();
return 0;

public partial class Program;
