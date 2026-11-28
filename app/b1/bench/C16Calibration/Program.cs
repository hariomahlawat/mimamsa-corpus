// C16 Stage 3 S3-B calibration study for the B04 sampled checks. Usage:
//   dotnet C16Calibration.dll --site <site> --work <dir> --out <calibration.json>
//       [--model-dir <dir> --model-sha <sha> --pack-dir <central pack dir>] [--instances 20] [--seeds 100] [--threads 6]
// Measures, with the production verifiers (Mimamsa.Core.ComponentVerification):
//   * conditional detection: the chance a check fails when a corrupted unit IS in its sample (S = whole population, or a
//     release id found whose sample includes the unit), per corruption type, with digests re-pinned to the tampered
//     content (a consistent rewrite: the signed-inventory and manifest checks pass);
//   * inclusion: the chance a seeded sample of size S includes at least one of k corrupted units, simulated with the real
//     sampler on the real populations and on synthetic populations up to 290,000 documents, beside the hypergeometric value;
//   * false rejects: clean components over many release ids and sizes (EXACT checks) and the measured re-embedding
//     difference distribution of the real model (the spot tolerance);
//   * cost per sample size (wall time on this host) and the fixed full-pass costs.
// It writes evidence only. Nothing here sets a contract value: proposals go to the owner (OD-12, FG-CALIBRATED-SAMPLES).
using System.Diagnostics;
using System.Globalization;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using Microsoft.Data.Sqlite;
using Mimamsa.Core.ComponentVerification;
using Mimamsa.Core.Generation;
using Mimamsa.Core.Graph;
using Mimamsa.Core.Knowledge;
using Mimamsa.Core.Search;
using Mimamsa.Hybrid;

string? Opt(string n) { var i = Array.IndexOf(args, n); return i >= 0 && i + 1 < args.Length ? args[i + 1] : null; }
int IntOpt(string n, int d) => Opt(n) is { } s ? int.Parse(s, CultureInfo.InvariantCulture) : d;
void Log(string m) => Console.Error.WriteLine($"[{DateTime.Now:HH:mm:ss}] {m}");
try { Process.GetCurrentProcess().PriorityClass = ProcessPriorityClass.BelowNormal; } catch (Exception) { }
var work = Path.GetFullPath(Opt("--work")!); Directory.CreateDirectory(work);
int instances = IntOpt("--instances", 20), seeds = IntOpt("--seeds", 100), threads = IntOpt("--threads", Math.Max(1, Environment.ProcessorCount / 2));
var g = GenerationStore.Load(Opt("--site")!, null, TextStoreOptions.Memory, null);
var docs = SearchIndex.IndexedDocuments(g);
var outp = new JsonObject
{
    ["study"] = "C16 S3-B B04 sampled-check calibration", ["generated_utc"] = DateTime.UtcNow.ToString("O"),
    ["host"] = new JsonObject { ["logical_cpus"] = Environment.ProcessorCount, ["os"] = Environment.OSVersion.ToString(), ["threads_used"] = threads },
    ["population"] = new JsonObject { ["generation"] = g.GenerationId, ["documents"] = g.Documents.Count, ["indexed_documents"] = docs.Count,
        ["passages"] = docs.Sum(d => d.Passages.Count), ["by_type"] = new JsonObject(docs.GroupBy(d => d.DocType).OrderBy(x => x.Key).Select(x => KeyValuePair.Create(x.Key, (JsonNode?)x.Count()))) },
    ["note"] = "Evidence for owner decision only. No contract value is changed; production keeps refusing (OD-C16-UNCALIBRATED-PRODUCTION).",
};
double Median(IEnumerable<double> xs) { var a = xs.Order().ToArray(); return a.Length == 0 ? double.NaN : a.Length % 2 == 1 ? a[a.Length / 2] : (a[a.Length / 2 - 1] + a[a.Length / 2]) / 2; }
double Hyper(long n, long k, long s) { if (k <= 0) return 0; s = Math.Min(s, n); if (n - k < s) return 1; double p = 1; for (long i = 0; i < s; i++) p *= (double)(n - k - i) / (n - i); return 1 - p; }
JsonArray Arr(IEnumerable<JsonNode?> xs) => new(xs.ToArray());

