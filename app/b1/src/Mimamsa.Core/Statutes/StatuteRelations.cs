// Statutory relationships for display (C14 F03): instrument catalogue, candidate correspondence edges and
// evidence-linked notices on commencement, repeal, savings and transitional text. Every notice quotes the held,
// verified text it was read from (document, page, quote). Nothing here is a legal determination: commencement dates,
// whether a provision applies to a case, and the effect of savings clauses are NOT decided. Correspondence between
// provisions comes from a secondary comparison table and never means the provisions are interchangeable.
using System.Text.RegularExpressions;
using Mimamsa.Core.Generation;

namespace Mimamsa.Core.Statutes;

public sealed record RelationEvidence(string DocId, int Page, string Quote);

/// kind: commencement_delegated | commencement_secondary_source | commencement_notification_not_held | repeal | savings_transitional | repealed_by
public sealed record StatuteNotice(string Kind, string Title, string Text, RelationEvidence? Evidence, string Basis);

public sealed record CommanderTask(string Task, string Purpose, IReadOnlyList<CommanderItem> Items);
public sealed record CommanderItem(string Family, string Kind, string Number, string? DocId, string? Heading, int? Page, bool Omitted, bool Found);

public sealed partial class StatuteRelations
{
    public const string Caution = "Correspondence is read from a secondary comparison table held in this library. Corresponding provisions are not " +
        "legally interchangeable: wording, ingredients, punishments and application dates can differ. Which law applies depends on the date of the " +
        "act and on the repeal and savings provisions, and is not determined here.";

    public required IReadOnlyList<Instrument> Instruments { get; init; }
    public required IReadOnlyDictionary<string, string> FamilyOfDoc { get; init; }
    public required IReadOnlyList<CorrespondenceEdge> Edges { get; init; }
    public required IReadOnlyDictionary<string, List<StatuteNotice>> Notices { get; init; }
    public required IReadOnlyList<CommanderTask> CommanderTasks { get; init; }
    public required IReadOnlyDictionary<string, string> TableStatus { get; init; }

    public Instrument? InstrumentOf(string docId) =>
        FamilyOfDoc.TryGetValue(docId, out var f) ? Instruments.FirstOrDefault(i => i.Key == f) : null;
    public Instrument? Family(string key) => Instruments.FirstOrDefault(i => i.Key == key);

    /// Edges touching a provision of the given family: as the new section (base match) or as one of the old sections.
    public IEnumerable<CorrespondenceEdge> EdgesFor(string family, string baseSection) =>
        Edges.Where(e => (e.NewFamily == family && e.NewBase.Equals(baseSection, StringComparison.OrdinalIgnoreCase))
                      || (e.OldFamily == family && e.OldBases.Contains(baseSection, StringComparer.OrdinalIgnoreCase)));

    [GeneratedRegex(@"^Repeal and savings", RegexOptions.IgnoreCase)] private static partial Regex RepealHeading();
    [GeneratedRegex(@"come\s+into\s+force\s+on\s+such\s+date\d{0,2}\s+as\s+the\s+Central\s+Government\s+may,?\s+by\s+notification[^.]{0,200}\.", RegexOptions.IgnoreCase)] private static partial Regex Delegated();
    [GeneratedRegex(@"[^.\n]{0,160}\b(?:1st|1)\s+July,?\s+2024\b[^.\n]{0,160}", RegexOptions.IgnoreCase)] private static partial Regex July2024();

    static readonly Dictionary<string, string> OldNames = new()
    {
        ["no:45 of 1860"] = "Indian Penal Code", ["no:2 of 1974"] = "Code of Criminal Procedure", ["no:1 of 1872"] = "Indian Evidence Act",
    };

    static string Squash(string s) => Regex.Replace(s, @"\s+", " ").Trim();

    /// Text of a section from its heading to the next section heading (same page and the following page), at most max chars.
    static (int page, string text)? SectionText(DocumentRecord d, TocEntry e, int max = 2400)
    {
        if (!d.Pages.TryGetValue(e.Page, out var pg)) return null;
        var rx = new Regex(@"(?m)^[ \t]*" + Regex.Escape(e.Number) + @"\.[ \t]+");
        var m = rx.Match(pg.Text);
        var start = m.Success ? m.Index : 0;
        var text = pg.Text[start..] + (d.Pages.TryGetValue(e.Page + 1, out var nx) ? "\n" + nx.Text : "");
        var next = Regex.Match(text[Math.Min(text.Length, 8)..], @"(?m)^[ \t]*\d{1,3}[A-Z]{0,2}\.[ \t]+[A-Z\[]");
        if (next.Success) text = text[..(next.Index + 8)];
        return (e.Page, text.Length > max ? text[..max] : text);
    }

