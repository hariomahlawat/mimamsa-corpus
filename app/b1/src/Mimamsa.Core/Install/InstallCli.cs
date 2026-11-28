// C16 Tranche B Stage 3 S3-C (B07/B08): installer, staging, backup and restore commands of the activation tool
// (Mimamsa.Activation). DEVELOPMENT/TEST installations only. One JSON object on stdout; exit 0 ok, 2 refused, 1 usage.
// Secrets never appear on the command line: connection strings are read from the environment variables named by the
// --*-env options; role passwords are generated into a secrets directory (never printed); backup keys are key files.
//
//   install-preflight --config F [--payload LABEL=TARGETROOT=DIR]... [--bytes LABEL=TARGETROOT=N]...
//   install-layout    --config F [--payload ...]... [--bytes ...]...        preflight (refuses), then lays down the layout
//   db-setup          --config F --admin-env A --owner-env O --secrets DIR [--create-db]
//   db-probe          --config F --owner-env O --secrets DIR [--staging-schema S]
//   migrate-clone     --config F --admin-env A --owner-env O --source DB --clone DB [--plan F] [--secrets DIR]
//   stage             (--config F | --site D --text-dir D) --generation G --pg-env O --loader-env L [--loader-role R]
//                     --contracts DIR [--development]                       production B07 wiring of GenerationStaging
//   release-check     --dir D                                              path/symlink negatives on a release tree
//   new-key           --out F                                              a development/test backup key
//   backup            --config F --key K [--db-env E] [--dest DIR] [--backup-id ID]
//   verify-backup     --key K --backup DIR
//   restore           --config F --key K --backup DIR [--appendonly-from DIR]... [--db-env E] [--secrets DIR]
using System.Reflection;
using System.Text.Json;
using System.Text.Json.Nodes;
using Mimamsa.Core.Activation;
using Mimamsa.Core.Knowledge;
using Npgsql;

namespace Mimamsa.Core.Install;

public static class InstallCli
{
    public static readonly string[] Commands = ["install-preflight", "install-layout", "db-setup", "db-probe", "migrate-clone", "stage", "release-check",
                                                "new-key", "backup", "verify-backup", "restore"];

    sealed class Args
    {
        readonly Dictionary<string, List<string>> _kv = new(StringComparer.Ordinal);
        public string Command { get; }
        public Args(string[] a)
        {
            Command = a[0];
            for (int i = 1; i < a.Length; i++)
            {
                if (!a[i].StartsWith("--", StringComparison.Ordinal)) throw new ArgumentException("unexpected argument " + a[i]);
                var k = a[i][2..];
                var v = i + 1 < a.Length && !a[i + 1].StartsWith("--", StringComparison.Ordinal) ? a[++i] : "true";
                (_kv.TryGetValue(k, out var l) ? l : _kv[k] = new()).Add(v);
            }
        }
        public string? this[string k] => _kv.TryGetValue(k, out var l) ? l[^1] : null;
        public IReadOnlyList<string> All(string k) => _kv.TryGetValue(k, out var l) ? l : [];
        public string Req(string k) => this[k] ?? throw new ArgumentException("--" + k + " is required");
        public bool Flag(string k) => this[k] == "true";
        public string Env(string k)
        {
            var name = Req(k);
            return Environment.GetEnvironmentVariable(name) is { Length: > 0 } v ? v : throw new ArgumentException("environment variable " + name + " (--" + k + ") is not set");
        }
    }

    static readonly JsonSerializerOptions Indented = new() { WriteIndented = true };
    static string Version => typeof(InstallCli).Assembly.GetCustomAttribute<AssemblyInformationalVersionAttribute>()?.InformationalVersion ?? "unrecorded";

    public static int Run(string[] argv, TextWriter stdout, Action<string>? log = null)
    {
        Args a;
        try { a = new Args(argv); }
        catch (ArgumentException e) { stdout.WriteLine(Result(false, "USAGE", e.Message)); return 1; }
        try { return Dispatch(a, stdout, log).GetAwaiter().GetResult(); }
        catch (InstallConfigException e) { stdout.WriteLine(Result(false, e.Code, e.Message)); return 2; }
        catch (DatabaseSetupException e) { stdout.WriteLine(Result(false, e.Code, e.Message)); return 2; }
        catch (BackupException e) { stdout.WriteLine(Result(false, e.Code, e.Message)); return 2; }
        catch (BackupCryptoException e) { stdout.WriteLine(Result(false, e.Code, e.Message)); return 2; }
        catch (ActivationRefused e) { stdout.WriteLine(Result(false, e.Code, e.Message)); return 2; }
        catch (SiteMigrationException e) { stdout.WriteLine(Result(false, e.Code, e.Message)); return 2; }
        catch (ArgumentException e) { stdout.WriteLine(Result(false, "USAGE", e.Message)); return 1; }
        catch (PostgresException e) { stdout.WriteLine(Result(false, "POSTGRES_" + e.SqlState, e.MessageText)); return 2; }
    }

