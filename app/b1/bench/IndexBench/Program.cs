// C15 WP1 in-process search benchmark. Usage:
//   IndexBench --site <site> [--engine memory|disk] [--index-dir <dir>] [--repeat 5] [--readers 10,25]
//              [--signatures <out.json>] [--out <result.json>] [--profile] [--with-page]
//              [--text-store memory|disk --text-dir <dir> --text-cache-mb 64 --doc-sample 300]   (C16 WP04)
//              [--parity <out.json> [--walkthrough <queries.json>] [--quick]]   (C16 WP05: full output signatures)
// Numbers only; no document text is written except the query strings themselves.
using System.Diagnostics;
using System.Text.Json;
using Mimamsa.Core.Generation;
using Mimamsa.Core.Search;

string? Arg(string n) { var i = Array.IndexOf(args, n); return i >= 0 && i + 1 < args.Length ? args[i + 1] : null; }
var site = Arg("--site") ?? throw new ArgumentException("--site is required");
var engine = Arg("--engine") ?? "memory";
int repeat = int.Parse(Arg("--repeat") ?? "5");
var readers = (Arg("--readers") ?? "10,25").Split(',').Select(int.Parse).ToArray();
bool profile = args.Contains("--profile");
bool withPage = args.Contains("--with-page");   // C16: time Search + Page(1) as the HTTP endpoint does

string[] Q = { "s.69 Army Act", "2013 INSC 408", "disability pension", "court martial", "summary of evidence", "AFT jurisdiction",
    "invalided out of service", "exact:\"Entitlement Rules\"", "desertion AND NOT pension", "Rule 22 Army Rules",
    "release medical board", "\"court martial\" NEAR/10 delay", "Civil Appeal No. 4949 of 2013",
    "writ petition armed forces tribunal", "field punishment", "attributable to military service",
    "sentence of dismissal", "section 302 Indian Penal Code", "Navy Act", "natural justice court of inquiry",
    "Dharamvir Singh", "section 302 IPC", "court marshal", "\"summary of evidence\"", "pension*", "title:army" };

var proc = Process.GetCurrentProcess();
double Mb(long b) => Math.Round(b / 1048576.0, 1);
object Mem() { GC.Collect(2, GCCollectionMode.Forced, true, true); GC.WaitForPendingFinalizers(); GC.Collect(); proc.Refresh();
    return new { working_set_mb = Mb(proc.WorkingSet64), managed_heap_mb = Mb(GC.GetTotalMemory(false)) }; }

// C16 WP04: --text-store memory|disk [--text-dir <dir>] [--text-cache-mb 64] selects the generation text store.
var textStore = Arg("--text-store") ?? "memory";
var textOptions = textStore == "disk"
    ? new TextStoreOptions { Store = "disk", Dir = Arg("--text-dir") ?? throw new ArgumentException("--text-dir is required for --text-store disk"),
                             CacheBytes = long.Parse(Arg("--text-cache-mb") ?? "64") << 20 }
    : TextStoreOptions.Memory;
