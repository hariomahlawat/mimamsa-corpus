using System.Text.Json.Nodes;
using Mimamsa.Core.Search;
using Mimamsa.Hybrid;

namespace Mimamsa.Tests;

/// C15 WP2: persistent vector store, eligibility inside the dense scan, the cross-encoder rerank stage and the
/// provision-heading boost. Model-dependent tests are no-ops unless MIMAMSA_HYBRID_MODEL / MIMAMSA_RERANKER_MODEL are set.
public class C15HybridTests
{
    static readonly SearchIndex Ix = SearchIndex.Build(Syn.Gen);
    static string? Env(string k) => Environment.GetEnvironmentVariable(k) is { Length: > 0 } m && Directory.Exists(m) ? m : null;

    sealed class FixedScorer(params int[] passages) : ISemanticScorer
    {
        public string Description => "fixed test scorer";
        public IReadOnlyList<(int Passage, double Score)> TopK(string query, int k) => passages.Take(k).Select((p, i) => (p, 0.9 - i * 0.01)).ToList();
    }

    /// Deterministic stand-in for a cross-encoder: +2 for text containing `good`, the `special` passage gets `specialScore`, else -1.
    sealed class FakeReranker(string good, string? special = null, float specialScore = 0) : IReranker
    {
        public string Description => "fake reranker";
        public float[] Score(string query, IReadOnlyList<string> passages) =>
            passages.Select(p => special is not null && p == special ? specialScore : p.Contains(good, StringComparison.OrdinalIgnoreCase) ? 2f : -1f).ToArray();
    }

    // ---------------------------------------------------------------- vector store
    [Fact]
    public void VectorStoreRoundTripsAndRefusesATamperedFile()
    {
        var dir = Path.Combine(Path.GetTempPath(), "mimamsa-vs-" + Guid.NewGuid().ToString("N")[..8]);
        Directory.CreateDirectory(dir);
        try
        {
            var path = Path.Combine(dir, "m.mvs");
            var s = new VectorStore(3);
            var k1 = VectorStore.Key("sha", 256, "passage: a"); var k2 = VectorStore.Key("sha", 256, "passage: b");
            s.Put(k1, new[] { 1f, 0f, 0f }); s.Put(k2, new[] { 0f, 1f, 0f });
            s.Save(path, new[] { k1, k2 });
            var r = VectorStore.Load(path, 3);
            Assert.Null(r.LoadIssue);
            Assert.Equal(2, r.Count);
            Assert.True(r.TryGet(k2, out var v) && v[1] == 1f);
            Assert.NotEqual(k1, VectorStore.Key("other-model", 256, "passage: a"));     // the model is part of the key
            Assert.Equal("shape mismatch (dim 3, count 2)", VectorStore.Load(path, 4).LoadIssue);
            var bytes = File.ReadAllBytes(path); bytes[30] ^= 0xFF; File.WriteAllBytes(path, bytes);
            var t = VectorStore.Load(path, 3);
            Assert.Equal(0, t.Count);
            Assert.Contains("integrity", t.LoadIssue);
        }
        finally { Directory.Delete(dir, true); }
    }

    [Fact]
    public void DenseIndexIsIncrementalAndFiltersInsideTheScan()
    {
        if (Env("MIMAMSA_HYBRID_MODEL") is not { } model) return;   // needs the pinned model on this host
        var dir = Path.Combine(Path.GetTempPath(), "mimamsa-dense-" + Guid.NewGuid().ToString("N")[..8]);
        try
        {
            using var e1 = new E5Embedder(model);
            var a = DenseIndex.Build(Ix, "g1", e1, dir, "test");
            Assert.Equal(Ix.N, a.Embedded);
            using var e2 = new E5Embedder(model);
            var b = DenseIndex.Build(Ix, "g2", e2, dir, "test");    // a new generation with the same texts: nothing re-embedded
            Assert.Equal(0, b.Embedded);
            Assert.Equal(Ix.N, b.Reused);
            Assert.Equal(a.TopK("written notice before the hearing", 5), b.TopK("written notice before the hearing", 5));
            var top = b.TopK("written notice before the hearing", 3);
            var filtered = b.TopK("written notice before the hearing", 3, p => p != top[0].Passage);
            Assert.DoesNotContain(filtered, x => x.Passage == top[0].Passage);
            Assert.Equal(3, filtered.Count);                         // the excluded passage did not use up depth
        }
        finally { if (Directory.Exists(dir)) Directory.Delete(dir, true); }
    }

    [Fact]
    public void DefaultFilteredTopKExcludesAndKeepsDepth()
    {
        ISemanticScorer s = new FixedScorer(5, 4, 3, 2, 1, 0);
        var r = s.TopK("q", 3, p => p % 2 == 0);
        Assert.Equal(new[] { 4, 2, 0 }, r.Select(x => x.Passage));
    }

    // ---------------------------------------------------------------- rerank stage
    [Fact]
    public void RerankerOffLeavesSearchUnchanged()
    {
        var a = new SearchService(Ix, _ => false);
        var b = new SearchService(Ix, _ => false) { Reranker = null, Hybrid = new HybridOptions(RerankPool: 3, RerankAdmit: 5) };
        foreach (var q in new[] { "notice", "hearing written notice allegation", "s.17 Bracken Service Act" })
            Assert.Equal(a.Search(q, new SearchFilters()).Hits.Select(h => (h.PassageIndex, h.Tier)), b.Search(q, new SearchFilters()).Hits.Select(h => (h.PassageIndex, h.Tier)));
    }

