// C16 Stage 3 S3-B: B04 component verifiers (GRAPH, LEXICAL_INDEX, VECTOR_PACK), lexical-index adoption and the
// cross-language golden values. Adversarial: content tampered while its digest still matches is caught by the sampled
// checks; corrupted components are refused; production never runs an uncalibrated sampled check.
using System.Security.Cryptography;
using System.Text;
using System.Text.Json.Nodes;
using Microsoft.Data.Sqlite;
using Mimamsa.Core.Activation;
using Mimamsa.Core.ComponentVerification;
using Mimamsa.Core.Generation;
using Mimamsa.Core.Graph;
using Mimamsa.Core.Knowledge;
using Mimamsa.Core.Search;
using Mimamsa.Tests.Activation;

namespace Mimamsa.Tests;

/// Deterministic stand-in for an embedding model (tests only): a unit vector from SHA-256 of the input. Counts calls so
/// tests can prove the verifier embeds only the sample, never the corpus.
public sealed class HashEmbedder(string modelSha256, int dim = 8, double noise = 0) : IPassageEmbedder
{
    public string ModelSha256 => modelSha256;
    public int Dim => dim;
    public int Calls;
    public float[] EmbedOne(string input, int maxTokens)
    {
        Interlocked.Increment(ref Calls);
        var h = SHA256.HashData(Encoding.UTF8.GetBytes(modelSha256 + "|" + input));
        var v = new float[dim];
        for (int i = 0; i < dim; i++) v[i] = h[i % 32] - 127.5f + (float)(noise * i);
        var n = (float)Math.Sqrt(v.Sum(x => (double)x * x));
        for (int i = 0; i < dim; i++) v[i] /= n;
        return v;
    }
}

public static class S3b
{
    public static string NewDir(string label)
    {
        var d = Path.Combine(Path.GetTempPath(), $"c16s3b-{label}-{Guid.NewGuid():N}"[..40]);
        Directory.CreateDirectory(d);
        return d;
    }

    public static void Delete(string d) { SqliteConnection.ClearAllPools(); try { Directory.Delete(d, true); } catch (IOException) { } catch (UnauthorizedAccessException) { } }

    public static JsonObject Contract(string kind) =>
        JsonNode.Parse(File.ReadAllBytes(TestDirs.RepoFile("app", "contract", "fixtures", "c16", "v2_1", "component_contracts", kind + ".json")))!.AsObject();

    public static Dictionary<string, JsonObject?> Contracts() =>
        ActivationOutcome.Kinds.ToDictionary(k => k, k => (JsonObject?)Contract(k), StringComparer.Ordinal);

    public static (byte[] Nodes, byte[] Edges) GraphRows(GenerationStore g)
    {
        var src = new KnowledgeSources { Graph = GraphBuilder.Build(g) };
        return (KnowledgeRows.DeriveFile("graph_nodes", src).Bytes, KnowledgeRows.DeriveFile("graph_edges", src).Bytes);
    }

    /// Builds the ADR-0007 index of `g` under `root` and returns its published directory.
    public static string BuildIndex(GenerationStore g, string root)
    {
        var ix = SearchIndex.Open(g, root, new SearchIndexOptions { UseForwardCache = false, KeepPrevious = 0, BuildTimeUtc = DateTimeOffset.Parse("2026-11-28T00:00:00Z") });
        SqliteConnection.ClearAllPools();
        return ix.IndexPath!;
    }

    public static string CopyDir(string src, string dst)
    {
        Directory.CreateDirectory(dst);
        foreach (var f in Directory.GetFiles(src)) File.Copy(f, Path.Combine(dst, Path.GetFileName(f)), true);
        return dst;
    }

    static string Sha(string p) => Convert.ToHexStringLower(SHA256.HashData(File.ReadAllBytes(p)));

    /// Re-pins MANIFEST.json to the (tampered) file: the digest then matches the content (a consistent rewrite).
    public static void Rehash(string dir)
    {
        SqliteConnection.ClearAllPools();
        var mp = Path.Combine(dir, "MANIFEST.json");
        var m = JsonNode.Parse(File.ReadAllText(mp))!.AsObject();
        m["file_sha256"] = Sha(Path.Combine(dir, "search.sqlite"));
        m["file_bytes"] = new FileInfo(Path.Combine(dir, "search.sqlite")).Length;
        File.WriteAllText(mp, m.ToJsonString());
    }

