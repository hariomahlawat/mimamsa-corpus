// Platform-neutral atomic transport-credit ledger (Serving §10, R2-N01). No ASP.NET or OS dependency.
// PostgreSQL holds the authoritative counters; CHECK constraints make overcommit impossible even if the
// application logic were wrong. Lock order is fixed: the 'site' row FIRST (single serialization point for every
// ledger transaction, i.e. the "single serialized admission loop" option of Serving §10), then the connection row.
// No transaction waits for 'site' while holding another ledger lock, so the protocol is deadlock-free.
using Npgsql;

namespace MimamsaPoc.Core;

public enum Settlement { Accepted, ReleasedZeroTransfer, Uncertain }

public sealed record Reservation(Guid Id, string ConnPool, long Amount);

public sealed record CreditConfig(long SiteCap, long ConnCap, long HeaderAllowance);

public sealed class CreditLedger
{
    public const string SitePool = "site";
    private readonly NpgsqlDataSource _db;
    private readonly CreditConfig _cfg;
    public string InstanceId { get; } = $"{Environment.MachineName}:{Environment.ProcessId}:{Guid.NewGuid():N}";

    public CreditLedger(NpgsqlDataSource db, CreditConfig cfg) { _db = db; _cfg = cfg; }

    public const string Schema = """
        CREATE TABLE IF NOT EXISTS credit_pools(
          pool_id text PRIMARY KEY, cap bigint NOT NULL, reserved bigint NOT NULL DEFAULT 0, charged bigint NOT NULL DEFAULT 0,
          CONSTRAINT credit_nonneg CHECK (reserved >= 0 AND charged >= 0),
          CONSTRAINT credit_no_overcommit CHECK (reserved + charged <= cap));
        CREATE TABLE IF NOT EXISTS credit_reservations(
          res_id uuid PRIMARY KEY, instance_id text NOT NULL, conn_pool text NOT NULL, session_id text, doc_id text,
          copy_sha256 text, range_start bigint, range_len bigint, amount bigint NOT NULL, charged bigint NOT NULL DEFAULT 0,
          accepted_bytes bigint NOT NULL DEFAULT 0,
          state text NOT NULL CHECK (state IN ('RESERVED','ACCEPTED','RELEASED','UNCERTAIN','DRAINED')),
          reason text, created_at timestamptz NOT NULL DEFAULT clock_timestamp(), settled_at timestamptz, drained_at timestamptz,
          duplicate_settlements int NOT NULL DEFAULT 0);
        CREATE INDEX IF NOT EXISTS credit_res_conn ON credit_reservations(conn_pool) WHERE state IN ('RESERVED','ACCEPTED','UNCERTAIN');
        CREATE TABLE IF NOT EXISTS credit_instances(instance_id text PRIMARY KEY, started_at timestamptz DEFAULT clock_timestamp(),
          heartbeat_at timestamptz DEFAULT clock_timestamp());
        """;

    public async Task InitAsync(bool resetForTest)
    {
        await using var c = await _db.OpenConnectionAsync();
        await using (var cmd = new NpgsqlCommand(Schema, c)) await cmd.ExecuteNonQueryAsync();
        if (resetForTest)
        {
            await using var r = new NpgsqlCommand("TRUNCATE credit_reservations, credit_pools, credit_instances", c);
            await r.ExecuteNonQueryAsync();
        }
        // Site cap is configuration; never lower it below what is already outstanding (CHECK would fail loudly).
        await using (var cmd = new NpgsqlCommand(
            """
            INSERT INTO credit_pools(pool_id, cap) VALUES ('site', $1)
            ON CONFLICT (pool_id) DO UPDATE SET cap = EXCLUDED.cap
            """, c))
        { cmd.Parameters.AddWithValue(_cfg.SiteCap); await cmd.ExecuteNonQueryAsync(); }
        await using (var cmd = new NpgsqlCommand("INSERT INTO credit_instances(instance_id) VALUES ($1)", c))
        { cmd.Parameters.AddWithValue(InstanceId); await cmd.ExecuteNonQueryAsync(); }
    }

    public static string ConnPoolId(string instanceId, string connectionId) => $"conn:{instanceId}:{connectionId}";

