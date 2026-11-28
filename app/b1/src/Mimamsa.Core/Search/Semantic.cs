// C14 S4 hybrid-retrieval PoC: the narrow contract between lexical search and an optional semantic scorer.
// Core holds no model code. When no scorer is configured (the default), search behaves exactly as in B1.
namespace Mimamsa.Core.Search;

/// Dense similarity over the indexed passages of the active generation. Scores are cosine similarities of
/// embedding vectors: a statement about wording, never about legal relevance or authority.
public interface ISemanticScorer
{
    /// e.g. "multilingual-e5-small@614241f6 (CPU)"; shown in the search run line and notes.
    string Description { get; }
    /// Top-k passage indexes (into SearchIndex.Passages) by similarity to the query, best first; ties by index.
    IReadOnlyList<(int Passage, double Score)> TopK(string query, int k);

    /// C15 WP2: top-k among passages for which `include` is true (eligibility applied inside the scorer, so withdrawn
    /// or ineligible passages never appear and never use up depth). Scorers without a native filter fall back to
    /// filtering a deeper unfiltered list.
    IReadOnlyList<(int Passage, double Score)> TopK(string query, int k, Func<int, bool>? include) =>
        include is null ? TopK(query, k) : TopK(query, k * 4 + 16).Where(x => include(x.Passage)).Take(k).ToList();
}

public sealed record HybridOptions(int LexicalDepth = 200, int DenseDepth = 100, int RrfK = 60, double MinSimilarity = 0.0,
    int RerankPool = 30, double RerankAdmit = 0.0)
{
    /// C16 S3-E: how dense candidates are admitted to fusion.
    ///   "floor" (default, unchanged): every dense candidate at or above MinSimilarity.
    ///   "gate_rank": MinSimilarity gates the QUERY (its best dense candidate must reach it); once open, the top AdmitK
    ///   dense candidates are admitted by rank, whatever their own similarity. Same mode decision as "floor" for every query.
    public string Admission { get; init; } = "floor";
    public int AdmitK { get; init; } = 10;
}

/// C16 S3-E: the dense admission rules (HybridOptions.Admission). Input is best first; output is a prefix of it.
public static class HybridAdmission
{
    public static List<(int Passage, double Score)> Admit(IReadOnlyList<(int Passage, double Score)> dense, HybridOptions o) => o.Admission switch
    {
        "floor" => dense.Where(x => x.Score >= o.MinSimilarity).ToList(),
        "gate_rank" => dense.Count > 0 && dense[0].Score >= o.MinSimilarity ? dense.Take(o.AdmitK).ToList() : new List<(int, double)>(),
        _ => throw new InvalidOperationException($"unknown hybrid admission rule '{o.Admission}'"),
    };
}

/// C15 WP2: scores (query, passage) pairs jointly (a cross-encoder). Higher is more relevant; the score describes text,
/// never legal relevance. `Admit` semantics belong to the caller (HybridOptions.RerankAdmit).
public interface IReranker
{
    string Description { get; }
    float[] Score(string query, IReadOnlyList<string> passages);
}

/// Reciprocal-rank fusion (Cormack et al. 2009) of a lexical ranking and a dense ranking. Deterministic: equal fused
/// scores are ordered by passage index. Identifier and title tiers are never passed in; they stay above fused hits.
public static class HybridFusion
{
    public static List<(int Passage, double Fused, int? LexRank, int? DenseRank)> Rrf(
        IReadOnlyList<int> lexicalRanked, IReadOnlyList<int> denseRanked, HybridOptions o)
    {
        var acc = new Dictionary<int, (double s, int? lr, int? dr)>();
        for (int i = 0; i < Math.Min(o.LexicalDepth, lexicalRanked.Count); i++)
        {
            var p = lexicalRanked[i];
            acc[p] = (1.0 / (o.RrfK + i + 1), i + 1, null);
        }
        for (int i = 0; i < Math.Min(o.DenseDepth, denseRanked.Count); i++)
        {
            var p = denseRanked[i];
            var add = 1.0 / (o.RrfK + i + 1);
            acc[p] = acc.TryGetValue(p, out var v) ? (v.s + add, v.lr, i + 1) : (add, null, i + 1);
        }
        return acc.Select(kv => (kv.Key, kv.Value.s, kv.Value.lr, kv.Value.dr))
                  .OrderByDescending(x => x.s).ThenBy(x => x.Key).ToList();
    }
}
