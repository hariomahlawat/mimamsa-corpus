// C15 WP1 in-process search benchmark. Usage:
//   IndexBench --site <site> [--engine memory|disk] [--index-dir <dir>] [--repeat 5] [--readers 10,25]
//              [--signatures <out.json>] [--out <result.json>] [--profile]
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

var sw = Stopwatch.StartNew();
var gen = GenerationStore.Load(site);
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
var svc = new SearchService(ix, _ => false);
var f = new SearchFilters();

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

var perQuery = new Dictionary<string, double>();
var seq = new List<double>();
foreach (var q in Q)
{
    var t = new List<double>();
    for (int i = 0; i < repeat; i++) { var s = Stopwatch.StartNew(); svc.Search(q, f); t.Add(s.Elapsed.TotalMilliseconds); }
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
            { var s = Stopwatch.StartNew(); svc.Search(q, f); lat.Add(s.Elapsed.TotalMilliseconds); }
    });
    conc[$"readers_{n}"] = new { stats = Stats(lat.ToList()), throughput_qps = Math.Round(lat.Count / w.Elapsed.TotalSeconds, 1) };
}
var result = new
{
    site, engine, replicate = rep > 1 ? rep : 1, documents = gen.Documents.Count, passages = ix.N, vocabulary = ix.VocabularySize, load_ms = loadMs, index_ms = buildMs,
    index_file_mb = ix.IndexPath is { } ip ? Mb(new FileInfo(Path.Combine(ip, "search.sqlite")).Length) : (double?)null,
    mem_after_load = memAfterLoad, mem_after_index = memAfterIndex, mem_end = Mem(),
    sequential = Stats(seq), concurrent = conc,
    per_query_median_ms = profile ? perQuery : null,
};
var json = JsonSerializer.Serialize(result, new JsonSerializerOptions { WriteIndented = true });
Console.WriteLine(json);
if (Arg("--out") is { } o) File.WriteAllText(o, json);
