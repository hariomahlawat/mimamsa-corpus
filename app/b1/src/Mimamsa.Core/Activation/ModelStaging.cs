// C16 Stage 3 S3-B (B10, DEVELOPMENT PATH ONLY): staging of an intelligence (model) release on a site.
//
// An intelligence release (arch §2 row 3, §8.3; decision D3) ships an embedding model and the FULL vector packs built
// for it upstream, signed under the separate `model` purpose. Until the owner authorises that purpose and its keys
// (FG-MODEL-TRUST-PURPOSE, OPEN) and calibrates the spot re-embed (FG-CALIBRATED-SAMPLES, OPEN), PRODUCTION REFUSES
// every model release before reading it (MODEL_TRUST_PURPOSE_NOT_AUTHORISED). No operational trust list carries the
// purpose: the v1 trust-list schema does not even allow it, so the only trust list that can name it is a DEVELOPMENT one.
//
// Development staging, in order (nothing is installed unless every step passes; fallback REFUSE_RELEASE):
//   1. signature: SHA256SUMS.sig over SHA256SUMS verifies with a key trusted for purpose `model` (never `release`);
//   2. inventory: every file listed hashes as listed, nothing unlisted, safe relative paths;
//   3. manifest: release_class INTELLIGENCE, signing_purpose model, one MODEL_FILE embedder whose model.onnx sha256 is the
//      declared model_sha256 and a required EMBEDDER model with that sha;
//   4. install: the model files are copied under models/<release id>/ and hashed again;
//   5. ONNX load self-test: the model loads, reports the pinned sha, and embeds a probe query to a finite unit vector;
//   6. vector packs: each pack whose 2.1 source digest equals an installed generation's is verified against it
//      (VectorPackVerifier with this model: trailer, keys, digests, spot re-embed); any pack that fails refuses the release;
//   7. MODEL_EVIDENCE.json (bound file hashes, key id, checks) then MODEL_VERIFIED.json {verified, vectors_for}.
// The MODELS journal transition (M1/M2) and KNOWLEDGE transitions (K1) then consult MODEL_VERIFIED.json as before.
using System.Security.Cryptography;
using System.Text;
using System.Text.Json.Nodes;
using Mimamsa.Core.ComponentVerification;
using Mimamsa.Core.Generation;

namespace Mimamsa.Core.Activation;

public sealed record ModelStagingReport(bool Ok, string? ModelId, string? ModelSha256, IReadOnlyList<string> Issues, IReadOnlyList<string> VectorsFor, JsonObject Evidence);

public static class ModelStaging
{
    public const string Purpose = "model";
    public const string EvidenceFile = "MODEL_EVIDENCE.json";
    public const string Sums = "SHA256SUMS", Sig = "SHA256SUMS.sig", Manifest = "KNOWLEDGE_RELEASE.json";

    static string Sha(string p) { using var f = File.OpenRead(p); return Convert.ToHexStringLower(SHA256.HashData(f)); }

    static ModelStagingReport Refuse(string code, string why, JsonObject? ev = null) =>
        new(false, null, null, [$"{code}: {why}"], [], ev ?? new JsonObject { ["refusal"] = code });

