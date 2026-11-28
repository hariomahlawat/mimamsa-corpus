// C16 S3-C (B07): configuration, four-release layout, reinstall, and the MEASURED disk preflight (refuses on failure,
// records measured values). System-level parts (services, virtual accounts, ACLs, a filled volume) run in CI only
// (app/installer/windows, .github/workflows/c16-s3c-install.yml); nothing here changes the host outside temp folders.
using System.Text;
using System.Text.Json.Nodes;
using Mimamsa.Core.Activation;
using Mimamsa.Core.Install;

namespace Mimamsa.Tests.Install;

public class InstallLayoutTests
{
    static InstallConfigException Bad(string json) => Assert.Throws<InstallConfigException>(() => InstallConfig.Parse(Encoding.UTF8.GetBytes(json)));

    [Fact]
    public void Config_refuses_production_mode_unknown_or_missing_roots_and_bad_limits()
    {
        var b = S3cDirs.New("cfg");
        try
        {
            var good = JsonNode.Parse(S3cDirs.Config(b).SourceBytes)!.AsObject();
            string With(Action<JsonObject> f) { var c = good.DeepClone().AsObject(); f(c); return c.ToJsonString(); }
            Assert.Equal("CONFIG_MODE", Bad(With(c => c["mode"] = "production")).Code);
            Assert.Equal("CONFIG_ROOT_MISSING", Bad(With(c => c["roots"]!.AsObject().Remove("backup"))).Code);
            Assert.Equal("CONFIG_ROOT_UNKNOWN", Bad(With(c => c["roots"]!["elsewhere"] = b)).Code);
            Assert.Equal("CONFIG_RETENTION", Bad(With(c => c["retention"]!["keep_previous"] = 0)).Code);
            Assert.Equal("CONFIG_HEADROOM", Bad(With(c => c["headroom_fraction"] = -0.5)).Code);
            Assert.Equal("CONFIG_IDENTITY", Bad(With(c => c["identities"] = new JsonObject { ["web"] = "Mimamsa Web" })).Code);
            Assert.Equal("CONFIG_FORMAT", Bad(With(c => c["format"] = "x")).Code);
            Assert.Equal(3, InstallConfig.Parse(Encoding.UTF8.GetBytes(With(c => c["retention"]!["keep_previous"] = 3))).KeepPrevious);
        }
        finally { S3cDirs.Delete(b); }
    }

    [Fact]
    public void Four_releases_have_distinct_roots_and_store_roots_stay_outside_the_application()
    {
        var b = S3cDirs.New("rel");
        try
        {
            var cfg = S3cDirs.Config(b);
            Assert.Empty(cfg.Issues());
            var r = cfg.Releases();
            Assert.Equal(["application", "intelligence", "knowledge", "site_data"], r.Keys.Order(StringComparer.Ordinal));
            var all = r.Values.SelectMany(x => x).ToList();
            Assert.Equal(all.Count, all.Distinct(StringComparer.OrdinalIgnoreCase).Count());   // no directory belongs to two releases
            foreach (var s in cfg.StoreRoots()) Assert.False(s.StartsWith(cfg.Root("application"), StringComparison.OrdinalIgnoreCase));
            // a store root inside the application directory, or inside another root, is refused
            var j = JsonNode.Parse(cfg.SourceBytes)!.AsObject();
            j["roots"]!["text_store"] = Path.Combine(cfg.Root("application"), "text-store");
            var nested = InstallConfig.Parse(Encoding.UTF8.GetBytes(j.ToJsonString()));
            Assert.Contains(nested.Issues(), i => i.Code == "ROOT_OVERLAP");
            Assert.Throws<InstallConfigException>(() => InstallLayout.Create(nested, null, "test"));
        }
        finally { S3cDirs.Delete(b); }
    }

    [Fact]
    public void Layout_is_idempotent_and_a_reinstall_keeps_site_data()
    {
        var b = S3cDirs.New("lay");
        try
        {
            var cfg = S3cDirs.Config(b);
            var rec = InstallLayout.Create(cfg, null, "test");
            foreach (var k in InstallConfig.RootNames) Assert.True(Directory.Exists(cfg.Root(k)), k);
            foreach (var d in InstallConfig.SiteDerived) Assert.True(Directory.Exists(Path.Combine(cfg.Root("site"), d)), d);
            Assert.True(File.Exists(Path.Combine(cfg.Root("config"), InstallLayout.RecordFile)));
            Assert.Equal(cfg.Sha256, (string?)rec["config_sha256"]);
            // site data written between installs
            var sentinels = new[] { Path.Combine(cfg.Root("site"), "journal", "journal.jsonl"), Path.Combine(cfg.Root("uploads"), "u.pdf"),
                                    Path.Combine(cfg.Root("site"), "exclusions", "ACCEPTED.json"), Path.Combine(cfg.Root("backup"), "x.mbk") };
            foreach (var s in sentinels) File.WriteAllText(s, "keep " + s);
            var rec2 = InstallLayout.Create(cfg, null, "test");
            Assert.Empty(rec2["created"]!.AsArray());
            foreach (var s in sentinels) Assert.Equal("keep " + s, File.ReadAllText(s));
            Assert.Equal(2, Directory.GetFiles(Path.Combine(cfg.Root("logs"), "install")).Length);   // append-only history
        }
        finally { S3cDirs.Delete(b); }
    }

