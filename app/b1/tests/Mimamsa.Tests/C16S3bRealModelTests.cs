// C16 Stage 3 S3-B (B10, development path) with the REAL pinned model: multilingual-e5-small@614241f6
// (model.onnx sha256 ca456c06...). Runs ONLY when the evidence driver sets:
//   MIMAMSA_HYBRID_MODEL         the pinned model directory (contains onnx/model.onnx)
//   MIMAMSA_S3B_SAMPLE_SITE      the real 290-document sample site (read only)
//   MIMAMSA_S3B_MODEL_RELEASE    a DEVELOPMENT intelligence release built by `python -m mimamsa_kbuild build-model-release`
//                                (its parent holds dev-model-trust/trust_list.json)
//   MIMAMSA_S3B_CENTRAL          a directory with the central index (index/<gen>) and graph rows (graph/) of the sample
//   MIMAMSA_S3B_EVIDENCE_OUT     where to write the evidence JSON
//   MIMAMSA_S3B_OTHER_MODEL      optional: another installed model directory (mismatched-model check)
// Otherwise it does nothing (CI has no model). The site never embeds the corpus: the vector pack was built centrally;
// here only the self-test probe and the spot sample are embedded, one input per call.
using System.Diagnostics;
using System.Text.Json;
using System.Text.Json.Nodes;
using Mimamsa.Core.Activation;
using Mimamsa.Core.ComponentVerification;
using Mimamsa.Core.Generation;
using Mimamsa.Core.Graph;
using Mimamsa.Hybrid;
using Mimamsa.Tests.Activation;

namespace Mimamsa.Tests;

public class C16S3bRealModelTests
{
    static string? Env(string n) => Environment.GetEnvironmentVariable(n) is { Length: > 0 } v ? v : null;

    sealed class CountingE5(E5Embedder inner) : IPassageEmbedder, IDisposable
    {
        public int Calls;
        public string ModelSha256 => inner.ModelSha256;
        public int Dim => inner.Dim;
        public float[] EmbedOne(string input, int maxTokens) { Interlocked.Increment(ref Calls); return inner.EmbedOne(input, maxTokens); }
        public void Dispose() => inner.Dispose();
    }

