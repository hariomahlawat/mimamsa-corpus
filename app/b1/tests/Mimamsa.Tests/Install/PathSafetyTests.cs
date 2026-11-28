// C16 S3-C: the Windows path and symlink negatives carried from CP-1 (report section 7): reserved names, case
// collisions, 8.3 aliases, symbolic links and junctions, in release trees, installation roots and backup entries.
// Each must be refused. Runs on Windows and Linux (the rules are portable; real junctions and 8.3 names on Windows).
using Mimamsa.Core.Install;

namespace Mimamsa.Tests.Install;

public class PathSafetyTests
{
    static HashSet<string> Codes(IEnumerable<PathIssue> i) => i.Select(x => x.Code).ToHashSet();

    [Theory]
    [InlineData("CON"), InlineData("con"), InlineData("Con.txt"), InlineData("NUL.tar.gz"), InlineData("aux"), InlineData("PRN.json"),
     InlineData("COM1"), InlineData("lpt9.log"), InlineData("COM\u00b9"), InlineData("CONIN$"), InlineData("CLOCK$"), InlineData("nul .txt")]
    public void Reserved_device_names_are_refused(string name) =>
        Assert.Contains("PATH_RESERVED_NAME", Codes(PathSafety.RelativeIssues("records/" + name)));

    [Theory]
    [InlineData("PROGRA~1"), InlineData("LONGNA~2.TXT"), InlineData("abc~12"), InlineData("DOCUME~1.J")]
    public void Short_name_shaped_components_are_refused(string name) =>
        Assert.Contains("PATH_SHORT_NAME_ALIAS", Codes(PathSafety.RelativeIssues("a/" + name + "/b")));

    [Theory]
    [InlineData("a/../b", "PATH_TRAVERSAL"), InlineData("../x", "PATH_TRAVERSAL"), InlineData("/abs/x", "PATH_TRAVERSAL"), InlineData("C:x", "PATH_ALTERNATE_STREAM"),
     InlineData("a//b", "PATH_TRAVERSAL"), InlineData("a/./b", "PATH_TRAVERSAL"), InlineData("file.txt:stream", "PATH_ALTERNATE_STREAM"),
     InlineData("dir./x", "PATH_TRAILING_DOT_SPACE"), InlineData("dir /x", "PATH_TRAILING_DOT_SPACE"), InlineData("a\\b", "PATH_INVALID_CHAR"),
     InlineData("a/b?c", "PATH_INVALID_CHAR"), InlineData("a/b\u0001c", "PATH_INVALID_CHAR"), InlineData("", "PATH_TRAVERSAL")]
    public void Unsafe_relative_paths_are_refused(string rel, string code) => Assert.Contains(code, Codes(PathSafety.RelativeIssues(rel)));

    [Fact]
    public void Ordinary_names_pass()
    {
        foreach (var p in new[] { "records/documents.jsonl", "accelerators/search-index/search.sqlite", "vault/sha256/ab/" + new string('a', 64), "COMMANDER.txt", "console/x", "a~b", "CONX" })
            Assert.Empty(PathSafety.RelativeIssues(p));
    }

    [Fact]
    public void Case_collisions_are_refused()
    {
        Assert.Contains("PATH_CASE_COLLISION", Codes(PathSafety.CaseCollisions(["text/A.txt", "text/a.txt"])));
        Assert.Contains("PATH_CASE_COLLISION", Codes(PathSafety.CaseCollisions(["Docs/x", "docs/y"])));
        Assert.Contains("PATH_CASE_COLLISION", Codes(PathSafety.CaseCollisions(["a", "A/b"])));
        Assert.Contains("PATH_CASE_COLLISION", Codes(PathSafety.CaseCollisions(["a/b", "a/b"])));
        Assert.Contains("PATH_CASE_COLLISION", Codes(PathSafety.CaseCollisions(["caf\u00e9/x", "CAFE\u0301/x"])));   // NFC equal under folding
        Assert.Empty(PathSafety.CaseCollisions(["a/x", "a/y", "b/x"]));
    }

    [Fact]
    public void Device_unc_and_relative_roots_are_refused()
    {
        Assert.Contains("PATH_DEVICE_OR_UNC", Codes(PathSafety.RootIssues(@"\\?\C:\Mimamsa")));
        Assert.Contains("PATH_DEVICE_OR_UNC", Codes(PathSafety.RootIssues(@"\\.\PhysicalDrive0")));
        Assert.Contains("PATH_DEVICE_OR_UNC", Codes(PathSafety.RootIssues(@"\\server\share\Mimamsa")));
        Assert.Contains("PATH_NOT_ABSOLUTE", Codes(PathSafety.RootIssues("relative" + Path.DirectorySeparatorChar + "x")));
        var b = S3cDirs.New("roots");
        try
        {
            Assert.Contains("PATH_RESERVED_NAME", Codes(PathSafety.RootIssues(Path.Combine(b, "CON", "x"))));
            Assert.Contains("PATH_TRAILING_DOT_SPACE", Codes(PathSafety.RootIssues(Path.Combine(b, "site.") + Path.DirectorySeparatorChar + "x")));
            Assert.Empty(PathSafety.RootIssues(Path.Combine(b, "site")));
        }
        finally { S3cDirs.Delete(b); }
    }

