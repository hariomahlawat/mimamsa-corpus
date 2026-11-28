// C16 Tranche B Stage 3 S3-C (B07/B08): path safety for installation roots, release directories and backup archives.
// Carried from CP-1 report section 7 ("the Windows path and symlink negatives"). Every check is portable (WD-4: the
// same rules on Windows and Linux, so a release or backup that is valid on one is valid on the other):
//   PATH_NOT_ABSOLUTE        an installation root that is not fully qualified
//   PATH_DEVICE_OR_UNC       \\?\, \\.\ device paths and \\server\share UNC roots
//   PATH_TRAVERSAL           empty, "." or ".." components, or a rooted/drive-qualified relative path
//   PATH_INVALID_CHAR        control characters, <>"|?*, or a separator inside a component
//   PATH_ALTERNATE_STREAM    a ':' inside a component (NTFS alternate data stream)
//   PATH_TRAILING_DOT_SPACE  a component ending in '.' or ' ' (Win32 strips it: two names, one file)
//   PATH_RESERVED_NAME       CON, PRN, AUX, NUL, COM0-9, LPT0-9 (and superscript digits), CONIN$, CONOUT$, CLOCK$, with
//                            or without an extension
//   PATH_SHORT_NAME_ALIAS    an 8.3 alias: a component shaped like NAME~1.EXT, or (Windows, existing path) a path whose
//                            long form differs from what was given
//   PATH_CASE_COLLISION      two entries of one set that are equal under case folding (or a file that is also a
//                            directory prefix under case folding)
//   PATH_REPARSE_POINT       a symbolic link, junction or other reparse point on the path or inside a tree
// Nothing here follows a link: trees are walked with reparse points reported and never entered.
using System.Runtime.InteropServices;
using System.Text;
using System.Text.RegularExpressions;

namespace Mimamsa.Core.Install;

public sealed record PathIssue(string Code, string Path, string Detail)
{
    public override string ToString() => $"{Code}: {Path}: {Detail}";
}

public static partial class PathSafety
{
    static readonly HashSet<string> Reserved = BuildReserved();
    static HashSet<string> BuildReserved()
    {
        var s = new HashSet<string>(StringComparer.OrdinalIgnoreCase) { "CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$", "CLOCK$" };
        foreach (var d in "0123456789\u00b9\u00b2\u00b3") { s.Add("COM" + d); s.Add("LPT" + d); }
        return s;
    }

    [GeneratedRegex(@"^[^~.]{1,6}~[0-9]+(\.[^.]{0,3})?$", RegexOptions.CultureInvariant)]
    private static partial Regex ShortNameRx();

    const string InvalidChars = "<>\"|?*";

    /// Issues of one path component (a file or directory name).
    public static List<PathIssue> ComponentIssues(string name, string context)
    {
        var o = new List<PathIssue>();
        if (name.Length == 0 || name == "." || name == "..") { o.Add(new("PATH_TRAVERSAL", context, $"component '{name}'")); return o; }
        if (name.Contains(':')) o.Add(new("PATH_ALTERNATE_STREAM", context, $"component '{name}' contains ':'"));
        if (name.Any(ch => ch < 0x20 || ch == 0x7f || InvalidChars.Contains(ch) || ch == '/' || ch == '\\'))
            o.Add(new("PATH_INVALID_CHAR", context, $"component '{Printable(name)}' contains a forbidden character"));
        if (name.EndsWith('.') || name.EndsWith(' ')) o.Add(new("PATH_TRAILING_DOT_SPACE", context, $"component '{name}' ends with a dot or space"));
        var stem = name.Split('.')[0].TrimEnd(' ');
        if (Reserved.Contains(stem)) o.Add(new("PATH_RESERVED_NAME", context, $"component '{name}' is a reserved device name"));
        if (ShortNameRx().IsMatch(name)) o.Add(new("PATH_SHORT_NAME_ALIAS", context, $"component '{name}' has the form of an 8.3 short-name alias"));
        return o;
    }

    static string Printable(string s) => new(s.Select(ch => ch < 0x20 || ch == 0x7f ? '?' : ch).ToArray());

