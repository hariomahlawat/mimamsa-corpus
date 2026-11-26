// JSON API for the B1 research workspace. Every route except /health and /api/login requires a session. Responses
// carry Cache-Control: no-store (client policy). Nothing here generates legal text: values are records, excerpts of
// verified text, or labelled automated candidates.
using System.Text.Json.Nodes;
using System.Text.RegularExpressions;
using Mimamsa.Core.Citation;
using Mimamsa.Core.Generation;
using Mimamsa.Core.Identity;
using Mimamsa.Core.Search;

namespace Mimamsa.Web;

public static partial class Api
{
    public static readonly (string key, string label)[] Axes =
    {
        ("source_integrity", "Source integrity"), ("source_authenticity", "Source authenticity"), ("evidence_fidelity", "Evidence fidelity"),
        ("legal_applicability", "Legal applicability"), ("legal_approval", "Legal approval"), ("publication", "Publication"),
        ("dependency_freshness", "Dependency freshness"),
    };

    public const string CandidateLabel = "AUTOMATED_CANDIDATE_NOT_VERIFIED";
    public const string GateText = "Closed: needs a Legal Reviewer appointment and recorded approvals. No legal reasoning is available in this version.";
    public const string NotAvailable = "This document is not available in this installation.";

    static IResult Json(object o, int status = 200) => Results.Json(o, statusCode: status);

    static async Task<Principal?> User(HttpContext ctx, AppServices s) => await s.AuthenticateAsync(ctx);

