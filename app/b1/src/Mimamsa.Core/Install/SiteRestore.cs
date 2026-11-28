// C16 Tranche B Stage 3 S3-C (B08; architecture section 10 restore steps 1-6; reference activation.Site.restore):
// restore of LOCAL SITE DATA onto a clean installation. TEST DATA ONLY (OG-3).
//   1. clean install (InstallLayout + SiteDatabaseSetup on a fresh database); refused otherwise (TARGET_NOT_CLEAN)
//   2. both parts are authenticated and fully extracted into scratch, every entry checked (regular files only, safe
//      relative names, no case collisions, MANIFEST.json last and exact) BEFORE anything on the target is touched
//   3. the append-only stores (journal, activation log, ExclusionStore): each store is taken from the NEWEST valid
//      candidate among the backup's append-only part, any newer offline copies supplied, and whatever the target already
//      holds; a target store is never overwritten by an older one. Refused if no candidate is at least as new as the
//      database dump (APPENDONLY_OLDER_THAN_DATABASE), if a store is missing (APPENDONLY_MISSING), corrupt beyond a torn
//      tail, or if candidates diverge (APPENDONLY_DIVERGED). Latest exclusions win.
//   2'. the site database schemas are restored with pg_restore in ONE transaction from the site's own dump (never a
//      knowledge archive: knowledge is re-imported from media), then the vault (sha256-verified, write-once), uploads
//      and config (an existing different target file is kept; the backup copy is set aside under restored-<id>/)
//   4/5. pointers are set from the JOURNAL HEAD (not from the backup), the site is left RECOVERING; the caller
//      re-imports the head release from media if it is not retained, stages it (`stage`), then runs `recover`, which
//      reconciles views and publication rows and re-applies the latest exclusion state; only then does it serve (6).
using System.Diagnostics;
using System.Formats.Tar;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json.Nodes;
using Mimamsa.Core.Activation;
using Npgsql;

namespace Mimamsa.Core.Install;

public static class SiteRestore
{
    public sealed class Options
    {
        public required InstallConfig Config { get; init; }
        public required byte[] Key { get; init; }
        public required string BackupDir { get; init; }
        /// Further append-only candidates (directories of other backups, e.g. a newer offline copy): only their
        /// appendonly.mbk is used.
        public IReadOnlyList<string> AppendOnlyFrom { get; init; } = [];
        public string? DbOwnerDsn { get; init; }
        public PgTools? Pg { get; init; }
        public Action<string>? Log { get; init; }
        public long MaxEntries { get; init; } = 2_000_000;
    }

    sealed record Extracted(string Dir, JsonObject Manifest, List<string> Files);

    static string Sha(string file) { using var f = File.OpenRead(file); return Convert.ToHexString(SHA256.HashData(f)).ToLowerInvariant(); }

