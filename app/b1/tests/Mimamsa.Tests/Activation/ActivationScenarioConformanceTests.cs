// C16 B06 differential conformance: the SAME shared scenario files SC01..SC25
// (app/contract/fixtures/c16/v2_1/activation_scenarios, produced by scenarios.run_scenario over the reference model
// activation.py) are run through the .NET implementation, and the observable trace after every step must equal the
// expected-outcomes file exactly; the expected errors and the assert_final invariants must hold too.
//
// What runs is the real implementation on a real on-disk site: the fsync'd hash-chained journal, the writer lease
// (OS file locks, lock record, epochs), pointer files, the file database domain, the activation log, the generation
// catalogue, and the I-6 reader over a REAL Ed25519-signed ExclusionStore. Each scenario "writer" is a separate engine
// instance (a separate lease session); process_die releases that instance's OS lease lock as a dead process would.
// Harness mapping (documented, not a semantic change): the site starts with a signed baseline exclusion update at
// store sequence 1 (Python's load_latest refuses a store with no accepted state), so scenario sequence n is store
// sequence n + 1. The participant is the in-process ActivationParticipant behind a DirectParticipantLink; the pipe
// transport is tested separately (ControlChannelTests) and across processes in the crash suite.
using System.Text;
using System.Text.Json.Nodes;
using Mimamsa.Core.Activation;

namespace Mimamsa.Tests.Activation;

public sealed class ScenarioHarness : IDisposable
{
    readonly JsonObject _scn;
    readonly FixtureSite _site;
    readonly Dictionary<string, ActivationEngine> _writers = new(StringComparer.Ordinal);
    readonly ActivationParticipant _participant;
    readonly DirectParticipantLink _link;
    readonly SiteInspector _observer;
    readonly Dictionary<string, byte[]> _backups = new(StringComparer.Ordinal);
    readonly List<ReaderPin> _pins = [];
    readonly long _baseline;
    readonly long _staleAfter;
    readonly int _keep;
    readonly string? _recoveryTarget;
    readonly long _free;
    readonly bool _observeSemantic;
    long _clock;
    JsonArray? _lastResponse;
    string Snapshot => Path.Combine(_site.Root, "exclusions.snapshot");

    public ScenarioHarness(JsonObject scenario)
    {
        _scn = scenario;
        var init = scenario["initial"]!.AsObject();
        var installed = init["installed"]!.AsArray().Select(x => (string)x!).ToList();
        // As activation.Site: the active model (when not null) is staged verified with vectors for every installed
        // generation, unless initial.staged_models describes it explicitly.
        var activeModel = (string?)init["models"];
        var models = new Dictionary<string, (bool, string[])>(StringComparer.Ordinal);
        if (activeModel is not null) models[activeModel] = (true, installed.ToArray());
        foreach (var (k, v) in init["staged_models"]!.AsObject())
            models[k] = ((bool)v!["verified"]!, v["vectors_for"]!.AsArray().Select(x => (string)x!).ToArray());
        var sizes = init["sizes"]!.AsObject().ToDictionary(kv => kv.Key, kv => (long)kv.Value!);
        // 2.1 (SC26+): lexical_only generations are classified as such when staged; its presence adds semantic_search
        // to the observed trace (SC01-SC25 traces are unchanged).
        _observeSemantic = init.ContainsKey("lexical_only");
        var lexical = init["lexical_only"]?.AsArray().Select(x => (string)x!).ToList() ?? [];
        _site = new FixtureSite("scn-" + ((string)scenario["scenario_id"]!)[..4], installed, (string)init["active"]!, activeModel, models, sizes, lexical);
        _baseline = _site.Store.Sequence;
        _staleAfter = (long)init["lock_stale_after_seconds"]!;
        _keep = (int)(long)init["keep_previous"]!;
        _recoveryTarget = (string?)init["recovery_target"];
        _free = (long)init["free_bytes"]!;
        _participant = new ActivationParticipant(new SiteInspector(_site.Layout, _site.NewReader()));
        _participant.LoadHead();
        _link = new DirectParticipantLink(_participant);
        _observer = _participant.Site;
    }

