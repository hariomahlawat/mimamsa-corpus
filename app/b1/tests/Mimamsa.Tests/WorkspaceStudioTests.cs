using System.Net;
using System.Net.Http.Json;
using System.Text.Json.Nodes;
using Mimamsa.Core.Studio;
using Npgsql;

namespace Mimamsa.Tests;

/// C15 WP5/WP6: Document Studio store and API, Commander workspace API. Uses the shared service fixture (SYN site,
/// disposable MIMAMSA_TEST_DB), so it runs in the "service" collection.
[Collection("service")]
public class WorkspaceStudioTests(ServiceFixture f)
{
    static NpgsqlDataSource Db() => new NpgsqlDataSourceBuilder(Environment.GetEnvironmentVariable("MIMAMSA_TEST_DB")!).Build();

    static async Task<HttpResponseMessage> Post(HttpClient c, string csrf, string path, object body, string? origin = null)
    {
        var m = new HttpRequestMessage(HttpMethod.Post, path) { Content = JsonContent.Create(body) };
        m.Headers.Add("X-CSRF-Token", csrf);
        if (origin is not null) m.Headers.Add("Origin", origin);
        return await c.SendAsync(m);
    }

    static async Task<JsonNode> J(HttpResponseMessage r) => JsonNode.Parse(await r.Content.ReadAsStringAsync())!;

    // ------------------------------------------------------------------ store
    [Fact]
    public async Task StoreIsOwnerScoped()
    {
        await using var db = Db();
        var st = new StudioStore(db); await st.EnsureSchemaAsync();
        var d = await st.CreateAsync("owner-a", "A's memo", "memo");
        Assert.Null(await st.GetAsync("owner-b", d.Id));
        Assert.Null(await st.VersionsAsync("owner-b", d.Id));
        Assert.Null(await st.SaveAsync("owner-b", d.Id, d.Version, "taken", "draft", new JsonArray()));
        Assert.False(await st.DeleteAsync("owner-b", d.Id));
        Assert.DoesNotContain(await st.ListAsync("owner-b"), x => x.Id == d.Id);
        Assert.NotNull(await st.GetAsync("owner-a", d.Id));        // untouched by the attempts above
        Assert.True(await st.DeleteAsync("owner-a", d.Id));
    }

    [Fact]
    public async Task SavesAreVersionedAndConflictsAreRefused()
    {
        await using var db = Db();
        var st = new StudioStore(db); await st.EnsureSchemaAsync();
        var d = await st.CreateAsync("owner-v", "Versions", "research-note");
        Assert.Equal(1, d.Version);
        Assert.All(d.Blocks, b => Assert.Equal("template", b!["origin"]!.GetValue<string>()));
        var body = StudioStore.Normalise(JsonNode.Parse("""[{"type":"text","origin":"user","text":"first"}]"""));
        var d2 = await st.SaveAsync("owner-v", d.Id, 1, "Versions", "in_review", body);
        Assert.Equal(2, d2!.Version); Assert.Equal("in_review", d2.State);
        await Assert.ThrowsAsync<StudioConflictException>(() => st.SaveAsync("owner-v", d.Id, 1, "Versions", "draft", body));   // stale base
        var v1 = await st.GetAsync("owner-v", d.Id, 1);
        Assert.Equal(4, v1!.Blocks.Count);                          // version 1 is kept as it was
        Assert.Equal(new[] { 2, 1 }, (await st.VersionsAsync("owner-v", d.Id))!.Select(v => v.Version));
    }

    /// Codex review of PR #75: an earlier version is read (and so exported and restored) with the title it was saved with.
    [Fact]
    public async Task EachVersionKeepsItsOwnTitle()
    {
        await using var db = Db();
        var st = new StudioStore(db); await st.EnsureSchemaAsync();
        var d = await st.CreateAsync("owner-t", "Original title", "blank");
        var d2 = await st.SaveAsync("owner-t", d.Id, 1, "Renamed", "draft", new JsonArray());
        Assert.Equal("Renamed", d2!.Title);
        Assert.Equal("Original title", (await st.GetAsync("owner-t", d.Id, 1))!.Title);
        Assert.Equal("Renamed", (await st.GetAsync("owner-t", d.Id))!.Title);
        Assert.True(await st.DeleteAsync("owner-t", d.Id));
    }

    /// Codex review of PR #75: every note up to the per-user cap is listed (the list used to stop at 500).
    [Fact]
    public async Task AllNotesUpToTheCapAreListed()
    {
        await using var db = Db();
        var st = new StudioStore(db); await st.EnsureSchemaAsync();
        const string owner = "owner-notes-501";
        await using (var del = db.CreateCommand("DELETE FROM studio_notes WHERE owner=$1"))
        { del.Parameters.AddWithValue(owner); await del.ExecuteNonQueryAsync(); }
        for (int i = 0; i < 501; i++) await st.AddNoteAsync(owner, $"note {i}", null, null, null);
        var notes = await st.NotesAsync(owner);
        Assert.Equal(501, notes.Count);
        Assert.Contains(notes, n => n.Text == "note 0");
    }

