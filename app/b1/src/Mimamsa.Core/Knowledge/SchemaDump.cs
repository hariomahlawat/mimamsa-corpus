// C16 B03: ordered dumps of a PostgreSQL schema, used to prove that a failed knowledge load or a migration left a schema
// byte-identical. For every relation: kind, column definitions, constraints, indexes, triggers, rules, view definition
// and every row as text in code-point order (COLLATE "C"). Sequences: last_value and is_called. Content-free output:
// only digests and counts leave this function.
using System.Security.Cryptography;
using System.Text;
using Npgsql;

namespace Mimamsa.Core.Knowledge;

public static class SchemaDump
{
    public static string Q(string ident) => "\"" + ident.Replace("\"", "\"\"") + "\"";

    /// relation name -> "kind|rows|sha256(definition and ordered rows)". An absent schema gives an empty map.
    public static async Task<SortedDictionary<string, string>> DumpAsync(NpgsqlConnection c, string schema, NpgsqlTransaction? tx = null)
    {
        var rels = new List<(string name, char kind)>();
        await using (var q = new NpgsqlCommand("""
            SELECT c.relname, c.relkind FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = $1 AND c.relkind IN ('r','p','v','m','S','f') ORDER BY c.relname COLLATE "C"
            """, c, tx))
        {
            q.Parameters.AddWithValue(schema);
            await using var r = await q.ExecuteReaderAsync();
            while (await r.ReadAsync()) rels.Add((r.GetString(0), r.GetChar(1)));
        }
        var result = new SortedDictionary<string, string>(StringComparer.Ordinal);
        foreach (var (name, kind) in rels)
        {
            var fq = Q(schema) + "." + Q(name);
            var sb = new StringBuilder().Append(kind).Append('\n');
            long rows = 0;
            if (kind == 'S')
            {
                await using var s = new NpgsqlCommand($"SELECT last_value::text || '|' || is_called::text FROM {fq}", c, tx);
                sb.Append(await s.ExecuteScalarAsync());
            }
            else
            {
                await Lines(c, tx, sb, """
                    SELECT a.attname || ' ' || format_type(a.atttypid, a.atttypmod) || CASE WHEN a.attnotnull THEN ' NOT NULL' ELSE '' END
                           || coalesce(' DEFAULT ' || pg_get_expr(d.adbin, d.adrelid), '') || coalesce(' COLLATE ' || co.collname, '')
                    FROM pg_attribute a LEFT JOIN pg_attrdef d ON d.adrelid = a.attrelid AND d.adnum = a.attnum
                    LEFT JOIN pg_collation co ON co.oid = a.attcollation AND a.attcollation <> 0 AND co.collname <> 'default'
                    WHERE a.attrelid = $1::regclass AND a.attnum > 0 AND NOT a.attisdropped ORDER BY a.attnum
                    """, fq);
                await Lines(c, tx, sb, "SELECT conname || ' ' || pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid = $1::regclass ORDER BY conname::text COLLATE \"C\"", fq);
                await Lines(c, tx, sb, "SELECT pg_get_indexdef(indexrelid) FROM pg_index WHERE indrelid = $1::regclass ORDER BY pg_get_indexdef(indexrelid) COLLATE \"C\"", fq);
                await Lines(c, tx, sb, "SELECT 'TRIGGER ' || tgname FROM pg_trigger WHERE tgrelid = $1::regclass AND NOT tgisinternal ORDER BY tgname::text COLLATE \"C\"", fq);
                await Lines(c, tx, sb, "SELECT 'RULE ' || rulename FROM pg_rewrite WHERE ev_class = $1::regclass AND rulename <> '_RETURN' ORDER BY rulename::text COLLATE \"C\"", fq);
                if (kind is 'v' or 'm') await Lines(c, tx, sb, "SELECT pg_get_viewdef($1::regclass, true)", fq);
                sb.Append("--rows\n");
                await using var rq = new NpgsqlCommand($"SELECT x FROM (SELECT t::text AS x FROM {fq} t) s ORDER BY x COLLATE \"C\"", c, tx);
                await using var rr = await rq.ExecuteReaderAsync();
                while (await rr.ReadAsync()) { sb.Append(rr.GetString(0)).Append('\n'); rows++; }
            }
            var sha = Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(sb.ToString()))).ToLowerInvariant();
            result[name] = $"{kind}|{rows}|{sha}";
        }
        return result;
    }

    static async Task Lines(NpgsqlConnection c, NpgsqlTransaction? tx, StringBuilder sb, string sql, string fq)
    {
        await using var q = new NpgsqlCommand(sql, c, tx);
        q.Parameters.AddWithValue(fq);
        await using var r = await q.ExecuteReaderAsync();
        while (await r.ReadAsync()) sb.Append(r.IsDBNull(0) ? "" : r.GetString(0)).Append('\n');
    }

    /// Dumps of several schemas, keyed "schema.relation". Missing schemas contribute nothing (and are listed as such).
    public static async Task<SortedDictionary<string, string>> DumpSchemasAsync(NpgsqlConnection c, IEnumerable<string> schemas)
    {
        var all = new SortedDictionary<string, string>(StringComparer.Ordinal);
        foreach (var s in schemas)
        {
            var d = await DumpAsync(c, s);
            if (d.Count == 0) all[s + "."] = "absent-or-empty";
            foreach (var (k, v) in d) all[s + "." + k] = v;
        }
        return all;
    }

    public static async Task<List<string>> SchemasAsync(NpgsqlConnection c, NpgsqlTransaction? tx = null)
    {
        var list = new List<string>();
        await using var q = new NpgsqlCommand("SELECT nspname FROM pg_namespace WHERE nspname NOT LIKE 'pg\\_%' AND nspname <> 'information_schema' ORDER BY nspname COLLATE \"C\"", c, tx);
        await using var r = await q.ExecuteReaderAsync();
        while (await r.ReadAsync()) list.Add(r.GetString(0));
        return list;
    }
}
