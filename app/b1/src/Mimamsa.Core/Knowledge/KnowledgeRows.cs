// C16 B03: KNOWLEDGE_ROWS. One deterministic derivation (`KnowledgeRows.Derive`) used by the central build (writer) and
// by the site (ROWS_REDERIVE_COMPARE after the load). Rows are canonical JSONL, never SQL: one object per row with
// exactly the allowlisted columns, canonical JSON, sorted by primary key (code-point order), LF line ends, final LF.
//   - PYTHON_REFERENCE tables (document_identities, evidence_anchors, corpus_relationships, taxonomy_nodes,
//     corpus_admissions) are derived from the strict C16 exchange exactly as knowledge_rows.derive_rows (byte for byte;
//     cross-language golden test on the contract 2.1 fixtures).
//   - DOTNET_B03 tables: candidates (v1 candidate records), provision_versions (A4 research aid records) and the GRAPH
//     component's graph_nodes / graph_edges (GraphBuilder over the generation; I-2).
// `ReadRowFile` is the typed per-table reader the loader runs BEFORE COPY (knowledge_rows.row_file_issues): any issue
// rejects the whole component.
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using Mimamsa.Core.Generation;
using Mimamsa.Core.Graph;

namespace Mimamsa.Core.Knowledge;

public sealed record RowIssue(string Code, string Message, string Where)
{
    public override string ToString() => $"{Code} [{Where}] {Message}";
}

public sealed class KnowledgeRowsException(string code, string message) : Exception($"{code}: {message}")
{
    public string Code { get; } = code;
}

/// The authoritative records rows are derived from. The same object is used centrally and on site.
public sealed class KnowledgeSources
{
    public IReadOnlyList<JsonObject> Identities { get; init; } = [];
    public IReadOnlyList<JsonObject> Anchors { get; init; } = [];
    public IReadOnlyList<JsonObject> Relationships { get; init; } = [];
    public IReadOnlyList<JsonObject> Taxonomy { get; init; } = [];
    public IReadOnlyList<JsonObject> Admissions { get; init; } = [];
    /// v1 candidate records, as signed (the servable ones of the generation).
    public IReadOnlyList<JsonObject> Candidates { get; init; } = [];
    /// A4 provision-version research-aid records, as signed.
    public IReadOnlyList<JsonObject> ProvisionVersions { get; init; } = [];
    /// The generation's graph as built by the application's GraphBuilder; null when not available (graph tables then
    /// cannot be derived here and are refused, fail closed).
    public LegalGraph? Graph { get; init; }

    static readonly string[] ExchangeFiles = ["identities", "anchors", "relationships", "taxonomy", "admissions"];

    public static IReadOnlyList<JsonObject> ReadJsonl(string path)
    {
        if (!File.Exists(path)) return [];
        var list = new List<JsonObject>();
        foreach (var line in File.ReadAllText(path, Encoding.UTF8).Split('\n'))
            if (line.Length > 0) list.Add(JsonNode.Parse(line)!.AsObject());
        return list;
    }

    /// A strict C16 exchange directory (corpus-v2/: identities.jsonl, anchors.jsonl, relationships.jsonl, taxonomy.jsonl,
    /// admissions.jsonl). Missing files are empty populations.
    public static KnowledgeSources FromExchange(string dir, KnowledgeSources? v1 = null)
    {
        var pop = ExchangeFiles.ToDictionary(k => k, k => ReadJsonl(Path.Combine(dir, k + ".jsonl")));
        return new KnowledgeSources
        {
            Identities = pop["identities"], Anchors = pop["anchors"], Relationships = pop["relationships"], Taxonomy = pop["taxonomy"],
            Admissions = pop["admissions"], Candidates = v1?.Candidates ?? [], ProvisionVersions = v1?.ProvisionVersions ?? [], Graph = v1?.Graph,
        };
    }

