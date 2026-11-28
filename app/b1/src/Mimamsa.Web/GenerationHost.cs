// C16 Tranche B Stage 3 (S3-D): in-process generation swap for the activation participant (B06 sections 3 and 4).
//
// The web process used to fail closed after OPEN until it was restarted. With activation enabled it now keeps the
// services of each knowledge generation it serves in a GenerationSlot (generation store, disk text store, disk index,
// graph, eligibility, search, boundary) and swaps between slots in process:
//
//   PREPARE (before ENTER_SWITCHING, nothing journaled)  the target's slot is loaded and verified BESIDE the serving
//            one, while the old generation keeps serving. A failure, or a residency budget that would be exceeded,
//            refuses the transition: the old generation keeps serving and nothing changes (ActivationEngine).
//   OPEN     the participant re-reads the journal head from disk and, under its lock, Switch()es: one reference
//            assignment, so every request admitted afterwards gets the new slot. A request is pinned to exactly the
//            slot of its participant pin (Acquire), so no request ever mixes generations.
//   release  a slot that is no longer current is released when its last request lease goes (disk text store
//            connections closed, index connections and cache dropped, every reference dropped for the GC).
//
// Memory is bounded: never more than MaxResident (2) slots are resident or loading. When a third would be needed (an
// old slot is still leased by long requests), Prepare waits up to BudgetWait for it to drain and then refuses.
// Bounded memory REQUIRES the disk text store and the disk index in activation mode (Program refuses to start
// otherwise): with the memory engines each resident generation would hold all page text and all postings.
//
// Failure paths fail closed: a load that throws leaves no slot; an OPEN onto a generation that is not resident loads
// it outside the participant lock while nothing is admitted (the participant is not on the journal head); a lease
// that cannot be taken (the slot was released between pin and lease) is answered 503.
using System.Diagnostics;

namespace Mimamsa.Web;

/// One knowledge generation's services. Services and Boundary are null only in unit tests of the host itself.
public sealed class GenerationSlot
{
    public required string Id { get; init; }
    public AppServices? Services { get; init; }
    public ActivationBoundary? Boundary { get; init; }
    /// Releases the slot's resources (closes the disk text store, releases the disk index). Called once.
    public Action? OnRelease { get; init; }
    /// Anything the slot keeps alive (unit tests read a WeakReference of it to prove release).
    public object? Payload { get; init; }
    internal int Leases;
    internal int ReleasedFlag;
    public bool Released => Volatile.Read(ref ReleasedFlag) == 1;
    public long LoadMs { get; set; }
}

public sealed class GenerationHost
{
    public const string SlotKey = "mimamsa.activation.slot";
    readonly Func<string, GenerationSlot> _load;
    readonly object _gate = new();
    readonly Dictionary<string, GenerationSlot> _resident = new(StringComparer.Ordinal);
    readonly HashSet<string> _loading = new(StringComparer.Ordinal);
    GenerationSlot? _current;
    string? _prepared;   // the most recent prepared target: kept until a switch decides (never trimmed before)

    public int MaxResident { get; init; } = 2;
    public TimeSpan BudgetWait { get; init; } = TimeSpan.FromSeconds(30);
    public Action<string>? Log { get; init; }
    long _loads, _releases, _refusals, _loadFailures;

    public GenerationHost(Func<string, GenerationSlot> load) { _load = load; }

    public GenerationSlot? Current => Volatile.Read(ref _current);
    public long Loads => Interlocked.Read(ref _loads);
    public long Releases => Interlocked.Read(ref _releases);
    public long BudgetRefusals => Interlocked.Read(ref _refusals);
    public long LoadFailures => Interlocked.Read(ref _loadFailures);
    public IReadOnlyList<string> Resident { get { lock (_gate) return _resident.Keys.Order(StringComparer.Ordinal).ToList(); } }
    public int ResidentCount { get { lock (_gate) return _resident.Count + _loading.Count; } }