    public static StatuteRelations Build(GenerationStore g)
    {
        var statutes = g.Documents.Values.Where(d => d.IsStatute).ToList();
        var instruments = InstrumentCatalog.Build(statutes, g.Documents);
        var familyOfDoc = new Dictionary<string, string>(StringComparer.Ordinal);
        foreach (var d in statutes) familyOfDoc[d.DocId] = InstrumentCatalog.FamilyKey(d, g.Documents);
        DocumentRecord? Primary(string fam) => instruments.FirstOrDefault(i => i.Key == fam) is { } i && g.Documents.TryGetValue(i.PrimaryDocId, out var d) ? d : null;

        var edges = new List<CorrespondenceEdge>();
        var tableStatus = new Dictionary<string, string>();
        var notices = new Dictionary<string, List<StatuteNotice>>();
        void Add(string fam, StatuteNotice n) => (notices.TryGetValue(fam, out var l) ? l : notices[fam] = new()).Add(n);

        foreach (var t in Correspondence.KnownTables)
        {
            if (!g.Documents.TryGetValue(t.DocId, out var td) || !td.OriginalVerified || td.DerivativeId is null) { tableStatus[t.DocId] = "not held"; continue; }
            var es = Correspondence.FromDocument(t, td);
            edges.AddRange(es);
            tableStatus[t.DocId] = $"{es.Count} candidate rows read";

            var newDoc = Primary(t.NewFamily);
            if (newDoc is null) continue;
            var toc = Toc.Build(newDoc);
            // commencement: delegated by the enacting text
            foreach (var pg in newDoc.Pages.Values.OrderBy(p => p.Page))
                if (Delegated().Match(pg.Text) is { Success: true } dm)
                {
                    Add(t.NewFamily, new StatuteNotice("commencement_delegated", "Commencement (enacting text)",
                        $"The held text of the {t.NewName} leaves the date of commencement to a Central Government notification.",
                        new RelationEvidence(newDoc.DocId, pg.Page, Squash(dm.Value)), "Quoted from the held text of the Act."));
                    break;
                }
            Add(t.NewFamily, new StatuteNotice("commencement_notification_not_held", "Commencement notification",
                "No commencement notification for this code is identified in this library. The date is therefore not established from primary text here.",
                null, "No held document is linked as the commencement notification."));
            // a secondary source stating the date (the comparison table itself)
            foreach (var pg in td.Pages.Values.OrderBy(p => p.Page))
                if (July2024().Match(pg.Text) is { Success: true } jm)
                {
                    Add(t.NewFamily, new StatuteNotice("commencement_secondary_source", "Commencement date stated in a secondary source",
                        "A secondary comparison table held in this library mentions 1 July 2024. A secondary source does not establish commencement.",
                        new RelationEvidence(td.DocId, pg.Page, Squash(jm.Value)), "Quoted from the comparison table (secondary source)."));
                    break;
                }
            // repeal and savings in the new code
            var rs = toc.FirstOrDefault(e => RepealHeading().IsMatch(e.Heading));
            if (rs is not null && SectionText(newDoc, rs) is { } st)
            {
                var text = st.text;
                int two = Regex.Match(text, @"\(2\)").Index;
                var repealPart = Squash(two > 0 ? text[..two] : text);
                var savingsPart = two > 0 ? Squash(text[two..]) : null;
                Add(t.NewFamily, new StatuteNotice("repeal", $"Repeal: section {rs.Number} of the {t.NewName}",
                    "Repealing text as printed in the held copy.", new RelationEvidence(newDoc.DocId, st.page, Trunc(repealPart, 600)), "Quoted from the held text."));
                if (savingsPart is not null)
                    Add(t.NewFamily, new StatuteNotice("savings_transitional", $"Savings and transitional text: section {rs.Number}(2) onwards",
                        "Savings for things done and proceedings pending under the repealed law, as printed. Their effect on a particular matter is not determined here.",
                        new RelationEvidence(newDoc.DocId, st.page, Trunc(savingsPart, 900)), "Quoted from the held text."));
                // the old code: repealed by
                if (OldNames.TryGetValue(t.OldFamily, out var oldName))
                {
                    var sentence = Regex.Match(repealPart, @"[^.;]*" + Regex.Escape(oldName) + @"[^.;]*[.;]?", RegexOptions.IgnoreCase);
                    Add(t.OldFamily, new StatuteNotice("repealed_by", $"Repealed by section {rs.Number} of the {t.NewName}",
                        $"The held text of the {t.NewName} repeals this code. Savings and transitional text in the same section can keep it relevant to matters arising before commencement.",
                        new RelationEvidence(newDoc.DocId, st.page, Trunc(sentence.Success ? Squash(sentence.Value) : repealPart, 400)), "Quoted from the held text of the new code."));
                    if (savingsPart is not null)
                        Add(t.OldFamily, new StatuteNotice("savings_transitional", $"Savings and transitional text: section {rs.Number}(2) of the {t.NewName}",
                            "Savings for things done and proceedings pending under this code, as printed in the new code. Their effect on a particular matter is not determined here.",
                            new RelationEvidence(newDoc.DocId, st.page, Trunc(savingsPart, 900)), "Quoted from the held text of the new code."));
                }
            }
        }

        return new StatuteRelations
        {
            Instruments = instruments, FamilyOfDoc = familyOfDoc, Edges = edges, Notices = notices, TableStatus = tableStatus,
            CommanderTasks = BuildTasks(instruments, g),
        };
    }

