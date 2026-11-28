// C16 Tranche B Stage 3 S3-C (B08, WD-10; architecture section 10): encrypted offline backup of LOCAL SITE DATA.
// TEST DATA ONLY in Tranche B; production media custody, keys and policy are owner gate OG-3.
//
// One backup = a directory <backup_id>/ with two separately encrypted parts and a checksum file:
//   site.mbk        the site database schemas (pg_dump custom format of the configured schemas, accelerator tables
//                   excluded), the vault (write-once objects), local uploads, config (secrets excluded), SITE_CONFIG.json
//                   and the trust directory; plus the APPEND-ONLY HEADS observed BEFORE the database was dumped
//   appendonly.mbk  the append-only stores, copied SEPARATELY and under the journal guard: the activation journal,
//                   the activation log, the ExclusionStore (with EXCLUSION_LATCH), SITE_INIT.json and the reader's
//                   EXCLUSION_HIGHWATER.json
//   SHA256SUMS      sha256 of both encrypted files (verified again after every copy)
// Knowledge (kr_ schemas, knowledge views, generations, accelerators) is never backed up: it is re-imported from release
// media (architecture section 7 decision; restore step 4). Each part is a POSIX tar (System.Formats.Tar, PAX) whose last
// entry MANIFEST.json lists every other entry with its sha256, inside the BackupCrypto STREAM encryption.
// Refused before anything is written: a reparse point (symlink/junction), an unsafe name or a case collision in any
// source tree (PathSafety), a missing database tool, or a pg_dump failure.
using System.Diagnostics;
using System.Formats.Tar;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json.Nodes;
using Mimamsa.Core.Activation;

namespace Mimamsa.Core.Install;

public sealed class BackupException(string code, string message) : Exception(code + ": " + message)
{
    public string Code { get; } = code;
}

/// pg_dump / pg_restore runner. The password goes to the child process through PGPASSWORD only (never argv or logs).
public sealed class PgTools(string bin)
{
    public string Bin { get; } = bin;
    public static PgTools? From(InstallConfig? cfg) =>
        (cfg?.PgBin ?? Environment.GetEnvironmentVariable("MIMAMSA_PG_BIN")) is { Length: > 0 } b ? new PgTools(b) : null;

    string Exe(string name)
    {
        var p = Path.Combine(Bin, OperatingSystem.IsWindows() ? name + ".exe" : name);
        return File.Exists(p) ? p : throw new BackupException("PG_TOOL_MISSING", $"{name} not found in the configured pg_bin");
    }

    /// The client tools must be the server's MAJOR version: pg_restore emits version-specific settings (for example
    /// transaction_timeout from 17), so a mismatched pair is refused up front instead of failing half way.
    public void RequireSameMajor(string dsn)
    {
        var psi = new ProcessStartInfo(Exe("pg_restore")) { RedirectStandardOutput = true, UseShellExecute = false };
        psi.ArgumentList.Add("--version");
        using var p = Process.Start(psi)!;
        var v = p.StandardOutput.ReadToEnd(); p.WaitForExit();
        var m = System.Text.RegularExpressions.Regex.Match(v, @"\)\s+(\d+)");
        using var c = new Npgsql.NpgsqlConnection(dsn);
        c.Open();
        using var q = new Npgsql.NpgsqlCommand("SHOW server_version_num", c);
        int server = int.Parse((string)q.ExecuteScalar()!) / 10000;
        if (!m.Success || int.Parse(m.Groups[1].Value) != server)
            throw new BackupException("PG_TOOL_VERSION_MISMATCH", $"client tools {(m.Success ? m.Groups[1].Value : "?")} differ from server major {server}");
    }

