using System.Text.Json.Nodes;

namespace Mimamsa.Core.Generation;

/// One page of verified derived text (importer page format: text after the [[page N]] marker line).
public sealed record PageText(int Page, string Text, string Method, bool LowConfidence, double? OcrConfidence);

/// A paragraph-sized span with an exact page anchor (contract derived_text.passages).
public sealed record Passage(string DocId, string PassageId, int Page, int CharStart, int CharEnd, string? ParagraphLabel, string Text)
{
    public string Key => DocId + "#" + PassageId;
}

public sealed record Judicial(string? Court, string? Bench, IReadOnlyList<string> CaseNumbers, string? NeutralCitation,
                              IReadOnlyList<string> ReportedCitations, string? Petitioner, string? Respondent, IReadOnlyList<string> Judges);

/// Served candidate evidence anchor as recorded by the importer (unbound spans are already stripped to page-only).
public sealed record ServedAnchor(string CopySha, int Page, bool PageOnly, string? PassageId, int? CharStart, int? CharEnd, string? Quote);

public sealed record Candidate(string CandidateId, string Type, string SourceDocId, string Status, string CapabilityRestriction,
                               IReadOnlyList<string> DeferredFindings, JsonObject? EvaluationRef, JsonObject Payload,
                               JsonObject Extractor, IReadOnlyList<ServedAnchor> Anchors);

/// Verified document in the active generation, bound to exactly one verified source copy.
public sealed class DocumentRecord
{
    public required string DocId { get; init; }
    public required string DocType { get; init; }
    public string? Title { get; init; }
    public string? Number { get; init; }
    public string? IssuingAuthority { get; init; }
    public string? IssueDate { get; init; }
    public string? EffectiveDate { get; init; }
    public string? Language { get; init; }
    public string CorpusStatus { get; init; } = "unknown";
    public string? CorpusStatusNote { get; init; }
    public string? CorpusStatusAsOf { get; init; }
    public string? TextMethod { get; init; }
    public double? OcrConfidence { get; init; }
    public required string CopySha { get; init; }
    public long CopyBytes { get; init; }
    public int PageCount { get; init; }
    public string? Completeness { get; init; }
    public string Publication { get; init; } = "PUBLISHED";
    public string? AccessMarking { get; init; }
    public Judicial? Judicial { get; init; }
    public required JsonObject Provenance { get; init; }
    public required JsonObject StatusAxes { get; init; }
    public required JsonObject Restriction { get; init; }
    public required JsonObject FieldOrigin { get; init; }
    public string? DerivativeId { get; set; }
    public string? DerivativeTextSha { get; set; }
    public string? PipelineName { get; set; }
    public string? PipelineVersion { get; set; }
    public bool QuotingPermitted { get; set; } = true;
    public Dictionary<int, PageText> Pages { get; } = new();
    public List<Passage> Passages { get; } = new();
    public List<Candidate> Candidates { get; } = new();
    public bool OriginalVerified { get; set; }
    public int? Year => IssueDate is { Length: >= 4 } d && int.TryParse(d[..4], out var y) ? y : null;
    public bool IsStatute => DocType is "act" or "rules" or "regulations" or "notification" or "order";
    public string CourtOrIssuer => Judicial?.Court ?? IssuingAuthority ?? "Not recorded";
}

/// A copy held by an activated generation (current or earlier): what citation resolution may open (ASR-E06).
public sealed record HeldCopy(string Sha, string DocId, int PageCount, string FirstRelease, string GenerationId, long Bytes);

/// Release identity shown in the banner, footer and provenance (from the importer-written release/RELEASE.json).
public sealed record ReleaseInfo(string ReleaseId, long Sequence, string CreatedAt, string? HfRepo, string? HfRevision,
                                 string? ToolsCommit, string BannerText, int AuthLedgerVersion, string ExclusionChannel);

/// A4 provision-version research aid with its evidence resolved against verified copies (never authority).
public sealed record ProvisionVersion(string VersionId, string Family, string Provision, string VersionKind, string? ChangeSummary,
                                      string? EffectiveFromStatus, string? EffectiveFromDate, string? ReportedDate,
                                      string? EffectiveToStatus, string? CurrencyStatus, string DeterminationState,
                                      IReadOnlyList<ResolvedEvidence> Evidence, JsonObject Raw);

public sealed record ResolvedEvidence(string Role, string? Sha, string? DocId, int? Page, string? Edition, string Resolution);

public sealed record Abbreviation(string Code, IReadOnlyList<string> Preferred, string Origin);