    [Fact]
    public void RealModelReleaseGivesFullServiceInDevelopmentAndIsRefusedInProduction()
    {
        if (Env("MIMAMSA_HYBRID_MODEL") is null || Env("MIMAMSA_S3B_SAMPLE_SITE") is not { } sample || Env("MIMAMSA_S3B_MODEL_RELEASE") is not { } release
            || Env("MIMAMSA_S3B_CENTRAL") is not { } central || Env("MIMAMSA_S3B_EVIDENCE_OUT") is not { } evidenceOut) return;
        int threads = Math.Max(1, Environment.ProcessorCount / 2);
        var ev = new JsonObject { ["model_release"] = Path.GetFullPath(release), ["threads"] = threads };
        var g = GenerationStore.Load(sample, null, TextStoreOptions.Memory);
        var gid = g.GenerationId;
        var trust = TrustList.Parse(File.ReadAllBytes(Path.Combine(release, "..", "dev-model-trust", "trust_list.json")));
        var today = DateOnly.FromDateTime(DateTime.UtcNow);
        var contracts = S3b.Contracts();
        var loaders = new List<CountingE5>();
        IPassageEmbedder Load(string dir) { var e = new CountingE5(new E5Embedder(dir, threads)); loaders.Add(e); return e; }

        using var site = new FixtureSite("b10real", ["L1", gid], "L1", null, new Dictionary<string, (bool, string[])>(), lexicalOnly: ["L1"]);
        // production: refused before anything is read (FG-MODEL-TRUST-PURPOSE open)
        var prod = ModelStaging.VerifyAndStage(site.Layout, release, trust, production: true, today, Load, contracts);
        Assert.False(prod.Ok);
        ev["production"] = new JsonObject { ["ok"] = prod.Ok, ["issue"] = prod.Issues[0] };
        // development: signature (purpose model), inventory, manifest, install, ONNX self-test, pack verified with spot re-embed
        var sw = Stopwatch.StartNew();
        var rep = ModelStaging.VerifyAndStage(site.Layout, release, trust, production: false, today, Load, contracts, null, gen => gen == gid ? g : throw new GenerationLoadException("SIMULATED_GENERATION"));
        ev["development"] = new JsonObject { ["ok"] = rep.Ok, ["issues"] = new JsonArray(rep.Issues.Select(i => (JsonNode)i).ToArray()), ["seconds"] = Math.Round(sw.Elapsed.TotalSeconds, 1),
            ["model_id"] = rep.ModelId, ["model_sha256"] = rep.ModelSha256, ["vectors_for"] = new JsonArray(rep.VectorsFor.Select(v => (JsonNode)v).ToArray()),
            ["evidence"] = rep.Evidence.DeepClone(), ["embed_calls"] = loaders.Sum(l => l.Calls) };
        Assert.True(rep.Ok, string.Join("; ", rep.Issues));
        Assert.Equal([gid], rep.VectorsFor);
        var spotSize = B04Sampling.DevelopmentDefaults["VECTOR_SPOT_REEMBED"].Size;
        Assert.True(loaders.Sum(l => l.Calls) <= spotSize + 1);   // the probe + the spot sample; never the corpus

        // a release signed with a `release` key is refused
        var releaseOnly = TrustList.Parse(DevRegisterKey.TrustList((new DevRegisterKey(), ["release"], false)));
        Assert.StartsWith("MODEL_SIGNATURE", ModelStaging.VerifyAndStage(site.Layout, release, releaseOnly, false, today, Load, contracts, null, _ => g).Issues[0]);

        // journal: M1 (verified model), M2 waived over lexical-only L1, K1 (verified vectors for the full generation)
        var p = new ActivationParticipant(new SiteInspector(site.Layout, site.NewReader()));
        Assert.True(p.LoadHead());
        using (var eng = new ActivationEngine(new ActivationEngineOptions
        {
            Site = site.Layout, WriterId = "activator-1", Database = site.Db, Exclusions = site.NewReader(),
            Participant = new DirectParticipantLink(p), Disk = new FixedDiskProbe(1L << 40), Production = false,
        }))
        {
            eng.AcquireLock();
            Assert.Equal("NO_MODEL", Assert.Throws<ActivationRefused>(() => eng.Transition("KNOWLEDGE", gid)).Code);
            eng.Transition("MODELS", rep.ModelId!);
            eng.Transition("KNOWLEDGE", gid);
            var pin = p.Pin();
            Assert.True(pin.SemanticSearch);
            ev["journal"] = new JsonObject { ["models"] = pin.Models, ["knowledge"] = pin.Knowledge, ["semantic_search"] = pin.SemanticSearch,
                ["steps"] = new JsonArray(ActivationJournal.Read(site.Layout.JournalPath).Entries.Select(e => (JsonNode)e.Step).ToArray()) };
            p.Unpin(pin);
        }

        // serving: semantic scorer from the verified pack, never embedding a passage (only the query)
        {
            var mdir = Path.Combine(site.Layout.ModelsDir, rep.ModelId!);
            using var qe = new E5Embedder(Path.Combine(mdir, "embedder"), threads, expectedModelSha256: rep.ModelSha256);
            var prmBytes = File.ReadAllBytes(Directory.GetFiles(Path.Combine(release, "accelerators", "vectors"), "*.params.json").Single());
            var packFile = VectorPackFile.Open(Path.Combine(mdir, "vectors", gid + ".mimvec"), out _)!;
            var ix = Mimamsa.Core.Search.SearchIndex.Build(g);
            var dense = DenseIndex.FromVerifiedPack(ix, qe, packFile, VectorPackParams.Parse(prmBytes), "multilingual-e5-small@614241f6");
            var top = dense.TopK("punishment for desertion under the Army Act", 5);
            Assert.Equal(0, dense.Embedded);
            Assert.Equal(5, top.Count);
            ev["serving"] = new JsonObject { ["passages"] = dense.Count, ["embedded_on_site"] = dense.Embedded, ["load_ms"] = Math.Round(dense.BuildTime.TotalMilliseconds),
                ["top1_doc"] = ix.Passages[top[0].Passage].DocId, ["top1_score"] = Math.Round(top[0].Score, 4) };
        }

        // the B04 verifiers on the real sample's centrally built index and graph, then the outcome rule
        // the index as the central build publishes it (SearchIndex.Open with a pinned build time), unless provided
        var idxRoot = Path.Combine(central, "index");
        var idxDir = Directory.Exists(idxRoot) && Directory.GetDirectories(idxRoot).Any(d => !Path.GetFileName(d).StartsWith('.'))
            ? Directory.GetDirectories(idxRoot).Single(d => !Path.GetFileName(d).StartsWith('.')) : S3b.BuildIndex(g, idxRoot);
        var lex = LexicalIndexVerifier.Verify(g, idxDir, "R-s3b-real", LexicalIndexVerifier.SiteSourceDigest(g),
            B04Sampling.Effective(contracts["LEXICAL_INDEX"], LexicalIndexVerifier.Postings, false), B04Sampling.Effective(contracts["LEXICAL_INDEX"], LexicalIndexVerifier.Queries, false));
        // graph rows as the central build writes them (the same B03 derivation), unless the driver provides files
        var (gn, ge) = File.Exists(Path.Combine(central, "graph", "graph_nodes.jsonl"))
            ? (File.ReadAllBytes(Path.Combine(central, "graph", "graph_nodes.jsonl")), File.ReadAllBytes(Path.Combine(central, "graph", "graph_edges.jsonl")))
            : S3b.GraphRows(g);
        var rows = GraphVerifier.Parse(gn, ge);
        var gev = GraphVerifier.Verify(g, gn, ge, GraphStore.Digest(GraphBuilder.Build(g)), GraphBuilder.Version, "R-s3b-real", B04Sampling.Effective(contracts["GRAPH"], GraphVerifier.Check, false));
        Assert.True(lex.Verified(LexicalIndexVerifier.Required), string.Join("; ", lex.Issues));
        Assert.True(gev.Verified(GraphVerifier.Required), string.Join("; ", gev.Issues));
        ev["lexical_index"] = lex.ToJson(LexicalIndexVerifier.Required);
        ev["graph"] = gev.ToJson(GraphVerifier.Required);
        var inputs = new Dictionary<string, string> { ["GRAPH"] = "VERIFIED", ["LEXICAL_INDEX"] = "VERIFIED", ["VECTOR_PACK"] = "VERIFIED",
                                                      ["KNOWLEDGE_ROWS"] = "VERIFIED", ["TEXT_STORE"] = "VERIFIED" };
        var dev = ActivationOutcome.Decide(inputs, contracts, "development");
        var prodOutcome = ActivationOutcome.Decide(inputs, contracts, "production");
        Assert.Equal("ACTIVE_FULL", (string?)dev["result"]);
        Assert.Equal("UNCALIBRATED_IN_PRODUCTION", (string?)prodOutcome["refusal"]);
        ev["outcome"] = new JsonObject { ["development"] = dev, ["production"] = prodOutcome,
            ["inputs_note"] = "GRAPH, LEXICAL_INDEX and VECTOR_PACK verified here on the real sample; KNOWLEDGE_ROWS and TEXT_STORE are verified by the B03 loader and DiskTextStore.Bind in the CP-1 slice (a real-corpus knowledge release is S3-A)" };

        // a missing pack: lexical-only; a mismatched installed model: refused
        var noPack = GenerationStaging.VerifyVectorPack(g, sample, null, "R", contracts, false, _ => null);
        Assert.Equal("MISSING", noPack.State);
        if (Env("MIMAMSA_S3B_OTHER_MODEL") is { } other)
        {
            var mdir = Path.Combine(site.Layout.ModelsDir, rep.ModelId!);
            using var o = new E5Embedder(other, threads);
            var packFile = Path.Combine(mdir, "vectors", gid + ".mimvec");
            var prm = File.ReadAllBytes(Directory.GetFiles(Path.Combine(release, "accelerators", "vectors"), "*.params.json").Single());
            var m = JsonNode.Parse(File.ReadAllBytes(Path.Combine(release, "KNOWLEDGE_RELEASE.json")))!["components"]!.AsArray().First(c => (string?)c!["kind"] == "VECTOR_PACK")!;
            var mis = VectorPackVerifier.Verify(g, packFile, prm, rep.ModelSha256!, (string)m["result_digest"]!, (string)m["source_digest"]!, "R-s3b-real", o, B04Sampling.Override("VECTOR_SPOT_REEMBED", 8, 1e-4));
            Assert.False(mis.Verified(VectorPackVerifier.Required));
            ev["mismatched_model"] = new JsonObject { ["other_model_sha256"] = o.ModelSha256, ["status"] = (string?)mis.ToJson(VectorPackVerifier.Required)["status"],
                ["issues"] = new JsonArray(mis.Issues.Select(i => (JsonNode)i).ToArray()) };
        }
        foreach (var l in loaders) l.Dispose();
        File.WriteAllText(evidenceOut, ev.ToJsonString(new JsonSerializerOptions { WriteIndented = true }));
    }
}