    public static void Exec(string db, string sql, params (string, object)[] ps)
    {
        using var c = new SqliteConnection(new SqliteConnectionStringBuilder { DataSource = db, Mode = SqliteOpenMode.ReadWrite, Pooling = false }.ToString());
        c.Open();
        using var cmd = new SqliteCommand(sql, c);
        foreach (var (k, v) in ps) cmd.Parameters.AddWithValue(k, v);
        cmd.ExecuteNonQuery();
    }

    /// Rewrites the postings of `term` with `edit` (df follows the list) - the file stays a valid index.
    internal static void EditPostings(string db, string term, Func<List<SearchIndex.Posting>, List<SearchIndex.Posting>> edit)
    {
        byte[] blob; int df;
        using (var c = new SqliteConnection(new SqliteConnectionStringBuilder { DataSource = db, Mode = SqliteOpenMode.ReadOnly, Pooling = false }.ToString()))
        {
            c.Open();
            using var q = new SqliteCommand("SELECT df, postings FROM terms WHERE term = $t", c);
            q.Parameters.AddWithValue("$t", term);
            using var r = q.ExecuteReader();
            Assert.True(r.Read(), "term not in index: " + term);
            df = r.GetInt32(0); blob = (byte[])r[1];
        }
        var list = edit(SqlitePostingTable.Decode(blob, df, out _));
        Exec(db, "UPDATE terms SET df = $d, postings = $p WHERE term = $t", ("$d", list.Count), ("$p", SqlitePostingTable.Encode(list)), ("$t", term));
    }

    public sealed record Pack(string Path, byte[] Params, string ResultDigest, string SourceDigest);

    /// Central pack build (as kbuild does): every indexed passage embedded with `emb`, entries sorted by key bytes.
    public static Pack BuildPack(GenerationStore g, IPassageEmbedder emb, string dir, int maxTokens = 256,
                                 Func<List<(UInt128 Key, float[] Vector)>, List<(UInt128 Key, float[] Vector)>>? tamper = null)
    {
        var p = new VectorPackParams(emb.ModelSha256, emb.Dim, maxTokens, "passage: ", "query: ");
        var entries = new Dictionary<UInt128, float[]>();
        foreach (var (_, input) in VectorPackVerifier.Inputs(g, p))
            entries.TryAdd(VectorPackVerifier.Key(emb.ModelSha256, maxTokens, input), emb.EmbedOne(input, maxTokens));
        var list = entries.Select(e => (e.Key, e.Value)).ToList();
        if (tamper is not null) list = tamper(list);
        var path = System.IO.Path.Combine(dir, emb.ModelSha256 + ".mimvec");
        VectorPackFile.Write(path, emb.Dim, list);
        var file = VectorPackFile.Open(path, out _)!;
        var keys = VectorPackVerifier.Inputs(g, p).Select(x => VectorPackVerifier.Key(emb.ModelSha256, maxTokens, x.Input));
        return new Pack(path, Encoding.UTF8.GetBytes(p.ToJson().ToJsonString()), file.ResultDigest(), VectorPackVerifier.SourceDigest(emb.ModelSha256, maxTokens, keys));
    }

    public static readonly string ModelA = new('a', 64), ModelB = new('b', 64);
}

public class C16S3bVerificationTests
{
    static GenerationStore G => Syn.Gen;
    static int AllDocs => G.Documents.Count + 1000;

    // ------------------------------------------------------------------ golden values (Python reference)
    static JsonObject Golden => JsonNode.Parse(File.ReadAllBytes(TestDirs.RepoFile("app", "contract", "fixtures", "c16", "v2_1", "component_verification", "golden.json")))!.AsObject();