    /// The loaded (verified) generation: its servable candidates' signed records, its A4 records, its graph and, when the
    /// generation carries one, its C16 exchange (generations/<id>/corpus-v2/).
    public static KnowledgeSources FromGeneration(GenerationStore g, LegalGraph? graph = null)
    {
        var gdir = Path.Combine(g.SiteRoot, "generations", g.GenerationId);
        var loaded = g.Documents.Values.SelectMany(d => d.Candidates).Select(c => c.CandidateId).ToHashSet(StringComparer.Ordinal);
        var cands = ReadJsonl(Path.Combine(gdir, "records", "candidates.jsonl"))
            .Where(c => c["candidate_id"] is JsonValue v && v.TryGetValue<string>(out var id) && loaded.Contains(id)).ToList();
        var v1 = new KnowledgeSources
        {
            Candidates = cands, ProvisionVersions = g.ProvisionVersions.Select(v => v.Raw).ToList(), Graph = graph ?? GraphBuilder.Build(g),
        };
        return FromExchange(Path.Combine(gdir, "corpus-v2"), v1);
    }
}

public sealed record TableRows(TableSpec Spec, byte[] Bytes, long RowCount, string RowsSha256);

public sealed record ComponentRows(string Kind, IReadOnlyList<TableRows> Tables, string ResultDigest, long ResultCount);

public static class KnowledgeRows
{
    // ------------------------------------------------------------------ derivation

    static JsonNode? Req(JsonObject o, string key, string where) =>
        o.TryGetPropertyValue(key, out var v) ? v?.DeepClone() : throw new KnowledgeRowsException("KR_ROWS_SOURCE_INVALID", $"{where}: missing '{key}'");
    static JsonNode? Opt(JsonObject? o, string key) => o is not null && o.TryGetPropertyValue(key, out var v) ? v?.DeepClone() : null;
    static JsonObject Obj(JsonObject o, string key, string where) =>
        o[key] as JsonObject ?? throw new KnowledgeRowsException("KR_ROWS_SOURCE_INVALID", $"{where}: '{key}' is not an object");
    static string? Str(JsonNode? n) => n is JsonValue v && v.TryGetValue<string>(out var s) ? s : null;
    static bool Truthy(JsonNode? n) => n switch
    {
        null => false,
        JsonValue v when v.GetValueKind() == JsonValueKind.False => false,
        JsonValue v when v.GetValueKind() == JsonValueKind.True => true,
        JsonValue v when v.GetValueKind() == JsonValueKind.String => v.GetValue<string>().Length > 0,
        JsonValue v when v.GetValueKind() == JsonValueKind.Number => Num(v) != 0,
        JsonArray a => a.Count > 0,
        JsonObject o => o.Count > 0,
        _ => true,
    };
    static double Num(JsonNode v) => v is JsonValue jv && jv.TryGetValue<JsonElement>(out var el) ? el.GetDouble()
        : v.AsValue().TryGetValue<int>(out var i) ? i : v.AsValue().TryGetValue<long>(out var l) ? l : v.GetValue<double>();
    static string Sha(JsonObject record) => CanonicalJson.RecordSha256(record);
    static JsonValue? V(string? s) => s is null ? null : JsonValue.Create(s);
    static JsonValue? V(int? i) => i is null ? null : JsonValue.Create(i.Value);

