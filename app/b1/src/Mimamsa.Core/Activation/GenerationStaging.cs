// C16 Tranche B CP-1: the activation tool's STAGING step, the only writer of the catalogue marker
// generations/<id>/C16_VERIFIED.json (bound staging evidence, StagingMarker). Review C16-CP1-02/04, contract 2.1
// activation-outcome rule (PR #82 1e3060de, C16-I21-01/02/03):
//   - one stager at a time per site (staging lease generations/.c16-staging.lease, exclusive);
//   - any prior marker is removed FIRST, so a failed (re-)verification leaves the generation not installed;
//   - each accelerator gets an explicit reference INPUT state (VERIFIED | FAILED | MISSING) from what the site checked:
//       KNOWLEDGE_ROWS, GRAPH  the B03 restricted loader (typed rows, counts, digests, full re-derivation);
//       LEXICAL_INDEX          the shipped accelerators/search-index/search.sqlite exists, hashes to the signed inventory
//                              and passes quick_check (a missing or bad file is FAILED - never skipped);
//       TEXT_STORE             adopted shipped store bound by Bind() = VERIFIED; a store the site had to build is FAILED
//                              as shipped, with REBUILD evidence (builder, source/result digests, the required checks)
//                              so the rule can mark it REBUILT_VERIFIED - distinct from MISSING;
//       VECTOR_PACK            absent = MISSING (lexical-only); present = FAILED (not verifiable here yet, B04);
//     and the decision is ActivationOutcome.Decide (the .NET mirror of components.activation_outcome): REFUSED in any
//     form (INVALID_INPUT, CONTRACT_INVALID, REBUILD_REQUIRED, UNCALIBRATED_IN_PRODUCTION) never stages;
//   - production staging (the default) refuses a release imported in development mode (development-signed), and the rule
//     refuses any UNCALIBRATED contract in use in production at every service level (owner gate
//     OD-C16-UNCALIBRATED-PRODUCTION open; C16-CP1-04) - so the CP-1 fixture can only be staged in development mode;
//   - the marker binds the generation's release and files, the input states, the decision and component digests, and
//     the staged DB evidence (schema names, per-table rows and rows_sha256); the engine re-validates it before DECIDED.
// Development / CP-1 fixture use; the production installer wiring (a CLI `stage` command) is B07.
using System.Reflection;
using System.Security.Cryptography;
using System.Text.Json.Nodes;
using Mimamsa.Core.ComponentVerification;
using Mimamsa.Core.Generation;
using Mimamsa.Core.Knowledge;

namespace Mimamsa.Core.Activation;

public sealed record StagingReport(string Generation, long ReleaseSequence, bool Ok, IReadOnlyList<string> Issues,
    IReadOnlyDictionary<string, string> Components, IReadOnlyList<string> LoadedTables, string? TextStoreOrigin, string? DeclaredServiceLevel)
{
    /// B06 2.1 classification recorded in the catalogue marker (K2: activates with no model).
    public bool LexicalOnly { get; init; }
    /// The reference inputs (kind -> VERIFIED | FAILED | MISSING), rebuild evidence and the decision (ActivationOutcome).
    public IReadOnlyDictionary<string, string> Inputs { get; init; } = new Dictionary<string, string>();
    public IReadOnlyDictionary<string, JsonObject?> Rebuilds { get; init; } = new Dictionary<string, JsonObject?>();
    public JsonObject? Outcome { get; init; }
    /// C16 S3-B: the B04 kind-specific evidence per component (checks, samples used, issues, timings).
    public IReadOnlyDictionary<string, JsonObject> Verification { get; init; } = new Dictionary<string, JsonObject>();
}

/// C16 S3-B (B10, development path): a model installed on the site and verified (ModelStaging), as GenerationStaging
/// needs it to verify a release's vector pack (one query-sized embed per sampled passage; never the corpus).
public sealed record InstalledModel(string ModelId, ComponentVerification.IPassageEmbedder Embedder);

public static class GenerationStaging
{
    public const string LeaseFile = ".c16-staging.lease";
    const string LexicalDb = "accelerators/search-index/search.sqlite";

    static string Sha(string p) { using var f = File.OpenRead(p); return Convert.ToHexString(SHA256.HashData(f)).ToLowerInvariant(); }
    static string Local(string gdir, string rel) => Path.Combine(gdir, rel.Replace('/', Path.DirectorySeparatorChar));
    static readonly string BuilderCommit = typeof(GenerationStaging).Assembly.GetCustomAttribute<AssemblyInformationalVersionAttribute>()?.InformationalVersion is { Length: > 0 } v ? v : "unrecorded";

