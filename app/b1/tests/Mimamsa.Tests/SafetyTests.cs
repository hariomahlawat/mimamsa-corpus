// C14 S2 safety: withdrawal scope and reinstatement (owner policy), policy-aware invalidation (F05), account lockout,
// throttling, Admin unlock and the audit log (F15). Unit tests here need no database; HTTP tests share the service
// fixture (SYN site). The mid-transfer cut-off test starts its own service with a tiny delivery slice.
using System.Diagnostics;
using System.Net;
using System.Net.Http.Json;
using System.Text.Json.Nodes;
using Mimamsa.Core.Delivery;
using Mimamsa.Core.Generation;
using Mimamsa.Core.Identity;
using Npgsql;

namespace Mimamsa.Tests;

public class LoginThrottleTests
{
    [Fact] public void FailuresPerUsernameAndPerSourceAreLimitedInASlidingWindow()
    {
        var now = new DateTime(2026, 11, 26, 12, 0, 0, DateTimeKind.Utc);
        var t = new LoginThrottle { PerUsername = 3, PerSource = 5, Window = TimeSpan.FromMinutes(1), Now = () => now };
        for (int i = 0; i < 3; i++) { Assert.True(t.Allowed("alice", "10.0.0.1")); t.RecordFailure("alice", "10.0.0.1"); }
        Assert.False(t.Allowed("alice", "10.0.0.9"));                 // per-username, from any address
        Assert.True(t.Allowed("bob", "10.0.0.1"));                    // another name from the same address still allowed
        t.RecordFailure("bob", "10.0.0.1"); t.RecordFailure("carol", "10.0.0.1");
        Assert.False(t.Allowed("dave", "10.0.0.1"));                  // per-source: 5 failures from 10.0.0.1
        Assert.True(t.Allowed("dave", "10.0.0.2"));
        now = now.AddSeconds(61);                                     // the window slides
        Assert.True(t.Allowed("alice", "10.0.0.1"));
        t.RecordFailure("alice", null); t.RecordFailure("alice", null); t.RecordFailure("alice", null);
        Assert.False(t.Allowed("alice", null));
        t.Clear("alice");                                             // Admin unlock clears the username window
        Assert.True(t.Allowed("alice", null));
    }
}

public class WithdrawalScopeTests
{
    static DocumentRecord D(string id, string sha, string? title, string type = "act", string? number = null, bool verified = true, string? lang = "en") =>
        new() { DocId = id, DocType = type, CopySha = sha, Title = title, Number = number, Language = lang, OriginalVerified = verified,
              Provenance = new JsonObject(), StatusAxes = new JsonObject(), Restriction = new JsonObject(), FieldOrigin = new JsonObject() };

    [Fact] public void VerifiedDuplicatesAreDistinguishedFromDistinctEditions()
    {
        string A = new('a', 64), B = new('b', 64), C = new('c', 64), E = new('e', 64);
        var docs = new[]
        {
            D("act-x-1950", A, "The X Act, 1950", number: "46 of 1950"),
            D("act-x-1950-sched", A, "Schedule"),                                      // byte-identical, verified -> duplicate
            D("act-x-1950-unverified", A, "Schedule", verified: false),               // identical bytes, not re-hashed -> never a duplicate
            D("act-x-1950-hi", B, "The X Act, 1950", number: "46 of 1950", lang: "hi"), // other language -> distinct edition
            D("act-x-1950-alt", C, "The X Act 1950"),                                  // other print, same normalised title
            D("act-y-1957", E, "The Y Act, 1957"),                                      // unrelated
        }.ToDictionary(d => d.DocId);
        var held = new[] { new HeldCopy(new string('f', 64), "act-x-1950", 10, "R1", "G1", 100, true) };
        var s = WithdrawalScope.Compute(docs, held, "act-x-1950");
        Assert.Equal(new[] { new string('f', 64), A }.OrderBy(x => x), s.OwnCopies.OrderBy(x => x));   // own copies: always included
        Assert.Equal(new[] { "act-x-1950-sched" }, s.VerifiedDuplicates.Select(x => x.DocId));
        Assert.Equal(new[] { "act-x-1950-alt", "act-x-1950-hi", "act-x-1950-unverified" }, s.DistinctEditions.Select(x => x.DocId));
        Assert.DoesNotContain(s.VerifiedDuplicates.Concat(s.DistinctEditions), x => x.DocId == "act-y-1957");
    }
}

