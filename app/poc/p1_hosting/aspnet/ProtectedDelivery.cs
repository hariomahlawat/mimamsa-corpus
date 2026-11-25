// Kestrel-specific transport adapter for protected PDF range delivery (R2-N01 PoC).
// Platform-neutral rules live in MimamsaPoc.Core; this file only binds them to ASP.NET Core / Kestrel:
//   - per-request bearer authentication and grant check (AuthStore)
//   - strict single bounded range (ByteRange), exact 206 Content-Range/Content-Length, no-store, no validators
//   - atomic connection+site credit reservation before any byte is handed to Kestrel (CreditLedger)
//   - each <= Slice bytes is copied into Kestrel's PipeWriter under the writer-priority guard (ServingState);
//     FlushAsync (which may block on a slow client) runs OUTSIDE the guard
//   - settlement: ACCEPTED(k) / RELEASED(0) / UNCERTAIN(full) ; charges drain only on observed transport termination
using System.IO.Pipelines;
using MimamsaPoc.Core;

namespace MimamsaPocApi;

public sealed record DeliveryConfig(int MaxRange, int Slice, int HeaderAllowance, int DrainGraceMs);

public static class ProtectedDelivery
{
    static string? Bearer(HttpContext ctx)
    {
        var h = ctx.Request.Headers.Authorization.ToString();
        return h.StartsWith("Bearer ", StringComparison.Ordinal) ? h[7..] : null;
    }

    static void NoStore(HttpResponse r)
    {
        r.Headers.CacheControl = "no-store, private";
        r.Headers.Pragma = "no-cache";
        r.Headers["X-Content-Type-Options"] = "nosniff";
    }

    static IResult Generic(int status) => Results.StatusCode(status);   // empty body: no content, no size disclosure

    public static void Map(WebApplication app)
    {
        // Bounded metadata bootstrap: exact eligible copy identity + length + range profile, only for a granted session.
        app.MapGet("/api/v2/documents/{docId}/pdf-meta", async (HttpContext ctx, string docId, AuthStore auth, DeliveryConfig cfg) =>
        {
            NoStore(ctx.Response);
            var p = await auth.AuthenticateAsync(Bearer(ctx));
            if (p is null) return Generic(401);
            var copy = await auth.AuthorizedCopyAsync(p, docId, null);
            if (copy is null) return Generic(404);
            return Results.Json(new { doc_id = copy.DocId, copy_sha256 = copy.Sha256, length = copy.Length,
                                      range_supported = true, max_range = cfg.MaxRange, chunk = cfg.Slice });
        });

        app.MapGet("/api/v2/documents/{docId}/copies/{sha}/range", ServeRangeAsync);
    }

    static async Task ServeRangeAsync(HttpContext ctx, string docId, string sha, AuthStore auth, CreditLedger ledger,
                                      ServingState state, Vault vault, DeliveryConfig cfg, ILoggerFactory lf)
    {
        var res = ctx.Response;
        NoStore(res);
        res.Headers.Connection = "close";   // one bounded response per connection; termination = drain evidence
        var p = await auth.AuthenticateAsync(Bearer(ctx));
        if (p is null) { res.StatusCode = 401; return; }
        var copy = await auth.AuthorizedCopyAsync(p, docId, sha);
        if (copy is null) { res.StatusCode = 404; return; }          // not granted, unknown, or withdrawn: same answer
        switch (ByteRange.Parse(ctx.Request.Headers.Range.ToString(), copy.Length, cfg.MaxRange, out var start, out var end))
        {
            case RangeParse.Ok: break;
            case RangeParse.Unsatisfiable:
                res.StatusCode = 416; res.Headers.ContentRange = $"bytes */{copy.Length}"; return;   // caller is authorized
            default:
                res.StatusCode = 400; return;  // missing, malformed, multi-range or oversized: no full-body fallback
        }
        int len = checked((int)(end - start + 1));
        // PREPARED: stage the immutable bytes outside any guard
        var bytes = await vault.ReadSliceAsync(copy.Sha256, start, len);
        var connPool = CreditLedger.ConnPoolId(ledger.InstanceId, ctx.Connection.Id);
        var reservation = await ledger.TryReserveAsync(connPool, len + cfg.HeaderAllowance, p.SessionId, docId, copy.Sha256, start, len);
        if (reservation is null) { res.StatusCode = 503; res.Headers.RetryAfter = "1"; return; }   // no credit: no bytes

        var writer = res.BodyWriter;
        long accepted = 0;
        bool headersSet = false;
        try
        {
            for (int off = 0; off < len; off += cfg.Slice)
            {
                int n = Math.Min(cfg.Slice, len - off);
                bool ok = state.TryAcceptUnderGuard(docId, copy.Sha256, () =>
                {
                    if (!headersSet)
                    {
                        res.StatusCode = 206;
                        res.ContentType = "application/pdf";
                        res.ContentLength = len;
                        res.Headers.ContentRange = $"bytes {start}-{end}/{copy.Length}";
                        res.Headers.AcceptRanges = "bytes";
                        headersSet = true;
                    }
                    var src = bytes.AsSpan(off, n);
                    while (!src.IsEmpty)
                    {
                        var dst = writer.GetSpan(Math.Min(src.Length, 16 * 1024));
                        int c = Math.Min(dst.Length, src.Length);
                        src[..c].CopyTo(dst); writer.Advance(c); src = src[c..];
                    }
                    accepted += n;   // ownership of these exact bytes now belongs to the Kestrel pipe
                });
                if (!ok)
                {
                    if (accepted == 0)
                    {
                        await ledger.SettleAsync(reservation, Settlement.ReleasedZeroTransfer, 0, "withdrawn before first byte");
                        res.StatusCode = 404; return;
                    }
                    await ledger.SettleAsync(reservation, Settlement.Accepted, accepted, "withdrawn mid-response: aborted after accepted prefix");
                    ctx.Abort();
                    return;
                }
                FlushResult fr = await writer.FlushAsync(ctx.RequestAborted);   // outside the guard; may block on slow clients
                if (fr.IsCanceled || fr.IsCompleted && off + n < len) throw new OperationCanceledException("client gone");
            }
            await ledger.SettleAsync(reservation, Settlement.Accepted, accepted, "complete response handed to transport");
        }
        catch (Exception ex) when (ex is OperationCanceledException or IOException or InvalidOperationException
                                   or Microsoft.AspNetCore.Connections.ConnectionResetException)
        {
            // Outcome unknown (client vanished / reset during flush): keep the FULL reservation charged until the
            // transport connection is observed terminated. Never refund here and never retry this range.
            await ledger.SettleAsync(reservation, Settlement.Uncertain, accepted, $"uncertain: {ex.GetType().Name} after {accepted} bytes accepted");
            lf.CreateLogger("delivery").LogWarning("uncertain transfer {Res} {Type}", reservation.Id, ex.GetType().Name);
            ctx.Abort();
        }
    }
}
