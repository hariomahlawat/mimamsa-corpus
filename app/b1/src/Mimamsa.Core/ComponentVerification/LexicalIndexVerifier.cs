// C16 Stage 3 S3-B (B04): LEXICAL_INDEX verification of a prebuilt ADR-0007 index (search.sqlite + MANIFEST.json)
// against the verified generation, WITHOUT rebuilding it:
//   SQLITE_QUICK_CHECK + manifest  IndexStore.Verify (format, generation, size, SHA-256 against MANIFEST.json,
//                                  quick_check, metadata, document/term/passage counts);
//   SOURCE_DIGEST_EQUALS_SITE      the ADR-0007 source digest of the site's own indexed documents equals the manifest's
//                                  (and the release component's declared source_digest);
//   SAMPLED_POSTINGS_REDERIVE      a deterministic sample of documents (stratified by type, seeded by the release id) is
//                                  re-tokenised with the index's own tokeniser: its docs row (doc id, derivative, service,
//                                  passage lengths) and, for every term it contains, its postings (passages and positions)
//                                  must equal the fresh tokenisation; a seeded sample of vocabulary terms is decoded in
//                                  full (structure: ascending passages and positions within the passage length) and any
//                                  posting it has into a sampled document must be one the tokenisation produced;
//   SAMPLED_QUERY_PARITY           a seeded sample of queries drawn from the sampled documents is evaluated by the real
//                                  query engine (SearchService) twice, restricted to the sampled documents: on the shipped
//                                  index, and on the same index with the sampled documents' postings and lengths replaced by
//                                  the site rebuild. Hits, tiers and scores must be identical.
// A matching file digest is necessary, never sufficient (arch §4): the sampled checks catch content that was rewritten
// consistently with its manifest. The index is adopted (IndexStore, AdoptShipped) only after these checks pass.
using System.Diagnostics;
using System.Text.Json.Nodes;
using Microsoft.Data.Sqlite;
using Mimamsa.Core.Generation;
using Mimamsa.Core.Search;

namespace Mimamsa.Core.ComponentVerification;

public static class LexicalIndexVerifier
{
    public static readonly string[] Required = ["SQLITE_QUICK_CHECK", "SAMPLED_POSTINGS_REDERIVE", "SAMPLED_QUERY_PARITY", "SOURCE_DIGEST_EQUALS_SITE"];
    public const string Postings = "SAMPLED_POSTINGS_REDERIVE", Queries = "SAMPLED_QUERY_PARITY";

    /// The ADR-0007 source digest of the generation's indexed documents (what the site would build).
    public static string SiteSourceDigest(GenerationStore g) => IndexStore.SourceDigest(SearchIndex.IndexedDocuments(g));