    [Fact]
    public void SamplesKeysSourceDigestAndPackBytesEqualThePythonReference()
    {
        var gold = Golden;
        foreach (var c in gold["seeded"]!.AsArray().Select(x => x!.AsObject()))
            Assert.Equal(c["seeded"]!.AsArray().Select(x => (string)x!), B04Sampling.Seeded((string)c["release_id"]!, (string)c["check_id"]!, c["members"]!.AsArray().Select(x => (string)x!), (int)c["size"]!));
        foreach (var c in gold["stratified"]!.AsArray().Select(x => x!.AsObject()))
        {
            var strata = c["strata"]!.AsObject().ToDictionary(kv => kv.Key, kv => kv.Value!.AsArray().Select(x => (string)x!).ToList());
            Assert.Equal(c["stratified"]!.AsArray().Select(x => (string)x!), B04Sampling.Stratified((string)c["release_id"]!, (string)c["check_id"]!, strata, (int)c["size"]!));
        }
        foreach (var c in gold["scores"]!.AsArray().Select(x => x!.AsObject()))
            Assert.Equal((string)c["score"]!, Convert.ToHexStringLower(B04Sampling.Score((string)c["release_id"]!, (string)c["check_id"]!, (string)c["member"]!)));
        foreach (var c in gold["vector_keys"]!.AsArray().Select(x => x!.AsObject()))
            Assert.Equal((string)c["key"]!, Convert.ToHexStringLower(VectorPackFile.KeyBytes(VectorPackVerifier.Key((string)c["model_sha256"]!, (int)c["max_tokens"]!, (string)c["input"]!))));
        var sd = gold["vector_source_digest"]!.AsObject();
        var keys = sd["keys"]!.AsArray().Select(k => System.Buffers.Binary.BinaryPrimitives.ReadUInt128LittleEndian(Convert.FromHexString((string)k!))).ToList();
        Assert.Equal((string)sd["digest"]!, VectorPackVerifier.SourceDigest((string)sd["model_sha256"]!, (int)sd["max_tokens"]!, keys));
        var mv = gold["mimvec"]!.AsObject();
        var dir = S3b.NewDir("gold");
        try
        {
            var entries = mv["entries"]!.AsArray().Select(e => (System.Buffers.Binary.BinaryPrimitives.ReadUInt128LittleEndian(Convert.FromHexString((string)e!["key"]!)),
                Enumerable.Range(0, 4).Select(i => BitConverter.ToSingle(Convert.FromHexString((string)e!["vector"]!), 4 * i)).ToArray())).ToList();
            var path = Path.Combine(dir, "g.mimvec");
            VectorPackFile.Write(path, 4, entries.AsEnumerable().Reverse());
            Assert.Equal((string)mv["file_sha256"]!, Convert.ToHexStringLower(SHA256.HashData(File.ReadAllBytes(path))));
            Assert.Equal((string)mv["result_digest"]!, VectorPackFile.Open(path, out _)!.ResultDigest());
        }
        finally { S3b.Delete(dir); }
        Assert.Equal(VectorPackParams.Parse(Encoding.UTF8.GetBytes(gold["params"]!.ToJsonString())).ToJson().ToJsonString(),
                     new VectorPackParams((string)gold["params"]!["model_sha256"]!, 384, 256, "passage: ", "query: ").ToJson().ToJsonString());
        foreach (var (k, v) in gold["development_defaults"]!.AsObject())
            Assert.Equal((int)v!["size"]!, B04Sampling.DevelopmentDefaults[k].Size);
    }

    [Fact]
    public void ProductionNeverRunsAnUncalibratedSampledCheckAndDevelopmentRecordsTheDefault()
    {
        foreach (var (kind, check) in new[] { ("GRAPH", "SAMPLED_REBUILD_PARITY"), ("LEXICAL_INDEX", "SAMPLED_POSTINGS_REDERIVE"), ("LEXICAL_INDEX", "SAMPLED_QUERY_PARITY"), ("VECTOR_PACK", "VECTOR_SPOT_REEMBED") })
        {
            var c = S3b.Contract(kind);
            Assert.True(ActivationOutcome.Uncalibrated(c));
            Assert.Throws<UncalibratedInProductionException>(() => B04Sampling.Effective(c, check, production: true));
            var e = B04Sampling.Effective(c, check, production: false);
            Assert.Equal("UNCALIBRATED_DEVELOPMENT_DEFAULT", e.SizeSource);
        }
    }

    // ------------------------------------------------------------------ GRAPH
    static ComponentEvidence VerifyGraph(byte[] n, byte[] e, int size, string? digest = null) =>
        GraphVerifier.Verify(G, n, e, digest ?? GraphVerifier.DigestOfRows(GraphBuilder.Version, GraphVerifier.Parse(n, e).Nodes.Keys, GraphVerifier.Parse(n, e).Edges.Keys),
                             GraphBuilder.Version, "R-s3b-test", B04Sampling.Override(GraphVerifier.Check, size));