    /// Authenticate and extract one part into `into` (which must not exist). Throws on any problem; nothing outside
    /// `into` is written.
    static Extracted Extract(string partFile, string part, byte[] key, string into, long maxEntries)
    {
        if (!File.Exists(partFile)) throw new BackupException("BACKUP_PARTIAL", Path.GetFileName(partFile) + " missing");
        Directory.CreateDirectory(into);
        var seen = new List<string>();
        var hashes = new Dictionary<string, (string sha, long bytes)>(StringComparer.Ordinal);
        JsonObject? manifest = null;
        using (var fs = File.OpenRead(partFile))
        using (var dec = new BackupCrypto.DecryptStream(fs, key, part))
        {
            TarReader tr;
            try { tr = new TarReader(dec, leaveOpen: true); } catch (Exception e) when (e is InvalidDataException or FormatException) { throw new BackupException("BACKUP_TAMPERED", e.Message); }
            using (tr)
            {
                while (true)
                {
                    TarEntry? e;
                    try { e = tr.GetNextEntry(copyData: false); }
                    catch (Exception x) when (x is InvalidDataException or FormatException or EndOfStreamException) { throw new BackupException("BACKUP_TAMPERED", "tar: " + x.Message); }
                    if (e is null) break;
                    if (manifest is not null) throw new BackupException("BACKUP_MANIFEST_MISMATCH", "an entry follows MANIFEST.json");
                    if (e.EntryType is not (TarEntryType.RegularFile or TarEntryType.V7RegularFile))
                        throw new BackupException("BACKUP_ENTRY_TYPE", $"{e.Name}: entry type {e.EntryType} (only regular files are restored)");
                    if (seen.Count + 1 > maxEntries) throw new BackupException("BACKUP_TOO_MANY_ENTRIES", partFile);
                    var issues = PathSafety.RelativeIssues(e.Name);
                    if (issues.Count > 0) throw new BackupException(issues[0].Code, "entry " + string.Join("; ", issues));
                    seen.Add(e.Name);
                    var col = PathSafety.CaseCollisions(seen);
                    if (col.Count > 0) throw new BackupException(col[0].Code, "entry " + col[0]);
                    if (e.Name == SiteBackup.ManifestEntry)
                    {
                        using var ms = new MemoryStream();
                        e.DataStream?.CopyTo(ms);
                        try { manifest = JsonNode.Parse(ms.ToArray())!.AsObject(); } catch (Exception x) { throw new BackupException("BACKUP_MANIFEST_MISMATCH", x.Message); }
                        continue;
                    }
                    var dst = Path.Combine(into, e.Name.Replace('/', Path.DirectorySeparatorChar));
                    if (!Path.GetFullPath(dst).StartsWith(Path.GetFullPath(into) + Path.DirectorySeparatorChar, StringComparison.Ordinal))
                        throw new BackupException("PATH_TRAVERSAL", e.Name);
                    Directory.CreateDirectory(Path.GetDirectoryName(dst)!);
                    using (var outf = new FileStream(dst, FileMode.CreateNew, FileAccess.Write))
                    using (var h = IncrementalHash.CreateHash(HashAlgorithmName.SHA256))
                    {
                        var buf = new byte[81920];
                        long n = 0; int r;
                        var src = e.DataStream ?? Stream.Null;
                        while ((r = src.Read(buf)) > 0) { outf.Write(buf, 0, r); h.AppendData(buf, 0, r); n += r; }
                        hashes[e.Name] = (Convert.ToHexString(h.GetHashAndReset()).ToLowerInvariant(), n);
                    }
                }
            }
            dec.Drain();   // the final frame must authenticate and nothing may follow it
        }
        if (manifest is null) throw new BackupException("BACKUP_MANIFEST_MISMATCH", "MANIFEST.json missing (truncated or partial backup)");
        if ((string?)manifest["part"] != part) throw new BackupException("BACKUP_MANIFEST_MISMATCH", "manifest names another part");
        var listed = manifest["entries"]!.AsArray().Select(x => x!.AsObject()).ToList();
        if (listed.Count != hashes.Count || listed.Any(x => !hashes.TryGetValue((string)x["path"]!, out var hv) || hv.sha != (string?)x["sha256"] || hv.bytes != (long)x["bytes"]!))
            throw new BackupException("BACKUP_MANIFEST_MISMATCH", "entries differ from the manifest");
        return new(into, manifest, hashes.Keys.Order(StringComparer.Ordinal).ToList());
    }

    // ------------------------------------------------------------------ append-only selection
    public sealed record Candidate(string Label, string Root, bool IsTarget);

    sealed record StoreView(Candidate C, byte[] Lines, string? Problem);

    static StoreView View(Candidate c, string rel, bool journal)
    {
        var p = Path.Combine(c.Root, rel.Replace('/', Path.DirectorySeparatorChar));
        if (!File.Exists(p)) return new(c, [], "missing");
        try
        {
            if (journal) ActivationJournal.Read(p);
            else new ActivationLog(p).Read();
        }
        catch (JournalCorruptException e) { return new(c, [], "corrupt: " + e.Message); }
        return new(c, AppendOnlyHeads.CompleteLines(p), null);
    }

    static bool IsPrefix(byte[] shorter, byte[] longer) => shorter.Length <= longer.Length && longer.AsSpan(0, shorter.Length).SequenceEqual(shorter);