    /// `load(modelDir)` opens the installed model (Mimamsa.Hybrid.E5Embedder in the service; a test embedder in tests).
    public static ModelStagingReport VerifyAndStage(SiteLayout site, string releaseDir, TrustList trust, bool production, DateOnly today,
                                                    Func<string, IPassageEmbedder> load, IReadOnlyDictionary<string, JsonObject?> contracts,
                                                    Action<string>? log = null)
    {
        if (production)
            return Refuse("MODEL_TRUST_PURPOSE_NOT_AUTHORISED",
                "intelligence releases are refused in production until the owner authorises the `model` signing purpose and its keys (FG-MODEL-TRUST-PURPOSE open) and the spot re-embed is calibrated (FG-CALIBRATED-SAMPLES open)");
        var ev = new JsonObject { ["mode"] = "development", ["purpose"] = Purpose };
        // 1. signature
        var sumsPath = Path.Combine(releaseDir, Sums); var sigPath = Path.Combine(releaseDir, Sig);
        if (!File.Exists(sumsPath) || !File.Exists(sigPath)) return Refuse("MODEL_SIGNATURE", "SHA256SUMS or its signature is missing");
        var sums = File.ReadAllBytes(sumsPath);
        var key = trust.VerifyDetached(sums, File.ReadAllBytes(sigPath), Purpose, production: false, today);
        if (key is null) return Refuse("MODEL_SIGNATURE", "no key trusted for purpose `model` verifies SHA256SUMS (a `release` key never signs models)");
        ev["key_id"] = key.KeyId; ev["key_holder"] = key.Holder;
        // 2. inventory
        var listed = new SortedDictionary<string, string>(StringComparer.Ordinal);
        foreach (var line in Encoding.UTF8.GetString(sums).Split('\n'))
        {
            if (line.Length == 0) continue;
            var parts = line.Split("  ", 2);
            if (parts.Length != 2 || parts[0].Length != 64 || parts[1].Contains('\\') || parts[1].StartsWith('/') || parts[1].Split('/').Any(x => x is "" or "." or ".."))
                return Refuse("MODEL_INVENTORY", "malformed or unsafe SHA256SUMS line");
            if (!listed.TryAdd(parts[1], parts[0])) return Refuse("MODEL_INVENTORY", "duplicate SHA256SUMS entry");
        }
        var present = Directory.EnumerateFiles(releaseDir, "*", SearchOption.AllDirectories)
            .Select(f => Path.GetRelativePath(releaseDir, f).Replace('\\', '/')).Where(r => r is not (Sums or Sig)).ToHashSet(StringComparer.Ordinal);
        if (!present.SetEquals(listed.Keys)) return Refuse("MODEL_INVENTORY", "files differ from SHA256SUMS (missing or unlisted)");
        foreach (var (rel, sha) in listed)
            if (Sha(Path.Combine(releaseDir, rel)) != sha) return Refuse("MODEL_INVENTORY", $"{rel} does not hash to SHA256SUMS");
        // 3. manifest
        JsonObject m;
        try { m = JsonNode.Parse(File.ReadAllBytes(Path.Combine(releaseDir, Manifest)))!.AsObject(); }
        catch (Exception e) when (e is System.Text.Json.JsonException or InvalidOperationException or IOException) { return Refuse("MODEL_MANIFEST", "manifest unreadable"); }
        if ((string?)m["release_class"] != "INTELLIGENCE" || (string?)m["signing_purpose"] != Purpose)
            return Refuse("MODEL_MANIFEST", "not an intelligence release signed under the `model` purpose");
        var id = SiteLayout.CheckId((string)m["release_id"]!);
        var comps = m["components"]!.AsArray().Select(c => c!.AsObject()).ToList();
        var modelComp = comps.Where(c => (string?)c["kind"] == "MODEL_FILE").ToList();
        if (modelComp.Count != 1) return Refuse("MODEL_MANIFEST", "exactly one MODEL_FILE component (the embedder) is required");
        var modelSha = (string?)modelComp[0]["model_sha256"];
        var mfiles = modelComp[0]["files"]!.AsArray().Select(f => f!.AsObject()).ToList();
        var onnx = mfiles.FirstOrDefault(f => ((string?)f["path"])?.EndsWith("/onnx/model.onnx", StringComparison.Ordinal) == true);
        if (modelSha is null || onnx is null || (string?)onnx["sha256"] != modelSha)
            return Refuse("MODEL_MANIFEST", "the embedder's model.onnx does not hash to the declared model_sha256");
        if (!(m["compatibility"]?["required_models"] as JsonArray ?? []).Any(r => (string?)r?["role"] == "EMBEDDER" && (string?)r?["sha256"] == modelSha))
            return Refuse("MODEL_MANIFEST", "the release does not require its own embedder");
        foreach (var f in comps.SelectMany(c => c["files"]!.AsArray()).Select(f => f!.AsObject()))
            if (listed.GetValueOrDefault((string)f["path"]!) != (string?)f["sha256"]) return Refuse("MODEL_MANIFEST", $"{(string?)f["path"]} differs from the signed inventory");
        var onnxPath = (string)onnx["path"]!;
        var root = onnxPath[..^"/onnx/model.onnx".Length];
        if (mfiles.Any(f => !((string)f["path"]!).StartsWith(root + "/", StringComparison.Ordinal))) return Refuse("MODEL_MANIFEST", "model files outside the embedder directory");
        ev["release_id"] = id; ev["model_sha256"] = modelSha;
        // 4. install (copy, hash again)
        var cat = new GenerationCatalog(site);
        var mdir = Path.Combine(site.ModelsDir, id);
        var modelDir = Path.Combine(mdir, "embedder");
        Directory.CreateDirectory(mdir);
        File.Delete(Path.Combine(mdir, "MODEL_VERIFIED.json"));
        File.Delete(Path.Combine(mdir, EvidenceFile));
        var installed = new JsonObject();
        foreach (var f in mfiles)
        {
            var rel = ((string)f["path"]!)[(root.Length + 1)..];
            var dst = Path.Combine(modelDir, rel.Replace('/', Path.DirectorySeparatorChar));
            Directory.CreateDirectory(Path.GetDirectoryName(dst)!);
            File.Copy(Path.Combine(releaseDir, (string)f["path"]!), dst, overwrite: true);
            if (Sha(dst) != (string?)f["sha256"]) return Refuse("MODEL_INSTALL", $"{rel} changed while being installed");
            installed[rel] = (string)f["sha256"]!;
        }
        ev["files"] = installed;
        // 5. ONNX load self-test
        IPassageEmbedder emb;
        try { emb = load(modelDir); }
        catch (Exception e) when (e is not OutOfMemoryException) { return Refuse("MODEL_SELFTEST", "the model does not load: " + e.GetType().Name); }
        var probe = emb.EmbedOne("query: mimamsa model self-test", 128);
        double norm = Math.Sqrt(probe.Sum(x => (double)x * x));
        if (emb.ModelSha256 != modelSha || probe.Length != emb.Dim || probe.Any(x => !float.IsFinite(x)) || Math.Abs(norm - 1) > 1e-3)
            return Refuse("MODEL_SELFTEST", "the loaded model is not the pinned model or does not embed a probe to a finite unit vector");
        ev["self_test"] = new JsonObject { ["dim"] = emb.Dim, ["norm"] = norm };
        // 6. vector packs for installed generations
        var vectorsFor = new List<string>();
        var packs = new JsonArray();
        foreach (var vp in comps.Where(c => (string?)c["kind"] == "VECTOR_PACK"))
        {
            var vfiles = vp["files"]!.AsArray().Select(f => f!.AsObject()).ToList();
            var pack = vfiles.FirstOrDefault(f => ((string?)f["path"])?.EndsWith(".mimvec", StringComparison.Ordinal) == true);
            var prm = vfiles.FirstOrDefault(f => ((string?)f["path"])?.EndsWith(".params.json", StringComparison.Ordinal) == true);
            if (pack is null || prm is null || (string?)vp["model_sha256"] != modelSha) return Refuse("MODEL_VECTOR_PACK", "a vector pack is not for this release's model or lacks its params");
            var prmBytes = File.ReadAllBytes(Path.Combine(releaseDir, (string)prm["path"]!));
            VectorPackParams p;
            try { p = VectorPackParams.Parse(prmBytes); } catch (Exception e) when (e is FormatException or System.Text.Json.JsonException or InvalidOperationException or NullReferenceException) { return Refuse("MODEL_VECTOR_PACK", "vector pack params unreadable"); }
            string? target = null;
            foreach (var gen in cat.Installed())
            {
                var g = GenerationStore.Load(site.Root, null, TextStoreOptions.Memory, null, gen);
                var keys = VectorPackVerifier.Inputs(g, p).Select(x => VectorPackVerifier.Key(modelSha, p.MaxTokens, x.Input));
                if (VectorPackVerifier.SourceDigest(modelSha, p.MaxTokens, keys) != (string?)vp["source_digest"]) continue;
                target = gen;
                var spot = B04Sampling.Effective(contracts.GetValueOrDefault("VECTOR_PACK"), VectorPackVerifier.Spot, production: false);
                var vev = VectorPackVerifier.Verify(g, Path.Combine(releaseDir, (string)pack["path"]!), prmBytes, modelSha, (string)vp["result_digest"]!,
                    (string)vp["source_digest"]!, id, emb, spot);
                packs.Add(new JsonObject { ["generation"] = gen, ["evidence"] = vev.ToJson(VectorPackVerifier.Required) });
                if (!vev.Verified(VectorPackVerifier.Required))
                    return Refuse("MODEL_VECTOR_PACK", $"the vector pack for {gen} does not verify (REFUSE_RELEASE): {string.Join("; ", vev.Issues.Take(3))}", ev);
                var dst = Path.Combine(mdir, "vectors", gen + ".mimvec");
                Directory.CreateDirectory(Path.GetDirectoryName(dst)!);
                File.Copy(Path.Combine(releaseDir, (string)pack["path"]!), dst, overwrite: true);
                vectorsFor.Add(gen);
                break;
            }
            if (target is null) packs.Add(new JsonObject { ["component_id"] = (string?)vp["component_id"], ["generation"] = null, ["note"] = "built for no generation installed on this site; not used" });
        }
        (emb as IDisposable)?.Dispose();
        ev["vector_packs"] = packs;
        ev["vectors_for"] = new JsonArray(vectorsFor.Select(v => (JsonNode)v).ToArray());
        // 7. evidence, then the verified record the activation engine consults (M1/M2/K1)
        DurableFile.WriteAtomic(Path.Combine(mdir, EvidenceFile), CanonicalJson.Bytes(ev));
        var prior = cat.Model(id)?.VectorsFor ?? new HashSet<string>();
        cat.StageModel(id, true, vectorsFor.Concat(prior).Distinct(StringComparer.Ordinal).Order(StringComparer.Ordinal));
        log?.Invoke($"model staging: {id} staged (development; model {modelSha[..12]}; vectors for {string.Join(",", vectorsFor)})");
        return new(true, id, modelSha, [], vectorsFor, ev);
    }