public class ReinstatementCoreTests
{
    static string M(string k) => Syn.Map[k]!.GetValue<string>();

    [Fact] public async Task ReinstateCommitsDurablyBeforeRelaxingTheFence()
    {
        var st = new ServingState();
        var shas = new[] { M("j_allow_r1_copy") };
        await st.WithdrawAsync("syn-j-allow", shas, () => Task.FromResult((2L, "d2", true)), () => { }, (_, _) => { });
        Assert.True(st.IsDocWithdrawn("syn-j-allow"));
        // durable CAS fails: the document stays withdrawn (fail closed)
        await Assert.ThrowsAsync<InvalidOperationException>(() => st.ReinstateAsync("syn-j-allow", () => throw new InvalidOperationException("witness CAS failed")));
        Assert.True(st.IsDocWithdrawn("syn-j-allow")); Assert.True(st.IsWithdrawn("syn-j-allow", shas[0]));
        // nothing changed in the database: nothing changes in memory
        var (_, _, ch0) = await st.ReinstateAsync("syn-j-allow", () => Task.FromResult((2L, "d2", false, new List<string>())));
        Assert.False(ch0); Assert.True(st.IsDocWithdrawn("syn-j-allow"));
        var (e, _, ch) = await st.ReinstateAsync("syn-j-allow", () => Task.FromResult((3L, "d3", true, shas.ToList())));
        Assert.True(ch); Assert.Equal(3, e); Assert.Equal(3, st.Epoch);
        Assert.False(st.IsDocWithdrawn("syn-j-allow")); Assert.False(st.IsWithdrawn("syn-j-allow", shas[0]));
    }

    [Fact] public void RenewedVerificationRefusesRestrictedTamperedOrUnknownDocuments()
    {
        var site = Syn.CopySite();
        try
        {
            var g = Syn.Gen; var d = g.Documents["syn-l-scan"];
            var clean = new Eligibility(g, new ServingState(), RestrictedRegister.Empty, new Vault(site));
            Assert.Empty(clean.ReinstatementProblems("syn-l-scan", new[] { d.CopySha }));
            Assert.Equal(new[] { "not_in_active_generation" }, clean.ReinstatementProblems("syn-nope", Array.Empty<string>()));
            Assert.NotEmpty(clean.ReinstatementProblems("syn-v-staged", Array.Empty<string>()));   // staged: never reinstatable

            var regPath = Path.Combine(site, "register-test.json");
            File.WriteAllText(regPath, $$"""{"items":[{"source_sha256":"{{new string('0', 64)}}","derived_sha256":[],"doc_id":"syn-l-scan"}]}""");
            var restricted = new Eligibility(g, new ServingState(), RestrictedRegister.Load(regPath), new Vault(site));
            Assert.Contains("restricted_register_document", restricted.ReinstatementProblems("syn-l-scan", new[] { d.CopySha }));

            // the vault object no longer re-hashes NOW (the load-time cache is not trusted for a reinstatement)
            var obj = new Vault(site).PathFor(d.CopySha);
            File.AppendAllText(obj, "tamper");
            Assert.Contains($"rehash_failed:{d.CopySha[..12]}", clean.ReinstatementProblems("syn-l-scan", new[] { d.CopySha }));
        }
        finally { try { Directory.Delete(site, true); } catch { } }
    }
}