    static string Result(bool ok, string code, string message, JsonObject? extra = null)
    {
        var o = extra ?? new JsonObject();
        o["ok"] = ok; o["code"] = code; o["message"] = message;
        return o.ToJsonString();
    }

    static IEnumerable<PreflightPayload> Payloads(Args a)
    {
        foreach (var p in a.All("payload"))
        {
            var x = p.Split('=', 3);
            if (x.Length != 3) throw new ArgumentException("--payload LABEL=TARGETROOT=DIR");
            yield return new PreflightPayload(x[0], x[1], x[2]);
        }
        foreach (var p in a.All("bytes"))
        {
            var x = p.Split('=', 3);
            if (x.Length != 3 || !long.TryParse(x[2], out var n) || n < 0) throw new ArgumentException("--bytes LABEL=TARGETROOT=N");
            yield return new PreflightPayload(x[0], x[1], null, n);
        }
    }

    static IEnumerable<PreflightPayload> Resolve(InstallConfig cfg, IEnumerable<PreflightPayload> ps) =>
        ps.Select(p => p with { TargetRoot = InstallConfig.RootNames.Contains(p.TargetRoot) ? cfg.Root(p.TargetRoot) : p.TargetRoot });

    static string Secret(string dir, string role)
    {
        Directory.CreateDirectory(dir);
        var p = Path.Combine(dir, role + ".pw");
        if (File.Exists(p)) return File.ReadAllText(p).Trim();
        var pw = SiteDatabaseSetup.NewPassword();
        File.WriteAllText(p, pw);
        if (!OperatingSystem.IsWindows()) File.SetUnixFileMode(p, UnixFileMode.UserRead | UnixFileMode.UserWrite);
        return pw;
    }

    static string WithDb(string dsn, string db, int pool = 4) => new NpgsqlConnectionStringBuilder(dsn) { Database = db, MaxPoolSize = pool }.ConnectionString;
    static string AsRole(string dsn, string role, string pw) => new NpgsqlConnectionStringBuilder(dsn) { Username = role, Password = pw, MaxPoolSize = 2 }.ConnectionString;

