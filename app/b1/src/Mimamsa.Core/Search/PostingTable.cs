// C15 WP1: the term -> postings map behind SearchIndex, with two engines (ADR-0006):
//   MemoryPostingTable  - the B1 in-process dictionary (unchanged behaviour);
//   SqlitePostingTable  - postings persisted in a per-generation SQLite file, read on demand through a bounded cache.
// Both expose the same ordered vocabulary (first-occurrence order, which prefix expansion depends on) and identical
// posting lists, so query evaluation and BM25 scores are bit-for-bit the same whichever engine is selected.
namespace Mimamsa.Core.Search;

internal abstract class PostingTable
{
    /// Vocabulary in first-occurrence order (the order the B1 dictionary enumerated its keys).
    public abstract IEnumerable<string> Keys { get; }
    public abstract int Count { get; }
    /// Number of passages containing the term (posting-list length), 0 when absent. Never loads the postings.
    public abstract int Df(string term);
    public abstract bool TryGetValue(string term, out List<SearchIndex.Posting> list);
    public bool ContainsKey(string term) => Df(term) > 0;
    public List<SearchIndex.Posting> this[string term] => TryGetValue(term, out var l) ? l : throw new KeyNotFoundException(term);
    /// (term, df) in vocabulary order, without loading postings.
    public IEnumerable<(string term, int df)> Terms => Keys.Select(k => (k, Df(k)));
}

internal sealed class MemoryPostingTable(Dictionary<string, List<SearchIndex.Posting>> map) : PostingTable
{
    public override IEnumerable<string> Keys => map.Keys;
    public override int Count => map.Count;
    public override int Df(string term) => map.TryGetValue(term, out var l) ? l.Count : 0;
    public override bool TryGetValue(string term, out List<SearchIndex.Posting> list)
    {
        if (map.TryGetValue(term, out var l)) { list = l; return true; }
        list = null!; return false;
    }
}
