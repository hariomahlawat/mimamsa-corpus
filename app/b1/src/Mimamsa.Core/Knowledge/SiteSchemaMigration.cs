// C16 B03 / I-3 (SG-2): the first schema migration, ADDITIVE and COPY-AND-VERIFY. It introduces the `site` and
// `knowledge` schemas beside the existing default-schema (`public`) tables:
//   - every site table of the old schema (users, sessions, audit, withdrawals, vault copies, serving policy, studio_*,
//     credit_*, graph_edge_reviews and any other non-accelerator table) is COPIED into `site` with its columns, defaults,
//     CHECK/PRIMARY KEY/UNIQUE constraints, indexes, foreign keys (re-pointed at the copies) and its own sequences set to
//     the old values; nothing is moved, altered or dropped in the old schema;
//   - the knowledge accelerators (graph_generation, graph_nodes, graph_edges) are left in place: knowledge rows are
//     loaded per release into kr_<n> by the restricted loader and rebuilt from records, never migrated;
//   - one transaction, writers blocked (SHARE locks) for its duration: a crash at any point leaves no new schema;
//   - verified inside the same transaction by ordered dumps (column definitions, constraints and every row, in
//     code-point order) and row counts, old against new, and recorded in site.schema_migrations;
//   - the application stays compatible: it keeps running unchanged against the old tables (default search_path) until
//     a later application release switches to `site`.
// Rollback drops the new schemas only (site, knowledge, kr_*), refuses when it would lose writes made to `site` since
// the migration, and proves the old schema unchanged by an ordered dump. Run ONLY on cloned databases until the owner
// gate OG-3; this code never runs automatically at application start.
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Npgsql;

namespace Mimamsa.Core.Knowledge;

public sealed record MigrationTable(string Table, long Rows, string OldDigest, string NewDigest);
public sealed record MigrationReport(string Version, string OldSchema, IReadOnlyList<MigrationTable> Tables, IReadOnlyList<string> LeftInPlace);

public sealed class SiteMigrationException(string code, string message) : Exception($"{code}: {message}")
{
    public string Code { get; } = code;
}

public sealed class SiteSchemaMigration(NpgsqlDataSource db)
{
    public const string Version = "c16-b03-site-v1";
    public const string OldSchema = "public", SiteSchema = "site", KnowledgeSchema = "knowledge";
    /// Knowledge accelerators: rebuilt from records, never migrated (left untouched in the old schema).
    public static readonly string[] AcceleratorTables = ["graph_generation", "graph_nodes", "graph_edges"];
    const long MigrationLockKey = 0x5349_5445_4D49_47;  // "SITEMIG"

    /// Test hook (crash injection): called after each table is copied, inside the migration transaction.
    public Func<string, NpgsqlConnection, Task>? AfterTableCopied { get; init; }

    static string Q(string s) => SchemaDump.Q(s);

    static async Task<bool> SchemaExists(NpgsqlConnection c, NpgsqlTransaction tx, string s)
    {
        await using var q = new NpgsqlCommand("SELECT 1 FROM pg_namespace WHERE nspname = $1", c, tx);
        q.Parameters.AddWithValue(s);
        return await q.ExecuteScalarAsync() is not null;
    }

    static async Task Exec(NpgsqlConnection c, NpgsqlTransaction tx, string sql, CancellationToken ct = default)
    {
        await using var cmd = new NpgsqlCommand(sql, c, tx);
        await cmd.ExecuteNonQueryAsync(ct);
    }

    static async Task<List<string>> BaseTables(NpgsqlConnection c, NpgsqlTransaction? tx, string schema)
    {
        var list = new List<string>();
        await using var q = new NpgsqlCommand("""
            SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = $1 AND c.relkind IN ('r','p') AND NOT c.relispartition ORDER BY c.relname COLLATE "C"
            """, c, tx);
        q.Parameters.AddWithValue(schema);
        await using var r = await q.ExecuteReaderAsync();
        while (await r.ReadAsync()) list.Add(r.GetString(0));
        return list;
    }