    /// `dir` holds search.sqlite and MANIFEST.json as shipped. `declaredSourceDigest`: the release component's value (or
    /// null to skip that comparison). `postings` and `queries` from B04Sampling.Effective (or a study override).
    public static ComponentEvidence Verify(GenerationStore g, string dir, string releaseId, string? declaredSourceDigest,
                                           EffectiveSample postings, EffectiveSample queries, int? termSample = null)
    {
        var ev = new ComponentEvidence("LEXICAL_INDEX");
        var sw = Stopwatch.StartNew();
        var digest = SiteSourceDigest(g);
        if (declaredSourceDigest is not null && declaredSourceDigest != digest)
            ev.Fail("SOURCE_DIGEST_EQUALS_SITE", "the release's declared source digest is not the site's");
        var why = IndexStore.Verify(dir, g.GenerationId, digest, full: true);
        if (why is not null)
        {
            var check = why.Contains("source digest", StringComparison.Ordinal) ? "SOURCE_DIGEST_EQUALS_SITE" : "SQLITE_QUICK_CHECK";
            ev.Fail(check, why);
            ev.NotRun(Postings, "index failed its manifest checks");
            ev.NotRun(Queries, "index failed its manifest checks");
            return ev;
        }
        ev.Pass("SQLITE_QUICK_CHECK"); ev.Pass("SOURCE_DIGEST_EQUALS_SITE");
        ev.TimingsMs["manifest_and_quick_check"] = sw.ElapsedMilliseconds;
        var db = Path.Combine(dir, IndexStore.DbFile);
        SearchIndex ix;
        try { ix = SearchIndex.OpenForVerification(g, db); }
        catch (Exception e) when (e is IndexIntegrityException or SqliteException or InvalidDataException or InvalidCastException or FormatException)
        {
            ev.Fail(Postings, "index unreadable: " + e.Message);
            ev.NotRun(Queries, "index unreadable");
            return ev;
        }
        try
        {
            sw.Restart();
            var docs = SearchIndex.IndexedDocuments(g);
            var strata = docs.GroupBy(d => d.DocType, StringComparer.Ordinal).ToDictionary(x => x.Key, x => x.Select(d => d.DocId).ToList(), StringComparer.Ordinal);
            var sampleIds = docs.Count == 0 ? [] : B04Sampling.Stratified(releaseId, Postings, strata, postings.Size);
            var diOf = new Dictionary<string, int>(StringComparer.Ordinal);
            for (int i = 0; i < ix.Docs.Count; i++) diOf[ix.Docs[i].DocId] = i;
            var rebuilt = Rederive(ix, sampleIds.Select(id => diOf[id]).ToList(), out var lens, out var services);
            var issues = PostingIssues(ix, db, rebuilt, lens, services, releaseId, termSample ?? postings.Size, out var termsChecked);
            ev.TimingsMs["postings"] = sw.ElapsedMilliseconds;
            if (issues.Count == 0) ev.Pass(Postings); else foreach (var i in issues.Take(20)) ev.Fail(Postings, i);
            var ps = postings.ToJson();
            ps["selection"] = "DETERMINISTIC_STRATIFIED_SEEDED_BY_RELEASE_ID"; ps["unit"] = "document"; ps["population"] = docs.Count;
            ps["selected"] = sampleIds.Count; ps["passages"] = lens.Count; ps["terms_rederived"] = rebuilt.Count; ps["vocabulary_terms_decoded"] = termsChecked;
            ps["seed"] = releaseId;
            ev.Samples[Postings] = ps;

            sw.Restart();
            var qissues = QueryParity(ix, rebuilt, lens, sampleIds, releaseId, queries.Size, out var ran);
            ev.TimingsMs["queries"] = sw.ElapsedMilliseconds;
            if (ran == 0 && sampleIds.Count > 0) ev.Fail(Queries, "no query could be drawn from the sampled documents");
            else if (qissues.Count == 0) ev.Pass(Queries); else foreach (var i in qissues.Take(20)) ev.Fail(Queries, i);
            var qs = queries.ToJson();
            qs["selection"] = "DETERMINISTIC_SEEDED_BY_RELEASE_ID"; qs["unit"] = "query over the sampled documents"; qs["selected"] = ran; qs["seed"] = releaseId;
            ev.Samples[Queries] = qs;
            ev.Facts["documents"] = docs.Count; ev.Facts["passages"] = ix.N; ev.Facts["terms"] = ix.VocabularySize;
        }
        finally { SqliteConnection.ClearAllPools(); }
        return ev;
    }

    /// Fresh tokenisation of the sampled documents: term -> postings (global passage index, positions) in passage order.
    static Dictionary<string, List<SearchIndex.Posting>> Rederive(SearchIndex ix, List<int> sampleDocs, out Dictionary<int, int> lens, out Dictionary<int, string?> services)
    {
        var map = new Dictionary<string, List<SearchIndex.Posting>>(StringComparer.Ordinal);
        lens = new(); services = new();
        foreach (var di in sampleDocs.Order())
        {
            var d = ix.Docs[di];
            var ordered = SearchIndex.OrderedPassages(d).ToList();
            var idx = ix.DocPassages[di];
            int army = 0, navy = 0, air = 0;
            for (int k = 0; k < ordered.Count && k < idx.Length; k++)
            {
                var t = SearchIndex.Tokenise(ordered[k]);
                lens[idx[k]] = t.Len; army += t.Army; navy += t.Navy; air += t.Air;
                foreach (var (term, pos) in t.Groups)
                    (map.TryGetValue(term, out var l) ? l : map[term] = []).Add(new SearchIndex.Posting(idx[k], pos));
            }
            services[di] = Legal.LegalIdentifierResolver.ServiceOf(d, army, navy, air);
        }
        return map;
    }

