// "Did you mean" suggestions (C14, F08). Deterministic and offered only: the query that ran is never rewritten.
// Two rules, both over the active generation's own vocabulary (index terms seen in ≥ 3 passages, plus party names):
//  1. a word the library does not contain is replaced by its nearest held word (edit distance ≤ 1 for 4–6 letters,
//     ≤ 2 for 7+; same first letter; most frequent wins, then alphabetical);
//  2. a pair of adjacent words that rarely occurs together ("court marshal") is replaced when a near spelling of one
//     word forms a pair at least ten times more frequent and seen at least five times ("court martial").
namespace Mimamsa.Core.Search;

public sealed class SpellingSuggester
{
    const int MinDf = 3;
    readonly SearchIndex _ix;
    readonly Dictionary<(char, int), List<(string term, int df)>> _buckets = new();

    public SpellingSuggester(SearchIndex ix)
    {
        _ix = ix;
        var vocab = new Dictionary<string, int>(StringComparer.Ordinal);
        foreach (var (t, post) in ix.Postings)
            if (post.Count >= MinDf && t.Length >= 3 && t.All(c => c is >= 'a' and <= 'z')) vocab[t] = post.Count;
        foreach (var (t, n) in ix.Resolver.PartyTerms)
            if (t.Length >= 3 && t.All(c => c is >= 'a' and <= 'z')) vocab[t] = Math.Max(vocab.GetValueOrDefault(t), Math.Max(MinDf, n));
        foreach (var (t, df) in vocab)
        {
            var k = (t[0], t.Length);
            if (!_buckets.TryGetValue(k, out var l)) _buckets[k] = l = new();
            l.Add((t, df));
        }
    }

    static int MaxDistance(int len) => len >= 7 ? 2 : len >= 4 ? 1 : 0;

    int Df(string t) => _ix.Postings.TryGetValue(t, out var l) ? l.Count : 0;

    IEnumerable<(string term, int df)> Near(string t)
    {
        int max = MaxDistance(t.Length);
        if (max == 0) yield break;
        for (int len = t.Length - max; len <= t.Length + max; len++)
            if (_buckets.TryGetValue((t[0], len), out var l))
                foreach (var (c, df) in l)
                    if (c != t && Distance(t, c, max) <= max) yield return (c, df);
    }

    /// Passages in which a is immediately followed by b, counted up to `limit`. Postings are ordered by passage and
    /// positions ascend, so this is a merge join with no allocation.
    int PairCount(string a, string b, int limit = int.MaxValue)
    {
        if (!_ix.Postings.TryGetValue(a, out var pa) || !_ix.Postings.TryGetValue(b, out var pb)) return 0;
        int n = 0, i = 0, j = 0;
        while (i < pa.Count && j < pb.Count && n < limit)
        {
            int c = pa[i].P.CompareTo(pb[j].P);
            if (c < 0) { i++; continue; }
            if (c > 0) { j++; continue; }
            int[] x = pa[i].Pos, y = pb[j].Pos;
            for (int u = 0, v = 0; u < x.Length && v < y.Length;)
            {
                int want = x[u] + 1;
                if (y[v] == want) { n++; break; }
                if (y[v] < want) v++; else u++;
            }
            i++; j++;
        }
        return n;
    }

    /// Suggested query for the plain words, or null. Words with digits or fewer than four letters are kept.
    public string? Suggest(IReadOnlyList<string> words)
    {
        var terms = words.Select(w => { var t = Text.Tokenize(w); return t.Count == 1 ? t[0].Term : null; }).ToList();
        var outp = terms.ToList();
        bool changed = false;
        bool Word(string? t) => t is { Length: >= 4 } && t.All(c => c is >= 'a' and <= 'z');
        for (int i = 0; i < outp.Count; i++)
        {
            var t = outp[i];
            if (!Word(t) || Df(t!) > 0 || _ix.Resolver.PartyTerms.ContainsKey(t!)) continue;
            var best = Near(t!).OrderByDescending(x => x.df).ThenBy(x => x.term, StringComparer.Ordinal).Select(x => x.term).FirstOrDefault();
            if (best is not null) { outp[i] = best; changed = true; }
        }
        for (int i = 0; i + 1 < outp.Count; i++)
        {
            string? a = outp[i], b = outp[i + 1];
            if (!Word(a) || !Word(b) || Text.Stopwords.Contains(a!) || Text.Stopwords.Contains(b!)) continue;
            int cur = PairCount(a!, b!, 5);
            if (cur >= 5) continue;               // an established pair is not questioned
            (int n, int idx, string term) best = (0, -1, "");
            foreach (var (cand, _) in Near(b!).OrderByDescending(x => x.df).Take(20))
                if (PairCount(a!, cand) is var n && n > best.n) best = (n, i + 1, cand);
            foreach (var (cand, _) in Near(a!).OrderByDescending(x => x.df).Take(20))
                if (PairCount(cand, b!) is var n && n > best.n) best = (n, i, cand);
            if (best.idx >= 0 && best.n >= Math.Max(5, 10 * cur)) { outp[best.idx] = best.term; changed = true; }
        }
        if (!changed) return null;
        return string.Join(" ", words.Select((w, i) => outp[i] is { } o && o != terms[i] ? o : w));
    }

    /// Optimal string alignment distance with an early exit above max.
    public static int Distance(string a, string b, int max)
    {
        if (Math.Abs(a.Length - b.Length) > max) return max + 1;
        var d = new int[a.Length + 1, b.Length + 1];
        for (int i = 0; i <= a.Length; i++) d[i, 0] = i;
        for (int j = 0; j <= b.Length; j++) d[0, j] = j;
        for (int i = 1; i <= a.Length; i++)
        {
            int rowMin = int.MaxValue;
            for (int j = 1; j <= b.Length; j++)
            {
                int cost = a[i - 1] == b[j - 1] ? 0 : 1;
                int v = Math.Min(Math.Min(d[i - 1, j] + 1, d[i, j - 1] + 1), d[i - 1, j - 1] + cost);
                if (i > 1 && j > 1 && a[i - 1] == b[j - 2] && a[i - 2] == b[j - 1]) v = Math.Min(v, d[i - 2, j - 2] + 1);
                d[i, j] = v; rowMin = Math.Min(rowMin, v);
            }
            if (rowMin > max) return max + 1;
        }
        return d[a.Length, b.Length];
    }
}