    /// Derive one table's rows (unordered) from the authoritative records.
    public static List<JsonObject> DeriveTable(string table, KnowledgeSources src)
    {
        switch (table)
        {
            case "document_identities":
                return src.Identities.Select(d =>
                {
                    var w = "identity"; var wi = Obj(d, "work_identity", w); var re = Obj(d, "research_eligibility", w);
                    var gref = Req(wi, "graph_node_ref", w);
                    return new JsonObject
                    {
                        ["doc_id"] = Req(d, "doc_id", w), ["source_copy_sha256"] = Req(Obj(d, "source_copy", w), "sha256", w),
                        ["corpus_generation_id"] = Req(d, "corpus_generation_id", w),
                        ["representation_kind"] = Req(Obj(d, "representation", w), "representation_kind", w), ["work_kind"] = Req(wi, "work_kind", w),
                        ["graph_node_ref"] = gref is JsonValue gv && gv.GetValueKind() == JsonValueKind.String ? gref : null,   // UNRESOLVED objects -> NULL
                        ["research_state"] = Req(re, "state", w), ["quoting_permitted"] = Req(re, "quoting_permitted", w), ["record_sha256"] = Sha(d),
                    };
                }).ToList();
            case "evidence_anchors":
                return src.Anchors.Select(a =>
                {
                    var w = "anchor"; var loc = Obj(a, "locator", w);
                    return new JsonObject
                    {
                        ["anchor_id"] = Req(a, "anchor_id", w), ["doc_id"] = Req(a, "doc_id", w), ["original_sha256"] = Req(a, "original_sha256", w),
                        ["representation_sha256"] = Req(a, "representation_sha256", w), ["derivative_text_sha256"] = Opt(a, "derivative_text_sha256"),
                        ["locator_kind"] = Req(loc, "kind", w), ["physical_page"] = Opt(loc, "physical_page"), ["image_sequence_id"] = Opt(loc, "image_sequence_id"),
                        ["verification_state"] = Req(Obj(a, "verification", w), "state", w), ["quoting_permitted"] = Req(a, "quoting_permitted", w),
                        ["record_sha256"] = Sha(a),
                    };
                }).ToList();
            case "corpus_relationships":
                return src.Relationships.Select(r =>
                {
                    var w = "relationship"; var subj = Obj(r, "subject", w); var tgt = Obj(r, "target", w);
                    bool resolved = Truthy(Req(tgt, "resolved", w));
                    return new JsonObject
                    {
                        ["relationship_id"] = Req(r, "relationship_id", w), ["category"] = Req(r, "category", w), ["subject_doc_id"] = Req(subj, "doc_id", w),
                        ["subject_sha256"] = Req(subj, "source_copy_sha256", w),
                        ["target_node_id"] = resolved ? Opt(tgt, "node_id") : null, ["target_raw_reference"] = resolved ? null : Opt(tgt, "raw_reference"),
                        ["evidentiary_basis"] = Req(r, "evidentiary_basis", w), ["verification"] = Req(r, "verification", w),
                        ["has_legal_effect"] = Req(r, "has_legal_effect", w), ["record_sha256"] = Sha(r),
                    };
                }).ToList();
            case "taxonomy_nodes":
                return src.Taxonomy.Select(t =>
                {
                    var w = "taxonomy";
                    var parents = (t["parent_ids"] as JsonArray ?? throw new KnowledgeRowsException("KR_ROWS_SOURCE_INVALID", "taxonomy: parent_ids is not a list"))
                        .Select(p => Str(p) ?? throw new KnowledgeRowsException("KR_ROWS_SOURCE_INVALID", "taxonomy: parent id is not a string"))
                        .Order(CanonicalJson.CodePointComparer).Select(p => (JsonNode)JsonValue.Create(p)!).ToArray();
                    return new JsonObject
                    {
                        ["node_id"] = Req(t, "node_id", w), ["level"] = Req(t, "level", w), ["label"] = Req(t, "label", w),
                        ["parent_ids_json"] = CanonicalJson.Text(new JsonArray(parents)), ["instrument_code"] = Opt(t, "instrument_code"),
                        ["verification"] = Req(t, "verification", w), ["record_sha256"] = Sha(t),
                    };
                }).ToList();
            case "corpus_admissions":
            {
                // is_effective: not superseded by any admission of the population (supersedes_admission_id)
                var superseded = src.Admissions.Select(a => Str(a["supersedes_admission_id"])).Where(s => s is not null).ToHashSet(StringComparer.Ordinal);
                return src.Admissions.Select(a =>
                {
                    var w = "admission"; var subj = Obj(a, "subject", w);
                    var id = Req(a, "admission_id", w);
                    return new JsonObject
                    {
                        ["admission_id"] = id, ["doc_id"] = Req(subj, "doc_id", w), ["source_copy_sha256"] = Req(subj, "source_copy_sha256", w),
                        ["revision"] = Req(a, "revision", w), ["decision"] = Req(a, "decision", w), ["application_eligible"] = Req(a, "application_eligible", w),
                        ["service_scope"] = a.ContainsKey("service_scope") ? Opt(a, "service_scope") : JsonValue.Create("NONE"),
                        ["is_effective"] = !(Str(id) is { } s && superseded.Contains(s)), ["record_sha256"] = Sha(a),
                    };
                }).ToList();
            }
            case "candidates":
                return src.Candidates.Select(c =>
                {
                    var w = "candidate";
                    return new JsonObject
                    {
                        ["candidate_id"] = Req(c, "candidate_id", w), ["candidate_type"] = Req(c, "candidate_type", w), ["source_doc_id"] = Req(c, "source_doc_id", w),
                        ["status"] = Req(c, "status", w), ["capability_restriction"] = Req(c, "capability_restriction", w), ["record_sha256"] = Sha(c),
                    };
                }).ToList();
            case "provision_versions":
                return src.ProvisionVersions.Select(v =>
                {
                    var w = "provision_version";
                    return new JsonObject
                    {
                        ["version_id"] = Req(v, "version_id", w), ["family"] = Req(v, "family", w), ["provision"] = Req(v, "provision", w),
                        ["version_kind"] = Req(v, "version_kind", w), ["determination_state"] = Req(v, "determination_state", w), ["record_sha256"] = Sha(v),
                    };
                }).ToList();
            case "graph_nodes":
                return (src.Graph ?? throw NoGraph()).Nodes.Select(n => new JsonObject
                {
                    ["id"] = n.Id, ["kind"] = n.Kind, ["label"] = n.Label, ["doc_id"] = V(n.DocId), ["held"] = n.Held, ["page"] = V(n.Page),
                    ["family"] = V(n.Family), ["code"] = V(n.Code),
                }).ToList();
            case "graph_edges":
                return (src.Graph ?? throw NoGraph()).Edges.Select(e => new JsonObject
                {
                    ["id"] = e.Id, ["type"] = e.Type, ["from_id"] = e.From, ["to_id"] = e.To, ["origin"] = e.Origin, ["source_doc_id"] = V(e.SourceDocId),
                    ["page"] = V(e.Page), ["temporal_from"] = V(e.TemporalFrom), ["temporal_from_status"] = e.TemporalFromStatus, ["temporal_to"] = V(e.TemporalTo),
                    ["temporal_to_status"] = e.TemporalToStatus, ["verification"] = e.Verification, ["review_state"] = e.ReviewState,
                    ["uncertainty"] = e.Uncertainty, ["has_legal_effect"] = e.HasLegalEffect,
                }).ToList();
            default:
                throw new KnowledgeRowsException("KR_ROWS_TABLE_NOT_ALLOWLISTED", table);
        }
    }