    ActivationEngine Writer(string id)
    {
        if (!_writers.TryGetValue(id, out var e))
        {
            e = new ActivationEngine(new ActivationEngineOptions
            {
                Site = _site.Layout, WriterId = id, Database = _site.Db, Exclusions = _site.NewReader(), Participant = _link,
                Clock = () => _clock, StaleAfterSeconds = _staleAfter, KeepPrevious = _keep, RecoveryTarget = _recoveryTarget,
                Disk = new FixedDiskProbe(_free), HeadroomFraction = 0.1,
            });
            _writers[id] = e;
        }
        return e;
    }

    ActivationEngine Holder()
    {
        var rec = WriterLease.ReadRecord(_site.Layout);
        return rec is { Held: true, WriterId: { } w } ? Writer(w) : Writer("activator-harness");
    }

    void AcceptExclusion(IEnumerable<string> items)
    {
        ActivationEngine.AcceptExclusion(_site.Layout, _observer, () =>
        {
            var h = _observer.ReadExclusions().Health;
            if (h is ExclusionHealth.MISSING or ExclusionHealth.BAD_SIGNATURE) throw new ActivationRefused("EXCLUSIONS_UNAVAILABLE", h.ToString());
            _site.Store.Append(items);
        });
    }

    void SnapshotStore()
    {
        if (Directory.Exists(Snapshot)) return;
        CopyDir(_site.Layout.ExclusionsDir, Snapshot);
    }

    static void CopyDir(string from, string to)
    {
        Directory.CreateDirectory(to);
        foreach (var f in Directory.GetFiles(from)) File.Copy(f, Path.Combine(to, Path.GetFileName(f)), true);
        foreach (var d in Directory.GetDirectories(from)) CopyDir(d, Path.Combine(to, Path.GetFileName(d)));
    }

    public void Op(string name, JsonObject a)
    {
        string W() => (string)a["writer"]!;
        switch (name)
        {
            case "lock_acquire": Writer(W()).AcquireLock(); break;
            case "lock_release": Writer(W()).ReleaseLock(); break;
            case "process_die": Writer(W()).Lease.SimulateDeath(); break;
            case "clock_advance": _clock += (long)a["seconds"]!; break;
            case "participant_lose": _link.Up = false; break;
            case "participant_restore": _link.Up = true; _participant.LoadHead(); break;
            case "transition":
                var eng = Writer(W());
                string? crash = (string?)a["crash_after"], exAt = (string?)a["exclusion_at_step"], lostAt = (string?)a["participant_lost_at"];
                var items = a["exclusion_items"]?.AsArray().Select(x => (string)x!).ToList();
                eng.Options.StepHook = step =>
                {
                    if (exAt == step) AcceptExclusion(items!);
                    if (lostAt == step) _link.Up = false;
                    if (crash == step) throw new ActivationCrash(step);
                };
                try { eng.Transition((string)a["target"]!, (string)a["to"]!, (string?)a["action"] ?? "ACTIVATE"); }
                finally { eng.Options.StepHook = null; }
                break;
            case "recover": Writer(W()).Recover(); break;
            case "pin": _pins.Add(_participant.Pin()); break;
            case "unpin":
                var i = (int?)(long?)a["index"] ?? 0;
                _participant.Unpin(_pins[i]); _pins.RemoveAt(i);
                break;
            case "respond":
                var r = _participant.Respond(_pins[(int?)(long?)a["index"] ?? 0], a["items"]!.AsArray().Select(x => (string)x!));
                _lastResponse = new JsonArray(r.Select(x => (JsonNode?)JsonValue.Create(x)).ToArray());
                break;
            case "accept_exclusion": AcceptExclusion(a["items"]!.AsArray().Select(x => (string)x!)); break;
            case "prune": Holder().Prune(); break;
            case "backup": _backups[(string)a["name"]!] = _site.Db.Backup(); break;
            case "restore": Writer(W()).Restore(_backups[(string)a["name"]!]); break;
            case "tear_journal_tail":
                var jp = _site.Layout.JournalPath;
                var bytes = File.ReadAllBytes(jp);
                if (bytes.Length > 0)
                {
                    int lastStart = Array.LastIndexOf(bytes, (byte)'\n', bytes.Length - 2) + 1;   // start of the last line
                    int keep = lastStart + (bytes.Length - lastStart) / 2;                         // half of it, no LF
                    using var f = new FileStream(jp, FileMode.Open, FileAccess.Write);
                    f.SetLength(keep);
                }
                _observer.InvalidateCache();
                break;
            case "corrupt_journal_middle":
                var jp2 = _site.Layout.JournalPath;
                var lines = File.ReadAllText(jp2, Encoding.UTF8).Split('\n');
                lines[1] = lines[1].Replace("\"at\":\"2", "\"at\":\"1");   // still canonical JSON; breaks the chain
                File.WriteAllText(jp2, string.Join('\n', lines), new UTF8Encoding(false));
                _observer.InvalidateCache();
                break;
            case "exclusion_store_remove":
                SnapshotStore();
                Directory.Delete(_site.Layout.ExclusionsDir, true);
                break;
            case "exclusion_store_restore":
                if (Directory.Exists(Snapshot))
                {
                    if (Directory.Exists(_site.Layout.ExclusionsDir)) Directory.Delete(_site.Layout.ExclusionsDir, true);
                    CopyDir(Snapshot, _site.Layout.ExclusionsDir);
                    Directory.Delete(Snapshot, true);
                }
                break;
            case "exclusion_store_regress":
                SnapshotStore();
                if (_site.Store.Sequence > _baseline) _site.Store.RegressOne();
                break;
            case "exclusion_signature_invalidate":
                SnapshotStore();
                _site.Store.InvalidateSignature();
                break;
            default: throw new InvalidOperationException("unknown op " + name);
        }
    }