    [Fact]
    public void NormaliseKeepsOnlyReferencesForCorpusBlocksAndRejectsSpoofing()
    {
        var b = StudioStore.Normalise(JsonNode.Parse("""
            [{"type":"citation","origin":"user","doc_id":"syn-s-act","copy":"ABCDEF012345","page":2,"citation":"FAKE","title":"FAKE","quote":"FAKE"}]
            """));
        var c = b[0]!.AsObject();
        Assert.Equal("corpus", c["origin"]!.GetValue<string>());
        Assert.Equal("abcdef012345", c["copy"]!.GetValue<string>());
        Assert.False(c.ContainsKey("citation")); Assert.False(c.ContainsKey("title")); Assert.False(c.ContainsKey("quote"));
        Assert.Throws<StudioValidationException>(() => StudioStore.Normalise(JsonNode.Parse("""[{"type":"text","origin":"corpus","text":"pretend source"}]""")));
        Assert.Throws<StudioValidationException>(() => StudioStore.Normalise(JsonNode.Parse("""[{"type":"citation","doc_id":"x","copy":"short","page":1}]""")));
        Assert.Throws<StudioValidationException>(() => StudioStore.Normalise(JsonNode.Parse("""[{"type":"script","origin":"user","text":"x"}]""")));
        Assert.Throws<StudioValidationException>(() => StudioStore.Normalise(new JsonArray(Enumerable.Range(0, 5).Select(_ => (JsonNode)new JsonObject { ["type"] = "text", ["origin"] = "user", ["text"] = new string('x', 15_000) }).ToArray())));
    }

    [Fact]
    public void TemplatesAreGenericAndNotLegalForms()
    {
        Assert.All(StudioStore.Templates.Where(t => t.Key != "blank"), t => Assert.Contains("not a legal form", t.Value.label));
    }

    // ------------------------------------------------------------------ API
    [Theory]
    [InlineData("/api/studio/documents")]
    [InlineData("/api/studio/notes")]
    [InlineData("/api/studio/templates")]
    [InlineData("/api/commander/domains")]
    [InlineData("/api/commander/domains/disciplinary")]
    public async Task WorkspaceRoutesNeedASession(string path)
    {
        Assert.Equal(HttpStatusCode.Unauthorized, (await f.CreateClient().GetAsync(path)).StatusCode);
    }

    [Fact]
    public async Task StudioPostsNeedCsrfAndSameOrigin()
    {
        var (c, csrf) = await f.Login("reader");
        Assert.Equal(HttpStatusCode.Forbidden, (await c.PostAsJsonAsync("/api/studio/documents", new { title = "x", template = "blank" })).StatusCode);
        Assert.Equal(HttpStatusCode.Forbidden, (await Post(c, csrf, "/api/studio/documents", new { title = "x", template = "blank" }, origin: "http://evil.example")).StatusCode);
        Assert.Equal(HttpStatusCode.Forbidden, (await c.PostAsJsonAsync("/api/studio/notes", new { text = "x" })).StatusCode);
        Assert.Equal(HttpStatusCode.Created, (await Post(c, csrf, "/api/studio/documents", new { title = "ok", template = "blank" })).StatusCode);
    }

    [Fact]
    public async Task AnotherUserIncludingAnAdminGets404OnEveryRoute()
    {
        var (owner, ocsrf) = await f.Login("reader");
        var id = (await J(await Post(owner, ocsrf, "/api/studio/documents", new { title = "Private", template = "memo" })))["id"]!.GetValue<string>();
        var (other, csrf) = await f.Login("admin");
        foreach (var path in new[] { $"/api/studio/documents/{id}", $"/api/studio/documents/{id}/versions", $"/api/studio/documents/{id}/export?format=html",
                                     $"/api/studio/documents/{id}?version=1" })
            Assert.Equal(HttpStatusCode.NotFound, (await other.GetAsync(path)).StatusCode);
        Assert.Equal(HttpStatusCode.NotFound, (await Post(other, csrf, $"/api/studio/documents/{id}/save", new { base_version = 1, title = "x", state = "draft", blocks = Array.Empty<object>() })).StatusCode);
        Assert.Equal(HttpStatusCode.NotFound, (await Post(other, csrf, $"/api/studio/documents/{id}/append", new { blocks = new[] { new { type = "text", origin = "user", text = "x" } } })).StatusCode);
        Assert.Equal(HttpStatusCode.NotFound, (await Post(other, csrf, $"/api/studio/documents/{id}/delete", new { })).StatusCode);
        Assert.DoesNotContain(id, await other.GetStringAsync("/api/studio/documents"));
        Assert.Equal(HttpStatusCode.OK, (await owner.GetAsync($"/api/studio/documents/{id}")).StatusCode);   // still the owner's
    }