// ============================================================ 1. inclusion (real populations and synthetic scale)
var strataDocs = docs.GroupBy(d => d.DocType, StringComparer.Ordinal).ToDictionary(x => x.Key, x => x.Select(d => d.DocId).ToList(), StringComparer.Ordinal);
var typeShare = strataDocs.ToDictionary(kv => kv.Key, kv => (double)kv.Value.Count / docs.Count);
int[] sizes = [1, 4, 16, 32, 64, 128, 256, 512];
JsonObject Inclusion(Dictionary<string, List<string>> strata, int k, int nSeeds, string check)
{
    var all = strata.Values.SelectMany(x => x).ToList();
    var o = new JsonObject { ["population"] = all.Count, ["corrupted"] = k, ["seeds"] = nSeeds };
    var rows = new JsonArray();
    var rnd = new Random(12345);
    // A stratified sample of size s is the first s members of the seed's round-robin order (B04Sampling.Stratified), so the
    // order is computed once per seed and a corruption is included at size s iff its best rank is < s. Cross-checked
    // against B04Sampling.Stratified itself on the first seed.
    var hits = new int[sizes.Length];
    var names = strata.Keys.Order(StringComparer.Ordinal).ToList();
    for (int r = 0; r < nSeeds; r++)
    {
        var rid = $"study-{r}";
        var queues = names.Select(nm => strata[nm].Select(m => (m, sc: B04Sampling.Score(rid, check, m))).ToList()).ToList();
        foreach (var q in queues) q.Sort((x, y) => x.sc.AsSpan().SequenceCompareTo(y.sc) is var c and not 0 ? c : string.CompareOrdinal(x.m, y.m));
        var rank = new Dictionary<string, int>(all.Count, StringComparer.Ordinal);
        int pos = 0;
        for (int depth = 0; queues.Any(q => depth < q.Count); depth++)
            foreach (var q in queues) if (depth < q.Count) rank[q[depth].m] = pos++;
        if (r == 0)
            foreach (var s in new[] { 4, 16 }.Where(s => s <= all.Count))
                if (!B04Sampling.Stratified(rid, check, strata, s).ToHashSet().SetEquals(rank.Where(kv => kv.Value < s).Select(kv => kv.Key)))
                    throw new InvalidOperationException("prefix property does not hold");
        var bad = Enumerable.Range(0, k).Select(_ => all[rnd.Next(all.Count)]).Distinct().ToList();
        int best = bad.Min(b => rank[b]);
        for (int i = 0; i < sizes.Length; i++) if (best < sizes[i]) hits[i]++;
    }
    for (int i = 0; i < sizes.Length; i++)
        if (sizes[i] <= all.Count)
            rows.Add(new JsonObject { ["sample"] = sizes[i], ["measured"] = Math.Round((double)hits[i] / nSeeds, 4), ["hypergeometric"] = Math.Round(Hyper(all.Count, k, sizes[i]), 4) });
    o["by_sample_size"] = rows;
    return o;
}
var incl = new JsonObject();
Log("inclusion: real sample");
incl["real_documents_k1"] = Inclusion(strataDocs, 1, seeds, "SAMPLED_POSTINGS_REDERIVE");
incl["real_documents_k1pct"] = Inclusion(strataDocs, Math.Max(1, docs.Count / 100), seeds, "SAMPLED_POSTINGS_REDERIVE");
incl["real_documents_k5pct"] = Inclusion(strataDocs, Math.Max(1, docs.Count / 20), seeds, "SAMPLED_POSTINGS_REDERIVE");
foreach (var n in new[] { 2_900, 29_000, 290_000 })
{
    Log($"inclusion: synthetic {n}");
    var syn = typeShare.ToDictionary(kv => kv.Key, kv => Enumerable.Range(0, (int)Math.Round(kv.Value * n)).Select(i => $"syn-{kv.Key}-{i}").ToList(), StringComparer.Ordinal);
    int ns = n >= 290_000 ? Math.Min(seeds, 40) : seeds;
    incl[$"synthetic_{n}_k1pct"] = Inclusion(syn, n / 100, ns, "SAMPLED_REBUILD_PARITY");
    incl[$"synthetic_{n}_k01pct"] = Inclusion(syn, Math.Max(1, n / 1000), ns, "SAMPLED_REBUILD_PARITY");
}
outp["inclusion"] = incl;

