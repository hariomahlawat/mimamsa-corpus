// C16 B06 unit tests: Ed25519 verification, the I-6 exclusion reader (including a store written by the Python
// ExclusionStore), the journal (torn tail, corruption, chain, epochs), the writer lease, retention and the reader
// pins / response boundary.
using System.Text;
using System.Text.Json.Nodes;
using Mimamsa.Core.Activation;

namespace Mimamsa.Tests.Activation;

public class Ed25519Tests
{
    static byte[] H(string s) => Convert.FromHexString(s);

    // RFC 8032 section 7.1, TEST 1 and TEST 2.
    [Theory]
    [InlineData("9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60", "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a", "",
        "e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901555fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b")]
    [InlineData("4ccd089b28ff96da9db6c346ec114e0f5b8a319f35aba624da8cf6ed4fb8a6fb", "3d4017c3e843895a92b70aa74d1b7ebc9c982ccf2ec4968cc0cd55f12af4660c", "72",
        "92a009a9f0d4cab8720e820b5f642540a2b27b5416503f8fb3762223ebdb69da085ac1e43e15996e458f3613d0f11d8c387b2eaeb4302aeeb00d291612bb0c00")]
    public void Rfc8032_vectors_sign_and_verify(string seed, string pub, string msg, string sig)
    {
        var (p, sign) = DevEd25519.FromSeed(H(seed));
        Assert.Equal(pub, Convert.ToHexString(p).ToLowerInvariant());
        Assert.Equal(sig, Convert.ToHexString(sign(H(msg))).ToLowerInvariant());
        Assert.True(Ed25519.Verify(H(pub), H(msg), H(sig)));
    }

    [Fact]
    public void Tampered_message_key_signature_and_non_canonical_S_are_rejected()
    {
        var k = new DevRegisterKey();
        var msg = Encoding.UTF8.GetBytes("exclusion update");
        var sig = k.Sign(msg);
        Assert.True(Ed25519.Verify(k.Public, msg, sig));
        Assert.False(Ed25519.Verify(k.Public, Encoding.UTF8.GetBytes("exclusion updatE"), sig));
        var bad = (byte[])sig.Clone(); bad[40] ^= 1;
        Assert.False(Ed25519.Verify(k.Public, msg, bad));
        bad = (byte[])sig.Clone(); bad[3] ^= 1;
        Assert.False(Ed25519.Verify(k.Public, msg, bad));
        Assert.False(Ed25519.Verify(new DevRegisterKey().Public, msg, sig));
        // S + L encodes the same scalar mod L but is non-canonical: refused (malleability).
        var s = new System.Numerics.BigInteger(sig.AsSpan(32), isUnsigned: true) + Ed25519.GroupOrder;
        var sb = new byte[32];
        Assert.True(s.TryWriteBytes(sb, out _, isUnsigned: true));
        Assert.False(Ed25519.Verify(k.Public, msg, [.. sig.AsSpan(0, 32), .. sb]));
        Assert.False(Ed25519.Verify(k.Public, msg, sig.AsSpan(0, 63)));
    }
}