    static byte[] EditRow(byte[] file, Func<JsonObject, bool> which, Action<JsonObject> edit)
    {
        var lines = Encoding.UTF8.GetString(file).Split('\n').Where(l => l.Length > 0).ToList();
        int i = lines.FindIndex(l => which(JsonNode.Parse(l)!.AsObject()));
        Assert.True(i >= 0, "no row to edit");
        var o = JsonNode.Parse(lines[i])!.AsObject(); edit(o);
        lines[i] = Encoding.UTF8.GetString(Mimamsa.Core.Knowledge.CanonicalJson.Bytes(o));
        return Encoding.UTF8.GetBytes(string.Concat(lines.Select(l => l + "\n")));
    }

    [Fact]
    public void ACleanGraphVerifiesAndTheFilteredBuilderIsTheFullBuilderOnEveryEdge()
    {
        var (n, e) = S3b.GraphRows(G);
        var ev = VerifyGraph(n, e, AllDocs);
        Assert.True(ev.Verified(GraphVerifier.Required), string.Join("; ", ev.Issues));
        Assert.Equal(GraphStore.Digest(GraphBuilder.Build(G)), GraphStore.Digest(GraphBuilder.Build(G, null)));
        Assert.Empty(GraphVerifier.FullRebuildParity(GraphVerifier.Parse(n, e), G));
        Assert.True(VerifyGraph(n, e, 1).Verified(GraphVerifier.Required));   // any sample of a clean graph passes
    }

    [Fact]
    public void ANonBuilderVerificationValueIsCaughtByTheStructuralRecheckWhileTheDigestMatches()
    {
        var (n, e) = S3b.GraphRows(G);
        var bad = EditRow(e, _ => true, o => o["verification"] = "LEGAL_REVIEWED");
        var ev = VerifyGraph(n, bad, 1);
        Assert.Equal("PASS", ev.Checks["GRAPH_DIGEST"]);
        Assert.Equal("FAIL", ev.Checks["GRAPH_STRUCTURAL_RECHECK"]);
        var dangling = EditRow(e, _ => true, o => o["to_id"] = "PROV:NOPE:s.0");
        Assert.Equal("FAIL", VerifyGraph(n, dangling, 1).Checks["GRAPH_STRUCTURAL_RECHECK"]);
        var page = EditRow(e, o => o["source_doc_id"] is not null && o["page"] is not null, o => o["page"] = 99999);
        Assert.Equal("FAIL", VerifyGraph(n, page, 1).Checks["GRAPH_STRUCTURAL_RECHECK"]);
    }

    [Fact]
    public void ARewrittenEdgeOrNodeOfASampledDocumentIsCaughtByRebuildParityWhileDigestAndStructureMatch()
    {
        var (n, e) = S3b.GraphRows(G);
        var bad = EditRow(e, o => o["source_doc_id"] is not null, o => o["uncertainty"] = "rewritten after the build");
        var ev = VerifyGraph(n, bad, AllDocs);
        Assert.Equal("PASS", ev.Checks["GRAPH_DIGEST"]);
        Assert.Equal("PASS", ev.Checks["GRAPH_STRUCTURAL_RECHECK"]);
        Assert.Equal("FAIL", ev.Checks["SAMPLED_REBUILD_PARITY"]);
        var badNode = EditRow(n, o => (bool)o["held"]! && o["doc_id"] is not null, o => o["label"] = "rewritten label");
        Assert.Equal("FAIL", VerifyGraph(badNode, e, AllDocs).Checks["SAMPLED_REBUILD_PARITY"]);
        var dropped = Encoding.UTF8.GetBytes(string.Concat(Encoding.UTF8.GetString(e).Split('\n').Where(l => l.Length > 0).Skip(1).Select(l => l + "\n")));
        Assert.Equal("FAIL", VerifyGraph(n, dropped, AllDocs).Checks["SAMPLED_REBUILD_PARITY"]);   // digest re-pinned to the shipped ids
    }

    [Fact]
    public void ATamperOutsideTheSampleIsTheResidualRiskTheCalibrationMeasures()
    {
        var (n, e) = S3b.GraphRows(G);
        var sample = B04Sampling.Stratified("R-s3b-test", GraphVerifier.Check, GraphVerifier.Strata(G), 1).ToHashSet();
        var bad = EditRow(e, o => o["source_doc_id"] is JsonValue v && !sample.Contains((string)v!), o => o["uncertainty"] = "rewritten");
        Assert.True(VerifyGraph(n, bad, 1).Verified(GraphVerifier.Required));            // a 1-document sample misses it
        Assert.NotEmpty(GraphVerifier.FullRebuildParity(GraphVerifier.Parse(n, bad), G));  // the full rebuild does not
    }