    [Fact]
    public void A_pre_existing_junction_inside_a_root_refuses_the_install()
    {
        var b = S3cDirs.New("lay-link");
        try
        {
            var cfg = S3cDirs.Config(b);
            InstallLayout.Create(cfg, null, "test");
            var elsewhere = Directory.CreateDirectory(Path.Combine(b, "elsewhere")).FullName;
            Directory.Delete(Path.Combine(cfg.Root("site"), "vault"));
            Assert.True(S3cDirs.Link(Path.Combine(cfg.Root("site"), "vault"), elsewhere));
            Assert.Equal("PATH_REPARSE_POINT", Assert.Throws<InstallConfigException>(() => InstallLayout.Create(cfg, null, "test")).Code);
        }
        finally { S3cDirs.Delete(b); }
    }

    [Fact]
    public void Preflight_measures_payload_bytes_applies_configured_headroom_and_refuses_when_short()
    {
        var b = S3cDirs.New("pf");
        try
        {
            var cfg = S3cDirs.Config(b, headroom: 0.25, minFree: 1000);
            var payload = Directory.CreateDirectory(Path.Combine(b, "payload")).FullName;
            File.WriteAllBytes(Path.Combine(payload, "a.bin"), new byte[40_000]);
            Directory.CreateDirectory(Path.Combine(payload, "sub"));
            File.WriteAllBytes(Path.Combine(payload, "sub", "b.bin"), new byte[10_000]);
            Assert.Equal(50_000, InstallPreflight.MeasureBytes(payload));
            var ps = new[] { new PreflightPayload("application", cfg.Root("application"), payload), new PreflightPayload("release", cfg.Root("site"), null, 8_000) };
            long need = (long)Math.Ceiling(58_000 * 1.25) + 1000;
            var fail = InstallPreflight.Run(cfg, ps, new FixedDiskProbe(need - 1));
            Assert.Equal("FAIL", (string?)fail["result"]);
            var v = fail["volumes"]!.AsArray().Single(x => (long)x!["measured_payload_bytes"]! == 58_000)!;
            Assert.Equal(need, (long)v["required_bytes"]!);
            Assert.Equal(need - 1, (long)v["free_bytes"]!);
            Assert.False((bool)fail["fixed_allocation"]!);
            var rec = InstallPreflight.Record(cfg, fail);
            Assert.True(File.Exists(rec) && rec!.EndsWith("FAIL.json"));
            Assert.Equal("PASS", (string?)InstallPreflight.Run(cfg, ps, new FixedDiskProbe(need))["result"]);
            // the real probe measures the actual volume
            var real = InstallPreflight.Run(cfg, ps);
            Assert.True(real["volumes"]!.AsArray().All(x => (long)x!["free_bytes"]! > 0));
        }
        finally { S3cDirs.Delete(b); }
    }

    [Fact]
    public void Install_layout_command_refuses_on_a_failed_preflight_and_writes_nothing_but_the_record()
    {
        var b = S3cDirs.New("pf-cli");
        try
        {
            var cfg = S3cDirs.Config(b, minFree: long.MaxValue / 4);   // more than any real volume has free
            var cfgFile = Path.Combine(b, "install.json");
            File.WriteAllBytes(cfgFile, cfg.SourceBytes);
            var sw = new StringWriter();
            int code = InstallCli.Run(["install-layout", "--config", cfgFile], sw);
            var o = JsonNode.Parse(sw.ToString())!;
            Assert.Equal(2, code);
            Assert.Equal("PREFLIGHT_FAILED", (string?)o["code"]);
            Assert.False(Directory.Exists(cfg.Root("site")));
            Assert.True(Directory.GetFiles(Path.Combine(cfg.Root("logs"), "preflight")).Single().EndsWith("FAIL.json"));
            // the same configuration with no minimum installs
            var ok = S3cDirs.Config(b);
            File.WriteAllBytes(cfgFile, ok.SourceBytes);
            sw = new StringWriter();
            Assert.Equal(0, InstallCli.Run(["install-layout", "--config", cfgFile, "--bytes", "release=site=1000"], sw));
            Assert.True(Directory.Exists(Path.Combine(ok.Root("site"), "journal")));
        }
        finally { S3cDirs.Delete(b); }
    }
}
