// C16 Tranche B CP-1: the activation tool's STAGING step, the owner of the catalogue marker
// generations/<id>/C16_VERIFIED.json (GenerationCatalog). A generation imported stage-only by the site importer (B01)
// becomes "installed" (activatable by the journal) only after the site has verified its knowledge components here:
//   - KNOWLEDGE_ROWS and GRAPH rows: the B03 restricted loader (typed parse, COPY as the loader role, counts, digests,
//     full re-derivation) into kr_<n>_staging, which DB_APPLIED later promotes;
//   - TEXT_STORE: the shipped store is adopted (2.1 source digest) or rebuilt locally; Bind() verifies it either way;
//   - LEXICAL_INDEX: the shipped file hashes to the signed inventory and passes quick_check (sampled checks are
//     UNCALIBRATED and not built: B04);
//   - VECTOR_PACK: absent in a lexical-only release (DEGRADED_LEXICAL_ONLY; the journal's K2 rule applies).
// The marker is written last and only when every check passes, so a generation that failed verification can never be
// activated. Development / CP-1 fixture use; the production installer wiring is B07.
using System.Security.Cryptography;
using System.Text.Json.Nodes;
using Mimamsa.Core.Generation;
using Mimamsa.Core.Knowledge;

namespace Mimamsa.Core.Activation;

public sealed record StagingReport(string Generation, long ReleaseSequence, bool Ok, IReadOnlyList<string> Issues,
    IReadOnlyDictionary<string, string> Components, IReadOnlyList<string> LoadedTables, string? TextStoreOrigin, string? DeclaredServiceLevel);

public static class GenerationStaging
{
    static string Sha(string p) { using var f = File.OpenRead(p); return Convert.ToHexString(SHA256.HashData(f)).ToLowerInvariant(); }
    static string Local(string gdir, string rel) => Path.Combine(gdir, rel.Replace('/', Path.DirectorySeparatorChar));

