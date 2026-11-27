// C16 B03: the knowledge-row allowlist that SHIPS WITH THE APPLICATION (never in a release). It is the application's
// knowledge schema version 1: every loadable table, its owner component (I-2: GRAPH owns graph_nodes and graph_edges),
// primary key, typed columns (KNOWLEDGE_ROWS_SCHEMA.json $defs/<table>_row, in `required` order) and derivation.
// Table and column names used in SQL come only from here, never from a release.
using System.Text.Json.Nodes;
using System.Text.RegularExpressions;

namespace Mimamsa.Core.Knowledge;

public enum ColType { Text, TextNull, Sha, ShaNull, Bool, Int, IntNull, IntMin1, IntMin1Null, Enum, Const }

public sealed record ColumnSpec(string Name, ColType Type, params string[] Values)
{
    public bool Nullable => Type is ColType.TextNull or ColType.ShaNull or ColType.IntNull or ColType.IntMin1Null;
    public bool IsInteger => Type is ColType.Int or ColType.IntNull or ColType.IntMin1 or ColType.IntMin1Null;
    public bool IsBool => Type == ColType.Bool;
    public string SqlType => IsInteger ? "integer" : IsBool ? "boolean" : "text COLLATE \"C\"";
}

public sealed record TableSpec(string Table, string Owner, string[] PrimaryKey, string Derivation, ColumnSpec[] Columns)
{
    public ColumnSpec Column(string name) => Columns.First(c => c.Name == name);
}

public static partial class KnowledgeAllowlist
{
    public const string Contract = "mimamsa-corpus-contract/2.1";
    public const int KnowledgeSchemaVersion = 1;
    public const string OwnerKnowledgeRows = "KNOWLEDGE_ROWS", OwnerGraph = "GRAPH";
    public const string PythonReference = "PYTHON_REFERENCE", DotnetB03 = "DOTNET_B03";
    public const int MaxRowBytes = 1 << 20, MaxText = 2000;
    public const string LoaderRole = "mimamsa_kr_loader";
    public static readonly string[] BuilderVerification = ["CANDIDATE", "EXTRACTED_STRUCTURE", "CURATED_NAVIGATION"];

    static ColumnSpec T(string n) => new(n, ColType.Text);
    static ColumnSpec TN(string n) => new(n, ColType.TextNull);
    static ColumnSpec Sha(string n) => new(n, ColType.Sha);
    static ColumnSpec ShaN(string n) => new(n, ColType.ShaNull);
    static ColumnSpec B(string n) => new(n, ColType.Bool);

    public static readonly IReadOnlyList<TableSpec> Tables =
    [
        new("document_identities", OwnerKnowledgeRows, ["doc_id"], PythonReference,
            [T("doc_id"), Sha("source_copy_sha256"), T("corpus_generation_id"), T("representation_kind"), T("work_kind"), TN("graph_node_ref"),
             T("research_state"), B("quoting_permitted"), Sha("record_sha256")]),
        new("evidence_anchors", OwnerKnowledgeRows, ["anchor_id"], PythonReference,
            [T("anchor_id"), T("doc_id"), Sha("original_sha256"), Sha("representation_sha256"), ShaN("derivative_text_sha256"), T("locator_kind"),
             new("physical_page", ColType.IntMin1Null), TN("image_sequence_id"), T("verification_state"), B("quoting_permitted"), Sha("record_sha256")]),
        new("corpus_relationships", OwnerKnowledgeRows, ["relationship_id"], PythonReference,
            [T("relationship_id"), T("category"), T("subject_doc_id"), Sha("subject_sha256"), TN("target_node_id"), TN("target_raw_reference"),
             T("evidentiary_basis"), T("verification"), B("has_legal_effect"), Sha("record_sha256")]),
        new("taxonomy_nodes", OwnerKnowledgeRows, ["node_id"], PythonReference,
            [T("node_id"), T("level"), T("label"), T("parent_ids_json"), TN("instrument_code"), T("verification"), Sha("record_sha256")]),
        new("corpus_admissions", OwnerKnowledgeRows, ["admission_id"], PythonReference,
            [T("admission_id"), T("doc_id"), Sha("source_copy_sha256"), new("revision", ColType.IntMin1), T("decision"), B("application_eligible"),
             T("service_scope"), B("is_effective"), Sha("record_sha256")]),
        new("candidates", OwnerKnowledgeRows, ["candidate_id"], DotnetB03,
            [T("candidate_id"), T("candidate_type"), T("source_doc_id"), T("status"), T("capability_restriction"), Sha("record_sha256")]),
        new("provision_versions", OwnerKnowledgeRows, ["version_id"], DotnetB03,
            [T("version_id"), T("family"), T("provision"), T("version_kind"), T("determination_state"), Sha("record_sha256")]),
        new("graph_nodes", OwnerGraph, ["id"], DotnetB03,
            [T("id"), T("kind"), T("label"), TN("doc_id"), B("held"), new("page", ColType.IntNull), TN("family"), TN("code")]),
        new("graph_edges", OwnerGraph, ["id"], DotnetB03,
            [T("id"), T("type"), T("from_id"), T("to_id"), T("origin"), TN("source_doc_id"), new("page", ColType.IntNull), TN("temporal_from"),
             T("temporal_from_status"), TN("temporal_to"), T("temporal_to_status"), new("verification", ColType.Enum, BuilderVerification),
             new("review_state", ColType.Const, "UNREVIEWED"), T("uncertainty"), B("has_legal_effect")]),
    ];

