// C16 B03: knowledge-row derivation and the typed row reader, without a database. Cross-language golden tests against
// the Python reference (app/contract/mimamsa_contract/c16/{canonical,knowledge_rows}.py and its 2.1 fixtures).
using System.Runtime.CompilerServices;
using System.Text;
using System.Text.Json.Nodes;
using Mimamsa.Core.Graph;
using Mimamsa.Core.Knowledge;

namespace Mimamsa.Tests;

public static class Repo
{
    static string Here([CallerFilePath] string p = "") => p;
    /// Repository root, from this source file's path (tests run from bin/).
    public static string Root => Path.GetFullPath(Path.Combine(Path.GetDirectoryName(Here())!, "..", "..", "..", ".."));
    public static string P(params string[] parts) => Path.Combine([Root, .. parts]);
    public static string V21(params string[] parts) => Path.Combine([Root, "app", "contract", "fixtures", "c16", "v2_1", .. parts]);
}

public class KnowledgeRowsTests
{
    static readonly string[] PythonTables = ["document_identities", "evidence_anchors", "corpus_relationships", "taxonomy_nodes", "corpus_admissions"];

    public static KnowledgeSources FixtureSources(Mimamsa.Core.Generation.GenerationStore? v1 = null) =>
        KnowledgeSources.FromExchange(Repo.V21("exchange"), v1 is null ? null : KnowledgeSources.FromGeneration(v1));

    static byte[] Rows(string table) => File.ReadAllBytes(Repo.V21("knowledge_rows", "rows", table + ".jsonl"));
    static HashSet<string> Codes(IEnumerable<RowIssue> issues) => issues.Select(i => i.Code).ToHashSet();

    [Fact]
    public void CanonicalJsonMatchesPythonGoldenVectors()
    {
        var path = Repo.P("app", "b1", "tests", "Mimamsa.Tests", "canonical_vectors.jsonl");
        int n = 0;
        foreach (var line in File.ReadAllLines(path))
        {
            var c = JsonNode.Parse(line)!;
            var input = c["input"]!.GetValue<string>();
            var want = c["canonical"]?.GetValue<string>();
            string? got;
            try { got = CanonicalJson.Text(JsonNode.Parse(input)); }
            catch (Exception) { got = null; }
            Assert.True(want == got, $"case {input}: want {want ?? "<refused>"}, got {got ?? "<refused>"}");
            n++;
        }
        Assert.True(n >= 20);
    }

    [Fact]
    public void CanonicalBytesEqualPythonOnTheFixtureCorpus()
    {
        var files = Directory.EnumerateFiles(Repo.P("app", "contract", "fixtures", "c16", "positive", "exchange"), "*.jsonl")
            .Concat(Directory.EnumerateFiles(Repo.V21("exchange"), "*.jsonl"))
            .Concat(Directory.EnumerateFiles(Repo.V21("knowledge_rows", "rows"), "*.jsonl")).ToList();
        Assert.True(files.Count >= 17);
        long lines = 0;
        foreach (var f in files)
        {
            var data = File.ReadAllBytes(f);
            using var ms = new MemoryStream();
            foreach (var line in Encoding.UTF8.GetString(data).Split('\n').Where(l => l.Length > 0))
            {
                ms.Write(CanonicalJson.Bytes(JsonNode.Parse(line))); ms.WriteByte((byte)'\n'); lines++;
            }
            Assert.True(data.AsSpan().SequenceEqual(ms.ToArray()), f);
        }
        Assert.True(lines > 50);
    }

