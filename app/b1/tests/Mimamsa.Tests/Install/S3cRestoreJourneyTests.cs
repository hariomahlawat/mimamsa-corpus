// C16 S3-C: the REAL RESTORE TEST (B07 + B08) on development/test data, FIXTURE acceptance level (SG-5). It runs ONLY
// when app/b1/build/c16_s3c_restore.py has built the release media and points MIMAMSA_S3C_CONTEXT at them; otherwise it
// does nothing. Disposable c16s3c_* databases and roles only; everything is created under the driver's work directory.
//
//   install   layout + measured preflight (installer CLI), hardened database, I-3 migration on a CLONE, restricted roles
//   stage     every release imported (B01, stage-only after G1) and STAGED with the production `stage` command (B03 loader,
//             B04 text store and lexical index, reference outcome rule)
//   activate  journal transitions through the activation CLI with the web process as the participant: G2, G3, G4;
//             retention prune (active + two previous distinct; G1 pruned); rollback to G3; exclusion E1
//   backup    encrypted backup (site schemas as the BACKUP role, vault, uploads, config) + separate append-only part
//   continue  activation of G4 and exclusion E2 AFTER the backup; the append-only stores copied again to separate media
//   destroy   web stopped, databases dropped, every site directory deleted
//   restore   onto a FRESH isolated installation (new roots, new database, new roles): negative drills first (wrong key,
//             tampered, truncated, partial, stale, missing append-only), then the restore; re-import of the journal-head
//             release from media, `stage`, `recover`
//   verify    the restored site serves EXACTLY what the destroyed site last served (statuses and normalised bodies), both
//             exclusions intact, site data identical to the backup (ordered dumps), the journal head followed (G4, not
//             the backup's G3); a rollback to a release not retained is refused until it is re-imported from media
using System.Diagnostics;
using System.Net;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json.Nodes;
using System.Text.RegularExpressions;
using Mimamsa.Core.Activation;
using Mimamsa.Core.Install;
using Mimamsa.Core.Knowledge;
using Npgsql;

namespace Mimamsa.Tests.Install;

public partial class S3cRestoreJourneyTests
{
    static JsonObject Obj(string path) => JsonNode.Parse(File.ReadAllText(path))!.AsObject();
    static string Sha(byte[] b) => Convert.ToHexString(SHA256.HashData(b)).ToLowerInvariant();

    [GeneratedRegex("(?i)(_ms$|^ms$|elapsed|took|latency|timing|duration)")] private static partial Regex Volatile();

    static JsonNode? Normalise(JsonNode? n)
    {
        switch (n)
        {
            case JsonObject o:
                var x = new JsonObject();
                foreach (var (k, v) in o.OrderBy(kv => kv.Key, StringComparer.Ordinal)) if (!Volatile().IsMatch(k)) x[k] = Normalise(v);
                return x;
            case JsonArray a: return new JsonArray(a.Select(Normalise).ToArray());
            default: return n?.DeepClone();
        }
    }

