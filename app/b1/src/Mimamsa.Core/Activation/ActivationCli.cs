// C16 B06: the activation tool's command line (interface IF-6: activate, rollback, recover, preflight, prune, plus
// status and a development-site init). The production executable (Mimamsa.Activation) passes no step hooks; the test
// host passes pause hooks for the process-kill crash suite.
// Every mutating command takes the single-writer lock and runs recover() first (I-4: recovery at every start).
// Output: one JSON object on stdout. Exit codes: 0 ok, 2 refused, 3 failed closed (journal corrupt), 1 usage/error.
// Secrets (database connection string, channel key) never appear on the command line: the connection string is read
// from the environment variable named by --pg-env, the channel key from a file.
using System.Text.Json.Nodes;

namespace Mimamsa.Core.Activation;

public static class ActivationCli
{
    public sealed class Args
    {
        readonly Dictionary<string, string> _kv = new(StringComparer.Ordinal);
        public string Command { get; }
        public Args(string[] a)
        {
            if (a.Length == 0) throw new ArgumentException("usage: <command> --site <dir> [options]");
            Command = a[0];
            for (int i = 1; i < a.Length; i++)
            {
                if (!a[i].StartsWith("--", StringComparison.Ordinal)) throw new ArgumentException("unexpected argument " + a[i]);
                var k = a[i][2..];
                _kv[k] = i + 1 < a.Length && !a[i + 1].StartsWith("--", StringComparison.Ordinal) ? a[++i] : "true";
            }
        }
        public string? this[string k] => _kv.GetValueOrDefault(k);
        public string Req(string k) => _kv.GetValueOrDefault(k) ?? throw new ArgumentException("--" + k + " is required");
        public bool Flag(string k) => _kv.GetValueOrDefault(k) == "true";
    }

    public static int Run(string[] argv, TextWriter stdout, Action<string>? stepHook = null, Action<string>? log = null)
    {
        Args a;
        try { a = new Args(argv); }
        catch (ArgumentException e) { stdout.WriteLine(Result(false, "USAGE", e.Message)); return 1; }
        try { return Dispatch(a, stdout, stepHook, log); }
        catch (ActivationRefused e) { stdout.WriteLine(Result(false, e.Code, e.Message)); return e.Code == "JOURNAL_CORRUPT" ? 3 : 2; }
        catch (ArgumentException e) { stdout.WriteLine(Result(false, "USAGE", e.Message)); return 1; }
    }

    static string Result(bool ok, string code, string message, JsonObject? extra = null)
    {
        var o = extra ?? new JsonObject();
        o["ok"] = ok; o["code"] = code; o["message"] = message;
        return o.ToJsonString();
    }

    public static ExclusionReader Reader(SiteLayout s, bool production) => new(new ExclusionReaderOptions
    {
        StoreDir = s.ExclusionsDir, TrustListPath = s.TrustListPath, HighWaterPath = s.HighWaterPath, Production = production,
    });

