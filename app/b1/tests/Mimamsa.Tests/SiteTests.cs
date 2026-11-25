using System.Text.Json.Nodes;
using Mimamsa.Core.Citation;
using Mimamsa.Core.Delivery;
using Mimamsa.Core.Generation;
using Mimamsa.Core.Search;

namespace Mimamsa.Tests;

/// Synthetic SYN site built by app/b1/build/build_fixture_site.py (two releases, imported by app/importer).
/// Required: MIMAMSA_TEST_SITE (site root) and MIMAMSA_TEST_MAP (fixture_map.json). Tests fail, never skip, without it.
public static class Syn
{
    public static string Site => Environment.GetEnvironmentVariable("MIMAMSA_TEST_SITE") is { Length: > 0 } s && Directory.Exists(s) ? s
        : throw new InvalidOperationException("MIMAMSA_TEST_SITE must point to a site built by app/b1/build/build_fixture_site.py");
    public static JsonObject Map => JsonNode.Parse(File.ReadAllText(Environment.GetEnvironmentVariable("MIMAMSA_TEST_MAP")
        ?? throw new InvalidOperationException("MIMAMSA_TEST_MAP must point to fixture_map.json")))!.AsObject();
    static GenerationStore? _g;
    public static GenerationStore Gen => _g ??= GenerationStore.Load(Site);

    /// Copy of the site that a test may tamper with.
    public static string CopySite()
    {
        var dst = Path.Combine(Path.GetTempPath(), "mimamsa-site-" + Guid.NewGuid().ToString("N")[..8]);
        foreach (var f in Directory.EnumerateFiles(Site, "*", SearchOption.AllDirectories))
        {
            var t = Path.Combine(dst, Path.GetRelativePath(Site, f));
            Directory.CreateDirectory(Path.GetDirectoryName(t)!);
            File.Copy(f, t);
            File.SetAttributes(t, FileAttributes.Normal);
        }
        return dst;
    }
}

public class GenerationStoreTests
{
    [Fact] public void LoadsOnlyVerifiedItemsOfTheActiveGeneration()
    {
        var g = Syn.Gen;
        Assert.Equal("R13-syn-fixture-20261125-00000002", g.Release.ReleaseId);
        Assert.Empty(g.LoadIssues);
        Assert.All(g.Documents.Values, d => Assert.True(d.OriginalVerified));
        Assert.Equal("STAGED", g.Documents["syn-v-staged"].Publication);
        Assert.False(SearchIndex.Indexable(g.Documents["syn-v-staged"]));   // staged never reaches search
        Assert.Contains(g.Documents.Values.SelectMany(d => d.Candidates), c => c.Type == "outcome");
    }

    [Fact] public void HeldCopiesIncludeTheEarlierActivatedEdition()
    {
        var old = Syn.Map["j_allow_r1_copy"]!.GetValue<string>();
        Assert.True(Syn.Gen.HeldCopies.ContainsKey(old + "|syn-j-allow"));
        Assert.True(Syn.Gen.HeldCopies[old + "|syn-j-allow"].Published);
        Assert.NotEqual(old, Syn.Gen.Documents["syn-j-allow"].CopySha);
    }

    [Fact] public void TamperedDerivativeIsNotServed()
    {
        var site = Syn.CopySite();
        var gid = File.ReadAllText(Path.Combine(site, "ACTIVE")).Trim();
        var f = Directory.EnumerateFiles(Path.Combine(site, "generations", gid, "derived")).First();
        File.AppendAllText(f, "tampered");
        var g = GenerationStore.Load(site);
        Assert.Equal(1, g.LoadIssues["DERIVATIVE_TEXT_HASH_MISMATCH"]);
        Assert.Single(g.Documents.Values, d => d.DerivativeId is null);
    }

    [Fact] public void TamperedVaultObjectIsNotServed()
    {
        var site = Syn.CopySite();
        var sha = Syn.Gen.Documents["syn-s-act"].CopySha;
        var f = Path.Combine(site, "vault", "sha256", sha[..2], sha);
        File.AppendAllText(f, "x");
        var g = GenerationStore.Load(site);
        Assert.False(g.Documents["syn-s-act"].OriginalVerified);
        Assert.False(SearchIndex.Indexable(g.Documents["syn-s-act"]));
    }

    [Fact] public void UnmaterializedGenerationIsRefused()
    {
        var site = Syn.CopySite();
        var gid = File.ReadAllText(Path.Combine(site, "ACTIVE")).Trim();
        var gp = Path.Combine(site, "generations", gid, "generation.json");
        var j = JsonNode.Parse(File.ReadAllText(gp))!.AsObject();
        j.Remove("materialized");
        File.WriteAllText(gp, j.ToJsonString());
        Assert.Equal("GENERATION_NOT_MATERIALIZED", Assert.Throws<GenerationLoadException>(() => GenerationStore.Load(site)).Code);
    }
}