// ============================================================ 2. LEXICAL_INDEX
Log("lexical: building the reference index");
var lexRoot = Path.Combine(work, "lex"); if (Directory.Exists(lexRoot)) Directory.Delete(lexRoot, true);
var ixDir = SearchIndex.Open(g, Path.Combine(lexRoot, "central"), new SearchIndexOptions { UseForwardCache = false, KeepPrevious = 0, BuildTimeUtc = DateTimeOffset.Parse("2026-11-28T00:00:00Z") }).IndexPath!;
SqliteConnection.ClearAllPools();
int bigN = docs.Count + 1;
string Sha(string p) => Convert.ToHexStringLower(SHA256.HashData(File.ReadAllBytes(p)));
void Rehash(string dir)
{
    SqliteConnection.ClearAllPools();
    var mp = Path.Combine(dir, "MANIFEST.json"); var m = JsonNode.Parse(File.ReadAllText(mp))!.AsObject();
    m["file_sha256"] = Sha(Path.Combine(dir, "search.sqlite")); m["file_bytes"] = new FileInfo(Path.Combine(dir, "search.sqlite")).Length;
    File.WriteAllText(mp, m.ToJsonString());
}
string Copy(string src, string name) { var d = Path.Combine(lexRoot, name); if (Directory.Exists(d)) { SqliteConnection.ClearAllPools(); Directory.Delete(d, true); } Directory.CreateDirectory(d); foreach (var f in Directory.GetFiles(src)) File.Copy(f, Path.Combine(d, Path.GetFileName(f))); return d; }
static void Put(List<byte> b, uint v) { while (v >= 0x80) { b.Add((byte)(v | 0x80)); v >>= 7; } b.Add((byte)v); }
static uint Get(byte[] b, ref int i) { uint v = 0; int sh = 0; while (true) { byte x = b[i++]; v |= (uint)(x & 0x7F) << sh; if (x < 0x80) return v; sh += 7; } }
static List<(int P, int[] Pos)> Decode(byte[] b, int df) { var l = new List<(int, int[])>(); int i = 0, p = 0; for (int k = 0; k < df; k++) { p += (int)Get(b, ref i); int n = (int)Get(b, ref i); var pos = new int[n]; int pr = 0; for (int j = 0; j < n; j++) { pr += (int)Get(b, ref i); pos[j] = pr; } l.Add((p, pos)); } return l; }
static byte[] Encode(List<(int P, int[] Pos)> l) { var b = new List<byte>(); int pp = 0; foreach (var (p, pos) in l) { Put(b, (uint)(p - pp)); pp = p; Put(b, (uint)pos.Length); int pr = 0; foreach (var x in pos) { Put(b, (uint)(x - pr)); pr = x; } } return b.ToArray(); }
SqliteConnection Rw(string db) { var c = new SqliteConnection(new SqliteConnectionStringBuilder { DataSource = db, Mode = SqliteOpenMode.ReadWrite, Pooling = false }.ToString()); c.Open(); return c; }
var refIx = SearchIndex.Build(g);   // memory engine: passage numbering identical to the disk index
// passage -> (term, positions) of its first queryable token, for targeted corruption
(string Term, int[] Pos)? TermOf(int p, bool queryable)
{
    var toks = Text.Tokenize(refIx.Passages[p].Text);
    var pick = toks.Take(12).FirstOrDefault(t => t.Term.Length > 2 && !Text.Stopwords.Contains(t.Term));
    if (!queryable) pick = toks.Count > 0 ? toks[toks.Count / 2] : default;
    if (pick.Term is null) return null;
    return (pick.Term, toks.Where(t => t.Term == pick.Term).Select(t => t.Position).ToArray());
}
// one corruption of one document (returns false when the document offers nothing to corrupt)
bool CorruptLex(string dir, string kind, int di, Random rnd)
{
    var db = Path.Combine(dir, "search.sqlite");
    var ps = refIx.DocPassages[di];
    if (ps.Length == 0) return false;
    int p = ps[rnd.Next(ps.Length)];
    using var c = Rw(db);
    if (kind == "LEN")
    {
        var blob = (byte[])new SqliteCommand($"SELECT lens FROM docs WHERE di = {di}", c).ExecuteScalar()!;
        int i = 0; var lens = new List<uint>(); while (i < blob.Length) lens.Add(Get(blob, ref i));
        lens[rnd.Next(lens.Count)] += 1;
        var nb = new List<byte>(); foreach (var x in lens) Put(nb, x);
        using var u = new SqliteCommand("UPDATE docs SET lens = $b WHERE di = $d", c); u.Parameters.AddWithValue("$b", nb.ToArray()); u.Parameters.AddWithValue("$d", di); u.ExecuteNonQuery();
        return true;
    }
    string term; List<(int P, int[] Pos)> list;
    if (kind == "EXTRA")
    {
        // a vocabulary term that does not occur in passage p gets a posting there
        var have = Text.Tokenize(refIx.Passages[p].Text).Select(t => t.Term).ToHashSet();
        var all = refIx.Postings.Keys.ToList();
        do term = all[rnd.Next(all.Count)]; while (have.Contains(term));
    }
    else { var t = TermOf(p, queryable: true); if (t is null) return false; term = t.Value.Term; }
    using (var q = new SqliteCommand("SELECT df, postings FROM terms WHERE term = $t", c))
    {
        q.Parameters.AddWithValue("$t", term);
        using var r = q.ExecuteReader(); if (!r.Read()) return false;
        list = Decode((byte[])r[1], r.GetInt32(0));
    }
    switch (kind)
    {
        case "DROP": if (list.RemoveAll(x => x.P == p) == 0) return false; break;
        case "SHIFT": { int k = list.FindIndex(x => x.P == p); if (k < 0) return false; list[k] = (p, list[k].Pos.Select(x => x + 1).ToArray()); break; }
        case "EXTRA": list.Add((p, [0])); list.Sort((a, b) => a.P.CompareTo(b.P)); break;
    }
    using var w = new SqliteCommand("UPDATE terms SET df = $d, postings = $b WHERE term = $t", c);
    w.Parameters.AddWithValue("$d", list.Count); w.Parameters.AddWithValue("$b", Encode(list)); w.Parameters.AddWithValue("$t", term); w.ExecuteNonQuery();
    return true;
}
ComponentEvidence VerifyLex(string dir, string rid, int s, int q) =>
    LexicalIndexVerifier.Verify(g, dir, rid, null, B04Sampling.Override(LexicalIndexVerifier.Postings, s), B04Sampling.Override(LexicalIndexVerifier.Queries, q));
