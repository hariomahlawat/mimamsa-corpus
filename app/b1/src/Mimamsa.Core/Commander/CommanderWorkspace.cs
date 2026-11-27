// C15 WP5: Commander workspace. Task-oriented research pages built ONLY from provisions held in this library, with
// headings and excerpts AS PRINTED in the held copy. There is no separate reasoning system: a domain is a fixed set of
// navigation groupings (chosen for unit commanders) whose items are resolved against the held text through
// ICommanderSource. Nothing here decides what applies to a case; every page is a candidate research aid.
//
// Integration seam: ICommanderSource is the only way this module reads the corpus. The default TocCommanderSource uses
// the held tables of contents (the same data as the C14 Commander home). When the C15 graph/reasoning API
// (docs/architecture/b1/C15_GRAPH_API.md, stream S3) is integrated, a graph-backed source replaces it without changing
// the API or the UI. Eligibility (withdrawal, restriction) is applied by the caller on every response.
using System.Text.RegularExpressions;
using Mimamsa.Core.Generation;
using Mimamsa.Core.Statutes;

namespace Mimamsa.Core.Commander;

/// One provision reference: instrument family ("doc:<id>" or "no:<act number>"), kind (Section/Rule) and number.
public sealed record ProvisionRef(string Family, string Kind, string Number);

/// A provision resolved against a held copy. Heading and excerpt are verbatim from the held text, never paraphrased.
public sealed record ResolvedProvision(string DocId, string Instrument, string Kind, string Number, string? Heading, int? Page,
                                       string? PassageId, bool Omitted, string? Excerpt, bool Found);

public interface ICommanderSource
{
    string Description { get; }
    /// Null when the instrument itself is not held; Found=false when it is held but the provision was not located.
    ResolvedProvision? Resolve(ProvisionRef r);
}

public sealed record CommanderGroup(string Label, string Note, IReadOnlyList<ProvisionRef> Items);

public sealed record CommanderDomain(string Id, string Title, string Purpose, IReadOnlyList<CommanderGroup> Groups,
                                     IReadOnlyList<ProvisionRef> Safeguards, IReadOnlyList<string> FormQueries, IReadOnlyList<string> ReviewQuestions);

public static class CommanderDomains
{
    public const string Label = "Candidate / research aid — not legal advice";
    public const string Disclaimer = "This page groups provisions held in this library under a commander's task heading. Headings and excerpts are " +
        "printed text from the held copy. The grouping is a navigation aid chosen for this workspace: it is not a prescribed sequence, does not " +
        "decide which provision applies to a case, and is not legal advice. Applicability, dates, amendments and savings need legal review.";

    const string AA = "no:46 of 1950", AR = "doc:rules-army-rules-1954", AFT = "no:55 of 2007";
    static ProvisionRef S(string n) => new(AA, "Section", n);
    static ProvisionRef R(string n) => new(AR, "Rule", n);
    static ProvisionRef T(string n) => new(AFT, "Section", n);

