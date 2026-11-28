// C16 B06 process-level crash suite (FG-JOURNAL-DURABILITY, protocol and process-crash level only).
// Real processes: the activation tool (test host build of the same CLI, with named pause points) is KILLED
// (Process.Kill = TerminateProcess on Windows, SIGKILL on Linux) at each journal boundary and inside steps, then the
// PRODUCTION tool recovers (twice: idempotent). A separate stand-in web process (participant-host) runs the
// ActivationParticipant behind the authenticated pipe. Covers: kills at every boundary, kills during recovery, random
// offsets (seeded), a second tool instance, takeover of a killed holder, participant loss after the acknowledgement, a
// stale web process, an exclusion accepted mid-switch, and exclusion acceptance contending with the tool's lock.
// Not covered (cannot be in CI): power loss and storage-cache behaviour (host-level drills, OG-8).
using System.Collections.Concurrent;
using System.Diagnostics;
using System.Text.Json.Nodes;
using Mimamsa.Core.Activation;

namespace Mimamsa.Tests.Activation;

sealed class Proc : IDisposable
{
    public Process P { get; }
    readonly BlockingCollection<string> _lines = new();
    public List<string> All { get; } = [];
    public System.Text.StringBuilder Err { get; } = new();

    Proc(Process p)
    {
        P = p;
        p.OutputDataReceived += (_, e) => { if (e.Data is not null) { lock (All) All.Add(e.Data); _lines.Add(e.Data); } };
        p.ErrorDataReceived += (_, e) => { if (e.Data is not null) lock (Err) Err.AppendLine(e.Data); };
        p.BeginOutputReadLine(); p.BeginErrorReadLine();
    }

    static string Config => new DirectoryInfo(AppContext.BaseDirectory).Parent!.Name;   // bin/<Config>/net10.0
    public static string ToolDll => TestDirs.RepoFile("app", "b1", "src", "Mimamsa.Activation", "bin", Config, "net10.0", "Mimamsa.Activation.dll");
    public static string HostDll => TestDirs.RepoFile("app", "b1", "tests", "Mimamsa.Activation.TestHost", "bin", Config, "net10.0", "Mimamsa.Activation.TestHost.dll");

    public static Proc Start(string dll, IEnumerable<string> args, IDictionary<string, string>? env = null)
    {
        var psi = new ProcessStartInfo("dotnet") { RedirectStandardOutput = true, RedirectStandardError = true, RedirectStandardInput = true, UseShellExecute = false };
        psi.ArgumentList.Add(dll);
        foreach (var a in args) psi.ArgumentList.Add(a);
        foreach (var k in new[] { "MIMAMSA_ACTIVATION_PAUSE_AT", "MIMAMSA_ACTIVATION_CONTINUE_FILE", "MIMAMSA_ACTIVATION_STEP_DELAY_MS" }) psi.Environment.Remove(k);
        if (env is not null) foreach (var (k, v) in env) psi.Environment[k] = v;
        return new Proc(Process.Start(psi)!);
    }

    public string WaitFor(Func<string, bool> pred, int seconds = 60)
    {
        var deadline = DateTime.UtcNow.AddSeconds(seconds);
        while (DateTime.UtcNow < deadline)
        {
            if (_lines.TryTake(out var l, 200) && pred(l)) return l;
            if (P.HasExited && _lines.Count == 0) break;
        }
        throw new Xunit.Sdk.XunitException("timed out waiting for output; stdout: " + string.Join(" | ", All) + " stderr: " + Err);
    }

    public string Ask(string line)
    {
        P.StandardInput.WriteLine(line);
        P.StandardInput.Flush();
        return WaitFor(l => l.StartsWith('{') || l == "RELOADED");
    }

    public int Exit(int seconds = 60)
    {
        if (!P.WaitForExit(seconds * 1000)) { Kill(); throw new Xunit.Sdk.XunitException("process did not exit; stdout: " + string.Join(" | ", All)); }
        P.WaitForExit();
        return P.ExitCode;
    }

    public void Kill() { try { P.Kill(entireProcessTree: true); } catch (InvalidOperationException) { } P.WaitForExit(); }

    public void Dispose()
    {
        if (!P.HasExited) { try { P.StandardInput.Close(); } catch (Exception) { } if (!P.WaitForExit(3000)) Kill(); }
        P.Dispose();
    }
}

public class ActivationCrashTests
{
    sealed class Rig : IDisposable
    {
        public FixtureSite Site = FixtureSite.Simple("crash", "R1", "R2", "R3");
        public string Pipe = "mimamsa-activation-crash-" + Guid.NewGuid().ToString("N")[..12];
        public Proc? Web;
        public string S => Site.Root;