public class ExclusionReaderTests
{
    [Fact]
    public void Reads_a_store_written_by_the_python_ExclusionStore_and_matches_its_effective_state()
    {
        var root = TestDirs.NewSite("pystore");
        try
        {
            CopyDir(TestDirs.RepoFile("app", "b1", "tests", "Mimamsa.Tests", "fixtures", "c16b06_python_exclusion_store"), root);
            var s = new SiteLayout(root);
            var r = ActivationCli.Reader(s, production: false);
            var snap = r.Read();
            Assert.Equal(ExclusionHealth.HEALTHY, snap.Health);
            var want = JsonNode.Parse(File.ReadAllText(Path.Combine(root, "EXPECTED_EFFECTIVE_STATE.json")))!;
            Assert.Equal((long)want["sequence"]!, snap.Sequence);
            Assert.Equal(want["tombstone_doc_ids"]!.AsArray().Select(x => (string)x!), snap.State!.WithdrawnDocIds.Order());
            Assert.Equal(want["tombstone_shas"]!.AsArray().Select(x => (string)x!), snap.State.WithdrawnShas.Order());
            Assert.Equal(want["restricted_tombstone_doc_ids"]!.AsArray().Select(x => (string)x!), snap.State.RestrictedDocIds.Order());
            Assert.Equal(want["restricted_tombstone_shas"]!.AsArray().Select(x => (string)x!), snap.State.RestrictedShas.Order());
            Assert.False(snap.State.IsExcluded("doc-a"));                 // readmitted by a signed update
            Assert.True(snap.State.IsExcluded("doc-b"));
            Assert.True(snap.State.IsExcluded("doc-restricted-1"));       // restricted tombstone: stays after omission
            Assert.True(snap.State.IsExcluded("doc-any", new string('c', 0) + string.Concat(Enumerable.Repeat("cd", 32))));
            // Production mode never uses DEVELOPMENT keys.
            Assert.Equal(ExclusionHealth.BAD_SIGNATURE, ActivationCli.Reader(new SiteLayout(root), production: true).Read().Health);
            // A signature byte flipped by an attacker: BAD_SIGNATURE (fail closed).
            var sig = Path.Combine(s.ExclusionsDir, "pairs", "00000003.sig");
            var b = File.ReadAllBytes(sig); b[10] ^= 0x20; File.WriteAllBytes(sig, b);
            Assert.Equal(ExclusionHealth.BAD_SIGNATURE, ActivationCli.Reader(s, false).Read().Health);
            b[10] ^= 0x20; File.WriteAllBytes(sig, b);
            // An altered payload: UNREADABLE (digest mismatch).
            var pj = Path.Combine(s.ExclusionsDir, "pairs", "00000002.json");
            var orig = File.ReadAllBytes(pj);
            File.WriteAllBytes(pj, [.. orig, (byte)' ']);
            Assert.Equal(ExclusionHealth.UNREADABLE, ActivationCli.Reader(s, false).Read().Health);
            File.WriteAllBytes(pj, orig);
            Assert.Equal(ExclusionHealth.HEALTHY, ActivationCli.Reader(s, false).Read().Health);
        }
        finally { TestDirs.Delete(root); }
    }

    static void CopyDir(string from, string to)
    {
        Directory.CreateDirectory(to);
        foreach (var f in Directory.GetFiles(from)) File.Copy(f, Path.Combine(to, Path.GetFileName(f)), true);
        foreach (var d in Directory.GetDirectories(from)) CopyDir(d, Path.Combine(to, Path.GetFileName(d)));
    }

    [Fact]
    public void Fails_closed_on_missing_unreadable_bad_signature_regressed_and_shrinking_stores()
    {
        using var site = FixtureSite.Simple("reader", "R1", "R2");
        var r = site.NewReader();
        Assert.Equal(ExclusionHealth.HEALTHY, r.Read().Health);
        site.Store.Append(["doc-x"]);
        Assert.Equal(2, r.Read().Sequence);

        // missing store directory
        var moved = site.Layout.ExclusionsDir + ".away";
        Directory.Move(site.Layout.ExclusionsDir, moved);
        Assert.Equal(ExclusionHealth.MISSING, r.Read().Health);
        Directory.Move(moved, site.Layout.ExclusionsDir);
        Assert.Equal(ExclusionHealth.HEALTHY, r.Read().Health);

        // unreadable ACCEPTED
        var acc = Path.Combine(site.Layout.ExclusionsDir, "ACCEPTED.json");
        var accBytes = File.ReadAllBytes(acc);
        File.WriteAllText(acc, "{not json");
        Assert.Equal(ExclusionHealth.UNREADABLE, r.Read().Health);
        File.WriteAllBytes(acc, accBytes);

        // untrusted signer (a key not in the trust list signs the next update)
        var other = new DevRegisterKey();
        site.Store.Append(["doc-y"], signOverride: other.Sign);
        Assert.Equal(ExclusionHealth.BAD_SIGNATURE, r.Read().Health);
        File.WriteAllBytes(acc, accBytes);
        Assert.Equal(ExclusionHealth.HEALTHY, r.Read().Health);

        // regression to an older, validly signed state: caught by this reader, by a NEW reader (persisted
        // high-water mark) and by the site's recorded sequence
        site.Store.RegressOne();
        Assert.Equal(ExclusionHealth.REGRESSED, r.Read().Health);
        Assert.Equal(ExclusionHealth.REGRESSED, site.NewReader().Read().Health);
        File.Delete(site.Layout.HighWaterPath);
        Assert.Equal(ExclusionHealth.REGRESSED, site.NewReader().Read(recordedSequence: 2).Health);
        File.WriteAllBytes(acc, accBytes);
        Assert.Equal(ExclusionHealth.HEALTHY, r.Read().Health);

        // deleting the store entirely after the latch: MISSING, never "empty and healthy"
        Directory.Delete(site.Layout.ExclusionsDir, true);
        Assert.Equal(ExclusionHealth.MISSING, site.NewReader().Read().Health);
    }

