// C16 Tranche B CP-1: the activation tool's STAGING step, the only writer of the catalogue marker
// generations/<id>/C16_VERIFIED.json (bound staging evidence, StagingMarker). Review C16-CP1-02/04:
//   - one stager at a time per site (staging lease generations/.c16-staging.lease, exclusive);
//   - any prior marker is removed FIRST, so a failed (re-)verification leaves the generation not installed;
//   - every component must reach an explicitly allowed state; MISSING never passes generically:
//       KNOWLEDGE_ROWS  VERIFIED          B03 restricted loader: typed rows, counts, digests, full re-derivation
//       GRAPH           VERIFIED          same loader (graph rows) - the release must ship it
//       TEXT_STORE      VERIFIED          shipped store adopted (2.1 source digest) and bound by Bind()
//                       REBUILT_VERIFIED  a store the site built and bound (shipped one absent or rejected) - distinct
//       LEXICAL_INDEX   VERIFIED          the shipped accelerators/search-index/search.sqlite exists, hashes to the
//                                         signed inventory and passes quick_check (sampled checks UNCALIBRATED, B04)
//       VECTOR_PACK     OMITTED_DEGRADED  only for a release classified lexical-only (2.1 K2); a shipped pack cannot be
//                                         verified here yet, so it FAILS (B04)
//   - production staging (the default) refuses a release imported in development mode (development-signed) and any
//     release whose verification relies on UNCALIBRATED sampled checks (C16-CP1-04; B04 rule 4);
//   - the marker binds the generation's release and files, the component states and digests, and the staged DB
//     evidence (schema names, per-table rows and rows_sha256); the engine re-validates it before DECIDED.
// Development / CP-1 fixture use; the production installer wiring (a CLI `stage` command) is B07.
using System.Security.Cryptography;
using System.Text.Json.Nodes;
using Mimamsa.Core.Generation;
using Mimamsa.Core.Knowledge;

namespace Mimamsa.Core.Activation;

public sealed record StagingReport(string Generation, long ReleaseSequence, bool Ok, IReadOnlyList<string> Issues,
    IReadOnlyDictionary<string, string> Components, IReadOnlyList<string> LoadedTables, string? TextStoreOrigin, string? DeclaredServiceLevel)
{
    /// B06 2.1 classification recorded in the catalogue marker (K2: activates with no model).
    public bool LexicalOnly { get; init; }
}

public static class GenerationStaging
{
    public const string LeaseFile = ".c16-staging.lease";
    public static readonly IReadOnlyDictionary<string, string[]> Allowed = new Dictionary<string, string[]>(StringComparer.Ordinal)
    {
        ["KNOWLEDGE_ROWS"] = ["VERIFIED"], ["GRAPH"] = ["VERIFIED"], ["TEXT_STORE"] = ["VERIFIED", "REBUILT_VERIFIED"],
        ["LEXICAL_INDEX"] = ["VERIFIED"], ["VECTOR_PACK"] = ["OMITTED_DEGRADED"],
    };
    const string LexicalDb = "accelerators/search-index/search.sqlite";

    static string Sha(string p) { using var f = File.OpenRead(p); return Convert.ToHexString(SHA256.HashData(f)).ToLowerInvariant(); }
    static string Local(string gdir, string rel) => Path.Combine(gdir, rel.Replace('/', Path.DirectorySeparatorChar));

    /// Test hook (C16-CP1-02 negatives): called after verification and before the marker is written.
    public static Action<string>? BeforeMarkerForTests { get; set; }