    /// Atomically reserve `amount` on both the connection pool and the site pool, or nothing.
    /// `admit` (optional) runs inside the same transaction after the caps check and before COMMIT; returning
    /// false rolls the reservation back. The delivery adapter uses it to take serving_policy FOR SHARE and to
    /// recheck policy authority (epoch, pending withdrawal, eligibility) so no reservation can commit under a
    /// stale policy or between withdrawal admission and the durable fence.
    public async Task<Reservation?> TryReserveAsync(string connPool, long amount, string sessionId, string docId,
                                                    string sha, long start, long len,
                                                    Func<NpgsqlConnection, NpgsqlTransaction, Guid, Task<bool>>? admit = null)
    {
        await using var c = await _db.OpenConnectionAsync();
        await using var tx = await c.BeginTransactionAsync();
        await LockSiteAsync(c, tx);
        await using (var ins = new NpgsqlCommand("INSERT INTO credit_pools(pool_id, cap) VALUES ($1, $2) ON CONFLICT DO NOTHING", c, tx))
        { ins.Parameters.AddWithValue(connPool); ins.Parameters.AddWithValue(_cfg.ConnCap); await ins.ExecuteNonQueryAsync(); }
        var pools = new[] { connPool, SitePool };
        bool ok = true;
        await using (var sel = new NpgsqlCommand(
            "SELECT pool_id, cap, reserved, charged FROM credit_pools WHERE pool_id = ANY($1) FOR UPDATE", c, tx))
        {
            sel.Parameters.AddWithValue(pools);
            await using var r = await sel.ExecuteReaderAsync();
            int n = 0;
            while (await r.ReadAsync()) { n++; if (r.GetInt64(2) + r.GetInt64(3) + amount > r.GetInt64(1)) ok = false; }
            if (n != 2) ok = false;
        }
        if (!ok) { await tx.RollbackAsync(); return null; }
        var id = Guid.NewGuid();
        if (admit is not null && !await admit(c, tx, id)) { await tx.RollbackAsync(); return null; }
        await using (var up = new NpgsqlCommand("UPDATE credit_pools SET reserved = reserved + $1 WHERE pool_id = ANY($2)", c, tx))
        { up.Parameters.AddWithValue(amount); up.Parameters.AddWithValue(pools); await up.ExecuteNonQueryAsync(); }
        await using (var ins = new NpgsqlCommand(
            """
            INSERT INTO credit_reservations(res_id, instance_id, conn_pool, session_id, doc_id, copy_sha256, range_start, range_len, amount, state)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,'RESERVED')
            """, c, tx))
        {
            foreach (var v in new object[] { id, InstanceId, connPool, sessionId, docId, sha, start, len, amount }) ins.Parameters.AddWithValue(v);
            await ins.ExecuteNonQueryAsync();
        }
        await tx.CommitAsync();
        return new Reservation(id, connPool, amount);
    }

    /// Settle once. Accepted(k): charge k (+ header allowance if k > 0), release the proven-unused rest.
    /// ReleasedZeroTransfer: release all (only when zero transfer is established). Uncertain: charge the full amount.
    /// A duplicate settlement is a no-op (counted), never a second release or charge.
    public async Task<bool> SettleAsync(Reservation res, Settlement s, long acceptedBytes, string reason)
    {
        await using var c = await _db.OpenConnectionAsync();
        await using var tx = await c.BeginTransactionAsync();
        var pools = new[] { res.ConnPool, SitePool };
        await LockSiteAsync(c, tx);
        await LockPoolAsync(c, tx, res.ConnPool);
        long charge = s switch
        {
            Settlement.Accepted => acceptedBytes <= 0 ? 0 : Math.Min(res.Amount, acceptedBytes + _cfg.HeaderAllowance),
            Settlement.Uncertain => res.Amount,
            _ => 0
        };
        string state = s switch { Settlement.Accepted => "ACCEPTED", Settlement.Uncertain => "UNCERTAIN", _ => "RELEASED" };
        await using var upd = new NpgsqlCommand(
            """
            UPDATE credit_reservations SET state=$2, charged=$3, accepted_bytes=$4, reason=$5, settled_at=clock_timestamp()
            WHERE res_id=$1 AND state='RESERVED' RETURNING amount
            """, c, tx);
        foreach (var v in new object[] { res.Id, state, charge, acceptedBytes, reason }) upd.Parameters.AddWithValue(v);
        var amt = await upd.ExecuteScalarAsync();
        if (amt is null)
        {
            await using var dup = new NpgsqlCommand("UPDATE credit_reservations SET duplicate_settlements = duplicate_settlements + 1 WHERE res_id=$1", c, tx);
            dup.Parameters.AddWithValue(res.Id); await dup.ExecuteNonQueryAsync();
            await tx.CommitAsync(); return false;
        }
        await using (var p = new NpgsqlCommand("UPDATE credit_pools SET reserved = reserved - $1, charged = charged + $2 WHERE pool_id = ANY($3)", c, tx))
        { p.Parameters.AddWithValue((long)amt); p.Parameters.AddWithValue(charge); p.Parameters.AddWithValue(pools); await p.ExecuteNonQueryAsync(); }
        await tx.CommitAsync();
        return true;
    }