    [Fact]
    public void State_only_shrinks_by_a_signed_readmission()
    {
        using var site = FixtureSite.Simple("reader-mono", "R1");
        var r = site.NewReader();
        site.Store.Append(["doc-x", "doc-z"]);
        Assert.True(r.Read().State!.IsExcluded("doc-x"));
        // a later update that merely OMITS doc-x keeps it excluded (monotone tombstone)
        site.Store.Append(["doc-q"]);
        Assert.True(r.Read().State!.IsExcluded("doc-x"));
        // an explicit signed readmission lifts it
        site.Store.Append([], readmitDocIds: ["doc-x"]);
        var s = r.Read();
        Assert.Equal(ExclusionHealth.HEALTHY, s.Health);
        Assert.False(s.State!.IsExcluded("doc-x"));
        Assert.True(s.State.IsExcluded("doc-z"));
        // tampering with the history (dropping an entry whose pair is still on disk) is refused
        var accPath = Path.Combine(site.Layout.ExclusionsDir, "ACCEPTED.json");
        var acc = JsonNode.Parse(File.ReadAllText(accPath))!.AsObject();
        acc["history"]!.AsArray().RemoveAt(1);
        File.WriteAllText(accPath, acc.ToJsonString());
        Assert.NotEqual(ExclusionHealth.HEALTHY, site.NewReader().Read().Health);
    }
}

public class ActivationJournalTests
{
    static FixtureSite Site(out ActivationEngine eng, out ActivationParticipant p, string label = "journal")
    {
        var site = FixtureSite.Simple(label, "R1", "R2", "R3");
        p = new ActivationParticipant(new SiteInspector(site.Layout, site.NewReader()));
        p.LoadHead();
        eng = new ActivationEngine(new ActivationEngineOptions
        {
            Site = site.Layout, WriterId = "activator-1", Database = site.Db, Exclusions = site.NewReader(),
            Participant = new DirectParticipantLink(p), Disk = new FixedDiskProbe(1L << 40),
        });
        eng.AcquireLock();
        return site;
    }

    [Fact]
    public void Records_are_canonical_hash_chained_schema_shaped_and_flushed_per_line()
    {
        using var site = Site(out var eng, out _);
        using var _e = eng;
        var txn = eng.Transition("KNOWLEDGE", "R2");
        var lines = File.ReadAllText(site.Layout.JournalPath).Split('\n');
        Assert.Equal("", lines[^1]);                       // LF-terminated
        Assert.Equal(3, lines.Length - 1);
        string? prev = null;
        for (int i = 0; i < 3; i++)
        {
            var o = JsonNode.Parse(lines[i])!.AsObject();
            Assert.Equal("mimamsa-corpus-contract/2.1", (string?)o["contract"]);
            Assert.Equal("activation_journal_record", (string?)o["record_kind"]);
            Assert.Equal(i + 1, (long)o["seq"]!);
            Assert.Equal(prev, (string?)o["previous_record_sha256"]);
            Assert.Equal(txn, (string?)o["txn_id"]);
            Assert.Matches("^TX-[0-9]{8}-[0-9a-f]{12}$", txn);
            Assert.Matches(@"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]{1,6})?Z$", (string)o["at"]!);
            Assert.Equal(1, (long)o["writer"]!["lock_epoch"]!);
            Assert.Equal(lines[i], Encoding.UTF8.GetString(CanonicalJson.Bytes(o)));
            prev = CanonicalJson.Sha256Hex(Encoding.UTF8.GetBytes(lines[i]));
        }
        Assert.Equal(["BEGIN", "DECIDED", "OPEN"], lines[..3].Select(l => (string)JsonNode.Parse(l)!["step"]!));
        Assert.Equal(1L, (long)JsonNode.Parse(lines[2])!["exclusion_seq"]!);   // the baseline store sequence applied at OPEN
    }

