// C16 B06 / I-6: Ed25519 signature VERIFICATION (RFC 8032 section 5.1.7), used by the read-only exclusion reader to
// verify the Python ExclusionStore's signed updates against the trust list.
// CP-1 (integration review): security-critical crypto uses a vetted library, not a hand-written one. .NET 10 has no
// Ed25519 in System.Security.Cryptography, so this delegates to BouncyCastle.Cryptography 2.6.2 (MIT, pure managed, no
// native dependency; package and version recorded in app/b1/evidence/c16_cp1/CP1_REPORT.md). B06's earlier managed
// BigInteger implementation is removed. Strictness kept explicit here: 32-byte key, 64-byte signature, S < L
// (malleability) is checked before the library call, which additionally rejects non-canonical point encodings.
// Verification only: the site never holds a signing key. Cross-checked in tests against the RFC 8032 vectors and against
// signatures made by pyca cryptography (the Python ExclusionStore).
using System.Numerics;
using BcEd25519 = Org.BouncyCastle.Math.EC.Rfc8032.Ed25519;

namespace Mimamsa.Core.Activation;

public static class Ed25519
{
    /// The prime order L of the base point (RFC 8032 section 5.1).
    internal static readonly BigInteger GroupOrder = BigInteger.Pow(2, 252) + BigInteger.Parse("27742317777372353535851937790883648493");

    public static bool Verify(ReadOnlySpan<byte> publicKey, ReadOnlySpan<byte> message, ReadOnlySpan<byte> signature)
    {
        if (publicKey.Length != BcEd25519.PublicKeySize || signature.Length != BcEd25519.SignatureSize) return false;
        if (new BigInteger(signature[32..], isUnsigned: true, isBigEndian: false) >= GroupOrder) return false;
        var sig = signature.ToArray(); var pk = publicKey.ToArray(); var m = message.ToArray();
        try { return BcEd25519.Verify(sig, 0, pk, 0, m, 0, m.Length); }
        catch (ArgumentException) { return false; }
    }
}