    /// The six initial domains (owner directive, Cycle 15 WP5). Provision numbers were checked against the headings printed
    /// in the held copies (see WORKSPACE_STUDIO_REPORT.md §2); an item whose heading does not fit is removed, not relabelled.
    public static readonly IReadOnlyList<CommanderDomain> All = new List<CommanderDomain>
    {
        new("disciplinary", "Disciplinary matters",
            "Offences, investigation and hearing of a charge, and disposal by a commanding officer or a court-martial.",
            new[]
            {
                new CommanderGroup("Hearing the charge", "Rules on the hearing of a charge, the summary of evidence and remand.", new[] { R("22"), R("23"), R("24") }),
                new CommanderGroup("Disposal by a commanding officer", "Summary disposal and its limits.", new[] { S("80"), S("81"), S("83"), S("84") }),
                new CommanderGroup("Courts-martial", "Kinds of courts-martial and the summary court-martial.", new[] { S("108"), S("116"), S("120") }),
                new CommanderGroup("Custody", "Custody of a person charged and the commanding officer's duties.", new[] { S("101"), S("102"), S("103") }),
            },
            new[] { S("122"), R("180") },
            new[] { "charge-sheet" },
            new[]
            {
                "Which procedural stage has been reached, and is the charge framed for that stage?",
                "Which version of each provision applies on the date of the alleged act and on the date of each procedural step?",
                "Is the officer acting competent for this step and this person's rank and service status?",
                "Do the time limits for trial apply, and have they been checked against the held text?",
                "Are there adverse or contrary judgments on this procedure?",
            }),
        new("court-of-inquiry", "Court of Inquiry",
            "Assembly and procedure of courts of inquiry, and protections where a person's character or military reputation is involved.",
            new[]
            {
                new CommanderGroup("Assembly and procedure", "Rules on courts of inquiry.", new[] { R("177"), R("179"), R("181"), R("182") }),
                new CommanderGroup("Character or reputation involved", "The rule on full opportunity to the person concerned.", new[] { R("180") }),
                new CommanderGroup("Inquiry into absence", "Statutory inquiry after absence without leave.", new[] { S("106") }),
            },
            new[] { R("180"), R("184") },
            new[] { "\"court of inquiry\" act:\"Army Rules\"" },
            new[]
            {
                "Who is the convening authority, and is the purpose of the inquiry recorded?",
                "Is the character or military reputation of any person likely to be affected, so that the protection rule applies?",
                "Has every affected person been given the opportunity the held rule describes, and is that recorded?",
                "Which use may be made of the inquiry's record in later proceedings?",
            }),
        new("summary-of-evidence", "Summary of Evidence",
            "Recording of the summary of evidence and the abstract of evidence before a court-martial.",
            new[]
            {
                new CommanderGroup("Hearing the charge", "The rule the summary follows from.", new[] { R("22") }),
                new CommanderGroup("Recording the summary", "The rule on taking down the summary of evidence.", new[] { R("23") }),
                new CommanderGroup("Remand after the summary", "The rule on remand of the accused.", new[] { R("24") }),
            },
            new[] { R("23") },
            new[] { "\"summary of evidence\" act:\"Army Rules\"" },
            new[]
            {
                "Has the accused had the opportunity the held rule gives to cross-examine and to make a statement?",
                "Is every witness statement recorded as the held rule requires, including any caution?",
                "Which disposal does the held remand rule allow after the summary, and who decides it?",
                "Is there any defect in the summary that a court has treated as material?",
            }),
        new("administrative-action", "Administrative action",
            "Termination of service, dismissal, removal or reduction, and remedies of aggrieved persons.",
            new[]
            {
                new CommanderGroup("Tenure and termination", "Statutory provisions on tenure and termination of service.", new[] { S("18"), S("19"), S("20"), S("22") }),
                new CommanderGroup("Remedies of aggrieved persons", "Complaints by officers and other persons.", new[] { S("26"), S("27") }),
                new CommanderGroup("Rules on termination", "Rules made under the Act.", new[] { R("13"), R("14"), R("17") }),
            },
            new[] { R("14"), S("27") },
            Array.Empty<string>(),
            new[]
            {
                "Is the proposed action administrative or disciplinary, and does the choice of route raise any issue?",
                "Which authority is competent for this action, rank and service status?",
                "Has the show-cause or opportunity requirement of the held rule been met and recorded?",
                "Are there judgments on the use of administrative action where a trial was practicable?",
            }),
        new("service-pension", "Service and pension matters",
            "The Armed Forces Tribunal's jurisdiction over service matters and the conditions for an application.",
            new[]
            {
                new CommanderGroup("Tribunal jurisdiction", "Jurisdiction of the Armed Forces Tribunal.", new[] { T("14"), T("15") }),
                new CommanderGroup("Applications", "Conditions and limitation for applications.", new[] { T("21"), T("22") }),
                new CommanderGroup("Release and discharge", "Rules on release and discharge.", new[] { R("13") }),
            },
            new[] { T("21") },
            new[] { "\"disability pension\"", "\"invalided\" act:\"Army Rules\"" },
            new[]
            {
                "Which pension or entitlement rules apply on the relevant dates? (The Army pension regulations and Entitlement Rules are not held in this library.)",
                "Have the remedies required before an application been exhausted, and is the application within time?",
                "Do recent judgments on attributability or aggravation bear on the facts?",
            }),
        new("forms", "Forms and procedural references",
            "Forms and appendices printed in the held Rules and Acts, found by search. Not a form registry.",
            new[]
            {
                new CommanderGroup("Rules that refer to forms", "Rules on the hearing of a charge and the summary of evidence.", new[] { R("22"), R("23") }),
            },
            Array.Empty<ProvisionRef>(),
            new[] { "\"form\" act:\"Army Rules\"", "appendix act:\"Army Rules\"", "charge-sheet" },
            new[]
            {
                "Is the form found here the current, applicable version for the date and procedure? (No form in this library is verified or approved.)",
                "Is the form prescribed, or a specimen only?",
                "Which entries, signatures or certificates must a competent person complete, and when?",
            }),
    };

