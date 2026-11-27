// C16 B06 / I-4: the local, authenticated, replay-protected control channel between the activation tool (client)
// and the web service participant (server). Interface B06 section 3.
//
// Transport: a named pipe (\\.\pipe\<name> on Windows; .NET maps the same API to a Unix domain socket on Linux).
// Nothing is reachable from the network: on Windows the pipe ACL allows only the configured identities (default: the
// current user) and explicitly denies the NETWORK SID; on Linux the socket is CurrentUserOnly.
// Authentication: every message is HMAC-SHA256'd with a per-install secret (control\channel.key, readable only by the
// two service identities). Replay protection: the server opens each connection with a fresh random session nonce;
// every message names that nonce and a strictly increasing counter, so a captured message is useless on any other
// connection and cannot be repeated on its own. Each message carries the lock epoch; the participant rejects an
// epoch lower than one already seen or different from the lock record's. On Windows the server also checks that the
// connecting process is the lock holder (GetNamedPipeClientProcessId against the lock record's pid).
using System.IO.Pipes;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json.Nodes;

namespace Mimamsa.Core.Activation;

public sealed class ControlChannelOptions
{
    public required string PipeName { get; init; }
    public required byte[] Secret { get; init; }
    public TimeSpan Timeout { get; init; } = TimeSpan.FromSeconds(5);
    /// Windows: SIDs allowed to connect (default: the current user only).
    public IReadOnlyList<string>? AllowedSids { get; init; }
    /// Windows: require the connecting process to be the lock holder recorded in LOCK.json.
    public bool RequirePeerIsLockHolder { get; init; } = true;

    public static byte[] LoadSecret(string path)
    {
        var b = File.ReadAllBytes(path);
        if (b.Length < 32) throw new InvalidOperationException("control channel key must be at least 32 bytes");
        return b;
    }
}

public static class ControlEnvelope
{
    public static string Mac(byte[] secret, JsonObject withoutMac) =>
        Convert.ToHexString(HMACSHA256.HashData(secret, CanonicalJson.Bytes(withoutMac))).ToLowerInvariant();

    public static string Seal(byte[] secret, string type, JsonObject body, long epoch, string session, long counter, string sender)
    {
        var o = new JsonObject { ["type"] = type, ["body"] = body, ["lock_epoch"] = epoch, ["session"] = session, ["counter"] = counter, ["sender"] = sender };
        o["mac"] = Mac(secret, o.DeepClone().AsObject());
        return Encoding.UTF8.GetString(CanonicalJson.Bytes(o));
    }

    /// Verify MAC, sender, session and counter. Returns null and a reason when the message is not authentic.
    public static JsonObject? Open(byte[] secret, string line, string expectSender, string session, long lastCounter, out string reason)
    {
        JsonObject o;
        try { o = CanonicalJson.ParseStrict(Encoding.UTF8.GetBytes(line)).AsObject(); }
        catch (Exception) { reason = "UNPARSEABLE"; return null; }
        var mac = (string?)o["mac"];
        var copy = o.DeepClone().AsObject(); copy.Remove("mac");
        var want = Mac(secret, copy);
        if (mac is null || mac.Length != want.Length || !CryptographicOperations.FixedTimeEquals(Encoding.ASCII.GetBytes(mac), Encoding.ASCII.GetBytes(want)))
        { reason = "BAD_MAC"; return null; }
        if ((string?)o["sender"] != expectSender) { reason = "BAD_SENDER"; return null; }
        if ((string?)o["session"] != session) { reason = "REPLAY_OTHER_SESSION"; return null; }
        if ((long?)o["counter"] is not { } c || c != lastCounter + 1) { reason = "REPLAY_COUNTER"; return null; }
        reason = "OK";
        return o;
    }
}

/// Web side: serves the participant on the pipe.
public sealed class ControlChannelServer : IAsyncDisposable
{
    readonly ControlChannelOptions _o;
    readonly ActivationParticipant _p;
    readonly CancellationTokenSource _cts = new();
    readonly List<Task> _loops = [];
    public int Rejected;
    public string? LastRejectReason { get; private set; }
    public Action<string>? Log { get; init; }

    public ControlChannelServer(ControlChannelOptions o, ActivationParticipant p) { _o = o; _p = p; }

