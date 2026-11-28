// C16 Tranche B Stage 3 S3-C (B07): database setup of a DEVELOPMENT/TEST installation, with the B03 2.1 hardening
// (interfaces/B03_KNOWLEDGE_ROWS.md section 4) and the I-3 migration gate (SG-2, OG-3).
//
// Roles (prefix configurable; NOSUPERUSER NOCREATEROLE NOCREATEDB NOREPLICATION NOBYPASSRLS NOINHERIT, no memberships):
//   <p>web        the web service: CONNECT; USAGE on the application schemas; DML on site tables; SELECT on knowledge
//   <p>backup     the backup task: CONNECT; USAGE and SELECT on the backed-up site schemas only (pg_dump)
//   <p>kr_loader  the B03 restricted loader: CONNECT only; per-release USAGE/INSERT on kr_<n>_staging is granted (and
//                 revoked) by KnowledgeRowLoader, never CREATE anywhere
//   the DATABASE OWNER is the activator (application DDL, kr_ promotion, knowledge views), as in CP-1
// Hardening (once per database, re-asserted on every install/upgrade): REVOKE CREATE ON SCHEMA public FROM PUBLIC;
// REVOKE TEMPORARY ON DATABASE FROM PUBLIC; REVOKE CREATE ON DATABASE FROM PUBLIC; REVOKE CONNECT ON DATABASE FROM
// PUBLIC; REVOKE ALL ON SCHEMA site, knowledge FROM PUBLIC; then explicit grants only (no TEMPORARY for anyone: no
// measured need). The probe matrix (has_*_privilege plus real attempts as each role) is the installer's acceptance test.
//
// Migrations (I-3): only migrations declared ADDITIVE or COPY_AND_VERIFY are accepted, and only on a CLONE (a database
// created from the source by CREATE DATABASE ... TEMPLATE and marked by the installer); forward, verify (ordered dumps),
// ROLLBACK, verify, forward again. A destructive migration (declared, or SQL with DROP/TRUNCATE/DELETE/ALTER ... DROP/
// RENAME/TYPE) is refused before anything runs. The operational database is never touched (OG-3).
using System.Security.Cryptography;
using System.Text.Json.Nodes;
using System.Text.RegularExpressions;
using Mimamsa.Core.Knowledge;
using Npgsql;

namespace Mimamsa.Core.Install;

public sealed class DatabaseSetupException(string code, string message) : Exception(code + ": " + message)
{
    public string Code { get; } = code;
}

public sealed record SiteRoles(string Web, string Backup, string Loader)
{
    public static SiteRoles For(string prefix) => new(prefix + "web", prefix + "backup", prefix + "kr_loader");
    public IEnumerable<string> All => [Web, Backup, Loader];
}

public static partial class SiteDatabaseSetup
{
    [GeneratedRegex("^[a-z_][a-z0-9_]{0,62}$")] private static partial Regex Ident();
    const string RoleAttributes = "LOGIN NOSUPERUSER NOCREATEROLE NOCREATEDB NOREPLICATION NOBYPASSRLS NOINHERIT";
    public const string CloneMarker = "mimamsa-installer-clone-of:";

    static string Q(string s) => Ident().IsMatch(s) ? "\"" + s + "\"" : throw new DatabaseSetupException("IDENT", "unsafe identifier");

    static async Task<long> Exec(NpgsqlDataSource ds, string sql, params object[] p)
    {
        await using var c = await ds.OpenConnectionAsync();
        await using var cmd = new NpgsqlCommand(sql, c);
        foreach (var x in p) cmd.Parameters.AddWithValue(x);
        return await cmd.ExecuteNonQueryAsync();
    }

    static async Task<T?> Scalar<T>(NpgsqlDataSource ds, string sql, params object[] p)
    {
        await using var c = await ds.OpenConnectionAsync();
        await using var cmd = new NpgsqlCommand(sql, c);
        foreach (var x in p) cmd.Parameters.AddWithValue(x);
        var r = await cmd.ExecuteScalarAsync();
        return r is null or DBNull ? default : (T)r;
    }

    public static string NewPassword() => Convert.ToBase64String(RandomNumberGenerator.GetBytes(24)).Replace('+', 'A').Replace('/', 'B').TrimEnd('=');

