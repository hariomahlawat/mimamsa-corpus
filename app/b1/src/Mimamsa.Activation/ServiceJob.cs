// C16 Tranche B Stage 3 S3-C (B07): run one bounded job AS a Windows service, so that it executes under that service's
// VIRTUAL ACCOUNT (NT SERVICE\<name>, WD-5). Used by the development installer's acceptance tests (CI only; they need
// administrator rights to (re)configure services): the ACL probe matrix (each identity attempts every forbidden write
// and must fail) and real activation-tool commands under the activation identity.
//   Mimamsa.Activation service-job --job <job.json> [--console]
// job.json: {"out": "<results file>", "probes": [{"kind": "write"|"read", "path": "<dir>"}...],
//            "command": ["status", "--site", "..."]}   (command optional: an activation-tool or installer command)
// The results file records the process identity (name and SID), each probe's outcome and the command's stdout.
using System.Diagnostics.CodeAnalysis;
using System.Security.Principal;
using System.ServiceProcess;
using System.Text.Json.Nodes;
using Mimamsa.Core.Activation;
using Mimamsa.Core.Install;

static class ServiceJob
{
    public static int Main(string[] args)
    {
        string? job = null; bool console = false;
        for (int i = 1; i < args.Length; i++)
        {
            if (args[i] == "--job" && i + 1 < args.Length) job = args[++i];
            else if (args[i] == "--console") console = true;
        }
        if (job is null) { Console.WriteLine("{\"ok\":false,\"code\":\"USAGE\",\"message\":\"--job is required\"}"); return 1; }
        if (console || !OperatingSystem.IsWindows()) return Execute(job);
        RunService(job);
        return 0;
    }

    [SuppressMessage("Interoperability", "CA1416")]
    static void RunService(string job) => ServiceBase.Run(new JobService(job));

    public static int Execute(string jobPath)
    {
        var job = JsonNode.Parse(File.ReadAllText(jobPath))!.AsObject();
        var res = new JsonObject();
        try
        {
            if (OperatingSystem.IsWindows())
            {
                using var id = WindowsIdentity.GetCurrent();
                res["identity"] = id.Name; res["sid"] = id.User?.Value;
            }
            else res["identity"] = Environment.UserName;
            var probes = new JsonArray();
            foreach (var p in job["probes"]?.AsArray() ?? [])
            {
                var kind = (string)p!["kind"]!; var path = (string)p["path"]!;
                bool allowed; string? err = null;
                try
                {
                    if (kind == "write")
                    {
                        var f = Path.Combine(path, "s3c-acl-probe-" + Guid.NewGuid().ToString("N") + ".tmp");
                        File.WriteAllText(f, "probe");
                        File.Delete(f);
                    }
                    else _ = Directory.EnumerateFileSystemEntries(path).Take(1).ToList();
                    allowed = true;
                }
                catch (Exception e) when (e is UnauthorizedAccessException or IOException) { allowed = false; err = e.GetType().Name; }
                probes.Add(new JsonObject { ["kind"] = kind, ["path"] = path, ["allowed"] = allowed, ["error"] = err });
            }
            res["probes"] = probes;
            if (job["command"] is JsonArray cmd)
            {
                var argv = cmd.Select(x => (string)x!).ToArray();
                var sw = new StringWriter();
                int code = InstallCli.Commands.Contains(argv[0]) ? InstallCli.Run(argv, sw) : ActivationCli.Run(argv, sw);
                res["command_exit"] = code; res["command_stdout"] = sw.ToString();
            }
            res["ok"] = true;
        }
        catch (Exception e) { res["ok"] = false; res["error"] = e.GetType().Name + ": " + e.Message; }
        File.WriteAllText((string)job["out"]!, res.ToJsonString());
        return (bool)res["ok"]! ? 0 : 1;
    }

    [SuppressMessage("Interoperability", "CA1416")]
    sealed class JobService(string job) : ServiceBase
    {
        protected override void OnStart(string[] args)
        {
            new Thread(() =>
            {
                try { ExitCode = Execute(job); }
                catch (Exception) { ExitCode = 1; }
                Stop();
            }) { IsBackground = true }.Start();
        }
    }
}
