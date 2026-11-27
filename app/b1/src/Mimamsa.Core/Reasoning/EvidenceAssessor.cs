// C15 WP4: research-only evidence assessment. It reports, for a question about a provision or a task, what the HELD
// evidence shows and what is missing, each finding in one of three explicit states:
//   ESTABLISHED               only when every supporting record is legally reviewed AND AUTH-LEDGER is above v0;
//                             at v0 nothing in this installation can be established, and the result says so;
//   CANDIDATE                 automated or unverified records, quoted with their evidence;
//   INSUFFICIENT_INFORMATION  a needed fact, date, notification or record is missing, or held records conflict.
// It never decides which law applies, never produces advice, and never invokes a rule pack (that path is gated in
// RuleEngine and is closed at v0). Ineligible (withdrawn) documents are excluded from every finding.
using Mimamsa.Core.Generation;
using Mimamsa.Core.Graph;
using Mimamsa.Core.Statutes;

namespace Mimamsa.Core.Reasoning;

[System.Text.Json.Serialization.JsonConverter(typeof(System.Text.Json.Serialization.JsonStringEnumConverter<EvidenceState>))]
public enum EvidenceState { ESTABLISHED, CANDIDATE, INSUFFICIENT_INFORMATION }

public sealed record EvidenceLink(string DocId, int? Page, string? Quote, string? EdgeId, string Verification, string Origin);
public sealed record Finding(string Code, string Statement, EvidenceState State, IReadOnlyList<EvidenceLink> Evidence, string Basis);
public sealed record Assessment(string Kind, string Subject, IReadOnlyDictionary<string, string?> Inputs, EvidenceState Overall,
    IReadOnlyList<Finding> Findings, IReadOnlyList<string> MissingFacts, IReadOnlyList<string> Blockers, string Notice, int AuthLedgerVersion);

public sealed class EvidenceAssessor(GenerationStore g, LegalGraph graph, Func<string, bool> visible)
{
    public const string Notice = "Research aid derived from held records. It states what the held evidence shows and what is missing; it is not legal " +
        "advice and does not determine what applies to any matter.";
    public const string LedgerBlocker = "AUTH-LEDGER is at version 0: no source or relationship in this installation is legally verified, so no finding can be ESTABLISHED.";
    public static readonly DateOnly SecondarySourceDate = new(2024, 7, 1);

    // The graph is immutable for a generation, so its lookups are built once per graph and shared by every request.
    sealed record Index(Dictionary<string, GraphNode> Nodes, ILookup<string, GraphEdge> In, ILookup<string, GraphEdge> Out);
    static readonly System.Runtime.CompilerServices.ConditionalWeakTable<LegalGraph, Index> Indexes = new();
    readonly Index _ix = Indexes.GetValue(graph, gr => new Index(gr.Nodes.ToDictionary(n => n.Id), gr.Edges.ToLookup(e => e.To), gr.Edges.ToLookup(e => e.From)));
    Dictionary<string, GraphNode> _nodes => _ix.Nodes;
    ILookup<string, GraphEdge> _in => _ix.In;
    ILookup<string, GraphEdge> _out => _ix.Out;
    int Ledger => g.Release.AuthLedgerVersion;

    bool NodeVisible(GraphNode n) => n.DocId is null || visible(n.DocId);
    bool EdgeVisible(GraphEdge e) => (e.SourceDocId is null || visible(e.SourceDocId))
        && _nodes.TryGetValue(e.From, out var a) && NodeVisible(a) && _nodes.TryGetValue(e.To, out var b) && NodeVisible(b);
    static EvidenceLink Link(GraphEdge e) => new(e.SourceDocId ?? "", e.Page, e.Quote, e.Id, e.Verification, e.Origin);

    /// A finding backed by records is ESTABLISHED only if all are legally reviewed and the ledger is above v0.
    EvidenceState Backed(IEnumerable<EvidenceLink> ev) =>
        Ledger > 0 && ev.Any() && ev.All(x => x.Verification == Verification.LegalReviewed) ? EvidenceState.ESTABLISHED : EvidenceState.CANDIDATE;

    Assessment Result(string kind, string subject, Dictionary<string, string?> inputs, List<Finding> f, List<string> missing, List<string> blockers)
    {
        if (Ledger <= 0 && !blockers.Contains(LedgerBlocker)) blockers.Insert(0, LedgerBlocker);
        var overall = missing.Count > 0 || f.Any(x => x.State == EvidenceState.INSUFFICIENT_INFORMATION) ? EvidenceState.INSUFFICIENT_INFORMATION
            : f.Any(x => x.State == EvidenceState.CANDIDATE) || f.Count == 0 ? (f.Count == 0 ? EvidenceState.INSUFFICIENT_INFORMATION : EvidenceState.CANDIDATE)
            : EvidenceState.ESTABLISHED;
        return new Assessment(kind, subject, inputs, overall, f, missing, blockers, Notice, Ledger);
    }

