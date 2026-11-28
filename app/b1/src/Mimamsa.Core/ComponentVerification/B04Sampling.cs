// C16 Stage 3 S3-B (B04): deterministic seeded samples and the effective sample of a contract check. The .NET mirror of
// mimamsa_contract.c16.verification (seeded_sample, stratified_sample, effective_sample); golden vectors in
// app/contract/fixtures/c16/v2_1/component_verification/golden.json are reproduced by C16S3bVerificationTests.
//
// Members are string identities (doc ids, passage ids, terms, key hex): their score is
//   SHA-256("mimamsa-b04-sample/2.1|<release id>|<check id>|<member>")
// and a sample keeps the members with the smallest (score bytes, member ordinal). Sizes are INPUTS: nothing here chooses
// one. A contract check whose size or tolerance is UNCALIBRATED never runs in production (the activation outcome refuses
// first; OD-C16-UNCALIBRATED-PRODUCTION); in development it runs with the DEVELOPMENT default below, which is recorded as
// `UNCALIBRATED_DEVELOPMENT_DEFAULT` in the evidence and is never written into a contract (FG-CALIBRATED-SAMPLES open).
using System.Security.Cryptography;
using System.Text;
using System.Text.Json.Nodes;

namespace Mimamsa.Core.ComponentVerification;

public static class B04Sampling
{
    public const string Format = "mimamsa-b04-sample/2.1";

    /// NOT calibrated: development-mode stand-ins while the contracts say UNCALIBRATED (identical to the Python reference
    /// DEVELOPMENT_DEFAULTS). Tolerance null = EXACT.
    public static readonly IReadOnlyDictionary<string, (int Size, double? Tolerance)> DevelopmentDefaults = new Dictionary<string, (int, double?)>(StringComparer.Ordinal)
    {
        ["SAMPLED_REBUILD_PARITY"] = (64, null),
        ["SAMPLED_POSTINGS_REDERIVE"] = (64, null),
        ["SAMPLED_QUERY_PARITY"] = (32, null),
        ["VECTOR_SPOT_REEMBED"] = (32, 1e-4),
    };

    public static byte[] Score(string releaseId, string checkId, string member) =>
        SHA256.HashData(Encoding.UTF8.GetBytes($"{Format}|{releaseId}|{checkId}|{member}"));

    static int CompareBytes(byte[] a, byte[] b) => a.AsSpan().SequenceCompareTo(b);

    static List<string> Ordered(string releaseId, string checkId, IEnumerable<string> members)
    {
        var scored = members.Distinct(StringComparer.Ordinal).Select(m => (m, s: Score(releaseId, checkId, m))).ToList();
        scored.Sort((x, y) => CompareBytes(x.s, y.s) is var c and not 0 ? c : string.CompareOrdinal(x.m, y.m));
        return scored.Select(x => x.m).ToList();
    }

    /// The `size` members with the smallest scores, returned in ordinal order.
    public static List<string> Seeded(string releaseId, string checkId, IEnumerable<string> members, int size)
    {
        if (size < 1) throw new ArgumentOutOfRangeException(nameof(size), "sample size must be positive");
        return Ordered(releaseId, checkId, members).Take(size).Order(StringComparer.Ordinal).ToList();
    }

    /// Round-robin over strata (ordinal name order), each in ascending score order; returned in ordinal order.
    public static List<string> Stratified(string releaseId, string checkId, IReadOnlyDictionary<string, List<string>> strata, int size)
    {
        if (size < 1) throw new ArgumentOutOfRangeException(nameof(size), "sample size must be positive");
        var seen = new HashSet<string>(StringComparer.Ordinal);
        foreach (var s in strata.Values)
            foreach (var m in s.Distinct(StringComparer.Ordinal))
                if (!seen.Add(m)) throw new ArgumentException("strata overlap: " + m);
        var queues = strata.Keys.Order(StringComparer.Ordinal).Select(k => Ordered(releaseId, checkId, strata[k])).ToList();
        var outp = new List<string>();
        for (int depth = 0; outp.Count < size && queues.Any(q => depth < q.Count); depth++)
            foreach (var q in queues)
                if (depth < q.Count && outp.Count < size) outp.Add(q[depth]);
        return outp.Order(StringComparer.Ordinal).ToList();
    }