        public Proc StartWeb(string? pipe = null)
        {
            var w = Proc.Start(Proc.HostDll, ["participant-host", "--site", S, "--pipe", pipe ?? Pipe, "--development"]);
            w.WaitFor(l => l == "READY");
            if (pipe is null) Web = w;
            return w;
        }

        // Channel timeout is a deadline for a live participant (replies take milliseconds); 30 s absorbs a loaded host.
        public string[] Common(string writer, int channelTimeout = 30) =>
            ["--site", S, "--pipe", Pipe, "--writer", writer, "--development", "--channel-timeout", channelTimeout.ToString()];

        public Proc Host(string cmd, string writer, int channelTimeout, IDictionary<string, string>? env, params string[] extra) =>
            Proc.Start(Proc.HostDll, [cmd, .. Common(writer, channelTimeout), .. extra], env);

        public Proc Host(string cmd, string writer, IDictionary<string, string>? env = null, params string[] extra) =>
            Proc.Start(Proc.HostDll, [cmd, .. Common(writer), .. extra], env);

        public (int code, JsonObject json) Tool(string cmd, string writer, params string[] extra)
        {
            using var p = Proc.Start(Proc.ToolDll, [cmd, .. Common(writer), .. extra]);
            int code = p.Exit();
            var last = p.All.LastOrDefault(l => l.StartsWith('{')) ?? throw new Xunit.Sdk.XunitException("no JSON from tool; stderr: " + p.Err);
            return (code, JsonNode.Parse(last)!.AsObject());
        }

        public JsonObject Status()
        {
            using var p = Proc.Start(Proc.ToolDll, ["status", "--site", S, "--development"]);
            p.Exit();
            return JsonNode.Parse(p.All.Last(l => l.StartsWith('{')))!.AsObject();
        }

        public JsonObject WebStatus() => JsonNode.Parse(Web!.Ask("status"))!.AsObject();

        public void Dispose() { Web?.Dispose(); Site.Dispose(); }
    }

    static Dictionary<string, string> PauseAt(string step, string? continueFile = null)
    {
        var d = new Dictionary<string, string> { ["MIMAMSA_ACTIVATION_PAUSE_AT"] = step };
        if (continueFile is not null) d["MIMAMSA_ACTIVATION_CONTINUE_FILE"] = continueFile;
        return d;
    }

    /// The site is consistent and OPEN on `expect`: pointer, views and the participant agree with the journal head,
    /// no transaction in flight, scratch empty, publication rows and log records only for committed transactions.
    static void AssertRecoveredOn(Rig rig, string expect, int committed)
    {
        var st = rig.Status();
        Assert.Equal("OPEN", (string?)st["state"]);
        Assert.Equal(expect, (string?)st["knowledge"]);
        Assert.Equal(expect, (string?)st["views"]);
        Assert.Null((string?)st["in_flight"]);
        Assert.False((bool)st["torn_tail"]!);
        Assert.True((bool)st["temp_empty"]!);
        Assert.Equal(committed, (int)st["publication_rows"]!);
        Assert.Equal(committed, (int)st["log_length"]!);
        var steps = st["journal_steps"]!.AsArray().Select(x => (string)x!).ToList();
        Assert.Equal(committed, steps.Count(s => s == "OPEN"));
        Assert.Equal(steps.Count(s => s == "BEGIN"), steps.Count(s => s is "OPEN" or "ABORTED"));
        var w = rig.WebStatus();
        Assert.True((bool)w["serving"]!, w.ToJsonString());
        Assert.Equal(expect, (string?)w["loaded"]);
    }

    public static IEnumerable<object[]> Boundaries() =>
    [
        ["BEGIN:marker", "R1", 0], ["BEGIN", "R1", 0], ["DECIDED", "R2", 1], ["DB_APPLIED", "R2", 1],
        ["POINTER_WRITTEN:inside", "R2", 1], ["POINTER_WRITTEN", "R2", 1], ["EXCLUSIONS_APPLIED", "R2", 1],
        ["LOGGED", "R2", 1], ["OPEN", "R2", 1],
    ];

    [Theory]
    [MemberData(nameof(Boundaries))]
    public void Killed_at_a_boundary_the_web_refuses_then_recovery_rolls_forward_or_aborts_idempotently(string step, string expect, int committed)
    {
        using var rig = new Rig();
        rig.StartWeb();
        using (var tool = rig.Host("activate", "activator-1", PauseAt(step), "--to", "R2"))
        {
            tool.WaitFor(l => l == "PAUSED " + step);
            Assert.False((bool)rig.WebStatus()["serving"]!);         // admission stopped from ACK_SWITCHING on
            tool.Kill();                                              // TerminateProcess / SIGKILL
        }
        var w = rig.WebStatus();
        Assert.False((bool)w["serving"]!, w.ToJsonString());         // a transaction is in flight: refuse to serve
        Assert.NotEqual("OPEN", (string?)rig.Status()["state"]);
        // A new tool process takes over the dead holder's lock and recovers; then recovery again changes nothing.
        var (c1, r1) = rig.Tool("recover", "activator-2");
        Assert.Equal(0, c1);
        Assert.True((bool)r1["ok"]!, r1.ToJsonString());
        var after1 = rig.Status();
        var (c2, _) = rig.Tool("recover", "activator-2");
        Assert.Equal(0, c2);
        var after2 = rig.Status();
        after1.Remove("lock_epoch"); after2.Remove("lock_epoch");
        Assert.Equal(after1.ToJsonString(), after2.ToJsonString());
        AssertRecoveredOn(rig, expect, committed);
    }

