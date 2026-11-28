// C16 Tranche B Stage 3 (S3-D): the in-process generation swap at the protocol level, with the REAL activation engine,
// participant and GenerationHost, and the two real SYN generations (MIMAMSA_TEST_SITE) as the generations' payload.
// FIXTURE acceptance (SG-5): simulated (unbound) staging markers on a B06 harness site; no database. The web process
// journey over the same wiring is C16S3dWebTests.
//   - concurrent readers across repeated swaps (activate and rollback) never see a mixed generation, never use a
//     released generation, and never more than two generations are resident;
//   - a failure while loading the target leaves the old generation serving, nothing journaled;
//   - the residency budget refuses a third generation while the old one is still in use, and admits it once drained;
//   - a rollback swap;
//   - memory: the swapped-out generation is released (WeakReference collected) and the heap is measured.
using System.Collections.Concurrent;
using System.Text.Json.Nodes;
using Mimamsa.Core.Activation;
using Mimamsa.Core.Generation;
using Mimamsa.Core.Search;
using Mimamsa.Tests.Activation;
using Mimamsa.Web;

namespace Mimamsa.Tests;

public class C16S3dSwapTests
{
    const string G1 = "R13-syn-fixture-20261125-00000001", G2 = "R13-syn-fixture-20261125-00000002";

    sealed class Rig : IDisposable
    {
        public FixtureSite Site { get; }
        public ActivationParticipant Participant { get; }
        public GenerationHost Host { get; }
        public ActivationEngine Engine { get; }
        public readonly ConcurrentQueue<string> Log = new();
        public Func<string, bool> FailLoad = _ => false;
        public int Loaded;

        public Rig(string label, Func<string, GenerationSlot>? loader = null, TimeSpan? budgetWait = null, params string[] extraGens)
        {
            Site = FixtureSite.Simple(label, [G1, G2, .. extraGens]);
            var reader = Site.NewReader();
            Participant = new ActivationParticipant(new SiteInspector(Site.Layout, reader));
            Host = new GenerationHost(id =>
            {
                if (FailLoad(id)) throw new InvalidDataException("injected load failure");
                Interlocked.Increment(ref Loaded);
                return (loader ?? SynSlot)(id);
            }) { BudgetWait = budgetWait ?? TimeSpan.FromSeconds(5), Log = Log.Enqueue };
            Host.Install((loader ?? SynSlot)(G1));
            Host.AttachTo(Participant);
            Assert.True(Participant.LoadHead());
            Engine = new ActivationEngine(new ActivationEngineOptions
            {
                Site = Site.Layout, WriterId = "s3d-test", Database = Site.Db, Exclusions = Site.NewReader(), Production = false,
                Participant = new DirectParticipantLink(Participant),
            });
            Engine.AcquireLock();
            if (Engine.NeedsRecovery()) Engine.Recover();
        }

        public void Dispose() { try { Engine.ReleaseLock(); } catch { } Engine.Dispose(); Site.Dispose(); }
    }

    /// A slot over a real SYN generation (memory text store and memory index, the heaviest case for the memory test).
    static GenerationSlot SynSlot(string id)
    {
        var g = GenerationStore.Load(Syn.Site, generationId: id);
        var ix = SearchIndex.Build(g);
        return new GenerationSlot { Id = id, Payload = new object[] { g, ix }, OnRelease = () => ix.Release() };
    }

    static GenerationStore Gen(GenerationSlot s) => (GenerationStore)((object[])s.Payload!)[0];

