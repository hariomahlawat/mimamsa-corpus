// C16 Tranche B B01: end-to-end check that a site written by the C16-aware importer (app/importer, contract 2.0/2.1
// exchange with typed receipts) loads in the B1 GenerationStore and exposes ONLY copies with an eligible effective
// admission or an independently established v1 copy (consumer rule I7, SG-1).
//
// The fixture site under fixtures/c16_b01/site is produced by the real importer from synthetic bytes:
//   python -I app/importer/c16_cases.py app/b1/tests/Mimamsa.Tests/fixtures/c16_b01 [--check]
// (the importer test suite re-runs --check, so the committed site always equals the importer's output).
using System.Text.Json.Nodes;
using Mimamsa.Core.Generation;

namespace Mimamsa.Tests;

public class C16ImporterSiteTests
{
    static string Root => Path.Combine(AppContext.BaseDirectory, "fixtures", "c16_b01");
    static JsonNode Expected => JsonNode.Parse(File.ReadAllText(Path.Combine(Root, "expected.json")))!;
    static List<string> Strings(JsonNode? n) => n!.AsArray().Select(x => x!.GetValue<string>()).OrderBy(x => x, StringComparer.Ordinal).ToList();

    [Fact]
    public void OnlyAdmittedOrEstablishedCopiesAreLoaded()
    {
        var store = GenerationStore.Load(Path.Combine(Root, "site"));
        Assert.Equal("R16-b01-e2e-20261128-00000002", store.GenerationId);
        Assert.Equal(Strings(Expected["expected_documents"]), store.Documents.Keys.OrderBy(x => x, StringComparer.Ordinal).ToList());
        Assert.All(store.Documents.Values, d => Assert.True(d.OriginalVerified));
        Assert.DoesNotContain("ORIGINAL_HASH_MISMATCH_OR_MISSING", store.LoadIssues.Keys);
        Assert.DoesNotContain("DERIVATIVE_TEXT_HASH_MISMATCH", store.LoadIssues.Keys);
        // the eligible C16 copy carries its verified derivative text (SEARCHABLE scope)
        var a = store.Documents["sc-2020-b01-eligible-ca0101"];
        Assert.Equal(2, a.PageCount);
        Assert.Equal(2, a.Pages.Count);
        foreach (var hidden in Strings(Expected["never_visible"]))
        {
            Assert.False(store.Documents.ContainsKey(hidden), hidden);
            Assert.DoesNotContain(store.HeldCopies.Values, h => h.DocId == hidden);
        }
    }

    [Fact]
    public void AnEarlierGenerationNeverResurrectsACopyTheActiveGenerationHolds()
    {
        // generation 1 served aft-2020-b01-later-held-oa0106; generation 2 (active) carries a producer hold on it
        var gen1 = JsonNode.Parse(File.ReadAllText(Path.Combine(Root, "site", "generations", "R16-b01-e2e-20261128-00000001", "generation.json")))!;
        Assert.Contains("aft-2020-b01-later-held-oa0106", gen1["item_document"]!["documents"]!.AsObject().Select(kv => kv.Key));
        var store = GenerationStore.Load(Path.Combine(Root, "site"));
        Assert.Equal(Strings(Expected["expected_held_copies"]), store.HeldCopies.Keys.OrderBy(x => x, StringComparer.Ordinal).ToList());
    }
}