    static async Task<int> Dispatch(Args a, TextWriter stdout, Action<string>? log)
    {
        switch (a.Command)
        {
            case "install-preflight":
            case "install-layout":
            {
                var cfg = InstallConfig.Load(a.Req("config"));
                var issues = cfg.Issues();
                if (issues.Count > 0) throw new InstallConfigException(issues[0].Code, string.Join("; ", issues));
                var pf = InstallPreflight.Run(cfg, Resolve(cfg, Payloads(a)).ToList());
                var where = InstallPreflight.Record(cfg, pf);
                pf["record"] = where;
                if ((string?)pf["result"] != "PASS") { stdout.WriteLine(Result(false, "PREFLIGHT_FAILED", "measured disk preflight failed", new JsonObject { ["preflight"] = pf })); return 2; }
                if (a.Command == "install-preflight") { stdout.WriteLine(Result(true, "PASS", "preflight", new JsonObject { ["preflight"] = pf })); return 0; }
                var rec = InstallLayout.Create(cfg, pf, Version);
                stdout.WriteLine(Result(true, "OK", "layout installed", new JsonObject { ["record"] = rec }));
                return 0;
            }
            case "db-setup":
            case "db-probe":
            {
                var cfg = InstallConfig.Load(a.Req("config"));
                var dbName = cfg.DatabaseName ?? throw new ArgumentException("database.name missing in the config");
                if (cfg.DisposablePrefix is { } pre && !dbName.StartsWith(pre, StringComparison.Ordinal)) throw new DatabaseSetupException("DATABASE_NOT_DISPOSABLE", dbName);
                var ownerDsn = WithDb(a.Env("owner-env"), dbName);
                var roles = SiteRoles.For(cfg.RolePrefix);
                var secrets = a.Req("secrets");
                if (a.Command == "db-setup")
                {
                    await using var admin = NpgsqlDataSource.Create(WithDb(a.Env("admin-env"), "postgres", 2));
                    if (a.Flag("create-db"))
                    {
                        await using var c = await admin.OpenConnectionAsync();
                        await using var q = new NpgsqlCommand("SELECT 1 FROM pg_database WHERE datname = $1", c);
                        q.Parameters.AddWithValue(dbName);
                        if (await q.ExecuteScalarAsync() is null)
                        {
                            var ownerRole = new NpgsqlConnectionStringBuilder(ownerDsn).Username!;
                            await using var cr = new NpgsqlCommand($"CREATE DATABASE \"{dbName}\" OWNER \"{ownerRole}\"", c);
                            await cr.ExecuteNonQueryAsync();
                        }
                    }
                    foreach (var r in roles.All.Where(r => r != roles.Loader)) await SiteDatabaseSetup.EnsureRoleAsync(admin, r, Secret(secrets, r));
                    await KnowledgeLoaderRole.EnsureAsync(admin, roles.Loader, Secret(secrets, roles.Loader));
                }
                await using var owner = NpgsqlDataSource.Create(ownerDsn);
                await SiteDatabaseSetup.HardenAndGrantAsync(owner, roles, ["public", "site"], cfg.BackupSchemas);
                var probe = await SiteDatabaseSetup.ProbeAsync(owner, roles, r => AsRole(ownerDsn, r, Secret(secrets, r)), a["staging-schema"]);
                bool ok = (bool)probe["all_ok"]!;
                stdout.WriteLine(Result(ok, ok ? "OK" : "PROBE_FAILED", a.Command, new JsonObject { ["database"] = dbName, ["roles"] = new JsonArray(roles.All.Select(r => (JsonNode)r).ToArray()), ["probe"] = probe }));
                return ok ? 0 : 2;
            }
            case "migrate-clone":
            {
                var cfg = InstallConfig.Load(a.Req("config"));
                var plan = a["plan"] is { } pf ? SiteDatabaseSetup.ParsePlan(File.ReadAllText(pf)) : SiteDatabaseSetup.BuiltInPlan;
                var issues = SiteDatabaseSetup.PlanIssues(plan);   // refused before ANY database work, clone included
                if (issues.Count > 0) throw new DatabaseSetupException(issues[0].Split(':')[0], string.Join("; ", issues));
                var source = a.Req("source"); var clone = a.Req("clone");
                var ownerBase = a.Env("owner-env");
                await using (var admin = NpgsqlDataSource.Create(WithDb(a.Env("admin-env"), "postgres", 2)))
                    await SiteDatabaseSetup.CloneAsync(admin, source, clone, new NpgsqlConnectionStringBuilder(ownerBase).Username!, cfg.DisposablePrefix);
                await using var owner = NpgsqlDataSource.Create(WithDb(ownerBase, clone));
                var rep = await SiteDatabaseSetup.MigrateCloneAsync(owner, plan);
                if (a["secrets"] is { } secrets)
                {
                    var roles = SiteRoles.For(cfg.RolePrefix);
                    await SiteDatabaseSetup.HardenAndGrantAsync(owner, roles, ["public", "site"], cfg.BackupSchemas);
                    rep["probe"] = await SiteDatabaseSetup.ProbeAsync(owner, roles, r => AsRole(WithDb(ownerBase, clone), r, Secret(secrets, r)));
                }
                stdout.WriteLine(Result(true, "OK", "migrated on the clone, rollback demonstrated", rep));
                return 0;
            }
            case "stage":
                return await Stage(a, stdout, log);
            case "release-check":
            {
                var issues = PathSafety.TreeIssues(a.Req("dir"), out var files);
                var arr = new JsonArray(issues.Select(i => (JsonNode)i.ToString()).ToArray());
                stdout.WriteLine(Result(issues.Count == 0, issues.Count == 0 ? "OK" : "RELEASE_PATH_UNSAFE", "release-check", new JsonObject { ["files"] = files.Count, ["issues"] = arr }));
                return issues.Count == 0 ? 0 : 2;
            }
            case "new-key":
                BackupCrypto.NewKeyFile(a.Req("out"));
                stdout.WriteLine(Result(true, "OK", "development/test backup key written (never printed)"));
                return 0;
            case "backup":
            {
                var cfg = InstallConfig.Load(a.Req("config"));
                var key = BackupCrypto.LoadKey(a.Req("key"));
                string? dsn = a["db-env"] is null ? null : WithDb(a.Env("db-env"), cfg.DatabaseName ?? throw new ArgumentException("database.name"));
                var rep = SiteBackup.Create(new SiteBackup.Options { Config = cfg, Key = key, DbDsn = dsn, Pg = PgTools.From(cfg), Destination = a["dest"], BackupId = a["backup-id"], Log = log });
                stdout.WriteLine(Result(true, "OK", "backup written and verified", rep));
                return 0;
            }
            case "verify-backup":
            {
                var rep = SiteBackup.Verify(a.Req("backup"), BackupCrypto.LoadKey(a.Req("key")));
                stdout.WriteLine(Result(true, "OK", "backup verified", rep));
                return 0;
            }
            case "restore":
            {
                var cfg = InstallConfig.Load(a.Req("config"));
                var key = BackupCrypto.LoadKey(a.Req("key"));
                string? dsn = a["db-env"] is null ? null : WithDb(a.Env("db-env"), cfg.DatabaseName ?? throw new ArgumentException("database.name"));
                var rep = SiteRestore.Run(new SiteRestore.Options { Config = cfg, Key = key, BackupDir = a.Req("backup"), AppendOnlyFrom = a.All("appendonly-from"), DbOwnerDsn = dsn, Pg = PgTools.From(cfg), Log = log });
                if (dsn is not null && a["secrets"] is { } secrets)
                {
                    // explicit grants again: pg_restore ran with --no-privileges
                    var roles = SiteRoles.For(cfg.RolePrefix);
                    await using var owner = NpgsqlDataSource.Create(dsn);
                    await SiteDatabaseSetup.HardenAndGrantAsync(owner, roles, ["public", "site"], cfg.BackupSchemas);
                    rep["probe"] = await SiteDatabaseSetup.ProbeAsync(owner, roles, r => AsRole(dsn, r, Secret(secrets, r)));
                }
                stdout.WriteLine(Result(true, "OK", "site data restored; re-import, stage and recover before serving", rep));
                return 0;
            }
            default:
                throw new ArgumentException("unknown command " + a.Command);
        }
    }