    static int Dispatch(Args a, TextWriter stdout, Action<string>? stepHook, Action<string>? log)
    {
        var site = new SiteLayout(a.Req("site"));
        bool production = !a.Flag("development");
        var reader = Reader(site, production);
        var insp = new SiteInspector(site, reader);

        if (a.Command == "status")
        {
            stdout.WriteLine(Status(insp).ToJsonString());
            return 0;
        }
        if (a.Command == "init")
        {
            var snap = reader.Read();
            if (!snap.Healthy) throw new ActivationRefused("EXCLUSIONS_UNAVAILABLE", snap.Health + ": " + snap.Detail);
            site.Initialise(a.Req("knowledge"), a["models"], snap.Sequence!.Value);   // no --models: no model installed (2.1 lexical-only site)
            new FileActivationDatabase(site.FileDbPath).Initialise(a.Req("knowledge"));
            stdout.WriteLine(Result(true, "OK", "initialised"));
            return 0;
        }

        PgAdvisoryLock? pg = null;
        IActivationDatabase db;
        if (a["pg-env"] is { } envName)
        {
            var cs = Environment.GetEnvironmentVariable(envName) ?? throw new ArgumentException("environment variable " + envName + " is not set");
            pg = new PgAdvisoryLock(cs);
            // C16 S3-C (B07, additive): --knowledge-rows drives the B03 knowledge schemas (kr_<n> promotion and the
            // `knowledge` views) from each staged generation's release sequence, as on an installed site
            db = a.Flag("knowledge-rows")
                ? new Mimamsa.Core.Knowledge.KnowledgeActivationDatabase(() => pg.Connection, gid =>
                    (long)System.Text.Json.Nodes.JsonNode.Parse(File.ReadAllText(Path.Combine(site.GenerationsDir, SiteLayout.CheckId(gid), "generation.json")))!["release_sequence"]!,
                    a["pg-schema"] ?? "site_activation")
                : new PgActivationDatabase(() => pg.Connection, a["pg-schema"] ?? "site_activation");
        }
        else db = new FileActivationDatabase(site.FileDbPath);

        using var link = a["pipe"] is { } pipe
            ? new PipeParticipantLink(new ControlChannelOptions
            {
                PipeName = pipe,
                Secret = ControlChannelOptions.LoadSecret(a["key"] ?? site.ChannelKeyPath),
                Timeout = TimeSpan.FromSeconds(double.Parse(a["channel-timeout"] ?? "5", System.Globalization.CultureInfo.InvariantCulture)),
            })
            : null;
        var opts = new ActivationEngineOptions
        {
            Site = site, WriterId = a["writer"] ?? "activator-" + Environment.MachineName.ToLowerInvariant(), Database = db, Exclusions = reader,
            Participant = link, ExternalLock = pg, StepHook = stepHook, Log = log,
            StaleAfterSeconds = long.Parse(a["stale-after"] ?? "30", System.Globalization.CultureInfo.InvariantCulture),
            KeepPrevious = int.Parse(a["keep-previous"] ?? "2", System.Globalization.CultureInfo.InvariantCulture),
            HeadroomFraction = double.Parse(a["headroom"] ?? "0.1", System.Globalization.CultureInfo.InvariantCulture),
            RecoveryTarget = a["recovery-target"],
            Production = production,   // C16-CP1-04: development-staged releases are refused unless --development
        };
        using var eng = new ActivationEngine(opts);
        bool mustRecover = eng.AcquireLock();
        try
        {
            if (pg is not null)
            {
                var head = site.ReadPointer("KNOWLEDGE") ?? throw new ArgumentException("site not initialised");
                if (db is Mimamsa.Core.Knowledge.KnowledgeActivationDatabase kdb) kdb.EnsureSchema(head);
                else ((PgActivationDatabase)db).EnsureSchema(head);
            }
            // I-4: every start of the tool recovers first whenever anything is unfinished (a takeover, a non-OPEN
            // marker, an in-flight transaction, a torn tail or pointers off the journal head).
            if (mustRecover || eng.NeedsRecovery()) eng.Recover();
            switch (a.Command)
            {
                case "recover":
                    eng.Recover();                            // idempotent: a second pass changes nothing
                    stdout.WriteLine(Result(true, "OK", "recovered", Status(insp)));
                    return 0;
                case "activate":
                case "rollback":
                    var target = a["target"] ?? "KNOWLEDGE";
                    var action = a.Command == "rollback" ? "ROLLBACK" : a["action"] ?? "ACTIVATE";
                    var txn = eng.Transition(target, a.Req("to"), action);
                    var st = Status(insp); st["txn_id"] = txn;
                    stdout.WriteLine(Result(true, "OK", "open", st));
                    return 0;
                case "preflight":
                    var pf = eng.Preflight(a["target"] ?? "KNOWLEDGE", a.Req("to"));
                    var arr = new JsonArray(); foreach (var r in pf.RetainedReleases) arr.Add(r);
                    stdout.WriteLine(Result(pf.Pass, pf.Pass ? "PASS" : "FAIL", "preflight", new JsonObject
                    {
                        ["measured_required_bytes"] = pf.MeasuredRequiredBytes, ["free_bytes"] = pf.FreeBytes,
                        ["headroom_fraction"] = pf.HeadroomFraction, ["retained_releases"] = arr,
                    }));
                    return pf.Pass ? 0 : 2;
                case "prune":
                    var removed = new JsonArray(); foreach (var g in eng.Prune()) removed.Add(g);
                    stdout.WriteLine(Result(true, "OK", "pruned", new JsonObject { ["removed"] = removed }));
                    return 0;
                default:
                    throw new ArgumentException("unknown command " + a.Command);
            }
        }
        finally { eng.ReleaseLock(); }
    }

    public static JsonObject Status(SiteInspector insp)
    {
        insp.InvalidateCache();
        var s = insp.Site;
        var o = new JsonObject { ["state"] = insp.State().ToString() };
        try
        {
            var j = insp.Journal();
            var steps = new JsonArray(); foreach (var e in j.Entries) steps.Add(e.Step);
            o["journal_steps"] = steps;
            o["in_flight"] = j.InFlight;
            o["torn_tail"] = j.TornTail;
        }
        catch (JournalCorruptException e) { o["journal_error"] = e.Message; }
        o["knowledge"] = s.ReadPointer("KNOWLEDGE");
        o["models"] = s.ReadPointer("MODELS");
        try { o["views"] = new FileActivationDatabase(s.FileDbPath).Views(); o["publication_rows"] = new FileActivationDatabase(s.FileDbPath).PublicationCount(); } catch (Exception) { }
        try { o["log_length"] = new ActivationLog(s.ActivationLogPath).Read().Count; } catch (JournalCorruptException) { o["log_length"] = null; }
        var ex = insp.ReadExclusions();
        o["exclusion_reader"] = ex.Health.ToString();
        o["store_seq"] = ex.Sequence;
        o["lock_epoch"] = WriterLease.CurrentEpoch(s);
        o["temp_empty"] = !Directory.Exists(s.ScratchDir) || !Directory.EnumerateFileSystemEntries(s.ScratchDir).Any();
        var inst = new JsonArray(); foreach (var g in insp.Catalog.Installed()) inst.Add(g);
        o["installed"] = inst;
        return o;
    }
}
