using System.Text;
using System.Text.Json.Nodes;
using Mimamsa.Core.Citation;
using Mimamsa.Core.Delivery;
using Mimamsa.Core.Generation;
using Mimamsa.Core.Search;

namespace Mimamsa.Tests;

/// Unit tests of the platform-neutral core. No database, no HTTP.
public class QueryParserTests
{
    [Fact] public void PlainWordsAreDetected()
    {
        var q = QueryParser.Parse("disability pension invalided");
        Assert.True(q.Plain); Assert.Equal(3, q.PlainWords.Count);
    }

    [Fact] public void ExactPhraseIsLexicalPhrase()
    {
        var q = QueryParser.Parse("exact:\"Rule 8(3)(a)\"");
        Assert.True(q.Exact); Assert.False(q.Plain);
        var ph = Assert.IsType<QPhrase>(q.Root);
        Assert.Equal(new[] { "rule", "8", "3", "a" }, ph.Terms);
    }

    [Fact] public void BooleanNotAndNear()
    {
        var q = QueryParser.Parse("exact:\"summary of evidence\" AND NOT pension");
        var and = Assert.IsType<QAnd>(q.Root);
        Assert.IsType<QNot>(and.Items[1]);
        var n = QueryParser.Parse("\"summary of evidence\" NEAR/5 tribunal");
        Assert.Equal(5, Assert.IsType<QNear>(n.Root).Distance);
    }

    [Fact] public void FieldsAndRanges()
    {
        var q = QueryParser.Parse("section:8 act:\"Bracken Hearing Rules\" year:1948..1950");
        var and = Assert.IsType<QAnd>(q.Root);
        var y = Assert.IsType<QField>(and.Items[2]);
        Assert.Equal(("1948", "1950"), (y.RangeFrom, y.RangeTo));
        Assert.Equal("act", Assert.IsType<QField>(and.Items[1]).Field);
    }

    [Theory]
    [InlineData("exact:(\"summary of evidence\" AND (BHT OR tribunal)", 6)]   // RET-13: unmatched '(' right after exact:
    [InlineData("\"court martial", 0)]
    [InlineData("pension)", 7)]
    [InlineData("a NEAR/0 b", 2)]
    public void MalformedQueriesReportPosition(string q, int pos)
    {
        var e = Assert.Throws<ParseException>(() => QueryParser.Parse(q));
        Assert.Equal(pos, e.Position);
    }

    [Fact] public void PlainFallbackRemovesSyntaxOnlyAfterConfirmation()
    {
        var q = QueryParser.PlainWords("exact:(\"summary of evidence\" AND (BHT OR tribunal)");
        Assert.True(q.Plain);
        Assert.DoesNotContain("AND", q.PlainWords);
        Assert.Contains("tribunal", q.PlainWords);
    }
}

public class IdentifierTests
{
    [Fact] public void RecognisesSectionCaseAndCitations()
    {
        var ids = Identifiers.Recognise("s.17 Bracken Service Act");
        var s = Assert.Single(ids);
        Assert.Equal((IdKind.Section, "17"), (s.Kind, s.Base));
        Assert.Equal("oa4112021", Assert.Single(Identifiers.Recognise("OA 411/2021")).Normalized);
        Assert.Equal(IdKind.NeutralCitation, Assert.Single(Identifiers.Recognise("2013 INSC 408")).Kind);
        Assert.Equal("ca49492013", Assert.Single(Identifiers.Recognise("Civil Appeal No. 4949 of 2013")).Normalized);
    }

    [Fact] public void CoverPageCaseNumberNormalisesLikeTheQuery()
    {
        var cover = Identifiers.CoverCaseNumbers("DHARAMVIR SINGH v. UNION OF INDIA & ORS. (Civil Appeal No. 4949 of 2013) JULY 2, 2013").ToList();
        Assert.Contains("ca49492013", cover);
    }

    [Fact] public void ActNumbersAreNotCaseNumbers()
    {
        Assert.DoesNotContain(Identifiers.Recognise("Act 37 of 1992"), i => i.Kind == IdKind.CaseNumber);
    }

    [Theory]
    [InlineData("Section 17. Authorised pause.", "17", null, true, true)]
    [InlineData("Section 117. Inventory of lamps.", "17", null, true, false)]
    [InlineData("69. Civil offences.—Subject to the provisions", "69", null, true, true)]
    [InlineData("69. Civil offences.—Subject to the provisions", "69", null, false, false)]
    [InlineData("Rule 8(3)(a). The chair must", "8", "(3)(a)", true, true)]
    [InlineData("Rule 8(3)(b). Oral notice", "8", "(3)(a)", true, false)]
    [InlineData("liable under section 69 of the Army Act", "69", null, false, true)]
    public void ProvisionMatchingNeverConfusesNumbers(string text, string baseNo, string? sub, bool statute, bool expected)
        => Assert.Equal(expected, Identifiers.PassageHasProvision(text, baseNo, sub, statute));