    // Helpers that keep no reference in the test method's own frame (tier-0 code reports every local and temporary live
    // until the method returns, which would keep a released generation reachable from the test itself).
    [System.Runtime.CompilerServices.MethodImpl(System.Runtime.CompilerServices.MethodImplOptions.NoInlining)]
    static WeakReference WeakCurrent(GenerationHost h) => new(Gen(h.Current!));
    sealed class Request { public ReaderPin? Pin; public GenerationSlot? Slot; }
    [System.Runtime.CompilerServices.MethodImpl(System.Runtime.CompilerServices.MethodImplOptions.NoInlining)]
    static Request PinAndLease(Rig rig) { var p = rig.Participant.Pin(); return new Request { Pin = p, Slot = rig.Host.Acquire(p.Knowledge) }; }
    [System.Runtime.CompilerServices.MethodImpl(System.Runtime.CompilerServices.MethodImplOptions.NoInlining)]
    static bool StillLeasedSlotReleased(Request r) => r.Slot!.Released;
    [System.Runtime.CompilerServices.MethodImpl(System.Runtime.CompilerServices.MethodImplOptions.NoInlining)]
    static void EndRequest(Rig rig, Request r) { rig.Host.ReleaseLease(r.Slot!); rig.Participant.Unpin(r.Pin!); r.Slot = null; r.Pin = null; }

    [Fact]
    public void ConcurrentReadersAcrossSwapsNeverMixGenerationsOrUseAReleasedOne()
    {
        using var rig = new Rig("s3d-concurrent");
        var stop = new CancellationTokenSource();
        long served = 0, refused = 0, mixed = 0, usedReleased = 0, overBudget = 0;
        var seen = new ConcurrentDictionary<string, int>();
        var readers = Enumerable.Range(0, 6).Select(_ => Task.Run(() =>
        {
            while (!stop.IsCancellationRequested)
            {
                ReaderPin pin;
                try { pin = rig.Participant.Pin(); }
                catch (ActivationRefused) { Interlocked.Increment(ref refused); Thread.Yield(); continue; }
                try
                {
                    var slot = rig.Host.Acquire(pin.Knowledge);
                    if (slot is null) { Interlocked.Increment(ref refused); continue; }
                    try
                    {
                        // a "request": several reads of its generation's services, spread over time
                        for (int i = 0; i < 5; i++)
                        {
                            var g = Gen(slot);
                            if (g.GenerationId != pin.Knowledge || slot.Id != pin.Knowledge) Interlocked.Increment(ref mixed);
                            if (slot.Released) Interlocked.Increment(ref usedReleased);
                            _ = g.Documents.Count;
                            if (rig.Host.ResidentCount > 2) Interlocked.Increment(ref overBudget);
                            Thread.SpinWait(2000);
                        }
                        seen.AddOrUpdate(slot.Id, 1, (_, n) => n + 1);
                        Interlocked.Increment(ref served);
                    }
                    finally { rig.Host.ReleaseLease(slot); }
                }
                finally { rig.Participant.Unpin(pin); }
            }
        })).ToList();
        Thread.Sleep(200);
        var txns = new List<string>();
        for (int i = 0; i < 6; i++)
        {
            txns.Add(rig.Engine.Transition("KNOWLEDGE", i % 2 == 0 ? G2 : G1, i % 2 == 0 ? "ACTIVATE" : "ROLLBACK"));
            Assert.Equal(i % 2 == 0 ? G2 : G1, rig.Host.Current!.Id);
            Thread.Sleep(100);
        }
        stop.Cancel();
        Task.WaitAll(readers.ToArray());
        Assert.Equal(0, Interlocked.Read(ref mixed));
        Assert.Equal(0, Interlocked.Read(ref usedReleased));
        Assert.Equal(0, Interlocked.Read(ref overBudget));
        Assert.True(seen.ContainsKey(G1) && seen.ContainsKey(G2), "both generations served: " + string.Join(",", seen));
        Assert.True(Interlocked.Read(ref served) > 50, $"served {served}");
        Assert.Equal(6, txns.Distinct().Count());
        // after the last swap (rollback to G1) and with every reader gone, only G1 is resident
        Assert.Equal(new[] { G1 }, rig.Host.Resident);
        Assert.True(rig.Host.Releases >= 6, $"releases {rig.Host.Releases}");
        S3dEvidence.Write("swap_concurrency.json", new JsonObject
        {
            ["readers"] = 6, ["swaps"] = 6, ["requests_served"] = served, ["requests_refused_during_switch"] = refused,
            ["mixed_generation"] = mixed, ["used_released_generation"] = usedReleased, ["over_two_resident"] = overBudget,
            ["served_by_generation"] = new JsonObject(seen.Select(kv => KeyValuePair.Create(kv.Key, (JsonNode?)kv.Value))),
            ["loads"] = rig.Host.Loads, ["releases"] = rig.Host.Releases,
        });
    }

