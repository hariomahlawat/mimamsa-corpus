// C15 WP3: builds the legal knowledge graph from the active generation. Deterministic (same generation -> same nodes,
// edges and edge ids), no downloads, no model calls. Sources and the verification each receives:
//   tables of contents (held Acts/Rules)        CONTAINS_PROVISION                       EXTRACTED_STRUCTURE
//   A4 provision versions (research aid)        VERSION_OF / OMITS / SUBSTITUTES / ...   CANDIDATE
//   A5 citation edges (judgments)               CITES_* / QUOTES_* / FOLLOWS / OVERRULES CANDIDATE
//   C14 correspondence tables (secondary)       RE_ENACTED_AS (never "interchangeable")  CANDIDATE
//   C14 repeal / savings notices (held text)    REPEALS_INSTRUMENT / SAVES_OR_TRANSITIONS CANDIDATE
//   C14 Commander task map                      PROCEDURE_REFERENCES_PROVISION           CURATED_NAVIGATION
// Forms and competent authorities are node/edge kinds of the model but are not populated: no held record extracts
// them yet, and they are never inferred.
using System.Text.RegularExpressions;
using Mimamsa.Core.Generation;

namespace Mimamsa.Core.Graph;

public static partial class GraphBuilder
{
    public const string Version = "c15-graph-1";
    public const string ReviewUnreviewed = "UNREVIEWED";

    [GeneratedRegex(@"^(?:(?<p>s|ss|r|rr|reg|rule|regulation|section)\.?\s*)(?<n>\d{1,3}[A-Z]{0,2})", RegexOptions.IgnoreCase)] private static partial Regex ProvRef();
    [GeneratedRegex(@"^PROV:(?<code>[^:]+):(?<p>[a-z]+)\.(?<n>.+)$")] private static partial Regex ProvNode();
    [GeneratedRegex(@"^JUD:JG-(?<sha>[0-9a-f]{12})$")] private static partial Regex JudNode();

    static string Trunc(string? s, int n) => s is null ? "" : s.Length > n ? s[..n] + "…" : s;

