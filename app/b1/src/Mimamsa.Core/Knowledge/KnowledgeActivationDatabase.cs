// C16 Tranche B CP-1: the activation journal's DATABASE commit domain (B06 IActivationDatabase) wired to the B03
// knowledge rows. DB_APPLIED for KNOWLEDGE, in ONE transaction:
//   - promote kr_<n>_staging to kr_<n> if the generation's rows were staged and not yet promoted (B03 PromoteAsync rule);
//   - point every `knowledge` view at kr_<n> (a rollback re-points at an earlier, still-present kr_<m>);
//   - the B06 knowledge_head view and the RELEASE_ACTIVATION publication row keyed by txn (as PgActivationDatabase).
// Every effect is idempotent, so recovery can replay it (B06 roll-forward). The generation -> release sequence map is
// the generation.json release_sequence (kr_<n> is named by it, B03). Runs on the activation tool's advisory-lock session.
// Development / CP-1 fixture use only; the operational migration and app search_path switch are OG-3 / B07.
using System.Text;
using System.Text.RegularExpressions;
using Mimamsa.Core.Activation;
using Npgsql;

namespace Mimamsa.Core.Knowledge;

public sealed partial class KnowledgeActivationDatabase : IActivationDatabase, IStagedKnowledgeEvidence
{
    /// C16-CP1-02: the generation's kr_<n> (or kr_<n>_staging) holds exactly the rows the marker records: the schema
    /// names match, every allowlisted table not in the evidence is empty, and every recorded table's ordered canonical
    /// export has the recorded row count and rows_sha256 (B03 ExportAsync, the loader's own verification form).
    public string? StagedEvidenceProblem(string generation, System.Text.Json.Nodes.JsonObject db)
    {
        var n = _sequenceOf(generation);
        string staging = KnowledgeAllowlist.StagingSchema(n), active = KnowledgeAllowlist.ActiveSchema(n);
        if ((string?)db["staging_schema"] != staging || (string?)db["active_schema"] != active) return "staged DB evidence names other kr_ schemas";
        var c = _conn();
        using var tx = c.BeginTransaction(System.Data.IsolationLevel.RepeatableRead);
        string? schema = SchemaExists(c, tx, active) ? active : SchemaExists(c, tx, staging) ? staging : null;
        if (schema is null) return $"no staged knowledge rows for {generation} ({staging} / {active} absent)";
        var want = db["tables"]!.AsObject();
        foreach (var t in KnowledgeAllowlist.Tables)
        {
            var (bytes, count) = KnowledgeRowLoader.ExportAsync(c, tx, schema, t).GetAwaiter().GetResult();
            var sha = Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(bytes)).ToLowerInvariant();
            if (want[t.Table] is not System.Text.Json.Nodes.JsonObject w) { if (count != 0) return $"{schema}.{t.Table} holds rows the staging evidence does not record"; continue; }
            if (count != (long)w["rows"]! || sha != (string?)w["rows_sha256"]) return $"{schema}.{t.Table} differs from the staging evidence";
        }
        tx.Commit();
        return null;
    }

    readonly Func<NpgsqlConnection> _conn;
    readonly Func<string, long> _sequenceOf;
    readonly string _schema;
    const long LoadLockKey = 0x4B52_4C4F_4144;  // the B03 loader's lock: never repoint while a load runs

    [GeneratedRegex("^[a-z_][a-z0-9_]{0,40}$")] private static partial Regex SchemaRx();

    public KnowledgeActivationDatabase(Func<NpgsqlConnection> connection, Func<string, long> releaseSequenceOf, string schema = "site_activation")
    {
        if (!SchemaRx().IsMatch(schema)) throw new ArgumentException("schema name");
        _conn = connection; _sequenceOf = releaseSequenceOf; _schema = schema;
    }

    static string Q(string ident) => SchemaDump.Q(ident);

    /// Install step: the activation tables, and the knowledge views on the initial generation (whose rows must already
    /// be promoted, or staged and then promoted here).
    public void EnsureSchema(string initialKnowledge)
    {
        new PgActivationDatabase(_conn, _schema).EnsureSchema(initialKnowledge);
        var c = _conn();
        using var tx = c.BeginTransaction();
        PointKnowledge(c, tx, initialKnowledge);
        tx.Commit();
    }

    bool SchemaExists(NpgsqlConnection c, NpgsqlTransaction tx, string schema)
    {
        using var q = new NpgsqlCommand("SELECT 1 FROM pg_namespace WHERE nspname = $1", c, tx);
        q.Parameters.AddWithValue(schema);
        return q.ExecuteScalar() is not null;
    }

    void PointKnowledge(NpgsqlConnection c, NpgsqlTransaction tx, string generation)
    {
        SiteLayout.CheckId(generation);
        var n = _sequenceOf(generation);
        string staging = KnowledgeAllowlist.StagingSchema(n), active = KnowledgeAllowlist.ActiveSchema(n);
        using (var lk = new NpgsqlCommand("SELECT pg_advisory_xact_lock($1)", c, tx)) { lk.Parameters.AddWithValue(LoadLockKey); lk.ExecuteNonQuery(); }
        var sql = new StringBuilder();
        if (!SchemaExists(c, tx, active))
        {
            if (!SchemaExists(c, tx, staging)) throw new ActivationRefused("KR_NOT_LOADED", $"no verified knowledge rows for {generation} (kr_{n})");
            sql.Append($"ALTER SCHEMA {Q(staging)} RENAME TO {Q(active)};\n");
        }
        sql.Append("CREATE SCHEMA IF NOT EXISTS knowledge;\nREVOKE ALL ON SCHEMA knowledge FROM PUBLIC;\n");
        foreach (var t in KnowledgeAllowlist.Tables)
            sql.Append($"CREATE OR REPLACE VIEW knowledge.{Q(t.Table)} AS SELECT {string.Join(",", t.Columns.Select(x => Q(x.Name)))} FROM {Q(active)}.{Q(t.Table)};\n");
        sql.Append($"CREATE OR REPLACE VIEW {_schema}.knowledge_head AS SELECT '{generation}'::text AS generation;\n");
        using var cmd = new NpgsqlCommand(sql.ToString(), c, tx);
        cmd.ExecuteNonQuery();
    }

    void Publication(NpgsqlConnection c, NpgsqlTransaction tx, PublicationRow r)
    {
        using var cmd = new NpgsqlCommand($"INSERT INTO {_schema}.release_activation(txn_id, release, channel, target) VALUES (@t, @r, @ch, @g) ON CONFLICT (txn_id) DO NOTHING", c, tx);
        cmd.Parameters.AddWithValue("t", r.TxnId); cmd.Parameters.AddWithValue("r", r.Release); cmd.Parameters.AddWithValue("ch", r.Channel); cmd.Parameters.AddWithValue("g", r.Target);
        cmd.ExecuteNonQuery();
    }

    public void Apply(string txnId, string target, string to)
    {
        var c = _conn();
        using var tx = c.BeginTransaction();
        if (target == "KNOWLEDGE") PointKnowledge(c, tx, to);
        Publication(c, tx, new PublicationRow(txnId, to, "RELEASE_ACTIVATION", target));
        tx.Commit();
    }

    public void Reconcile(string knowledge, IEnumerable<PublicationRow> committed)
    {
        var c = _conn();
        using var tx = c.BeginTransaction();
        PointKnowledge(c, tx, knowledge);
        foreach (var r in committed) Publication(c, tx, r);
        tx.Commit();
    }

    public string? Views() => new PgActivationDatabase(_conn, _schema).Views();

    /// The kr_<n> schema the `knowledge` views currently read (null if none).
    public string? KnowledgeSchema()
    {
        using var cmd = new NpgsqlCommand("""
            SELECT DISTINCT n.nspname FROM pg_depend d JOIN pg_rewrite r ON r.oid = d.objid JOIN pg_class v ON v.oid = r.ev_class
              JOIN pg_namespace vn ON vn.oid = v.relnamespace JOIN pg_class t ON t.oid = d.refobjid JOIN pg_namespace n ON n.oid = t.relnamespace
             WHERE vn.nspname = 'knowledge' AND n.nspname <> 'knowledge'
            """, _conn());
        using var rd = cmd.ExecuteReader();
        var found = new List<string>();
        while (rd.Read()) found.Add(rd.GetString(0));
        return found.Count == 1 ? found[0] : found.Count == 0 ? null : throw new InvalidOperationException("knowledge views read more than one schema");
    }

    public int PublicationCount() => new PgActivationDatabase(_conn, _schema).PublicationCount();
    public byte[] Backup() => throw new NotSupportedException("PostgreSQL backups are B08");
    public void Restore(byte[] backup) => throw new NotSupportedException("PostgreSQL restore is B08");
}