    static string Trunc(string s, int n) => s.Length > n ? s[..n] + "…" : s;

    // Commander workspace (early): task headings are navigation aids chosen for unit commanders; each item is resolved
    // against the held instrument's table of contents and shows the heading AS PRINTED. Unresolved items say so.
    static readonly (string task, string purpose, (string family, string kind, string number)[] items)[] Tasks =
    {
        ("Investigating an offence and hearing the charge", "Hearing of the charge and recording evidence before any decision.",
            new[] { ("doc:rules-army-rules-1954", "Rule", "22"), ("doc:rules-army-rules-1954", "Rule", "23"), ("doc:rules-army-rules-1954", "Rule", "24") }),
        ("Absence and desertion", "Offence provisions and the procedure when a person absents himself.",
            new[] { ("no:46 of 1950", "Section", "38"), ("no:46 of 1950", "Section", "39"), ("no:46 of 1950", "Section", "106") }),
        ("Arrest and custody", "Custody of persons subject to the Act and the commanding officer's duties.",
            new[] { ("no:46 of 1950", "Section", "101"), ("no:46 of 1950", "Section", "102"), ("no:46 of 1950", "Section", "103") }),
        ("Summary punishment by a commanding officer", "Punishments a commanding officer may award and their limits.",
            new[] { ("no:46 of 1950", "Section", "80"), ("no:46 of 1950", "Section", "81"), ("no:46 of 1950", "Section", "83") }),
        ("Summary court-martial", "Constitution and powers of a summary court-martial.",
            new[] { ("no:46 of 1950", "Section", "116"), ("no:46 of 1950", "Section", "120") }),
        ("Safeguards", "Protections for the person concerned: courts of inquiry affecting character, and offences under civil law.",
            new[] { ("doc:rules-army-rules-1954", "Rule", "180"), ("no:46 of 1950", "Section", "69"), ("no:46 of 1950", "Section", "70") }),
    };

    static List<CommanderTask> BuildTasks(List<Instrument> instruments, GenerationStore g)
    {
        var tocs = new Dictionary<string, (string doc, List<TocEntry> toc)?>();
        (string doc, List<TocEntry> toc)? TocOf(string fam)
        {
            if (tocs.TryGetValue(fam, out var c)) return c;
            // "doc:<id>" names a document directly; "no:<n>" an Act family, resolved to its primary edition
            var id = fam.StartsWith("doc:", StringComparison.Ordinal) ? fam[4..] : instruments.FirstOrDefault(x => x.Key == fam)?.PrimaryDocId;
            c = id is not null && g.Documents.TryGetValue(id, out var d) ? (d.DocId, Toc.Build(d)) : null;
            tocs[fam] = c; return c;
        }
        return Tasks.Select(t => new CommanderTask(t.task, t.purpose, t.items.Select(it =>
        {
            var toc = TocOf(it.family);
            var e = toc?.toc.FirstOrDefault(x => x.Number == it.number);
            return new CommanderItem(it.family, it.kind, it.number, toc?.doc, e?.Heading, e?.Page, e?.Omitted ?? false, e is not null);
        }).ToList())).ToList();
    }
}