    public void Start(int instances = 2)
    {
        for (int i = 0; i < instances; i++) _loops.Add(Task.Run(() => Loop(_cts.Token)));
    }

    NamedPipeServerStream Create()
    {
        if (OperatingSystem.IsWindows()) return WindowsPipe.Create(_o.PipeName, _o.AllowedSids);
        return new NamedPipeServerStream(_o.PipeName, PipeDirection.InOut, NamedPipeServerStream.MaxAllowedServerInstances, PipeTransmissionMode.Byte,
            PipeOptions.Asynchronous | PipeOptions.CurrentUserOnly);
    }

    async Task Loop(CancellationToken ct)
    {
        while (!ct.IsCancellationRequested)
        {
            NamedPipeServerStream? pipe = null;
            try
            {
                pipe = Create();
                await pipe.WaitForConnectionAsync(ct);
                await Serve(pipe, ct);
            }
            catch (OperationCanceledException) { break; }
            catch (Exception e) when (e is IOException or ObjectDisposedException or InvalidOperationException) { }
            finally { if (pipe is not null) await pipe.DisposeAsync(); }
        }
    }

    readonly List<string> _rejections = [];

    void Reject(string why)
    {
        lock (_rejections)
        {
            Interlocked.Increment(ref Rejected);
            LastRejectReason = why;
            _rejections.Add(why);
            Monitor.PulseAll(_rejections);
        }
        Log?.Invoke("control channel: rejected (" + why + ")");
    }

    /// Wait until the server has recorded a rejection with this reason (the client may give up before the server
    /// gets to it under load). Returns false when none arrives within `timeout`.
    public bool WaitForRejection(string reason, TimeSpan timeout)
    {
        var deadline = DateTime.UtcNow + timeout;
        lock (_rejections)
        {
            while (!_rejections.Contains(reason))
            {
                var left = deadline - DateTime.UtcNow;
                if (left <= TimeSpan.Zero) return false;
                Monitor.Wait(_rejections, left);
            }
            return true;
        }
    }

    async Task Serve(NamedPipeServerStream pipe, CancellationToken ct)
    {
        if (OperatingSystem.IsWindows() && _o.RequirePeerIsLockHolder)
        {
            var pid = WindowsPipe.ClientPid(pipe);
            var rec = WriterLease.ReadRecord(_p.Site.Site);
            if (rec is null || !rec.Held || rec.Pid != pid) { Reject("PEER_NOT_LOCK_HOLDER"); return; }
        }
        var nonce = Convert.ToHexString(RandomNumberGenerator.GetBytes(32)).ToLowerInvariant();
        var w = new StreamWriter(pipe, new UTF8Encoding(false)) { NewLine = "\n", AutoFlush = true };
        var r = new StreamReader(pipe, new UTF8Encoding(false));
        await w.WriteLineAsync(new JsonObject { ["type"] = "HELLO", ["session"] = nonce, ["channel"] = "mimamsa-activation/1" }.ToJsonString());
        long inCounter = 0, outCounter = 0;
        bool switchingHere = false;
        try
        {
            while (!ct.IsCancellationRequested)
            {
                var line = await r.ReadLineAsync(ct);
                if (line is null) break;
                var m = ControlEnvelope.Open(_o.Secret, line, "tool", nonce, inCounter, out var why);
                if (m is null) { Reject(why); break; }               // unauthenticated or replayed: drop the connection
                inCounter++;
                long epoch = (long)m["lock_epoch"]!;
                var body = m["body"]!.AsObject();
                JsonObject reply; string type;
                try
                {
                    switch ((string?)m["type"])
                    {
                        case "ENTER_SWITCHING":
                            var ack = _p.EnterSwitching((string)body["txn_id"]!, epoch);
                            switchingHere = true;
                            type = "ACK_SWITCHING";
                            reply = new JsonObject { ["txn_id"] = ack.TxnId, ["admitted_stopped"] = ack.AdmittedStopped, ["pinned"] = ack.Pinned };
                            break;
                        case "OPEN":
                            var serving = _p.Open((string)body["txn_id"]!, (string)body["knowledge"]!, (string?)body["models"], (long)body["exclusion_seq"]!, epoch);
                            switchingHere = false;
                            type = "ACK_OPEN";
                            reply = new JsonObject { ["txn_id"] = (string)body["txn_id"]!, ["serving"] = serving };
                            break;
                        case "PING":
                            type = "PONG"; reply = new JsonObject(); break;
                        case "QUERY_PINS":
                            type = "PINS";
                            var arr = new JsonArray();
                            foreach (var g in _p.PinnedGenerations().Order(StringComparer.Ordinal)) arr.Add(g);
                            reply = new JsonObject { ["generations"] = arr };
                            break;
                        default:
                            Reject("UNKNOWN_TYPE"); return;
                    }
                }
                catch (ActivationRefused e)
                {
                    Reject(e.Code);
                    type = "REJECT"; reply = new JsonObject { ["reason"] = e.Code };
                }
                await w.WriteLineAsync(ControlEnvelope.Seal(_o.Secret, type, reply, epoch, nonce, ++outCounter, "web"));
            }
        }
        finally
        {
            if (switchingHere) _p.ChannelLost();
        }
    }

