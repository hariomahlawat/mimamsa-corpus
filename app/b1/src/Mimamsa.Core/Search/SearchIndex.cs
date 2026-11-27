// In-process positional BM25 index over verified passages of the active generation (P2 configuration:
// BM25 + abbreviation expansion + exact-identifier layer). Built once per generation at start-up. P2 measured this
// configuration with Tantivy; this is an own C# implementation of the same method (no Tantivy binding), so P2's
// figures are NOT evidence for this implementation (see docs/architecture/b1/B1_PROTOTYPE.md).
using Mimamsa.Core.Generation;

namespace Mimamsa.Core.Search;

public sealed class SearchIndex
{
    public const double K1 = 1.2, B = 0.75;
    internal readonly record struct Posting(int P, int[] Pos);

    public IReadOnlyList<Passage> Passages => _passages;
    public IReadOnlyList<DocumentRecord> Docs => _docs;
    readonly List<Passage> _passages = new();
    readonly List<DocumentRecord> _docs = new();
    readonly List<int> _passageDoc = new();
    readonly List<int> _passageLen = new();
    /// C15 WP1: memory or SQLite engine (PostingTable); identical vocabulary order and posting lists either way.
    internal PostingTable Postings { get; private set; } = null!;
    /// "memory" or "disk" (for the run line and diagnostics).
    public string Engine { get; private set; } = "memory";
    /// Disk engine only: the published index directory in use (null for memory).
    public string? IndexPath { get; private set; }
    internal readonly Dictionary<string, HashSet<string>> StemGroups = new(StringComparer.Ordinal);
    internal readonly Dictionary<string, List<int>> MetaIds = new(StringComparer.Ordinal);
    internal readonly Dictionary<string, List<int>> CoverIds = new(StringComparer.Ordinal);
    internal readonly List<HashSet<string>> TitleTerms = new();
    internal readonly List<int[]> DocPassages = new();
    /// C14: display/ranking properties per document (see Legal.LegalIdentifierResolver).
    public readonly List<string> GroupKey = new();
    public readonly List<string?> Service = new();
    public Legal.LegalIdentifierResolver Resolver { get; private set; } = null!;
    public double AvgLen { get; private set; }
    public int N => _passages.Count;
    public Dictionary<string, Abbreviation> Abbrev { get; } = new(StringComparer.Ordinal);

    public int DocOf(int p) => _passageDoc[p];
    public int LenOf(int p) => _passageLen[p];

    public static bool Indexable(DocumentRecord d) =>
        d.Publication == "PUBLISHED" && d.OriginalVerified && d.DerivativeId is not null && d.Passages.Count > 0;

    /// Documents the index covers, in index order. C14 F07 hook (S3): extracted text flagged unreliable (legacy-font
    /// Hindi) is not indexed. Indexable() is left unchanged because Eligibility uses it: such documents stay openable.
    internal static List<DocumentRecord> IndexedDocuments(GenerationStore g) =>
        g.Documents.Values.Where(d => Indexable(d) && !d.TextExcludedFromSearch).OrderBy(d => d.DocId, StringComparer.Ordinal).ToList();

    internal static IEnumerable<Passage> OrderedPassages(DocumentRecord d) => d.Passages.OrderBy(p => p.Page).ThenBy(p => p.CharStart);

    /// In-memory engine (B1 behaviour).
    public static SearchIndex Build(GenerationStore g)
    {
        var ix = new SearchIndex();
        ix.Postings = new MemoryPostingTable(BuildPostings(g, ix));
        ix.Finish();
        return ix;
    }

    /// Tokens of one passage as the index uses them: length, term groups in first-occurrence order with ascending
    /// positions, and the service-word counts. C15 WP1: cacheable per derivative (ForwardCache) for incremental builds.
    internal sealed record PassageTokens(int Len, (string Term, int[] Pos)[] Groups, int Army, int Navy, int Air);

    internal static PassageTokens Tokenise(Passage p)
    {
        var toks = Text.Tokenize(p.Text);
        int army = 0, navy = 0, air = 0;
        for (int k = 0; k < toks.Count; k++)
            switch (toks[k].Term)
            {
                case "army": army++; break;
                case "navy" or "naval": navy++; break;
                case "air" when k + 1 < toks.Count && toks[k + 1].Term == "force": air++; break;
            }
        return new PassageTokens(toks.Count, toks.GroupBy(t => t.Term).Select(g => (g.Key, g.Select(t => t.Position).ToArray())).ToArray(), army, navy, air);
    }

