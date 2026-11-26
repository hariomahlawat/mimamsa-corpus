using System.Text.Json.Nodes;
using Mimamsa.Core.Search;
using Mimamsa.Hybrid;

namespace Mimamsa.Tests;

/// C14 S4 hybrid PoC. The flag-off and fusion tests need only the SYN site; the tokenizer and real-model tests also
/// need MIMAMSA_HYBRID_MODEL (directory of the pinned multilingual-e5-small revision) and are no-ops without it.
public class HybridTests
{
    static readonly SearchIndex Ix = SearchIndex.Build(Syn.Gen);
    static string? ModelDir => Environment.GetEnvironmentVariable("MIMAMSA_HYBRID_MODEL") is { Length: > 0 } m && Directory.Exists(m) ? m : null;

    /// A deterministic stand-in scorer: ranks passages by index from a fixed list.
    sealed class FixedScorer(params int[] passages) : ISemanticScorer
    {
        public string Description => "fixed test scorer";
        public IReadOnlyList<(int Passage, double Score)> TopK(string query, int k) => passages.Take(k).Select((p, i) => (p, 0.9 - i * 0.01)).ToList();
    }

    static List<(int, string, double)> Sig(SearchResult r) => r.Hits.Select(h => (h.PassageIndex, h.Tier, h.Score)).ToList();
    static readonly string[] Queries = { "notice", "s.17 Bracken Service Act", "OA 411/2021", "hearing written notice allegation", "exact:\"summary of evidence\"", "summary AND evidence" };

    [Fact]
    public void FlagOffIsIdenticalToB1()
    {
        var b1 = new SearchService(Ix, _ => false);
        var off = new SearchService(Ix, _ => false) { Semantic = null, Hybrid = new HybridOptions(5, 5, 1) };
        foreach (var q in Queries)
        {
            var a = b1.Search(q, new SearchFilters()); var b = off.Search(q, new SearchFilters());
            Assert.Equal(Sig(a), Sig(b));
            Assert.Equal(a.Mode, b.Mode);
            Assert.NotEqual("hybrid", b.Mode);
        }
    }

    [Fact]
    public void IdentifierTierStaysFirstAndUnchangedWithHybridOn()
    {
        var b1 = new SearchService(Ix, _ => false);
        // the stand-in scorer pushes the LAST passages of the index, i.e. unrelated text, as hard as it can
        var on = new SearchService(Ix, _ => false) { Semantic = new FixedScorer(Enumerable.Range(0, Ix.N).Reverse().ToArray()) };
        foreach (var q in new[] { "s.17 Bracken Service Act", "OA 411/2021", "Rule 3A" })
        {
            var a = b1.Search(q, new SearchFilters()); var b = on.Search(q, new SearchFilters());
            var pinnedA = a.Hits.TakeWhile(h => h.Tier is "identifier" or "title").Select(h => h.PassageIndex).ToList();
            var pinnedB = b.Hits.TakeWhile(h => h.Tier is "identifier" or "title").Select(h => h.PassageIndex).ToList();
            Assert.Equal(pinnedA, pinnedB);
            if (pinnedA.Count > 0) Assert.Equal("identifier", b.Mode);
        }
    }

    [Fact]
    public void HybridModeIsReportedAndSemanticOnlyHitsAreLabelled()
    {
        int last = Ix.N - 1;
        var on = new SearchService(Ix, _ => false) { Semantic = new FixedScorer(last) };
        var r = on.Search("notice", new SearchFilters());
        Assert.Equal("hybrid", r.Mode);
        var h = r.Hits.First(x => x.PassageIndex == last);
        Assert.Contains(h.Reasons, s => s.Contains("similarity is not legal relevance"));
        Assert.Contains(r.Notes, n => n.StartsWith("Hybrid search"));
    }

    [Fact]
    public void ExactAndOperatorQueriesStayLexical()
    {
        var on = new SearchService(Ix, _ => false) { Semantic = new FixedScorer(0, 1, 2) };
        Assert.NotEqual("hybrid", on.Search("exact:\"summary of evidence\"", new SearchFilters()).Mode);
        Assert.NotEqual("hybrid", on.Search("summary AND evidence", new SearchFilters()).Mode);
    }

    [Fact]
    public void WithdrawnDocumentsStayHiddenUnderHybrid()
    {
        var hiddenDoc = Ix.Passages[0].DocId;
        var on = new SearchService(Ix, d => d == hiddenDoc) { Semantic = new FixedScorer(Enumerable.Range(0, Ix.N).ToArray()) };
        var r = on.Search("notice", new SearchFilters());
        Assert.DoesNotContain(r.Hits, h => Ix.Passages[h.PassageIndex].DocId == hiddenDoc);
    }

    [Fact]
    public void FusionIsDeterministicWithIndexTieBreak()
    {
        var o = new HybridOptions(10, 10, 60);
        var a = HybridFusion.Rrf(new[] { 5, 3, 9 }, new[] { 3, 7, 5 }, o);
        var b = HybridFusion.Rrf(new[] { 5, 3, 9 }, new[] { 3, 7, 5 }, o);
        Assert.Equal(a, b);
        Assert.Equal(3, a[0].Passage);   // rank 2 + rank 1 beats rank 1 + rank 3
        // exact ties (9 lexical rank 3, 5? no) -> symmetric case: two passages with mirrored ranks tie; lower index first
        var t = HybridFusion.Rrf(new[] { 8, 4 }, new[] { 4, 8 }, o);
        Assert.Equal(new[] { 4, 8 }, t.Select(x => x.Passage).ToArray());
    }

    [Fact]
    public void TokenizerMatchesTheModelsTokenizerJson()
    {
        if (ModelDir is null) return;   // needs the pinned model on this host
        using var e = new E5Embedder(ModelDir);
        var vectors = JsonNode.Parse(File.ReadAllText(Path.Combine(AppContext.BaseDirectory, "hybrid_tokenizer_vectors.json")))!.AsArray();
        foreach (var v in vectors)
        {
            var want = v!["ids"]!.AsArray().Select(x => (long)x!.GetValue<int>()).ToArray();
            Assert.Equal(want, e.Encode(v["text"]!.GetValue<string>(), 512));
        }
    }

    [Fact]
    public void RealModelEmbeddingsAreNormalisedAndDeterministic()
    {
        if (ModelDir is null) return;
        using var e = new E5Embedder(ModelDir);
        var a = e.EmbedQuery("written notice before a hearing");
        var b = e.EmbedQuery("written notice before a hearing");
        Assert.Equal(a, b);
        Assert.InRange(a.Sum(x => (double)x * x), 0.999, 1.001);
        var related = e.Embed(new[] { "passage: notice in writing must be given before the hearing" }, 64)[0];
        var unrelated = e.Embed(new[] { "passage: the battery voltage of the generator was low" }, 64)[0];
        double Cos(float[] x, float[] y) => x.Zip(y, (p, q) => (double)p * q).Sum();
        Assert.True(Cos(a, related) > Cos(a, unrelated));
    }
}