    [Fact]
    public void Killed_during_recovery_then_recovered()
    {
        using var rig = new Rig();
        rig.StartWeb();
        using (var tool = rig.Host("activate", "activator-1", PauseAt("DECIDED"), "--to", "R2")) { tool.WaitFor(l => l == "PAUSED DECIDED"); tool.Kill(); }
        foreach (var step in new[] { "recover:DB_APPLIED", "recover:POINTER_WRITTEN", "recover:reconciled" })
            using (var rec = rig.Host("recover", "activator-2", PauseAt(step))) { rec.WaitFor(l => l == "PAUSED " + step); rec.Kill(); }
        Assert.False((bool)rig.WebStatus()["serving"]!);
        Assert.Equal(0, rig.Tool("recover", "activator-3").code);
        AssertRecoveredOn(rig, "R2", 1);
    }

    [Fact]
    public void A_second_tool_instance_is_refused_while_the_holder_lives_and_takes_over_once_it_is_killed()
    {
        using var rig = new Rig();
        rig.StartWeb();
        using var holder = rig.Host("activate", "activator-1", PauseAt("DB_APPLIED"), "--to", "R2");
        holder.WaitFor(l => l == "PAUSED DB_APPLIED");
        var (code, res) = rig.Tool("activate", "activator-2", "--to", "R3");
        Assert.Equal(2, code);
        Assert.Equal("LOCK_CONTENDED", (string?)res["code"]);
        holder.Kill();
        var (code2, res2) = rig.Tool("activate", "activator-2", "--to", "R3");      // takeover, recover (R2), then R3
        Assert.Equal(0, code2);
        Assert.Equal("R3", (string?)res2["knowledge"]);
        Assert.Equal(2, (long)res2["lock_epoch"]!);
        AssertRecoveredOn(rig, "R3", 2);
    }

    [Fact]
    public void Participant_lost_after_the_acknowledgement_the_decision_stands_and_web_processes_serve_only_the_head()
    {
        using var rig = new Rig();
        rig.StartWeb();
        using var stale = rig.StartWeb(pipe: rig.Pipe + "-stale");          // a web process that never hears OPEN
        Assert.True((bool)JsonNode.Parse(stale.Ask("status"))!["serving"]!);
        var cont = Path.Combine(rig.S, "continue");
        using var tool = rig.Host("activate", "activator-1", 5, PauseAt("DECIDED", cont), "--to", "R2");   // OPEN to the dead participant gives up after 5 s
        tool.WaitFor(l => l == "PAUSED DECIDED");
        rig.Web!.Kill();                                                       // participant dies after ACK_SWITCHING
        File.WriteAllText(cont, "go");
        Assert.Equal(0, tool.Exit());                                          // rolls forward; OPEN not acknowledged
        Assert.Equal("R2", (string?)rig.Status()["knowledge"]);
        // The stale web process still holds R1: it must not serve.
        var s = JsonNode.Parse(stale.Ask("status"))!.AsObject();
        Assert.False((bool)s["serving"]!);
        Assert.Equal("NOT_ON_JOURNAL_HEAD", (string?)s["reason"]);
        // A restarted web process loads the journal head before serving.
        rig.Web.Dispose();
        rig.StartWeb();
        AssertRecoveredOn(rig, "R2", 1);
        stale.Ask("reload");
        Assert.True((bool)JsonNode.Parse(stale.Ask("status"))!["serving"]!);
    }

    [Fact]
    public void No_participant_before_BEGIN_refuses_and_journals_nothing()
    {
        using var rig = new Rig();
        var (code, res) = rig.Tool("activate", "activator-1", "--to", "R2", "--channel-timeout", "1");
        Assert.Equal(2, code);
        Assert.Equal("PARTICIPANT_UNAVAILABLE", (string?)res["code"]);
        var st = rig.Status();
        Assert.Empty(st["journal_steps"]!.AsArray());
        Assert.Equal("R1", (string?)st["knowledge"]);
    }

