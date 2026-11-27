using System.Text.Json;
using Mimamsa.Core.Citation;
using Mimamsa.Core.Commander;
using Mimamsa.Core.Delivery;
using Mimamsa.Core.Generation;
using Mimamsa.Core.Graph;
using Mimamsa.Core.Search;

namespace Mimamsa.Tests;

/// C16 WP04: in-process tests pick the text store from MIMAMSA_TEST_TEXT_STORE (memory by default, or disk), so the
/// whole suite can be run against either store. Disk stores go under a per-process temporary root, never into the
/// shared fixture sites.
public static class TestText
{
    public static string Store => Environment.GetEnvironmentVariable("MIMAMSA_TEST_TEXT_STORE") is { Length: > 0 } s ? s : "memory";
    static readonly string Root = Path.Combine(Path.GetTempPath(), "mimamsa-c16-text-" + Environment.ProcessId);
    static string Key(string site) => Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(System.Text.Encoding.UTF8.GetBytes(Path.GetFullPath(site))))[..12];
    public static TextStoreOptions Options(string site) => Store == "disk" ? new TextStoreOptions { Store = "disk", Dir = Path.Combine(Root, Key(site)) } : TextStoreOptions.Memory;
    public static GenerationStore Load(string site) => GenerationStore.Load(site, null, Options(site));
}

/// C16 WP04 (ADR-0008): the disk text store gives exactly what the in-memory reference gives, reads no text until it
/// is used, verifies text against the generation's text_sha256, and recovers from interrupted builds and corruption
/// without ever serving unverified text.
public class TextStoreTests : IDisposable
{
    readonly string _root = Path.Combine(Path.GetTempPath(), "mimamsa-c16-ts-" + Guid.NewGuid().ToString("N")[..8]);
    readonly List<string> _log = new();
    readonly List<GenerationStore> _opened = new();

    public void Dispose()
    {
        foreach (var g in _opened) (g.Text as IDisposable)?.Dispose();
        Microsoft.Data.Sqlite.SqliteConnection.ClearAllPools();
        try { Directory.Delete(_root, true); } catch { }
    }

    GenerationStore Disk(string site, TextStoreOptions? o = null, string? root = null)
    {
        var g = GenerationStore.Load(site, null, (o ?? new TextStoreOptions()) with { Store = "disk", Dir = root ?? _root }, _log.Add);
        _opened.Add(g);
        return g;
    }

    static GenerationStore Mem(string site) => GenerationStore.Load(site);
    static string? SampleSite => Environment.GetEnvironmentVariable("MIMAMSA_SAMPLE_SITE") is { Length: > 0 } s && Directory.Exists(s) ? s : null;
    string Published => Directory.GetDirectories(_root).Single(d => !Path.GetFileName(d).StartsWith('.'));
    string DbPath => Path.Combine(Published, DiskTextStore.DbFile);

    static readonly string[] Queries = { "notice", "s.17 Bracken Service Act", "OA 411/2021", "hearing written notice allegation",
        "exact:\"summary of evidence\"", "summary AND evidence", "\"written notice\" NEAR/5 hearing", "hear*", "title:bracken", "Vale v Lark", "hearnig",
        "s.69 Army Act", "court martial", "disability pension", "\"summary of evidence\"", "Rule 22 Army Rules", "section 302 IPC", "Dharamvir Singh" };

    /// Every observable text fact of a generation: derivative identity, text assessment, page order and fields, and
    /// passage order, identity and text. Equal strings mean the two stores attach identical text.
    static IEnumerable<string> TextFacts(GenerationStore g)
    {
        yield return "issues:" + string.Join(",", g.LoadIssues.Select(kv => kv.Key + "=" + kv.Value));
        foreach (var d in g.Documents.Values)
        {
            yield return $"D|{d.DocId}|{d.DerivativeId}|{d.DerivativeTextSha}|{d.PipelineName}|{d.PipelineVersion}|{d.QuotingPermitted}|{JsonSerializer.Serialize(d.TextAssessment)}";
            foreach (var (n, p) in d.Pages) yield return $"P|{n}|{p.Page}|{p.Method}|{p.LowConfidence}|{p.OcrConfidence:R}|{p.Length}|{p.Text.Length}|{p.Text}";
            foreach (var p in d.Passages) yield return $"S|{p.Key}|{p.Page}|{p.CharStart}|{p.CharEnd}|{p.ParagraphLabel}|{p.Length}|{p.Text}";
        }
    }

