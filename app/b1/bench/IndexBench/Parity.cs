// C16 WP05: full output signatures for proving that an evaluator change is exact. For every case (query x filters x
// service x headings x hybrid/rerank hook x withdrawal set) it records state, mode, error, chips, notes, highlight
// terms and phrases (in order), facets, totals, EVERY hit (passage, tier, score as a round-trip string, all reasons)
// and Page() output (groups, variants, passages, counts) for several pages, page sizes and sorts. The hit list is
// written as a SHA-256 plus its first 30 entries, so a file stays small while still covering every hit.
// Only query strings, passage indexes, document indexes and scores are written; no document text.
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Mimamsa.Core.Search;

static class Parity
{
    public static readonly string[] Extra =
    {
        // phrases, NEAR, NOT, OR, prefix, exact
        "\"court martial\"", "\"summary of evidence\" NEAR/5 recorded", "\"court martial\" NEAR/10 delay", "pension NEAR/3 disability",
        "(desertion OR absence) AND NOT pension", "NOT pension", "desertion OR \"absence without leave\"", "pension* AND army",
        "milit*", "exact:court martial", "exact:\"summary of evidence\"", "\"Rule 22\"", "\"section 69\"",
        "\"court martial\" NEAR/2 (general OR summary)", "(army OR navy) NEAR/4 act",
        // fields and ranges
        "title:army", "party:union", "judge:singh", "court:delhi", "bench:chandigarh", "type:judgment pension", "type:statute",
        "case:\"OA 123/2015\"", "citation:\"2013 INSC 408\"", "date:2015-01-01..2016-12-31 pension", "year:2019 court martial",
        "year:2010..2020 AND desertion", "section:69", "section:8(3)(a)", "rule:22", "act:\"Army Act\"", "act:\"Army Act\" AND punishment",
        // identifiers and citations
        "Army Act s.69", "section 39 Army Act", "s. 38 AA", "Rule 180", "OA 1234/2015", "2023 INSC 1", "(2013) 7 SCC 316",
        "AIR 1987 SC 2386", "Writ Petition (Civil) No. 123 of 2019", "Regulation 520",
        // natural language, abbreviations, stopwords, misspellings
        "AWL", "CO", "SCM GCM DCM", "the", "of the", "what is the punishment for desertion", "pension for disability attributable to service",
        "union of india v", "dharamvir", "armed forces tribunal order challenged in high court",
        // empty and errors
        "zzqxv", "quantum entanglement", "\"zzqxv army\"", "army AND zzqxv", "(court martial", "title:", "NEAR/3 x", "\"\"",
    };

    sealed class FakeSemantic : ISemanticScorer
    {
        readonly int _n;
        public FakeSemantic(int n) { _n = n; }
        public string Description => "parity-fake-semantic";
        static uint H(string s, int p) { uint h = 2166136261; foreach (var c in s) h = (h ^ c) * 16777619; h = (h ^ (uint)p) * 16777619; h ^= h >> 13; h *= 0x5bd1e995; return h ^ (h >> 15); }
        public IReadOnlyList<(int Passage, double Score)> TopK(string query, int k)
        {
            if (_n == 0) return Array.Empty<(int, double)>();
            var cand = new List<(int, double)>();
            int start = (int)(H(query, 0) % (uint)_n);
            for (int i = 0; i < Math.Min(_n, 4000); i++) { int p = (int)((start + (long)i * 7919) % _n); cand.Add((p, (H(query, p) % 10000) / 10000.0)); }
            return cand.OrderByDescending(x => x.Item2).ThenBy(x => x.Item1).Take(k).ToList();
        }
    }

    sealed class FakeReranker : IReranker
    {
        public string Description => "parity-fake-reranker";
        public float[] Score(string query, IReadOnlyList<string> passages) =>
            passages.Select(t => (float)(((t.Length * 31 + query.Length * 17) % 997) / 100.0 - 4.0)).ToArray();
    }

    static string R(double d) => d.ToString("R", System.Globalization.CultureInfo.InvariantCulture);

