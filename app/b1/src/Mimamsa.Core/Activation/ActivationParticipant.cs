// C16 B06 / I-4: the web service as a PARTICIPANT of activation (interface B06 sections 3 and 4).
// - ENTER_SWITCHING: stop admitting new requests (the host answers 503), acknowledge with the pinned count. Pinned
//   in-flight requests finish on their generation.
// - PREPARE (C16 Stage 3, 2.1 additive, before ENTER_SWITCHING): load and verify the target generation's services
//   beside the serving ones (OnPrepare), outside the lock, while the old generation keeps serving. A refusal makes
//   the tool refuse the transition before anything is journaled.
// - OPEN: re-read the journal head from disk (never trust the message alone), swap services, resume admission.
// - After a restart or reconnect it serves only when the site is OPEN (no in-flight transaction, recovery complete),
//   the exclusion reader is healthy, and its loaded generation equals the journal head.
// - Pins capture {knowledge generation, model generation, exclusion sequence}. Respond filters every response by the
//   CURRENT exclusion state, so an exclusion accepted after the pin is never bypassed.
// - Old generations stay alive while pinned (the host releases its old AppServices when PinCount reaches zero).
namespace Mimamsa.Core.Activation;

/// A request's pin. Models is null when no model is installed (2.1). SemanticSearch is fixed for the request:
/// false (lexical-only knowledge, no model, or a model without verified vectors) means the semantic path, including
/// query embedding, must not run.
public sealed record ReaderPin(long Id, string Knowledge, string? Models, long ExclusionSeq, bool SemanticSearch = false);

public sealed class ActivationParticipant
{
    readonly SiteInspector _site;
    readonly object _gate = new();
    readonly Dictionary<string, int> _pins = new(StringComparer.Ordinal);
    long _nextPin;
    long _maxEpoch;
    bool _switching;
    string? _switchTxn;

    public string? LoadedKnowledge { get; private set; }
    public string? LoadedModels { get; private set; }
    /// Called with (knowledge, models) when the participant loads a new head; returns false if the swap failed. Runs
    /// under the participant's lock, so it must be fast: with OnPrepare set it only switches to services that
    /// OnPrepare has already loaded and verified (C16 Stage 3, in-process generation swap).
    public Func<string, string?, bool>? OnSwap { get; set; }
    /// Called with a generation when its last pin is released and it is no longer loaded (close its stores, CG-4).
    public Action<string>? OnGenerationReleased { get; set; }
    /// C16 Stage 3 (in-process swap, 2.1 additive): load and verify the services of (knowledge, models) BESIDE the ones
    /// serving now, without stopping admission. Called OUTSIDE the participant's lock (loading can take long, and the
    /// old generation keeps serving meanwhile). Returns false when the services cannot be loaded or verified, or when
    /// the residency budget would be exceeded; the activation tool then refuses the transition before BEGIN, so the
    /// old generation keeps serving. Null (the default and the conformance harness) means nothing to load: true.
    public Func<string, string?, bool>? OnPrepare { get; set; }

    public ActivationParticipant(SiteInspector site) { _site = site; }
    public SiteInspector Site => _site;

    /// Start-up or reconnect: load the journal head if (and only if) the site is OPEN.
    public bool LoadHead()
    {
        string? k, m;
        lock (_gate)
        {
            _switching = false; _switchTxn = null;
            if (_site.State() != SiteState.OPEN) { LoadedKnowledge = null; LoadedModels = null; return false; }
            k = _site.Site.ReadPointer("KNOWLEDGE"); m = _site.Site.ReadPointer("MODELS");
            if (k is null) return false;
        }
        if (!EnsurePrepared(k, m)) { lock (_gate) { LoadedKnowledge = null; LoadedModels = null; } return false; }
        lock (_gate)
        {
            if (_switching || _site.State() != SiteState.OPEN || _site.Site.ReadPointer("KNOWLEDGE") != k || _site.Site.ReadPointer("MODELS") != m) return false;
            return LoadFromDisk();
        }
    }

    /// Outside the lock: make sure the services of (k, m) are resident (no-op without OnPrepare).
    bool EnsurePrepared(string k, string? m)
    {
        if (OnPrepare is null) return true;
        try { return OnPrepare(k, m); }
        catch (Exception) { return false; }   // fail closed
    }