    public static void Map(WebApplication app)
    {
        app.MapGet("/health", () => Results.Text("ok"));
        MapStatutes(app);   // C14 S3: /api/statutes, /api/documents/{id}/relations, /api/library (Api.Statutes.cs)

        app.MapPost("/api/login", async (HttpContext ctx, AppServices s) =>
        {
            if (!SameOrigin(ctx)) return Json(new { error = "origin" }, 403);
            JsonObject? body;
            try { body = (await JsonNode.ParseAsync(ctx.Request.Body))?.AsObject(); } catch { body = null; }
            var u = body?["username"]?.GetValue<string>() ?? ""; var pw = body?["password"]?.GetValue<string>() ?? "";
            var r = await s.Identity.LoginAsync(u.Trim(), pw);
            if (r is null) return Json(new { error = "The username or password is not correct, or the account is locked." }, 401);
            ctx.Response.Cookies.Append(AppServices.SessionCookie, r.Value.token, new CookieOptions
            { HttpOnly = true, SameSite = SameSiteMode.Strict, Secure = s.SecureCookies, Path = "/", IsEssential = true });
            return Json(SessionDto(r.Value.p, s));
        });

        app.MapPost("/api/logout", async (HttpContext ctx, AppServices s) =>
        {
            var p = await User(ctx, s);
            if (p is not null && (!CsrfOk(ctx, p) || !SameOrigin(ctx))) return Json(new { error = "csrf" }, 403);
            await s.Identity.LogoutAsync(ctx.Request.Cookies[AppServices.SessionCookie]);
            ctx.Response.Cookies.Delete(AppServices.SessionCookie, new CookieOptions { Path = "/", SameSite = SameSiteMode.Strict, Secure = s.SecureCookies });
            ctx.Response.Headers["Clear-Site-Data"] = "\"cache\", \"storage\"";
            return Json(new { ok = true });
        });

        app.MapGet("/api/session", async (HttpContext ctx, AppServices s) =>
        {
            var p = await User(ctx, s);
            return p is null ? Json(new { authenticated = false, release = ReleaseDto(s) }, 401) : Json(SessionDto(p, s));
        });

        app.MapGet("/api/search", async (HttpContext ctx, AppServices s) =>
        {
            var p = await User(ctx, s);
            if (p is null) return Json(new { error = "auth" }, 401);
            var q = ctx.Request.Query;
            var raw = q["q"].ToString();
            if (raw.Length > 1000) return Json(new { state = "parser_error", mode = "parser_error", error = "The query is longer than 1,000 characters.", error_position = 1000 });
            var filters = new SearchFilters(Set(q["type"]), Set(q["court"]), Int(q["year_from"]), Int(q["year_to"]), Set(q["status"]));
            var sw = System.Diagnostics.Stopwatch.StartNew();
            var res = s.Search.Search(raw, filters, q["plain"] == "1");
            var ms = sw.Elapsed.TotalMilliseconds;
            return Json(SearchDto(res, s, ms));
        });

        app.MapGet("/api/documents/{docId}", async (HttpContext ctx, string docId, AppServices s) =>
        {
            var p = await User(ctx, s);
            if (p is null) return Json(new { error = "auth" }, 401);
            var d = s.VisibleDocument(docId);
            return d is null ? Json(new { state = "unavailable", notice = NotAvailable }, 404) : Json(DocumentDto(d, s, p));
        });

        app.MapGet("/api/documents/{docId}/text", async (HttpContext ctx, string docId, int? from, int? to, AppServices s) =>
        {
            var p = await User(ctx, s);
            if (p is null) return Json(new { error = "auth" }, 401);
            var d = s.VisibleDocument(docId);
            if (d is null) return Json(new { state = "unavailable", notice = NotAvailable }, 404);
            int a = Math.Max(1, from ?? 1), b = Math.Min(d.PageCount, to ?? (a + 39));
            if (b - a > 79) b = a + 79;
            var pages = d.Pages.Values.Where(x => x.Page >= a && x.Page <= b).OrderBy(x => x.Page)
                .Select(x => new { page = x.Page, method = x.Method, low_confidence = x.LowConfidence, ocr = x.Method == "ocr", text = x.Text,
                                   passages = d.Passages.Where(ps => ps.Page == x.Page).Select(ps => new { id = ps.PassageId, start = ps.CharStart, end = ps.CharEnd, para = ps.ParagraphLabel }) });
            return Json(new { doc_id = d.DocId, copy_sha256 = d.CopySha, page_count = d.PageCount, from = a, to = b,
                              derivative = new { id = d.DerivativeId, text_sha256 = d.DerivativeTextSha, pipeline = d.PipelineName, version = d.PipelineVersion, quoting_permitted = d.QuotingPermitted },
                              text_pages = d.Pages.Keys.Order().ToArray(), text_reliability = TextReliabilityDto(d), pages });
        });

        app.MapGet("/api/documents/{docId}/sections", async (HttpContext ctx, string docId, AppServices s) =>
        {
            var p = await User(ctx, s);
            if (p is null) return Json(new { error = "auth" }, 401);
            var d = s.VisibleDocument(docId);
            if (d is null) return Json(new { state = "unavailable", notice = NotAvailable }, 404);
            return Json(new { doc_id = d.DocId, note = "Headings as printed in the held copy. Amendment notes are compilation text, not a verified amendment history.",
                              sections = d.IsStatute ? Toc.Build(d).Select(e => new { number = e.Number, heading = e.Heading, page = e.Page, passage_id = e.PassageId, omitted_as_printed = e.Omitted }) : null });
        });

        app.MapGet("/api/documents/{docId}/citation", async (HttpContext ctx, string docId, int page, string? para, AppServices s) =>
        {
            var p = await User(ctx, s);
            if (p is null) return Json(new { error = "auth" }, 401);
            var d = s.VisibleDocument(docId);
            if (d is null || page < 1 || page > d.PageCount) return Json(new { state = "unavailable", notice = NotAvailable }, 404);
            var label = d.DocType is "judgment" or "order" ? para : null;
            var rel = s.Generation.Release.ReleaseId;
            var permalink = LegalCitation.Permalink(rel, d.DocId, d.CopySha, page, label);
            bool ocr = d.Pages.TryGetValue(page, out var pg) && pg.Method == "ocr";
            return Json(new { legal = CitationFor(d, page, para), internal_reference = LegalCitation.InternalReference(d.DocId, d.CopySha, page, rel) + " " + permalink,
                              permalink, ocr_page = ocr, ocr_note = ocr ? "OCR text: for search only. Quote from the original page." : null });
        });

        app.MapGet("/api/cite", async (HttpContext ctx, string doc, string sha, int page, AppServices s) =>
        {
            var p = await User(ctx, s);
            if (p is null) return Json(new { error = "auth" }, 401);
            var r = CitationResolver.Resolve(s.Generation, sha, doc, page, s.Eligible.HeldEligible, s.Eligible.CurrentVisibleCopy);
            var held = r.Copy is null ? null : s.Generation.HeldCopies.GetValueOrDefault(r.Copy + "|" + doc);
            return Json(new { state = r.State, notice = r.Notice, copy = r.Copy, page = r.Page, doc_id = r.Copy is null ? null : doc,
                              current_copy = r.State == "CITED_COPY_ELIGIBLE_NOT_CURRENT" ? r.CurrentCopy : null,
                              copy_pages = held?.PageCount, first_release = held?.FirstRelease,
                              text_available = r.State == "CITED_COPY_ELIGIBLE" });
        });

        // ---------------- Administration (Admin role checked server-side on every call)
        app.MapGet("/api/admin/overview", async (HttpContext ctx, AppServices s) =>
        {
            var p = await User(ctx, s);
            if (p is null) return Json(new { error = "auth" }, 401);
            if (!p.IsAdmin) return Json(new { error = "This action is for Admins." }, 403);
            var g = s.Generation;
            var quarantine = g.Quarantine.Select(q => new { kind = q?["kind"]?.GetValue<string>(), id = q?["id"]?.GetValue<string>(),
                                                            reasons = (q?["reasons"] as JsonArray)?.Select(x => x?.GetValue<string>()) });
            return Json(new
            {
                release = ReleaseDto(s), generation = g.GenerationId,
                verified = new { documents = g.Documents.Count, derivatives = g.Documents.Values.Count(d => d.DerivativeId is not null),
                                 candidates = g.Documents.Values.Sum(d => d.Candidates.Count), originals_rehashed_ok = g.Documents.Values.Count(d => d.OriginalVerified) },
                load_issues = g.LoadIssues, quarantine,
                withdrawals = (await s.Policy.WithdrawalsAsync()).Select(w => new { doc_id = w.DocId, copy = w.Sha, reason = w.Reason, actor = w.Actor, at = w.At, epoch = w.Epoch }),
                policy = new { epoch = s.State.Epoch, digest = s.State.Digest },
            });
        });

        app.MapPost("/api/admin/withdraw", async (HttpContext ctx, AppServices s, ActiveStreams active) =>
        {
            var p = await User(ctx, s);
            if (p is null) return Json(new { error = "auth" }, 401);
            if (!p.IsAdmin) return Json(new { error = "This action is for Admins." }, 403);
            if (!CsrfOk(ctx, p) || !SameOrigin(ctx)) return Json(new { error = "csrf" }, 403);
            JsonObject? body;
            try { body = (await JsonNode.ParseAsync(ctx.Request.Body))?.AsObject(); } catch { body = null; }
            var docId = body?["doc_id"]?.GetValue<string>() ?? ""; var reason = (body?["reason"]?.GetValue<string>() ?? "").Trim();
            if (reason.Length < 3 || reason.Length > 500) return Json(new { error = "A reason of 3 to 500 characters is required." }, 400);
            if (!s.Generation.Documents.TryGetValue(docId, out var d)) return Json(new { error = "unknown_document" }, 404);
            var copies = (await s.Policy.CopiesOfAsync(docId)).Append(d.CopySha).Distinct().ToList();
            if (s.State.IsDocWithdrawn(docId)) return Json(new { status = "already_withdrawn", changed = false });
            var op = "withdraw-" + Guid.NewGuid().ToString("N")[..8];
            int reset = 0;
            var (epoch, digest, changed) = await s.State.WithdrawAsync(docId, copies,
                () => s.Policy.WithdrawDocCasAsync(docId, d.CopySha, op, reason, p.UserId),
                () => DeliveryTrace.Emit("admit", "policy_probe", new { operation = op, copy = d.CopySha, monotonic_ms = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds() }),
                (e, dg) => DeliveryTrace.Emit("fence", "witness", new { operation = op, copy = d.CopySha, epoch = e, digest = dg }),
                () => { foreach (var c in copies) reset += active.ResetAll(Mimamsa.Core.Delivery.ServingState.Key(docId, c)); });
            DeliveryTrace.Flush();
            await s.Identity.AuditAsync(p.UserId, "withdraw", docId, $"epoch {epoch}");
            return Json(new { status = "withdrawn", changed, epoch, reset_streams = reset, copies_withdrawn = copies.Count,
                              effect = "Every copy of this document (current and earlier editions) is removed from search, documents, citations and original delivery for every user, effective now. Byte-identical copies held under another document id are separate documents and are not affected." });
        });
    }

