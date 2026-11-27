// C15 WP3: legal knowledge graph model. Nodes and typed edges are DERIVED deterministically from the verified,
// signed generation (A4 provision versions, A5 citation edges, C14 correspondence and notices, tables of contents,
// Commander task references). Nothing here is a legal fact: every edge carries its source identity, evidence location,
// temporal scope, verification status and review state, and the builder can never emit a reviewed or verified status
// (no automatic promotion; LEGAL_KNOWLEDGE_ARCHITECTURE §5–§7, EVIDENCE_STANDARD).
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;

namespace Mimamsa.Core.Graph;

public static class NodeKind
{
    public const string Instrument = "instrument", Provision = "provision", ProvisionVersion = "provision_version", Judgment = "judgment",
        UnresolvedReference = "unresolved_reference", ProceduralRequirement = "procedural_requirement", Form = "form", CompetentAuthority = "competent_authority";
    public static readonly string[] All = { Instrument, Provision, ProvisionVersion, Judgment, UnresolvedReference, ProceduralRequirement, Form, CompetentAuthority };
}

/// Edge types use the architecture vocabulary (LEGAL_KNOWLEDGE_ARCHITECTURE §5). Stored once; rendered in both directions.
public static class EdgeType
{
    public const string Contains = "CONTAINS_PROVISION", VersionOf = "VERSION_OF", Amends = "AMENDS_PROVISION_VERSION", Omits = "OMITS_PROVISION",
        Substitutes = "SUBSTITUTES_PROVISION_TEXT", Inserts = "INSERTS_PROVISION", RepealsProvision = "REPEALS_PROVISION", Commences = "COMMENCES",
        RepealsInstrument = "REPEALS_INSTRUMENT", SavesOrTransitions = "SAVES_OR_TRANSITIONS", ReEnactedAs = "RE_ENACTED_AS",
        CitesProvision = "CITES_PROVISION", QuotesProvision = "QUOTES_PROVISION", CitesJudgment = "CITES_JUDGMENT",
        FollowsProposition = "FOLLOWS_PROPOSITION", OverrulesOrLimits = "OVERRULES_OR_LIMITS_PROPOSITION",
        ProcedureReferencesProvision = "PROCEDURE_REFERENCES_PROVISION", AuthorityFor = "COMPETENT_AUTHORITY_FOR", FormFor = "PRESCRIBES_OR_EXEMPLIFIES_FORM";
}

/// Verification is assigned by the builder from the origin of the record and can only ever be one of the first three.
/// The reviewed values exist for records accepted through the authorised review process; the builder never emits them.
public static class Verification
{
    public const string Candidate = "CANDIDATE", ExtractedStructure = "EXTRACTED_STRUCTURE", CuratedNavigation = "CURATED_NAVIGATION",
        DocumentaryChecked = "DOCUMENTARY_CHECKED", LegalReviewed = "LEGAL_REVIEWED";
    public static readonly string[] BuilderValues = { Candidate, ExtractedStructure, CuratedNavigation };
}

public sealed record GraphNode(string Id, string Kind, string Label, string? DocId, string? CopySha, bool Held, int? Page, string? Family, string? Code);

public sealed record GraphEdge(string Id, string Type, string From, string To, string Origin, string? SourceDocId, string? SourceCopySha, int? Page,
    string? Quote, string? TemporalFrom, string TemporalFromStatus, string? TemporalTo, string TemporalToStatus, string Verification,
    string ReviewState, string Uncertainty, bool HasLegalEffect);

public sealed record LegalGraph(string GenerationId, string BuilderVersion, IReadOnlyList<GraphNode> Nodes, IReadOnlyList<GraphEdge> Edges);

/// Stable identifiers shared by the builder, the store and the API.
public static partial class GraphIds
{
    // Codes for held instruments, aligned with the A5 provision node ids ("PROV:AA-1950:s.69"). Others use DOC-<doc_id>.
    public static readonly IReadOnlyDictionary<string, string> CodeByPrimaryDoc = new Dictionary<string, string>(StringComparer.Ordinal)
    {
        ["act-army-1950"] = "AA-1950", ["rules-army-rules-1954"] = "AR-1954", ["act-air-force-1950"] = "AFA-1950", ["act-navy-1957"] = "NA-1957",
        ["act-armed-forces-tribunal-2007"] = "AFT-2007", ["rules-aft-procedure-rules-2008"] = "AFT-PR-2008", ["act-ipc-1860"] = "IPC-1860",
        ["act-crpc-1973"] = "CRPC-1973", ["act-evidence-1872"] = "IEA-1872", ["act-bns-2023"] = "BNS-2023", ["act-bnss-2023"] = "BNSS-2023",
        ["act-bsa-2023"] = "BSA-2023",
    };

    [GeneratedRegex(@"^([A-Z]+?)(\d{4})$")] private static partial Regex A4Family();
    [GeneratedRegex(@"^\d{1,3}[A-Z]{0,2}")] private static partial Regex BaseNo();

    /// A4 family code ("AA1950", "AFTPR2008") to the A5/graph code ("AA-1950", "AFT-PR-2008").
    public static string CodeFromA4Family(string family) => family == "AFTPR2008" ? "AFT-PR-2008"
        : A4Family().Match(family) is { Success: true } m ? $"{m.Groups[1].Value}-{m.Groups[2].Value}" : family;

    public static string InstrumentCode(string primaryDocId) => CodeByPrimaryDoc.TryGetValue(primaryDocId, out var c) ? c : "DOC-" + primaryDocId;
    public static string Prefix(string docType) => docType switch { "rules" => "r", "regulations" => "reg", _ => "s" };
    public static string BaseSection(string number) => BaseNo().Match(number.Trim()) is { Success: true } m ? m.Value : number.Trim();

    public static string Instrument(string familyKey) => "INST:" + familyKey;
    public static string Provision(string code, string prefix, string section) => $"PROV:{code}:{prefix}.{BaseSection(section)}";
    public static string Version(string versionId) => "VER:" + versionId;
    public static string Judgment(string docId) => "JUD:" + docId;
    public static string Reference(string raw) => "REF:" + Hash(raw)[..16];
    public static string Procedure(string task) => "PROC:" + Regex.Replace(task.ToLowerInvariant(), @"[^a-z0-9]+", "-").Trim('-');

    public static string Hash(string s) => Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(s))).ToLowerInvariant();
    public static string EdgeId(string type, string from, string to, string origin, string? sourceDoc, int? page, string? quote) =>
        "E" + Hash($"{type}|{from}|{to}|{origin}|{sourceDoc}|{page}|{(quote is null ? "" : quote[..Math.Min(80, quote.Length)])}")[..20];
}
