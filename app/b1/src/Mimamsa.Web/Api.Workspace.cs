// C15 WP5/WP6: Commander workspace and Document Studio routes. Same session, CSRF, Origin and no-store rules as the
// rest of the API; logs stay content-free (route templates only, plus metadata-only audit entries for Studio writes).
// Every corpus-derived value passes the single eligibility decision at read time: an unavailable source carries no
// source-derived field, and Studio citations of withdrawn sources show only "source no longer available".
using System.Net;
using System.Text;
using System.Text.Json.Nodes;
using Mimamsa.Core.Citation;
using Mimamsa.Core.Commander;
using Mimamsa.Core.Identity;
using Mimamsa.Core.Search;
using Mimamsa.Core.Studio;

namespace Mimamsa.Web;

public static partial class Api
{
    public const string SourceUnavailable = "Source no longer available in this installation.";
    public const string NotApprovedFooter = "Not legally approved. Prepared in Mimamsa Document Studio as a research and drafting aid. " +
        "Corpus citations are copy-pinned and must be checked against the original. Review labels are the author's workflow labels, " +
        "not legal approval. No form in this library is verified or approved for issue.";

    static async Task<(Principal? p, IResult? error)> Writer(HttpContext ctx, AppServices s)
    {
        var p = await User(ctx, s);
        if (p is null) return (null, Json(new { error = "auth" }, 401));
        if (!CsrfOk(ctx, p) || !SameOrigin(ctx)) return (null, Json(new { error = "csrf" }, 403));
        return (p, null);
    }

    static async Task<JsonObject?> Body(HttpContext ctx)
    {
        try { return (await JsonNode.ParseAsync(ctx.Request.Body))?.AsObject(); } catch { return null; }
    }

    static readonly object NotFound = new { error = "not_found", notice = "No such document in your Studio." };

    // ------------------------------------------------------------------ Commander
    static object ProvisionDto(ResolvedProvision? r, ProvisionRef pr, AppServices s)
    {
        var vd = r is { Found: true } ? s.VisibleDocument(r.DocId) : null;
        return vd is not null
            ? new { kind = pr.Kind, number = pr.Number, found = true, doc_id = (string?)r!.DocId, copy = (string?)vd.CopySha[..12], instrument = (string?)r.Instrument, heading = r.Heading, page = r.Page,
                    passage_id = r.PassageId, omitted_as_printed = r.Omitted, excerpt = r.Excerpt, link = (string?)$"/s/{r.DocId}/{Uri.EscapeDataString(pr.Number)}" }
            : new { kind = pr.Kind, number = pr.Number, found = false, doc_id = (string?)null, copy = (string?)null, instrument = (string?)null, heading = (string?)null, page = (int?)null,
                    passage_id = (string?)null, omitted_as_printed = false, excerpt = (string?)null, link = (string?)null };
    }

    static object FormHits(string query, AppServices s)
    {
        var r = s.Search.Search(query, new SearchFilters(Types: new HashSet<string> { "rules", "act", "regulations" }));
        var ix = s.Search.Index;
        var seen = new HashSet<string>();
        var hits = new List<object>();
        foreach (var h in r.Hits)
        {
            var p = ix.Passages[h.PassageIndex];
            if (!seen.Add(p.DocId + "|" + p.Page) || s.VisibleDocument(p.DocId) is not { } d) continue;
            var snip = System.Text.RegularExpressions.Regex.Replace(p.Text, @"\s+", " ").Trim();
            hits.Add(new { doc_id = d.DocId, title = d.Title, page = p.Page, snippet = snip.Length > 240 ? snip[..240] + "…" : snip,
                           link = $"/d/{d.DocId}?p={p.Page}&a={Uri.EscapeDataString(p.PassageId)}" });
            if (hits.Count == 5) break;
        }
        return new { query, total_documents = r.TotalDocuments, results = hits };
    }