    /// Create or re-assert a restricted login role (role administrator). Passwords are quoted by the server (%L) and
    /// never logged. The role must have no memberships in either direction (SET ROLE impossible).
    public static async Task EnsureRoleAsync(NpgsqlDataSource roleAdmin, string role, string password)
    {
        if (!Ident().IsMatch(role)) throw new DatabaseSetupException("IDENT", "role name");
        var exists = await Scalar<int?>(roleAdmin, "SELECT 1 FROM pg_roles WHERE rolname = $1", role) is not null;
        var sql = await Scalar<string>(roleAdmin, $"SELECT format('{(exists ? "ALTER" : "CREATE")} ROLE %I {RoleAttributes} CONNECTION LIMIT 16 PASSWORD %L', $1::text, $2::text)", role, password);
        await Exec(roleAdmin, sql!);
        var members = await Scalar<long>(roleAdmin, "SELECT count(*) FROM pg_auth_members m JOIN pg_roles r ON r.oid IN (m.member, m.roleid) WHERE r.rolname = $1", role);
        if (members != 0) throw new DatabaseSetupException("ROLE_HAS_MEMBERSHIP", role + " is a member of, or has members in, another role");
    }

    /// Hardening and explicit grants (database owner). Idempotent; re-run after every migration or restore.
    public static async Task HardenAndGrantAsync(NpgsqlDataSource owner, SiteRoles roles, IReadOnlyList<string> appSchemas, IReadOnlyList<string> backupSchemas)
    {
        foreach (var r in roles.All) Q(r);
        var db = await Scalar<string>(owner, "SELECT current_database()");
        var ownerRole = await Scalar<string>(owner, "SELECT current_user");
        var existing = new List<string>();
        foreach (var s in appSchemas.Concat(backupSchemas).Append("knowledge").Distinct())
            if (await Scalar<int?>(owner, "SELECT 1 FROM pg_namespace WHERE nspname = $1", s) is not null) existing.Add(s);
        var sql = new System.Text.StringBuilder();
        sql.Append($"REVOKE CREATE ON SCHEMA public FROM PUBLIC;\n");
        sql.Append($"REVOKE TEMPORARY ON DATABASE {Q(db!)} FROM PUBLIC;\nREVOKE CREATE ON DATABASE {Q(db!)} FROM PUBLIC;\nREVOKE CONNECT ON DATABASE {Q(db!)} FROM PUBLIC;\n");
        foreach (var s in new[] { "site", "knowledge" }.Where(existing.Contains)) sql.Append($"REVOKE ALL ON SCHEMA {Q(s)} FROM PUBLIC;\n");
        foreach (var r in roles.All)
        {
            sql.Append($"GRANT CONNECT ON DATABASE {Q(db!)} TO {Q(r)};\n");
            sql.Append($"REVOKE TEMPORARY, CREATE ON DATABASE {Q(db!)} FROM {Q(r)};\n");
        }
        foreach (var s in appSchemas.Where(existing.Contains))
        {
            sql.Append($"GRANT USAGE ON SCHEMA {Q(s)} TO {Q(roles.Web)};\nREVOKE CREATE ON SCHEMA {Q(s)} FROM {Q(roles.Web)};\n");
            sql.Append($"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA {Q(s)} TO {Q(roles.Web)};\n");
            sql.Append($"GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA {Q(s)} TO {Q(roles.Web)};\n");
            sql.Append($"ALTER DEFAULT PRIVILEGES FOR ROLE {Q(ownerRole!)} IN SCHEMA {Q(s)} GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {Q(roles.Web)};\n");
            sql.Append($"ALTER DEFAULT PRIVILEGES FOR ROLE {Q(ownerRole!)} IN SCHEMA {Q(s)} GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO {Q(roles.Web)};\n");
        }
        if (existing.Contains("knowledge"))
        {
            sql.Append($"GRANT USAGE ON SCHEMA knowledge TO {Q(roles.Web)};\nGRANT SELECT ON ALL TABLES IN SCHEMA knowledge TO {Q(roles.Web)};\n");
            sql.Append($"ALTER DEFAULT PRIVILEGES FOR ROLE {Q(ownerRole!)} IN SCHEMA knowledge GRANT SELECT ON TABLES TO {Q(roles.Web)};\n");
        }
        foreach (var s in backupSchemas.Where(existing.Contains))
        {
            sql.Append($"GRANT USAGE ON SCHEMA {Q(s)} TO {Q(roles.Backup)};\nGRANT SELECT ON ALL TABLES IN SCHEMA {Q(s)} TO {Q(roles.Backup)};\nGRANT SELECT ON ALL SEQUENCES IN SCHEMA {Q(s)} TO {Q(roles.Backup)};\n");
            sql.Append($"ALTER DEFAULT PRIVILEGES FOR ROLE {Q(ownerRole!)} IN SCHEMA {Q(s)} GRANT SELECT ON TABLES TO {Q(roles.Backup)};\n");
        }
        await Exec(owner, sql.ToString());
    }