    [Fact] public void HeadingOutranksReference()
    {
        Assert.Equal(3, Identifiers.ProvisionStrength("69. Civil offences.—Subject to", "69", null, true));
        Assert.Equal(2, Identifiers.ProvisionStrength("69. Civil offences.", "69", null, true));
        Assert.Equal(1, Identifiers.ProvisionStrength("see section 69", "69", null, true));
        Assert.Equal(2, Identifiers.ProvisionStrength("Rule 8(3)(a). The chair must provide notice.", "8", null, true));
    }
}

public class TextAndOffsetTests
{
    [Fact] public void TokenizerKeepsDevanagariMarksInsideWords()
    {
        var t = Text.Tokenize("सुनवाई से पहले लिखित सूचना दें।");
        Assert.Equal(6, t.Count);
        Assert.Equal("सुनवाई", t[0].Term);
    }

    [Fact] public void CodePointOffsetsMapAcrossSurrogatePairs()
    {
        var s = "a\U0001F600bc";                        // 'a', emoji (2 UTF-16 units), 'b', 'c'
        Assert.True(CodePoints.TryMap(s, 2, 4, out var a, out var b));
        Assert.Equal("bc", s[a..b]);
        Assert.Equal(4, CodePoints.Length(s));
    }

    [Fact] public void PageSplitMatchesImporterFormat()
    {
        var p = GenerationStore.SplitPages("[[page 1]]\nfirst\n[[page 3]]\nthird\nline\n")!;
        Assert.Equal("first", p[1]); Assert.Equal("third\nline", p[3]);
        Assert.Null(GenerationStore.SplitPages("no marker\n[[page 1]]\nx"));
        Assert.Null(GenerationStore.SplitPages("[[page 1]]\na\n[[page 1]]\nb"));
    }

    [Fact] public void SnippetHighlightsAreRelativeToTheExcerpt()
    {
        var sn = Snippets.Build("The panel rejects the automatic invalidity submission.", new HashSet<string> { "invalidity" }, Array.Empty<IReadOnlyList<string>>());
        var h = Assert.Single(sn.Highlights);
        Assert.Equal("invalidity", sn.Text[h[0]..h[1]]);
    }
}

public class ByteRangeTests
{
    [Theory]
    [InlineData("bytes=0-99", RangeParse.Ok)]
    [InlineData(null, RangeParse.Missing)]
    [InlineData("bytes=0-10,20-30", RangeParse.MultiRange)]
    [InlineData("bytes=-100", RangeParse.Malformed)]
    [InlineData("bytes=10-", RangeParse.Malformed)]
    [InlineData("bytes=0-70000", RangeParse.TooLarge)]
    [InlineData("bytes=999999-1000000", RangeParse.Unsatisfiable)]
    [InlineData("Bytes=0-1", RangeParse.Malformed)]
    [InlineData("bytes=+1-2", RangeParse.Malformed)]
    public void OnlyOneExplicitBoundedRange(string? header, RangeParse expected)
        => Assert.Equal(expected, ByteRange.Parse(header, 100_000, 65_536, out _, out _));
}

public class LegalCitationTests
{
    static DocumentRecord Doc(string? origin = null, string fidelity = "AUTOMATED_CANDIDATE_NOT_VERIFIED") => new()
    {
        DocId = "example-synthetic-judgment-0001", DocType = "judgment", Title = "SYNTHETIC EXAMPLE", IssueDate = "2099-01-15",
        CopySha = new string('c', 64), Judicial = new Judicial("Synthetic Tribunal", null, new[] { "EXAMPLE-0001" }, "2099 EXAMPLE 1",
            Array.Empty<string>(), "A. Example", "Union of Example", Array.Empty<string>()),
        Provenance = new JsonObject(), Restriction = new JsonObject(),
        StatusAxes = new JsonObject { ["evidence_fidelity"] = new JsonObject { ["value"] = fidelity } },
        FieldOrigin = origin is null ? new JsonObject() : new JsonObject { ["neutral_citation"] = origin },
    };

    [Fact] public void SameVectorAsTheContractReference()      // app/contract/tests/test_citation.py
        => Assert.Equal("A. Example v. Union of Example, 2099 EXAMPLE 1 (Synthetic Tribunal, 15 January 2099), para 7 (metadata not verified)",
                        LegalCitation.Format(Doc(), 12, "7"));

    [Fact] public void LlmFieldsAreOmittedAndInternalIdsNeverAppear()
    {
        var s = LegalCitation.Format(Doc("llm"), 3, null);
        Assert.DoesNotContain("2099 EXAMPLE 1", s);
        Assert.DoesNotContain("example-synthetic", s);
        Assert.EndsWith(", p. 3 (metadata not verified)", s);
    }

    [Fact] public void MarkerDroppedOnlyWhenChecked()
        => Assert.DoesNotContain("(metadata not verified)", LegalCitation.Format(Doc(fidelity: "DOCUMENTARY_CHECKED"), 1, null));
}
