// C16 contract 2.1 (PR #82 1e3060de, C16-I21-01/02/03) mirrored in .NET: ActivationOutcome reproduces every decision
// of the Python reference activation_outcome exactly (result, service level, refusal, reasons, per-component states,
// uncalibrated components in use), on vectors written by make_outcome_vectors.py from the reference.
using System.Text.Json.Nodes;
using Mimamsa.Core.Activation;

namespace Mimamsa.Tests;

public class C16Cp1OutcomeTests
{
    public static IEnumerable<object[]> Cases() =>
        JsonNode.Parse(File.ReadAllText(Repo.P("app", "b1", "tests", "Mimamsa.Tests", "outcome_vectors.json")))!.AsArray()
            .Select(c => new object[] { (string)c!["name"]! });

    static JsonObject Case(string name) =>
        JsonNode.Parse(File.ReadAllText(Repo.P("app", "b1", "tests", "Mimamsa.Tests", "outcome_vectors.json")))!.AsArray()
            .Single(c => (string)c!["name"]! == name)!.AsObject();

    [Theory]
    [MemberData(nameof(Cases))]
    public void DotnetOutcomeEqualsThePythonReference(string name)
    {
        var c = Case(name);
        var results = c["results"]!.AsObject().ToDictionary(kv => kv.Key, kv => (string)kv.Value!, StringComparer.Ordinal);
        var contracts = c["contracts"]!.AsObject().ToDictionary(kv => kv.Key, kv => (JsonObject?)kv.Value!.AsObject(), StringComparer.Ordinal);
        var rebuilds = c["rebuilds"] is JsonObject rb ? rb.ToDictionary(kv => kv.Key, kv => (JsonObject?)kv.Value!.AsObject(), StringComparer.Ordinal) : null;
        var got = ActivationOutcome.Decide(results, contracts, (string)c["mode"]!, rebuilds);
        var want = c["expected"]!;
        Assert.True(JsonNode.DeepEquals(want, got), $"{name}\nwant {want.ToJsonString()}\ngot  {got.ToJsonString()}");
    }

    [Fact]
    public void EveryCurrentContractIsUncalibratedSoProductionRefusesTheCp1Release()
    {
        var contracts = ActivationOutcome.Kinds.ToDictionary(k => k,
            k => (JsonObject?)JsonNode.Parse(File.ReadAllText(Repo.V21("component_contracts", k + ".json")))!.AsObject(), StringComparer.Ordinal);
        var lexical = new Dictionary<string, string> { ["KNOWLEDGE_ROWS"] = "VERIFIED", ["GRAPH"] = "VERIFIED", ["LEXICAL_INDEX"] = "VERIFIED", ["TEXT_STORE"] = "VERIFIED" };
        var prod = ActivationOutcome.Decide(lexical, contracts, "production");
        Assert.Equal("UNCALIBRATED_IN_PRODUCTION", (string?)prod["refusal"]);
        Assert.Equal("ACTIVE_DEGRADED", (string?)ActivationOutcome.Decide(lexical, contracts, "development")["result"]);
    }
}
