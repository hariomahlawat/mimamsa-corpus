// C16 B06: read-only view of a site's activation state, shared by the web participant, the status command and the
// conformance harness. Never writes anything except the exclusion reader's site-local high-water mark.
namespace Mimamsa.Core.Activation;

public sealed class SiteInspector
{
    public SiteLayout Site { get; }
    public GenerationCatalog Catalog { get; }
    public ExclusionReader Exclusions { get; }

    public SiteInspector(SiteLayout site, ExclusionReader exclusions)
    {
        Site = site; Catalog = new GenerationCatalog(site); Exclusions = exclusions;
    }

    /// Per site root: set while an engine in this process executes a transition (observability only: SWITCHING
    /// versus RECOVERING; both refuse service).
    static readonly System.Collections.Concurrent.ConcurrentDictionary<string, int> InProgress = new(StringComparer.OrdinalIgnoreCase);
    internal static void Enter(string root) => InProgress.AddOrUpdate(root, 1, (_, n) => n + 1);
    internal static void Exit(string root) => InProgress.AddOrUpdate(root, 0, (_, n) => Math.Max(0, n - 1));

    long _jLen = -1; DateTime _jTime; JournalState? _jCache;

    /// The verified journal (cached by file length and write time). Throws JournalCorruptException.
    public JournalState Journal()
    {
        var fi = new FileInfo(Site.JournalPath);
        long len = fi.Exists ? fi.Length : 0;
        var t = fi.Exists ? fi.LastWriteTimeUtc : DateTime.MinValue;
        lock (this)
        {
            if (_jCache is not null && len == _jLen && t == _jTime) return _jCache;
            var j = ActivationJournal.Read(Site.JournalPath);
            _jCache = j; _jLen = len; _jTime = t;
            return j;
        }
    }

    public void InvalidateCache() { lock (this) _jCache = null; }

    public SiteState State()
    {
        JournalState j;
        try { j = Journal(); }
        catch (JournalCorruptException) { return SiteState.FAILED_CLOSED; }
        var m = Site.ReadMarker();
        if (m == SiteState.OPEN && j.InFlight is null && !j.TornTail) return SiteState.OPEN;
        return InProgress.GetValueOrDefault(Site.Root) > 0 && m == SiteState.SWITCHING ? SiteState.SWITCHING : SiteState.RECOVERING;
    }

    /// Highest exclusion sequence the site has recorded (applied to a generation or written in an OPEN record).
    public long RecordedExclusionSeq()
    {
        long a = 0;
        try { var ap = Site.ReadApplied(); if (ap.Count > 0) a = ap.Values.Max(); } catch (Exception) { a = long.MaxValue; }
        long o = 0;
        try { o = Journal().LastOpenExclusionSeq; } catch (JournalCorruptException) { }
        return Math.Max(a, o);
    }

    public ExclusionSnapshot ReadExclusions() => Exclusions.Read(RecordedExclusionSeq());
}