    /// Coordinate with the B06 participant: PREPARE loads beside the serving slot, OPEN switches.
    public void AttachTo(Mimamsa.Core.Activation.ActivationParticipant p)
    {
        p.OnPrepare = (k, _) => Prepare(k);
        p.OnSwap = (k, _) => Switch(k);
    }

    /// Start-up: the slot the process loaded first becomes current.
    public void Install(GenerationSlot s)
    {
        lock (_gate) { _resident[s.Id] = s; Volatile.Write(ref _current, s); }
    }

    /// Load and verify `id` beside the serving slot (no-op when resident). Runs OUTSIDE the participant lock. False
    /// when the load or verification failed, or the residency budget stayed exhausted for BudgetWait.
    public bool Prepare(string id)
    {
        var sw = Stopwatch.StartNew();
        while (true)
        {
            lock (_gate)
            {
                if (_resident.ContainsKey(id)) { _prepared = id; return true; }
                if (!_loading.Contains(id))
                {
                    TrimLocked();
                    if (_resident.Count + _loading.Count < MaxResident) { _loading.Add(id); break; }
                }
            }
            if (sw.Elapsed > BudgetWait)
            {
                Interlocked.Increment(ref _refusals);
                Log?.Invoke($"generation swap: residency budget ({MaxResident}) exhausted for {BudgetWait.TotalSeconds:0}s; target refused");
                return false;
            }
            Thread.Sleep(25);
        }
        GenerationSlot? s = null;
        try
        {
            s = _load(id);
            if (s.Id != id) throw new InvalidOperationException("loader returned another generation");
            s.LoadMs = sw.ElapsedMilliseconds;
        }
        catch (Exception e)
        {
            Interlocked.Increment(ref _loadFailures);
            Log?.Invoke($"generation swap: target failed to load or verify ({e.GetType().Name}); the serving generation is unchanged");
            s = null;
        }
        finally
        {
            lock (_gate)
            {
                _loading.Remove(id);
                if (s is not null) { _resident[id] = s; _prepared = id; }
            }
        }
        if (s is null) return false;
        Interlocked.Increment(ref _loads);
        Log?.Invoke($"generation swap: target loaded and verified beside the serving generation ({s.LoadMs} ms; resident {ResidentCount})");
        return true;
    }

    /// OPEN (under the participant lock): make `id` current. One reference assignment; no I/O.
    public bool Switch(string id)
    {
        lock (_gate)
        {
            if (!_resident.TryGetValue(id, out var s) || s.Released) return false;
            Volatile.Write(ref _current, s);
            _prepared = null;
            TrimLocked();
            return true;
        }
    }

    /// A request's lease on exactly its pinned generation (null: not resident, answered 503).
    public GenerationSlot? Acquire(string id)
    {
        lock (_gate)
        {
            if (!_resident.TryGetValue(id, out var s) || s.Released) return null;
            s.Leases++;
            return s;
        }
    }

    public void ReleaseLease(GenerationSlot s)
    {
        lock (_gate)
        {
            s.Leases--;
            if (s.Leases == 0 && !ReferenceEquals(s, _current)) TrimLocked();
        }
    }

    /// Release every slot that is neither current nor the pending prepared target and has no lease.
    void TrimLocked()
    {
        foreach (var (id, s) in _resident.ToList())
        {
            if (ReferenceEquals(s, _current) || id == _prepared || s.Leases > 0) continue;
            _resident.Remove(id);
            if (Interlocked.Exchange(ref s.ReleasedFlag, 1) == 1) continue;
            try { s.OnRelease?.Invoke(); } catch (Exception e) { Log?.Invoke("generation swap: release error " + e.GetType().Name); }
            Interlocked.Increment(ref _releases);
            Log?.Invoke($"generation swap: previous generation released (last lease gone; resident {_resident.Count + _loading.Count})");
        }
    }
}
