// Mimamsa P1 hosting PoC: ASP.NET Core (.NET 10 LTS) minimal API.
// v1 endpoints: /health, /api/search, /api/documents/{id}, /api/documents/{id}/pdf (P1 throughput comparison)
// v2 endpoints (R2-N01): bounded metadata bootstrap + authenticated, credit-reserved, bounded range delivery.
// Platform-neutral rules: ../core (MimamsaPoc.Core). OS/host specifics: this project (Kestrel adapter,
// UseWindowsService, socket-buffer option). Windows-first, not Windows-only.
using System.Collections.Concurrent;
using System.Text.Json;
using Microsoft.AspNetCore.Server.Kestrel.Transport.Sockets;
using MimamsaPoc.Core;
using MimamsaPocApi;
using Npgsql;

if (args.Length >= 2 && args[0] == "--ledger-oracle")
{
    Console.WriteLine(await LedgerOracle.RunAsync(args[1]));
    return;
}

var builder = WebApplication.CreateSlimBuilder(args);
builder.Host.UseWindowsService(o => o.ServiceName = "MimamsaPocApi");
builder.Logging.ClearProviders();
builder.Logging.AddConsole();
builder.Logging.SetMinimumLevel(LogLevel.Warning);

var conf = builder.Configuration;
var cs = conf["Mimamsa:Db"] ?? "Host=127.0.0.1;Port=55432;Username=poc;Database=poc;Maximum Pool Size=32;Minimum Pool Size=4";
var pdfRoot = Path.GetFullPath(conf["Mimamsa:PdfRoot"] ?? "pdfstore");
var token = conf["Mimamsa:DevToken"] ?? "dev-token";
var credit = new CreditConfig(conf.GetValue<long>("Mimamsa:Credit:SiteCap", 8L << 20), conf.GetValue<long>("Mimamsa:Credit:ConnCap", 256L << 10),
                              conf.GetValue<long>("Mimamsa:Credit:HeaderAllowance", 1024));
// Test mode gates every test-only behaviour (seeding, ledger reset, deterministic pause hooks, short reconcile age).
bool testMode = conf.GetValue("Mimamsa:Test:Enabled", false);
var delivery = new DeliveryConfig(conf.GetValue("Mimamsa:Delivery:MaxRange", 128 * 1024), conf.GetValue("Mimamsa:Delivery:Slice", 64 * 1024 - 1024),
                                  (int)credit.HeaderAllowance, conf.GetValue("Mimamsa:Delivery:DrainGraceMs", 250),
                                  testMode, conf.GetValue("Mimamsa:Test:PauseMs", 1500), conf.GetValue("Mimamsa:Delivery:MaxStreamsPerSession", 4));
// Post-crash reconciliation never trusts the caller: minimum heartbeat age is server-side (>= 30 s in production)
// and every release additionally needs positive OS socket evidence (DrainProbe.SocketSafe).
var reconcileMinAge = TimeSpan.FromSeconds(testMode ? conf.GetValue("Mimamsa:Test:ReconcileMinAgeSec", 5)
                                                    : Math.Max(30, conf.GetValue("Mimamsa:Reconcile:MinAgeSec", 30)));
// Bounded kernel send buffer (production default 32 KiB requested; Linux reports/uses 2x). Together with the RST of
// active affected streams at FENCE this bounds post-acknowledgement egress of a withdrawn copy to what a finished
// response still has queued in the server kernel (<= effective SO_SNDBUF). 0 = OS default (unbounded by us).
int listenSndBuf = conf.GetValue("Mimamsa:Transport:ListenSendBufferBytes", 32 * 1024);
var dataSource = new NpgsqlDataSourceBuilder(cs).Build();
var ledger = new CreditLedger(dataSource, credit);
var auth = new AuthStore(dataSource);
var state = new ServingState();
var vault = new Vault(conf["Mimamsa:VaultRoot"] ?? Path.Combine(AppContext.BaseDirectory, "vault"));
var pendingDrains = new ConcurrentDictionary<string, DateTime>();
var active = new ActiveStreams();
// Liveness guard for per-slice reservation: admit at most N concurrent protected responses, where N responses of
// maximum accounted size fit inside the site cap. A slot is returned only after the connection's charges drained,
// so a started response can never stall on site credit held by other started responses.
long maxResponseWire = delivery.MaxRange + (long)Math.Ceiling(delivery.MaxRange / (double)delivery.Slice) * credit.HeaderAllowance;
var slots = new ResponseSlots(conf.GetValue("Mimamsa:Delivery:SlotGate", true)
    ? (int)Math.Max(1, credit.SiteCap / maxResponseWire)
    : 100_000);   // gate disabled (tests that race single-slice responses directly at the ledger)