    /// Fills passages, lengths and document metadata and returns the postings map. `tokens` supplies each document's
    /// passage tokens (default: tokenise now); the result is identical whichever source supplies them.
    internal static Dictionary<string, List<Posting>> BuildPostings(GenerationStore g, SearchIndex ix,
        Func<DocumentRecord, IReadOnlyList<Passage>, PassageTokens[]>? tokens = null)
    {
        tokens ??= (_, ps) => ps.Select(Tokenise).ToArray();
        var postings = new Dictionary<string, List<Posting>>(StringComparer.Ordinal);
        foreach (var a in g.Abbreviations) ix.Abbrev.TryAdd(a.Code, a);
        foreach (var d in IndexedDocuments(g))
        {
            int di = ix._docs.Count;
            int army = 0, navy = 0, air = 0;
            var ordered = OrderedPassages(d).ToList();
            var tk = tokens(d, ordered);
            var ps = new int[ordered.Count];
            for (int k = 0; k < ordered.Count; k++)
            {
                int pi = ix._passages.Count;
                ix._passages.Add(ordered[k]); ix._passageDoc.Add(di); ps[k] = pi;
                var t = tk[k];
                ix._passageLen.Add(t.Len);
                army += t.Army; navy += t.Navy; air += t.Air;
                foreach (var (term, pos) in t.Groups)
                {
                    if (!postings.TryGetValue(term, out var list)) postings[term] = list = new();
                    list.Add(new Posting(pi, pos));
                }
            }
            ix.AddDocument(d, ps, Legal.LegalIdentifierResolver.ServiceOf(d, army, navy, air));
        }
        return postings;
    }

    /// Per-document metadata that needs no tokenisation of passage text (titles, identifiers, cover numbers).
    internal void AddDocument(DocumentRecord d, int[] passageIndexes, string? service)
    {
        int di = _docs.Count;
        _docs.Add(d);
        TitleTerms.Add(Text.Tokenize(d.Title ?? "").Select(t => t.Term).ToHashSet());
        DocPassages.Add(passageIndexes);
        GroupKey.Add(Legal.LegalIdentifierResolver.GroupKey(d));
        Service.Add(service);
        void AddId(Dictionary<string, List<int>> table, string? norm) { if (!string.IsNullOrEmpty(norm)) (table.TryGetValue(norm, out var l) ? l : table[norm] = new()).Add(di); }
        if (d.Judicial is { } j)
        {
            foreach (var c in j.CaseNumbers) AddId(MetaIds, Identifiers.NormCase(c) ?? Identifiers.NormCitation(c));
            AddId(MetaIds, j.NeutralCitation is null ? null : Identifiers.NormCitation(j.NeutralCitation));
            foreach (var r in j.ReportedCitations) AddId(MetaIds, Identifiers.NormCitation(r));
        }
        if (d.DocType is "judgment" or "order" && d.Pages.TryGetValue(1, out var p1))
            foreach (var id in Identifiers.CoverCaseNumbers(p1.Text).Concat(Identifiers.MastheadCitations(p1.Text)).Distinct()) AddId(CoverIds, id);
    }

    internal void AddPassage(Passage p, int doc, int len) { _passages.Add(p); _passageDoc.Add(doc); _passageLen.Add(len); }

    void Finish()
    {
        Resolver = new Legal.LegalIdentifierResolver(_docs, TitleTerms);
        foreach (var t in Postings.Keys)
        {
            var s = Text.Stem(t);
            if (!StemGroups.TryGetValue(s, out var set)) StemGroups[s] = set = new(StringComparer.Ordinal);
            set.Add(t);
        }
        AvgLen = _passageLen.Count == 0 ? 1 : _passageLen.Average();
    }

    /// Disk engine (C15 WP1, ADR-0006): opens the verified published index of this generation under `root`, or builds,
    /// verifies and atomically publishes one first. Postings are then read on demand; nothing is served from an index
    /// that failed verification.
    public static SearchIndex Open(GenerationStore g, string root, SearchIndexOptions options, Action<string>? log = null)
    {
        var store = new IndexStore(root, options, log);
        var ix = new SearchIndex { Engine = "disk" };
        var path = store.OpenOrBuild(g, ix);
        ix.IndexPath = path;
        ix.Postings = SqlitePostingTable.Open(Path.Combine(path, IndexStore.DbFile), options.CacheBytes);
        ix.Finish();
        return ix;
    }


    public double Idf(int df) => Math.Log(1 + (N - df + 0.5) / (df + 0.5));

    public double TfNorm(int tf, int p) => tf * (K1 + 1) / (tf + K1 * (1 - B + B * LenOf(p) / AvgLen));
}
