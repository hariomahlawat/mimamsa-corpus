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
    return;
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
var index = searchEngine switch
{
    "memory" => SearchIndex.Build(generation),
    "disk" => SearchIndex.Open(generation, conf["Mimamsa:Search:IndexDir"] is { Length: > 0 } idir ? idir : Path.Combine(site, "search-index"),
        new SearchIndexOptions
        {
            CacheBytes = conf.GetValue("Mimamsa:Search:CacheMb", 128L) << 20,
            VerifyOnOpen = conf.GetValue("Mimamsa:Search:VerifyOnOpen", true),
            RebuildOnFailure = conf.GetValue("Mimamsa:Search:RebuildOnFailure", true),
            KeepPrevious = conf.GetValue("Mimamsa:Search:KeepPrevious", 2),
        }, Console.WriteLine),
    _ => throw new InvalidOperationException("Mimamsa:Search:Engine must be 'memory' or 'disk'"),
};
var indexBuildMs = phase.ElapsedMilliseconds;
AppServices? appRef = null;
// C14 S4 hybrid-retrieval PoC: off unless Mimamsa:Hybrid:Enabled=true. The model directory and its pinned SHA-256
// are required when enabled; a mismatch stops start-up. No network access at run time.
ISemanticScorer? semantic = null;
long hybridMs = 0;
if (conf.GetValue("Mimamsa:Hybrid:Enabled", false))
{
    phase.Restart();
    var emb = new Mimamsa.Hybrid.E5Embedder(conf["Mimamsa:Hybrid:ModelDir"] ?? throw new InvalidOperationException("Mimamsa:Hybrid:ModelDir is required when hybrid is enabled"),
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
var search = new SearchService(index, docId => appRef!.VisibleDocument(docId) is null)
{
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
appRef = app0;
var active = new ActiveStreams();
var pendingDrains = new ConcurrentDictionary<string, DateTime>();
long maxResponseWire = delivery.MaxRange + (long)Math.Ceiling(delivery.MaxRange / (double)delivery.Slice) * credit.HeaderAllowance;
var slots = new ResponseSlots((int)Math.Max(1, credit.SiteCap / maxResponseWire));
builder.Services.AddSingleton(app0).AddSingleton(delivery).AddSingleton(slots).AddSingleton(active);

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
            threads = p.Threads.Count, text_store = generation.Text.Stats(),
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

// ---- C16 B06 (CP-1 slice; OFF unless Mimamsa:Activation:Enabled=true): the service as an activation PARTICIPANT.
// It serves the authenticated local control channel, refuses /api requests (503) while a transition or recovery is in
// progress, while the signed exclusion store is unhealthy, or while this process is not on the journal head, and pins
// {knowledge, model, exclusion sequence} per request. In this slice there is no in-process generation swap: OPEN onto
// a generation other than the one this process loaded leaves it not serving until it is restarted (fail closed).
// Response-boundary exclusion filtering of every API surface is B06-integrated work (Core: ActivationParticipant.Respond).
if (conf.GetValue("Mimamsa:Activation:Enabled", false))
{
    var actSite = new Mimamsa.Core.Activation.SiteLayout(site);
    var actInsp = new Mimamsa.Core.Activation.SiteInspector(actSite,
        Mimamsa.Core.Activation.ActivationCli.Reader(actSite, production: !conf.GetValue("Mimamsa:Activation:DevelopmentTrust", false)));
    var participant = new Mimamsa.Core.Activation.ActivationParticipant(actInsp) { OnSwap = (k, _) => k == generation.GenerationId };
    participant.LoadHead();
    var channel = new Mimamsa.Core.Activation.ControlChannelServer(new Mimamsa.Core.Activation.ControlChannelOptions
    {
        PipeName = conf["Mimamsa:Activation:Pipe"] is { Length: > 0 } pn ? pn : "mimamsa-activation",
        Secret = Mimamsa.Core.Activation.ControlChannelOptions.LoadSecret(conf["Mimamsa:Activation:KeyFile"] is { Length: > 0 } kf ? kf : actSite.ChannelKeyPath),
    }, participant) { Log = m => log.LogWarning("{Message}", m) };
    channel.Start();
    app.Lifetime.ApplicationStopping.Register(() => channel.DisposeAsync().AsTask().Wait(2000));
    log.LogInformation("activation participant enabled (serving: {Serving})", participant.IsServing());
    // Response boundary (CP-1 surfaces: search, document, document text, citation, permalink): filter by the CURRENT
    // exclusion state for the request's pin; an unreadable store withholds (fail closed).
    app0.ActivationExcluded = (ctx, docId, sha) =>
    {
        if (ctx.Items["mimamsa.activation.pin"] is not Mimamsa.Core.Activation.ReaderPin pin) return true;
        try { return participant.Respond(pin, new[] { (docId, sha) }, x => x.docId, x => x.sha).Count == 0; }
        catch (Mimamsa.Core.Activation.ActivationRefused) { return true; }
    };
    app.Use(async (ctx, next) =>
    {
        if (!ctx.Request.Path.StartsWithSegments("/api")) { await next(); return; }
        Mimamsa.Core.Activation.ReaderPin pin;
        try { pin = participant.Pin(); }
        catch (Mimamsa.Core.Activation.ActivationRefused)
        {
            ctx.Response.StatusCode = 503;
            ctx.Response.Headers.RetryAfter = "5";
            await ctx.Response.WriteAsJsonAsync(new { state = "activation_not_serving" });
            return;
        }
        ctx.Items["mimamsa.activation.pin"] = pin;
        try { await next(); } finally { participant.Unpin(pin); }
    });
}

app.UseDefaultFiles();
var types =new Microsoft.AspNetCore.StaticFiles.FileExtensionContentTypeProvider();
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
app.Run();

public partial class Program;
