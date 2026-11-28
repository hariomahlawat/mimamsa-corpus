// C16 S3-C (B08; architecture section 10; plan B08 acceptance 1-8 at the file/journal level, TEST DATA ONLY):
// encrypted backup and restore of local site data with SEPARATE append-only stores, on a B06 fixture site whose
// journal, activation log and signed ExclusionStore are real (the B06 engine writes them). The PostgreSQL part and the
// full serving journey with real releases are in SiteDatabaseInstallTests and S3cRestoreJourneyTests.
//   - restore follows the JOURNAL HEAD, not the backup; latest exclusions win; a target store is never overwritten by an
//     older one; recovery then reconciles views and publication rows and re-applies the latest exclusions
//   - refused: append-only stores missing or older than the database dump, diverged or corrupt stores, a wrong key, a
//     tampered/truncated/partial backup, unsafe or non-regular archive entries, a corrupt vault object, an unclean target
using System.Formats.Tar;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json.Nodes;
using Mimamsa.Core.Activation;
using Mimamsa.Core.Install;
using Mimamsa.Tests.Activation;

namespace Mimamsa.Tests.Install;

public sealed class BackupFixture : IDisposable
{
    public readonly string Base;
    public readonly FixtureSite Fx;
    public readonly InstallConfig Cfg;
    public readonly byte[] Key = RandomNumberGenerator.GetBytes(32);
    public readonly ActivationEngine Eng;
    public readonly string VaultSha;
    public string B1 = "", B2 = "";

    public BackupFixture()
    {
        Base = S3cDirs.New("bk");
        Fx = FixtureSite.Simple("s3c-bk", "G1", "G2", "G3");
        Cfg = S3cDirs.Config(Path.Combine(Base, "src"), site: Fx.Root);
        InstallLayout.Create(Cfg, null, "test");
        var obj = Encoding.UTF8.GetBytes("vault object bytes");
        VaultSha = Convert.ToHexString(SHA256.HashData(obj)).ToLowerInvariant();
        Directory.CreateDirectory(Path.Combine(Fx.Root, "vault", "sha256", VaultSha[..2]));
        File.WriteAllBytes(Path.Combine(Fx.Root, "vault", "sha256", VaultSha[..2], VaultSha), obj);
        Directory.CreateDirectory(Path.Combine(Cfg.Root("uploads"), "admin"));
        File.WriteAllText(Path.Combine(Cfg.Root("uploads"), "admin", "local-upload.txt"), "a local Admin upload");
        File.WriteAllText(Path.Combine(Cfg.Root("config"), "appsettings.site.json"), "{\"site\":\"s3c\"}");
        Directory.CreateDirectory(Path.Combine(Cfg.Root("config"), "secrets"));
        File.WriteAllText(Path.Combine(Cfg.Root("config"), "secrets", "c16s3c_web.pw"), "never backed up");
        File.WriteAllText(Path.Combine(Fx.Root, "SITE_CONFIG.json"), "{\"exclusion_channel\":\"signed\"}");
        Eng = new ActivationEngine(new ActivationEngineOptions
        {
            Site = Fx.Layout, WriterId = "s3c-activator", Database = Fx.Db, Exclusions = Fx.NewReader(), Disk = new FixedDiskProbe(1L << 40), Participant = Link(Fx.Layout, Fx.NewReader()),
        });
        Eng.AcquireLock();
        Eng.Transition("KNOWLEDGE", "G2");
        Exclude("doc-x");
        B1 = Backup();
        Eng.Transition("KNOWLEDGE", "G3");
        Exclude("doc-y");
        B2 = Backup();
    }

    public static IParticipantLink Link(SiteLayout s, ExclusionReader r) { var p = new ActivationParticipant(new SiteInspector(s, r)); p.LoadHead(); return new DirectParticipantLink(p); }

    public void Exclude(string doc) => ActivationEngine.AcceptExclusion(Fx.Layout, new SiteInspector(Fx.Layout, Fx.NewReader()), () => Fx.Store.Append([doc]));

    public string Backup(string? dest = null) =>
        (string)SiteBackup.Create(new SiteBackup.Options { Config = Cfg, Key = Key, Destination = dest, FrameBytes = 4096 })["path"]!;

    /// A clean target installation (fresh roots).
    public InstallConfig Target(string label)
    {
        var t = S3cDirs.Config(Path.Combine(Base, label));
        InstallLayout.Create(t, null, "test");
        return t;
    }

