// C16 Stage 3 S3-B (B10, development path): an intelligence release signed under the separate `model` purpose with a
// DEVELOPMENT key installs a verified model with verified vectors for a real generation; the journal then activates
// MODELS (M1, M2 waived over lexical-only knowledge) and a FULL knowledge generation (K1), and semantic search turns on.
// Production refuses the model release outright (FG-MODEL-TRUST-PURPOSE open). A `release` key, a mismatched pack, a
// tampered file or a model that fails its self-test refuse the release and nothing is staged. The test model here is a
// deterministic stand-in (HashEmbedder over a fixed model file); the real multilingual-e5-small run is recorded in
// app/b1/evidence/c16_s3b (C16S3bRealModelTests, gated on MIMAMSA_HYBRID_MODEL).
using System.Security.Cryptography;
using System.Text;
using System.Text.Json.Nodes;
using Mimamsa.Core.Activation;
using Mimamsa.Core.ComponentVerification;
using Mimamsa.Core.Generation;
using Mimamsa.Tests.Activation;

namespace Mimamsa.Tests;

public static class ModelReleaseBuilder
{
    static string Sha(byte[] b) => Convert.ToHexStringLower(SHA256.HashData(b));

    /// The model "file" is fixed bytes; the test embedder takes its identity (sha) from that file, like E5Embedder does.
    public static Func<string, IPassageEmbedder> TestLoader(double noise = 0) =>
        dir => new HashEmbedder(Sha(File.ReadAllBytes(Path.Combine(dir, "onnx", "model.onnx"))), 8, noise);

    public static readonly byte[] ModelBytes = Encoding.ASCII.GetBytes("mimamsa s3b test model (not an ONNX model; HashEmbedder stand-in)");
    public static string ModelSha => Sha(ModelBytes);

    /// Writes a signed development intelligence release: models/embedder/onnx/{model.onnx,sentencepiece.bpe.model},
    /// accelerators/vectors/<sha>.{mimvec,params.json} for each generation, KNOWLEDGE_RELEASE.json, SHA256SUMS(.sig).
    public static string Write(string dir, string releaseId, IEnumerable<GenerationStore> packsFor, Func<byte[], byte[]> sign, IPassageEmbedder? packEmbedder = null,
                               byte[]? modelBytes = null, Action<string>? beforeSigning = null)
    {
        Directory.CreateDirectory(dir);
        var mb = modelBytes ?? ModelBytes;
        var msha = Sha(mb);
        void Put(string rel, byte[] b) { var p = Path.Combine(dir, rel.Replace('/', Path.DirectorySeparatorChar)); Directory.CreateDirectory(Path.GetDirectoryName(p)!); File.WriteAllBytes(p, b); }
        Put("models/embedder/onnx/model.onnx", mb);
        Put("models/embedder/onnx/sentencepiece.bpe.model", "spm"u8.ToArray());
        var comps = new JsonArray(new JsonObject
        {
            ["component_id"] = "model-embedder", ["kind"] = "MODEL_FILE", ["model_sha256"] = msha,
            ["files"] = new JsonArray(new JsonObject { ["path"] = "models/embedder/onnx/model.onnx", ["sha256"] = msha },
                                      new JsonObject { ["path"] = "models/embedder/onnx/sentencepiece.bpe.model", ["sha256"] = Sha("spm"u8.ToArray()) }),
        });
        int i = 0;
        foreach (var g in packsFor)
        {
            var vdir = Path.Combine(dir, "accelerators", "vectors", $"g{i}");
            Directory.CreateDirectory(vdir);
            var pack = S3b.BuildPack(g, packEmbedder ?? new HashEmbedder(msha), vdir);
            File.Move(pack.Path, Path.Combine(vdir, msha + ".mimvec"));
            Put($"accelerators/vectors/g{i}/{msha}.params.json", pack.Params);
            comps.Add(new JsonObject
            {
                ["component_id"] = $"vectors-{i}", ["kind"] = "VECTOR_PACK", ["model_sha256"] = msha, ["fallback"] = "REFUSE_RELEASE",
                ["result_digest"] = pack.ResultDigest, ["source_digest"] = pack.SourceDigest,
                ["files"] = new JsonArray(new JsonObject { ["path"] = $"accelerators/vectors/g{i}/{msha}.mimvec", ["sha256"] = Sha(File.ReadAllBytes(Path.Combine(vdir, msha + ".mimvec"))) },
                                          new JsonObject { ["path"] = $"accelerators/vectors/g{i}/{msha}.params.json", ["sha256"] = Sha(pack.Params) }),
            });
            i++;
        }
        Put("KNOWLEDGE_RELEASE.json", Encoding.UTF8.GetBytes(new JsonObject
        {
            ["record_kind"] = "knowledge_release_manifest", ["release_class"] = "INTELLIGENCE", ["signing_purpose"] = "model", ["release_id"] = releaseId,
            ["compatibility"] = new JsonObject { ["required_models"] = new JsonArray(new JsonObject { ["role"] = "EMBEDDER", ["sha256"] = msha, ["model_id"] = "test-embedder" }) },
            ["components"] = comps,
        }.ToJsonString()));
        beforeSigning?.Invoke(dir);
        var sums = new StringBuilder();
        foreach (var f in Directory.GetFiles(dir, "*", SearchOption.AllDirectories).Select(f => Path.GetRelativePath(dir, f).Replace('\\', '/')).Order(StringComparer.Ordinal))
            sums.Append(Sha(File.ReadAllBytes(Path.Combine(dir, f)))).Append("  ").Append(f).Append('\n');
        var sb = Encoding.UTF8.GetBytes(sums.ToString());
        File.WriteAllBytes(Path.Combine(dir, "SHA256SUMS"), sb);
        File.WriteAllBytes(Path.Combine(dir, "SHA256SUMS.sig"), sign(sb));
        return dir;
    }
}