    [Fact]
    public async Task S3cRealRestore()
    {
        var ctxPath = Environment.GetEnvironmentVariable("MIMAMSA_S3C_CONTEXT");
        if (string.IsNullOrEmpty(ctxPath)) return;   // only the S3-C driver runs this journey
        var ctx = Obj(ctxPath);
        string S(string k) => (string)ctx[k]!;
        var rel = ctx["releases"]!.AsObject();
        string Id(string g) => (string)rel[g]!["release_id"]!;
        long Seq(string g) => (long)rel[g]!["release_sequence"]!;
        string work = S("work");
        var checks = new JsonObject();
        var timings = new JsonObject();
        void Check(string name, bool ok, string? detail = null)
        {
            checks[name] = detail is null ? ok : new JsonObject { ["ok"] = ok, ["detail"] = detail.Length > 600 ? detail[..600] : detail };
            Assert.True(ok, name + (detail is null ? "" : ": " + detail));
        }
        var results = new JsonObject
        {
            ["acceptance_level"] = "FIXTURE (SG-5) S3-C real restore test on isolated development sites; development keys, test data; not the owner's offline host (OG-8)",
            ["checks"] = checks, ["timings_ms"] = timings,
        };

        var r = S3cPg.Rand();
        string prefixA = $"c16s3c_{r}_", prefixB = $"c16s3c_{r}b_", src = prefixA + "src", dbA = prefixA + "a", dbB = prefixB + "b";
        var rolesA = SiteRoles.For(prefixA); var rolesB = SiteRoles.For(prefixB);
        string[] exclude = ["public.graph_generation", "public.graph_nodes", "public.graph_edges"];
        // the application still runs on the default schema in the I-3 compatibility window: back up its site tables there
        // too (accelerator tables excluded); `site` holds the verified copies. Knowledge (kr_, knowledge) is never backed up.
        var cfgA = S3cDirs.Config(Path.Combine(work, "siteA"), db: dbA, prefix: prefixA, backupSchemas: ["public", "site"], exclude: exclude);
        var cfgB = S3cDirs.Config(Path.Combine(work, "siteB"), db: dbB, prefix: prefixB, backupSchemas: ["public", "site"], exclude: exclude);
        string cfA = Path.Combine(work, "install-A.json"), cfB = Path.Combine(work, "install-B.json");
        File.WriteAllBytes(cfA, cfgA.SourceBytes); File.WriteAllBytes(cfB, cfgB.SourceBytes);
        string secretsA = Path.Combine(work, "secrets-A"), secretsB = Path.Combine(work, "secrets-B");
        string Env(string label, string value) { var n = $"S3C_J_{label}_{r}".ToUpperInvariant(); Environment.SetEnvironmentVariable(n, value); return n; }
        var adminEnv = Env("admin", S3cPg.AdminDsn("postgres"));
        var ownerEnv = Env("owner", S3cPg.OwnerDsn("postgres"));
        var webs = new List<Cp1Web>();

        (int code, JsonObject o) Cli(params string[] args)
        {
            var sw = new StringWriter();
            int c = InstallCli.Commands.Contains(args[0]) ? InstallCli.Run(args, sw) : ActivationCli.Run(args, sw);
            var text = sw.ToString().Trim();
            var last = text.Split('\n').Last(l => l.TrimStart().StartsWith('{'));
            return (c, JsonNode.Parse(last)!.AsObject());
        }
        (int code, string output) Py(params string[] args)
        {
            var psi = new ProcessStartInfo(S("python")) { RedirectStandardOutput = true, RedirectStandardError = true, UseShellExecute = false };
            foreach (var a in new[] { "-I", S("driver") }.Concat(args)) psi.ArgumentList.Add(a);
            using var p = Process.Start(psi)!;
            var o = p.StandardOutput.ReadToEnd() + p.StandardError.ReadToEnd();
            p.WaitForExit();
            return (p.ExitCode, o);
        }
        string LoaderEnv(string secrets, SiteRoles roles, string db) =>
            Env("loader_" + db, S3cPg.RoleDsn(db, roles.Loader, File.ReadAllText(Path.Combine(secrets, roles.Loader + ".pw")).Trim()));
        long ms(Stopwatch sw) => sw.ElapsedMilliseconds;

        Dictionary<string, string> WebEnv(InstallConfig cfg, string db, string pipe, string tag) => new()
        {
            ["Mimamsa__Site"] = cfg.Root("site"), ["Mimamsa__Db"] = new NpgsqlConnectionStringBuilder(S3cPg.OwnerDsn(db)) { MaxPoolSize = 8 }.ConnectionString,
            ["Mimamsa__Test__Enabled"] = "true", ["Mimamsa__Test__Users__0"] = "reader:User:reader-password-1", ["Mimamsa__RestrictedRegister"] = S("register"),
            ["Mimamsa__Activation__Enabled"] = "true", ["Mimamsa__Activation__DevelopmentTrust"] = "true",
            ["Mimamsa__Activation__Pipe"] = pipe, ["Mimamsa__Activation__KeyFile"] = cfg.Site.ChannelKeyPath,
            ["Mimamsa__Text__Store"] = "disk", ["Mimamsa__Text__Dir"] = Path.Combine(cfg.Root("text_store"), "web-" + tag), ["Mimamsa__Search__Engine"] = "memory",
        };
        async Task<Cp1Web> Web(InstallConfig cfg, string db, string pipe, string tag) { var w = await Cp1Web.StartAsync(WebEnv(cfg, db, pipe, tag)); webs.Add(w); return w; }
        async Task StopAll() { foreach (var w in webs) await w.DisposeAsync(); webs.Clear(); }

        try
        {
            // ================================================================ INSTALL site A
            var swInstall = Stopwatch.StartNew();
            var payloads = rel.Select(kv => new[] { "--payload", $"{kv.Key}=import={(string)kv.Value!["bundle"]!}" }).SelectMany(x => x).ToArray();
            var (code, o) = Cli(["install-layout", "--config", cfA, .. payloads]);
            Check("install_layout_with_measured_preflight", code == 0 && (string?)o["record"]!["preflight"]!["result"] == "PASS", o.ToJsonString());
            await S3cPg.CreateDbAsync(src);
            await using (var ds = NpgsqlDataSource.Create(S3cPg.OwnerDsn(src))) await TestPg.SeedSiteAsync(ds);
            (code, o) = Cli("migrate-clone", "--config", cfA, "--admin-env", adminEnv, "--owner-env", ownerEnv, "--source", src, "--clone", dbA);
            Check("i3_migration_on_clone_with_rollback_demonstrated", code == 0 && (bool)o["rollback_demonstrated"]!, o.ToJsonString());
            (code, o) = Cli("db-setup", "--config", cfA, "--admin-env", adminEnv, "--owner-env", ownerEnv, "--secrets", secretsA);
            Check("db_setup_hardening_probe_matrix_A", code == 0 && (bool)o["probe"]!["all_ok"]!, o.ToJsonString());
            results["probe_matrix_rows"] = o["probe"]!["probes"]!.AsArray().Count;
            timings["install_site_a"] = ms(swInstall);
            var siteA = cfgA.Site;
            var (pc, po) = Py("setup-site", "--site", siteA.Root);
            Check("site_a_signed_exclusion_channel", pc == 0, po);
            Directory.CreateDirectory(Path.GetDirectoryName(siteA.ChannelKeyPath)!);
            File.WriteAllBytes(siteA.ChannelKeyPath, RandomNumberGenerator.GetBytes(32));
            // local site data the restore must preserve: an Admin upload and a config file
            Directory.CreateDirectory(Path.Combine(cfgA.Root("uploads"), "admin"));
            File.WriteAllText(Path.Combine(cfgA.Root("uploads"), "admin", "local-order.txt"), "local Admin upload (test data)");
            File.WriteAllText(Path.Combine(cfgA.Root("config"), "appsettings.site.json"), "{\"site\":\"S3-C test site A\"}");

            // ================================================================ IMPORT and STAGE every release (production `stage`)
            var loaderA = LoaderEnv(secretsA, rolesA, dbA);
            foreach (var g in new[] { "G1", "G2", "G3", "G4" })
            {
                (code, o) = Cli("release-check", "--dir", (string)rel[g]!["bundle"]!);
                Check($"release_media_path_safe_{g}", code == 0, o.ToJsonString());
                (pc, po) = g == "G1" ? Py("import", "--site", siteA.Root, "--release", g, "--context", ctxPath) : Py("import", "--site", siteA.Root, "--release", g, "--context", ctxPath, "--stage-only");
                Check($"b01_import_{g}", pc == 0, po);
                (code, o) = Cli("stage", "--config", cfA, "--generation", Id(g), "--pg-env", ownerEnv, "--loader-env", loaderA, "--contracts", S("contracts"), "--development");
                Check($"stage_command_{g}", code == 0 && (bool)o["staged"]! && (string?)o["outcome"]!["result"] == "ACTIVE_DEGRADED", o.ToJsonString());
            }
            (code, o) = Cli("db-probe", "--config", cfA, "--owner-env", ownerEnv, "--secrets", secretsA, "--staging-schema", KnowledgeAllowlist.StagingSchema(Seq("G2")));
            Check("loader_has_no_create_on_staging_and_probe_matrix_holds", code == 0 && o["probe"]!["probes"]!.AsArray().Any(p => ((string?)p!["probe"])!.Contains("CREATE on kr_")), o.ToJsonString());

            // ================================================================ ACTIVATE through the journal (web = participant)
            (code, o) = Cli("init", "--site", siteA.Root, "--knowledge", Id("G1"), "--development");
            Check("journal_init_on_g1", code == 0, o.ToJsonString());
            var pipeA = "mimamsa-s3c-a-" + r;
            string[] ActA(string cmd, string to) => [cmd, "--site", siteA.Root, "--to", to, "--pg-env", ownerEnv, "--knowledge-rows", "--development", "--pipe", pipeA,
                                                     "--key", siteA.ChannelKeyPath, "--keep-previous", cfgA.KeepPrevious.ToString(), "--headroom", "0.1"];
            Environment.SetEnvironmentVariable(ownerEnv, S3cPg.OwnerDsn(dbA));   // the activation CLI reads the full DSN
            var w = await Web(cfgA, dbA, pipeA, "1");
            foreach (var g in new[] { "G2", "G3", "G4" })
            {
                (code, o) = Cli(ActA("activate", Id(g)));
                Check($"activate_{g}", code == 0 && (string?)o["knowledge"] == Id(g), o.ToJsonString());
                await StopAll(); w = await Web(cfgA, dbA, pipeA, g);
            }
            (code, o) = Cli("prune", "--site", siteA.Root, "--pg-env", ownerEnv, "--knowledge-rows", "--development", "--pipe", pipeA, "--key", siteA.ChannelKeyPath, "--keep-previous", "2");
            var installedA = new GenerationCatalog(siteA).Installed();
            Check("retention_prunes_only_beyond_active_plus_two_previous_distinct", code == 0 && o["removed"]!.AsArray().Select(x => (string)x!).SequenceEqual([Id("G1")])
                  && installedA.SequenceEqual(new[] { Id("G2"), Id("G3"), Id("G4") }.Order(StringComparer.Ordinal)), o.ToJsonString() + " installed=" + string.Join(",", installedA));
            (code, o) = Cli(ActA("rollback", Id("G3")));
            Check("rollback_to_g3", code == 0 && (string?)o["knowledge"] == Id("G3"), o.ToJsonString());
            (code, o) = Cli("prune", "--site", siteA.Root, "--pg-env", ownerEnv, "--knowledge-rows", "--development", "--pipe", pipeA, "--key", siteA.ChannelKeyPath, "--keep-previous", "2");
            Check("prune_after_rollback_keeps_active_and_previous_distinct", code == 0 && o["removed"]!.AsArray().Count == 0, o.ToJsonString());
            await StopAll(); w = await Web(cfgA, dbA, pipeA, "rb");

            // exclusion E1 (the admitted copy) accepted through the activation guard
            var readerA = ActivationCli.Reader(siteA, production: false);
            void Exclude(SiteLayout site, ExclusionReader reader, string[] what)
            {
                var seq = reader.Read().Sequence!.Value + 1;
                ActivationEngine.AcceptExclusion(site, new SiteInspector(site, reader), () =>
                {
                    var (c, outp) = Py(["exclude", "--site", site.Root, "--sequence", seq.ToString(), .. what]);
                    if (c != 0) throw new InvalidOperationException("exclusion append failed: " + outp);
                });
            }
            Exclude(siteA, readerA, ["--doc", S("admitted_doc")]);

            // what is served: documents and queries chosen from the active generation's records
            var gdir = Path.Combine(siteA.GenerationsDir, Id("G4"));
            var served = JsonNode.Parse(File.ReadAllText(Path.Combine(gdir, "generation.json")))!["servable"]!["documents"]!.AsArray().Select(x => (string)x!).Order(StringComparer.Ordinal).ToList();
            var docs = File.ReadAllLines(Path.Combine(gdir, "records", "documents.jsonl")).Where(l => l.Trim().Length > 0).Select(l => JsonNode.Parse(l)!.AsObject()).ToList();
            string docA = S("admitted_doc");
            var statute = docs.Where(d => (string?)d["doc_type"] == "act" && served.Contains((string)d["doc_id"]!) && (string)d["doc_id"]! != docA).Select(d => (string)d["doc_id"]!).Order(StringComparer.Ordinal).First();
            var legacy = served.Where(d => d != docA && d != statute).Take(2).ToList();
            async Task<JsonObject> Serve(Cp1Web web)
            {
                var c = await web.LoginAsync("reader");
                var snap = new JsonObject();
                var urls = new List<string>();
                foreach (var d in legacy.Append(statute).Append(docA).Append(S("held_doc")).Append(S("c16_only_doc")))
                    foreach (var suffix in new[] { "", "/text", "/sections", "/citation?page=1" }) urls.Add($"/api/documents/{Uri.EscapeDataString(d)}{suffix}");
                // permalink (citation by copy hash) for each document of interest: doc-id (E1) and copy-hash (E2) exclusions
                foreach (var d in legacy.Append(statute).Append(docA))
                    if (docs.FirstOrDefault(x => (string)x["doc_id"]! == d)?["source_copy"]?["sha256"] is JsonNode sh)
                        urls.Add($"/api/cite?doc={Uri.EscapeDataString(d)}&sha={(string)sh!}&page=1");
                foreach (var q in new[] { S("admitted_query"), "Synthetic held writ petition", "court martial", "disability pension", "Army Act" })
                    urls.Add("/api/search?q=" + Uri.EscapeDataString(q));
                foreach (var u in urls)
                {
                    var resp = await c.GetAsync(u);
                    var body = await resp.Content.ReadAsStringAsync();
                    string norm;
                    try { norm = Normalise(JsonNode.Parse(body))?.ToJsonString() ?? ""; } catch (System.Text.Json.JsonException) { norm = body; }
                    snap[u] = $"{(int)resp.StatusCode} {Sha(Encoding.UTF8.GetBytes(norm))}";
                }
                return snap;
            }
            var sBackup = await Serve(w);
            Check("a_admitted_copy_withdrawn_before_backup", sBackup[$"/api/documents/{docA}"]!.ToString().StartsWith("404"));
            Check("a_statute_served_before_backup", sBackup[$"/api/documents/{statute}"]!.ToString().StartsWith("200"));
            await StopAll();

            // ================================================================ BACKUP (encrypted; site DB as the backup role)
            var key = Path.Combine(work, "keys", "backup-test.key");
            Check("test_backup_key", Cli("new-key", "--out", key).code == 0);
            async Task<SortedDictionary<string, string>> SiteDump(string db)
            {
                await using var c = new NpgsqlConnection(S3cPg.OwnerDsn(db));
                await c.OpenAsync();
                var d = await SchemaDump.DumpSchemasAsync(c, ["public", "site"]);
                return new SortedDictionary<string, string>(d.Where(kv => !exclude.Any(t => kv.Key.Contains(t.Split('.')[1], StringComparison.Ordinal))).ToDictionary(), StringComparer.Ordinal);
            }
            var dumpAtBackup = await SiteDump(dbA);
            var backupEnv = Env("backup", S3cPg.RoleDsn(dbA, rolesA.Backup, File.ReadAllText(Path.Combine(secretsA, rolesA.Backup + ".pw")).Trim()));
            var media = Path.Combine(work, "offline-media");
            var swB = Stopwatch.StartNew();
            (code, o) = Cli("backup", "--config", cfA, "--key", key, "--db-env", backupEnv, "--dest", Path.Combine(media, "main"));
            timings["backup"] = ms(swB);
            Check("encrypted_backup_written_verified_and_copied_to_media", code == 0 && o["copied_to_media"] is JsonObject, o.ToJsonString());
            var mainDir = (string)o["copied_to_media"]!["path"]!;
            results["backup"] = new JsonObject { ["site_entries"] = o["site"]!["entries"]!.DeepClone(), ["appendonly_entries"] = o["appendonly"]!["entries"]!.DeepClone() };

            // ================================================================ CONTINUE after the backup: activation and exclusion E2
            w = await Web(cfgA, dbA, pipeA, "late");
            (code, o) = Cli(ActA("activate", Id("G4")));
            Check("activate_g4_after_backup", code == 0, o.ToJsonString());
            await StopAll(); w = await Web(cfgA, dbA, pipeA, "late2");
            var cA = await w.LoginAsync("reader");
            var statuteSha = (string)JsonNode.Parse(await cA.GetStringAsync($"/api/documents/{statute}/text"))!["copy_sha256"]!;
            Exclude(siteA, readerA, ["--sha", statuteSha]);
            var sLate = await Serve(w);
            Check("late_state_differs_from_backup_state", sLate[$"/api/documents/{statute}"]!.ToString().StartsWith("404") && !JsonNode.DeepEquals(sLate, sBackup));
            await StopAll();
            // the append-only stores copied SEPARATELY to their own media (only that part is kept there)
            (code, o) = Cli("backup", "--config", cfA, "--key", key, "--db-env", backupEnv, "--dest", Path.Combine(media, "late"));
            Check("late_backup", code == 0 && o["copied_to_media"] is JsonObject, o.ToJsonString());
            var lateDir = (string)o["copied_to_media"]!["path"]!;   // media copy: the site's own backup root is destroyed below
            var aoMedia = Path.Combine(media, "appendonly-late");
            Directory.CreateDirectory(aoMedia);
            File.Copy(Path.Combine(lateDir, "appendonly.mbk"), Path.Combine(aoMedia, "appendonly.mbk"));
            BackupRepack.UpdateSums(aoMedia);
            var journalA = File.ReadAllBytes(siteA.JournalPath);
            var exclA = File.ReadAllBytes(Path.Combine(siteA.ExclusionsDir, "ACCEPTED.json"));

            // ================================================================ DESTROY site A
            await S3cPg.DropDbAsync(dbA);
            await S3cPg.DropDbAsync(src);
            foreach (var k in InstallConfig.RootNames) S3cDirs.Delete(cfgA.Root(k));
            Check("site_a_destroyed", !Directory.Exists(siteA.Root) && !Directory.Exists(cfgA.Root("backup")));

            // ================================================================ FRESH isolated site B
            (code, o) = Cli("install-layout", "--config", cfB);
            Check("install_site_b", code == 0, o.ToJsonString());
            Environment.SetEnvironmentVariable(ownerEnv, S3cPg.OwnerDsn("postgres"));
            (code, o) = Cli("db-setup", "--config", cfB, "--admin-env", adminEnv, "--owner-env", ownerEnv, "--secrets", secretsB, "--create-db");
            Check("db_setup_site_b_fresh_roles", code == 0 && (bool)o["probe"]!["all_ok"]!, o.ToJsonString());
            var siteB = cfgB.Site;
            Dictionary<string, string> Snap(string root) => Directory.Exists(root)
                ? Directory.EnumerateFiles(root, "*", SearchOption.AllDirectories).ToDictionary(f => Path.GetRelativePath(root, f), f => Sha(File.ReadAllBytes(f))) : new();
            var bRoot = Path.Combine(work, "siteB");
            var cleanB = Snap(bRoot);
            async Task<long> TablesB()
            {
                await using var c = new NpgsqlConnection(S3cPg.OwnerDsn(dbB));
                await c.OpenAsync();
                await using var q = new NpgsqlCommand("SELECT count(*) FROM pg_class k JOIN pg_namespace n ON n.oid = k.relnamespace WHERE n.nspname IN ('public','site') AND k.relkind = 'r'", c);
                return (long)(await q.ExecuteScalarAsync())!;
            }

            // ---- negative drills first: each refused, the target untouched
            string Drill(string label, Action<string> damage, bool site = true, bool ao = true, string? from = null)
            {
                var d = Path.Combine(media, "drill-" + label);
                Directory.CreateDirectory(d);
                if (site) File.Copy(Path.Combine(from ?? mainDir, "site.mbk"), Path.Combine(d, "site.mbk"));
                if (ao) File.Copy(Path.Combine(from ?? mainDir, "appendonly.mbk"), Path.Combine(d, "appendonly.mbk"));
                damage(d);
                BackupRepack.UpdateSums(d);
                return d;
            }
            var wrongKey = Path.Combine(work, "keys", "wrong.key");
            Cli("new-key", "--out", wrongKey);
            var drills = new (string name, string[] args, string expect)[]
            {
                ("wrong_key", ["--key", wrongKey, "--backup", mainDir], "BACKUP_WRONG_KEY"),
                ("tampered", ["--key", key, "--backup", Drill("tamper", d => { var b = File.ReadAllBytes(Path.Combine(d, "site.mbk")); b[b.Length / 3] ^= 0x10; File.WriteAllBytes(Path.Combine(d, "site.mbk"), b); })], "BACKUP_AUTH_FAILED"),
                ("truncated", ["--key", key, "--backup", Drill("trunc", d => { var b = File.ReadAllBytes(Path.Combine(d, "site.mbk")); File.WriteAllBytes(Path.Combine(d, "site.mbk"), b[..(b.Length - 100)]); })], "BACKUP_TRUNCATED"),
                ("partial_site_part_missing", ["--key", key, "--backup", Drill("partial", _ => { }, site: false)], "BACKUP_PARTIAL"),
                ("appendonly_missing", ["--key", key, "--backup", Drill("noao", _ => { }, ao: false)], "APPENDONLY_MISSING"),
                ("stale_appendonly_older_than_database", ["--key", key, "--backup", Drill("stale", _ => { }, ao: false, from: lateDir), "--appendonly-from", Drill("old-ao", _ => { }, site: false)], "APPENDONLY_OLDER_THAN_DATABASE"),
            };
            foreach (var (name, args, expect) in drills)
            {
                (code, o) = Cli(["restore", "--config", cfB, .. args, "--db-env", ownerEnv]);
                Check("drill_refused_" + name, code == 2 && (string?)o["code"] == expect, o.ToJsonString());
                Check("drill_target_untouched_" + name, await TablesB() == 0 && Snap(bRoot).Count == cleanB.Count && Snap(bRoot).All(kv => cleanB.TryGetValue(kv.Key, out var v) && v == kv.Value));
            }

            // ---- the restore: the backup's site part + the separately kept, NEWER append-only stores
            var swR = Stopwatch.StartNew();
            (code, o) = Cli("restore", "--config", cfB, "--key", key, "--backup", mainDir, "--appendonly-from", aoMedia, "--db-env", ownerEnv, "--secrets", secretsB);
            timings["restore_command"] = ms(swR);
            Check("restore_succeeds", code == 0, o.ToJsonString());
            Check("restore_follows_journal_head_not_backup", (string?)o["journal_head"]!["knowledge"] == Id("G4") && ((string?)o["appendonly"]!["journal_from"])!.StartsWith("offline copy"), o["appendonly"]!.ToJsonString());
            Check("restore_latest_exclusions_win", ((string?)o["appendonly"]!["exclusions_from"])!.StartsWith("offline copy"));
            Check("restore_reimport_required_head_only", o["reimport_required"]!.AsArray().Select(x => (string)x!).SequenceEqual([Id("G4")]));
            Check("restore_probe_matrix_holds_on_b", (bool)o["probe"]!["all_ok"]!);
            Check("restored_journal_equals_destroyed_site_journal", File.ReadAllBytes(siteB.JournalPath).SequenceEqual(journalA));
            Check("restored_exclusions_equal_destroyed_site", File.ReadAllBytes(Path.Combine(siteB.ExclusionsDir, "ACCEPTED.json")).SequenceEqual(exclA));
            Check("restored_site_data_equals_backup_ordered_dumps", (await SiteDump(dbB)).SequenceEqual(dumpAtBackup));
            Check("restored_local_upload_and_config", File.ReadAllText(Path.Combine(cfgB.Root("uploads"), "admin", "local-order.txt")) == "local Admin upload (test data)"
                  && File.Exists(Path.Combine(cfgB.Root("config"), "appsettings.site.json")));
            Check("nothing_serves_before_recovery", siteB.ReadMarker() == SiteState.RECOVERING);

            // ---- re-import the journal-head release from media, stage, recover
            var swRe = Stopwatch.StartNew();
            Environment.SetEnvironmentVariable(ownerEnv, S3cPg.OwnerDsn("postgres"));
            var loaderB = LoaderEnv(secretsB, rolesB, dbB);
            (pc, po) = Py("import", "--site", siteB.Root, "--release", "G4", "--context", ctxPath, "--stage-only");
            Check("reimport_head_from_media_stage_only", pc == 0, po);
            (code, o) = Cli("stage", "--config", cfB, "--generation", Id("G4"), "--pg-env", ownerEnv, "--loader-env", loaderB, "--contracts", S("contracts"), "--development");
            var stageIssues = o["issues"]?.AsArray().Select(x => (string)x!).ToList() ?? [];
            // S3C-B01-B03-REIMPORT-AFTER-EXCLUSION resolved (coordinator decision, option 2): the release is materialised
            // exactly as shipped; copies withdrawn by the site (E1 by doc id, E2 by copy hash) are only MARKED
            // `locally_excluded`, so B03/B04 re-derivation from the materialised release equals the shipped rows.
            Check("reimport_after_exclusions_stages_without_rederive_mismatch", code == 0 && (bool)o["staged"]! && !stageIssues.Any(i => i.StartsWith("KR_ROWS_REDERIVE_MISMATCH")), o.ToJsonString());
            var gB = JsonNode.Parse(File.ReadAllText(Path.Combine(siteB.GenerationsDir, Id("G4"), "generation.json")))!;
            var lxDocs = gB["locally_excluded"]?["documents"]?.AsArray().Select(x => (string)x!).ToHashSet() ?? [];
            var servB = gB["servable"]!["documents"]!.AsArray().Select(x => (string)x!).ToHashSet();
            Check("withdrawn_copies_marked_not_servable_and_materialised", lxDocs.Contains(docA) && lxDocs.Contains(statute) && !servB.Contains(docA) && !servB.Contains(statute)
                  && File.ReadAllText(Path.Combine(siteB.GenerationsDir, Id("G4"), "records", "documents.jsonl")).Contains($"\"doc_id\": \"{docA}\""), gB["locally_excluded"]?.ToJsonString());
            var defaultLoad = Mimamsa.Core.Generation.GenerationStore.Load(siteB.Root, null, Mimamsa.Core.Generation.TextStoreOptions.Memory, null, Id("G4"));
            var shippedLoad = Mimamsa.Core.Generation.GenerationStore.Load(siteB.Root, null, Mimamsa.Core.Generation.TextStoreOptions.Memory, null, Id("G4"), includeLocallyExcluded: true);
            Check("default_mode_loader_leaves_locally_excluded_out_fail_closed", !defaultLoad.Documents.ContainsKey(docA) && !defaultLoad.Documents.ContainsKey(statute)
                  && shippedLoad.Documents.ContainsKey(docA) && shippedLoad.Documents.ContainsKey(statute));
            Environment.SetEnvironmentVariable(ownerEnv, S3cPg.OwnerDsn(dbB));
            (code, o) = Cli("recover", "--site", siteB.Root, "--pg-env", ownerEnv, "--knowledge-rows", "--development");
            timings["reimport_stage_recover"] = ms(swRe);
            timings["restore_total"] = (long)timings["restore_command"]! + ms(swRe);
            var journalB = ActivationJournal.Read(siteB.JournalPath);
            int opened = journalB.Transactions.Count(t => journalB.Has(t, "OPEN"));
            Check("recover_reconciles_views_publication_rows_and_exclusions", code == 0 && (string?)o["state"] == "OPEN" && (string?)o["knowledge"] == Id("G4")
                  && (string?)o["exclusion_reader"] == "HEALTHY", o.ToJsonString());
            await using (var c = new NpgsqlConnection(S3cPg.OwnerDsn(dbB)))
            {
                await c.OpenAsync();
                await using var q = new NpgsqlCommand("SELECT (SELECT count(*) FROM site_activation.release_activation), (SELECT generation FROM site_activation.knowledge_head)", c);
                await using var rr = await q.ExecuteReaderAsync();
                await rr.ReadAsync();
                Check("publication_rows_reconciled_from_journal", rr.GetInt64(0) == opened && rr.GetString(1) == Id("G4"), $"{rr.GetInt64(0)} rows, {opened} committed; head {rr.GetString(1)}");
            }
            Check("applied_exclusions_latest", siteB.ReadApplied()[Id("G4")] == (long)JsonNode.Parse(exclA)!["sequence"]!);

            // ---- serve and compare with what the destroyed site last served
            var pipeB = "mimamsa-s3c-b-" + r;
            Directory.CreateDirectory(Path.GetDirectoryName(siteB.ChannelKeyPath)!);
            File.WriteAllBytes(siteB.ChannelKeyPath, RandomNumberGenerator.GetBytes(32));   // per-install secret: never backed up
            var wb = await Web(cfgB, dbB, pipeB, "restored");
            var sRestored = await Serve(wb);
            var diff = sLate.Where(kv => sRestored[kv.Key]?.ToString() != kv.Value?.ToString()).Select(kv => kv.Key).ToList();
            Check("restored_site_serves_identically", diff.Count == 0 && sRestored.Count == sLate.Count, string.Join(", ", diff));
            Check("exclusion_e1_intact_after_restore", sRestored[$"/api/documents/{docA}"]!.ToString().StartsWith("404") && sRestored[$"/api/documents/{docA}/text"]!.ToString().StartsWith("404"));
            Check("exclusion_e2_intact_after_restore", sRestored[$"/api/documents/{statute}"]!.ToString().StartsWith("404"));
            Check("legacy_copies_still_served", legacy.All(d => sRestored[$"/api/documents/{d}"]!.ToString().StartsWith("200")));
            results["served_requests_compared"] = sRestored.Count;

            // ---- a release that is not retained: refused, then re-imported from media and rolled back to
            string[] ActB(string cmd, string to) => [cmd, "--site", siteB.Root, "--to", to, "--pg-env", ownerEnv, "--knowledge-rows", "--development", "--pipe", pipeB,
                                                     "--key", siteB.ChannelKeyPath, "--keep-previous", cfgB.KeepPrevious.ToString()];
            (code, o) = Cli(ActB("rollback", Id("G3")));
            Check("rollback_to_release_not_retained_refused", code == 2, o.ToJsonString());
            Environment.SetEnvironmentVariable(ownerEnv, S3cPg.OwnerDsn("postgres"));
            (pc, po) = Py("import", "--site", siteB.Root, "--release", "G3", "--context", ctxPath, "--stage-only");
            Check("reimport_g3_from_media", pc == 0, po);
            (code, o) = Cli("stage", "--config", cfB, "--generation", Id("G3"), "--pg-env", ownerEnv, "--loader-env", loaderB, "--contracts", S("contracts"), "--development");
            Check("stage_g3_on_b", code == 0, o.ToJsonString());
            Environment.SetEnvironmentVariable(ownerEnv, S3cPg.OwnerDsn(dbB));
            (code, o) = Cli(ActB("rollback", Id("G3")));
            Check("rollback_after_reimport", code == 0 && (string?)o["knowledge"] == Id("G3"), o.ToJsonString());
            await StopAll();
            var wb2 = await Web(cfgB, dbB, pipeB, "rolled-back");
            var cB = await wb2.LoginAsync("reader");
            Check("rollback_cannot_resurrect_excluded_items",
                  (await cB.GetAsync($"/api/documents/{docA}")).StatusCode == HttpStatusCode.NotFound && (await cB.GetAsync($"/api/documents/{statute}")).StatusCode == HttpStatusCode.NotFound);

            results["journal_steps_b"] = new JsonArray(ActivationJournal.Read(siteB.JournalPath).Entries.Select(e => (JsonNode)e.Step).ToArray());
            File.WriteAllText(S("results"), results.ToJsonString(new System.Text.Json.JsonSerializerOptions { WriteIndented = true }));
        }
        finally
        {
            await StopAll();
            NpgsqlConnection.ClearAllPools();
            foreach (var d in new[] { dbB, dbA, src }) try { await S3cPg.DropDbAsync(d); } catch (Exception e) { Console.Error.WriteLine($"s3c cleanup {d}: {e.GetType().Name}"); }
            foreach (var role in rolesA.All.Concat(rolesB.All)) try { await S3cPg.DropRoleAsync(role); } catch (Exception e) { Console.Error.WriteLine($"s3c cleanup role: {e.GetType().Name}"); }
        }
    }
}