    /// The size and tolerance a sampled check runs with. Calibrated contract values win; UNCALIBRATED runs only in
    /// development with the declared default (SizeSource UNCALIBRATED_DEVELOPMENT_DEFAULT); production throws.
    public static EffectiveSample Effective(JsonObject? contract, string checkId, bool production)
    {
        var check = (contract?["checks"] as JsonArray)?.Select(x => x as JsonObject).FirstOrDefault(x => (string?)x?["check_id"] == checkId);
        var s = check?["sample"] as JsonObject;
        var sizeNode = s?["size"]; var tolNode = s?["tolerance"];
        int? size = sizeNode is JsonObject so ? (int?)so["value"] : null;
        double? tol = tolNode is JsonObject to ? (double?)to["value"] : null;
        bool exact = tolNode is JsonValue tv && tv.TryGetValue<string>(out var ts) && ts == "EXACT";
        if (size is not null && (tol is not null || exact))
            return new EffectiveSample(checkId, size.Value, exact ? null : tol, "CONTRACT_CALIBRATED");
        if (production)
            throw new UncalibratedInProductionException(checkId);
        var d = DevelopmentDefaults[checkId];
        return new EffectiveSample(checkId, size ?? d.Size, exact ? null : tol ?? d.Tolerance, "UNCALIBRATED_DEVELOPMENT_DEFAULT");
    }

    /// Explicit override (calibration study, tests). Recorded as STUDY_OVERRIDE.
    public static EffectiveSample Override(string checkId, int size, double? tolerance = null) => new(checkId, size, tolerance, "STUDY_OVERRIDE");
}

public sealed record EffectiveSample(string CheckId, int Size, double? Tolerance, string SizeSource)
{
    public JsonObject ToJson() => new()
    {
        ["size"] = Size, ["tolerance"] = Tolerance is { } t ? JsonValue.Create(t) : JsonValue.Create("EXACT"), ["size_source"] = SizeSource,
    };
}

public sealed class UncalibratedInProductionException(string checkId)
    : Exception($"UNCALIBRATED_IN_PRODUCTION: {checkId} has no calibrated sample in its contract (OD-C16-UNCALIBRATED-PRODUCTION open)")
{
    public string CheckId { get; } = checkId;
}

/// Evidence of one component verification (B04): per-check PASS | FAIL | NOT_RUN, the samples used, issues and cost.
/// Status VERIFIED only when every check the kind requires passed.
public sealed class ComponentEvidence(string kind)
{
    public string Kind { get; } = kind;
    public SortedDictionary<string, string> Checks { get; } = new(StringComparer.Ordinal);
    public SortedDictionary<string, JsonObject> Samples { get; } = new(StringComparer.Ordinal);
    public List<string> Issues { get; } = [];
    public SortedDictionary<string, long> TimingsMs { get; } = new(StringComparer.Ordinal);
    public JsonObject Facts { get; } = new();

    public void Pass(string check) { if (!Checks.TryGetValue(check, out var v) || v != "FAIL") Checks[check] = "PASS"; }
    public void Fail(string check, string issue) { Checks[check] = "FAIL"; Issues.Add($"{check}: {issue}"); }
    public void NotRun(string check, string why) { if (!Checks.ContainsKey(check)) Checks[check] = "NOT_RUN"; Issues.Add($"{check} not run: {why}"); }

    public bool Verified(IEnumerable<string> required) => required.All(r => Checks.TryGetValue(r, out var v) && v == "PASS") && !Checks.Values.Contains("FAIL");
    public string Status(IEnumerable<string> required) => Verified(required) ? "VERIFIED" : "FAILED";

    public JsonObject ToJson(IEnumerable<string> required) => new()
    {
        ["kind"] = Kind, ["status"] = Status(required),
        ["checks"] = new JsonObject(Checks.Select(kv => KeyValuePair.Create(kv.Key, (JsonNode?)kv.Value))),
        ["samples"] = new JsonObject(Samples.Select(kv => KeyValuePair.Create(kv.Key, (JsonNode?)kv.Value.DeepClone()))),
        ["issues"] = new JsonArray(Issues.Select(i => (JsonNode)i).ToArray()),
        ["timings_ms"] = new JsonObject(TimingsMs.Select(kv => KeyValuePair.Create(kv.Key, (JsonNode?)kv.Value))),
        ["facts"] = Facts.DeepClone(),
    };
}
