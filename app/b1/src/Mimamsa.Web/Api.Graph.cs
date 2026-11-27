// C15 WP3/WP4: read-only graph and research-assessment routes (contract: docs/architecture/b1/C15_GRAPH_API.md).
// Every route needs a session; responses are no-store (global middleware) and logs are content-free (route templates
// only). Eligibility is applied on every request: the set of documents that are not visible now (withdrawn, ineligible)
// is passed to every query, so a withdrawal takes effect at once on nodes, edges, paths, statistics and assessments.
// Node copy hashes are never returned (review F02); quotations are returned only where the source permits quoting.
using Mimamsa.Core.Graph;
using Mimamsa.Core.Reasoning;

namespace Mimamsa.Web;

public static partial class Api
{
    static string[] HiddenDocs(AppServices s) => s.Generation.Documents.Keys.Where(d => s.VisibleDocument(d) is null).ToArray();

    static object NodeDto(GraphNode n) => new { id = n.Id, kind = n.Kind, label = n.Label, doc_id = n.DocId, held = n.Held, page = n.Page, family = n.Family, code = n.Code };

    static object EdgeDto(EdgeView v, AppServices s) => new
    {
        id = v.Edge.Id, type = v.Edge.Type, from = NodeDto(v.FromNode), to = NodeDto(v.ToNode), origin = v.Edge.Origin,
        source = v.Edge.SourceDocId is { } sd ? new { doc_id = sd, page = v.Edge.Page } : null,
        quote = v.Edge.SourceDocId is { } q && s.VisibleDocument(q)?.QuotingPermitted == true ? v.Edge.Quote : null,
        temporal = new { from = v.Edge.TemporalFrom, from_status = v.Edge.TemporalFromStatus, to = v.Edge.TemporalTo, to_status = v.Edge.TemporalToStatus },
        verification = v.Edge.Verification, review_state = v.Edge.ReviewState, uncertainty = v.Edge.Uncertainty, has_legal_effect = v.Edge.HasLegalEffect,
        label = v.Edge.Verification == Verification.Candidate ? "Candidate (automated, not verified)" : v.Edge.Verification == Verification.CuratedNavigation ? "Navigation aid (not a legal requirement)" : "Structure read from the held text",
    };

    static IResult NotPublished() => Json(new { state = "unavailable", notice = "The legal knowledge graph is not available in this installation." }, 503);

