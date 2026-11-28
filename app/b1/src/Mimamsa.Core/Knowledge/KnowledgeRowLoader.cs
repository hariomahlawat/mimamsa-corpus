// C16 B03: the site's restricted knowledge-row loader (arch §7, interface B03 §4). There is no PostgreSQL archive
// restore: knowledge tables are filled only by this deterministic, validated row load.
//   1. Typed reading BEFORE COPY (KnowledgeRows.ReadRowFile): any issue rejects the whole component.
//   2. Application DDL (activator role) creates a fresh `kr_<n>_staging` with the allowlisted tables only (no triggers,
//      no rules) and grants the loader role exactly USAGE on that schema and INSERT on its tables.
//   3. The loader role (`mimamsa_kr_loader`: NOSUPERUSER NOCREATEROLE NOCREATEDB NOREPLICATION NOBYPASSRLS NOINHERIT,
//      no memberships, no CREATE or TEMP on the database, no access to site/knowledge/other kr_ schemas; checked
//      before every load, fail closed) loads with parameterised binary `COPY ... FROM STDIN` into named allowlisted
//      tables. Values are never interpolated into SQL; table and column names come only from the application allowlist.
//   4. The loader's grants are revoked; the activator recounts, recomputes rows_sha256 from an ordered canonical export
//      and re-derives every row from the authoritative records (ROWS_REDERIVE_COMPARE).
//   5. Any failure drops the staging schema; nothing else is touched (site and the active kr_ schema stay
//      byte-identical, proved by ordered dumps in the tests).
// Promotion (`PromoteAsync`, at DB_APPLIED, B06) renames kr_<n>_staging to kr_<n> and repoints the `knowledge` views in
// one transaction.
using System.Text;
using System.Text.Json.Nodes;
using System.Text.RegularExpressions;
using Npgsql;
using NpgsqlTypes;

namespace Mimamsa.Core.Knowledge;

/// One table as declared in the signed KNOWLEDGE_RELEASE.json (component `tables`).
public sealed record DeclaredTable(string Table, long RowCount, string RowsSha256);

public sealed class KnowledgeLoadRequest
{
    public required long ReleaseSequence { get; init; }
    /// table -> row-file bytes (already covered by the verified SHA256SUMS).
    public required IReadOnlyDictionary<string, byte[]> Files { get; init; }
    public required IReadOnlyList<DeclaredTable> Declared { get; init; }
    /// The generation's authoritative records, for ROWS_REDERIVE_COMPARE.
    public required KnowledgeSources Sources { get; init; }
}

public sealed record KnowledgeLoadResult(bool Ok, string StagingSchema, IReadOnlyList<RowIssue> Issues, IReadOnlyList<TableRows> Verified)
{
    public IEnumerable<string> Codes => Issues.Select(i => i.Code);
}

public sealed partial class KnowledgeRowLoader(NpgsqlDataSource activator, string loaderConnectionString)
{
    public string LoaderRole { get; init; } = KnowledgeAllowlist.LoaderRole;
    /// Test hook: called after every row written to COPY (crash, privilege-probe and interruption injection).
    public Func<string, long, Task>? OnRowWritten { get; init; }
    /// Test hook: called with the activator connection after COPY and before verification (tamper injection).
    public Func<NpgsqlConnection, string, Task>? BeforeVerify { get; init; }

    const long LoadLockKey = 0x4B52_4C4F_4144;  // "KRLOAD": one knowledge load at a time per database

    [GeneratedRegex("^[a-z_][a-z0-9_]{0,62}$")] private static partial Regex RoleName();

    static string Q(string ident) => SchemaDump.Q(ident);

    static string Short(string s) => s.Length <= 200 ? s : s[..200];