    public (int code, string stderr) Run(string tool, string dsn, IEnumerable<string> args, TimeSpan? timeout = null)
    {
        var b = new Npgsql.NpgsqlConnectionStringBuilder(dsn);
        var psi = new ProcessStartInfo(Exe(tool)) { RedirectStandardError = true, RedirectStandardOutput = true, UseShellExecute = false };
        foreach (var a in new[] { "--host", b.Host!, "--port", b.Port.ToString(), "--username", b.Username!, "--no-password" }) psi.ArgumentList.Add(a);
        foreach (var a in args) psi.ArgumentList.Add(a);
        psi.Environment["PGPASSWORD"] = b.Password ?? "";
        psi.Environment["PGCONNECT_TIMEOUT"] = "15";
        using var p = Process.Start(psi)!;
        var err = p.StandardError.ReadToEndAsync();
        var outp = p.StandardOutput.ReadToEndAsync();
        if (!p.WaitForExit(timeout ?? TimeSpan.FromMinutes(30))) { try { p.Kill(true); } catch { } throw new BackupException("PG_TOOL_TIMEOUT", tool); }
        var e = err.Result + outp.Result;
        if (b.Password is { Length: > 0 } pw) e = e.Replace(pw, "***");
        return (p.ExitCode, e.Length > 4000 ? e[..4000] : e);
    }
}

public sealed record AppendOnlyHeads(long JournalBytes, string JournalPrefixSha256, long LogBytes, string LogPrefixSha256, long ExclusionSequence, string? ExclusionDigest)
{
    public JsonObject ToJson() => new()
    {
        ["journal_bytes"] = JournalBytes, ["journal_prefix_sha256"] = JournalPrefixSha256, ["log_bytes"] = LogBytes,
        ["log_prefix_sha256"] = LogPrefixSha256, ["exclusion_sequence"] = ExclusionSequence, ["exclusion_digest"] = ExclusionDigest,
    };
    public static AppendOnlyHeads FromJson(JsonNode n) => new((long)n["journal_bytes"]!, (string)n["journal_prefix_sha256"]!, (long)n["log_bytes"]!,
        (string)n["log_prefix_sha256"]!, (long)n["exclusion_sequence"]!, (string?)n["exclusion_digest"]);

    /// Complete-line prefix of an append-only line file (a torn last line is not part of the store).
    public static byte[] CompleteLines(string path)
    {
        var b = DurableFile.ReadIfExists(path) ?? [];
        int last = Array.LastIndexOf(b, (byte)'\n');
        return last < 0 ? [] : b[..(last + 1)];
    }

    public static string Sha(ReadOnlySpan<byte> b) => Convert.ToHexString(SHA256.HashData(b)).ToLowerInvariant();

    /// Heads of the append-only stores laid out as on a site (journal/, activation-log/, exclusions/).
    public static AppendOnlyHeads Read(string root)
    {
        var j = CompleteLines(Path.Combine(root, "journal", "journal.jsonl"));
        var l = CompleteLines(Path.Combine(root, "activation-log", "activation-log.jsonl"));
        long seq = 0; string? dig = null;
        var acc = Path.Combine(root, "exclusions", "ACCEPTED.json");
        if (File.Exists(acc))
        {
            var o = JsonNode.Parse(File.ReadAllBytes(acc))!;
            seq = (long)o["sequence"]!; dig = (string?)o["digest"];
        }
        return new(j.Length, Sha(j), l.Length, Sha(l), seq, dig);
    }
}

public static class SiteBackup
{
    public const string SitePart = "site", AppendOnlyPart = "appendonly", SumsFile = "SHA256SUMS", ManifestEntry = "MANIFEST.json";
    public static string PartFile(string part) => part + ".mbk";

    /// Files of the append-only set, relative to the site root (directories are taken whole).
    public static readonly string[] AppendOnlyFiles = ["journal/journal.jsonl", "activation-log/activation-log.jsonl", "EXCLUSION_LATCH",
                                                       "activation-state/SITE_INIT.json", "activation-state/EXCLUSION_HIGHWATER.json"];
    public const string ExclusionsDir = "exclusions";

    public sealed class Options
    {
        public required InstallConfig Config { get; init; }
        public required byte[] Key { get; init; }
        /// Npgsql DSN used by pg_dump (the backup role, or the owner in development); null = no database part (unit tests).
        public string? DbDsn { get; init; }
        public string? DbName { get; init; }
        public PgTools? Pg { get; init; }
        /// Offline media directory: the backup is copied there and verified after the copy. Null = backup root only.
        public string? Destination { get; init; }
        public int FrameBytes { get; init; } = BackupCrypto.DefaultFrameBytes;
        public string? BackupId { get; init; }
        public Action<string>? Log { get; init; }
    }