builder.Services.AddSingleton(dataSource).AddSingleton(ledger).AddSingleton(auth).AddSingleton(state)
       .AddSingleton(vault).AddSingleton(delivery).AddSingleton(credit).AddSingleton(slots).AddSingleton(active);

// OS adapter: optional SO_SNDBUF on the listen socket (accepted sockets inherit it on Linux and Windows).
// Used to make slow-client / uncertain-transfer tests deterministic; 0 = OS default.
builder.WebHost.UseSockets(o =>
{
    if (listenSndBuf > 0)
        o.CreateBoundListenSocket = ep => { var s = SocketTransportOptions.CreateDefaultBoundListenSocket(ep); s.SendBufferSize = listenSndBuf; return s; };
});
builder.WebHost.ConfigureKestrel(k =>
{
    k.AddServerHeader = false;
    k.Limits.MaxConcurrentConnections = conf.GetValue<long>("Mimamsa:Transport:MaxConcurrentConnections", 1000);
    k.Limits.MaxResponseBufferSize = 64 * 1024;   // bounded app-side send buffer (one slice incl. header allowance)
    // Transport-termination observation: when a connection ends, its accepted charges drain after a grace.
    k.ConfigureEndpointDefaults(lo => lo.Use(next => async conn =>
    {
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
                finally { pendingDrains.TryRemove(pool, out _); slots.ReleaseFor(conn.ConnectionId); }
            });
        }
    }));
});

var app = builder.Build();

// ---- startup: schemas, optional reset (tests only), seed, in-memory eligibility mirror
await using (var c = await dataSource.OpenConnectionAsync())
await using (var cmd = new NpgsqlCommand(AuthStore.Schema, c)) await cmd.ExecuteNonQueryAsync();
// Single serving instance per database (the in-memory fence is process-local): hold a session advisory lock for the
// process lifetime; a second instance (e.g. an overlapped recycle) refuses to start instead of serving stale policy.
var instanceLockConn = await dataSource.OpenConnectionAsync();
await using (var lk = new NpgsqlCommand("SELECT pg_try_advisory_lock(hashtext('mimamsa-serving-instance'))", instanceLockConn))
{
    bool got = false;
    for (int i = 0; i < 50 && !got; i++) { got = (bool)(await lk.ExecuteScalarAsync())!; if (!got) await Task.Delay(200); }
    if (!got) throw new InvalidOperationException("another serving instance holds the instance lock; refusing to start");
}
bool testReset = testMode && conf.GetValue("Mimamsa:Test:ResetLedger", false);
await ledger.InitAsync(resetForTest: testReset);
var seed = conf["Mimamsa:SeedFile"];
if (!string.IsNullOrEmpty(seed))
{
    if (!testMode) throw new InvalidOperationException("Mimamsa:SeedFile is test-only; refusing to start outside Mimamsa:Test:Enabled");
    await Seed.ApplyAsync(dataSource, vault, seed, testReset);
}
DeliveryTrace.Start(conf["Mimamsa:Trace:Path"]);
await using (var c = await dataSource.OpenConnectionAsync())
{
    var w = new List<string>();
    await using (var q = new NpgsqlCommand("SELECT doc_id, copy_sha256 FROM vault_copies WHERE state='withdrawn'", c))
    await using (var r = await q.ExecuteReaderAsync())
        while (await r.ReadAsync()) w.Add(ServingState.Key(r.GetString(0), r.GetString(1)));
    await using var pq = new NpgsqlCommand("SELECT epoch, digest FROM serving_policy WHERE id = 1", c);
    await using var pr = await pq.ExecuteReaderAsync();
    await pr.ReadAsync();
    state.Load(w, pr.GetInt64(0), pr.GetString(1));
    // durable witness read at boot: the exporter turns this into 'recover' after a restart, or initial_witness
    DeliveryTrace.Emit("boot", "witness", new { epoch = state.Epoch, digest = state.Digest, instance = ledger.InstanceId });
}
_ = Task.Run(async () => { while (true) { try { await ledger.HeartbeatAsync(); } catch { } await Task.Delay(2000); } });
// Automatic, evidence-gated reconciliation of charges left by a previous (crashed) instance.
async Task<int> ReconcilePriorAsync()
{
    var drained = await ledger.ReconcilePriorInstancesAsync(reconcileMinAge, DrainProbe.SocketSafe);
    foreach (var (id, _, ev) in drained) DeliveryTrace.Emit("prove_release", "drain_probe", new { attempt = id.ToString(), proof = "reconciliation", evidence = ev });
    if (drained.Count > 0) DeliveryTrace.Flush();
    return drained.Count;
}
_ = Task.Run(async () => { while (true) { await Task.Delay(1000); try { await ReconcilePriorAsync(); } catch { } } });