var lex = new JsonObject();
// false rejects and cost on the clean index
{
    var fr = new JsonArray(); var cost = new JsonArray();
    foreach (var s in new[] { 1, 4, 16, 64, 128, bigN })
    {
        int fails = 0; var ms = new List<double>();
        int reps = s == bigN ? 3 : Math.Min(seeds, 20);
        for (int r = 0; r < reps; r++)
        {
            var sw = Stopwatch.StartNew();
            var ev = VerifyLex(ixDir, $"study-{r}", s, 32);
            ms.Add(sw.Elapsed.TotalMilliseconds);
            if (!ev.Verified(LexicalIndexVerifier.Required)) fails++;
        }
        fr.Add(new JsonObject { ["sample_docs"] = s == bigN ? "ALL" : s, ["query_sample"] = 32, ["runs"] = reps, ["false_rejects"] = fails });
        cost.Add(new JsonObject { ["sample_docs"] = s == bigN ? "ALL" : s, ["median_ms"] = Math.Round(Median(ms)), ["runs"] = reps });
        Log($"lexical clean s={s}: {fails} false rejects, {Median(ms):0} ms");
    }
    lex["false_rejects_clean"] = fr; lex["cost_ms_by_sample"] = cost;
    lex["index_bytes"] = new FileInfo(Path.Combine(ixDir, "search.sqlite")).Length;
}
// conditional detection per corruption type
{
    var det = new JsonObject();
    foreach (var kind in new[] { "DROP", "SHIFT", "LEN", "EXTRA" })
    {
        int made = 0, postingsFail = 0, queryFail = 0, anyFail = 0, queryFailSmall = 0, smallRuns = 0;
        var rnd = new Random(kind.GetHashCode(StringComparison.Ordinal) & 0x7fffffff);
        for (int inst = 0; inst < instances; inst++)
        {
            int di = rnd.Next(refIx.Docs.Count);
            var d = Copy(ixDir, "inst");
            if (!CorruptLex(d, kind, di, rnd)) { inst--; continue; }
            Rehash(d);
            made++;
            var ev = VerifyLex(d, "study-cond", bigN, 32);
            if (ev.Checks.GetValueOrDefault("SAMPLED_POSTINGS_REDERIVE") == "FAIL") postingsFail++;
            if (ev.Checks.GetValueOrDefault("SAMPLED_QUERY_PARITY") == "FAIL") queryFail++;
            if (!ev.Verified(LexicalIndexVerifier.Required)) anyFail++;
            // query parity when the corrupted document is in a 16-document sample (release id searched for)
            var docId = refIx.Docs[di].DocId;
            var rid = Enumerable.Range(0, 5000).Select(i => $"study-find-{i}").FirstOrDefault(r => B04Sampling.Stratified(r, LexicalIndexVerifier.Postings, strataDocs, 16).Contains(docId));
            if (rid is not null)
            {
                smallRuns++;
                if (VerifyLex(d, rid, 16, 32).Checks.GetValueOrDefault("SAMPLED_QUERY_PARITY") == "FAIL") queryFailSmall++;
            }
        }
        det[kind] = new JsonObject
        {
            ["instances"] = made, ["detected_any_check_when_sampled"] = Math.Round((double)anyFail / made, 3),
            ["postings_rederive_detects"] = Math.Round((double)postingsFail / made, 3),
            ["query_parity_detects_all_docs_32_queries"] = Math.Round((double)queryFail / made, 3),
            ["query_parity_detects_16_docs_32_queries"] = smallRuns == 0 ? null : Math.Round((double)queryFailSmall / smallRuns, 3),
        };
        Log($"lexical {kind}: postings {postingsFail}/{made}, query(all) {queryFail}/{made}, query(16) {queryFailSmall}/{smallRuns}");
    }
    lex["conditional_detection"] = det;
}
outp["LEXICAL_INDEX"] = lex;

