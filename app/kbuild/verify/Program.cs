// C16 Stage 3 S3-B central helper. Usage:
//   KBuildVerify vectors --site <site> [--generation <id>] --model-dir <dir> --model-sha <sha> --out <dir>
//                [--max-tokens 256] [--threads N] [--batch 16] [--cache <file.mvs>]
//       Central vector pack for the generation's indexed passages (MIMVEC01 sorted by key bytes, params sidecar,
//       summary.json with result_digest and the 2.1 source digest). Vectors already in --cache (content-keyed, same model
//       and max tokens) are reused; the rest are embedded in batches with at most --threads intra-op threads at
//       below-normal priority. This is the ONLY place the corpus is embedded; the site never does.
//   KBuildVerify verify-vectors --site <site> [--generation <id>] --pack <file> --params <file> --model-dir <dir>
//                --model-sha <sha> --release-id <id> --result-digest <hex> --source-digest <hex> --sample <n>
//                --tolerance <t> --out <evidence.json> [--threads N]
//   KBuildVerify verify-accel --site <site> [--generation <id>] --bundle <dir> --out <evidence.json>
//                [--sample-graph n] [--sample-postings n] [--sample-queries n]
//       The B04 GRAPH and LEXICAL_INDEX checks of a built bundle's shipped accelerators against the reference site's
//       generation, centrally, with the same verifiers the site runs. Sample sizes are STUDY/CENTRAL overrides recorded
//       as such; contracts stay UNCALIBRATED.
// No text is printed. Exit 0 = command ran (the evidence says VERIFIED or FAILED); 2 = verification FAILED; 1 = error.
using System.Diagnostics;
using System.Globalization;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using Mimamsa.Core.ComponentVerification;
using Mimamsa.Core.Generation;
using Mimamsa.Hybrid;

string? Opt(string n) { var i = Array.IndexOf(args, n); return i >= 0 && i + 1 < args.Length ? args[i + 1] : null; }
string Arg(string n) => Opt(n) ?? throw new ArgumentException($"{n} is required");
int IntOpt(string n, int d) => Opt(n) is { } s ? int.Parse(s, CultureInfo.InvariantCulture) : d;
void Log(string m) => Console.Error.WriteLine(m);
try { Process.GetCurrentProcess().PriorityClass = ProcessPriorityClass.BelowNormal; } catch (Exception) { /* not permitted: the kbuild job object still caps us */ }
var json = new JsonSerializerOptions { WriteIndented = true };
if (args.Length == 0) { Log("usage: KBuildVerify vectors|verify-vectors|verify-accel ..."); return 1; }
var gen = GenerationStore.Load(Arg("--site"), null, TextStoreOptions.Memory, Log, Opt("--generation"));
int threads = IntOpt("--threads", Math.Max(1, Environment.ProcessorCount / 2));