public class C16S3bModelTests
{
    /// A B06 fixture site whose generation `G` is a real copy of the SYN generation (full knowledge: not lexical-only)
    /// and whose active generation L1 is lexical-only; no model installed.
    static (FixtureSite Site, string G) Site(string label)
    {
        var g = Syn.Gen.GenerationId;
        var site = new FixtureSite(label, ["L1", g], "L1", null, new Dictionary<string, (bool, string[])>(), lexicalOnly: ["L1"]);
        foreach (var f in Directory.GetFiles(Syn.Site, "*", SearchOption.AllDirectories).Where(f => !Path.GetFileName(f).Equals("ACTIVE", StringComparison.Ordinal)))
        {
            var rel = Path.GetRelativePath(Syn.Site, f);
            if (rel.StartsWith("generations", StringComparison.Ordinal) && !rel.StartsWith(Path.Combine("generations", g), StringComparison.Ordinal)) continue;
            var dst = Path.Combine(site.Root, rel);
            if (File.Exists(dst)) continue;
            Directory.CreateDirectory(Path.GetDirectoryName(dst)!); File.Copy(f, dst);
        }
        return (site, g);
    }

    static TrustList Trust(DevRegisterKey k, params string[] purposes) => TrustList.Parse(DevRegisterKey.TrustList((k, purposes, false)));
    static DateOnly Today => DateOnly.FromDateTime(DateTime.UtcNow);

