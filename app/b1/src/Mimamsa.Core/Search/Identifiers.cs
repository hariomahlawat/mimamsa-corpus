// Exact-identifier layer (P2: lifted exact-ID Target@1 from 0.53 to 0.82). Recognises sections/rules, neutral and
// reported citations and case numbers in the query, normalises them, and resolves them against document metadata
// (case_numbers, neutral_citation, reported_citations) and identifiers printed at the top of page 1. Matching
// passages are pinned above ranked results and are never displaced by scoring (design 03 §2 ranking rule).
using System.Text.RegularExpressions;

namespace Mimamsa.Core.Search;

public enum IdKind { Section, NeutralCitation, ReportedCitation, CaseNumber }

public sealed record QueryIdentifier(IdKind Kind, string Raw, string Normalized, int Start, int End, string? Base = null,
                                     string? Sub = null, string? ProvisionWord = null);

public static partial class Identifiers
{
    [GeneratedRegex(@"(?<![\w.])(?<w>ss|s|sec|section|r|rule|rules|reg|regulation|regulations|art|article|para|paragraph)\s*\.?\s*(?<n>\d{1,4}[A-Z]{0,2})(?<sub>(?:\s*\([0-9a-zA-Z]{1,4}\))*)(?![\w/])", RegexOptions.IgnoreCase)]
    private static partial Regex SectionRx();
    [GeneratedRegex(@"\b(?<y>(?:19|20)\d{2})\s+(?<r>[A-Z]{2,10})\s+(?<n>\d{1,6})\b")]
    private static partial Regex NeutralRx();
    [GeneratedRegex(@"[\[(](?<y>\d{4})[\])]\s*(?<v>\d{1,3})?\s*(?<r>SCC|S\.\s?C\.\s?R\.|SCR|SLR|AIR)\s*(?<p>\d{1,5})", RegexOptions.IgnoreCase)]
    private static partial Regex ReportedRx();
    [GeneratedRegex(@"(?<t>\b[A-Z][A-Za-z]{0,14}\.?(?:\s?\(?[A-Za-z]{1,6}\)?\.?){0,3})\s*(?:No\.?\s*)?(?<n>\d{1,6})\s*(?:/|\s+of\s+)\s*(?<y>(?:19|20)\d{2})\b")]
    private static partial Regex CaseRx();
    // C14 WP1: AIR ("AIR 1987 SC 2386") and SCALE ("2013 (7) SCALE 123") reports.
    [GeneratedRegex(@"\bAIR\s*(?<y>(?:19|20)\d{2})\s*(?<c>S\.?\s?C\.?|[A-Z][A-Za-z&]{1,14})\s*(?<p>\d{1,5})\b")]
    private static partial Regex AirRx();
    [GeneratedRegex(@"\b(?<y>(?:19|20)\d{2})\s*\(\s*(?<v>\d{1,2})\s*\)\s*SCALE\s*(?<p>\d{1,5})\b", RegexOptions.IgnoreCase)]
    private static partial Regex ScaleRx();

    static IEnumerable<Match> ReportedMatches(string q) =>
        ReportedRx().Matches(q).Concat(AirRx().Matches(q)).Concat(ScaleRx().Matches(q)).OrderBy(m => m.Index);

    /// Reported citations printed in the masthead of page 1 (the first 600 characters: report name, volume, page).
    /// Captured as candidate parallel citations of the judgment itself; later text on page 1 may cite other cases,
    /// so it is not read. Extracted, not verified.
    public static IEnumerable<string> MastheadCitations(string page1)
    {
        var head = page1.Length > 600 ? page1[..600] : page1;
        foreach (var m in ReportedMatches(head)) yield return NormCitation(m.Value);
    }