    /// A relative path inside a release, archive or store: '/' separated, no root, no drive, every component safe.
    public static List<PathIssue> RelativeIssues(string rel)
    {
        var o = new List<PathIssue>();
        if (rel.Length == 0) { o.Add(new("PATH_TRAVERSAL", rel, "empty path")); return o; }
        if (rel.Contains('\\')) o.Add(new("PATH_INVALID_CHAR", rel, "backslash in a portable relative path"));
        if (rel.StartsWith('/') || (rel.Length >= 2 && rel[1] == ':')) o.Add(new("PATH_TRAVERSAL", rel, "rooted or drive-qualified"));
        foreach (var c in rel.Split('/')) o.AddRange(ComponentIssues(c, rel));
        return o;
    }

    /// Case collisions within a set of relative paths (files and their directory prefixes).
    public static List<PathIssue> CaseCollisions(IEnumerable<string> relPaths)
    {
        var o = new List<PathIssue>();
        var seen = new Dictionary<string, string>(StringComparer.Ordinal);       // folded -> first spelling
        var kinds = new Dictionary<string, bool>(StringComparer.Ordinal);        // folded -> is file
        foreach (var p in relPaths)
        {
            var parts = p.Split('/');
            for (int i = 1; i <= parts.Length; i++)
            {
                var prefix = string.Join('/', parts.Take(i));
                var folded = Fold(prefix);
                bool isFile = i == parts.Length;
                if (seen.TryGetValue(folded, out var first))
                {
                    if (!string.Equals(first, prefix, StringComparison.Ordinal))
                        o.Add(new("PATH_CASE_COLLISION", prefix, $"collides with '{first}' under case folding"));
                    else if (kinds[folded] != isFile || (isFile && kinds[folded]))
                        o.Add(new("PATH_CASE_COLLISION", prefix, isFile && kinds[folded] ? "duplicate entry" : "both a file and a directory"));
                }
                else { seen[folded] = prefix; kinds[folded] = isFile; }
            }
        }
        return o.DistinctBy(x => x.Code + "|" + x.Path).ToList();
    }

    static string Fold(string s) => s.Normalize(NormalizationForm.FormC).ToUpperInvariant();

