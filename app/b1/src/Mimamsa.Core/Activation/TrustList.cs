// C16 B06 / I-6: read-only view of the pinned trust list (contract v1 trust_list.schema.json; reference
// mimamsa_contract/trust.py). Used only to verify; the site has no path to add, replace or re-purpose keys.
// In production mode development keys (holder DEVELOPMENT or key_id "dev-...") are never used.
using System.Security.Cryptography;
using System.Text.Json.Nodes;

namespace Mimamsa.Core.Activation;

public sealed record TrustedKey(string KeyId, byte[] Raw, string Holder, IReadOnlySet<string> Purposes, bool Revoked, string? ValidUntil)
{
    public bool IsDev => Holder == "DEVELOPMENT" || KeyId.StartsWith("dev-", StringComparison.Ordinal);
}

public sealed class TrustList
{
    public long Sequence { get; }
    public IReadOnlyList<TrustedKey> Keys { get; }
    TrustList(long seq, IReadOnlyList<TrustedKey> keys) { Sequence = seq; Keys = keys; }

    public static TrustList Parse(byte[] utf8)
    {
        var o = CanonicalJson.ParseStrict(utf8).AsObject();
        if ((string?)o["record_kind"] != "trust_list") throw new FormatException("not a trust list");
        var keys = new List<TrustedKey>();
        foreach (var k in o["keys"]!.AsArray())
        {
            var ko = k!.AsObject();
            var id = (string)ko["key_id"]!;
            var hex = (string)ko["public_key_hex"]!;
            if (hex.Length != 64) throw new FormatException("public key length");
            var raw = Convert.FromHexString(hex);
            var fp = Convert.ToHexString(SHA256.HashData(raw)).ToLowerInvariant();
            var holder = (string)ko["holder"]!;
            if ((id.StartsWith("dev-", StringComparison.Ordinal) ? id[4..] : id) != fp) throw new FormatException("trust list key_id does not match its public key");
            if (id.StartsWith("dev-", StringComparison.Ordinal) != (holder == "DEVELOPMENT")) throw new FormatException("dev- key ids are exactly the DEVELOPMENT holder keys");
            var purposes = ko["purposes"]!.AsArray().Select(p => (string)p!).ToHashSet(StringComparer.Ordinal);
            keys.Add(new TrustedKey(id, raw, holder, purposes, (bool)ko["revoked"]!, (string?)ko["valid_until"]));
        }
        if (keys.Count == 0) throw new FormatException("trust list has no keys");
        return new TrustList((long)o["sequence"]!, keys);
    }

    public IEnumerable<TrustedKey> Usable(string purpose, bool production, DateOnly today)
    {
        var t = today.ToString("yyyy-MM-dd");
        foreach (var k in Keys)
        {
            if (k.Revoked || !k.Purposes.Contains(purpose)) continue;
            if (k.ValidUntil is { } vu && string.CompareOrdinal(vu, t) < 0) continue;
            if (production && k.IsDev) continue;
            yield return k;
        }
    }

    /// The key that verifies `signature` over `data` for `purpose`, or null.
    public TrustedKey? VerifyDetached(byte[] data, byte[] signature, string purpose, bool production, DateOnly today) =>
        Usable(purpose, production, today).FirstOrDefault(k => Ed25519.Verify(k.Raw, data, signature));
}
