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
    internal readonly Dictionary<string, List<Posting>> Postings = new(StringComparer.Ordinal);
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

    public static SearchIndex Build(GenerationStore g)
    {
        var ix = new SearchIndex();
        foreach (var a in g.Abbreviations) ix.Abbrev.TryAdd(a.Code, a);
        // C14 F07 hook (S3): extracted text flagged unreliable (legacy-font Hindi) is not indexed. Indexable() is left
        // unchanged because Eligibility uses it: such documents stay openable, labelled, from Statutes and links.
        foreach (var d in g.Documents.Values.Where(d => Indexable(d) && !d.TextExcludedFromSearch).OrderBy(d => d.DocId, StringComparer.Ordinal))
        {
            int di = ix._docs.Count;
            ix._docs.Add(d);
            ix.TitleTerms.Add(Text.Tokenize(d.Title ?? "").Select(t => t.Term).ToHashSet());
            var ps = new List<int>();
            int army = 0, navy = 0, air = 0;
            foreach (var p in d.Passages.OrderBy(p => p.Page).ThenBy(p => p.CharStart))
            {
                int pi = ix._passages.Count;
                ix._passages.Add(p); ix._passageDoc.Add(di); ps.Add(pi);
                var toks = Text.Tokenize(p.Text);
                ix._passageLen.Add(toks.Count);
                for (int k = 0; k < toks.Count; k++)
                    switch (toks[k].Term)
                    {
                        case "army": army++; break;
                        case "navy" or "naval": navy++; break;
                        case "air" when k + 1 < toks.Count && toks[k + 1].Term == "force": air++; break;
                    }
                foreach (var grp in toks.GroupBy(t => t.Term))
                {
                    if (!ix.Postings.TryGetValue(grp.Key, out var list)) ix.Postings[grp.Key] = list = new();
                    list.Add(new Posting(pi, grp.Select(t => t.Position).ToArray()));
                }
            }
            ix.DocPassages.Add(ps.ToArray());
            ix.GroupKey.Add(Legal.LegalIdentifierResolver.GroupKey(d));
            ix.Service.Add(Legal.LegalIdentifierResolver.ServiceOf(d, army, navy, air));
            void AddId(Dictionary<string, List<int>> table, string? norm) { if (!string.IsNullOrEmpty(norm)) (table.TryGetValue(norm, out var l) ? l : table[norm] = new()).Add(di); }
            if (d.Judicial is { } j)
            {
                foreach (var c in j.CaseNumbers) AddId(ix.MetaIds, Identifiers.NormCase(c) ?? Identifiers.NormCitation(c));
                AddId(ix.MetaIds, j.NeutralCitation is null ? null : Identifiers.NormCitation(j.NeutralCitation));
                foreach (var r in j.ReportedCitations) AddId(ix.MetaIds, Identifiers.NormCitation(r));
            }
            if (d.DocType is "judgment" or "order" && d.Pages.TryGetValue(1, out var p1))
                foreach (var id in Identifiers.CoverCaseNumbers(p1.Text).Concat(Identifiers.MastheadCitations(p1.Text)).Distinct()) AddId(ix.CoverIds, id);
        }
        ix.Resolver = new Legal.LegalIdentifierResolver(ix._docs, ix.TitleTerms);
        foreach (var t in ix.Postings.Keys)
        {
            var s = Text.Stem(t);
            if (!ix.StemGroups.TryGetValue(s, out var set)) ix.StemGroups[s] = set = new(StringComparer.Ordinal);
            set.Add(t);
        }
        ix.AvgLen = ix._passageLen.Count == 0 ? 1 : ix._passageLen.Average();
        return ix;
    }

    public double Idf(int df) => Math.Log(1 + (N - df + 0.5) / (df + 0.5));

    public double TfNorm(int tf, int p) => tf * (K1 + 1) / (tf + K1 * (1 - B + B * LenOf(p) / AvgLen));
}
