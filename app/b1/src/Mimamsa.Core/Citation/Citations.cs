// Legal citation text (port of app/contract/mimamsa_contract/citation.py, design 03 §5) and citation-permalink
// resolution (port of app/importer cite(), policy app/design/policies/citation_resolution.json, ASR-E06).
using System.Globalization;
using Mimamsa.Core.Generation;

namespace Mimamsa.Core.Citation;

public static class LegalCitation
{
    static bool Ok(DocumentRecord d, string field) => d.FieldOrigin[field]?.GetValue<string>() != "llm";

    static string? FmtDate(string? iso) =>
        iso is not null && DateOnly.TryParseExact(iso, "yyyy-MM-dd", CultureInfo.InvariantCulture, DateTimeStyles.None, out var d)
            ? $"{d.Day} {d.ToString("MMMM", CultureInfo.InvariantCulture)} {d.Year}" : null;

    /// Only printed or rule/crawler metadata; LLM-derived fields omitted; absent parts omitted, never guessed.
    public static string Format(DocumentRecord d, int? page, string? paragraphLabel)
    {
        var j = d.Judicial;
        var parts = new List<string>();
        var title = Ok(d, "title") ? d.Title : null;
        string? name = j is { Petitioner: { } p, Respondent: { } r } && Ok(d, "parties") ? $"{p} v. {r}" : title;
        if (!string.IsNullOrEmpty(name)) parts.Add(name);
        string? cite = null;
        if (j?.NeutralCitation is { } nc && Ok(d, "neutral_citation")) cite = nc;
        else if (j is { ReportedCitations.Count: > 0 } && Ok(d, "reported_citations")) cite = j.ReportedCitations[0];
        else if (j is { CaseNumbers.Count: > 0 } && Ok(d, "case_numbers")) cite = j.CaseNumbers[0];
        else if (d.Number is { } num && Ok(d, "number")) cite = num;
        if (cite is not null) parts.Add(cite);
        var court = (Ok(d, "court") ? j?.Court : null) ?? (Ok(d, "issuing_authority") ? d.IssuingAuthority : null);
        var when = Ok(d, "issue_date") ? FmtDate(d.IssueDate) : null;
        var paren = string.Join(", ", new[] { court, when }.Where(x => !string.IsNullOrEmpty(x)));
        var text = parts.Count > 0 ? string.Join(", ", parts) : "[title not printed]";
        if (paren.Length > 0) text += $" ({paren})";
        if (!string.IsNullOrEmpty(paragraphLabel)) text += $", para {paragraphLabel}";
        else if (page is not null) text += $", p. {page}";
        var ef = d.StatusAxes["evidence_fidelity"]?["value"]?.GetValue<string>();
        if (ef is not ("DOCUMENTARY_CHECKED" or "FIDELITY_VERIFIED")) text += " (metadata not verified)";
        return text;
    }

    public static string InternalReference(string docId, string sha, int? page, string releaseId) =>
        $"[{docId} · copy {sha[..12]} · p.{page} · {releaseId}]";

    public static string Permalink(string releaseId, string docId, string sha, int page, string? para) =>
        $"/cite/{Uri.EscapeDataString(releaseId)}/{Uri.EscapeDataString(docId)}/{sha[..12]}/{page}" + (para is null ? "" : "/" + Uri.EscapeDataString(para));
}

public sealed record CiteResolution(string State, string? Copy, int? Page, string? CurrentCopy, string? Notice);

public static class CitationResolver
{
    public static readonly IReadOnlyDictionary<string, string?> Notices = new Dictionary<string, string?>
    {
        ["CITED_COPY_ELIGIBLE"] = null,
        ["CITED_COPY_ELIGIBLE_NOT_CURRENT"] = "This copy is not the current edition in the library.",
        ["CITED_COPY_UNAVAILABLE"] = "The cited copy is not available in this installation.",
        ["CITED_PAGE_NOT_IN_COPY"] = "The cited page does not exist in the cited copy.",
        ["AMBIGUOUS_REFERENCE"] = "The citation does not identify a single copy. Use the full reference.",
        ["REFERENCE_MISMATCH"] = "The citation's document and copy do not match.",
    };

    static CiteResolution R(string state, string? copy = null, int? page = null, string? current = null) =>
        new(state, copy, page, current, Notices[state]);

    /// Opens only the exact cited copy; never substitutes the current edition; withdrawn, restricted and not-held
    /// copies give one indistinguishable state. `excluded(docId, sha)` is the current exclusion/withdrawal state.
    public static CiteResolution Resolve(GenerationStore g, string sha12, string docId, int page, Func<string, string, bool> excluded)
    {
        var prefix = (sha12 ?? "").Trim().ToLowerInvariant();
        if (prefix.Length < 12 || prefix.Length > 64 || !prefix.All(Uri.IsHexDigit)) return R("CITED_COPY_UNAVAILABLE");
        // excluded copies are removed before disambiguation, so an ambiguity never reveals an excluded copy
        var matches = g.HeldCopies.Values.Where(h => h.Sha.StartsWith(prefix, StringComparison.Ordinal) && !excluded(h.DocId, h.Sha)).ToList();
        if (matches.Count > 1) return R("AMBIGUOUS_REFERENCE");
        if (matches.Count == 0) return R("CITED_COPY_UNAVAILABLE");
        var h = matches[0];
        if (h.DocId != docId) return R("REFERENCE_MISMATCH");
        if (h.PageCount < 1 || page < 1 || page > h.PageCount) return R("CITED_PAGE_NOT_IN_COPY");
        var current = g.Documents.TryGetValue(docId, out var d) ? d.CopySha : null;
        if (current == h.Sha) return R("CITED_COPY_ELIGIBLE", h.Sha, page, h.Sha);
        var currentOk = current is not null && !excluded(docId, current);
        return R("CITED_COPY_ELIGIBLE_NOT_CURRENT", h.Sha, page, currentOk ? current : null);
    }
}