// ---- v1 auth stub (P1 throughput endpoints only)
app.Use(async (ctx, next) =>
{
    if (ctx.Request.Path.StartsWithSegments("/api") && !ctx.Request.Path.StartsWithSegments("/api/v2"))
    {
        if (ctx.Request.Headers.Authorization.ToString() != $"Bearer {token}") { ctx.Response.StatusCode = 401; return; }
    }
    await next();
});

app.MapGet("/health", () => Results.Text("ok"));

app.MapGet("/api/search", async (string q, int? limit, NpgsqlDataSource db) =>
{
    var lim = Math.Clamp(limit ?? 10, 1, 50);
    await using var cmd = db.CreateCommand(@"
        WITH q AS (SELECT replace(plainto_tsquery('english', $1)::text, '&', '|')::tsquery AS q)
        SELECT u.doc_id, max(ts_rank(u.tsv, q.q)) AS s FROM units u, q
        WHERE u.tsv @@ q.q GROUP BY u.doc_id ORDER BY s DESC LIMIT $2");
    cmd.Parameters.AddWithValue(q);
    cmd.Parameters.AddWithValue(lim);
    var res = new List<object>();
    await using var r = await cmd.ExecuteReaderAsync();
    while (await r.ReadAsync()) res.Add(new { doc_id = r.GetString(0), score = r.GetFloat(1) });
    return Results.Json(new { q, results = res });
});

app.MapGet("/api/documents/{id}", async (string id, NpgsqlDataSource db) =>
{
    await using var cmd = db.CreateCommand("SELECT meta::text FROM documents WHERE doc_id = $1");
    cmd.Parameters.AddWithValue(id);
    var meta = (string?)await cmd.ExecuteScalarAsync();
    return meta is null ? Results.NotFound() : Results.Text(meta, "application/json");
});

app.MapGet("/api/documents/{id}/pdf", async (string id, NpgsqlDataSource db) =>
{
    await using var cmd = db.CreateCommand("SELECT pdf_file FROM documents WHERE doc_id = $1");
    cmd.Parameters.AddWithValue(id);
    var name = await cmd.ExecuteScalarAsync() as string;
    if (name is null) return Results.NotFound();
    var full = Path.GetFullPath(Path.Combine(pdfRoot, name));
    if (!full.StartsWith(pdfRoot + Path.DirectorySeparatorChar) || !File.Exists(full)) return Results.NotFound();
    return Results.File(full, "application/pdf", enableRangeProcessing: true);
});

// ---- v2 protected delivery (R2-N01)
ProtectedDelivery.Map(app);

// ---- admin (synthetic test control): withdrawal fence, prior-instance reconciliation, ledger view
async Task<Principal?> Admin(HttpContext ctx)
{
    var h = ctx.Request.Headers.Authorization.ToString();
    var p = await auth.AuthenticateAsync(h.StartsWith("Bearer ") ? h[7..] : null);
    return p is { IsAdmin: true } ? p : null;
}
app.MapPost("/admin/withdraw", async (HttpContext ctx, string doc, string sha) =>
{
    if (await Admin(ctx) is null) return Results.StatusCode(401);
    var shaC = ServingState.CanonicalSha(sha);
    if (shaC is null || string.IsNullOrWhiteSpace(doc)) return Results.Json(new { error = "invalid_copy_identity" }, statusCode: 400);
    // typed precheck: unknown copy -> 404, no protocol entry, no epoch change
    string? curState;
    await using (var c0 = await dataSource.OpenConnectionAsync())
    await using (var q0 = new NpgsqlCommand("SELECT state FROM vault_copies WHERE doc_id=$1 AND copy_sha256=$2", c0))
    { q0.Parameters.AddWithValue(doc); q0.Parameters.AddWithValue(shaC); curState = (string?)await q0.ExecuteScalarAsync(); }
    if (curState is null) return Results.Json(new { error = "unknown_copy", doc, sha = shaC }, statusCode: 404);
    if (curState == "withdrawn")
        return Results.Json(new { status = "already_withdrawn", epoch = state.Epoch, digest = state.Digest, changed = false });
    var op = "withdraw-" + Guid.NewGuid().ToString("N")[..8];
    long admittedMs = 0; int resetStreams = 0;
    var (epoch, digest, changed) = await state.WithdrawAsync(doc, shaC,
        durableCas: async () =>
        {
            await using var c = await dataSource.OpenConnectionAsync();
            await using var tx = await c.BeginTransactionAsync();
            long e0; string d0;
            await using (var q = new NpgsqlCommand("SELECT epoch, digest FROM serving_policy WHERE id = 1 FOR UPDATE", c, tx))
            await using (var r = await q.ExecuteReaderAsync()) { await r.ReadAsync(); e0 = r.GetInt64(0); d0 = r.GetString(1); }
            int rows;
            await using (var u = new NpgsqlCommand("UPDATE vault_copies SET state='withdrawn', fence_seq=fence_seq+1 WHERE doc_id=$1 AND copy_sha256=$2 AND state='eligible'", c, tx))
            { u.Parameters.AddWithValue(doc); u.Parameters.AddWithValue(shaC); rows = await u.ExecuteNonQueryAsync(); }
            if (rows != 1) { await tx.RollbackAsync(); return (e0, d0, false); }   // concurrently withdrawn: idempotent, no bump
            var d1 = "state-" + Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(
                         System.Text.Encoding.UTF8.GetBytes($"{d0}|{op}|{doc}|{shaC}|{e0 + 1}")))[..16].ToLowerInvariant();
            await using (var cas = new NpgsqlCommand("UPDATE serving_policy SET epoch = $1, digest = $2 WHERE id = 1 AND epoch = $3", c, tx))
            {
                cas.Parameters.AddWithValue(e0 + 1); cas.Parameters.AddWithValue(d1); cas.Parameters.AddWithValue(e0);
                if (await cas.ExecuteNonQueryAsync() != 1) throw new InvalidOperationException("witness CAS failed");
            }
            await tx.CommitAsync();
            await using var c2 = await dataSource.OpenConnectionAsync();
            await using var rb = new NpgsqlCommand("SELECT epoch, digest FROM serving_policy WHERE id = 1", c2);
            await using var rr = await rb.ExecuteReaderAsync(); await rr.ReadAsync();
            return (rr.GetInt64(0), rr.GetString(1), true);
        },
        emitAdmit: () => { admittedMs = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds();
                           DeliveryTrace.Emit("admit", "policy_probe", new { operation = op, copy = shaC, monotonic_ms = admittedMs }); },
        emitFence: (e, d) => DeliveryTrace.Emit("fence", "witness", new { operation = op, copy = shaC, epoch = e, digest = d }),
        // cut in-flight egress of the withdrawn copy (RST discards kernel-queued bytes) BEFORE acknowledging
        onFenced: () => { resetStreams = active.ResetAll(ServingState.Key(doc, shaC)); });
    DeliveryTrace.Flush();
    return Results.Json(new { operation = op, epoch, digest, changed, admitted_ms = admittedMs, reset_streams = resetStreams });
});
app.MapPost("/admin/reconcile-prior", async (HttpContext ctx) =>
{
    if (await Admin(ctx) is null) return Results.StatusCode(401);
    return Results.Json(new { drained = await ReconcilePriorAsync(), min_age_s = reconcileMinAge.TotalSeconds });
});
app.MapGet("/admin/ledger", async (HttpContext ctx) =>
{
    if (await Admin(ctx) is null) return Results.StatusCode(401);
    var site = await ledger.PoolAsync(CreditLedger.SitePool);
    _ = slots;
    return Results.Json(new { instance = ledger.InstanceId, site = new { site.cap, site.reserved, site.charged }, response_slots = slots.Capacity, slots_free = slots.Free, pending_drains = pendingDrains.Count, epoch = state.Epoch, digest = state.Digest });
});

app.Run();