    int _disposed;
    public async ValueTask DisposeAsync()
    {
        if (Interlocked.Exchange(ref _disposed, 1) == 1) return;
        _cts.Cancel();
        try { await Task.WhenAll(_loops).WaitAsync(TimeSpan.FromSeconds(5)); } catch (Exception) { }
        _cts.Dispose();
    }
}

/// Tool side: IParticipantLink over the pipe. One persistent authenticated connection; reconnects once on failure.
public sealed class PipeParticipantLink : IParticipantLink, IDisposable
{
    readonly ControlChannelOptions _o;
    NamedPipeClientStream? _pipe;
    StreamReader? _r; StreamWriter? _w;
    string? _session;
    long _out, _in;

    public PipeParticipantLink(ControlChannelOptions o) { _o = o; }

    void Connect()
    {
        Close();
        var opts = PipeOptions.Asynchronous | (OperatingSystem.IsWindows() ? PipeOptions.None : PipeOptions.CurrentUserOnly);
        var p = new NamedPipeClientStream(".", _o.PipeName, PipeDirection.InOut, opts);
        try { p.Connect((int)_o.Timeout.TotalMilliseconds); }
        catch (Exception e) when (e is TimeoutException or IOException or UnauthorizedAccessException) { p.Dispose(); throw new ParticipantUnavailableException("cannot connect: " + e.GetType().Name); }
        _pipe = p;
        _r = new StreamReader(p, new UTF8Encoding(false));
        _w = new StreamWriter(p, new UTF8Encoding(false)) { NewLine = "\n", AutoFlush = true };
        var hello = ReadLine() ?? throw new ParticipantUnavailableException("no HELLO");
        var h = JsonNode.Parse(hello)!.AsObject();
        if ((string?)h["type"] != "HELLO" || (string?)h["session"] is not { Length: 64 } s) throw new ParticipantUnavailableException("bad HELLO");
        _session = s; _out = 0; _in = 0;
    }

    string? ReadLine()
    {
        using var cts = new CancellationTokenSource(_o.Timeout);
        try { return _r!.ReadLineAsync(cts.Token).AsTask().GetAwaiter().GetResult(); }
        catch (OperationCanceledException) { throw new ParticipantUnavailableException("timeout"); }
        catch (IOException e) { throw new ParticipantUnavailableException("pipe: " + e.Message); }
    }

    JsonObject Call(string type, JsonObject body, long epoch, string expect)
    {
        for (int attempt = 0; ; attempt++)
        {
            try
            {
                if (_pipe is null || !_pipe.IsConnected) Connect();
                _w!.WriteLine(ControlEnvelope.Seal(_o.Secret, type, body.DeepClone().AsObject(), epoch, _session!, ++_out, "tool"));
                var line = ReadLine() ?? throw new ParticipantUnavailableException("participant closed the channel");
                var m = ControlEnvelope.Open(_o.Secret, line, "web", _session!, _in, out var why) ?? throw new ParticipantUnavailableException("reply not authentic: " + why);
                _in++;
                if ((string?)m["type"] == "REJECT") throw new ParticipantUnavailableException("participant rejected: " + (string?)m["body"]!["reason"]);
                if ((string?)m["type"] != expect) throw new ParticipantUnavailableException("unexpected reply " + (string?)m["type"]);
                return m["body"]!.AsObject();
            }
            catch (Exception e) when (attempt == 0 && e is IOException or ParticipantUnavailableException && e.Message.StartsWith("pipe", StringComparison.Ordinal))
            {
                Close();
            }
            catch (IOException e) { Close(); throw new ParticipantUnavailableException("pipe: " + e.Message); }
        }
    }