    public async Task<KnowledgeLoadResult> LoadAsync(KnowledgeLoadRequest req, CancellationToken ct = default)
    {
        var staging = KnowledgeAllowlist.StagingSchema(req.ReleaseSequence);
        if (!RoleName().IsMatch(LoaderRole)) throw new ArgumentException("loader role name");
        var issues = new List<RowIssue>();
        var verified = new List<TableRows>();
        await using var admin = await activator.OpenConnectionAsync(ct);
        await using (var lk = new NpgsqlCommand("SELECT pg_try_advisory_lock($1)", admin))
        {
            lk.Parameters.AddWithValue(LoadLockKey);
            if (await lk.ExecuteScalarAsync(ct) is not true)
                return new(false, staging, [new("KR_LOAD_BUSY", "another knowledge load holds the lock", staging)], []);
        }
        bool ok = false;
        try
        {
            // a staging schema left by an interrupted earlier attempt is never reused
            await DropStagingAsync(admin, staging, ct);

            var parsed = ValidateFiles(req, issues);
            if (issues.Count > 0) return new(false, staging, issues, []);

            if (await SchemaExistsAsync(admin, KnowledgeAllowlist.ActiveSchema(req.ReleaseSequence), ct))
            {
                issues.Add(new("KR_LOAD_TARGET_EXISTS", "this release's knowledge schema is already applied", KnowledgeAllowlist.ActiveSchema(req.ReleaseSequence)));
                return new(false, staging, issues, []);
            }
            issues.AddRange(await LoaderRoleIssuesAsync(admin, ct));
            if (issues.Count > 0) return new(false, staging, issues, []);

            await CreateStagingAsync(admin, staging, ct);
            await CopyAsync(staging, parsed, ct);
            await using (var rv = new NpgsqlCommand(
                $"REVOKE ALL ON ALL TABLES IN SCHEMA {Q(staging)} FROM {Q(LoaderRole)}; REVOKE ALL ON SCHEMA {Q(staging)} FROM {Q(LoaderRole)}", admin))
                await rv.ExecuteNonQueryAsync(ct);
            if (BeforeVerify is not null) await BeforeVerify(admin, staging);
            issues.AddRange(await VerifyAsync(admin, staging, req, verified, ct));
            ok = issues.Count == 0;
            return new(ok, staging, issues, ok ? verified : []);
        }
        catch (Exception e)
        {
            ok = false;
            issues.Add(new("KR_LOAD_INTERRUPTED", $"{e.GetType().Name}: {Short(e.Message)}", staging));
            return new(false, staging, issues, []);
        }
        finally
        {
            if (!ok)
            {
                try { await DropStagingAsync(admin, staging, CancellationToken.None); }
                catch (Exception e) { issues.Add(new("KR_STAGING_DROP_FAILED", Short(e.Message), staging)); }
            }
            try
            {
                await using var ul = new NpgsqlCommand("SELECT pg_advisory_unlock($1)", admin);
                ul.Parameters.AddWithValue(LoadLockKey);
                await ul.ExecuteScalarAsync(CancellationToken.None);
            }
            catch (Exception) { /* the session lock ends with the connection */ }
        }
    }

    static List<KnowledgeRows.ParsedRowFile> ValidateFiles(KnowledgeLoadRequest req, List<RowIssue> issues)
    {
        var parsed = new List<KnowledgeRows.ParsedRowFile>();
        var declared = new Dictionary<string, DeclaredTable>(StringComparer.Ordinal);
        foreach (var d in req.Declared)
        {
            if (KnowledgeAllowlist.Find(d.Table) is null) issues.Add(new("KR_ROWS_TABLE_NOT_ALLOWLISTED", "declared table not on the application's allowlist", d.Table));
            else if (!declared.TryAdd(d.Table, d)) issues.Add(new("KR_ROWS_ALLOWLIST", "table declared twice", d.Table));
        }
        foreach (var (table, bytes) in req.Files.OrderBy(f => f.Key, StringComparer.Ordinal))
        {
            var p = KnowledgeRows.ReadRowFile(table, bytes);
            issues.AddRange(p.Issues);
            if (p.Spec is not null && !declared.ContainsKey(table)) issues.Add(new("KR_ROWS_UNDECLARED", "row file not declared in the signed manifest", table));
            parsed.Add(p);
        }
        foreach (var t in declared.Keys.Where(t => !req.Files.ContainsKey(t)))
            issues.Add(new("KR_ROWS_FILE_MISSING", "declared table has no row file", t));
        return parsed;
    }

    static async Task<bool> SchemaExistsAsync(NpgsqlConnection c, string schema, CancellationToken ct)
    {
        await using var q = new NpgsqlCommand("SELECT 1 FROM pg_namespace WHERE nspname = $1", c);
        q.Parameters.AddWithValue(schema);
        return await q.ExecuteScalarAsync(ct) is not null;
    }

