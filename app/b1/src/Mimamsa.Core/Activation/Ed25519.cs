// C16 B06 / I-6: Ed25519 signature VERIFICATION (RFC 8032 section 5.1.7), used by the read-only exclusion reader to
// verify the Python ExclusionStore's signed updates against the trust list. Pure managed code over BigInteger so the
// site needs no new native or third-party dependency (.NET 10 has no Ed25519 in System.Security.Cryptography).
// Strict: 32-byte key, 64-byte signature, S < L, canonical point encodings (y < p, no "negative zero"), cofactorless
// equation [S]B == R + [k]A (the same equation OpenSSL / pyca cryptography check). Verification only: the site never
// holds a signing key, and nothing here is secret, so the variable-time arithmetic leaks nothing.
// Cross-checked in tests against the RFC 8032 vectors and against signatures made by pyca cryptography.
using System.Numerics;
using System.Security.Cryptography;

namespace Mimamsa.Core.Activation;

public static class Ed25519
{
    static readonly BigInteger P = BigInteger.Pow(2, 255) - 19;
    static readonly BigInteger L = BigInteger.Pow(2, 252) + BigInteger.Parse("27742317777372353535851937790883648493");
    static readonly BigInteger D = Mod(-121665 * Inv(121666));
    static readonly BigInteger SqrtM1 = BigInteger.ModPow(2, (P - 1) / 4, P);
    static readonly (BigInteger X, BigInteger Y, BigInteger Z, BigInteger T) G = BasePoint();

    static BigInteger Mod(BigInteger a) { var r = a % P; return r.Sign < 0 ? r + P : r; }
    static BigInteger Inv(BigInteger a) => BigInteger.ModPow(Mod(a), P - 2, P);

    static (BigInteger, BigInteger, BigInteger, BigInteger) BasePoint()
    {
        var y = Mod(4 * Inv(5));
        var x = RecoverX(y, 0) ?? throw new InvalidOperationException("base point");
        return (x, y, 1, Mod(x * y));
    }

    static BigInteger? RecoverX(BigInteger y, int sign)
    {
        if (y >= P) return null;
        var x2 = Mod((y * y - 1) * Inv(D * y * y + 1));
        if (x2.IsZero) return sign == 1 ? null : BigInteger.Zero;
        var x = BigInteger.ModPow(x2, (P + 3) / 8, P);
        if (!Mod(x * x - x2).IsZero) x = Mod(x * SqrtM1);
        if (!Mod(x * x - x2).IsZero) return null;
        if ((int)(x & 1) != sign) x = P - x;
        return x;
    }

    internal static (BigInteger X, BigInteger Y, BigInteger Z, BigInteger T) Add(
        (BigInteger X, BigInteger Y, BigInteger Z, BigInteger T) p, (BigInteger X, BigInteger Y, BigInteger Z, BigInteger T) q)
    {
        var a = Mod((p.Y - p.X) * (q.Y - q.X));
        var b = Mod((p.Y + p.X) * (q.Y + q.X));
        var c = Mod(2 * p.T * q.T * D);
        var d = Mod(2 * p.Z * q.Z);
        BigInteger e = b - a, f = d - c, g = d + c, h = b + a;
        return (Mod(e * f), Mod(g * h), Mod(f * g), Mod(e * h));
    }

    internal static (BigInteger X, BigInteger Y, BigInteger Z, BigInteger T) Mul(BigInteger s, (BigInteger X, BigInteger Y, BigInteger Z, BigInteger T) p)
    {
        (BigInteger X, BigInteger Y, BigInteger Z, BigInteger T) q = (0, 1, 1, 0);
        while (s.Sign > 0)
        {
            if (!s.IsEven) q = Add(q, p);
            p = Add(p, p);
            s >>= 1;
        }
        return q;
    }

    static bool Equal((BigInteger X, BigInteger Y, BigInteger Z, BigInteger T) a, (BigInteger X, BigInteger Y, BigInteger Z, BigInteger T) b) =>
        Mod(a.X * b.Z - b.X * a.Z).IsZero && Mod(a.Y * b.Z - b.Y * a.Z).IsZero;

    static BigInteger LittleEndian(ReadOnlySpan<byte> b) => new(b, isUnsigned: true, isBigEndian: false);

    static (BigInteger, BigInteger, BigInteger, BigInteger)? Decode(ReadOnlySpan<byte> s)
    {
        if (s.Length != 32) return null;
        var y = LittleEndian(s) & ((BigInteger.One << 255) - 1);
        int sign = s[31] >> 7;
        var x = RecoverX(y, sign);
        if (x is null) return null;
        return (x.Value, y, 1, Mod(x.Value * y));
    }

    internal static byte[] Encode((BigInteger X, BigInteger Y, BigInteger Z, BigInteger T) p)
    {
        var zi = Inv(p.Z);
        var x = Mod(p.X * zi);
        var y = Mod(p.Y * zi);
        var outb = new byte[32];
        y.TryWriteBytes(outb, out _, isUnsigned: true, isBigEndian: false);
        outb[31] |= (byte)((int)(x & 1) << 7);
        return outb;
    }

    internal static BigInteger ScalarModL(ReadOnlySpan<byte> b) => LittleEndian(b) % L;
    internal static BigInteger GroupOrder => L;
    internal static (BigInteger X, BigInteger Y, BigInteger Z, BigInteger T) Base => G;

    public static bool Verify(ReadOnlySpan<byte> publicKey, ReadOnlySpan<byte> message, ReadOnlySpan<byte> signature)
    {
        if (publicKey.Length != 32 || signature.Length != 64) return false;
        var a = Decode(publicKey);
        if (a is null) return false;
        var r = Decode(signature[..32]);
        if (r is null) return false;
        var s = LittleEndian(signature[32..]);
        if (s >= L) return false;
        var buf = new byte[64 + message.Length];
        signature[..32].CopyTo(buf);
        publicKey.CopyTo(buf.AsSpan(32));
        message.CopyTo(buf.AsSpan(64));
        var k = ScalarModL(SHA512.HashData(buf));
        var sB = Mul(s, G);
        var rka = Add(r.Value, Mul(k, a.Value));
        return Equal(sB, rka);
    }
}