    Assessment Unavailable(string kind, string subject, Dictionary<string, string?> inputs) =>
        Result(kind, subject, inputs, new() { new Finding("not_available", "This provision or instrument is not available in this installation.",
            EvidenceState.INSUFFICIENT_INFORMATION, Array.Empty<EvidenceLink>(), "No eligible held record.") }, new(), new());

    public GraphNode? ProvisionNode(string code, string prefix, string section) =>
        _nodes.GetValueOrDefault(GraphIds.Provision(code, prefix, section)) is { } n && NodeVisible(n) ? n : null;

    // ------------------------------------------------------------------ temporal applicability
    public Assessment Temporal(string code, string prefix, string section, DateOnly? asOf)
    {
        var inputs = new Dictionary<string, string?> { ["provision"] = GraphIds.Provision(code, prefix, section), ["as_of"] = asOf?.ToString("yyyy-MM-dd") };
        var node = ProvisionNode(code, prefix, section);
        if (node is null) return Unavailable("temporal", inputs["provision"]!, inputs);
        var f = new List<Finding>(); var missing = new List<string>(); var blockers = new List<string>();
        if (asOf is null) missing.Add("as_of_date: the date for which the provision's text is wanted (for example the date of the act or of the proceeding)");
        foreach (var c in _in[node.Id].Where(e => e.Type == EdgeType.Contains && EdgeVisible(e) && e.Uncertainty.Contains("omitted", StringComparison.Ordinal)))
            f.Add(new Finding("printed_as_omitted", "The held compilation prints this provision as omitted.", Backed(new[] { Link(c) }), new[] { Link(c) },
                "Heading as printed in the held compilation (a compilation is not the amending instrument)."));
        var versions = _in[node.Id].Where(e => e.From.StartsWith("VER:", StringComparison.Ordinal) && EdgeVisible(e)).OrderBy(e => e.From, StringComparer.Ordinal).ToList();
        foreach (var v in versions)
            f.Add(new Finding("version_record", $"{_nodes[v.From].Label}: {v.Type.Replace('_', ' ').ToLowerInvariant()}; effective from {v.TemporalFromStatus}" +
                $"{(v.TemporalFrom is null ? "" : $" ({v.TemporalFrom})")}; effective to {v.TemporalToStatus}.", Backed(new[] { Link(v) }), new[] { Link(v) }, v.Uncertainty));
        if (versions.Count == 0)
            f.Add(new Finding("no_version_record", "No provision-version record is held for this provision, so its text cannot be placed in time.",
                EvidenceState.INSUFFICIENT_INFORMATION, Array.Empty<EvidenceLink>(), "Absence of a held version record."));
        else if (asOf is { } d)
        {
            var covering = versions.Where(v => DateOnly.TryParse(v.TemporalFrom, out var from) && from <= d && v.TemporalToStatus is "OPEN" or "IN_FORCE" or "CURRENT").ToList();
            if (covering.Count == 1)
                f.Add(new Finding("version_interval_covers_date", $"Only {_nodes[covering[0].From].Label} has a recorded interval that covers {d:yyyy-MM-dd}.",
                    Backed(new[] { Link(covering[0]) }), new[] { Link(covering[0]) }, "Recorded effective interval of an automated version candidate."));
            else
                f.Add(new Finding("version_for_date_not_determined", $"Which version applied on {d:yyyy-MM-dd} cannot be determined from held records: the effective dates are not established.",
                    EvidenceState.INSUFFICIENT_INFORMATION, versions.Select(Link).ToList(), "Effective-from or effective-to dates are not recorded as established for the held versions."));
        }
        return Result("temporal", node.Id, inputs, f, missing, blockers);
    }