    // ------------------------------------------------------------------ Studio rendering (eligibility at read time)
    static JsonObject RenderBlock(JsonNode? n, AppServices s)
    {
        var b = (JsonObject)n!.DeepClone();
        var type = b["type"]?.GetValue<string>();
        if (type is not ("citation" or "quote")) return b;
        var doc = b["doc_id"]!.GetValue<string>(); var copy = b["copy"]!.GetValue<string>(); var page = b["page"]!.GetValue<int>();
        var para = b["para"]?.GetValue<string>();
        var res = CitationResolver.Resolve(s.Generation, copy, doc, page, s.Eligible.HeldEligible, s.Eligible.CurrentVisibleCopy);
        bool available = res.State is "CITED_COPY_ELIGIBLE" or "CITED_COPY_ELIGIBLE_NOT_CURRENT";
        var d = available ? s.Generation.Documents.GetValueOrDefault(doc) : null;
        if (!available || d is null)
        {
            // nothing derived from the source is returned: no title, citation text or quotation
            return new JsonObject { ["type"] = type, ["origin"] = "corpus", ["doc_id"] = doc, ["copy"] = copy, ["page"] = page, ["available"] = false, ["notice"] = SourceUnavailable };
        }
        var rel = s.Generation.Release.ReleaseId;
        b["available"] = true;
        b["title"] = d.Title;
        b["citation"] = CitationFor(d, page, para);
        b["permalink"] = $"/cite/{rel}/{doc}/{copy}/{page}" + (para is null ? "" : $"?para={Uri.EscapeDataString(para)}");
        b["internal_reference"] = $"[{doc} · copy {copy} · p.{page} · {rel}]";
        if (res.State == "CITED_COPY_ELIGIBLE_NOT_CURRENT") b["edition_note"] = "This copy is not the current edition in the library.";
        if (type == "quote")
        {
            var pid = b["passage_id"]?.GetValue<string>();
            var passage = res.State == "CITED_COPY_ELIGIBLE" ? d.Passages.FirstOrDefault(x => x.PassageId == pid && x.Page == page) : null;
            if (passage is null) { b["quote_available"] = false; b["quote_notice"] = "The quoted passage is not available for this copy."; }
            else { b["quote_available"] = true; b["quote"] = passage.Text.Length > 1500 ? passage.Text[..1500] + "…" : passage.Text; }
        }
        return b;
    }

    static object StudioDto(StudioDoc d, AppServices s) => new
    {
        id = d.Id, title = d.Title, template = d.Template, state = d.State, version = d.Version, created_at = d.CreatedAt, updated_at = d.UpdatedAt,
        blocks = new JsonArray(d.Blocks.Select(b => (JsonNode)RenderBlock(b, s)).ToArray()),
        notice = "Working document: private to you; never added to the library, search or graph. Review states are your own labels, not legal approval.",
    };

    static string OriginLabel(string? o) => o switch { "template" => "Template heading", "suggestion" => "Automated suggestion", "corpus" => "From the library", _ => "Author" };