    static readonly Dictionary<string, TableSpec> ByName = Tables.ToDictionary(t => t.Table, StringComparer.Ordinal);

    public static TableSpec? Find(string table) => ByName.GetValueOrDefault(table);

    /// Files a component owns in a release (I-2: one owner per path).
    public static string FilePath(TableSpec t) => t.Owner == OwnerGraph ? $"accelerators/graph/{t.Table}.jsonl" : $"accelerators/rows/{t.Table}.jsonl";

    [GeneratedRegex("^kr_[0-9]{1,9}_staging$")] public static partial Regex StagingPattern();
    [GeneratedRegex("^kr_[0-9]{1,9}$")] public static partial Regex ActivePattern();

    public static string StagingSchema(long n) => n is >= 0 and <= 999_999_999 ? $"kr_{n}_staging" : throw new ArgumentOutOfRangeException(nameof(n));
    public static string ActiveSchema(long n) => n is >= 0 and <= 999_999_999 ? $"kr_{n}" : throw new ArgumentOutOfRangeException(nameof(n));

    /// The allowlist document (record_kind knowledge_rows_allowlist) this application ships; equal to the contract
    /// fixture `v2_1/knowledge_rows/allowlist.json` (test).
    public static JsonObject Document() => new()
    {
        ["contract"] = Contract, ["record_kind"] = "knowledge_rows_allowlist", ["knowledge_schema_version"] = KnowledgeSchemaVersion,
        ["tables"] = new JsonArray(Tables.Select(t => (JsonNode)new JsonObject
        {
            ["table"] = t.Table, ["owner_component"] = t.Owner, ["primary_key"] = new JsonArray(t.PrimaryKey.Select(k => (JsonNode)k!).ToArray()),
            ["row_schema"] = $"#/$defs/{t.Table}_row", ["derivation"] = t.Derivation,
        }).ToArray()),
        ["loader"] = new JsonObject
        {
            ["role"] = LoaderRole,
            ["role_attributes"] = new JsonArray("NOSUPERUSER", "NOCREATEROLE", "NOCREATEDB", "NOREPLICATION", "NOBYPASSRLS", "NOINHERIT"),
            ["grants"] = new JsonArray("USAGE ON SCHEMA kr_<n>_staging", "INSERT ON ALL TABLES IN SCHEMA kr_<n>_staging"),
            ["staging_schema_pattern"] = "^kr_[0-9]{1,9}_staging$", ["load_method"] = "PARAMETERISED_COPY_FROM_STDIN",
            ["forbidden"] = new JsonArray("site schema access", "knowledge schema access", "other kr_ schemas", "CREATE FUNCTION", "CREATE TRIGGER",
                "CREATE RULE", "CREATE EXTENSION", "SET ROLE", "DDL of any kind"),
        },
    };

    /// I-2 and allowlist sanity for an allowlist document (as knowledge_rows.allowlist_issues, minus JSON Schema):
    /// a table listed twice, a row schema not naming its own definition, a primary key outside the columns, or a graph
    /// table not owned by GRAPH (or another table owned by GRAPH) is an issue; so is any table unknown to this application.
    public static List<RowIssue> AllowlistIssues(JsonObject doc)
    {
        var issues = new List<RowIssue>();
        if (doc["knowledge_schema_version"]?.GetValue<int>() != KnowledgeSchemaVersion)
            issues.Add(new("KR_ROWS_SCHEMA_VERSION", "knowledge schema version not supported by this application", "allowlist"));
        var seen = new HashSet<string>(StringComparer.Ordinal);
        foreach (var n in doc["tables"] as JsonArray ?? [])
        {
            var name = n?["table"]?.GetValue<string>() ?? "";
            if (!seen.Add(name)) issues.Add(new("KR_ROWS_ALLOWLIST", "table listed twice", name));
            if (Find(name) is not { } spec) { issues.Add(new("KR_ROWS_TABLE_NOT_ALLOWLISTED", "table unknown to this application", name)); continue; }
            if (n!["row_schema"]?.GetValue<string>() != $"#/$defs/{name}_row")
                issues.Add(new("KR_ROWS_ALLOWLIST", "row schema does not name the table's own row definition", name));
            var pk = (n["primary_key"] as JsonArray ?? []).Select(x => x?.GetValue<string>() ?? "").ToArray();
            if (!pk.All(k => spec.Columns.Any(c => c.Name == k)))
                issues.Add(new("KR_ROWS_ALLOWLIST", "primary key column not in the row definition", name));
            var owner = n["owner_component"]?.GetValue<string>();
            if ((name is "graph_nodes" or "graph_edges") != (owner == OwnerGraph))
                issues.Add(new("KR_ROWS_ALLOWLIST", "graph tables are owned by GRAPH, all others by KNOWLEDGE_ROWS (I-2)", name));
        }
        return issues;
    }
}
