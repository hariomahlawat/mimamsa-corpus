// C16 Stage 3 S3-B (B04): GRAPH verification of a prebuilt graph component against the verified generation.
//   GRAPH_DIGEST              GraphStore.Digest recomputed over the shipped row ids equals the declared result_digest;
//   GRAPH_STRUCTURAL_RECHECK  full pass over the shipped rows (mimamsa_contract.c16.verification.graph_structural_issues):
//                             unique ids, known kinds and types, every edge endpoint exists, every evidence page and held
//                             node resolves to a verified page of a served document, builder-only verification values;
//   SAMPLED_REBUILD_PARITY    a deterministic sample of SOURCE DOCUMENTS (stratified by document type, seeded by the
//                             release id) is rebuilt with the application's GraphBuilder (GraphBuilder.Build with a source
//                             filter, full cross-document context) and compared row for row, both ways: every rebuilt edge
//                             is shipped byte-identical, every shipped edge of a sampled (or source-less) document is
//                             rebuilt; held nodes of sampled documents and the non-held endpoints of rebuilt edges equal.
// The KNOWLEDGE_ROWS-style full re-derivation (`FullRebuildParity`) is kept for the calibration study and as the
// stronger check the loader runs today; see app/b1/evidence/c16_s3b/S3B_REPORT.md for the cost comparison.
using System.Diagnostics;
using System.Text;
using System.Text.Json.Nodes;
using Mimamsa.Core.Generation;
using Mimamsa.Core.Graph;
using Mimamsa.Core.Knowledge;

namespace Mimamsa.Core.ComponentVerification;

public static class GraphVerifier
{
    public static readonly string[] Required = ["GRAPH_DIGEST", "GRAPH_STRUCTURAL_RECHECK", "SAMPLED_REBUILD_PARITY"];
    public const string Check = "SAMPLED_REBUILD_PARITY";
    public const string NotRunInProduction = "UNCALIBRATED_IN_PRODUCTION: the contract sample is uncalibrated, so production never runs it (the outcome refuses)";
    static readonly HashSet<string> Kinds = [.. NodeKind.All];
    static readonly HashSet<string> Types = typeof(EdgeType).GetFields().Where(f => f.IsLiteral).Select(f => (string)f.GetRawConstantValue()!).ToHashSet(StringComparer.Ordinal);

    public sealed record Rows(IReadOnlyDictionary<string, (JsonObject Row, string Line)> Nodes, IReadOnlyDictionary<string, (JsonObject Row, string Line)> Edges, List<string> ParseIssues);

    public static Rows Parse(byte[] nodesFile, byte[] edgesFile)
    {
        var issues = new List<string>();
        Dictionary<string, (JsonObject, string)> Read(byte[] b, string what)
        {
            var d = new Dictionary<string, (JsonObject, string)>(StringComparer.Ordinal);
            foreach (var line in Encoding.UTF8.GetString(b).Split('\n'))
            {
                if (line.Length == 0) continue;
                JsonObject o;
                try { o = JsonNode.Parse(line)!.AsObject(); }
                catch (Exception e) when (e is System.Text.Json.JsonException or InvalidOperationException) { issues.Add($"GRAPH_ROW_UNPARSEABLE: {what}"); continue; }
                var id = (string?)o["id"] ?? "";
                if (!d.TryAdd(id, (o, line))) issues.Add($"GRAPH_DUPLICATE_{(what == "graph_nodes" ? "NODE" : "EDGE")}: {id}");
            }
            return d;
        }
        return new Rows(Read(nodesFile, "graph_nodes"), Read(edgesFile, "graph_edges"), issues);
    }

    static string? S(JsonNode? n) => n is JsonValue v && v.TryGetValue<string>(out var s) ? s : null;
    static int? I(JsonNode? n) => n is JsonValue v && v.TryGetValue<int>(out var i) ? i : null;
    static bool B(JsonNode? n) => n is JsonValue v && v.TryGetValue<bool>(out var b) && b;

    /// Digest over the shipped ids exactly as GraphStore.Digest / digests.graph_digest.
    public static string DigestOfRows(string builderVersion, IEnumerable<string> nodeIds, IEnumerable<string> edgeIds) =>
        GraphIds.Hash(builderVersion + "|" + string.Join(",", nodeIds.Order(StringComparer.Ordinal)) + "|" + string.Join(",", edgeIds.Order(StringComparer.Ordinal)));

