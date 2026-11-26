using System.Collections.Concurrent;
using System.Net;
using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Text.Json.Nodes;
using System.Diagnostics;

namespace Mimamsa.Tests;

/// One real Kestrel service process (loopback, test mode) over the SYN site and a disposable database
/// (MIMAMSA_TEST_DB, required). Its stdout is captured to prove that logs are content-free.
public sealed class ServiceFixture : IAsyncLifetime
{
    public readonly ConcurrentQueue<string> Log = new();
    public string Base { get; private set; } = "";
    Process? _p;

    public static string RegisterPath => Path.GetFullPath(Path.Combine(WebDir(), "..", "..", "..", "..", "config", "restricted_material.json"));

    /// `dotnet <dll>` for the service under test. The DLL path goes through ArgumentList, which quotes it, so a
    /// checkout under a path containing spaces works (a single argument string was split at the first space).
    public static ProcessStartInfo ServiceStartInfo(string dll, string workingDirectory)
    {
        var psi = new ProcessStartInfo(Environment.GetEnvironmentVariable("DOTNET_HOST_PATH") ?? "dotnet")
        { WorkingDirectory = workingDirectory, RedirectStandardOutput = true, RedirectStandardError = true, UseShellExecute = false };
        psi.ArgumentList.Add(dll);
        return psi;
    }

    static ProcessStartInfo ServiceStartInfo() => ServiceStartInfo(Path.Combine(AppContext.BaseDirectory, "Mimamsa.Web.dll"), WebDir());

    /// Start the service with the given extra settings and return (exit code, output) once it exits (or -1 if healthy).
    public static async Task<(int code, string output)> StartExpectingExit(Dictionary<string, string> env)
    {
        var psi = ServiceStartInfo();
        var l = new System.Net.Sockets.TcpListener(IPAddress.Loopback, 0); l.Start(); int port = ((IPEndPoint)l.LocalEndpoint).Port; l.Stop();
        psi.Environment["ASPNETCORE_URLS"] = $"http://127.0.0.1:{port}";
        psi.Environment["Mimamsa__Site"] = Syn.Site;
        psi.Environment["Mimamsa__Db"] = Environment.GetEnvironmentVariable("MIMAMSA_TEST_DB")!;
        foreach (var (k, v) in env) psi.Environment[k] = v;
        using var p = Process.Start(psi)!;
        var outTask = p.StandardOutput.ReadToEndAsync(); var errTask = p.StandardError.ReadToEndAsync();
        if (!p.WaitForExit(60_000)) { p.Kill(true); return (-1, "still running"); }
        return (p.ExitCode, await outTask + await errTask);
    }

    internal static string WebDir()
    {
        var d = new DirectoryInfo(AppContext.BaseDirectory);
        while (d is not null && !Directory.Exists(Path.Combine(d.FullName, "src", "Mimamsa.Web"))) d = d.Parent;
        return d is null ? throw new InvalidOperationException("app/b1/src/Mimamsa.Web not found") : Path.Combine(d.FullName, "src", "Mimamsa.Web");
    }

