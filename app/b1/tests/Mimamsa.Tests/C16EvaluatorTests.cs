using Mimamsa.Core.Search;

namespace Mimamsa.Tests;

/// C16 WP05: the array-based evaluator keeps the B1 result contract. Full byte-for-byte parity against the C15
/// evaluator is proven by IndexBench --parity (app/b1/evidence/c16_evaluator); these tests pin the invariants that
/// parity depends on, so a later change cannot silently break them.
public class C16EvaluatorTests
{
    static readonly SearchIndex Ix = SearchIndex.Build(Syn.Gen);

    static readonly string[] Queries = { "notice", "notice hearing", "s.17 Bracken Service Act", "OA 411/2021", "hearing written notice allegation",
        "exact:\"summary of evidence\"", "summary AND evidence", "\"written notice\" NEAR/5 hearing", "(notice OR hearing) NEAR/3 written",
        "hear*", "title:bracken", "Vale v Lark", "hearnig", "notice AND NOT hearing", "NOT notice", "section:17", "act:\"Bracken Service Act\"",
        "notice OR hearing OR notice", "zzqxv" };

    static List<string> Sig(SearchResult r) => r.Hits.Select(h => $"{h.PassageIndex}:{h.Tier}:{h.Score:R}:{string.Join("|", h.Reasons)}")
        .Concat(r.Chips.Select(c => $"chip:{c.Kind}:{c.Text}"))
        .Concat(r.Facets.Select(f => $"facet:{f.Key}:{string.Join(",", f.Value.Select(v => $"{v.Value}={v.Count}"))}"))
        .Append($"{r.State}/{r.Mode}/{r.TotalDocuments}/{r.TotalPassages}/{string.Join(",", r.HighlightTerms)}").ToList();

    [Fact]
    public void RankedHitsAreOrderedByScoreThenPassage()
    {
        var svc = new SearchService(Ix, _ => false);
        foreach (var q in Queries)
        {
            var lex = svc.Search(q, new SearchFilters()).Hits.SkipWhile(h => h.Tier != "lexical").ToList();
            for (int i = 1; i < lex.Count; i++)
                Assert.True(lex[i - 1].Score > lex[i].Score || (lex[i - 1].Score == lex[i].Score && lex[i - 1].PassageIndex < lex[i].PassageIndex),
                    $"{q}: hit {i} out of order");
        }
    }

    [Fact]
    public void AHitIsTheSameObjectEveryTimeItIsReadAndPagesCarryThoseObjects()
    {
        var svc = new SearchService(Ix, _ => false);
        var r = svc.Search("notice", new SearchFilters());
        Assert.True(r.Hits.Count > 3);
        Assert.Same(r.Hits[2], r.Hits[2]);
        Assert.Equal(r.Hits.Count, r.Hits.Count());
        Assert.Equal(Enumerable.Range(0, r.Hits.Count).Select(i => r.Hits[i]), r.Hits);
        var page = svc.Page(r, 1, 25, null);
        Assert.All(page.Hits, h => Assert.Contains(r.Hits, x => ReferenceEquals(x, h)));
        Assert.Throws<ArgumentOutOfRangeException>(() => r.Hits[r.Hits.Count]);
    }

    [Fact]
    public void AWordRepeatedInTheQueryHasItsMatchCountsSummedInTheReason()
    {
        // the C15 dictionary added the counts of every clause that noted the same display; the segments must too
        var svc = new SearchService(Ix, _ => false);
        var once = svc.Search("notice", new SearchFilters()).Hits.First(h => h.Tier == "lexical");
        var twice = svc.Search("notice notice", new SearchFilters()).Hits.First(h => h.PassageIndex == once.PassageIndex);
        int Count(Hit h) => int.Parse(System.Text.RegularExpressions.Regex.Match(h.Reasons[0], @"'notice' \((\d+)\)").Groups[1].Value);
        Assert.Equal(2 * Count(once), Count(twice));
    }

    [Fact]
    public void ConcurrentSearchesReturnExactlyWhatSequentialSearchesReturn()
    {
        // the per-thread accumulators must never leak state between queries or threads
        var svc = new SearchService(Ix, _ => false);
        var expected = Queries.ToDictionary(q => q, q => Sig(svc.Search(q, new SearchFilters())));
        Parallel.For(0, 64, new ParallelOptions { MaxDegreeOfParallelism = 8 }, k =>
        {
            var q = Queries[k % Queries.Length];
            Assert.Equal(expected[q], Sig(svc.Search(q, new SearchFilters())));
        });
        foreach (var q in Queries) Assert.Equal(expected[q], Sig(svc.Search(q, new SearchFilters())));
    }

    [Fact]
    public void WithdrawnDocumentsAreAbsentFromHitsCountsFacetsAndPages()
    {
        var hidden = Syn.Gen.Documents.Keys.First(k => k.StartsWith("syn-j-"));
        int hiddenDoc = Enumerable.Range(0, Ix.Docs.Count).First(d => Ix.Docs[d].DocId == hidden);
        var open = new SearchService(Ix, _ => false);
        var svc = new SearchService(Ix, d => d == hidden);
        foreach (var q in Queries)
        {
            var all = open.Search(q, new SearchFilters());
            var r = svc.Search(q, new SearchFilters());
            Assert.DoesNotContain(r.Hits, h => Ix.Docs[Ix.DocOf(h.PassageIndex)].DocId == hidden);
            Assert.Equal(all.Hits.Count(h => Ix.DocOf(h.PassageIndex) != hiddenDoc), r.TotalPassages);
            var page = svc.Page(r, 1, 100, null);
            Assert.DoesNotContain(page.Groups, g => g.Doc == hiddenDoc || g.Variants.Any(v => v.Doc == hiddenDoc));
            Assert.Equal(r.Hits.Select(h => Ix.DocOf(h.PassageIndex)).Distinct().Count(), r.TotalDocuments);
        }
    }
}