    [Fact]
    public void ApplicationAllowlistEqualsTheContractFixtureAndSchema()
    {
        var fixture = JsonNode.Parse(File.ReadAllText(Repo.V21("knowledge_rows", "allowlist.json")))!.AsObject();
        Assert.Equal(CanonicalJson.Text(fixture), CanonicalJson.Text(KnowledgeAllowlist.Document()));
        Assert.Empty(KnowledgeAllowlist.AllowlistIssues(fixture));

        // I-2: the graph tables cannot be moved to KNOWLEDGE_ROWS, nor another table to GRAPH
        var moved = fixture.DeepClone().AsObject();
        moved["tables"]!.AsArray().First(t => t!["table"]!.GetValue<string>() == "graph_edges")!["owner_component"] = "KNOWLEDGE_ROWS";
        Assert.Contains("KR_ROWS_ALLOWLIST", Codes(KnowledgeAllowlist.AllowlistIssues(moved)));
        var grabbed = fixture.DeepClone().AsObject();
        grabbed["tables"]!.AsArray().First(t => t!["table"]!.GetValue<string>() == "candidates")!["owner_component"] = "GRAPH";
        Assert.Contains("KR_ROWS_ALLOWLIST", Codes(KnowledgeAllowlist.AllowlistIssues(grabbed)));
        // N39: a table the application does not have is never loadable, whatever an allowlist says
        var extra = fixture.DeepClone().AsObject();
        extra["tables"]!.AsArray().Add(new JsonObject { ["table"] = "app_users", ["owner_component"] = "KNOWLEDGE_ROWS", ["primary_key"] = new JsonArray("user_id"), ["row_schema"] = "#/$defs/app_users_row", ["derivation"] = "DOTNET_B03" });
        Assert.Contains("KR_ROWS_TABLE_NOT_ALLOWLISTED", Codes(KnowledgeAllowlist.AllowlistIssues(extra)));
        Assert.Contains("KR_ROWS_TABLE_NOT_ALLOWLISTED", Codes(KnowledgeRows.ReadRowFile("app_users", "{}\n"u8).Issues));

        // the typed columns are exactly the contract schema's row definitions, in `required` order
        var schema = JsonNode.Parse(File.ReadAllText(Repo.P("app", "contract", "schemas", "c16", "KNOWLEDGE_ROWS_SCHEMA.json")))!;
        foreach (var t in KnowledgeAllowlist.Tables)
        {
            var def = schema["$defs"]![$"{t.Table}_row"]!;
            Assert.False(def["additionalProperties"]!.GetValue<bool>());
            Assert.Equal(def["required"]!.AsArray().Select(x => x!.GetValue<string>()), t.Columns.Select(c => c.Name));
            Assert.Equal(def["properties"]!.AsObject().Select(p => p.Key).Order(), t.Columns.Select(c => c.Name).Order());
            foreach (var c in t.Columns)
            {
                var p = def["properties"]![c.Name]!;
                var r = p["$ref"]?.GetValue<string>();
                var type = p["type"] is JsonArray ta ? string.Join(",", ta.Select(x => x!.GetValue<string>())) : p["type"]?.GetValue<string>();
                var expect = c.Type switch
                {
                    ColType.Text => r == "#/$defs/text", ColType.TextNull => r == "#/$defs/text_null", ColType.Sha => r == "#/$defs/sha",
                    ColType.ShaNull => r == "#/$defs/sha_null", ColType.Bool => type == "boolean", ColType.IntNull => type == "integer,null" && p["minimum"] is null,
                    ColType.IntMin1Null => type == "integer,null" && p["minimum"]!.GetValue<int>() == 1, ColType.IntMin1 => type == "integer" && p["minimum"]!.GetValue<int>() == 1,
                    ColType.Enum => p["enum"]!.AsArray().Select(x => x!.GetValue<string>()).SequenceEqual(c.Values),
                    ColType.Const => p["const"]!.GetValue<string>() == c.Values[0], _ => false,
                };
                Assert.True(expect, $"{t.Table}.{c.Name}");
            }
        }
    }

    [Fact]
    public void DerivationMatchesThePythonReferenceByteForByte()
    {
        var src = FixtureSources();
        foreach (var t in PythonTables)
        {
            var d = KnowledgeRows.DeriveFile(t, src);
            Assert.True(d.Bytes.AsSpan().SequenceEqual(Rows(t)), t);
            Assert.True(d.RowCount > 0, t);
            Assert.Empty(KnowledgeRows.ReadRowFile(t, Rows(t)).Issues);
            Assert.Empty(KnowledgeRows.RederiveCompare(t, Rows(t), src));
        }
    }