    static string NewId() => $"BK-{DateTimeOffset.UtcNow:yyyyMMddTHHmmssZ}-{Convert.ToHexString(RandomNumberGenerator.GetBytes(4)).ToLowerInvariant()}";

    sealed record Src(string Entry, string File);

    static List<Src> Tree(string root, string prefix, Func<string, bool>? skip = null)
    {
        if (!Directory.Exists(root)) return [];
        var issues = PathSafety.TreeIssues(root, out var files);
        if (issues.Count > 0) throw new BackupException(issues[0].Code, "backup source " + root + ": " + string.Join("; ", issues.Take(5)));
        return files.Where(f => skip is null || !skip(f)).Select(f => new Src(prefix + f, Path.Combine(root, f.Replace('/', Path.DirectorySeparatorChar)))).ToList();
    }

    static string Sha(string file) { using var f = File.OpenRead(file); return Convert.ToHexString(SHA256.HashData(f)).ToLowerInvariant(); }

    /// Write one encrypted tar part; MANIFEST.json is the last entry.
    static JsonObject WritePart(string outFile, Options o, string backupId, string part, IReadOnlyList<Src> srcs, JsonObject manifestExtra)
    {
        var names = srcs.Select(s => s.Entry).ToList();
        var bad = names.SelectMany(PathSafety.RelativeIssues).Concat(PathSafety.CaseCollisions(names)).ToList();
        if (bad.Count > 0) throw new BackupException(bad[0].Code, string.Join("; ", bad.Take(5)));
        var entries = new JsonArray();
        long total = 0;
        var tmp = outFile + ".partial";
        using (var fs = new FileStream(tmp, FileMode.CreateNew, FileAccess.Write, FileShare.None))
        {
            using (var enc = new BackupCrypto.EncryptStream(fs, o.Key, backupId, part, o.FrameBytes))
            using (var tw = new TarWriter(enc, TarEntryFormat.Pax, leaveOpen: true))
            {
                foreach (var s in srcs.OrderBy(x => x.Entry, StringComparer.Ordinal))
                {
                    var sha = Sha(s.File);
                    using var data = File.OpenRead(s.File);
                    var e = new PaxTarEntry(TarEntryType.RegularFile, s.Entry) { DataStream = data, ModificationTime = DateTimeOffset.UnixEpoch, Mode = UnixFileMode.UserRead | UnixFileMode.UserWrite | UnixFileMode.GroupRead };
                    tw.WriteEntry(e);
                    if (Sha(s.File) != sha) throw new BackupException("BACKUP_SOURCE_CHANGED", s.Entry + " changed while it was being backed up");
                    entries.Add(new JsonObject { ["path"] = s.Entry, ["sha256"] = sha, ["bytes"] = data.Length });
                    total += data.Length;
                }
                var manifest = new JsonObject
                {
                    ["format"] = "mimamsa-backup-manifest/1", ["backup_id"] = backupId, ["part"] = part, ["created_at"] = DateTimeOffset.UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ"),
                    ["mode"] = o.Config.Mode, ["entries"] = entries, ["total_bytes"] = total,
                };
                foreach (var (k, v) in manifestExtra) manifest[k] = v?.DeepClone();
                var mb = Encoding.UTF8.GetBytes(manifest.ToJsonString());
                tw.WriteEntry(new PaxTarEntry(TarEntryType.RegularFile, ManifestEntry) { DataStream = new MemoryStream(mb), ModificationTime = DateTimeOffset.UnixEpoch });
            }
            fs.Flush(true);
        }
        File.Move(tmp, outFile);
        return new JsonObject { ["part"] = part, ["entries"] = entries.Count, ["plaintext_bytes"] = total };
    }