    // ------------------------------------------------------------------ commencement, repeal, savings and correspondence
    public Assessment Succession(string code, string prefix, string section, DateOnly? conductDate, DateOnly? proceedingDate)
    {
        var inputs = new Dictionary<string, string?> { ["provision"] = GraphIds.Provision(code, prefix, section),
            ["conduct_date"] = conductDate?.ToString("yyyy-MM-dd"), ["proceeding_date"] = proceedingDate?.ToString("yyyy-MM-dd") };
        var node = ProvisionNode(code, prefix, section);
        if (node is null) return Unavailable("succession", inputs["provision"]!, inputs);
        var f = new List<Finding>(); var missing = new List<string>();
        var blockers = new List<string> { "Which law governs a matter depends on commencement and on the repeal and savings provisions; neither is evaluated here (no approved rule pack)." };
        if (conductDate is null) missing.Add("conduct_date: the date of the act or omission (substantive law)");
        if (proceedingDate is null) missing.Add("proceeding_date: the date the proceeding was or will be started (procedure may follow a different date)");

        var families = new HashSet<string>(StringComparer.Ordinal);
        if (node.Family is not null) families.Add(node.Family);
        foreach (var e in _out[node.Id].Concat(_in[node.Id]).Where(e => e.Type == EdgeType.ReEnactedAs && EdgeVisible(e)))
        {
            var other = _nodes[e.From == node.Id ? e.To : e.From];
            if (other.Family is not null) families.Add(other.Family);
            f.Add(new Finding("correspondence", e.From == node.Id
                    ? $"A held comparison table lists {other.Label} as corresponding to this provision."
                    : $"A held comparison table lists this provision as corresponding to {other.Label}.",
                Backed(new[] { Link(e) }), new[] { Link(e) }, StatuteRelations.Caution));
        }
        bool secondaryDateSeen = false;
        foreach (var fam in families)
            foreach (var n in g.Relations.Notices.GetValueOrDefault(fam) ?? new())
            {
                if (n.Evidence is { } ev && !visible(ev.DocId)) continue;
                var link = n.Evidence is { } e2 ? new[] { new EvidenceLink(e2.DocId, e2.Page, e2.Quote, null, Verification.Candidate, "C14_NOTICE") } : Array.Empty<EvidenceLink>();
                var name = g.Relations.Family(fam)?.Title ?? fam;
                switch (n.Kind)
                {
                    case "commencement_notification_not_held":
                        f.Add(new Finding("commencement_not_established", $"{name}: no commencement notification is held; the commencement date is not established from primary text.",
                            EvidenceState.INSUFFICIENT_INFORMATION, link, n.Basis));
                        break;
                    case "commencement_secondary_source":
                        secondaryDateSeen = true;
                        f.Add(new Finding("commencement_secondary_source", $"{name}: {n.Text}", Backed(link), link, n.Basis));
                        break;
                    default:
                        f.Add(new Finding(n.Kind, $"{name}: {n.Title}. {n.Text}", Backed(link), link, n.Basis));
                        break;
                }
            }
        if (conductDate is { } cd && secondaryDateSeen)
            f.Add(new Finding("conduct_date_vs_secondary_date",
                $"The conduct date {cd:yyyy-MM-dd} is {(cd < SecondarySourceDate ? "before" : "on or after")} 1 July 2024, the date stated in a held secondary source. " +
                "That date is not established from a held commencement notification.", EvidenceState.CANDIDATE, Array.Empty<EvidenceLink>(),
                "Comparison with a date read from a secondary source only."));
        return Result("succession", node.Id, inputs, f, missing, blockers);
    }

    // ------------------------------------------------------------------ procedural prerequisites, competent authority, safeguards
    public Assessment Procedure(string task)
    {
        var inputs = new Dictionary<string, string?> { ["task"] = task };
        var t = g.Relations.CommanderTasks.FirstOrDefault(x => string.Equals(x.Task, task, StringComparison.OrdinalIgnoreCase));
        var f = new List<Finding>(); var missing = new List<string>();
        if (t is null) return Result("procedure", task, inputs, new() { new Finding("unknown_task", "No such task is defined.", EvidenceState.INSUFFICIENT_INFORMATION, Array.Empty<EvidenceLink>(), "") }, missing, new());
        var pid = GraphIds.Procedure(t.Task);
        foreach (var e in _out[pid].Where(e => e.Type == EdgeType.ProcedureReferencesProvision))
        {
            var p = _nodes[e.To];
            if (!EdgeVisible(e)) { f.Add(new Finding("provision_not_available", $"{p.Code} {p.Label.Split(' ')[0]}: not available in this installation.", EvidenceState.INSUFFICIENT_INFORMATION, Array.Empty<EvidenceLink>(), "Source withdrawn or ineligible.")); continue; }
            f.Add(p.Held
                ? new Finding("referenced_provision", $"{p.Label} (heading as printed).", EvidenceState.CANDIDATE, new[] { Link(e) }, e.Uncertainty)
                : new Finding("referenced_provision_not_found", $"{p.Label}: not found in the held copy.", EvidenceState.INSUFFICIENT_INFORMATION, Array.Empty<EvidenceLink>(), "Not located in the held table of contents."));
        }
        var gate = RuleGate.Decide(Ledger, approvedGrantCoversExactScope: false);
        foreach (var (code, what) in new[] { ("procedural_prerequisites", "Procedural prerequisites"), ("competent_authority", "Competent authority"), ("mandatory_safeguards", "Mandatory safeguards") })
            f.Add(new Finding(code, $"{what}: not evaluated. No approved rule pack encodes them and no competent-authority record is extracted from the held texts.",
                EvidenceState.INSUFFICIENT_INFORMATION, Array.Empty<EvidenceLink>(), "Rule gate closed: " + string.Join(" ", gate.Blockers)));
        missing.Add("the facts of the matter (who, what, when, status of the person, stage of the proceeding)");
        return Result("procedure", t.Task, inputs, f, missing, gate.Blockers.ToList());
    }