    [Fact]
    public void ADevelopmentModelReleaseGivesFullServiceThroughM1M2AndK1()
    {
        var (site, g) = Site("b10full");
        using var _ = site;
        var key = new DevRegisterKey();
        var gen = GenerationStore.Load(site.Root, null, TextStoreOptions.Memory, null, g);
        var rel = ModelReleaseBuilder.Write(Path.Combine(site.Root, "..", Path.GetFileName(site.Root) + "-mrel"), "M-s3b-dev-1", [gen], key.Sign);
        try
        {
            var rep = ModelStaging.VerifyAndStage(site.Layout, rel, Trust(key, "model"), production: false, Today, ModelReleaseBuilder.TestLoader(), S3b.Contracts());
            Assert.True(rep.Ok, string.Join("; ", rep.Issues));
            Assert.Equal([g], rep.VectorsFor);
            var cat = new GenerationCatalog(site.Layout);
            Assert.Equal(new StagedModel(true, new HashSet<string> { g }).VectorsFor, cat.Model("M-s3b-dev-1")!.VectorsFor);
            Assert.True(File.Exists(Path.Combine(site.Layout.ModelsDir, "M-s3b-dev-1", ModelStaging.EvidenceFile)));
            Assert.Equal("UNCALIBRATED_DEVELOPMENT_DEFAULT", (string?)rep.Evidence["vector_packs"]![0]!["evidence"]!["samples"]!["VECTOR_SPOT_REEMBED"]!["size_source"]);

            // the knowledge generation's own pack, verified against the installed model (GenerationStaging's path)
            var installed = ModelStaging.Installed(site.Layout, ModelReleaseBuilder.TestLoader());
            Assert.Equal("M-s3b-dev-1", installed(ModelReleaseBuilder.ModelSha)!.ModelId);
            Assert.Null(installed(S3b.ModelB));

            var p = new ActivationParticipant(new SiteInspector(site.Layout, site.NewReader()));
            Assert.True(p.LoadHead());
            using var eng = new ActivationEngine(new ActivationEngineOptions
            {
                Site = site.Layout, WriterId = "activator-1", Database = site.Db, Exclusions = site.NewReader(),
                Participant = new DirectParticipantLink(p), Disk = new FixedDiskProbe(1L << 40), Production = false,
            });
            eng.AcquireLock();
            Assert.Equal("NO_MODEL", Assert.Throws<ActivationRefused>(() => eng.Transition("KNOWLEDGE", g)).Code);   // K1 before the model
            eng.Transition("MODELS", "M-s3b-dev-1");                                                                 // M1; M2 waived (L1 lexical-only)
            var lex = p.Pin(); Assert.False(lex.SemanticSearch); p.Unpin(lex);
            eng.Transition("KNOWLEDGE", g);                                                                          // K1: verified vectors for g
            var full = p.Pin();
            Assert.True(full.SemanticSearch);
            Assert.Equal("M-s3b-dev-1", full.Models);
            p.Unpin(full);
        }
        finally { TestDirs.Delete(rel); }
    }

    [Fact]
    public void ProductionAndAReleaseKeyAreRefusedAndNothingIsStaged()
    {
        var (site, g) = Site("b10prod");
        using var _ = site;
        var key = new DevRegisterKey();
        var gen = GenerationStore.Load(site.Root, null, TextStoreOptions.Memory, null, g);
        var rel = ModelReleaseBuilder.Write(Path.Combine(site.Root, "..", Path.GetFileName(site.Root) + "-mrel"), "M-s3b-prod", [gen], key.Sign);
        try
        {
            var prod = ModelStaging.VerifyAndStage(site.Layout, rel, Trust(key, "model"), production: true, Today, ModelReleaseBuilder.TestLoader(), S3b.Contracts());
            Assert.False(prod.Ok);
            Assert.StartsWith("MODEL_TRUST_PURPOSE_NOT_AUTHORISED", prod.Issues[0]);
            var releaseKey = ModelStaging.VerifyAndStage(site.Layout, rel, Trust(key, "release"), production: false, Today, ModelReleaseBuilder.TestLoader(), S3b.Contracts());
            Assert.StartsWith("MODEL_SIGNATURE", releaseKey.Issues[0]);
            Assert.Null(new GenerationCatalog(site.Layout).Model("M-s3b-prod"));
            var p = new ActivationParticipant(new SiteInspector(site.Layout, site.NewReader()));
            Assert.True(p.LoadHead());
            using var eng = new ActivationEngine(new ActivationEngineOptions
            {
                Site = site.Layout, WriterId = "activator-1", Database = site.Db, Exclusions = site.NewReader(),
                Participant = new DirectParticipantLink(p), Disk = new FixedDiskProbe(1L << 40), Production = false,
            });
            eng.AcquireLock();
            Assert.Equal("NOT_STAGED", Assert.Throws<ActivationRefused>(() => eng.Transition("MODELS", "M-s3b-prod")).Code);   // M1
        }
        finally { TestDirs.Delete(rel); }
    }

