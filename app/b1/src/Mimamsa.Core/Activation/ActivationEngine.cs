// C16 B06 core: the activation tool's state machine, a durable implementation of the reference model
// app/contract/mimamsa_contract/c16/activation.py (architecture section 8.2) plus the protocol parts of scenarios.py
// (single writer with epoch, participant on the control channel, torn-tail reader, I-6 exclusion reader).
//
// Transaction:  validate -> participant ENTER_SWITCHING/ACK -> marker SWITCHING -> BEGIN -> DECIDED (the ONE commit
//               decision) -> DB_APPLIED -> POINTER_WRITTEN -> EXCLUSIONS_APPLIED -> LOGGED -> OPEN -> marker OPEN ->
//               participant OPEN/ACK.
// Every journal record is flushed to the device before the next effect; every effect runs under the writer guard
// with a holder check (a stale writer is fenced at every step), and is idempotent so recovery can replay it.
// recover(): refuses service until done; truncates a torn tail; aborts undecided transactions; rolls decided ones
//            forward; reconciles pointers, views and publication rows with the journal head; re-applies the latest
//            exclusion state to every installed generation; clears all scratch; marker OPEN. Idempotent.
// Named step hooks (StepHook) exist for the conformance harness and the crash test host; the production CLI passes
// none.
using System.Security.Cryptography;
using System.Text;

namespace Mimamsa.Core.Activation;

public sealed class ActivationRefused(string code, string message) : Exception(code + ": " + message)
{
    public string Code { get; } = code;
}

/// Injected crash (conformance harness only): the transition stops here as if the process had died.
public sealed class ActivationCrash(string point) : Exception("crash injected after " + point)
{
    public string Point { get; } = point;
}

public sealed class ParticipantUnavailableException(string message) : Exception(message);

public sealed record SwitchAck(string TxnId, bool AdmittedStopped, int Pinned);

/// The activation tool's view of the web service participant (control channel, interface B06 section 3).
public interface IParticipantLink
{
    /// ENTER_SWITCHING -> ACK_SWITCHING. Throws ParticipantUnavailableException when there is no acknowledgement.
    SwitchAck EnterSwitching(string txnId, long lockEpoch);
    /// OPEN -> ACK_OPEN. Throws ParticipantUnavailableException when lost (the decision stands regardless).
    void Open(string txnId, string knowledge, string models, long exclusionSeq, long lockEpoch);
    /// Generations pinned by in-flight requests, or null when the participant cannot be asked.
    IReadOnlySet<string>? PinnedGenerations(long lockEpoch);
}

public sealed record PreflightResult(long MeasuredRequiredBytes, long FreeBytes, double HeadroomFraction, IReadOnlyList<string> RetainedReleases, bool Pass);

public sealed class ActivationEngineOptions
{
    public required SiteLayout Site { get; init; }
    public required string WriterId { get; init; }
    public required IActivationDatabase Database { get; init; }
    public required ExclusionReader Exclusions { get; init; }
    public IParticipantLink? Participant { get; set; }
    public Func<long> Clock { get; init; } = () => DateTimeOffset.UtcNow.ToUnixTimeSeconds();
    public long StaleAfterSeconds { get; init; } = 30;
    public int KeepPrevious { get; init; } = 2;
    public double HeadroomFraction { get; init; } = 0.1;
    public string? RecoveryTarget { get; init; }
    public IDiskProbe Disk { get; init; } = new DriveDiskProbe();
    public IExternalWriterLock? ExternalLock { get; init; }
    public Action<string>? StepHook { get; set; }
    public Action<string>? Log { get; init; }
}

public sealed class ActivationEngine : IDisposable
{
    readonly ActivationEngineOptions _o;
    readonly SiteLayout _s;
    readonly GenerationCatalog _cat;
    readonly SiteInspector _insp;
    readonly ActivationLog _log;
    public WriterLease Lease { get; }

    public ActivationEngine(ActivationEngineOptions o)
    {
        _o = o; _s = o.Site; _cat = new GenerationCatalog(_s);
        _insp = new SiteInspector(_s, o.Exclusions);
        _log = new ActivationLog(_s.ActivationLogPath);
        Lease = new WriterLease(_s, o.WriterId, o.Clock, o.StaleAfterSeconds, o.ExternalLock);
    }

