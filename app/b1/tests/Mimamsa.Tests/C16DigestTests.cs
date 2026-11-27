// C16 Tranche B CP-1 (PR #82 clarifications 2 and 5): the .NET component digests reproduce the contract 2.1 golden
// vectors (app/contract/fixtures/c16/v2_1/digests/golden.json, written by digests.py), and a text store shipped prebuilt
// with a generation is adopted (no rebuild) only when its bundle-independent source digest equals the site's.
using System.Security.Cryptography;
using System.Text.Json.Nodes;
using Mimamsa.Core.Generation;
using Mimamsa.Core.Knowledge;

namespace Mimamsa.Tests;

public class C16DigestTests
{
    static JsonObject Golden(string kind) =>
        JsonNode.Parse(File.ReadAllText(Repo.V21("digests", "golden.json")))![kind]!.AsObject();

    [Fact]
    public void TextStoreSourceDigestEqualsThePythonGolden()
    {
        var g = Golden("TEXT_STORE_SOURCE");
        var docs = g["documents"]!.AsArray().Select(d => ((string)d!["doc_id"]!, (string)d["copy_sha256"]!));
        var derived = g["derived"]!.AsArray().Select(d => d!.AsObject());
        Assert.Equal((string)g["digest"]!, DiskTextStore.SourceDigest21((string)g["generation_id"]!, docs, derived));
        // the input order never matters (documents, derivatives, pages and passages are sorted by the digest)
        Assert.Equal((string)g["digest"]!, DiskTextStore.SourceDigest21((string)g["generation_id"]!, docs.Reverse(), derived.Reverse()));
        // every bound input changes it
        var changed = g["derived"]!.DeepClone().AsArray();
        changed[0]!["pages"]![0]!["char_count"] = 41;
        Assert.NotEqual((string)g["digest"]!, DiskTextStore.SourceDigest21((string)g["generation_id"]!, docs, changed.Select(d => d!.AsObject())));
        Assert.NotEqual((string)g["digest"]!, DiskTextStore.SourceDigest21("CG-other", docs, derived));
    }

    [Fact]
    public void KnowledgeRowsComponentDigestEqualsThePythonGolden()
    {
        var g = Golden("KNOWLEDGE_ROWS");
        var tables = g["tables"]!.AsArray().Select(t => ((string)t!["table"]!, (long)t["row_count"]!, (string)t["rows_sha256"]!)).ToList();
        Assert.Equal((string)g["digest"]!, KnowledgeRows.ComponentDigest(tables));
        Assert.Equal((string)g["digest"]!, KnowledgeRows.ComponentDigest(Enumerable.Reverse(tables)));
        Assert.NotEqual((string)g["wrong_no_final_lf"]!, KnowledgeRows.ComponentDigest(tables));
        var pre = System.Text.Encoding.UTF8.GetBytes((string)g["preimage"]!);
        Assert.Equal((string)g["digest"]!, Convert.ToHexString(SHA256.HashData(pre)).ToLowerInvariant());
    }

    // ---------------------------------------------------------------- shipped (prebuilt) text store adoption

    sealed class Shipped : IDisposable
    {
        public readonly string Site = Syn.CopySite();
        public readonly string Root = Path.Combine(Path.GetTempPath(), "mimamsa-c16-adopt-" + Guid.NewGuid().ToString("N")[..8]);
        public readonly List<string> Log = new();
        readonly List<GenerationStore> _opened = new();
        public string Gid => File.ReadAllText(Path.Combine(Site, "ACTIVE")).Trim();
        public string Gdir => Path.Combine(Site, "generations", Gid);

        public GenerationStore Load(string root, bool adopt = true, bool verifyOnOpen = true)
        {
            var g = GenerationStore.Load(Site, null, new TextStoreOptions { Store = "disk", Dir = root, AdoptShipped = adopt, VerifyOnOpen = verifyOnOpen,
                                                                             BuildTimeUtc = DateTimeOffset.Parse("2026-11-27T00:00:00Z") }, Log.Add);
            _opened.Add(g);
            return g;
        }