    [Fact]
    public void Torn_tail_is_absent_and_truncated_by_recovery_but_corruption_elsewhere_fails_closed()
    {
        using var site = Site(out var eng, out var p, "journal-torn");
        using var _e = eng;
        eng.Transition("KNOWLEDGE", "R2");
        var jp = site.Layout.JournalPath;
        var full = File.ReadAllBytes(jp);
        // unterminated last line
        File.WriteAllBytes(jp, full[..^7]);
        var j = ActivationJournal.Read(jp);
        Assert.True(j.TornTail);
        Assert.Equal(["BEGIN", "DECIDED"], j.Entries.Select(e => e.Step));
        Assert.Throws<InvalidOperationException>(() => ActivationJournal.Append(jp, j, j.Entries[0].TxnId, "OPEN", "activator-1", 1, exclusionSeq: 1));
        eng.Recover();
        var after = ActivationJournal.Read(jp);
        Assert.False(after.TornTail);
        Assert.Equal(["BEGIN", "DECIDED", "OPEN"], after.Entries.Select(e => e.Step));
        Assert.Equal("R2", site.Layout.ReadPointer("KNOWLEDGE"));
        Assert.True(p.IsServing());
        // terminated but unparseable LAST line: also torn
        File.AppendAllText(jp, "{\"half\":\n");
        Assert.True(ActivationJournal.Read(jp).TornTail);
        eng.Recover();
        // the same garbage in the MIDDLE: corruption, recovery refused, nothing served
        var good = File.ReadAllLines(jp);
        File.WriteAllText(jp, good[0] + "\n{\"half\":\n" + string.Join("\n", good[1..]) + "\n");
        Assert.Throws<JournalCorruptException>(() => ActivationJournal.Read(jp));
        var ex = Assert.Throws<ActivationRefused>(() => eng.Recover());
        Assert.Equal("JOURNAL_CORRUPT", ex.Code);
        p.Site.InvalidateCache();
        Assert.Equal(SiteState.FAILED_CLOSED, p.Site.State());
        Assert.False(p.IsServing());
        Assert.Throws<ActivationRefused>(() => p.Pin());
    }

    [Fact]
    public void A_lower_epoch_cannot_append()
    {
        using var site = Site(out var eng, out _, "journal-epoch");
        using var _e = eng;
        eng.Transition("KNOWLEDGE", "R2");
        var j = ActivationJournal.Read(site.Layout.JournalPath);
        var ex = Assert.Throws<ActivationRefused>(() => ActivationJournal.Append(site.Layout.JournalPath, j, "TX-00000009-aaaaaaaaaaaa", "BEGIN", "stale-writer", 0, "KNOWLEDGE", "R2", "R3", "ACTIVATE"));
        Assert.Equal("NOT_LOCK_HOLDER", ex.Code);
    }

    [Fact]
    public void Stale_writer_after_takeover_is_fenced_at_every_step()
    {
        using var site = Site(out var eng1, out var p, "journal-fence");
        using var _1 = eng1;
        using var eng2 = new ActivationEngine(new ActivationEngineOptions
        {
            Site = site.Layout, WriterId = "activator-2", Database = site.Db, Exclusions = site.NewReader(),
            Participant = new DirectParticipantLink(p), Disk = new FixedDiskProbe(1L << 40), Clock = () => DateTimeOffset.UtcNow.ToUnixTimeSeconds() + 100,
        });
        // eng1's heartbeat is stale from eng2's clock: takeover with epoch 2; eng2 must recover first
        Assert.True(eng2.AcquireLock());
        Assert.Equal("RECOVERY_REQUIRED", Assert.Throws<ActivationRefused>(() => eng2.Transition("KNOWLEDGE", "R2")).Code);
        // the old writer (alive, but fenced) is refused everywhere
        Assert.Equal("NOT_LOCK_HOLDER", Assert.Throws<ActivationRefused>(() => eng1.Transition("KNOWLEDGE", "R3")).Code);
        Assert.Equal("NOT_LOCK_HOLDER", Assert.Throws<ActivationRefused>(() => eng1.Recover()).Code);
        Assert.Throws<ActivationRefused>(() => eng1.Lease.Authorised(() => { }));
        eng2.Recover();
        eng2.Transition("KNOWLEDGE", "R2");
        Assert.All(ActivationJournal.Read(site.Layout.JournalPath).Entries, e => Assert.Equal(2, e.LockEpoch));
    }

