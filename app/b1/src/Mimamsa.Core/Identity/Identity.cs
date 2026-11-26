// Local accounts and server-side sessions (C-4: two roles, Admin and User; ownership checks in the backend).
// Passwords: PBKDF2-HMAC-SHA256, 600,000 iterations, 16-byte salt (OWASP 2023 figure). Session tokens: 32 random
// bytes; only their SHA-256 is stored. Idle timeout 30 min (client policy), absolute lifetime 12 h.
using System.Security.Cryptography;
using System.Text;
using Npgsql;

namespace Mimamsa.Core.Identity;

public sealed record Principal(string UserId, string Username, string Role, string SessionId, string Csrf)
{
    public bool IsAdmin => Role == "Admin";
}

public static class Passwords
{
    public const int Iterations = 600_000;

    public static string Hash(string password, int iterations = Iterations)
    {
        var salt = RandomNumberGenerator.GetBytes(16);
        var h = Rfc2898DeriveBytes.Pbkdf2(Encoding.UTF8.GetBytes(password), salt, iterations, HashAlgorithmName.SHA256, 32);
        return $"pbkdf2-sha256${iterations}${Convert.ToBase64String(salt)}${Convert.ToBase64String(h)}";
    }

    public static bool Verify(string password, string stored)
    {
        var p = stored.Split('$');
        if (p.Length != 4 || p[0] != "pbkdf2-sha256" || !int.TryParse(p[1], out var it) || it < 100_000) return false;
        var salt = Convert.FromBase64String(p[2]); var want = Convert.FromBase64String(p[3]);
        var got = Rfc2898DeriveBytes.Pbkdf2(Encoding.UTF8.GetBytes(password), salt, it, HashAlgorithmName.SHA256, want.Length);
        return CryptographicOperations.FixedTimeEquals(got, want);
    }

    /// Minimum policy for local accounts: 12+ characters. (Site policy may add more; AD integration is later.)
    public static string? Weakness(string password) => password.Length < 12 ? "Password must be at least 12 characters." : null;
}

public sealed class IdentityStore
{
    readonly NpgsqlDataSource _db;
    public TimeSpan Idle { get; init; } = TimeSpan.FromMinutes(30);
    public TimeSpan Absolute { get; init; } = TimeSpan.FromHours(12);
    public IdentityStore(NpgsqlDataSource db) { _db = db; }

    public const string Schema = """
        CREATE TABLE IF NOT EXISTS app_users(
          user_id text PRIMARY KEY, username text NOT NULL UNIQUE, role text NOT NULL CHECK (role IN ('Admin','User')),
          pwd_hash text NOT NULL, disabled boolean NOT NULL DEFAULT false, failed_count int NOT NULL DEFAULT 0,
          locked_until timestamptz, created_at timestamptz NOT NULL DEFAULT now());
        CREATE TABLE IF NOT EXISTS app_sessions(
          token_sha256 text PRIMARY KEY, session_id text NOT NULL UNIQUE, user_id text NOT NULL REFERENCES app_users(user_id),
          csrf text NOT NULL, created_at timestamptz NOT NULL DEFAULT now(), last_seen timestamptz NOT NULL DEFAULT now(),
          expires_at timestamptz NOT NULL);
        CREATE TABLE IF NOT EXISTS audit_log(
          id bigserial PRIMARY KEY, at timestamptz NOT NULL DEFAULT now(), actor text, action text NOT NULL, object text, detail text);
        """;