    public SiteInspector Inspector => _insp;
    public ActivationEngineOptions Options => _o;
    public GenerationCatalog Catalog => _cat;

    void Log(string m) => _o.Log?.Invoke(m);
    void Step(string name) => _o.StepHook?.Invoke(name);

    // ------------------------------------------------------------------ lock
    /// Take the single-writer lock. Returns true when the site must be recovered before any transition.
    public bool AcquireLock() => Lease.Acquire(() => _s.WriteMarker(SiteState.RECOVERING));
    public void ReleaseLock() => Lease.Release();

    JournalState ReadJournal()
    {
        try { return ActivationJournal.Read(_s.JournalPath); }
        catch (JournalCorruptException e) { throw new ActivationRefused("JOURNAL_CORRUPT", e.Message); }
    }

    ExclusionSnapshot HealthyExclusions()
    {
        var snap = _insp.ReadExclusions();
        if (!snap.Healthy) throw new ActivationRefused("EXCLUSIONS_UNAVAILABLE", snap.Health + ": " + snap.Detail);
        return snap;
    }

    static string TxnId(int n, string target, string to) =>
        $"TX-{n:D8}-{Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes($"{target}|{to}|{n}"))).ToLowerInvariant()[..12]}";

    // ------------------------------------------------------------------ preflight and retention
    public PreflightResult Preflight(string target, string to)
    {
        var keep = Protected(_o.Participant?.PinnedGenerations(Lease.Epoch) ?? new HashSet<string>(), ReadJournal());
        if (target == "KNOWLEDGE") keep.Add(to);
        long size = target == "KNOWLEDGE" ? _cat.MeasuredBytes(to) : 0;
        long need = (long)(size * (1 + _o.HeadroomFraction));
        long free = _o.Disk.FreeBytes(_s.Root);
        return new PreflightResult(need, free, _o.HeadroomFraction, keep.Order(StringComparer.Ordinal).ToList(), free >= need);
    }

    /// Previous DISTINCT verified generations, most recent first (rollback history can repeat ids).
    public List<string> PreviousDistinct(JournalState? j = null)
    {
        j ??= ReadJournal();
        var history = new List<string> { _s.ReadInit().knowledge };
        foreach (var t in j.Transactions)
        {
            var b = j.Begin(t);
            if (b.Target == "KNOWLEDGE" && j.Has(t, "DECIDED") && history[^1] != b.To) history.Add(b.To!);
        }
        var active = _s.ReadPointer("KNOWLEDGE");
        var installed = _cat.Installed().ToHashSet(StringComparer.Ordinal);
        var outl = new List<string>();
        for (int i = history.Count - 1; i >= 0; i--)
        {
            var g = history[i];
            if (g != active && !outl.Contains(g) && installed.Contains(g)) outl.Add(g);
        }
        return outl.Take(_o.KeepPrevious).ToList();
    }

    HashSet<string> Protected(IReadOnlySet<string> pinned, JournalState j)
    {
        var p = new HashSet<string>(StringComparer.Ordinal);
        if (_s.ReadPointer("KNOWLEDGE") is { } a) p.Add(a);
        p.UnionWith(PreviousDistinct(j));
        foreach (var t in j.Transactions)
        {
            var b = j.Begin(t);
            if (b.Target == "KNOWLEDGE" && !j.Has(t, "OPEN") && !j.Has(t, "ABORTED")) p.Add(b.To!);
        }
        p.UnionWith(pinned);
        if (_o.RecoveryTarget is { } rt && _cat.Installed().Contains(rt)) p.Add(rt);
        return p;
    }