[Collection("service")]
public class SafetyHttpTests(ServiceFixture f)
{
    static async Task<HttpResponseMessage> Post(HttpClient c, string csrf, string path, object body)
    {
        var m = new HttpRequestMessage(HttpMethod.Post, path) { Content = JsonContent.Create(body) };
        m.Headers.Add("X-CSRF-Token", csrf);
        return await c.SendAsync(m);
    }
    HttpClient Anon() => f.CreateClient();
    static Task<HttpResponseMessage> Login(HttpClient c, string u, string pw) => c.PostAsJsonAsync("/api/login", new { username = u, password = pw });

    [Fact] public async Task ApiResponsesNameThePolicyEpochAndThePollDoesNotNeedASessionRefresh()
    {
        var (c, _) = await f.Login("reader");
        var r = await c.GetAsync("/api/documents/syn-s-act");
        Assert.True(long.TryParse(r.Headers.GetValues("X-Mimamsa-Policy-Epoch").Single(), out var e1));
        var p = JsonNode.Parse(await c.GetStringAsync("/api/policy"))!;
        Assert.True(p["epoch"]!.GetValue<long>() >= e1);
        Assert.Equal(HttpStatusCode.Unauthorized, (await Anon().GetAsync("/api/policy")).StatusCode);
        Assert.False((await c.GetAsync("/assets/app.css")).Headers.Contains("X-Mimamsa-Policy-Epoch"));   // static files: no header
    }

    [Fact] public async Task ReinstatementNeedsAnAdminAReasonAndRenewedVerification()
    {
        const string doc = "syn-l-scan";
        var (admin, csrf) = await f.Login("admin");
        var (user, ucsrf) = await f.Login("reader");
        var before = long.Parse((await user.GetAsync("/api/session")).Headers.GetValues("X-Mimamsa-Policy-Epoch").Single());
        Assert.Equal(HttpStatusCode.Conflict, (await Post(admin, csrf, "/api/admin/reinstate", new { doc_id = doc, reason = "not withdrawn yet" })).StatusCode);
        Assert.Equal(HttpStatusCode.OK, (await Post(admin, csrf, "/api/admin/withdraw", new { doc_id = doc, reason = "C14 reinstatement test" })).StatusCode);
        var afterWithdraw = (await user.GetAsync($"/api/documents/{doc}"));
        Assert.Equal(HttpStatusCode.NotFound, afterWithdraw.StatusCode);
        Assert.True(long.Parse(afterWithdraw.Headers.GetValues("X-Mimamsa-Policy-Epoch").Single()) > before);   // epoch moved: clients re-check

        Assert.Equal(HttpStatusCode.Forbidden, (await Post(user, ucsrf, "/api/admin/reinstate", new { doc_id = doc, reason = "user may not" })).StatusCode);
        Assert.Equal(HttpStatusCode.Forbidden, (await admin.PostAsJsonAsync("/api/admin/reinstate", new { doc_id = doc, reason = "no csrf token" })).StatusCode);
        Assert.Equal(HttpStatusCode.BadRequest, (await Post(admin, csrf, "/api/admin/reinstate", new { doc_id = doc, reason = "x" })).StatusCode);

        var ok = await Post(admin, csrf, "/api/admin/reinstate", new { doc_id = doc, reason = "C14 test: withdrawn in error" });
        Assert.Equal(HttpStatusCode.OK, ok.StatusCode);
        var j = JsonNode.Parse(await ok.Content.ReadAsStringAsync())!;
        Assert.Equal("reinstated", j["status"]!.GetValue<string>());
        Assert.Contains("re-hashed", j["verification"]!.GetValue<string>());
        Assert.Equal(HttpStatusCode.OK, (await user.GetAsync($"/api/documents/{doc}")).StatusCode);
        Assert.Equal(HttpStatusCode.OK, (await user.GetAsync($"/api/v2/documents/{doc}/pdf-meta")).StatusCode);

        var o = JsonNode.Parse(await admin.GetStringAsync("/api/admin/overview"))!["withdrawals"]!.AsArray();
        var mine = o.Where(x => x!["doc_id"]!.GetValue<string>() == doc).ToList();
        Assert.Equal("reinstate", mine[0]!["action"]!.GetValue<string>());
        Assert.Equal("withdraw", mine[1]!["action"]!.GetValue<string>());
        Assert.Equal("document", mine[1]!["scope"]!.GetValue<string>());
        var audit = await admin.GetStringAsync("/api/admin/audit?limit=200");
        Assert.Contains("\"reinstate\"", audit); Assert.Contains($"\"{doc}\"", audit);
    }

