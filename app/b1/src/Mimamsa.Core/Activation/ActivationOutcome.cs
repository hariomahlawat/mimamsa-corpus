// C16 contract 2.1 (PR #82 1e3060de, review C16-I21-01/02/03): the .NET mirror of
// mimamsa_contract.c16.components.activation_outcome, rebuild_issues, contract_issues (rule part) and uncalibrated.
// Byte-for-byte decisions are cross-checked against vectors written by the Python reference
// (app/b1/tests/Mimamsa.Tests/outcome_vectors.json, make_outcome_vectors.py).
// Not mirrored: the JSON-schema half of contract_issues (the .NET side has no schema validator); a contract must also
// pass the reference schema check, which the central build (B02) and the contract tests enforce on the shipped files.
using System.Text.Json.Nodes;

namespace Mimamsa.Core.Activation;

public static class ActivationOutcome
{
    public static readonly string[] Cheap = ["KNOWLEDGE_ROWS", "GRAPH", "LEXICAL_INDEX", "TEXT_STORE"];
    public static readonly string[] Kinds = ["GRAPH", "KNOWLEDGE_ROWS", "LEXICAL_INDEX", "TEXT_STORE", "VECTOR_PACK"];
    public static readonly string[] States = ["VERIFIED", "FAILED", "MISSING"];
    public static readonly string[] Modes = ["production", "development"];
    public const string OwnerGateUncalibratedProduction = "OD-C16-UNCALIBRATED-PRODUCTION";
    public static readonly IReadOnlyDictionary<string, string[]> RequiredChecks = new Dictionary<string, string[]>(StringComparer.Ordinal)
    {
        ["KNOWLEDGE_ROWS"] = ["ROW_COUNTS", "ROWS_ALLOWLIST_AND_TYPES", "ROWS_REDERIVE_COMPARE"],
        ["GRAPH"] = ["GRAPH_DIGEST", "GRAPH_STRUCTURAL_RECHECK", "SAMPLED_REBUILD_PARITY"],
        ["LEXICAL_INDEX"] = ["SQLITE_QUICK_CHECK", "SAMPLED_POSTINGS_REDERIVE", "SAMPLED_QUERY_PARITY"],
        ["TEXT_STORE"] = ["SQLITE_QUICK_CHECK", "TEXT_STORE_BIND_EXACT", "PAGE_HASH_ON_READ"],
        ["VECTOR_PACK"] = ["VECTOR_TRAILER", "VECTOR_KEYS_RECOMPUTED", "VECTOR_SPOT_REEMBED"],
    };
    static readonly HashSet<string> Sampled = ["SAMPLED_REBUILD_PARITY", "SAMPLED_POSTINGS_REDERIVE", "SAMPLED_QUERY_PARITY", "VECTOR_SPOT_REEMBED"];

    static string? S(JsonNode? n) => n is JsonValue v && v.TryGetValue<string>(out var s) ? s : null;
    static bool Sha64(JsonNode? n) => S(n) is { Length: 64 } s && s.All(c => c is >= '0' and <= '9' or >= 'a' and <= 'f');

    /// The rule half of contract_issues: kind known, every required check present, sampled checks seeded, exhaustive full.
    public static List<string> ContractRuleIssues(JsonObject c)
    {
        var out_ = new List<string>();
        var kind = S(c["kind"]);
        if (kind is null || !RequiredChecks.ContainsKey(kind) || c["checks"] is not JsonArray checks) return ["SCHEMA: contract kind or checks missing"];
        var ids = checks.Select(x => S(x?["check_id"])).Where(x => x is not null).ToHashSet();
        foreach (var m in RequiredChecks[kind].Where(r => !ids.Contains(r)).Order(StringComparer.Ordinal)) out_.Add($"required check {m} missing");
        foreach (var x in checks.Select(x => x!.AsObject()))
        {
            var id = S(x["check_id"]) ?? ""; var sel = S(x["sample"]?["selection"]);
            if (Sampled.Contains(id) && sel == "FULL") out_.Add("a sampled check must use a deterministic seeded sample");
            if (!Sampled.Contains(id) && sel != "FULL") out_.Add("an exhaustive check must run on the full component");
        }
        return out_;
    }

    public static bool Uncalibrated(JsonObject c) =>
        (c["checks"] as JsonArray ?? []).Any(x => S(x?["sample"]?["size"]) == "UNCALIBRATED" || S(x?["sample"]?["tolerance"]) == "UNCALIBRATED");

    public static List<string> RebuildIssues(string kind, JsonObject? rec)
    {
        if (!Cheap.Contains(kind)) return ["only cheap accelerators are rebuilt on site (vectors never: site_embedding NEVER)"];
        if (rec is null) return ["no rebuild evidence"];
        var out_ = new List<string>();
        if (S(rec["status"]) != "VERIFIED") out_.Add("rebuild not verified");
        if (rec["builder"] is not JsonObject b || !new[] { "name", "version", "commit" }.All(k => S(b[k]) is { Length: > 0 }))
            out_.Add("rebuild provenance (builder name, version, commit) incomplete");
        if (!(Sha64(rec["source_digest"]) && Sha64(rec["result_digest"]))) out_.Add("rebuild source_digest/result_digest missing or malformed");
        if (rec["checks"] is not JsonObject checks || checks.Any(kv => S(kv.Value) is not ("PASS" or "FAIL")))
            out_.Add("rebuild check results missing or malformed");
        else
        {
            var passed = checks.Where(kv => S(kv.Value) == "PASS").Select(kv => kv.Key).ToHashSet(StringComparer.Ordinal);
            if (RequiredChecks[kind].Any(r => !passed.Contains(r))) out_.Add("a required check did not pass on the rebuilt component");
            if (checks.Any(kv => S(kv.Value) == "FAIL")) out_.Add("a check failed on the rebuilt component");
        }
        return out_;
    }

