using Mimamsa.Core.Search;

namespace Mimamsa.Tests;

/// C15 WP1 (ADR-0008): the disk engine returns exactly what the in-memory engine returns, and the index store recovers
/// from interrupted builds and corrupted files without ever serving an unverified index.
public class PersistentIndexTests : IDisposable
{
    readonly string _root = Path.Combine(Path.GetTempPath(), "mimamsa-c15-index-" + Guid.NewGuid().ToString("N")[..8]);
    readonly List<string> _log = new();
    public void Dispose() { Microsoft.Data.Sqlite.SqliteConnection.ClearAllPools(); try { Directory.Delete(_root, true); } catch { } }

    static readonly string[] Queries = { "notice", "s.17 Bracken Service Act", "OA 411/2021", "hearing written notice allegation",
        "exact:\"summary of evidence\"", "summary AND evidence", "\"written notice\" NEAR/5 hearing", "hear*", "title:bracken", "Vale v Lark", "hearnig" };

    static List<string> Sig(SearchResult r) => r.Hits.Select(h => $"{h.PassageIndex}:{h.Tier}:{h.Score:R}:{string.Join("|", h.Reasons)}")
        .Concat(r.Chips.Select(c => $"chip:{c.Kind}:{c.Text}")).Append($"{r.State}/{r.Mode}/{r.TotalDocuments}/{r.TotalPassages}").ToList();

    SearchIndex OpenDisk(SearchIndexOptions? o = null) => SearchIndex.Open(Syn.Gen, _root, o ?? new SearchIndexOptions(), _log.Add);
    string Published => Directory.GetDirectories(_root).Single(d => !Path.GetFileName(d).StartsWith('.'));

    [Fact]
    public void DiskEngineReturnsExactlyWhatTheMemoryEngineReturns()
    {
        var mem = new SearchService(SearchIndex.Build(Syn.Gen), _ => false);
        foreach (var built in new[] { true, false })   // freshly built, then reopened from disk
        {
            var disk = new SearchService(OpenDisk(), _ => false);
            Assert.Equal("disk", disk.Index.Engine);
            foreach (var q in Queries) Assert.Equal(Sig(mem.Search(q, new SearchFilters())), Sig(disk.Search(q, new SearchFilters())));
            Assert.Contains(_log, l => l.Contains(built ? "built and published" : "opened"));
            _log.Clear();
        }
    }

    [Fact]
    public void WithdrawnDocumentsAreNeverReturnedByTheDiskEngine()
    {
        var hidden = Syn.Gen.Documents.Keys.First(k => k.StartsWith("syn-j-"));
        var disk = new SearchService(OpenDisk(), d => d == hidden);
        foreach (var q in Queries)
            Assert.DoesNotContain(disk.Search(q, new SearchFilters()).Hits, h => disk.Index.Passages[h.PassageIndex].DocId == hidden);
    }

    [Fact]
    public void AnInterruptedBuildIsNeverServedAndIsCleanedUpAtTheNextStart()
    {
        Assert.Throws<IOException>(() => OpenDisk(new SearchIndexOptions { FailAfterTerms = 10 }));
        Assert.Single(Directory.GetDirectories(_root, ".building-*"));
        Assert.DoesNotContain(Directory.GetDirectories(_root), d => !Path.GetFileName(d).StartsWith('.'));   // nothing published
        Microsoft.Data.Sqlite.SqliteConnection.ClearAllPools();
        var ix = OpenDisk();
        Assert.Empty(Directory.GetDirectories(_root, ".building-*"));
        Assert.Contains(_log, l => l.Contains("removing interrupted build"));
        Assert.Equal(Sig(new SearchService(SearchIndex.Build(Syn.Gen), _ => false).Search("notice", new SearchFilters())),
                     Sig(new SearchService(ix, _ => false).Search("notice", new SearchFilters())));
    }

    [Fact]
    public void ACorruptedIndexIsQuarantinedAndRebuilt()
    {
        OpenDisk();
        Microsoft.Data.Sqlite.SqliteConnection.ClearAllPools();
        var db = Path.Combine(Published, IndexStore_DbFile);
        using (var f = new FileStream(db, FileMode.Open, FileAccess.ReadWrite)) { f.Position = f.Length / 2; var b = new byte[64]; f.ReadExactly(b); for (int i = 0; i < b.Length; i++) b[i] ^= 0x5A; f.Position = f.Length / 2; f.Write(b); }
        _log.Clear();
        var ix = OpenDisk();
        Assert.Contains(_log, l => l.Contains("SHA-256 differs"));
        Assert.Single(Directory.GetDirectories(_root, ".quarantine-*"));
        Assert.Contains(_log, l => l.Contains("built and published"));
        Assert.Equal(Sig(new SearchService(SearchIndex.Build(Syn.Gen), _ => false).Search("hearing", new SearchFilters())),
                     Sig(new SearchService(ix, _ => false).Search("hearing", new SearchFilters())));
    }

    [Fact]
    public void ATruncatedIndexIsRefusedWhenRebuildIsDisabled()
    {
        OpenDisk();
        Microsoft.Data.Sqlite.SqliteConnection.ClearAllPools();
        var db = Path.Combine(Published, IndexStore_DbFile);
        using (var f = new FileStream(db, FileMode.Open, FileAccess.ReadWrite)) f.SetLength(f.Length / 3);
        var e = Assert.Throws<IndexIntegrityException>(() => OpenDisk(new SearchIndexOptions { RebuildOnFailure = false, VerifyOnOpen = false }));
        Assert.Contains("size differs", e.Message);   // detected even without the full hash
    }

    [Fact]
    public void AnIndexForDifferentContentIsRebuiltNotServed()
    {
        OpenDisk();
        var mf = Path.Combine(Published, "MANIFEST.json");
        File.WriteAllText(mf, File.ReadAllText(mf).Replace("\"source_digest\": \"", "\"source_digest\": \"0"));
        _log.Clear();
        OpenDisk();
        Assert.Contains(_log, l => l.Contains("source digest differs"));
        Assert.Contains(_log, l => l.Contains("built and published"));
    }

    [Fact]
    public void OlderGenerationIndexesAreKeptForRollbackUpToTheLimit()
    {
        OpenDisk();
        var current = Published;
        for (int i = 0; i < 4; i++)
        {
            var d = Directory.CreateDirectory(Path.Combine(_root, $"R-old-{i}")).FullName;
            File.WriteAllText(Path.Combine(d, "MANIFEST.json"), "{}");
            File.SetLastWriteTimeUtc(Path.Combine(d, "MANIFEST.json"), DateTime.UtcNow.AddDays(-10 + i));
        }
        Microsoft.Data.Sqlite.SqliteConnection.ClearAllPools();
        OpenDisk(new SearchIndexOptions { KeepPrevious = 2 });
        var left = Directory.GetDirectories(_root).Where(d => !Path.GetFileName(d).StartsWith('.')).Select(Path.GetFileName).OrderBy(x => x).ToList();
        Assert.Equal(new[] { "R-old-2", "R-old-3", Path.GetFileName(current) }.OrderBy(x => x), left);
    }

    const string IndexStore_DbFile = "search.sqlite";
}