    /// The privilege probe matrix: catalogue checks AND real attempts as each role. Every row must hold.
    public static async Task<JsonObject> ProbeAsync(NpgsqlDataSource owner, SiteRoles roles, Func<string, string> roleDsn, string? stagingSchema = null)
    {
        var db = (await Scalar<string>(owner, "SELECT current_database()"))!;
        var rows = new JsonArray();
        bool all = true;
        async Task Cat(string name, string sql, bool expect, params object[] p)
        {
            var got = await Scalar<bool>(owner, sql, p);
            rows.Add(new JsonObject { ["probe"] = name, ["expected"] = expect, ["actual"] = got, ["ok"] = got == expect });
            all &= got == expect;
        }
        async Task Try(string name, string role, string sql, bool expectAllowed)
        {
            bool allowed; string? state = null;
            try
            {
                await using var ds = NpgsqlDataSource.Create(roleDsn(role));
                await using var c = await ds.OpenConnectionAsync();
                await using var tx = await c.BeginTransactionAsync();
                await using (var cmd = new NpgsqlCommand(sql, c, tx)) await cmd.ExecuteNonQueryAsync();
                await tx.RollbackAsync();
                allowed = true;
            }
            catch (PostgresException e) { allowed = false; state = e.SqlState; }
            rows.Add(new JsonObject { ["probe"] = name, ["role"] = role, ["expected_allowed"] = expectAllowed, ["allowed"] = allowed, ["sqlstate"] = state, ["ok"] = allowed == expectAllowed });
            all &= allowed == expectAllowed;
        }
        foreach (var r in roles.All.Append("public"))
        {
            await Cat($"{r}: CREATE on schema public", "SELECT has_schema_privilege($1, 'public', 'CREATE')", false, r);
            await Cat($"{r}: TEMPORARY on database", "SELECT has_database_privilege($1, $2, 'TEMPORARY')", false, r, db);
            await Cat($"{r}: CREATE on database", "SELECT has_database_privilege($1, $2, 'CREATE')", false, r, db);
        }
        await Cat("public: CONNECT on database", "SELECT has_database_privilege('public', $1, 'CONNECT')", false, db);
        foreach (var r in roles.All)
        {
            await Cat($"{r}: superuser/createrole/createdb/replication/bypassrls all off",
                "SELECT NOT (rolsuper OR rolcreaterole OR rolcreatedb OR rolreplication OR rolbypassrls) AND NOT rolinherit FROM pg_roles WHERE rolname = $1", true, r);
            await Cat($"{r}: no role memberships", "SELECT NOT EXISTS (SELECT 1 FROM pg_auth_members m JOIN pg_roles x ON x.oid IN (m.member, m.roleid) WHERE x.rolname = $1)", true, r);
        }
        bool hasSite = await Scalar<int?>(owner, "SELECT 1 FROM pg_namespace WHERE nspname = 'site'") is not null;
        if (hasSite)
        {
            await Cat($"{roles.Loader}: USAGE on schema site", "SELECT has_schema_privilege($1, 'site', 'USAGE')", false, roles.Loader);
            await Cat($"{roles.Web}: USAGE on schema site", "SELECT has_schema_privilege($1, 'site', 'USAGE')", true, roles.Web);
            await Cat($"{roles.Web}: CREATE on schema site", "SELECT has_schema_privilege($1, 'site', 'CREATE')", false, roles.Web);
            await Cat($"{roles.Backup}: CREATE on schema site", "SELECT has_schema_privilege($1, 'site', 'CREATE')", false, roles.Backup);
            await Cat("public: USAGE on schema site", "SELECT has_schema_privilege('public', 'site', 'USAGE')", false);
            var anyTable = await Scalar<string>(owner, "SELECT quote_ident(relname) FROM pg_class k JOIN pg_namespace n ON n.oid = k.relnamespace WHERE n.nspname = 'site' AND relkind = 'r' ORDER BY relname LIMIT 1");
            if (anyTable is not null)
            {
                await Try($"{roles.Loader}: SELECT site.{anyTable}", roles.Loader, $"SELECT 1 FROM site.{anyTable} LIMIT 1", false);
                await Try($"{roles.Backup}: SELECT site.{anyTable}", roles.Backup, $"SELECT 1 FROM site.{anyTable} LIMIT 1", true);
                await Try($"{roles.Backup}: DELETE site.{anyTable}", roles.Backup, $"DELETE FROM site.{anyTable}", false);
                await Try($"{roles.Web}: SELECT site.{anyTable}", roles.Web, $"SELECT 1 FROM site.{anyTable} LIMIT 1", true);
                await Try($"{roles.Web}: DROP site.{anyTable}", roles.Web, $"DROP TABLE site.{anyTable}", false);
            }
        }
        if (await Scalar<int?>(owner, "SELECT 1 FROM pg_namespace WHERE nspname = 'knowledge'") is not null)
        {
            await Cat($"{roles.Loader}: USAGE on schema knowledge", "SELECT has_schema_privilege($1, 'knowledge', 'USAGE')", false, roles.Loader);
            await Cat($"{roles.Web}: CREATE on schema knowledge", "SELECT has_schema_privilege($1, 'knowledge', 'CREATE')", false, roles.Web);
            await Try($"{roles.Web}: replace a knowledge view", roles.Web, "CREATE OR REPLACE VIEW knowledge.s3c_probe AS SELECT 1 AS x", false);
        }
        if (stagingSchema is not null && await Scalar<int?>(owner, "SELECT 1 FROM pg_namespace WHERE nspname = $1", stagingSchema) is not null)
            await Cat($"{roles.Loader}: CREATE on {stagingSchema}", "SELECT has_schema_privilege($1, $2, 'CREATE')", false, roles.Loader, stagingSchema);
        foreach (var r in roles.All)
        {
            await Try($"{r}: CREATE TABLE in public", r, "CREATE TABLE public.s3c_probe(x int)", false);
            await Try($"{r}: CREATE TEMP TABLE", r, "CREATE TEMP TABLE s3c_probe(x int)", false);
            await Try($"{r}: CREATE FUNCTION in public", r, "CREATE FUNCTION public.s3c_probe() RETURNS int LANGUAGE sql AS 'SELECT 1'", false);
            await Try($"{r}: CREATE SCHEMA", r, "CREATE SCHEMA s3c_probe", false);
        }
        foreach (var other in roles.All)
            foreach (var r in roles.All.Where(x => x != other))
                await Try($"{r}: SET ROLE {other}", r, $"SET ROLE {Q(other)}", false);
        return new JsonObject { ["all_ok"] = all, ["probes"] = rows };
    }