    public async Task InitializeAsync()
    {
        var db = Environment.GetEnvironmentVariable("MIMAMSA_TEST_DB") ?? throw new InvalidOperationException("MIMAMSA_TEST_DB (Npgsql DSN of a disposable database) is required");
        var l = new System.Net.Sockets.TcpListener(IPAddress.Loopback, 0); l.Start(); int port = ((IPEndPoint)l.LocalEndpoint).Port; l.Stop();
        Base = $"http://127.0.0.1:{port}";
        var psi = ServiceStartInfo();
        foreach (var (k, v) in new Dictionary<string, string>
        {
            ["ASPNETCORE_URLS"] = Base, ["Mimamsa__Site"] = Syn.Site, ["Mimamsa__Db"] = db, ["Mimamsa__Test__Enabled"] = "true",
            ["Mimamsa__Test__ResetState"] = "true", ["Mimamsa__Test__ResetLedger"] = "true", ["Mimamsa__Test__Users__0"] = "admin:Admin:admin-password-1",
            ["Mimamsa__Test__Users__1"] = "reader:User:reader-password-1", ["Mimamsa__Test__Users__2"] = "locktest:User:locktest-password-1",
            // C14 S2: short lock (test mode only) so expiry is testable; accounts reserved for the lockout and unlock
            // tests; a high per-source throttle so the suite's own failed sign-ins from 127.0.0.1 never trip it.
            ["Mimamsa__Test__LockSeconds"] = "3", ["Mimamsa__Login__ThrottlePerSource"] = "1000",
            ["Mimamsa__Test__Users__3"] = "locktest2:User:locktest2-password-1", ["Mimamsa__Test__Users__4"] = "unlocktest:User:unlocktest-password-1",
            ["Mimamsa__RestrictedRegister"] = RegisterPath,
        }) psi.Environment[k] = v;
        _p = Process.Start(psi)!;
        _p.OutputDataReceived += (_, e) => { if (e.Data is not null) Log.Enqueue(e.Data); };
        _p.ErrorDataReceived += (_, e) => { if (e.Data is not null) Log.Enqueue(e.Data); };
        _p.BeginOutputReadLine(); _p.BeginErrorReadLine();
        using var h = new HttpClient();
        for (int i = 0; i < 240; i++)
        {
            if (_p.HasExited) throw new InvalidOperationException("service exited: " + string.Join("\n", Log));
            try { if ((await h.GetAsync(Base + "/health")).IsSuccessStatusCode) return; } catch (HttpRequestException) { }
            await Task.Delay(250);
        }
        throw new TimeoutException("service did not become healthy");
    }

    public Task DisposeAsync() { try { _p?.Kill(true); _p?.WaitForExit(5000); } catch { } return Task.CompletedTask; }

    public HttpClient CreateClient() => new(new HttpClientHandler { UseCookies = true, CookieContainer = new CookieContainer(), AllowAutoRedirect = false }) { BaseAddress = new Uri(Base) };

    public async Task<(HttpClient c, string csrf)> Login(string user)
    {
        var c = CreateClient();
        var r = await c.PostAsJsonAsync("/api/login", new { username = user, password = $"{user}-password-1" });
        r.EnsureSuccessStatusCode();
        var j = JsonNode.Parse(await r.Content.ReadAsStringAsync())!;
        return (c, j["csrf"]!.GetValue<string>());
    }
}

[CollectionDefinition("service")] public class ServiceCollection : ICollectionFixture<ServiceFixture> { }

[Collection("service")]
public class HttpTests(ServiceFixture f)
{
    static string Doc(string fid) => "syn-" + fid.ToLowerInvariant();

    [Theory]
    [InlineData("/api/search?q=notice")]
    [InlineData("/api/documents/syn-s-act")]
    [InlineData("/api/documents/syn-s-act/text")]
    [InlineData("/api/cite?doc=syn-s-act&sha=000000000000&page=1")]
    [InlineData("/api/v2/documents/syn-s-act/pdf-meta")]
    [InlineData("/api/admin/overview")]
    public async Task EveryApiRouteNeedsASession(string path)
    {
        var r = await f.CreateClient().GetAsync(path);
        Assert.Equal(HttpStatusCode.Unauthorized, r.StatusCode);
    }

    [Fact] public async Task LoginFailuresAreGenericAndLockTheAccount()
    {
        var c = f.CreateClient();
        for (int i = 0; i < 5; i++)
            Assert.Equal(HttpStatusCode.Unauthorized, (await c.PostAsJsonAsync("/api/login", new { username = "locktest", password = "wrong-password-xx" })).StatusCode);
        var locked = await c.PostAsJsonAsync("/api/login", new { username = "locktest", password = "locktest-password-1" });
        Assert.Equal(HttpStatusCode.Unauthorized, locked.StatusCode);
        var unknown = await c.PostAsJsonAsync("/api/login", new { username = "nobody", password = "x" });
        Assert.Equal(await locked.Content.ReadAsStringAsync(), await unknown.Content.ReadAsStringAsync());
    }

