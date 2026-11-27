// C16 B06: PostgreSQL commit domain and advisory lock for the activation journal.
// - PgAdvisoryLock: a session-level pg_try_advisory_lock held on one dedicated connection for the writer's lifetime.
//   PostgreSQL releases it when the session ends (process death, network loss, pg_terminate_backend). Verify() checks
//   on that same session that the lock is still held, so "lock loss (database session dropped)" surfaces as
//   LOCK_LOST at the next effect. On a takeover (dead or heartbeat-stale file holder) the stale holder's backend is
//   terminated first.
// - PgActivationDatabase: DB_APPLIED in ONE transaction on the lock session: the knowledge head view is replaced and
//   the RELEASE_ACTIVATION publication row is inserted keyed by txn (ON CONFLICT DO NOTHING). Running the effect on the
//   advisory-lock session means a writer whose session was dropped cannot apply anything.
//   The real view swap to kr_<n> schemas arrives with B03; this core keeps a generation-head view in its own schema.
using System.Text.RegularExpressions;
using Npgsql;

namespace Mimamsa.Core.Activation;

public sealed class PgAdvisoryLock : IExternalWriterLock
{
    readonly string _cs;
    readonly long _key;
    NpgsqlConnection? _conn;
    public PgAdvisoryLock(string connectionString, long key = 0x4D494D5341435456 /* "MIMSACTV" */)
    {
        // A dedicated, unpooled session: the lock lives exactly as long as this physical connection.
        _cs = new NpgsqlConnectionStringBuilder(connectionString) { Pooling = false }.ConnectionString;
        _key = key;
    }

    public NpgsqlConnection Connection => _conn ?? throw new InvalidOperationException("advisory lock not held");

    public bool TryAcquire(bool takeover)
    {
        _conn?.Dispose();
        _conn = new NpgsqlConnection(_cs);
        _conn.Open();
        if (Try()) return true;
        if (!takeover) { _conn.Dispose(); _conn = null; return false; }
        using (var k = new NpgsqlCommand("SELECT pg_terminate_backend(l.pid) FROM pg_locks l WHERE l.locktype = 'advisory' AND l.granted " +
               "AND ((l.classid::bigint << 32) | l.objid::bigint) = @k AND l.pid <> pg_backend_pid()", _conn))
        {
            k.Parameters.AddWithValue("k", _key);
            k.ExecuteNonQuery();
        }
        for (int i = 0; i < 50; i++) { if (Try()) return true; Thread.Sleep(100); }
        _conn.Dispose(); _conn = null;
        return false;
    }

    bool Try()
    {
        using var c = new NpgsqlCommand("SELECT pg_try_advisory_lock(@k)", _conn);
        c.Parameters.AddWithValue("k", _key);
        return (bool)c.ExecuteScalar()!;
    }

    public void Verify()
    {
        if (_conn is null) throw new InvalidOperationException("no lock session");
        using var c = new NpgsqlCommand("SELECT count(*) FROM pg_locks WHERE locktype = 'advisory' AND granted AND pid = pg_backend_pid() " +
                                        "AND ((classid::bigint << 32) | objid::bigint) = @k", _conn);
        c.Parameters.AddWithValue("k", _key);
        if ((long)c.ExecuteScalar()! < 1) throw new InvalidOperationException("advisory lock not held");
    }

    public int BackendPid
    {
        get { using var c = new NpgsqlCommand("SELECT pg_backend_pid()", Connection); return (int)c.ExecuteScalar()!; }
    }

    public void Dispose() { _conn?.Dispose(); _conn = null; }
}

public sealed class PgActivationDatabase : IActivationDatabase
{
    readonly Func<NpgsqlConnection> _conn;
    readonly string _schema;
    static readonly Regex SchemaRx = new("^[a-z_][a-z0-9_]{0,40}$", RegexOptions.CultureInvariant);