    public JsonObject Restore(InstallConfig t, string backupDir, params string[] aoFrom) =>
        SiteRestore.Run(new SiteRestore.Options { Config = t, Key = Key, BackupDir = backupDir, AppendOnlyFrom = aoFrom });

    public string Copy(string backupDir, string label, bool site = true, bool ao = true)
    {
        var d = Path.Combine(Base, "media", label);
        Directory.CreateDirectory(d);
        if (site) File.Copy(Path.Combine(backupDir, "site.mbk"), Path.Combine(d, "site.mbk"));
        if (ao) File.Copy(Path.Combine(backupDir, "appendonly.mbk"), Path.Combine(d, "appendonly.mbk"));
        BackupRepack.UpdateSums(d);
        return d;
    }

    public void Dispose()
    {
        try { Eng.ReleaseLock(); } catch { }
        Eng.Dispose();
        Fx.Dispose();
        S3cDirs.Delete(Base);
    }
}

public class SiteBackupRestoreTests : IClassFixture<BackupFixture>
{
    readonly BackupFixture F;
    public SiteBackupRestoreTests(BackupFixture f) { F = f; }

    static string Code(Action a) => Assert.Throws<BackupException>(a).Code;
    static byte[] Bytes(string p) => File.ReadAllBytes(p);

