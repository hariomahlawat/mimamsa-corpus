// Legal identifier resolution (C14 WP1). One reusable resolver for the identifiers a legal researcher types:
//  - statutory abbreviations and short names (IPC, CrPC, BNS, BNSS, BSA, IEA, AA, AFA, NA, AFT Act, AR …), resolved
//    only against instruments HELD in the active generation and always disclosed as an alias chip;
//  - sections, sub-sections, neutral and reported citations, case numbers (recognised by Search.Identifiers);
//  - party / case names, resolved against judgment metadata (petitioner, respondent);
//  - ambiguity: several instruments or too many parties -> nothing is pinned, the candidates are offered.
// It also derives three deterministic, display-only document properties used by search presentation: the instrument
// group key (editions and language versions of one instrument), the variant label, and the service context.
// Nothing here is a legal conclusion: an alias says which held title the letters were read as, not that two
// instruments are equivalent.
using System.Text.RegularExpressions;
using Mimamsa.Core.Generation;
using Mimamsa.Core.Search;

namespace Mimamsa.Core.Legal;

public sealed record AliasUse(string Alias, string Expansion, string HeldTitle);

public enum ScopeKind { Any, Scoped, Ambiguous, NotHeld }

/// Result of resolving the instrument words of a provision query ("Army Act", "IPC", "Rules").
public sealed record InstrumentScope(ScopeKind Kind, IReadOnlyList<int> Docs, string Text, IReadOnlyList<AliasUse> Aliases,
                                     IReadOnlyList<string> Terms);

/// Judgments whose parties match the query words. TooMany: more than MaxCaseNamePins; nothing is pinned.
public sealed record CaseNameMatch(IReadOnlyList<int> Docs, int Count, bool TooMany, IReadOnlyList<string> Terms);

public sealed partial class LegalIdentifierResolver
{
    public const int MaxCaseNamePins = 5;
    /// A query word counts as a name when it occurs among the parties of at most this many judgments.
    public const int MaxNameWordJudgments = 50;

    /// Short names and abbreviations -> title words of the instrument meant (stopwords omitted). Applied only where
    /// an instrument name is expected (after a section/rule number), and only when a held title contains every word.
    public static readonly IReadOnlyDictionary<string, string> Aliases = new Dictionary<string, string>(StringComparer.Ordinal)
    {
        ["ipc"] = "indian penal code",
        ["crpc"] = "code criminal procedure", ["cpc"] = "code civil procedure",
        ["iea"] = "indian evidence act", ["ie"] = "indian evidence act",
        ["bns"] = "bharatiya nyaya sanhita", ["bnss"] = "bharatiya nagarik suraksha sanhita", ["bsa"] = "bharatiya sakshya adhiniyam",
        ["aa"] = "army act", ["afa"] = "air force act", ["na"] = "navy act",
        ["aft"] = "armed forces tribunal", ["ar"] = "army rules", ["afr"] = "air force rules", ["nr"] = "navy rules",
    };

    static readonly HashSet<string> GenericInstrumentWords = new(StringComparer.Ordinal)
    { "act", "acts", "rule", "rules", "regulation", "regulations", "order", "orders", "notification", "notifications", "code", "manual" };

    /// Words that occur in many party names and say nothing about which case is meant.
    static readonly HashSet<string> GenericPartyWords = new(StringComparer.Ordinal)
    {
        "v", "vs", "versus", "union", "india", "state", "states", "ors", "others", "anr", "another", "govt", "government", "uoi",
        "secretary", "ministry", "defence", "chief", "army", "staff", "navy", "air", "force", "through", "general", "court",
        "martial", "high", "supreme", "tribunal", "armed", "forces", "officer", "officers", "commanding", "ex", "sepoy",
        "havildar", "naik", "lt", "col", "maj", "capt", "major", "colonel", "captain", "retd", "dr", "smt", "shri", "sri",
        "mr", "mrs", "ms", "director", "commissioner", "controller", "accounts", "pension", "pensions", "principal", "and",
        "the", "of", "petitioner", "respondent", "appellant", "applicant", "no", "lpa", "wp", "writ", "petition", "civil",
    };

    readonly IReadOnlyList<DocumentRecord> _docs;
    readonly IReadOnlyList<HashSet<string>> _titleTerms;
    readonly Dictionary<int, HashSet<string>> _petitioner = new(), _respondent = new();
    readonly Dictionary<string, int> _partyDf = new(StringComparer.Ordinal);
    readonly Dictionary<string, List<int>> _partyDocs = new(StringComparer.Ordinal);

