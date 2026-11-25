// Table of contents for Acts and Rules, read from the verified derived text: lines that begin "<number>. <heading>".
// The body occurrence ("69. Civil offences.—Subject to ...") is preferred over the arrangement list entry. Heading
// text is shown as printed in the held copy (a compilation for India Code Acts); nothing is normalised or inferred.
using System.Text.RegularExpressions;

namespace Mimamsa.Core.Generation;

public sealed record TocEntry(string Number, string Heading, int Page, string? PassageId, bool Omitted);

public static partial class Toc
{
    [GeneratedRegex(@"(?m)^[ \t]*(?<n>\d{1,3}[A-Z]{0,2})\.[ \t]+(?<h>\S[^\n]{0,180})")]
    private static partial Regex Heading();

    public static List<TocEntry> Build(DocumentRecord d)
    {
        var best = new Dictionary<string, (TocEntry e, int rank)>();
        foreach (var page in d.Pages.Values.OrderBy(p => p.Page))
            foreach (Match m in Heading().Matches(page.Text))
            {
                var n = m.Groups["n"].Value; var h = m.Groups["h"].Value.Trim();
                int dash = h.IndexOf('—');
                bool body = dash > 0;
                var heading = (body ? h[..dash] : h).TrimEnd('.', ' ');
                if (heading.Length < 2 || !char.IsLetter(heading.TrimStart('[')[0]) || !char.IsUpper(heading.TrimStart('[')[0])) continue;
                // "[Field punishment.] Omitted by ..." (bracketed heading) is how the compilation prints an omitted section;
                // footnote lines ("4. The words ... omitted, ibid") are not headings and rank lowest.
                bool omitted = h.StartsWith('[') && h.Contains("Omitted", StringComparison.Ordinal);
                int rank = body || (omitted && h.Length > 15) ? 3 : omitted ? 2 : h.Contains("omitted", StringComparison.OrdinalIgnoreCase) || h.Contains("Subs.") || h.Contains("Ins.") ? 0 : 1;
                if (rank == 0) continue;
                var pid = d.Passages.Where(p => p.Page == page.Page && p.CharStart <= m.Index && m.Index < p.CharEnd).Select(p => p.PassageId).FirstOrDefault();
                var e = new TocEntry(n, heading.Length > 120 ? heading[..120] + "…" : heading, page.Page, pid, omitted);
                if (!best.TryGetValue(n, out var cur) || rank > cur.rank) best[n] = (e, rank);
            }
        return best.Values.Select(x => x.e)
            .OrderBy(e => int.Parse(Regex.Match(e.Number, @"^\d+").Value)).ThenBy(e => e.Number, StringComparer.Ordinal).ToList();
    }
}
