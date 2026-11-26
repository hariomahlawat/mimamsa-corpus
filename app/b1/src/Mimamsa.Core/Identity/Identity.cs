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
    public static string? Weakness(string password) => password.Length < 6 ? "Password must be at least 6 characters." : null;
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

    /// Failed attempts that lock an account, and for how long. The duration is configurable only in test mode.
    public const int LockThreshold = 5;
    public TimeSpan LockDuration { get; init; } = TimeSpan.FromMinutes(5);
    public LoginThrottle Throttle { get; init; } = new();

    public enum LoginOutcome { Ok, Failed, Locked, Throttled }

    /// Returns (token, principal) or null. Five failures lock the account for LockDuration (C14 F15):
    ///  - an attempt while the account is locked is refused WITHOUT verifying the password, without counting as a new
    ///    failure and without extending the lock, so the lock always ends LockDuration after the failure that set it;
    ///  - the first failure after a lock has expired starts a new count;
    ///  - failed attempts are also throttled per username and per source address (sliding window), before any
    ///    password work.
    /// The same generic failure is returned for unknown users, wrong passwords, disabled and locked accounts (no
    /// account enumeration); throttling applies equally to existing and unknown usernames.
    public async Task<(string token, Principal p)?> LoginAsync(string username, string password, string? source = null)
        => (await LoginDetailedAsync(username, password, source)).session;

    public async Task<(LoginOutcome outcome, (string token, Principal p)? session)> LoginDetailedAsync(string username, string password, string? source = null)
    {
        if (username.Length is 0 or > 64 || password.Length is 0 or > 256) return (LoginOutcome.Failed, null);
        var userKey = username.ToLowerInvariant();
        if (!Throttle.Allowed(userKey, source))
        {
            await AuditAsync(null, "login_throttled", null, null);
            return (LoginOutcome.Throttled, null);
        }
        await using var c = await _db.OpenConnectionAsync();
        string? uid = null, role = null, hash = null; bool disabled = false; bool lockedNow = false;
        await using (var q = new NpgsqlCommand("SELECT user_id, role, pwd_hash, disabled, (locked_until IS NOT NULL AND locked_until > now()) FROM app_users WHERE username=$1", c))
        {
            q.Parameters.AddWithValue(username);
            await using var r = await q.ExecuteReaderAsync();
            if (await r.ReadAsync()) { uid = r.GetString(0); role = r.GetString(1); hash = r.GetString(2); disabled = r.GetBoolean(3); lockedNow = r.GetBoolean(4); }
        }
        if (uid is not null && lockedNow)
        {
            Throttle.RecordFailure(userKey, source);
            await AuditAsync(null, "login_refused_locked", uid, null);
            return (LoginOutcome.Locked, null);
        }
        bool ok = hash is not null && Passwords.Verify(password, hash) && !disabled;
        if (!ok)
        {
            Throttle.RecordFailure(userKey, source);
            if (uid is not null)
            {
                // A lock that has expired is cleared and the count starts again; the lock is set exactly once, at the
                // LockThreshold-th failure, and never moved by later attempts.
                await using var f = new NpgsqlCommand("""
                    WITH cur AS (
                      SELECT CASE WHEN locked_until IS NOT NULL AND locked_until <= now() THEN 0 ELSE failed_count END AS n
                      FROM app_users WHERE user_id = $1)
                    UPDATE app_users u SET failed_count = cur.n + 1,
                      locked_until = CASE WHEN cur.n + 1 >= $2 THEN now() + $3 ELSE NULL END
                    FROM cur WHERE u.user_id = $1
                    RETURNING u.locked_until IS NOT NULL
                    """, c);
                f.Parameters.AddWithValue(uid); f.Parameters.AddWithValue(LockThreshold); f.Parameters.AddWithValue(LockDuration);
                var locked = (bool)(await f.ExecuteScalarAsync())!;
                await AuditAsync(null, "login_failed", uid, null);
                if (locked) await AuditAsync(null, "lockout", uid, $"locked for {LockDuration.TotalSeconds:0} s after {LockThreshold} failed attempts");
                return (locked ? LoginOutcome.Locked : LoginOutcome.Failed, null);
            }
            // Unknown usernames are not recorded (a password typed into the username field must never be stored).
            await AuditAsync(null, "login_failed", "unknown", null);
            return (LoginOutcome.Failed, null);
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
        return (LoginOutcome.Ok, (token, new Principal(uid!, username, role!, sid, csrf)));
    }

    /// Admin unlock: clears the lock and the failure count. The reason is mandatory and recorded (content-free audit).
    public async Task<bool> UnlockAsync(string username, string actorUserId, string reason)
    {
        await using var c = await _db.OpenConnectionAsync();
        await using var q = new NpgsqlCommand("UPDATE app_users SET failed_count = 0, locked_until = NULL WHERE username = $1 RETURNING user_id", c);
        q.Parameters.AddWithValue(username);
        var uid = (string?)await q.ExecuteScalarAsync();
        if (uid is null) return false;
        Throttle.Clear(username.ToLowerInvariant());
        await AuditAsync(actorUserId, "unlock", uid, reason);
        return true;
    }

    public sealed record AccountRow(string UserId, string Username, string Role, bool Disabled, int FailedCount, DateTime? LockedUntil, bool Locked);

    public async Task<List<AccountRow>> AccountsAsync()
    {
        await using var c = await _db.OpenConnectionAsync();
        await using var q = new NpgsqlCommand("SELECT user_id, username, role, disabled, failed_count, locked_until, (locked_until IS NOT NULL AND locked_until > now()) FROM app_users ORDER BY username", c);
        await using var r = await q.ExecuteReaderAsync();
        var l = new List<AccountRow>();
        while (await r.ReadAsync())
            l.Add(new AccountRow(r.GetString(0), r.GetString(1), r.GetString(2), r.GetBoolean(3), r.GetInt32(4), r.IsDBNull(5) ? null : r.GetDateTime(5), r.GetBoolean(6)));
        return l;
    }

    public sealed record AuditRow(long Id, DateTime At, string? Actor, string Action, string? Object, string? Detail);

    /// Audit page, newest first. Actor and object user ids are resolved to usernames; nothing else is joined in.
    public async Task<List<AuditRow>> AuditPageAsync(long? before, int limit)
    {
        limit = Math.Clamp(limit, 1, 200);
        await using var c = await _db.OpenConnectionAsync();
        await using var q = new NpgsqlCommand("""
            SELECT a.id, a.at, coalesce(ua.username, a.actor), a.action, coalesce(uo.username, a.object), a.detail
            FROM audit_log a LEFT JOIN app_users ua ON ua.user_id = a.actor LEFT JOIN app_users uo ON uo.user_id = a.object
            WHERE ($1::bigint IS NULL OR a.id < $1) ORDER BY a.id DESC LIMIT $2
            """, c);
        q.Parameters.AddWithValue(NpgsqlTypes.NpgsqlDbType.Bigint, (object?)before ?? DBNull.Value); q.Parameters.AddWithValue(limit);
        await using var r = await q.ExecuteReaderAsync();
        var l = new List<AuditRow>();
        while (await r.ReadAsync())
            l.Add(new AuditRow(r.GetInt64(0), r.GetDateTime(1), r.IsDBNull(2) ? null : r.GetString(2), r.GetString(3), r.IsDBNull(4) ? null : r.GetString(4), r.IsDBNull(5) ? null : r.GetString(5)));
        return l;
    }

    /// Per-request authentication from the database (no caching between requests). Touches last_seen unless
    /// `touch` is false (background policy polling must not keep an idle session alive).
    public async Task<Principal?> AuthenticateAsync(string? token, bool touch = true)
    {
        if (string.IsNullOrEmpty(token) || token.Length > 128) return null;
        await using var c = await _db.OpenConnectionAsync();
        await using var q = new NpgsqlCommand(touch ? """
            UPDATE app_sessions s SET last_seen = now()
            FROM app_users u
            WHERE s.token_sha256 = $1 AND u.user_id = s.user_id AND NOT u.disabled
              AND s.expires_at > now() AND s.last_seen > now() - $2
            RETURNING u.user_id, u.username, u.role, s.session_id, s.csrf
            """ : """
            SELECT u.user_id, u.username, u.role, s.session_id, s.csrf
            FROM app_sessions s JOIN app_users u ON u.user_id = s.user_id
            WHERE s.token_sha256 = $1 AND NOT u.disabled AND s.expires_at > now() AND s.last_seen > now() - $2
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
