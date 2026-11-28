// Kestrel transport adapter for protected original delivery (R2-N01), refactored from
// app/poc/p1_hosting/aspnet/ProtectedDelivery.cs for B1:
//   - authentication is the B1 server-side session (HttpOnly SameSite=Strict cookie), checked per request;
//   - the authorised copy is the importer-verified copy of a PUBLISHED document in the ACTIVE generation (or a copy
//     held by an earlier activated generation, for exact citation opening, ASR-E06) and not withdrawn;
//   - unchanged rules: one strict bounded single range, exact 206, no-store, no validators, credit reserved before any
//     byte is handed to Kestrel, slices copied under the writer-priority guard, settlement ACCEPTED/RELEASED/UNCERTAIN;
//   - review N1: at a withdrawal FENCE, connections that already finished a response for the copy but have not yet
//     drained are also reset (RST), not only in-flight streams.
using System.Collections.Concurrent;
using System.IO.Pipelines;
using Microsoft.AspNetCore.Connections;
using Mimamsa.Core.Delivery;
using Mimamsa.Core.Identity;

namespace Mimamsa.Web;

public sealed record DeliveryConfig(int MaxRange, int Slice, int HeaderAllowance, int DrainGraceMs, bool TestMode = false,
                                    int TestPauseMs = 1500, int MaxStreamsPerSession = 4);

/// In-flight protected streams per copy, plus connections that served the copy and have not yet drained (N1).
public sealed class ActiveStreams
{
    readonly ConcurrentDictionary<string, ConcurrentDictionary<string, HttpContext>> _by = new();
    readonly ConcurrentDictionary<string, int> _perSession = new();
    readonly ConcurrentDictionary<string, ConnectionContext> _connections = new();
    readonly ConcurrentDictionary<string, ConcurrentDictionary<string, byte>> _servedBy = new();   // copy key -> connection ids

    public void Add(string key, string stream, HttpContext ctx) => _by.GetOrAdd(key, _ => new())[stream] = ctx;
    public void Remove(string key, string stream) { if (_by.TryGetValue(key, out var m)) m.TryRemove(stream, out _); }
    public void ConnectionOpened(ConnectionContext c) => _connections[c.ConnectionId] = c;
    public void ConnectionDrained(string connectionId)
    {
        _connections.TryRemove(connectionId, out _);
        foreach (var (_, set) in _servedBy) set.TryRemove(connectionId, out _);
    }
    public void Served(string key, string connectionId) => _servedBy.GetOrAdd(key, _ => new())[connectionId] = 0;

    internal static void Rst(Microsoft.AspNetCore.Http.Features.IFeatureCollection f)
    {
        try
        {
            var sock = f.Get<Microsoft.AspNetCore.Connections.Features.IConnectionSocketFeature>()?.Socket;
            if (sock is not null) sock.LingerState = new System.Net.Sockets.LingerOption(true, 0);   // RST: discard queued bytes
        }
        catch (Exception) { }
    }

    public int ResetAll(string key)
    {
        int n = 0;
        if (_by.TryGetValue(key, out var m))
            foreach (var (_, ctx) in m) { Rst(ctx.Features); ctx.Abort(); n++; }
        if (_servedBy.TryGetValue(key, out var conns))
            foreach (var id in conns.Keys)
                if (_connections.TryGetValue(id, out var c)) { Rst(c.Features); c.Abort(); n++; }
        return n;
    }