    /// Verify a stage-only generation and, if the reference rule activates it, write its bound C16_VERIFIED.json marker.
    /// contracts: the B04 component verification contracts (kind -> contract) the decision is taken against.
    public static async Task<StagingReport> VerifyAndStageAsync(SiteLayout site, string generation, KnowledgeRowLoader loader, string textRoot,
                                                                IReadOnlyDictionary<string, JsonObject?> contracts, Action<string>? log = null,
                                                                bool production = true, CancellationToken ct = default,
                                                                Func<string, InstalledModel?>? models = null)
    {
        SiteLayout.CheckId(generation);
        Directory.CreateDirectory(site.GenerationsDir);
        FileStream lease;
        try { lease = new FileStream(Path.Combine(site.GenerationsDir, LeaseFile), FileMode.OpenOrCreate, FileAccess.ReadWrite, FileShare.None); }
        catch (IOException) { return new(generation, 0, false, ["STAGING_LEASE_HELD: another stager holds the staging lease"], new Dictionary<string, string>(), [], null, null); }
        using (lease)
        {
            var cat = new GenerationCatalog(site);
            cat.Invalidate(generation);   // a failed (re-)verification must leave no marker
            return await StageLockedAsync(site, cat, generation, loader, textRoot, contracts, log, production, models, ct);
        }
    }

    /// The sample a B04 sampled check runs with. In production an UNCALIBRATED contract check is never run: null is
    /// returned and the caller records the check NOT_RUN. That never lets an unverified component serve: the contract is
    /// then uncalibrated by construction, so ActivationOutcome refuses the release (UNCALIBRATED_IN_PRODUCTION) whatever
    /// the input state (OD-C16-UNCALIBRATED-PRODUCTION open).
    static ComponentVerification.EffectiveSample? SampleFor(IReadOnlyDictionary<string, JsonObject?> contracts, string kind, string check, bool production)
    {
        try { return ComponentVerification.B04Sampling.Effective(contracts.GetValueOrDefault(kind), check, production); }
        catch (ComponentVerification.UncalibratedInProductionException) { return null; }
    }

    /// VECTOR_PACK input state for a generation (B04, B10): (MISSING | FAILED | VERIFIED, evidence, the model verified with).
    /// A shipped pack is verified against the INSTALLED, verified model it names; no installed model, a mismatched model or
    /// any failed check is FAILED (lexical-only service under the outcome rule). Nothing here embeds the corpus.
    public static (string State, JsonObject? Evidence, InstalledModel? Model) VerifyVectorPack(GenerationStore g, string gdir, JsonObject? vp, string releaseId,
        IReadOnlyDictionary<string, JsonObject?> contracts, bool production, Func<string, InstalledModel?>? models)
    {
        if (vp is null) return ("MISSING", null, null);
        var vfiles = vp["files"]?.AsArray().Select(f => f!.AsObject()).ToList() ?? [];
        var pack = vfiles.FirstOrDefault(f => ((string?)f["path"])?.EndsWith(".mimvec", StringComparison.Ordinal) == true);
        var prm = vfiles.FirstOrDefault(f => ((string?)f["path"])?.EndsWith(".params.json", StringComparison.Ordinal) == true);
        var modelSha = (string?)vp["model_sha256"];
        var installed = modelSha is null ? null : models?.Invoke(modelSha);
        var ev = new ComponentEvidence("VECTOR_PACK");
        if (pack is null || prm is null || modelSha is null) ev.Fail("VECTOR_TRAILER", "the release declares no vector file, params file or model");
        else if (vfiles.Any(f => !File.Exists(Local(gdir, (string)f["path"]!)) || Sha(Local(gdir, (string)f["path"]!)) != (string?)f["sha256"]))
            ev.Fail("VECTOR_TRAILER", "a vector pack file differs from the signed inventory");
        else if (installed is null) ev.NotRun(VectorPackVerifier.Spot, $"no installed, verified model {modelSha[..Math.Min(12, modelSha.Length)]}: lexical-only service");
        else
        {
            ev = VectorPackVerifier.Verify(g, Local(gdir, (string)pack["path"]!), File.ReadAllBytes(Local(gdir, (string)prm["path"]!)), modelSha,
                (string)vp["result_digest"]!, (string)vp["source_digest"]!, releaseId, installed.Embedder, SampleFor(contracts, "VECTOR_PACK", VectorPackVerifier.Spot, production));
            bool ok = ev.Verified(VectorPackVerifier.Required.Where(r => !(r == VectorPackVerifier.Spot && production && ev.Checks.GetValueOrDefault(r) == "NOT_RUN")));
            if (ok) return ("VERIFIED", ev.ToJson(VectorPackVerifier.Required), installed);
        }
        return ("FAILED", ev.ToJson(VectorPackVerifier.Required), null);
    }