    /// An absolute installation root (it may not exist yet): fully qualified, no device or UNC prefix, safe components,
    /// and no existing ancestor (or itself) that is a reparse point or reached through an 8.3 alias.
    public static List<PathIssue> RootIssues(string path)
    {
        var o = new List<PathIssue>();
        if (string.IsNullOrWhiteSpace(path)) { o.Add(new("PATH_NOT_ABSOLUTE", path, "empty")); return o; }
        if (path.StartsWith(@"\\?\") || path.StartsWith(@"\\.\") || path.StartsWith("//?/") || path.StartsWith("//./"))
        { o.Add(new("PATH_DEVICE_OR_UNC", path, "device path prefix")); return o; }
        if (path.StartsWith(@"\\") || path.StartsWith("//")) { o.Add(new("PATH_DEVICE_OR_UNC", path, "UNC path")); return o; }
        if (!Path.IsPathFullyQualified(path)) { o.Add(new("PATH_NOT_ABSOLUTE", path, "not fully qualified")); return o; }
        var full = Path.GetFullPath(path);
        var root = Path.GetPathRoot(full)!;
        var rest = full[root.Length..].Split([Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar], StringSplitOptions.RemoveEmptyEntries);
        // Path.GetFullPath silently strips trailing dots/spaces on Windows: check the components as GIVEN as well
        var given = path[Math.Min(root.Length, path.Length)..].Split(['\\', '/'], StringSplitOptions.RemoveEmptyEntries);
        foreach (var c in given.Concat(rest).Distinct()) o.AddRange(ComponentIssues(c, path));
        var cur = root;
        foreach (var c in rest)
        {
            cur = Path.Combine(cur, c);
            FileSystemInfo? fi = Directory.Exists(cur) ? new DirectoryInfo(cur) : File.Exists(cur) ? new FileInfo(cur) : null;
            if (fi is null) break;
            if (IsReparse(fi)) { o.Add(new("PATH_REPARSE_POINT", cur, "symbolic link, junction or reparse point on the path")); break; }
        }
        if (OperatingSystem.IsWindows() && (Directory.Exists(full) || File.Exists(full)) && LongPath(full) is { } lp
            && !string.Equals(lp.TrimEnd('\\'), full.TrimEnd('\\'), StringComparison.OrdinalIgnoreCase))
            o.Add(new("PATH_SHORT_NAME_ALIAS", path, $"the long form of this path is '{lp}'"));
        return o.DistinctBy(x => x.Code + "|" + x.Path + "|" + x.Detail).ToList();
    }

    public static bool IsReparse(FileSystemInfo fi) => fi.Attributes.HasFlag(FileAttributes.ReparsePoint) || fi.LinkTarget is not null;

    /// Every entry of an existing tree (never following a link): reparse points, unsafe names and case collisions.
    /// Returns the relative file list as well (for inventories). The root itself must not be a reparse point.
    public static List<PathIssue> TreeIssues(string root, out List<string> files, int maxEntries = 2_000_000)
    {
        var o = new List<PathIssue>();
        files = new List<string>();
        var rootInfo = new DirectoryInfo(root);
        if (!rootInfo.Exists) { o.Add(new("PATH_NOT_FOUND", root, "directory does not exist")); return o; }
        o.AddRange(RootIssues(rootInfo.FullName));
        if (IsReparse(rootInfo)) return o;
        var all = new List<string>();
        var stack = new Stack<(DirectoryInfo dir, string rel)>();
        stack.Push((rootInfo, ""));
        int n = 0;
        while (stack.Count > 0)
        {
            var (dir, rel) = stack.Pop();
            foreach (var e in dir.EnumerateFileSystemInfos("*", new EnumerationOptions { RecurseSubdirectories = false, AttributesToSkip = 0, IgnoreInaccessible = false, MatchType = MatchType.Simple }))
            {
                if (++n > maxEntries) { o.Add(new("PATH_TOO_MANY_ENTRIES", root, $"more than {maxEntries} entries")); return o; }
                var r = rel.Length == 0 ? e.Name : rel + "/" + e.Name;
                o.AddRange(ComponentIssues(e.Name, r));
                if (IsReparse(e)) { o.Add(new("PATH_REPARSE_POINT", r, "symbolic link, junction or reparse point inside the tree")); continue; }
                all.Add(r);
                if (e is DirectoryInfo d) stack.Push((d, r));
                else files.Add(r);
            }
        }
        o.AddRange(CaseCollisions(all));
        files.Sort(StringComparer.Ordinal);
        return o;
    }

    /// Distinctness of a set of absolute roots: equal paths (case-insensitively, as on Windows) or one root nested in
    /// another are reported unless the pair is explicitly allowed.
    public static List<PathIssue> OverlapIssues(IReadOnlyDictionary<string, string> roots, Func<string, string, bool>? allowNested = null)
    {
        var o = new List<PathIssue>();
        var list = roots.Select(kv => (kv.Key, Norm(kv.Value))).ToList();
        for (int i = 0; i < list.Count; i++)
            for (int j = 0; j < list.Count; j++)
            {
                if (i == j) continue;
                var (a, pa) = list[i]; var (b, pb) = list[j];
                if (i < j && string.Equals(pa, pb, StringComparison.OrdinalIgnoreCase)) o.Add(new("ROOT_OVERLAP", pa, $"roots '{a}' and '{b}' are the same directory"));
                else if (pa.StartsWith(pb + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase) && !(allowNested?.Invoke(a, b) ?? false))
                    o.Add(new("ROOT_OVERLAP", pa, $"root '{a}' is inside root '{b}'"));
            }
        return o;
    }

    static string Norm(string p) => Path.TrimEndingDirectorySeparator(Path.GetFullPath(p));

    // ------------------------------------------------------------------ Windows 8.3 helpers
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, EntryPoint = "GetLongPathNameW", SetLastError = true)]
    static extern uint GetLongPathNameW(string shortPath, StringBuilder longPath, uint bufferLength);
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, EntryPoint = "GetShortPathNameW", SetLastError = true)]
    static extern uint GetShortPathNameW(string longPath, StringBuilder shortPath, uint bufferLength);

    /// The long form of an existing path (Windows), or null.
    public static string? LongPath(string path)
    {
        if (!OperatingSystem.IsWindows()) return null;
        var sb = new StringBuilder(1024);
        var n = GetLongPathNameW(path, sb, (uint)sb.Capacity);
        return n == 0 || n > sb.Capacity ? null : sb.ToString();
    }

    /// The 8.3 short form of an existing path (Windows), or null when the volume keeps no short names.
    public static string? ShortPath(string path)
    {
        if (!OperatingSystem.IsWindows()) return null;
        var sb = new StringBuilder(1024);
        var n = GetShortPathNameW(path, sb, (uint)sb.Capacity);
        return n == 0 || n > sb.Capacity ? null : sb.ToString();
    }
}