    /// Retention (D4/D6): runs only while OPEN; keeps the active release, the previous distinct releases, in-flight
    /// targets, pinned generations and the explicit recovery target; never removes the last generation. Refuses to
    /// prune (removes nothing) when the participant's pins cannot be read.
    public List<string> Prune()
    {
        return Lease.Authorised(() =>
        {
            var j = ReadJournal();
            if (_s.ReadMarker() != SiteState.OPEN || j.InFlight is not null) return new List<string>();
            var pinned = _o.Participant is null ? new HashSet<string>() : _o.Participant.PinnedGenerations(Lease.Epoch);
            if (pinned is null) { Log("prune skipped: participant pins unavailable"); return new List<string>(); }
            var keep = Protected(pinned, j);
            var installed = _cat.Installed();
            var removed = installed.Where(g => !keep.Contains(g)).ToList();
            if (installed.Count - removed.Count < 1) return new List<string>();
            foreach (var g in removed) _cat.Remove(g);
            return removed;
        });
    }

    // ------------------------------------------------------------------ transitions
    public string Transition(string target, string to, string action = "ACTIVATE")
    {
        if (target is not ("KNOWLEDGE" or "MODELS")) throw new ActivationRefused("INVALID_TARGET", "target must be KNOWLEDGE or MODELS");
        if (action is not ("ACTIVATE" or "ROLLBACK" or "RESTORE")) throw new ActivationRefused("INVALID_ACTION", "action");
        SiteLayout.CheckId(to);
        if (!Lease.IsHolder()) throw new ActivationRefused("NOT_LOCK_HOLDER", "this writer does not hold the activation lock");
        var j = ReadJournal();
        HealthyExclusions();
        if (_o.Participant is null) throw new ActivationRefused("PARTICIPANT_UNAVAILABLE", "no participant link");
        Lease.Heartbeat();
        if (_s.ReadMarker() != SiteState.OPEN || j.InFlight is not null || j.TornTail)
            throw new ActivationRefused("RECOVERY_REQUIRED", "another transition or recovery is in progress");
        var installed = _cat.Installed();
        if (target == "KNOWLEDGE" && !installed.Contains(to)) throw new ActivationRefused("NOT_STAGED", "target generation is not staged and verified");
        var activeK = _s.ReadPointer("KNOWLEDGE")!;
        if (target == "MODELS")
        {
            var m = _cat.Model(to);
            if (m is null || !m.Verified) throw new ActivationRefused("NOT_STAGED", "target model is not staged and verified");
            if (!m.VectorsFor.Contains(activeK)) throw new ActivationRefused("NO_VECTORS", "target model has no verified vectors for the active knowledge generation");
        }
        else
        {
            var m = _cat.Model(_s.ReadPointer("MODELS")!);
            if (m is null || !m.VectorsFor.Contains(to)) throw new ActivationRefused("NO_VECTORS", "active model has no verified vectors for the target generation");
        }
        if (!Preflight(target, to).Pass) throw new ActivationRefused("PREFLIGHT_FAILED", "measured disk preflight failed");
        var txn = TxnId(j.Transactions.Count() + 1, target, to);
        var from = _s.ReadPointer(target);

        SwitchAck ack;
        try { ack = _o.Participant.EnterSwitching(txn, Lease.Epoch); }
        catch (ParticipantUnavailableException e) { throw new ActivationRefused("PARTICIPANT_UNAVAILABLE", "no ACK_SWITCHING: " + e.Message); }
        if (!ack.AdmittedStopped || ack.TxnId != txn) throw new ActivationRefused("PARTICIPANT_UNAVAILABLE", "participant did not stop admission");

        SiteInspector.Enter(_s.Root);
        try
        {
            try
            {
                Lease.Authorised(() =>
                {
                    _s.WriteMarker(SiteState.SWITCHING);
                    Step("BEGIN:marker");
                    var jj = ActivationJournal.Read(_s.JournalPath);
                    ActivationJournal.Append(_s.JournalPath, jj, txn, "BEGIN", Lease.WriterId, Lease.Epoch, target, from, to, action);
                    Directory.CreateDirectory(Path.Combine(_s.ScratchDir, txn + ".staging"));
                });
            }
            catch (ActivationRefused)
            {
                // Nothing journaled: put the participant back on the (unchanged) head.
                TryOpenParticipant(txn);
                throw;
            }
            Step("BEGIN");
            Lease.Authorised(() => ActivationJournal.Append(_s.JournalPath, ActivationJournal.Read(_s.JournalPath), txn, "DECIDED", Lease.WriterId, Lease.Epoch));
            Step("DECIDED");
            RollForward(txn, "");
            Lease.Authorised(() => _s.WriteMarker(SiteState.OPEN));
        }
        finally { SiteInspector.Exit(_s.Root); }
        TryOpenParticipant(txn);
        Log($"OPEN {txn} {target} -> {to}");
        return txn;
    }