    /// The reference structural issues (same codes as the Python reference).
    public static List<string> StructuralIssues(Rows r, GenerationStore g)
    {
        var outp = new List<string>(r.ParseIssues);
        bool PageOk(string doc, int page) => g.Documents.TryGetValue(doc, out var d) && d.Pages.ContainsKey(page);
        foreach (var (id, (n, _)) in r.Nodes)
        {
            if (!Kinds.Contains(S(n["kind"]) ?? "")) outp.Add($"GRAPH_UNKNOWN_KIND: {id}");
            var doc = S(n["doc_id"]); var page = I(n["page"]);
            if (doc is not null)
            {
                if (!g.Documents.ContainsKey(doc)) outp.Add($"GRAPH_NODE_DOC_UNRESOLVED: {id}");
                else if (page is { } p && !PageOk(doc, p)) outp.Add($"GRAPH_NODE_PAGE_UNRESOLVED: {id}");
            }
            else if (B(n["held"]) && S(n["kind"]) != NodeKind.ProceduralRequirement) outp.Add($"GRAPH_HELD_NODE_WITHOUT_DOCUMENT: {id}");
        }
        foreach (var (id, (e, _)) in r.Edges)
        {
            if (!Types.Contains(S(e["type"]) ?? "")) outp.Add($"GRAPH_UNKNOWN_TYPE: {id}");
            if (!r.Nodes.ContainsKey(S(e["from_id"]) ?? "") || !r.Nodes.ContainsKey(S(e["to_id"]) ?? "")) outp.Add($"GRAPH_DANGLING_EDGE: {id}");
            if (!Verification.BuilderValues.Contains(S(e["verification"])) || S(e["review_state"]) != GraphBuilder.ReviewUnreviewed) outp.Add($"GRAPH_NOT_BUILDER_VALUE: {id}");
            var doc = S(e["source_doc_id"]); var page = I(e["page"]);
            if (doc is not null)
            {
                if (!g.Documents.ContainsKey(doc)) outp.Add($"GRAPH_EVIDENCE_DOC_UNRESOLVED: {id}");
                else if (page is { } p && !PageOk(doc, p)) outp.Add($"GRAPH_EVIDENCE_PAGE_UNRESOLVED: {id}");
            }
        }
        return outp;
    }

    /// Canonical row lines of a (possibly filtered) built graph, by id, through the one B03 row mapping.
    static (Dictionary<string, string> Nodes, Dictionary<string, string> Edges) Lines(LegalGraph graph)
    {
        var src = new KnowledgeSources { Graph = graph };
        Dictionary<string, string> Map(string table) => Encoding.UTF8.GetString(KnowledgeRows.DeriveFile(table, src).Bytes).Split('\n')
            .Where(l => l.Length > 0).ToDictionary(l => (string)JsonNode.Parse(l)!["id"]!, l => l, StringComparer.Ordinal);
        return (Map("graph_nodes"), Map("graph_edges"));
    }

    /// Source documents of the generation by stratum (document type).
    public static Dictionary<string, List<string>> Strata(GenerationStore g) =>
        g.Documents.Values.GroupBy(d => d.DocType, StringComparer.Ordinal).ToDictionary(x => x.Key, x => x.Select(d => d.DocId).ToList(), StringComparer.Ordinal);

    /// SAMPLED_REBUILD_PARITY over the given source documents. Returns the parity issues (empty = parity).
    public static List<string> SampledParity(Rows shipped, GenerationStore g, IReadOnlyCollection<string> sampleDocs, out int comparedEdges, out int comparedNodes)
    {
        var inSample = new HashSet<string>(sampleDocs, StringComparer.Ordinal);
        bool Inc(string? doc) => doc is null || inSample.Contains(doc);
        var built = GraphBuilder.Build(g, Inc);
        var (bn, be) = Lines(built);
        var issues = new List<string>();
        comparedEdges = 0; comparedNodes = 0;
        foreach (var (id, line) in be)
        {
            comparedEdges++;
            if (!shipped.Edges.TryGetValue(id, out var s)) issues.Add($"GRAPH_PARITY_EDGE_MISSING: {id}");
            else if (s.Line != line) issues.Add($"GRAPH_PARITY_EDGE_DIFFERS: {id}");
        }
        foreach (var (id, (row, _)) in shipped.Edges)
            if (Inc(S(row["source_doc_id"])) && !be.ContainsKey(id)) issues.Add($"GRAPH_PARITY_EDGE_EXTRA: {id}");
        var builtNodes = built.Nodes.ToDictionary(n => n.Id, StringComparer.Ordinal);
        foreach (var n in built.Nodes.Where(n => n.Held && Inc(n.DocId)))
        {
            comparedNodes++;
            if (!shipped.Nodes.TryGetValue(n.Id, out var s)) issues.Add($"GRAPH_PARITY_NODE_MISSING: {n.Id}");
            else if (s.Line != bn[n.Id]) issues.Add($"GRAPH_PARITY_NODE_DIFFERS: {n.Id}");
        }
        foreach (var (id, (row, _)) in shipped.Nodes)
            if (B(row["held"]) && Inc(S(row["doc_id"])) && !(builtNodes.TryGetValue(id, out var bnode) && bnode.Held)) issues.Add($"GRAPH_PARITY_NODE_EXTRA: {id}");
        foreach (var id in built.Edges.SelectMany(e => new[] { e.From, e.To }).Distinct(StringComparer.Ordinal))
        {
            var n = builtNodes[id];
            if (n.Held && Inc(n.DocId)) continue;   // compared above
            if (!shipped.Nodes.TryGetValue(id, out var s)) { issues.Add($"GRAPH_PARITY_NODE_MISSING: {id}"); continue; }
            if (n.Held || B(s.Row["held"])) continue;   // a held variant from an unsampled source takes precedence in the full build
            comparedNodes++;
            if (s.Line != bn[id]) issues.Add($"GRAPH_PARITY_NODE_DIFFERS: {id}");
        }
        return issues;
    }