    [Fact] public async Task ResponseClassesCarryTheClientCachePolicy()
    {
        var (c, _) = await f.Login("reader");
        foreach (var p in new[] { "/api/search?q=notice", "/api/documents/syn-s-act", "/api/documents/syn-s-act/text", "/api/session", "/", "/r" })
        {
            var r = await c.GetAsync(p);
            Assert.Equal("no-store", r.Headers.CacheControl?.ToString());
            Assert.Contains("default-src 'self'", r.Headers.GetValues("Content-Security-Policy").Single());
            Assert.Equal("nosniff", r.Headers.GetValues("X-Content-Type-Options").Single());
        }
        var meta = JsonNode.Parse(await c.GetStringAsync("/api/v2/documents/syn-s-act/pdf-meta"))!;
        var range = new HttpRequestMessage(HttpMethod.Get, $"/api/v2/documents/syn-s-act/copies/{meta["copy_sha256"]}/range");
        range.Headers.Range = new RangeHeaderValue(0, 99);
        var rr = await c.SendAsync(range);
        Assert.Contains("no-store", rr.Headers.CacheControl!.ToString());
        Assert.Null(rr.Headers.ETag); Assert.Null(rr.Content.Headers.LastModified);
        Assert.Equal("no-cache", (await c.GetAsync("/assets/app.css")).Headers.CacheControl?.ToString());
    }

    [Fact] public async Task ProtectedRangesAreExactAndBounded()
    {
        var (c, _) = await f.Login("reader");
        var meta = JsonNode.Parse(await c.GetStringAsync("/api/v2/documents/syn-s-act/pdf-meta"))!;
        var sha = meta["copy_sha256"]!.GetValue<string>(); long len = meta["length"]!.GetValue<long>();
        var vault = File.ReadAllBytes(Path.Combine(Syn.Site, "vault", "sha256", sha[..2], sha));
        async Task<HttpResponseMessage> Get(string? range)
        {
            var m = new HttpRequestMessage(HttpMethod.Get, $"/api/v2/documents/syn-s-act/copies/{sha}/range");
            if (range is not null) m.Headers.TryAddWithoutValidation("Range", range);
            return await c.SendAsync(m);
        }
        var ok = await Get("bytes=10-209");
        Assert.Equal(HttpStatusCode.PartialContent, ok.StatusCode);
        Assert.Equal(vault[10..210], await ok.Content.ReadAsByteArrayAsync());
        Assert.Equal($"bytes 10-209/{len}", ok.Content.Headers.ContentRange!.ToString());
        Assert.Equal(HttpStatusCode.BadRequest, (await Get(null)).StatusCode);
        Assert.Equal(HttpStatusCode.BadRequest, (await Get("bytes=0-1,5-6")).StatusCode);
        Assert.Equal(HttpStatusCode.BadRequest, (await Get("bytes=0-")).StatusCode);
        Assert.Equal(HttpStatusCode.RequestedRangeNotSatisfiable, (await Get($"bytes={len}-{len + 5}")).StatusCode);
        Assert.Equal(HttpStatusCode.NotFound, (await c.GetAsync($"/api/v2/documents/syn-s-act/copies/{new string('0', 64)}/range")).StatusCode);
    }

    [Fact] public async Task StagedDocumentIsUnavailableEverywhere()
    {
        var (c, _) = await f.Login("admin");
        Assert.Equal(HttpStatusCode.NotFound, (await c.GetAsync("/api/documents/syn-v-staged")).StatusCode);
        Assert.Equal(HttpStatusCode.NotFound, (await c.GetAsync("/api/v2/documents/syn-v-staged/pdf-meta")).StatusCode);
        var s = JsonNode.Parse(await c.GetStringAsync("/api/search?q=exact%3Aviolet-plume-canary"))!;
        Assert.DoesNotContain("syn-v-staged", s.ToJsonString());
    }