    /// Release charges of a connection pool ONLY after transport termination has been observed (the caller passes
    /// the evidence). Unsettled RESERVED rows on a terminated connection are treated as uncertain: charged in full,
    /// then drained with the same evidence (never refunded as if unused).
    public async Task<List<(Guid id, string priorState)>> DrainConnectionAsync(string connPool, string evidence)
    {
        await using var c = await _db.OpenConnectionAsync();
        await using var tx = await c.BeginTransactionAsync();
        var pools = new[] { connPool, SitePool };
        await LockSiteAsync(c, tx);
        await LockPoolAsync(c, tx, connPool);
        long reservedGone = 0, chargedGone = 0; int n = 0;
        var drained = new List<(Guid, string)>();
        await using (var q = new NpgsqlCommand(
            """
            UPDATE credit_reservations SET
              charged = CASE WHEN state='RESERVED' THEN amount ELSE charged END,
              reason = coalesce(reason,'') || CASE WHEN state='RESERVED' THEN ' | unsettled at termination: treated as uncertain' ELSE '' END
                       || ' | drained: ' || $2,
              state='DRAINED', drained_at=clock_timestamp()
            WHERE conn_pool=$1 AND state IN ('RESERVED','ACCEPTED','UNCERTAIN')
            RETURNING amount, charged, (settled_at IS NULL), res_id
            """, c, tx))
        {
            q.Parameters.AddWithValue(connPool); q.Parameters.AddWithValue(evidence);
            await using var r = await q.ExecuteReaderAsync();
            while (await r.ReadAsync())
            {
                n++;
                if (r.GetBoolean(2)) reservedGone += r.GetInt64(0); else chargedGone += r.GetInt64(1);
                drained.Add((r.GetGuid(3), r.GetBoolean(2) ? "RESERVED" : "SETTLED"));
            }
        }
        if (n > 0)
        {
            await using var p = new NpgsqlCommand("UPDATE credit_pools SET reserved = reserved - $1, charged = charged - $2 WHERE pool_id = ANY($3)", c, tx);
            p.Parameters.AddWithValue(reservedGone); p.Parameters.AddWithValue(chargedGone); p.Parameters.AddWithValue(pools);
            await p.ExecuteNonQueryAsync();
        }
        await using (var d = new NpgsqlCommand("DELETE FROM credit_pools WHERE pool_id=$1 AND reserved=0 AND charged=0", c, tx))
        { d.Parameters.AddWithValue(connPool); await d.ExecuteNonQueryAsync(); }
        await tx.CommitAsync();
        return drained;
    }

    /// Outstanding charges of OTHER (previous) process instances survive restart. They are released only by an
    /// explicit reconciliation call (operator/admin) once the caller asserts that the old process is gone and the
    /// configured residual-delivery grace has elapsed; the evidence string is stored with every drained row.
    public async Task<List<(Guid id, string priorState)>> ReconcilePriorInstancesAsync(string evidence, TimeSpan minAgeSinceHeartbeat)
    {
        await using var c = await _db.OpenConnectionAsync();
        await using var q = new NpgsqlCommand(
            """
            SELECT DISTINCT r.conn_pool FROM credit_reservations r JOIN credit_instances i USING (instance_id)
            WHERE r.instance_id <> $1 AND r.state IN ('RESERVED','ACCEPTED','UNCERTAIN')
              AND i.heartbeat_at < clock_timestamp() - $2
            """, c);
        q.Parameters.AddWithValue(InstanceId); q.Parameters.AddWithValue(minAgeSinceHeartbeat);
        var pools = new List<string>();
        await using (var r = await q.ExecuteReaderAsync()) while (await r.ReadAsync()) pools.Add(r.GetString(0));
        var all = new List<(Guid, string)>();
        foreach (var p in pools) all.AddRange(await DrainConnectionAsync(p, "prior instance reconciled: " + evidence));
        return all;
    }

    static async Task LockSiteAsync(NpgsqlConnection c, NpgsqlTransaction tx) => await LockPoolAsync(c, tx, SitePool);

    static async Task LockPoolAsync(NpgsqlConnection c, NpgsqlTransaction tx, string pool)
    {
        await using var lk = new NpgsqlCommand("SELECT 1 FROM credit_pools WHERE pool_id = $1 FOR UPDATE", c, tx);
        lk.Parameters.AddWithValue(pool); await lk.ExecuteNonQueryAsync();
    }

    public async Task HeartbeatAsync()
    {
        await using var c = await _db.OpenConnectionAsync();
        await using var q = new NpgsqlCommand("UPDATE credit_instances SET heartbeat_at = clock_timestamp() WHERE instance_id=$1", c);
        q.Parameters.AddWithValue(InstanceId); await q.ExecuteNonQueryAsync();
    }

    public async Task<(long cap, long reserved, long charged)> PoolAsync(string pool)
    {
        await using var c = await _db.OpenConnectionAsync();
        await using var q = new NpgsqlCommand("SELECT cap, reserved, charged FROM credit_pools WHERE pool_id=$1", c);
        q.Parameters.AddWithValue(pool);
        await using var r = await q.ExecuteReaderAsync();
        return await r.ReadAsync() ? (r.GetInt64(0), r.GetInt64(1), r.GetInt64(2)) : (0, 0, 0);
    }
}