    public SwitchAck EnterSwitching(string txnId, long lockEpoch)
    {
        var b = Call("ENTER_SWITCHING", new JsonObject { ["txn_id"] = txnId }, lockEpoch, "ACK_SWITCHING");
        return new SwitchAck((string)b["txn_id"]!, (bool)b["admitted_stopped"]!, (int)(long)b["pinned"]!);
    }

    public void Open(string txnId, string knowledge, string? models, long exclusionSeq, long lockEpoch) =>
        Call("OPEN", new JsonObject { ["txn_id"] = txnId, ["knowledge"] = knowledge, ["models"] = models, ["exclusion_seq"] = exclusionSeq }, lockEpoch, "ACK_OPEN");

    public IReadOnlySet<string>? PinnedGenerations(long lockEpoch)
    {
        try { return Call("QUERY_PINS", new JsonObject(), lockEpoch, "PINS")["generations"]!.AsArray().Select(x => (string)x!).ToHashSet(StringComparer.Ordinal); }
        catch (ParticipantUnavailableException) { return null; }
    }

    public void Ping(long lockEpoch) => Call("PING", new JsonObject(), lockEpoch, "PONG");

    /// Test support: send raw bytes (replay and forgery tests) and read one raw line back (null when dropped).
    public string? SendRaw(string line)
    {
        if (_pipe is null || !_pipe.IsConnected) Connect();
        try { _w!.WriteLine(line); return ReadLine(); }
        catch (ParticipantUnavailableException) { return null; }
        catch (IOException) { return null; }
    }
    public string? Session => _session;
    public long NextCounter => _out + 1;
    public void Connected() { if (_pipe is null || !_pipe.IsConnected) Connect(); }
    public void AdvanceCounter() => _out++;

    void Close()
    {
        try { _r?.Dispose(); } catch (Exception) { }
        try { _w?.Dispose(); } catch (Exception) { }
        try { _pipe?.Dispose(); } catch (Exception) { }
        _pipe = null; _r = null; _w = null;
    }

    public void Dispose() => Close();
}

static class WindowsPipe
{
    [DllImport("kernel32.dll", SetLastError = true)]
    static extern bool GetNamedPipeClientProcessId(Microsoft.Win32.SafeHandles.SafePipeHandle pipe, out uint clientProcessId);

    public static int ClientPid(NamedPipeServerStream s) =>
        GetNamedPipeClientProcessId(s.SafePipeHandle, out var pid) ? (int)pid : -1;

    [System.Runtime.Versioning.SupportedOSPlatform("windows")]
    public static NamedPipeServerStream Create(string name, IReadOnlyList<string>? allowedSids)
    {
        var sec = new PipeSecurity();
        var me = System.Security.Principal.WindowsIdentity.GetCurrent().User!;
        sec.SetOwner(me);
        sec.AddAccessRule(new PipeAccessRule(me, PipeAccessRights.FullControl, System.Security.AccessControl.AccessControlType.Allow));
        foreach (var sid in allowedSids ?? [])
            sec.AddAccessRule(new PipeAccessRule(new System.Security.Principal.SecurityIdentifier(sid), PipeAccessRights.ReadWrite, System.Security.AccessControl.AccessControlType.Allow));
        sec.AddAccessRule(new PipeAccessRule(new System.Security.Principal.SecurityIdentifier(System.Security.Principal.WellKnownSidType.NetworkSid, null),
            PipeAccessRights.FullControl, System.Security.AccessControl.AccessControlType.Deny));
        return NamedPipeServerStreamAcl.Create(name, PipeDirection.InOut, NamedPipeServerStream.MaxAllowedServerInstances, PipeTransmissionMode.Byte,
            PipeOptions.Asynchronous, 0, 0, sec);
    }
}