    static async Task DropStagingAsync(NpgsqlConnection admin, string staging, CancellationToken ct)
    {
        if (!KnowledgeAllowlist.StagingPattern().IsMatch(staging)) throw new ArgumentException("not a staging schema");
        await using var d = new NpgsqlCommand($"DROP SCHEMA IF EXISTS {Q(staging)} CASCADE", admin);
        await d.ExecuteNonQueryAsync(ct);
    }

    /// Startup recovery: drop every kr_<n>_staging left by an interrupted load (never user-visible; holds the load lock).
    public async Task<IReadOnlyList<string>> DropStaleStagingAsync(CancellationToken ct = default)
    {
        await using var admin = await activator.OpenConnectionAsync(ct);
        await using (var lk = new NpgsqlCommand("SELECT pg_try_advisory_lock($1)", admin))
        {
            lk.Parameters.AddWithValue(LoadLockKey);
            if (await lk.ExecuteScalarAsync(ct) is not true) return [];
        }
        var dropped = new List<string>();
        foreach (var s in await SchemaDump.SchemasAsync(admin))
            if (KnowledgeAllowlist.StagingPattern().IsMatch(s)) { await DropStagingAsync(admin, s, ct); dropped.Add(s); }
        await using (var ul = new NpgsqlCommand("SELECT pg_advisory_unlock($1)", admin)) { ul.Parameters.AddWithValue(LoadLockKey); await ul.ExecuteScalarAsync(ct); }
        return dropped;
    }

    /// The loader role must be exactly as restricted as the contract fixes it; a connection string pointing at any more
    /// privileged role is refused before anything is created (fail closed).
    async Task<List<RowIssue>> LoaderRoleIssuesAsync(NpgsqlConnection admin, CancellationToken ct)
    {
        var issues = new List<RowIssue>();
        void Bad(string why) => issues.Add(new("KR_LOADER_ROLE_PRIVILEGED", why, LoaderRole));
        await using (var lc = new NpgsqlConnection(loaderConnectionString))
        {
            await lc.OpenAsync(ct);
            await using var who = new NpgsqlCommand("SELECT current_user::text || '|' || session_user::text", lc);
            if ((string?)await who.ExecuteScalarAsync(ct) != $"{LoaderRole}|{LoaderRole}") Bad("the loader connection does not authenticate as the loader role");
        }
        await using var q = new NpgsqlCommand("""
            SELECT r.rolsuper, r.rolinherit, r.rolcreaterole, r.rolcreatedb, r.rolreplication, r.rolbypassrls,
                   (SELECT count(*) FROM pg_auth_members m WHERE m.member = r.oid),
                   has_database_privilege(r.oid, current_database(), 'CREATE'), has_database_privilege(r.oid, current_database(), 'TEMPORARY'),
                   (SELECT count(*) FROM pg_namespace n WHERE has_schema_privilege(r.oid, n.oid, 'CREATE')),
                   (SELECT count(*) FROM pg_namespace n WHERE (n.nspname IN ('site','knowledge') OR n.nspname LIKE 'kr\_%')
                        AND has_schema_privilege(r.oid, n.oid, 'USAGE')),
                   (SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
                     WHERE n.nspname NOT IN ('pg_catalog','information_schema') AND n.nspname NOT LIKE 'pg\_%' AND c.relkind IN ('r','p','v','m','f')
                       AND has_table_privilege(r.oid, c.oid, 'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER'))
            FROM pg_roles r WHERE r.rolname = $1
            """, admin);
        q.Parameters.AddWithValue(LoaderRole);
        await using var r = await q.ExecuteReaderAsync(ct);
        if (!await r.ReadAsync(ct)) { Bad("loader role does not exist"); return issues; }
        if (r.GetBoolean(0)) Bad("SUPERUSER");
        if (r.GetBoolean(1)) Bad("INHERIT");
        if (r.GetBoolean(2)) Bad("CREATEROLE");
        if (r.GetBoolean(3)) Bad("CREATEDB");
        if (r.GetBoolean(4)) Bad("REPLICATION");
        if (r.GetBoolean(5)) Bad("BYPASSRLS");
        if (r.GetInt64(6) > 0) Bad("member of another role (SET ROLE)");
        if (r.GetBoolean(7)) Bad("CREATE on the database");
        if (r.GetBoolean(8)) Bad("TEMPORARY on the database (temporary functions)");
        if (r.GetInt64(9) > 0) Bad("CREATE on a schema");
        if (r.GetInt64(10) > 0) Bad("access to site, knowledge or a kr_ schema");
        if (r.GetInt64(11) > 0) Bad("privileges on a table or view");
        return issues;
    }