    [Fact]
    public void DerivationIsDeterministicOnTheSyntheticGeneration()
    {
        // two independent loads of the generation, two derivations: identical bytes, digests and counts
        var a = KnowledgeRows.Derive(FixtureSources(Syn.Gen));
        var b = KnowledgeRows.Derive(FixtureSources(Mimamsa.Core.Generation.GenerationStore.Load(Syn.Site)));
        Assert.Equal(2, a.Count);
        Assert.Equal(["GRAPH", "KNOWLEDGE_ROWS"], a.Select(c => c.Kind));
        for (int i = 0; i < a.Count; i++)
        {
            Assert.Equal(a[i].ResultDigest, b[i].ResultDigest);
            Assert.Equal(a[i].Tables.Select(t => t.RowsSha256), b[i].Tables.Select(t => t.RowsSha256));
        }
        var tables = a.SelectMany(c => c.Tables).ToDictionary(t => t.Spec.Table);
        Assert.Equal(9, tables.Count);
        var graph = GraphBuilder.Build(Syn.Gen);
        Assert.Equal(graph.Nodes.Count, tables["graph_nodes"].RowCount);
        Assert.Equal(graph.Edges.Count, tables["graph_edges"].RowCount);
        Assert.True(tables["candidates"].RowCount > 0 && tables["provision_versions"].RowCount > 0);
        Assert.Equal(Syn.Gen.Documents.Values.Sum(d => d.Candidates.Count), tables["candidates"].RowCount);
        Assert.Equal(KnowledgeRows.ComponentDigest(a[1].Tables.Select(t => (t.Spec.Table, t.RowCount, t.RowsSha256))), a[1].ResultDigest);

        // the writer's files: canonical, typed, and re-derivable
        var root = Path.Combine(Path.GetTempPath(), "mimamsa-c16b03-rows-" + Guid.NewGuid().ToString("N")[..8]);
        try
        {
            var written = KnowledgeRows.Write(root, FixtureSources(Syn.Gen));
            foreach (var t in written.SelectMany(c => c.Tables))
            {
                var rel = KnowledgeAllowlist.FilePath(t.Spec);
                Assert.StartsWith(t.Spec.Owner == "GRAPH" ? "accelerators/graph/" : "accelerators/rows/", rel);
                var bytes = File.ReadAllBytes(Path.Combine(root, rel));
                Assert.Equal(t.RowsSha256, CanonicalJson.Sha256Hex(bytes));
                Assert.Empty(KnowledgeRows.ReadRowFile(t.Spec.Table, bytes).Issues);
                Assert.Empty(KnowledgeRows.RederiveCompare(t.Spec.Table, bytes, FixtureSources(Syn.Gen)));
                Assert.True(bytes.Length == 0 || bytes[^1] == (byte)'\n');
                Assert.DoesNotContain((byte)'\r', bytes);
            }
        }
        finally { if (Directory.Exists(root)) Directory.Delete(root, true); }
    }

    /// The real sample (skipped without MIMAMSA_SAMPLE_SITE): candidates, provision versions and the graph derive cleanly.
    [Fact]
    public void DerivationOnTheRealSample()
    {
        if (Environment.GetEnvironmentVariable("MIMAMSA_SAMPLE_SITE") is not { Length: > 0 } s || !Directory.Exists(s)) return;
        var g = TestText.Load(s);
        var src = KnowledgeSources.FromGeneration(g);
        var comps = KnowledgeRows.Derive(src);
        var t = comps.SelectMany(c => c.Tables).ToDictionary(x => x.Spec.Table);
        Assert.Equal(g.Documents.Values.Sum(d => d.Candidates.Count), t["candidates"].RowCount);
        Assert.Equal(g.ProvisionVersions.Count, t["provision_versions"].RowCount);
        Assert.True(t["graph_edges"].RowCount > 0);
        Assert.Equal(comps.Select(c => c.ResultDigest), KnowledgeRows.Derive(src).Select(c => c.ResultDigest));
    }