    /// PREPARE from the activation tool (before ENTER_SWITCHING; nothing is journaled yet): load and verify the
    /// target's services beside the serving ones while the current generation keeps serving.
    public PrepareAck Prepare(string txn, string target, string to, long epoch)
    {
        string k; string? m;
        lock (_gate)
        {
            CheckEpoch(epoch);
            if (target is not ("KNOWLEDGE" or "MODELS")) return new PrepareAck(txn, false, "INVALID_TARGET");
            k = target == "KNOWLEDGE" ? to : (LoadedKnowledge ?? _site.Site.ReadPointer("KNOWLEDGE") ?? "");
            m = target == "MODELS" ? to : (LoadedKnowledge is not null ? LoadedModels : _site.Site.ReadPointer("MODELS"));
            if (k.Length == 0) return new PrepareAck(txn, false, "NO_KNOWLEDGE");
        }
        return EnsurePrepared(k, m) ? new PrepareAck(txn, true, null) : new PrepareAck(txn, false, "PREPARE_FAILED");
    }

    /// Pins currently held on one generation (the host releases a generation's services only at zero).
    public int PinsOf(string generation) { lock (_gate) return _pins.GetValueOrDefault(generation); }

    bool LoadFromDisk()
    {
        var k = _site.Site.ReadPointer("KNOWLEDGE");
        var m = _site.Site.ReadPointer("MODELS");
        if (k is null) return false;   // MODELS may be null (2.1: no model installed)
        if (OnSwap is not null && !OnSwap(k, m)) { LoadedKnowledge = null; LoadedModels = null; return false; }
        var old = LoadedKnowledge;
        LoadedKnowledge = k; LoadedModels = m;
        if (old is not null && old != k && _pins.GetValueOrDefault(old) == 0) OnGenerationReleased?.Invoke(old);
        return true;
    }

    void CheckEpoch(long epoch)
    {
        if (epoch < _maxEpoch) throw new ActivationRefused("STALE_EPOCH", "control message from a lower lock epoch");
        if (epoch != WriterLease.CurrentEpoch(_site.Site)) throw new ActivationRefused("STALE_EPOCH", "control message epoch is not the lock record's epoch");
        _maxEpoch = epoch;
    }

    public SwitchAck EnterSwitching(string txn, long epoch)
    {
        lock (_gate)
        {
            CheckEpoch(epoch);
            _switching = true; _switchTxn = txn;
            return new SwitchAck(txn, true, _pins.Values.Sum());
        }
    }

    /// OPEN from the activation tool: reload the head from disk; serving resumes only if the disk agrees.
    public bool Open(string txn, string knowledge, string? models, long exclusionSeq, long epoch)
    {
        lock (_gate)
        {
            CheckEpoch(epoch);
            _switching = false; _switchTxn = null;
            if (_site.State() != SiteState.OPEN) return false;
            if (_site.Site.ReadPointer("KNOWLEDGE") != knowledge || _site.Site.ReadPointer("MODELS") != models) return false;
            // Already prepared (the normal path, or no OnPrepare): switch now, atomically under the lock.
            if (OnPrepare is null) return LoadFromDisk();
        }
        // Not necessarily resident (restart, recovery roll-forward, rollback to a released generation): load OUTSIDE
        // the lock. Meanwhile LoadedKnowledge differs from the head, so nothing is admitted (fail closed, 503).
        if (!EnsurePrepared(knowledge, models)) { lock (_gate) { LoadedKnowledge = null; LoadedModels = null; } return false; }
        lock (_gate)
        {
            if (_switching || _site.State() != SiteState.OPEN) return false;
            if (_site.Site.ReadPointer("KNOWLEDGE") != knowledge || _site.Site.ReadPointer("MODELS") != models) return false;
            return LoadFromDisk();
        }
    }

    /// The control channel to the tool was lost: admission state is re-derived from disk (the site marker and the
    /// journal decide; a switch in progress keeps the site non-OPEN, so nothing is served until recovery).
    public void ChannelLost()
    {
        lock (_gate)
        {
            if (!_switching) return;
            _switching = false; _switchTxn = null;
        }
    }

    public bool Switching { get { lock (_gate) return _switching; } }