        /// Builds the generation's store centrally (another root), then ships it with the generation the way the site
        /// importer materialises a knowledge release: accelerators/text-store/ plus a KNOWLEDGE_RELEASE.json TEXT_STORE
        /// component carrying the 2.1 source digest and the file inventory.
        public string Ship(string? sourceDigest = null)
        {
            var central = Load(Path.Combine(Root, "central"), adopt: false);
            var built = ((DiskTextStore)central.Text).StorePath!;
            var dst = Path.Combine(Gdir, "accelerators", "text-store");
            Directory.CreateDirectory(dst);
            var files = new JsonArray();
            foreach (var f in new[] { DiskTextStore.DbFile, DiskTextStore.ManifestFile })
            {
                File.Copy(Path.Combine(built, f), Path.Combine(dst, f), true);
                files.Add(new JsonObject { ["path"] = "accelerators/text-store/" + f, ["sha256"] = Sha(Path.Combine(dst, f)), ["bytes"] = new FileInfo(Path.Combine(dst, f)).Length });
            }
            var digest = sourceDigest ?? (string)JsonNode.Parse(File.ReadAllText(Path.Combine(built, DiskTextStore.ManifestFile)))!["source_digest"]!;
            var km = new JsonObject { ["components"] = new JsonArray(new JsonObject
            {
                ["component_id"] = "text-store", ["kind"] = "TEXT_STORE", ["authority"] = "ACCELERATOR", ["source_digest"] = digest, ["files"] = files,
            }) };
            File.WriteAllText(Path.Combine(Gdir, "KNOWLEDGE_RELEASE.json"), km.ToJsonString());
            return dst;
        }

        static string Sha(string p) => Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(p))).ToLowerInvariant();

        public void Dispose()
        {
            foreach (var g in _opened) (g.Text as IDisposable)?.Dispose();
            Microsoft.Data.Sqlite.SqliteConnection.ClearAllPools();
            foreach (var d in new[] { Site, Root }) try { Directory.Delete(d, true); } catch { }
        }
    }

    static string Facts(GenerationStore g) => string.Join("\n", g.Documents.Values.OrderBy(d => d.DocId, StringComparer.Ordinal)
        .SelectMany(d => d.Pages.Values.OrderBy(p => p.Page).Select(p => $"{d.DocId}|{d.DerivativeId}|{p.Page}|{p.Method}|{p.Text}"))
        .Concat(g.Documents.Values.SelectMany(d => d.Passages.Select(p => $"{d.DocId}|{p.PassageId}|{p.CharStart}|{p.CharEnd}|{p.Text}"))));

    [Theory]
    [InlineData(true)]
    [InlineData(false)]
    public void AShippedStoreWithTheSitesSourceDigestIsAdoptedWithoutARebuild(bool verifyOnOpen)
    {
        using var s = new Shipped();
        s.Ship();
        s.Log.Clear();
        var g = s.Load(Path.Combine(s.Root, "site"), verifyOnOpen: verifyOnOpen);
        var store = (DiskTextStore)g.Text;
        Assert.Equal("adopted", store.Origin);
        Assert.Contains(s.Log, l => l.Contains("adopted shipped store"));
        Assert.DoesNotContain(s.Log, l => l.Contains("built and published"));
        Assert.Equal(Facts(GenerationStore.Load(s.Site)), Facts(g));    // exactly the memory reference
        // the adopted file is byte-identical to the shipped one (no rebuild)
        Assert.Equal(File.ReadAllBytes(Path.Combine(s.Gdir, "accelerators", "text-store", DiskTextStore.DbFile)),
                     File.ReadAllBytes(Path.Combine(store.StorePath!, DiskTextStore.DbFile)));
    }

    [Theory]
    [InlineData("digest")]
    [InlineData("bytes")]
    [InlineData("missing")]
    public void AShippedStoreThatDoesNotMatchIsNotAdoptedAndTheSiteBuilds(string fault)
    {
        using var s = new Shipped();
        var dir = s.Ship(fault == "digest" ? new string('0', 64) : null);
        if (fault == "bytes") { var p = Path.Combine(dir, DiskTextStore.DbFile); var b = File.ReadAllBytes(p); b[^1] ^= 1; File.WriteAllBytes(p, b); }
        if (fault == "missing") File.Delete(Path.Combine(dir, DiskTextStore.ManifestFile));
        s.Log.Clear();
        var g = s.Load(Path.Combine(s.Root, "site"));
        Assert.Equal("built", ((DiskTextStore)g.Text).Origin);
        Assert.Contains(s.Log, l => l.Contains("no shipped store adopted"));
        Assert.Contains(s.Log, l => l.Contains("built and published"));
        Assert.Equal(Facts(GenerationStore.Load(s.Site)), Facts(g));
    }

    [Fact]
    public void AnAdoptedStoreStillGoesThroughBindOnEveryOpen()
    {
        using var s = new Shipped();
        s.Ship();
        var root = Path.Combine(s.Root, "site");
        Assert.Equal("adopted", ((DiskTextStore)s.Load(root).Text).Origin);
        // a later change to the generation's derivative records changes the 2.1 digest: the store is rebuilt, never served
        var rec = Path.Combine(s.Gdir, "records", "derived_text.jsonl");
        File.WriteAllLines(rec, File.ReadAllLines(rec).Skip(1));
        s.Log.Clear();
        var g = s.Load(root);
        Assert.Equal("built", ((DiskTextStore)g.Text).Origin);
        Assert.Equal(Facts(GenerationStore.Load(s.Site)), Facts(g));
    }
}