    /// The production `stage` command (B07): GenerationStaging.VerifyAndStageAsync with the restricted loader's
    /// credentials, after the release-path negatives. Writes the bound catalogue marker only when the reference outcome
    /// rule activates the generation.
    static async Task<int> Stage(Args a, TextWriter stdout, Action<string>? log)
    {
        InstallConfig? cfg = a["config"] is { } cf ? InstallConfig.Load(cf) : null;
        var site = new SiteLayout(cfg?.Root("site") ?? a.Req("site"));
        var textDir = a["text-dir"] ?? cfg?.Root("text_store") ?? throw new ArgumentException("--text-dir is required");
        var gen = SiteLayout.CheckId(a.Req("generation"));
        var gdir = Path.Combine(site.GenerationsDir, gen);
        var pathIssues = PathSafety.TreeIssues(gdir, out _);
        if (pathIssues.Count > 0)
        {
            stdout.WriteLine(Result(false, "RELEASE_PATH_UNSAFE", "the generation tree is not safe to stage", new JsonObject { ["issues"] = new JsonArray(pathIssues.Select(i => (JsonNode)i.ToString()).ToArray()) }));
            return 2;
        }
        var contracts = ActivationOutcome.Kinds.ToDictionary(k => k, k =>
        {
            var p = Path.Combine(a.Req("contracts"), k + ".json");
            return File.Exists(p) ? (JsonObject?)JsonNode.Parse(File.ReadAllText(p))!.AsObject() : null;
        }, StringComparer.Ordinal);
        var ownerDsn = a.Env("pg-env");
        if (cfg?.DatabaseName is { } dbn) ownerDsn = WithDb(ownerDsn, dbn);
        var loaderDsn = a.Env("loader-env");
        var role = a["loader-role"] ?? (cfg is null ? KnowledgeAllowlist.LoaderRole : SiteRoles.For(cfg.RolePrefix).Loader);
        await using var owner = NpgsqlDataSource.Create(ownerDsn);
        var loader = new KnowledgeRowLoader(owner, loaderDsn) { LoaderRole = role };
        var rep = await GenerationStaging.VerifyAndStageAsync(site, gen, loader, textDir, contracts, log, production: !a.Flag("development"));
        var o = new JsonObject
        {
            ["generation"] = rep.Generation, ["release_sequence"] = rep.ReleaseSequence, ["staged"] = rep.Ok,
            ["issues"] = new JsonArray(rep.Issues.Select(i => (JsonNode)i).ToArray()),
            ["components"] = new JsonObject(rep.Components.Select(kv => KeyValuePair.Create(kv.Key, (JsonNode?)kv.Value))),
            ["inputs"] = new JsonObject(rep.Inputs.Select(kv => KeyValuePair.Create(kv.Key, (JsonNode?)kv.Value))),
            ["loaded_tables"] = new JsonArray(rep.LoadedTables.Select(t => (JsonNode)t).ToArray()),
            ["text_store_origin"] = rep.TextStoreOrigin, ["declared_service_level"] = rep.DeclaredServiceLevel, ["lexical_only"] = rep.LexicalOnly,
            ["outcome"] = rep.Outcome?.DeepClone(), ["production"] = !a.Flag("development"),
            ["staging_schema"] = KnowledgeAllowlist.StagingSchema(rep.ReleaseSequence),
        };
        stdout.WriteLine(Result(rep.Ok, rep.Ok ? "STAGED" : "STAGING_REFUSED", "stage", o));
        return rep.Ok ? 0 : 2;
    }
}