var sw = Stopwatch.StartNew();
var gen = GenerationStore.Load(site, null, textOptions, Console.Error.WriteLine);
long loadMs = sw.ElapsedMilliseconds;
// --replicate R (stress): R copies of every document under synthetic ids. Passage text strings are SHARED with the
// loaded generation, so this measures index scaling (postings, vocabulary, query cost) at R x the passages without
// multiplying the generation's text memory; text memory is reported separately from the unreplicated load.
if (int.TryParse(Arg("--replicate"), out var rep) && rep > 1)
{
    var docs = new Dictionary<string, DocumentRecord>(StringComparer.Ordinal);
    foreach (var d in gen.Documents.Values)
        for (int k = 0; k < rep; k++)
        {
            var c = new DocumentRecord
            {
                DocId = k == 0 ? d.DocId : $"{d.DocId}~r{k}", DocType = d.DocType, Title = d.Title, Number = d.Number, IssuingAuthority = d.IssuingAuthority,
                IssueDate = d.IssueDate, Language = d.Language, CorpusStatus = d.CorpusStatus, CopySha = d.CopySha, CopyBytes = d.CopyBytes, PageCount = d.PageCount,
                Publication = d.Publication, Judicial = d.Judicial, Provenance = d.Provenance, StatusAxes = d.StatusAxes, Restriction = d.Restriction, FieldOrigin = d.FieldOrigin,
            };
            c.DerivativeId = d.DerivativeId; c.OriginalVerified = d.OriginalVerified; c.TextAssessment = d.TextAssessment;
            foreach (var (n, pg) in d.Pages) c.Pages[n] = pg;
            foreach (var p in d.Passages) c.Passages.Add(p with { DocId = c.DocId });
            docs[c.DocId] = c;
        }
    gen = new GenerationStore
    {
        SiteRoot = gen.SiteRoot, GenerationId = gen.GenerationId + $"-x{rep}", Release = gen.Release, Documents = docs, HeldCopies = gen.HeldCopies,
        ProvisionVersions = gen.ProvisionVersions, Abbreviations = gen.Abbreviations, LoadIssues = gen.LoadIssues, Quarantine = gen.Quarantine,
    };
}
var memAfterLoad = Mem();
sw.Restart();
SearchIndex ix = engine switch
{
    "memory" => SearchIndex.Build(gen),
    "disk" => SearchIndex.Open(gen, Arg("--index-dir") ?? throw new ArgumentException("--index-dir is required for disk"), new SearchIndexOptions { CacheBytes = long.Parse(Arg("--cache-mb") ?? "128") << 20, UseForwardCache = !args.Contains("--no-forward-cache") }, Console.Error.WriteLine),
    _ => throw new ArgumentException("engine"),
};
long buildMs = sw.ElapsedMilliseconds;
var memAfterIndex = Mem();
if (Arg("--parity") is { } parityOut) { Parity.Run(ix, parityOut, Arg("--walkthrough"), args.Contains("--quick")); return; }
// C16 WP04: --build-only builds (or opens) the selected stores and reports start-up only.
if (args.Contains("--build-only"))
{
    var b = JsonSerializer.Serialize(new { site, engine, text_store = textStore, load_ms = loadMs, index_ms = buildMs, documents = gen.Documents.Count, passages = ix.N, mem_after_index = memAfterIndex }, new JsonSerializerOptions { WriteIndented = true });
    Console.WriteLine(b);
    if (Arg("--out") is { } bo) File.WriteAllText(bo, b);
    return;
}
var svc = new SearchService(ix, _ => false);
var f = new SearchFilters();

// C16 WP04: document-text API cost. The projection is the /api/documents/{id}/text route's default window (pages
// 1-40), serialised as the route does. Cold = first use after start-up (disk: includes verifying the derivative against
// text_sha256 unless the index build already touched it); warm = the same documents again. Also 10 concurrent readers.
static string DocTextApi(DocumentRecord d)
{
    int a = 1, b = Math.Min(d.PageCount, a + 39);
    var pages = d.Pages.Values.Where(x => x.Page >= a && x.Page <= b).OrderBy(x => x.Page)
        .Select(x => new { page = x.Page, method = x.Method, low_confidence = x.LowConfidence, ocr = x.Method == "ocr", text = x.Text,
                           passages = d.Passages.Where(ps => ps.Page == x.Page).Select(ps => new { id = ps.PassageId, start = ps.CharStart, end = ps.CharEnd, para = ps.ParagraphLabel }) });
    return JsonSerializer.Serialize(new { doc_id = d.DocId, copy_sha256 = d.CopySha, page_count = d.PageCount, from = a, to = b,
        derivative = new { id = d.DerivativeId, text_sha256 = d.DerivativeTextSha, pipeline = d.PipelineName, version = d.PipelineVersion, quoting_permitted = d.QuotingPermitted },
        text_pages = d.Pages.Keys.Order().ToArray(), pages });
}
int docSample = int.Parse(Arg("--doc-sample") ?? "300");
var allDocs = gen.Documents.Values.Where(d => d.DerivativeId is not null).OrderBy(d => d.DocId, StringComparer.Ordinal).ToList();
var sampleDocs = Enumerable.Range(0, Math.Min(docSample, allDocs.Count)).Select(i => allDocs[(int)((long)i * allDocs.Count / Math.Min(docSample, allDocs.Count))]).ToList();
var parity = System.Security.Cryptography.IncrementalHash.CreateHash(System.Security.Cryptography.HashAlgorithmName.SHA256);
List<double> TimeDocs(bool hash)
{
    var t = new List<double>();
    foreach (var d in sampleDocs)
    {
        var s = Stopwatch.StartNew(); var json = DocTextApi(d); t.Add(s.Elapsed.TotalMilliseconds);
        if (hash) parity.AppendData(System.Text.Encoding.UTF8.GetBytes(json));
    }
    return t;
}
var docCold = TimeDocs(true);
var docWarm = TimeDocs(false);
var docTextApiParity = Convert.ToHexString(parity.GetHashAndReset()).ToLowerInvariant();
var docConc = new System.Collections.Concurrent.ConcurrentBag<double>();
Parallel.For(0, 10, new ParallelOptions { MaxDegreeOfParallelism = 10 }, k =>
{
    for (int i = 0; i < sampleDocs.Count; i++)
    { var d = sampleDocs[(i + k * 31) % sampleDocs.Count]; var s = Stopwatch.StartNew(); DocTextApi(d); docConc.Add(s.Elapsed.TotalMilliseconds); }
});

