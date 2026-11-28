// C16 CP-1 review C16-CP1-01: the complete inventory of HTTP surfaces and how each behaves when the activation journal
// manages the site (Mimamsa:Activation:Enabled). Default mode (activation off) is unaffected by this file.
//
//   Boundary          emits document-derived content and enforces the response boundary: the handler filters by the
//                     current signed exclusion state, and the final buffered check (ActivationBoundary) withholds the
//                     whole response if it names any copy excluded by the time it would be committed.
//   ContentFree       emits no document-derived content (session, health, accounts, SPA shell).
//   ProtectiveAction  a protective Admin action whose response names only what the Admin asked about (withdraw).
//   Refused           emits document-derived content but is not yet behind the boundary: refused with a content-free
//                     503 while activation is enabled (graph, reasoning, Commander, Studio incl. exports, statutes,
//                     library, relations, protected PDF/Range delivery, admin overview/scope/audit/reinstate).
//
// Every endpoint the app maps must be classified: with activation enabled the app refuses to start if one is not
// (ActivationRouteInventory.Unclassified), and a unit test compares the mapped routes in the source with this table.
using Microsoft.AspNetCore.Routing;

namespace Mimamsa.Web;

public enum RouteClass { Boundary, ContentFree, ProtectiveAction, Refused }

public static class ActivationRouteInventory
{
    public const string Fallback = "FALLBACK";

    public static readonly IReadOnlyDictionary<string, RouteClass> Routes = new Dictionary<string, RouteClass>(StringComparer.Ordinal)
    {
        // document surfaces behind the response boundary
        ["GET /api/search"] = RouteClass.Boundary,
        ["GET /api/documents/{docId}"] = RouteClass.Boundary,
        ["GET /api/documents/{docId}/text"] = RouteClass.Boundary,
        ["GET /api/documents/{docId}/sections"] = RouteClass.Boundary,
        ["GET /api/documents/{docId}/citation"] = RouteClass.Boundary,
        ["GET /api/cite"] = RouteClass.Boundary,
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
        // document-derived, not yet behind the boundary: refused while activation is enabled
        ["GET /api/admin/overview"] = RouteClass.Refused,
        ["GET /api/admin/withdraw-scope"] = RouteClass.Refused,
        ["POST /api/admin/reinstate"] = RouteClass.Refused,
        ["GET /api/admin/audit"] = RouteClass.Refused,
        ["GET /api/documents/{docId}/relations"] = RouteClass.Refused,
        ["GET /api/statutes"] = RouteClass.Refused,
        ["GET /api/library"] = RouteClass.Refused,
        ["GET /api/graph/stats"] = RouteClass.Refused,
        ["GET /api/graph/resolve"] = RouteClass.Refused,
        ["GET /api/graph/node"] = RouteClass.Refused,
        ["GET /api/graph/path"] = RouteClass.Refused,
        ["GET /api/reasoning/assess"] = RouteClass.Refused,
        ["GET /api/reasoning/rule-gate"] = RouteClass.Refused,
        ["GET /api/commander/domains"] = RouteClass.Refused,
        ["GET /api/commander/domains/{id}"] = RouteClass.Refused,
        ["GET /api/studio/templates"] = RouteClass.Refused,
        ["GET /api/studio/documents"] = RouteClass.Refused,
        ["POST /api/studio/documents"] = RouteClass.Refused,
        ["GET /api/studio/documents/{id}"] = RouteClass.Refused,
        ["GET /api/studio/documents/{id}/versions"] = RouteClass.Refused,
        ["POST /api/studio/documents/{id}/save"] = RouteClass.Refused,
        ["POST /api/studio/documents/{id}/append"] = RouteClass.Refused,
        ["POST /api/studio/documents/{id}/delete"] = RouteClass.Refused,
        ["GET /api/studio/documents/{id}/export"] = RouteClass.Refused,
        ["GET /api/studio/notes"] = RouteClass.Refused,
        ["POST /api/studio/notes"] = RouteClass.Refused,
        ["POST /api/studio/notes/{id}/delete"] = RouteClass.Refused,
        ["GET /api/v2/documents/{docId}/pdf-meta"] = RouteClass.Refused,
        ["GET /api/v2/documents/{docId}/copies/{sha}/range"] = RouteClass.Refused,
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