    static List<string> SearchSig(SearchService s, string q)
    {
        var r = s.Search(q, new SearchFilters());
        var terms = r.HighlightTerms.ToHashSet(StringComparer.Ordinal);
        var ix = s.Index;
        return r.Hits.Select((h, i) =>
            {
                var p = ix.Passages[h.PassageIndex];
                var head = $"{h.PassageIndex}:{p.Key}:{h.Tier}:{h.Score:R}:{string.Join("|", h.Reasons)}";
                if (i >= 60) return head;
                var sn = Snippets.Build(p.Text, terms, r.HighlightPhrases);   // what the search API returns for a hit
                return head + $"|{sn.Text}|{string.Join(";", sn.Highlights.Select(x => x[0] + "-" + x[1]))}|{sn.TruncatedStart}|{sn.TruncatedEnd}|{sn.PassageCharStart}";
            })
            .Concat(r.Chips.Select(c => $"chip:{c.Kind}:{c.Text}:{c.Source}"))
            .Concat(r.Facets.Select(f => $"facet:{f.Key}:{string.Join(",", f.Value.Select(v => v.Value + "=" + v.Count))}"))
            .Append($"{r.State}/{r.Mode}/{r.TotalDocuments}/{r.TotalPassages}/{string.Join(",", r.HighlightTerms.Order(StringComparer.Ordinal))}").ToList();
    }

    /// The document text API's page projection (Api.cs /api/documents/{id}/text), all pages.
    static string DocumentTextApi(DocumentRecord d) => JsonSerializer.Serialize(new
    {
        doc_id = d.DocId, copy_sha256 = d.CopySha, page_count = d.PageCount,
        derivative = new { id = d.DerivativeId, text_sha256 = d.DerivativeTextSha, pipeline = d.PipelineName, version = d.PipelineVersion, quoting_permitted = d.QuotingPermitted },
        text_pages = d.Pages.Keys.Order().ToArray(),
        pages = d.Pages.Values.OrderBy(x => x.Page).Select(x => new { page = x.Page, method = x.Method, low_confidence = x.LowConfidence, ocr = x.Method == "ocr", text = x.Text,
            passages = d.Passages.Where(ps => ps.Page == x.Page).Select(ps => new { id = ps.PassageId, start = ps.CharStart, end = ps.CharEnd, para = ps.ParagraphLabel }) }),
        chars = d.Pages.Values.OrderBy(x => x.Page).Select(x => x.Length),
    });

    /// Citation, permalink and Studio quote for every passage (Api.cs citation route and Api.Workspace quote block).
    static IEnumerable<string> CitationsAndQuotes(GenerationStore g)
    {
        foreach (var d in g.Documents.Values)
            foreach (var p in d.Passages)
            {
                var label = d.DocType is "judgment" or "order" ? p.ParagraphLabel : null;
                var found = d.Passages.FirstOrDefault(x => x.PassageId == p.PassageId && x.Page == p.Page);
                var quote = found is null || !d.QuotingPermitted ? null : found.Text.Length > 1500 ? found.Text[..1500] + "…" : found.Text;
                yield return $"{LegalCitation.Format(d, p.Page, label)}|{LegalCitation.Permalink(g.Release.ReleaseId, d.DocId, d.CopySha, p.Page, label)}|" +
                             $"{LegalCitation.InternalReference(d.DocId, d.CopySha, p.Page, g.Release.ReleaseId)}|{quote}";
            }
    }

    static IEnumerable<string> CommanderExcerpts(GenerationStore g)
    {
        var src = new TocCommanderSource(g);
        foreach (var dom in CommanderDomains.All)
            foreach (var r in dom.Groups.SelectMany(x => x.Items).Concat(dom.Safeguards))
                yield return JsonSerializer.Serialize(src.Resolve(r));
    }

