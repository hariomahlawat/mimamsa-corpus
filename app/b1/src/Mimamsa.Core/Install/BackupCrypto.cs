// C16 Tranche B Stage 3 S3-C (B08, WD-10): encryption of offline backup media. No hand-rolled cryptography: the
// primitives are the platform's vetted implementations (System.Security.Cryptography: AES-256-GCM via Windows CNG or
// OpenSSL, HKDF-SHA256 per RFC 5869, SHA-256, RandomNumberGenerator). The only construction here is the standard
// "STREAM" chunked-AEAD composition (Hoang, Reyhanitabar, Rogaway, Vizar 2015, as used by age/Tink):
//   file   = MAGIC(8) | u32 header length | header (canonical JSON) | frame*
//   frame  = u32 plaintext length | ciphertext | 16-byte GCM tag
//   key    = HKDF-SHA256(ikm = 32-byte master key, salt = 32 random bytes from the header,
//                        info = "mimamsa-backup/1|" + part + "|" + backup_id)     (a fresh key per file)
//   nonce  = u64 big-endian frame counter | 3 zero bytes | final flag (1 on the last frame, else 0)
//   aad    = SHA-256(MAGIC | header length | header)                              (binds every frame to the header)
// Properties: confidentiality and integrity of every frame; reordering, dropping, duplicating or truncating frames, or
// appending data after the final frame, is detected; a changed header is detected; the wrong key is identified by the
// key id (a keyed hash, never the key) and then fails authentication anyway. Plaintext is released to the caller frame
// by frame only after that frame authenticated; callers treat output as untrusted until the stream ends cleanly (the
// restore extracts into scratch and commits only after the whole file verified).
// TEST/DEVELOPMENT keys only in Tranche B; production key custody and media policy are owner gate OG-3.
using System.Buffers.Binary;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json.Nodes;

namespace Mimamsa.Core.Install;

public sealed class BackupCryptoException(string code, string message) : Exception(code + ": " + message)
{
    public string Code { get; } = code;
}

public sealed record BackupHeader(string BackupId, string Part, byte[] Salt, string KeyId, int FrameBytes, string CreatedAt, byte[] Raw);

public static class BackupCrypto
{
    public static readonly byte[] Magic = "MIMBK001"u8.ToArray();
    public const string Format = "mimamsa-backup/1";
    public const int DefaultFrameBytes = 1 << 20;
    const int MaxHeader = 64 * 1024, TagBytes = 16;