    [Fact]
    public void AMismatchedOrTamperedPackOrABadModelRefusesTheRelease()
    {
        var (site, g) = Site("b10bad");
        using var _ = site;
        var key = new DevRegisterKey();
        var gen = GenerationStore.Load(site.Root, null, TextStoreOptions.Memory, null, g);
        var baseDir = Path.Combine(site.Root, "..", Path.GetFileName(site.Root) + "-mrel");
        try
        {
            // pack built with a DIFFERENT model's vectors but labelled with this model (keys recomputed fine, vectors wrong)
            var mismatched = ModelReleaseBuilder.Write(Path.Combine(baseDir, "a"), "M-a", [gen], key.Sign, packEmbedder: new HashEmbedder(ModelReleaseBuilder.ModelSha, 8, noise: 1.0));
            var r1 = ModelStaging.VerifyAndStage(site.Layout, mismatched, Trust(key, "model"), false, Today, ModelReleaseBuilder.TestLoader(), S3b.Contracts());
            Assert.StartsWith("MODEL_VECTOR_PACK", r1.Issues[0]);
            Assert.Null(new GenerationCatalog(site.Layout).Model("M-a"));
            // a file changed after signing
            var tampered = ModelReleaseBuilder.Write(Path.Combine(baseDir, "b"), "M-b", [gen], key.Sign);
            File.AppendAllText(Path.Combine(tampered, "models", "embedder", "onnx", "sentencepiece.bpe.model"), "x");
            Assert.StartsWith("MODEL_INVENTORY", ModelStaging.VerifyAndStage(site.Layout, tampered, Trust(key, "model"), false, Today, ModelReleaseBuilder.TestLoader(), S3b.Contracts()).Issues[0]);
            // the loaded model is not the pinned one (self-test)
            var self = ModelReleaseBuilder.Write(Path.Combine(baseDir, "c"), "M-c", [gen], key.Sign);
            var wrongLoader = (Func<string, IPassageEmbedder>)(_ => new HashEmbedder(S3b.ModelB));
            Assert.StartsWith("MODEL_SELFTEST", ModelStaging.VerifyAndStage(site.Layout, self, Trust(key, "model"), false, Today, wrongLoader, S3b.Contracts()).Issues[0]);
            Assert.Null(new GenerationCatalog(site.Layout).Model("M-c"));
        }
        finally { TestDirs.Delete(baseDir); }
    }

    [Fact]
    public void AModelWithoutVectorsForAFullGenerationCannotServeIt()
    {
        var (site, g) = Site("b10novec");
        using var _ = site;
        var key = new DevRegisterKey();
        var rel = ModelReleaseBuilder.Write(Path.Combine(site.Root, "..", Path.GetFileName(site.Root) + "-mrel"), "M-novec", [], key.Sign);   // no pack
        try
        {
            var rep = ModelStaging.VerifyAndStage(site.Layout, rel, Trust(key, "model"), false, Today, ModelReleaseBuilder.TestLoader(), S3b.Contracts());
            Assert.True(rep.Ok, string.Join("; ", rep.Issues));
            Assert.Empty(rep.VectorsFor);
            var p = new ActivationParticipant(new SiteInspector(site.Layout, site.NewReader()));
            Assert.True(p.LoadHead());
            using var eng = new ActivationEngine(new ActivationEngineOptions
            {
                Site = site.Layout, WriterId = "activator-1", Database = site.Db, Exclusions = site.NewReader(),
                Participant = new DirectParticipantLink(p), Disk = new FixedDiskProbe(1L << 40), Production = false,
            });
            eng.AcquireLock();
            eng.Transition("MODELS", "M-novec");                                                                     // M2 waived over lexical-only L1
            Assert.Equal("NO_VECTORS", Assert.Throws<ActivationRefused>(() => eng.Transition("KNOWLEDGE", g)).Code);  // K1
            var pin = p.Pin(); Assert.False(pin.SemanticSearch); p.Unpin(pin);                                       // lexical-only service
        }
        finally { TestDirs.Delete(rel); }
    }
}