    /// `connection` returns the advisory-lock session (effects run on it) or, for readers, any open connection.
    public PgActivationDatabase(Func<NpgsqlConnection> connection, string schema = "site_activation")
    {
        if (!SchemaRx.IsMatch(schema)) throw new ArgumentException("schema name");
        _conn = connection; _schema = schema;
    }

    public void EnsureSchema(string initialKnowledge)
    {
        SiteLayout.CheckId(initialKnowledge);
        using var c = new NpgsqlCommand($"""
            CREATE SCHEMA IF NOT EXISTS {_schema};
            CREATE TABLE IF NOT EXISTS {_schema}.release_activation(txn_id text PRIMARY KEY, release text NOT NULL,
              channel text NOT NULL CHECK (channel = 'RELEASE_ACTIVATION'), target text NOT NULL CHECK (target IN ('KNOWLEDGE','MODELS')),
              recorded_at timestamptz NOT NULL DEFAULT now());
            CREATE TABLE IF NOT EXISTS {_schema}.site_rows(name text PRIMARY KEY, value bigint NOT NULL);
            INSERT INTO {_schema}.site_rows VALUES ('users', 1) ON CONFLICT DO NOTHING;
            """, _conn());
        c.ExecuteNonQuery();
        using var v = new NpgsqlCommand($"SELECT to_regclass('{_schema}.knowledge_head') IS NULL", _conn());
        if ((bool)v.ExecuteScalar()!) SetView(initialKnowledge, null);
    }

    void SetView(string gen, NpgsqlTransaction? tx)
    {
        SiteLayout.CheckId(gen);   // safe identifier: [A-Za-z0-9._-] only, so the literal cannot break out
        using var c = new NpgsqlCommand($"CREATE OR REPLACE VIEW {_schema}.knowledge_head AS SELECT '{gen}'::text AS generation", _conn(), tx);
        c.ExecuteNonQuery();
    }

    public void Apply(string txnId, string target, string to)
    {
        var conn = _conn();
        using var tx = conn.BeginTransaction();
        if (target == "KNOWLEDGE") SetView(to, tx);
        using (var c = new NpgsqlCommand($"INSERT INTO {_schema}.release_activation(txn_id, release, channel, target) VALUES (@t, @r, 'RELEASE_ACTIVATION', @g) ON CONFLICT (txn_id) DO NOTHING", conn, tx))
        {
            c.Parameters.AddWithValue("t", txnId); c.Parameters.AddWithValue("r", to); c.Parameters.AddWithValue("g", target);
            c.ExecuteNonQuery();
        }
        tx.Commit();
    }

    public void Reconcile(string knowledge, IEnumerable<PublicationRow> committed)
    {
        var conn = _conn();
        using var tx = conn.BeginTransaction();
        SetView(knowledge, tx);
        foreach (var r in committed)
        {
            using var c = new NpgsqlCommand($"INSERT INTO {_schema}.release_activation(txn_id, release, channel, target) VALUES (@t, @r, @ch, @g) ON CONFLICT (txn_id) DO NOTHING", conn, tx);
            c.Parameters.AddWithValue("t", r.TxnId); c.Parameters.AddWithValue("r", r.Release); c.Parameters.AddWithValue("ch", r.Channel); c.Parameters.AddWithValue("g", r.Target);
            c.ExecuteNonQuery();
        }
        tx.Commit();
    }

    public string? Views()
    {
        using var c = new NpgsqlCommand($"SELECT generation FROM {_schema}.knowledge_head", _conn());
        return (string?)c.ExecuteScalar();
    }

    public int PublicationCount()
    {
        using var c = new NpgsqlCommand($"SELECT count(*) FROM {_schema}.release_activation", _conn());
        return (int)(long)c.ExecuteScalar()!;
    }

    public byte[] Backup() => throw new NotSupportedException("PostgreSQL backups are B08 (encrypted offline backup), not the activation core");
    public void Restore(byte[] backup) => throw new NotSupportedException("PostgreSQL restore is B08");
}