    public static JsonObject Create(Options o)
    {
        var cfg = o.Config;
        var site = cfg.Site;
        var sw = Stopwatch.StartNew();
        var id = o.BackupId ?? NewId();
        SiteLayout.CheckId(id);
        var dir = Path.Combine(cfg.Root("backup"), id);
        if (Directory.Exists(dir)) throw new BackupException("BACKUP_EXISTS", id);
        var scratch = Path.Combine(cfg.Root("scratch"), "backup-" + id);
        Directory.CreateDirectory(scratch);
        try
        {
            // 1. heads of the append-only stores BEFORE the database is dumped: the restore refuses any append-only set
            //    older than these (stale rollback impossible)
            var heads0 = WriterLease.UnderGuard(site, () => AppendOnlyHeads.Read(site.Root), TimeSpan.FromMinutes(2));

            // 2. database: pg_dump of the configured site schemas only (never kr_, knowledge or site_activation)
            JsonObject? dbInfo = null;
            var srcs = new List<Src>();
            if (o.DbDsn is not null)
            {
                var pg = o.Pg ?? throw new BackupException("PG_TOOL_MISSING", "pg_bin is not configured");
                pg.RequireSameMajor(o.DbDsn);
                var dump = Path.Combine(scratch, "site.pgdump");
                var args = new List<string> { "--format=custom", "--no-owner", "--no-privileges", "--file", dump, "--dbname", o.DbName ?? new Npgsql.NpgsqlConnectionStringBuilder(o.DbDsn).Database! };
                foreach (var s in cfg.BackupSchemas) { args.Add("--schema"); args.Add(s); }
                foreach (var t in cfg.BackupExcludeTables) { args.Add("--exclude-table"); args.Add(t); }
                var (code, err) = pg.Run("pg_dump", o.DbDsn, args);
                if (code != 0) throw new BackupException("PG_DUMP_FAILED", err);
                srcs.Add(new Src("db/site.pgdump", dump));
                dbInfo = new JsonObject
                {
                    ["schemas"] = new JsonArray(cfg.BackupSchemas.Select(x => (JsonNode)x).ToArray()),
                    ["exclude_tables"] = new JsonArray(cfg.BackupExcludeTables.Select(x => (JsonNode)x).ToArray()),
                    ["format"] = "pg_dump custom", ["tool"] = "pg_dump",
                };
            }

            // 3. files of the site part
            srcs.AddRange(Tree(Path.Combine(site.Root, "vault"), "files/vault/"));
            srcs.AddRange(Tree(cfg.Root("uploads"), "files/uploads/"));
            srcs.AddRange(Tree(cfg.Root("config"), "files/config/", f => f.StartsWith("secrets/", StringComparison.OrdinalIgnoreCase)));
            srcs.AddRange(Tree(Path.Combine(site.Root, "trust"), "files/site/trust/"));
            if (File.Exists(Path.Combine(site.Root, "SITE_CONFIG.json"))) srcs.Add(new Src("files/site/SITE_CONFIG.json", Path.Combine(site.Root, "SITE_CONFIG.json")));

            Directory.CreateDirectory(dir);
            var sitePart = WritePart(Path.Combine(dir, PartFile(SitePart)), o, id, SitePart, srcs,
                new JsonObject { ["db"] = dbInfo, ["appendonly_heads_at_db_time"] = heads0.ToJson(), ["knowledge_backed_up"] = false });

            // 4. the append-only stores, copied SEPARATELY under the journal guard (a consistent snapshot between appends)
            var ao = Path.Combine(scratch, "appendonly");
            var aoHeads = WriterLease.UnderGuard(site, () =>
            {
                foreach (var f in AppendOnlyFiles)
                {
                    var src = Path.Combine(site.Root, f.Replace('/', Path.DirectorySeparatorChar));
                    if (!File.Exists(src)) continue;
                    var dst = Path.Combine(ao, f.Replace('/', Path.DirectorySeparatorChar));
                    Directory.CreateDirectory(Path.GetDirectoryName(dst)!);
                    File.Copy(src, dst);
                }
                var ex = Path.Combine(site.Root, ExclusionsDir);
                if (Directory.Exists(ex))
                {
                    foreach (var r in Tree(ex, ""))
                    {
                        var dst = Path.Combine(ao, ExclusionsDir, r.Entry.Replace('/', Path.DirectorySeparatorChar));
                        Directory.CreateDirectory(Path.GetDirectoryName(dst)!);
                        File.Copy(r.File, dst);
                    }
                }
                return AppendOnlyHeads.Read(ao);
            }, TimeSpan.FromMinutes(2));
            var aoPart = WritePart(Path.Combine(dir, PartFile(AppendOnlyPart)), o, id, AppendOnlyPart, Tree(ao, "appendonly/"),
                new JsonObject { ["heads"] = aoHeads.ToJson() });

            // 5. checksums, then verification of what is on disk (re-hash and a full authenticated read)
            var sums = new StringBuilder();
            foreach (var p in new[] { SitePart, AppendOnlyPart }) sums.Append(Sha(Path.Combine(dir, PartFile(p)))).Append("  ").Append(PartFile(p)).Append('\n');
            DurableFile.WriteAtomic(Path.Combine(dir, SumsFile), Encoding.ASCII.GetBytes(sums.ToString()));
            var verified = Verify(dir, o.Key);
            JsonObject? copied = null;
            if (o.Destination is not null)
            {
                var dest = Path.Combine(o.Destination, id);
                var di = PathSafety.RootIssues(o.Destination);
                if (di.Count > 0) throw new BackupException(di[0].Code, "destination: " + string.Join("; ", di));
                Directory.CreateDirectory(dest);
                foreach (var f in new[] { PartFile(SitePart), PartFile(AppendOnlyPart), SumsFile }) File.Copy(Path.Combine(dir, f), Path.Combine(dest, f));
                copied = Verify(dest, o.Key);
                copied["path"] = dest;
            }
            sw.Stop();
            return new JsonObject
            {
                ["ok"] = true, ["backup_id"] = id, ["path"] = dir, ["site"] = sitePart, ["appendonly"] = aoPart,
                ["appendonly_heads_at_db_time"] = heads0.ToJson(), ["appendonly_heads"] = aoHeads.ToJson(),
                ["verified"] = verified, ["copied_to_media"] = copied, ["elapsed_ms"] = sw.ElapsedMilliseconds,
                ["encryption"] = "AES-256-GCM STREAM frames, HKDF-SHA256 per-file key (System.Security.Cryptography)", ["test_key_only"] = true,
            };
        }
        finally
        {
            try { Directory.Delete(scratch, recursive: true); } catch (Exception e) when (e is IOException or UnauthorizedAccessException) { o.Log?.Invoke("backup scratch not removed: " + e.Message); }
        }
    }