    [Fact]
    public void RerankStageKeepsPinnedTiersAndLexicalCandidates()
    {
        var plain = new SearchService(Ix, _ => false);
        var rr = new SearchService(Ix, _ => false) { Reranker = new FakeReranker("notice") };
        foreach (var q in new[] { "s.17 Bracken Service Act", "OA 411/2021", "Rule 3A" })
        {
            var a = plain.Search(q, new SearchFilters()); var b = rr.Search(q, new SearchFilters());
            var pa = a.Hits.TakeWhile(h => h.Tier is "identifier" or "title" or "case_name").Select(h => h.PassageIndex).ToList();
            Assert.Equal(pa, b.Hits.Take(pa.Count).Select(h => h.PassageIndex).ToList());
        }
        var r = rr.Search("hearing written notice allegation", new SearchFilters());
        var x = plain.Search("hearing written notice allegation", new SearchFilters());
        Assert.Equal("hybrid", r.Mode);
        Assert.Equal(x.Hits.Select(h => h.PassageIndex).OrderBy(p => p), r.Hits.Select(h => h.PassageIndex).OrderBy(p => p));   // nothing lexical dropped
        Assert.Contains("notice", Ix.Passages[r.Hits[0].PassageIndex].Text, StringComparison.OrdinalIgnoreCase);                // reordered by the reranker
        Assert.Contains(r.Hits[0].Reasons, s => s.Contains("not legal relevance"));
    }

    [Fact]
    public void DenseOnlyCandidatesNeedTheRerankerAdmission()
    {
        int last = Ix.N - 1;
        string text = Ix.Passages[last].Text;
        var below = new SearchService(Ix, _ => false) { Semantic = new FixedScorer(last), Reranker = new FakeReranker("notice", text, -0.5f) };
        var above = new SearchService(Ix, _ => false) { Semantic = new FixedScorer(last), Reranker = new FakeReranker("notice", text, 0.5f) };
        var plainHits = new SearchService(Ix, _ => false).Search("notice", new SearchFilters()).Hits.Select(h => h.PassageIndex).ToHashSet();
        Assert.DoesNotContain(last, plainHits);
        Assert.DoesNotContain(below.Search("notice", new SearchFilters()).Hits, h => h.PassageIndex == last);
        var hit = above.Search("notice", new SearchFilters()).Hits.Single(h => h.PassageIndex == last);
        Assert.Equal("semantic", hit.Tier);
    }

    [Fact]
    public void WithdrawnDocumentsNeverReachTheRerankPool()
    {
        int last = Ix.N - 1;
        var hiddenDoc = Ix.Passages[last].DocId;
        var s = new SearchService(Ix, d => d == hiddenDoc) { Semantic = new FixedScorer(last), Reranker = new FakeReranker("notice", Ix.Passages[last].Text, 9f) };
        Assert.DoesNotContain(s.Search("notice", new SearchFilters()).Hits, h => Ix.Passages[h.PassageIndex].DocId == hiddenDoc);
    }

    [Fact]
    public void RerankerTokenizerMatchesTheModelsTokenizerJson()
    {
        if (Env("MIMAMSA_RERANKER_MODEL") is not { } model) return;   // needs the pinned reranker on this host
        using var ce = new CrossEncoder(model);
        foreach (var v in JsonNode.Parse(File.ReadAllText(Path.Combine(AppContext.BaseDirectory, "reranker_tokenizer_vectors.json")))!.AsArray())
        {
            var want = v!["ids"]!.AsArray().Select(x => (long)x!.GetValue<int>()).ToArray();
            Assert.Equal(want, ce.EncodePair(v["query"]!.GetValue<string>(), v["passage"]!.GetValue<string>(), 512));
        }
    }

    // ---------------------------------------------------------------- provision-heading boost
    [Fact]
    public void ProvisionHeadingBoostFollowsItsFixedRule()
    {
        var ph = ProvisionHeadings.Empty();
        ph.Add(7, "The Army Act, 1950", "39", "Absence without leave");
        ph.Add(8, "The Army Act, 1950", "116", "Summary court-martial");
        ph.Add(9, "The Army Act, 1950", "120", "Powers of summary courts-martial");
        ph.Add(10, "The Army Act, 1950", "38", "Desertion and aiding desertion");
        var scores = new Dictionary<int, double> { [1] = 10, [7] = 1 };
        var reasons = new Dictionary<int, string>();

        Assert.Same(scores, ph.Boost(scores, new[] { "absence", "without", "leave" }, reasons));           // no procedural cue: unchanged
        var b = ph.Boost(scores, new[] { "absence", "without", "leave", "punishment" }, reasons);
        Assert.True(b[7] > b[1]);                                                                          // provision above the top result
        Assert.Equal(1, scores[7]);                                                                        // input not modified
        Assert.Contains("Absence without leave", reasons[7]);
        Assert.False(b.ContainsKey(10));                                                                   // desertion: one stem, coverage 0.5

        var c = ph.Boost(new() { [1] = 3 }, "how to hold a summary court martial".Split(' '), reasons);
        Assert.True(c[8] > c[9]);                                                                          // full coverage before 0.75
        Assert.True(c[9] > c[1]);

        // two generic heading words in a long, case-law question do not reach the query-coverage threshold
        ph.Add(11, "The Bharatiya Nagarik Suraksha Sanhita, 2023", "9", "Powers of High Court");
        var d = ph.Boost(new() { [1] = 3 }, "can high court entertain writ against armed forces tribunal order".Split(' '), reasons);
        Assert.False(d.ContainsKey(11));
    }
}