    [Fact] public async Task WithdrawalScopeIsListedAndOnlyVerifiedDuplicatesCanBeIncluded()
    {
        var (admin, csrf) = await f.Login("admin");
        var (user, _) = await f.Login("reader");
        Assert.Equal(HttpStatusCode.Forbidden, (await user.GetAsync("/api/admin/withdraw-scope?doc_id=syn-s-act")).StatusCode);
        var sc = JsonNode.Parse(await admin.GetStringAsync("/api/admin/withdraw-scope?doc_id=syn-j-allow"))!;
        Assert.Equal(2, sc["own_copies"]!.AsArray().Count);                       // current copy and the earlier edition
        Assert.Empty(sc["verified_duplicates"]!.AsArray());                         // SYN holds no byte-identical twin
        // a document that is not a verified duplicate is refused, and nothing is withdrawn
        var bad = await Post(admin, csrf, "/api/admin/withdraw", new { doc_id = "syn-m-guide", reason = "scope test", include_duplicates = new[] { "syn-s-act" } });
        Assert.Equal(HttpStatusCode.BadRequest, bad.StatusCode);
        Assert.Equal(HttpStatusCode.OK, (await user.GetAsync("/api/documents/syn-m-guide")).StatusCode);
        Assert.Equal(HttpStatusCode.OK, (await user.GetAsync("/api/documents/syn-s-act")).StatusCode);
    }

    [Fact] public async Task AttemptsDuringALockNeitherCountNorExtendIt()
    {
        var c = Anon();
        for (int i = 0; i < 5; i++) Assert.Equal(HttpStatusCode.Unauthorized, (await Login(c, "locktest2", "wrong-password-xx")).StatusCode);
        var lockedAt = Stopwatch.StartNew();
        await Task.Delay(1000);
        // correct and wrong attempts while locked: refused, and (the F15 defect) they must not move the lock forward
        Assert.Equal(HttpStatusCode.Unauthorized, (await Login(c, "locktest2", "locktest2-password-1")).StatusCode);
        Assert.Equal(HttpStatusCode.Unauthorized, (await Login(c, "locktest2", "wrong-password-xx")).StatusCode);
        await Task.Delay(Math.Max(0, 3300 - (int)lockedAt.ElapsedMilliseconds));    // lock is 3 s (test mode)
        Assert.Equal(HttpStatusCode.OK, (await Login(c, "locktest2", "locktest2-password-1")).StatusCode);
        var (admin, _) = await f.Login("admin");
        var audit = await admin.GetStringAsync("/api/admin/audit?limit=200");
        Assert.Contains("\"lockout\"", audit); Assert.Contains("\"login_refused_locked\"", audit);
    }

