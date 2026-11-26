// Instrument catalogue for the Statutes workspace (C14 F11): one entry per instrument, with its editions, language
// versions and schedules nested under it. Grouping is deterministic and metadata-based:
//   family key = the printed Act number ("46 of 1950") when the record has one; a schedule record (doc_id "<parent>-sched-…")
//   joins its parent's family; otherwise the document is its own family.
// Category is a navigation aid from the title and number only. It is not a legal classification.
using System.Globalization;
using System.Text.RegularExpressions;
using Mimamsa.Core.Generation;

namespace Mimamsa.Core.Statutes;

public sealed record Edition(string DocId, string Label, string? Language, bool IsSchedule, string Title, int PageCount, string DocType, string? Reliability);

public sealed record Instrument(string Key, string Title, string Category, string? Number, string DocType, string PrimaryDocId,
                                IReadOnlyList<Edition> Editions, IReadOnlyList<Edition> Schedules);

public static partial class InstrumentCatalog
{
    public static readonly string[] CategoryOrder =
        { "Army", "Navy", "Air Force", "Armed Forces Tribunal", "Criminal codes (in force from 1 July 2024)", "Criminal codes (repealed; historical)", "Other" };

    // Act numbers of the 2023 codes and of the codes they replace (as printed on the held copies).
    static readonly HashSet<string> NewCodes = new(StringComparer.OrdinalIgnoreCase) { "45 of 2023", "46 of 2023", "47 of 2023" };
    static readonly HashSet<string> OldCodes = new(StringComparer.OrdinalIgnoreCase) { "45 of 1860", "2 of 1974", "1 of 1872" };

    [GeneratedRegex(@"^(?<parent>.+?)-sched-")] private static partial Regex SchedParent();

    public static string? NormNumber(string? n) => string.IsNullOrWhiteSpace(n) ? null : Regex.Replace(n.Trim().ToLowerInvariant(), @"\s+", " ");

    public static string FamilyKey(DocumentRecord d, IReadOnlyDictionary<string, DocumentRecord> all)
    {
        if (NormNumber(d.Number) is { } n) return "no:" + n;
        var m = SchedParent().Match(d.DocId);
        if (m.Success && all.TryGetValue(m.Groups["parent"].Value, out var parent) && NormNumber(parent.Number) is { } pn) return "no:" + pn;
        if (m.Success) return "doc:" + m.Groups["parent"].Value;
        return "doc:" + d.DocId;
    }

    public static bool IsSchedule(DocumentRecord d) => d.DocId.Contains("-sched-", StringComparison.Ordinal);

    /// "THE FIRST SCHEDULE" -> "The First Schedule"; already mixed-case titles are kept as printed.
    public static string TitleCase(string? t)
    {
        if (string.IsNullOrWhiteSpace(t)) return "Untitled";
        t = t.Trim();
        if (t.Any(char.IsLower)) return t;
        var s = CultureInfo.InvariantCulture.TextInfo.ToTitleCase(t.ToLowerInvariant());
        return Regex.Replace(s, @"\b(Of|And|The|To|For|In|On)\b", m => m.Index == 0 ? m.Value : m.Value.ToLowerInvariant());
    }

    public static string Language(DocumentRecord d) =>
        d.Language is "hi" ? "hi" : d.TextAssessment?.DetectedLanguage == "hi" ? "hi" : d.Language ?? d.TextAssessment?.DetectedLanguage ?? "en";

    public static string EditionLabel(DocumentRecord d)
    {
        var parts = new List<string>();
        if (IsSchedule(d)) parts.Add("Schedule: " + TitleCase(d.Title));
        parts.Add(Language(d) == "hi" ? "Hindi" : "English");
        if (d.DocId.Contains("-alt-", StringComparison.Ordinal)) parts.Add("separately published copy");
        if (d.DocId.Contains("consolidated", StringComparison.Ordinal)) parts.Add("consolidated (as amended)");
        if (d.TextAssessment?.Reliability == TextQuality.Unreliable) parts.Add("extracted text unreliable");
        return string.Join(" · ", parts);
    }

    public static string Category(string title, string? number, string docId)
    {
        var n = NormNumber(number);
        if (n is not null && NewCodes.Contains(n)) return CategoryOrder[4];
        if (n is not null && OldCodes.Contains(n)) return CategoryOrder[5];
        var t = title.ToLowerInvariant();
        if (t.Contains("tribunal") || docId.StartsWith("rules-aft", StringComparison.Ordinal) || docId.StartsWith("notif-aft", StringComparison.Ordinal)
            || docId.Contains("armed-forces-tribunal", StringComparison.Ordinal) || docId.StartsWith("notif-jurisdiction", StringComparison.Ordinal)
            || docId.StartsWith("notif-appointed-day-aft", StringComparison.Ordinal)) return CategoryOrder[3];
        if (t.Contains("navy") || t.Contains("naval")) return CategoryOrder[1];
        if (t.Contains("army")) return CategoryOrder[0];
        if (t.Contains("air force")) return CategoryOrder[2];
        return CategoryOrder[6];
    }

    static int PrimaryRank(DocumentRecord d) =>
        (IsSchedule(d) ? 8 : 0) + (Language(d) == "hi" ? 4 : 0) + (d.DocId.Contains("-alt-", StringComparison.Ordinal) ? 2 : 0)
        + (d.DocId.Contains("consolidated", StringComparison.Ordinal) ? 1 : 0);

    public static List<Instrument> Build(IEnumerable<DocumentRecord> statutes, IReadOnlyDictionary<string, DocumentRecord> all)
    {
        var list = new List<Instrument>();
        foreach (var g in statutes.GroupBy(d => FamilyKey(d, all)))
        {
            var members = g.OrderBy(PrimaryRank).ThenBy(d => d.DocId.Length).ThenBy(d => d.DocId, StringComparer.Ordinal).ToList();
            var primary = members[0];
            Edition E(DocumentRecord d) => new(d.DocId, EditionLabel(d), Language(d), IsSchedule(d), TitleCase(d.Title), d.PageCount, d.DocType, d.TextAssessment?.Reliability);
            var title = primary.Title is { Length: > 0 } pt ? TitleCase(pt) : primary.DocId;
            list.Add(new Instrument(g.Key, title, Category(title, primary.Number, primary.DocId), primary.Number, primary.DocType, primary.DocId,
                members.Where(d => !IsSchedule(d)).Select(E).ToList(), members.Where(IsSchedule).Select(E).ToList()));
        }
        return list.OrderBy(i => Array.IndexOf(CategoryOrder, i.Category))
                   .ThenBy(i => i.DocType switch { "act" => 0, "rules" => 1, "regulations" => 2, "order" => 3, _ => 4 })
                   .ThenBy(i => i.Title, StringComparer.OrdinalIgnoreCase).ToList();
    }
}
