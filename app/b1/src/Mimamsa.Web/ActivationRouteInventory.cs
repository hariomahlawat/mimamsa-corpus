// C16 CP-1 review C16-CP1-01: the complete inventory of HTTP surfaces and how each behaves when the activation journal
// manages the site (Mimamsa:Activation:Enabled). Default mode (activation off) is unaffected by this file.
// C16 Stage 3 (S3-D): every surface that CP-1 refused is now behind the response boundary; nothing is Refused except
// unknown routes.
//
//   Boundary           emits document-derived content and enforces the response boundary: handlers filter through the
//                      single eligibility decision (Eligibility.Boundary), and the final buffered check
//                      (ActivationBoundary.MayCommit) withholds the whole response if it touched or names any copy
//                      excluded by the time it would be committed.
//   BoundaryPrivate    the user's own Studio documents and notes: handlers render sources through the same eligibility
//                      decision (an unavailable source shows only the content-free "source no longer available" form);
//                      the final buffered check re-checks every source the handler rendered (the touched set). The
//                      body is not scanned for ids, because the author's own stored reference fields stay in the
//                      unavailable form (C15) and are not corpus content.
//   BoundaryStreaming  protected PDF Range delivery: checked before the first byte and again immediately before each
//                      slice is handed to the transport (bounded drain); bytes already sent are not recalled.
//   ContentFree        emits no document-derived content (session, health, accounts, SPA shell).
//   ProtectiveAction   a protective Admin action whose response names only what the Admin asked about (withdraw).
//   Refused            not classified: refused with a content-free 503 while activation is enabled (fail closed).
//
// Every endpoint the app maps must be classified: with activation enabled the app refuses to start if one is not
// (ActivationRouteInventory.Unclassified), and a unit test compares the mapped routes in the source with this table.
using Microsoft.AspNetCore.Routing;

namespace Mimamsa.Web;

public enum RouteClass { Boundary, BoundaryPrivate, BoundaryStreaming, ContentFree, ProtectiveAction, Refused }

public static class ActivationRouteInventory
{
    public const string Fallback = "FALLBACK";

    public static readonly IReadOnlyDictionary<string, RouteClass> Routes = new Dictionary<string, RouteClass>(StringComparer.Ordinal)
    {
        // document surfaces behind the response boundary (CP-1)
        ["GET /api/search"] = RouteClass.Boundary,
        ["GET /api/documents/{docId}"] = RouteClass.Boundary,
        ["GET /api/documents/{docId}/text"] = RouteClass.Boundary,
        ["GET /api/documents/{docId}/sections"] = RouteClass.Boundary,
        ["GET /api/documents/{docId}/citation"] = RouteClass.Boundary,
        ["GET /api/cite"] = RouteClass.Boundary,
        // brought behind the boundary in Stage 3 (S3-D); refused under activation in CP-1
        ["GET /api/admin/overview"] = RouteClass.Boundary,
        ["GET /api/admin/withdraw-scope"] = RouteClass.Boundary,
        ["POST /api/admin/reinstate"] = RouteClass.Boundary,
        ["GET /api/admin/audit"] = RouteClass.Boundary,
        ["GET /api/documents/{docId}/relations"] = RouteClass.Boundary,
        ["GET /api/statutes"] = RouteClass.Boundary,
        ["GET /api/library"] = RouteClass.Boundary,
        ["GET /api/graph/stats"] = RouteClass.Boundary,
        ["GET /api/graph/resolve"] = RouteClass.Boundary,
        ["GET /api/graph/node"] = RouteClass.Boundary,
        ["GET /api/graph/path"] = RouteClass.Boundary,
        ["GET /api/reasoning/assess"] = RouteClass.Boundary,
        ["GET /api/reasoning/rule-gate"] = RouteClass.Boundary,
        ["GET /api/commander/domains"] = RouteClass.Boundary,
        ["GET /api/commander/domains/{id}"] = RouteClass.Boundary,
        ["GET /api/v2/documents/{docId}/pdf-meta"] = RouteClass.Boundary,
        ["GET /api/v2/documents/{docId}/copies/{sha}/range"] = RouteClass.BoundaryStreaming,
        ["GET /api/studio/templates"] = RouteClass.BoundaryPrivate,
        ["GET /api/studio/documents"] = RouteClass.BoundaryPrivate,
        ["POST /api/studio/documents"] = RouteClass.BoundaryPrivate,
        ["GET /api/studio/documents/{id}"] = RouteClass.BoundaryPrivate,
        ["GET /api/studio/documents/{id}/versions"] = RouteClass.BoundaryPrivate,
        ["POST /api/studio/documents/{id}/save"] = RouteClass.BoundaryPrivate,
        ["POST /api/studio/documents/{id}/append"] = RouteClass.BoundaryPrivate,
        ["POST /api/studio/documents/{id}/delete"] = RouteClass.BoundaryPrivate,
        ["GET /api/studio/documents/{id}/export"] = RouteClass.BoundaryPrivate,
        ["GET /api/studio/notes"] = RouteClass.BoundaryPrivate,
        ["POST /api/studio/notes"] = RouteClass.BoundaryPrivate,
        ["POST /api/studio/notes/{id}/delete"] = RouteClass.BoundaryPrivate,
        // no document-derived content
        ["GET /health"] = RouteClass.ContentFree,
        ["POST /api/login"] = RouteClass.ContentFree,
        ["POST /api/logout"] = RouteClass.ContentFree,
        ["GET /api/session"] = RouteClass.ContentFree,
        ["GET /api/policy"] = RouteClass.ContentFree,
        ["GET /api/diag/memory"] = RouteClass.ContentFree,
        ["GET /api/admin/accounts"] = RouteClass.ContentFree,
        ["POST /api/admin/unlock"] = RouteClass.ContentFree,
        [Fallback] = RouteClass.ContentFree,
        // protective action
        ["POST /api/admin/withdraw"] = RouteClass.ProtectiveAction,
    };

    /// "METHOD /pattern" for a mapped route endpoint, FALLBACK for the SPA fallback, null for anything else.
    public static IEnumerable<string> Keys(Endpoint e)
    {
        if (e is not RouteEndpoint re) yield break;
        var raw = re.RoutePattern.RawText ?? "";
        if (raw.StartsWith("{*", StringComparison.Ordinal)) { yield return Fallback; yield break; }
        var methods = e.Metadata.GetMetadata<Microsoft.AspNetCore.Routing.HttpMethodMetadata>()?.HttpMethods ?? ["*"];
        foreach (var m in methods) yield return $"{m} {raw}";
    }

    /// Unknown routes are refused (fail closed).
    public static RouteClass Classify(Endpoint? e)
    {
        if (e is null) return RouteClass.Refused;
        var keys = Keys(e).ToList();
        if (keys.Count == 0) return RouteClass.Refused;
        var classes = keys.Select(k => Routes.TryGetValue(k, out var c) ? c : RouteClass.Refused).Distinct().ToList();
        return classes.Count == 1 ? classes[0] : RouteClass.Refused;
    }

    /// Every mapped endpoint key not in the inventory (startup self-check when activation is enabled).
    public static List<string> Unclassified(IEnumerable<Endpoint> endpoints) =>
        endpoints.SelectMany(Keys).Where(k => !Routes.ContainsKey(k)).Distinct().Order(StringComparer.Ordinal).ToList();
}