    static void MapGraph(WebApplication app)
    {
        app.MapGet("/api/graph/stats", async (HttpContext ctx, AppServices s) =>
        {
            if (await User(ctx, s) is null) return Json(new { error = "auth" }, 401);
            if (s.GraphDb is null || s.Graph is null) return NotPublished();
            try
            {
                var st = await s.GraphDb.StatsAsync(s.Graph.GenerationId, HiddenDocs(s));
                return Json(new { generation = s.Graph.GenerationId, builder = s.Graph.BuilderVersion, nodes = st.Nodes, edges = st.Edges,
                    nodes_by_kind = st.NodesByKind, edges_by_type = st.EdgesByType, edges_by_verification = st.EdgesByVerification,
                    auth_ledger_version = s.Generation.Release.AuthLedgerVersion,
                    notice = "Every relationship is a candidate, structure read from held text, or a navigation aid. None is a verified legal fact." });
            }
            catch (GraphNotPublishedException) { return NotPublished(); }
        });

        // Resolve a provision (doc + section) or a document to its node id.
        app.MapGet("/api/graph/resolve", async (HttpContext ctx, string doc, string? section, AppServices s) =>
        {
            if (await User(ctx, s) is null) return Json(new { error = "auth" }, 401);
            if (s.Graph is null) return NotPublished();
            var d = s.VisibleDocument(doc);
            if (d is null) return Json(new { state = "unavailable", notice = NotAvailable }, 404);
            string id;
            if (d.DocType == "judgment") id = GraphIds.Judgment(d.DocId);
            else
            {
                var inst = s.Generation.Relations.InstrumentOf(d.DocId);
                if (inst is null) return Json(new { state = "not_in_graph" }, 404);
                id = section is { Length: > 0 }
                    ? GraphIds.Provision(GraphIds.InstrumentCode(inst.PrimaryDocId), GraphIds.Prefix(s.Generation.Documents[inst.PrimaryDocId].DocType), section)
                    : GraphIds.Instrument(inst.Key);
            }
            return Json(new { node_id = id });
        });

        app.MapGet("/api/graph/node", async (HttpContext ctx, string id, int? depth, int? limit, AppServices s) =>
        {
            if (await User(ctx, s) is null) return Json(new { error = "auth" }, 401);
            if (s.GraphDb is null || s.Graph is null) return NotPublished();
            try
            {
                var (node, edges, truncated) = await s.GraphDb.NeighbourhoodAsync(s.Graph.GenerationId, id, depth ?? 1, HiddenDocs(s), limit ?? 300);
                if (node is null) return Json(new { state = "unavailable", notice = "This item is not available in this installation." }, 404);
                return Json(new { node = NodeDto(node), edges = edges.Select(e => EdgeDto(e, s)), truncated, depth = Math.Clamp(depth ?? 1, 1, 2),
                    absence = "Absence of a relationship here is not evidence that none exists, nor that there is no adverse authority." });
            }
            catch (GraphNotPublishedException) { return NotPublished(); }
        });

        app.MapGet("/api/graph/path", async (HttpContext ctx, string from, string to, int? max_depth, AppServices s) =>
        {
            if (await User(ctx, s) is null) return Json(new { error = "auth" }, 401);
            if (s.GraphDb is null || s.Graph is null) return NotPublished();
            try
            {
                var p = await s.GraphDb.PathAsync(s.Graph.GenerationId, from, to, max_depth ?? 3, HiddenDocs(s));
                return Json(p is null
                    ? new { found = false, max_depth = Math.Clamp(max_depth ?? 3, 1, GraphStore.MaxDepth), nodes = (object)Array.Empty<string>(), edges = (object)Array.Empty<object>(),
                            notice = "No connection of that length through available records. A path is navigation, not a legal relationship." }
                    : new { found = true, max_depth = Math.Clamp(max_depth ?? 3, 1, GraphStore.MaxDepth), nodes = (object)p.Nodes, edges = (object)p.Edges.Select(e => EdgeDto(e, s)).ToList(),
                            notice = "A path is navigation through candidate records, not a legal relationship." });
            }
            catch (GraphNotPublishedException) { return NotPublished(); }
        });

        // WP4: research-only evidence assessment. kind = temporal | succession | procedure | conflicts.
        app.MapGet("/api/reasoning/assess", async (HttpContext ctx, string kind, string? doc, string? section, string? task, string? as_of,
                                                   string? conduct_date, string? proceeding_date, AppServices s) =>
        {
            if (await User(ctx, s) is null) return Json(new { error = "auth" }, 401);
            if (s.Graph is null) return NotPublished();
            static DateOnly? D(string? v) => DateOnly.TryParse(v, out var d) ? d : null;
            var a = new EvidenceAssessor(s.Generation, s.Graph, id => s.VisibleDocument(id) is not null);
            if (kind == "procedure") return task is null ? Json(new { error = "task is required" }, 400) : Json(a.Procedure(task));
            if (doc is null || section is null) return Json(new { error = "doc and section are required" }, 400);
            var d = s.VisibleDocument(doc);
            var inst = d is null ? null : s.Generation.Relations.InstrumentOf(d.DocId);
            if (d is null || inst is null) return Json(new { state = "unavailable", notice = NotAvailable }, 404);
            var code = GraphIds.InstrumentCode(inst.PrimaryDocId); var prefix = GraphIds.Prefix(s.Generation.Documents[inst.PrimaryDocId].DocType);
            return kind switch
            {
                "temporal" => Json(a.Temporal(code, prefix, section, D(as_of))),
                "succession" => Json(a.Succession(code, prefix, section, D(conduct_date), D(proceeding_date))),
                "conflicts" => Json(a.Conflicts(code, prefix, section)),
                _ => Json(new { error = "kind must be temporal, succession, procedure or conflicts" }, 400),
            };
        });

        app.MapGet("/api/reasoning/rule-gate", async (HttpContext ctx, AppServices s) =>
        {
            if (await User(ctx, s) is null) return Json(new { error = "auth" }, 401);
            var gate = RuleGate.Decide(s.Generation.Release.AuthLedgerVersion, approvedGrantCoversExactScope: false);
            return Json(new { evaluation_admitted = gate.EvaluationAdmitted, delivery_authorized = gate.DeliveryAuthorized, blockers = gate.Blockers,
                rule_packs_installed = 0, auth_ledger_version = s.Generation.Release.AuthLedgerVersion });
        });
    }
}