    public static IEnumerable<object[]> Negatives()
    {
        static object[] C(string name, string table, Func<byte[], byte[]> make, string code) => [name, table, make, code];
        static byte[] Rep(byte[] d, string a, string b) { var s = Encoding.UTF8.GetString(d); int i = s.IndexOf(a, StringComparison.Ordinal); return Encoding.UTF8.GetBytes(s[..i] + b + s[(i + a.Length)..]); }
        static byte[] Lines(byte[] d) => d;
        // the Python reference's negatives (test_row_file_negatives) ...
        yield return C("table not allowlisted", "app_users", Lines, "KR_ROWS_TABLE_NOT_ALLOWLISTED");
        yield return C("extra column", "document_identities", d => Rep(d, "\"doc_id\"", "\"extra\":\"x\",\"doc_id\""), "KR_ROWS_TYPE");
        yield return C("mistyped value", "document_identities", d => Rep(d, "\"quoting_permitted\":true", "\"quoting_permitted\":\"yes\""), "KR_ROWS_TYPE");
        yield return C("duplicate key", "document_identities", d => [.. d, .. d.AsSpan(0, Array.IndexOf(d, (byte)'\n') + 1)], "KR_ROWS_DUPLICATE_KEY");
        yield return C("reordered rows", "document_identities",
            d => Encoding.UTF8.GetBytes(string.Join("\n", Encoding.UTF8.GetString(d).TrimEnd('\n').Split('\n').Reverse()) + "\n"), "KR_ROWS_NOT_CANONICAL");
        yield return C("non-object line", "document_identities", d => [.. "[1,2]\n"u8.ToArray(), .. d], "KR_ROWS_MALFORMED");
        yield return C("SQL text in a value", "document_identities", d => Rep(d, "\"doc_id\":\"", "\"doc_id\":\"x'; DROP TABLE site.app_users; --"), "KR_ROWS_NOT_CANONICAL");
        // ... and more
        yield return C("missing column", "document_identities", d => Rep(d, "\"quoting_permitted\":true,", ""), "KR_ROWS_TYPE");
        yield return C("null in a required column", "document_identities", d => Rep(d, "\"work_kind\":\"", "\"work_kind\":null,\"x\":\""), "KR_ROWS_TYPE");
        yield return C("NUL in text", "document_identities", d => Rep(d, "\"doc_id\":\"", "\"doc_id\":\"\\u0000"), "KR_ROWS_TYPE");
        yield return C("text over 2000", "document_identities", d => Rep(d, "\"doc_id\":\"", "\"doc_id\":\"" + new string('a', 2001)), "KR_ROWS_TYPE");
        yield return C("bad sha", "document_identities", d => Rep(d, "\"record_sha256\":\"", "\"record_sha256\":\"Z"), "KR_ROWS_TYPE");
        yield return C("integer below minimum", "corpus_admissions", d => Rep(d, "\"revision\":1", "\"revision\":0"), "KR_ROWS_TYPE");
        yield return C("integer as float text", "corpus_admissions", d => Rep(d, "\"revision\":1", "\"revision\":1.0"), "KR_ROWS_NOT_CANONICAL");
        yield return C("non-NFC string", "document_identities", d => Rep(d, "\"doc_id\":\"", "\"doc_id\":\"é"), "KR_ROWS_NOT_CANONICAL");
        yield return C("whitespace", "document_identities", d => Rep(d, "\"doc_id\":", "\"doc_id\": "), "KR_ROWS_NOT_CANONICAL");
        yield return C("CRLF", "document_identities", d => Rep(d, "\n", "\r\n"), "KR_ROWS_NOT_CANONICAL");
        yield return C("blank line", "document_identities", d => [.. "\n"u8.ToArray(), .. d], "KR_ROWS_NOT_CANONICAL");
        yield return C("no final LF", "document_identities", d => d[..^1], "KR_ROWS_NOT_CANONICAL");
        yield return C("byte order mark", "document_identities", d => [0xEF, 0xBB, 0xBF, .. d], "KR_ROWS_MALFORMED");
        yield return C("invalid UTF-8", "document_identities", d => [.. "{\"doc_id\":\"\xff\"}\n"u8.ToArray().Select(b => b == 0xC3 ? (byte)0xFF : b), .. d], "KR_ROWS_MALFORMED");
        yield return C("oversized row", "document_identities", d => [.. Encoding.UTF8.GetBytes("{\"doc_id\":\"" + new string('a', KnowledgeAllowlist.MaxRowBytes) + "\"}\n"), .. d], "KR_ROWS_OVERSIZED");
        yield return C("SQL as a column name", "document_identities", d => Rep(d, "\"doc_id\"", "\"doc_id\\\"; DROP TABLE x; --\":1,\"doc_id\""), "KR_ROWS_TYPE");
    }