    static string TokenHash(string token) => Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(token))).ToLowerInvariant();
    static string NewToken() => Convert.ToBase64String(RandomNumberGenerator.GetBytes(32)).TrimEnd('=').Replace('+', '-').Replace('/', '_');

    public async Task EnsureSchemaAsync()
    {
        await using var c = await _db.OpenConnectionAsync();
        await using var cmd = new NpgsqlCommand(Schema, c);
        await cmd.ExecuteNonQueryAsync();
    }

    public async Task<bool> CreateUserAsync(string username, string role, string password, int iterations = Passwords.Iterations)
    {
        if (role is not ("Admin" or "User")) throw new ArgumentException("role must be Admin or User");
        if (Passwords.Weakness(password) is { } w) throw new ArgumentException(w);
        await using var c = await _db.OpenConnectionAsync();
        await using var cmd = new NpgsqlCommand("INSERT INTO app_users(user_id, username, role, pwd_hash) VALUES ($1,$2,$3,$4) ON CONFLICT (username) DO NOTHING", c);
        cmd.Parameters.AddWithValue("u-" + Guid.NewGuid().ToString("N")[..12]); cmd.Parameters.AddWithValue(username);
        cmd.Parameters.AddWithValue(role); cmd.Parameters.AddWithValue(Passwords.Hash(password, iterations));
        return await cmd.ExecuteNonQueryAsync() == 1;
    }

    public async Task<int> UserCountAsync()
    {
        await using var c = await _db.OpenConnectionAsync();
        await using var cmd = new NpgsqlCommand("SELECT count(*) FROM app_users", c);
        return (int)(long)(await cmd.ExecuteScalarAsync())!;
    }

    /// Returns (token, principal) or null. Five failures lock the account for 5 minutes. The same generic failure is
    /// returned for unknown users, wrong passwords, disabled and locked accounts (no account enumeration).
    public async Task<(string token, Principal p)?> LoginAsync(string username, string password)
    {
        if (username.Length is 0 or > 64 || password.Length is 0 or > 256) return null;
        await using var c = await _db.OpenConnectionAsync();
        string? uid = null, role = null, hash = null; bool disabled = false; DateTime? locked = null;
        await using (var q = new NpgsqlCommand("SELECT user_id, role, pwd_hash, disabled, locked_until FROM app_users WHERE username=$1", c))
        {
            q.Parameters.AddWithValue(username);
            await using var r = await q.ExecuteReaderAsync();
            if (await r.ReadAsync()) { uid = r.GetString(0); role = r.GetString(1); hash = r.GetString(2); disabled = r.GetBoolean(3); locked = r.IsDBNull(4) ? null : r.GetDateTime(4); }
        }
        bool ok = hash is not null && Passwords.Verify(password, hash) && !disabled && (locked is null || locked < DateTime.UtcNow);
        if (!ok)
        {
            if (uid is not null)
            {
                await using var f = new NpgsqlCommand("""
                    UPDATE app_users SET failed_count = failed_count + 1,
                      locked_until = CASE WHEN failed_count + 1 >= 5 THEN now() + interval '5 minutes' ELSE locked_until END
                    WHERE user_id=$1
                    """, c);
                f.Parameters.AddWithValue(uid); await f.ExecuteNonQueryAsync();
            }
            await AuditAsync(null, "login_failed", null, null);
            return null;
        }
        await using (var z = new NpgsqlCommand("UPDATE app_users SET failed_count=0, locked_until=NULL WHERE user_id=$1", c))
        { z.Parameters.AddWithValue(uid!); await z.ExecuteNonQueryAsync(); }
        var token = NewToken(); var sid = "s-" + Guid.NewGuid().ToString("N")[..16]; var csrf = NewToken();
        await using (var ins = new NpgsqlCommand("INSERT INTO app_sessions(token_sha256, session_id, user_id, csrf, expires_at) VALUES ($1,$2,$3,$4,now() + $5)", c))
        {
            ins.Parameters.AddWithValue(TokenHash(token)); ins.Parameters.AddWithValue(sid); ins.Parameters.AddWithValue(uid!);
            ins.Parameters.AddWithValue(csrf); ins.Parameters.AddWithValue(Absolute); await ins.ExecuteNonQueryAsync();
        }
        await AuditAsync(uid, "login", null, null);
        return (token, new Principal(uid!, username, role!, sid, csrf));
    }

    /// Per-request authentication from the database (no caching between requests). Touches last_seen.
    public async Task<Principal?> AuthenticateAsync(string? token)
    {
        if (string.IsNullOrEmpty(token) || token.Length > 128) return null;
        await using var c = await _db.OpenConnectionAsync();
        await using var q = new NpgsqlCommand("""
            UPDATE app_sessions s SET last_seen = now()
            FROM app_users u
            WHERE s.token_sha256 = $1 AND u.user_id = s.user_id AND NOT u.disabled
              AND s.expires_at > now() AND s.last_seen > now() - $2
            RETURNING u.user_id, u.username, u.role, s.session_id, s.csrf
            """, c);
        q.Parameters.AddWithValue(TokenHash(token)); q.Parameters.AddWithValue(Idle);
        await using var r = await q.ExecuteReaderAsync();
        return await r.ReadAsync() ? new Principal(r.GetString(0), r.GetString(1), r.GetString(2), r.GetString(3), r.GetString(4)) : null;
    }

    public async Task LogoutAsync(string? token)
    {
        if (string.IsNullOrEmpty(token)) return;
        await using var c = await _db.OpenConnectionAsync();
        await using var q = new NpgsqlCommand("DELETE FROM app_sessions WHERE token_sha256=$1", c);
        q.Parameters.AddWithValue(TokenHash(token)); await q.ExecuteNonQueryAsync();
    }

    /// Metadata-only audit (security architecture §10): never search text, document text or notes.
    public async Task AuditAsync(string? actor, string action, string? obj, string? detail)
    {
        await using var c = await _db.OpenConnectionAsync();
        await using var q = new NpgsqlCommand("INSERT INTO audit_log(actor, action, object, detail) VALUES ($1,$2,$3,$4)", c);
        q.Parameters.AddWithValue((object?)actor ?? DBNull.Value); q.Parameters.AddWithValue(action);
        q.Parameters.AddWithValue((object?)obj ?? DBNull.Value); q.Parameters.AddWithValue((object?)detail ?? DBNull.Value);
        await q.ExecuteNonQueryAsync();
    }
}
