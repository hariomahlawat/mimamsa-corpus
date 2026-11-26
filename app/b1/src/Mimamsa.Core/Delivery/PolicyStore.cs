// Durable serving policy (R2-N01): copy eligibility, the policy witness (epoch, digest) and the local Admin
// withdrawal record. One PostgreSQL transaction per withdrawal (CAS on the witness). Refactored from the PoC admin
// endpoint into the core so that the Web adapter only binds HTTP.
// Scope note: local Admin withdrawals live in the site database; contract README §3.3 records that the signed
// exclusion channel does not yet cover them (conflict X7, B2).
using System.Security.Cryptography;
using System.Text;
using Npgsql;

namespace Mimamsa.Core.Delivery;

public sealed record WithdrawalRow(string DocId, string Sha, string Reason, string Actor, DateTime At, long Epoch)
{
    public string Action { get; init; } = "withdraw";
    public string Scope { get; init; } = "document";
    public string? Verification { get; init; }
}

public sealed class PolicyStore
{
    readonly NpgsqlDataSource _db;
    public PolicyStore(NpgsqlDataSource db) { _db = db; }

    public const string Schema = """
        CREATE TABLE IF NOT EXISTS vault_copies(doc_id text, copy_sha256 text, length bigint NOT NULL,
          state text NOT NULL DEFAULT 'eligible' CHECK (state IN ('eligible','withdrawn')), fence_seq bigint NOT NULL DEFAULT 0,
          PRIMARY KEY (doc_id, copy_sha256));
        CREATE TABLE IF NOT EXISTS serving_policy(id int PRIMARY KEY CHECK (id = 1), epoch bigint NOT NULL, digest text NOT NULL);
        INSERT INTO serving_policy VALUES (1, 1, 'state-1') ON CONFLICT DO NOTHING;
        CREATE TABLE IF NOT EXISTS withdrawals(id bigserial PRIMARY KEY, doc_id text NOT NULL, copy_sha256 text NOT NULL,
          reason text NOT NULL CHECK (length(trim(reason)) >= 3), actor text NOT NULL, at timestamptz NOT NULL DEFAULT now(), epoch bigint NOT NULL);
        -- C14: one history for both directions, and the scope a withdrawal was taken under (owner policy: verified
        -- duplicate copies are distinguished from distinct editions and only included on explicit opt-in).
        ALTER TABLE withdrawals ADD COLUMN IF NOT EXISTS action text NOT NULL DEFAULT 'withdraw';
        ALTER TABLE withdrawals ADD COLUMN IF NOT EXISTS scope text NOT NULL DEFAULT 'document';
        ALTER TABLE withdrawals ADD COLUMN IF NOT EXISTS verification text;
        """;

    public async Task EnsureSchemaAsync()
    {
        await using var c = await _db.OpenConnectionAsync();
        await using var cmd = new NpgsqlCommand(Schema, c);
        await cmd.ExecuteNonQueryAsync();
    }

    /// Register every verified copy of the active generation as eligible unless already present (a withdrawal is
    /// never undone by a restart or re-import).
    public async Task SyncCopiesAsync(IEnumerable<(string docId, string sha, long length)> copies)
    {
        await using var c = await _db.OpenConnectionAsync();
        await using var tx = await c.BeginTransactionAsync();
        foreach (var (d, s, l) in copies)
        {
            await using var cmd = new NpgsqlCommand("INSERT INTO vault_copies(doc_id, copy_sha256, length) VALUES ($1,$2,$3) ON CONFLICT DO NOTHING", c, tx);
            cmd.Parameters.AddWithValue(d); cmd.Parameters.AddWithValue(s); cmd.Parameters.AddWithValue(l);
            await cmd.ExecuteNonQueryAsync();
        }
        await tx.CommitAsync();
    }

