using Mimamsa.Core.Generation;
using Mimamsa.Core.Graph;
using Mimamsa.Core.Reasoning;
using Npgsql;

namespace Mimamsa.Tests;

/// C15 WP4 rule-engine foundation: SYNTHETIC oracles only (DETERMINISTIC_LEGAL_ENGINE §8, §10). No legal rule is encoded.
public class RuleEngineTests
{
    static readonly Tri T = Tri.True, F = Tri.False, U = Tri.Unknown;

    [Fact]
    public void StrongKleeneTruthTables()
    {
        Assert.Equal(U, Kleene.Not(U)); Assert.Equal(F, Kleene.Not(T));
        Assert.Equal(F, Kleene.And(F, U)); Assert.Equal(U, Kleene.And(T, U)); Assert.Equal(T, Kleene.And(T, T));
        Assert.Equal(T, Kleene.Or(T, U)); Assert.Equal(U, Kleene.Or(F, U)); Assert.Equal(F, Kleene.Or(F, F));
    }

    /// Synthetic oracle from §8: P and Q conjunctive; exception E overrides only when established.
    static DecisionTable Synthetic() => new("SYN-PQE", new[] { "P", "Q", "E" }, new[]
    {
        new DecisionRow(new Dictionary<string, bool> { ["E"] = true }, "not_applicable"),
        new DecisionRow(new Dictionary<string, bool> { ["P"] = true, ["Q"] = true, ["E"] = false }, "pass"),
        new DecisionRow(new Dictionary<string, bool> { ["P"] = true, ["Q"] = false, ["E"] = false }, "fail"),
        new DecisionRow(new Dictionary<string, bool> { ["P"] = false, ["E"] = false }, "fail"),
    });

    [Fact]
    public void SyntheticDecisionTableFollowsTheOracle()
    {
        var t = Synthetic();
        TableResult R(Tri p, Tri q, Tri e) => t.Evaluate(new Dictionary<string, Tri> { ["P"] = p, ["Q"] = q, ["E"] = e });
        Assert.Equal(("DECIDED", "pass"), (R(T, T, F).State, R(T, T, F).Output));
        Assert.Equal(TableResult.Unknown, R(T, T, U).State);                 // unknown exception prevents an unconditional pass
        Assert.Equal("fail", R(T, F, F).Output);
        Assert.Equal("not_applicable", R(T, T, T).Output);
        Assert.Equal(TableResult.Unknown, R(U, T, F).State);                 // unknown prerequisite is never coerced to false
        Assert.NotEmpty(R(T, T, F).Trace);
    }

    [Fact]
    public void OverlappingRowsRejectThePack()
    {
        Assert.Throws<RulePackRejectedException>(() => new DecisionTable("SYN-OVERLAP", new[] { "P", "Q" }, new[]
        {
            new DecisionRow(new Dictionary<string, bool> { ["P"] = true }, "a"),
            new DecisionRow(new Dictionary<string, bool> { ["Q"] = true }, "b"),     // P=T,Q=T matches both
        }));
        Assert.Throws<RulePackRejectedException>(() => new DecisionTable("SYN-UNDECLARED", new[] { "P" },
            new[] { new DecisionRow(new Dictionary<string, bool> { ["X"] = true }, "a") }));
    }

    [Fact]
    public void GateIsClosedAtLedgerV0AndTheEvaluatorIsNotInvoked()
    {
        var t = Synthetic();
        var facts = new Dictionary<string, Tri> { ["P"] = T, ["Q"] = T, ["E"] = F };
        foreach (var grant in new[] { false, true })
        {
            var (state, result, gate) = RuleGate.Evaluate(t, facts, authLedgerVersion: 0, approvedGrantCoversExactScope: grant);
            Assert.Equal("NOT_CHECKED", state); Assert.Null(result);
            Assert.False(gate.EvaluationAdmitted); Assert.False(gate.DeliveryAuthorized);
            Assert.Contains(gate.Blockers, b => b.Contains("version 0"));
        }
        Assert.Equal("NOT_CHECKED", RuleGate.Evaluate(t, facts, 1, false).state);   // a later ledger still needs an exact grant
        Assert.Equal(0, t.Invocations);
        Assert.Equal("EVALUATED", RuleGate.Evaluate(t, facts, 1, true).state);    // synthetic mechanics only; no such grant exists
    }
}

