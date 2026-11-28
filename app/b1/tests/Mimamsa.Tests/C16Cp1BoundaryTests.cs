// C16 CP-1 review C16-CP1-01/03 unit tests (no database, no web process): the route inventory covers every route the
// web project maps (and nothing else), unknown routes are refused, and the final buffered check names every copy a
// response mentions. The end-to-end behaviour (withdrawal on every surface, paused requests) is in C16Cp1SliceTests.
using System.Text;
using System.Text.RegularExpressions;
using Mimamsa.Web;

namespace Mimamsa.Tests;

public class C16Cp1BoundaryTests
{
    static readonly Regex MapRx = new(@"\bapp\.Map(Get|Post|Put|Delete|Patch)\(\s*""([^""]+)""", RegexOptions.CultureInvariant);

    static List<string> MappedRoutesInSource()
    {
        var dir = ServiceFixture.WebDir();
        var keys = new List<string>();
        foreach (var f in Directory.EnumerateFiles(dir, "*.cs", SearchOption.AllDirectories).Where(f => !f.Contains(Path.DirectorySeparatorChar + "obj" + Path.DirectorySeparatorChar) && !f.Contains(Path.DirectorySeparatorChar + "bin" + Path.DirectorySeparatorChar)))
            foreach (Match m in MapRx.Matches(File.ReadAllText(f)))
                keys.Add($"{m.Groups[1].Value.ToUpperInvariant()} {m.Groups[2].Value}");
        return keys.Distinct().Order(StringComparer.Ordinal).ToList();
    }

    [Fact]
    public void EveryMappedRouteIsClassifiedAndTheInventoryHasNoStaleEntries()
    {
        var mapped = MappedRoutesInSource();
        Assert.True(mapped.Count >= 40, $"route scan found only {mapped.Count} routes");
        var inventory = ActivationRouteInventory.Routes.Keys.Where(k => k != ActivationRouteInventory.Fallback).Order(StringComparer.Ordinal).ToList();
        Assert.Equal(inventory, mapped);   // a new route fails here until it is classified (and the app refuses to start)
        var src = string.Join("\n", Directory.EnumerateFiles(ServiceFixture.WebDir(), "*.cs").Select(File.ReadAllText));
        Assert.Contains("MapFallback(", src);
        Assert.DoesNotContain("MapMethods(", src);
        Assert.DoesNotContain("MapGroup(", src);
    }

    /// C16 Stage 3 (S3-D): every surface CP-1 refused is now behind the response boundary; only unknown routes are
    /// refused. Document-derived surfaces are Boundary (buffered, body scanned), the user's own Studio documents and notes
    /// BoundaryPrivate (buffered, touched sources re-checked), protected Range delivery BoundaryStreaming.
    [Fact]
    public void EverySurfaceIsBehindTheBoundaryAndOnlyUnknownRoutesAreRefused()
    {
        foreach (var r in new[] { "GET /api/search", "GET /api/documents/{docId}", "GET /api/documents/{docId}/text", "GET /api/documents/{docId}/sections",
                                  "GET /api/documents/{docId}/citation", "GET /api/cite", "GET /api/documents/{docId}/relations", "GET /api/statutes", "GET /api/library",
                                  "GET /api/admin/overview", "GET /api/admin/withdraw-scope", "POST /api/admin/reinstate", "GET /api/admin/audit",
                                  "GET /api/v2/documents/{docId}/pdf-meta" })
            Assert.Equal(RouteClass.Boundary, ActivationRouteInventory.Routes[r]);
        var byPrefix = new Dictionary<string, (RouteClass cls, int count)>
        {
            ["/api/graph/"] = (RouteClass.Boundary, 4), ["/api/reasoning/"] = (RouteClass.Boundary, 2), ["/api/commander/"] = (RouteClass.Boundary, 2),
            ["/api/studio/"] = (RouteClass.BoundaryPrivate, 12), ["/api/v2/documents/{docId}/copies/"] = (RouteClass.BoundaryStreaming, 1),
        };
        foreach (var (prefix, (cls, count)) in byPrefix)
        {
            var routes = ActivationRouteInventory.Routes.Where(kv => kv.Key.Contains(' ') && kv.Key.Split(' ')[1].StartsWith(prefix, StringComparison.Ordinal)).ToList();
            Assert.Equal(count, routes.Count);
            Assert.All(routes, kv => Assert.Equal(cls, kv.Value));
        }
        Assert.DoesNotContain(RouteClass.Refused, ActivationRouteInventory.Routes.Values);
        Assert.Equal(RouteClass.Refused, ActivationRouteInventory.Classify(null));
        // 44 mapped routes and the SPA fallback; CP-1 refused 29 of them (its report said 45 routes, Studio 13 and 30 refused;
        // the inventory itself has 44 mapped routes, 12 of them Studio)
        Assert.Equal(45, ActivationRouteInventory.Routes.Count);
        Assert.Equal(RouteClass.ProtectiveAction, ActivationRouteInventory.Routes["POST /api/admin/withdraw"]);
    }

    [Fact]
    public void TheFinalCheckNamesEveryServedDocumentAndHeldCopyInTheBody()
    {
        var g = Syn.Gen;
        var b = new ActivationBoundary(null!, g, null);
        var d = g.Documents.Values.OrderBy(x => x.DocId, StringComparer.Ordinal).First();
        var other = g.Documents.Values.OrderBy(x => x.DocId, StringComparer.Ordinal).Last();
        var body = Encoding.UTF8.GetBytes($$"""{"groups":[{"variants":[{"doc_id":"{{d.DocId}}","title":"x"}]}],"nested":{"deep":["{{other.CopySha}}"]},"text":"no ids here"}""");
        var named = b.Named(body);
        Assert.Contains((d.DocId, (string?)d.CopySha), named);
        Assert.Contains(named, x => x.doc == other.DocId && x.sha == other.CopySha);
        Assert.Empty(b.Named(Encoding.UTF8.GetBytes("""{"ok":true}""")));
        Assert.Contains(b.Named(Encoding.UTF8.GetBytes("not json")), x => x.doc.StartsWith('\u0000'));   // never released
    }
}