    static async Task<StagingReport> StageLockedAsync(SiteLayout site, GenerationCatalog cat, string generation, KnowledgeRowLoader loader, string textRoot,
                                                      IReadOnlyDictionary<string, JsonObject?> contracts, Action<string>? log, bool production,
                                                      Func<string, InstalledModel?>? models, CancellationToken ct)
    {
        var verification = new Dictionary<string, JsonObject>(StringComparer.Ordinal);
        var gdir = Path.Combine(site.GenerationsDir, generation);
        var issues = new List<string>();
        var inputs = new Dictionary<string, string>(StringComparer.Ordinal);
        var rebuilds = new Dictionary<string, JsonObject?>(StringComparer.Ordinal);
        var tables = new List<string>();
        var meta = JsonNode.Parse(File.ReadAllText(Path.Combine(gdir, "generation.json")))!.AsObject();
        long seq = meta["release_sequence"]!.GetValue<long>();
        var kmPath = Path.Combine(gdir, "KNOWLEDGE_RELEASE.json");
        if (!File.Exists(kmPath))
            return new(generation, seq, false, ["NO_KNOWLEDGE_RELEASE: the generation carries no knowledge release manifest"], inputs, tables, null, null);
        var kmBytes = File.ReadAllBytes(kmPath);
        var km = JsonNode.Parse(kmBytes)!.AsObject();
        var components = km["components"]!.AsArray().Select(c => c!.AsObject()).ToList();
        var level = (string?)km["capability"]?["declared_service_level"];
        var lexicalOnly = LexicalOnly.Classify(kmBytes);
        JsonObject? Comp(string kind) => components.FirstOrDefault(c => (string)c["kind"]! == kind);

        // C16-CP1-04: production staging never accepts a release imported in development mode (development-signed)
        if (production && (string?)meta["import_mode"] != "production")
            return new(generation, seq, false, ["DEVELOPMENT_RELEASE_IN_PRODUCTION: the generation was imported in development mode (development-signed)"],
                       inputs, tables, null, level) { LexicalOnly = lexicalOnly };

        // C16 S3-B: the verified generation (memory text) that every B04 check compares against
        var g = GenerationStore.Load(site.Root, null, TextStoreOptions.Memory, null, generation);
        var releaseId = (string)km["release_id"]!;
        bool Accept(ComponentEvidence ev, string[] required, params string[] sampledChecks) =>
            ev.Verified(required.Where(r => !(sampledChecks.Contains(r) && ev.Checks.GetValueOrDefault(r) == "NOT_RUN" && production)));

        // LEXICAL_INDEX: inventory, presence, hash and quick_check (CP-1), then the B04 checks on the shipped file itself:
        // manifest and source digest, SAMPLED_POSTINGS_REDERIVE and SAMPLED_QUERY_PARITY (LexicalIndexVerifier)
        var lex = Comp("LEXICAL_INDEX");
        var lexEntry = lex?["files"]?.AsArray().Select(f => f!.AsObject()).FirstOrDefault(f => (string?)f["path"] == LexicalDb);
        inputs["LEXICAL_INDEX"] = "FAILED";
        if (lex is null) { inputs["LEXICAL_INDEX"] = "MISSING"; issues.Add("LEXICAL_INDEX: the release ships no lexical index"); }
        else if (lexEntry is null) issues.Add($"LEXICAL_INDEX: {LexicalDb} is not in the signed inventory");
        else if (!File.Exists(Local(gdir, LexicalDb))) issues.Add($"LEXICAL_INDEX: {LexicalDb} is missing");
        else if (Sha(Local(gdir, LexicalDb)) != (string?)lexEntry["sha256"]) issues.Add("LEXICAL_INDEX: file differs from the signed inventory");
        else
        {
            var ev = LexicalIndexVerifier.Verify(g, Path.GetDirectoryName(Local(gdir, LexicalDb))!, releaseId, (string?)lex["source_digest"],
                SampleFor(contracts, "LEXICAL_INDEX", LexicalIndexVerifier.Postings, production), SampleFor(contracts, "LEXICAL_INDEX", LexicalIndexVerifier.Queries, production));
            verification["LEXICAL_INDEX"] = ev.ToJson(LexicalIndexVerifier.Required);
            if (Accept(ev, LexicalIndexVerifier.Required, LexicalIndexVerifier.Postings, LexicalIndexVerifier.Queries)) inputs["LEXICAL_INDEX"] = "VERIFIED";
            else issues.AddRange(ev.Issues.Take(5).Select(i => "LEXICAL_INDEX: " + i));
        }

        // VECTOR_PACK (B04, B10): absent = MISSING (lexical-only). A shipped pack is verified against the INSTALLED, verified
        // model it names (VectorPackVerifier: trailer, every key recomputed, source and result digests, spot re-embed of a
        // seeded sample, one query-sized embed each). No installed model, a mismatched model or any failed check = FAILED,
        // which the outcome rule turns into lexical-only service (never site embedding of the corpus).
        var (vpState, vpEvidence, vectorModel) = VerifyVectorPack(g, gdir, Comp("VECTOR_PACK"), releaseId, contracts, production, models);
        inputs["VECTOR_PACK"] = vpState;
        if (vpEvidence is not null) verification["VECTOR_PACK"] = vpEvidence;

        // KNOWLEDGE_ROWS + GRAPH through the one typed restricted loader (B03: typed rows, counts, digests, full re-derivation)
        var files = new Dictionary<string, byte[]>(StringComparer.Ordinal);
        var declared = new List<DeclaredTable>();
        foreach (var comp in components.Where(c => (string)c["kind"]! is "KNOWLEDGE_ROWS" or "GRAPH"))
            foreach (var t in comp["tables"]!.AsArray().Select(x => x!.AsObject()))
            {
                files[(string)t["table"]!] = await File.ReadAllBytesAsync(Local(gdir, (string)t["file"]!), ct);
                declared.Add(new DeclaredTable((string)t["table"]!, (long)t["row_count"]!, (string)t["rows_sha256"]!));
            }
        var staged = new List<StagedTable>();
        inputs["KNOWLEDGE_ROWS"] = Comp("KNOWLEDGE_ROWS") is null ? "MISSING" : "FAILED";
        inputs["GRAPH"] = Comp("GRAPH") is null ? "MISSING" : "FAILED";
        bool graphB04 = false;
        if (Comp("GRAPH") is { } gc && files.TryGetValue("graph_nodes", out var gn) && files.TryGetValue("graph_edges", out var ge))
        {
            // GRAPH (B04, S3-B): GRAPH_DIGEST, GRAPH_STRUCTURAL_RECHECK and SAMPLED_REBUILD_PARITY on the shipped rows, in
            // addition to the loader's full re-derivation below (kept: see app/b1/evidence/c16_s3b/S3B_REPORT.md)
            var gev = GraphVerifier.Verify(g, gn, ge, (string)gc["result_digest"]!, (string?)km["compatibility"]?["graph_builder_version"] ?? "", releaseId,
                SampleFor(contracts, "GRAPH", GraphVerifier.Check, production));
            verification["GRAPH"] = gev.ToJson(GraphVerifier.Required);
            graphB04 = Accept(gev, GraphVerifier.Required, GraphVerifier.Check);
            if (!graphB04) issues.AddRange(gev.Issues.Take(5).Select(i => "GRAPH: " + i));
        }
        if (declared.Count > 0)
        {
            var load = await loader.LoadAsync(new KnowledgeLoadRequest { ReleaseSequence = seq, Files = files, Declared = declared, Sources = KnowledgeSources.FromGeneration(g) }, ct);
            issues.AddRange(load.Issues.Select(i => i.ToString()));
            tables.AddRange(load.Verified.Select(t => $"{t.Spec.Table}:{t.RowCount}"));
            staged.AddRange(load.Verified.Select(t => new StagedTable(t.Spec.Table, t.RowCount, t.RowsSha256)));
            if (load.Ok && Comp("KNOWLEDGE_ROWS") is not null) inputs["KNOWLEDGE_ROWS"] = "VERIFIED";
            if (load.Ok && graphB04 && load.Verified.Any(t => t.Spec.Table == "graph_nodes") && load.Verified.Any(t => t.Spec.Table == "graph_edges"))
                inputs["GRAPH"] = "VERIFIED";
        }

        // TEXT_STORE: adopted shipped store = VERIFIED; a site-built store = FAILED as shipped plus rebuild evidence
        string? origin = null;
        inputs["TEXT_STORE"] = Comp("TEXT_STORE") is null ? "MISSING" : "FAILED";
        try
        {
            var tg = GenerationStore.Load(site.Root, null, new TextStoreOptions { Store = "disk", Dir = textRoot }, log, generation);
            var store = tg.Text as DiskTextStore;
            origin = store?.Origin;
            bool same = tg.Documents.Count == g.Documents.Count
                        && tg.Documents.Values.All(d => g.Documents.TryGetValue(d.DocId, out var m) && d.Passages.Count == m.Passages.Count
                                                        && d.Pages.Values.All(p => m.Pages.TryGetValue(p.Page, out var mp) && p.Text == mp.Text));
            var storeFile = store?.StorePath is { } sp ? Path.Combine(sp, DiskTextStore.DbFile) : null;
            var storeManifest = store?.StorePath is { } sp2 ? JsonNode.Parse(File.ReadAllText(Path.Combine(sp2, DiskTextStore.ManifestFile)))!.AsObject() : null;
            (tg.Text as IDisposable)?.Dispose();
            if (!same) issues.Add("TEXT_STORE: disk store differs from the verified records");
            else if (origin == "adopted") inputs["TEXT_STORE"] = "VERIFIED";
            else if (storeFile is not null && storeManifest is not null)
                rebuilds["TEXT_STORE"] = new JsonObject
                {
                    ["status"] = "VERIFIED",
                    ["builder"] = new JsonObject { ["name"] = "Mimamsa.Core.DiskTextStore", ["version"] = DiskTextStore.FormatVersion, ["commit"] = BuilderCommit },
                    ["source_digest"] = (string?)storeManifest["source_digest"], ["result_digest"] = Sha(storeFile),
                    // quick_check and Bind() ran in Verify/OpenOrBuild; every page read is hashed (PAGE_HASH_ON_READ)
                    ["checks"] = new JsonObject { ["SQLITE_QUICK_CHECK"] = "PASS", ["TEXT_STORE_BIND_EXACT"] = "PASS", ["PAGE_HASH_ON_READ"] = "PASS" },
                };
        }
        catch (TextIntegrityException e) { issues.Add("TEXT_STORE: " + e.Message); }
        Microsoft.Data.Sqlite.SqliteConnection.ClearAllPools();

        var outcome = ActivationOutcome.Decide(inputs, contracts, production ? "production" : "development", rebuilds);
        var states = ActivationOutcome.Kinds.ToDictionary(k => k, k => (string?)outcome["components"]?[k]?["state"] ?? "NOT_DECIDED", StringComparer.Ordinal);
        if ((string?)outcome["result"] == "REFUSED")
            issues.Add($"OUTCOME_REFUSED {(string?)outcome["refusal"]}: {string.Join("; ", outcome["reasons"]!.AsArray().Select(x => (string?)x))}");
        // B06 2.1: a release whose vector pack is not in use (missing or failed) is served lexical-only (K2)
        lexicalOnly = LexicalOnly.Classify(kmBytes, (string?)outcome["service_level"] == "DEGRADED_LEXICAL_ONLY" ? LexicalOnly.DegradedVectorOutcome : null);
        bool pass = issues.Count == 0;
        if (pass)
        {
            long bytes = Directory.EnumerateFiles(gdir, "*", SearchOption.AllDirectories).Sum(f => new FileInfo(f).Length);
            var digests = components.ToDictionary(c => (string)c["component_id"]!, c => (string)c["result_digest"]!, StringComparer.Ordinal);
            var recorded = new Dictionary<string, string>(StringComparer.Ordinal);
            foreach (var k in ActivationOutcome.Kinds) { recorded["input:" + k] = inputs[k]; recorded["state:" + k] = states[k]; }
            recorded["result"] = (string)outcome["result"]!; recorded["service_level"] = (string)outcome["service_level"]!;
            var evidence = new StagingEvidence(lexicalOnly, production, bytes, recorded, digests,
                KnowledgeAllowlist.StagingSchema(seq), KnowledgeAllowlist.ActiveSchema(seq), staged);
            cat.StageBound(generation, StagingMarker.Build(site, generation, evidence));
            if (cat.MarkerProblem(generation, full: true) is { } why) { cat.Invalidate(generation); issues.Add("MARKER: " + why); pass = false; }
            else
            {
                log?.Invoke($"staging: {generation} staged ({(string)outcome["result"]!}, lexical_only={lexicalOnly}, production={production})");
                // B10 (S3-B): the installed model now has verified vectors for this generation (K1 for its activation)
                if (vectorModel is not null && cat.Model(vectorModel.ModelId) is { Verified: true } sm)
                    cat.StageModel(vectorModel.ModelId, true, sm.VectorsFor.Append(generation).Distinct(StringComparer.Ordinal).Order(StringComparer.Ordinal));
            }
        }
        return new(generation, seq, pass, issues, states, tables, origin, level)
        { LexicalOnly = lexicalOnly, Inputs = inputs, Rebuilds = rebuilds, Outcome = outcome, Verification = verification };
    }
}