    static readonly Dictionary<string, string> CaseTypes = new()
    {
        ["civilappeal"] = "ca", ["civilappeals"] = "ca", ["criminalappeal"] = "crla", ["originalapplication"] = "oa",
        ["transferapplication"] = "ta", ["writpetition"] = "wp", ["writpetitionc"] = "wpc", ["writpetitioncivil"] = "wpc",
        ["wpcivil"] = "wpc", ["civilwritpetition"] = "cwp", ["miscellaneousapplication"] = "ma", ["specialleavepetition"] = "slp",
        ["slpc"] = "slpc", ["letterspatentappeal"] = "lpa",
    };

    /// Canonical case-type code. Text before the type ("UNION OF INDIA & ORS. (Civil Appeal No.") is dropped by
    /// matching a known long form as a suffix; short codes (OA, CWP, W.P.(C)) are kept as letters.
    public static string NormCaseType(string t)
    {
        var k = Regex.Replace(t.ToLowerInvariant(), "[^a-z]", "");
        if (k.EndsWith("no")) k = k[..^2];
        if (CaseTypes.TryGetValue(k, out var v)) return v;
        foreach (var (longForm, code) in CaseTypes.OrderByDescending(kv => kv.Key.Length))
            if (k.EndsWith(longForm, StringComparison.Ordinal)) return code;
        if (k.Length <= 8) return k;
        var words = Regex.Matches(t, "[A-Za-z]+").Select(m => m.Value.ToLowerInvariant()).ToList();
        return words.Count > 0 ? words[^1] : k;
    }

    public static string NormCitation(string s) => Regex.Replace(s.ToLowerInvariant(), "[^a-z0-9]", "");

    /// Normalised case number "<type><number><year>" or null when the string is not a case number.
    public static string? NormCase(string s)
    {
        var m = CaseRx().Match(s);
        if (!m.Success) return null;
        var t = NormCaseType(m.Groups["t"].Value);
        if (t.Length == 0 || t.Length > 24) return null;
        return t + int.Parse(m.Groups["n"].Value) + m.Groups["y"].Value;
    }

    public static List<QueryIdentifier> Recognise(string q)
    {
        var ids = new List<QueryIdentifier>();
        bool Overlaps(int s, int e) => ids.Any(x => s < x.End && e > x.Start);
        // Reported citations first, so "AIR 1987 SC 2386" is not read as the neutral citation "1987 SC 2386".
        foreach (Match m in ReportedMatches(q))
            if (!Overlaps(m.Index, m.Index + m.Length))
                ids.Add(new QueryIdentifier(IdKind.ReportedCitation, m.Value, NormCitation(m.Value), m.Index, m.Index + m.Length));
        foreach (Match m in NeutralRx().Matches(q))
            if (m.Groups["r"].Value is not ("AND" or "OR" or "NOT" or "NEAR") && !Overlaps(m.Index, m.Index + m.Length))
                ids.Add(new QueryIdentifier(IdKind.NeutralCitation, m.Value, NormCitation(m.Value), m.Index, m.Index + m.Length));
        foreach (Match m in CaseRx().Matches(q))
        {
            if (Overlaps(m.Index, m.Index + m.Length)) continue;
            var t = NormCaseType(m.Groups["t"].Value);
            if (t.Length == 0 || t.Length > 24 || Regex.IsMatch(t, "^(s|sec|section|r|rule|rules|reg|regulation|art|article|para|act|acts|ordinance|notification|order|and|or|not)$")) continue;
            ids.Add(new QueryIdentifier(IdKind.CaseNumber, m.Value.Trim(), t + int.Parse(m.Groups["n"].Value) + m.Groups["y"].Value,
                                        m.Index, m.Index + m.Length));
        }
        foreach (Match m in SectionRx().Matches(q))
        {
            if (Overlaps(m.Index, m.Index + m.Length)) continue;
            var w = m.Groups["w"].Value.ToLowerInvariant();
            var word = w.StartsWith('r') && !w.StartsWith("reg") ? "Rule" : w.StartsWith("reg") ? "Regulation"
                     : w.StartsWith("art") ? "Article" : w.StartsWith("para") ? "Paragraph" : "Section";
            var sub = Regex.Replace(m.Groups["sub"].Value, @"\s", "");
            var n = m.Groups["n"].Value.ToUpperInvariant();
            ids.Add(new QueryIdentifier(IdKind.Section, m.Value, (n + sub).ToLowerInvariant(), m.Index, m.Index + m.Length, n, sub, word));
        }
        return ids.OrderBy(x => x.Start).ToList();
    }

