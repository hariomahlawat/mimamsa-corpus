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