public class SearchServiceTests
{
    static readonly SearchIndex Ix = SearchIndex.Build(Syn.Gen);
    static SearchService Svc(params string[] hidden) => new(Ix, d => hidden.Contains(d));
    static List<string> Ids(SearchResult r) => r.Hits.Select(h => Ix.Passages[h.PassageIndex].DocId + "#" + Ix.Passages[h.PassageIndex].PassageId).ToList();
    static string P(string fid) { var m = Syn.Map["map"]![fid]!.AsArray(); return m[0]!.GetValue<string>() + "#" + m[1]!.GetValue<string>(); }

    [Fact] public void SectionIdentifierPinsTheExactSectionNotSection117()
    {
        var r = Svc().Search("s.17 Bracken Service Act", new SearchFilters());
        Assert.Equal("identifier", r.Mode);
        Assert.Equal(P("A-17"), Ids(r)[0]);
        Assert.DoesNotContain(P("A-117"), Ids(r));
    }

    [Fact] public void CaseNumberResolvesToItsProceedingNotTheLookalike()
    {
        var r = Svc().Search("OA 411/2021", new SearchFilters());
        Assert.Equal(P("J2-MAJ"), Ids(r)[0]);
        Assert.DoesNotContain(P("J3-ORDER"), Ids(r));
    }

    [Fact] public void ExactPhraseWithNotExcludesAndKeepsContiguity()
    {
        var r = Svc("syn-v-withdrawn").Search("exact:\"summary of evidence\" AND NOT pension", new SearchFilters());
        Assert.Equal(new[] { P("M-SYN") }, Ids(r).Take(1));
        Assert.DoesNotContain(P("M-NEAR"), Ids(r));
        Assert.DoesNotContain(P("M-DIS"), Ids(r));
    }

    [Fact] public void WithdrawnAndStagedNeverAppear()
    {
        var r = Svc("syn-v-withdrawn").Search("exact:violet-plume-canary", new SearchFilters());
        Assert.Equal("empty", r.State);
        Assert.Empty(r.Facets.Values.SelectMany(v => v));
    }

    [Fact] public void FiltersAndFacetCountsAreDeterministic()
    {
        var all = Svc().Search("notice", new SearchFilters());
        var only = Svc().Search("notice", new SearchFilters(Types: new HashSet<string> { "judgment" }));
        Assert.All(only.Hits, h => Assert.Equal("judgment", Ix.Docs[Ix.DocOf(h.PassageIndex)].DocType));
        Assert.Equal(all.Facets["type"].Sum(f => f.Count), only.Facets["type"].Sum(f => f.Count));   // the type facet ignores its own filter
        var again = Svc().Search("notice", new SearchFilters(Types: new HashSet<string> { "judgment" }));
        Assert.Equal(Ids(only), Ids(again));
    }

    [Fact] public void YearRangeAndProximity()
    {
        Assert.Equal(P("H-ILL"), Ids(Svc().Search("sick-call deferment medical attendant year:1948..1950", new SearchFilters()))[0]);
        var near = Svc().Search("exact:\"summary of evidence\" NEAR/5 tribunal", new SearchFilters());
        Assert.Equal(new[] { P("M-SYN") }, Ids(near));
    }

    [Fact] public void ParserErrorIsNeverAnEmptySuccess()
    {
        var r = Svc().Search("exact:(\"summary of evidence\" AND (BHT OR tribunal)", new SearchFilters());
        Assert.Equal("parser_error", r.State);
        Assert.Empty(r.Hits);
        var plain = Svc().Search("exact:(\"summary of evidence\" AND (BHT OR tribunal)", new SearchFilters(), plainAfterConfirmation: true);
        Assert.Equal("results", plain.State);
    }

    [Fact] public void DocumentIdentifierPinsOneRepresentativeNotEveryPassage()     // review F05
    {
        var r = Svc().Search("2021 BRSYN 12", new SearchFilters());
        var pinned = r.Hits.Where(h => h.Tier is "identifier" or "document").ToList();
        Assert.True(pinned.Count <= 2);                                     // one per matching document (full and short copy)
        Assert.All(r.Hits.Where(h => h.Tier == "identifier"), h => Assert.Contains("2021 BRSYN 12", Ix.Passages[h.PassageIndex].Text));
        Assert.Contains(r.Hits, h => h.Tier == "mention" && Ix.Passages[h.PassageIndex].DocId == "syn-j-allow");
    }

    [Fact] public void ModeIsNeverReportedAsHybrid()
    {
        foreach (var q in new[] { "BHT hearing tribunal", "late warning invalidates hearing without notice" })
            Assert.NotEqual("hybrid", Svc().Search(q, new SearchFilters()).Mode);
    }
}

/// Review F01: ONE eligibility decision for every delivery path (current copy, earlier edition, citation).
public class EligibilityAndCitationTests
{
    static string M(string k) => Syn.Map[k]!.GetValue<string>();
    static (Eligibility e, ServingState st) Make(RestrictedRegister? reg = null)
    {
        var st = new ServingState();
        return (new Eligibility(Syn.Gen, st, reg ?? RestrictedRegister.Empty, new Vault(Syn.Site)), st);
    }
    static CiteResolution Cite(Eligibility e, string sha, string doc, int page) =>
        CitationResolver.Resolve(Syn.Gen, sha[..12], doc, page, e.HeldEligible, e.CurrentVisibleCopy);

