// Candidate correspondence edges between the 2023 criminal codes and the codes they replace (C14 F03), read
// deterministically from the comparison tables held in this library (Bureau of Police Research and Development
// correspondence tables, ref-bprd-comparison-*). Those tables are SECONDARY sources. Every edge is a candidate with
// its evidence (table document, page and the row text as printed); nothing is verified or approved, and an edge
// never asserts that two provisions are legally interchangeable.
//
// Table layout in the extracted text (one cell per line or several cells on one line):
//   <new section> <subject…> <old section | New | -> <summary of comparison…>
// Rows appear in ascending order of the new section. A line is accepted as a row head only when its section number is
// not lower than the previous head and at most MaxJump higher (old-code section numbers inside summaries are usually
// far from the current new section), and when it is followed by something that looks like a subject or an old section
// rather than summary prose. Rows that cannot be read this way are skipped, not guessed.
using System.Text.RegularExpressions;
using Mimamsa.Core.Generation;

namespace Mimamsa.Core.Statutes;

/// A held comparison table: which family is the new code and which the old (family keys as InstrumentCatalog.FamilyKey).
public sealed record CorrespondenceTable(string DocId, string NewFamily, string OldFamily, string NewName, string OldName, int NewMax);

public sealed record CorrespondenceEdge(string TableDocId, string NewFamily, string OldFamily, string NewName, string OldName,
                                        string NewSection, string NewBase, string? OldSection, IReadOnlyList<string> OldBases,
                                        bool NewProvision, int Page, string RowText);

public static partial class Correspondence
{
    public const int MaxJump = 15;

    /// The three tables of the B1 sample. Identified by document id; used only when that document is held and verified.
    public static readonly CorrespondenceTable[] KnownTables =
    {
        new("ref-bprd-comparison-bns-ipc", "no:45 of 2023", "no:45 of 1860", "BNS", "IPC", 358),
        new("ref-bprd-comparison-bnss-crpc", "no:46 of 2023", "no:2 of 1974", "BNSS", "CrPC", 531),
        new("ref-bprd-comparison-bsa-iea", "no:47 of 2023", "no:1 of 1872", "BSA", "IEA", 170),
    };

    const string Sec = @"\d{1,3}[A-Z]{0,2}(?:\s?\(\s?[0-9a-zA-Z]{1,4}\s?\))*";
    [GeneratedRegex(@"^(?<sec>" + Sec + @")(?:\s+(?<rest>.*))?$")] private static partial Regex Head();
    [GeneratedRegex(@"^\(\s?[0-9a-zA-Z]{1,4}\s?\)$")] private static partial Regex SubOnly();
    [GeneratedRegex(@"^(?:(?:IEA|IPC|CrPC)\s+)?(?<old>" + Sec + @"(?:\s*,\s*para\s*\d+)?(?:\s*(?:,|and|&)\s*" + Sec + @"(?:\s*,\s*para\s*\d+)?)*)\s*\]?\s*$")] private static partial Regex OldLine();
    [GeneratedRegex(@"^(?<old>" + Sec + @")\s*\]?\s+(?<text>\S.*)$")] private static partial Regex OldStart();
    [GeneratedRegex(@"^(?<text>.*[A-Za-z.)”""'])\s+(?<old>\d{1,3}[A-Z]{0,2}(?:\(\w{1,4}\))*)$")] private static partial Regex OldEnd();
    [GeneratedRegex(@"^(?:New\b.*|Newly\b.*|[-–—]+)$")] private static partial Regex NewMark();
    [GeneratedRegex(@"\d{1,3}[A-Z]{0,2}")] private static partial Regex BaseTok();
    // Codex review of PR #70: sub-section parts ("(1)", "( 2 )", "(a)") are removed before base sections are read, so
    // "320(1)" yields 320 and "65B(2)" yields 65B, never a spurious section 1 or 2.
    [GeneratedRegex(@"\(\s?[0-9a-zA-Z]{1,4}\s?\)")] private static partial Regex SubPart();
    [GeneratedRegex(@",\s*para\s*\d+")] private static partial Regex Para();

    static readonly string[] SummaryStarts = { "No change", "No ", "Section ", "IPC ", "CrPC ", "IEA ", "BNS ", "BNSS ", "BSA ", "Words ", "Word ",
        "This ", "Formal", "Newly", "Minimum", "However", "Further", "In the ", "In IPC", "In CrPC", "In IEA", "Sub-section", "Subsection", "©" };

    public static string Base(string sec) => Regex.Match(sec, @"^\d{1,3}[A-Z]{0,2}").Value;
    static int Num(string sec) => int.Parse(Regex.Match(sec, @"^\d+").Value);
    static string Clean(string sec) => Regex.Replace(sec, @"\s+", "");

