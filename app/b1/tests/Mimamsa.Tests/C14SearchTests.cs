using Mimamsa.Core.Generation;
using Mimamsa.Core.Legal;
using Mimamsa.Core.Search;

namespace Mimamsa.Tests;

/// C14 WP1/WP3 search: the legal identifier resolver, case names, citations, spelling suggestions, paging,
/// instrument grouping and the service preference.
public class LegalIdentifierResolverTests
{
    static DocumentRecord Doc(string id, string type, string title, string? lang = "en", Judicial? j = null, string? date = null) =>
        new() { DocId = id, DocType = type, Title = title, Language = lang, Judicial = j, IssueDate = date, CopySha = new string('0', 64),
                Provenance = new(), StatusAxes = new(), Restriction = new(), FieldOrigin = new() };
    static Judicial Parties(string pet, string res) => new(null, null, Array.Empty<string>(), null, Array.Empty<string>(), pet, res, Array.Empty<string>());

    static readonly List<DocumentRecord> Docs = new()
    {
        Doc("act-ipc-1860", "act", "The Indian Penal Code"),
        Doc("act-army-1950", "act", "The Army Act, 1950"),
        Doc("act-army-1950-hi", "act", "The Army Act, 1950", "hi"),
        Doc("rules-army-rules-1954", "rules", "Army Rules,1954"),
        Doc("sc-2013-dharamvir", "judgment", "DHARAMVIR SINGH versus UNION OF INDIA", j: Parties("DHARAMVIR SINGH", "UNION OF INDIA & ORS."), date: "2013-07-02"),
        Doc("sc-1987-ranjit", "judgment", "RANJIT THAKUR versus UNION OF INDIA", j: Parties("RANJIT THAKUR", "UNION OF INDIA AND ORS."), date: "1987-10-15"),
        Doc("sc-2015-uoi", "judgment", "UNION OF INDIA versus RAJBIR SINGH", j: Parties("UNION OF INDIA", "RAJBIR SINGH"), date: "2015-02-13"),
    };
    static LegalIdentifierResolver R(IEnumerable<DocumentRecord>? docs = null)
    {
        var d = (docs ?? Docs).ToList();
        return new LegalIdentifierResolver(d, d.Select(x => Text.Tokenize(x.Title ?? "").Select(t => t.Term).ToHashSet()).ToList());
    }

    [Theory]
    [InlineData("IPC")] [InlineData("I.P.C.")] [InlineData("ipc")]
    public void AbbreviationResolvesToTheHeldInstrumentAndIsDisclosed(string w)
    {
        var s = R().ResolveInstrument(new[] { w });
        Assert.Equal(ScopeKind.Scoped, s.Kind);
        Assert.Equal("act-ipc-1860", Docs[Assert.Single(s.Docs)].DocId);
        var a = Assert.Single(s.Aliases);
        Assert.Equal("ipc", a.Alias);
        Assert.Equal("The Indian Penal Code", a.HeldTitle);
    }

    [Fact] public void AbbreviationOfAnInstrumentNotHeldIsNotExpandedAndIsReportedNotHeld()
    {
        var s = R().ResolveInstrument(new[] { "BNS" });
        Assert.Equal(ScopeKind.NotHeld, s.Kind);
        Assert.Empty(s.Aliases);
    }

    [Fact] public void ExistingScopingRulesAreUnchanged()
    {
        Assert.Equal(ScopeKind.Any, R().ResolveInstrument(Array.Empty<string>()).Kind);
        Assert.Equal(ScopeKind.Ambiguous, R().ResolveInstrument(new[] { "Rules" }).Kind);          // generic words only
        Assert.Equal(ScopeKind.NotHeld, R().ResolveInstrument(new[] { "Navy", "Rules" }).Kind);
        var army = R().ResolveInstrument(new[] { "Army", "Act" });
        Assert.Equal(ScopeKind.Scoped, army.Kind);
        Assert.Equal(2, army.Docs.Count);                         // English and Hindi copies of one instrument
        Assert.Equal("The Army Act, 1950", army.Text);
        Assert.Equal("Army Rules,1954", Docs[Assert.Single(R().ResolveInstrument(new[] { "AR" }).Docs)].Title);
    }

    [Theory]
    [InlineData("Dharamvir Singh", "sc-2013-dharamvir")]
    [InlineData("Ranjit Thakur v Union of India", "sc-1987-ranjit")]
    [InlineData("ranjit thakur versus union of india", "sc-1987-ranjit")]
    public void CaseNamePinsTheNamedJudgment(string q, string doc)
    {
        var m = R().ResolveCaseName(q.Split(' '));
        Assert.NotNull(m);
        Assert.False(m!.TooMany);
        Assert.Equal(doc, Docs[Assert.Single(m.Docs)].DocId);
    }

