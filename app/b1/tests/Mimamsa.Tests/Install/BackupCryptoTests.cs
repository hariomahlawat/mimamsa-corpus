// C16 S3-C (B08, WD-10): the encrypted backup format. Round trip, wrong key, and every tampering class: a flipped
// ciphertext or tag bit, a changed header, truncation (inside a frame and at a frame boundary), dropped, reordered and
// duplicated frames, and data appended after the final frame. All must be refused before plaintext is trusted.
using System.Buffers.Binary;
using System.Security.Cryptography;
using Mimamsa.Core.Install;

namespace Mimamsa.Tests.Install;

public class BackupCryptoTests
{
    static byte[] Enc(byte[] key, byte[] plain, int frame = 1024, string part = "site", string id = "BK-test")
    {
        using var ms = new MemoryStream();
        using (var e = new BackupCrypto.EncryptStream(ms, key, id, part, frame)) e.Write(plain);
        return ms.ToArray();
    }

    static byte[] Dec(byte[] key, byte[] file, string? part = "site")
    {
        using var d = new BackupCrypto.DecryptStream(new MemoryStream(file), key, part);
        using var o = new MemoryStream();
        d.CopyTo(o);
        return o.ToArray();
    }

    static string Code(Action a) => Assert.Throws<BackupCryptoException>(a).Code;

    /// Offsets of the frames (start of each u32 length) after the header.
    static List<(int start, int len)> Frames(byte[] f)
    {
        int hl = (int)BinaryPrimitives.ReadUInt32BigEndian(f.AsSpan(8));
        int pos = 12 + hl;
        var o = new List<(int, int)>();
        while (pos < f.Length)
        {
            int n = (int)BinaryPrimitives.ReadUInt32BigEndian(f.AsSpan(pos));
            o.Add((pos, 4 + n + 16));
            pos += 4 + n + 16;
        }
        return o;
    }

    [Theory]
    [InlineData(0), InlineData(1), InlineData(1023), InlineData(1024), InlineData(1025), InlineData(5000)]
    public void Round_trip(int size)
    {
        var key = RandomNumberGenerator.GetBytes(32);
        var plain = RandomNumberGenerator.GetBytes(size);
        var f = Enc(key, plain);
        Assert.Equal(plain, Dec(key, f));
        Assert.Equal(Math.Max(1, (size + 1023) / 1024), Frames(f).Count);
        // ciphertext does not contain the plaintext and two encryptions differ (fresh salt => fresh key)
        Assert.NotEqual(f, Enc(key, plain));
    }

    [Fact]
    public void Wrong_key_is_refused_by_key_id_and_the_key_is_never_in_the_header()
    {
        var key = RandomNumberGenerator.GetBytes(32);
        var f = Enc(key, RandomNumberGenerator.GetBytes(3000));
        Assert.Equal("BACKUP_WRONG_KEY", Code(() => Dec(RandomNumberGenerator.GetBytes(32), f)));
        var h = BackupCrypto.ReadHeader(new MemoryStream(f));
        Assert.DoesNotContain(Convert.ToHexString(key).ToLowerInvariant(), System.Text.Encoding.ASCII.GetString(h.Raw));
        Assert.Equal("BACKUP_PART_MISMATCH", Code(() => Dec(key, f, "appendonly")));
    }

    [Fact]
    public void Any_flipped_bit_in_a_frame_fails_authentication()
    {
        var key = RandomNumberGenerator.GetBytes(32);
        var f = Enc(key, RandomNumberGenerator.GetBytes(3000));
        foreach (var (start, len) in Frames(f))
            foreach (var off in new[] { 4, len / 2, len - 1 })   // ciphertext start, middle, tag
            {
                var g = (byte[])f.Clone(); g[start + off] ^= 0x01;
                Assert.Equal("BACKUP_AUTH_FAILED", Code(() => Dec(key, g)));
            }
    }