    public static void Run(SearchIndex ix, string outPath, string? walkthrough, bool quick)
    {
        var queries = new List<(string id, string q, Dictionary<string, string>? p)>();
        string[] bench = { "s.69 Army Act", "2013 INSC 408", "disability pension", "court martial", "summary of evidence", "AFT jurisdiction",
            "invalided out of service", "exact:\"Entitlement Rules\"", "desertion AND NOT pension", "Rule 22 Army Rules",
            "release medical board", "\"court martial\" NEAR/10 delay", "Civil Appeal No. 4949 of 2013",
            "writ petition armed forces tribunal", "field punishment", "attributable to military service",
            "sentence of dismissal", "section 302 Indian Penal Code", "Navy Act", "natural justice court of inquiry",
            "Dharamvir Singh", "section 302 IPC", "court marshal", "\"summary of evidence\"", "pension*", "title:army" };
        foreach (var q in bench) queries.Add(("B:" + q, q, null));
        if (walkthrough is not null)
            foreach (var e in JsonDocument.Parse(File.ReadAllText(walkthrough)).RootElement.EnumerateArray())
                queries.Add((e.GetProperty("id").GetString()!, e.GetProperty("query").GetString()!,
                    e.TryGetProperty("params", out var pp) ? pp.EnumerateObject().ToDictionary(x => x.Name, x => x.Value.GetString()!) : null));
        foreach (var q in Extra) queries.Add(("X:" + q, q, null));

        // withdrawal sets: none, and every document whose index is 3 mod 7 (a deterministic ~14% hidden)
        var hiddenIds = Enumerable.Range(0, ix.Docs.Count).Where(d => d % 7 == 3).Select(d => ix.Docs[d].DocId).ToHashSet(StringComparer.Ordinal);
        var headings = ProvisionHeadings.Build(ix);
        var filterSets = new (string name, SearchFilters f)[]
        {
            ("none", new SearchFilters()),
            ("judgment-2015-2022", new SearchFilters(Types: new HashSet<string> { "judgment" }, YearFrom: 2015, YearTo: 2022)),
            ("statutes", new SearchFilters(Types: new HashSet<string> { "rules", "act", "regulations" })),
        };
        var cases = new List<(string key, Func<SearchResult> run, SearchService svc)>();
        foreach (var (id, q, p) in queries)
        {
            var fl = p is null ? new SearchFilters() : new SearchFilters(
                p.TryGetValue("type", out var t) ? new HashSet<string> { t } : null, p.TryGetValue("court", out var c) ? new HashSet<string> { c } : null,
                p.TryGetValue("year_from", out var yf) ? int.Parse(yf) : null, p.TryGetValue("year_to", out var yt) ? int.Parse(yt) : null, null);
            foreach (var hide in new[] { false, true })
            {
                Func<string, bool> hidden = hide ? hiddenIds.Contains : _ => false;
                var plain = new SearchService(ix, hidden);
                var withHead = new SearchService(ix, hidden) { Headings = headings };
                var hybrid = new SearchService(ix, hidden) { Headings = headings, Semantic = new FakeSemantic(ix.N) };
                var rerank = new SearchService(ix, hidden) { Headings = headings, Semantic = new FakeSemantic(ix.N), Reranker = new FakeReranker() };
                string k0 = $"{id}|hide={hide}";
                cases.Add(($"{k0}|lex|{(p is null ? "none" : "params")}", () => plain.Search(q, fl), plain));
                cases.Add(($"{k0}|head", () => withHead.Search(q, fl), withHead));
                if (quick) continue;
                cases.Add(($"{k0}|hybrid", () => hybrid.Search(q, fl), hybrid));
                cases.Add(($"{k0}|rerank", () => rerank.Search(q, fl), rerank));
                cases.Add(($"{k0}|lex|svc=army", () => plain.Search(q, fl, false, "army"), plain));
                cases.Add(($"{k0}|hybrid|svc=navy", () => hybrid.Search(q, fl, false, "navy"), hybrid));
                cases.Add(($"{k0}|lex|plainconfirm", () => plain.Search(q, fl, true), plain));
                if (p is null && !hide)
                    foreach (var (fn, f) in filterSets.Skip(1)) cases.Add(($"{k0}|lex|{fn}", () => plain.Search(q, f), plain));
            }
        }

        var outp = new Dictionary<string, object>();
        foreach (var (key, run, svc) in cases)
        {
            SearchResult r;
            try { r = run(); }
            catch (Exception e) { outp[key] = new { exception = e.GetType().Name + ": " + e.Message }; continue; }
            var sha = SHA256.Create();
            var head = new List<string>();
            int i = 0;
            foreach (var h in r.Hits)
            {
                var line = $"{h.PassageIndex}:{h.Tier}:{R(h.Score)}:{string.Join("|", h.Reasons)}\n";
                var b = Encoding.UTF8.GetBytes(line);
                sha.TransformBlock(b, 0, b.Length, null, 0);
                if (i++ < 30) head.Add(line.TrimEnd('\n'));
            }
            sha.TransformFinalBlock(Array.Empty<byte>(), 0, 0);
            var pages = new Dictionary<string, object>();
            foreach (var sort in new[] { "", "new", "old" })
                foreach (var size in new[] { 25, 100, 7 })
                {
                    var first = svc.Page(r, 1, size, sort);
                    foreach (var pg in new[] { 1, 2, first.PageCount, first.PageCount + 3, 0 }.Distinct())
                    {
                        var x = svc.Page(r, pg, size, sort);
                        var po = new
                        {
                            x.Page, x.PageSize, x.PageCount, x.TotalGroups,
                            groups = x.Groups.Select(g => $"{g.Doc}[{string.Join(",", g.Variants.Select(v => $"{v.Doc}:{v.Label}:{v.Passage}"))}]").ToArray(),
                            hits = x.Hits.Select(h => $"{h.PassageIndex}:{h.Tier}:{R(h.Score)}:{string.Join("|", h.Reasons)}").ToArray(),
                            counts = x.PassageCounts.OrderBy(kv => kv.Key).Select(kv => $"{kv.Key}={kv.Value}").ToArray(),
                        };
                        // the whole page (every group, variant, passage, reason and count) as a hash, plus its shape
                        pages[$"{sort}/{size}/{pg}"] = $"{x.Page}/{x.PageCount}/{x.TotalGroups}/{x.Hits.Count}/" +
                            Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(JsonSerializer.Serialize(po))))[..16];
                    }
                }
            outp[key] = new
            {
                r.State, r.Mode, r.Error, r.ErrorPosition, r.TotalPassages, r.TotalDocuments, r.Service,
                chips = r.Chips.Select(c => $"{c.Kind}|{c.Text}|{c.Source}").ToArray(),
                notes = r.Notes.ToArray(),
                highlight = r.HighlightTerms.ToArray(),
                phrases = r.HighlightPhrases.Select(p => string.Join(" ", p)).ToArray(),
                facets = r.Facets.Select(kv => kv.Key + ":" + string.Join(",", kv.Value.Select(v => $"{v.Value}={v.Count}"))).ToArray(),
                hit_count = r.Hits.Count, hits_sha256 = Convert.ToHexString(sha.Hash!), hits_head = head, pages,
            };
        }
        File.WriteAllText(outPath, JsonSerializer.Serialize(outp));
        Console.Error.WriteLine($"parity: {outp.Count} cases written to {outPath}");
    }
}
