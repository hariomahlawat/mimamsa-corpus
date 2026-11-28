// C16 S3-C (B07 + B06, WD-13, D4/D6): activation, rollback and retention on an INSTALLED layout, with the retention
// limit taken from the installation configuration (configurable; default active + two previous distinct verified
// releases). Never pruned: the active release, the previous distinct releases within the limit, a pinned generation, the
// target of an in-flight transaction, the explicit recovery target, and the sole remaining generation. B06 fixture
// generations (simulation markers) are used here; the same limits with real releases run in S3cRestoreJourneyTests.
using Mimamsa.Core.Activation;
using Mimamsa.Core.Install;
using Mimamsa.Tests.Activation;

namespace Mimamsa.Tests.Install;

public class InstalledRetentionTests
{
    static readonly string[] Gens = ["R1", "R2", "R3", "R4", "R5", "R6"];

    sealed class Installed : IDisposable
    {
        public readonly FixtureSite Fx;
        public readonly InstallConfig Cfg;
        public readonly ActivationParticipant P;
        public readonly DirectParticipantLink Link;
        public readonly ActivationEngine Eng;
        readonly string _base;
        public Installed(int keep, string[] gens, string? recoveryTarget = null, Action<string>? hook = null)
        {
            _base = S3cDirs.New("ret");
            Fx = new FixtureSite("s3c-ret", gens, gens[0], "M1", new Dictionary<string, (bool, string[])> { ["M1"] = (true, gens) });
            Cfg = S3cDirs.Config(_base, site: Fx.Root, keep: keep);
            InstallLayout.Create(Cfg, null, "test");
            P = new ActivationParticipant(new SiteInspector(Fx.Layout, Fx.NewReader()));
            P.LoadHead();
            Link = new DirectParticipantLink(P);
            Eng = new ActivationEngine(new ActivationEngineOptions
            {
                Site = Fx.Layout, WriterId = "s3c-retention", Database = Fx.Db, Exclusions = Fx.NewReader(), Participant = Link,
                Disk = new FixedDiskProbe(1L << 40), KeepPrevious = Cfg.KeepPrevious, HeadroomFraction = Cfg.HeadroomFraction,
                RecoveryTarget = recoveryTarget, StepHook = hook,
            });
            Eng.AcquireLock();
        }
        public List<string> Installed_() => new GenerationCatalog(Fx.Layout).Installed();
        public void Dispose() { try { Eng.ReleaseLock(); } catch { } Eng.Dispose(); Fx.Dispose(); S3cDirs.Delete(_base); }
    }

    [Theory]
    [InlineData(1), InlineData(2), InlineData(3)]
    public void The_configured_limit_keeps_the_active_and_that_many_previous_distinct_releases(int keep)
    {
        using var s = new Installed(keep, Gens);
        foreach (var g in Gens.Skip(1)) s.Eng.Transition("KNOWLEDGE", g);
        var expectKept = Gens.Reverse().Take(keep + 1).Order(StringComparer.Ordinal).ToList();
        var removed = s.Eng.Prune();
        Assert.Equal(Gens.Except(expectKept), removed.Order(StringComparer.Ordinal));
        Assert.Equal(expectKept, s.Installed_());
        Assert.Empty(s.Eng.Prune());   // idempotent
    }

    [Fact]
    public void Rollback_history_counts_distinct_releases_only()
    {
        using var s = new Installed(2, Gens);
        s.Eng.Transition("KNOWLEDGE", "R2");
        s.Eng.Transition("KNOWLEDGE", "R3");
        s.Eng.Transition("KNOWLEDGE", "R2", "ROLLBACK");
        s.Eng.Transition("KNOWLEDGE", "R3");
        s.Eng.Transition("KNOWLEDGE", "R4");
        Assert.Equal(["R3", "R2"], s.Eng.PreviousDistinct());
        Assert.Equal(["R1", "R5", "R6"], s.Eng.Prune().Order(StringComparer.Ordinal));
    }

    [Fact]
    public void Pinned_recovery_target_and_sole_generations_are_never_pruned()
    {
        using (var s = new Installed(1, Gens, recoveryTarget: "R1"))
        {
            s.Eng.Transition("KNOWLEDGE", "R2");
            var pin = s.P.Pin();                       // a reader pinned to R2
            s.Eng.Transition("KNOWLEDGE", "R3");
            s.Eng.Transition("KNOWLEDGE", "R4");
            s.Eng.Transition("KNOWLEDGE", "R5");
            var removed = s.Eng.Prune();
            Assert.DoesNotContain("R1", removed);        // explicit recovery target
            Assert.DoesNotContain("R2", removed);        // pinned
            Assert.Equal(["R3", "R6"], removed.Order(StringComparer.Ordinal));
            s.P.Unpin(pin);
            Assert.Equal(["R2"], s.Eng.Prune());
            s.Link.Up = false;                          // pins unknown: nothing is pruned
            Assert.Empty(s.Eng.Prune());
        }
        using (var solo = new Installed(1, ["S1"]))
            Assert.Empty(solo.Eng.Prune());              // the sole generation
    }

    [Fact]
    public void An_in_flight_target_is_never_pruned_and_nothing_is_pruned_until_recovery()
    {
        bool crash = false;
        using var s = new Installed(1, Gens, hook: step => { if (crash && step == "BEGIN") throw new ActivationCrash(step); });
        s.Eng.Transition("KNOWLEDGE", "R2");
        s.Eng.Transition("KNOWLEDGE", "R3");
        crash = true;
        Assert.Throws<ActivationCrash>(() => s.Eng.Transition("KNOWLEDGE", "R6"));
        crash = false;
        Assert.Empty(s.Eng.Prune());                     // not OPEN: no pruning at all
        Assert.Contains("R6", s.Installed_());
        s.Eng.Recover();                                 // BEGIN without DECIDED: aborted
        Assert.Equal(SiteState.OPEN, s.Fx.Layout.ReadMarker());
        var removed = s.Eng.Prune();
        Assert.DoesNotContain("R3", removed); Assert.DoesNotContain("R2", removed);
    }
}