    // ------------------------------------------------------------------ LEXICAL_INDEX
    static ComponentEvidence VerifyIndex(string dir, int size, string? declared = null) =>
        LexicalIndexVerifier.Verify(G, dir, "R-s3b-test", declared, B04Sampling.Override(LexicalIndexVerifier.Postings, size), B04Sampling.Override(LexicalIndexVerifier.Queries, 100_000));

    static (string Term, int Passage) FirstQueriedTerm(string dir)
    {
        var ix = SearchIndex.OpenForVerification(G, Path.Combine(dir, "search.sqlite"));
        for (int p = 0; p < ix.N; p++)
            foreach (var t in Text.Tokenize(ix.Passages[p].Text).Select(t => t.Term).Where(t => t.Length > 2 && !Text.Stopwords.Contains(t)).Take(12))
                if (ix.Postings.Df(t) >= 2) return (t, p);
        throw new InvalidOperationException("no term");
    }

    [Fact]
    public void ACleanIndexVerifiesWithoutARebuild()
    {
        var root = S3b.NewDir("lex");
        try
        {
            var dir = S3b.BuildIndex(G, root);
            var ev = VerifyIndex(dir, AllDocs, LexicalIndexVerifier.SiteSourceDigest(G));
            Assert.True(ev.Verified(LexicalIndexVerifier.Required), string.Join("; ", ev.Issues));
            Assert.True((int)ev.Samples["SAMPLED_QUERY_PARITY"]["selected"]! > 10);
            Assert.True(VerifyIndex(dir, 1).Verified(LexicalIndexVerifier.Required));
            Assert.Equal("FAIL", VerifyIndex(dir, 1, new string('0', 64)).Checks["SOURCE_DIGEST_EQUALS_SITE"]);
        }
        finally { S3b.Delete(root); }
    }

    [Fact]
    public void APrebuiltIndexWhoseDigestMatchesButWhosePostingsWereRewrittenIsCaught()
    {
        var root = S3b.NewDir("lex");
        try
        {
            var dir = S3b.BuildIndex(G, root);
            var (term, passage) = FirstQueriedTerm(dir);
            var db = Path.Combine(dir, "search.sqlite");
            S3b.EditPostings(db, term, l => l.Where(p => p.P != passage).ToList());   // the term silently vanishes from one passage
            S3b.Rehash(dir);
            Assert.Null(IndexStore.Verify(dir, G.GenerationId, LexicalIndexVerifier.SiteSourceDigest(G), full: true));   // manifest, sha, quick_check all pass
            var ev = VerifyIndex(dir, AllDocs);
            Assert.Equal("PASS", ev.Checks["SQLITE_QUICK_CHECK"]);
            Assert.Equal("FAIL", ev.Checks["SAMPLED_POSTINGS_REDERIVE"]);
            Assert.Equal("FAIL", ev.Checks["SAMPLED_QUERY_PARITY"]);
        }
        finally { S3b.Delete(root); }
    }

    [Fact]
    public void ShiftedPositionsAlteredLengthsAndAByteFlipAreRefused()
    {
        var root = S3b.NewDir("lex");
        try
        {
            var dir = S3b.BuildIndex(G, root);
            var (term, passage) = FirstQueriedTerm(dir);
            var a = S3b.CopyDir(dir, Path.Combine(root, "a"));
            S3b.EditPostings(Path.Combine(a, "search.sqlite"), term, l => l.Select(p => p.P == passage ? new SearchIndex.Posting(p.P, p.Pos.Select(x => x + 1).ToArray()) : p).ToList());
            S3b.Rehash(a);
            Assert.Equal("FAIL", VerifyIndex(a, AllDocs).Checks["SAMPLED_POSTINGS_REDERIVE"]);
            var b = S3b.CopyDir(dir, Path.Combine(root, "b"));
            S3b.Exec(Path.Combine(b, "search.sqlite"), "UPDATE docs SET service = 'navy' WHERE di = 0");
            S3b.Rehash(b);
            Assert.Equal("FAIL", VerifyIndex(b, AllDocs).Checks["SAMPLED_POSTINGS_REDERIVE"]);
            var c = S3b.CopyDir(dir, Path.Combine(root, "c"));
            var bytes = File.ReadAllBytes(Path.Combine(c, "search.sqlite")); bytes[^100] ^= 0x5A; File.WriteAllBytes(Path.Combine(c, "search.sqlite"), bytes);
            var ev = VerifyIndex(c, AllDocs);
            Assert.Equal("FAIL", ev.Checks["SQLITE_QUICK_CHECK"]);
            Assert.False(ev.Verified(LexicalIndexVerifier.Required));
        }
        finally { S3b.Delete(root); }
    }

