// C16 S3-C test support: disposable install layouts (MIMAMSA_S3C_DIR, else the temp folder), disposable PostgreSQL
// databases and roles (prefix c16s3c_ only, guarded), links/junctions for the path negatives, and a re-packer that
// rebuilds an encrypted backup part with chosen entries (correct manifest and checksums, so only the semantic checks
// under test can fire). Never touches an operational site, database or key.
using System.Diagnostics;
using System.Formats.Tar;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json.Nodes;
using Mimamsa.Core.Install;
using Npgsql;

namespace Mimamsa.Tests.Install;

public static class S3cDirs
{
    public static string Base
    {
        get
        {
            var b = Environment.GetEnvironmentVariable("MIMAMSA_S3C_DIR") is { Length: > 0 } e ? e : Path.Combine(Path.GetTempPath(), "mimamsa-c16s3c");
            Directory.CreateDirectory(b);
            return b;
        }
    }

    public static string New(string label)
    {
        var d = Path.Combine(Base, label + "-" + Guid.NewGuid().ToString("N")[..8]);
        Directory.CreateDirectory(d);
        return d;
    }

    public static void Delete(string dir)
    {
        if (!Directory.Exists(dir)) return;
        // remove links first, without following them
        foreach (var e in new DirectoryInfo(dir).EnumerateFileSystemInfos("*", new EnumerationOptions { RecurseSubdirectories = true, AttributesToSkip = 0, IgnoreInaccessible = true }).ToList())
        {
            try
            {
                if (PathSafety.IsReparse(e)) { if (e is DirectoryInfo d) d.Delete(); else e.Delete(); }
                else if (e is FileInfo f) f.Attributes = FileAttributes.Normal;
            }
            catch (Exception) { }
        }
        for (int i = 0; i < 20; i++)
        {
            try { if (Directory.Exists(dir)) Directory.Delete(dir, true); return; }
            catch (Exception x) when (x is IOException or UnauthorizedAccessException) { Thread.Sleep(100); }
        }
    }

    /// A configuration whose roots are distinct directories under `baseDir` (site may be given).
    public static InstallConfig Config(string baseDir, string? site = null, int keep = 2, double headroom = 0.1, string? db = null, string? prefix = null,
                                       IEnumerable<string>? backupSchemas = null, IEnumerable<string>? exclude = null, long minFree = 0)
    {
        var roots = new JsonObject();
        foreach (var k in InstallConfig.RootNames) roots[k] = k == "site" && site is not null ? site : Path.Combine(baseDir, k.Replace('_', '-'));
        var o = new JsonObject
        {
            ["format"] = InstallConfig.Format, ["mode"] = "test", ["roots"] = roots, ["headroom_fraction"] = headroom, ["min_free_bytes"] = minFree,
            ["retention"] = new JsonObject { ["keep_previous"] = keep },
            ["database"] = new JsonObject { ["name"] = db, ["role_prefix"] = prefix ?? "c16s3c_", ["disposable_prefix"] = "c16s3c_", ["pg_bin"] = Environment.GetEnvironmentVariable("MIMAMSA_PG_BIN") },
            ["backup"] = new JsonObject
            {
                ["db_schemas"] = new JsonArray((backupSchemas ?? ["site"]).Select(x => (JsonNode)x).ToArray()),
                ["exclude_tables"] = new JsonArray((exclude ?? []).Select(x => (JsonNode)x).ToArray()),
            },
        };
        return InstallConfig.Parse(Encoding.UTF8.GetBytes(o.ToJsonString()));
    }

    /// A directory junction (Windows, no privilege needed) or a symbolic link (Linux). Returns false if unsupported.
    public static bool Link(string linkPath, string target)
    {
        if (OperatingSystem.IsWindows())
        {
            var psi = new ProcessStartInfo("cmd.exe") { UseShellExecute = false, RedirectStandardOutput = true, RedirectStandardError = true };
            foreach (var a in new[] { "/c", "mklink", "/J", linkPath, target }) psi.ArgumentList.Add(a);
            using var p = Process.Start(psi)!;
            p.WaitForExit();
            return p.ExitCode == 0 && Directory.Exists(linkPath);
        }
        Directory.CreateSymbolicLink(linkPath, target);
        return true;
    }

    /// A file symbolic link; false where the OS refuses (Windows without developer mode or administrator).
    public static bool FileLink(string linkPath, string target)
    {
        try { File.CreateSymbolicLink(linkPath, target); return true; }
        catch (Exception e) when (e is IOException or UnauthorizedAccessException) { return false; }
    }
}

public sealed record PartEntry(string Name, byte[] Data, TarEntryType Type = TarEntryType.RegularFile, string? LinkName = null);

public static class BackupRepack
{
    public static List<PartEntry> Read(string partFile, byte[] key, string part)
    {
        var o = new List<PartEntry>();
        using var fs = File.OpenRead(partFile);
        using var dec = new BackupCrypto.DecryptStream(fs, key, part);
        using var tr = new TarReader(dec);
        TarEntry? e;
        while ((e = tr.GetNextEntry(copyData: true)) is not null)
        {
            using var ms = new MemoryStream();
            e.DataStream?.CopyTo(ms);
            o.Add(new(e.Name, ms.ToArray(), e.EntryType, e.LinkName));
        }
        return o;
    }