    public JsonObject Observe(int step, string? error)
    {
        _observer.InvalidateCache();
        var s = _site.Layout;
        var knowledge = s.ReadPointer("KNOWLEDGE");
        var ex = _observer.ReadExclusions();
        JsonArray steps;
        try { steps = new JsonArray(_observer.Journal().Entries.Select(e => (JsonNode?)JsonValue.Create(e.Step)).ToArray()); }
        catch (JournalCorruptException) { steps = new JsonArray(ActivationJournal.DiagnosticSteps(s.JournalPath).Select(x => (JsonNode?)JsonValue.Create(x)).ToArray()); }
        var applied = s.ReadApplied();
        var inst = new JsonArray(_observer.Catalog.Installed().Order(StringComparer.Ordinal).Select(x => (JsonNode?)JsonValue.Create(x)).ToArray());
        var o = new JsonObject
        {
            ["step"] = step, ["error"] = error, ["knowledge"] = knowledge, ["models"] = s.ReadPointer("MODELS"),
            ["views"] = _site.Db.Views(), ["state"] = _observer.State().ToString(), ["serving"] = _link.Up && _participant.IsServing(),
            ["journal_steps"] = steps, ["publication_rows"] = _site.Db.PublicationCount(),
            ["log_length"] = new ActivationLog(s.ActivationLogPath).Read().Count,
            ["active_exclusion_seq"] = knowledge is not null && applied.TryGetValue(knowledge, out var av) ? av - _baseline : null,
            ["store_seq"] = ex.Sequence is { } sq ? sq - _baseline : null,
            ["installed"] = inst, ["pins"] = _pins.Count,
            ["temp_empty"] = !Directory.Exists(s.ScratchDir) || !Directory.EnumerateFileSystemEntries(s.ScratchDir).Any(),
            ["exclusion_reader"] = ex.Health.ToString(), ["lock_epoch"] = WriterLease.CurrentEpoch(s),
            ["response"] = _lastResponse?.DeepClone(),
        };
        if (_observeSemantic) o["semantic_search"] = (bool)o["serving"]! && _observer.SemanticSearchEnabled();
        return o;
    }