    /// Verify a stage-only generation and, if everything passes, write its bound C16_VERIFIED.json marker.
    public static async Task<StagingReport> VerifyAndStageAsync(SiteLayout site, string generation, KnowledgeRowLoader loader, string textRoot,
                                                                Action<string>? log = null, bool production = true, CancellationToken ct = default)
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
            return await StageLockedAsync(site, cat, generation, loader, textRoot, log, production, ct);
        }
    }

    static async Task<StagingReport> StageLockedAsync(SiteLayout site, GenerationCatalog cat, string generation, KnowledgeRowLoader loader, string textRoot,
                                                      Action<string>? log, bool production, CancellationToken ct)
    {
        var gdir = Path.Combine(site.GenerationsDir, generation);
        var issues = new List<string>();
        var comps = new Dictionary<string, string>(StringComparer.Ordinal);
        var tables = new List<string>();
        var meta = JsonNode.Parse(File.ReadAllText(Path.Combine(gdir, "generation.json")))!.AsObject();
        long seq = meta["release_sequence"]!.GetValue<long>();
        var kmPath = Path.Combine(gdir, "KNOWLEDGE_RELEASE.json");
        if (!File.Exists(kmPath))
            return new(generation, seq, false, ["NO_KNOWLEDGE_RELEASE: the generation carries no knowledge release manifest"], comps, tables, null, null);
        var kmBytes = File.ReadAllBytes(kmPath);
        var km = JsonNode.Parse(kmBytes)!.AsObject();
        var components = km["components"]!.AsArray().Select(c => c!.AsObject()).ToList();
        var level = (string?)km["capability"]?["declared_service_level"];
        bool lexicalOnly = LexicalOnly.Classify(kmBytes);
        JsonObject? Comp(string kind) => components.FirstOrDefault(c => (string)c["kind"]! == kind);

        // C16-CP1-04: production staging never accepts a development-imported (dev-signed) or uncalibrated release
        if (production)
        {
            if ((string?)meta["import_mode"] != "production")
                issues.Add("DEVELOPMENT_RELEASE_IN_PRODUCTION: the generation was imported in development mode (development-signed)");
            var uncal = components.Where(c => (c["verify"] as JsonArray)?.Any(v => ((string?)v)?.StartsWith("SAMPLED_", StringComparison.Ordinal) == true) == true)
                                  .Select(c => (string)c["kind"]!).ToList();
            if (uncal.Count > 0) issues.Add("UNCALIBRATED_IN_PRODUCTION: sampled checks have no calibrated sizes (FG-CALIBRATED-SAMPLES): " + string.Join(", ", uncal));
            if (issues.Count > 0) return new(generation, seq, false, issues, comps, tables, null, level) { LexicalOnly = lexicalOnly };
        }

        // LEXICAL_INDEX first (cheap, no DB): the expected file must be in the inventory, present, hashed and quick_checked
        var lex = Comp("LEXICAL_INDEX");
        var lexEntry = lex?["files"]?.AsArray().Select(f => f!.AsObject()).FirstOrDefault(f => (string?)f["path"] == LexicalDb);
        string lexState = "FAILED";
        if (lex is null) issues.Add("LEXICAL_INDEX: the release ships no lexical index");
        else if (lexEntry is null) issues.Add($"LEXICAL_INDEX: {LexicalDb} is not in the signed inventory");
        else if (!File.Exists(Local(gdir, LexicalDb))) issues.Add($"LEXICAL_INDEX: {LexicalDb} is missing");
        else if (Sha(Local(gdir, LexicalDb)) != (string?)lexEntry["sha256"]) issues.Add("LEXICAL_INDEX: file differs from the signed inventory");
        else
        {
            using var sc = new Microsoft.Data.Sqlite.SqliteConnection($"Data Source={Local(gdir, LexicalDb)};Mode=ReadOnly;Pooling=False");
            sc.Open();
            using var q = sc.CreateCommand(); q.CommandText = "PRAGMA quick_check";
            if ((string?)q.ExecuteScalar() == "ok") lexState = "VERIFIED"; else issues.Add("LEXICAL_INDEX: quick_check failed");
        }
        comps["LEXICAL_INDEX"] = lexState;

        // VECTOR_PACK: absent only for a lexical-only release
        var vp = Comp("VECTOR_PACK");
        comps["VECTOR_PACK"] = vp is null && lexicalOnly ? "OMITTED_DEGRADED" : "FAILED";
        if (comps["VECTOR_PACK"] == "FAILED") issues.Add(vp is null ? "VECTOR_PACK: absent but the release is not lexical-only" : "VECTOR_PACK: vector verification is not available (B04)");

        // KNOWLEDGE_ROWS + GRAPH through the one typed restricted loader (B03)
        var g = GenerationStore.Load(site.Root, null, TextStoreOptions.Memory, null, generation);
        if (Comp("KNOWLEDGE_ROWS") is null) issues.Add("KNOWLEDGE_ROWS: the release ships no knowledge rows");
        if (Comp("GRAPH") is null) issues.Add("GRAPH: the release ships no graph rows");
        var files = new Dictionary<string, byte[]>(StringComparer.Ordinal);
        var declared = new List<DeclaredTable>();
        foreach (var comp in components.Where(c => (string)c["kind"]! is "KNOWLEDGE_ROWS" or "GRAPH"))
            foreach (var t in comp["tables"]!.AsArray().Select(x => x!.AsObject()))
            {
                files[(string)t["table"]!] = await File.ReadAllBytesAsync(Local(gdir, (string)t["file"]!), ct);
                declared.Add(new DeclaredTable((string)t["table"]!, (long)t["row_count"]!, (string)t["rows_sha256"]!));
            }
        var staged = new List<StagedTable>();
        if (issues.Count == 0)
        {
            var load = await loader.LoadAsync(new KnowledgeLoadRequest { ReleaseSequence = seq, Files = files, Declared = declared, Sources = KnowledgeSources.FromGeneration(g) }, ct);
            issues.AddRange(load.Issues.Select(i => i.ToString()));
            tables.AddRange(load.Verified.Select(t => $"{t.Spec.Table}:{t.RowCount}"));
            staged.AddRange(load.Verified.Select(t => new StagedTable(t.Spec.Table, t.RowCount, t.RowsSha256)));
            comps["KNOWLEDGE_ROWS"] = load.Ok ? "VERIFIED" : "FAILED";
            comps["GRAPH"] = load.Ok && load.Verified.Any(t => t.Spec.Table == "graph_nodes") && load.Verified.Any(t => t.Spec.Table == "graph_edges") ? "VERIFIED" : "FAILED";
        }
        else { comps["KNOWLEDGE_ROWS"] = "NOT_RUN"; comps["GRAPH"] = "NOT_RUN"; }

        // TEXT_STORE: adopted when shipped and matching (VERIFIED), else built by the site (REBUILT_VERIFIED); Bind both
        string? origin = null;
        try
        {
            var tg = GenerationStore.Load(site.Root, null, new TextStoreOptions { Store = "disk", Dir = textRoot }, log, generation);
            origin = (tg.Text as DiskTextStore)?.Origin;
            bool same = tg.Documents.Count == g.Documents.Count
                        && tg.Documents.Values.All(d => g.Documents.TryGetValue(d.DocId, out var m) && d.Passages.Count == m.Passages.Count
                                                        && d.Pages.Values.All(p => m.Pages.TryGetValue(p.Page, out var mp) && p.Text == mp.Text));
            (tg.Text as IDisposable)?.Dispose();
            comps["TEXT_STORE"] = !same ? "FAILED" : origin == "adopted" ? "VERIFIED" : "REBUILT_VERIFIED";
            if (!same) issues.Add("TEXT_STORE: disk store differs from the verified records");
        }
        catch (TextIntegrityException e) { comps["TEXT_STORE"] = "FAILED"; issues.Add("TEXT_STORE: " + e.Message); }
        Microsoft.Data.Sqlite.SqliteConnection.ClearAllPools();

        foreach (var (k, allowed) in Allowed)
            if (!comps.TryGetValue(k, out var st) || !allowed.Contains(st))
                if (!issues.Any(i => i.StartsWith(k, StringComparison.Ordinal))) issues.Add($"{k}: state {(comps.GetValueOrDefault(k) ?? "ABSENT")} is not allowed");
        bool pass = issues.Count == 0;
        if (pass)
        {
            long bytes = Directory.EnumerateFiles(gdir, "*", SearchOption.AllDirectories).Sum(f => new FileInfo(f).Length);
            var digests = components.ToDictionary(c => (string)c["component_id"]!, c => (string)c["result_digest"]!, StringComparer.Ordinal);
            var evidence = new StagingEvidence(lexicalOnly, production, bytes, comps, digests,
                KnowledgeAllowlist.StagingSchema(seq), KnowledgeAllowlist.ActiveSchema(seq), staged);
            BeforeMarkerForTests?.Invoke(generation);
            cat.StageBound(generation, StagingMarker.Build(site, generation, evidence));
            if (cat.MarkerProblem(generation, full: true) is { } why) { cat.Invalidate(generation); issues.Add("MARKER: " + why); pass = false; }
            else log?.Invoke($"staging: {generation} verified and staged ({GenerationCatalog.Marker}, lexical_only={lexicalOnly}, production={production})");
        }
        return new(generation, seq, pass, issues, comps, tables, origin, level) { LexicalOnly = lexicalOnly };
    }
}