    static IEnumerable<string> Tocs(GenerationStore g) =>
        g.Documents.Values.Where(d => d.IsStatute).Select(d => d.DocId + ":" + JsonSerializer.Serialize(Toc.Build(d)));

    void AssertEquivalent(GenerationStore mem, GenerationStore disk)
    {
        Assert.Equal("memory", mem.Text.Kind);
        Assert.Equal("disk", disk.Text.Kind);
        Assert.Equal(TextFacts(mem), TextFacts(disk));
        Assert.Equal(mem.Documents.Values.Select(DocumentTextApi), disk.Documents.Values.Select(DocumentTextApi));
        Assert.Equal(CitationsAndQuotes(mem), CitationsAndQuotes(disk));
        var sm = new SearchService(SearchIndex.Build(mem), _ => false);
        var sd = new SearchService(SearchIndex.Build(disk), _ => false);
        foreach (var q in Queries) Assert.Equal(SearchSig(sm, q), SearchSig(sd, q));
        Assert.Equal(Tocs(mem), Tocs(disk));
        Assert.Equal(CommanderExcerpts(mem), CommanderExcerpts(disk));
        Assert.Equal(JsonSerializer.Serialize(GraphBuilder.Build(mem)), JsonSerializer.Serialize(GraphBuilder.Build(disk)));   // graph quotes
        Assert.Equal(JsonSerializer.Serialize(mem.Relations.Edges), JsonSerializer.Serialize(disk.Relations.Edges));
    }

    [Fact]
    public void DiskStoreGivesExactlyWhatTheMemoryStoreGivesOnTheSynSite()
    {
        var mem = Mem(Syn.Site);
        foreach (var built in new[] { true, false })   // freshly built, then reopened from disk
        {
            var disk = Disk(Syn.Site);
            Assert.Contains(_log, l => l.Contains(built ? "built and published" : "text store: opened"));
            AssertEquivalent(mem, disk);
            _log.Clear();
        }
    }

    [Fact]
    public void DiskStoreGivesExactlyWhatTheMemoryStoreGivesOnTheRealSample()
    {
        if (SampleSite is not { } site) return;   // the real sample is optional on a development host
        AssertEquivalent(Mem(site), Disk(site));
    }

    [Fact]
    public void OpeningReadsNoTextAndReadsAreVerifiedAndCached()
    {
        Disk(Syn.Site);
        var g = Disk(Syn.Site);   // reopened
        var s0 = g.Text.Stats();
        Assert.Equal(0, s0.PageReads); Assert.Equal(0, s0.DocumentsVerified); Assert.Equal(0, s0.BytesRead);
        var d = g.Documents.Values.First(x => x.Passages.Count > 0);
        var p = d.Passages[0];
        var once = p.Text;
        var s1 = g.Text.Stats();
        Assert.Equal(1, s1.DocumentsVerified);   // the whole derivative was hashed against text_sha256 on first use
        Assert.Equal(1, s1.PageReads);
        Assert.Equal(once, d.Passages[0].Text);
        var s2 = g.Text.Stats();
        Assert.Equal(1, s2.PageReads);           // served from the cache
        Assert.True(s2.CacheHits >= 1);
        Assert.Equal(1, s2.DocumentsVerified);
    }

    [Fact]
    public void TheCacheStaysWithinItsBudgetAndOutputIsUnchanged()
    {
        var mem = Mem(Syn.Site);
        var g = Disk(Syn.Site, new TextStoreOptions { CacheBytes = 8 << 10 });   // 4k chars over 16 shards: far less than the text
        Assert.Equal(TextFacts(mem), TextFacts(g));
        Assert.Equal(TextFacts(mem), TextFacts(g));   // second pass: evictions and re-reads
        var st = g.Text.Stats();
        Assert.True(st.CachedChars <= st.CacheBudgetChars, $"{st.CachedChars} > {st.CacheBudgetChars}");
        Assert.True(st.PageReads > g.Documents.Values.Sum(d => d.Pages.Count));   // pages were evicted and read again
    }

