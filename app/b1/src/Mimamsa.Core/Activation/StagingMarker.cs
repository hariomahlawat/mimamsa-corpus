// C16 CP-1 review C16-CP1-02: the catalogue marker generations/<id>/C16_VERIFIED.json as bound staging EVIDENCE.
//
// A bound marker (format c16-staging-marker/1) records what staging verified and binds it to the immutable inputs:
//   - the generation's release (release_id, release_sequence, sums_sha256 = the signed SHA256SUMS digest) and the
//     sha256 and size of generation.json, KNOWLEDGE_RELEASE.json, release/RELEASE.json, every records/*.jsonl and every
//     ACCELERATOR component file;
//   - every component's verified state and result_digest;
//   - the staged database evidence: the kr_<n> schema names and each loaded table's row count and rows_sha256;
//   - the staging mode (production / development) and the owner that wrote it.
// It carries a self-digest (marker_sha256 over its canonical form without that field), is written owner-only
// (Windows: protected ACL, owner + SYSTEM + Administrators; Linux: mode 0644), and is re-validated:
//   - by GenerationCatalog.Installed (cheap: parse, self-digest, ownership, binding of generation.json and
//     KNOWLEDGE_RELEASE.json by hash, every other bound file by size);
//   - by the activation engine immediately before DECIDED and by recovery before OPEN (full: every bound file re-hashed,
//     and the staged rows re-digested in the database).
// An unbound (legacy) marker is accepted only on a simulation site carrying activation-state/SIMULATION_UNBOUND_MARKERS
// (the B06 scenario harness); GenerationStaging never writes one.
using System.Runtime.Versioning;
using System.Security.AccessControl;
using System.Security.Cryptography;
using System.Security.Principal;
using System.Text.Json.Nodes;

namespace Mimamsa.Core.Activation;

public sealed record StagedTable(string Table, long RowCount, string RowsSha256);

public sealed record StagingEvidence(
    bool LexicalOnly, bool Production, long MeasuredBytes,
    IReadOnlyDictionary<string, string> Components, IReadOnlyDictionary<string, string> ComponentDigests,
    string StagingSchema, string ActiveSchema, IReadOnlyList<StagedTable> Tables);

public static class StagingMarker
{
    public const string Format = "c16-staging-marker/1";
    public const string SimulationFlag = "SIMULATION_UNBOUND_MARKERS";

    static string Sha(string p) { using var f = File.OpenRead(p); return Convert.ToHexString(SHA256.HashData(f)).ToLowerInvariant(); }
    static string ShaBytes(byte[] b) => Convert.ToHexString(SHA256.HashData(b)).ToLowerInvariant();
    static string Local(string gdir, string rel) => Path.Combine(gdir, rel.Replace('/', Path.DirectorySeparatorChar));

    /// Paths (relative, '/') the marker binds for a generation directory.
    public static List<string> BoundPaths(string gdir)
    {
        var paths = new SortedSet<string>(StringComparer.Ordinal) { "generation.json" };
        foreach (var p in new[] { "KNOWLEDGE_RELEASE.json", "release/RELEASE.json", "corpus-v2/GENERATION.json" })
            if (File.Exists(Local(gdir, p))) paths.Add(p);
        var rec = Path.Combine(gdir, "records");
        if (Directory.Exists(rec))
            foreach (var f in Directory.EnumerateFiles(rec, "*.jsonl")) paths.Add("records/" + Path.GetFileName(f));
        var km = Local(gdir, "KNOWLEDGE_RELEASE.json");
        if (File.Exists(km))
            foreach (var c in JsonNode.Parse(File.ReadAllText(km))!["components"]!.AsArray().Select(c => c!.AsObject()).Where(c => (string?)c["authority"] == "ACCELERATOR"))
                foreach (var f in c["files"]!.AsArray()) paths.Add((string)f!["path"]!);
        return paths.ToList();
    }

    public static string OwnerId() => OperatingSystem.IsWindows() ? WindowsIdentity.GetCurrent().User!.Value : Environment.UserName;

    public static byte[] Build(SiteLayout site, string generation, StagingEvidence ev)
    {
        var gdir = Path.Combine(site.GenerationsDir, generation);
        var gen = JsonNode.Parse(File.ReadAllText(Path.Combine(gdir, "generation.json")))!.AsObject();
        var files = new JsonObject();
        foreach (var p in BoundPaths(gdir))
        {
            var full = Local(gdir, p);
            if (!File.Exists(full)) throw new ActivationRefused("STAGING_EVIDENCE_INVALID", $"bound file missing at staging: {p}");
            files[p] = new JsonObject { ["sha256"] = Sha(full), ["bytes"] = new FileInfo(full).Length };
        }
        var comps = new JsonObject(); foreach (var (k, v) in ev.Components.OrderBy(x => x.Key, StringComparer.Ordinal)) comps[k] = v;
        var digests = new JsonObject(); foreach (var (k, v) in ev.ComponentDigests.OrderBy(x => x.Key, StringComparer.Ordinal)) digests[k] = v;
        var tables = new JsonObject();
        foreach (var t in ev.Tables.OrderBy(t => t.Table, StringComparer.Ordinal)) tables[t.Table] = new JsonObject { ["rows"] = t.RowCount, ["rows_sha256"] = t.RowsSha256 };
        var o = new JsonObject
        {
            ["format"] = Format, ["generation"] = generation, ["release_id"] = (string?)gen["release_id"],
            ["release_sequence"] = gen["release_sequence"]?.GetValue<long>(), ["sums_sha256"] = (string?)gen["sums_sha256"],
            ["lexical_only"] = ev.LexicalOnly, ["production"] = ev.Production, ["measured_bytes"] = ev.MeasuredBytes,
            ["components"] = comps, ["component_digests"] = digests, ["files"] = files,
            ["db"] = new JsonObject { ["staging_schema"] = ev.StagingSchema, ["active_schema"] = ev.ActiveSchema, ["tables"] = tables },
            ["owner"] = OwnerId(),
        };
        o["marker_sha256"] = ShaBytes(CanonicalJson.Bytes(o));
        return CanonicalJson.Bytes(o);
    }

