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
var generation = GenerationStore.Load(site, vault);
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
var index = SearchIndex.Build(generation);
AppServices? appRef = null;
var search = new SearchService(index, docId => appRef!.VisibleDocument(docId) is null);
var app0 = new AppServices
{
    Generation = generation, Search = search, State = state, Policy = policy, Identity = identity, Ledger = ledger, Vault = vault,
    Eligible = eligibility, TestMode = testMode, SecureCookies = conf.GetValue("Mimamsa:SecureCookies", false),
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
    await using var cmd = new NpgsqlCommand("TRUNCATE app_sessions, app_users, audit_log, withdrawals, vault_copies; UPDATE serving_policy SET epoch = 1, digest = 'state-1'", c);
    await cmd.ExecuteNonQueryAsync();
}
await ledger.InitAsync(resetForTest: testMode && conf.GetValue("Mimamsa:Test:ResetLedger", false));
await policy.SyncCopiesAsync(generation.Documents.Values.Select(d => (d.DocId, d.CopySha, d.CopyBytes))
    .Concat(generation.HeldCopies.Values.Where(h => !generation.Documents.ContainsKey(h.DocId) || generation.Documents[h.DocId].CopySha != h.Sha)
                                        .Select(h => (h.DocId, h.Sha, h.Bytes))));
var (withdrawn, epoch, digest) = await policy.LoadAsync();
state.Load(withdrawn, epoch, digest);
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
    await next();
    var ep = ctx.GetEndpoint() as RouteEndpoint;
    var route = ep?.RoutePattern.RawText ?? (isStatic ? "static" : "spa");
    if (!isStatic) log.LogInformation("request {Method} {Route} {Status} {Ms}ms", ctx.Request.Method, route, ctx.Response.StatusCode, sw.ElapsedMilliseconds);
});

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
app.Run();

public partial class Program;