    [Fact] public async Task AnAdminCanUnlockWithARecordedReason()
    {
        var c = Anon();
        for (int i = 0; i < 5; i++) await Login(c, "unlocktest", "wrong-password-xx");
        Assert.Equal(HttpStatusCode.Unauthorized, (await Login(c, "unlocktest", "unlocktest-password-1")).StatusCode);
        var (admin, csrf) = await f.Login("admin");
        var (user, ucsrf) = await f.Login("reader");
        var accounts = JsonNode.Parse(await admin.GetStringAsync("/api/admin/accounts"))!.AsArray();
        Assert.True(accounts.Single(a => a!["username"]!.GetValue<string>() == "unlocktest")!["locked"]!.GetValue<bool>());
        Assert.Equal(HttpStatusCode.Forbidden, (await user.GetAsync("/api/admin/accounts")).StatusCode);
        Assert.Equal(HttpStatusCode.Forbidden, (await Post(user, ucsrf, "/api/admin/unlock", new { username = "unlocktest", reason = "users may not" })).StatusCode);
        Assert.Equal(HttpStatusCode.Forbidden, (await admin.PostAsJsonAsync("/api/admin/unlock", new { username = "unlocktest", reason = "no csrf" })).StatusCode);
        Assert.Equal(HttpStatusCode.BadRequest, (await Post(admin, csrf, "/api/admin/unlock", new { username = "unlocktest", reason = "" })).StatusCode);
        Assert.Equal(HttpStatusCode.NotFound, (await Post(admin, csrf, "/api/admin/unlock", new { username = "nobody-here", reason = "unknown account" })).StatusCode);
        Assert.Equal(HttpStatusCode.OK, (await Post(admin, csrf, "/api/admin/unlock", new { username = "unlocktest", reason = "C14 test: owner confirmed identity" })).StatusCode);
        Assert.Equal(HttpStatusCode.OK, (await Login(c, "unlocktest", "unlocktest-password-1")).StatusCode);
        var audit = await admin.GetStringAsync("/api/admin/audit?limit=200");
        Assert.Contains("C14 test: owner confirmed identity", audit);
        Assert.Contains("\"unlock\"", audit);
    }

    [Fact] public async Task FailedSignInsAreThrottledPerUsernameWithoutRevealingWhetherItExists()
    {
        var c = Anon();
        var codes = new List<HttpStatusCode>();
        for (int i = 0; i < 11; i++) codes.Add((await Login(c, "ghost-throttle-probe", "wrong-password-xx")).StatusCode);
        Assert.All(codes.Take(10), s => Assert.Equal(HttpStatusCode.Unauthorized, s));
        var throttled = await Login(c, "ghost-throttle-probe", "wrong-password-xx");
        Assert.Equal((HttpStatusCode)429, throttled.StatusCode);
        Assert.NotNull(throttled.Headers.RetryAfter);
        Assert.DoesNotContain("ghost", await throttled.Content.ReadAsStringAsync());
    }

    [Fact] public async Task TheAuditLogIsAdminOnlyPagedAndContentFree()
    {
        var (user, _) = await f.Login("reader");
        await user.GetStringAsync("/api/search?q=zebra-quokka-audit-probe");
        await Login(Anon(), "reader", "secret-typed-password-probe");
        await Login(Anon(), "password-typed-into-username", "x");
        Assert.Equal(HttpStatusCode.Forbidden, (await user.GetAsync("/api/admin/audit")).StatusCode);
        var (admin, _) = await f.Login("admin");
        var page1 = JsonNode.Parse(await admin.GetStringAsync("/api/admin/audit?limit=3"))!;
        Assert.Equal(3, page1["rows"]!.AsArray().Count);
        var next = page1["next_before"]!.GetValue<long>();
        var page2 = JsonNode.Parse(await admin.GetStringAsync($"/api/admin/audit?limit=3&before={next}"))!;
        Assert.All(page2["rows"]!.AsArray(), r => Assert.True(r!["id"]!.GetValue<long>() < next));
        var all = await admin.GetStringAsync("/api/admin/audit?limit=200");
        Assert.DoesNotContain("zebra-quokka", all);
        Assert.DoesNotContain("secret-typed-password-probe", all);
        Assert.DoesNotContain("password-typed-into-username", all);   // unknown usernames are never stored
        Assert.DoesNotContain("password-1", all);
    }
}

/// Mid-transfer enforcement (C14): a protected range transfer that is in progress when the document is withdrawn is
/// cut off; it does not complete. Uses its own service process (single-instance lock is per database) with a tiny
/// delivery slice so a SYN original spans several slices, and the test-mode pause after the first slice.
public class MidTransferWithdrawalTests : IAsyncLifetime
{
    Process? _p; string _base = ""; readonly System.Collections.Concurrent.ConcurrentQueue<string> _log = new();