    /// Rewrite `part` of the backup in `dir` with `edit` applied to its entries (MANIFEST.json rebuilt to match unless
    /// keepManifest), and SHA256SUMS updated.
    public static void Rewrite(string dir, string part, byte[] key, Func<List<PartEntry>, List<PartEntry>> edit, bool keepManifest = false, string? backupId = null)
    {
        var file = Path.Combine(dir, SiteBackup.PartFile(part));
        var entries = Read(file, key, part);
        var manifest = JsonNode.Parse(entries.Single(x => x.Name == SiteBackup.ManifestEntry).Data)!.AsObject();
        var body = edit(entries.Where(x => x.Name != SiteBackup.ManifestEntry).ToList());
        if (!keepManifest)
        {
            var arr = new JsonArray();
            foreach (var x in body.Where(x => x.Type == TarEntryType.RegularFile))
                arr.Add(new JsonObject { ["path"] = x.Name, ["sha256"] = Convert.ToHexString(SHA256.HashData(x.Data)).ToLowerInvariant(), ["bytes"] = (long)x.Data.Length });
            manifest["entries"] = arr;
        }
        Write(file, key, backupId ?? (string)manifest["backup_id"]!, part, body.Append(new PartEntry(SiteBackup.ManifestEntry, Encoding.UTF8.GetBytes(manifest.ToJsonString()))));
        UpdateSums(dir);
    }

    public static void Write(string file, byte[] key, string backupId, string part, IEnumerable<PartEntry> entries, int frame = 4096)
    {
        File.Delete(file);
        using var fs = File.Create(file);
        using (var enc = new BackupCrypto.EncryptStream(fs, key, backupId, part, frame))
        using (var tw = new TarWriter(enc, TarEntryFormat.Pax, leaveOpen: true))
            foreach (var x in entries)
            {
                var te = new PaxTarEntry(x.Type, x.Name);
                if (x.Type == TarEntryType.RegularFile) te.DataStream = new MemoryStream(x.Data);
                if (!string.IsNullOrEmpty(x.LinkName) && x.Type is TarEntryType.SymbolicLink or TarEntryType.HardLink) te.LinkName = x.LinkName;
                tw.WriteEntry(te);
            }
    }

    public static void UpdateSums(string dir)
    {
        var sb = new StringBuilder();
        foreach (var p in new[] { SiteBackup.SitePart, SiteBackup.AppendOnlyPart })
        {
            var f = Path.Combine(dir, SiteBackup.PartFile(p));
            if (File.Exists(f)) sb.Append(Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(f))).ToLowerInvariant()).Append("  ").Append(SiteBackup.PartFile(p)).Append('\n');
        }
        File.WriteAllText(Path.Combine(dir, SiteBackup.SumsFile), sb.ToString());
    }
}

/// Disposable c16s3c_ databases and roles (cluster objects): created and dropped by the tests, never anything else.
public static class S3cPg
{
    public static bool Available => Environment.GetEnvironmentVariable("MIMAMSA_TEST_DB") is { Length: > 0 };
    static string AppDsn => Environment.GetEnvironmentVariable("MIMAMSA_TEST_DB")!;
    static string AdminBase => Environment.GetEnvironmentVariable("MIMAMSA_TEST_PG_ADMIN") is { Length: > 0 } a ? a : AppDsn;
    public static string OwnerRole => new NpgsqlConnectionStringBuilder(AppDsn).Username!;
    public static string OwnerDsn(string db) => new NpgsqlConnectionStringBuilder(AppDsn) { Database = db, MaxPoolSize = 4 }.ConnectionString;
    public static string AdminDsn(string db) => new NpgsqlConnectionStringBuilder(AdminBase) { Database = db, MaxPoolSize = 2 }.ConnectionString;
    public static string RoleDsn(string db, string role, string pw) => new NpgsqlConnectionStringBuilder(AppDsn) { Database = db, Username = role, Password = pw, MaxPoolSize = 2 }.ConnectionString;
    public static string Rand() => Convert.ToHexString(RandomNumberGenerator.GetBytes(4)).ToLowerInvariant();

    public static void Guard(string name)
    {
        if (!name.StartsWith("c16s3c_", StringComparison.Ordinal) || name.Any(ch => !(char.IsAsciiLetterLower(ch) || char.IsAsciiDigit(ch) || ch == '_')))
            throw new InvalidOperationException("only disposable c16s3c_ objects may be created or dropped by these tests");
    }

    public static async Task ExecAsync(string dsn, string sql)
    {
        await using var c = new NpgsqlConnection(dsn);
        await c.OpenAsync();
        await using var cmd = new NpgsqlCommand(sql, c);
        await cmd.ExecuteNonQueryAsync();
    }

    public static async Task CreateDbAsync(string name)
    {
        Guard(name);
        NpgsqlConnection.ClearAllPools();
        await ExecAsync(AdminDsn("postgres"), $"CREATE DATABASE \"{name}\" OWNER \"{OwnerRole}\"");
    }

    public static async Task DropDbAsync(string name) { Guard(name); NpgsqlConnection.ClearAllPools(); await ExecAsync(AdminDsn("postgres"), $"DROP DATABASE IF EXISTS \"{name}\" WITH (FORCE)"); }

    public static async Task DropRoleAsync(string role)
    {
        Guard(role);
        NpgsqlConnection.ClearAllPools();
        // privileges granted in databases that are already dropped leave nothing behind; in the cluster: drop owned
        await ExecAsync(AdminDsn("postgres"), $"DROP ROLE IF EXISTS \"{role}\"");
    }
}