    /// Ordered dump of one table's data and definition, independent of the schema it lives in: columns (name, type,
    /// NOT NULL), constraints (schema names removed, so a foreign key to the copy compares equal) and every row as text
    /// in code-point order.
    public static async Task<(long Rows, string Digest)> TableDigestAsync(NpgsqlConnection c, NpgsqlTransaction? tx, string schema, string table)
    {
        var fq = Q(schema) + "." + Q(table);
        var sb = new StringBuilder();
        async Task Lines(string sql)
        {
            await using var q = new NpgsqlCommand(sql, c, tx);
            q.Parameters.AddWithValue(fq);
            await using var r = await q.ExecuteReaderAsync();
            while (await r.ReadAsync()) sb.Append(r.IsDBNull(0) ? "" : r.GetString(0)).Append('\n');
        }
        await Lines("""
            SELECT a.attname || ' ' || format_type(a.atttypid, a.atttypmod) || CASE WHEN a.attnotnull THEN ' NOT NULL' ELSE '' END
            FROM pg_attribute a WHERE a.attrelid = $1::regclass AND a.attnum > 0 AND NOT a.attisdropped ORDER BY a.attnum
            """);
        await Lines("""
            SELECT x FROM (SELECT contype::text || ' ' || replace(replace(pg_get_constraintdef(oid), 'REFERENCES public.', 'REFERENCES '), 'REFERENCES site.', 'REFERENCES ') AS x
                           FROM pg_constraint WHERE conrelid = $1::regclass) s ORDER BY x COLLATE "C"
            """);
        sb.Append("--rows\n");
        long rows = 0;
        await using (var q = new NpgsqlCommand($"SELECT x FROM (SELECT t::text AS x FROM {fq} t) s ORDER BY x COLLATE \"C\"", c, tx))
        await using (var r = await q.ExecuteReaderAsync())
            while (await r.ReadAsync()) { sb.Append(r.GetString(0)).Append('\n'); rows++; }
        return (rows, Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(sb.ToString()))).ToLowerInvariant());
    }

    public async Task<string> StatusAsync()
    {
        await using var c = await db.OpenConnectionAsync();
        await using var tx = await c.BeginTransactionAsync();
        if (!await SchemaExists(c, tx, SiteSchema)) return "NOT_APPLIED";
        await using var q = new NpgsqlCommand("SELECT version FROM site.schema_migrations WHERE version = $1", c, tx);
        q.Parameters.AddWithValue(Version);
        return await q.ExecuteScalarAsync() is null ? "FOREIGN_SITE_SCHEMA" : "APPLIED";
    }

    public async Task<MigrationReport> ForwardAsync(CancellationToken ct = default)
    {
        await using var c = await db.OpenConnectionAsync(ct);
        await using var tx = await c.BeginTransactionAsync(ct);
        await using (var lk = new NpgsqlCommand("SELECT pg_advisory_xact_lock($1)", c, tx)) { lk.Parameters.AddWithValue(MigrationLockKey); await lk.ExecuteNonQueryAsync(ct); }
        if (await SchemaExists(c, tx, SiteSchema)) throw new SiteMigrationException("SITE_MIGRATION_ALREADY_APPLIED", "schema site exists");
        if (await SchemaExists(c, tx, KnowledgeSchema)) throw new SiteMigrationException("SITE_MIGRATION_KNOWLEDGE_EXISTS", "schema knowledge exists");

        var all = await BaseTables(c, tx, OldSchema);
        var tables = all.Where(t => !AcceleratorTables.Contains(t)).ToList();
        var left = all.Where(t => AcceleratorTables.Contains(t)).ToList();
        if (tables.Count > 0)
            await Exec(c, tx, $"LOCK TABLE {string.Join(",", tables.Select(t => Q(OldSchema) + "." + Q(t)))} IN SHARE MODE", ct);

        await Exec(c, tx, $"CREATE SCHEMA {SiteSchema}; REVOKE ALL ON SCHEMA {SiteSchema} FROM PUBLIC; CREATE SCHEMA {KnowledgeSchema}; REVOKE ALL ON SCHEMA {KnowledgeSchema} FROM PUBLIC;", ct);
        foreach (var t in tables)
        {
            await Exec(c, tx, $"CREATE TABLE {SiteSchema}.{Q(t)} (LIKE {Q(OldSchema)}.{Q(t)} INCLUDING ALL); INSERT INTO {SiteSchema}.{Q(t)} SELECT * FROM {Q(OldSchema)}.{Q(t)};", ct);
            if (AfterTableCopied is not null) await AfterTableCopied(t, c);
        }

        // sequences: the copies get their own, positioned exactly where the old ones are (the old ones are not touched)
        var seqs = new List<(string table, string column, string oldSeq, bool identity)>();
        await using (var q = new NpgsqlCommand("""
            SELECT c.relname, a.attname, pg_get_serial_sequence(quote_ident(n.nspname) || '.' || quote_ident(c.relname), a.attname), a.attidentity <> ''
            FROM pg_attribute a JOIN pg_class c ON c.oid = a.attrelid JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = $1 AND c.relname = ANY($2) AND a.attnum > 0 AND NOT a.attisdropped
              AND pg_get_serial_sequence(quote_ident(n.nspname) || '.' || quote_ident(c.relname), a.attname) IS NOT NULL
            ORDER BY 1, 2
            """, c, tx))
        {
            q.Parameters.AddWithValue(OldSchema); q.Parameters.AddWithValue(tables.ToArray());
            await using var r = await q.ExecuteReaderAsync(ct);
            while (await r.ReadAsync(ct)) seqs.Add((r.GetString(0), r.GetString(1), r.GetString(2), r.GetBoolean(3)));
        }
        foreach (var (t, col, oldSeq, identity) in seqs)
        {
            string newSeq;
            if (identity)
            {
                await using var g = new NpgsqlCommand("SELECT pg_get_serial_sequence($1, $2)", c, tx);
                g.Parameters.AddWithValue($"{SiteSchema}.{Q(t)}"); g.Parameters.AddWithValue(col);
                newSeq = (string)(await g.ExecuteScalarAsync(ct))!;
            }
            else
            {
                var seqName = oldSeq.Contains('.') ? oldSeq[(oldSeq.LastIndexOf('.') + 1)..].Trim('"') : oldSeq;
                newSeq = $"{SiteSchema}.{Q(seqName)}";
                await using var tq = new NpgsqlCommand("SELECT format_type(seqtypid, NULL) FROM pg_sequence WHERE seqrelid = $1::regclass", c, tx);
                tq.Parameters.AddWithValue(oldSeq);
                var type = (string)(await tq.ExecuteScalarAsync(ct))!;
                await Exec(c, tx, $"CREATE SEQUENCE {newSeq} AS {type}; ALTER TABLE {SiteSchema}.{Q(t)} ALTER COLUMN {Q(col)} SET DEFAULT nextval('{newSeq.Replace("'", "''")}'::regclass); ALTER SEQUENCE {newSeq} OWNED BY {SiteSchema}.{Q(t)}.{Q(col)};", ct);
            }
            await Exec(c, tx, $"SELECT setval('{newSeq.Replace("'", "''")}'::regclass, s.last_value, s.is_called) FROM {oldSeq} s", ct);
        }

        // foreign keys (LIKE does not copy them): re-pointed at the copies; a reference to a table that is not copied is refused
        var fks = new List<(string table, string name, string def)>();
        await Exec(c, tx, "SET LOCAL search_path TO pg_catalog", ct);   // so pg_get_constraintdef qualifies every referenced table
        await using (var q = new NpgsqlCommand("""
            SELECT c.relname, k.conname, pg_get_constraintdef(k.oid), rn.nspname, rc.relname
            FROM pg_constraint k JOIN pg_class c ON c.oid = k.conrelid JOIN pg_namespace n ON n.oid = c.relnamespace
            JOIN pg_class rc ON rc.oid = k.confrelid JOIN pg_namespace rn ON rn.oid = rc.relnamespace
            WHERE k.contype = 'f' AND n.nspname = $1 AND c.relname = ANY($2) ORDER BY 1, 2
            """, c, tx))
        {
            q.Parameters.AddWithValue(OldSchema); q.Parameters.AddWithValue(tables.ToArray());
            await using var r = await q.ExecuteReaderAsync(ct);
            while (await r.ReadAsync(ct))
            {
                if (r.GetString(3) != OldSchema || !tables.Contains(r.GetString(4)))
                    throw new SiteMigrationException("SITE_MIGRATION_FOREIGN_REFERENCE", $"{r.GetString(0)} references a table that is not migrated");
                fks.Add((r.GetString(0), r.GetString(1), r.GetString(2)));
            }
        }
        foreach (var (t, name, def) in fks)
        {
            var re = def.Replace($"REFERENCES {OldSchema}.", $"REFERENCES {SiteSchema}.", StringComparison.Ordinal);
            if (re == def) throw new SiteMigrationException("SITE_MIGRATION_FOREIGN_REFERENCE", $"cannot re-point {name}");
            await Exec(c, tx, $"ALTER TABLE {SiteSchema}.{Q(t)} ADD CONSTRAINT {Q(name)} {re}", ct);
        }
        await Exec(c, tx, "SET LOCAL search_path TO DEFAULT", ct);

        // verify by ordered dumps and counts, old against new, before anything is committed
        var report = new List<MigrationTable>();
        foreach (var t in tables)
        {
            var (oldRows, oldDigest) = await TableDigestAsync(c, tx, OldSchema, t);
            var (newRows, newDigest) = await TableDigestAsync(c, tx, SiteSchema, t);
            if (oldRows != newRows || oldDigest != newDigest)
                throw new SiteMigrationException("SITE_MIGRATION_VERIFY_FAILED", $"{t}: copy differs from the old table ({newRows}/{oldRows} rows)");
            report.Add(new MigrationTable(t, newRows, oldDigest, newDigest));
        }
        var result = new MigrationReport(Version, OldSchema, report, left);
        await Exec(c, tx, $"CREATE TABLE {SiteSchema}.schema_migrations(version text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now(), old_schema text NOT NULL, report jsonb NOT NULL)", ct);
        await using (var ins = new NpgsqlCommand($"INSERT INTO {SiteSchema}.schema_migrations(version, old_schema, report) VALUES ($1, $2, $3::jsonb)", c, tx))
        {
            ins.Parameters.AddWithValue(Version); ins.Parameters.AddWithValue(OldSchema); ins.Parameters.AddWithValue(JsonSerializer.Serialize(result));
            await ins.ExecuteNonQueryAsync(ct);
        }
        await tx.CommitAsync(ct);
        return result;
    }

    /// Compatibility-window check: the tables whose copy no longer equals the old table (either side written since).
    public async Task<IReadOnlyList<string>> DivergedTablesAsync()
    {
        await using var c = await db.OpenConnectionAsync();
        var report = await ReportAsync(c, null) ?? throw new SiteMigrationException("SITE_MIGRATION_NOT_APPLIED", "no migration record");
        var diverged = new List<string>();
        foreach (var t in report.Tables)
            if ((await TableDigestAsync(c, null, OldSchema, t.Table)).Digest != (await TableDigestAsync(c, null, SiteSchema, t.Table)).Digest) diverged.Add(t.Table);
        return diverged;
    }

    static async Task<MigrationReport?> ReportAsync(NpgsqlConnection c, NpgsqlTransaction? tx)
    {
        await using var q = new NpgsqlCommand("SELECT report::text FROM site.schema_migrations WHERE version = $1", c, tx);
        q.Parameters.AddWithValue(Version);
        try { return await q.ExecuteScalarAsync() is string s ? JsonSerializer.Deserialize<MigrationReport>(s) : null; }
        catch (PostgresException e) when (e.SqlState is "42P01" or "3F000") { return null; }
    }

    /// Rollback: switch back to the old schema by dropping the new schemas (site, knowledge and any kr_ schema). Refused
    /// when `site` was written since the migration (those writes would be lost). The old schema is proved unchanged.
    public async Task RollbackAsync(CancellationToken ct = default)
    {
        await using var c = await db.OpenConnectionAsync(ct);
        await using var tx = await c.BeginTransactionAsync(ct);
        await using (var lk = new NpgsqlCommand("SELECT pg_advisory_xact_lock($1)", c, tx)) { lk.Parameters.AddWithValue(MigrationLockKey); await lk.ExecuteNonQueryAsync(ct); }
        if (!await SchemaExists(c, tx, SiteSchema)) throw new SiteMigrationException("SITE_MIGRATION_NOT_APPLIED", "schema site does not exist");
        var report = await ReportAsync(c, tx) ?? throw new SiteMigrationException("SITE_MIGRATION_NOT_APPLIED", "schema site was not created by this migration");
        foreach (var t in report.Tables)
            if ((await TableDigestAsync(c, tx, SiteSchema, t.Table)).Digest != t.NewDigest)
                throw new SiteMigrationException("SITE_ROLLBACK_WOULD_LOSE_WRITES", $"{t.Table} was written in schema site since the migration");
        var before = await SchemaDump.DumpAsync(c, OldSchema, tx);
        var drop = new List<string> { SiteSchema, KnowledgeSchema };
        foreach (var s in await SchemaDump.SchemasAsync(c, tx))
            if (KnowledgeAllowlist.ActivePattern().IsMatch(s) || KnowledgeAllowlist.StagingPattern().IsMatch(s)) drop.Add(s);
        await Exec(c, tx, string.Join(";", drop.Select(s => $"DROP SCHEMA IF EXISTS {Q(s)} CASCADE")), ct);
        var after = await SchemaDump.DumpAsync(c, OldSchema, tx);
        if (!before.SequenceEqual(after)) throw new SiteMigrationException("SITE_ROLLBACK_OLD_SCHEMA_CHANGED", "the old schema changed during rollback");
        await tx.CommitAsync(ct);
    }
}