    static Dictionary<string, string> Snapshot(string root) =>
        Directory.Exists(root)
            ? Directory.EnumerateFiles(root, "*", SearchOption.AllDirectories).ToDictionary(f => Path.GetRelativePath(root, f), f => Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(f))))
            : new();

    [Fact]
    public void Backup_is_encrypted_checksummed_and_excludes_knowledge_and_secrets()
    {
        var entries = BackupRepack.Read(Path.Combine(F.B2, "site.mbk"), F.Key, "site").Select(e => e.Name).ToList();
        Assert.Contains($"files/vault/sha256/{F.VaultSha[..2]}/{F.VaultSha}", entries);
        Assert.Contains("files/uploads/admin/local-upload.txt", entries);
        Assert.Contains("files/config/appsettings.site.json", entries);
        Assert.Contains("files/site/SITE_CONFIG.json", entries);
        Assert.DoesNotContain(entries, e => e.Contains("secrets/") || e.Contains("generations/") || e.Contains("journal") || e.Contains("exclusions"));
        Assert.Equal(SiteBackup.ManifestEntry, entries[^1]);
        var ao = BackupRepack.Read(Path.Combine(F.B2, "appendonly.mbk"), F.Key, "appendonly").Select(e => e.Name).ToList();
        Assert.Contains("appendonly/journal/journal.jsonl", ao);
        Assert.Contains("appendonly/activation-log/activation-log.jsonl", ao);
        Assert.Contains("appendonly/exclusions/ACCEPTED.json", ao);
        Assert.Contains("appendonly/activation-state/SITE_INIT.json", ao);
        // ciphertext reveals nothing of the plaintext
        Assert.DoesNotContain("local Admin upload", Encoding.Latin1.GetString(Bytes(Path.Combine(F.B2, "site.mbk"))));
        Assert.DoesNotContain("TX-", Encoding.Latin1.GetString(Bytes(Path.Combine(F.B2, "appendonly.mbk"))));
        Assert.Equal("match", (string?)SiteBackup.Verify(F.B2, F.Key)["sha256sums"]);
    }

    [Fact]
    public void Restore_onto_a_clean_install_follows_the_journal_head_and_recovers_with_the_latest_exclusions()
    {
        var t = F.Target("t-full");
        var r = F.Restore(t, F.B2);
        var ts = t.Site;
        var ao = BackupRepack.Read(Path.Combine(F.B2, "appendonly.mbk"), F.Key, "appendonly").ToDictionary(e => e.Name, e => e.Data);
        Assert.Equal(ao["appendonly/journal/journal.jsonl"], Bytes(ts.JournalPath));
        Assert.Equal(ao["appendonly/activation-log/activation-log.jsonl"], Bytes(ts.ActivationLogPath));
        Assert.Equal(ao["appendonly/exclusions/ACCEPTED.json"], Bytes(Path.Combine(ts.ExclusionsDir, "ACCEPTED.json")));
        long b2Seq = (long)JsonNode.Parse(ao["appendonly/exclusions/ACCEPTED.json"])!["sequence"]!;
        Assert.Null(ts.ReadPointer("KNOWLEDGE"));                       // derived pointer: absent until recovery (head not installed)
        Assert.Equal("G3", (string?)r["journal_head"]!["knowledge"]);
        Assert.Equal(SiteState.RECOVERING, ts.ReadMarker());
        Assert.Equal(["G3"], r["reimport_required"]!.AsArray().Select(x => (string)x!));
        Assert.Equal("a local Admin upload", File.ReadAllText(Path.Combine(t.Root("uploads"), "admin", "local-upload.txt")));
        Assert.True(File.Exists(Path.Combine(ts.Root, "vault", "sha256", F.VaultSha[..2], F.VaultSha)));
        Assert.False(Directory.Exists(Path.Combine(t.Root("config"), "secrets")) && File.Exists(Path.Combine(t.Root("config"), "secrets", "c16s3c_web.pw")));
        // nothing serves before recovery; simulate the re-import + staging of the head (B06 harness), then recover
        File.WriteAllText(Path.Combine(ts.StateDir, StagingMarker.SimulationFlag), "B06 simulation harness");
        new GenerationCatalog(ts).StageGeneration("G3");
        var db = new FileActivationDatabase(ts.FileDbPath);
        using var eng = new ActivationEngine(new ActivationEngineOptions
        {
            Site = ts, WriterId = "s3c-restorer", Database = db, Exclusions = ActivationCli.Reader(ts, production: false), Disk = new FixedDiskProbe(1L << 40),
            Participant = BackupFixture.Link(ts, ActivationCli.Reader(ts, production: false)),
        });
        eng.AcquireLock();
        Assert.True(eng.NeedsRecovery());
        eng.Recover();
        Assert.Equal(SiteState.OPEN, ts.ReadMarker());
        Assert.Equal("G3", db.Views());
        Assert.Equal("G3", ts.ReadPointer("KNOWLEDGE"));                // recovery derived ACTIVE from the journal head
        Assert.Equal(2, db.PublicationCount());                         // both committed transactions reconciled
        Assert.Equal(b2Seq, ts.ReadApplied()["G3"]);                      // latest exclusion state applied
        // a rollback to a release that is not retained on the restored site is refused until it is re-imported
        Assert.Throws<ActivationRefused>(() => eng.Transition("KNOWLEDGE", "G2", "ROLLBACK"));
        eng.ReleaseLock();
    }

    [Fact]
    public void An_older_backup_with_a_newer_offline_append_only_copy_follows_the_newer_journal_and_exclusions()
    {
        var t = F.Target("t-older-db");
        var r = F.Restore(t, F.B1, F.B2);
        Assert.StartsWith("offline copy", (string?)r["appendonly"]!["journal_from"]);
        Assert.Equal("G3", (string?)r["journal_head"]!["knowledge"]);           // not G2, which the older backup saw
        var seqB2 = (long)r["appendonly"]!["exclusion_sequence"]!;
        Assert.Equal(seqB2, (long)JsonNode.Parse(BackupRepack.Read(Path.Combine(F.B2, "appendonly.mbk"), F.Key, "appendonly")
            .Single(e => e.Name == "appendonly/exclusions/ACCEPTED.json").Data)!["sequence"]!);
    }

    [Fact]
    public void Append_only_stores_older_than_the_database_or_missing_are_refused()
    {
        var siteOnly = F.Copy(F.B2, "b2-site-only", ao: false);
        var aoOld = F.Copy(F.B1, "b1-ao-only", site: false);
        var t = F.Target("t-stale");
        var before = Snapshot(Path.Combine(Path.GetDirectoryName(t.Root("site"))!));
        Assert.Equal("APPENDONLY_OLDER_THAN_DATABASE", Code(() => F.Restore(t, siteOnly, aoOld)));
        Assert.Equal("APPENDONLY_MISSING", Code(() => F.Restore(t, siteOnly)));
        Assert.Equal(before, Snapshot(Path.Combine(Path.GetDirectoryName(t.Root("site"))!)));   // target untouched
    }

    [Fact]
    public void A_newer_target_store_is_kept_and_never_overwritten()
    {
        var t = F.Target("t-newer");
        // the target already holds append-only stores NEWER than any backup (copied from the live site after one more
        // exclusion): the restore must keep them byte for byte
        F.Exclude("doc-z");
        var ts = t.Site;
        Directory.CreateDirectory(ts.JournalDir);
        File.Copy(F.Fx.Layout.JournalPath, ts.JournalPath);
        Directory.CreateDirectory(Path.GetDirectoryName(ts.ActivationLogPath)!);
        File.Copy(F.Fx.Layout.ActivationLogPath, ts.ActivationLogPath);
        foreach (var f in Directory.EnumerateFiles(F.Fx.Layout.ExclusionsDir, "*", SearchOption.AllDirectories))
        {
            var d = Path.Combine(ts.ExclusionsDir, Path.GetRelativePath(F.Fx.Layout.ExclusionsDir, f));
            Directory.CreateDirectory(Path.GetDirectoryName(d)!);
            File.Copy(f, d, true);
        }
        var before = Snapshot(ts.ExclusionsDir);
        var j = Bytes(ts.JournalPath);
        var r = F.Restore(t, F.B1);
        Assert.Equal("target site", (string?)r["appendonly"]!["journal_from"]);
        Assert.Equal("target site", (string?)r["appendonly"]!["exclusions_from"]);
        Assert.Equal(F.Fx.Store.Sequence, (long)r["appendonly"]!["exclusion_sequence"]!);
        Assert.Equal(j, Bytes(ts.JournalPath));
        Assert.Equal(before, Snapshot(ts.ExclusionsDir));
    }

    [Fact]
    public void Diverged_or_corrupt_append_only_stores_are_refused()
    {
        // a journal that extends the B1 head differently from B2 (a valid, hash-chained record of another transaction)
        var t = F.Target("t-diverged");
        var ao1 = BackupRepack.Read(Path.Combine(F.B1, "appendonly.mbk"), F.Key, "appendonly");
        var ts = t.Site;
        Directory.CreateDirectory(ts.JournalDir);
        File.WriteAllBytes(ts.JournalPath, ao1.Single(e => e.Name == "appendonly/journal/journal.jsonl").Data);
        var js = ActivationJournal.Read(ts.JournalPath);
        ActivationJournal.Append(ts.JournalPath, js, "TX-00000099-0123456789ab", "BEGIN", "forger-xyz", js.MaxEpoch, "KNOWLEDGE", "G2", "G1", "ACTIVATE");
        Assert.Equal("APPENDONLY_DIVERGED", Code(() => F.Restore(t, F.B1, F.B2)));

        // the only journal candidate corrupt in the middle (crafted inside an authenticated backup): refused
        var bad = F.Copy(F.B2, "b2-corrupt-journal");
        BackupRepack.Rewrite(bad, "appendonly", F.Key, es => es.Select(e => e.Name != "appendonly/journal/journal.jsonl" ? e
            : e with { Data = Encoding.UTF8.GetBytes("{not json}\n").Concat(e.Data).ToArray() }).ToList());
        var t2 = F.Target("t-corrupt");
        Assert.Equal("APPENDONLY_CORRUPT", Code(() => F.Restore(t2, bad)));

        // a torn tail on a candidate is tolerated (the complete lines are the store)
        var torn = F.Copy(F.B2, "b2-torn");
        BackupRepack.Rewrite(torn, "appendonly", F.Key, es => es.Select(e => e.Name != "appendonly/journal/journal.jsonl" ? e
            : e with { Data = e.Data.Concat(Encoding.UTF8.GetBytes("{\"partial")).ToArray() }).ToList());
        var t3 = F.Target("t-torn");
        Assert.Equal("G3", (string?)F.Restore(t3, torn)["journal_head"]!["knowledge"]);
        Assert.False(ActivationJournal.Read(t3.Site.JournalPath).TornTail);
    }

    [Fact]
    public void Wrong_key_tampering_truncation_and_partial_backups_are_refused_before_the_target_is_touched()
    {
        var t = F.Target("t-neg");
        var root = Path.GetDirectoryName(t.Root("site"))!;
        var before = Snapshot(root);
        Assert.Equal("BACKUP_WRONG_KEY", Assert.Throws<BackupCryptoException>(() =>
            SiteRestore.Run(new SiteRestore.Options { Config = t, Key = RandomNumberGenerator.GetBytes(32), BackupDir = F.B2 })).Code);
        var flipped = F.Copy(F.B2, "flip");
        var b = Bytes(Path.Combine(flipped, "site.mbk")); b[b.Length / 2] ^= 0x40; File.WriteAllBytes(Path.Combine(flipped, "site.mbk"), b);
        Assert.Equal("BACKUP_CHECKSUM_MISMATCH", Code(() => F.Restore(t, flipped)));
        BackupRepack.UpdateSums(flipped);   // an attacker who also rewrites SHA256SUMS is still caught by authentication
        Assert.Equal("BACKUP_AUTH_FAILED", Assert.Throws<BackupCryptoException>(() => F.Restore(t, flipped)).Code);
        var cut = F.Copy(F.B2, "cut");
        var c = Bytes(Path.Combine(cut, "appendonly.mbk")); File.WriteAllBytes(Path.Combine(cut, "appendonly.mbk"), c[..(c.Length - 40)]);
        BackupRepack.UpdateSums(cut);
        Assert.Equal("BACKUP_TRUNCATED", Assert.Throws<BackupCryptoException>(() => F.Restore(t, cut)).Code);
        var partial = F.Copy(F.B2, "partial");
        File.Delete(Path.Combine(partial, "site.mbk"));
        Assert.Equal("BACKUP_PARTIAL", Code(() => F.Restore(t, partial)));
        var nosums = F.Copy(F.B2, "nosums");
        File.Delete(Path.Combine(nosums, "SHA256SUMS"));
        Assert.Equal("BACKUP_PARTIAL", Code(() => F.Restore(t, nosums)));
        Assert.Equal(before, Snapshot(root));
    }

    [Fact]
    public void Unsafe_entries_and_corrupt_vault_objects_inside_an_authenticated_backup_are_refused()
    {
        string Case(string label, Func<List<PartEntry>, List<PartEntry>> edit, bool keepManifest = false)
        {
            var d = F.Copy(F.B2, label);
            BackupRepack.Rewrite(d, "site", F.Key, edit, keepManifest);
            var t = F.Target("t-" + label);
            var root = Path.GetDirectoryName(t.Root("site"))!;
            var before = Snapshot(root);
            var code = Code(() => F.Restore(t, d));
            Assert.Equal(before, Snapshot(root));   // every refusal happens before the target is touched
            return code;
        }
        Assert.Equal("BACKUP_ENTRY_TYPE", Case("symlink", es => [.. es, new PartEntry("files/uploads/evil", [], TarEntryType.SymbolicLink, "../../../etc")]));
        Assert.Equal("BACKUP_ENTRY_TYPE", Case("hardlink", es => [.. es, new PartEntry("files/uploads/evil2", [], TarEntryType.HardLink, "files/config/appsettings.site.json")]));
        Assert.Equal("PATH_RESERVED_NAME", Case("reserved", es => [.. es, new PartEntry("files/uploads/CON.txt", "x"u8.ToArray())]));
        Assert.Equal("PATH_SHORT_NAME_ALIAS", Case("alias", es => [.. es, new PartEntry("files/uploads/LOCAL-~1.TXT", "x"u8.ToArray())]));
        Assert.Equal("PATH_TRAVERSAL", Case("traversal", es => [.. es, new PartEntry("files/uploads/../../x", "x"u8.ToArray())]));
        Assert.Equal("PATH_CASE_COLLISION", Case("case", es => [.. es, new PartEntry("files/uploads/ADMIN/local-upload.txt", "y"u8.ToArray())]));
        Assert.Equal("BACKUP_MANIFEST_MISMATCH", Case("manifest", es => es.Select(e => e.Name.EndsWith("local-upload.txt") ? e with { Data = "changed"u8.ToArray() } : e).ToList(), keepManifest: true));
        Assert.Equal("VAULT_OBJECT_CORRUPT", Case("vault", es => es.Select(e => e.Name.Contains("files/vault/") ? e with { Data = "not the object"u8.ToArray() } : e).ToList()));
        Assert.Equal("BACKUP_ENTRY_UNKNOWN", Case("unknown", es => [.. es, new PartEntry("elsewhere/x", "x"u8.ToArray())]));
    }

    [Fact]
    public void An_unclean_target_is_refused()
    {
        var t = F.Target("t-unclean");
        Directory.CreateDirectory(Path.Combine(t.Root("site"), "vault", "sha256", "aa"));
        File.WriteAllText(Path.Combine(t.Root("site"), "vault", "sha256", "aa", new string('a', 64)), "x");
        Assert.Equal("TARGET_NOT_CLEAN", Code(() => F.Restore(t, F.B2)));
    }

    [Fact]
    public void Backup_refuses_links_in_sources_and_verifies_the_copy_on_media()
    {
        var media = Path.Combine(F.Base, "offline-media");
        Directory.CreateDirectory(media);
        var p = F.Backup(media);
        var id = Path.GetFileName(p);
        Assert.Equal("match", (string?)SiteBackup.Verify(Path.Combine(media, id), F.Key)["sha256sums"]);
        var outside = Directory.CreateDirectory(Path.Combine(F.Base, "outside")).FullName;
        var link = Path.Combine(F.Cfg.Root("uploads"), "linked");
        Assert.True(S3cDirs.Link(link, outside));
        try { Assert.Equal("PATH_REPARSE_POINT", Code(() => F.Backup())); }
        finally { Directory.Delete(link); }
    }
}