    public LegalIdentifierResolver(IReadOnlyList<DocumentRecord> docs, IReadOnlyList<HashSet<string>> titleTerms)
    {
        _docs = docs; _titleTerms = titleTerms;
        for (int d = 0; d < docs.Count; d++)
        {
            if (docs[d].Judicial is not { } j) continue;
            var pet = Terms(j.Petitioner); var res = Terms(j.Respondent);
            if (pet.Count == 0 && res.Count == 0) continue;
            _petitioner[d] = pet; _respondent[d] = res;
            foreach (var t in pet.Union(res))
            {
                _partyDf[t] = _partyDf.GetValueOrDefault(t) + 1;
                (_partyDocs.TryGetValue(t, out var l) ? l : _partyDocs[t] = new()).Add(d);
            }
        }
    }

    static HashSet<string> Terms(string? s) => Text.Tokenize(s ?? "").Select(t => t.Term).ToHashSet(StringComparer.Ordinal);

    /// Party-name vocabulary (term -> number of judgments), for spelling suggestions.
    public IReadOnlyDictionary<string, int> PartyTerms => _partyDf;

    /// C16 S3-D: true when a judgment that is not hidden carries the party term (suggestions use only visible names).
    public bool PartyTermVisible(string term, Func<int, bool> hidden) =>
        _partyDocs.TryGetValue(term, out var l) && l.Any(d => !hidden(d));

    // ------------------------------------------------------------------ dotted abbreviations
    [GeneratedRegex(@"^(?:[A-Za-z]{1,2}\.){2,}[A-Za-z]{0,2}\.?$")] private static partial Regex DottedRx();

    /// "I.P.C." -> "IPC", "Cr.P.C." -> "CrPC". Only whole dotted words; "s.69" and ordinary words are unchanged.
    public static string CollapseDotted(string word) => DottedRx().IsMatch(word) ? word.Replace(".", "") : word;

    // ------------------------------------------------------------------ citation-only queries
    /// A query that is a citation such as "(2013) 7 SCC 316" or "[2013] 8 S.C.R. 1119" uses brackets as part of the
    /// citation, not as query syntax. True when the text outside recognised identifiers has no syntax at all.
    public static bool IsIdentifierQuery(string raw)
    {
        var ids = Identifiers.Recognise(raw);
        if (ids.Count == 0 || !ids.Any(i => i.Kind is IdKind.ReportedCitation or IdKind.NeutralCitation or IdKind.CaseNumber)) return false;
        var outside = new System.Text.StringBuilder();
        int last = 0;
        foreach (var id in ids) { outside.Append(raw, last, Math.Max(0, id.Start - last)).Append(' '); last = Math.Max(last, id.End); }
        if (last < raw.Length) outside.Append(raw[last..]);
        var rest = outside.ToString();
        if (rest.IndexOfAny(new[] { '(', ')', '"', '*', ':', '[', ']' }) >= 0) return false;
        return !Regex.IsMatch(rest, @"\b(AND|OR|NOT|NEAR/\d+)\b");
    }