// ============================================================ 3. GRAPH
Log("graph: rows");
var (nodes, edges) = (KnowledgeRows.DeriveFile("graph_nodes", new KnowledgeSources { Graph = GraphBuilder.Build(g) }).Bytes,
                      KnowledgeRows.DeriveFile("graph_edges", new KnowledgeSources { Graph = GraphBuilder.Build(g) }).Bytes);
var graph = new JsonObject();
var gStrata = GraphVerifier.Strata(g);
ComponentEvidence VerifyGraph(byte[] n, byte[] e, string rid, int s)
{
    var rows = GraphVerifier.Parse(n, e);
    return GraphVerifier.Verify(g, n, e, GraphVerifier.DigestOfRows(GraphBuilder.Version, rows.Nodes.Keys, rows.Edges.Keys), GraphBuilder.Version, rid, B04Sampling.Override(GraphVerifier.Check, s));
}
{
    var fr = new JsonArray(); var cost = new JsonArray();
    foreach (var s in new[] { 1, 4, 16, 64, 128, g.Documents.Count + 1 })
    {
        int fails = 0; var ms = new List<double>(); int reps = s > g.Documents.Count ? 3 : Math.Min(seeds, 20);
        for (int r = 0; r < reps; r++)
        {
            var sw = Stopwatch.StartNew();
            if (!VerifyGraph(nodes, edges, $"study-{r}", s).Verified(GraphVerifier.Required)) fails++;
            ms.Add(sw.Elapsed.TotalMilliseconds);
        }
        fr.Add(new JsonObject { ["sample_docs"] = s > g.Documents.Count ? "ALL" : s, ["runs"] = reps, ["false_rejects"] = fails });
        cost.Add(new JsonObject { ["sample_docs"] = s > g.Documents.Count ? "ALL" : s, ["median_ms"] = Math.Round(Median(ms)), ["runs"] = reps });
        Log($"graph clean s={s}: {fails} false rejects, {Median(ms):0} ms");
    }
    var fsw = Stopwatch.StartNew();
    var fullIssues = GraphVerifier.FullRebuildParity(GraphVerifier.Parse(nodes, edges), g);
    graph["full_rebuild_parity_ms"] = Math.Round(fsw.Elapsed.TotalMilliseconds); graph["full_rebuild_parity_issues_clean"] = fullIssues.Count;
    graph["false_rejects_clean"] = fr; graph["cost_ms_by_sample"] = cost;
    graph["rows"] = new JsonObject { ["nodes"] = Encoding.UTF8.GetString(nodes).Count(ch => ch == '\n'), ["edges"] = Encoding.UTF8.GetString(edges).Count(ch => ch == '\n') };
}
{
    var lines = Encoding.UTF8.GetString(edges).Split('\n').Where(l => l.Length > 0).ToList();
    var nlines = Encoding.UTF8.GetString(nodes).Split('\n').Where(l => l.Length > 0).ToList();
    byte[] Join(IEnumerable<string> ls) => Encoding.UTF8.GetBytes(string.Concat(ls.Select(l => l + "\n")));
    var det = new JsonObject();
    foreach (var kind in new[] { "FIELD", "TEMPORAL", "DROP", "REVIEWED", "NODE_LABEL" })
    {
        var rnd = new Random(kind.Length * 7919);
        int made = 0, structural = 0, parity = 0, any = 0;
        for (int inst = 0; inst < instances; inst++)
        {
            byte[] n = nodes, e = edges;
            if (kind == "NODE_LABEL")
            {
                var held = nlines.Select((l, i) => (l, i)).Where(x => x.l.Contains("\"held\":true") && !x.l.Contains("\"doc_id\":null")).ToList();
                var (l, i) = held[rnd.Next(held.Count)];
                var o = JsonNode.Parse(l)!.AsObject(); o["label"] = o["label"] + " (rewritten)";
                var copy = nlines.ToList(); copy[i] = Encoding.UTF8.GetString(Mimamsa.Core.Knowledge.CanonicalJson.Bytes(o)); n = Join(copy);
            }
            else
            {
                var cand = lines.Select((l, i) => (l, i)).Where(x => !x.l.Contains("\"source_doc_id\":null")).ToList();
                var (l, i) = cand[rnd.Next(cand.Count)];
                var copy = lines.ToList();
                var o = JsonNode.Parse(l)!.AsObject();
                switch (kind)
                {
                    case "FIELD": o["uncertainty"] = "rewritten"; break;
                    case "TEMPORAL": o["temporal_from"] = "1900-01-01"; break;
                    case "REVIEWED": o["verification"] = "LEGAL_REVIEWED"; break;
                }
                if (kind == "DROP") copy.RemoveAt(i); else copy[i] = Encoding.UTF8.GetString(Mimamsa.Core.Knowledge.CanonicalJson.Bytes(o));
                e = Join(copy);
            }
            made++;
            var ev = VerifyGraph(n, e, "study-cond", g.Documents.Count + 1);
            if (ev.Checks.GetValueOrDefault("GRAPH_STRUCTURAL_RECHECK") == "FAIL") structural++;
            if (ev.Checks.GetValueOrDefault("SAMPLED_REBUILD_PARITY") == "FAIL") parity++;
            if (!ev.Verified(GraphVerifier.Required)) any++;
        }
        det[kind] = new JsonObject { ["instances"] = made, ["detected_when_sampled"] = Math.Round((double)any / made, 3),
            ["structural_recheck_detects"] = Math.Round((double)structural / made, 3), ["rebuild_parity_detects"] = Math.Round((double)parity / made, 3) };
        Log($"graph {kind}: structural {structural}/{made}, parity {parity}/{made}");
    }
    graph["conditional_detection"] = det;
}
outp["GRAPH"] = graph;