    /// The full rebuild (GraphBuilder over the whole generation) compared row for row: the stronger reference check.
    public static List<string> FullRebuildParity(Rows shipped, GenerationStore g)
    {
        var (bn, be) = Lines(GraphBuilder.Build(g));
        var issues = new List<string>();
        void Cmp(Dictionary<string, string> want, IReadOnlyDictionary<string, (JsonObject Row, string Line)> got, string what)
        {
            foreach (var (id, line) in want)
                if (!got.TryGetValue(id, out var s)) issues.Add($"GRAPH_PARITY_{what}_MISSING: {id}");
                else if (s.Line != line) issues.Add($"GRAPH_PARITY_{what}_DIFFERS: {id}");
            foreach (var id in got.Keys) if (!want.ContainsKey(id)) issues.Add($"GRAPH_PARITY_{what}_EXTRA: {id}");
        }
        Cmp(bn, shipped.Nodes, "NODE"); Cmp(be, shipped.Edges, "EDGE");
        return issues;
    }

    /// The three GRAPH checks. `sample` comes from B04Sampling.Effective (or an explicit study override).
    public static ComponentEvidence Verify(GenerationStore g, byte[] nodesFile, byte[] edgesFile, string declaredDigest, string builderVersion,
                                           string releaseId, EffectiveSample? sample)
    {
        var ev = new ComponentEvidence("GRAPH");
        var sw = Stopwatch.StartNew();
        var rows = Parse(nodesFile, edgesFile);
        if (builderVersion != GraphBuilder.Version) ev.Fail("GRAPH_DIGEST", $"graph builder version {builderVersion} is not this application's {GraphBuilder.Version}");
        else if (DigestOfRows(builderVersion, rows.Nodes.Keys, rows.Edges.Keys) != declaredDigest) ev.Fail("GRAPH_DIGEST", "GraphStore digest of the shipped rows differs from the declared result_digest");
        else ev.Pass("GRAPH_DIGEST");
        var structural = StructuralIssues(rows, g);
        if (structural.Count == 0) ev.Pass("GRAPH_STRUCTURAL_RECHECK");
        else foreach (var i in structural.Take(20)) ev.Fail("GRAPH_STRUCTURAL_RECHECK", i);
        ev.Facts["structural_issues"] = structural.Count;
        ev.TimingsMs["structural"] = sw.ElapsedMilliseconds;
        if (sample is null) { ev.NotRun(Check, NotRunInProduction); return ev; }
        sw.Restart();
        var strata = Strata(g);
        var docs = B04Sampling.Stratified(releaseId, Check, strata, sample.Size);
        var parity = SampledParity(rows, g, docs, out var ce, out var cn);
        ev.TimingsMs["sampled_rebuild"] = sw.ElapsedMilliseconds;
        if (parity.Count == 0) ev.Pass(Check);
        else foreach (var i in parity.Take(20)) ev.Fail(Check, i);
        var s = sample.ToJson();
        s["selection"] = "DETERMINISTIC_STRATIFIED_SEEDED_BY_RELEASE_ID"; s["unit"] = "source document"; s["population"] = g.Documents.Count;
        s["selected"] = docs.Count; s["compared_edges"] = ce; s["compared_nodes"] = cn; s["seed"] = releaseId;
        ev.Samples[Check] = s;
        ev.Facts["nodes"] = rows.Nodes.Count; ev.Facts["edges"] = rows.Edges.Count;
        return ev;
    }
}