    [Fact]
    public void Exclusion_accepted_mid_switch_is_applied_before_exposure_and_contends_with_the_tool_lock()
    {
        using var rig = new Rig();
        rig.StartWeb();
        var insp = new SiteInspector(rig.Site.Layout, rig.Site.NewReader());
        var cont = Path.Combine(rig.S, "continue");
        // 1. paused INSIDE a guarded step: acceptance cannot get the lock (cross-process contention)
        using (var tool = rig.Host("activate", "activator-1", PauseAt("POINTER_WRITTEN:inside", cont), "--to", "R2"))
        {
            tool.WaitFor(l => l == "PAUSED POINTER_WRITTEN:inside");
            var ex = Assert.Throws<ActivationRefused>(() =>
                ActivationEngine.AcceptExclusion(rig.Site.Layout, insp, () => rig.Site.Store.Append(["doc-x"]), TimeSpan.FromMilliseconds(500)));
            Assert.Equal("LOCK_CONTENDED", ex.Code);
            File.WriteAllText(cont, "go");
            Assert.Equal(0, tool.Exit());
        }
        File.Delete(cont);
        // 2. paused BETWEEN steps of the next switch: acceptance proceeds, is not applied while SWITCHING, and OPEN
        //    applies the newest state to every generation before anything is served.
        using (var tool = rig.Host("activate", "activator-1", PauseAt("LOGGED", cont), "--to", "R3"))
        {
            tool.WaitFor(l => l == "PAUSED LOGGED");
            long before = rig.Site.Layout.ReadApplied()["R3"];
            ActivationEngine.AcceptExclusion(rig.Site.Layout, insp, () => rig.Site.Store.Append(["doc-x"]));
            Assert.Equal(before, rig.Site.Layout.ReadApplied()["R3"]);
            File.WriteAllText(cont, "go");
            Assert.Equal(0, tool.Exit());
        }
        var seq = rig.Site.Store.Sequence;
        Assert.All(rig.Site.Layout.ReadApplied().Values, v => Assert.Equal(seq, v));
        Assert.Equal(seq, ActivationJournal.Read(rig.Site.Layout.JournalPath).Entries[^1].ExclusionSeq);
        AssertRecoveredOn(rig, "R3", 2);
    }

    [Fact]
    public void Random_offset_kills_always_recover_to_a_consistent_generation()
    {
        // N seeded runs; N is reported, not claimed exhaustive. Test host with a per-step delay, then the production
        // tool (no hooks) at random offsets as well.
        const int N = 6;
        var rnd = new Random(20261127);
        for (int i = 0; i < N + 3; i++)
        {
            using var rig = new Rig();
            rig.StartWeb();
            bool production = i >= N;
            var p = production
                ? Proc.Start(Proc.ToolDll, ["activate", .. rig.Common("activator-1"), "--to", "R2"])
                : rig.Host("activate", "activator-1", new Dictionary<string, string> { ["MIMAMSA_ACTIVATION_STEP_DELAY_MS"] = "40" }, "--to", "R2");
            Thread.Sleep(rnd.Next(production ? 150 : 200, production ? 700 : 900));
            p.Kill();
            p.Dispose();
            Assert.Equal(0, rig.Tool("recover", "activator-2").code);
            var k = (string)rig.Status()["knowledge"]!;
            Assert.Contains(k, new[] { "R1", "R2" });
            AssertRecoveredOn(rig, k, k == "R2" ? 1 : 0);
        }
    }

    [Fact]
    public void Production_tool_end_to_end_and_it_carries_no_pause_hooks()
    {
        var src = File.ReadAllText(TestDirs.RepoFile("app", "b1", "src", "Mimamsa.Activation", "Program.cs"));
        Assert.DoesNotContain("MIMAMSA_ACTIVATION_PAUSE", src);
        Assert.Contains("stepHook: null", src);
        using var rig = new Rig();
        rig.StartWeb();
        Assert.Equal(0, rig.Tool("activate", "activator-1", "--to", "R2").code);
        Assert.Equal(0, rig.Tool("activate", "activator-1", "--to", "R3").code);
        Assert.Equal(0, rig.Tool("rollback", "activator-1", "--to", "R2").code);
        var (pc, pf) = rig.Tool("preflight", "activator-1", "--to", "R1");
        Assert.Equal(0, pc);
        Assert.Equal("PASS", (string?)pf["code"]);
        var (_, pr) = rig.Tool("prune", "activator-1");
        Assert.Empty(pr["removed"]!.AsArray());                               // R1, R3 are the two previous distinct
        var (mc, mres) = rig.Tool("activate", "activator-1", "--target", "MODELS", "--to", "M2");
        Assert.Equal(0, mc);
        Assert.Equal("M2", (string?)mres["models"]);
        AssertRecoveredOn(rig, "R2", 4);
    }
}