    [Fact]
    public void A_changed_header_fails()
    {
        var key = RandomNumberGenerator.GetBytes(32);
        var f = Enc(key, RandomNumberGenerator.GetBytes(3000));
        var text = System.Text.Encoding.ASCII.GetString(f, 12, (int)BinaryPrimitives.ReadUInt32BigEndian(f.AsSpan(8)));
        int i = text.IndexOf("\"created_at\":\"", StringComparison.Ordinal) + 14;   // change a digit of the timestamp
        var g = (byte[])f.Clone(); g[12 + i] = (byte)(g[12 + i] == (byte)'1' ? '2' : '1');
        Assert.Equal("BACKUP_AUTH_FAILED", Code(() => Dec(key, g)));
        var h = (byte[])f.Clone(); h[0] = (byte)'X';
        Assert.Equal("BACKUP_NOT_A_BACKUP", Code(() => Dec(key, h)));
    }

    [Fact]
    public void Truncation_dropping_reordering_duplicating_and_appending_are_detected()
    {
        var key = RandomNumberGenerator.GetBytes(32);
        var f = Enc(key, RandomNumberGenerator.GetBytes(3500));     // 4 frames
        var fr = Frames(f);
        Assert.Equal(4, fr.Count);
        byte[] Cat(params (int s, int l)[] parts) => [.. f.AsSpan(0, fr[0].start).ToArray(), .. parts.SelectMany(p => f.AsSpan(p.s, p.l).ToArray())];
        Assert.Equal("BACKUP_TRUNCATED", Code(() => Dec(key, Cat(fr[0], fr[1], fr[2]))));                 // final frame dropped at a boundary
        Assert.Equal("BACKUP_TRUNCATED", Code(() => Dec(key, f[..(f.Length - 7)])));                      // cut inside the final frame
        Assert.Equal("BACKUP_TRUNCATED", Code(() => Dec(key, f[..(fr[0].start + 2)])));                   // cut inside a length
        Assert.Equal("BACKUP_AUTH_FAILED", Code(() => Dec(key, Cat(fr[1], fr[0], fr[2], fr[3]))));       // reordered
        Assert.Equal("BACKUP_AUTH_FAILED", Code(() => Dec(key, Cat(fr[0], fr[2], fr[3]))));              // a middle frame dropped
        Assert.Equal("BACKUP_AUTH_FAILED", Code(() => Dec(key, Cat(fr[0], fr[0], fr[1], fr[2], fr[3])))); // duplicated
        Assert.Equal("BACKUP_TAMPERED", Code(() => Dec(key, [.. f, 0x00])));                              // data after the final frame
        Assert.Equal("BACKUP_TAMPERED", Code(() => Dec(key, [.. f, .. f.AsSpan(fr[3].start, fr[3].len).ToArray()])));
        // a frame spliced from ANOTHER backup under the same key fails (per-file key from the header salt)
        var other = Enc(key, RandomNumberGenerator.GetBytes(3500));
        var of = Frames(other);
        Assert.Equal("BACKUP_AUTH_FAILED", Code(() => Dec(key, [.. f.AsSpan(0, fr[3].start).ToArray(), .. other.AsSpan(of[3].start, of[3].len).ToArray()])));
    }

    [Fact]
    public void Key_files_are_hex_never_overwritten_and_malformed_keys_refused()
    {
        var b = S3cDirs.New("key");
        try
        {
            var p = Path.Combine(b, "backup.key");
            BackupCrypto.NewKeyFile(p);
            Assert.Equal(32, BackupCrypto.LoadKey(p).Length);
            Assert.Equal("KEY_EXISTS", Assert.Throws<BackupCryptoException>(() => BackupCrypto.NewKeyFile(p)).Code);
            File.WriteAllText(p, "abc");
            Assert.Equal("KEY_MALFORMED", Assert.Throws<BackupCryptoException>(() => BackupCrypto.LoadKey(p)).Code);
        }
        finally { S3cDirs.Delete(b); }
    }
}