    [Fact]
    public void AFailureWhileLoadingTheTargetLeavesTheOldGenerationServingAndNothingJournaled()
    {
        using var rig = new Rig("s3d-loadfail");
        rig.FailLoad = id => id == G2;
        int before = rig.Engine.Inspector.Journal().Entries.Count;
        var e = Assert.Throws<ActivationRefused>(() => rig.Engine.Transition("KNOWLEDGE", G2));
        Assert.Equal("PARTICIPANT_NOT_PREPARED", e.Code);
        Assert.Equal(before, rig.Engine.Inspector.Journal().Entries.Count);    // nothing journaled
        Assert.Equal(G1, rig.Site.Layout.ReadPointer("KNOWLEDGE"));
        Assert.Equal(SiteState.OPEN, rig.Site.Layout.ReadMarker());
        Assert.True(rig.Participant.IsServing());                               // never stopped admitting
        var pin = rig.Participant.Pin();
        Assert.Equal(G1, pin.Knowledge);
        var slot = rig.Host.Acquire(G1);
        Assert.NotNull(slot);
        rig.Host.ReleaseLease(slot!); rig.Participant.Unpin(pin);
        Assert.Equal(new[] { G1 }, rig.Host.Resident);                                  // the failed load left nothing behind
        Assert.Equal(1, rig.Host.LoadFailures);
        // the cause removed, the same transition succeeds
        rig.FailLoad = _ => false;
        rig.Engine.Transition("KNOWLEDGE", G2);
        Assert.Equal(G2, rig.Host.Current!.Id);
        Assert.Equal(new[] { G2 }, rig.Host.Resident);
    }

    [Fact]
    public void ARollbackSwapServesThePreviousGenerationAgainAndReleasesTheNewOne()
    {
        using var rig = new Rig("s3d-rollback");
        rig.Engine.Transition("KNOWLEDGE", G2);
        Assert.Equal(G2, rig.Host.Current!.Id);
        var g2 = WeakCurrent(rig.Host);
        rig.Engine.Transition("KNOWLEDGE", G1, "ROLLBACK");
        Assert.Equal(G1, rig.Host.Current!.Id);
        Assert.Equal(G1, rig.Participant.LoadedKnowledge);
        var pin = rig.Participant.Pin();
        Assert.Equal(G1, pin.Knowledge);
        rig.Participant.Unpin(pin);
        Assert.Equal(new[] { G1 }, rig.Host.Resident);
        GC.Collect(); GC.WaitForPendingFinalizers(); GC.Collect();
        Assert.False(g2.IsAlive, "the rolled-back-from generation was released");
        Assert.Equal(3, rig.Host.Loads + 1);   // G1 at start (Install), G2, then G1 again (it had been released)
    }

    [Fact]
    public void TheResidencyBudgetRefusesAThirdGenerationWhileTheOldOneIsInUse()
    {
        // light slots: this test is about the budget, not the payload
        GenerationSlot Light(string id) => new() { Id = id, Payload = new byte[1 << 20] };
        using var rig = new Rig("s3d-budget", Light, TimeSpan.FromMilliseconds(300), "G3-light");
        var pin = rig.Participant.Pin();
        var old = rig.Host.Acquire(pin.Knowledge)!;           // a long request still on G1
        rig.Engine.Transition("KNOWLEDGE", G2);               // G2 loads beside G1 (2 resident) and becomes current
        Assert.Equal(2, rig.Host.ResidentCount);
        Assert.False(old.Released);
        var e = Assert.Throws<ActivationRefused>(() => rig.Engine.Transition("KNOWLEDGE", "G3-light"));
        Assert.Equal("PARTICIPANT_NOT_PREPARED", e.Code);     // a third would exceed two resident: refused before BEGIN
        Assert.Equal(1, rig.Host.BudgetRefusals);
        Assert.Equal(G2, rig.Site.Layout.ReadPointer("KNOWLEDGE"));
        Assert.Equal(2, rig.Host.ResidentCount);
        rig.Host.ReleaseLease(old); rig.Participant.Unpin(pin);   // the long request ends: G1 is released
        Assert.True(old.Released);
        Assert.Equal(1, rig.Host.ResidentCount);
        rig.Engine.Transition("KNOWLEDGE", "G3-light");           // now admitted
        Assert.Equal("G3-light", rig.Host.Current!.Id);
        Assert.True(rig.Host.ResidentCount <= 2);
    }

