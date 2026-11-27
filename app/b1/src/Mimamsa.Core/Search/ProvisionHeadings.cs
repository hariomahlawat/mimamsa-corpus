// C15 WP2/WP7: provision-heading boost for procedural plain-language queries.
//
// A commander's question ("absence without leave punishment", "how to hold a summary court martial") should lead to
// the provision whose printed heading states that subject, not to judgments that mention it. The rule below was fixed
// before it was measured on the C14 walkthrough queries and is not tuned on the retrieval oracle:
//   1. Gate: the query contains one of a fixed list of procedural cue words (ProceduralCues).
//   2. Candidates: provisions of held Acts/Rules/Regulations from the table of contents read from the verified text
//      (Toc). Arrangement (contents-list) passages are skipped: a passage carrying four or more section headings.
//   3. Match: heading and query content stems (stopwords, digits and stems shorter than 3 removed); at least two
//      heading stems in the query and coverage (matched / heading stems) of at least 0.6.
//   4. Boost: at most MaxBoosted provisions, ordered by coverage, then matched stems, then their own BM25 score; each is
//      placed above the ranked results (score = top x (1 + coverage)) with a stated reason. It is a ranked lexical hit,
//      never a pinned identifier, and it never touches identifier, case-name or title tiers.
// The heading is the compilation's printed text; the reason says so. Nothing here decides what applies to a case.
using System.Text.RegularExpressions;
using Mimamsa.Core.Generation;

namespace Mimamsa.Core.Search;

public sealed partial class ProvisionHeadings
{
    public static readonly HashSet<string> ProceduralCues = new(StringComparer.Ordinal)
    {
        "how", "procedure", "procedural", "power", "powers", "punishment", "punishments", "punish", "award", "awardable",
        "arrest", "custody", "detention", "hold", "convene", "convening", "record", "recording", "investigate",
        "investigation", "inquiry", "duty", "duties", "who", "when", "can", "may", "must", "required", "requirement",
        "safeguard", "safeguards", "right", "rights", "steps", "process", "form", "forms", "appeal", "petition",
        "sentence", "trial", "try", "tried", "charge", "hearing",
    };
    public const double MinCoverage = 0.6;
    /// Added after observing the C14 walkthrough queries (development data, not the oracle; see DECLARATIONS.md):
    /// the matched heading stems must also cover at least half of the query's content stems, so two generic words
    /// ("high court") cannot pull statute provisions above the case law a question is really about.
    public const double MinQueryCoverage = 0.5;
    public const int MinMatched = 2, MaxBoosted = 5;

    sealed record Entry(int Passage, string DocTitle, string Number, string Heading, HashSet<string> Stems);
    readonly List<Entry> _entries = new();
    public int Count => _entries.Count;

    [GeneratedRegex(@"(?:^|\s)\d{1,3}[A-Z]{0,2}\.\s+\[?[A-Z][a-z]")] private static partial Regex HeadingMark();

    static HashSet<string> Stems(string s) => Text.Tokenize(s).Select(t => t.Term)
        .Where(t => !Text.Stopwords.Contains(t) && !t.All(char.IsDigit)).Select(Text.Stem).Where(t => t.Length >= 3).ToHashSet();

    public static ProvisionHeadings Build(SearchIndex ix)
    {
        var ph = new ProvisionHeadings();
        var byId = new Dictionary<(string, string), int>();
        for (int i = 0; i < ix.N; i++) byId[(ix.Passages[i].DocId, ix.Passages[i].PassageId)] = i;
        foreach (var d in ix.Docs.Where(d => d.IsStatute))
            foreach (var e in Toc.Build(d))
            {
                if (e.PassageId is null || !byId.TryGetValue((d.DocId, e.PassageId), out var p)) continue;
                if (HeadingMark().Matches(ix.Passages[p].Text).Count >= 4) continue;      // a contents list, not the provision
                var stems = Stems(e.Heading.Trim('[', ']', '.'));
                if (stems.Count == 0) continue;
                ph._entries.Add(new Entry(p, d.Title ?? d.DocId, e.Number, e.Heading.Trim(), stems));
            }
        return ph;
    }

    /// Test and tooling seam: an empty set to which entries are added directly.
    public static ProvisionHeadings Empty() => new();
    public void Add(int passage, string docTitle, string number, string heading)
    {
        var stems = Stems(heading.Trim('[', ']', '.'));
        if (stems.Count > 0) _entries.Add(new Entry(passage, docTitle, number, heading, stems));
    }

    /// Returns `scores` with the matching provisions boosted (a new dictionary; the input is not modified).
    public Dictionary<int, double> Boost(Dictionary<int, double> scores, IReadOnlyList<string> words, Dictionary<int, string> reasons)
    {
        var picks = Picks(p => scores.GetValueOrDefault(p), () => scores.Count > 0 ? scores.Values.Max() : 1.0, words);
        if (picks.Count == 0) return scores;
        var r = new Dictionary<int, double>(scores);
        foreach (var (p, s, why) in picks) { r[p] = s; reasons[p] = why; }
        return r;
    }

    /// C16 WP05: the boosted provisions with their new scores, in pick order, for any score representation. `own` is
    /// a passage's current score (0 when it has none) and `top` the highest current score (1.0 when there is none).
    /// Boost() above is this applied to a dictionary; the rule and the arithmetic are unchanged.
    internal List<(int Passage, double Score, string Reason)> Picks(Func<int, double> own, Func<double> top, IReadOnlyList<string> words)
    {
        var none = new List<(int, double, string)>();
        var raw = words.SelectMany(w => Text.Tokenize(w)).Select(t => t.Term).ToList();
        if (!raw.Any(ProceduralCues.Contains)) return none;
        var q = Stems(string.Join(" ", words));
        if (q.Count < MinMatched) return none;
        var picks = _entries.Select(e => (e, m: e.Stems.Count(q.Contains)))
            .Where(x => x.m >= MinMatched && (double)x.m / x.e.Stems.Count >= MinCoverage && (double)x.m / q.Count >= MinQueryCoverage)
            .Select(x => (x.e, x.m, c: (double)x.m / x.e.Stems.Count, own: own(x.e.Passage)))
            .GroupBy(x => x.e.Passage).Select(g => g.OrderByDescending(x => x.c).First())
            .OrderByDescending(x => x.c).ThenByDescending(x => x.m).ThenByDescending(x => x.own).ThenBy(x => x.e.Passage)
            .Take(MaxBoosted).ToList();
        if (picks.Count == 0) return none;
        double t = top();
        return picks.Select(x => (x.e.Passage, t * (1 + x.c) + x.own * 1e-3,
            $"Provision heading matches the question: {x.e.Number}. {x.e.Heading} ({x.e.DocTitle}); heading as printed in the held copy")).ToList();
    }
}