    [Fact]
    public void Transition_refused_towards_unstaged_or_unverified_targets_and_while_recovering()
    {
        using var site = Site(out var eng, out _, "journal-refuse");
        using var _e = eng;
        Assert.Equal("NOT_STAGED", Assert.Throws<ActivationRefused>(() => eng.Transition("KNOWLEDGE", "R9")).Code);
        Assert.Equal("NOT_STAGED", Assert.Throws<ActivationRefused>(() => eng.Transition("MODELS", "M9")).Code);
        Assert.Equal("INVALID_ID", Assert.Throws<ActivationRefused>(() => eng.Transition("KNOWLEDGE", "..\\evil")).Code);
        site.Layout.WriteMarker(SiteState.RECOVERING);
        Assert.Equal("RECOVERY_REQUIRED", Assert.Throws<ActivationRefused>(() => eng.Transition("KNOWLEDGE", "R2")).Code);
        Assert.Empty(ActivationJournal.Read(site.Layout.JournalPath).Entries);
    }

    [Fact]
    public void Exclusion_acceptance_contends_for_the_same_lock_as_the_journal_writer()
    {
        using var site = Site(out var eng, out var p, "journal-contend");
        using var _e = eng;
        // hold the guard as a journal append would, and try to accept an exclusion meanwhile
        var held = new ManualResetEventSlim();
        var release = new ManualResetEventSlim();
        var t = Task.Run(() => WriterLease.UnderGuard(site.Layout, () => { held.Set(); release.Wait(); return 0; }));
        held.Wait();
        var ex = Assert.Throws<ActivationRefused>(() => ActivationEngine.AcceptExclusion(site.Layout, p.Site, () => site.Store.Append(["doc-x"]), TimeSpan.FromMilliseconds(300)));
        Assert.Equal("LOCK_CONTENDED", ex.Code);
        release.Set(); t.Wait();
        ActivationEngine.AcceptExclusion(site.Layout, p.Site, () => site.Store.Append(["doc-x"]));
        Assert.Equal(2, site.Layout.ReadApplied()["R3"]);
    }
}

public class ActivationPinTests
{
    [Fact]
    public void Pinned_reader_never_bypasses_a_later_exclusion_and_rollback_cannot_resurrect_it()
    {
        using var site = FixtureSite.Simple("pins", "R1", "R2", "R3");
        var p = new ActivationParticipant(new SiteInspector(site.Layout, site.NewReader()));
        p.LoadHead();
        using var eng = new ActivationEngine(new ActivationEngineOptions
        {
            Site = site.Layout, WriterId = "activator-1", Database = site.Db, Exclusions = site.NewReader(),
            Participant = new DirectParticipantLink(p), Disk = new FixedDiskProbe(1L << 40),
        });
        eng.AcquireLock();
        var pin = p.Pin();
        Assert.Equal(("R1", "M1"), (pin.Knowledge, pin.Models));
        ActivationEngine.AcceptExclusion(site.Layout, p.Site, () => site.Store.Append(["doc-x"]));
        Assert.Equal(["doc-y"], p.Respond(pin, ["doc-x", "doc-y"]));     // accepted AFTER the pin: still enforced
        eng.Transition("KNOWLEDGE", "R2");
        Assert.Equal(1, p.PinCount);                                      // the old generation stays pinned (CG-4)
        Assert.Contains("R1", eng.Inspector.Catalog.Installed());
        var released = new List<string>();
        p.OnGenerationReleased = released.Add;
        p.Unpin(pin);
        Assert.Equal(["R1"], released);
        eng.Transition("KNOWLEDGE", "R1", "ROLLBACK");                     // rollback to the older generation
        var pin2 = p.Pin();
        Assert.Equal(["doc-y"], p.Respond(pin2, ["doc-x", "doc-y"]));    // no resurrection
        Assert.Equal(site.Store.Sequence, site.Layout.ReadApplied()["R1"]);
    }

