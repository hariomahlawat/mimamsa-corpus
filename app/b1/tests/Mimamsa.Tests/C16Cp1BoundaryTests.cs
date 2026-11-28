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

    [Fact]
    public void DocumentSurfacesAreBehindTheBoundaryAndEverythingElseDerivedIsRefused()
    {
        foreach (var r in new[] { "GET /api/search", "GET /api/documents/{docId}", "GET /api/documents/{docId}/text", "GET /api/documents/{docId}/sections",
                                  "GET /api/documents/{docId}/citation", "GET /api/cite" })
            Assert.Equal(RouteClass.Boundary, ActivationRouteInventory.Routes[r]);
        foreach (var prefix in new[] { "/api/graph/", "/api/reasoning/", "/api/commander/", "/api/studio/", "/api/v2/", "/api/statutes", "/api/library" })
            Assert.All(ActivationRouteInventory.Routes.Where(kv => kv.Key.Contains(' ') && kv.Key.Split(' ')[1].StartsWith(prefix, StringComparison.Ordinal)),
                       kv => Assert.Equal(RouteClass.Refused, kv.Value));
        Assert.Equal(RouteClass.Refused, ActivationRouteInventory.Classify(null));
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