    static KnowledgeRowsException NoGraph() => new("KR_ROWS_NOT_DERIVABLE_HERE", "graph rows need the generation's graph (GraphBuilder)");

    /// Canonical row-file bytes of one table, typed-checked: the writer never emits a row its own reader would reject.
    public static TableRows DeriveFile(string table, KnowledgeSources src)
    {
        var spec = KnowledgeAllowlist.Find(table) ?? throw new KnowledgeRowsException("KR_ROWS_TABLE_NOT_ALLOWLISTED", table);
        var rows = DeriveTable(table, src);
        for (int i = 0; i < rows.Count; i++)
            if (TypeIssue(spec, rows[i]) is { } why) throw new KnowledgeRowsException("KR_ROWS_TYPE", $"{table}: derived row {i + 1}: {why}");
        var bytes = RowFileBytes(spec, rows);
        var parsed = ReadRowFile(table, bytes);
        if (parsed.Issues.Count > 0) throw new KnowledgeRowsException(parsed.Issues[0].Code, $"{table}: derived rows: {parsed.Issues[0].Message}");
        return new TableRows(spec, bytes, rows.Count, CanonicalJson.Sha256Hex(bytes));
    }

    /// The writer: row files of both components (KNOWLEDGE_ROWS and GRAPH), per-table row_count and rows_sha256, and the
    /// component digests (arch §5).
    public static IReadOnlyList<ComponentRows> Derive(KnowledgeSources src, bool includeGraph = true)
    {
        var tables = KnowledgeAllowlist.Tables.Where(t => includeGraph || t.Owner != KnowledgeAllowlist.OwnerGraph)
            .Select(t => DeriveFile(t.Table, src)).ToList();
        return tables.GroupBy(t => t.Spec.Owner).OrderBy(g => g.Key, StringComparer.Ordinal)
            .Select(g => new ComponentRows(g.Key, g.ToList(), ComponentDigest(g.Select(t => (t.Spec.Table, t.RowCount, t.RowsSha256))), g.Sum(t => t.RowCount)))
            .ToList();
    }