    static bool LooksLikeRowStart(string s)
    {
        if (s.Length == 0) return false;
        if (OldLine().IsMatch(s) || NewMark().IsMatch(s)) return true;   // "IEA 3", "65A", "New", "-"
        if (SummaryStarts.Any(p => s.StartsWith(p, StringComparison.Ordinal))) return false;
        char c = s[0];
        return char.IsUpper(c) || c is '"' or '“' or '\'' or '‘' or '[' || NewMark().IsMatch(s) || OldLine().IsMatch(s) || OldStart().IsMatch(s);
    }

    /// Parse one table document's pages (page number -> text) into candidate edges.
    public static List<CorrespondenceEdge> Parse(CorrespondenceTable t, IEnumerable<(int page, string text)> pages)
    {
        var lines = new List<(int page, string line)>();
        foreach (var (page, text) in pages.OrderBy(p => p.page))
            foreach (var raw in text.Split('\n'))
            {
                var l = raw.Trim();
                if (l.Length == 0 || l.StartsWith('©')) continue;
                lines.Add((page, l));
            }

        // pass 1: row heads
        var heads = new List<(int idx, string sec, string? rest, int skip)>();
        int prev = 0;
        for (int i = 0; i < lines.Count; i++)
        {
            var m = Head().Match(lines[i].line);
            if (!m.Success) continue;
            var sec = Clean(m.Groups["sec"].Value);
            var rest = m.Groups["rest"].Success ? m.Groups["rest"].Value.Trim() : "";
            int skip = 0;
            if (!sec.Contains('(') && rest.Length == 0 && i + 1 < lines.Count && SubOnly().IsMatch(lines[i + 1].line))
            { sec += Clean(lines[i + 1].line); skip = 1; }
            int n = Num(sec);
            if (n < 1 || n > t.NewMax || n < prev || (heads.Count > 0 && n - prev > MaxJump)) continue;
            var follow = rest.Length > 0 ? rest : (i + 1 + skip < lines.Count ? lines[i + 1 + skip].line : "");
            if (!LooksLikeRowStart(follow)) continue;
            heads.Add((i, sec, rest.Length > 0 ? rest : null, skip));
            prev = n;
            // the old-section cell on the next line ("1 Short title…" in the BSA table) is not itself a row head
            int consumed = rest.Length == 0 && (OldStart().IsMatch(follow) || OldLine().IsMatch(follow)) ? 1 : 0;
            i += skip + consumed;
        }

        // pass 2: the old section of each row
        var edges = new List<CorrespondenceEdge>();
        for (int h = 0; h < heads.Count; h++)
        {
            var (idx, sec, rest, skip) = heads[h];
            int end = h + 1 < heads.Count ? heads[h + 1].idx : Math.Min(lines.Count, idx + 40);
            var block = new List<string>();
            if (rest is not null) block.Add(rest);
            for (int j = idx + 1 + skip; j < end; j++) block.Add(lines[j].line);
            string? old = null; bool isNew = false;
            foreach (var l in block.Take(7))
            {
                if (NewMark().IsMatch(l)) { isNew = true; break; }
                if (OldLine().Match(l) is { Success: true } ol) { old = ol.Groups["old"].Value; break; }
                if (OldStart().Match(l) is { Success: true } os && !SummaryStarts.Any(p => l.StartsWith(p, StringComparison.Ordinal)))
                {
                    var txt = os.Groups["text"].Value;
                    if (txt.StartsWith("New", StringComparison.Ordinal)) { isNew = true; break; }
                    old = os.Groups["old"].Value; break;
                }
                if (OldEnd().Match(l) is { Success: true } oe && oe.Groups["text"].Value.Any(char.IsLetter)) { old = oe.Groups["old"].Value; break; }
            }
            if (old is null && !isNew) continue;   // unreadable row: skipped, not guessed
            var bases = old is null ? new List<string>()
                : BaseTok().Matches(SubPart().Replace(Para().Replace(old, ""), "")).Select(x => x.Value).Where(b => int.Parse(Regex.Match(b, @"^\d+").Value) > 0).Distinct().ToList();
            var rowText = Regex.Replace(string.Join(" ", new[] { sec }.Concat(block.Take(12))), @"\s+", " ").Trim();
            if (rowText.Length > 420) rowText = rowText[..420] + "…";
            edges.Add(new CorrespondenceEdge(t.DocId, t.NewFamily, t.OldFamily, t.NewName, t.OldName, sec, Base(sec),
                old is null ? null : Regex.Replace(old.Trim().TrimEnd(']'), @"\s+", " "), bases, isNew, lines[idx].page, rowText));
        }
        return edges;
    }

    public static List<CorrespondenceEdge> FromDocument(CorrespondenceTable t, DocumentRecord d) =>
        Parse(t, d.Pages.Values.Select(p => (p.Page, p.Text)));
}