// C16 WP04: snippet cost as the search API pays it: Snippets.Build over the passage text of the first 20 hits of each
// query (the default result page), measured on the first build after the query (cold for the text store's cache
// unless the query itself read those passages) and again (warm). The snippets also feed the parity hash.
var snippetParity = System.Security.Cryptography.IncrementalHash.CreateHash(System.Security.Cryptography.HashAlgorithmName.SHA256);
var snipCold = new List<double>(); var snipWarm = new List<double>();
foreach (var q in Q)
{
    var r = svc.Search(q, f);
    var terms = r.HighlightTerms.ToHashSet(StringComparer.Ordinal);
    var hits = r.Hits.Take(20).ToList();
    foreach (var pass in new[] { snipCold, snipWarm })
        foreach (var h in hits)
        {
            var s = Stopwatch.StartNew();
            var sn = Snippets.Build(ix.Passages[h.PassageIndex].Text, terms, r.HighlightPhrases);
            pass.Add(s.Elapsed.TotalMilliseconds * 1000);   // microseconds
            if (ReferenceEquals(pass, snipCold)) snippetParity.AppendData(System.Text.Encoding.UTF8.GetBytes($"{q}|{h.PassageIndex}|{sn.Text}|{string.Join(";", sn.Highlights.Select(x => x[0] + "-" + x[1]))}\n"));
        }
}
var snippetParityHash = Convert.ToHexString(snippetParity.GetHashAndReset()).ToLowerInvariant();

// warm-up + signatures
var sigs = new Dictionary<string, object>();
foreach (var q in Q)
{
    var r = svc.Search(q, f);
    sigs[q] = new { r.State, r.Mode, r.TotalDocuments, r.TotalPassages,
        chips = r.Chips.Select(c => $"{c.Kind}|{c.Text}|{c.Source}").ToArray(),
        facets = r.Facets.ToDictionary(kv => kv.Key, kv => kv.Value.Select(v => $"{v.Value}={v.Count}").ToArray()),
        highlight = r.HighlightTerms.OrderBy(x => x, StringComparer.Ordinal).ToArray(),
        hits = r.Hits.Select((h, i) => $"{h.PassageIndex}:{h.Tier}:{Math.Round(h.Score, 6)}" + (i < 100 ? ":" + string.Join("|", h.Reasons) : "")).ToArray() };
}
if (Arg("--signatures") is { } sp) File.WriteAllText(sp, JsonSerializer.Serialize(sigs));

