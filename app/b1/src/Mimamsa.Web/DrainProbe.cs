// OS adapter (from app/poc/p1_hosting/aspnet/DrainProbe.cs; B1: full 4-tuple match, review N2): evidence that a terminated connection holds no more deliverable bytes in the server's kernel.
// Linux: /proc/net/tcp{,6} tx_queue for the exact (local port, remote port) socket must be 0 or the socket gone.
// Windows (and any other OS): TCP state of the exact socket from the OS TCP table
// (IPGlobalProperties.GetActiveTcpConnections -> GetTcpTable2 on Windows). The server is the active closer after
// the response; it sends FIN only after all response bytes. FIN_WAIT_2 / TIME_WAIT / CLOSED / absent therefore
// mean the peer has cumulatively ACKed every byte including FIN, i.e. nothing deliverable remains in the server's
// kernel. ESTABLISHED / FIN_WAIT_1 / CLOSING / LAST_ACK keep the charge. This is weaker than a byte counter
// (no partial occupancy figure) and is labelled as such; GetPerTcpConnectionEStats would give byte counts.
using System.Globalization;
using System.Net;

namespace Mimamsa.Web;

public static class DrainProbe
{
    // MIMAMSA_DRAIN_PROBE=tcpstate forces the portable TCP-state probe (used to validate the Windows path on Linux)
    public static bool KernelEvidenceAvailable => OperatingSystem.IsLinux() && File.Exists("/proc/net/tcp")
        && Environment.GetEnvironmentVariable("MIMAMSA_DRAIN_PROBE") != "tcpstate";

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

    /// B1 (review N2): match the full 4-tuple (local address and port, remote address and port), not ports only.
    /// IPv4-mapped IPv6 addresses are compared in their IPv4 form.
    public static System.Net.NetworkInformation.TcpState? TcpState(IPEndPoint local, IPEndPoint remote)
    {
        static IPAddress N(IPAddress a) => a.IsIPv4MappedToIPv6 ? a.MapToIPv4() : a;
        foreach (var c in System.Net.NetworkInformation.IPGlobalProperties.GetIPGlobalProperties().GetActiveTcpConnections())
            if (c.LocalEndPoint.Port == local.Port && c.RemoteEndPoint.Port == remote.Port
                && N(c.LocalEndPoint.Address).Equals(N(local.Address)) && N(c.RemoteEndPoint.Address).Equals(N(remote.Address)))
                return c.State;
        return null;
    }

    /// One-shot positive evidence that the socket (localPort, remotePort) can deliver no more bytes.
    public static (bool safe, string evidence) SocketSafe(int localPort, int remotePort)
    {
        if (KernelEvidenceAvailable)
        {
            var tx = TxQueue(localPort, remotePort);
            if (tx is null) return (true, $"linux /proc/net/tcp: socket {localPort}->{remotePort} gone");
            return tx == 0 ? (true, $"linux /proc/net/tcp: socket {localPort}->{remotePort} tx_queue=0")
                           : (false, $"linux /proc/net/tcp: socket {localPort}->{remotePort} still holds {tx} bytes");
        }
        var table = System.Net.NetworkInformation.IPGlobalProperties.GetIPGlobalProperties().GetActiveTcpConnections()
            .Select(c => (c.LocalEndPoint.Port, c.RemoteEndPoint.Port, c.State));
        return SocketSafeFrom(table, localPort, remotePort);
    }

    /// Reconciliation of a previous instance (review of PR #57): only ports were recorded with the reservation, so the
    /// check is conservative over EVERY socket with that port pair on any address family or interface (IPv4, IPv6,
    /// non-loopback). The charge is released only if no such socket exists, or every one is in a state that proves
    /// all bytes were acknowledged (FIN_WAIT_2, TIME_WAIT, CLOSED). Any other state keeps the charge.
    public static (bool safe, string evidence) SocketSafeFrom(IEnumerable<(int local, int remote, System.Net.NetworkInformation.TcpState state)> table,
                                                              int localPort, int remotePort)
    {
        var matches = table.Where(t => t.local == localPort && t.remote == remotePort).Select(t => t.state).ToList();
        if (matches.Count == 0) return (true, $"OS TCP table: no socket {localPort}->{remotePort} on any address");
        var unsafeStates = matches.Where(st => st is not (System.Net.NetworkInformation.TcpState.FinWait2 or System.Net.NetworkInformation.TcpState.TimeWait
                                                          or System.Net.NetworkInformation.TcpState.Closed)).ToList();
        return unsafeStates.Count == 0
            ? (true, $"OS TCP table: every socket {localPort}->{remotePort} in {string.Join("/", matches.Distinct())}")
            : (false, $"OS TCP table: socket {localPort}->{remotePort} in {string.Join("/", unsafeStates.Distinct())} (may still deliver; charge kept)");
    }

    /// Wait until the kernel holds no unacknowledged bytes for this socket. Never gives up by releasing:
    /// returns (true, evidence) on proof, or keeps polling (with backoff) until proof arrives.
    public static async Task<(string proof, string evidence)> AwaitDrainAsync(EndPoint? local, EndPoint? remote, int graceMs)
    {
        await Task.Delay(graceMs);
        if (local is not IPEndPoint l || remote is not IPEndPoint r)
            return ("termination", $"transport terminated + {graceMs} ms grace (no endpoint information; kernel drain UNPROVEN)");
        if (!KernelEvidenceAvailable)
        {
            int d = 20;
            while (true)
            {
                var st = TcpState(l, r);
                if (st is null) return ("drain", $"OS TCP table: socket {l.Port}->{r.Port} gone (all data ACKed or connection reset)");
                if (st is System.Net.NetworkInformation.TcpState.FinWait2 or System.Net.NetworkInformation.TcpState.TimeWait
                       or System.Net.NetworkInformation.TcpState.Closed)
                    return ("drain", $"OS TCP table: socket {l.Port}->{r.Port} in {st} (peer ACKed all bytes incl. FIN)");
                await Task.Delay(d); d = Math.Min(d * 2, 2000);
            }
        }
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