/// C15 WP3 graph builder invariants on the SYN site, and golden research assessments on the real sample.
public class GraphBuilderTests
{
    [Fact]
    public void BuilderIsDeterministicAndNeverPromotes()
    {
        var a = GraphBuilder.Build(Syn.Gen); var b = GraphBuilder.Build(Syn.Gen);
        Assert.Equal(a.Nodes.Select(n => n.Id), b.Nodes.Select(n => n.Id));
        Assert.Equal(a.Edges.Select(e => e.Id), b.Edges.Select(e => e.Id));
        Assert.Equal(GraphStore.Digest(a), GraphStore.Digest(b));
        Assert.All(a.Edges, e => Assert.Contains(e.Verification, Verification.BuilderValues));
        Assert.All(a.Edges, e => Assert.Equal(GraphBuilder.ReviewUnreviewed, e.ReviewState));
        Assert.All(a.Edges, e => Assert.False(string.IsNullOrWhiteSpace(e.Uncertainty)));
        var ids = a.Nodes.Select(n => n.Id).ToHashSet();
        Assert.All(a.Edges, e => { Assert.Contains(e.From, ids); Assert.Contains(e.To, ids); });
        Assert.Contains(a.Edges, e => e.Origin == "A5" && e.Type == EdgeType.CitesJudgment && e.SourceDocId == "syn-j-allow" && e.Page is not null);
        Assert.Contains(a.Nodes, n => n.Kind == NodeKind.Instrument);
    }

    static GenerationStore? _sample;
    static GenerationStore? Sample => Environment.GetEnvironmentVariable("MIMAMSA_SAMPLE_SITE") is { Length: > 0 } s && Directory.Exists(s) ? _sample ??= GenerationStore.Load(s) : null;

    /// Golden research assessments built from held texts of the real sample (skipped without MIMAMSA_SAMPLE_SITE).
    [Fact]
    public void GoldenAssessmentsOnTheRealSample()
    {
        if (Sample is not { } g) return;
        var graph = GraphBuilder.Build(g);
        var a = new EvidenceAssessor(g, graph, _ => true);
        Assert.Equal(0, g.Release.AuthLedgerVersion);

        // TA-01: Army Act s.75 printed as omitted (1992); the date the omission took effect is not established
        var t75 = a.Temporal("AA-1950", "s", "75", new DateOnly(2000, 1, 1));
        Assert.Equal(EvidenceState.INSUFFICIENT_INFORMATION, t75.Overall);
        Assert.Contains(t75.Findings, f => f.Code == "printed_as_omitted" && f.State == EvidenceState.CANDIDATE && f.Evidence.All(e => e.Page is not null));
        Assert.Contains(t75.Blockers, b => b == EvidenceAssessor.LedgerBlocker);
        Assert.Contains("as_of_date", string.Join(" ", a.Temporal("AA-1950", "s", "75", null).MissingFacts));

        // TA-03: IPC s.302 and BNS s.103, conduct before 1 July 2024: correspondence and repeal are candidates; commencement
        // is not established from a held notification, so the question remains INSUFFICIENT_INFORMATION
        var ipc = a.Succession("IPC-1860", "s", "302", new DateOnly(2023, 12, 1), null);
        Assert.Equal(EvidenceState.INSUFFICIENT_INFORMATION, ipc.Overall);
        Assert.Contains(ipc.Findings, f => f.Code == "correspondence" && f.Statement.Contains("s.103") && f.State == EvidenceState.CANDIDATE);
        Assert.Contains(ipc.Findings, f => f.Code == "repealed_by" && f.Evidence.Count == 1 && f.Evidence[0].Quote is { Length: > 0 });
        Assert.Contains(ipc.Findings, f => f.Code == "commencement_not_established" && f.State == EvidenceState.INSUFFICIENT_INFORMATION);
        Assert.Contains(ipc.Findings, f => f.Code == "conduct_date_vs_secondary_date" && f.Statement.Contains("before"));
        Assert.Contains(ipc.MissingFacts, m => m.StartsWith("proceeding_date"));
        var bns = a.Succession("BNS-2023", "s", "103", new DateOnly(2024, 8, 1), new DateOnly(2024, 9, 1));
        Assert.Contains(bns.Findings, f => f.Code == "correspondence" && f.Statement.Contains("s.302"));
        Assert.Contains(bns.Findings, f => f.Code == "conduct_date_vs_secondary_date" && f.Statement.Contains("on or after"));
        Assert.Equal(EvidenceState.INSUFFICIENT_INFORMATION, bns.Overall);

        // nothing is ESTABLISHED at AUTH-LEDGER v0, in any assessment
        var proc = a.Procedure("Summary court-martial");
        foreach (var x in new[] { t75, ipc, bns, proc, a.Conflicts("AA-1950", "s", "127"), a.Conflicts("IPC-1860", "s", "302") })
            Assert.DoesNotContain(x.Findings, f => f.State == EvidenceState.ESTABLISHED);
        Assert.Contains(proc.Findings, f => f.Code == "competent_authority" && f.State == EvidenceState.INSUFFICIENT_INFORMATION);
        // the crawler records the IPC as "repealed", which agrees with the held repeal text: no status conflict is reported (negative control)
        Assert.DoesNotContain(a.Conflicts("IPC-1860", "s", "302").Findings, f => f.Code == "status_vs_repeal_text");

        // eligibility: withdrawing the comparison table removes the correspondence; withdrawing the IPC hides the provision
        var noTable = new EvidenceAssessor(g, graph, d => d != "ref-bprd-comparison-bns-ipc").Succession("IPC-1860", "s", "302", null, null);
        Assert.DoesNotContain(noTable.Findings, f => f.Code == "correspondence");
        var noIpc = new EvidenceAssessor(g, graph, d => d != "act-ipc-1860").Temporal("IPC-1860", "s", "302", new DateOnly(2020, 1, 1));
        Assert.Equal("not_available", Assert.Single(noIpc.Findings).Code);
    }
}