    /// Application DDL for knowledge schema version 1: the allowlisted tables, typed, with primary keys and the
    /// builder-only graph edge values enforced again in the database. No triggers, no rules, no functions.
    public static string TableDdl(string schema, TableSpec t)
    {
        var cols = t.Columns.Select(c =>
        {
            var def = $"{Q(c.Name)} {c.SqlType}{(c.Nullable ? "" : " NOT NULL")}";
            if (c.Type == ColType.Enum) def += $" CHECK ({Q(c.Name)} IN ({string.Join(",", c.Values.Select(v => "'" + v + "'"))}))";
            if (c.Type == ColType.Const) def += $" CHECK ({Q(c.Name)} = '{c.Values[0]}')";
            return def;
        });
        return $"CREATE TABLE {Q(schema)}.{Q(t.Table)} ({string.Join(", ", cols)}, PRIMARY KEY ({string.Join(",", t.PrimaryKey.Select(Q))}))";
    }

    async Task CreateStagingAsync(NpgsqlConnection admin, string staging, CancellationToken ct)
    {
        await using var tx = await admin.BeginTransactionAsync(ct);
        var sql = new StringBuilder();
        sql.Append($"CREATE SCHEMA {Q(staging)};\nREVOKE ALL ON SCHEMA {Q(staging)} FROM PUBLIC;\n");
        foreach (var t in KnowledgeAllowlist.Tables) sql.Append(TableDdl(staging, t)).Append(";\n");
        sql.Append($"GRANT USAGE ON SCHEMA {Q(staging)} TO {Q(LoaderRole)};\nGRANT INSERT ON ALL TABLES IN SCHEMA {Q(staging)} TO {Q(LoaderRole)};\n");
        await using (var cmd = new NpgsqlCommand(sql.ToString(), admin, tx)) await cmd.ExecuteNonQueryAsync(ct);
        await tx.CommitAsync(ct);
    }

    async Task CopyAsync(string staging, List<KnowledgeRows.ParsedRowFile> parsed, CancellationToken ct)
    {
        await using var lc = new NpgsqlConnection(loaderConnectionString);
        await lc.OpenAsync(ct);
        await using var tx = await lc.BeginTransactionAsync(ct);
        foreach (var p in parsed.OrderBy(p => p.Spec!.Table, StringComparer.Ordinal))
        {
            var t = p.Spec!;
            await using var w = await lc.BeginBinaryImportAsync(
                $"COPY {Q(staging)}.{Q(t.Table)} ({string.Join(",", t.Columns.Select(c => Q(c.Name)))}) FROM STDIN (FORMAT BINARY)", ct);
            long i = 0;
            foreach (var row in p.Rows)
            {
                await w.StartRowAsync(ct);
                foreach (var c in t.Columns)
                {
                    var v = row[c.Name];
                    if (v is null) await w.WriteNullAsync(ct);
                    else if (c.IsBool) await w.WriteAsync(v.GetValue<bool>(), NpgsqlDbType.Boolean, ct);
                    else if (c.IsInteger) await w.WriteAsync(checked((int)v.GetValue<double>()), NpgsqlDbType.Integer, ct);
                    else await w.WriteAsync(v.GetValue<string>(), NpgsqlDbType.Text, ct);
                }
                if (OnRowWritten is not null) await OnRowWritten(t.Table, ++i);
            }
            await w.CompleteAsync(ct);
        }
        await tx.CommitAsync(ct);
    }