    // ------------------------------------------------------------------ instruments
    /// Resolve the instrument words of a provision query. Rules (unchanged from review F05/F14, plus aliases):
    ///  - no instrument words: provision in any Act/Rules/Regulations;
    ///  - only generic words ("Rules", "Act"): ambiguous; candidates offered; nothing pinned;
    ///  - words matching no held title (after alias expansion): not held; nothing pinned;
    ///  - otherwise the closest titles (fewest extra words); distinct closest titles are ambiguous.
    /// C16 S3-D: `hidden` (index document -> hidden now: withdrawn, restricted, excluded by the response boundary)
    /// removes those instruments from every rule, so no alias, scope or candidate list names one. With nothing hidden
    /// (or null) the result is exactly as before.
    public InstrumentScope ResolveInstrument(IReadOnlyList<string> rawWords, Func<int, bool>? hidden = null)
    {
        bool Statute(int d) => _docs[d].IsStatute && (hidden is null || !hidden(d));
        var words = rawWords.Select(CollapseDotted).ToList();
        var terms = words.SelectMany(w => Text.Tokenize(w)).Select(t => t.Term).Where(t => !Text.Stopwords.Contains(t)).ToList();
        var aliases = new List<AliasUse>();
        var expanded = new List<string>();
        foreach (var t in terms)
        {
            if (Aliases.TryGetValue(t, out var exp))
            {
                var e = exp.Split(' ');
                var held = Enumerable.Range(0, _docs.Count).Where(d => Statute(d) && e.All(_titleTerms[d].Contains)).ToList();
                if (held.Count > 0)
                {
                    expanded.AddRange(e);
                    aliases.Add(new AliasUse(t, exp, _docs[held.OrderBy(d => _titleTerms[d].Count).ThenBy(d => _docs[d].DocId, StringComparer.Ordinal).First()].Title ?? exp));
                    continue;
                }
            }
            expanded.Add(t);
        }
        expanded = expanded.Distinct().ToList();
        if (expanded.Count == 0)
            return new InstrumentScope(ScopeKind.Any, Enumerable.Range(0, _docs.Count).Where(Statute).ToList(),
                "any Act, Rules or Regulations in the library", aliases, expanded);

        var specific = expanded.Where(w => !GenericInstrumentWords.Contains(w) && !w.All(char.IsDigit)).ToList();
        if (specific.Count == 0)
        {
            var kinds = expanded.Where(GenericInstrumentWords.Contains).ToHashSet();
            var all = Enumerable.Range(0, _docs.Count)
                .Where(d => Statute(d) && kinds.All(k => _titleTerms[d].Contains(k) || _titleTerms[d].Contains(k + "s") || _titleTerms[d].Contains(k.TrimEnd('s'))))
                .OrderBy(d => _titleTerms[d].Count(t => !kinds.Contains(t) && !Text.Stopwords.Contains(t) && !t.All(char.IsDigit)))
                .ThenBy(d => _docs[d].Title, StringComparer.OrdinalIgnoreCase)
                .Select(d => _docs[d].Title).Distinct().ToList();
            var text = all.Count == 0 ? "no instrument of that kind is held"
                : $"{all.Count} candidate instrument(s): " + string.Join("; ", all.Take(8)) + (all.Count > 8 ? $"; +{all.Count - 8} more" : "");
            return new InstrumentScope(ScopeKind.Ambiguous, Array.Empty<int>(), text, aliases, expanded);
        }
        var cands = new List<(int d, int extra)>();
        for (int d = 0; d < _docs.Count; d++)
            if (Statute(d) && expanded.All(w => _titleTerms[d].Contains(w)))
                cands.Add((d, _titleTerms[d].Count(t => !expanded.Contains(t) && !Text.Stopwords.Contains(t) && !t.All(char.IsDigit))));
        if (cands.Count == 0)
            return new InstrumentScope(ScopeKind.NotHeld, Array.Empty<int>(), string.Join(" ", rawWords), aliases, expanded);
        int best = cands.Min(c => c.extra);
        var top = cands.Where(c => c.extra == best).Select(c => c.d).ToList();
        var titles = top.Select(d => NormTitle(_docs[d].Title)).Distinct().ToList();
        if (titles.Count == 1)
            return new InstrumentScope(ScopeKind.Scoped, top, _docs[top.OrderBy(d => PrimaryRank(_docs[d])).First()].Title ?? string.Join(" ", rawWords), aliases, expanded);
        return new InstrumentScope(ScopeKind.Ambiguous, Array.Empty<int>(), string.Join("; ", top.Select(d => _docs[d].Title).Distinct().Take(6)), aliases, expanded);
    }

    public static string NormTitle(string? t) =>
        string.Join(" ", Text.Tokenize(t ?? "").Select(x => x.Term).Where(x => !x.All(char.IsDigit) && !Text.Stopwords.Contains(x)));