    // ---------------------------------------------------------------- helpers
    static bool SameOrigin(HttpContext ctx)
    {
        var origin = ctx.Request.Headers.Origin.ToString();
        if (string.IsNullOrEmpty(origin)) return ctx.Request.Headers["Sec-Fetch-Site"].ToString() is "" or "same-origin" or "none";
        return Uri.TryCreate(origin, UriKind.Absolute, out var o) && o.Authority == ctx.Request.Host.Value;
    }

    public static bool CsrfOk(HttpContext ctx, Principal p)
    {
        var h = ctx.Request.Headers["X-CSRF-Token"].ToString();
        return h.Length > 0 && System.Security.Cryptography.CryptographicOperations.FixedTimeEquals(
            System.Text.Encoding.UTF8.GetBytes(h), System.Text.Encoding.UTF8.GetBytes(p.Csrf));
    }

    static HashSet<string>? Set(Microsoft.Extensions.Primitives.StringValues v) =>
        v.Count == 0 ? null : v.SelectMany(x => (x ?? "").Split('|', StringSplitOptions.RemoveEmptyEntries)).ToHashSet(StringComparer.Ordinal);
    static int? Int(Microsoft.Extensions.Primitives.StringValues v) => int.TryParse(v.ToString(), out var i) ? i : null;

