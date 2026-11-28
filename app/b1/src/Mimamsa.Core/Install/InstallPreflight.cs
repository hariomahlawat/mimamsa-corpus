// C16 Tranche B Stage 3 S3-C (B07): the installer's MEASURED disk preflight (FG-DISK-PREFLIGHT mechanism, D5, WD-6).
// Required bytes per volume = the bytes actually measured in the payloads that will land on that volume (application
// files, release bundles to import, a backup to restore), times (1 + the configured headroom fraction), plus the
// configured minimum free space. Compared with the volume's measured free space, read at preflight time while every
// retained release stays on disk. No fixed allocation; a failure refuses the installation and the record (with the
// measured values) is kept under logs/preflight. The activation-time preflight is ActivationEngine.Preflight (B06),
// which the installed layout runs with the configured headroom.
using System.Text.Json.Nodes;
using Mimamsa.Core.Activation;

namespace Mimamsa.Core.Install;

public sealed record PreflightPayload(string Label, string TargetRoot, string? SourceDir, long Bytes = 0);

public static class InstallPreflight
{
    /// Bytes of every regular file under a directory (no link is followed; a reparse point is refused by the caller's
    /// tree check, and is not counted here).
    public static long MeasureBytes(string dir)
    {
        if (File.Exists(dir)) return new FileInfo(dir).Length;
        if (!Directory.Exists(dir)) return 0;
        long n = 0;
        var stack = new Stack<DirectoryInfo>(); stack.Push(new DirectoryInfo(dir));
        while (stack.Count > 0)
            foreach (var e in stack.Pop().EnumerateFileSystemInfos())
            {
                if (PathSafety.IsReparse(e)) continue;
                if (e is DirectoryInfo d) stack.Push(d); else n += ((FileInfo)e).Length;
            }
        return n;
    }

    /// The mount point (Linux/macOS) or drive root (Windows) a path lives on, for grouping.
    public static string VolumeOf(string path)
    {
        var full = Path.GetFullPath(path);
        if (OperatingSystem.IsWindows()) return Path.GetPathRoot(full)!.ToUpperInvariant();
        string best = "/";
        foreach (var d in DriveInfo.GetDrives())
        {
            string m;
            try { m = d.RootDirectory.FullName; } catch (Exception) { continue; }
            var mm = m.EndsWith('/') ? m : m + "/";
            if ((full + "/").StartsWith(mm, StringComparison.Ordinal) && m.Length > best.Length) best = m;
        }
        return best;
    }

    /// Free bytes available to the caller on the volume of `path` (the nearest existing ancestor is measured).
    public sealed class VolumeProbe : IDiskProbe
    {
        public long FreeBytes(string path)
        {
            var p = Path.GetFullPath(path);
            while (!Directory.Exists(p) && Path.GetDirectoryName(p) is { } parent) p = parent;
            if (OperatingSystem.IsWindows()) return new DriveInfo(Path.GetPathRoot(p)!).AvailableFreeSpace;
            return new DriveInfo(VolumeOf(p)).AvailableFreeSpace;
        }
    }

    public static JsonObject Run(InstallConfig cfg, IEnumerable<PreflightPayload> payloads, IDiskProbe? probe = null)
    {
        probe ??= new VolumeProbe();
        var byVol = new SortedDictionary<string, (long bytes, List<string> labels, string sample)>(StringComparer.Ordinal);
        foreach (var p in payloads)
        {
            long b = p.SourceDir is null ? p.Bytes : MeasureBytes(p.SourceDir);
            var v = VolumeOf(p.TargetRoot);
            (long bytes, List<string> labels, string sample) cur = byVol.TryGetValue(v, out var x) ? x : (0L, new List<string>(), p.TargetRoot);
            cur.bytes += b; cur.labels.Add($"{p.Label}={b}");
            byVol[v] = cur;
        }
        // every configured root's volume is checked, even with nothing to land there (the minimum free space applies)
        foreach (var k in InstallConfig.RootNames)
        {
            var v = VolumeOf(cfg.Root(k));
            if (!byVol.ContainsKey(v)) byVol[v] = (0L, new List<string>(), cfg.Root(k));
        }
        var vols = new JsonArray();
        bool pass = true;
        foreach (var (v, (bytes, labels, sample)) in byVol)
        {
            long need = (long)Math.Ceiling(bytes * (1 + cfg.HeadroomFraction)) + cfg.MinFreeBytes;
            long free = probe.FreeBytes(sample);
            bool ok = free >= need;
            pass &= ok;
            vols.Add(new JsonObject
            {
                ["volume"] = v, ["measured_payload_bytes"] = bytes, ["payloads"] = new JsonArray(labels.Select(l => (JsonNode)l).ToArray()),
                ["required_bytes"] = need, ["free_bytes"] = free, ["result"] = ok ? "PASS" : "FAIL",
            });
        }
        return new JsonObject
        {
            ["record_kind"] = "install_preflight", ["result"] = pass ? "PASS" : "FAIL", ["headroom_fraction"] = cfg.HeadroomFraction,
            ["min_free_bytes"] = cfg.MinFreeBytes, ["measured_at"] = DateTimeOffset.UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ"),
            ["volumes"] = vols, ["fixed_allocation"] = false,
        };
    }

    /// Keep the record (pass or fail) under logs/preflight when the logs root can be created.
    public static string? Record(InstallConfig cfg, JsonObject rec)
    {
        try
        {
            var d = Path.Combine(cfg.Root("logs"), "preflight");
            Directory.CreateDirectory(d);
            var p = Path.Combine(d, $"PREFLIGHT-{DateTimeOffset.UtcNow:yyyyMMddTHHmmssfffZ}-{(string?)rec["result"]}.json");
            DurableFile.WriteAtomic(p, System.Text.Encoding.UTF8.GetBytes(rec.ToJsonString(new System.Text.Json.JsonSerializerOptions { WriteIndented = true })));
            return p;
        }
        catch (Exception e) when (e is IOException or UnauthorizedAccessException) { return null; }
    }
}
