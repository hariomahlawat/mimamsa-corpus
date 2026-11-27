// C16 B06 / I-4: the local authenticated control channel. Real named pipes (Unix sockets on Linux) in-process: the
// activation engine talks to the participant only through PipeParticipantLink -> ControlChannelServer.
using System.Text.Json.Nodes;
using Mimamsa.Core.Activation;

namespace Mimamsa.Tests.Activation;

public class ControlChannelTests
{
    sealed class Rig : IAsyncDisposable
    {
        public FixtureSite Site = FixtureSite.Simple("chan", "R1", "R2", "R3");
        public ActivationParticipant P;
        public ControlChannelServer Server;
        public string Pipe = "mimamsa-activation-test-" + Guid.NewGuid().ToString("N")[..12];
        public byte[] Secret;
        public Rig()
        {
            Secret = File.ReadAllBytes(Site.Layout.ChannelKeyPath);
            P = new ActivationParticipant(new SiteInspector(Site.Layout, Site.NewReader()));
            P.LoadHead();
            Server = new ControlChannelServer(new ControlChannelOptions { PipeName = Pipe, Secret = Secret }, P);
            Server.Start();
        }
        // A generous DEADLINE, not a delay: replies arrive in milliseconds and rejected connections are closed at once
        // (EOF), so only a host under heavy load ever comes near it. Tests that expect no server pass a short one.
        public PipeParticipantLink Link(byte[]? secret = null, double timeoutSeconds = 30) =>
            new(new ControlChannelOptions { PipeName = Pipe, Secret = secret ?? Secret, Timeout = TimeSpan.FromSeconds(timeoutSeconds) });
        public ActivationEngine Engine(IParticipantLink link) => new(new ActivationEngineOptions
        {
            Site = Site.Layout, WriterId = "activator-1", Database = Site.Db, Exclusions = Site.NewReader(), Participant = link,
            Disk = new FixedDiskProbe(1L << 40),
        });
        public async ValueTask DisposeAsync() { await Server.DisposeAsync(); Site.Dispose(); }
    }

    [Fact]
    public async Task Activation_switches_the_participant_through_the_authenticated_pipe()
    {
        await using var rig = new Rig();
        using var link = rig.Link();
        using var eng = rig.Engine(link);
        eng.AcquireLock();
        var pin = rig.P.Pin();
        eng.Transition("KNOWLEDGE", "R2");
        Assert.Equal("R2", rig.P.LoadedKnowledge);
        Assert.True(rig.P.IsServing());
        Assert.Equal(["R1"], link.PinnedGenerations(eng.Lease.Epoch)!);  // the old generation is still pinned
        rig.P.Unpin(pin);
        Assert.Empty(link.PinnedGenerations(eng.Lease.Epoch)!);
        Assert.Equal(0, rig.Server.Rejected);
    }

    [Fact]
    public async Task Unauthenticated_peer_is_refused_and_nothing_is_journaled()
    {
        await using var rig = new Rig();
        using var bad = rig.Link(secret: new byte[32]);
        using var eng = rig.Engine(bad);
        eng.AcquireLock();
        var ex = Assert.Throws<ActivationRefused>(() => eng.Transition("KNOWLEDGE", "R2"));
        Assert.Equal("PARTICIPANT_UNAVAILABLE", ex.Code);
        Assert.True(rig.Server.WaitForRejection("BAD_MAC", TimeSpan.FromSeconds(60)), "server never recorded BAD_MAC");
        Assert.Empty(ActivationJournal.Read(rig.Site.Layout.JournalPath).Entries);
        Assert.False(rig.P.Switching);
        Assert.True(rig.P.IsServing());
    }

    [Fact]
    public async Task Replayed_messages_are_refused_on_another_connection_and_on_the_same_one()
    {
        await using var rig = new Rig();
        using var eng = rig.Engine(rig.Link());
        eng.AcquireLock();
        long epoch = eng.Lease.Epoch;
        // Capture a genuine message on connection A.
        using var a = rig.Link();
        a.Connected();
        var captured = ControlEnvelope.Seal(rig.Secret, "PING", new JsonObject(), epoch, a.Session!, a.NextCounter, "tool");
        Assert.NotNull(a.SendRaw(captured));                                  // accepted once
        Assert.Null(a.SendRaw(captured));                                     // same connection, same counter: dropped
        Assert.True(rig.Server.WaitForRejection("REPLAY_COUNTER", TimeSpan.FromSeconds(60)), "server never recorded REPLAY_COUNTER");
        using var b = rig.Link();
        b.Connected();
        Assert.Null(b.SendRaw(captured));                                     // another connection: other session nonce
        Assert.True(rig.Server.WaitForRejection("REPLAY_OTHER_SESSION", TimeSpan.FromSeconds(60)), "server never recorded REPLAY_OTHER_SESSION");
        Assert.False(rig.P.Switching);
    }

    [Fact]
    public async Task Lower_or_foreign_lock_epoch_is_rejected()
    {
        await using var rig = new Rig();
        using var link = rig.Link();
        using var eng = rig.Engine(link);
        eng.AcquireLock();
        eng.AcquireLock();                                                    // epoch 2
        Assert.Throws<ParticipantUnavailableException>(() => link.EnterSwitching("TX-00000001-aaaaaaaaaaaa", 1));
        Assert.True(rig.Server.WaitForRejection("STALE_EPOCH", TimeSpan.FromSeconds(60)), "server never recorded STALE_EPOCH");
        Assert.Throws<ParticipantUnavailableException>(() => link.EnterSwitching("TX-00000001-aaaaaaaaaaaa", 7));
        Assert.False(rig.P.Switching);
        link.Ping(2);
    }

    [Fact]
    public async Task Connection_from_a_process_that_is_not_the_lock_holder_is_refused_on_windows()
    {
        if (!OperatingSystem.IsWindows()) return;   // pid check is Windows-only (Linux: CurrentUserOnly socket)
        await using var rig = new Rig();
        using var link = rig.Link();
        // nobody holds the lock: the connecting process cannot be the holder
        Assert.Throws<ParticipantUnavailableException>(() => link.Ping(0));
        Assert.True(rig.Server.WaitForRejection("PEER_NOT_LOCK_HOLDER", TimeSpan.FromSeconds(60)), "server never recorded PEER_NOT_LOCK_HOLDER");
    }

    [Fact]
    public async Task Participant_lost_before_BEGIN_refuses_the_transition()
    {
        await using var rig = new Rig();
        using var link = rig.Link(timeoutSeconds: 2);   // no server: the connect attempt must give up
        using var eng = rig.Engine(link);
        eng.AcquireLock();
        await rig.Server.DisposeAsync();
        Assert.Equal("PARTICIPANT_UNAVAILABLE", Assert.Throws<ActivationRefused>(() => eng.Transition("KNOWLEDGE", "R2")).Code);
        Assert.Empty(ActivationJournal.Read(rig.Site.Layout.JournalPath).Entries);
        Assert.Equal("R1", rig.Site.Layout.ReadPointer("KNOWLEDGE"));
    }
}