    /// C15 security review M1: OCR text is for search only, so a quote block on an OCR page never carries the text,
    /// in the API or in either export; the citation itself stays available.
    [Fact]
    public async Task OcrTextIsNeverExportedAsAQuotation()
    {
        var (user, csrf) = await f.Login("reader");
        var s = JsonNode.Parse(await user.GetStringAsync("/api/search?q=" + Uri.EscapeDataString("सुनवाई से पहले लिखित सूचना")))!;
        var hit = s["passages"]!.AsArray().First(p => p!["ocr"]!.GetValue<bool>())!;
        var doc = hit["doc_id"]!.GetValue<string>(); var page = hit["page"]!.GetValue<int>(); var pid = hit["passage_id"]!.GetValue<string>();
        var copy = s["documents"]![doc]!["copy_sha256"]!.GetValue<string>()[..12];
        var id = (await J(await Post(user, csrf, "/api/studio/documents", new { title = "Quotes OCR", template = "blank" })))["id"]!.GetValue<string>();
        var r = await Post(user, csrf, $"/api/studio/documents/{id}/append", new { blocks = new object[] { new { type = "quote", doc_id = doc, copy, page, passage_id = pid } } });
        Assert.Equal(HttpStatusCode.OK, r.StatusCode);
        var q = (await J(r))["blocks"]!.AsArray().Single(b => b!["type"]!.GetValue<string>() == "quote")!.AsObject();
        Assert.True(q["available"]!.GetValue<bool>());
        Assert.False(q["quote_available"]!.GetValue<bool>());
        Assert.False(q.ContainsKey("quote"));
        foreach (var fmt in new[] { "html", "md" })
            Assert.DoesNotContain("सुनवाई", await user.GetStringAsync($"/api/studio/documents/{id}/export?format={fmt}"));
    }

    [Fact]
    public async Task CitationsFollowWithdrawalWithoutDeletingTheAuthorsText()
    {
        const string doc = "syn-h-manual";
        var (user, csrf) = await f.Login("reader");
        var meta = JsonNode.Parse(await user.GetStringAsync($"/api/v2/documents/{doc}/pdf-meta"))!;
        var copy = meta["copy_sha256"]!.GetValue<string>()[..12];
        var qp = JsonNode.Parse(await user.GetStringAsync($"/api/documents/{doc}/text"))!["pages"]!.AsArray().First(pg => pg!["passages"]!.AsArray().Count > 0)!;
        var pid = qp["passages"]![0]!["id"]!.GetValue<string>(); var qpage = qp["page"]!.GetValue<int>();
        var id = (await J(await Post(user, csrf, "/api/studio/documents", new { title = "Cites the manual", template = "blank" })))["id"]!.GetValue<string>();
        var app = await Post(user, csrf, $"/api/studio/documents/{id}/append", new { blocks = new object[] {
            new { type = "text", origin = "user", text = "My own analysis <script>alert(1)</script>" },
            new { type = "citation", doc_id = doc, copy, page = 1, citation = "FAKE CITATION TEXT" },
            new { type = "quote", doc_id = doc, copy, page = qpage, passage_id = pid } } });
        Assert.Equal(HttpStatusCode.OK, app.StatusCode);
        var d = await J(app);
        var cite = d["blocks"]!.AsArray().Single(b => b!["type"]!.GetValue<string>() == "citation")!;
        Assert.True(cite["available"]!.GetValue<bool>());
        Assert.DoesNotContain("FAKE", cite["citation"]!.GetValue<string>());
        var title = cite["title"]!.GetValue<string>();

        var (admin, acsrf) = await f.Login("admin");
        Assert.Equal(HttpStatusCode.OK, (await Post(admin, acsrf, "/api/admin/withdraw", new { doc_id = doc, reason = "C15 studio withdrawal test" })).StatusCode);
        try
        {
            var after = await J(await user.GetAsync($"/api/studio/documents/{id}"));
            var c2 = after["blocks"]!.AsArray().Single(b => b!["type"]!.GetValue<string>() == "citation")!.AsObject();
            Assert.False(c2["available"]!.GetValue<bool>());
            Assert.Equal("Source no longer available in this installation.", c2["notice"]!.GetValue<string>());
            Assert.False(c2.ContainsKey("title")); Assert.False(c2.ContainsKey("citation"));
            // Codex review of PR #75: the unavailable quote keeps the author's stored reference, so saving the rendered
            // document back (as the editor does) succeeds and the reference survives without any source text
            var q2 = after["blocks"]!.AsArray().Single(b => b!["type"]!.GetValue<string>() == "quote")!.AsObject();
            Assert.Equal(pid, q2["passage_id"]!.GetValue<string>()); Assert.False(q2.ContainsKey("quote"));
            var wire = after["blocks"]!.AsArray().Select(b => b!["type"]!.GetValue<string>() is "citation" or "quote"
                ? (JsonNode)new JsonObject { ["type"] = b["type"]!.GetValue<string>(), ["doc_id"] = b["doc_id"]!.GetValue<string>(), ["copy"] = b["copy"]!.GetValue<string>(),
                                             ["page"] = b["page"]!.GetValue<int>(), ["passage_id"] = b["passage_id"]?.GetValue<string>(), ["para"] = b["para"]?.GetValue<string>() }
                : new JsonObject { ["type"] = b["type"]!.GetValue<string>(), ["origin"] = b["origin"]?.GetValue<string>(), ["text"] = b["text"]?.GetValue<string>() }).ToArray();
            var saved = await Post(user, csrf, $"/api/studio/documents/{id}/save", new { blocks = new JsonArray(wire), base_version = after["version"]!.GetValue<int>(), title = "Cites the manual", state = "draft" });
            Assert.Equal(HttpStatusCode.OK, saved.StatusCode);
            Assert.Contains("My own analysis", after.ToJsonString());               // the author's text is kept
            var html = await user.GetStringAsync($"/api/studio/documents/{id}/export?format=html");
            Assert.DoesNotContain(title, html);
            Assert.Contains("Source no longer available in this installation.", html);
            Assert.Contains("Not legally approved", html);
            Assert.DoesNotContain("<script>alert(1)</script>", html);              // escaped
            Assert.Contains("&lt;script&gt;", html);
            var md = await user.GetStringAsync($"/api/studio/documents/{id}/export?format=md");
            Assert.DoesNotContain(title, md);
            Assert.Contains("Not legally approved", md);
        }
        finally
        {
            Assert.Equal(HttpStatusCode.OK, (await Post(admin, acsrf, "/api/admin/reinstate", new { doc_id = doc, reason = "C15 studio withdrawal test restore" })).StatusCode);
        }
        var back = await J(await user.GetAsync($"/api/studio/documents/{id}"));
        Assert.True(back["blocks"]!.AsArray().Single(b => b!["type"]!.GetValue<string>() == "citation")!["available"]!.GetValue<bool>());
    }

