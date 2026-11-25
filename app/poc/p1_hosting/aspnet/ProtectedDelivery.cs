// Kestrel-specific transport adapter for protected PDF range delivery (R2-N01 PoC).
// Platform-neutral rules live in MimamsaPoc.Core; this file only binds them to ASP.NET Core / Kestrel:
//   - per-request bearer authentication and grant check (AuthStore)
//   - strict single bounded range (ByteRange), exact 206 Content-Range/Content-Length, no-store, no validators
//   - atomic connection+site credit reservation before any byte is handed to Kestrel (CreditLedger)
//   - each <= Slice bytes is copied into Kestrel's PipeWriter under the writer-priority guard (ServingState);
//     FlushAsync (which may block on a slow client) runs OUTSIDE the guard
//   - settlement: ACCEPTED(k) / RELEASED(0) / UNCERTAIN(full) ; charges drain only on observed transport termination
using System.Collections.Concurrent;
using System.IO.Pipelines;
using MimamsaPoc.Core;
using Npgsql;

namespace MimamsaPocApi;

public sealed record DeliveryConfig(int MaxRange, int Slice, int HeaderAllowance, int DrainGraceMs);

public sealed class ResponseSlots
{
    readonly SemaphoreSlim _s; readonly ConcurrentDictionary<string, bool> _held = new();
    public int Capacity { get; }
    public int Free => _s.CurrentCount;
    public ResponseSlots(int n) { Capacity = n; _s = new SemaphoreSlim(n, n); }
    public bool TryAcquire(string connectionId) { if (!_s.Wait(0)) return false; _held[connectionId] = true; return true; }
    public void ReleaseFor(string connectionId) { if (_held.TryRemove(connectionId, out _)) _s.Release(); }
}

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
                                      ServingState state, Vault vault, DeliveryConfig cfg, ResponseSlots slots, ILoggerFactory lf)
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
        if (!slots.TryAcquire(ctx.Connection.Id)) { res.StatusCode = 503; res.Headers.RetryAfter = "1"; return; }   // returned after drain
        var connPool = CreditLedger.ConnPoolId(ledger.InstanceId, ctx.Connection.Id);
        string connLabel = $"c{ctx.Connection.RemotePort}", stream = ctx.TraceIdentifier;
        var writer = res.BodyWriter;
        long wireOffset = 0;          // accounted wire offset within this response stream
        bool headersSet = false;
        int off = 0;
        var log = lf.CreateLogger("delivery");

        while (off < len)
        {
            int n = Math.Min(cfg.Slice, len - off);
            long amount = n + cfg.HeaderAllowance;      // worst-case charged wire bytes for this attempt
            // ---- reservation (atomic connection + site credit) with in-transaction policy recheck
            Reservation? r = null; long resEpoch = 0; bool policyDenied = false;
            var deadline = DateTime.UtcNow.AddMilliseconds(2000);
            while (true)
            {
                policyDenied = false;
                long wo = wireOffset;
                r = await ledger.TryReserveAsync(connPool, amount, p.SessionId, docId, copy.Sha256, start + off, n, async (c, tx, id) =>
                {
                    await using var q = new Npgsql.NpgsqlCommand("SELECT epoch FROM serving_policy WHERE id = 1 FOR SHARE", c, tx);
                    long dbEpoch = (long)(await q.ExecuteScalarAsync())!;
                    return state.UnderReadGuard(eligible =>
                    {
                        if (!eligible || state.Epoch != dbEpoch) { policyDenied = true; return false; }
                        resEpoch = dbEpoch;
                        DeliveryTrace.Emit("reserve", "ledger", new { attempt = id.ToString(), connection = connLabel, stream, copy = copy.Sha256,
                                                                    offset = wo, size = amount, epoch = dbEpoch });
                        return true;
                    }, docId, copy.Sha256);
                });
                if (r is not null) break;
                bool withdrawn = policyDenied && state.UnderReadGuard(e => !e && !state.Pending, docId, copy.Sha256);
                if (withdrawn) { if (!headersSet) { res.StatusCode = 404; return; } ctx.Abort(); return; }
                if (!headersSet && !policyDenied) { res.StatusCode = 503; res.Headers.RetryAfter = "1"; return; }  // no credit: no bytes
                if (DateTime.UtcNow > deadline) { log.LogWarning("credit/policy wait expired mid-response; aborting"); ctx.Abort(); return; }
                await Task.Delay(20);    // pending withdrawal or credit exhausted mid-response: bounded wait, never a short 206
            }

            // ---- handoff under the guard: fresh recheck (enter), then exact slice into the bounded Kestrel pipe (accept)
            long acceptedWire = 0;
            bool ok = state.UnderReadGuard(eligible =>
            {
                if (!eligible || state.Epoch != resEpoch) return false;
                DeliveryTrace.Emit("enter", "policy_probe", new { attempt = r.Id.ToString() });
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
                acceptedWire = amount;
                DeliveryTrace.Emit("accept", "terminal", new { attempt = r.Id.ToString(), offset = wireOffset, size = amount });
                return true;
            }, docId, copy.Sha256);

            if (!ok)
            {
                // zero transfer is established (nothing was handed to the pipe for this attempt)
                if (await ledger.SettleAsync(r, Settlement.ReleasedZeroTransfer, 0, "policy changed before handoff"))
                    DeliveryTrace.Emit("settle", "ledger", new { attempt = r.Id.ToString(), outcome = "zero" });
                bool withdrawn = state.UnderReadGuard(e => !e, docId, copy.Sha256);
                if (withdrawn)
                {
                    if (!headersSet) { res.StatusCode = 404; return; }
                    ctx.Abort(); return;                       // mid-response withdrawal: stop, no fresh bytes
                }
                continue;                                      // epoch moved (other copy withdrawn): re-reserve under new epoch
            }
            wireOffset += acceptedWire; off += n;
            try
            {
                FlushResult fr = await writer.FlushAsync(ctx.RequestAborted);   // outside the guard; may block on slow clients
                if (fr.IsCanceled || (fr.IsCompleted && off < len)) throw new OperationCanceledException("client gone");
            }
            catch (Exception ex) when (ex is OperationCanceledException or IOException or InvalidOperationException
                                       or Microsoft.AspNetCore.Connections.ConnectionResetException)
            {
                // completion lost / client vanished: retain the FULL reservation until termination evidence; never retry
                if (await ledger.SettleAsync(r, Settlement.Uncertain, acceptedWire, $"uncertain: {ex.GetType().Name}"))
                    DeliveryTrace.Emit("settle", "ledger", new { attempt = r.Id.ToString(), outcome = "uncertain" });
                log.LogWarning("uncertain transfer {Res} {Type}", r.Id, ex.GetType().Name);
                ctx.Abort();
                return;
            }
            if (await ledger.SettleAsync(r, Settlement.Accepted, acceptedWire, "slice handed to transport and flushed"))
                DeliveryTrace.Emit("settle", "ledger", new { attempt = r.Id.ToString(), outcome = "accepted", size = acceptedWire });
        }
    }
}