    /// Installed, verified models by model sha (for GenerationStaging's vector-pack verification). Only models whose
    /// MODEL_EVIDENCE.json and MODEL_VERIFIED.json both exist, verified, and whose installed model.onnx still hashes to
    /// the recorded sha.
    public static Func<string, InstalledModel?> Installed(SiteLayout site, Func<string, IPassageEmbedder> load)
    {
        var cache = new Dictionary<string, InstalledModel?>(StringComparer.Ordinal);
        return sha =>
        {
            if (cache.TryGetValue(sha, out var hit)) return hit;
            InstalledModel? found = null;
            var cat = new GenerationCatalog(site);
            if (Directory.Exists(site.ModelsDir))
                foreach (var d in Directory.GetDirectories(site.ModelsDir).Order(StringComparer.Ordinal))
                {
                    var evPath = Path.Combine(d, EvidenceFile);
                    if (!File.Exists(evPath)) continue;
                    var ev = JsonNode.Parse(File.ReadAllBytes(evPath))!.AsObject();
                    var id = Path.GetFileName(d);
                    if ((string?)ev["model_sha256"] != sha || cat.Model(id) is not { Verified: true }) continue;
                    var onnx = Path.Combine(d, "embedder", "onnx", "model.onnx");
                    if (!File.Exists(onnx) || Sha(onnx) != sha) continue;
                    found = new InstalledModel(id, load(Path.Combine(d, "embedder")));
                    break;
                }
            cache[sha] = found;
            return found;
        };
    }
}