// ============================================================ 4. VECTOR_PACK (real model)
if (Opt("--model-dir") is { } modelDir && Opt("--pack-dir") is { } packDir)
{
    var vec = new JsonObject();
    var msha = Opt("--model-sha")!;
    var sw = Stopwatch.StartNew();
    var file = VectorPackFile.Open(Path.Combine(packDir, msha + ".mimvec"), out var why) ?? throw new InvalidOperationException(why);
    vec["trailer_and_index_ms"] = Math.Round(sw.Elapsed.TotalMilliseconds); sw.Restart();
    var digest = file.ResultDigest(); vec["result_digest_ms"] = Math.Round(sw.Elapsed.TotalMilliseconds); sw.Restart();
    var prm = VectorPackParams.Parse(File.ReadAllBytes(Path.Combine(packDir, msha + ".params.json")));
    var inputs = VectorPackVerifier.Inputs(g, prm);
    var keyOf = new Dictionary<UInt128, string>();
    foreach (var (_, inp) in inputs) keyOf.TryAdd(VectorPackVerifier.Key(msha, prm.MaxTokens, inp), inp);
    vec["keys_recompute_ms"] = Math.Round(sw.Elapsed.TotalMilliseconds);
    vec["entries"] = file.Count; vec["distinct_passages"] = keyOf.Count; vec["pack_bytes"] = new FileInfo(file.Path).Length;
    var bandStrata = new Dictionary<string, List<string>>(StringComparer.Ordinal);
    var byHex = new Dictionary<string, UInt128>(StringComparer.Ordinal);
    foreach (var (k, inp) in keyOf)
    {
        var hex = Convert.ToHexStringLower(VectorPackFile.KeyBytes(k)); byHex[hex] = k;
        var band = $"len{Math.Min(Encoding.UTF8.GetByteCount(inp) / 512, 7)}";
        (bandStrata.TryGetValue(band, out var l) ? l : bandStrata[band] = []).Add(hex);
    }
    vec["strata"] = new JsonObject(bandStrata.OrderBy(x => x.Key).Select(x => KeyValuePair.Create(x.Key, (JsonNode?)x.Value.Count)));
    int pool = IntOpt("--vector-pool", 128);
    var chosen = B04Sampling.Stratified("study-vectors", "VECTOR_SPOT_REEMBED", bandStrata, pool);
    using var emb = new E5Embedder(modelDir, threads, expectedModelSha256: msha);
    var diffs = new List<double>(); var embedMs = new List<double>(); var fresh = new Dictionary<string, float[]>();
    foreach (var hex in chosen)
    {
        var t = Stopwatch.StartNew();
        var f = emb.EmbedOne(keyOf[byHex[hex]], prm.MaxTokens);
        embedMs.Add(t.Elapsed.TotalMilliseconds);
        fresh[hex] = f;
        diffs.Add(VectorPackVerifier.MaxAbsDifference(file.Read(byHex[hex]), f));
    }
    // repeat and thread-count variation on a subset
    var repeat = new List<double>(); var cross = new List<double>();
    using (var one = new E5Embedder(modelDir, 1, expectedModelSha256: msha))
        foreach (var hex in chosen.Take(24))
        {
            repeat.Add(VectorPackVerifier.MaxAbsDifference(fresh[hex], emb.EmbedOne(keyOf[byHex[hex]], prm.MaxTokens)));
            cross.Add(VectorPackVerifier.MaxAbsDifference(fresh[hex], one.EmbedOne(keyOf[byHex[hex]], prm.MaxTokens)));
        }
    var sorted = diffs.Order().ToArray();
    vec["clean_reembed"] = new JsonObject
    {
        ["passages"] = diffs.Count, ["max_abs_difference_max"] = sorted[^1], ["p99"] = sorted[(int)Math.Floor(0.99 * (sorted.Length - 1))],
        ["median"] = Median(diffs), ["repeat_same_threads_max"] = repeat.Max(), ["threads_1_vs_n_max"] = cross.Max(),
        ["embed_ms_median"] = Math.Round(Median(embedMs), 1), ["embed_ms_p95"] = Math.Round(embedMs.Order().ElementAt((int)(0.95 * (embedMs.Count - 1))), 1),
        ["note"] = "pack vectors were embedded centrally in batches of 16 (padded); the site re-embeds one input per call",
    };
    // conditional detection: corrupt the pack vector of each chosen passage, compare with its fresh embedding
    var tolerances = new[] { 1e-6, 1e-5, 1e-4, 1e-3, 1e-2 };
    var det = new JsonObject();
    var rnd = new Random(4242);
    float[] Norm(float[] v) { var n = Math.Sqrt(v.Sum(x => (double)x * x)); return v.Select(x => (float)(x / n)).ToArray(); }
    foreach (var (kind, make) in new (string, Func<string, float[]>)[]
    {
        ("SWAP_WITH_OTHER_PASSAGE", hex => file.Read(byHex[chosen[(chosen.IndexOf(hex) + 1) % chosen.Count]])),
        ("NOISE_1e-2", hex => Norm(file.Read(byHex[hex]).Select(x => x + (float)(1e-2 * (rnd.NextDouble() * 2 - 1))).ToArray())),
        ("NOISE_1e-3", hex => Norm(file.Read(byHex[hex]).Select(x => x + (float)(1e-3 * (rnd.NextDouble() * 2 - 1))).ToArray())),
        ("NOISE_1e-4", hex => Norm(file.Read(byHex[hex]).Select(x => x + (float)(1e-4 * (rnd.NextDouble() * 2 - 1))).ToArray())),
        ("NOISE_1e-5", hex => Norm(file.Read(byHex[hex]).Select(x => x + (float)(1e-5 * (rnd.NextDouble() * 2 - 1))).ToArray())),
        ("SIGN_FLIP_ONE_COMPONENT", hex => { var v = file.Read(byHex[hex]); v[rnd.Next(v.Length)] *= -1; return v; }),
    })
    {
        var ds = chosen.Select(hex => VectorPackVerifier.MaxAbsDifference(make(hex), fresh[hex])).ToList();
        det[kind] = new JsonObject(tolerances.Select(t => KeyValuePair.Create($"tol_{t:0e0}", (JsonNode?)Math.Round(ds.Count(d => d > t) / (double)ds.Count, 3))));
    }
    vec["conditional_detection_by_tolerance"] = det;
    vec["false_reject_by_tolerance"] = new JsonObject(tolerances.Select(t => KeyValuePair.Create($"tol_{t:0e0}", (JsonNode?)Math.Round(diffs.Count(d => d > t) / (double)diffs.Count, 4))));
    // inclusion of corrupted passages (no embedding needed: the sampler alone)
    var keysAll = bandStrata;
    vec["inclusion_k1pct"] = Inclusion(keysAll, Math.Max(1, keyOf.Count / 100), Math.Min(seeds, 50), "VECTOR_SPOT_REEMBED");
    // synthetic pack scale: fixed full-pass costs (trailer, digest) on a random 100,000 x 384 pack
    var synPath = Path.Combine(work, "synthetic-100k.mimvec");
    var r2 = new Random(7);
    VectorPackFile.Write(synPath, 384, Enumerable.Range(0, 100_000).Select(i => ((UInt128)(ulong)r2.NextInt64() << 64 | (ulong)r2.NextInt64(), Enumerable.Range(0, 384).Select(_ => (float)r2.NextDouble()).ToArray())));
    sw.Restart(); var syn = VectorPackFile.Open(synPath, out _)!; var openMs = sw.Elapsed.TotalMilliseconds; sw.Restart(); syn.ResultDigest(); var digMs = sw.Elapsed.TotalMilliseconds;
    vec["synthetic_100k_pack"] = new JsonObject { ["bytes"] = new FileInfo(synPath).Length, ["trailer_and_index_ms"] = Math.Round(openMs), ["result_digest_ms"] = Math.Round(digMs) };
    File.Delete(synPath);
    outp["VECTOR_PACK"] = vec;
    Log("vectors done");
}
File.WriteAllText(Opt("--out")!, outp.ToJsonString(new JsonSerializerOptions { WriteIndented = true }));
SqliteConnection.ClearAllPools();
Log("written " + Opt("--out"));
return 0;