    public async Task<(List<(string, string)> withdrawn, long epoch, string digest)> LoadAsync()
    {
        await using var c = await _db.OpenConnectionAsync();
        var w = new List<(string, string)>();
        await using (var q = new NpgsqlCommand("SELECT doc_id, copy_sha256 FROM vault_copies WHERE state='withdrawn'", c))
        await using (var r = await q.ExecuteReaderAsync())
            while (await r.ReadAsync()) w.Add((r.GetString(0), r.GetString(1)));
        await using var pq = new NpgsqlCommand("SELECT epoch, digest FROM serving_policy WHERE id = 1", c);
        await using var pr = await pq.ExecuteReaderAsync();
        await pr.ReadAsync();
        return (w, pr.GetInt64(0), pr.GetString(1));
    }

    public async Task<List<string>> CopiesOfAsync(string docId)
    {
        await using var c = await _db.OpenConnectionAsync();
        await using var q = new NpgsqlCommand("SELECT copy_sha256 FROM vault_copies WHERE doc_id=$1", c);
        q.Parameters.AddWithValue(docId);
        var l = new List<string>();
        await using var r = await q.ExecuteReaderAsync();
        while (await r.ReadAsync()) l.Add(r.GetString(0));
        return l;
    }

    public async Task<string?> CopyStateAsync(string docId, string sha)
    {
        await using var c = await _db.OpenConnectionAsync();
        await using var q = new NpgsqlCommand("SELECT state FROM vault_copies WHERE doc_id=$1 AND copy_sha256=$2", c);
        q.Parameters.AddWithValue(docId); q.Parameters.AddWithValue(sha);
        return (string?)await q.ExecuteScalarAsync();
    }

    /// Durable CAS: copy -> withdrawn and witness epoch+1 in one transaction; returns changed=false when the copy was
    /// already withdrawn (idempotent, no epoch bump). Throws on witness CAS failure (caller stays fenced: fail closed).
    public async Task<(long epoch, string digest, bool changed)> WithdrawCasAsync(string docId, string sha, string op, string reason, string actor)
        => await WithdrawDocCasAsync(docId, sha, op, reason, actor);

    /// Document-level withdrawal: every eligible copy row of the doc_id becomes withdrawn in one transaction.
    public async Task<(long epoch, string digest, bool changed)> WithdrawDocCasAsync(string docId, string currentSha, string op, string reason, string actor)
        => await WithdrawDocCasAsync(docId, currentSha, op, reason, actor, "document");