    /// Pick the newest valid line store (journal or activation log) that is at least the database-time head.
    static (StoreView pick, JsonArray notes) PickLines(List<Candidate> cands, string rel, bool journal, long minBytes, string minPrefixSha, string what)
    {
        var notes = new JsonArray();
        var valid = new List<StoreView>();
        foreach (var c in cands)
        {
            var v = View(c, rel, journal);
            if (v.Problem is not null) { notes.Add($"{c.Label}: {what} {v.Problem}"); continue; }
            if (v.Lines.Length < minBytes || AppendOnlyHeads.Sha(v.Lines.AsSpan(0, (int)minBytes)) != minPrefixSha)
            { notes.Add($"{c.Label}: {what} older than the database dump or diverged from it"); continue; }
            valid.Add(v);
        }
        bool anyPresent = cands.Any(c => File.Exists(Path.Combine(c.Root, rel.Replace('/', Path.DirectorySeparatorChar))));
        // a store that never had an entry (no transition yet) is legitimately absent everywhere when the database-time
        // head is empty too; it is then left absent on the target
        if (valid.Count == 0 && !anyPresent && minBytes == 0) return (new StoreView(cands[^1], [], null), notes);
        if (valid.Count == 0)
        {
            throw new BackupException(anyPresent ? "APPENDONLY_OLDER_THAN_DATABASE" : "APPENDONLY_MISSING",
                $"no {what} at least as new as the database backup: {string.Join("; ", notes.Select(n => (string?)n))}");
        }
        var best = valid.OrderByDescending(v => v.Lines.Length).ThenByDescending(v => v.C.IsTarget).First();
        foreach (var v in valid)
            if (!IsPrefix(v.Lines, best.Lines)) throw new BackupException("APPENDONLY_DIVERGED", $"{what} of {v.C.Label} is not a prefix of {best.C.Label}");
        return (best, notes);
    }

    static (Candidate pick, long seq, long highWater, JsonArray notes) PickExclusions(List<Candidate> cands, long minSeq, string? minDigest)
    {
        var notes = new JsonArray();
        var valid = new List<(Candidate c, long seq, JsonArray hist)>();
        long high = 0;
        foreach (var c in cands)
        {
            var hw = Path.Combine(c.Root, "activation-state", "EXCLUSION_HIGHWATER.json");
            if (File.Exists(hw)) try { high = Math.Max(high, (long)JsonNode.Parse(File.ReadAllBytes(hw))!["sequence"]!); } catch (Exception) { notes.Add($"{c.Label}: unreadable EXCLUSION_HIGHWATER"); }
            var acc = Path.Combine(c.Root, "exclusions", "ACCEPTED.json");
            if (!File.Exists(acc)) { notes.Add($"{c.Label}: exclusions missing"); continue; }
            JsonObject o;
            try { o = JsonNode.Parse(File.ReadAllBytes(acc))!.AsObject(); } catch (Exception e) { notes.Add($"{c.Label}: exclusions unreadable: {e.Message}"); continue; }
            long seq = (long)o["sequence"]!;
            var hist = o["history"]?.AsArray() ?? new JsonArray();
            bool covers = seq > minSeq ? (minSeq == 0 || hist.Any(h => (long)h![0]! == minSeq && (minDigest is null || (string?)h[1] == minDigest)))
                                       : seq == minSeq && (minDigest is null || (string?)o["digest"] == minDigest);
            if (!covers) { notes.Add($"{c.Label}: exclusions (sequence {seq}) older than the database dump or diverged from it"); continue; }
            // every pair named by the history must be present (a store copied incompletely is not a store)
            bool complete = hist.All(h => File.Exists(Path.Combine(c.Root, "exclusions", "pairs", ((long)h![0]!).ToString("D8") + ".json")));
            if (!complete) { notes.Add($"{c.Label}: exclusions incomplete (a signed pair named by the history is missing)"); continue; }
            valid.Add((c, seq, hist));
        }
        if (valid.Count == 0)
            throw new BackupException(cands.Any(c => File.Exists(Path.Combine(c.Root, "exclusions", "ACCEPTED.json"))) ? "APPENDONLY_OLDER_THAN_DATABASE" : "APPENDONLY_MISSING",
                "no ExclusionStore at least as new as the database backup: " + string.Join("; ", notes.Select(n => (string?)n)));
        var best = valid.OrderByDescending(v => v.seq).ThenByDescending(v => v.c.IsTarget).First();
        foreach (var v in valid.Where(v => v.seq < best.seq))
        {
            var dig = (string?)JsonNode.Parse(File.ReadAllBytes(Path.Combine(v.c.Root, "exclusions", "ACCEPTED.json")))!["digest"];
            if (!best.hist.Any(h => (long)h![0]! == v.seq && (string?)h[1] == dig)) throw new BackupException("APPENDONLY_DIVERGED", $"exclusions of {v.c.Label} are not in the history of {best.c.Label}");
        }
        if (high > best.seq) throw new BackupException("APPENDONLY_EXCLUSIONS_REGRESSED", $"a reader saw exclusion sequence {high}, newer than any store supplied ({best.seq})");
        return (best.c, best.seq, Math.Max(high, best.seq), notes);
    }