    [Fact]
    public void ProductionRunsNoUncalibratedSampleOnTheIndex()
    {
        var root = S3b.NewDir("lex");
        try
        {
            var dir = S3b.BuildIndex(G, root);
            var ev = LexicalIndexVerifier.Verify(G, dir, "R", null, null, null);
            Assert.Equal("NOT_RUN", ev.Checks["SAMPLED_POSTINGS_REDERIVE"]);
            Assert.Equal("NOT_RUN", ev.Checks["SAMPLED_QUERY_PARITY"]);
            Assert.False(ev.Verified(LexicalIndexVerifier.Required));
        }
        finally { S3b.Delete(root); }
    }

    /// A copy of the SYN site whose active generation ships a prebuilt index (as a C16 knowledge release does).
    static (string Site, GenerationStore Gen, string Shipped) SiteWithShippedIndex(string work, Action<string>? tamper = null)
    {
        var site = Path.Combine(work, "site");
        foreach (var f in Directory.GetFiles(Syn.Site, "*", SearchOption.AllDirectories))
        {
            var dst = Path.Combine(site, Path.GetRelativePath(Syn.Site, f));
            Directory.CreateDirectory(Path.GetDirectoryName(dst)!); File.Copy(f, dst);
        }
        var g = GenerationStore.Load(site, null, TextStoreOptions.Memory);
        var built = S3b.BuildIndex(g, Path.Combine(work, "central"));
        var gdir = Path.Combine(site, "generations", g.GenerationId);
        var shipped = S3b.CopyDir(built, Path.Combine(gdir, "accelerators", "search-index"));
        tamper?.Invoke(shipped);
        var sha = Convert.ToHexStringLower(SHA256.HashData(File.ReadAllBytes(Path.Combine(shipped, "search.sqlite"))));
        File.WriteAllText(Path.Combine(gdir, "KNOWLEDGE_RELEASE.json"), new JsonObject
        {
            ["release_id"] = "R-s3b-adopt",
            ["components"] = new JsonArray(new JsonObject
            {
                ["kind"] = "LEXICAL_INDEX", ["source_digest"] = LexicalIndexVerifier.SiteSourceDigest(g),
                ["files"] = new JsonArray(new JsonObject { ["path"] = "accelerators/search-index/search.sqlite", ["sha256"] = sha }),
            }),
        }.ToJsonString());
        return (site, g, shipped);
    }

    [Fact]
    public void AVerifiedShippedIndexIsAdoptedWithoutARebuildAndATamperedOneIsRebuilt()
    {
        var work = S3b.NewDir("adopt");
        try
        {
            var (site, g, _) = SiteWithShippedIndex(work);
            var log = new List<string>();
            var ix = SearchIndex.Open(g, Path.Combine(work, "ix1"), new SearchIndexOptions { AdoptShipped = "development" }, log.Add);
            Assert.Equal("adopted", ix.Origin);
            Assert.DoesNotContain(log, l => l.Contains("built and published"));
            var mem = new SearchService(SearchIndex.Build(g), _ => false);
            var disk = new SearchService(ix, _ => false);
            foreach (var q in new[] { "notice", "summary AND evidence", "hear*", "\"written notice\"" })
                Assert.Equal(mem.Search(q, new SearchFilters()).Hits.Select(h => (h.PassageIndex, h.Score)), disk.Search(q, new SearchFilters()).Hits.Select(h => (h.PassageIndex, h.Score)));
            Assert.Equal("built", SearchIndex.Open(g, Path.Combine(work, "ix2"), new SearchIndexOptions(), log.Add).Origin);   // default: never adopts
            Assert.Equal("built", SearchIndex.Open(g, Path.Combine(work, "ix3"), new SearchIndexOptions { AdoptShipped = "production" }, log.Add).Origin);
            SqliteConnection.ClearAllPools();

            var work2 = S3b.NewDir("adopt");
            try
            {
                var (_, g2, _) = SiteWithShippedIndex(work2, shipped =>
                {
                    S3b.EditPostings(Path.Combine(shipped, "search.sqlite"), "notice", l => l.Skip(1).ToList());
                    S3b.Rehash(shipped);
                });
                var log2 = new List<string>();
                var ix2 = SearchIndex.Open(g2, Path.Combine(work2, "ix"), new SearchIndexOptions { AdoptShipped = "development" }, log2.Add);
                Assert.Equal("built", ix2.Origin);
                Assert.Contains(log2, l => l.Contains("shipped index not adopted: B04 checks failed"));
            }
            finally { S3b.Delete(work2); }
        }
        finally { S3b.Delete(work); }
    }