    /// Ordered canonical export of one staging table: the same bytes a canonical row file of those rows would have.
    public static async Task<(byte[] Bytes, long Count)> ExportAsync(NpgsqlConnection c, NpgsqlTransaction? tx, string schema, TableSpec t, CancellationToken ct = default)
    {
        await using var q = new NpgsqlCommand(
            $"SELECT {string.Join(",", t.Columns.Select(x => Q(x.Name)))} FROM {Q(schema)}.{Q(t.Table)} ORDER BY {string.Join(",", t.PrimaryKey.Select(Q))}", c, tx);
        await using var r = await q.ExecuteReaderAsync(ct);
        using var ms = new MemoryStream();
        long n = 0;
        while (await r.ReadAsync(ct))
        {
            var o = new JsonObject();
            for (int i = 0; i < t.Columns.Length; i++)
            {
                var col = t.Columns[i];
                o[col.Name] = r.IsDBNull(i) ? null : col.IsBool ? JsonValue.Create(r.GetBoolean(i)) : col.IsInteger ? JsonValue.Create(r.GetInt32(i)) : JsonValue.Create(r.GetString(i));
            }
            ms.Write(CanonicalJson.Bytes(o)); ms.WriteByte((byte)'\n');
            n++;
        }
        return (ms.ToArray(), n);
    }

    static async Task<List<RowIssue>> VerifyAsync(NpgsqlConnection admin, string staging, KnowledgeLoadRequest req, List<TableRows> verified, CancellationToken ct)
    {
        var issues = new List<RowIssue>();
        await using var tx = await admin.BeginTransactionAsync(System.Data.IsolationLevel.RepeatableRead, ct);
        await using (var ro = new NpgsqlCommand("SET TRANSACTION READ ONLY", admin, tx)) await ro.ExecuteNonQueryAsync(ct);

        // the staging schema holds exactly the allowlisted tables, with no triggers and no rules
        var dump = await SchemaDump.DumpAsync(admin, staging, tx);
        var expected = KnowledgeAllowlist.Tables.Select(t => t.Table).ToHashSet(StringComparer.Ordinal);
        foreach (var rel in dump.Keys.Where(k => !expected.Contains(k) && !k.EndsWith("_pkey", StringComparison.Ordinal)))
            issues.Add(new("KR_STAGING_TAMPERED", "unexpected relation in the staging schema", rel));
        await using (var tq = new NpgsqlCommand("""
            SELECT (SELECT count(*) FROM pg_trigger g JOIN pg_class c ON c.oid = g.tgrelid JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = $1 AND NOT g.tgisinternal)
                 + (SELECT count(*) FROM pg_rules WHERE schemaname = $1)
                 + (SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace WHERE n.nspname = $1)
            """, admin, tx))
        {
            tq.Parameters.AddWithValue(staging);
            if ((long)(await tq.ExecuteScalarAsync(ct))! > 0) issues.Add(new("KR_STAGING_TAMPERED", "trigger, rule or function in the staging schema", staging));
        }
        var declared = req.Declared.ToDictionary(d => d.Table, StringComparer.Ordinal);
        foreach (var t in KnowledgeAllowlist.Tables)
        {
            var (bytes, count) = await ExportAsync(admin, tx, staging, t, ct);
            if (!declared.TryGetValue(t.Table, out var d))
            {
                if (count != 0) issues.Add(new("KR_STAGING_TAMPERED", "rows in a table the release did not ship", t.Table));
                continue;
            }
            var sha = CanonicalJson.Sha256Hex(bytes);
            bool fine = true;
            if (count != d.RowCount) { issues.Add(new("KR_ROWS_COUNT_MISMATCH", $"{count} rows loaded, {d.RowCount} declared", t.Table)); fine = false; }
            if (sha != d.RowsSha256) { issues.Add(new("KR_ROWS_DIGEST_MISMATCH", "rows_sha256 of the ordered export differs from the declared value", t.Table)); fine = false; }
            else if (!bytes.AsSpan().SequenceEqual(req.Files[t.Table])) { issues.Add(new("KR_ROWS_DIGEST_MISMATCH", "ordered export differs from the shipped row file", t.Table)); fine = false; }
            var re = KnowledgeRows.RederiveCompare(t.Table, bytes, req.Sources);
            issues.AddRange(re);
            if (fine && re.Count == 0) verified.Add(new TableRows(t, bytes, count, sha));
        }
        await tx.CommitAsync(ct);
        return issues;
    }