    [Fact]
    public void Concurrent_readers_during_switches_never_pin_a_mixed_generation()
    {
        using var site = FixtureSite.Simple("mixed", "R1", "R2", "R3");
        var p = new ActivationParticipant(new SiteInspector(site.Layout, site.NewReader()));
        p.LoadHead();
        using var eng = new ActivationEngine(new ActivationEngineOptions
        {
            Site = site.Layout, WriterId = "activator-1", Database = site.Db, Exclusions = site.NewReader(),
            Participant = new DirectParticipantLink(p), Disk = new FixedDiskProbe(1L << 40),
        });
        eng.AcquireLock();
        var valid = new HashSet<(string, string)> { ("R1", "M1"), ("R2", "M1"), ("R2", "M2"), ("R3", "M2"), ("R1", "M2") };
        var seen = new System.Collections.Concurrent.ConcurrentBag<(string, string)>();
        int refused = 0;
        using var stop = new CancellationTokenSource();
        var readers = Enumerable.Range(0, 3).Select(_ => Task.Run(() =>
        {
            while (!stop.IsCancellationRequested)
            {
                try
                {
                    var pin = p.Pin();
                    seen.Add((pin.Knowledge, pin.Models));
                    Assert.Equal(pin.Knowledge, p.Respond(pin, [pin.Knowledge]).Single());
                    p.Unpin(pin);
                }
                catch (ActivationRefused) { Interlocked.Increment(ref refused); }
                Thread.Sleep(1);
            }
        })).ToArray();
        eng.Transition("KNOWLEDGE", "R2");
        eng.Transition("MODELS", "M2");
        eng.Transition("KNOWLEDGE", "R3");
        eng.Transition("KNOWLEDGE", "R1", "ROLLBACK");
        Thread.Sleep(100);
        stop.Cancel();
        Task.WaitAll(readers);
        Assert.NotEmpty(seen);
        Assert.All(seen, pair => Assert.Contains(pair, valid));
        Assert.Equal(0, p.PinCount);
    }

    [Fact]
    public void Retention_keeps_previous_distinct_pinned_inflight_and_recovery_target()
    {
        using var site = new FixtureSite("retain", ["R0", "R1", "R2", "R3", "R4", "R5"], "R1", "M1",
            new Dictionary<string, (bool, string[])> { ["M1"] = (true, ["R0", "R1", "R2", "R3", "R4", "R5"]) });
        var p = new ActivationParticipant(new SiteInspector(site.Layout, site.NewReader()));
        p.LoadHead();
        var link = new DirectParticipantLink(p);
        using var eng = new ActivationEngine(new ActivationEngineOptions
        {
            Site = site.Layout, WriterId = "activator-1", Database = site.Db, Exclusions = site.NewReader(),
            Participant = link, Disk = new FixedDiskProbe(1L << 40), RecoveryTarget = "R0",
        });
        eng.AcquireLock();
        eng.Transition("KNOWLEDGE", "R2");
        var pin = p.Pin();                                     // R2 pinned
        eng.Transition("KNOWLEDGE", "R1", "ROLLBACK");
        eng.Transition("KNOWLEDGE", "R3");
        eng.Transition("KNOWLEDGE", "R4");
        Assert.Equal(["R3", "R1"], eng.PreviousDistinct());
        link.Up = false;
        Assert.Empty(eng.Prune());                             // pins unknown: prune nothing
        link.Up = true;
        var removed = eng.Prune();
        Assert.Equal(["R5"], removed);                         // R0 recovery target, R1/R3 previous, R2 pinned, R4 active
        p.Unpin(pin);
        Assert.Equal(["R2"], eng.Prune());
    }
}