    // ------------------------------------------------------------------ VECTOR_PACK
    static ComponentEvidence VerifyPack(S3b.Pack p, IPassageEmbedder? emb, string model, int size = 100_000) =>
        VectorPackVerifier.Verify(G, p.Path, p.Params, model, p.ResultDigest, p.SourceDigest, "R-s3b-test", emb, B04Sampling.Override(VectorPackVerifier.Spot, size, 1e-6));

    [Fact]
    public void ACleanPackVerifiesAndTheSiteEmbedsOnlyTheSample()
    {
        var dir = S3b.NewDir("vec");
        try
        {
            var pack = S3b.BuildPack(G, new HashEmbedder(S3b.ModelA), dir);
            var site = new HashEmbedder(S3b.ModelA);
            var ev = VerifyPack(pack, site, S3b.ModelA, size: 5);
            Assert.True(ev.Verified(VectorPackVerifier.Required), string.Join("; ", ev.Issues));
            Assert.Equal(5, site.Calls);                                   // one query-sized embed per sampled passage, never the corpus
            Assert.True((int)ev.Facts["keys"]! > 5);
        }
        finally { S3b.Delete(dir); }
    }

    [Fact]
    public void SwappedVectorsWithIntactKeysAndDigestAreCaughtBySpotReembed()
    {
        var dir = S3b.NewDir("vec");
        try
        {
            var pack = S3b.BuildPack(G, new HashEmbedder(S3b.ModelA), dir, tamper: l =>
            {
                var x = l.ToList(); (x[0], x[1]) = ((x[0].Key, x[1].Vector), (x[1].Key, x[0].Vector)); return x;
            });
            var ev = VerifyPack(pack, new HashEmbedder(S3b.ModelA), S3b.ModelA);
            Assert.Equal("PASS", ev.Checks["VECTOR_TRAILER"]);
            Assert.Equal("PASS", ev.Checks["VECTOR_KEYS_RECOMPUTED"]);
            Assert.Equal("PASS", ev.Checks["RESULT_DIGEST"]);
            Assert.Equal("FAIL", ev.Checks["VECTOR_SPOT_REEMBED"]);
            var noisy = VerifyPack(S3b.BuildPack(G, new HashEmbedder(S3b.ModelA, noise: 1e-3), Path.Combine(dir, "n")), new HashEmbedder(S3b.ModelA), S3b.ModelA);
            Assert.Equal("FAIL", noisy.Checks["VECTOR_SPOT_REEMBED"]);
        }
        finally { S3b.Delete(dir); }
    }

    [Fact]
    public void ForeignOrMissingKeysACorruptFileAndAMismatchedModelAreRefused()
    {
        var dir = S3b.NewDir("vec");
        try
        {
            var foreign = S3b.BuildPack(G, new HashEmbedder(S3b.ModelA), dir, tamper: l => l.Skip(1).Append((UInt128.MaxValue, l[0].Vector)).ToList());
            Assert.Equal("FAIL", VerifyPack(foreign, new HashEmbedder(S3b.ModelA), S3b.ModelA).Checks["VECTOR_KEYS_RECOMPUTED"]);
            var clean = S3b.BuildPack(G, new HashEmbedder(S3b.ModelA), Path.Combine(dir, "c"));
            var b = File.ReadAllBytes(clean.Path); b[40] ^= 1;
            var corrupt = Path.Combine(dir, "corrupt.mimvec"); File.WriteAllBytes(corrupt, b);
            Assert.Equal("FAIL", VerifyPack(clean with { Path = corrupt }, new HashEmbedder(S3b.ModelA), S3b.ModelA).Checks["VECTOR_TRAILER"]);
            File.WriteAllBytes(corrupt, File.ReadAllBytes(clean.Path)[..^1]);
            Assert.Equal("FAIL", VerifyPack(clean with { Path = corrupt }, new HashEmbedder(S3b.ModelA), S3b.ModelA).Checks["VECTOR_TRAILER"]);
            // mismatched model and pack: the installed model is another one; or the release names another model
            Assert.Equal("FAIL", VerifyPack(clean, new HashEmbedder(S3b.ModelB), S3b.ModelA).Checks["VECTOR_SPOT_REEMBED"]);
            Assert.Equal("FAIL", VerifyPack(clean, new HashEmbedder(S3b.ModelB), S3b.ModelB).Checks["VECTOR_KEYS_RECOMPUTED"]);
            var none = VerifyPack(clean, null, S3b.ModelA);
            Assert.Equal("NOT_RUN", none.Checks["VECTOR_SPOT_REEMBED"]);
            Assert.False(none.Verified(VectorPackVerifier.Required));
        }
        finally { S3b.Delete(dir); }
    }