/// C15 WP3 PostgreSQL store: atomic publication, integrity, crash recovery and eligibility on every query.
/// Uses a unique generation id in MIMAMSA_TEST_DB and removes it afterwards.
[Collection("service")]
public class GraphStoreTests
{
    static NpgsqlDataSource Db() => new NpgsqlDataSourceBuilder(Environment.GetEnvironmentVariable("MIMAMSA_TEST_DB")
        ?? throw new InvalidOperationException("MIMAMSA_TEST_DB is required")).Build();

    static LegalGraph WithGen(LegalGraph g, string gen) => g with { GenerationId = gen };

    static async Task Drop(NpgsqlDataSource ds, string gen)
    {
        await using var c = await ds.OpenConnectionAsync();
        foreach (var t in new[] { "graph_generation", "graph_edges", "graph_nodes" })
            await using (var d = new NpgsqlCommand($"DELETE FROM {t} WHERE generation_id=$1", c)) { d.Parameters.AddWithValue(gen); await d.ExecuteNonQueryAsync(); }
    }

    [Fact]
    public async Task PublishVerifyQueryAndEligibility()
    {
        await using var ds = Db();
        var store = new GraphStore(ds); await store.EnsureSchemaAsync();
        var gen = "test-" + Guid.NewGuid().ToString("N")[..10];
        var built = WithGen(GraphBuilder.Build(Syn.Gen), gen);
        // C15 security review L3: an unresolved reference cited only by syn-j-allow, labelled with text from that judgment
        var refNode = new GraphNode(GraphIds.Reference("L3 probe reference text"), NodeKind.UnresolvedReference, "L3 probe reference text", null, null, false, null, null, null);
        var refEdge = new GraphEdge("E-L3-PROBE", EdgeType.CitesJudgment, GraphIds.Judgment("syn-j-allow"), refNode.Id, "A5", "syn-j-allow", null, 1, null,
            null, "AS_OF_SOURCE_DATE", null, "NOT_APPLICABLE", Verification.Candidate, "UNREVIEWED", "test probe", false);
        var graph = built with { Nodes = built.Nodes.Append(refNode).ToList(), Edges = built.Edges.Append(refEdge).ToList() };
        try
        {
            await Assert.ThrowsAsync<GraphNotPublishedException>(() => store.StatsAsync(gen, Array.Empty<string>()));
            Assert.True(await store.PublishAsync(graph));
            Assert.False(await store.PublishAsync(graph));                         // identical graph: not republished
            Assert.True((await store.VerifyAsync(graph)).ok);

            var none = Array.Empty<string>();
            var stats = await store.StatsAsync(gen, none);
            Assert.Equal(graph.Nodes.Count, stats.Nodes); Assert.Equal(graph.Edges.Count, stats.Edges);

            var jud = GraphIds.Judgment("syn-j-allow");
            var (node, edges, _) = await store.NeighbourhoodAsync(gen, jud, 1, none);
            Assert.NotNull(node);
            Assert.Contains(edges, e => e.Edge.Type == EdgeType.CitesJudgment && e.Edge.From == jud);

            // withdrawal: the document's node, its edges and the statistics drop at once; reinstatement restores them
            var hidden = new[] { "syn-j-allow" };
            Assert.Null((await store.NeighbourhoodAsync(gen, jud, 2, hidden)).node);
            Assert.Null(await store.NodeAsync(gen, jud, hidden));
            Assert.True((await store.StatsAsync(gen, hidden)).Edges < stats.Edges);
            var target = edges.First(e => e.Edge.From == jud).Edge.To;
            Assert.Null(await store.PathAsync(gen, jud, target, 2, hidden));
            Assert.NotNull(await store.PathAsync(gen, jud, target, 2, none));
            Assert.Equal(stats.Edges, (await store.StatsAsync(gen, none)).Edges);

            // C15 security review L3: a node without its own document (an unresolved reference labelled with text from
            // the citing judgment) is hidden once every edge touching it comes from, or leads to, a withdrawn document
            Assert.Equal("L3 probe reference text", (await store.NodeAsync(gen, refNode.Id, none))!.Label);
            Assert.Null(await store.NodeAsync(gen, refNode.Id, hidden));
            Assert.True((await store.StatsAsync(gen, hidden)).Nodes <= stats.Nodes - 2);   // the judgment and its orphaned reference leave the count

            // every instrument reaches its provisions, and a path never crosses a hidden document
            var inst = graph.Nodes.First(n => n.Kind == NodeKind.Instrument && graph.Edges.Any(e => e.From == n.Id && e.Type == EdgeType.Contains));
            var prov = graph.Edges.First(e => e.From == inst.Id && e.Type == EdgeType.Contains).To;
            var p = await store.PathAsync(gen, inst.Id, prov, 1, none);
            Assert.Equal(new[] { inst.Id, prov }, p!.Nodes);
            Assert.Null(await store.PathAsync(gen, inst.Id, prov, 4, new[] { inst.DocId! }));
        }
        finally { await Drop(ds, gen); }
    }