    [Theory]
    [InlineData("union of india")] [InlineData("court martial")] [InlineData("singh")] [InlineData("disability pension")]
    public void GenericOrUnknownWordsNeverPinACase(string q) => Assert.Null(R().ResolveCaseName(q.Split(' ')));

    [Fact] public void ManyJudgmentsWithTheSamePartiesAreNotPinned()
    {
        var many = Enumerable.Range(0, 6).Select(i => Doc($"hc-{i}", "judgment", "x", j: Parties("ZORAWAR SINGH", "UNION OF INDIA"))).ToList();
        var m = R(many).ResolveCaseName(new[] { "Zorawar", "Singh" });
        Assert.NotNull(m);
        Assert.True(m!.TooMany);
        Assert.Empty(m.Docs);
        Assert.Equal(6, m.Count);
    }

    [Theory]
    [InlineData("(2013) 7 SCC 316", true)] [InlineData("[2013] 8 S.C.R. 1119", true)] [InlineData("AIR 1987 SC 2386", true)]
    [InlineData("(court martial)", false)] [InlineData("(2013) 7 SCC 316 AND pension", false)] [InlineData("disability pension", false)]
    public void BracketedCitationsAreIdentifiersNotQuerySyntax(string q, bool expected) =>
        Assert.Equal(expected, LegalIdentifierResolver.IsIdentifierQuery(q));

    [Fact] public void AirAndScaleCitationsAreRecognisedAndNotReadAsNeutralCitations()
    {
        var air = Assert.Single(Identifiers.Recognise("AIR 1987 SC 2386"));
        Assert.Equal(IdKind.ReportedCitation, air.Kind);
        Assert.Equal("air1987sc2386", air.Normalized);
        Assert.Equal(IdKind.ReportedCitation, Assert.Single(Identifiers.Recognise("2013 (7) SCALE 123")).Kind);
        Assert.Equal(IdKind.NeutralCitation, Assert.Single(Identifiers.Recognise("2013 INSC 408")).Kind);
        Assert.Equal(new[] { "20138scr1119" }, Identifiers.MastheadCitations("[2013] 8 S.C.R. 1119 DHARAMVIR SINGH v. UNION OF INDIA").ToArray());
        Assert.Empty(Identifiers.MastheadCitations(new string('x', 700) + " (2013) 7 SCC 316"));   // later text cites other cases
    }

    [Fact] public void EditionsAndLanguageVersionsShareAGroupAndEnglishRepresentsIt()
    {
        var en = Doc("act-bns-2023", "act", "BNS"); var hi = Doc("act-bns-2023-alt-d163e7", "act", "BNS", "hi");
        var cons = Doc("act-crpc-1973-consolidated", "act", "CrPC");
        Assert.Equal(LegalIdentifierResolver.GroupKey(en), LegalIdentifierResolver.GroupKey(hi));
        Assert.Equal("act-crpc-1973", LegalIdentifierResolver.GroupKey(cons));
        Assert.True(LegalIdentifierResolver.PrimaryRank(en) < LegalIdentifierResolver.PrimaryRank(hi));
        Assert.Equal("Hindi text", LegalIdentifierResolver.VariantLabel(hi));
        Assert.Equal("Consolidated text", LegalIdentifierResolver.VariantLabel(cons));
        var j = Doc("sc-2013-x-hi", "judgment", "x", "hi");
        Assert.Equal("sc-2013-x-hi", LegalIdentifierResolver.GroupKey(j));     // judgments are never merged
    }

    [Fact] public void ServiceIsDerivedDeterministically()
    {
        Assert.Equal("army", LegalIdentifierResolver.ServiceOf(Doc("a", "act", "The Army Act, 1950"), 0, 0, 0));
        Assert.Equal("navy", LegalIdentifierResolver.ServiceOf(Doc("a", "regulations", "Regulations for the Navy Part I"), 0, 0, 0));
        Assert.Equal("airforce", LegalIdentifierResolver.ServiceOf(Doc("a", "act", "The Air Force Act, 1950"), 0, 0, 0));
        Assert.Null(LegalIdentifierResolver.ServiceOf(Doc("a", "act", "The Army and Air Force (Disposal of Private Property) Act, 1950"), 0, 0, 0));
        Assert.Null(LegalIdentifierResolver.ServiceOf(Doc("a", "act", "The Indian Penal Code"), 0, 0, 0));
        Assert.Equal("army", LegalIdentifierResolver.ServiceOf(Doc("j", "judgment", "x"), 12, 3, 1));
        Assert.Null(LegalIdentifierResolver.ServiceOf(Doc("j", "judgment", "x"), 6, 4, 0));     // not dominant
        Assert.Null(LegalIdentifierResolver.ServiceOf(Doc("j", "judgment", "x"), 3, 0, 0));     // too few mentions
    }