    static int[] Varints(byte[] b)
    {
        var res = new List<int>(); int i = 0;
        while (i < b.Length)
        {
            uint v = 0; int shift = 0;
            while (true) { if (i >= b.Length || shift > 28) throw new InvalidDataException("corrupt passage lengths"); byte x = b[i++]; v |= (uint)(x & 0x7F) << shift; if (x < 0x80) break; shift += 7; }
            res.Add((int)v);
        }
        return res.ToArray();
    }

    static bool Same(SearchIndex.Posting a, SearchIndex.Posting b) => a.P == b.P && a.Pos.AsSpan().SequenceEqual(b.Pos);

    static List<string> PostingIssues(SearchIndex ix, string db, Dictionary<string, List<SearchIndex.Posting>> rebuilt, Dictionary<int, int> lens,
                                      Dictionary<int, string?> services, string releaseId, int termSample, out int termsChecked)
    {
        var issues = new List<string>();
        // 1. docs rows of the sampled documents, read from the file (not through the loader)
        using (var c = new SqliteConnection(SqlitePostingTable.ReadOnlyConnectionString(db)))
        {
            c.Open();
            foreach (var (di, svc) in services)
            {
                using var q = new SqliteCommand("SELECT doc_id, derivative_id, service, lens FROM docs WHERE di = $d", c);
                q.Parameters.AddWithValue("$d", di);
                using var r = q.ExecuteReader();
                var d = ix.Docs[di];
                if (!r.Read()) { issues.Add($"docs row {di} missing"); continue; }
                if (r.GetString(0) != d.DocId) issues.Add($"docs row {di}: document differs");
                if ((r.IsDBNull(1) ? null : r.GetString(1)) != d.DerivativeId) issues.Add($"docs row {d.DocId}: derivative differs");
                if ((r.IsDBNull(2) ? null : r.GetString(2)) != svc) issues.Add($"docs row {d.DocId}: service differs from the re-tokenisation");
                int[] stored;
                try { stored = Varints((byte[])r[3]); } catch (InvalidDataException) { issues.Add($"docs row {d.DocId}: lengths unreadable"); continue; }
                var want = ix.DocPassages[di].Select(p => lens.GetValueOrDefault(p, -1)).ToArray();
                if (!stored.AsSpan().SequenceEqual(want)) issues.Add($"docs row {d.DocId}: passage lengths differ from the re-tokenisation");
            }
        }
        var sampled = new HashSet<int>(lens.Keys);
        // 2. every term of the sampled documents: its postings into those documents equal the re-tokenisation
        foreach (var (term, want) in rebuilt)
        {
            List<SearchIndex.Posting> got;
            try { if (!ix.Postings.TryGetValue(term, out got)) { issues.Add($"term '{Clip(term)}' of a sampled document is not in the index"); continue; } }
            catch (InvalidDataException) { issues.Add($"postings of '{Clip(term)}' unreadable"); continue; }
            var inSample = got.Where(p => sampled.Contains(p.P)).ToList();
            if (inSample.Count != want.Count || !inSample.Zip(want).All(x => Same(x.First, x.Second)))
                issues.Add($"postings of '{Clip(term)}' differ from the re-tokenisation of the sampled documents");
        }
        // 3. a seeded sample of vocabulary terms decoded in full: structure, and nothing extra into sampled documents
        var vocab = ix.Postings.Keys.ToList();
        var terms = vocab.Count == 0 ? [] : B04Sampling.Seeded(releaseId, Postings + ":terms", vocab, termSample);
        termsChecked = terms.Count;
        foreach (var term in terms)
        {
            List<SearchIndex.Posting> got;
            try { got = ix.Postings[term]; }
            catch (InvalidDataException) { issues.Add($"postings of '{Clip(term)}' unreadable"); continue; }
            int prev = -1;
            foreach (var p in got)
            {
                if (p.P <= prev || p.P >= ix.N) { issues.Add($"postings of '{Clip(term)}' are not ascending passages of this index"); break; }
                prev = p.P;
                if (p.Pos.Length == 0 || p.Pos.Zip(p.Pos.Skip(1)).Any(x => x.Second <= x.First) || p.Pos[^1] >= ix.LenOf(p.P))
                { issues.Add($"postings of '{Clip(term)}' have positions outside the passage"); break; }
                if (sampled.Contains(p.P) && !(rebuilt.TryGetValue(term, out var w) && w.Any(x => Same(x, p))))
                { issues.Add($"postings of '{Clip(term)}' name a sampled passage the re-tokenisation does not"); break; }
            }
        }
        return issues;
    }