    /// Writes `accelerators/rows/<table>.jsonl` (KNOWLEDGE_ROWS) and `accelerators/graph/<table>.jsonl` (GRAPH) under
    /// `releaseRoot`, each atomically (temp file, then rename).
    public static IReadOnlyList<ComponentRows> Write(string releaseRoot, KnowledgeSources src, bool includeGraph = true)
    {
        var comps = Derive(src, includeGraph);
        foreach (var t in comps.SelectMany(c => c.Tables))
        {
            var path = Path.Combine(releaseRoot, KnowledgeAllowlist.FilePath(t.Spec).Replace('/', Path.DirectorySeparatorChar));
            Directory.CreateDirectory(Path.GetDirectoryName(path)!);
            var tmp = path + ".tmp-" + Environment.ProcessId;
            File.WriteAllBytes(tmp, t.Bytes);
            File.Move(tmp, path, overwrite: true);
        }
        return comps;
    }

    /// Component digest (arch §5): sha256 over "table|row_count|rows_sha256\n" per table, tables in name order.
    public static string ComponentDigest(IEnumerable<(string Table, long RowCount, string RowsSha256)> tables)
    {
        var sb = new StringBuilder();
        foreach (var (t, n, sha) in tables.OrderBy(x => x.Table, StringComparer.Ordinal)) sb.Append(t).Append('|').Append(n).Append('|').Append(sha).Append('\n');
        return CanonicalJson.Sha256Hex(Encoding.UTF8.GetBytes(sb.ToString()));
    }

    public static int ComparePk(TableSpec spec, JsonObject a, JsonObject b)
    {
        foreach (var k in spec.PrimaryKey)
        {
            int c = CanonicalJson.CompareCodePoints(Str(a[k]), Str(b[k]));
            if (c != 0) return c;
        }
        return 0;
    }

    public static byte[] RowFileBytes(TableSpec spec, IEnumerable<JsonObject> rows)
    {
        var ordered = rows.ToList();
        ordered.Sort((a, b) => ComparePk(spec, a, b));
        using var ms = new MemoryStream();
        foreach (var r in ordered) { ms.Write(CanonicalJson.Bytes(r)); ms.WriteByte((byte)'\n'); }
        return ms.ToArray();
    }

    // ------------------------------------------------------------------ typed reader (before COPY)

    public sealed record ParsedRowFile(TableSpec? Spec, IReadOnlyList<JsonObject> Rows, IReadOnlyList<RowIssue> Issues);

    static readonly UTF8Encoding StrictUtf8 = new(false, true);

    /// knowledge_rows.row_file_issues: allowlisted table; every line UTF-8 JSON, an object, typed with exactly the
    /// allowlisted columns; no oversized row; unique primary key; canonical bytes in primary-key order.
    /// Stricter than the Python reference only where PostgreSQL could not store the value anyway (NUL in text, an
    /// integer outside int32): those are KR_ROWS_TYPE here.
    public static ParsedRowFile ReadRowFile(string table, ReadOnlySpan<byte> data)
    {
        var spec = KnowledgeAllowlist.Find(table);
        if (spec is null) return new(null, [], [new("KR_ROWS_TABLE_NOT_ALLOWLISTED", "table not on the application's allowlist", table)]);
        var issues = new List<RowIssue>();
        var rows = new List<JsonObject>();
        int n = 0, start = 0;
        while (start <= data.Length)
        {
            int rel = data[start..].IndexOf((byte)'\n');
            int end = rel < 0 ? data.Length : start + rel;
            var line = data[start..end];
            n++;
            start = end + 1;
            if (line.Length == 0) { if (rel < 0) break; continue; }
            var where = $"{table}:{n}";
            if (line.Length > KnowledgeAllowlist.MaxRowBytes) { issues.Add(new("KR_ROWS_OVERSIZED", "row exceeds the size limit", where)); }
            else
            {
                JsonNode? node;
                try
                {
                    if (line.StartsWith("﻿"u8)) throw new FormatException("byte order mark");
                    node = JsonNode.Parse(StrictUtf8.GetString(line));
                }
                catch (Exception) { issues.Add(new("KR_ROWS_MALFORMED", "row is not UTF-8 JSON", where)); goto next; }
                if (node is not JsonObject obj) { issues.Add(new("KR_ROWS_MALFORMED", "row is not a JSON object", where)); goto next; }
                string? why;
                try { why = TypeIssue(spec, obj); }
                catch (Exception) { why = "unreadable value"; }
                if (why is not null) { issues.Add(new("KR_ROWS_TYPE", $"row violates its typed definition (unknown, missing or mistyped column): {why}", where)); goto next; }
                rows.Add(obj);
            }
        next:
            if (rel < 0) break;
        }
        var keys = new HashSet<string>(StringComparer.Ordinal);
        foreach (var r in rows)
            if (!keys.Add(string.Join("\u0001", spec.PrimaryKey.Select(k => Str(r[k])))))
            { issues.Add(new("KR_ROWS_DUPLICATE_KEY", "duplicate primary key", table)); break; }
        if (issues.Count == 0)
        {
            try
            {
                if (!RowFileBytes(spec, rows).AsSpan().SequenceEqual(data))
                    issues.Add(new("KR_ROWS_NOT_CANONICAL", "rows not canonical or not in primary-key order", table));
            }
            catch (CanonicalException e) { issues.Add(new("KR_ROWS_NOT_CANONICAL", e.Message, table)); }
        }
        return new(spec, issues.Count == 0 ? rows : [], issues);
    }