    /// DB_APPLIED (B06): kr_<n>_staging becomes kr_<n> and every `knowledge` view points at it, in one transaction.
    public static async Task PromoteAsync(NpgsqlDataSource activator, long n, CancellationToken ct = default)
    {
        string staging = KnowledgeAllowlist.StagingSchema(n), active = KnowledgeAllowlist.ActiveSchema(n);
        await using var c = await activator.OpenConnectionAsync(ct);
        await using var tx = await c.BeginTransactionAsync(ct);
        await using (var lk = new NpgsqlCommand("SELECT pg_advisory_xact_lock($1)", c, tx)) { lk.Parameters.AddWithValue(LoadLockKey); await lk.ExecuteNonQueryAsync(ct); }
        if (!await SchemaExistsAsync(c, staging, ct)) throw new InvalidOperationException("KR_PROMOTE_NO_STAGING");
        if (await SchemaExistsAsync(c, active, ct)) throw new InvalidOperationException("KR_PROMOTE_TARGET_EXISTS");
        var sql = new StringBuilder($"ALTER SCHEMA {Q(staging)} RENAME TO {Q(active)};\nCREATE SCHEMA IF NOT EXISTS knowledge;\nREVOKE ALL ON SCHEMA knowledge FROM PUBLIC;\n");
        foreach (var t in KnowledgeAllowlist.Tables)
            sql.Append($"CREATE OR REPLACE VIEW knowledge.{Q(t.Table)} AS SELECT {string.Join(",", t.Columns.Select(x => Q(x.Name)))} FROM {Q(active)}.{Q(t.Table)};\n");
        await using (var cmd = new NpgsqlCommand(sql.ToString(), c, tx)) await cmd.ExecuteNonQueryAsync(ct);
        await tx.CommitAsync(ct);
    }
}

/// Setup of the restricted loader role (application install step; needs a role administrator) and the database
/// hardening it relies on (database owner). Passwords are quoted by the server (format %L) and never logged.
public static partial class KnowledgeLoaderRole
{
    [GeneratedRegex("^[a-z_][a-z0-9_]{0,62}$")] private static partial Regex RoleName();

    public const string Attributes = "LOGIN NOSUPERUSER NOCREATEROLE NOCREATEDB NOREPLICATION NOBYPASSRLS NOINHERIT";

    public static async Task EnsureAsync(NpgsqlDataSource roleAdmin, string role, string password, CancellationToken ct = default)
    {
        if (!RoleName().IsMatch(role)) throw new ArgumentException("role name");
        await using var c = await roleAdmin.OpenConnectionAsync(ct);
        await using var exists = new NpgsqlCommand("SELECT 1 FROM pg_roles WHERE rolname = $1", c);
        exists.Parameters.AddWithValue(role);
        var verb = await exists.ExecuteScalarAsync(ct) is null ? "CREATE" : "ALTER";
        await using var f = new NpgsqlCommand($"SELECT format('{verb} ROLE %I {Attributes} CONNECTION LIMIT 4 PASSWORD %L', $1::text, $2::text)", c);
        f.Parameters.AddWithValue(role); f.Parameters.AddWithValue(password);
        var sql = (string)(await f.ExecuteScalarAsync(ct))!;
        await using var run = new NpgsqlCommand(sql, c);
        await run.ExecuteNonQueryAsync(ct);
        // no memberships in either direction (SET ROLE is impossible without one)
        await using var m = new NpgsqlCommand("SELECT count(*) FROM pg_auth_members WHERE member = (SELECT oid FROM pg_roles WHERE rolname = $1)", c);
        m.Parameters.AddWithValue(role);
        if ((long)(await m.ExecuteScalarAsync(ct))! != 0) throw new InvalidOperationException("loader role is a member of another role");
    }

    /// Database owner: the loader may connect, but neither the loader nor PUBLIC may create temporary objects
    /// (pg_temp functions) or objects in the public schema.
    public static async Task HardenDatabaseAsync(NpgsqlDataSource owner, string role, CancellationToken ct = default)
    {
        if (!RoleName().IsMatch(role)) throw new ArgumentException("role name");
        await using var c = await owner.OpenConnectionAsync(ct);
        await using var cmd = new NpgsqlCommand($"""
            DO $$ BEGIN
              EXECUTE format('REVOKE TEMPORARY ON DATABASE %I FROM PUBLIC', current_database());
              EXECUTE format('GRANT CONNECT ON DATABASE %I TO %I', current_database(), '{role}');
            END $$;
            REVOKE CREATE ON SCHEMA public FROM PUBLIC;
            """, c);
        await cmd.ExecuteNonQueryAsync(ct);
    }
}