    /// Run the scenario; returns the trace. Throws with a precise message on an unexpected error.
    public JsonArray Run()
    {
        var trace = new JsonArray { Observe(0, null) };
        int i = 0;
        foreach (var st in _scn["steps"]!.AsArray())
        {
            i++;
            var o = st!.AsObject();
            string? err = null;
            try { Op((string)o["op"]!, o["args"]!.AsObject()); }
            catch (ActivationRefused) { err = "Refused"; }
            catch (ActivationCrash) { err = "Crash"; }
            var want = (string?)o["expect_error"];
            if (err != want) throw new Xunit.Sdk.XunitException($"{_scn["scenario_id"]} step {i} ({o["op"]}): expected {want ?? "no error"}, got {err ?? "no error"}");
            trace.Add(Observe(i, err));
        }
        return trace;
    }

    public void Dispose()
    {
        foreach (var w in _writers.Values) w.Dispose();
        _site.Dispose();
    }
}

public class ActivationScenarioConformanceTests
{
    static string Dir => TestDirs.RepoFile("app", "contract", "fixtures", "c16", "v2_1", "activation_scenarios");

    public static IEnumerable<object[]> Scenarios() =>
        Directory.GetFiles(Dir, "SC*.json").Where(f => !f.EndsWith(".expected.json", StringComparison.Ordinal))
            .Select(f => new object[] { Path.GetFileNameWithoutExtension(f) }).OrderBy(x => (string)x[0], StringComparer.Ordinal);

    [Fact]
    public void Every_shared_scenario_in_the_fixture_directory_is_present_with_its_expected_outcome()
    {
        // The full set comes from the contract fixture directory (SC01-SC31 at 2.1 f653c4b8): contiguous, none skipped,
        // and every scenario has its reference outcome. The theory below runs each of them.
        var ids = Scenarios().Select(x => ((string)x[0])[..4]).ToList();
        Assert.True(ids.Count >= 31, $"expected at least SC01-SC31, found {ids.Count}");
        Assert.Equal(Enumerable.Range(1, ids.Count).Select(n => $"SC{n:D2}"), ids);
        foreach (var x in Scenarios()) Assert.True(File.Exists(Path.Combine(Dir, (string)x[0] + ".expected.json")), (string)x[0]);
    }

    [Theory]
    [MemberData(nameof(Scenarios))]
    public void Dotnet_implementation_reproduces_the_reference_trace(string id)
    {
        var scn = JsonNode.Parse(File.ReadAllText(Path.Combine(Dir, id + ".json")))!.AsObject();
        var exp = JsonNode.Parse(File.ReadAllText(Path.Combine(Dir, id + ".expected.json")))!.AsObject();
        // The expected outcomes are bound to this exact scenario by its canonical sha256.
        Assert.Equal((string)exp["scenario_sha256"]!, CanonicalJson.RecordSha256(scn));
        using var h = new ScenarioHarness(scn);
        var trace = h.Run();
        var want = exp["trace"]!.AsArray();
        Assert.Equal(want.Count, trace.Count);
        for (int i = 0; i < want.Count; i++)
        {
            var w = Encoding.UTF8.GetString(CanonicalJson.Bytes(want[i]));
            var g = Encoding.UTF8.GetString(CanonicalJson.Bytes(trace[i]));
            if (w != g) throw new Xunit.Sdk.XunitException($"{id} step {i}:\n expected {w}\n got      {g}");
        }
        // assert_final invariants (scenarios.final_assertion_failures)
        var last = trace[^1]!.AsObject();
        var names = new Dictionary<string, string> { ["knowledge"] = "knowledge", ["models"] = "models", ["serving"] = "serving", ["installed"] = "installed",
            ["log_length"] = "log_length", ["last_response"] = "response", ["temp_empty"] = "temp_empty", ["semantic_search"] = "semantic_search" };
        foreach (var (k, v) in scn["assert_final"]!.AsObject())
        {
            var wantV = k == "installed" ? new JsonArray(v!.AsArray().Select(x => (string)x!).Order(StringComparer.Ordinal).Select(x => (JsonNode?)JsonValue.Create(x)).ToArray()) : v;
            Assert.Equal(Encoding.UTF8.GetString(CanonicalJson.Bytes(wantV)), Encoding.UTF8.GetString(CanonicalJson.Bytes(last[names[k]])));
        }
    }
}