    // ------------------------------------------------------------------ I-3 migration gate
    public enum MigrationKind { ADDITIVE, COPY_AND_VERIFY, DESTRUCTIVE }
    public sealed record MigrationStep(string Id, MigrationKind Kind, string? Sql = null);

    /// The application's registered migrations (this release): only B03's copy-and-verify site migration.
    public static IReadOnlyList<MigrationStep> BuiltInPlan => [new(SiteSchemaMigration.Version, MigrationKind.COPY_AND_VERIFY)];

    [GeneratedRegex(@"\b(DROP|TRUNCATE)\b|(?<!\bON\s+)\b(DELETE|UPDATE)\b|\bALTER\s+TABLE\b[^;]*\b(RENAME|ALTER\s+COLUMN\s+\S+\s+(SET\s+DATA\s+)?TYPE)\b|\bALTER\s+SCHEMA\b[^;]*\bRENAME\b",
        RegexOptions.IgnoreCase | RegexOptions.CultureInvariant)]
    private static partial Regex DestructiveSql();

    /// Refusals for a migration plan: any DESTRUCTIVE step, any step whose SQL contains a destructive statement, and
    /// any step that is not a registered application migration.
    public static List<string> PlanIssues(IEnumerable<MigrationStep> plan)
    {
        var o = new List<string>();
        foreach (var s in plan)
        {
            if (s.Kind == MigrationKind.DESTRUCTIVE) o.Add($"MIGRATION_DESTRUCTIVE: {s.Id} is declared destructive");
            else if (s.Sql is { } sql && DestructiveSql().Match(sql) is { Success: true } m) o.Add($"MIGRATION_DESTRUCTIVE: {s.Id} contains '{m.Value.Trim()}'");
            else if (s.Sql is null && s.Id != SiteSchemaMigration.Version) o.Add($"MIGRATION_UNKNOWN: {s.Id} is not a registered application migration");
        }
        return o;
    }

    public static IReadOnlyList<MigrationStep> ParsePlan(string json) =>
        JsonNode.Parse(json)!["steps"]!.AsArray().Select(x => new MigrationStep((string)x!["id"]!, Enum.Parse<MigrationKind>((string)x["kind"]!), (string?)x["sql"])).ToList();