    /// Identifiers printed near the top of page 1 (cover). Extracted, not verified; used only for the identifier tier.
    public static IEnumerable<string> CoverCaseNumbers(string page1)
    {
        var head = page1.Length > 1500 ? page1[..1500] : page1;
        foreach (Match m in CaseRx().Matches(head))
        {
            var t = NormCaseType(m.Groups["t"].Value);
            if (t.Length is > 0 and <= 24) yield return t + int.Parse(m.Groups["n"].Value) + m.Groups["y"].Value;
        }
        foreach (Match m in NeutralRx().Matches(head)) yield return NormCitation(m.Value);
    }

    /// Raw case-number strings printed near the top of page 1 (for display as unverified candidates).
    public static IEnumerable<string> CoverCaseNumberStrings(string page1)
    {
        var head = page1.Length > 1500 ? page1[..1500] : page1;
        foreach (Match m in CaseRx().Matches(head))
        {
            var t = NormCaseType(m.Groups["t"].Value);
            if (t.Length is > 0 and <= 24 && !Regex.IsMatch(t, "^(s|sec|section|r|rule|rules|act|acts|order|and|or|not)$"))
            {
                var v = Regex.Replace(m.Value.Trim(), @"\s+", " ");
                var lf = Regex.Match(v, @"\b(?:Civil|Criminal|Writ|Original|Special|Transfer|Miscellaneous|Letters)\b.*", RegexOptions.IgnoreCase);
                yield return lf.Success ? lf.Value : v;
            }
        }
    }

    /// Does a passage state or refer to provision `base(sub)`? Returns 0 (no), 1 (a reference such as "section 69"),
    /// 2 (a heading line "69. Civil offences." in a statute) or 3 (a heading followed by the provision text "69. ...—").
    /// Headings count only in statute documents; "Section 117" never matches 17; a sub-clause, when given, must match.
    public static int ProvisionStrength(string text, string baseNo, string? sub, bool statute)
    {
        var b = Regex.Escape(baseNo);
        var s = string.IsNullOrEmpty(sub) ? "" : string.Concat(Regex.Matches(sub, @"\(([0-9a-zA-Z]{1,4})\)").Select(x => @"\s*\(" + Regex.Escape(x.Groups[1].Value) + @"\)"));
        int best = 0;
        if (statute)
        {
            var head = new Regex(@"(?m)^\s*\[?(?:(?:Section|Rule|Regulation|Article)\s+)?" + b + (s.Length > 0 ? s : @"(?![0-9A-Za-z])(?:\s*\([0-9a-zA-Z]{1,4}\))*") + @"\s*[.\-–—]\s*(?<rest>[^\n]*)");
            foreach (Match m in head.Matches(text))
            {
                var rest = m.Groups["rest"].Value;
                if (rest.Length == 0) continue;
                best = Math.Max(best, rest.Contains('—') || rest.Contains("Omitted", StringComparison.OrdinalIgnoreCase) || rest.Length > 90 ? 3 : 2);
            }
        }
        if (best == 0)
        {
            var refRx = new Regex(@"(?<![\w])(?:sections?|secs?\.?|ss?\.|rules?|r\.|regulations?|regs?\.|articles?|arts?\.)\s*" + b + @"(?![0-9A-Za-z])" + s,
                                  RegexOptions.IgnoreCase);
            if (refRx.IsMatch(text)) best = 1;
        }
        return best;
    }

    public static bool PassageHasProvision(string text, string baseNo, string? sub, bool statute) =>
        ProvisionStrength(text, baseNo, sub, statute) > 0;
}
