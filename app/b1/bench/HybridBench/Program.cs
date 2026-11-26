// C14 S4 hybrid benchmark and similarity-floor calibration (offline; reads an importer site and the pinned model).
//   throughput <site> <model> <cpu|dml> [n=512] [tokens=256]   passage embedding throughput + query latency
//   embed      <site> <model> <cpu|dml> <cacheDir>             build (or load) the cached passage vectors; time it
//   calibrate  <site> <model> <cacheDir> <queries.json> <out.json>
// calibrate never reads the retrieval oracle or its fixture: it uses the C14 walkthrough query set on the real sample.
using System.Diagnostics;
using System.Text.Json;
using System.Text.Json.Nodes;
using Mimamsa.Core.Generation;
using Mimamsa.Core.Search;
using Mimamsa.Hybrid;

var a = args;
var sw = Stopwatch.StartNew();
var gen = GenerationStore.Load(a[1]);
var ix = SearchIndex.Build(gen);
Console.Error.WriteLine($"site loaded: {ix.Docs.Count} docs, {ix.N} passages in {sw.ElapsedMilliseconds} ms");

switch (a[0])
{
    case "throughput":
    {
        bool dml = a[3] == "dml";
        int n = a.Length > 4 ? int.Parse(a[4]) : 512, tok = a.Length > 5 ? int.Parse(a[5]) : 256;
        using var e = new E5Embedder(a[2], tryDirectMl: dml);
        var texts = ix.Passages.Take(n).Select(p => "passage: " + p.Text).ToList();
        e.Embed(texts.Take(16).ToList(), tok);   // warm-up
        sw.Restart();
        for (int s = 0; s < texts.Count; s += 16) e.Embed(texts.Skip(s).Take(16).ToList(), tok);
        double perPassage = sw.Elapsed.TotalMilliseconds / texts.Count;
        var ql = new List<double>();
        foreach (var q in new[] { "written notice before hearing", "disability pension attributable to service", "summary court martial", "सेना अधिनियम धारा", "absence without leave" })
        { sw.Restart(); e.EmbedQuery(q); ql.Add(sw.Elapsed.TotalMilliseconds); }
        Console.WriteLine(JsonSerializer.Serialize(new { device = e.Device, passages = texts.Count, max_tokens = tok, ms_per_passage = Math.Round(perPassage, 2),
            passages_per_s = Math.Round(1000 / perPassage, 1), query_embed_ms = ql.Select(x => Math.Round(x, 1)), working_set_mb = Process.GetCurrentProcess().WorkingSet64 / 1048576 }));
        break;
    }
    case "embed":
    {
        using var e = new E5Embedder(a[2], tryDirectMl: a[3] == "dml");
        var d = DenseIndex.Build(ix, gen.GenerationId, e, a[4], "multilingual-e5-small@614241f6", log: m => Console.Error.WriteLine(m));
        sw.Restart(); for (int i = 0; i < 20; i++) d.TopK("disability pension attributable to military service", 100);
        Console.WriteLine(JsonSerializer.Serialize(new { device = e.Device, passages = d.Count, from_cache = d.FromCache, build_s = Math.Round(d.BuildTime.TotalSeconds, 1),
            topk_ms_incl_query_embed = Math.Round(sw.Elapsed.TotalMilliseconds / 20, 1), working_set_mb = Process.GetCurrentProcess().WorkingSet64 / 1048576 }));
        break;
    }
    case "calibrate":
    {
        using var e = new E5Embedder(a[2]);
        var d = DenseIndex.Build(ix, gen.GenerationId, e, a[3], "multilingual-e5-small@614241f6");
        var svc = new SearchService(ix, _ => false);
        var rows = new JsonArray();
        var p99s = new List<double>(); var p999s = new List<double>(); var lexTop = new List<double>();
        foreach (var q in JsonNode.Parse(File.ReadAllText(a[4]))!.AsArray())
        {
            var text = q!["query"]!.GetValue<string>();
            var all = d.TopK(text, ix.N).Select(x => x.Score).ToArray();   // every passage, best first
            var sorted = all.OrderBy(x => x).ToArray();
            double P(double f) => sorted[(int)Math.Clamp(Math.Round(f * (sorted.Length - 1)), 0, sorted.Length - 1)];
            var top = svc.Search(text, new SearchFilters()).Hits.FirstOrDefault(h => h.Tier == "lexical");
            double? lexSim = null;
            if (top is not null) lexSim = d.TopK(text, ix.N).First(x => x.Passage == top.PassageIndex).Score;
            p99s.Add(P(0.99)); p999s.Add(P(0.999)); if (lexSim is { } l) lexTop.Add(l);
            rows.Add(new JsonObject { ["id"] = q["id"]!.GetValue<string>(), ["median"] = Math.Round(P(0.5), 4), ["p99"] = Math.Round(P(0.99), 4),
                ["p999"] = Math.Round(P(0.999), 4), ["max"] = Math.Round(sorted[^1], 4), ["lexical_top1_similarity"] = lexSim is null ? null : Math.Round(lexSim.Value, 4) });
        }
        var summary = new JsonObject { ["queries"] = rows.Count, ["passages"] = ix.N, ["mean_p99"] = Math.Round(p99s.Average(), 4),
            ["max_p99"] = Math.Round(p99s.Max(), 4),
            // Similarity floor by the rule fixed before any calibration numbers were seen: median over the walkthrough
            // queries of each query's 99.9th-percentile similarity across all passages.
            ["floor_median_p999"] = Math.Round(p999s.OrderBy(x => x).ElementAt(p999s.Count / 2), 4), ["median_lexical_top1_similarity"] = Math.Round(lexTop.OrderBy(x => x).ElementAt(lexTop.Count / 2), 4) };
        File.WriteAllText(a[5], new JsonObject { ["summary"] = summary, ["per_query"] = rows }.ToJsonString(new JsonSerializerOptions { WriteIndented = true }));
        Console.WriteLine(summary.ToJsonString());
        break;
    }
}
