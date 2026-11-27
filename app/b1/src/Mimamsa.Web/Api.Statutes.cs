// C14 S3: Statutes catalogue, statutory relationships, library home and the early Commander task home.
// Every value is a record, a count, or a quotation of verified held text with its page; candidates are labelled and
// nothing is approved. Withdrawn or ineligible documents are filtered through VisibleDocument on every route.
using Mimamsa.Core.Generation;
using Mimamsa.Core.Statutes;

namespace Mimamsa.Web;

public static partial class Api
{
    const string CandidateText = "Candidate (automated, not verified)";

    static object TextReliabilityDto(DocumentRecord d) => d.TextAssessment is not { } a ? new { state = "not_assessed", label = (string?)null, basis = (string?)null, excluded_from_search = false }
        : new
        {
            state = a.Reliability,
            label = a.Reliability switch
            {
                TextQuality.Unreliable => "Extracted text unreliable",
                TextQuality.PartlyUnreliable => "Hindi portions of the extracted text unreliable",
                TextQuality.NoText => "No extracted text",
                _ => (string?)null,
            },
            basis = (string?)a.Basis, excluded_from_search = d.TextExcludedFromSearch,
        };

    static string LanguageName(string? code) => code switch { "hi" => "Hindi", "en" => "English", "en+hi" => "English and Hindi", "none" => "No text", _ => code ?? "Not recorded" };

    static object? InstrumentDto(Instrument i, AppServices s)
    {
        var eds = i.Editions.Where(e => s.VisibleDocument(e.DocId) is not null).ToList();
        var sch = i.Schedules.Where(e => s.VisibleDocument(e.DocId) is not null).ToList();
        if (eds.Count == 0 && sch.Count == 0) return null;
        var primary = eds.FirstOrDefault(e => e.DocId == i.PrimaryDocId) ?? eds.FirstOrDefault() ?? sch[0];
        object Ed(Edition e) => new { doc_id = e.DocId, label = e.Label, language = e.Language, title = e.Title, page_count = e.PageCount, text_reliability = e.Reliability };
        return new { key = i.Key, title = i.Title, category = i.Category, number = i.Number, type = i.DocType, primary_doc = primary.DocId,
                     editions = eds.Select(Ed), schedules = sch.Select(Ed) };
    }

    static object? EvidenceDto(RelationEvidence? e, AppServices s) =>
        e is null ? null : s.VisibleDocument(e.DocId) is null
            ? new { doc_id = (string?)null, page = (int?)null, quote = (string?)null, title = (string?)null, resolution = "COPY_NOT_AVAILABLE_IN_THIS_INSTALLATION" }
            : new { doc_id = (string?)e.DocId, page = (int?)e.Page, quote = (string?)e.Quote, title = s.Generation.Documents[e.DocId].Title, resolution = "RESOLVED_TO_VERIFIED_COPY" };