    [Fact]
    public void Junction_or_symlink_on_a_root_or_inside_a_release_tree_is_refused()
    {
        var b = S3cDirs.New("links");
        try
        {
            var real = Directory.CreateDirectory(Path.Combine(b, "real")).FullName;
            File.WriteAllText(Path.Combine(real, "f.txt"), "x");
            var link = Path.Combine(b, "linked");
            Assert.True(S3cDirs.Link(link, real), "a junction (Windows) or symlink (Linux) can be created in a temp directory");
            // as an installation root, and as an ancestor of one
            Assert.Contains("PATH_REPARSE_POINT", Codes(PathSafety.RootIssues(link)));
            Assert.Contains("PATH_REPARSE_POINT", Codes(PathSafety.RootIssues(Path.Combine(link, "sub"))));
            // inside a release tree: reported and never followed
            var rel = Directory.CreateDirectory(Path.Combine(b, "release")).FullName;
            File.WriteAllText(Path.Combine(rel, "ok.txt"), "x");
            Assert.True(S3cDirs.Link(Path.Combine(rel, "records"), real));
            var issues = PathSafety.TreeIssues(rel, out var files);
            Assert.Contains("PATH_REPARSE_POINT", Codes(issues));
            Assert.DoesNotContain(files, f => f.StartsWith("records/"));   // the link target was not walked
            // a file symlink, where the OS allows creating one
            if (S3cDirs.FileLink(Path.Combine(b, "release2-file"), Path.Combine(real, "f.txt")))
            {
                var rel2 = Directory.CreateDirectory(Path.Combine(b, "release2")).FullName;
                File.Move(Path.Combine(b, "release2-file"), Path.Combine(rel2, "doc.pdf"));
                Assert.Contains("PATH_REPARSE_POINT", Codes(PathSafety.TreeIssues(rel2, out _)));
            }
        }
        finally { S3cDirs.Delete(b); }
    }

    [Fact]
    public void Case_collision_inside_a_tree_is_refused_where_the_filesystem_allows_one()
    {
        var b = S3cDirs.New("case");
        try
        {
            File.WriteAllText(Path.Combine(b, "Doc.txt"), "1");
            var second = Path.Combine(b, "doc.txt");
            bool distinct = !File.Exists(second);          // case-sensitive filesystem (Linux)
            if (distinct) File.WriteAllText(second, "2");
            var issues = PathSafety.TreeIssues(b, out var files);
            if (distinct) Assert.Contains("PATH_CASE_COLLISION", Codes(issues));
            else Assert.Single(files);                     // NTFS: one file; the collision is refused in archives (CaseCollisions)
        }
        finally { S3cDirs.Delete(b); }
    }

    [Fact]
    public void Eight_dot_three_alias_of_an_existing_path_is_refused_on_windows()
    {
        if (!OperatingSystem.IsWindows()) return;
        var b = S3cDirs.New("alias");
        try
        {
            var longDir = Directory.CreateDirectory(Path.Combine(b, "ALongDirectoryNameForAliasProbe")).FullName;
            var shortForm = PathSafety.ShortPath(longDir);
            if (shortForm is null || string.Equals(shortForm, longDir, StringComparison.OrdinalIgnoreCase))
            {
                // volume without 8.3 names: the shape check still refuses an alias-shaped component
                Assert.Contains("PATH_SHORT_NAME_ALIAS", Codes(PathSafety.RootIssues(Path.Combine(b, "ALONGD~1"))));
                return;
            }
            Assert.Contains("PATH_SHORT_NAME_ALIAS", Codes(PathSafety.RootIssues(shortForm)));
            Assert.DoesNotContain("PATH_SHORT_NAME_ALIAS", Codes(PathSafety.RootIssues(longDir)));
        }
        finally { S3cDirs.Delete(b); }
    }

    [Fact]
    public void Nested_or_equal_roots_are_refused()
    {
        var b = S3cDirs.New("overlap");
        try
        {
            var o = PathSafety.OverlapIssues(new Dictionary<string, string>
            {
                ["site"] = Path.Combine(b, "site"), ["text_store"] = Path.Combine(b, "site", "text-store"), ["a"] = Path.Combine(b, "A"), ["b"] = Path.Combine(b, "a"),
            });
            Assert.Contains(o, i => i.Code == "ROOT_OVERLAP" && i.Detail.Contains("'text_store' is inside root 'site'"));
            Assert.Contains(o, i => i.Code == "ROOT_OVERLAP" && i.Detail.Contains("same directory"));
        }
        finally { S3cDirs.Delete(b); }
    }
}
