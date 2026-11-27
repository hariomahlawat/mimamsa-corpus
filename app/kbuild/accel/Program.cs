// C16 B02 stage S6 accelerator builder. Usage:
//   KBuildAccel --site <scratch site> --text-dir <dir> --index-dir <dir> --graph-out <dir> --build-time <ISO-8601 UTC> --out <summary.json>
// Builds, with the existing B1 code paths and nothing else:
//   * the ADR-0008 disk text store    (GenerationStore.Load with TextStoreOptions { Store = "disk" })
//   * the ADR-0007 disk lexical index (SearchIndex.Open; forward cache off so the result never depends on earlier builds)
//   * the C15 graph                    (GraphBuilder.Build), exported as raw JSON lines; the Python side canonicalises
//     them into allowlisted rows (KNOWLEDGE_ROWS_SCHEMA graph_nodes_row / graph_edges_row).
// built_utc is the pinned build time, so two builds from the same generation are byte-identical. No text is printed.
// It never opens a network connection and never embeds.
using System.Globalization;
using System.Text;
using System.Text.Json;
using Mimamsa.Core.Generation;
using Mimamsa.Core.Graph;
using Mimamsa.Core.Search;

string Arg(string n) { var i = Array.IndexOf(args, n); return i >= 0 && i + 1 < args.Length ? args[i + 1] : throw new ArgumentException($"{n} is required"); }
var site = Arg("--site");
var textDir = Arg("--text-dir");
var indexDir = Arg("--index-dir");
var graphOut = Arg("--graph-out");
var outPath = Arg("--out");
var buildTime = DateTimeOffset.Parse(Arg("--build-time"), CultureInfo.InvariantCulture, DateTimeStyles.AssumeUniversal);

void Log(string m) => Console.Error.WriteLine(m);
// AdoptShipped off: the build (S6) and its parity check (S9) always rebuild, never copy a shipped store.
var textOptions = new TextStoreOptions { Store = "disk", Dir = textDir, KeepPrevious = 0, BuildTimeUtc = buildTime, AdoptShipped = false };
var gen = GenerationStore.Load(site, null, textOptions, Log);
var ix = SearchIndex.Open(gen, indexDir, new SearchIndexOptions { UseForwardCache = false, KeepPrevious = 0, BuildTimeUtc = buildTime }, Log);
var graph = GraphBuilder.Build(gen);
if (graph.Edges.Any(e => !Verification.BuilderValues.Contains(e.Verification) || e.ReviewState != GraphBuilder.ReviewUnreviewed))
    throw new InvalidOperationException("the graph builder emitted a reviewed or verified edge");

Directory.CreateDirectory(graphOut);
var compact = new JsonSerializerOptions { WriteIndented = false };
void WriteLines(string file, IEnumerable<Dictionary<string, object?>> rows)
{
    using var w = new StreamWriter(Path.Combine(graphOut, file), false, new UTF8Encoding(false)) { NewLine = "\n" };
    foreach (var r in rows) w.WriteLine(JsonSerializer.Serialize(r, compact));
}
WriteLines("nodes.raw.jsonl", graph.Nodes.Select(n => new Dictionary<string, object?>
{
    ["id"] = n.Id, ["kind"] = n.Kind, ["label"] = n.Label, ["doc_id"] = n.DocId, ["held"] = n.Held, ["page"] = n.Page,
    ["family"] = n.Family, ["code"] = n.Code,
}));
WriteLines("edges.raw.jsonl", graph.Edges.Select(e => new Dictionary<string, object?>
{
    ["id"] = e.Id, ["type"] = e.Type, ["from_id"] = e.From, ["to_id"] = e.To, ["origin"] = e.Origin, ["source_doc_id"] = e.SourceDocId,
    ["page"] = e.Page, ["temporal_from"] = e.TemporalFrom, ["temporal_from_status"] = e.TemporalFromStatus, ["temporal_to"] = e.TemporalTo,
    ["temporal_to_status"] = e.TemporalToStatus, ["verification"] = e.Verification, ["review_state"] = e.ReviewState,
    ["uncertainty"] = e.Uncertainty, ["has_legal_effect"] = e.HasLegalEffect,
}));

var summary = new Dictionary<string, object?>
{
    ["generation_id"] = gen.GenerationId, ["documents"] = gen.Documents.Count, ["passages"] = ix.N,
    ["text_store_dir"] = gen.Text.StorePath is { } d ? Path.GetFileName(d) : null,
    ["index_dir"] = ix.IndexPath is { } p ? Path.GetFileName(p) : null,
    ["graph_builder_version"] = graph.BuilderVersion, ["graph_nodes"] = graph.Nodes.Count, ["graph_edges"] = graph.Edges.Count,
    ["graph_digest"] = GraphStore.Digest(graph),
};
File.WriteAllText(outPath, JsonSerializer.Serialize(summary, new JsonSerializerOptions { WriteIndented = true }));
(gen.Text as IDisposable)?.Dispose();
Microsoft.Data.Sqlite.SqliteConnection.ClearAllPools();
return 0;