    static async Task<string> XferDsnAsync()
    {
        if (Environment.GetEnvironmentVariable("MIMAMSA_TEST_DB_XFER") is { Length: > 0 } x) return x;
        var b = new NpgsqlConnectionStringBuilder(Environment.GetEnvironmentVariable("MIMAMSA_TEST_DB")
            ?? throw new InvalidOperationException("MIMAMSA_TEST_DB is required"));
        var name = b.Database + "_xfer";
        await using (var c = new NpgsqlConnection(b.ConnectionString))
        {
            await c.OpenAsync();
            await using var q = new NpgsqlCommand("SELECT 1 FROM pg_database WHERE datname = $1", c);
            q.Parameters.AddWithValue(name);
            if (await q.ExecuteScalarAsync() is null)
            {
                await using var cr = new NpgsqlCommand($"CREATE DATABASE \"{name}\"", c);
                try { await cr.ExecuteNonQueryAsync(); }
                catch (PostgresException e) { throw new InvalidOperationException($"create database {name} (or set MIMAMSA_TEST_DB_XFER): {e.MessageText}"); }
            }
        }
        b.Database = name;
        return b.ConnectionString;
    }

    public async Task InitializeAsync()
    {
        var l = new System.Net.Sockets.TcpListener(IPAddress.Loopback, 0); l.Start(); int port = ((IPEndPoint)l.LocalEndpoint).Port; l.Stop();
        _base = $"http://127.0.0.1:{port}";
        var psi = ServiceFixture.ServiceStartInfo(Path.Combine(AppContext.BaseDirectory, "Mimamsa.Web.dll"), ServiceFixture.WebDir());
        foreach (var (k, v) in new Dictionary<string, string>
        {
            ["ASPNETCORE_URLS"] = _base, ["Mimamsa__Site"] = Syn.Site, ["Mimamsa__Db"] = await XferDsnAsync(), ["Mimamsa__Test__Enabled"] = "true",
            ["Mimamsa__Test__ResetState"] = "true", ["Mimamsa__Test__ResetLedger"] = "true", ["Mimamsa__Test__Users__0"] = "admin:Admin:admin-password-1",
            ["Mimamsa__Test__Users__1"] = "reader:User:reader-password-1", ["Mimamsa__RestrictedRegister"] = ServiceFixture.RegisterPath,
            ["Mimamsa__Delivery__Slice"] = "256", ["Mimamsa__Test__PauseMs"] = "5000",
        }) psi.Environment[k] = v;
        _p = Process.Start(psi)!;
        _p.OutputDataReceived += (_, e) => { if (e.Data is not null) _log.Enqueue(e.Data); };
        _p.ErrorDataReceived += (_, e) => { if (e.Data is not null) _log.Enqueue(e.Data); };
        _p.BeginOutputReadLine(); _p.BeginErrorReadLine();
        using var h = new HttpClient();
        for (int i = 0; i < 240; i++)
        {
            if (_p.HasExited) throw new InvalidOperationException("service exited: " + string.Join("\n", _log));
            try { if ((await h.GetAsync(_base + "/health")).IsSuccessStatusCode) return; } catch (HttpRequestException) { }
            await Task.Delay(250);
        }
        throw new TimeoutException("transfer service did not become healthy");
    }
    public Task DisposeAsync() { try { _p?.Kill(true); _p?.WaitForExit(5000); } catch { } return Task.CompletedTask; }

    HttpClient Client() => new(new HttpClientHandler { UseCookies = true, CookieContainer = new CookieContainer() }) { BaseAddress = new Uri(_base) };
    async Task<(HttpClient c, string csrf)> SignIn(string user)
    {
        var c = Client();
        var r = await c.PostAsJsonAsync("/api/login", new { username = user, password = $"{user}-password-1" });
        r.EnsureSuccessStatusCode();
        return (c, JsonNode.Parse(await r.Content.ReadAsStringAsync())!["csrf"]!.GetValue<string>());
    }

