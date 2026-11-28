// C16 Tranche B Stage 3 S3-C (B07): the development installer's configuration and the four-release directory layout
// (architecture section 2 and 7; plan B07, WD-4/5/6/13). DEVELOPMENT and TEST installations only: the target hardware,
// Windows edition, production keys and operational migration remain owner gates (OG-1, OG-2, OG-3).
//
// Four separately versioned things, each with its own roots:
//   application   binaries, web assets, application DDL, bundled trust list and default config (installer channel)
//   knowledge     vault, generations, pointers (site root), text-store, search-index (release-import channel)
//   intelligence  models (site root) and vectors (release-import channel; MODEL releases are blocked, B10)
//   site_data     journal, activation-log, exclusions, activation-state, trust, control channel key (site root), plus
//                 uploads, config, backup and logs; NEVER written by a release
// Every root is a configuration value (WD-6). The current B06/B01 code fixes some directories relative to the site root
// (SiteLayout: vault, generations, journal, activation-log, exclusions, activation-state, models, trust, control); those
// are reported here as derived from `site` and cannot be relocated separately yet (an open item, not silently ignored).
// Store roots must be outside the application directory and outside each other (CG-3). Headroom, minimum free space and
// retention limits are configurable; nothing here is a fixed allocation (D5).
using System.Security.Cryptography;
using System.Text;
using System.Text.Json.Nodes;
using Mimamsa.Core.Activation;

namespace Mimamsa.Core.Install;

public sealed class InstallConfigException(string code, string message) : Exception(code + ": " + message)
{
    public string Code { get; } = code;
}

public sealed class InstallConfig
{
    public const string Format = "mimamsa-dev-install/1";
    public static readonly string[] RootNames = ["application", "site", "text_store", "search_index", "vectors", "uploads", "config", "backup", "logs", "import", "scratch"];
    /// Directories the existing site code derives from the site root (SiteLayout / importer); not separately relocatable.
    public static readonly string[] SiteDerived = ["vault", "generations", "journal", "activation-log", "exclusions", "activation-state", "models", "trust", "control"];

    public required string Mode { get; init; }                       // "development" | "test" (production is refused here)
    public required IReadOnlyDictionary<string, string> Roots { get; init; }
    public double HeadroomFraction { get; init; } = 0.1;
    public long MinFreeBytes { get; init; }
    public int KeepPrevious { get; init; } = 2;                      // WD-13: active + two previous distinct verified releases
    public string WebIdentity { get; init; } = "MimamsaWeb";
    public string ActivationIdentity { get; init; } = "MimamsaActivation";
    public string? DatabaseName { get; init; }
    public string RolePrefix { get; init; } = "mimamsa_";
    /// Disposable-name guard for development/CI databases: when set, every database the installer creates, clones,
    /// migrates or restores into must start with it (never an operational database).
    public string? DisposablePrefix { get; init; }
    public IReadOnlyList<string> BackupSchemas { get; init; } = ["site"];
    public IReadOnlyList<string> BackupExcludeTables { get; init; } = [];
    public string? PgBin { get; init; }
    public byte[] SourceBytes { get; init; } = [];

    public string Root(string name) => Roots.TryGetValue(name, out var r) ? r : throw new InstallConfigException("CONFIG_ROOT_MISSING", name);
    public SiteLayout Site => new(Root("site"));
    public string Sha256 => Convert.ToHexString(SHA256.HashData(SourceBytes)).ToLowerInvariant();

    public static InstallConfig Load(string path) => Parse(File.ReadAllBytes(path));