    static (string body, string contentType, string ext) Export(StudioDoc d, AppServices s, string format)
    {
        var blocks = d.Blocks.Select(b => RenderBlock(b, s)).ToList();
        var stamp = $"Exported {DateTime.UtcNow:yyyy-MM-dd HH:mm} UTC · version {d.Version} · state {d.State.Replace('_', ' ')} · release {s.Generation.Release.ReleaseId}";
        if (format == "md")
        {
            var sb = new StringBuilder();
            sb.Append("# ").AppendLine(d.Title).AppendLine().Append("> ").AppendLine(NotApprovedFooter).AppendLine();
            foreach (var b in blocks)
            {
                var type = b["type"]?.GetValue<string>(); var origin = b["origin"]?.GetValue<string>(); var text = b["text"]?.GetValue<string>() ?? "";
                switch (type)
                {
                    case "heading": sb.Append("## ").AppendLine(text.Replace("\n", " ")).AppendLine(); break;
                    case "question": sb.Append("- [ ] ").Append(text.Replace("\n", " ")).AppendLine($"  _({OriginLabel(origin)})_").AppendLine(); break;
                    case "citation" or "quote":
                        if (b["available"]?.GetValue<bool>() != true) { sb.AppendLine($"> [From the library] {SourceUnavailable}").AppendLine(); break; }
                        if (type == "quote" && b["quote_available"]?.GetValue<bool>() == true)
                            foreach (var line in b["quote"]!.GetValue<string>().Split('\n')) sb.Append("> ").AppendLine(line);
                        sb.AppendLine($"> — {b["citation"]!.GetValue<string>()}  ").AppendLine($"> {b["internal_reference"]!.GetValue<string>()} {b["permalink"]!.GetValue<string>()}").AppendLine();
                        break;
                    default:
                        if (origin is "suggestion") sb.AppendLine("_[Automated suggestion]_");
                        sb.AppendLine(text).AppendLine(); break;
                }
            }
            sb.AppendLine("---").AppendLine(NotApprovedFooter).AppendLine().AppendLine(stamp);
            return (sb.ToString(), "text/markdown; charset=utf-8", "md");
        }
        string E(string? x) => WebUtility.HtmlEncode(x ?? "");
        var h = new StringBuilder();
        h.Append("<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\"><title>").Append(E(d.Title)).Append("</title><style>")
         .Append("body{font:15px/1.55 Georgia,serif;max-width:46rem;margin:2rem auto;padding:0 1rem;color:#1d1d1f}")
         .Append(".banner,.footer{font:13px/1.4 system-ui,sans-serif;border:1px solid #b58105;background:#fff8e6;padding:.6rem .8rem}")
         .Append(".origin{font:11px system-ui,sans-serif;color:#555;text-transform:uppercase;letter-spacing:.04em}")
         .Append("blockquote{border-left:3px solid #888;margin:.5rem 0;padding:.2rem .8rem}.cite{font:13px system-ui,sans-serif;color:#333}")
         .Append(".na{color:#8a1c1c}</style></head><body>");
        h.Append("<h1>").Append(E(d.Title)).Append("</h1><p class=\"banner\">").Append(E(NotApprovedFooter)).Append("</p>");
        foreach (var b in blocks)
        {
            var type = b["type"]?.GetValue<string>(); var origin = b["origin"]?.GetValue<string>(); var text = b["text"]?.GetValue<string>() ?? "";
            h.Append("<section><div class=\"origin\">").Append(E(OriginLabel(origin))).Append("</div>");
            switch (type)
            {
                case "heading": h.Append("<h2>").Append(E(text)).Append("</h2>"); break;
                case "question": h.Append("<p>&#9744; ").Append(E(text)).Append("</p>"); break;
                case "citation" or "quote":
                    if (b["available"]?.GetValue<bool>() != true) { h.Append("<p class=\"na\">").Append(E(SourceUnavailable)).Append("</p>"); break; }
                    if (type == "quote" && b["quote_available"]?.GetValue<bool>() == true) h.Append("<blockquote>").Append(E(b["quote"]!.GetValue<string>()).Replace("\n", "<br>")).Append("</blockquote>");
                    h.Append("<p class=\"cite\">").Append(E(b["citation"]!.GetValue<string>())).Append("<br>").Append(E(b["internal_reference"]!.GetValue<string>())).Append(' ')
                     .Append(E(b["permalink"]!.GetValue<string>())).Append("</p>");
                    break;
                default: h.Append("<p>").Append(E(text).Replace("\n", "<br>")).Append("</p>"); break;
            }
            h.Append("</section>");
        }
        h.Append("<hr><p class=\"footer\">").Append(E(NotApprovedFooter)).Append("<br>").Append(E(stamp)).Append("</p></body></html>");
        return (h.ToString(), "text/html; charset=utf-8", "html");
    }

    static async Task<IResult> Guard(Func<Task<IResult>> f)
    {
        try { return await f(); }
        catch (StudioValidationException e) { return Json(new { error = e.Message }, 400); }
        catch (StudioConflictException e) { return Json(new { error = "conflict", notice = "This document was saved elsewhere (for example in another tab). Reload to continue.", current = e.Current }, 409); }
    }