    public static LegalGraph Build(GenerationStore g)
    {
        var rel = g.Relations;
        var nodes = new Dictionary<string, GraphNode>(StringComparer.Ordinal);
        var edges = new Dictionary<string, GraphEdge>(StringComparer.Ordinal);
        var familyOfCode = new Dictionary<string, Statutes.Instrument>(StringComparer.Ordinal);

        void Node(GraphNode n) { if (!nodes.TryGetValue(n.Id, out var cur) || (n.Held && !cur.Held)) nodes[n.Id] = n; }
        void Edge(string type, string from, string to, string origin, DocumentRecord? src, string? sha, int? page, string? quote,
                  string? tFrom, string tFromStatus, string? tTo, string tToStatus, string verification, string uncertainty, bool legalEffect)
        {
            var q = quote is null ? null : Trunc(Regex.Replace(quote, @"\s+", " ").Trim(), 400);
            var id = GraphIds.EdgeId(type, from, to, origin, src?.DocId, page, q);
            edges.TryAdd(id, new GraphEdge(id, type, from, to, origin, src?.DocId, sha ?? src?.CopySha, page, q, tFrom, tFromStatus, tTo, tToStatus,
                verification, ReviewUnreviewed, uncertainty, legalEffect));
        }
        string EnsureProvision(string code, string prefix, string section)
        {
            var id = GraphIds.Provision(code, prefix, section);
            if (!nodes.ContainsKey(id))
            {
                // provision not located in a held table of contents: kept as a reference node; when its instrument is held the
                // node still names that instrument's document, so withdrawal of the instrument hides it too
                var inst = familyOfCode.GetValueOrDefault(code);
                var doc = inst is null ? null : g.Documents.GetValueOrDefault(inst.PrimaryDocId);
                Node(new GraphNode(id, NodeKind.Provision, $"{code} {prefix}.{GraphIds.BaseSection(section)}", doc?.DocId, doc?.CopySha, false, null, inst?.Key, code));
            }
            return id;
        }

        // 1. instruments and their provisions (tables of contents of the primary edition)
        foreach (var inst in rel.Instruments)
        {
            if (!g.Documents.TryGetValue(inst.PrimaryDocId, out var primary)) continue;
            var code = GraphIds.InstrumentCode(inst.PrimaryDocId);
            familyOfCode[code] = inst;
            Node(new GraphNode(GraphIds.Instrument(inst.Key), NodeKind.Instrument, inst.Title, primary.DocId, primary.CopySha, true, null, inst.Key, code));
        }
        foreach (var inst in rel.Instruments)
        {
            if (!g.Documents.TryGetValue(inst.PrimaryDocId, out var primary) || primary.DocType is not ("act" or "rules" or "regulations")) continue;
            var code = GraphIds.InstrumentCode(inst.PrimaryDocId); var prefix = GraphIds.Prefix(primary.DocType);
            foreach (var e in Toc.Build(primary))
            {
                var id = GraphIds.Provision(code, prefix, e.Number);
                if (nodes.TryGetValue(id, out var existing) && existing.Held) continue;
                Node(new GraphNode(id, NodeKind.Provision, $"{prefix}.{GraphIds.BaseSection(e.Number)} {e.Heading}", primary.DocId, primary.CopySha, true, e.Page, inst.Key, code));
                Edge(EdgeType.Contains, GraphIds.Instrument(inst.Key), id, "TOC", primary, null, e.Page, e.Heading, null, "NOT_APPLICABLE", null, "NOT_APPLICABLE",
                    Verification.ExtractedStructure, e.Omitted ? "Heading as printed in the held compilation, which prints this provision as omitted; structure only."
                        : "Heading as printed in the held compilation; structure only.", false);
            }
        }

        // 2. A4 provision versions (research aid): one version node, linked to its provision by the version kind
        foreach (var v in g.ProvisionVersions)
        {
            var code = GraphIds.CodeFromA4Family(v.Family);
            var m = ProvRef().Match(v.Provision.Trim());
            string provId;
            if (m.Success)
            {
                var p = m.Groups["p"].Value.ToLowerInvariant();
                provId = EnsureProvision(code, p is "r" or "rr" or "rule" ? "r" : p is "reg" or "regulation" ? "reg" : "s", m.Groups["n"].Value);
            }
            else provId = EnsureProvision(code, "part", Regex.Replace(v.Provision.Trim(), @"\s+", "-"));
            var ev = v.Evidence.FirstOrDefault(x => x.DocId is not null && g.Documents.ContainsKey(x.DocId));
            var evDoc = ev?.DocId is { } did ? g.Documents[did] : null;
            var instDoc = familyOfCode.GetValueOrDefault(code) is { } fi ? g.Documents.GetValueOrDefault(fi.PrimaryDocId) : null;
            var verDoc = evDoc ?? instDoc;
            var verId = GraphIds.Version(v.VersionId);
            Node(new GraphNode(verId, NodeKind.ProvisionVersion, $"{v.VersionId} ({v.VersionKind.Replace('_', ' ')})", verDoc?.DocId, verDoc?.CopySha, evDoc is not null, ev?.Page, familyOfCode.GetValueOrDefault(code)?.Key, code));
            var type = v.VersionKind switch
            {
                "omission" => EdgeType.Omits, "substitution" => EdgeType.Substitutes, "insertion" => EdgeType.Inserts,
                "amendment_words" => EdgeType.Amends, "repeal" or "repeal_with_savings" => EdgeType.RepealsProvision, "commencement" => EdgeType.Commences,
                _ => EdgeType.VersionOf,
            };
            Edge(type, verId, provId, "A4", verDoc, ev?.Sha, ev?.Page, v.ChangeSummary, v.EffectiveFromDate ?? v.ReportedDate, v.EffectiveFromStatus ?? "NOT_RECORDED",
                null, v.EffectiveToStatus ?? "NOT_RECORDED", Verification.Candidate,
                $"A4 automated provision-version candidate ({v.DeterminationState}); temporal chain not established.", type != EdgeType.VersionOf);
        }

        // 3. judgments and A5 citation / treatment candidates
        var docBySha12 = g.Documents.Values.GroupBy(d => d.CopySha[..12]).ToDictionary(x => x.Key, x => x.First().DocId);
        foreach (var d in g.Documents.Values.Where(d => d.DocType == "judgment"))
            Node(new GraphNode(GraphIds.Judgment(d.DocId), NodeKind.Judgment, d.Title ?? d.DocId, d.DocId, d.CopySha, true, null, null, null));
        foreach (var d in g.Documents.Values)
            foreach (var c in d.Candidates.Where(c => c.Type == "graph_edge"))
            {
                var relation = c.Payload["relation"]?.GetValue<string>();
                if (relation is null) continue;
                var from = d.DocType == "judgment" ? GraphIds.Judgment(d.DocId) : GraphIds.Instrument(rel.FamilyOfDoc.GetValueOrDefault(d.DocId) ?? "doc:" + d.DocId);
                if (!nodes.ContainsKey(from)) Node(new GraphNode(from, d.DocType == "judgment" ? NodeKind.Judgment : NodeKind.Instrument, d.Title ?? d.DocId, d.DocId, d.CopySha, true, null, null, null));
                var target = c.Payload["target"]?["node_id"]?.GetValue<string>();
                string to;
                if (target is not null && ProvNode().Match(target) is { Success: true } pm) to = EnsureProvision(pm.Groups["code"].Value, pm.Groups["p"].Value, pm.Groups["n"].Value);
                else if (target is not null && JudNode().Match(target) is { Success: true } jm)
                {
                    if (docBySha12.TryGetValue(jm.Groups["sha"].Value, out var tdoc) && g.Documents[tdoc].DocType == "judgment") to = GraphIds.Judgment(tdoc);
                    else { to = target; Node(new GraphNode(to, NodeKind.Judgment, "Judgment not held in this library", null, null, false, null, null, null)); }
                }
                else
                {
                    var raw = c.Payload["target"]?["raw_reference"]?.GetValue<string>() ?? target ?? "unresolved";
                    to = GraphIds.Reference(raw);
                    Node(new GraphNode(to, NodeKind.UnresolvedReference, Trunc(raw, 160), null, null, false, null, null, null));
                }
                var a = c.Anchors.FirstOrDefault();
                bool legal = c.Payload["has_legal_effect"]?.GetValue<bool>() ?? false;
                Edge(relation, from, to, "A5", d, a?.CopySha, a?.Page, a?.Quote, d.IssueDate, "AS_OF_SOURCE_DATE", null, "NOT_APPLICABLE", Verification.Candidate,
                    relation is EdgeType.CitesJudgment or EdgeType.CitesProvision or EdgeType.QuotesProvision
                        ? "A5 extracted citation candidate; a citation does not establish how the source treated the target."
                        : "A5 treatment candidate; requires legal review before any reliance.", legal);
            }

        // 4. C14 correspondence (secondary comparison tables): old provision RE_ENACTED_AS new provision
        foreach (var ce in rel.Edges)
        {
            if (ce.OldBases.Count == 0) continue;
            var oldInst = rel.Family(ce.OldFamily); var newInst = rel.Family(ce.NewFamily);
            if (oldInst is null || newInst is null || !g.Documents.TryGetValue(ce.TableDocId, out var table)) continue;
            var newProv = EnsureProvision(GraphIds.InstrumentCode(newInst.PrimaryDocId), "s", ce.NewBase);
            foreach (var ob in ce.OldBases)
                Edge(EdgeType.ReEnactedAs, EnsureProvision(GraphIds.InstrumentCode(oldInst.PrimaryDocId), "s", ob), newProv, "C14_CORRESPONDENCE", table, null, ce.Page,
                    ce.RowText, null, "NOT_DETERMINED", null, "NOT_DETERMINED", Verification.Candidate, Statutes.StatuteRelations.Caution, true);
        }

        // 5. C14 repeal and savings notices quoting held text: new instrument -> old instrument
        foreach (var (fam, list) in rel.Notices)
            foreach (var n in list.Where(n => n.Evidence is not null && n.Kind is "repealed_by" or "savings_transitional"))
            {
                if (!rel.FamilyOfDoc.TryGetValue(n.Evidence!.DocId, out var newFam) || newFam == fam || !g.Documents.TryGetValue(n.Evidence.DocId, out var src)) continue;
                Edge(n.Kind == "repealed_by" ? EdgeType.RepealsInstrument : EdgeType.SavesOrTransitions, GraphIds.Instrument(newFam), GraphIds.Instrument(fam),
                    "C14_NOTICE", src, null, n.Evidence.Page, n.Evidence.Quote, null, "NOT_DETERMINED", null, "NOT_DETERMINED", Verification.Candidate,
                    "Quoted from held text; commencement is not established from a held notification, and the effect on a particular matter is not determined.", true);
            }

        // 6. C14 Commander task map (navigation aid, never a legal requirement)
        foreach (var t in rel.CommanderTasks)
        {
            var pid = GraphIds.Procedure(t.Task);
            Node(new GraphNode(pid, NodeKind.ProceduralRequirement, t.Task, null, null, true, null, null, null));
            foreach (var it in t.Items)
            {
                var inst = rel.Family(it.Family) ?? (it.Family.StartsWith("doc:", StringComparison.Ordinal) ? rel.Instruments.FirstOrDefault(i => i.PrimaryDocId == it.Family[4..]) : null);
                if (inst is null) continue;
                var prov = EnsureProvision(GraphIds.InstrumentCode(inst.PrimaryDocId), it.Kind == "Rule" ? "r" : "s", it.Number);
                var src = it.DocId is not null ? g.Documents.GetValueOrDefault(it.DocId) : null;
                Edge(EdgeType.ProcedureReferencesProvision, pid, prov, "C14_COMMANDER_TASK", src, null, it.Page, it.Heading, null, "NOT_APPLICABLE", null, "NOT_APPLICABLE",
                    Verification.CuratedNavigation, "Navigation aid chosen for unit commanders; not a statement of a legal requirement or of what applies.", false);
            }
        }

        return new LegalGraph(g.GenerationId, Version, nodes.Values.OrderBy(n => n.Id, StringComparer.Ordinal).ToList(),
                              edges.Values.OrderBy(e => e.Id, StringComparer.Ordinal).ToList());
    }
}