    /// Verify a stage-only generation and, if everything passes, write its C16_VERIFIED.json catalogue marker.
    public static async Task<StagingReport> VerifyAndStageAsync(SiteLayout site, string generation, KnowledgeRowLoader loader, string textRoot,
                                                                Action<string>? log = null, CancellationToken ct = default)
    {
        SiteLayout.CheckId(generation);
        var gdir = Path.Combine(site.GenerationsDir, generation);
        var issues = new List<string>();
        var comps = new Dictionary<string, string>(StringComparer.Ordinal);
        var tables = new List<string>();
        var meta = JsonNode.Parse(File.ReadAllText(Path.Combine(gdir, "generation.json")))!.AsObject();
        long seq = meta["release_sequence"]!.GetValue<long>();
        var kmPath = Path.Combine(gdir, "KNOWLEDGE_RELEASE.json");
        if (!File.Exists(kmPath))
            return new(generation, seq, false, ["NO_KNOWLEDGE_RELEASE: the generation carries no knowledge release manifest"], comps, tables, null, null);
        var km = JsonNode.Parse(File.ReadAllText(kmPath))!.AsObject();
        var components = km["components"]!.AsArray().Select(c => c!.AsObject()).ToList();
        var level = (string?)km["capability"]?["declared_service_level"];
        var g = GenerationStore.Load(site.Root, null, TextStoreOptions.Memory, null, generation);

        // KNOWLEDGE_ROWS + GRAPH through the one typed restricted loader (B03)
        var files = new Dictionary<string, byte[]>(StringComparer.Ordinal);
        var declared = new List<DeclaredTable>();
        foreach (var comp in components.Where(c => (string)c["kind"]! is "KNOWLEDGE_ROWS" or "GRAPH"))
            foreach (var t in comp["tables"]!.AsArray().Select(x => x!.AsObject()))
            {
                files[(string)t["table"]!] = await File.ReadAllBytesAsync(Local(gdir, (string)t["file"]!), ct);
                declared.Add(new DeclaredTable((string)t["table"]!, (long)t["row_count"]!, (string)t["rows_sha256"]!));
            }
        var load = await loader.LoadAsync(new KnowledgeLoadRequest { ReleaseSequence = seq, Files = files, Declared = declared, Sources = KnowledgeSources.FromGeneration(g) }, ct);
        issues.AddRange(load.Issues.Select(i => i.ToString()));
        tables.AddRange(load.Verified.Select(t => $"{t.Spec.Table}:{t.RowCount}"));
        comps["KNOWLEDGE_ROWS"] = load.Ok ? "VERIFIED" : "FAILED";
        comps["GRAPH"] = load.Ok && load.Verified.Any(t => t.Spec.Table == "graph_nodes") && load.Verified.Any(t => t.Spec.Table == "graph_edges") ? "VERIFIED" : "FAILED";

        // TEXT_STORE: adopted when shipped and matching, otherwise rebuilt locally; both verified by Bind
        string? origin = null;
        try
        {
            var tg = GenerationStore.Load(site.Root, null, new TextStoreOptions { Store = "disk", Dir = textRoot }, log, generation);
            origin = (tg.Text as DiskTextStore)?.Origin;
            bool same = tg.Documents.Count == g.Documents.Count
                        && tg.Documents.Values.All(d => g.Documents.TryGetValue(d.DocId, out var m) && d.Passages.Count == m.Passages.Count
                                                        && d.Pages.Values.All(p => m.Pages.TryGetValue(p.Page, out var mp) && p.Text == mp.Text));
            (tg.Text as IDisposable)?.Dispose();
            comps["TEXT_STORE"] = !same ? "FAILED" : origin == "built" ? "REBUILT_LOCALLY" : "VERIFIED";
            if (!same) issues.Add("TEXT_STORE: disk store differs from the verified records");
        }
        catch (TextIntegrityException e) { comps["TEXT_STORE"] = "FAILED"; issues.Add("TEXT_STORE: " + e.Message); }

        // LEXICAL_INDEX file: inventory hash and quick_check (sampled checks UNCALIBRATED, not built)
        var lex = components.FirstOrDefault(c => (string)c["kind"]! == "LEXICAL_INDEX");
        if (lex is null) comps["LEXICAL_INDEX"] = "MISSING";
        else
        {
            bool ok = lex["files"]!.AsArray().Select(f => f!.AsObject()).All(f => File.Exists(Local(gdir, (string)f["path"]!)) && Sha(Local(gdir, (string)f["path"]!)) == (string)f["sha256"]!);
            var db = Path.Combine(gdir, "accelerators", "search-index", "search.sqlite");
            if (ok && File.Exists(db))
            {
                using var sc = new Microsoft.Data.Sqlite.SqliteConnection($"Data Source={db};Mode=ReadOnly;Pooling=False");
                sc.Open();
                using var q = sc.CreateCommand(); q.CommandText = "PRAGMA quick_check";
                ok = (string?)q.ExecuteScalar() == "ok";
            }
            comps["LEXICAL_INDEX"] = ok ? "VERIFIED" : "FAILED";
            if (!ok) issues.Add("LEXICAL_INDEX: file differs from the signed inventory or fails quick_check");
        }
        comps["VECTOR_PACK"] = components.Any(c => (string)c["kind"]! == "VECTOR_PACK") ? "NOT_VERIFIED_HERE" : "MISSING";
        Microsoft.Data.Sqlite.SqliteConnection.ClearAllPools();

        bool pass = issues.Count == 0 && comps.Values.All(v => v is "VERIFIED" or "REBUILT_LOCALLY" or "MISSING") && comps["KNOWLEDGE_ROWS"] == "VERIFIED";
        if (pass)
        {
            long bytes = Directory.EnumerateFiles(gdir, "*", SearchOption.AllDirectories).Sum(f => new FileInfo(f).Length);
            new GenerationCatalog(site).StageGeneration(generation, bytes);
            log?.Invoke($"staging: {generation} verified and staged ({GenerationCatalog.Marker})");
        }
        return new(generation, seq, pass, issues, comps, tables, origin, level);
    }
}