    public bool TryEnterSession(string session, int max)
    {
        while (true)
        {
            int cur = _perSession.GetOrAdd(session, 0);
            if (cur >= max) return false;
            if (_perSession.TryUpdate(session, cur + 1, cur)) return true;
        }
    }
    public void LeaveSession(string session) => _perSession.AddOrUpdate(session, 0, (_, v) => Math.Max(0, v - 1));
}

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
    public static void NoStore(HttpResponse r)
    {
        r.Headers.CacheControl = "no-store, private";
        r.Headers.Pragma = "no-cache";
        r.Headers["X-Content-Type-Options"] = "nosniff";
    }

    public static void Map(WebApplication app)
    {
        // Bounded metadata bootstrap: exact eligible copy identity + length + range profile.
        app.MapGet("/api/v2/documents/{docId}/pdf-meta", async (HttpContext ctx, string docId, string? copy, AppServices s, DeliveryConfig cfg) =>
        {
            NoStore(ctx.Response);
            var p = await s.AuthenticateAsync(ctx);
            if (p is null) return Results.StatusCode(401);
            var c = s.AuthorizedCopy(docId, copy);
            if (c is null) return Results.StatusCode(404);
            return Results.Json(new { doc_id = docId, copy_sha256 = c.Value.sha, length = c.Value.length, page_count = c.Value.pages,
                                      range_supported = true, max_range = cfg.MaxRange, chunk = cfg.Slice });
        });
        app.MapGet("/api/v2/documents/{docId}/copies/{sha}/range", ServeRangeAsync);
    }

    static async Task ServeRangeAsync(HttpContext ctx, string docId, string sha, AppServices s, DeliveryConfig cfg,
                                      ResponseSlots slots, ActiveStreams active, ILoggerFactory lf)
    {
        var res = ctx.Response;
        NoStore(res);
        res.Headers.Connection = "close";   // one bounded response per connection; termination = drain evidence
        var p = await s.AuthenticateAsync(ctx);
        if (p is null) { res.StatusCode = 401; return; }
        var shaC = ServingState.CanonicalSha(sha);
        var copy = shaC is null ? null : s.AuthorizedCopy(docId, shaC);
        if (copy is null) { res.StatusCode = 404; return; }          // unknown, unpublished or withdrawn: same answer
        if (cfg.TestMode && ctx.Request.Headers["X-Mimamsa-Test-Fail"] == "range") { ctx.Abort(); return; }   // UX-15 test control
        switch (ByteRange.Parse(ctx.Request.Headers.Range.ToString(), copy.Value.length, cfg.MaxRange, out var start, out var end))
        {
            case RangeParse.Ok: break;
            case RangeParse.Unsatisfiable:
                res.StatusCode = 416; res.Headers.ContentRange = $"bytes */{copy.Value.length}"; return;
            default:
                res.StatusCode = 400; return;  // missing, malformed, multi-range or oversized: no full-body fallback
        }
        if (!active.TryEnterSession(p.SessionId, cfg.MaxStreamsPerSession)) { res.StatusCode = 503; res.Headers.RetryAfter = "1"; return; }
        if (!slots.TryAcquire(ctx.Connection.Id)) { active.LeaveSession(p.SessionId); res.StatusCode = 503; res.Headers.RetryAfter = "1"; return; }
        var copyKey = ServingState.Key(docId, copy.Value.sha);
        active.Add(copyKey, ctx.TraceIdentifier, ctx);
        active.Served(copyKey, ctx.Connection.Id);
        try { await ServeStagedAsync(ctx, docId, copy.Value.sha, copy.Value.length, start, end, p, s, cfg, lf); }
        finally { active.Remove(copyKey, ctx.TraceIdentifier); active.LeaveSession(p.SessionId); }
    }

    static async Task ServeStagedAsync(HttpContext ctx, string docId, string sha, long length, long start, long end, Principal p,
                                       AppServices s, DeliveryConfig cfg, ILoggerFactory lf)
    {
        var res = ctx.Response;
        var ledger = s.Ledger; var state = s.State;
        string hook = cfg.TestMode ? ctx.Request.Headers["X-Mimamsa-Test-Pause"].ToString() : "";
        int len = checked((int)(end - start + 1));
        var bytes = await s.Vault.ReadSliceAsync(sha, start, len);        // PREPARED outside any guard
        var connPool = CreditLedger.ConnPoolId(ledger.InstanceId, ctx.Connection.Id);
        string connLabel = $"c{ctx.Connection.RemotePort}", stream = ctx.TraceIdentifier;
        var writer = res.BodyWriter;
        long wireOffset = 0; bool headersSet = false; int off = 0;
        var log = lf.CreateLogger("delivery");
        while (off < len)
        {
            if (ctx.RequestAborted.IsCancellationRequested) { ctx.Abort(); return; }
            int n = Math.Min(cfg.Slice, len - off);
            long amount = n + cfg.HeaderAllowance;
            Reservation? r = null; long resEpoch = 0; bool policyDenied;
            var deadline = DateTime.UtcNow.AddMilliseconds(2000);
            while (true)
            {
                policyDenied = false;
                long wo = wireOffset;
                r = await ledger.TryReserveAsync(connPool, amount, p.SessionId, docId, sha, start + off, n, async (c, tx, id) =>
                {
                    await using var q = new Npgsql.NpgsqlCommand("SELECT epoch FROM serving_policy WHERE id = 1 FOR SHARE", c, tx);
                    long dbEpoch = (long)(await q.ExecuteScalarAsync())!;
                    return state.UnderReadGuard(eligible =>
                    {
                        if (!eligible || state.Epoch != dbEpoch) { policyDenied = true; return false; }
                        resEpoch = dbEpoch;
                        DeliveryTrace.Emit("reserve", "ledger", new { attempt = id.ToString(), connection = connLabel, stream, copy = sha, offset = wo, size = amount, epoch = dbEpoch });
                        return true;
                    }, docId, sha);
                }, ctx.Connection.LocalPort, ctx.Connection.RemotePort);
                if (r is not null) break;
                bool withdrawn = policyDenied && state.UnderReadGuard(e => !e && !state.Pending, docId, sha);
                if (withdrawn) { if (!headersSet) { res.StatusCode = 404; return; } ctx.Abort(); return; }
                if (!headersSet && !policyDenied) { res.StatusCode = 503; res.Headers.RetryAfter = "1"; return; }
                if (DateTime.UtcNow > deadline) { log.LogWarning("credit/policy wait expired mid-response; aborting"); ctx.Abort(); return; }
                await Task.Delay(20);
            }
            if (hook == "before-enter" && off == 0)
            { try { await Task.Delay(cfg.TestPauseMs, ctx.RequestAborted); } catch (OperationCanceledException) { } }
            // C16 Stage 3 (activation only): the streaming response boundary. The CURRENT signed exclusion state is
            // re-read immediately before each slice is handed to the transport; an excluded copy stops here (bounded
            // drain: what was handed over before this check is not recalled) and the connection is reset.
            if (s.BoundaryExcludedNow(ctx, docId, sha))
            {
                if (await ledger.SettleAsync(r, Settlement.ReleasedZeroTransfer, 0, "excluded at the response boundary before handoff"))
                    DeliveryTrace.Emit("settle", "ledger", new { attempt = r.Id.ToString(), outcome = "zero" });
                if (!headersSet) { res.StatusCode = 404; return; }
                ActiveStreams.Rst(ctx.Features); ctx.Abort(); return;
            }
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
                    res.Headers.ContentRange = $"bytes {start}-{end}/{length}";
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
            }, docId, sha);
            if (!ok)
            {
                if (await ledger.SettleAsync(r, Settlement.ReleasedZeroTransfer, 0, "policy changed before handoff"))
                    DeliveryTrace.Emit("settle", "ledger", new { attempt = r.Id.ToString(), outcome = "zero" });
                if (state.UnderReadGuard(e => !e, docId, sha)) { if (!headersSet) { res.StatusCode = 404; return; } ctx.Abort(); return; }
                continue;
            }
            wireOffset += acceptedWire; off += n;
            try
            {
                FlushResult fr = await writer.FlushAsync(ctx.RequestAborted);
                if (fr.IsCanceled || (fr.IsCompleted && off < len)) throw new OperationCanceledException("client gone");
            }
            catch (Exception ex) when (ex is OperationCanceledException or IOException or InvalidOperationException or ConnectionResetException)
            {
                if (await ledger.SettleAsync(r, Settlement.Uncertain, acceptedWire, $"uncertain: {ex.GetType().Name}"))
                    DeliveryTrace.Emit("settle", "ledger", new { attempt = r.Id.ToString(), outcome = "uncertain" });
                log.LogWarning("uncertain transfer {Type}", ex.GetType().Name);
                ctx.Abort();
                return;
            }
            if (await ledger.SettleAsync(r, Settlement.Accepted, acceptedWire, "slice handed to transport and flushed"))
                DeliveryTrace.Emit("settle", "ledger", new { attempt = r.Id.ToString(), outcome = "accepted", size = acceptedWire });
            if (hook == "after-first-slice" && off == n && off < len)
            { try { await Task.Delay(cfg.TestPauseMs, ctx.RequestAborted); } catch (OperationCanceledException) { } }
            if (off == n && off < len && s.ActivationStreamPause is { } pause) await pause(ctx);   // C16 Stage 3 test-only
        }
    }
}