switch (args[0])
{
    case "vectors":
    {
        var sw = Stopwatch.StartNew();
        int maxTokens = IntOpt("--max-tokens", 256), batch = IntOpt("--batch", 16);
        using var emb = new E5Embedder(Arg("--model-dir"), threads, expectedModelSha256: Arg("--model-sha"));
        var p = new VectorPackParams(emb.ModelSha256, emb.Dim, maxTokens, emb.PassagePrefix, emb.QueryPrefix);
        var inputs = VectorPackVerifier.Inputs(gen, p);
        var cachePath = Opt("--cache");
        var cache = cachePath is null ? new VectorStore(emb.Dim) : VectorStore.Load(cachePath, emb.Dim);
        var want = new Dictionary<UInt128, string>();
        foreach (var (_, input) in inputs) want.TryAdd(VectorPackVerifier.Key(emb.ModelSha256, maxTokens, input), input);
        var missing = want.Where(kv => !cache.TryGet(kv.Key, out _)).ToList();
        Log($"vectors: {want.Count} distinct passages; {want.Count - missing.Count} reused from the cache; {missing.Count} to embed ({threads} threads, batch {batch})");
        for (int s = 0; s < missing.Count; s += batch)
        {
            var chunk = missing.Skip(s).Take(batch).ToList();
            var vs = emb.Embed(chunk.Select(c => c.Value).ToList(), maxTokens);
            for (int i = 0; i < chunk.Count; i++) cache.Put(chunk[i].Key, vs[i]);
            if (cachePath is not null && (s / batch) % 200 == 199) cache.Save(cachePath, cache.Keys());
        }
        if (cachePath is not null && missing.Count > 0) cache.Save(cachePath, cache.Keys());
        var outDir = Arg("--out");
        Directory.CreateDirectory(outDir);
        var packPath = Path.Combine(outDir, emb.ModelSha256 + ".mimvec");
        VectorPackFile.Write(packPath, emb.Dim, want.Keys.Select(k => { cache.TryGet(k, out var v); return (k, v); }));
        var prm = Encoding.UTF8.GetBytes(p.ToJson().ToJsonString(json) + "\n");
        File.WriteAllBytes(Path.Combine(outDir, emb.ModelSha256 + ".params.json"), prm);
        var file = VectorPackFile.Open(packPath, out var why) ?? throw new InvalidOperationException("written pack does not verify: " + why);
        var summary = new JsonObject
        {
            ["generation_id"] = gen.GenerationId, ["model_sha256"] = emb.ModelSha256, ["dim"] = emb.Dim, ["max_tokens"] = maxTokens,
            ["passages"] = inputs.Count, ["entries"] = file.Count, ["embedded"] = missing.Count, ["reused"] = want.Count - missing.Count,
            ["result_digest"] = file.ResultDigest(), ["source_digest"] = VectorPackVerifier.SourceDigest(emb.ModelSha256, maxTokens, want.Keys),
            ["threads"] = threads, ["batch"] = batch, ["seconds"] = Math.Round(sw.Elapsed.TotalSeconds, 1),
        };
        File.WriteAllText(Path.Combine(outDir, "summary.json"), summary.ToJsonString(json));
        return 0;
    }
    case "verify-vectors":
    {
        using var emb = new E5Embedder(Arg("--model-dir"), threads, expectedModelSha256: Arg("--model-sha"));
        var ev = VectorPackVerifier.Verify(gen, Arg("--pack"), File.ReadAllBytes(Arg("--params")), Arg("--model-sha"), Arg("--result-digest"), Arg("--source-digest"),
            Arg("--release-id"), emb, B04Sampling.Override(VectorPackVerifier.Spot, IntOpt("--sample", 32), double.Parse(Arg("--tolerance"), CultureInfo.InvariantCulture)));
        var o = ev.ToJson(VectorPackVerifier.Required);
        File.WriteAllText(Arg("--out"), o.ToJsonString(json));
        return ev.Verified(VectorPackVerifier.Required) ? 0 : 2;
    }
    case "verify-accel":
    {
        var bundle = Arg("--bundle");
        var km = JsonNode.Parse(File.ReadAllBytes(Path.Combine(bundle, "KNOWLEDGE_RELEASE.json")))!.AsObject();
        var rid = (string)km["release_id"]!;
        var comps = km["components"]!.AsArray().Select(c => c!.AsObject()).ToList();
        var outp = new JsonObject { ["release_id"] = rid, ["generation_id"] = gen.GenerationId };
        bool ok = true;
        if (comps.FirstOrDefault(c => (string?)c["kind"] == "GRAPH") is { } gc)
        {
            var t = gc["tables"]!.AsArray().Select(x => x!.AsObject()).ToDictionary(x => (string)x["table"]!, x => (string)x["file"]!);
            var ev = GraphVerifier.Verify(gen, File.ReadAllBytes(Path.Combine(bundle, t["graph_nodes"])), File.ReadAllBytes(Path.Combine(bundle, t["graph_edges"])),
                (string)gc["result_digest"]!, (string?)km["compatibility"]?["graph_builder_version"] ?? "", rid,
                B04Sampling.Override(GraphVerifier.Check, IntOpt("--sample-graph", gen.Documents.Count)));
            outp["GRAPH"] = ev.ToJson(GraphVerifier.Required);
            ok &= ev.Verified(GraphVerifier.Required);
        }
        if (comps.FirstOrDefault(c => (string?)c["kind"] == "LEXICAL_INDEX") is { } lc)
        {
            var ev = LexicalIndexVerifier.Verify(gen, Path.Combine(bundle, "accelerators", "search-index"), rid, (string?)lc["source_digest"],
                B04Sampling.Override(LexicalIndexVerifier.Postings, IntOpt("--sample-postings", gen.Documents.Count)),
                B04Sampling.Override(LexicalIndexVerifier.Queries, IntOpt("--sample-queries", 64)));
            outp["LEXICAL_INDEX"] = ev.ToJson(LexicalIndexVerifier.Required);
            ok &= ev.Verified(LexicalIndexVerifier.Required);
        }
        outp["status"] = ok ? "VERIFIED" : "FAILED";
        File.WriteAllText(Arg("--out"), outp.ToJsonString(json));
        Microsoft.Data.Sqlite.SqliteConnection.ClearAllPools();
        return ok ? 0 : 2;
    }
    default:
        Log("unknown command " + args[0]);
        return 1;
}
