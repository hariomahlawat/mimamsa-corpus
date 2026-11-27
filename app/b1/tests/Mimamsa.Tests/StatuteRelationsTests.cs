using Mimamsa.Core.Generation;
using Mimamsa.Core.Statutes;

namespace Mimamsa.Tests;

/// C14 S3: correspondence derivation (F03), text reliability (F07) and the instrument catalogue (F11).
/// The table rows below are synthetic text in the three layouts seen in the held comparison tables.
public class StatuteRelationsTests
{
    static readonly CorrespondenceTable Ipc = new("t-ipc", "no:45 of 2023", "no:45 of 1860", "BNS", "IPC", 358);
    static readonly CorrespondenceTable Iea = new("t-iea", "no:47 of 2023", "no:1 of 1872", "BSA", "IEA", 170);
    static readonly CorrespondenceTable Crpc = new("t-crpc", "no:46 of 2023", "no:2 of 1974", "BNSS", "CrPC", 531);

    static List<CorrespondenceEdge> Parse(CorrespondenceTable t, params string[] pages) =>
        Correspondence.Parse(t, pages.Select((p, i) => (i + 1, p)));

    const string IpcEarly = """
        © header line
        BNS
        Sections
        Subject
        IPC
        Sections
        40
        Commencement of the right of
        private defence of the body.

        102
         No change.
        41
        When the right of defence of
        property extends to causing death.

        103
         Words are replaced in this row.
        42
        When such right extends to causing
        any harm other than death.

        104
         No change.
        """;

    [Fact]
    public void OldSectionNumbersInTheOldColumnNeverBecomeRowHeads()
    {
        var e = Parse(Ipc, IpcEarly);
        Assert.Equal(new[] { "40", "41", "42" }, e.Select(x => x.NewSection));
        Assert.Equal(new[] { "102", "103", "104" }, e.Select(x => x.OldSection));
    }

    const string IpcStyle = """
        102
        Punishment for something else.
        301
         No change.
        103
        Punishment for murder.
        302
        Alternative punishment is added for one clause.
        104
        Punishment for murder by life-
        convict.

        303
        An alternate punishment is given.
        106
        (1)

        Causing death by negligence.
        304A
        IPC section is included as subsection in BNS.
        106
        (2)

        Causing death by negligence.
        -
        This is a new addition kept on hold.
        110
        Attempt to commit culpable homicide. 308
         No change.
        111
        Organized crime.
        -
        Newly added section.
        """;

    [Fact]
    public void IpcLayoutRowsGiveTheOldSectionAndSkipNumbersInsideSummaries()
    {
        var e = Parse(Ipc, IpcStyle);
        string Old(string s) => e.Single(x => x.NewSection == s).OldSection ?? "NEW";
        Assert.Equal("301", Old("102"));
        Assert.Equal("302", Old("103"));
        Assert.Equal("303", Old("104"));
        Assert.Equal("304A", Old("106(1)"));
        Assert.True(e.Single(x => x.NewSection == "106(2)").NewProvision);
        Assert.Equal("308", Old("110"));           // old section printed at the end of the subject line
        Assert.True(e.Single(x => x.NewSection == "111").NewProvision);
        Assert.All(e, x => Assert.Equal(1, x.Page));
        Assert.Contains("Punishment for murder", e.Single(x => x.NewSection == "103").RowText);
    }

    /// Codex review of PR #70: sub-section numbers in the old column are not base sections (no link to "s.1"/"s.2").
    [Fact]
    public void SubsectionNumbersInTheOldColumnAreNotBaseSections()
    {
        var input = System.Text.RegularExpressions.Regex.Replace(IpcStyle, @"(?m)^(\s*)302(\r?)$", "${1}302(1), 303(2)${2}");
        Assert.NotEqual(IpcStyle, input);
        var e = Parse(Ipc, input);
        var row = e.Single(x => x.NewSection == "103");
        Assert.Equal(new[] { "302", "303" }, row.OldBases);
        Assert.Equal("304A", e.Single(x => x.NewSection == "106(1)").OldBases.Single());
    }

    [Fact]
    public void BsaLayoutWithTheOldSectionNextToTheNewOne()
    {
        var e = Parse(Iea, """
            BSA
            Section
            1
            1 Short title, application and
            commencement.

            The extent clause is excluded.
            2 IEA 3
            Interpret
            ation
            clause

            Definitions.
            """);
        var later = Parse(Iea, """
            61  New
            Electronic or digital record.
            "Quoted text of the new provision."
            62 65A
            Special provisions as to evidence
            relating to electronic record.

             No change.
            63 65B
            Admissibility
            of
            electronic
            records.
            """);
        string Old(string s) => e.Single(x => x.NewSection == s).OldSection ?? "NEW";
        Assert.Equal("1", Old("1"));
        Assert.Equal("3", Old("2"));
        Assert.True(later.Single(x => x.NewSection == "61").NewProvision);
        Assert.Equal("65A", later.Single(x => x.NewSection == "62").OldSection);
        Assert.Equal("65B", later.Single(x => x.NewSection == "63").OldSection);
        Assert.Equal(new[] { "65B" }, later.Single(x => x.NewSection == "63").OldBases);
    }