    [Theory]
    [MemberData(nameof(Negatives))]
    public void RowFileNegativesAreRejectedBeforeCopy(string name, string table, Func<byte[], byte[]> make, string code)
    {
        var data = make(Rows("document_identities") is var d && table == "corpus_admissions" ? Rows("corpus_admissions") : d);
        var r = KnowledgeRows.ReadRowFile(table, data);
        Assert.True(Codes(r.Issues).Contains(code), $"{name}: want {code}, got [{string.Join(", ", r.Issues)}]");
        Assert.Empty(r.Rows);
    }

    [Fact]
    public void GraphEdgeRowsAcceptBuilderValuesOnly()
    {
        var g = KnowledgeRows.DeriveFile("graph_edges", FixtureSources(Syn.Gen)).Bytes;
        Assert.Empty(KnowledgeRows.ReadRowFile("graph_edges", g).Issues);
        foreach (var (a, b) in new[] { ("\"verification\":\"CANDIDATE\"", "\"verification\":\"LEGAL_REVIEWED\""),
                                       ("\"verification\":\"EXTRACTED_STRUCTURE\"", "\"verification\":\"DOCUMENTARY_CHECKED\""),
                                       ("\"review_state\":\"UNREVIEWED\"", "\"review_state\":\"REVIEWED\"") })
        {
            var s = Encoding.UTF8.GetString(g);
            if (!s.Contains(a)) continue;
            var bad = Encoding.UTF8.GetBytes(s.Replace(a, b));
            Assert.Contains("KR_ROWS_TYPE", Codes(KnowledgeRows.ReadRowFile("graph_edges", bad).Issues));
        }
    }

    [Fact]
    public void WellFormedRowThatIsNotTrueFailsReDerivation()
    {
        var spec = KnowledgeAllowlist.Find("corpus_admissions")!;
        var rows = Encoding.UTF8.GetString(Rows("corpus_admissions")).Split('\n').Where(l => l.Length > 0).Select(l => JsonNode.Parse(l)!.AsObject()).ToList();
        rows[0]["application_eligible"] = !rows[0]["application_eligible"]!.GetValue<bool>();
        var data = KnowledgeRows.RowFileBytes(spec, rows);
        Assert.Empty(KnowledgeRows.ReadRowFile("corpus_admissions", data).Issues);                        // well-formed ...
        Assert.Contains("KR_ROWS_REDERIVE_MISMATCH", Codes(KnowledgeRows.RederiveCompare("corpus_admissions", data, FixtureSources())));  // ... but not true
        // graph rows cannot be re-derived without the generation's graph: fail closed
        Assert.Contains("KR_ROWS_NOT_DERIVABLE_HERE", Codes(KnowledgeRows.RederiveCompare("graph_nodes", ""u8, FixtureSources())));
    }
}