    [Fact]
    public async Task InterruptedPublicationLeavesThePreviousGraphIntact()
    {
        await using var ds = Db();
        var store = new GraphStore(ds); await store.EnsureSchemaAsync();
        var gen = "test-" + Guid.NewGuid().ToString("N")[..10];
        var v1 = WithGen(GraphBuilder.Build(Syn.Gen), gen);
        var v2 = v1 with { Edges = v1.Edges.Skip(1).ToList() };
        try
        {
            Assert.True(await store.PublishAsync(v1));
            await Assert.ThrowsAsync<IOException>(() => store.PublishAsync(v2, () => throw new IOException("simulated crash before commit")));
            Assert.True((await store.VerifyAsync(v1)).ok);                         // rolled back: v1 still published, intact
            Assert.False((await store.VerifyAsync(v2)).ok);
            Assert.True(await store.PublishAsync(v2));                              // recovery: the next publication succeeds
            Assert.True((await store.VerifyAsync(v2)).ok);
        }
        finally { await Drop(ds, gen); }
    }

    [Fact]
    public async Task TheBuilderCannotPublishReviewedEdges()
    {
        await using var ds = Db();
        var store = new GraphStore(ds);
        var g = GraphBuilder.Build(Syn.Gen);
        var forged = g with { GenerationId = "test-forged", Edges = g.Edges.Select((e, i) => i == 0 ? e with { Verification = Verification.LegalReviewed } : e).ToList() };
        await Assert.ThrowsAsync<InvalidOperationException>(() => store.PublishAsync(forged));
    }
}