    static string Clip(string s) => s.Length <= 24 ? s : s[..24] + "…";

    /// Posting table: the shipped one, with postings into the sampled passages replaced by the rebuilt ones.
    sealed class Overlay(PostingTable shipped, Dictionary<string, List<SearchIndex.Posting>> rebuilt, HashSet<int> sampled) : PostingTable
    {
        readonly List<string> _keys = shipped.Keys.Concat(rebuilt.Keys.Where(k => shipped.Df(k) == 0)).ToList();
        public override IEnumerable<string> Keys => _keys;
        public override int Count => _keys.Count;
        public override int Df(string term) { int d = shipped.Df(term); return d > 0 ? d : rebuilt.TryGetValue(term, out var l) ? l.Count : 0; }
        public override bool TryGetValue(string term, out List<SearchIndex.Posting> list)
        {
            var have = shipped.TryGetValue(term, out var s);
            var r = rebuilt.GetValueOrDefault(term);
            if (!have && r is null) { list = null!; return false; }
            list = (s ?? []).Where(p => !sampled.Contains(p.P)).Concat(r ?? []).OrderBy(p => p.P).ToList();
            return true;
        }
    }

    static List<string> QueryParity(SearchIndex ix, Dictionary<string, List<SearchIndex.Posting>> rebuilt, Dictionary<int, int> lens, List<string> sampleIds,
                                    string releaseId, int size, out int ran)
    {
        ran = 0;
        var issues = new List<string>();
        if (sampleIds.Count == 0) return issues;
        var keep = new HashSet<string>(sampleIds, StringComparer.Ordinal);
        var rebuiltIx = ix.WithPostings(new Overlay(ix.Postings, rebuilt, [.. lens.Keys]), lens);
        // candidate queries from the sampled documents' own tokens (stopwords and one-letter terms skipped)
        var candidates = new HashSet<string>(StringComparer.Ordinal);
        foreach (var p in lens.Keys.Order())
        {
            var toks = Text.Tokenize(ix.Passages[p].Text).Select(t => t.Term).Where(t => t.Length > 2 && !Text.Stopwords.Contains(t)).Take(12).ToList();
            for (int i = 0; i < toks.Count; i++)
            {
                candidates.Add(toks[i]);
                if (toks[i].Length >= 5 && char.IsLetter(toks[i][0])) candidates.Add(toks[i][..4] + "*");
                if (i + 1 < toks.Count && toks[i + 1] != toks[i]) { candidates.Add($"{toks[i]} {toks[i + 1]}"); candidates.Add($"\"{toks[i]} {toks[i + 1]}\""); }
            }
        }
        if (candidates.Count == 0) return issues;
        var queries = B04Sampling.Seeded(releaseId, Queries, candidates, size);
        var shippedSvc = new SearchService(ix, d => !keep.Contains(d));
        var rebuiltSvc = new SearchService(rebuiltIx, d => !keep.Contains(d));
        foreach (var q in queries)
        {
            ran++;
            var a = shippedSvc.Search(q, new SearchFilters());
            var b = rebuiltSvc.Search(q, new SearchFilters());
            bool same = a.State == b.State && a.Mode == b.Mode && a.Hits.Count == b.Hits.Count
                        && a.Hits.Zip(b.Hits).All(x => x.First.PassageIndex == x.Second.PassageIndex && x.First.Tier == x.Second.Tier
                                                       && BitConverter.DoubleToInt64Bits(x.First.Score) == BitConverter.DoubleToInt64Bits(x.Second.Score));
            if (!same) issues.Add($"query {ran} ranks differently on the shipped index than on the site rebuild of the sampled documents");
        }
        return issues;
    }
}