void Run(string q) { var r = svc.Search(q, f); if (withPage) { var pg = svc.Page(r, 1, SearchService.DefaultPageSize, null); foreach (var h in pg.Hits) _ = h.Reasons.Count; } }
var perQuery = new Dictionary<string, double>();
var perQueryAlloc = new Dictionary<string, double>();   // C16: managed bytes allocated per query (MB, mean of the repeats)
var seq = new List<double>();
foreach (var q in Q)
{
    var t = new List<double>();
    long a0 = GC.GetAllocatedBytesForCurrentThread();
    for (int i = 0; i < repeat; i++) { var s = Stopwatch.StartNew(); Run(q); t.Add(s.Elapsed.TotalMilliseconds); }
    perQueryAlloc[q] = Math.Round((GC.GetAllocatedBytesForCurrentThread() - a0) / (double)repeat / 1048576.0, 2);
    seq.AddRange(t); perQuery[q] = t.Order().ElementAt(t.Count / 2);
}
static object Stats(List<double> a) { a.Sort(); double P(double p) => Math.Round(a[Math.Max(0, (int)Math.Ceiling(p / 100 * a.Count) - 1)], 1);
    return new { n = a.Count, p50 = P(50), p95 = P(95), max = Math.Round(a[^1], 1) }; }
var conc = new Dictionary<string, object>();
foreach (var n in readers)
{
    var lat = new System.Collections.Concurrent.ConcurrentBag<double>();
    var w = Stopwatch.StartNew();
    Parallel.For(0, n, new ParallelOptions { MaxDegreeOfParallelism = n }, k =>
    {
        for (int i = 0; i < repeat * 2; i++)
            foreach (var q in Q.Skip(k % Q.Length).Concat(Q.Take(k % Q.Length)))
            { var s = Stopwatch.StartNew(); Run(q); lat.Add(s.Elapsed.TotalMilliseconds); }
    });
    conc[$"readers_{n}"] = new { stats = Stats(lat.ToList()), throughput_qps = Math.Round(lat.Count / w.Elapsed.TotalSeconds, 1) };
}
var sigHash = Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(System.Text.Encoding.UTF8.GetBytes(JsonSerializer.Serialize(sigs)))).ToLowerInvariant();
var result = new
{
    site, engine, text_store = textStore, with_page = withPage, replicate = rep > 1 ? rep : 1, documents = gen.Documents.Count, passages = ix.N, vocabulary = ix.VocabularySize, load_ms = loadMs, index_ms = buildMs,
    startup_ms = loadMs + buildMs,
    index_file_mb = ix.IndexPath is { } ip ? Mb(new FileInfo(Path.Combine(ip, "search.sqlite")).Length) : (double?)null,
    text_file_mb = gen.Text.StorePath is { } tp ? Mb(new FileInfo(Path.Combine(tp, DiskTextStore.DbFile)).Length) : (double?)null,
    derived_text_mb = Mb(allDocs.Select(d => d.DerivativeTextSha).Distinct().Sum(s => new FileInfo(Path.Combine(gen.SiteRoot, "generations", gen.GenerationId, "derived", s + ".txt")).Length)),
    derived_text_mb_per_document = Mb(allDocs.Sum(d => new FileInfo(Path.Combine(gen.SiteRoot, "generations", gen.GenerationId, "derived", d.DerivativeTextSha + ".txt")).Length)),
    mem_after_load = memAfterLoad, mem_after_index = memAfterIndex, mem_end = Mem(),
    sequential = Stats(seq), concurrent = conc,
    doc_text_api = new { documents = sampleDocs.Count, cold = Stats(docCold), warm = Stats(docWarm), readers_10 = Stats(docConc.ToList()) },
    snippet_us = new { cold = Stats(snipCold), warm = Stats(snipWarm) },
    text_store_stats = gen.Text.Stats(),
    parity = new { search_signatures_sha256 = sigHash, doc_text_api_sha256 = docTextApiParity, snippets_sha256 = snippetParityHash },
    per_query_median_ms = profile ? perQuery : null,
    per_query_alloc_mb = profile ? perQueryAlloc : null,
    sequential_alloc_mb_per_query = Math.Round(perQueryAlloc.Values.Average(), 2),
};
var json = JsonSerializer.Serialize(result, new JsonSerializerOptions { WriteIndented = true });
Console.WriteLine(json);
if (Arg("--out") is { } o) File.WriteAllText(o, json);