    [Fact]
    public void BnssLayoutWithBracketedOldSectionsAndOldSectionAtLineStart()
    {
        var e = Parse(Crpc, """
            2(1)(c) "bailable offence".
            2(a)]
             No change.
            2(1)(d) "bail bond".
             -
            Newly added.
            """);
        var tail = Parse(Crpc, """
            530
            Trial and proceedings to be
            held in electronic mode.

             -
            Newly added under heading.
            531
            Repeal and savings.
            484 Proviso to subsection (2) (a) is excluded.
            """);
        string Old(string s) => e.Single(x => x.NewSection == s).OldSection ?? "NEW";
        Assert.Equal("2(a)", Old("2(1)(c)"));
        Assert.True(e.Single(x => x.NewSection == "2(1)(d)").NewProvision);
        Assert.True(tail.Single(x => x.NewSection == "530").NewProvision);
        Assert.Equal("484", tail.Single(x => x.NewSection == "531").OldSection);
    }

    [Fact]
    public void NegativeCasesAreSkippedNotGuessed()
    {
        var e = Parse(Ipc, """
            5
            Punishment for something.
            10
             No change.
            3
            Out-of-order row that must not become a head.
            12
            Row with no readable old section
            and only prose that follows
            on several lines without a number.
            """);
        Assert.Equal("10", e.Single(x => x.NewSection == "5").OldSection);  // "10" followed by summary prose is not a head
        Assert.DoesNotContain(e, x => x.NewSection == "3");                 // lower than the previous head
        Assert.DoesNotContain(e, x => x.NewSection == "12");                // no old section and no "New" mark: skipped
        Assert.Empty(Parse(Ipc, "400\nSection number beyond the code.\n12\n"));   // above NewMax: never a head
    }

    [Fact]
    public void TextQualityFlagsLegacyFontHindiOnly()
    {
        string wellFormed = string.Join(" ", Enumerable.Repeat("सेना अधिनियम धारा अपराध दंड न्यायालय", 60));
        string legacy = string.Join(" ", Enumerable.Repeat("िारा धसधिि अपराि ्यायालय सेना अधिनियम", 60));
        var ok = TextQuality.Assess(new[] { wellFormed });
        var bad = TextQuality.Assess(new[] { legacy });
        var mixed = TextQuality.Assess(new[] { legacy, string.Concat(Enumerable.Repeat("The Army Act provides for courts-martial. ", 400)) });
        var en = TextQuality.Assess(new[] { "Plain English text only." });
        Assert.Equal(("hi", TextQuality.Reliable), (ok.DetectedLanguage, ok.Reliability));
        Assert.Equal(("hi", TextQuality.Unreliable), (bad.DetectedLanguage, bad.Reliability));
        Assert.Equal(TextQuality.PartlyUnreliable, mixed.Reliability);
        Assert.Equal(("en", TextQuality.Reliable), (en.DetectedLanguage, en.Reliability));
        Assert.Equal(TextQuality.NoText, TextQuality.Assess(new[] { "   " }).Reliability);
        // too little Devanagari: not assessed, never flagged
        Assert.Equal(TextQuality.Reliable, TextQuality.Assess(new[] { "िारा धसधिि" }).Reliability);
    }

    [Fact]
    public void CatalogueTitleCaseAndCategories()
    {
        Assert.Equal("The First Schedule", InstrumentCatalog.TitleCase("THE FIRST SCHEDULE"));
        Assert.Equal("Army Rules,1954", InstrumentCatalog.TitleCase("Army Rules,1954"));
        Assert.Equal("Criminal codes (in force from 1 July 2024)", InstrumentCatalog.Category("The Bharatiya Nyaya Sanhita, 2023", "45 of 2023", "act-bns-2023"));
        Assert.Equal("Criminal codes (repealed; historical)", InstrumentCatalog.Category("The Indian Penal Code", "45 of 1860", "act-ipc-1860"));
        Assert.Equal("Armed Forces Tribunal", InstrumentCatalog.Category("Armed Forces Tribunal (Procedure) Rules, 2008", null, "rules-aft-procedure-rules-2008"));
        Assert.Equal("Navy", InstrumentCatalog.Category("Regulations for the Navy Part I", null, "regs-regulations-for-the-navy-part-i"));
        Assert.Equal("Army", InstrumentCatalog.Category("The Army and Air Force (Disposal of Private Property) Act, 1950", "40 of 1950", "act-army-af"));
        Assert.Equal("Air Force", InstrumentCatalog.Category("The Air Force Act, 1950", "45 of 1950", "act-air-force-1950"));
    }