    /// The table's $defs/<table>_row: exactly the columns, each with its type. Null when the row conforms.
    public static string? TypeIssue(TableSpec spec, JsonObject row)
    {
        foreach (var (k, _) in row)
            if (!spec.Columns.Any(c => c.Name == k)) return $"unknown column '{k}'";
        foreach (var c in spec.Columns)
        {
            if (!row.TryGetPropertyValue(c.Name, out var v)) return $"missing column '{c.Name}'";
            if (ValueIssue(c, v) is { } why) return $"column '{c.Name}': {why}";
        }
        return null;
    }

    static string? ValueIssue(ColumnSpec c, JsonNode? v)
    {
        var kind = v?.GetValueKind() ?? JsonValueKind.Null;
        if (kind == JsonValueKind.Null) return c.Nullable ? null : "null not allowed";
        switch (c.Type)
        {
            case ColType.Bool:
                return kind is JsonValueKind.True or JsonValueKind.False ? null : "not a boolean";
            case ColType.Int or ColType.IntNull or ColType.IntMin1 or ColType.IntMin1Null:
            {
                if (kind != JsonValueKind.Number) return "not an integer";
                double d = Num(v!);
                if (Math.Floor(d) != d || double.IsInfinity(d)) return "not an integer";
                if (d is > int.MaxValue or < int.MinValue) return "integer out of range";
                if (c.Type is ColType.IntMin1 or ColType.IntMin1Null && d < 1) return "below the minimum 1";
                return null;
            }
            default:
            {
                if (kind != JsonValueKind.String) return "not a string";
                var s = v!.GetValue<string>();
                if (s.Contains('\0')) return "NUL in text";
                int len = s.EnumerateRunes().Count();
                switch (c.Type)
                {
                    case ColType.Text: return len is >= 1 and <= KnowledgeAllowlist.MaxText ? null : "text length outside 1..2000";
                    case ColType.TextNull: return len <= KnowledgeAllowlist.MaxText ? null : "text longer than 2000";
                    case ColType.Sha or ColType.ShaNull: return s.Length == 64 && s.All(ch => ch is >= '0' and <= '9' or >= 'a' and <= 'f') ? null : "not a sha256";
                    case ColType.Enum: return c.Values.Contains(s) ? null : "value not allowed";
                    case ColType.Const: return s == c.Values[0] ? null : "value not allowed";
                    default: return "unknown type";
                }
            }
        }
    }

    // ------------------------------------------------------------------ re-derivation check

    /// ROWS_REDERIVE_COMPARE: the shipped (or exported) rows must equal the rows re-derived from the authoritative records.
    public static List<RowIssue> RederiveCompare(string table, ReadOnlySpan<byte> shipped, KnowledgeSources src)
    {
        byte[] want;
        try { want = DeriveFile(table, src).Bytes; }
        catch (KnowledgeRowsException e) { return [new(e.Code == "KR_ROWS_NOT_DERIVABLE_HERE" ? e.Code : "KR_ROWS_REDERIVE_FAILED", e.Message, table)]; }
        catch (CanonicalException e) { return [new("KR_ROWS_REDERIVE_FAILED", e.Message, table)]; }
        return want.AsSpan().SequenceEqual(shipped) ? [] : [new("KR_ROWS_REDERIVE_MISMATCH", "shipped rows differ from rows re-derived from the records", table)];
    }
}