    /// Integrity of a backup directory: SHA256SUMS matches both parts; both authenticate end to end under the key.
    public static JsonObject Verify(string dir, byte[] key)
    {
        var o = new JsonObject();
        foreach (var p in new[] { SitePart, AppendOnlyPart }) o[p] = VerifyPart(dir, key, p);
        o["sha256sums"] = "match";
        return o;
    }

    public static bool HasPart(string dir, string part) => File.Exists(Path.Combine(dir, PartFile(part)));

    /// One part: listed in SHA256SUMS, present, matching, and authenticated end to end. Returns the plaintext bytes.
    public static long VerifyPart(string dir, byte[] key, string part)
    {
        var sumsPath = Path.Combine(dir, SumsFile);
        if (!File.Exists(sumsPath)) throw new BackupException("BACKUP_PARTIAL", "SHA256SUMS missing in " + dir);
        var want = File.ReadAllLines(sumsPath).Where(l => l.Length > 0).Select(l => l.Split("  ", 2)).Where(x => x.Length == 2)
                       .ToDictionary(x => x[1], x => x[0], StringComparer.Ordinal);
        var f = Path.Combine(dir, PartFile(part));
        if (!File.Exists(f) || !want.ContainsKey(PartFile(part))) throw new BackupException("BACKUP_PARTIAL", PartFile(part) + " missing in " + dir);
        if (Sha(f) != want[PartFile(part)]) throw new BackupException("BACKUP_CHECKSUM_MISMATCH", PartFile(part));
        using var fs = File.OpenRead(f);
        using var dec = new BackupCrypto.DecryptStream(fs, key, part);
        return dec.Drain();
    }
}