    [Fact]
    public async Task AuditEntriesAreMetadataOnly()
    {
        var (user, csrf) = await f.Login("reader");
        var id = (await J(await Post(user, csrf, "/api/studio/documents", new { title = "Audit check", template = "blank" })))["id"]!.GetValue<string>();
        const string secret = "WORKING-CONTENT-MUST-NOT-BE-LOGGED-7f3a";
        Assert.Equal(HttpStatusCode.OK, (await Post(user, csrf, $"/api/studio/documents/{id}/save", new { base_version = 1, title = "Audit check", state = "draft",
            blocks = new[] { new { type = "text", origin = "user", text = secret } } })).StatusCode);
        await using var db = Db();
        await using var c = await db.OpenConnectionAsync();
        await using var q = new NpgsqlCommand("SELECT count(*) FROM audit_log WHERE detail LIKE '%' || $1 || '%' OR object LIKE '%' || $1 || '%'", c);
        q.Parameters.AddWithValue(secret);
        Assert.Equal(0L, (long)(await q.ExecuteScalarAsync())!);
        Assert.DoesNotContain(f.Log, l => l.Contains(secret));
    }

    [Fact]
    public async Task CommanderDomainsCarryNoSourceFieldsForUnheldProvisions()
    {
        var (user, _) = await f.Login("reader");
        var list = await J(await user.GetAsync("/api/commander/domains"));
        Assert.Equal(6, list["domains"]!.AsArray().Count);
        Assert.Contains("not legal advice", list["label"]!.GetValue<string>());
        var d = await J(await user.GetAsync("/api/commander/domains/disciplinary"));
        Assert.NotEmpty(d["review_questions"]!.AsArray());
        // the SYN site holds no Army Act or Army Rules: every item is reported as unavailable, with no derived field
        foreach (var it in d["groups"]!.AsArray().SelectMany(g => g!["items"]!.AsArray()))
        {
            Assert.False(it!["found"]!.GetValue<bool>());
            Assert.Null(it["heading"]); Assert.Null(it["excerpt"]); Assert.Null(it["doc_id"]); Assert.Null(it["instrument"]);
        }
        Assert.Equal(HttpStatusCode.NotFound, (await user.GetAsync("/api/commander/domains/no-such-area")).StatusCode);
    }
}