    // ------------------------------------------------------------------ target checks
    static List<string> TargetProblems(InstallConfig cfg, NpgsqlDataSource? db, IEnumerable<string> schemas)
    {
        var o = new List<string>();
        var site = cfg.Site;
        if (new GenerationCatalog(site).Installed().Count > 0) o.Add("the target site has installed generations");
        var vault = Path.Combine(site.Root, "vault");
        if (Directory.Exists(vault) && Directory.EnumerateFiles(vault, "*", SearchOption.AllDirectories).Any()) o.Add("the target vault is not empty");
        if (Directory.Exists(cfg.Root("uploads")) && Directory.EnumerateFileSystemEntries(cfg.Root("uploads")).Any()) o.Add("the target uploads root is not empty");
        if (db is not null)
        {
            using var c = db.OpenConnection();
            using var q = new NpgsqlCommand("SELECT count(*) FROM pg_class k JOIN pg_namespace n ON n.oid = k.relnamespace WHERE n.nspname = ANY($1) AND k.relkind IN ('r','p','v','m','S')", c);
            q.Parameters.AddWithValue(schemas.ToArray());
            if ((long)q.ExecuteScalar()! > 0) o.Add("the target database already holds objects in the backed-up schemas");
        }
        return o;
    }

    static void CopyFileWriteOnce(string src, string dst, string? expectSha, JsonArray conflicts, string conflictDir, string rel)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(dst)!);
        if (File.Exists(dst))
        {
            if (Sha(dst) == Sha(src)) return;
            if (expectSha is not null) throw new BackupException("VAULT_OBJECT_CONFLICT", rel);
            var aside = Path.Combine(conflictDir, rel.Replace('/', Path.DirectorySeparatorChar));
            Directory.CreateDirectory(Path.GetDirectoryName(aside)!);
            File.Copy(src, aside, overwrite: false);
            conflicts.Add(rel);
            return;
        }
        File.Copy(src, dst + ".restoring", overwrite: true);
        if (expectSha is not null && Sha(dst + ".restoring") != expectSha) { File.Delete(dst + ".restoring"); throw new BackupException("VAULT_OBJECT_CORRUPT", rel); }
        File.Move(dst + ".restoring", dst);
    }

    public static JsonObject Run(Options o)
    {
        var sw = Stopwatch.StartNew();
        var cfg = o.Config;
        var site = cfg.Site;
        var key = o.Key;
        var verify = SiteBackup.Verify(o.BackupDir, key);   // checksums + authentication of both parts
        var work = Path.Combine(cfg.Root("scratch"), "restore-" + Convert.ToHexString(RandomNumberGenerator.GetBytes(5)).ToLowerInvariant());
        NpgsqlDataSource? db = o.DbOwnerDsn is null ? null : NpgsqlDataSource.Create(o.DbOwnerDsn);
        try
        {
            // ---- 2: authenticate and extract everything first
            var sitePart = Extract(Path.Combine(o.BackupDir, SiteBackup.PartFile(SiteBackup.SitePart)), SiteBackup.SitePart, key, Path.Combine(work, "site"), o.MaxEntries);
            var aoPart = Extract(Path.Combine(o.BackupDir, SiteBackup.PartFile(SiteBackup.AppendOnlyPart)), SiteBackup.AppendOnlyPart, key, Path.Combine(work, "ao0"), o.MaxEntries);
            if ((string?)sitePart.Manifest["backup_id"] != (string?)aoPart.Manifest["backup_id"]) throw new BackupException("BACKUP_MANIFEST_MISMATCH", "the two parts belong to different backups");
            var cands = new List<Candidate> { new("backup " + (string?)aoPart.Manifest["backup_id"], Path.Combine(aoPart.Dir, "appendonly"), false) };
            int k = 1;
            foreach (var extra in o.AppendOnlyFrom)
            {
                var x = Extract(Path.Combine(extra, SiteBackup.PartFile(SiteBackup.AppendOnlyPart)), SiteBackup.AppendOnlyPart, key, Path.Combine(work, "ao" + k++), o.MaxEntries);
                cands.Add(new("offline copy " + (string?)x.Manifest["backup_id"], Path.Combine(x.Dir, "appendonly"), false));
            }
            cands.Add(new("target site", site.Root, true));

            // ---- 3: append-only selection against the database-time heads (stale rollback impossible)
            var h0 = AppendOnlyHeads.FromJson(sitePart.Manifest["appendonly_heads_at_db_time"]!);
            var (jPick, jNotes) = PickLines(cands, "journal/journal.jsonl", true, h0.JournalBytes, h0.JournalPrefixSha256, "journal");
            var (lPick, lNotes) = PickLines(cands, "activation-log/activation-log.jsonl", false, h0.LogBytes, h0.LogPrefixSha256, "activation log");
            var (ePick, eSeq, highWater, eNotes) = PickExclusions(cands, h0.ExclusionSequence, h0.ExclusionDigest);
            var initCand = cands.FirstOrDefault(c => File.Exists(Path.Combine(c.Root, "activation-state", "SITE_INIT.json")))
                           ?? throw new BackupException("APPENDONLY_MISSING", "SITE_INIT.json missing");
            var inits = cands.Where(c => File.Exists(Path.Combine(c.Root, "activation-state", "SITE_INIT.json")))
                             .Select(c => Sha(Path.Combine(c.Root, "activation-state", "SITE_INIT.json"))).Distinct().ToList();
            if (inits.Count != 1) throw new BackupException("APPENDONLY_DIVERGED", "SITE_INIT.json differs between candidates");

            // ---- 1: the target must be a clean installation
            var probs = TargetProblems(cfg, db, cfg.BackupSchemas);
            if (probs.Count > 0) throw new BackupException("TARGET_NOT_CLEAN", string.Join("; ", probs));

            // ---- 2': database (one transaction, the site's own dump), then files
            JsonObject? dbOut = null;
            var dump = Path.Combine(sitePart.Dir, "db", "site.pgdump");
            if (sitePart.Manifest["db"] is JsonObject dbm)
            {
                if (o.DbOwnerDsn is null || o.Pg is null) throw new BackupException("PG_TOOL_MISSING", "the backup holds a database part: a database and pg_bin are required");
                var dbName = new NpgsqlConnectionStringBuilder(o.DbOwnerDsn).Database!;
                if (cfg.DisposablePrefix is { } pre && !dbName.StartsWith(pre, StringComparison.Ordinal)) throw new BackupException("DATABASE_NOT_DISPOSABLE", dbName);
                var (code, err) = o.Pg.Run("pg_restore", o.DbOwnerDsn, ["--exit-on-error", "--single-transaction", "--no-owner", "--no-privileges", "--dbname", dbName, dump]);
                if (code != 0) throw new BackupException("PG_RESTORE_FAILED", err);
                dbOut = new JsonObject { ["schemas"] = dbm["schemas"]?.DeepClone(), ["restored"] = true };
            }
            var conflicts = new JsonArray();
            var aside = Path.Combine(cfg.Root("config"), "restored-" + (string?)sitePart.Manifest["backup_id"]);
            int vaultN = 0, upN = 0, cfgN = 0;
            foreach (var f in sitePart.Files)
            {
                var src = Path.Combine(sitePart.Dir, f.Replace('/', Path.DirectorySeparatorChar));
                if (f.StartsWith("files/vault/", StringComparison.Ordinal))
                {
                    var rel = f["files/vault/".Length..];
                    var name = rel.Split('/')[^1];
                    string? expect = name.Length == 64 && name.All(Uri.IsHexDigit) ? name.ToLowerInvariant() : null;
                    CopyFileWriteOnce(src, Path.Combine(site.Root, "vault", rel.Replace('/', Path.DirectorySeparatorChar)), expect, conflicts, aside, "vault/" + rel);
                    vaultN++;
                }
                else if (f.StartsWith("files/uploads/", StringComparison.Ordinal))
                { CopyFileWriteOnce(src, Path.Combine(cfg.Root("uploads"), f["files/uploads/".Length..].Replace('/', Path.DirectorySeparatorChar)), null, conflicts, aside, f["files/".Length..]); upN++; }
                else if (f.StartsWith("files/config/", StringComparison.Ordinal))
                { CopyFileWriteOnce(src, Path.Combine(cfg.Root("config"), f["files/config/".Length..].Replace('/', Path.DirectorySeparatorChar)), null, conflicts, aside, f["files/".Length..]); cfgN++; }
                else if (f.StartsWith("files/site/", StringComparison.Ordinal))
                    CopyFileWriteOnce(src, Path.Combine(site.Root, f["files/site/".Length..].Replace('/', Path.DirectorySeparatorChar)), null, conflicts, aside, f["files/".Length..]);
                else if (f != "db/site.pgdump") throw new BackupException("BACKUP_ENTRY_UNKNOWN", f);
            }

            // ---- 3': install the chosen append-only stores; a target store is replaced only by a strictly newer one
            void PutLines(StoreView pick, string rel)
            {
                if (pick.C.IsTarget || pick.Lines.Length == 0) return;
                var dst = Path.Combine(site.Root, rel.Replace('/', Path.DirectorySeparatorChar));
                Directory.CreateDirectory(Path.GetDirectoryName(dst)!);
                DurableFile.WriteAtomic(dst, pick.Lines);
            }
            PutLines(jPick, "journal/journal.jsonl");
            PutLines(lPick, "activation-log/activation-log.jsonl");
            if (!ePick.IsTarget)
            {
                var exDst = Path.Combine(site.Root, "exclusions");
                foreach (var f in Directory.EnumerateFiles(Path.Combine(ePick.Root, "exclusions"), "*", SearchOption.AllDirectories))
                {
                    var rel = Path.GetRelativePath(Path.Combine(ePick.Root, "exclusions"), f);
                    var dst = Path.Combine(exDst, rel);
                    Directory.CreateDirectory(Path.GetDirectoryName(dst)!);
                    if (File.Exists(dst) && Sha(dst) == Sha(f)) continue;
                    if (rel.StartsWith("pairs", StringComparison.Ordinal) && File.Exists(dst)) throw new BackupException("APPENDONLY_DIVERGED", "a signed exclusion pair differs: " + rel);
                    DurableFile.WriteAtomic(dst, File.ReadAllBytes(f));
                }
                var latch = Path.Combine(ePick.Root, "EXCLUSION_LATCH");
                if (File.Exists(latch) && !File.Exists(Path.Combine(site.Root, "EXCLUSION_LATCH"))) DurableFile.WriteAtomic(Path.Combine(site.Root, "EXCLUSION_LATCH"), File.ReadAllBytes(latch));
            }
            Directory.CreateDirectory(site.StateDir);
            if (!File.Exists(site.InitPath)) DurableFile.WriteAtomic(site.InitPath, File.ReadAllBytes(Path.Combine(initCand.Root, "activation-state", "SITE_INIT.json")));
            DurableFile.WriteAtomic(site.HighWaterPath, CanonicalJson.Bytes(new JsonObject { ["sequence"] = highWater }));

            // ---- 4/5: pointers follow the JOURNAL HEAD; the site stays RECOVERING until `recover` (after re-import)
            var journal = ActivationJournal.Read(site.JournalPath);
            var (initK, initM) = site.ReadInit();
            string headK = journal.HeadBegin("KNOWLEDGE")?.To ?? initK;
            var headMBegin = journal.HeadBegin("MODELS");
            string? headM = headMBegin is null ? initM : headMBegin.To;
            DurableFile.WriteAtomic(site.ActivePointer, Encoding.UTF8.GetBytes(headK));
            site.WritePointer("MODELS", headM);
            site.WriteMarker(SiteState.RECOVERING);
            var installed = new GenerationCatalog(site).Installed();
            sw.Stop();
            return new JsonObject
            {
                ["ok"] = true, ["backup_id"] = (string?)sitePart.Manifest["backup_id"], ["verified"] = verify, ["db"] = dbOut,
                ["vault_objects"] = vaultN, ["uploads"] = upN, ["config_files"] = cfgN, ["conflicts_set_aside"] = conflicts,
                ["appendonly"] = new JsonObject
                {
                    ["journal_from"] = jPick.C.Label, ["journal_bytes"] = jPick.Lines.Length, ["activation_log_from"] = lPick.C.Label,
                    ["exclusions_from"] = ePick.Label, ["exclusion_sequence"] = eSeq, ["high_water"] = highWater,
                    ["database_time_heads"] = h0.ToJson(),
                    ["notes"] = new JsonArray(jNotes.Concat(lNotes).Concat(eNotes).Select(n => n?.DeepClone()).ToArray()),
                },
                ["journal_head"] = new JsonObject { ["knowledge"] = headK, ["models"] = headM },
                ["state"] = "RECOVERING",
                ["reimport_required"] = new JsonArray(installed.Contains(headK) ? [] : [(JsonNode)headK]),
                ["next_steps"] = "re-import the journal-head release from media (stage-only), `stage` it, then `recover`; the site serves only after recovery",
                ["elapsed_ms"] = sw.ElapsedMilliseconds,
            };
        }
        finally
        {
            db?.Dispose();
            try { if (Directory.Exists(work)) Directory.Delete(work, recursive: true); } catch (Exception e) when (e is IOException or UnauthorizedAccessException) { o.Log?.Invoke("restore scratch not removed: " + e.Message); }
        }
    }
}