    [Theory]
    [InlineData("marshal", "martial", 2)] [InlineData("disabilty", "disability", 1)] [InlineData("dharamveer", "dharamvir", 2)]
    [InlineData("form", "from", 1)] [InlineData("court", "court", 0)]
    public void EditDistanceIsOptimalStringAlignment(string a, string b, int d) => Assert.Equal(d, SpellingSuggester.Distance(a, b, 3));
}

/// Same behaviour on the real SYN fixture index (needs MIMAMSA_TEST_SITE like SearchServiceTests).
public class C14SearchSiteTests
{
    static readonly SearchIndex Ix = SearchIndex.Build(Syn.Gen);
    static SearchService Svc() => new(Ix, _ => false);
    static string Doc(Hit h) => Ix.Passages[h.PassageIndex].DocId;

    [Fact] public void CaseNameTierPinsBothJudgmentsNamedVsAboveCitingDocuments()
    {
        var r = Svc().Search("Vale v Lark", new SearchFilters());
        Assert.Equal("identifier", r.Mode);
        var chip = Assert.Single(r.Chips, c => c.Kind == "case_name");
        Assert.Contains("2 judgments", chip.Text);
        var pinned = r.Hits.TakeWhile(h => h.Tier == "case_name").Select(Doc).ToList();
        Assert.Equal(new[] { "syn-j-allow", "syn-j-lookalike" }.OrderBy(x => x), pinned.OrderBy(x => x));
    }

    [Fact] public void UnrecordedCitationSaysSoAndPinsNothing()
    {
        var r = Svc().Search("(2020) 3 SCC 99", new SearchFilters());
        Assert.Contains(r.Chips, c => c.Kind == "not_held" && c.Text.Contains("(2020) 3 SCC 99"));
        Assert.DoesNotContain(r.Hits, h => h.Tier is "identifier" or "document" or "case_name");
        Assert.NotEqual("parser_error", r.State);
    }

    [Fact] public void SpellingSuggestionIsOfferedNeverApplied()
    {
        var r = Svc().Search("hearnig", new SearchFilters());
        var s = Assert.Single(r.Chips, c => c.Kind == "suggestion");
        Assert.Equal("hearing", s.Source);
        Assert.Equal("empty", r.State);                         // the query ran as typed
        Assert.DoesNotContain(Svc().Search("hearing", new SearchFilters()).Chips, c => c.Kind == "suggestion");
    }

    [Fact] public void PagesCoverEveryDocumentOnceInRelevanceOrder()
    {
        var svc = Svc();
        var r = svc.Search("notice", new SearchFilters());
        var all = r.Hits.Select(h => Ix.DocOf(h.PassageIndex)).Distinct().ToHashSet();
        var seen = new List<int>();
        var p1 = svc.Page(r, 1, 2, null);
        for (int p = 1; p <= p1.PageCount; p++)
        {
            var pg = svc.Page(r, p, 2, null);
            foreach (var g in pg.Groups) { seen.Add(g.Doc); seen.AddRange(g.Variants.Select(v => v.Doc)); }
            var order = r.Hits.Select(h => h.PassageIndex).ToList();
            var idx = pg.Hits.Select(h => order.IndexOf(h.PassageIndex)).ToList();
            Assert.Equal(idx.OrderBy(i => i), idx);              // relevance order kept inside a page
        }
        Assert.Equal(all.Count, seen.Count);
        Assert.Equal(all, seen.ToHashSet());
        var newest = svc.Page(r, 1, 100, "new").Groups.Select(g => Ix.Docs[g.Doc].IssueDate ?? "").Where(d => d.Length > 0).ToList();
        Assert.Equal(newest.OrderByDescending(d => d, StringComparer.Ordinal), newest);
    }

    [Fact] public void ServicePreferenceNeverMovesPinnedTiers()
    {
        var plain = Svc().Search("s.17 Bracken Service Act", new SearchFilters());
        var army = Svc().Search("s.17 Bracken Service Act", new SearchFilters(), service: "army");
        Assert.Equal(plain.Hits.Where(h => h.Tier != "lexical").Select(h => h.PassageIndex), army.Hits.Where(h => h.Tier != "lexical").Select(h => h.PassageIndex));
        Assert.Equal(plain.Hits.Count, army.Hits.Count);       // nothing excluded
        Assert.Equal("army", army.Service);
        Assert.Null(Svc().Search("notice", new SearchFilters(), service: "marines").Service);
    }
}
