// C16 B06 with PostgreSQL (MIMAMSA_TEST_DB; locally a disposable c16b06_ database): the DB commit domain runs on the
// advisory-lock session in one transaction; lock contention through the advisory lock; LOCK LOSS (the database
// session terminated mid-transaction) fences the writer, and the next holder rolls the decided transaction forward.
// Each test uses its own schema and advisory key and drops the schema afterwards.
using Mimamsa.Core.Activation;
using Npgsql;

namespace Mimamsa.Tests.Activation;

public class ActivationPgTests
{
    static string? Dsn => Environment.GetEnvironmentVariable("MIMAMSA_TEST_DB");

    sealed class PgRig : IDisposable
    {
        public FixtureSite Site;
        public string Schema = "c16b06_" + Guid.NewGuid().ToString("N")[..10];
        public long Key = Random.Shared.NextInt64(1, long.MaxValue);
        public ActivationParticipant P;
        public PgRig(string label)
        {
            Site = FixtureSite.Simple(label, "R1", "R2", "R3");
            P = new ActivationParticipant(new SiteInspector(Site.Layout, Site.NewReader()));
            P.LoadHead();
        }

        public (ActivationEngine eng, PgAdvisoryLock lk, PgActivationDatabase db) Engine(string writer, Func<long>? clock = null, FixtureSite? site = null)
        {
            var lk = new PgAdvisoryLock(Dsn!, Key);
            var db = new PgActivationDatabase(() => lk.Connection, Schema);
            var s = site ?? Site;
            var eng = new ActivationEngine(new ActivationEngineOptions
            {
                Site = s.Layout, WriterId = writer, Database = db, Exclusions = s.NewReader(), ExternalLock = lk,
                Participant = new DirectParticipantLink(P), Disk = new FixedDiskProbe(1L << 40),
                Clock = clock ?? (() => DateTimeOffset.UtcNow.ToUnixTimeSeconds()),
            });
            return (eng, lk, db);
        }

        public void Dispose()
        {
            using (var c = new NpgsqlConnection(Dsn)) { c.Open(); using var cmd = new NpgsqlCommand($"DROP SCHEMA IF EXISTS {Schema} CASCADE", c); cmd.ExecuteNonQuery(); }
            Site.Dispose();
        }
    }

    static void Terminate(int backendPid)
    {
        using var c = new NpgsqlConnection(Dsn); c.Open();
        using var cmd = new NpgsqlCommand("SELECT pg_terminate_backend(@p)", c);
        cmd.Parameters.AddWithValue("p", backendPid);
        cmd.ExecuteNonQuery();
    }

    [Fact]
    public void Activation_applies_views_and_publication_rows_in_postgres()
    {
        if (Dsn is null) return;
        using var rig = new PgRig("pg-apply");
        var (eng, _, db) = rig.Engine("activator-1");
        using var _e = eng;
        eng.AcquireLock();
        db.EnsureSchema("R1");
        Assert.Equal("R1", db.Views());
        eng.Transition("KNOWLEDGE", "R2");
        eng.Transition("MODELS", "M2");
        Assert.Equal("R2", db.Views());
        Assert.Equal(2, db.PublicationCount());
        eng.Recover();                                    // idempotent reconciliation
        Assert.Equal(2, db.PublicationCount());
    }

    [Fact]
    public void Database_session_dropped_mid_transaction_fences_the_writer_and_the_next_holder_rolls_forward()
    {
        if (Dsn is null) return;
        using var rig = new PgRig("pg-lost");
        var (eng1, lk1, db1) = rig.Engine("activator-1");
        eng1.AcquireLock();
        db1.EnsureSchema("R1");
        int backend = lk1.BackendPid;
        eng1.Options.StepHook = s => { if (s == "DECIDED") Terminate(backend); };
        var ex = Assert.Throws<ActivationRefused>(() => eng1.Transition("KNOWLEDGE", "R2"));
        Assert.Equal("LOCK_LOST", ex.Code);
        Assert.Equal(["BEGIN", "DECIDED"], ActivationJournal.Read(rig.Site.Layout.JournalPath).Entries.Select(e => e.Step));
        Assert.False(rig.P.IsServing());
        eng1.Dispose();                                   // the fenced writer exits

        var (eng2, _, db2) = rig.Engine("activator-2");
        using var _2 = eng2;
        Assert.True(eng2.AcquireLock());                  // takeover: must recover
        eng2.Recover();
        Assert.Equal("R2", db2.Views());
        Assert.Equal(1, db2.PublicationCount());
        Assert.Equal("R2", rig.Site.Layout.ReadPointer("KNOWLEDGE"));
        Assert.True(rig.P.IsServing());
        Assert.All(ActivationJournal.Read(rig.Site.Layout.JournalPath).Entries.Skip(2), e => Assert.Equal(2, e.LockEpoch));
    }

    [Fact]
    public void Advisory_lock_contention_and_stale_holder_takeover()
    {
        if (Dsn is null) return;
        using var rig = new PgRig("pg-contend");
        using var other = FixtureSite.Simple("pg-contend-b", "R1", "R2");
        var (eng1, lk1, db1) = rig.Engine("activator-1");
        using var _1 = eng1;
        eng1.AcquireLock();
        db1.EnsureSchema("R1");
        // a writer on ANOTHER site directory (free file lock) still contends on the database advisory lock
        var (engB, _, _) = rig.Engine("activator-b", site: other);
        using var _b = engB;
        Assert.Equal("LOCK_CONTENDED", Assert.Throws<ActivationRefused>(() => engB.AcquireLock()).Code);
        // a heartbeat-stale holder on the same site is taken over: its database session is terminated
        var (eng2, _, db2) = rig.Engine("activator-2", clock: () => DateTimeOffset.UtcNow.ToUnixTimeSeconds() + 100);
        using var _2 = eng2;
        Assert.True(eng2.AcquireLock());
        Assert.Throws<ActivationRefused>(() => eng1.Lease.Authorised(() => { }));
        Assert.ThrowsAny<Exception>(() => lk1.Verify());
        eng2.Recover();
        eng2.Transition("KNOWLEDGE", "R3");
        Assert.Equal("R3", db2.Views());
    }
}