    static object ReleaseDto(AppServices s)
    {
        var r = s.Generation.Release;
        return new { release_id = r.ReleaseId, sequence = r.Sequence, created_at = r.CreatedAt, hf_repo = r.HfRepo,
                     hf_revision = r.HfRevision, hf_revision_short = r.HfRevision is { Length: >= 8 } h ? h[..8] : r.HfRevision,
                     banner = r.BannerText, auth_ledger_version = r.AuthLedgerVersion, exclusion_channel = r.ExclusionChannel,
                     generation = s.Generation.GenerationId };
    }

    static object SessionDto(Principal p, AppServices s) => new
    {
        authenticated = true, user = p.Username, role = p.Role, csrf = p.Csrf, release = ReleaseDto(s),
        degraded = new[]
        {
            new { code = "NOT_PRODUCTION", text = "Not a production installation. The library release is signed with a development key." },
        },
        capabilities = new { semantic_search = false, generative_ai = false, legal_reasoning = false, notes = false },
        gate = GateText,
    };

    static object SearchDto(SearchResult r, AppServices s, double ms)
    {
        var ix = s.Search.Index;
        var docs = new Dictionary<string, object>();
        var passages = new List<object>();
        var terms = r.HighlightTerms.ToHashSet(StringComparer.Ordinal);
        foreach (var h in r.Hits)
        {
            var p = ix.Passages[h.PassageIndex];
            var d = ix.Docs[ix.DocOf(h.PassageIndex)];
            if (!docs.ContainsKey(d.DocId)) docs[d.DocId] = DocSummary(d, s);
            var sn = Snippets.Build(p.Text, terms, r.HighlightPhrases);
            d.Pages.TryGetValue(p.Page, out var pg);
            passages.Add(new
            {
                doc_id = d.DocId, passage_id = p.PassageId, page = p.Page, paragraph_label = p.ParagraphLabel, tier = h.Tier,
                snippet = sn.Text, highlights = sn.Highlights, truncated_start = sn.TruncatedStart, truncated_end = sn.TruncatedEnd,
                reasons = h.Reasons, ocr = pg?.Method == "ocr", low_confidence = pg?.LowConfidence ?? false,
                link = $"/d/{Uri.EscapeDataString(d.DocId)}?p={p.Page}&a={p.PassageId}&copy={d.CopySha[..12]}",
            });
        }
        return new
        {
            state = r.State, mode = r.Mode, chips = r.Chips.Select(c => new { kind = c.Kind, text = c.Text, source = c.Source }),
            error = r.Error, error_position = r.ErrorPosition, total_passages = r.TotalPassages, total_documents = r.TotalDocuments,
            shown_passages = passages.Count, passages, documents = docs,
            highlight_terms = r.HighlightTerms.Concat(r.HighlightPhrases.SelectMany(x => x)).Where(t => t.Length > 1 && !Text.Stopwords.Contains(t)).Distinct().Take(60),
            facets = r.Facets.ToDictionary(kv => kv.Key, kv => kv.Value.Select(v => new { value = v.Value, count = v.Count })),
            run = new { mode_label = r.Mode == "identifier" ? "Identifier match first, then lexical" : r.Mode == "lexical" ? "Lexical (BM25)" : "Not run",
                        semantic = "not part of B1", release_id = s.Generation.Release.ReleaseId, elapsed_ms = Math.Round(ms, 1) },
            notes = r.Notes,
        };
    }