    public bool IsServing(out string reason)
    {
        lock (_gate)
        {
            if (_switching) { reason = "SWITCHING"; return false; }
            var st = _site.State();
            if (st != SiteState.OPEN) { reason = st.ToString(); return false; }
            var ex = _site.ReadExclusions();
            if (!ex.Healthy) { reason = "EXCLUSIONS_" + ex.Health; return false; }
            if (LoadedKnowledge is null || LoadedKnowledge != _site.Site.ReadPointer("KNOWLEDGE") || LoadedModels != _site.Site.ReadPointer("MODELS"))
            { reason = "NOT_ON_JOURNAL_HEAD"; return false; }
            reason = "OK";
            return true;
        }
    }

    public bool IsServing() => IsServing(out _);

    /// 2.1: semantic search is available only while serving and when SiteInspector.SemanticSearchEnabled holds.
    public bool SemanticSearchAvailable() { lock (_gate) return IsServing(out _) && _site.SemanticSearchEnabled(LoadedKnowledge, LoadedModels); }

    public ReaderPin Pin()
    {
        lock (_gate)
        {
            if (!IsServing(out var why)) throw new ActivationRefused("NOT_SERVING", why);
            var ex = _site.ReadExclusions();
            var applied = _site.Site.ReadApplied();
            if (!ex.Healthy || applied.GetValueOrDefault(LoadedKnowledge!, -1) != ex.Sequence)
                throw new ActivationRefused("NOT_SERVING", "exclusions not applied to the active generation");
            _pins[LoadedKnowledge!] = _pins.GetValueOrDefault(LoadedKnowledge!) + 1;
            return new ReaderPin(++_nextPin, LoadedKnowledge!, LoadedModels, ex.Sequence!.Value, _site.SemanticSearchEnabled(LoadedKnowledge, LoadedModels));
        }
    }

    /// Response boundary: filter by the CURRENT exclusion state (never only the state seen at pin time).
    public List<string> Respond(ReaderPin pin, IEnumerable<string> docIds) => Respond(pin, docIds, d => d, _ => null);

    public List<T> Respond<T>(ReaderPin pin, IEnumerable<T> items, Func<T, string> docId, Func<T, string?> sha)
    {
        var state = CurrentExclusions();
        return items.Where(i => !state.IsExcluded(docId(i), sha(i))).ToList();
    }

    /// The CURRENT signed exclusion state (re-read now); throws when it cannot be read (fail closed).
    public EffectiveExclusions CurrentExclusions()
    {
        var ex = _site.ReadExclusions();
        if (!ex.Healthy) throw new ActivationRefused("EXCLUSIONS_UNAVAILABLE", ex.Health + ": " + ex.Detail);
        return ex.State!;
    }

    public void Unpin(ReaderPin pin)
    {
        lock (_gate)
        {
            var n = _pins.GetValueOrDefault(pin.Knowledge) - 1;
            if (n <= 0) { _pins.Remove(pin.Knowledge); if (pin.Knowledge != LoadedKnowledge) OnGenerationReleased?.Invoke(pin.Knowledge); }
            else _pins[pin.Knowledge] = n;
        }
    }

    public int PinCount { get { lock (_gate) return _pins.Values.Sum(); } }
    public IReadOnlySet<string> PinnedGenerations() { lock (_gate) return _pins.Where(kv => kv.Value > 0).Select(kv => kv.Key).ToHashSet(StringComparer.Ordinal); }
}

/// In-process link (conformance harness and single-process tests). `Up = false` models a lost web process.
public sealed class DirectParticipantLink(ActivationParticipant participant) : IParticipantLink
{
    public bool Up { get; set; } = true;
    public ActivationParticipant Participant { get; } = participant;

    public SwitchAck EnterSwitching(string txnId, long lockEpoch)
    {
        if (!Up) throw new ParticipantUnavailableException("participant down");
        return Participant.EnterSwitching(txnId, lockEpoch);
    }

    public PrepareAck Prepare(string txnId, string target, string to, long lockEpoch)
    {
        if (!Up) throw new ParticipantUnavailableException("participant down");
        return Participant.Prepare(txnId, target, to, lockEpoch);
    }

    public void Open(string txnId, string knowledge, string? models, long exclusionSeq, long lockEpoch)
    {
        if (!Up) throw new ParticipantUnavailableException("participant down");
        Participant.Open(txnId, knowledge, models, exclusionSeq, lockEpoch);
    }

    public IReadOnlySet<string>? PinnedGenerations(long lockEpoch) => Up ? Participant.PinnedGenerations() : null;
}