    public static CommanderDomain? Get(string id) => All.FirstOrDefault(d => d.Id == id);
}

/// Default source: the held table of contents of each instrument (the same resolution as the C14 Commander home), with
/// an excerpt from the held text of the provision (up to ~420 characters, from its heading).
public sealed partial class TocCommanderSource(GenerationStore g) : ICommanderSource
{
    public string Description => "held tables of contents (C14 statute relations)";
    readonly Dictionary<string, (DocumentRecord doc, List<TocEntry> toc)?> _tocs = new();
    readonly object _lock = new();

    (DocumentRecord doc, List<TocEntry> toc)? TocOf(string family)
    {
        lock (_lock)
        {
            if (_tocs.TryGetValue(family, out var c)) return c;
            var rel = g.Relations;
            var id = family.StartsWith("doc:", StringComparison.Ordinal) ? family[4..] : rel.Instruments.FirstOrDefault(x => x.Key == family)?.PrimaryDocId;
            c = id is not null && g.Documents.TryGetValue(id, out var d) ? (d, Toc.Build(d)) : null;
            _tocs[family] = c;
            return c;
        }
    }

    [GeneratedRegex(@"\s+")] private static partial Regex Ws();

    public ResolvedProvision? Resolve(ProvisionRef r)
    {
        var t = TocOf(r.Family);
        if (t is null) return null;
        var (d, toc) = t.Value;
        var e = toc.FirstOrDefault(x => x.Number.Equals(r.Number, StringComparison.OrdinalIgnoreCase));
        if (e is null) return new ResolvedProvision(d.DocId, d.Title ?? d.DocId, r.Kind, r.Number, null, null, null, false, null, false);
        int page = BodyPage(d, e);
        var passage = page == e.Page ? e.PassageId : d.Passages.FirstOrDefault(p => p.Page == page)?.PassageId;
        return new ResolvedProvision(d.DocId, d.Title ?? d.DocId, r.Kind, r.Number, e.Heading, page, passage, e.Omitted, Excerpt(d, e.Number, page), true);
    }

    /// The table of contents can point at the "arrangement of sections" page, where the numbered heading is also printed.
    /// The provision's own text comes after it, so the LAST page on which "<number>. <start of heading>" begins a line is
    /// taken; if the heading is not found elsewhere, the table-of-contents page is kept.
    static int BodyPage(DocumentRecord d, TocEntry e)
    {
        var head = Regex.Replace(e.Heading, @"\s+", " ").Trim();
        var start = head.Length > 18 ? head[..18] : head;
        var words = Regex.Escape(start).Replace(@"\ ", @"\s+");
        var rx = new Regex(@"(?m)^[ \t]*" + Regex.Escape(e.Number) + @"\.\s*\[?" + words, RegexOptions.IgnoreCase);
        var pages = d.Pages.Where(kv => rx.IsMatch(kv.Value.Text)).Select(kv => kv.Key).ToList();
        return pages.Count == 0 ? e.Page : pages.Max();
    }

    static string? Excerpt(DocumentRecord d, string number, int page)
    {
        if (!d.Pages.TryGetValue(page, out var pg)) return null;
        var m = Regex.Match(pg.Text, @"(?m)^[ \t]*" + Regex.Escape(number) + @"\.\s+");
        var start = m.Success ? m.Index : 0;
        var s = Ws().Replace(pg.Text[start..], " ").Trim();
        return s.Length > 420 ? s[..420] + "…" : s;
    }
}
