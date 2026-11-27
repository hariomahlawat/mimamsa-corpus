// C16 B06 / I-4: the web service as a PARTICIPANT of activation (interface B06 sections 3 and 4).
// - ENTER_SWITCHING: stop admitting new requests (the host answers 503), acknowledge with the pinned count. Pinned
//   in-flight requests finish on their generation.
// - OPEN: re-read the journal head from disk (never trust the message alone), swap services, resume admission.
// - After a restart or reconnect it serves only when the site is OPEN (no in-flight transaction, recovery complete),
//   the exclusion reader is healthy, and its loaded generation equals the journal head.
// - Pins capture {knowledge generation, model generation, exclusion sequence}. Respond filters every response by the
//   CURRENT exclusion state, so an exclusion accepted after the pin is never bypassed.
// - Old generations stay alive while pinned (the host releases its old AppServices when PinCount reaches zero).
namespace Mimamsa.Core.Activation;

public sealed record ReaderPin(long Id, string Knowledge, string Models, long ExclusionSeq);

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
    /// Called with (knowledge, models) when the participant loads a new head; returns false if the swap failed.
    public Func<string, string, bool>? OnSwap { get; set; }
    /// Called with a generation when its last pin is released and it is no longer loaded (close its stores, CG-4).
    public Action<string>? OnGenerationReleased { get; set; }

    public ActivationParticipant(SiteInspector site) { _site = site; }
    public SiteInspector Site => _site;

    /// Start-up or reconnect: load the journal head if (and only if) the site is OPEN.
    public bool LoadHead()
    {
        lock (_gate)
        {
            _switching = false; _switchTxn = null;
            if (_site.State() != SiteState.OPEN) { LoadedKnowledge = null; LoadedModels = null; return false; }
            return LoadFromDisk();
        }
    }

    bool LoadFromDisk()
    {
        var k = _site.Site.ReadPointer("KNOWLEDGE");
        var m = _site.Site.ReadPointer("MODELS");
        if (k is null || m is null) return false;
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
    public bool Open(string txn, string knowledge, string models, long exclusionSeq, long epoch)
    {
        lock (_gate)
        {
            CheckEpoch(epoch);
            _switching = false; _switchTxn = null;
            if (_site.State() != SiteState.OPEN) return false;
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
            return new ReaderPin(++_nextPin, LoadedKnowledge!, LoadedModels!, ex.Sequence!.Value);
        }
    }

    /// Response boundary: filter by the CURRENT exclusion state (never only the state seen at pin time).
    public List<string> Respond(ReaderPin pin, IEnumerable<string> docIds) => Respond(pin, docIds, d => d, _ => null);

    public List<T> Respond<T>(ReaderPin pin, IEnumerable<T> items, Func<T, string> docId, Func<T, string?> sha)
    {
        var ex = _site.ReadExclusions();
        if (!ex.Healthy) throw new ActivationRefused("EXCLUSIONS_UNAVAILABLE", ex.Health + ": " + ex.Detail);
        return items.Where(i => !ex.State!.IsExcluded(docId(i), sha(i))).ToList();
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

    public void Open(string txnId, string knowledge, string models, long exclusionSeq, long lockEpoch)
    {
        if (!Up) throw new ParticipantUnavailableException("participant down");
        Participant.Open(txnId, knowledge, models, exclusionSeq, lockEpoch);
    }

    public IReadOnlySet<string>? PinnedGenerations(long lockEpoch) => Up ? Participant.PinnedGenerations() : null;
}