    [Fact]
    public void WithdrawnAndIneligibleDocumentsStayHiddenWithTheDiskStore()
    {
        var g = Disk(Syn.Site);
        var hidden = g.Documents.Keys.First(k => k.StartsWith("syn-j-", StringComparison.Ordinal));
        var svc = new SearchService(SearchIndex.Build(g), d => d == hidden);
        foreach (var q in Queries) Assert.DoesNotContain(svc.Search(q, new SearchFilters()).Hits, h => svc.Index.Passages[h.PassageIndex].DocId == hidden);
        // The single eligibility decision is unchanged: a withdrawn document is not visible, so no route reaches its text.
        var st = new ServingState();
        var e = new Eligibility(g, st, RestrictedRegister.Empty, new Vault(Syn.Site));
        Assert.NotNull(e.Visible(hidden));
        st.Load(new[] { (hidden, g.Documents[hidden].CopySha) }, 1, "test");
        Assert.Null(e.Visible(hidden));
        Assert.Null(e.Visible("syn-v-staged"));   // staged: never visible
    }

    [Fact]
    public void TamperedTextIsDetectedOnFirstUseAndWithheld()
    {
        Disk(Syn.Site);
        var victim = Mem(Syn.Site).Documents.Values.First(d => d.Passages.Count > 0);
        // Flip bytes inside the stored derivative (as an attacker or a disk fault would), then open without the whole-file check.
        Microsoft.Data.Sqlite.SqliteConnection.ClearAllPools();
        using (var c = new Microsoft.Data.Sqlite.SqliteConnection($"Data Source={DbPath};Pooling=False"))
        {
            c.Open();
            using var cmd = new Microsoft.Data.Sqlite.SqliteCommand("UPDATE texts SET bytes = CAST(replace(CAST(bytes AS TEXT), 'e', 'E') AS BLOB) WHERE di = (SELECT di FROM docs WHERE doc_id = $d)", c);
            cmd.Parameters.AddWithValue("$d", victim.DocId);
            Assert.Equal(1, cmd.ExecuteNonQuery());
        }
        var g = Disk(Syn.Site, new TextStoreOptions { VerifyOnOpen = false });
        var d = g.Documents[victim.DocId];
        Assert.Throws<TextIntegrityException>(() => d.Passages[0].Text);
        Assert.Throws<TextIntegrityException>(() => d.Pages.Values.First().Text);   // stays withheld
        var other = g.Documents.Values.First(x => x.DocId != victim.DocId && x.Passages.Count > 0);
        Assert.Equal(Mem(Syn.Site).Documents[other.DocId].Passages[0].Text, other.Passages[0].Text);   // other documents unaffected
    }

    [Fact]
    public void ACorruptedStoreFileIsQuarantinedAndRebuiltIdentically()
    {
        Disk(Syn.Site);
        Microsoft.Data.Sqlite.SqliteConnection.ClearAllPools();
        foreach (var g0 in _opened) (g0.Text as IDisposable)?.Dispose();
        var bytes = File.ReadAllBytes(DbPath);
        for (int i = 0; i < 64; i++) bytes[bytes.Length / 2 + i] ^= 0x5A;
        File.WriteAllBytes(DbPath, bytes);
        var g = Disk(Syn.Site);
        Assert.Contains(_log, l => l.Contains("SHA-256 differs from manifest"));
        Assert.Contains(_log, l => l.Contains("quarantined"));
        Assert.Contains(_log, l => l.Contains("built and published"));
        Assert.Single(Directory.GetDirectories(_root, ".quarantine-*"));
        Assert.Equal(TextFacts(Mem(Syn.Site)), TextFacts(g));
    }

    [Fact]
    public void ACorruptedStoreIsRefusedWhenRebuildIsDisabled()
    {
        Disk(Syn.Site);
        foreach (var g0 in _opened) (g0.Text as IDisposable)?.Dispose();
        Microsoft.Data.Sqlite.SqliteConnection.ClearAllPools();
        using (var f = new FileStream(DbPath, FileMode.Open)) f.SetLength(f.Length - 8192);   // truncated
        Assert.Throws<TextIntegrityException>(() => Disk(Syn.Site, new TextStoreOptions { RebuildOnFailure = false, VerifyOnOpen = false }));
    }