    void TryOpenParticipant(string txn)
    {
        if (_o.Participant is null || _s.ReadMarker() != SiteState.OPEN) return;
        try
        {
            var seq = HealthyExclusions().Sequence ?? 0;
            _o.Participant.Open(txn, _s.ReadPointer("KNOWLEDGE")!, _s.ReadPointer("MODELS")!, seq, Lease.Epoch);
        }
        catch (Exception e) when (e is ParticipantUnavailableException or ActivationRefused)
        {
            Log("participant not reachable at OPEN; it reloads the journal head when it reconnects");
        }
    }

    void RollForward(string txn, string prefix)
    {
        var b = ReadJournal().Begin(txn);
        string target = b.Target!, to = b.To!;

        Lease.Authorised(() => _o.Database.Apply(txn, target, to));
        Step(prefix + "DB_APPLIED");

        Lease.Authorised(() =>
        {
            Directory.CreateDirectory(_s.ScratchDir);
            var tmp = Path.Combine(_s.ScratchDir, txn + ".pointer.tmp");
            using (var f = new FileStream(tmp, FileMode.Create, FileAccess.Write, FileShare.None, 4096, FileOptions.WriteThrough))
            { f.Write(Encoding.UTF8.GetBytes(to)); f.Flush(true); }
            Step(prefix + "POINTER_WRITTEN:inside");
            DurableFile.Replace(tmp, _s.Pointer(target));
            DurableFile.SyncDirectory(_s.Root);
        });
        Step(prefix + "POINTER_WRITTEN");

        Lease.Authorised(() =>
        {
            var snap = HealthyExclusions();
            var ap = _s.ReadApplied();
            ap[_s.ReadPointer("KNOWLEDGE")!] = snap.Sequence!.Value;
            _s.WriteApplied(ap);
        });
        Step(prefix + "EXCLUSIONS_APPLIED");

        Lease.Authorised(() => _log.AppendOnce(txn, target, to, b.Action!, HealthyExclusions().Sequence!.Value));
        Step(prefix + "LOGGED");

        Lease.Authorised(() =>
        {
            // The newest exclusion state, re-read at exposure, is applied to every installed generation.
            var seq = HealthyExclusions().Sequence!.Value;
            var ap = _s.ReadApplied();
            foreach (var g in _cat.Installed()) ap[g] = seq;
            _s.WriteApplied(ap);
            var jj = ActivationJournal.Read(_s.JournalPath);
            if (!jj.Has(txn, "OPEN")) ActivationJournal.Append(_s.JournalPath, jj, txn, "OPEN", Lease.WriterId, Lease.Epoch, exclusionSeq: seq);
            CleanupScratch(txn);
        });
        Step(prefix + "OPEN");
    }

    void CleanupScratch(string? txn)
    {
        if (!Directory.Exists(_s.ScratchDir)) return;
        foreach (var p in Directory.EnumerateFileSystemEntries(_s.ScratchDir))
        {
            if (txn is not null && !Path.GetFileName(p).StartsWith(txn + ".", StringComparison.Ordinal)) continue;
            if (Directory.Exists(p)) Directory.Delete(p, true); else File.Delete(p);
        }
    }

    // ------------------------------------------------------------------ recovery
    /// True when the site is not in a clean OPEN state: marker not OPEN, a transaction in flight, a torn tail, or
    /// pointers that do not follow the journal head.
    public bool NeedsRecovery()
    {
        var j = ReadJournal();
        if (_s.ReadMarker() != SiteState.OPEN || j.InFlight is not null || j.TornTail) return true;
        foreach (var target in new[] { "KNOWLEDGE", "MODELS" })
            if (j.HeadBegin(target) is { } head && _s.ReadPointer(target) != head.To) return true;
        return false;
    }

