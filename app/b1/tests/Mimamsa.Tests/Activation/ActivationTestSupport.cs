// C16 B06 test support: development Ed25519 signing (tests only; the site never signs), a writer of the Python
// ExclusionStore on-disk format (pairs/<seq>.json|.sig, ACCEPTED.json, EXCLUSION_LATCH) signed with a development
// register key, development trust lists, and disposable site directories.
using System.Numerics;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json.Nodes;
using Mimamsa.Core.Activation;

namespace Mimamsa.Tests.Activation;

public static class DevEd25519
{
    /// RFC 8032 section 5.1.6 signing (development and test keys only).
    public static (byte[] pub, Func<byte[], byte[]> sign) FromSeed(byte[] seed)
    {
        var h = SHA512.HashData(seed);
        var a = new BigInteger(h.AsSpan(0, 32), isUnsigned: true, isBigEndian: false);
        a &= (BigInteger.One << 254) - 8;
        a |= BigInteger.One << 254;
        var prefix = h.AsSpan(32, 32).ToArray();
        var pub = Ed25519.Encode(Ed25519.Mul(a, Ed25519.Base));
        byte[] Sign(byte[] msg)
        {
            var r = Ed25519.ScalarModL(SHA512.HashData([.. prefix, .. msg]));
            var rs = Ed25519.Encode(Ed25519.Mul(r, Ed25519.Base));
            var k = Ed25519.ScalarModL(SHA512.HashData([.. rs, .. pub, .. msg]));
            var s = (r + k * a) % Ed25519.GroupOrder;
            var sb = new byte[32];
            s.TryWriteBytes(sb, out _, isUnsigned: true, isBigEndian: false);
            return [.. rs, .. sb];
        }
        return (pub, Sign);
    }
}

public sealed class DevRegisterKey
{
    public byte[] Public { get; }
    public Func<byte[], byte[]> Sign { get; }
    public DevRegisterKey(byte[]? seed = null)
    {
        (Public, Sign) = DevEd25519.FromSeed(seed ?? RandomNumberGenerator.GetBytes(32));
    }
    public string KeyId => "dev-" + Convert.ToHexString(SHA256.HashData(Public)).ToLowerInvariant();

    public static byte[] TrustList(params (DevRegisterKey key, string[] purposes, bool revoked)[] keys)
    {
        var arr = new JsonArray();
        foreach (var (k, p, rev) in keys)
        {
            var pa = new JsonArray(); foreach (var x in p) pa.Add(x);
            arr.Add(new JsonObject { ["key_id"] = k.KeyId, ["public_key_hex"] = Convert.ToHexString(k.Public).ToLowerInvariant(), ["holder"] = "DEVELOPMENT", ["purposes"] = pa, ["revoked"] = rev });
        }
        return CanonicalJson.Bytes(new JsonObject { ["contract_version"] = "1.0.0", ["record_kind"] = "trust_list", ["sequence"] = 1, ["issued_at"] = "2026-11-27T00:00:00Z", ["keys"] = arr });
    }
}

/// Writes the Python ExclusionStore format (mimamsa_contract/exclusions.py) so the .NET reader can be exercised on
/// real signed stores. Withdrawn items are doc ids.
public sealed class DevExclusionStore
{
    readonly string _dir;
    readonly DevRegisterKey _key;
    public DevExclusionStore(string dir, DevRegisterKey key) { _dir = dir; _key = key; }

    public static string RegisterJson() =>
        "{\"items\":[{\"restriction_id\":\"RX-B06-FIXTURE\",\"source_sha256\":\"" + new string('0', 63) + "1\"}]}";

    public long Sequence => File.Exists(Path.Combine(_dir, "ACCEPTED.json"))
        ? (long)CanonicalJson.ParseStrict(File.ReadAllBytes(Path.Combine(_dir, "ACCEPTED.json")))["sequence"]! : 0;