    [Fact]
    public void AnAbandonedPreparedTargetDoesNotBlockTheNextTransition()
    {
        GenerationSlot Light(string id) => new() { Id = id, Payload = new byte[1024] };
        using var rig = new Rig("s3d-abandoned", Light, TimeSpan.FromMilliseconds(300), "G3-light");
        // a PREPARE whose transition never reached OPEN (the participant was not told of the abort)
        Assert.True(rig.Participant.Prepare("TX-abandoned", "KNOWLEDGE", G2, WriterLease.CurrentEpoch(rig.Site.Layout)).Prepared);
        Assert.Equal(2, rig.Host.ResidentCount);
        rig.Engine.Transition("KNOWLEDGE", "G3-light");      // supersedes it: the stale target is released, not counted
        Assert.Equal("G3-light", rig.Host.Current!.Id);
        Assert.Equal(new[] { "G3-light" }, rig.Host.Resident);
        Assert.Equal(0, rig.Host.BudgetRefusals);
    }

    /// Facet recount (S3-D goal 3): with the response boundary as the engine's hidden-document predicate, totals and every
    /// facet value are counted over the surviving results only - exactly the unfiltered counts minus the excluded
    /// documents that matched - with and without a filter, and no hit, chip or count names an excluded document.
    [Theory]
    [InlineData("hearing", null)]
    [InlineData("written", null)]
    [InlineData("hearing", "judgment")]
    public void FacetsAndTotalsAreCountedExactlyOverTheSurvivingResults(string query, string? type)
    {
        var ix = SearchIndex.Build(Syn.Gen);
        var filters = new SearchFilters(Types: type is null ? null : new HashSet<string> { type });
        var all = new SearchService(ix, _ => false).Search(query, new SearchFilters());
        var docsAll = all.Hits.Select(h => ix.Docs[ix.DocOf(h.PassageIndex)]).DistinctBy(d => d.DocId).ToList();
        Assert.True(docsAll.Count >= 3, $"query '{query}' matches {docsAll.Count} documents");
        // exclude one judgment (doc id) and one other document (as a copy-hash exclusion would)
        var hidden = new HashSet<string>(StringComparer.Ordinal)
        {
            docsAll.First(d => d.DocType == "judgment").DocId, docsAll.First(d => d.DocType != "judgment").DocId,
        };
        var allF = new SearchService(ix, _ => false).Search(query, filters);
        var hid = new SearchService(ix, hidden.Contains) { HideChipsOfHiddenDocuments = true }.Search(query, filters);
        Assert.DoesNotContain(hid.Hits, h => hidden.Contains(ix.Docs[ix.DocOf(h.PassageIndex)].DocId));
        var allFDocs = allF.Hits.Select(h => ix.Docs[ix.DocOf(h.PassageIndex)].DocId).ToHashSet();
        Assert.Equal(allF.TotalDocuments - hidden.Count(allFDocs.Contains), hid.TotalDocuments);
        Assert.Equal(allF.Hits.Count(h => !hidden.Contains(ix.Docs[ix.DocOf(h.PassageIndex)].DocId)), hid.TotalPassages);
        // facets are computed BEFORE the filter (each facet ignores its own filter), over every matching document
        foreach (var (facet, values) in allF.Facets)
        {
            Func<Mimamsa.Core.Generation.DocumentRecord, string?> key = facet switch
            {
                "type" => d => d.DocType, "court" => d => d.CourtOrIssuer, "year" => d => d.Year?.ToString(), _ => d => d.CorpusStatus,
            };
            bool passOthers(Mimamsa.Core.Generation.DocumentRecord d) => facet == "type" || type is null || d.DocType == type;
            var expected = values.Select(v => (v.Value, Count: v.Count - docsAll.Count(d => hidden.Contains(d.DocId) && passOthers(d) && (key(d) ?? "Not recorded") == v.Value)))
                                 .Where(x => x.Count > 0).OrderBy(x => x.Value, StringComparer.Ordinal).ToList();
            var actual = hid.Facets[facet].Select(v => (v.Value, v.Count)).OrderBy(x => x.Value, StringComparer.Ordinal).ToList();
            Assert.Equal(expected, actual);
        }
        // the hidden documents are not named by any chip, and the counts in the response are consistent with its hits
        Assert.All(hid.Chips, c => Assert.True(hidden.All(h => !(c.Text + c.Source).Contains(h, StringComparison.Ordinal))));
        Assert.Equal(hid.TotalDocuments, hid.Hits.Select(h => ix.DocOf(h.PassageIndex)).Distinct().Count());
    }