    [Fact] public void CurrentCopyOpensExactly()
    {
        var (e, _) = Make();
        var d = Syn.Gen.Documents["syn-j-allow"];
        Assert.Equal(("CITED_COPY_ELIGIBLE", d.CopySha, 2), (Cite(e, d.CopySha, d.DocId, 2).State, Cite(e, d.CopySha, d.DocId, 2).Copy, 2));
        Assert.NotNull(e.Copy("syn-j-allow", null));
    }

    [Fact] public void PublishedEarlierEditionOpensAsCitedNotSubstituted()
    {
        var (e, _) = Make();
        var r = Cite(e, M("j_allow_r1_copy"), "syn-j-allow", 6);
        Assert.Equal(("CITED_COPY_ELIGIBLE_NOT_CURRENT", M("j_allow_r1_copy"), 6), (r.State, r.Copy, r.Page));
        Assert.Equal(Syn.Gen.Documents["syn-j-allow"].CopySha, r.CurrentCopy);
        Assert.NotNull(e.Copy("syn-j-allow", M("j_allow_r1_copy")));
    }

    [Fact] public async Task WithdrawalCoversEveryCopyIncludingTheEarlierEdition()
    {
        var (e, st) = Make();
        var shas = new[] { Syn.Gen.Documents["syn-j-allow"].CopySha, M("j_allow_r1_copy") };
        await st.WithdrawAsync("syn-j-allow", shas, () => Task.FromResult((2L, "d", true)), () => { }, (_, _) => { });
        Assert.Null(e.Copy("syn-j-allow", null));
        Assert.Null(e.Copy("syn-j-allow", M("j_allow_r1_copy")));
        var withdrawn = Cite(e, M("j_allow_r1_copy"), "syn-j-allow", 6);
        Assert.Equal(Cite(e, new string('a', 64), "syn-j-allow", 6), withdrawn);
        Assert.Equal("CITED_COPY_UNAVAILABLE", withdrawn.State);
    }

    [Fact] public async Task WithdrawingOnlyTheEarlierCopyHidesTheWholeDocument()
    {
        var (e, st) = Make();
        await st.WithdrawAsync("syn-j-allow", new[] { M("j_allow_r1_copy") }, () => Task.FromResult((2L, "d", true)), () => { }, (_, _) => { });
        Assert.Null(e.Visible("syn-j-allow"));
        Assert.Null(e.Copy("syn-j-allow", null));
    }

    [Fact] public void NeverPublishedEarlierCopyIsNotServed()
    {
        var (e, _) = Make();
        Assert.NotNull(e.Copy("syn-x-stagedearly", null));                        // current copy is published in R2
        Assert.Null(e.Copy("syn-x-stagedearly", M("x_stagedearly_r1_copy")));     // R1 copy was STAGED
        Assert.Equal("CITED_COPY_UNAVAILABLE", Cite(e, M("x_stagedearly_r1_copy"), "syn-x-stagedearly", 1).State);
    }

    [Fact] public void CopyDroppedFromTheLaterReleaseIsNotServed()
    {
        var (e, _) = Make();
        Assert.True(Syn.Gen.HeldCopies.ContainsKey(M("x_dropped_r1_copy") + "|syn-x-dropped"));
        Assert.Null(e.Copy("syn-x-dropped", M("x_dropped_r1_copy")));
        Assert.Equal("CITED_COPY_UNAVAILABLE", Cite(e, M("x_dropped_r1_copy"), "syn-x-dropped", 1).State);
    }

    [Fact] public void RegisterHitOnAnEarlierCopyIsNotServed()
    {
        var f = Path.GetTempFileName();
        File.WriteAllText(f, $$"""{"items":[{"restriction_id":"RM-T","source_sha256":"{{M("j_allow_r1_copy")}}","doc_id":"syn-unrelated"}]}""");
        var (e, _) = Make(RestrictedRegister.Load(f));
        Assert.Null(e.Copy("syn-j-allow", M("j_allow_r1_copy")));
        Assert.NotNull(e.Copy("syn-j-allow", null));
        Assert.Equal("CITED_COPY_UNAVAILABLE", Cite(e, M("j_allow_r1_copy"), "syn-j-allow", 6).State);
    }

    [Fact] public void PageMismatchAndShortPrefixAreSpecificNotices()
    {
        var (e, _) = Make();
        var d = Syn.Gen.Documents["syn-v-other"];
        Assert.Equal("CITED_PAGE_NOT_IN_COPY", Cite(e, d.CopySha, d.DocId, 99).State);
        Assert.Equal("REFERENCE_MISMATCH", Cite(e, d.CopySha, "syn-s-act", 1).State);
        Assert.Equal("CITED_COPY_UNAVAILABLE", CitationResolver.Resolve(Syn.Gen, d.CopySha[..8], d.DocId, 1, e.HeldEligible, e.CurrentVisibleCopy).State);
    }
}
