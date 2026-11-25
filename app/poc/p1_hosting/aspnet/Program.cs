// Mimamsa P1 hosting PoC: ASP.NET Core (.NET 10 LTS) minimal API.
// Endpoints: /health, /api/search, /api/documents/{id}, /api/documents/{id}/pdf (range-capable), auth stub.
// Windows: UseWindowsService() is a no-op unless the process is started by the Service Control Manager.
using System.Text.Json;
using Npgsql;

var builder = WebApplication.CreateSlimBuilder(args);
builder.Host.UseWindowsService(o => o.ServiceName = "MimamsaPocApi");
builder.Logging.ClearProviders();
builder.Logging.AddConsole();
builder.Logging.SetMinimumLevel(LogLevel.Warning);

var cs = builder.Configuration["Mimamsa:Db"] ?? "Host=127.0.0.1;Port=55432;Username=poc;Database=poc;Maximum Pool Size=32;Minimum Pool Size=4";
var pdfRoot = Path.GetFullPath(builder.Configuration["Mimamsa:PdfRoot"] ?? "pdfstore");
var token = builder.Configuration["Mimamsa:DevToken"] ?? "dev-token";
var dataSource = new NpgsqlDataSourceBuilder(cs).Build();
builder.Services.AddSingleton(dataSource);

var app = builder.Build();

// Auth stub: a fixed bearer token. Placeholder for Windows Integrated Auth / local accounts later.
app.Use(async (ctx, next) =>
{
    if (ctx.Request.Path.StartsWithSegments("/api"))
    {
        var h = ctx.Request.Headers.Authorization.ToString();
        if (h != $"Bearer {token}") { ctx.Response.StatusCode = 401; return; }
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

app.Run();
