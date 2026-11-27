// Event trace for the R2-N01 oracle (PR #54 transport_oracle.py normalized-trace format, before merging).
// Emitted by in-process instrumentation at the exact code points (ledger commit, guard entry, PipeWriter
// handoff, durable witness commit, termination drain). NOTE: these are NOT independent probes in the sense of
// transport.md; they are the application's own instrumentation, cross-checked by the exporter against the
// PostgreSQL ledger rows. Client events (http, receive, cancel, ack, restart) come from the separate test client.
using System.Collections.Concurrent;
using System.Text.Json;

namespace MimamsaPocApi;

public static class DeliveryTrace
{
    static readonly ConcurrentQueue<string> Q = new();
    static string? _path;
    static long _seq;
    public static string Boot { get; } = Guid.NewGuid().ToString("N")[..12];

    public static void Start(string? path)
    {
        if (string.IsNullOrEmpty(path)) return;
        _path = path;
        _ = Task.Run(async () =>
        {
            while (true)
            {
                await Task.Delay(20);
                Flush();
            }
        });
    }

    public static void Flush()
    {
        if (_path is null || Q.IsEmpty) return;
        lock (Q)
        {
            using var w = new StreamWriter(_path, append: true);
            while (Q.TryDequeue(out var line)) w.WriteLine(line);
        }
    }

    public static long UnixNs() => (DateTime.UtcNow.Ticks - DateTime.UnixEpoch.Ticks) * 100;

    public static void Emit(string kind, string source, object fields)
    {
        if (_path is null) return;
        var d = JsonSerializer.SerializeToElement(fields).EnumerateObject().ToDictionary(p => p.Name, p => (object)p.Value);
        d["kind"] = kind; d["source"] = source; d["t_ns"] = UnixNs(); d["boot"] = Boot;
        d["local_seq"] = Interlocked.Increment(ref _seq);
        Q.Enqueue(JsonSerializer.Serialize(d));
    }
}