    // ------------------------------------------------------------------ conflicting and unresolved records
    public Assessment Conflicts(string code, string prefix, string section)
    {
        var inputs = new Dictionary<string, string?> { ["provision"] = GraphIds.Provision(code, prefix, section) };
        var node = ProvisionNode(code, prefix, section);
        if (node is null) return Unavailable("conflicts", inputs["provision"]!, inputs);
        var f = new List<Finding>();
        var printedOmitted = _in[node.Id].Where(e => e.Type == EdgeType.Contains && EdgeVisible(e) && e.Uncertainty.Contains("omitted", StringComparison.Ordinal)).ToList();
        var versions = _in[node.Id].Where(e => e.From.StartsWith("VER:", StringComparison.Ordinal) && EdgeVisible(e)).ToList();
        var ending = versions.Where(v => v.Type is EdgeType.Omits or EdgeType.RepealsProvision).ToList();
        if (printedOmitted.Count > 0 && ending.Count == 0)
            f.Add(new Finding("omission_without_version_record", "The held compilation prints this provision as omitted, but no held version record describes the omission.",
                EvidenceState.INSUFFICIENT_INFORMATION, printedOmitted.Select(Link).ToList(), "Unresolved: the compilation and the version records disagree."));
        if (printedOmitted.Count == 0 && ending.Count > 0 && _in[node.Id].Any(e => e.Type == EdgeType.Contains && EdgeVisible(e)))
            f.Add(new Finding("version_omission_not_printed", "A held version record describes an omission or repeal, but the held compilation prints the provision without an omission mark.",
                EvidenceState.INSUFFICIENT_INFORMATION, ending.Select(Link).ToList(), "Unresolved: the version records and the compilation disagree."));
        var undetermined = versions.Where(v => v.TemporalFrom is null && v.TemporalFromStatus is not ("REPORTED_IN_COMPILATION_ONLY")).ToList();
        if (versions.Count > 1 && undetermined.Count > 0)
            f.Add(new Finding("version_chain_undetermined", $"{versions.Count} version records are held and {undetermined.Count} have no established start date, so their order in time is unresolved.",
                EvidenceState.INSUFFICIENT_INFORMATION, undetermined.Select(Link).ToList(), "Temporal chain not established."));
        if (node.Family is not null && g.Relations.Family(node.Family) is { } inst && g.Documents.TryGetValue(inst.PrimaryDocId, out var pd))
        {
            var repealed = _in[GraphIds.Instrument(node.Family)].Where(e => e.Type == EdgeType.RepealsInstrument && EdgeVisible(e)).ToList();
            if (repealed.Count > 0 && pd.CorpusStatus is "in_force" or "amended" or "unknown")
                f.Add(new Finding("status_vs_repeal_text", $"The crawler status of {inst.Title} is '{pd.CorpusStatus}', while held text of another instrument repeals it.",
                    EvidenceState.INSUFFICIENT_INFORMATION, repealed.Select(Link).ToList(), "Unresolved: a display-only crawler status and held repeal text disagree; savings may keep the instrument relevant."));
        }
        if (f.Count == 0)
            f.Add(new Finding("no_conflict_detected", "No conflict was detected among the held records checked. Absence of a detected conflict is not evidence that none exists.",
                EvidenceState.CANDIDATE, Array.Empty<EvidenceLink>(), "Checks: compilation omission mark, version records, version dates, crawler status against repeal text."));
        return Result("conflicts", node.Id, inputs, f, new(), new());
    }
}