    static object DocSummary(DocumentRecord d, AppServices s) => new
    {
        doc_id = d.DocId, title = d.Title, type = d.DocType, court = d.Judicial?.Court, bench = d.Judicial?.Bench, issuer = d.IssuingAuthority,
        issue_date = d.IssueDate, number = d.Number, case_numbers = d.Judicial?.CaseNumbers, neutral_citation = d.Judicial?.NeutralCitation,
        corpus_status = d.CorpusStatus, copy_sha256 = d.CopySha, retrieved_at = d.Provenance["retrieved_at"]?.GetValue<string>(),
        source_url = d.Provenance["source_url"]?.GetValue<string>(), language = d.Language, text_method = d.TextMethod,
        candidate_outcomes = d.Candidates.Count(c => c.Type == "outcome"), release_id = s.Generation.Release.ReleaseId,
        text_reliability = d.TextAssessment?.Reliability,
    };

    [GeneratedRegex(@"^JUD:JG-([0-9a-f]{12})")] private static partial Regex JudNode();

    static Dictionary<string, List<(DocumentRecord from, Candidate c)>>? _incoming;
    static readonly object _inLock = new();

    static Dictionary<string, List<(DocumentRecord from, Candidate c)>> Incoming(AppServices s)
    {
        lock (_inLock)
        {
            if (_incoming is not null) return _incoming;
            var byPrefix = s.Generation.Documents.Values.GroupBy(d => d.CopySha[..12]).ToDictionary(g => g.Key, g => g.First().DocId);
            var map = new Dictionary<string, List<(DocumentRecord from, Candidate c)>>();
            foreach (var d in s.Generation.Documents.Values)
                foreach (var c in d.Candidates.Where(c => c.Type == "graph_edge"))
                    if (c.Payload["target"]?["node_id"]?.GetValue<string>() is { } node && JudNode().Match(node) is { Success: true } m
                        && byPrefix.TryGetValue(m.Groups[1].Value, out var target) && target != d.DocId)
                        (map.TryGetValue(target, out var l) ? l : map[target] = new()).Add((d, c));
            return _incoming = map;
        }
    }

    static object? TargetLink(Candidate c, AppServices s)
    {
        var node = c.Payload["target"]?["node_id"]?.GetValue<string>();
        if (node is null) return null;
        var m = JudNode().Match(node);
        if (!m.Success) return null;
        var d = s.Generation.Documents.Values.FirstOrDefault(x => x.CopySha.StartsWith(m.Groups[1].Value, StringComparison.Ordinal));
        return d is null || s.VisibleDocument(d.DocId) is null ? null : new { doc_id = d.DocId, title = d.Title };
    }

    /// Users never see internal node ids (they can name copies by hash, including withdrawn ones): review F02.
    static JsonObject UserPayload(JsonObject p)
    {
        var o = p.DeepClone().AsObject();
        o.Remove("source_node");
        if (o["target"] is JsonObject t) { t.Remove("node_id"); }
        return o;
    }