    public long Append(IEnumerable<string> withdrawnDocIds, IEnumerable<string>? readmitDocIds = null, Func<byte[], byte[]>? signOverride = null)
    {
        var acc = File.Exists(Path.Combine(_dir, "ACCEPTED.json")) ? CanonicalJson.ParseStrict(File.ReadAllBytes(Path.Combine(_dir, "ACCEPTED.json"))).AsObject() : null;
        long seq = ((long?)acc?["sequence"] ?? 0) + 1;
        var reg = RegisterJson();
        var w = new JsonArray();
        foreach (var d in withdrawnDocIds) w.Add(new JsonObject { ["doc_id"] = d, ["reason"] = "B06 fixture withdrawal" });
        var upd = new JsonObject
        {
            ["contract_version"] = "1.0.0", ["record_kind"] = "exclusion_update", ["sequence"] = seq, ["issued_at"] = "2026-11-27T00:00:00Z",
            ["register_sha256"] = CanonicalJson.Sha256Hex(Encoding.UTF8.GetBytes(reg)), ["register_json"] = reg, ["withdrawals"] = w,
        };
        if (readmitDocIds is not null)
        {
            var r = new JsonArray(); foreach (var d in readmitDocIds) r.Add(new JsonObject { ["doc_id"] = d, ["reason"] = "B06 fixture readmission" });
            upd["readmissions"] = r;
        }
        var data = CanonicalJson.Bytes(upd);
        var sig = (signOverride ?? _key.Sign)(data);
        var pairs = Path.Combine(_dir, "pairs");
        Directory.CreateDirectory(pairs);
        File.WriteAllBytes(Path.Combine(pairs, seq.ToString("D8") + ".json"), data);
        File.WriteAllBytes(Path.Combine(pairs, seq.ToString("D8") + ".sig"), sig);
        var digest = CanonicalJson.Sha256Hex(data);
        var hist = acc?["history"]?.DeepClone().AsArray() ?? new JsonArray();
        hist.Add(new JsonArray(seq, digest, $"seq-{seq}-{digest[..16]}"));
        var rec = new JsonObject
        {
            ["operation_id"] = $"seq-{seq}-{digest[..16]}", ["sequence"] = seq, ["digest"] = digest,
            ["signature_sha256"] = CanonicalJson.Sha256Hex(sig), ["epoch"] = ((long?)acc?["epoch"] ?? 0) + 1,
            ["previous_sequence"] = (long?)acc?["sequence"] ?? 0, ["previous_digest"] = (string?)acc?["digest"], ["history"] = hist,
        };
        var latch = Path.Combine(Path.GetDirectoryName(Path.GetFullPath(_dir))!, "EXCLUSION_LATCH");
        if (!File.Exists(latch)) File.WriteAllBytes(latch, CanonicalJson.Bytes(new JsonObject { ["latched"] = true, ["first_sequence"] = seq }));
        DurableFile.WriteAtomic(Path.Combine(_dir, "ACCEPTED.json"), CanonicalJson.Bytes(rec));
        return seq;
    }

    /// Rewrite ACCEPTED to the previous accepted record (a validly signed but OLDER state: a regression).
    public void RegressOne()
    {
        var acc = CanonicalJson.ParseStrict(File.ReadAllBytes(Path.Combine(_dir, "ACCEPTED.json"))).AsObject();
        var hist = acc["history"]!.AsArray();
        if (hist.Count < 2) throw new InvalidOperationException("nothing to regress to");
        var prev = hist[^2]!.AsArray();
        var nh = new JsonArray(); for (int i = 0; i < hist.Count - 1; i++) nh.Add(hist[i]!.DeepClone());
        long ps = (long)prev[0]!;
        var data = File.ReadAllBytes(Path.Combine(_dir, "pairs", ps.ToString("D8") + ".json"));
        var sig = File.ReadAllBytes(Path.Combine(_dir, "pairs", ps.ToString("D8") + ".sig"));
        // The newer pair stays on disk outside the (shortened) accepted range? It is ABOVE it, so the reader's
        // history check does not see it; only the sequence comparison catches the regression.
        DurableFile.WriteAtomic(Path.Combine(_dir, "ACCEPTED.json"), CanonicalJson.Bytes(new JsonObject
        {
            ["operation_id"] = (string)prev[2]!, ["sequence"] = ps, ["digest"] = (string)prev[1]!, ["signature_sha256"] = CanonicalJson.Sha256Hex(sig),
            ["epoch"] = (long)acc["epoch"]! - 1, ["previous_sequence"] = ps - 1, ["previous_digest"] = null, ["history"] = nh,
        }));
        _ = data;
    }