    /// Runs against the real 290-document sample when MIMAMSA_SAMPLE_SITE is set (corpus bytes are not in git).
    [Fact]
    public void SampleRelationsWhenTheSampleSiteIsAvailable()
    {
        var site = Environment.GetEnvironmentVariable("MIMAMSA_SAMPLE_SITE");
        if (string.IsNullOrEmpty(site) || !Directory.Exists(site)) return;
        var g = TestText.Load(site);
        var r = g.Relations;
        bool Edge(string nf, string ns, string of, string os) => r.Edges.Any(e => e.NewFamily == nf && e.NewBase == ns && e.OldFamily == of && e.OldBases.Contains(os));
        Assert.True(Edge("no:45 of 2023", "103", "no:45 of 1860", "302"), "BNS 103 <- IPC 302");
        Assert.True(Edge("no:45 of 2023", "109", "no:45 of 1860", "307"), "BNS 109 <- IPC 307");
        Assert.True(Edge("no:47 of 2023", "63", "no:1 of 1872", "65B"), "BSA 63 <- IEA 65B");
        Assert.True(Edge("no:46 of 2023", "531", "no:2 of 1974", "484"), "BNSS 531 <- CrPC 484");
        Assert.False(Edge("no:45 of 2023", "103", "no:45 of 1860", "41"));
        foreach (var fam in new[] { "no:45 of 2023", "no:46 of 2023", "no:47 of 2023" })
        {
            Assert.Contains(r.Notices[fam], n => n.Kind == "repeal" && n.Evidence is not null);
            Assert.Contains(r.Notices[fam], n => n.Kind == "savings_transitional" && n.Evidence is not null);
            Assert.Contains(r.Notices[fam], n => n.Kind == "commencement_delegated" && n.Evidence is not null);
            Assert.Contains(r.Notices[fam], n => n.Kind == "commencement_notification_not_held" && n.Evidence is null);
        }
        foreach (var fam in new[] { "no:45 of 1860", "no:2 of 1974", "no:1 of 1872" })
            Assert.Contains(r.Notices[fam], n => n.Kind == "repealed_by" && n.Evidence is not null);
        Assert.Equal(TextQuality.Unreliable, g.Documents["act-army-1950-hi"].TextAssessment!.Reliability);
        Assert.Equal(TextQuality.Reliable, g.Documents["act-bns-2023-alt-d163e7"].TextAssessment!.Reliability);
        Assert.Equal(TextQuality.Reliable, g.Documents["act-army-1950"].TextAssessment!.Reliability);
        var army = r.InstrumentOf("act-army-1950-hi")!;
        Assert.Equal("act-army-1950", army.PrimaryDocId);
        Assert.Contains(army.Editions, e => e.DocId == "act-army-1950-hi");
        Assert.All(r.CommanderTasks.SelectMany(t => t.Items), i => Assert.True(i.Found, $"{i.Kind} {i.Number} not found in held TOC"));
        // optional evidence for the stream report (written only when a directory is given)
        if (Environment.GetEnvironmentVariable("MIMAMSA_EVIDENCE_DIR") is { Length: > 0 } dir)
        {
            var stats = new
            {
                tables = r.TableStatus,
                edges_by_table = r.Edges.GroupBy(e => e.TableDocId).ToDictionary(g => g.Key, g => new { rows = g.Count(), new_provisions = g.Count(e => e.NewProvision), with_old_section = g.Count(e => !e.NewProvision) }),
                notices = r.Notices.ToDictionary(kv => kv.Key, kv => kv.Value.Select(n => n.Kind)),
                instruments = r.Instruments.Count, statute_documents = r.FamilyOfDoc.Count,
                text_reliability = g.Documents.Values.GroupBy(d => d.TextAssessment?.Reliability ?? "none").ToDictionary(x => x.Key, x => x.Select(d => d.DocId).OrderBy(s => s).ToList()),
            };
            Directory.CreateDirectory(dir);
            File.WriteAllText(Path.Combine(dir, "relations_stats.json"), System.Text.Json.JsonSerializer.Serialize(stats, new System.Text.Json.JsonSerializerOptions { WriteIndented = true }));
        }
    }
}