    public async Task<(long epoch, string digest, bool changed)> WithdrawDocCasAsync(string docId, string currentSha, string op, string reason, string actor, string scope)
    {
        await using var c = await _db.OpenConnectionAsync();
        await using var tx = await c.BeginTransactionAsync();
        long e0; string d0;
        await using (var q = new NpgsqlCommand("SELECT epoch, digest FROM serving_policy WHERE id = 1 FOR UPDATE", c, tx))
        await using (var r = await q.ExecuteReaderAsync()) { await r.ReadAsync(); e0 = r.GetInt64(0); d0 = r.GetString(1); }
        int rows;
        await using (var u = new NpgsqlCommand("UPDATE vault_copies SET state='withdrawn', fence_seq=fence_seq+1 WHERE doc_id=$1 AND state='eligible'", c, tx))
        { u.Parameters.AddWithValue(docId); rows = await u.ExecuteNonQueryAsync(); }
        if (rows == 0) { await tx.RollbackAsync(); return (e0, d0, false); }
        var sha = currentSha;
        var d1 = "state-" + Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes($"{d0}|{op}|{docId}|{sha}|{e0 + 1}")))[..16].ToLowerInvariant();
        await using (var cas = new NpgsqlCommand("UPDATE serving_policy SET epoch = $1, digest = $2 WHERE id = 1 AND epoch = $3", c, tx))
        {
            cas.Parameters.AddWithValue(e0 + 1); cas.Parameters.AddWithValue(d1); cas.Parameters.AddWithValue(e0);
            if (await cas.ExecuteNonQueryAsync() != 1) throw new InvalidOperationException("witness CAS failed");
        }
        await using (var w = new NpgsqlCommand("INSERT INTO withdrawals(doc_id, copy_sha256, reason, actor, epoch, action, scope) VALUES ($1,$2,$3,$4,$5,'withdraw',$6)", c, tx))
        {
            w.Parameters.AddWithValue(docId); w.Parameters.AddWithValue(sha); w.Parameters.AddWithValue(reason);
            w.Parameters.AddWithValue(actor); w.Parameters.AddWithValue(e0 + 1); w.Parameters.AddWithValue(scope); await w.ExecuteNonQueryAsync();
        }
        await tx.CommitAsync();
        return (e0 + 1, d1, true);
    }

    /// Reinstatement (owner policy): every withdrawn copy row of the doc_id becomes eligible again and the witness epoch
    /// is bumped, in one transaction, with the reason and the renewed-verification summary recorded. The caller must
    /// have re-verified eligibility BEFORE calling; this method changes nothing when no copy row is withdrawn.
    public async Task<(long epoch, string digest, bool changed, List<string> shas)> ReinstateDocCasAsync(string docId, string currentSha, string op, string reason, string actor, string verification)
    {
        await using var c = await _db.OpenConnectionAsync();
        await using var tx = await c.BeginTransactionAsync();
        long e0; string d0;
        await using (var q = new NpgsqlCommand("SELECT epoch, digest FROM serving_policy WHERE id = 1 FOR UPDATE", c, tx))
        await using (var r = await q.ExecuteReaderAsync()) { await r.ReadAsync(); e0 = r.GetInt64(0); d0 = r.GetString(1); }
        var shas = new List<string>();
        await using (var u = new NpgsqlCommand("UPDATE vault_copies SET state='eligible', fence_seq=fence_seq+1 WHERE doc_id=$1 AND state='withdrawn' RETURNING copy_sha256", c, tx))
        {
            u.Parameters.AddWithValue(docId);
            await using var r = await u.ExecuteReaderAsync();
            while (await r.ReadAsync()) shas.Add(r.GetString(0));
        }
        if (shas.Count == 0) { await tx.RollbackAsync(); return (e0, d0, false, shas); }
        var d1 = "state-" + Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes($"{d0}|{op}|reinstate|{docId}|{currentSha}|{e0 + 1}")))[..16].ToLowerInvariant();
        await using (var cas = new NpgsqlCommand("UPDATE serving_policy SET epoch = $1, digest = $2 WHERE id = 1 AND epoch = $3", c, tx))
        {
            cas.Parameters.AddWithValue(e0 + 1); cas.Parameters.AddWithValue(d1); cas.Parameters.AddWithValue(e0);
            if (await cas.ExecuteNonQueryAsync() != 1) throw new InvalidOperationException("witness CAS failed");
        }
        await using (var w = new NpgsqlCommand("INSERT INTO withdrawals(doc_id, copy_sha256, reason, actor, epoch, action, scope, verification) VALUES ($1,$2,$3,$4,$5,'reinstate','document',$6)", c, tx))
        {
            w.Parameters.AddWithValue(docId); w.Parameters.AddWithValue(currentSha); w.Parameters.AddWithValue(reason);
            w.Parameters.AddWithValue(actor); w.Parameters.AddWithValue(e0 + 1); w.Parameters.AddWithValue(verification); await w.ExecuteNonQueryAsync();
        }
        await tx.CommitAsync();
        return (e0 + 1, d1, true, shas);
    }

    public async Task<List<WithdrawalRow>> WithdrawalsAsync()
    {
        await using var c = await _db.OpenConnectionAsync();
        await using var q = new NpgsqlCommand("SELECT doc_id, copy_sha256, reason, actor, at, epoch, action, scope, verification FROM withdrawals ORDER BY id DESC LIMIT 200", c);
        await using var r = await q.ExecuteReaderAsync();
        var list = new List<WithdrawalRow>();
        while (await r.ReadAsync()) list.Add(new WithdrawalRow(r.GetString(0), r.GetString(1), r.GetString(2), r.GetString(3), r.GetDateTime(4), r.GetInt64(5))
            { Action = r.GetString(6), Scope = r.GetString(7), Verification = r.IsDBNull(8) ? null : r.GetString(8) });
        return list;
    }
}