    static object CandidateDto(Candidate c, AppServices s) => new
    {
        candidate_id = c.CandidateId, type = c.Type, status = c.Status, label = "Candidate (automated, not verified)",
        capability_restriction = c.CapabilityRestriction, deferred_findings = c.DeferredFindings,
        evaluation = c.EvaluationRef is null ? null : new
        {
            report_path = c.EvaluationRef["report_path"]?.GetValue<string>(), report_commit = c.EvaluationRef["report_commit"]?.GetValue<string>(),
            precision = c.EvaluationRef["precision"]?.GetValue<double?>(), coverage = c.EvaluationRef["coverage_or_recall"]?.GetValue<double?>(),
            ci_note = c.EvaluationRef["ci_note"]?.GetValue<string>(), human_checked = c.EvaluationRef["human_checked"]?.GetValue<bool>() ?? false,
        },
        evaluated = c.EvaluationRef is not null,
        extractor = new { name = c.Extractor["name"]?.GetValue<string>(), version = c.Extractor["version"]?.GetValue<string>(), commit = c.Extractor["artefact_commit"]?.GetValue<string>() },
        payload = UserPayload(c.Payload),
        anchors = c.Anchors.Select(a => new { copy = a.CopySha, page = a.Page, page_only = a.PageOnly, passage_id = a.PassageId,
                                             extractor_quote = a.Quote, quote_note = a.Quote is null ? null : "Text quoted by the extractor; open the original page to read the source." }),
        target_in_library = c.Type == "graph_edge" ? TargetLink(c, s) : null,
    };