    /// C14 F10: results are paged by document group; every group is reachable and passages keep relevance order.
    [Fact] public async Task SearchIsPagedByDocumentGroup()
    {
        var (c, _) = await f.Login("reader");
        var first = JsonNode.Parse(await c.GetStringAsync("/api/search?q=notice&page_size=1"))!;
        int pages = first["page_count"]!.GetValue<int>(), groups = first["total_groups"]!.GetValue<int>();
        Assert.True(pages >= 2);
        Assert.Equal(groups, pages);
        var seen = new HashSet<string>();
        for (int p = 1; p <= pages; p++)
        {
            var r = JsonNode.Parse(await c.GetStringAsync($"/api/search?q=notice&page_size=1&page={p}"))!;
            Assert.Equal(p, r["page"]!.GetValue<int>());
            var g = Assert.Single(r["groups"]!.AsArray());
            Assert.True(seen.Add(g!["doc_id"]!.GetValue<string>()));
            Assert.All(r["passages"]!.AsArray(), x => Assert.Equal(g["doc_id"]!.GetValue<string>(), x!["doc_id"]!.GetValue<string>()));
        }
        var beyond = JsonNode.Parse(await c.GetStringAsync($"/api/search?q=notice&page_size=1&page={pages + 5}"))!;
        Assert.Equal(pages, beyond["page"]!.GetValue<int>());      // clamped, never empty
        var svc = JsonNode.Parse(await c.GetStringAsync("/api/search?q=notice&service=army"))!;
        Assert.Equal("Army", svc["run"]!["service_label"]!.GetValue<string>());
        var bad = JsonNode.Parse(await c.GetStringAsync("/api/search?q=notice&service=marines"))!;
        Assert.Null(bad["run"]!["service"]);                          // unknown service ignored, not an error
    }

    [Fact] public async Task UsersCannotReachAdministration()
    {
        var (c, csrf) = await f.Login("reader");
        Assert.Equal(HttpStatusCode.Forbidden, (await c.GetAsync("/api/admin/overview")).StatusCode);
        var m = new HttpRequestMessage(HttpMethod.Post, "/api/admin/withdraw") { Content = JsonContent.Create(new { doc_id = "syn-v-other", reason = "not allowed" }) };
        m.Headers.Add("X-CSRF-Token", csrf);
        Assert.Equal(HttpStatusCode.Forbidden, (await c.SendAsync(m)).StatusCode);
    }

    [Fact] public async Task WithdrawalNeedsCsrfAndThenRemovesTheDocumentFromEverySurface()
    {
        var (admin, csrf) = await f.Login("admin");
        var (user, _) = await f.Login("reader");
        var meta = JsonNode.Parse(await user.GetStringAsync("/api/v2/documents/syn-v-other/pdf-meta"))!;
        var sha = meta["copy_sha256"]!.GetValue<string>();
        var noCsrf = await admin.PostAsJsonAsync("/api/admin/withdraw", new { doc_id = "syn-v-other", reason = "synthetic test" });
        Assert.Equal(HttpStatusCode.Forbidden, noCsrf.StatusCode);
        var m = new HttpRequestMessage(HttpMethod.Post, "/api/admin/withdraw") { Content = JsonContent.Create(new { doc_id = "syn-v-other", reason = "synthetic test" }) };
        m.Headers.Add("X-CSRF-Token", csrf);
        var w = await admin.SendAsync(m);
        Assert.Equal(HttpStatusCode.OK, w.StatusCode);
        Assert.Equal(HttpStatusCode.NotFound, (await user.GetAsync("/api/documents/syn-v-other")).StatusCode);
        Assert.Equal(HttpStatusCode.NotFound, (await user.GetAsync("/api/v2/documents/syn-v-other/pdf-meta")).StatusCode);
        var rm = new HttpRequestMessage(HttpMethod.Get, $"/api/v2/documents/syn-v-other/copies/{sha}/range");
        rm.Headers.TryAddWithoutValidation("Range", "bytes=0-9");
        Assert.Equal(HttpStatusCode.NotFound, (await user.SendAsync(rm)).StatusCode);
        var s = await user.GetStringAsync("/api/search?q=ceramic%20glaze");
        Assert.DoesNotContain("syn-v-other", s);
        // F02: A4 evidence naming the withdrawn copy is redacted (no doc id, no hash, no page) on other documents
        var act = await user.GetStringAsync("/api/documents/syn-s-act");
        Assert.DoesNotContain(sha, act);
        Assert.DoesNotContain("syn-v-other", act);
        Assert.Contains("COPY_NOT_AVAILABLE_IN_THIS_INSTALLATION", act);
        var cite = JsonNode.Parse(await user.GetStringAsync($"/api/cite?doc=syn-v-other&sha={sha[..12]}&page=1"))!;
        var unknown = JsonNode.Parse(await user.GetStringAsync($"/api/cite?doc=syn-v-other&sha={new string('a', 12)}&page=1"))!;
        Assert.Equal(unknown.ToJsonString(), cite.ToJsonString());
    }