    [Fact]
    public void AnInterruptedBuildIsNeverServedAndIsCleanedUpAtTheNextStart()
    {
        Assert.Throws<IOException>(() => Disk(Syn.Site, new TextStoreOptions { FailAfterDocuments = 2 }));
        Assert.Single(Directory.GetDirectories(_root, ".building-*"));
        Assert.DoesNotContain(Directory.GetDirectories(_root), d => !Path.GetFileName(d).StartsWith('.'));   // nothing published
        Microsoft.Data.Sqlite.SqliteConnection.ClearAllPools();
        var g = Disk(Syn.Site);
        Assert.Contains(_log, l => l.Contains("removing interrupted build"));
        Assert.Empty(Directory.GetDirectories(_root, ".building-*"));
        Assert.Equal(TextFacts(Mem(Syn.Site)), TextFacts(g));
    }

    [Fact]
    public void AChangedDerivativeRecordIsRebuiltNotServed()
    {
        var site = Syn.CopySite();
        try
        {
            var root = Path.Combine(_root, "copy");
            Disk(site, root: root);
            var gid = File.ReadAllText(Path.Combine(site, "ACTIVE")).Trim();
            var rec = Path.Combine(site, "generations", gid, "records", "derived_text.jsonl");
            var lines = File.ReadAllLines(rec);
            File.WriteAllLines(rec, lines.Skip(1));   // one derivative fewer
            _log.Clear();
            var g = Disk(site, root: root);
            Assert.Contains(_log, l => l.Contains("source digest differs"));
            Assert.Contains(_log, l => l.Contains("built and published"));
            Assert.Equal(TextFacts(Mem(site)), TextFacts(g));
        }
        finally { foreach (var g0 in _opened) (g0.Text as IDisposable)?.Dispose(); Microsoft.Data.Sqlite.SqliteConnection.ClearAllPools(); try { Directory.Delete(site, true); } catch { } }
    }

    [Fact]
    public void TamperedDerivativeFileGivesTheSameLoadIssuesInBothStores()
    {
        var site = Syn.CopySite();
        try
        {
            var gid = File.ReadAllText(Path.Combine(site, "ACTIVE")).Trim();
            var f = Directory.EnumerateFiles(Path.Combine(site, "generations", gid, "derived")).First();
            File.AppendAllText(f, "tampered");
            var disk = Disk(site, root: Path.Combine(_root, "tamper"));
            Assert.Equal(1, disk.LoadIssues["DERIVATIVE_TEXT_HASH_MISMATCH"]);
            Assert.Equal(TextFacts(Mem(site)), TextFacts(disk));
        }
        finally { foreach (var g0 in _opened) (g0.Text as IDisposable)?.Dispose(); Microsoft.Data.Sqlite.SqliteConnection.ClearAllPools(); try { Directory.Delete(site, true); } catch { } }
    }

    [Fact]
    public void ConcurrentReadersGetIdenticalText()
    {
        var mem = Mem(Syn.Site);
        var g = Disk(Syn.Site, new TextStoreOptions { CacheBytes = 128 << 10 });
        var expected = mem.Documents.Values.SelectMany(d => d.Passages).Select(p => p.Key + "|" + p.Text).ToList();
        var passages = g.Documents.Values.SelectMany(d => d.Passages).ToList();
        Parallel.For(0, 8, k =>
        {
            for (int i = 0; i < passages.Count; i++)
            {
                int j = (i * 7 + k * 13) % passages.Count;
                Assert.Equal(expected[j], passages[j].Key + "|" + passages[j].Text);
            }
        });
    }

    // ------------------------------------------------------------------ ChatGPT review of PR #80
    void CloseAll() { foreach (var g0 in _opened) (g0.Text as IDisposable)?.Dispose(); _opened.Clear(); Microsoft.Data.Sqlite.SqliteConnection.ClearAllPools(); }

    static void Sql(string db, string sql, params (string k, object v)[] ps)
    {
        using var c = new Microsoft.Data.Sqlite.SqliteConnection($"Data Source={db};Pooling=False");
        c.Open();
        using var cmd = new Microsoft.Data.Sqlite.SqliteCommand(sql, c);
        foreach (var (k, v) in ps) cmd.Parameters.AddWithValue(k, v);
        Assert.True(cmd.ExecuteNonQuery() >= 1, sql);
    }