    [Fact] public async Task AnInProgressRangeTransferIsCutOffByAWithdrawal()
    {
        var (user, _) = await SignIn("reader");
        var (admin, csrf) = await SignIn("admin");
        // the largest SYN original that is a current, published copy
        string doc = ""; string sha = ""; long len = 0;
        foreach (var d in new[] { "syn-s-act", "syn-s-rule", "syn-s-notice", "syn-j-reject", "syn-j-allow", "syn-h-manual", "syn-m-guide", "syn-l-scan", "syn-j-lookalike" })
        {
            var m = await user.GetAsync($"/api/v2/documents/{d}/pdf-meta");
            if (!m.IsSuccessStatusCode) continue;
            var j = JsonNode.Parse(await m.Content.ReadAsStringAsync())!;
            if (j["length"]!.GetValue<long>() > len) { len = j["length"]!.GetValue<long>(); doc = d; sha = j["copy_sha256"]!.GetValue<string>(); }
        }
        Assert.True(len >= 1500, $"need an original of at least 1500 bytes, largest is {len}");
        var end = Math.Min(len, 4000) - 1;

        // control: the same range completes when nothing happens
        var ctl = new HttpRequestMessage(HttpMethod.Get, $"/api/v2/documents/{doc}/copies/{sha}/range");
        ctl.Headers.TryAddWithoutValidation("Range", $"bytes=0-{end}");
        var full = await (await user.SendAsync(ctl)).Content.ReadAsByteArrayAsync();
        Assert.Equal(end + 1, full.Length);

        // the transfer pauses after its first 256-byte slice; the withdrawal lands during the pause
        var req = new HttpRequestMessage(HttpMethod.Get, $"/api/v2/documents/{doc}/copies/{sha}/range");
        req.Headers.TryAddWithoutValidation("Range", $"bytes=0-{end}");
        req.Headers.TryAddWithoutValidation("X-Mimamsa-Test-Pause", "after-first-slice");
        var resp = await user.SendAsync(req, HttpCompletionOption.ResponseHeadersRead);
        Assert.Equal(HttpStatusCode.PartialContent, resp.StatusCode);
        var stream = await resp.Content.ReadAsStreamAsync();
        var buf = new byte[1024]; int got = 0;
        got += await stream.ReadAsync(buf);                                   // the first slice arrives
        Assert.InRange(got, 1, 256);
        var w = new HttpRequestMessage(HttpMethod.Post, "/api/admin/withdraw") { Content = JsonContent.Create(new { doc_id = doc, reason = "C14 mid-transfer test" }) };
        w.Headers.Add("X-CSRF-Token", csrf);
        var wr = JsonNode.Parse(await (await admin.SendAsync(w)).Content.ReadAsStringAsync())!;
        Assert.True(wr["reset_streams"]!.GetValue<int>() >= 1, "the in-flight stream was reset at the fence");
        bool cut = false;
        try
        {
            using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(15));
            while (true) { int n = await stream.ReadAsync(buf, cts.Token); if (n == 0) break; got += n; }
        }
        catch (Exception e) when (e is IOException or HttpRequestException or OperationCanceledException) { cut = true; }
        Assert.True(cut || got < end + 1, $"transfer completed after withdrawal ({got} of {end + 1} bytes)");
        Assert.True(got < end + 1, $"received {got} of {end + 1} bytes");
        // and no new range is served
        var after = new HttpRequestMessage(HttpMethod.Get, $"/api/v2/documents/{doc}/copies/{sha}/range");
        after.Headers.TryAddWithoutValidation("Range", "bytes=0-99");
        Assert.Equal(HttpStatusCode.NotFound, (await user.SendAsync(after)).StatusCode);
    }
}