    static void MapWorkspace(WebApplication app)
    {
        app.MapGet("/api/commander/domains", async (HttpContext ctx, AppServices s) =>
        {
            if (await User(ctx, s) is null) return Json(new { error = "auth" }, 401);
            return Json(new { label = CommanderDomains.Label, disclaimer = CommanderDomains.Disclaimer,
                              domains = CommanderDomains.All.Select(d => new { id = d.Id, title = d.Title, purpose = d.Purpose }) });
        });

        app.MapGet("/api/commander/domains/{id}", async (HttpContext ctx, string id, AppServices s) =>
        {
            if (await User(ctx, s) is null) return Json(new { error = "auth" }, 401);
            var d = CommanderDomains.Get(id);
            if (d is null) return Json(new { error = "not_found" }, 404);
            var src = s.Commander;
            return Json(new
            {
                id = d.Id, title = d.Title, purpose = d.Purpose, label = CommanderDomains.Label, disclaimer = CommanderDomains.Disclaimer, source = src.Description,
                groups = d.Groups.Select(g => new { label = g.Label, note = g.Note, items = g.Items.Select(i => ProvisionDto(src.Resolve(i), i, s)) }),
                safeguards = d.Safeguards.Select(i => ProvisionDto(src.Resolve(i), i, s)),
                forms = d.FormQueries.Select(q => FormHits(q, s)),
                forms_note = "Search results in the held Acts, Rules and Regulations, shown as candidates: this is not a form registry. No form in this library is verified, applicable or approved for issue.",
                review_questions = d.ReviewQuestions,
                review_note = "Questions a competent legal adviser should answer before any action. They are prompts, not conclusions.",
            });
        });

        // ---------------- Studio (owner-only; an unknown id and someone else's id both answer 404)
        app.MapGet("/api/studio/templates", async (HttpContext ctx, AppServices s) =>
        {
            if (await User(ctx, s) is null) return Json(new { error = "auth" }, 401);
            return Json(new { templates = StudioStore.Templates.Select(t => new { id = t.Key, label = t.Value.label, headings = t.Value.headings }),
                              note = "Generic working skeletons only. No legal form is offered: none in this library is verified or approved." });
        });

        app.MapGet("/api/studio/documents", async (HttpContext ctx, AppServices s) =>
        {
            var p = await User(ctx, s);
            if (p is null) return Json(new { error = "auth" }, 401);
            return Json(new { documents = await s.Studio.ListAsync(p.UserId) });
        });

        app.MapPost("/api/studio/documents", async (HttpContext ctx, AppServices s) =>
        {
            var (p, err) = await Writer(ctx, s); if (err is not null) return err;
            var b = await Body(ctx);
            return await Guard(async () =>
            {
                var d = await s.Studio.CreateAsync(p!.UserId, b?["title"]?.GetValue<string>(), b?["template"]?.GetValue<string>() ?? "blank");
                await s.Identity.AuditAsync(p.UserId, "studio_create", d.Id, $"template {d.Template}");
                return Json(StudioDto(d, s), 201);
            });
        });

        app.MapGet("/api/studio/documents/{id}", async (HttpContext ctx, string id, int? version, AppServices s) =>
        {
            var p = await User(ctx, s);
            if (p is null) return Json(new { error = "auth" }, 401);
            var d = await s.Studio.GetAsync(p.UserId, id, version);
            return d is null ? Json(NotFound, 404) : Json(StudioDto(d, s));
        });

        app.MapGet("/api/studio/documents/{id}/versions", async (HttpContext ctx, string id, AppServices s) =>
        {
            var p = await User(ctx, s);
            if (p is null) return Json(new { error = "auth" }, 401);
            var v = await s.Studio.VersionsAsync(p.UserId, id);
            return v is null ? Json(NotFound, 404) : Json(new { versions = v });
        });

        app.MapPost("/api/studio/documents/{id}/save", async (HttpContext ctx, string id, AppServices s) =>
        {
            var (p, err) = await Writer(ctx, s); if (err is not null) return err;
            var b = await Body(ctx);
            return await Guard(async () =>
            {
                var blocks = StudioStore.Normalise(b?["blocks"]);
                var baseVersion = b?["base_version"] is JsonValue bv && bv.TryGetValue<int>(out var bvi) ? bvi : -1;
                var d = await s.Studio.SaveAsync(p!.UserId, id, baseVersion, b?["title"]?.GetValue<string>(), b?["state"]?.GetValue<string>() ?? "draft", blocks);
                if (d is null) return Json(NotFound, 404);
                await s.Identity.AuditAsync(p.UserId, "studio_save", d.Id, $"version {d.Version}; {blocks.Count} blocks; state {d.State}");
                return Json(StudioDto(d, s));
            });
        });

        // Append blocks to the current version (used by "Add to Studio" in the reader and the Commander workspace).
        app.MapPost("/api/studio/documents/{id}/append", async (HttpContext ctx, string id, AppServices s) =>
        {
            var (p, err) = await Writer(ctx, s); if (err is not null) return err;
            var b = await Body(ctx);
            return await Guard(async () =>
            {
                var add = StudioStore.Normalise(b?["blocks"]);
                for (int attempt = 0; attempt < 3; attempt++)
                {
                    var cur = await s.Studio.GetAsync(p!.UserId, id);
                    if (cur is null) return Json(NotFound, 404);
                    var all = new JsonArray(cur.Blocks.Select(x => x!.DeepClone()).Concat(add.Select(x => x!.DeepClone())).ToArray());
                    try
                    {
                        var d = await s.Studio.SaveAsync(p.UserId, id, cur.Version, cur.Title, cur.State, StudioStore.Normalise(all));
                        if (d is null) return Json(NotFound, 404);
                        await s.Identity.AuditAsync(p.UserId, "studio_append", d.Id, $"version {d.Version}; +{add.Count} blocks");
                        return Json(StudioDto(d, s));
                    }
                    catch (StudioConflictException) when (attempt < 2) { }
                }
                return Json(new { error = "conflict" }, 409);
            });
        });

        app.MapPost("/api/studio/documents/{id}/delete", async (HttpContext ctx, string id, AppServices s) =>
        {
            var (p, err) = await Writer(ctx, s); if (err is not null) return err;
            if (!await s.Studio.DeleteAsync(p!.UserId, id)) return Json(NotFound, 404);
            await s.Identity.AuditAsync(p.UserId, "studio_delete", id, null);
            return Json(new { deleted = true });
        });

        app.MapGet("/api/studio/documents/{id}/export", async (HttpContext ctx, string id, string? format, int? version, AppServices s) =>
        {
            var p = await User(ctx, s);
            if (p is null) return Json(new { error = "auth" }, 401);
            var d = await s.Studio.GetAsync(p.UserId, id, version);
            if (d is null) return Json(NotFound, 404);
            var (body, type, ext) = Export(d, s, format == "md" ? "md" : "html");
            await s.Identity.AuditAsync(p.UserId, "studio_export", d.Id, $"version {d.Version}; {ext}");
            ctx.Response.Headers.ContentDisposition = $"attachment; filename=\"mimamsa-studio-{d.Id}-v{d.Version}.{ext}\"";
            ctx.Response.Headers["X-Content-Type-Options"] = "nosniff";
            ctx.Response.Headers.ContentSecurityPolicy = "sandbox; default-src 'none'; style-src 'unsafe-inline'";
            return Results.Text(body, type, Encoding.UTF8);
        });

        app.MapGet("/api/studio/notes", async (HttpContext ctx, AppServices s) =>
        {
            var p = await User(ctx, s);
            if (p is null) return Json(new { error = "auth" }, 401);
            var notes = await s.Studio.NotesAsync(p.UserId);
            return Json(new
            {
                notes = notes.Select(n =>
                {
                    bool hasRef = n.RefDoc is not null;
                    var res = hasRef ? CitationResolver.Resolve(s.Generation, n.RefCopy!, n.RefDoc!, n.RefPage!.Value, s.Eligible.HeldEligible, s.Eligible.CurrentVisibleCopy) : null;
                    bool ok = res is not null && res.State is "CITED_COPY_ELIGIBLE" or "CITED_COPY_ELIGIBLE_NOT_CURRENT";
                    var d = ok ? s.Generation.Documents.GetValueOrDefault(n.RefDoc!) : null;
                    return new
                    {
                        id = n.Id, text = n.Text, created_at = n.CreatedAt, has_reference = hasRef,
                        reference = !hasRef ? null : d is null ? new { available = false, notice = (string?)SourceUnavailable, title = (string?)null, citation = (string?)null, link = (string?)null }
                            : new { available = true, notice = (string?)null, title = (string?)d.Title, citation = (string?)CitationFor(d, n.RefPage!.Value, null),
                                    link = (string?)$"/cite/{s.Generation.Release.ReleaseId}/{n.RefDoc}/{n.RefCopy}/{n.RefPage}" },
                    };
                }),
            });
        });

        app.MapPost("/api/studio/notes", async (HttpContext ctx, AppServices s) =>
        {
            var (p, err) = await Writer(ctx, s); if (err is not null) return err;
            var b = await Body(ctx);
            return await Guard(async () =>
            {
                int? page = b?["ref_page"] is JsonValue pv && pv.TryGetValue<int>(out var pg) ? pg : null;
                var n = await s.Studio.AddNoteAsync(p!.UserId, b?["text"]?.GetValue<string>(), b?["ref_doc"]?.GetValue<string>(), b?["ref_copy"]?.GetValue<string>(), page);
                await s.Identity.AuditAsync(p.UserId, "studio_note", n.Id, n.RefDoc is null ? "no reference" : "with reference");
                return Json(new { id = n.Id }, 201);
            });
        });

        app.MapPost("/api/studio/notes/{id}/delete", async (HttpContext ctx, string id, AppServices s) =>
        {
            var (p, err) = await Writer(ctx, s); if (err is not null) return err;
            return await s.Studio.DeleteNoteAsync(p!.UserId, id) ? Json(new { deleted = true }) : Json(NotFound, 404);
        });
    }
}