    [Theory]                                                                   // review F01: earlier copies that are not eligible
    [InlineData("syn-x-stagedearly", "x_stagedearly_r1_copy")]
    [InlineData("syn-x-dropped", "x_dropped_r1_copy")]
    public async Task IneligibleEarlierCopiesGetTheGenericAnswerOnEveryPath(string doc, string key)
    {
        var (c, _) = await f.Login("reader");
        var sha = Syn.Map[key]!.GetValue<string>();
        Assert.Equal(HttpStatusCode.NotFound, (await c.GetAsync($"/api/v2/documents/{doc}/pdf-meta?copy={sha}")).StatusCode);
        var m = new HttpRequestMessage(HttpMethod.Get, $"/api/v2/documents/{doc}/copies/{sha}/range");
        m.Headers.TryAddWithoutValidation("Range", "bytes=0-99");
        Assert.Equal(HttpStatusCode.NotFound, (await c.SendAsync(m)).StatusCode);
        var cite = JsonNode.Parse(await c.GetStringAsync($"/api/cite?doc={doc}&sha={sha[..12]}&page=1"))!;
        Assert.Equal("CITED_COPY_UNAVAILABLE", cite["state"]!.GetValue<string>());
        Assert.Null(cite["copy"]);
    }

    [Fact] public async Task UserPayloadsNeverCarryInternalNodeIds()            // review F02
    {
        var (c, _) = await f.Login("reader");
        var d = await c.GetStringAsync("/api/documents/syn-j-allow");
        Assert.DoesNotContain("node_id", d);
        Assert.DoesNotContain("source_node", d);
        Assert.DoesNotContain("JUD:JG-", d);
    }

    [Fact] public async Task CitationOfAnEarlierEditionOpensThatCopyAndOffersCurrentSeparately()
    {
        var (c, _) = await f.Login("reader");
        var old = Syn.Map["j_allow_r1_copy"]!.GetValue<string>();
        var r = JsonNode.Parse(await c.GetStringAsync($"/api/cite?doc=syn-j-allow&sha={old[..12]}&page=6"))!;
        Assert.Equal("CITED_COPY_ELIGIBLE_NOT_CURRENT", r["state"]!.GetValue<string>());
        Assert.Equal(old, r["copy"]!.GetValue<string>());
        Assert.NotNull(r["current_copy"]);
        var meta = JsonNode.Parse(await c.GetStringAsync($"/api/v2/documents/syn-j-allow/pdf-meta?copy={old}"))!;
        Assert.Equal(old, meta["copy_sha256"]!.GetValue<string>());
        Assert.Equal(6, meta["page_count"]!.GetValue<int>());
    }