    /// Flip one bit of the accepted pair's signature.
    public void InvalidateSignature()
    {
        var acc = CanonicalJson.ParseStrict(File.ReadAllBytes(Path.Combine(_dir, "ACCEPTED.json")));
        var p = Path.Combine(_dir, "pairs", ((long)acc["sequence"]!).ToString("D8") + ".sig");
        var b = File.ReadAllBytes(p); b[5] ^= 0x01; File.WriteAllBytes(p, b);
    }
}

public static class TestDirs
{
    /// Base for disposable activation sites: MIMAMSA_C16B06_DIR (local: E:\Mimamsa-Data\c16b06) or the temp folder.
    public static string Base
    {
        get
        {
            var b = Environment.GetEnvironmentVariable("MIMAMSA_C16B06_DIR") is { Length: > 0 } e ? e : Path.Combine(Path.GetTempPath(), "mimamsa-c16b06");
            Directory.CreateDirectory(b);
            return b;
        }
    }

    public static string NewSite(string label)
    {
        var d = Path.Combine(Base, label + "-" + Guid.NewGuid().ToString("N")[..10]);
        Directory.CreateDirectory(d);
        return d;
    }

    public static void Delete(string dir)
    {
        for (int i = 0; i < 20; i++)
        {
            try { if (Directory.Exists(dir)) Directory.Delete(dir, true); return; }
            catch (Exception e) when (e is IOException or UnauthorizedAccessException) { Thread.Sleep(100); }
        }
    }

    public static string RepoFile(params string[] rel)
    {
        var d = new DirectoryInfo(AppContext.BaseDirectory);
        while (d is not null && !Directory.Exists(Path.Combine(d.FullName, "app", "contract"))) d = d.Parent;
        if (d is null) throw new DirectoryNotFoundException("repository root not found above " + AppContext.BaseDirectory);
        return Path.Combine([d.FullName, .. rel]);
    }
}

/// A fixture activation site: staged generations and models, a signed exclusion store at a baseline sequence, a
/// development trust list, the file database and an initialised OPEN marker.
public sealed class FixtureSite : IDisposable
{
    public string Root { get; }
    public SiteLayout Layout { get; }
    public DevRegisterKey Key { get; } = new();
    public DevExclusionStore Store { get; }
    public FileActivationDatabase Db { get; }

    public FixtureSite(string label, IEnumerable<string> installed, string active, string models,
        IDictionary<string, (bool verified, string[] vectorsFor)> stagedModels, IDictionary<string, long>? sizes = null)
    {
        Root = TestDirs.NewSite(label);
        Layout = new SiteLayout(Root);
        var cat = new GenerationCatalog(Layout);
        foreach (var g in installed) cat.StageGeneration(g, sizes is not null && sizes.TryGetValue(g, out var sz) ? sz : 0);
        foreach (var (m, v) in stagedModels) cat.StageModel(m, v.verified, v.vectorsFor);
        Directory.CreateDirectory(Path.GetDirectoryName(Layout.TrustListPath)!);
        File.WriteAllBytes(Layout.TrustListPath, DevRegisterKey.TrustList((Key, ["register"], false)));
        Directory.CreateDirectory(Layout.ExclusionsDir);
        Store = new DevExclusionStore(Layout.ExclusionsDir, Key);
        var baseline = Store.Append([]);                          // baseline signed state (scenario sequence 0)
        Layout.Initialise(active, models, baseline);
        Db = new FileActivationDatabase(Layout.FileDbPath);
        Db.Initialise(active);
        Directory.CreateDirectory(Path.GetDirectoryName(Layout.ChannelKeyPath)!);
        File.WriteAllBytes(Layout.ChannelKeyPath, RandomNumberGenerator.GetBytes(32));
    }

    public static FixtureSite Simple(string label, params string[] gens) =>
        new(label, gens, gens[0], "M1", new Dictionary<string, (bool, string[])> { ["M1"] = (true, gens), ["M2"] = (true, gens) });

    public ExclusionReader NewReader() => ActivationCli.Reader(Layout, production: false);

    public void Dispose() => TestDirs.Delete(Root);
}
