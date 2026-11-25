// OS adapter: evidence that a terminated connection holds no more deliverable bytes in the server's kernel.
// Linux: /proc/net/tcp{,6} tx_queue for the exact (local port, remote port) socket must be 0 or the socket gone.
// Other OSes (incl. Windows): NOT IMPLEMENTED -> falls back to "transport terminated + grace", explicitly labelled
// as unproven. A Windows adapter would use GetPerTcpConnectionEStats (TcpConnectionEstatsSendBuff/Data) or an
// ETW TCP provider; that remains open for the selected-host run.
using System.Globalization;
using System.Net;

namespace MimamsaPocApi;

public static class DrainProbe
{
    public static bool KernelEvidenceAvailable => OperatingSystem.IsLinux() && File.Exists("/proc/net/tcp");

    /// Returns the kernel tx_queue bytes for the socket, or null when the socket no longer exists.
    public static long? TxQueue(int localPort, int remotePort)
    {
        long? found = null;
        foreach (var f in new[] { "/proc/net/tcp", "/proc/net/tcp6" })
        {
            if (!File.Exists(f)) continue;
            foreach (var line in File.ReadLines(f).Skip(1))
            {
                var p = line.Split(' ', StringSplitOptions.RemoveEmptyEntries);
                if (p.Length < 5) continue;
                int lp = int.Parse(p[1][(p[1].LastIndexOf(':') + 1)..], NumberStyles.HexNumber);
                int rp = int.Parse(p[2][(p[2].LastIndexOf(':') + 1)..], NumberStyles.HexNumber);
                if (lp != localPort || rp != remotePort) continue;
                long tx = long.Parse(p[4].Split(':')[0], NumberStyles.HexNumber);
                found = (found ?? 0) + tx;
            }
        }
        return found;
    }

    /// Wait until the kernel holds no unacknowledged bytes for this socket. Never gives up by releasing:
    /// returns (true, evidence) on proof, or keeps polling (with backoff) until proof arrives.
    public static async Task<(string proof, string evidence)> AwaitDrainAsync(EndPoint? local, EndPoint? remote, int graceMs)
    {
        await Task.Delay(graceMs);
        if (!KernelEvidenceAvailable || local is not IPEndPoint l || remote is not IPEndPoint r)
            return ("termination", $"transport terminated + {graceMs} ms grace (kernel drain UNPROVEN on {Environment.OSVersion.Platform})");
        int delay = 20; int zeroSeen = 0;
        while (true)
        {
            var tx = TxQueue(l.Port, r.Port);
            if (tx is null) return ("drain", $"linux /proc/net/tcp: socket {l.Port}->{r.Port} gone");
            if (tx == 0 && ++zeroSeen >= 2) return ("drain", $"linux /proc/net/tcp: socket {l.Port}->{r.Port} tx_queue=0 (2 consecutive samples)");
            if (tx != 0) zeroSeen = 0;
            await Task.Delay(delay);
            delay = Math.Min(delay * 2, 2000);
        }
    }
}