    static void GuardName(string name, string? disposablePrefix)
    {
        if (!Ident().IsMatch(name)) throw new DatabaseSetupException("IDENT", "database name");
        if (disposablePrefix is not null && !name.StartsWith(disposablePrefix, StringComparison.Ordinal))
            throw new DatabaseSetupException("DATABASE_NOT_DISPOSABLE", $"{name} does not start with the configured disposable prefix");
    }

    /// Clone `source` (CREATE DATABASE ... TEMPLATE) and mark the clone; the installer migrates only marked clones.
    public static async Task CloneAsync(NpgsqlDataSource admin, string source, string clone, string ownerRole, string? disposablePrefix)
    {
        GuardName(source, disposablePrefix); GuardName(clone, disposablePrefix);
        if (source == clone) throw new DatabaseSetupException("MIGRATION_NOT_ON_CLONE", "the clone must be a different database");
        NpgsqlConnection.ClearAllPools();
        await Exec(admin, $"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = $1 AND pid <> pg_backend_pid()", source);
        await Exec(admin, $"CREATE DATABASE {Q(clone)} OWNER {Q(ownerRole)} TEMPLATE {Q(source)}");
        await Exec(admin, $"COMMENT ON DATABASE {Q(clone)} IS '{CloneMarker}{source}'");
    }

    public static async Task<string?> CloneOfAsync(NpgsqlDataSource ds) =>
        await Scalar<string>(ds, "SELECT shobj_description(oid, 'pg_database') FROM pg_database WHERE datname = current_database()") is { } d && d.StartsWith(CloneMarker, StringComparison.Ordinal)
            ? d[CloneMarker.Length..] : null;

    /// The I-3 demonstration on a CLONE: forward (copy-and-verify), verify the old schema unchanged, ROLLBACK, verify,
    /// forward again. Refuses destructive plans and non-clones before anything runs.
    public static async Task<JsonObject> MigrateCloneAsync(NpgsqlDataSource cloneOwner, IReadOnlyList<MigrationStep> plan, Func<string, Task>? afterForward = null)
    {
        var issues = PlanIssues(plan);
        if (issues.Count > 0) throw new DatabaseSetupException(issues[0].Split(':')[0], string.Join("; ", issues));
        var src = await CloneOfAsync(cloneOwner) ?? throw new DatabaseSetupException("MIGRATION_NOT_ON_CLONE", "the target database is not an installer clone; migrations run on clones only (SG-2, OG-3)");
        var mig = new SiteSchemaMigration(cloneOwner);
        async Task<List<KeyValuePair<string, string>>> PublicDump()
        {
            await using var c = await cloneOwner.OpenConnectionAsync();
            return (await SchemaDump.DumpSchemasAsync(c, ["public"])).ToList();
        }
        var before = await PublicDump();
        var steps = new JsonArray();
        var f1 = await mig.ForwardAsync();
        steps.Add(new JsonObject { ["step"] = "forward", ["tables"] = f1.Tables.Count, ["all_verified"] = f1.Tables.All(t => t.OldDigest == t.NewDigest) });
        if (afterForward is not null) await afterForward("forward");
        bool publicSame1 = before.SequenceEqual(await PublicDump());
        bool notDiverged = (await mig.DivergedTablesAsync()).Count == 0;
        await mig.RollbackAsync();
        bool publicSame2 = before.SequenceEqual(await PublicDump());
        var status = await mig.StatusAsync();
        steps.Add(new JsonObject { ["step"] = "rollback", ["status_after"] = status, ["public_unchanged"] = publicSame2 });
        var f2 = await mig.ForwardAsync();
        bool publicSame3 = before.SequenceEqual(await PublicDump());
        steps.Add(new JsonObject { ["step"] = "forward_again", ["tables"] = f2.Tables.Count, ["public_unchanged"] = publicSame3 });
        bool ok = publicSame1 && notDiverged && publicSame2 && status == "NOT_APPLIED" && publicSame3 && f2.Tables.Count == f1.Tables.Count;
        if (!ok) throw new DatabaseSetupException("MIGRATION_VERIFY_FAILED", steps.ToJsonString());
        return new JsonObject
        {
            ["ok"] = true, ["clone_of"] = src, ["migration"] = SiteSchemaMigration.Version, ["kind"] = "COPY_AND_VERIFY",
            ["old_schema_unchanged"] = true, ["rollback_demonstrated"] = true, ["steps"] = steps,
            ["tables"] = new JsonArray(f2.Tables.Select(t => (JsonNode)new JsonObject { ["table"] = t.Table, ["rows"] = t.Rows, ["digest"] = t.NewDigest }).ToArray()),
            ["left_in_place"] = new JsonArray(f2.LeftInPlace.Select(x => (JsonNode)x).ToArray()),
        };
    }
}