    // ------------------------------------------------------------------ case names
    /// Judgments whose parties contain every name word of the query ("Dharamvir Singh", "Ranjit Thakur v Union of
    /// India"). Requires at least one name-like word that is uncommon among parties (≤ 50 judgments), so generic
    /// words ("court martial", "union of india") never pin; more than 5 matching judgments are reported, not pinned.
    /// "X v Y" constrains X to one side and Y to the other.
    /// C16 S3-D: `hidden` judgments never match (nor count), so the chip neither names nor counts them.
    public CaseNameMatch? ResolveCaseName(IReadOnlyList<string> words, Func<int, bool>? hidden = null)
    {
        var toks = words.SelectMany(w => Text.Tokenize(w)).Select(t => t.Term).ToList();
        if (toks.Count == 0 || toks.Count > 10 || toks.Any(t => t.Any(char.IsDigit))) return null;
        int vs = toks.FindIndex(t => t is "v" or "vs" or "versus");
        List<string> Name(IEnumerable<string> ts) => ts.Where(t => !Text.Stopwords.Contains(t) && t is not ("v" or "vs" or "versus")).Distinct().ToList();
        var all = Name(toks);
        var nameLike = all.Where(t => !GenericPartyWords.Contains(t)).ToList();
        if (nameLike.Count == 0 || !nameLike.Any(t => _partyDf.GetValueOrDefault(t) is >= 1 and <= MaxNameWordJudgments)) return null;
        if (all.Count < 2 && all[0].Length < 6) return null;
        if (all.Any(t => !_partyDf.ContainsKey(t))) return null;
        var left = vs >= 0 ? Name(toks.Take(vs)) : null;
        var right = vs >= 0 ? Name(toks.Skip(vs + 1)) : null;
        var hits = new List<int>();
        foreach (var (d, pet) in _petitioner)
        {
            var res = _respondent[d];
            bool ok = vs >= 0
                ? (left!.All(pet.Contains) && right!.All(res.Contains)) || (left!.All(res.Contains) && right!.All(pet.Contains))
                : all.All(t => pet.Contains(t) || res.Contains(t)) && (all.All(pet.Contains) || all.All(res.Contains) || all.Count > 2);
            if (ok && (hidden is null || !hidden(d))) hits.Add(d);
        }
        if (hits.Count == 0) return null;
        hits.Sort((a, b) => string.CompareOrdinal(_docs[b].IssueDate ?? "", _docs[a].IssueDate ?? "") is var c && c != 0 ? c : string.CompareOrdinal(_docs[a].DocId, _docs[b].DocId));
        return new CaseNameMatch(hits.Count > MaxCaseNamePins ? Array.Empty<int>() : hits, hits.Count, hits.Count > MaxCaseNamePins, all);
    }

    public string CaseLabel(int d)
    {
        var j = _docs[d].Judicial!;
        return j.Petitioner is { } p && j.Respondent is { } r ? $"{p} v. {r}" : _docs[d].Title ?? _docs[d].DocId;
    }

    // ------------------------------------------------------------------ editions and language versions
    [GeneratedRegex(@"(-hi|-alt-[0-9a-f]{6}|-consolidated)$")] private static partial Regex VariantSuffixRx();

    /// Documents that are editions or language versions of one instrument share a key (the doc id without the
    /// importer's "-hi", "-alt-xxxxxx" or "-consolidated" suffix). Other documents are their own group.
    public static string GroupKey(DocumentRecord d) => d.IsStatute ? VariantSuffixRx().Replace(d.DocId, "") : d.DocId;

    /// Lower ranks are preferred as the group's representative: English first, then the plain id, then the id.
    public static int PrimaryRank(DocumentRecord d) =>
        (d.Language is null or "en" ? 0 : 4) + (VariantSuffixRx().IsMatch(d.DocId) ? 2 : 0);

    public static string VariantLabel(DocumentRecord d) =>
        d.Language == "hi" ? "Hindi text"
        : d.DocId.EndsWith("-consolidated", StringComparison.Ordinal) ? "Consolidated text"
        : d.DocId.Contains("-alt-", StringComparison.Ordinal) ? "Alternate print"
        : d.Language is { } l && l != "en" ? $"Text in '{l}'" : "Other copy";

    // ------------------------------------------------------------------ service context
    public static readonly IReadOnlyDictionary<string, string> ServiceLabels = new Dictionary<string, string>
    { ["army"] = "Army", ["navy"] = "Navy", ["airforce"] = "Air Force" };

    /// Service a document belongs to, for an optional ranking preference. Statutes: from the title (an instrument
    /// naming several services, or none, is general). Other documents: the dominant service in their text
    /// (≥ 5 mentions and at least twice the next). Null = general. Display and ranking only, never a filter.
    public static string? ServiceOf(DocumentRecord d, int army, int navy, int airForce)
    {
        if (d.IsStatute)
        {
            var t = " " + NormTitle(d.Title) + " ";
            var s = new List<string>();
            if (t.Contains(" army ")) s.Add("army");
            if (t.Contains(" navy ") || t.Contains(" naval ")) s.Add("navy");
            if (t.Contains(" air force ")) s.Add("airforce");
            return s.Count == 1 ? s[0] : null;
        }
        var c = new[] { ("army", army), ("navy", navy), ("airforce", airForce) }.OrderByDescending(x => x.Item2).ToArray();
        return c[0].Item2 >= 5 && c[0].Item2 >= 2 * c[1].Item2 ? c[0].Item1 : null;
    }
}