    [Fact] public async Task LegalCitationAndInternalReferenceAreSeparate()
    {
        var (c, _) = await f.Login("reader");
        var j = JsonNode.Parse(await c.GetStringAsync("/api/documents/syn-j-allow/citation?page=7&para=12"))!;
        var legal = j["legal"]!.GetValue<string>();
        Assert.Equal("Vale v. Lark, 2021 BRSYN 21 (Fictional Bracken Tribunal, 15 September 2021), para 12 (metadata not verified)", legal);
        Assert.DoesNotContain("syn-j-allow", legal);
        Assert.Contains("syn-j-allow", j["internal_reference"]!.GetValue<string>());
    }

    [Fact] public async Task CandidatesAreLabelledAndNeverAuthority()
    {
        var (c, _) = await f.Login("reader");
        var d = JsonNode.Parse(await c.GetStringAsync("/api/documents/syn-j-allow"))!;
        foreach (var o in d["outcomes"]!.AsArray())
        {
            Assert.Equal("AUTOMATED_CANDIDATE_NOT_VERIFIED", o!["status"]!.GetValue<string>());
            Assert.False(o["evaluated"]!.GetValue<bool>());       // evaluation_ref null -> "not evaluated"
        }
        var axes = d["status_axes"]!.AsArray().Select(a => a!["label"]!.GetValue<string>()).ToArray();
        Assert.Equal(new[] { "Source integrity", "Source authenticity", "Evidence fidelity", "Legal applicability", "Legal approval", "Publication", "Dependency freshness" }, axes);
    }

    [Fact] public async Task LogsAreContentFree()
    {
        var (c, _) = await f.Login("reader");
        const string secret = "zebracanarytoken";
        await c.GetAsync($"/api/search?q={secret}%20summary");
        await c.GetAsync("/api/documents/syn-m-guide/text?from=1&to=4");
        await Task.Delay(300);
        var all = string.Join("\n", f.Log);
        Assert.Contains("request GET /api/search 200", all);
        Assert.DoesNotContain(secret, all);
        Assert.DoesNotContain("BHT means", all);            // document text
        Assert.DoesNotContain("reader-password-1", all);
    }

    [Fact] public async Task LogoutClearsSiteDataAndInvalidatesTheSession()
    {
        var (c, csrf) = await f.Login("reader");
        var m = new HttpRequestMessage(HttpMethod.Post, "/api/logout");
        m.Headers.Add("X-CSRF-Token", csrf);
        var r = await c.SendAsync(m);
        Assert.Equal("\"cache\", \"storage\"", r.Headers.GetValues("Clear-Site-Data").Single());
        Assert.Equal(HttpStatusCode.Unauthorized, (await c.GetAsync("/api/search?q=notice")).StatusCode);
    }
}

/// Review F16: the restricted-material re-check is mandatory and fails closed.
public class RegisterStartupTests
{
    [Fact] public async Task ServiceRefusesToStartWithoutTheRegister()
    {
        var (code, output) = await ServiceFixture.StartExpectingExit(new() { ["Mimamsa__RestrictedRegister"] = "" });
        Assert.NotEqual(0, code); Assert.NotEqual(-1, code);
        Assert.Contains("RestrictedRegister is required", output);
    }

    [Fact] public async Task ServiceRefusesARegisterThatDoesNotMatchTheRelease()
    {
        var f = Path.GetTempFileName();
        File.WriteAllText(f, """{"items":[{"restriction_id":"RM-T","source_sha256":"00","doc_id":"x"}]}""");
        var (code, output) = await ServiceFixture.StartExpectingExit(new() { ["Mimamsa__RestrictedRegister"] = f });
        Assert.NotEqual(0, code); Assert.NotEqual(-1, code);
        Assert.Contains("does not match the register pinned by the active release", output);
    }

    [Fact] public async Task OptOutIsHonouredOnlyInTestMode()
    {
        var (code, output) = await ServiceFixture.StartExpectingExit(new() { ["Mimamsa__RestrictedRegister"] = "", ["Mimamsa__Test__AllowNoRegister"] = "true" });
        Assert.Contains("RestrictedRegister is required", output);        // Test:Enabled not set -> still refused
        Assert.NotEqual(0, code);
    }
}