    /// Mirror of activation_outcome: {result, service_level, site_embedding, refusal, reasons, components, uncalibrated_in_use}.
    public static JsonObject Decide(IReadOnlyDictionary<string, string> results, IReadOnlyDictionary<string, JsonObject?> contracts, string mode,
                                    IReadOnlyDictionary<string, JsonObject?>? rebuilds = null)
    {
        rebuilds ??= new Dictionary<string, JsonObject?>();
        JsonObject Refuse(string code, IEnumerable<string> why, JsonObject? comps = null, IEnumerable<string>? uncal = null) => new()
        {
            ["result"] = "REFUSED", ["service_level"] = "NOT_SERVING", ["site_embedding"] = "NEVER", ["refusal"] = code,
            ["reasons"] = new JsonArray(why.Select(w => (JsonNode)w).ToArray()), ["components"] = comps ?? new JsonObject(),
            ["uncalibrated_in_use"] = new JsonArray((uncal ?? []).Select(u => (JsonNode)u).ToArray()),
        };
        if (!Modes.Contains(mode)) return Refuse("INVALID_INPUT", ["unknown mode"]);
        if (results.Keys.Any(k => !Kinds.Contains(k))) return Refuse("INVALID_INPUT", ["unknown component kind in results"]);
        if (rebuilds.Keys.Any(k => !Cheap.Contains(k))) return Refuse("INVALID_INPUT", ["rebuild evidence for a kind that is never rebuilt on site"]);
        var states = Kinds.ToDictionary(k => k, k => results.GetValueOrDefault(k) ?? "MISSING", StringComparer.Ordinal);
        if (states.Values.Any(v => !States.Contains(v))) return Refuse("INVALID_INPUT", ["unknown component state"]);
        var comps = new JsonObject(); var reasons = new List<string>(); var missingRebuild = new List<string>();
        foreach (var k in Kinds)
        {
            if (states[k] == "VERIFIED") comps[k] = new JsonObject { ["state"] = "VERIFIED" };
            else if (Cheap.Contains(k))
            {
                var why = RebuildIssues(k, rebuilds.GetValueOrDefault(k));
                if (why.Count > 0)
                {
                    comps[k] = new JsonObject { ["state"] = "REBUILD_REQUIRED", ["input_state"] = states[k], ["why"] = new JsonArray(why.Select(w => (JsonNode)w).ToArray()) };
                    missingRebuild.Add(k);
                }
                else
                {
                    var r = rebuilds[k]!;
                    comps[k] = new JsonObject { ["state"] = "REBUILT_VERIFIED", ["input_state"] = states[k], ["builder"] = r["builder"]!.DeepClone(),
                        ["source_digest"] = S(r["source_digest"]), ["result_digest"] = S(r["result_digest"]), ["checks"] = r["checks"]!.DeepClone() };
                }
            }
            else comps[k] = new JsonObject { ["state"] = "NOT_USED", ["input_state"] = states[k] };
        }
        string St(string k) => S(comps[k]!["state"])!;
        var inUse = Kinds.Where(k => St(k) is "VERIFIED" or "REBUILT_VERIFIED").Order(StringComparer.Ordinal).ToList();
        var bad = inUse.Where(k => contracts.GetValueOrDefault(k) is not { } c || S(c["kind"]) != k || ContractRuleIssues(c).Count > 0).ToList();
        if (bad.Count > 0) return Refuse("CONTRACT_INVALID", ["missing or invalid verification contract: " + string.Join(", ", bad)], comps);
        if (missingRebuild.Count > 0)
            return Refuse("REBUILD_REQUIRED", ["cheap accelerator failed or missing and not rebuilt and verified: " + string.Join(", ", missingRebuild.Order(StringComparer.Ordinal))], comps);
        var level = St("VECTOR_PACK") == "VERIFIED" ? "FULL" : "DEGRADED_LEXICAL_ONLY";
        if (level != "FULL") reasons.Add("vectors missing or failed: lexical-only service, no site embedding");
        var rebuilt = Kinds.Where(k => St(k) == "REBUILT_VERIFIED").Order(StringComparer.Ordinal).ToList();
        if (rebuilt.Count > 0) reasons.Add("rebuilt locally and verified: " + string.Join(", ", rebuilt));
        var uncal = inUse.Where(k => Uncalibrated(contracts[k]!)).ToList();
        if (uncal.Count > 0 && mode == "production")
            return Refuse("UNCALIBRATED_IN_PRODUCTION", reasons.Append($"uncalibrated sampled checks in use in production ({OwnerGateUncalibratedProduction} open): " + string.Join(", ", uncal)), comps, uncal);
        if (uncal.Count > 0) reasons.Add("uncalibrated sampled checks (development only): " + string.Join(", ", uncal));
        var result = level != "FULL" ? "ACTIVE_DEGRADED" : rebuilt.Count > 0 ? "ACTIVE_AFTER_LOCAL_REBUILD" : "ACTIVE_FULL";
        return new JsonObject
        {
            ["result"] = result, ["service_level"] = level, ["site_embedding"] = "NEVER", ["refusal"] = null,
            ["reasons"] = new JsonArray(reasons.Select(w => (JsonNode)w).ToArray()), ["components"] = comps,
            ["uncalibrated_in_use"] = new JsonArray(uncal.Select(u => (JsonNode)u).ToArray()),
        };
    }
}