    [Fact]
    public void TheSwappedOutGenerationIsReleasedAndItsMemoryIsMeasured()
    {
        static long Heap() { GC.Collect(); GC.WaitForPendingFinalizers(); GC.Collect(); return GC.GetTotalMemory(true); }
        var h0 = Heap();
        using var rig = new Rig("s3d-memory");
        var g1 = WeakCurrent(rig.Host);
        var h1 = Heap();                                  // one generation resident
        Assert.True(rig.Participant.Prepare("TX-probe", "KNOWLEDGE", G2, WriterLease.CurrentEpoch(rig.Site.Layout)).Prepared);
        var h2 = Heap();                                  // two resident (the target loaded beside)
        Assert.Equal(2, rig.Host.ResidentCount);
        // a request still pinned on G1 keeps it alive across the switch
        var request = PinAndLease(rig);
        rig.Engine.Transition("KNOWLEDGE", G2);
        var h3 = Heap();
        Assert.True(g1.IsAlive);
        Assert.False(StillLeasedSlotReleased(request));
        EndRequest(rig, request);                         // last pin on G1 goes
        var h4 = Heap();
        Assert.False(g1.IsAlive, "G1 was released when its last pin went");
        Assert.Equal(new[] { G2 }, rig.Host.Resident);
        double Mb(long b) => Math.Round(b / 1048576.0, 2);
        S3dEvidence.Write("swap_memory.json", new JsonObject
        {
            ["note"] = "GC.GetTotalMemory(true) after full collections, in the shared xunit test process (other tests run in parallel, so absolute values carry noise; the weak-reference result is the assertion)",
            ["text_store"] = "memory (heaviest case: page text resident)", ["index"] = "memory",
            ["baseline_mb"] = Mb(h0), ["one_resident_mb"] = Mb(h1), ["two_resident_mb"] = Mb(h2),
            ["after_switch_old_still_pinned_mb"] = Mb(h3), ["after_last_pin_released_mb"] = Mb(h4),
            ["one_generation_cost_mb"] = Mb(h1 - h0), ["second_generation_cost_mb"] = Mb(h2 - h1), ["released_mb"] = Mb(h3 - h4),
            ["old_generation_collected"] = !g1.IsAlive,
        });
    }
}

/// Evidence written by the S3-D tests when MIMAMSA_S3D_EVIDENCE_DIR is set (local runs); nothing otherwise.
static class S3dEvidence
{
    public static void Write(string name, JsonObject o)
    {
        if (Environment.GetEnvironmentVariable("MIMAMSA_S3D_EVIDENCE_DIR") is not { Length: > 0 } dir) return;
        Directory.CreateDirectory(dir);
        File.WriteAllText(Path.Combine(dir, name), o.ToJsonString(new System.Text.Json.JsonSerializerOptions { WriteIndented = true }) + "\n");
    }
}