    public static InstallConfig Parse(byte[] bytes)
    {
        JsonObject o;
        try { o = JsonNode.Parse(bytes)!.AsObject(); }
        catch (Exception e) when (e is System.Text.Json.JsonException or InvalidOperationException) { throw new InstallConfigException("CONFIG_MALFORMED", e.Message); }
        if ((string?)o["format"] != Format) throw new InstallConfigException("CONFIG_FORMAT", "format must be " + Format);
        var mode = (string?)o["mode"] ?? "";
        if (mode is not ("development" or "test"))
            throw new InstallConfigException("CONFIG_MODE", "only development and test installations are supported (production is owner gate OG-1/OG-2/OG-3)");
        var roots = new Dictionary<string, string>(StringComparer.Ordinal);
        foreach (var (k, v) in o["roots"]?.AsObject() ?? throw new InstallConfigException("CONFIG_ROOTS", "roots missing"))
        {
            if (!RootNames.Contains(k)) throw new InstallConfigException("CONFIG_ROOT_UNKNOWN", k);
            roots[k] = (string?)v ?? throw new InstallConfigException("CONFIG_ROOT_MISSING", k);
        }
        foreach (var k in RootNames) if (!roots.ContainsKey(k)) throw new InstallConfigException("CONFIG_ROOT_MISSING", k);
        double head = (double?)o["headroom_fraction"] ?? 0.1;
        if (!(head >= 0 && head <= 10)) throw new InstallConfigException("CONFIG_HEADROOM", "headroom_fraction must be within [0, 10]");
        int keep = (int?)o["retention"]?["keep_previous"] ?? 2;
        if (keep < 1 || keep > 16) throw new InstallConfigException("CONFIG_RETENTION", "retention.keep_previous must be within [1, 16]");
        long minFree = (long?)o["min_free_bytes"] ?? 0;
        if (minFree < 0) throw new InstallConfigException("CONFIG_MIN_FREE", "min_free_bytes must not be negative");
        var db = o["database"]?.AsObject();
        static List<string> Strs(JsonNode? n) => n?.AsArray().Select(x => (string)x!).ToList() ?? new();
        var cfg = new InstallConfig
        {
            Mode = mode, Roots = roots, HeadroomFraction = head, KeepPrevious = keep, MinFreeBytes = minFree,
            WebIdentity = (string?)o["identities"]?["web"] ?? "MimamsaWeb",
            ActivationIdentity = (string?)o["identities"]?["activation"] ?? "MimamsaActivation",
            DatabaseName = (string?)db?["name"], RolePrefix = (string?)db?["role_prefix"] ?? "mimamsa_",
            DisposablePrefix = (string?)db?["disposable_prefix"], PgBin = (string?)db?["pg_bin"],
            BackupSchemas = o["backup"]?["db_schemas"] is { } bs ? Strs(bs) : ["site"],
            BackupExcludeTables = Strs(o["backup"]?["exclude_tables"]),
            SourceBytes = bytes,
        };
        foreach (var id in new[] { cfg.WebIdentity, cfg.ActivationIdentity })
            if (!System.Text.RegularExpressions.Regex.IsMatch(id, "^[A-Za-z][A-Za-z0-9_]{1,63}$")) throw new InstallConfigException("CONFIG_IDENTITY", "service identity names are [A-Za-z][A-Za-z0-9_]*");
        if (!System.Text.RegularExpressions.Regex.IsMatch(cfg.RolePrefix, "^[a-z_][a-z0-9_]{0,30}$")) throw new InstallConfigException("CONFIG_ROLE_PREFIX", "role_prefix");
        foreach (var s in cfg.BackupSchemas.Concat(cfg.BackupExcludeTables.Select(t => t.Split('.')[0])))
            if (!System.Text.RegularExpressions.Regex.IsMatch(s, "^[a-z_][a-z0-9_]{0,62}$")) throw new InstallConfigException("CONFIG_BACKUP_SCHEMA", s);
        return cfg;
    }

    /// The four releases and the directories each owns (derived site directories included).
    public IReadOnlyDictionary<string, IReadOnlyList<string>> Releases()
    {
        string S(string d) => Path.Combine(Root("site"), d);
        return new Dictionary<string, IReadOnlyList<string>>(StringComparer.Ordinal)
        {
            ["application"] = [Root("application")],
            ["knowledge"] = [S("vault"), S("generations"), Root("text_store"), Root("search_index"), Root("import")],
            ["intelligence"] = [S("models"), Root("vectors")],
            ["site_data"] = [S("journal"), S("activation-log"), S("exclusions"), S("activation-state"), S("trust"), S("control"),
                             Root("uploads"), Root("config"), Root("backup"), Root("logs")],
        };
    }