    static void MapStatutes(WebApplication app)
    {
        app.MapGet("/api/statutes", async (HttpContext ctx, AppServices s) =>
        {
            var p = await User(ctx, s);
            if (p is null) return Json(new { error = "auth" }, 401);
            var list = s.Generation.Documents.Values.Where(d => d.IsStatute && s.VisibleDocument(d.DocId) is not null)
                .OrderBy(d => d.DocType).ThenBy(d => d.Title, StringComparer.OrdinalIgnoreCase)
                .Select(d => new { doc_id = d.DocId, title = d.Title, type = d.DocType, number = d.Number, issue_date = d.IssueDate, corpus_status = d.CorpusStatus,
                                   language = d.Language, page_count = d.PageCount, text_reliability = d.TextAssessment?.Reliability });
            var rel = s.Generation.Relations;
            return Json(new
            {
                statutes = list,
                categories = InstrumentCatalog.CategoryOrder,
                instruments = rel.Instruments.Select(i => InstrumentDto(i, s)).Where(x => x is not null),
                note = "One entry per instrument; editions, language versions and schedules are nested. Categories are a navigation aid, not a legal classification.",
            });
        });

        // Statutory relationships of a document's instrument: notices (commencement, repeal, savings and transitional text,
        // repealed-by) and candidate correspondence for one section (?section=) or for the sections printed on a page (?page=).
        app.MapGet("/api/documents/{docId}/relations", async (HttpContext ctx, string docId, string? section, int? page, AppServices s) =>
        {
            var p = await User(ctx, s);
            if (p is null) return Json(new { error = "auth" }, 401);
            var d = s.VisibleDocument(docId);
            if (d is null) return Json(new { state = "unavailable", notice = NotAvailable }, 404);
            var rel = s.Generation.Relations;
            var inst = d.IsStatute ? rel.InstrumentOf(d.DocId) : null;
            if (inst is null) return Json(new { doc_id = d.DocId, instrument = (object?)null, notices = Array.Empty<object>(), correspondence = Array.Empty<object>() });
            var sections = new List<string>();
            if (!string.IsNullOrWhiteSpace(section)) sections.Add(Correspondence.Base(section.Trim()) is { Length: > 0 } b ? b : section.Trim());
            else if (page is int pg) sections.AddRange(Toc.Build(d).Where(e => e.Page == pg).Select(e => e.Number).Distinct());
            object Target(string family, string sec)
            {
                var ti = rel.Family(family);
                var tdoc = ti is null ? null : ti.Editions.Select(e => e.DocId).FirstOrDefault(id => s.VisibleDocument(id) is not null && id == ti.PrimaryDocId)
                                              ?? ti.Editions.Select(e => e.DocId).FirstOrDefault(id => s.VisibleDocument(id) is not null);
                return new { family, title = ti?.Title, section = sec, doc_id = tdoc, held = tdoc is not null };
            }
            var corr = sections.SelectMany(sec => rel.EdgesFor(inst.Key, sec)
                    .Where(e => s.VisibleDocument(e.TableDocId) is not null)
                    .Select(e => new
                    {
                        this_section = sec,
                        direction = e.NewFamily == inst.Key ? "replaces" : "replaced_by",
                        new_section = e.NewSection, old_section = e.OldSection, new_provision = e.NewProvision,
                        other = e.NewFamily == inst.Key
                            ? (e.NewProvision ? null : (object?)e.OldBases.Select(b => Target(e.OldFamily, b)).ToList())
                            : new[] { Target(e.NewFamily, e.NewBase) },
                        evidence = new { doc_id = e.TableDocId, page = e.Page, row = e.RowText, title = s.Generation.Documents[e.TableDocId].Title, source = "secondary comparison table" },
                        label = CandidateText, determination = CandidateLabel,
                    }))
                .ToList();
            var notices = (rel.Notices.GetValueOrDefault(inst.Key) ?? new()).Select(n => new { kind = n.Kind, title = n.Title, text = n.Text, basis = n.Basis, evidence = EvidenceDto(n.Evidence, s) });
            return Json(new
            {
                doc_id = d.DocId,
                instrument = InstrumentDto(inst, s),
                sections,
                notices,
                correspondence = corr,
                caution = StatuteRelations.Caution,
                label = CandidateText,
                absence = "No correspondence or notice shown does not mean there is none: only the comparison tables and texts held in this library are read.",
            });
        });

        // Library home: what this installation holds, statute shortcuts, and the early Commander task home.
        app.MapGet("/api/library", async (HttpContext ctx, AppServices s) =>
        {
            var p = await User(ctx, s);
            if (p is null) return Json(new { error = "auth" }, 401);
            var g = s.Generation;
            var visible = g.Documents.Values.Where(d => s.VisibleDocument(d.DocId) is not null).ToList();
            var rel = g.Relations;
            var shortcuts = rel.Instruments.Where(i => i.DocType == "act" || i.Key == "doc:rules-army-rules-1954")
                .Where(i => i.Category != InstrumentCatalog.CategoryOrder[6])
                .Select(i => InstrumentDto(i, s)).Where(x => x is not null).Take(16);
            // Codex review of PR #70: an item whose source is not available (withdrawn, ineligible) carries NO
            // source-derived field (instrument title, heading, page, omission marker); only the fixed task label stays.
            var tasks = rel.CommanderTasks.Select(t => new
            {
                task = t.Task, purpose = t.Purpose,
                items = t.Items.Select(it =>
                {
                    bool available = it.Found && it.DocId is not null && s.VisibleDocument(it.DocId) is not null;
                    return new
                    {
                        kind = it.Kind, number = it.Number,
                        instrument = available ? g.Documents.GetValueOrDefault(it.DocId!)?.Title : null,
                        doc_id = available ? it.DocId : null,
                        heading = available ? it.Heading : null,
                        page = available ? it.Page : null,
                        omitted_as_printed = available && it.Omitted,
                        found = available,
                    };
                }),
            });
            return Json(new
            {
                release = new { release_id = g.Release.ReleaseId, created_at = g.Release.CreatedAt, hf_revision_short = g.Release.HfRevision?[..Math.Min(8, g.Release.HfRevision.Length)] },
                documents = visible.Count,
                pages = visible.Sum(d => d.PageCount),
                by_type = visible.GroupBy(d => d.DocType).OrderByDescending(x => x.Count()).Select(x => new { type = x.Key, count = x.Count() }),
                by_court = visible.Where(d => d.Judicial?.Court is not null).GroupBy(d => d.Judicial!.Court!).OrderByDescending(x => x.Count()).Select(x => new { court = x.Key, count = x.Count() }),
                years = visible.Where(d => d.Year is not null).Select(d => d.Year!.Value).DefaultIfEmpty().Aggregate((min: int.MaxValue, max: int.MinValue), (a, y) => (Math.Min(a.min, y), Math.Max(a.max, y))) is var r && r.min <= r.max ? new { from = r.min, to = r.max } : null,
                unreliable_text = visible.Count(d => d.TextAssessment?.Reliability == TextQuality.Unreliable),
                shortcuts,
                commander_tasks = tasks,
                commander_note = "Early Commander workspace: task headings are navigation aids; each provision is shown with its heading as printed in the held copy. It is not legal advice and does not decide what applies to a case.",
                examples = new[] { "s.69 Army Act", "Rule 22 Army Rules", "2013 INSC 408", "\"summary of evidence\"", "disability pension invalided", "section 302 Indian Penal Code" },
            });
        });
    }
}