    public void Recover()
    {
        if (!Lease.IsHolder()) throw new ActivationRefused("NOT_LOCK_HOLDER", "this writer does not hold the activation lock");
        Lease.Authorised(() =>
        {
            var j = ReadJournal();
            _s.WriteMarker(SiteState.RECOVERING);
            ActivationJournal.TruncateTornTail(_s.JournalPath, j);
        });
        HealthyExclusions();
        foreach (var txn in ReadJournal().Transactions.ToList())
        {
            var j = ReadJournal();
            bool decided = j.Has(txn, "DECIDED"), aborted = j.Has(txn, "ABORTED"), open = j.Has(txn, "OPEN");
            if (!decided && !aborted)
            {
                Lease.Authorised(() => ActivationJournal.Append(_s.JournalPath, ActivationJournal.Read(_s.JournalPath), txn, "ABORTED", Lease.WriterId, Lease.Epoch));
                Step("recover:ABORTED");
            }
            else if (decided && !open)
            {
                SiteInspector.Enter(_s.Root);
                try { RollForward(txn, "recover:"); }
                finally { SiteInspector.Exit(_s.Root); }
            }
            Lease.Authorised(() => CleanupScratch(txn));
        }
        Lease.Authorised(() =>
        {
            var j = ReadJournal();
            foreach (var target in new[] { "KNOWLEDGE", "MODELS" })
                if (j.HeadBegin(target) is { } head && _s.ReadPointer(target) != head.To)
                    DurableFile.WriteAtomic(_s.Pointer(target), Encoding.UTF8.GetBytes(head.To!));
            var committed = j.Transactions.Where(t => j.Has(t, "OPEN")).Select(j.Begin)
                .Select(b => new PublicationRow(b.TxnId, b.To!, "RELEASE_ACTIVATION", b.Target!)).ToList();
            _o.Database.Reconcile(_s.ReadPointer("KNOWLEDGE")!, committed);
            var seq = HealthyExclusions().Sequence!.Value;
            var ap = _s.ReadApplied();
            foreach (var g in _cat.Installed()) ap[g] = seq;
            _s.WriteApplied(ap);
            CleanupScratch(null);
            Step("recover:reconciled");
            _s.WriteMarker(SiteState.OPEN);
        });
        TryOpenParticipant("RECOVERY");
        Log("recovery complete");
    }

    // ------------------------------------------------------------------ restore (semantics only; B08 does the media)
    public void Restore(byte[] databaseBackup)
    {
        Lease.Authorised(() =>
        {
            _s.WriteMarker(SiteState.RECOVERING);
            _o.Database.Restore(databaseBackup);
        });
        Recover();
    }

    // ------------------------------------------------------------------ exclusion acceptance
    /// Exclusion acceptance takes the same lock (the journal guard). `writeStore` (the ExclusionStore append, done by
    /// its own writer) runs under the guard; when the site is OPEN the newest state is applied at once to every
    /// installed generation, otherwise it is applied before OPEN by the transition or by recovery.
    public static void AcceptExclusion(SiteLayout site, SiteInspector inspector, Action writeStore, TimeSpan? timeout = null)
    {
        WriterLease.UnderGuard(site, () =>
        {
            writeStore();
            inspector.InvalidateCache();
            if (site.ReadMarker() != SiteState.OPEN) return 0;
            JournalState j;
            try { j = ActivationJournal.Read(site.JournalPath); } catch (JournalCorruptException) { return 0; }
            if (j.InFlight is not null) return 0;
            var snap = inspector.ReadExclusions();
            if (!snap.Healthy) throw new ActivationRefused("EXCLUSIONS_UNAVAILABLE", snap.Health + ": " + snap.Detail);
            var ap = site.ReadApplied();
            foreach (var g in inspector.Catalog.Installed()) ap[g] = snap.Sequence!.Value;
            site.WriteApplied(ap);
            return 0;
        }, timeout);
    }

    public void Dispose() => Lease.Dispose();
}