    /// What an attacker with write access to the store directory can do: make the manifest agree with the altered file.
    static void RegenerateManifest(string dir)
    {
        var db = Path.Combine(dir, DiskTextStore.DbFile); var mf = Path.Combine(dir, DiskTextStore.ManifestFile);
        var m = System.Text.Json.Nodes.JsonNode.Parse(File.ReadAllText(mf))!.AsObject();
        m["file_bytes"] = new FileInfo(db).Length;
        using (var f = File.OpenRead(db)) m["file_sha256"] = Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(f)).ToLowerInvariant();
        File.WriteAllText(mf, m.ToJsonString());
    }

    public static IEnumerable<object[]> Tampers() =>
        from t in new[] { "quoting", "page_range", "paragraph_label", "text_and_hash" } from v in new[] { true, false } select new object[] { t, v };

    /// P1: a reopened store's metadata is bound to the generation's records, not to its own (locally writable) manifest.
    /// Each alteration below is made consistent with a regenerated manifest, so only the binding can catch it; with either
    /// VerifyOnOpen setting it is refused when rebuilding is disabled, and otherwise quarantined and rebuilt from source.
    [Theory]
    [MemberData(nameof(Tampers))]
    public void ReopenedMetadataIsBoundToTheGenerationRecords(string tamper, bool verifyOnOpen)
    {
        var mem = Mem(Syn.Site);
        Disk(Syn.Site);
        CloseAll();
        var victim = mem.Documents.Values.Where(d => d.Passages.Any(p => p.ParagraphLabel is not null) || d.Passages.Count > 0)
            .OrderBy(d => d.QuotingPermitted ? 1 : 0).First();   // prefer a document whose text may NOT be quoted
        var di = ("$d", (object)victim.DocId);
        switch (tamper)
        {
            case "quoting":
                Sql(DbPath, "UPDATE docs SET quoting_permitted = 1 - quoting_permitted WHERE doc_id = $d", di); break;
            case "page_range":
                Sql(DbPath, "UPDATE pages SET byte_len = byte_len - 1, char_len = char_len - 1 WHERE id = (SELECT min(id) FROM pages WHERE di = (SELECT di FROM docs WHERE doc_id = $d))", di); break;
            case "paragraph_label":
                Sql(DbPath, "UPDATE passages SET paragraph_label = 'para 999' WHERE id = (SELECT min(id) FROM passages WHERE di = (SELECT di FROM docs WHERE doc_id = $d))", di); break;
            case "text_and_hash":
                // Substitute different text of the same length and record its own hash as the derivative's text_sha256.
                byte[] bytes;
                using (var c = new Microsoft.Data.Sqlite.SqliteConnection($"Data Source={DbPath};Pooling=False"))
                {
                    c.Open();
                    using var q = new Microsoft.Data.Sqlite.SqliteCommand("SELECT t.bytes FROM texts t JOIN docs d ON d.di = t.di WHERE d.doc_id = $d", c);
                    q.Parameters.AddWithValue("$d", victim.DocId);
                    bytes = (byte[])q.ExecuteScalar()!;
                }
                for (int i = 0; i < bytes.Length; i++) if (bytes[i] == (byte)'e') bytes[i] = (byte)'E';
                var sha = Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(bytes)).ToLowerInvariant();
                Sql(DbPath, "UPDATE texts SET bytes = $b WHERE di = (SELECT di FROM docs WHERE doc_id = $d)", ("$b", bytes), di);
                Sql(DbPath, "UPDATE docs SET text_sha256 = $s WHERE doc_id = $d", ("$s", sha), di);
                break;
        }
        RegenerateManifest(Published);
        _log.Clear();
        // Refused either by the binding or, for an inconsistent anchor, already by the metadata sanity check.
        var refused = Assert.Throws<TextIntegrityException>(() => Disk(Syn.Site, new TextStoreOptions { VerifyOnOpen = verifyOnOpen, RebuildOnFailure = false }));
        Assert.Matches("differs from the generation's records|metadata unreadable", refused.Message);
        _log.Clear();
        var g = Disk(Syn.Site, new TextStoreOptions { VerifyOnOpen = verifyOnOpen });
        Assert.Contains(_log, l => l.Contains("failed verification"));
        Assert.Contains(_log, l => l.Contains("quarantined"));
        Assert.Contains(_log, l => l.Contains("built and published"));
        Assert.Equal(mem.Documents[victim.DocId].QuotingPermitted, g.Documents[victim.DocId].QuotingPermitted);   // the store never grants quoting
        Assert.Equal(TextFacts(mem), TextFacts(g));
    }

    /// P1: once a document fails verification, none of its pages is served again, including pages already cached, and
    /// that holds for concurrent readers: a read that starts after the failure is published never returns text.
    [Fact]
    public void AFailedDocumentNeverServesItsCachedPages()
    {
        var mem = Mem(Syn.Site);
        Disk(Syn.Site);
        var g = Disk(Syn.Site);   // reopened: nothing read yet
        var d = g.Documents.Values.First(x => x.Pages.Count >= 2);
        var pages = d.Pages.Values.OrderBy(p => p.Page).ToList();
        var warm = pages[0]; var cold = pages[1];
        Assert.Equal(mem.Documents[d.DocId].Pages[warm.Page].Text, warm.Text);   // verified and cached
        Assert.Equal(1, g.Text.Stats().DocumentsVerified);
        // Corrupt the cold page's bytes in place (same length), as a disk fault would after verification.
        using (var c = new Microsoft.Data.Sqlite.SqliteConnection($"Data Source={DbPath};Pooling=False"))
        {
            c.Open();
            long di, start;
            using (var q = new Microsoft.Data.Sqlite.SqliteCommand("SELECT p.di, p.byte_start FROM pages p JOIN docs x ON x.di = p.di WHERE x.doc_id = $d AND p.page = $p", c))
            {
                q.Parameters.AddWithValue("$d", d.DocId); q.Parameters.AddWithValue("$p", cold.Page);
                using var r = q.ExecuteReader(); Assert.True(r.Read()); di = r.GetInt64(0); start = r.GetInt64(1);
            }
            using var blob = new Microsoft.Data.Sqlite.SqliteBlob(c, "texts", "bytes", di);
            blob.Position = start; var b = new byte[1]; blob.ReadExactly(b);
            blob.Position = start; blob.Write(new[] { (byte)(b[0] ^ 0x20) });
        }
        int published = 0, servedAfter = 0, reads = 0;
        using var stop = new CancellationTokenSource();
        var readers = Enumerable.Range(0, 6).Select(k => Task.Run(() =>
        {
            while (!stop.IsCancellationRequested)
            {
                bool after = Volatile.Read(ref published) == 1;
                try { _ = warm.Text; if (after) Interlocked.Increment(ref servedAfter); }
                catch (TextIntegrityException) { }
                Interlocked.Increment(ref reads);
            }
        })).ToArray();
        Thread.Sleep(50);
        Assert.Throws<TextIntegrityException>(() => cold.Text);
        Volatile.Write(ref published, 1);
        Thread.Sleep(200);
        stop.Cancel();
        Task.WaitAll(readers);
        Assert.True(reads > 0);
        Assert.Equal(0, servedAfter);
        Assert.Throws<TextIntegrityException>(() => warm.Text);
        Assert.Throws<TextIntegrityException>(() => d.Passages.First(p => p.Page == warm.Page).Text);
        var other = g.Documents.Values.First(x => x.DocId != d.DocId && x.Passages.Count > 0);
        Assert.Equal(mem.Documents[other.DocId].Passages[0].Text, other.Passages[0].Text);   // other documents unaffected
    }

    /// P2: a derivative missing when the store was built and restored afterwards (records unchanged) is available after a
    /// reopen, exactly as the memory store loads it; the cached omission and load issue are not carried over.
    [Theory]
    [InlineData(true)]
    [InlineData(false)]
    public void ADerivativeRestoredAfterTheBuildIsAvailableAfterReopen(bool verifyOnOpen)
    {
        var site = Syn.CopySite();
        try
        {
            var root = Path.Combine(_root, "restore");
            var gid = File.ReadAllText(Path.Combine(site, "ACTIVE")).Trim();
            var f = Directory.EnumerateFiles(Path.Combine(site, "generations", gid, "derived")).First();
            File.Move(f, f + ".away");
            var built = Disk(site, new TextStoreOptions { VerifyOnOpen = verifyOnOpen }, root);
            Assert.Equal(1, built.LoadIssues["DERIVATIVE_TEXT_MISSING"]);
            CloseAll();
            File.Move(f + ".away", f);
            _log.Clear();
            var g = Disk(site, new TextStoreOptions { VerifyOnOpen = verifyOnOpen }, root);
            Assert.Contains(_log, l => l.Contains("is available in the generation but not in the store"));
            Assert.False(g.LoadIssues.ContainsKey("DERIVATIVE_TEXT_MISSING"));
            Assert.Equal(TextFacts(Mem(site)), TextFacts(g));
        }
        finally { CloseAll(); try { Directory.Delete(site, true); } catch { } }
    }

    /// P2: a derivative removed or corrupted after the store was built is not served from the store after a reopen; the
    /// reopened generation omits it with the same load issue as the memory store.
    [Theory]
    [InlineData("remove", true)]
    [InlineData("remove", false)]
    [InlineData("corrupt", true)]
    [InlineData("corrupt", false)]
    public void ADerivativeRemovedOrCorruptedAfterTheBuildIsNotServedAfterReopen(string change, bool verifyOnOpen)
    {
        var site = Syn.CopySite();
        try
        {
            var root = Path.Combine(_root, "lost");
            var gid = File.ReadAllText(Path.Combine(site, "ACTIVE")).Trim();
            var f = Directory.EnumerateFiles(Path.Combine(site, "generations", gid, "derived")).First();
            var built = Disk(site, new TextStoreOptions { VerifyOnOpen = verifyOnOpen }, root);
            Assert.DoesNotContain("DERIVATIVE_TEXT_MISSING", built.LoadIssues.Keys);
            CloseAll();
            if (change == "remove") File.Delete(f);
            else { var b = File.ReadAllBytes(f); b[b.Length / 2] ^= 0x20; File.WriteAllBytes(f, b); }   // same length
            _log.Clear();
            var g = Disk(site, new TextStoreOptions { VerifyOnOpen = verifyOnOpen }, root);
            Assert.Contains(_log, l => l.Contains("is in the store but not available in the generation"));
            Assert.Equal(1, g.LoadIssues[change == "remove" ? "DERIVATIVE_TEXT_MISSING" : "DERIVATIVE_TEXT_HASH_MISMATCH"]);
            Assert.Equal(TextFacts(Mem(site)), TextFacts(g));
        }
        finally { CloseAll(); try { Directory.Delete(site, true); } catch { } }
    }

    [Fact]
    public void RetentionKeepsTheNewestOtherGenerationStores()
    {
        Disk(Syn.Site);
        // Pretend three older generations were published here; only KeepPrevious of them stay.
        var src = Published;
        foreach (var (name, age) in new[] { ("R-old-1", 3), ("R-old-2", 2), ("R-old-3", 1) })
        {
            var dst = Path.Combine(_root, name);
            Directory.CreateDirectory(dst);
            File.Copy(Path.Combine(src, DiskTextStore.ManifestFile), Path.Combine(dst, DiskTextStore.ManifestFile));
            File.SetLastWriteTimeUtc(Path.Combine(dst, DiskTextStore.ManifestFile), DateTime.UtcNow.AddHours(-age));
        }
        Directory.CreateDirectory(Path.Combine(_root, "not-a-store"));   // never deleted: no text-store manifest
        Disk(Syn.Site, new TextStoreOptions { KeepPrevious = 2 });
        var left = Directory.GetDirectories(_root).Select(Path.GetFileName).Where(n => !n!.StartsWith('.')).ToHashSet();
        Assert.Contains("R-old-2", left); Assert.Contains("R-old-3", left); Assert.DoesNotContain("R-old-1", left); Assert.Contains("not-a-store", left);
    }
}
