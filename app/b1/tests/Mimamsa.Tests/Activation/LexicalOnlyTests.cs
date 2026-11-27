// C16 B06, contract 2.1 lexical-only knowledge releases (B06 interface, "Model compatibility"): classification, the
// model gate (M1, M2, K1, K2) on a real site, a null MODELS pointer, per-pin semantic availability, and the search
// service skipping the semantic path (no query embedding) when the pin disallows it.
using System.Text;
using System.Text.Json.Nodes;
using Mimamsa.Core.Activation;
using Mimamsa.Core.Search;

namespace Mimamsa.Tests.Activation;

public class LexicalOnlyTests
{
    static byte[] Cp1Release() => File.ReadAllBytes(TestDirs.RepoFile("app", "contract", "fixtures", "c16", "v2_1", "cp1", "KNOWLEDGE_RELEASE.json"));
    static byte[] Bytes(JsonNode n) => Encoding.UTF8.GetBytes(n.ToJsonString());

    [Fact]
    public void Classification_follows_the_release_manifest_or_a_degraded_vector_outcome()
    {
        Assert.True(LexicalOnly.Classify(Cp1Release()));                           // the CP-1 release: no VECTOR_PACK
        var withPack = JsonNode.Parse(Cp1Release())!;
        withPack["components"]!.AsArray().Add(new JsonObject { ["kind"] = "VECTOR_PACK", ["component_id"] = "vectors" });
        Assert.False(LexicalOnly.Classify(Bytes(withPack)));
        var full = JsonNode.Parse(Cp1Release())!;
        full["capability"]!["declared_service_level"] = "FULL";
        Assert.False(LexicalOnly.Classify(Bytes(full)));
        var shipped = JsonNode.Parse(Cp1Release())!;
        foreach (var a in shipped["capability"]!["accounting"]!.AsArray()) if ((string?)a!["kind"] == "VECTOR_PACK") a["status"] = "SHIPPED";
        Assert.False(LexicalOnly.Classify(Bytes(shipped)));
        Assert.True(LexicalOnly.Classify(Bytes(withPack), "ACTIVE_DEGRADED"));      // vectors rejected, B04 rule 2
        Assert.False(LexicalOnly.Classify("{not json"u8.ToArray()));              // unreadable: the stricter rule K1

        using var site = FixtureSite.Simple("lexclass", "R1");
        var cat = new GenerationCatalog(site.Layout);
        Assert.True(cat.StageGeneration("L9", Cp1Release(), 0));
        Assert.True(cat.IsLexicalOnly("L9"));
        Assert.False(cat.IsLexicalOnly("R1"));
    }

    [Fact]
    public void A_site_without_a_model_serves_lexical_only_and_installs_a_verified_model_later()
    {
        using var site = new FixtureSite("lexsite", ["L1", "L2", "R2"], "L1", null,
            new Dictionary<string, (bool, string[])> { ["MX"] = (false, []), ["M2"] = (true, ["R2"]) }, lexicalOnly: ["L1", "L2"]);
        Assert.Null(site.Layout.ReadPointer("MODELS"));
        Assert.Equal("", File.ReadAllText(site.Layout.ModelsPointer));               // explicit: no model installed
        var p = new ActivationParticipant(new SiteInspector(site.Layout, site.NewReader()));
        Assert.True(p.LoadHead());
        using var eng = new ActivationEngine(new ActivationEngineOptions
        {
            Site = site.Layout, WriterId = "activator-1", Database = site.Db, Exclusions = site.NewReader(),
            Participant = new DirectParticipantLink(p), Disk = new FixedDiskProbe(1L << 40),
        });
        eng.AcquireLock();
        var pin = p.Pin();
        Assert.Null(pin.Models);
        Assert.False(pin.SemanticSearch);
        p.Unpin(pin);
        Assert.Equal("NO_MODEL", Assert.Throws<ActivationRefused>(() => eng.Transition("KNOWLEDGE", "R2")).Code);  // K1
        eng.Transition("KNOWLEDGE", "L2");                                                                         // K2
        Assert.Equal("NOT_STAGED", Assert.Throws<ActivationRefused>(() => eng.Transition("MODELS", "MX")).Code); // M1
        eng.Transition("MODELS", "M2");                                                                            // M2 waived
        Assert.Equal("M2", p.LoadedModels);
        var lex = p.Pin();
        Assert.False(lex.SemanticSearch);                                            // lexical-only knowledge
        p.Unpin(lex);
        eng.Transition("KNOWLEDGE", "R2");                                                                         // K1 met
        var full = p.Pin();
        Assert.True(full.SemanticSearch);
        Assert.True(p.SemanticSearchAvailable());
        p.Unpin(full);
        Assert.Equal(["BEGIN", "DECIDED", "OPEN"], ActivationJournal.Read(site.Layout.JournalPath).Entries.Take(3).Select(e => e.Step));
    }

    sealed class CountingScorer : ISemanticScorer
    {
        public int Calls;
        public string Description => "counting test scorer";
        public IReadOnlyList<(int Passage, double Score)> TopK(string query, int k) { Interlocked.Increment(ref Calls); return [(0, 0.99)]; }
    }

    [Fact]
    public void Semantic_path_and_query_embedding_are_skipped_when_the_pin_disallows_them()
    {
        var scorer = new CountingScorer();
        bool allowed = false;
        var ix = SearchIndex.Build(Syn.Gen);
        var svc = new SearchService(ix, _ => false) { Semantic = scorer, SemanticAllowed = () => allowed };
        var lexical = new SearchService(ix, _ => false);
        var off = svc.Search("notice of court martial", new SearchFilters());
        Assert.Equal(0, scorer.Calls);                                               // no query embedding at all
        Assert.Null(svc.ActiveSemantic);
        Assert.NotEqual("hybrid", off.Mode);
        var plain = lexical.Search("notice of court martial", new SearchFilters());
        Assert.Equal(plain.Hits.Select(h => h.PassageIndex), off.Hits.Select(h => h.PassageIndex));   // exactly lexical
        allowed = true;
        svc.Search("notice of court martial", new SearchFilters());
        Assert.True(scorer.Calls > 0);
    }
}
