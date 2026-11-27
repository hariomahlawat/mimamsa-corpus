// C16 B06: durable file primitives (importer _write_atomic discipline, P8). Data is flushed to the device
// (FileStream.Flush(true) = FlushFileBuffers on Windows, fsync on Linux) before the rename that publishes it; on Linux
// the directory is fsync'd as well. NTFS publishes the rename through its own journal (no directory fsync, P8).
namespace Mimamsa.Core.Activation;

public static class DurableFile
{
    public static void WriteAtomic(string path, byte[] data)
    {
        var tmp = path + ".tmp-" + Environment.ProcessId + "-" + Guid.NewGuid().ToString("N")[..8];
        using (var f = new FileStream(tmp, FileMode.CreateNew, FileAccess.Write, FileShare.None, 4096, FileOptions.WriteThrough))
        {
            f.Write(data);
            f.Flush(true);
        }
        try { Replace(tmp, path); }
        catch { try { File.Delete(tmp); } catch (Exception) { } throw; }
        SyncDirectory(Path.GetDirectoryName(Path.GetFullPath(path))!);
    }

    /// Atomic rename over `path`, retried briefly: on Windows a reader opening the target at that instant can make
    /// the replace fail transiently.
    public static void Replace(string tmp, string path)
    {
        for (int attempt = 0; ; attempt++)
        {
            try { File.Move(tmp, path, overwrite: true); return; }
            catch (Exception e) when (attempt < 40 && e is IOException or UnauthorizedAccessException) { Thread.Sleep(5); }
        }
    }

    public static void SyncDirectory(string dir)
    {
        if (OperatingSystem.IsWindows()) return;
        try
        {
            using var h = File.OpenHandle(dir, FileMode.Open, FileAccess.Read, FileShare.ReadWrite, FileOptions.None);
            RandomAccess.FlushToDisk(h);
        }
        catch (Exception e) when (e is IOException or UnauthorizedAccessException) { /* best effort, as the importer */ }
    }

    /// Read a whole file while letting writers append to it and replace it (FileShare.ReadWrite | Delete): a reader
    /// must never make the activation tool's append or atomic rename fail (Windows refuses MoveFileEx onto a file
    /// opened without FILE_SHARE_DELETE), nor the Python ExclusionStore's os.replace.
    public static byte[] ReadShared(string path)
    {
        for (int attempt = 0; ; attempt++)
        {
            try
            {
                using var f = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.ReadWrite | FileShare.Delete, 4096, FileOptions.None);
                using var ms = new MemoryStream();
                f.CopyTo(ms);
                return ms.ToArray();
            }
            catch (Exception e) when (attempt < 40 && e is (IOException and not FileNotFoundException and not DirectoryNotFoundException) or UnauthorizedAccessException)
            {
                // A replace in progress: Windows reports a delete-pending target as a sharing violation or as access
                // denied for a moment. Real permission problems still surface after the retries.
                Thread.Sleep(5);
            }
        }
    }

    public static byte[]? ReadIfExists(string path)
    {
        try { return ReadShared(path); }
        catch (FileNotFoundException) { return null; }
        catch (DirectoryNotFoundException) { return null; }
    }
}