    /// Store roots the web identity may read but never write (CG-3); written only by the activation identity.
    public IReadOnlyList<string> StoreRoots() => [Root("site"), Root("text_store"), Root("search_index"), Root("vectors")];

    /// Validation: every root safe (PathSafety.RootIssues), all roots distinct and not nested, nothing inside the
    /// application directory, the backup root not inside the site.
    public List<PathIssue> Issues()
    {
        var o = new List<PathIssue>();
        foreach (var (k, v) in Roots) o.AddRange(PathSafety.RootIssues(v).Select(i => i with { Detail = $"[{k}] " + i.Detail }));
        o.AddRange(PathSafety.OverlapIssues(Roots));
        return o;
    }
}

/// Lays down the layout. Idempotent; never deletes or overwrites anything that exists (a reinstall keeps site data).
public static class InstallLayout
{
    public const string RecordFile = "INSTALL_RECORD.json";

    public static JsonObject Create(InstallConfig cfg, JsonObject? preflight, string toolVersion)
    {
        var issues = cfg.Issues();
        if (issues.Count > 0) throw new InstallConfigException(issues[0].Code, string.Join("; ", issues));
        var created = new JsonArray();
        void Ensure(string d)
        {
            if (Directory.Exists(d)) return;
            Directory.CreateDirectory(d);
            created.Add(d);
        }
        foreach (var k in InstallConfig.RootNames) Ensure(cfg.Root(k));
        foreach (var d in InstallConfig.SiteDerived) Ensure(Path.Combine(cfg.Root("site"), d));
        foreach (var d in new[] { "preflight", "install" }) Ensure(Path.Combine(cfg.Root("logs"), d));
        // after creation: the tree must contain no reparse points (a pre-existing junction would redirect a store)
        foreach (var k in InstallConfig.RootNames)
        {
            var t = PathSafety.TreeIssues(cfg.Root(k), out _).Where(i => i.Code is "PATH_REPARSE_POINT" or "PATH_SHORT_NAME_ALIAS" or "PATH_RESERVED_NAME").ToList();
            if (t.Count > 0) throw new InstallConfigException(t[0].Code, string.Join("; ", t));
        }
        var releases = new JsonObject();
        foreach (var (r, dirs) in cfg.Releases()) releases[r] = new JsonArray(dirs.Select(d => (JsonNode)d).ToArray());
        var rec = new JsonObject
        {
            ["format"] = "mimamsa-dev-install-record/1", ["mode"] = cfg.Mode, ["config_sha256"] = cfg.Sha256,
            ["tool_version"] = toolVersion, ["recorded_at"] = DateTimeOffset.UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ"),
            ["releases"] = releases, ["created"] = created, ["preflight"] = preflight?.DeepClone(),
            ["keep_previous"] = cfg.KeepPrevious, ["headroom_fraction"] = cfg.HeadroomFraction,
            ["relocatable_roots"] = new JsonArray(InstallConfig.RootNames.Select(x => (JsonNode)x).ToArray()),
            ["site_derived_not_yet_relocatable"] = new JsonArray(InstallConfig.SiteDerived.Select(x => (JsonNode)x).ToArray()),
        };
        // history, append-only: each install run adds a record; nothing earlier is overwritten
        var hist = Path.Combine(cfg.Root("logs"), "install", $"INSTALL-{DateTimeOffset.UtcNow:yyyyMMddTHHmmssfffZ}-{Convert.ToHexString(RandomNumberGenerator.GetBytes(3)).ToLowerInvariant()}.json");
        DurableFile.WriteAtomic(hist, Encoding.UTF8.GetBytes(rec.ToJsonString(new System.Text.Json.JsonSerializerOptions { WriteIndented = true })));
        DurableFile.WriteAtomic(Path.Combine(cfg.Root("config"), RecordFile), Encoding.UTF8.GetBytes(rec.ToJsonString(new System.Text.Json.JsonSerializerOptions { WriteIndented = true })));
        return rec;
    }
}