    static object DocumentDto(DocumentRecord d, AppServices s, Principal p)
    {
        var rel = s.Generation.Release;
        var prov = d.Provenance;
        // A4 families are linked to this document only through evidence that resolves to this verified copy; every
        // version of a linked family is then listed (so a later omission version without a held copy still shows).
        var families = s.Generation.ProvisionVersions.Where(v => v.Evidence.Any(e => e.DocId == d.DocId)).Select(v => v.Family).ToHashSet();
        // A4 'edition' text and HF-free evidence never name a withdrawn copy: redaction below uses the same eligibility.
        var versions = s.Generation.ProvisionVersions.Where(v => families.Contains(v.Family)).ToList();
        var incoming = Incoming(s).GetValueOrDefault(d.DocId) ?? new();
        return new
        {
            doc_id = d.DocId, doc_type = d.DocType, title = d.Title, number = d.Number, issuing_authority = d.IssuingAuthority,
            issue_date = d.IssueDate, effective_date = d.EffectiveDate, language = d.Language,
            // C14 S3 (F07): the header's language marker and reliability chip read these (they were computed but not sent)
            language_detected = d.TextAssessment?.DetectedLanguage,
            language_name = LanguageName(d.Language ?? d.TextAssessment?.DetectedLanguage),
            text_reliability = TextReliabilityDto(d),
            corpus_status = d.CorpusStatus, corpus_status_note = d.CorpusStatusNote, corpus_status_as_of = d.CorpusStatusAsOf,
            corpus_status_label = "Corpus status (display-only summary from the crawler metadata; not legal applicability)",
            text_method = d.TextMethod, ocr_confidence = d.OcrConfidence, quoting_permitted = d.QuotingPermitted,
            copy = new { sha256 = d.CopySha, bytes = d.CopyBytes, page_count = d.PageCount, completeness = d.Completeness,
                         rehashed_at_load = d.OriginalVerified, vault_key = $"vault/sha256/{d.CopySha[..2]}/{d.CopySha}" },
            judicial = d.Judicial is null ? null : new
            {
                court = d.Judicial.Court, bench = d.Judicial.Bench, case_numbers = d.Judicial.CaseNumbers, neutral_citation = d.Judicial.NeutralCitation,
                reported_citations = d.Judicial.ReportedCitations, petitioner = d.Judicial.Petitioner, respondent = d.Judicial.Respondent, judges = d.Judicial.Judges,
                judges_note = "Judges as recorded by the crawler; the list may be incomplete (review F06: SC records often hold only the first judge). Read the bench from the original.",
                cover_case_numbers = d.Judicial.CaseNumbers.Count == 0 && d.Pages.TryGetValue(1, out var p1) ? Mimamsa.Core.Search.Identifiers.CoverCaseNumberStrings(p1.Text).Distinct().Take(6).ToArray() : Array.Empty<string>(),
                cover_case_numbers_note = "Printed near the top of page 1; extracted automatically, not verified (candidate).",
            },
            field_origin = d.FieldOrigin,
            status_axes = Axes.Select(a => new
            {
                axis = a.key, label = a.label, value = d.StatusAxes[a.key]?["value"]?.GetValue<string>(),
                basis = d.StatusAxes[a.key]?["basis"]?.GetValue<string>(), evidence_ref = d.StatusAxes[a.key]?["evidence_ref"]?.GetValue<string>(),
                recorded_at = d.StatusAxes[a.key]?["recorded_at"]?.GetValue<string>(), policy_v1 = d.StatusAxes[a.key]?["policy_v1"],
            }),
            provenance = new
            {
                source_url = prov["source_url"]?.GetValue<string>(), retrieved_at = prov["retrieved_at"]?.GetValue<string>(),
                acquisition_channel = prov["acquisition_channel"]?.GetValue<string>(), source_system = prov["source_system"]?.GetValue<string>(),
                source_record_id = prov["source_record_id"]?.GetValue<string>(), original_filename = prov["original_filename"]?.GetValue<string>(),
                aliases = prov["aliases"], hf = prov["hf"], release_id = rel.ReleaseId, generation = s.Generation.GenerationId,
                pipeline = new { id = d.DerivativeId, name = d.PipelineName, version = d.PipelineVersion, text_sha256 = d.DerivativeTextSha },
                access_marking = d.AccessMarking, publication_history = new[] { new { channel = "RELEASE_ACTIVATION", release_id = rel.ReleaseId, actor = p.IsAdmin ? "site import (B1 build)" : null } },
            },
            pages = d.Pages.Values.OrderBy(x => x.Page).Select(x => new { page = x.Page, method = x.Method, low_confidence = x.LowConfidence, chars = x.Text.Length }),
            outcomes = d.Candidates.Where(c => c.Type == "outcome").Select(c => CandidateDto(c, s)),
            edges_out = d.Candidates.Where(c => c.Type == "graph_edge").Take(400).Select(c => CandidateDto(c, s)),
            edges_out_total = d.Candidates.Count(c => c.Type == "graph_edge"),
            edges_in = incoming.Where(x => s.VisibleDocument(x.from.DocId) is not null).Take(200)
                               .Select(x => new { from_doc = x.from.DocId, from_title = x.from.Title, candidate = CandidateDto(x.c, s) }),
            provision_versions = versions.Select(v => new
            {
                version_id = v.VersionId, family = v.Family, provision = v.Provision, version_kind = v.VersionKind, change_summary = v.ChangeSummary,
                effective_from = new { status = v.EffectiveFromStatus, date = v.EffectiveFromDate, reported_date = v.ReportedDate },
                effective_to_status = v.EffectiveToStatus, currency = v.CurrencyStatus, determination_state = v.DeterminationState,
                evidence = v.Evidence.Select(e => e.DocId is not null && s.VisibleDocument(e.DocId) is null
                    ? new { role = e.Role, copy = (string?)null, doc_id = (string?)null, page = (int?)null, edition = (string?)null, resolution = "COPY_NOT_AVAILABLE_IN_THIS_INSTALLATION" }
                    : new { role = e.Role, copy = e.DocId is null ? null : e.Sha, doc_id = e.DocId, page = e.Page, edition = e.Edition, resolution = e.Resolution }),
                label = "Temporal version candidate (A4): AUTOMATED_CANDIDATE_NOT_VERIFIED. Temporal chain not established.",
                linked_by = v.Evidence.Any(e => e.DocId == d.DocId) ? "evidence in this copy" : "same provision family as evidence in this copy",
            }),
            citation = new
            {
                legal = LegalCitation.Format(d, null, null),
                internal_template = LegalCitation.InternalReference(d.DocId, d.CopySha, null, rel.ReleaseId),
                release_id = rel.ReleaseId,
            },
            absence_notice = "Extracted links are candidates. No extracted link does not mean there is no related or adverse authority.",
        };
    }

    /// Legal citation for a passage (pinpoint para where the judgment prints numbered paragraphs, else page).
    public static string CitationFor(DocumentRecord d, int page, string? para) =>
        LegalCitation.Format(d, page, d.DocType is "judgment" or "order" ? para : null);
}