    /// Write owner-only (atomic replace, then the platform protection).
    public static void Write(string path, byte[] bytes)
    {
        DurableFile.WriteAtomic(path, bytes);
        if (OperatingSystem.IsWindows()) ProtectWindows(path);
        else File.SetUnixFileMode(path, UnixFileMode.UserRead | UnixFileMode.UserWrite | UnixFileMode.GroupRead | UnixFileMode.OtherRead);
    }

    [SupportedOSPlatform("windows")]
    static SecurityIdentifier[] Trusted() =>
        [new(WellKnownSidType.LocalSystemSid, null), new(WellKnownSidType.BuiltinAdministratorsSid, null)];

    [SupportedOSPlatform("windows")]
    static void ProtectWindows(string path)
    {
        var fi = new FileInfo(path);
        var acl = new FileSecurity();
        var me = WindowsIdentity.GetCurrent().User!;
        acl.SetAccessRuleProtection(isProtected: true, preserveInheritance: false);
        acl.AddAccessRule(new FileSystemAccessRule(me, FileSystemRights.FullControl, AccessControlType.Allow));
        foreach (var s in Trusted()) acl.AddAccessRule(new FileSystemAccessRule(s, FileSystemRights.FullControl, AccessControlType.Allow));
        fi.SetAccessControl(acl);
    }

    static string? OwnershipProblem(string path)
    {
        if (OperatingSystem.IsWindows()) return WindowsOwnershipProblem(path);
        var mode = File.GetUnixFileMode(path);
        return (mode & (UnixFileMode.GroupWrite | UnixFileMode.OtherWrite)) != 0 ? "marker is group- or world-writable" : null;
    }

    [SupportedOSPlatform("windows")]
    static string? WindowsOwnershipProblem(string path)
    {
        var acl = new FileInfo(path).GetAccessControl();
        var me = WindowsIdentity.GetCurrent().User!;
        if (acl.GetOwner(typeof(SecurityIdentifier)) is not SecurityIdentifier owner || (owner != me && !Trusted().Contains(owner))) return "marker owner is not the stager";
        const FileSystemRights write = FileSystemRights.WriteData | FileSystemRights.AppendData | FileSystemRights.Write | FileSystemRights.Modify
                                      | FileSystemRights.FullControl | FileSystemRights.ChangePermissions | FileSystemRights.TakeOwnership | FileSystemRights.Delete;
        foreach (FileSystemAccessRule r in acl.GetAccessRules(true, true, typeof(SecurityIdentifier)))
            if (r.AccessControlType == AccessControlType.Allow && (r.FileSystemRights & write) != 0
                && r.IdentityReference is SecurityIdentifier sid && sid != me && !Trusted().Contains(sid))
                return "marker is writable by another principal";
        return null;
    }

    /// Null when the marker at generations/<gen>/C16_VERIFIED.json is bound evidence matching the files; else why.
    /// full: re-hash every bound file (otherwise generation.json and KNOWLEDGE_RELEASE.json by hash, the rest by size).
    public static string? Validate(SiteLayout site, string generation, bool full, out JsonObject? marker)
    {
        marker = null;
        var gdir = Path.Combine(site.GenerationsDir, generation);
        var path = Path.Combine(gdir, GenerationCatalog.Marker);
        byte[]? b;
        try { b = DurableFile.ReadIfExists(path); } catch (IOException e) { return "marker unreadable: " + e.GetType().Name; }
        if (b is null) return "no marker";
        JsonObject o;
        try { o = CanonicalJson.ParseStrict(b).AsObject(); } catch (Exception) { return "marker is not valid JSON"; }
        if ((string?)o["format"] != Format) return "marker is not bound staging evidence";
        var self = (string?)o["marker_sha256"];
        var copy = (JsonObject)o.DeepClone(); copy.Remove("marker_sha256");
        if (self is null || self != ShaBytes(CanonicalJson.Bytes(copy))) return "marker self-digest differs (corrupted or edited)";
        if ((string?)o["generation"] != generation) return "marker names another generation";
        if (OwnershipProblem(path) is { } own) return own;
        JsonObject gen;
        try { gen = JsonNode.Parse(File.ReadAllText(Path.Combine(gdir, "generation.json")))!.AsObject(); } catch (Exception) { return "generation.json unreadable"; }
        if ((string?)gen["release_id"] != (string?)o["release_id"] || (string?)gen["sums_sha256"] != (string?)o["sums_sha256"])
            return "marker is for another release (stale)";
        var files = o["files"] as JsonObject;
        if (files is null || !files.ContainsKey("generation.json")) return "marker binds no files";
        var bound = BoundPaths(gdir);
        if (!bound.OrderBy(x => x, StringComparer.Ordinal).SequenceEqual(files.Select(kv => kv.Key).OrderBy(x => x, StringComparer.Ordinal)))
            return "the generation's file set differs from the staged one";
        foreach (var (p, v) in files)
        {
            var f = Local(gdir, p);
            if (!File.Exists(f)) return $"bound file missing: {p}";
            if (new FileInfo(f).Length != (long)v!["bytes"]!) return $"bound file size changed: {p}";
            if ((full || p is "generation.json" or "KNOWLEDGE_RELEASE.json") && Sha(f) != (string?)v["sha256"]) return $"bound file changed: {p}";
        }
        marker = o;
        return null;
    }
}