    static JsonObject PackComponent(S3b.Pack p, string model) => new()
    {
        ["kind"] = "VECTOR_PACK", ["model_sha256"] = model, ["result_digest"] = p.ResultDigest, ["source_digest"] = p.SourceDigest,
        ["files"] = new JsonArray(
            new JsonObject { ["path"] = "accelerators/vectors/" + Path.GetFileName(p.Path), ["sha256"] = Convert.ToHexStringLower(SHA256.HashData(File.ReadAllBytes(p.Path))) },
            new JsonObject { ["path"] = $"accelerators/vectors/{model}.params.json", ["sha256"] = Convert.ToHexStringLower(SHA256.HashData(p.Params)) }),
    };

    [Fact]
    public void StagingVectorStatesGiveFullOnlyWithAVerifiedModelAndLexicalOnlyOtherwise()
    {
        var gdir = S3b.NewDir("vgen");
        try
        {
            var vdir = Path.Combine(gdir, "accelerators", "vectors"); Directory.CreateDirectory(vdir);
            var pack = S3b.BuildPack(G, new HashEmbedder(S3b.ModelA), vdir);
            File.WriteAllBytes(Path.Combine(vdir, S3b.ModelA + ".params.json"), pack.Params);
            var comp = PackComponent(pack, S3b.ModelA);
            var contracts = S3b.Contracts();
            InstalledModel? A(string sha) => sha == S3b.ModelA ? new InstalledModel("MA", new HashEmbedder(S3b.ModelA)) : null;
            InstalledModel? Wrong(string sha) => new InstalledModel("MB", new HashEmbedder(S3b.ModelB));

            var (st, ev, m) = GenerationStaging.VerifyVectorPack(G, gdir, comp, "R-s3b", contracts, production: false, A);
            Assert.Equal("VERIFIED", st); Assert.Equal("MA", m!.ModelId);
            Assert.Equal("UNCALIBRATED_DEVELOPMENT_DEFAULT", (string?)ev!["samples"]!["VECTOR_SPOT_REEMBED"]!["size_source"]);
            Assert.Equal("MISSING", GenerationStaging.VerifyVectorPack(G, gdir, null, "R", contracts, false, A).State);
            Assert.Equal("FAILED", GenerationStaging.VerifyVectorPack(G, gdir, comp, "R", contracts, false, null).State);    // no model: lexical-only
            Assert.Equal("FAILED", GenerationStaging.VerifyVectorPack(G, gdir, comp, "R", contracts, false, Wrong).State);   // mismatched model
            File.WriteAllBytes(pack.Path, File.ReadAllBytes(pack.Path)[..^1]);
            Assert.Equal("FAILED", GenerationStaging.VerifyVectorPack(G, gdir, comp, "R", contracts, false, A).State);       // differs from inventory

            var all = ActivationOutcome.Kinds.ToDictionary(k => k, _ => "VERIFIED");
            var dev = ActivationOutcome.Decide(all, contracts, "development");
            Assert.Equal("ACTIVE_FULL", (string?)dev["result"]);
            Assert.Contains("VECTOR_PACK", dev["uncalibrated_in_use"]!.AsArray().Select(x => (string?)x));
            var prod = ActivationOutcome.Decide(all, contracts, "production");
            Assert.Equal("UNCALIBRATED_IN_PRODUCTION", (string?)prod["refusal"]);
            all["VECTOR_PACK"] = "FAILED";
            var degraded = ActivationOutcome.Decide(all, contracts, "development");
            Assert.Equal("ACTIVE_DEGRADED", (string?)degraded["result"]); Assert.Equal("DEGRADED_LEXICAL_ONLY", (string?)degraded["service_level"]);
            Assert.Equal("NEVER", (string?)degraded["site_embedding"]);
        }
        finally { S3b.Delete(gdir); }
    }
}