    /// A new random 256-bit master key, written as 64 hex characters (development and test keys only).
    public static void NewKeyFile(string path)
    {
        if (File.Exists(path)) throw new BackupCryptoException("KEY_EXISTS", "refusing to overwrite an existing key file");
        Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(path))!);
        var k = RandomNumberGenerator.GetBytes(32);
        try { File.WriteAllText(path, Convert.ToHexString(k).ToLowerInvariant() + "\n", Encoding.ASCII); }
        finally { CryptographicOperations.ZeroMemory(k); }
        if (!OperatingSystem.IsWindows()) File.SetUnixFileMode(path, UnixFileMode.UserRead | UnixFileMode.UserWrite);
    }

    public static byte[] LoadKey(string path)
    {
        var t = File.ReadAllText(path, Encoding.ASCII).Trim();
        if (t.Length != 64 || !t.All(Uri.IsHexDigit)) throw new BackupCryptoException("KEY_MALFORMED", "a backup key is 64 hex characters");
        return Convert.FromHexString(t);
    }

    /// Key identifier: a keyed hash, so the header reveals nothing usable about the key.
    public static string KeyId(byte[] master) =>
        Convert.ToHexString(HMACSHA256.HashData(master, "mimamsa-backup-key-id/1"u8)).ToLowerInvariant()[..32];

    static byte[] FileKey(byte[] master, byte[] salt, string part, string backupId) =>
        HKDF.DeriveKey(HashAlgorithmName.SHA256, master, 32, salt, Encoding.UTF8.GetBytes($"{Format}|{part}|{backupId}"));

    static byte[] Nonce(ulong counter, bool final)
    {
        var n = new byte[12];
        BinaryPrimitives.WriteUInt64BigEndian(n, counter);
        n[11] = final ? (byte)1 : (byte)0;
        return n;
    }

    static byte[] HeaderBytes(string backupId, string part, byte[] salt, string keyId, int frameBytes, string createdAt) =>
        Activation.CanonicalJson.Bytes(new JsonObject
        {
            ["format"] = Format, ["cipher"] = "AES-256-GCM", ["kdf"] = "HKDF-SHA256", ["construction"] = "STREAM-u64-counter-final-flag",
            ["backup_id"] = backupId, ["part"] = part, ["salt"] = Convert.ToHexString(salt).ToLowerInvariant(), ["key_id"] = keyId,
            ["frame_bytes"] = frameBytes, ["created_at"] = createdAt,
        });

    /// Read and validate the header (no key needed); the stream is left at the first frame.
    public static BackupHeader ReadHeader(Stream s)
    {
        var magic = new byte[8];
        if (s.ReadAtLeast(magic, 8, throwOnEndOfStream: false) != 8 || !magic.SequenceEqual(Magic)) throw new BackupCryptoException("BACKUP_NOT_A_BACKUP", "bad magic");
        var lb = new byte[4];
        if (s.ReadAtLeast(lb, 4, throwOnEndOfStream: false) != 4) throw new BackupCryptoException("BACKUP_TRUNCATED", "header length");
        int len = (int)BinaryPrimitives.ReadUInt32BigEndian(lb);
        if (len <= 0 || len > MaxHeader) throw new BackupCryptoException("BACKUP_HEADER_INVALID", "header length out of range");
        var hb = new byte[len];
        if (s.ReadAtLeast(hb, len, throwOnEndOfStream: false) != len) throw new BackupCryptoException("BACKUP_TRUNCATED", "header");
        JsonObject h;
        try { h = Activation.CanonicalJson.ParseStrict(hb).AsObject(); }
        catch (Exception e) { throw new BackupCryptoException("BACKUP_HEADER_INVALID", e.Message); }
        if ((string?)h["format"] != Format || (string?)h["cipher"] != "AES-256-GCM" || (string?)h["kdf"] != "HKDF-SHA256")
            throw new BackupCryptoException("BACKUP_HEADER_INVALID", "unsupported format, cipher or kdf");
        var salt = Convert.FromHexString((string?)h["salt"] ?? "");
        int frame = (int?)h["frame_bytes"] ?? 0;
        if (salt.Length != 32 || frame < 1024 || frame > (16 << 20)) throw new BackupCryptoException("BACKUP_HEADER_INVALID", "salt or frame size");
        var raw = new byte[12 + len];
        Magic.CopyTo(raw, 0); lb.CopyTo(raw, 8); hb.CopyTo(raw, 12);
        return new BackupHeader((string)h["backup_id"]!, (string)h["part"]!, salt, (string)h["key_id"]!, frame, (string)h["created_at"]!, raw);
    }

    /// A write-only stream: plaintext in, encrypted frames out. Dispose (or Complete) writes the final frame.
    public sealed class EncryptStream : Stream
    {
        readonly Stream _out;
        readonly AesGcm _gcm;
        readonly byte[] _aad, _buf;
        int _fill;
        ulong _counter;
        bool _done;

        public EncryptStream(Stream output, byte[] master, string backupId, string part, int frameBytes = DefaultFrameBytes, string? createdAt = null)
        {
            if (master.Length != 32) throw new BackupCryptoException("KEY_MALFORMED", "the master key is 32 bytes");
            _out = output;
            var salt = RandomNumberGenerator.GetBytes(32);
            var hb = HeaderBytes(backupId, part, salt, KeyId(master), frameBytes, createdAt ?? DateTimeOffset.UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ"));
            var lb = new byte[4]; BinaryPrimitives.WriteUInt32BigEndian(lb, (uint)hb.Length);
            _out.Write(Magic); _out.Write(lb); _out.Write(hb);
            _aad = SHA256.HashData([.. Magic, .. lb, .. hb]);
            var key = FileKey(master, salt, part, backupId);
            _gcm = new AesGcm(key, TagBytes);
            CryptographicOperations.ZeroMemory(key);
            _buf = new byte[frameBytes];
        }

        void Emit(bool final)
        {
            var ct = new byte[_fill]; var tag = new byte[TagBytes];
            _gcm.Encrypt(Nonce(_counter++, final), _buf.AsSpan(0, _fill), ct, tag, _aad);
            var lb = new byte[4]; BinaryPrimitives.WriteUInt32BigEndian(lb, (uint)_fill);
            _out.Write(lb); _out.Write(ct); _out.Write(tag);
            CryptographicOperations.ZeroMemory(_buf.AsSpan(0, _fill));
            _fill = 0;
        }

        public override void Write(byte[] buffer, int offset, int count) => Write(buffer.AsSpan(offset, count));
        public override void Write(ReadOnlySpan<byte> data)
        {
            if (_done) throw new ObjectDisposedException(nameof(EncryptStream));
            while (data.Length > 0)
            {
                // a full buffer is emitted only when more data follows, so the last frame always carries the final flag
                if (_fill == _buf.Length) Emit(false);
                int n = Math.Min(data.Length, _buf.Length - _fill);
                data[..n].CopyTo(_buf.AsSpan(_fill));
                _fill += n; data = data[n..];
            }
        }

        public void Complete()
        {
            if (_done) return;
            Emit(true);
            _done = true;
            _out.Flush();
            _gcm.Dispose();
        }

        protected override void Dispose(bool disposing) { if (disposing) Complete(); base.Dispose(disposing); }
        public override bool CanRead => false; public override bool CanSeek => false; public override bool CanWrite => !_done;
        public override long Length => throw new NotSupportedException(); public override long Position { get => throw new NotSupportedException(); set => throw new NotSupportedException(); }
        public override void Flush() { }
        public override int Read(byte[] b, int o, int c) => throw new NotSupportedException();
        public override long Seek(long o, SeekOrigin s) => throw new NotSupportedException();
        public override void SetLength(long v) => throw new NotSupportedException();
    }

    /// A read-only stream over an encrypted file: each frame is authenticated before any of its bytes are returned;
    /// the end of the plaintext is reported only after the final frame authenticated and nothing follows it.
    public sealed class DecryptStream : Stream
    {
        readonly Stream _in;
        readonly AesGcm _gcm;
        readonly byte[] _aad;
        readonly int _frameBytes;
        byte[] _plain = [];
        int _pos;
        ulong _counter;
        bool _final, _eof;
        public BackupHeader Header { get; }

        public DecryptStream(Stream input, byte[] master, string? expectPart = null)
        {
            _in = input;
            Header = ReadHeader(input);
            if (expectPart is not null && Header.Part != expectPart) throw new BackupCryptoException("BACKUP_PART_MISMATCH", $"expected part {expectPart}, found {Header.Part}");
            if (master.Length != 32) throw new BackupCryptoException("KEY_MALFORMED", "the master key is 32 bytes");
            if (!CryptographicOperations.FixedTimeEquals(Encoding.ASCII.GetBytes(KeyId(master)), Encoding.ASCII.GetBytes(Header.KeyId)))
                throw new BackupCryptoException("BACKUP_WRONG_KEY", "the backup was encrypted under a different key");
            _aad = SHA256.HashData(Header.Raw);
            var key = FileKey(master, Header.Salt, Header.Part, Header.BackupId);
            _gcm = new AesGcm(key, TagBytes);
            CryptographicOperations.ZeroMemory(key);
            _frameBytes = Header.FrameBytes;
        }

        bool NextFrame()
        {
            if (_final)
            {
                if (!_eof)
                {
                    if (_in.ReadByte() != -1) throw new BackupCryptoException("BACKUP_TAMPERED", "data after the final frame");
                    _eof = true;
                }
                return false;
            }
            var lb = new byte[4];
            int got = _in.ReadAtLeast(lb, 4, throwOnEndOfStream: false);
            if (got == 0) throw new BackupCryptoException("BACKUP_TRUNCATED", "the stream ended before the final frame");
            if (got != 4) throw new BackupCryptoException("BACKUP_TRUNCATED", "frame length");
            int len = (int)BinaryPrimitives.ReadUInt32BigEndian(lb);
            if (len < 0 || len > _frameBytes) throw new BackupCryptoException("BACKUP_TAMPERED", "frame length out of range");
            var ct = new byte[len]; var tag = new byte[TagBytes];
            if (_in.ReadAtLeast(ct, len, throwOnEndOfStream: false) != len || _in.ReadAtLeast(tag, TagBytes, throwOnEndOfStream: false) != TagBytes)
                throw new BackupCryptoException("BACKUP_TRUNCATED", "frame body");
            var pt = new byte[len];
            // try as a non-final frame first; a full-size frame can only be non-final unless it is also the last
            try { _gcm.Decrypt(Nonce(_counter, false), ct, tag, pt, _aad); }
            catch (CryptographicException)
            {
                try { _gcm.Decrypt(Nonce(_counter, true), ct, tag, pt, _aad); _final = true; }
                catch (CryptographicException) { throw new BackupCryptoException("BACKUP_AUTH_FAILED", $"frame {_counter} failed authentication (tampered, reordered or wrong key)"); }
            }
            _counter++;
            _plain = pt; _pos = 0;
            return true;
        }

        public override int Read(byte[] buffer, int offset, int count) => Read(buffer.AsSpan(offset, count));
        public override int Read(Span<byte> dst)
        {
            while (_pos >= _plain.Length)
                if (!NextFrame()) return 0;
            int n = Math.Min(dst.Length, _plain.Length - _pos);
            _plain.AsSpan(_pos, n).CopyTo(dst);
            _pos += n;
            return n;
        }

        /// Read to the end, authenticating every frame (verification without keeping the plaintext).
        public long Drain()
        {
            long total = 0;
            var b = new byte[81920];
            int n;
            while ((n = Read(b)) > 0) total += n;
            return total;
        }

        protected override void Dispose(bool disposing) { if (disposing) _gcm.Dispose(); base.Dispose(disposing); }
        public override bool CanRead => true; public override bool CanSeek => false; public override bool CanWrite => false;
        public override long Length => throw new NotSupportedException(); public override long Position { get => throw new NotSupportedException(); set => throw new NotSupportedException(); }
        public override void Flush() { }
        public override long Seek(long o, SeekOrigin s) => throw new NotSupportedException();
        public override void SetLength(long v) => throw new NotSupportedException();
        public override void Write(byte[] b, int o, int c) => throw new NotSupportedException();
    }
}
