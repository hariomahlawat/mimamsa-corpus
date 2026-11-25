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
var delivery = new DeliveryConfig(conf.GetValue("Mimamsa:Delivery:MaxRange", 128 * 1024), conf.GetValue("Mimamsa:Delivery:Slice", 64 * 1024),
                                  (int)credit.HeaderAllowance, conf.GetValue("Mimamsa:Delivery:DrainGraceMs", 250));
int listenSndBuf = conf.GetValue("Mimamsa:Transport:ListenSendBufferBytes", 0);
var dataSource = new NpgsqlDataSourceBuilder(cs).Build();
var ledger = new CreditLedger(dataSource, credit);
var auth = new AuthStore(dataSource);
var state = new ServingState();
var vault = new Vault(conf["Mimamsa:VaultRoot"] ?? Path.Combine(AppContext.BaseDirectory, "vault"));
var pendingDrains = new ConcurrentDictionary<string, DateTime>();

builder.Services.AddSingleton(dataSource).AddSingleton(ledger).AddSingleton(auth).AddSingleton(state)
       .AddSingleton(vault).AddSingleton(delivery).AddSingleton(credit);

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
    k.Limits.MaxResponseBufferSize = delivery.Slice;   // bounded app-side send buffer
    // Transport-termination observation: when a connection ends, its accepted charges drain after a grace.
    k.ConfigureEndpointDefaults(lo => lo.Use(next => async conn =>
    {
        try { await next(conn); }
        finally
        {
            var pool = CreditLedger.ConnPoolId(ledger.InstanceId, conn.ConnectionId);
            var ended = DateTime.UtcNow;
            pendingDrains[pool] = ended;
            _ = Task.Run(async () =>
            {
                await Task.Delay(delivery.DrainGraceMs);
                try { await ledger.DrainConnectionAsync(pool, $"kestrel connection {conn.ConnectionId} terminated {ended:O}; grace {delivery.DrainGraceMs} ms"); }
                finally { pendingDrains.TryRemove(pool, out _); }
            });
        }
    }));
});

var app = builder.Build();

// ---- startup: schemas, optional reset (tests only), seed, in-memory eligibility mirror
await using (var c = await dataSource.OpenConnectionAsync())
await using (var cmd = new NpgsqlCommand(AuthStore.Schema, c)) await cmd.ExecuteNonQueryAsync();
await ledger.InitAsync(resetForTest: conf.GetValue("Mimamsa:Test:ResetLedger", false));
var seed = conf["Mimamsa:SeedFile"];
if (!string.IsNullOrEmpty(seed)) await Seed.ApplyAsync(dataSource, vault, seed);
await using (var c = await dataSource.OpenConnectionAsync())
await using (var q = new NpgsqlCommand("SELECT doc_id, copy_sha256 FROM vault_copies WHERE state='withdrawn'", c))
await using (var r = await q.ExecuteReaderAsync())
{
    var w = new List<string>(); while (await r.ReadAsync()) w.Add(ServingState.Key(r.GetString(0), r.GetString(1)));
    state.LoadWithdrawn(w);
}
_ = Task.Run(async () => { while (true) { try { await ledger.HeartbeatAsync(); } catch { } await Task.Delay(2000); } });

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
    var seq = await state.WithdrawAsync(doc, sha, async () =>
    {
        await using var c = await dataSource.OpenConnectionAsync();
        await using var u = new NpgsqlCommand("UPDATE vault_copies SET state='withdrawn', fence_seq=fence_seq+1 WHERE doc_id=$1 AND copy_sha256=$2", c);
        u.Parameters.AddWithValue(doc); u.Parameters.AddWithValue(sha); await u.ExecuteNonQueryAsync();
    });
    return Results.Json(new { fence_seq = seq, at = DateTime.UtcNow });
});
app.MapPost("/admin/reconcile-prior", async (HttpContext ctx, string evidence, int minAgeSec) =>
{
    if (await Admin(ctx) is null) return Results.StatusCode(401);
    return Results.Json(new { drained = await ledger.ReconcilePriorInstancesAsync(evidence, TimeSpan.FromSeconds(minAgeSec)) });
});
app.MapGet("/admin/ledger", async (HttpContext ctx) =>
{
    if (await Admin(ctx) is null) return Results.StatusCode(401);
    var site = await ledger.PoolAsync(CreditLedger.SitePool);
    return Results.Json(new { instance = ledger.InstanceId, site = new { site.cap, site.reserved, site.charged }, pending_drains = pendingDrains.Count, fence_seq = state.FenceSeq });
});

app.Run();
