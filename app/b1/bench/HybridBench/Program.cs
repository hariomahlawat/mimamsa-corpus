// C14 S4 hybrid benchmark and similarity-floor calibration (offline; reads an importer site and the pinned model).
//   throughput <site> <model> <cpu|dml> [n=512] [tokens=256]   passage embedding throughput + query latency
//   embed      <site> <model> <cpu|dml> <cacheDir>             build (or load) the cached passage vectors; time it
//   calibrate  <site> <model> <cacheDir> <queries.json> <out.json>
//   probe      <site> <model> <cacheDir> <query> [n=15]           C15 diagnosis: dense ranking of every passage for one query
//   rrprobe    <site> <reranker> <onnxFile> <query> [n=15]        C15 diagnosis: cross-encoder logit of every passage for one query
//   rrbench    <site> <reranker> <onnxFile> [pairs=60]            C15: reranker latency per pair (CPU)
//   calsub     <site> <model> <queries.json> <n> <seed> <out.json>   C15: the C14 floor rule over a seeded random passage sample
//   dump       <site> <n> <seed> <out.jsonl>                      C16 S3-E: seeded passage sample (distractors for the dev set)
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
        Console.WriteLine(JsonSerializer.Serialize(new { device = e.Device, passages = d.Count, reused = d.Reused, embedded = d.Embedded, build_s = Math.Round(d.BuildTime.TotalSeconds, 1),
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
    case "probe":
    {
        // C15 S2 diagnosis only: prints the dense ranking (passage id, document, cosine) for one query. Used to explain
        // RET-07/RET-10 mechanisms; no parameter is chosen from its output.
        using var e = new E5Embedder(a[2]);
        var d = DenseIndex.Build(ix, gen.GenerationId, e, a[3], "probe");
        int n = a.Length > 5 ? int.Parse(a[5]) : 15;
        var all = d.TopK(a[4], ix.N);
        int r = 0;
        foreach (var (p, sc) in all.Take(n)) Console.WriteLine($"{++r,3}  {sc:0.0000}  {ix.Passages[p].DocId,-22} {ix.Passages[p].PassageId,-10} {ix.Passages[p].Text[..Math.Min(70, ix.Passages[p].Text.Length)]}");
        break;
    }
    case "rrprobe":
    {
        // C15 S2 diagnosis only (small sites): cross-encoder logit of every passage for one query.
        using var ce = new CrossEncoder(a[2], a[3]);
        int n = a.Length > 5 ? int.Parse(a[5]) : 15;
        var sc = ce.Score(a[4], ix.Passages.Select(p => p.Text).ToList());
        int r = 0;
        foreach (var i in Enumerable.Range(0, ix.N).OrderByDescending(i => sc[i]).ThenBy(i => i).Take(n))
            Console.WriteLine($"{++r,3}  {sc[i],7:0.000}  {ix.Passages[i].DocId,-22} {ix.Passages[i].PassageId,-10} {ix.Passages[i].Text[..Math.Min(70, ix.Passages[i].Text.Length)]}");
        break;
    }
    case "rrbench":
    {
        using var ce = new CrossEncoder(a[2], a[3]);
        int pairs = a.Length > 4 ? int.Parse(a[4]) : 60;
        var texts = ix.Passages.Where(p => p.Text.Length > 600).Take(pairs).Select(p => p.Text).ToList();
        ce.Score("warm up", texts.Take(4).ToList());
        var lat = new List<double>();
        foreach (var q in new[] { "absence without leave punishment", "how to hold a summary court martial", "disability pension attributable to military service", "सेना अधिनियम धारा 69", "court martial set aside violation of natural justice" })
        { sw.Restart(); ce.Score(q, texts); lat.Add(sw.Elapsed.TotalMilliseconds); }
        Console.WriteLine(JsonSerializer.Serialize(new { model = ce.Label, pairs = texts.Count, ms_per_query = lat.Select(x => Math.Round(x)), ms_per_pair = Math.Round(lat.Average() / texts.Count, 2),
            working_set_mb = Process.GetCurrentProcess().WorkingSet64 / 1048576 }));
        break;
    }
    case "dump":
    {
        // C16 S3-E development data: a seeded uniform sample of passages (text + document title/type) as JSONL, used as
        // realistic distractors around the synthetic development set. Never run on the SYN (oracle) site.
        int n = int.Parse(a[2]), seed = int.Parse(a[3]);
        var rng = new Random(seed);
        var idx = Enumerable.Range(0, ix.N).OrderBy(_ => rng.Next()).Take(n).OrderBy(i => i).ToList();
        using var w = new StreamWriter(a[4], false, new System.Text.UTF8Encoding(false));
        foreach (var i in idx)
        {
            var p = ix.Passages[i]; var d = ix.Docs[ix.DocOf(i)];
            w.WriteLine(new JsonObject { ["i"] = i, ["doc_id"] = p.DocId, ["passage_id"] = p.PassageId, ["doc_type"] = d.DocType, ["title"] = d.Title,
                ["language"] = d.Language, ["text"] = p.Text }.ToJsonString());
        }
        Console.WriteLine($"{idx.Count} passages written (seed {seed})");
        break;
    }
    case "vecs":
    {
        // C16 S3-E: C# embeddings of a few texts (JSON list in a[6]) to check equivalence with the Python dev harness.
        //   vecs <site> <modelDir> <onnxFile> <pooling> <spm|-> <texts.json> <out.json>
        using var e = new E5Embedder(a[2], threads: Math.Max(1, Environment.ProcessorCount / 2), onnxFile: a[3], sentencePieceModel: a[5] == "-" ? null : a[5]) { Pooling = a[4] };
        var texts = JsonNode.Parse(File.ReadAllText(a[6]))!.AsArray().Select(x => x!.GetValue<string>()).ToList();
        var v = texts.Select(t => e.Embed(new[] { t }, 256)[0]).ToArray();   // one text per call (int8 models: see dev_eval.py)
        File.WriteAllText(a[7], JsonSerializer.Serialize(v));
        Console.WriteLine($"{v.Length} vectors of {e.Dim}");
        break;
    }
    case "calsub":
    {
        // C15 declared variant of the C14 floor rule (DECLARATIONS.md item 2): median over the walkthrough queries of
        // each query's 99.9th-percentile cosine, the percentile taken over a seeded uniform random passage sample.
        using var e = new E5Embedder(a[2]);
        int n = int.Parse(a[4]), seed = int.Parse(a[5]);
        var rng = new Random(seed);
        var idx = Enumerable.Range(0, ix.N).OrderBy(_ => rng.Next()).Take(n).OrderBy(i => i).ToList();
        var vecs = new List<float[]>();
        for (int s0 = 0; s0 < idx.Count; s0 += 16)
        {
            vecs.AddRange(e.Embed(idx.Skip(s0).Take(16).Select(i => e.PassagePrefix + ix.Passages[i].Text).ToList(), 256));
            if (s0 % 800 == 0) Console.Error.WriteLine($"embedded {s0}/{idx.Count}");
        }
        var rows = new JsonArray(); var p999s = new List<double>();
        foreach (var q in JsonNode.Parse(File.ReadAllText(a[3]))!.AsArray())
        {
            var qv = e.EmbedQuery(q!["query"]!.GetValue<string>());
            var sims = vecs.Select(v => (double)v.Zip(qv, (x, y) => x * y).Sum()).OrderBy(x => x).ToArray();
            double P(double f) => sims[(int)Math.Clamp(Math.Round(f * (sims.Length - 1)), 0, sims.Length - 1)];
            p999s.Add(P(0.999));
            rows.Add(new JsonObject { ["id"] = q["id"]!.GetValue<string>(), ["p99"] = Math.Round(P(0.99), 4), ["p999"] = Math.Round(P(0.999), 4), ["max"] = Math.Round(sims[^1], 4) });
        }
        var summary = new JsonObject { ["model_sha256"] = e.ModelSha256, ["sample"] = idx.Count, ["seed"] = seed, ["passages_total"] = ix.N, ["queries"] = rows.Count,
            ["floor_median_p999"] = Math.Round(p999s.OrderBy(x => x).ElementAt(p999s.Count / 2), 4) };
        File.WriteAllText(a[6], new JsonObject { ["summary"] = summary, ["per_query"] = rows }.ToJsonString(new JsonSerializerOptions { WriteIndented = true }));
        Console.WriteLine(summary.ToJsonString());
        break;
    }
}