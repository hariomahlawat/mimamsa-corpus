// Query execution: identifier tier (pinned) -> identifier mentions -> BM25 ranked passages. Lexical only in B1:
// there is no semantic/vector layer, and the response says so ("mode" is "identifier" or "lexical", never "hybrid").
using Mimamsa.Core.Generation;

namespace Mimamsa.Core.Search;

public sealed record SearchFilters(IReadOnlySet<string>? Types = null, IReadOnlySet<string>? Courts = null, int? YearFrom = null,
                                   int? YearTo = null, IReadOnlySet<string>? Statuses = null)
{
    public bool Any => Types is { Count: > 0 } || Courts is { Count: > 0 } || YearFrom is not null || YearTo is not null || Statuses is { Count: > 0 };
}

public sealed record Chip(string Kind, string Text, string? Source);
public sealed record Hit(int PassageIndex, string Tier, double Score, IReadOnlyList<string> Reasons);
public sealed record FacetValue(string Value, int Count);

public sealed record SearchResult(string State, string Mode, IReadOnlyList<Chip> Chips, IReadOnlyList<Hit> Hits,
                                  int TotalPassages, int TotalDocuments, IReadOnlyDictionary<string, IReadOnlyList<FacetValue>> Facets,
                                  string? Error, int? ErrorPosition, IReadOnlyList<string> HighlightTerms,
                                  IReadOnlyList<IReadOnlyList<string>> HighlightPhrases, IReadOnlyList<string> Notes,
                                  string? Service = null);

public sealed class SearchService
{
    public const int MaxHits = 200;
    readonly SearchIndex _ix;
    readonly Func<string, bool> _docHidden;   // withdrawn (serving fence) -> hidden from every surface

    public SearchService(SearchIndex ix, Func<string, bool> docHidden) { _ix = ix; _docHidden = docHidden; }
    public SearchIndex Index => _ix;
    /// C14 S4 hybrid PoC. Null (the default) = B1 lexical behaviour, unchanged.
    public ISemanticScorer? Semantic { get; init; }
    /// C16 B06 (2.1 lexical-only releases): when set and false for the current request, the semantic path is skipped
    /// entirely (no query embedding, no dense candidates); lexical search is unchanged. Null (default) = always allowed.
    public Func<bool>? SemanticAllowed { get; set; }
    /// The scorer this request may use: Semantic unless SemanticAllowed says no.
    public ISemanticScorer? ActiveSemantic => Semantic is not null && (SemanticAllowed?.Invoke() ?? true) ? Semantic : null;
    /// C15 WP2: optional cross-encoder rerank stage (off when null).
    public IReranker? Reranker { get; init; }
    /// C15 WP2/WP7: provision-heading boost for procedural queries (off when null).
    public ProvisionHeadings? Headings { get; init; }
    public HybridOptions Hybrid { get; init; } = new();
    /// C16 Stage 3 (activation only; default false = unchanged): documents hidden for this request (the response
    /// boundary) are dropped BEFORE the case-name and identifier chips are written, so a chip never names or counts
    /// an excluded judgment.
    public bool HideChipsOfHiddenDocuments { get; init; }

    sealed class Ctx
    {
        public bool Exact;
        public readonly HashSet<string> Highlight = new(StringComparer.Ordinal);
        public readonly List<IReadOnlyList<string>> Phrases = new();
        // C15 WP1: match counts per display term, in first-noted order; Reasons() builds the per-passage view on demand
        // for displayed hits only. C16 WP05: each display keeps the passage-ordered (passage, count) arrays its clauses
        // already produced (one segment per noting clause) instead of a dictionary entry per matched passage; a
        // passage's count for a display is the sum over that display's segments, exactly as the dictionary summed it.
        public readonly List<(string display, List<Seg> segs)> Matched = new();
        public readonly Dictionary<string, int> MatchedIndex = new(StringComparer.Ordinal);
        public readonly List<Chip> Chips = new();
        /// C15: passage -> reason for a provision-heading boost (shown with the match reasons).
        public readonly Dictionary<int, string> HeadingReasons = new();
    }

    /// Passages (ascending) noted for one display by one clause, with their counts (null = 1 each).
    readonly record struct Seg(int[] P, int[]? N, int Count);

    SpellingSuggester? _speller;
    SpellingSuggester Speller => _speller ??= new SpellingSuggester(_ix);

    public SearchResult Search(string raw, SearchFilters filters, bool plainAfterConfirmation = false, string? service = null)
    {
        var semantic = ActiveSemantic;   // C16 B06: null when the activation gate disables semantic search for this request
        ParsedQuery q;
        // A citation such as "(2013) 7 SCC 316" uses brackets as part of the identifier, not as query syntax (C14 F06).
        if (!plainAfterConfirmation && Legal.LegalIdentifierResolver.IsIdentifierQuery(raw ?? ""))
            q = new ParsedQuery(raw!, false, true, null, raw!.Split(' ', StringSplitOptions.RemoveEmptyEntries));
        else try { q = plainAfterConfirmation ? QueryParser.PlainWords(raw!) : QueryParser.Parse(raw!); }
        catch (ParseException e)
        {
            return new SearchResult("parser_error", "parser_error", Array.Empty<Chip>(), Array.Empty<Hit>(), 0, 0,
                new Dictionary<string, IReadOnlyList<FacetValue>>(), e.Message, e.Position, Array.Empty<string>(), Array.Empty<IReadOnlyList<string>>(), Array.Empty<string>());
        }
        var ctx = new Ctx { Exact = q.Exact };
        var notes = new List<string> { "Lexical search (BM25 word and phrase matching). Semantic search is not part of B1." };
        // C16 WP05: hits are held as entries (passage, score, explicit hit or -1) until a hit is read. Explicit hits are
        // the pinned, mention, case-name, title, heading-first, fused and reranked ones, created as before; a ranked
        // lexical hit (-1) is created on read as new Hit(p, "lexical", score, Reasons(p, ctx)), as it was eagerly.
        var ordered = new Entries(this, ctx);
        var seen = new HashSet<int>();
        string mode = "lexical";
        if (q.Exact) ctx.Chips.Add(new Chip("mode", "Exact: lexical only, no abbreviation expansion", null));

        if (q.Plain)
        {
            var (pinned, mentions, rest) = IdentifierTiers(q.Raw, ctx);
            foreach (var h in pinned) if (seen.Add(h.PassageIndex)) ordered.Add(h);
            // Case-name tier (C14 F02): a query naming the parties pins those judgments above judgments that cite them.
            if (rest.Count > 0 && Identifiers.Recognise(q.Raw).Count == 0 && _ix.Resolver.ResolveCaseName(rest) is { } cn0
                && (HideChipsOfHiddenDocuments ? VisibleCaseNames(cn0) : cn0) is { } cn)
            {
                if (cn.TooMany)
                    ctx.Chips.Add(new Chip("case_name", HideChipsOfHiddenDocuments ? "Party name matches many judgments" : $"Party name matches {cn.Count} judgments",
                        $"Too many to pin. Add the other party (“X v Y”), the year, or use party:“{string.Join(" ", cn.Terms)}”. Results below are ranked by words."));
                else
                {
                    ctx.Chips.Add(new Chip("case_name", cn.Docs.Count == 1 ? $"Case name · {_ix.Resolver.CaseLabel(cn.Docs[0])}" : $"Case name · {cn.Docs.Count} judgments with these parties",
                        "Matched against the parties recorded in the judgment metadata (crawler, not verified). Judgments that only cite the case follow as ranked results."));
                    foreach (var d in cn.Docs)
                        if (seen.Add(_ix.DocPassages[d][0]))
                            ordered.Add(new Hit(_ix.DocPassages[d][0], "case_name", 1e9, new[] { $"Case name: parties {_ix.Resolver.CaseLabel(d)} (metadata, not verified)" }));
                }
            }
            if (ordered.Count > 0) mode = "identifier";
            foreach (var h in mentions) if (seen.Add(h.PassageIndex)) ordered.Add(h);
            if (!q.Exact && mode == "lexical" && rest.Count > 0 && Speller.Suggest(rest) is { } suggestion)
                ctx.Chips.Add(new Chip("suggestion", $"Did you mean: {suggestion}", suggestion));
            if (rest.Count > 0)
            {
                // Short-title match: plain words that are exactly an instrument's title (ignoring years/stopwords) put
                // that instrument's first passage first, labelled as a title match.
                var words = rest.SelectMany(w => Text.Tokenize(w)).Select(t => t.Term).Where(t => !Text.Stopwords.Contains(t) && !t.All(char.IsDigit)).ToHashSet();
                if (words.Count >= 2)
                {
                    var titleSets = StatuteTitleSets;
                    for (int d = 0; d < _ix.Docs.Count; d++)
                        if (_ix.Docs[d].IsStatute && titleSets[d]!.SetEquals(words) && seen.Add(_ix.DocPassages[d][0]))
                            ordered.Add(new Hit(_ix.DocPassages[d][0], "title", 5e8, new[] { $"title match: {_ix.Docs[d].Title}" }));
                }
                var scores = PlainScores(rest, ctx);
                // C15 WP2/WP7: provision-heading boost for procedural plain-language queries (see ProvisionHeadings).
                if (!q.Exact && Headings is not null)
                    scores = Boost(scores, rest, ctx.HeadingReasons);
                // In hybrid and rerank modes the matched provisions are placed before fused/reranked results (after the
                // identifier, case-name and title tiers): rank fusion would otherwise dilute the boost. Added after the
                // C14 walkthrough queries showed no effect in hybrid mode (development data; DECLARATIONS.md item 3).
                if (ctx.HeadingReasons.Count > 0 && (semantic is not null || Reranker is not null) && !q.Exact)
                    foreach (var p in ctx.HeadingReasons.Keys.Where(scores.Contains).OrderByDescending(scores.ScoreOf).ThenBy(p => p))
                        if (!_docHidden(_ix.Passages[p].DocId) && seen.Add(p)) ordered.Add(new Hit(p, "lexical", scores.ScoreOf(p), Reasons(p, ctx)));
                // ---- C15 WP2 rerank stage (begin). Only when a reranker is configured; pinned tiers above are untouched.
                if (Reranker is not null && !q.Exact)
                {
                    var lex = scores.Ranked();
                    var query = string.Join(" ", rest);
                    var dense = semantic is null ? new List<(int Passage, double Score)>()
                        : semantic.TopK(query, Hybrid.RerankPool, p => !_docHidden(_ix.Passages[p].DocId)).ToList();
                    var pool = new List<(int p, bool lexical)>();
                    var inPool = new HashSet<int>();
                    foreach (var p in lex.Where(p => !seen.Contains(p) && !_docHidden(_ix.Passages[p].DocId)).Take(Hybrid.RerankPool)) if (inPool.Add(p)) pool.Add((p, true));
                    foreach (var (p, _) in dense) if (!seen.Contains(p) && inPool.Add(p)) pool.Add((p, false));
                    var rr = pool.Count == 0 ? Array.Empty<float>() : Reranker.Score(query, pool.Select(x => _ix.Passages[x.p].Text).ToList());
                    var kept = pool.Select((x, i) => (x.p, x.lexical, s: rr[i], i))
                                   .Where(x => x.lexical || x.s >= Hybrid.RerankAdmit)
                                   .OrderByDescending(x => x.s).ThenBy(x => x.i).ToList();
                    foreach (var k in kept)
                    {
                        if (!seen.Add(k.p)) continue;
                        var why = new List<string>(k.lexical ? Reasons(k.p, ctx) : Array.Empty<string>());
                        why.Add($"Reranked by textual relevance (cross-encoder logit {k.s:0.00}); textual relevance is not legal relevance");
                        ordered.Add(new Hit(k.p, k.lexical ? "lexical" : "semantic", k.s, why));
                    }
                    ordered.AddRanked(scores, seen);   // lexical tail beyond the pool
                    if (mode == "lexical" && pool.Count > 0) mode = "hybrid";
                    notes[0] = $"Hybrid search (BM25{(semantic is null ? "" : $" with embedding candidates: {semantic.Description}")}, reranked by {Reranker.Description}). Identifier matches are placed first and are never re-ranked.";
                }
                else
                // ---- C15 WP2 rerank stage (end)
                // ---- C14 S4 hybrid hook (begin). Only plain, non-exact queries; identifier and title tiers above are
                // already placed and are never re-ranked. With no semantic scorer this block is skipped entirely.
                if (semantic is not null && !q.Exact)
                {
                    var lex = scores.Ranked();
                    // C15 WP2: eligibility is applied inside the dense scan (withdrawn passages never use up depth)
                    var dense = semantic.TopK(string.Join(" ", rest), Hybrid.DenseDepth, p => !_docHidden(_ix.Passages[p].DocId))
                                        .Where(x => x.Score >= Hybrid.MinSimilarity).ToList();
                    var sim = dense.ToDictionary(x => x.Passage, x => x.Score);
                    foreach (var f in HybridFusion.Rrf(lex, dense.Select(x => x.Passage).ToList(), Hybrid))
                    {
                        if (!seen.Add(f.Passage)) continue;
                        var why = new List<string>(f.LexRank is null ? Array.Empty<string>() : Reasons(f.Passage, ctx));
                        if (f.DenseRank is { } dr) why.Add($"Similar wording (embedding similarity {sim[f.Passage]:0.00}, rank {dr}); similarity is not legal relevance");
                        ordered.Add(new Hit(f.Passage, f.LexRank is null ? "semantic" : "lexical", f.Fused, why));
                    }
                    ordered.AddRanked(scores, seen);   // lexical tail beyond fusion depth
                    if (mode == "lexical" && dense.Count > 0) mode = "hybrid";
                    notes[0] = $"Hybrid search (BM25 fused with embedding similarity: {semantic.Description}). Identifier matches are placed first and are never re-ranked.";
                }
                else
                // ---- C14 S4 hybrid hook (end)
                ordered.AddRanked(scores, seen);
            }
        }
        else
        {
            var scores = Eval(q.Root!, ctx);
            ordered.AddRanked(scores, seen);
            DescribeChips(q.Root!, ctx);
        }

        // eligibility is decided once per document within this query (C15 WP1), not once per passage hit
        var hiddenByDoc = new sbyte[_ix.Docs.Count];   // 0 not yet asked, 1 hidden, 2 shown
        ordered.Keep(p =>
        {
            int d = _ix.DocOf(p);
            if (hiddenByDoc[d] == 0) hiddenByDoc[d] = _docHidden(_ix.Docs[d].DocId) ? (sbyte)1 : (sbyte)2;
            return hiddenByDoc[d] == 2;
        });
        if (service is not null && Legal.LegalIdentifierResolver.ServiceLabels.TryGetValue(service, out var svcLabel))
        {
            ServicePreference(ordered, service, hybrid: mode == "hybrid");
            notes.Add($"Service preference: {svcLabel}. Ranked results from {svcLabel} instruments and judgments are raised and those of other services lowered; identifier, case-name and mention tiers are unchanged and nothing is excluded.");
        }
        else service = null;
        var facets = Facets(ordered, filters);
        var passByDoc = new sbyte[_ix.Docs.Count];
        ordered.Keep(p =>
        {
            int d = _ix.DocOf(p);
            if (passByDoc[d] == 0) passByDoc[d] = Pass(_ix.Docs[d], filters, null) ? (sbyte)2 : (sbyte)1;
            return passByDoc[d] == 2;
        });
        int docs = 0;
        var counted = new bool[_ix.Docs.Count];
        for (int i = 0; i < ordered.Count; i++) if (!counted[_ix.DocOf(ordered.P[i])]) { counted[_ix.DocOf(ordered.P[i])] = true; docs++; }
        var filtered = ordered.ToHitList();
        var state = filtered.Count > 0 ? "results" : "empty";
        // All filtered hits are returned in relevance order; the HTTP layer pages them by document (C14 F10).
        return new SearchResult(state, mode, ctx.Chips, filtered, filtered.Count, docs, facets, null, null,
            ctx.Highlight.ToList(), ctx.Phrases, notes, service);
    }

    /// HideChipsOfHiddenDocuments: the case-name match without hidden judgments (null when none is left).
    Legal.CaseNameMatch? VisibleCaseNames(Legal.CaseNameMatch cn)
    {
        if (cn.TooMany) return cn;   // no judgment is named and the chip text carries no count in this mode
        var docs = cn.Docs.Where(d => !_docHidden(_ix.Docs[d].DocId)).ToList();
        return docs.Count == 0 ? null : cn with { Docs = docs, Count = docs.Count };
    }

    // ------------------------------------------------------------------ service preference (C14 F09, short term)
    public const double SameServiceBoost = 1.6, OtherServicePenalty = 0.5;

    /// Re-orders only the ranked tiers ("lexical", "title"): a document of the preferred service scores ×1.6, one of
    /// another service ×0.5, a general document ×1.0. Pinned tiers keep their place and order. Deterministic.
    /// Hybrid mode (Codex review of PR #70): fused RRF scores, the raw-BM25 lexical tail beyond LexicalDepth and
    /// dense-only ("semantic") hits are not on one scale, so the preference is applied to a rank-based score
    /// 1/(RrfK + position) over the incoming hybrid order (fused hits, then the tail). Equal multipliers therefore keep
    /// that order exactly, and dense-only hits are ranked with the others instead of being treated as pinned.
    /// Lexical-only search keeps the original BM25 × multiplier behaviour.
    /// C16 WP05: applied to the entries in place (same order and scores as the former list version).
    void ServicePreference(Entries hits, string service, bool hybrid = false)
    {
        bool Ranked(int i) => hits.Tier(i) is "lexical" || (hybrid && hits.Tier(i) is "semantic");
        double F(int p) => _ix.Service[_ix.DocOf(p)] is not { } s ? 1.0 : s == service ? SameServiceBoost : OtherServicePenalty;
        var fixedPart = new List<int>();
        var ranked = new List<int>();
        for (int i = 0; i < hits.Count; i++) (Ranked(i) ? ranked : fixedPart).Add(i);
        var s = new double[ranked.Count];
        for (int i = 0; i < ranked.Count; i++) s[i] = (hybrid ? 1.0 / (HybridRankK + i + 1) : hits.S[ranked[i]]) * F(hits.P[ranked[i]]);
        var order = Ranking.Descending(s, ranked.Count);   // by s descending, then by i (stable)
        hits.Reorder(fixedPart.Concat(order.Select(k => ranked[k])).ToArray(), fixedPart.Count, order.Select(k => s[k]).ToArray());
    }

    /// Same constant as the default RRF k (HybridOptions.RrfK), so a position weight matches the fusion's own scale.
    public const int HybridRankK = 60;

    // ------------------------------------------------------------------ document-level pages and instrument groups (C14 F10, F11)
    public sealed record GroupVariant(int Doc, string Label, int Passage);
    public sealed record ResultGroup(int Doc, IReadOnlyList<GroupVariant> Variants);
    public sealed record ResultPage(IReadOnlyList<Hit> Hits, IReadOnlyList<ResultGroup> Groups, int Page, int PageSize, int PageCount, int TotalGroups,
                                    IReadOnlyDictionary<int, int> PassageCounts);
    public const int DefaultPageSize = 25, MaxPageSize = 100;

    /// Groups hits by instrument (editions and language versions of one instrument form one group, represented by
    /// the English, unsuffixed copy when it has hits) and returns one page of groups. Passages keep the relevance
    /// order of the full result; sort "new"/"old" orders groups by the representative's date (undated last).
    public ResultPage Page(SearchResult r, int page, int size, string? sort)
    {
        size = Math.Clamp(size <= 0 ? DefaultPageSize : size, 1, MaxPageSize);
        var order = new List<string>();
        var members = new Dictionary<string, List<int>>(StringComparer.Ordinal);
        var firstPassage = new Dictionary<int, int>();
        // C16 WP05: passages are read from the hit list without creating Hit objects; only the page's hits are created.
        var all = r.Hits;
        var hl = all as HitList;
        int n = all.Count;
        int PassageAt(int i) => hl is not null ? hl.PassageAt(i) : all[i].PassageIndex;
        for (int i = 0; i < n; i++)
        {
            int p = PassageAt(i), d = _ix.DocOf(p);
            if (!firstPassage.TryAdd(d, p)) continue;
            var key = _ix.GroupKey[d];
            if (!members.TryGetValue(key, out var l)) { members[key] = l = new(); order.Add(key); }
            l.Add(d);
        }
        var groups = order.Select(k =>
        {
            var ds = members[k];
            int rep = ds.OrderBy(d => Legal.LegalIdentifierResolver.PrimaryRank(_ix.Docs[d])).ThenBy(d => ds.IndexOf(d)).First();
            return new ResultGroup(rep, ds.Where(d => d != rep).Select(d => new GroupVariant(d, Legal.LegalIdentifierResolver.VariantLabel(_ix.Docs[d]), firstPassage[d])).ToList());
        }).ToList();
        if (sort is "new" or "old")
        {
            var idx = groups.Select((g, i) => (g, i)).ToList();
            string Date(ResultGroup g) => _ix.Docs[g.Doc].IssueDate ?? "";
            groups = (sort == "new"
                ? idx.OrderBy(x => Date(x.g).Length == 0).ThenByDescending(x => Date(x.g), StringComparer.Ordinal)
                : idx.OrderBy(x => Date(x.g).Length == 0).ThenBy(x => Date(x.g), StringComparer.Ordinal)).ThenBy(x => x.i).Select(x => x.g).ToList();
        }
        int pages = Math.Max(1, (groups.Count + size - 1) / size);
        page = Math.Clamp(page <= 0 ? 1 : page, 1, pages);
        var slice = groups.Skip((page - 1) * size).Take(size).ToList();
        // Passages carried by a page: the first LeadPassages in relevance order (unchanged from before paging, so the
        // top of the ranking is complete), then at most PassagesPerGroup per document. Counts are reported per group.
        var shown = slice.Select(g => g.Doc).ToHashSet();
        var perDoc = new Dictionary<int, int>();
        var counts = new Dictionary<int, int>();
        var hits = new List<Hit>();
        for (int i = 0; i < n; i++)
        {
            int d = _ix.DocOf(PassageAt(i));
            if (!shown.Contains(d)) continue;
            counts[d] = counts.GetValueOrDefault(d) + 1;
            if (hits.Count < LeadPassages || perDoc.GetValueOrDefault(d) < PassagesPerGroup) { hits.Add(all[i]); perDoc[d] = perDoc.GetValueOrDefault(d) + 1; }
        }
        return new ResultPage(hits, slice, page, size, pages, groups.Count, counts);
    }
    public const int LeadPassages = 20, PassagesPerGroup = 3;

    // ------------------------------------------------------------------ identifier tiers
    (List<Hit> pinned, List<Hit> mentions, List<string> rest) IdentifierTiers(string raw, Ctx ctx)
    {
        var ids = Identifiers.Recognise(raw);
        var pinned = new List<Hit>(); var mentions = new List<Hit>();
        // words outside identifier spans
        var outside = new System.Text.StringBuilder();
        int last = 0;
        foreach (var id in ids) { outside.Append(raw, last, id.Start - last).Append(' '); last = id.End; }
        outside.Append(raw[last..]);
        var restWords = outside.ToString().Split(' ', StringSplitOptions.RemoveEmptyEntries).ToList();

        foreach (var id in ids.Where(i => i.Kind != IdKind.Section))
        {
            var idToks = Text.Tokenize(id.Raw).Select(t => t.Term).ToList();
            var label = id.Kind switch { IdKind.NeutralCitation => "Neutral citation", IdKind.ReportedCitation => "Reported citation", _ => "Case number" };
            var docs = new SortedSet<int>();
            if (_ix.MetaIds.TryGetValue(id.Normalized, out var m)) docs.UnionWith(m);
            var cover = new SortedSet<int>();
            if (_ix.CoverIds.TryGetValue(id.Normalized, out var c)) cover.UnionWith(c.Where(d => !docs.Contains(d)));
            if (HideChipsOfHiddenDocuments) { docs.RemoveWhere(d => _docHidden(_ix.Docs[d].DocId)); cover.RemoveWhere(d => _docHidden(_ix.Docs[d].DocId)); }
            ctx.Chips.Add(new Chip("identifier", $"{label} · {id.Raw.Trim()}", docs.Count + cover.Count > 0 ? $"{docs.Count + cover.Count} matching document(s)" : "no document carries this identifier"));
            if (docs.Count + cover.Count == 0 && id.Kind is IdKind.ReportedCitation or IdKind.NeutralCitation)
                ctx.Chips.Add(new Chip("not_held", $"Citation not recorded in this library: {id.Raw.Trim()}",
                    "No held document carries this citation in its metadata or in the masthead of its first page. Parallel citations (SCC, AIR, SCALE) are often not recorded: search the party names or the neutral citation. Absence here is not evidence that the judgment is not held, or that it does not exist."));
            ctx.Phrases.Add(idToks);
            var mentionHits = PhraseOccurrences(idToks);
            // A document-level identifier pins ONE representative passage per matching document: a passage that
            // contains the identifier (labelled as such), else the document's first passage (labelled as a document
            // match, not an identifier hit). Other passages are not inflated into identifier hits (review F05).
            foreach (var (set, why) in new[] { (docs, $"{label} {id.Raw.Trim()} in document metadata"), (cover, $"{label} {id.Raw.Trim()} printed at the top of p.1 (extracted, not verified)") })
                foreach (var d in set)
                {
                    var ps = _ix.DocPassages[d];
                    var withId = ps.Where(mentionHits.Contains).ToList();
                    if (withId.Count > 0)
                        foreach (var p in withId.Take(3))
                            pinned.Add(new Hit(p, "identifier", 1e9, new[] { why, "the identifier appears in this passage" }));
                    else
                        pinned.Add(new Hit(ps[0], "document", 1e9, new[] { why + "; this passage is the document's first passage and does not itself contain the identifier" }));
                }
            foreach (var (p, n) in mentionHits.Pairs().OrderByDescending(kv => kv.n).ThenBy(kv => kv.p))
                if (!docs.Contains(_ix.DocOf(p)) && !cover.Contains(_ix.DocOf(p)))
                    mentions.Add(new Hit(p, "mention", 1e6 + n, new[] { $"mentions {id.Raw.Trim()} ({n}); a mention is not the identified document" }));
        }

        foreach (var id in ids.Where(i => i.Kind == IdKind.Section))
        {
            // Instrument scoping (review F05, F14) and short names/abbreviations (C14 F01): Legal.LegalIdentifierResolver.
            var scope = _ix.Resolver.ResolveInstrument(restWords);
            var actWords = scope.Terms.ToList();
            void AliasChips()
            {
                foreach (var a in scope.Aliases)
                    ctx.Chips.Add(new Chip("alias", $"{a.Alias.ToUpperInvariant()} → {a.HeldTitle}",
                        $"The letters “{a.Alias.ToUpperInvariant()}” were read as the held instrument “{a.HeldTitle}”. An alias says which title was searched; it is not a statement that two instruments are equivalent."));
            }
            if (scope.Kind == Legal.ScopeKind.NotHeld)
            {
                ctx.Chips.Add(new Chip("not_held", $"No instrument titled “{scope.Text}” in this library",
                    $"{id.ProvisionWord} {id.Base}{id.Sub} was not looked up in any other instrument. The words are searched as plain text. Absence here is not evidence that the instrument or provision does not exist."));
                ctx.Phrases.Add(Text.Tokenize(id.Raw).Select(t => t.Term).ToList());
                continue;
            }
            if (scope.Kind == Legal.ScopeKind.Ambiguous)
            {
                ctx.Chips.Add(new Chip("ambiguous", $"{id.ProvisionWord} {id.Base}{id.Sub}: which instrument?", "Several instruments could be meant: " + scope.Text + ". Add the full title or year."));
                AliasChips();
                restWords.Clear();
                continue;
            }
            var scoped = scope.Docs.ToList();
            var scopeText = scope.Text;
            if (scope.Kind == Legal.ScopeKind.Scoped) restWords.Clear();
            var label = $"{id.ProvisionWord} {id.Base}{id.Sub}";
            ctx.Chips.Add(new Chip("identifier", $"{label} · {scopeText}", null));
            AliasChips();
            var found = new List<(int p, int strength)>();
            foreach (var d in scoped)
                foreach (var p in _ix.DocPassages[d])
                {
                    int st = Identifiers.ProvisionStrength(_ix.Passages[p].Text, id.Base!, id.Sub, true);
                    if (st > 0) found.Add((p, st));
                }
            foreach (var (p, st) in found.OrderByDescending(x => x.strength).ThenBy(x => x.p))
                pinned.Add(new Hit(p, "identifier", 1e9 + st, new[] { st switch
                {
                    3 => $"{label}: provision text in {_ix.Docs[_ix.DocOf(p)].Title}",
                    2 => $"{label}: heading in {_ix.Docs[_ix.DocOf(p)].Title}",
                    _ => $"{label}: reference in {_ix.Docs[_ix.DocOf(p)].Title}",
                } }));
            // mentions in other documents: provision reference together with the Act's name in the same passage
            if (actWords.Count > 0 && scoped.Count > 0 && scopeText != "")
            {
                var actPhrase = actWords;
                foreach (var (p, _) in PhraseOccurrences(actPhrase).Pairs())
                    if (!scoped.Contains(_ix.DocOf(p)) && Identifiers.PassageHasProvision(_ix.Passages[p].Text, id.Base!, id.Sub, false))
                        mentions.Add(new Hit(p, "mention", 1e6, new[] { $"refers to {label} of {string.Join(" ", actWords)}" }));
            }
            ctx.Phrases.Add(Text.Tokenize(id.Raw).Select(t => t.Term).ToList());
        }
        return (pinned, mentions, restWords);
    }

    static string NormTitle(string? t) => Legal.LegalIdentifierResolver.NormTitle(t);

    /// C16 WP05: the normalised title words of every statute (null for other documents), computed once per index
    /// instead of once per document for every query of two or more words. Same words, same comparison.
    HashSet<string>?[]? _titleSets;
    HashSet<string>?[] StatuteTitleSets => _titleSets ??= _ix.Docs.Select(d => d.IsStatute ? NormTitle(d.Title).Split(' ').ToHashSet() : null).ToArray();

    /// Phrase occurrences, ascending by passage (passage, count).
    sealed class Occ(int[] p, int[] n, int count)
    {
        public static readonly Occ None = new(Array.Empty<int>(), Array.Empty<int>(), 0);
        public readonly int[] P = p, N = n;
        public readonly int Count = count;
        public bool Contains(int passage) => Array.BinarySearch(P, 0, Count, passage) >= 0;
        public IEnumerable<(int p, int n)> Pairs() { for (int i = 0; i < Count; i++) yield return (P[i], N[i]); }
    }

    /// C15 WP1: merge join over the passage-ordered posting lists with binary search on the ascending positions (same
    /// result and order as the B1 dictionary/HashSet version, without materialising every posting). C16 WP05: the
    /// result is a pair of passage-ordered arrays instead of a dictionary (it was filled in passage order).
    Occ PhraseOccurrences(IReadOnlyList<string> terms)
    {
        if (terms.Count == 0 || terms.Any(t => !_ix.Postings.ContainsKey(t))) return Occ.None;
        var first = _ix.Postings[terms[0]];
        var others = terms.Skip(1).Select(t => _ix.Postings[t]).ToArray();
        var at = new int[others.Length];
        var cur = new int[]?[others.Length];
        var ps = new List<int>(); var ns = new List<int>();
        foreach (var post in first)
        {
            bool all = true;
            for (int k = 0; k < others.Length; k++)
            {
                var l = others[k];
                while (at[k] < l.Count && l[at[k]].P < post.P) at[k]++;
                cur[k] = at[k] < l.Count && l[at[k]].P == post.P ? l[at[k]].Pos : null;
                if (cur[k] is null) all = false;
            }
            if (!all) continue;
            int n = 0;
            foreach (var pos in post.Pos)
            {
                bool ok = true;
                for (int k = 0; k < others.Length && ok; k++) ok = Array.BinarySearch(cur[k]!, pos + k + 1) >= 0;
                if (ok) n++;
            }
            if (n > 0) { ps.Add(post.P); ns.Add(n); }
        }
        return ps.Count == 0 ? Occ.None : new Occ(ps.ToArray(), ns.ToArray(), ps.Count);
    }

    /// Positions of `term` in passage p (binary search on the passage-ordered list), or null.
    static int[]? PositionsIn(List<SearchIndex.Posting> post, int p)
    {
        int lo = 0, hi = post.Count - 1;
        while (lo <= hi)
        {
            int mid = (lo + hi) >>> 1, c = post[mid].P.CompareTo(p);
            if (c == 0) return post[mid].Pos;
            if (c < 0) lo = mid + 1; else hi = mid - 1;
        }
        return null;
    }

    // ------------------------------------------------------------------ plain words (ranked any-word match)
    Scored PlainScores(List<string> words, Ctx ctx)
    {
        var clauses = new List<(string display, QNode node, double weight)>();
        foreach (var w in words)
        {
            var toks = Text.Tokenize(w).Select(t => t.Term).ToList();
            if (toks.Count == 0) continue;
            if (toks.Count == 1 && Text.Stopwords.Contains(toks[0]) && words.Count > 1) continue;
            clauses.Add((w, toks.Count == 1 ? new QTerm(toks[0], false) : new QPhrase(toks, w), 1.0));
            var code = w.Trim('.', ',', ';', ':', '?', '!');
            if (!ctx.Exact && _ix.Abbrev.TryGetValue(code, out var ab) && code.All(char.IsUpper))
            {
                foreach (var meaning in ab.Preferred)
                {
                    var mt = Text.Tokenize(meaning).Select(t => t.Term).ToList();
                    if (mt.Count > 0) clauses.Add((meaning, mt.Count == 1 ? new QTerm(mt[0], false) : new QPhrase(mt, meaning), 0.8));
                }
                ctx.Chips.Add(new Chip("abbreviation", $"{code} → {string.Join(" | ", ab.Preferred)}",
                    (ab.Preferred.Count > 1 ? "several meanings searched; " : "one listed meaning searched; context decides; ") + ab.Origin));
            }
        }
        if (clauses.Count == 0) return Scored.Empty;
        var total = clauses.Count(c => c.weight >= 1.0);
        // Every clause is evaluated first, in order (their notes and highlights are recorded in the same order as
        // before); then the per-passage sums are formed in clause order, exactly as the dictionary accumulated them.
        var evals = clauses.Select(c => Eval(c.node, ctx)).ToList();
        var ps = new List<int>(); var s = new List<double>();
        double sum = 0; int hits = 0, cur = -1;
        void Close() { if (cur >= 0) { ps.Add(cur); s.Add(sum * (0.5 + 0.5 * Math.Min(1.0, (double)Math.Max(hits, 1) / Math.Max(total, 1)))); } }
        // coordination: passages matching more of the user's words rank higher (Lucene classic coord)
        var walk = new KWay(evals.Select(r => (r.P, r.Count)).ToArray());
        while (walk.Next(out int p, out int c, out int i))
        {
            if (p != cur) { Close(); cur = p; sum = 0; hits = 0; }
            sum = sum + evals[c].S[i] * clauses[c].weight;
            hits = hits + (clauses[c].weight >= 1.0 ? 1 : 0);
        }
        Close();
        return new Scored(ps.ToArray(), s.ToArray(), ps.Count);
    }

    /// C15 WP2/WP7 provision-heading boost on the passage-ordered scores (ProvisionHeadings.Picks; same rule and
    /// arithmetic as ProvisionHeadings.Boost on a dictionary: boosted passages get the new score, new ones are added).
    Scored Boost(Scored scores, IReadOnlyList<string> words, Dictionary<int, string> reasons)
    {
        var picks = Headings!.Picks(scores.ScoreOf, () => scores.Count > 0 ? scores.Max() : 1.0, words);
        if (picks.Count == 0) return scores;
        var map = new SortedDictionary<int, double>();
        foreach (var (p, s, why) in picks) { map[p] = s; reasons[p] = why; }
        return scores.With(map);
    }

    // ------------------------------------------------------------------ Boolean evaluation
    IEnumerable<string> Variants(string term, bool prefix, Ctx ctx)
    {
        if (prefix) return _ix.Postings.Keys.Where(k => k.StartsWith(term, StringComparison.Ordinal)).Take(256);
        if (ctx.Exact) return new[] { term };
        return _ix.StemGroups.TryGetValue(Text.Stem(term), out var g) ? g.Append(term).Distinct() : new[] { term };
    }

    /// Records that `display` matched passages `ps` (ascending) with counts `ns` (null = 1 each). The display takes
    /// its place in first-noted order when it is first noted with at least one passage, as before.
    static void Note(Ctx ctx, string display, int[] ps, int[]? ns, int count)
    {
        if (count == 0) return;
        if (!ctx.MatchedIndex.TryGetValue(display, out var i)) { i = ctx.Matched.Count; ctx.MatchedIndex[display] = i; ctx.Matched.Add((display, new List<Seg>())); }
        ctx.Matched[i].segs.Add(new Seg(ps, ns, count));
    }

    Scored Eval(QNode node, Ctx ctx)
    {
        switch (node)
        {
            case QTerm t:
            {
                var lists = new List<List<SearchIndex.Posting>>();
                foreach (var v in Variants(t.Term, t.Prefix, ctx))
                {
                    if (!_ix.Postings.TryGetValue(v, out var post)) continue;
                    ctx.Highlight.Add(v);
                    lists.Add(post);
                }
                int[] ps, tf;
                if (lists.Count == 1)
                {
                    var l = lists[0];
                    ps = new int[l.Count]; tf = new int[l.Count];
                    for (int i = 0; i < l.Count; i++) { ps[i] = l[i].P; tf[i] = l[i].Pos.Length; }
                }
                else
                {
                    // union of the variants' passage-ordered lists; tf is the sum of their position counts
                    var arrays = lists.Select(l => { var a = new int[l.Count]; for (int i = 0; i < a.Length; i++) a[i] = l[i].P; return a; }).ToArray();
                    var pl = new List<int>(); var tl = new List<int>();
                    var walk = new KWay(arrays.Select(a => (a, a.Length)).ToArray());
                    while (walk.Next(out int p, out int li, out int ii))
                    {
                        int n = lists[li][ii].Pos.Length;
                        if (pl.Count > 0 && pl[^1] == p) tl[^1] += n; else { pl.Add(p); tl.Add(n); }
                    }
                    ps = pl.ToArray(); tf = tl.ToArray();
                }
                double idf = _ix.Idf(ps.Length);
                var s = new double[ps.Length];
                for (int i = 0; i < ps.Length; i++) s[i] = idf * _ix.TfNorm(tf[i], ps[i]);
                Note(ctx, t.Term + (t.Prefix ? "*" : ""), ps, tf, ps.Length);
                return new Scored(ps, s, ps.Length);
            }
            case QPhrase ph:
            {
                var occ = PhraseOccurrences(ph.Terms);
                ctx.Phrases.Add(ph.Terms);
                // Df is the posting-list length (TryGetValue(t).Count before), read without loading the list
                double idf = ph.Terms.Sum(t => _ix.Postings.Df(t) is var df && df > 0 ? _ix.Idf(df) : 0);
                // A phrase that is itself a provision identifier ("Rule 8(3)(a)"): the provision's own text in an Act or
                // Rules document ranks before passages that merely mention it (exact-identifier rule, design 03 §2).
                var ids = Identifiers.Recognise(ph.Display);
                var prov = ids.Count == 1 && ids[0].Kind == IdKind.Section && ids[0].Start == 0 && ids[0].End >= ph.Display.TrimEnd().Length ? ids[0] : null;
                var s = new double[occ.Count];
                var provText = new List<int>();
                for (int i = 0; i < occ.Count; i++)
                {
                    int p = occ.P[i];
                    s[i] = idf * _ix.TfNorm(occ.N[i], p);
                    if (prov is not null && _ix.Docs[_ix.DocOf(p)].IsStatute)
                    {
                        int st = Identifiers.ProvisionStrength(_ix.Passages[p].Text, prov.Base!, prov.Sub, true);
                        if (st >= 2) { s[i] += 1000 * st; provText.Add(p); }
                    }
                }
                Note(ctx, "“" + ph.Display + "”", occ.P, occ.N, occ.Count);
                if (prov is not null) Note(ctx, $"{prov.ProvisionWord} {prov.Base}{prov.Sub} provision text", provText.ToArray(), null, provText.Count);
                return new Scored(occ.P, s, occ.Count);
            }
            case QAnd a:
            {
                var pos = a.Items.Where(i => i is not QNot).ToList();
                var neg = a.Items.OfType<QNot>().ToList();
                Scored? acc = null;
                foreach (var i in pos)
                {
                    var r = Eval(i, ctx);
                    acc = acc is null ? r : Scored.Intersect(acc, r);
                }
                acc ??= Scored.All(_ix.N);
                foreach (var n in neg)
                {
                    var r = Eval(n.Item, new Ctx { Exact = ctx.Exact });
                    acc = Scored.Except(acc, r);
                }
                return acc;
            }
            case QOr o:
            {
                // items are evaluated in order first (notes and highlights as before); each passage's score is then
                // 0.0 + s(item 0) + s(item 1) + ... over the items that matched it, in item order (GetValueOrDefault + s)
                var rs = o.Items.Select(i => Eval(i, ctx)).ToList();
                var ps = new List<int>(); var s = new List<double>();
                var walk = new KWay(rs.Select(r => (r.P, r.Count)).ToArray());
                while (walk.Next(out int p, out int li, out int ii))
                {
                    if (ps.Count > 0 && ps[^1] == p) s[^1] = s[^1] + rs[li].S[ii];
                    else { ps.Add(p); s.Add(0.0 + rs[li].S[ii]); }
                }
                return new Scored(ps.ToArray(), s.ToArray(), ps.Count);
            }
            case QNot n:
            {
                var r = Eval(n.Item, new Ctx { Exact = ctx.Exact });
                return Scored.Except(Scored.All(_ix.N), r);
            }
            case QNear nr:
            {
                var l = Eval(nr.Left, ctx); var r = Eval(nr.Right, ctx);
                var spans = new SpanSource(this, ctx);
                var ps = new List<int>(); var ss = new List<double>();
                for (int i = 0, j = 0; i < l.Count && j < r.Count;)
                {
                    int c = l.P[i].CompareTo(r.P[j]);
                    if (c < 0) { i++; continue; }
                    if (c > 0) { j++; continue; }
                    int p = l.P[i];
                    var ls = spans.Of(nr.Left, p); var rsp = spans.Of(nr.Right, p);
                    if (ls.Any(x => rsp.Any(y => Math.Max(0, Math.Max(x.s, y.s) - Math.Min(x.e, y.e) - 1) <= nr.Distance)))
                    { ps.Add(p); ss.Add(l.S[i] + r.S[j]); }
                    i++; j++;
                }
                return new Scored(ps.ToArray(), ss.ToArray(), ps.Count);
            }
            case QField f: return EvalField(f, ctx);
            default: return Scored.Empty;
        }
    }

    /// Word or phrase positions in one passage, for NEAR. C16 WP05: the posting lists of each operand are resolved
    /// once per NEAR evaluation instead of once per candidate passage (same lists, same positions, same order).
    sealed class SpanSource(SearchService svc, Ctx ctx)
    {
        readonly Dictionary<QNode, List<List<SearchIndex.Posting>>?> _lists = new(ReferenceEqualityComparer.Instance);

        List<List<SearchIndex.Posting>>? Lists(QNode node)
        {
            if (_lists.TryGetValue(node, out var l)) return l;
            var ix = svc._ix;
            switch (node)
            {
                case QTerm t:
                    l = new();
                    foreach (var v in svc.Variants(t.Term, t.Prefix, ctx))
                        if (ix.Postings.TryGetValue(v, out var post)) l.Add(post);
                    break;
                case QPhrase ph:
                    l = ph.Terms.All(ix.Postings.ContainsKey) ? ph.Terms.Select(t => ix.Postings[t]).ToList() : null;
                    break;
            }
            return _lists[node] = l;
        }

        public List<(int s, int e)> Of(QNode node, int p)
        {
            var res = new List<(int, int)>();
            switch (node)
            {
                case QTerm t:
                    foreach (var post in Lists(t)!)
                        if (PositionsIn(post, p) is { } xs) res.AddRange(xs.Select(i => (i, i)));
                    break;
                case QPhrase ph:
                    if (Lists(ph) is { } lists)
                    {
                        var sets = lists.Select(post => PositionsIn(post, p)?.ToHashSet() ?? new()).ToList();
                        foreach (var st in sets[0])
                            if (Enumerable.Range(1, sets.Count - 1).All(k => sets[k].Contains(st + k))) res.Add((st, st + sets.Count - 1));
                    }
                    break;
                case QOr o: foreach (var i in o.Items) res.AddRange(Of(i, p)); break;
                default: throw new ParseException("NEAR works between words or phrases.", 0);
            }
            return res;
        }
    }

    Scored DocPassages(Func<DocumentRecord, bool> pred, double score = 0)
    {
        var ps = new List<int>();
        for (int d = 0; d < _ix.Docs.Count; d++)
            if (pred(_ix.Docs[d])) ps.AddRange(_ix.DocPassages[d]);
        var arr = ps.ToArray();
        // passages are numbered document by document, so this is already ascending; kept exact if it ever is not
        for (int i = 1; i < arr.Length; i++) if (arr[i] <= arr[i - 1]) { arr = arr.Distinct().Order().ToArray(); break; }
        var s = new double[arr.Length];
        Array.Fill(s, score);
        return new Scored(arr, s, arr.Length);
    }

    static bool Contains(string? hay, IReadOnlyList<string> terms)
    {
        if (hay is null || terms.Count == 0) return false;
        var toks = Text.Tokenize(hay).Select(t => t.Term).ToList();
        for (int i = 0; i + terms.Count <= toks.Count; i++)
            if (Enumerable.Range(0, terms.Count).All(k => toks[i + k] == terms[k])) return true;
        return false;
    }

    Scored EvalField(QField f, Ctx ctx)
    {
        switch (f.Field)
        {
            case "title": return DocPassages(d => Contains(d.Title, f.Terms), 0.5);
            case "party": return DocPassages(d => Contains(d.Judicial?.Petitioner, f.Terms) || Contains(d.Judicial?.Respondent, f.Terms));
            case "judge":
                ctx.Chips.Add(new Chip("caveat", "Judge metadata may be incomplete (crawler); absence here is not evidence.", "Supreme Court records often hold only the first judge. Read the bench from the original."));
                return DocPassages(d => d.Judicial?.Judges.Any(j => Contains(j, f.Terms)) == true);
            case "court": return DocPassages(d => Contains(d.Judicial?.Court ?? d.IssuingAuthority, f.Terms));
            case "bench": return DocPassages(d => Contains(d.Judicial?.Bench, f.Terms));
            case "type":
            {
                var v = f.Value.ToLowerInvariant().TrimEnd('s');
                return DocPassages(d => d.DocType.TrimEnd('s') == v || (v == "statute" && d.IsStatute));
            }
            case "case":
            {
                var n = Identifiers.NormCase(f.Value) ?? Identifiers.NormCitation(f.Value);
                return DocPassages(d => d.Judicial?.CaseNumbers.Any(c => (Identifiers.NormCase(c) ?? Identifiers.NormCitation(c)) == n) == true);
            }
            case "citation":
            {
                var n = Identifiers.NormCitation(f.Value);
                return DocPassages(d => d.Judicial is { } j && ((j.NeutralCitation is { } nc && Identifiers.NormCitation(nc) == n)
                                                               || j.ReportedCitations.Any(r => Identifiers.NormCitation(r) == n)));
            }
            case "date":
            case "year":
            {
                string from = f.RangeFrom ?? f.Value, to = f.RangeTo ?? f.Value;
                if (f.Field == "year") { from = from.Length == 4 ? from + "-01-01" : from; to = to.Length == 4 ? to + "-12-31" : to; }
                return DocPassages(d => d.IssueDate is { } dt && string.CompareOrdinal(dt, from) >= 0 && string.CompareOrdinal(dt, to) <= 0);
            }
            case "section":
            {
                var m = System.Text.RegularExpressions.Regex.Match(f.Value, @"^(?<n>\d{1,4}[A-Za-z]{0,2})(?<sub>(\([0-9a-zA-Z]{1,4}\))*)$");
                if (!m.Success) throw new ParseException("section: needs a number such as 69 or 8(3)(a).", 0);
                var baseNo = m.Groups["n"].Value.ToUpperInvariant(); var sub = m.Groups["sub"].Value;
                if (!_ix.Postings.TryGetValue(baseNo.ToLowerInvariant(), out var post)) return Scored.Empty;
                var ps = new List<int>(); var ss = new List<double>();
                var text = new List<int>(); var refs = new List<int>();
                foreach (var x in post)
                {
                    int st = Identifiers.ProvisionStrength(_ix.Passages[x.P].Text, baseNo, sub, _ix.Docs[_ix.DocOf(x.P)].IsStatute);
                    if (st > 0) { ps.Add(x.P); ss.Add(st >= 2 ? 1000.0 * st : 1.0); (st >= 2 ? text : refs).Add(x.P); }
                }
                // the two displays take their places in the order they were first noted (passage order)
                string tDisp = $"provision {baseNo}{sub} (text)", rDisp = $"reference to {baseNo}{sub}";
                if (text.Count > 0 && (refs.Count == 0 || text[0] < refs[0]))
                { Note(ctx, tDisp, text.ToArray(), null, text.Count); Note(ctx, rDisp, refs.ToArray(), null, refs.Count); }
                else
                { Note(ctx, rDisp, refs.ToArray(), null, refs.Count); Note(ctx, tDisp, text.ToArray(), null, text.Count); }
                ctx.Highlight.Add(baseNo.ToLowerInvariant());
                return new Scored(ps.ToArray(), ss.ToArray(), ps.Count);
            }
            case "act":
            {
                var res = DocPassages(d => d.IsStatute && Contains(d.Title, f.Terms), 0.5);
                ctx.Phrases.Add(f.Terms);
                var occ = PhraseOccurrences(f.Terms);
                Note(ctx, "“" + f.Value + "”", occ.P, occ.N, occ.Count);
                var one = new double[occ.Count];
                Array.Fill(one, 1.0);
                return Scored.Union(res, new Scored(occ.P, one, occ.Count));   // res[p] = res.GetValueOrDefault(p) + 1.0
            }
            default: return Scored.Empty;
        }
    }

    void DescribeChips(QNode n, Ctx ctx)
    {
        switch (n)
        {
            case QField f: ctx.Chips.Add(new Chip("field", $"{char.ToUpperInvariant(f.Field[0])}{f.Field[1..]} = {f.Value}", null)); break;
            case QNear nr: ctx.Chips.Add(new Chip("operator", $"NEAR/{nr.Distance}", "within that many words, any order")); DescribeChips(nr.Left, ctx); DescribeChips(nr.Right, ctx); break;
            case QAnd a: foreach (var i in a.Items) DescribeChips(i, ctx); break;
            case QOr o: foreach (var i in o.Items) DescribeChips(i, ctx); break;
            case QNot x: ctx.Chips.Add(new Chip("operator", "NOT " + Describe(x.Item), "excluded")); break;
            case QPhrase p: ctx.Chips.Add(new Chip("phrase", "“" + p.Display + "”", "contiguous words")); break;
        }
    }

    static string Describe(QNode n) => n switch
    {
        QTerm t => t.Term, QPhrase p => "“" + p.Display + "”", QField f => f.Field + ":" + f.Value, _ => "(group)"
    };

    /// C15 WP1: built on first read (only displayed hits are ever read), from the same per-passage match counts.
    /// C15 WP2: a provision-heading match adds its reason after the matched terms.
    /// C16 WP05: a display's count for p is the sum over its segments (binary search), as the dictionary summed it.
    IReadOnlyList<string> Reasons(int p, Ctx ctx) => new LazyReasons(() =>
    {
        var m = new List<KeyValuePair<string, int>>();
        foreach (var (display, segs) in ctx.Matched)
        {
            int n = 0; bool any = false;
            foreach (var g in segs)
            {
                int i = Array.BinarySearch(g.P, 0, g.Count, p);
                if (i >= 0) { any = true; n += g.N is null ? 1 : g.N[i]; }
            }
            if (any) m.Add(new KeyValuePair<string, int>(display, n));
        }
        var r = m.Count > 0
            ? new List<string> { "Matched: " + string.Join(", ", m.OrderByDescending(kv => kv.Value).Take(4).Select(kv => $"{(kv.Key.StartsWith('“') ? kv.Key : "'" + kv.Key + "'")} ({kv.Value})")) }
            : new List<string> { "Matched the query filters" };
        if (ctx.HeadingReasons.TryGetValue(p, out var h)) r.Add(h);
        return r;
    });

    sealed class LazyReasons(Func<List<string>> make) : IReadOnlyList<string>
    {
        readonly Lazy<List<string>> _v = new(make, LazyThreadSafetyMode.ExecutionAndPublication);
        public string this[int i] => _v.Value[i];
        public int Count => _v.Value.Count;
        public IEnumerator<string> GetEnumerator() => _v.Value.GetEnumerator();
        System.Collections.IEnumerator System.Collections.IEnumerable.GetEnumerator() => GetEnumerator();
    }

    // ------------------------------------------------------------------ filters and facets
    static bool Pass(DocumentRecord d, SearchFilters f, string? except)
    {
        if (except != "type" && f.Types is { Count: > 0 } && !f.Types.Contains(d.DocType)) return false;
        if (except != "court" && f.Courts is { Count: > 0 } && !f.Courts.Contains(d.CourtOrIssuer)) return false;
        if (except != "status" && f.Statuses is { Count: > 0 } && !f.Statuses.Contains(d.CorpusStatus)) return false;
        if (except != "year" && (f.YearFrom is not null || f.YearTo is not null))
        {
            if (d.Year is not { } y) return false;
            if (f.YearFrom is { } a && y < a) return false;
            if (f.YearTo is { } b && y > b) return false;
        }
        return true;
    }

    /// Facet counts over the distinct documents of the hits. C16 WP05: the documents are collected with one flag per
    /// document (ascending) instead of Distinct() over every hit; each facet's values are fully ordered (count, then
    /// value; or value), so the order in which documents are visited does not change the result.
    Dictionary<string, IReadOnlyList<FacetValue>> Facets(Entries hits, SearchFilters f)
    {
        var present = new bool[_ix.Docs.Count];
        for (int i = 0; i < hits.Count; i++) present[_ix.DocOf(hits.P[i])] = true;
        var docs = new List<DocumentRecord>();
        for (int d = 0; d < present.Length; d++) if (present[d]) docs.Add(_ix.Docs[d]);
        IReadOnlyList<FacetValue> Count(string name, Func<DocumentRecord, string?> key, bool byCountDesc = true)
        {
            var g = docs.Where(d => Pass(d, f, name)).GroupBy(d => key(d) ?? "Not recorded").Select(x => new FacetValue(x.Key, x.Count()));
            return (byCountDesc ? g.OrderByDescending(x => x.Count).ThenBy(x => x.Value, StringComparer.Ordinal) : g.OrderByDescending(x => x.Value, StringComparer.Ordinal)).ToList();
        }
        return new()
        {
            ["type"] = Count("type", d => d.DocType),
            ["court"] = Count("court", d => d.CourtOrIssuer),
            ["year"] = Count("year", d => d.Year?.ToString(), byCountDesc: false),
            ["status"] = Count("status", d => d.CorpusStatus),
        };
    }

    // ------------------------------------------------------------------ C16 WP05: evaluator data structures

    /// Hits of one query before they are read: parallel arrays of passage, score and explicit-hit index (-1 = a ranked
    /// lexical hit whose Hit is created on read with Reasons(p, ctx); otherwise an index into Explicit).
    sealed class Entries(SearchService svc, Ctx ctx)
    {
        public int[] P = new int[16];
        public double[] S = new double[16];
        public int[] X = new int[16];
        public int Count;
        public readonly List<Hit> Explicit = new();

        void Grow(int need)
        {
            if (need <= P.Length) return;
            int n = Math.Max(need, P.Length * 2);
            Array.Resize(ref P, n); Array.Resize(ref S, n); Array.Resize(ref X, n);
        }

        void Put(int p, double s, int x) { Grow(Count + 1); P[Count] = p; S[Count] = s; X[Count] = x; Count++; }

        public void Add(Hit h) { Explicit.Add(h); Put(h.PassageIndex, h.Score, Explicit.Count - 1); }

        /// The ranked lexical tier: passages by score descending, then passage ascending, skipping those already placed.
        public void AddRanked(Scored scores, HashSet<int> seen)
        {
            var order = scores.Order;   // ties keep index order = passage order
            Grow(Count + order.Length);
            foreach (var k in order)
            {
                int p = scores.P[k];
                if (seen.Contains(p)) continue;
                P[Count] = p; S[Count] = scores.S[k]; X[Count] = -1; Count++;
            }
        }

        public string Tier(int i) => X[i] < 0 ? "lexical" : Explicit[X[i]].Tier;

        /// Keeps, in order, the entries whose passage passes.
        public void Keep(Func<int, bool> pass)
        {
            int w = 0;
            for (int i = 0; i < Count; i++)
                if (pass(P[i])) { P[w] = P[i]; S[w] = S[i]; X[w] = X[i]; w++; }
            Count = w;
        }

        /// New order (indexes into the current entries); entries from position `rescoredFrom` on take `scores`.
        public void Reorder(int[] order, int rescoredFrom, double[] scores)
        {
            var p = new int[Count]; var s = new double[Count]; var x = new int[Count];
            for (int i = 0; i < order.Length; i++)
            {
                int k = order[i];
                p[i] = P[k]; x[i] = X[k];
                if (i < rescoredFrom) s[i] = S[k];
                else
                {
                    s[i] = scores[i - rescoredFrom];
                    if (X[k] >= 0) { Explicit.Add(Explicit[X[k]] with { Score = s[i] }); x[i] = Explicit.Count - 1; }   // as `h with { Score }`
                }
            }
            P = p; S = s; X = x;
        }

        public HitList ToHitList() => new(svc, ctx, P, S, X, Count, Explicit);
    }

    /// The returned hits. A ranked lexical hit is created on first read, exactly as it was created eagerly before
    /// (new Hit(p, "lexical", score, Reasons(p, ctx))), and then kept, so each index always returns the same object.
    sealed class HitList(SearchService svc, Ctx ctx, int[] p, double[] s, int[] x, int count, List<Hit> explicitHits) : IReadOnlyList<Hit>
    {
        readonly Dictionary<int, Hit> _made = new();
        public int Count => count;
        public int PassageAt(int i) => (uint)i < (uint)count ? p[i] : throw new ArgumentOutOfRangeException(nameof(i));
        public Hit this[int i]
        {
            get
            {
                if ((uint)i >= (uint)count) throw new ArgumentOutOfRangeException(nameof(i));
                if (x[i] >= 0) return explicitHits[x[i]];
                lock (_made)
                {
                    if (!_made.TryGetValue(i, out var h)) _made[i] = h = new Hit(p[i], "lexical", s[i], svc.Reasons(p[i], ctx));
                    return h;
                }
            }
        }
        public IEnumerator<Hit> GetEnumerator() { for (int i = 0; i < count; i++) yield return this[i]; }
        System.Collections.IEnumerator System.Collections.IEnumerable.GetEnumerator() => GetEnumerator();
    }
}

/// C16 WP05: matches of a query node as parallel arrays in ascending passage order (was Dictionary<int, double>).
/// Every operation reproduces the dictionary arithmetic exactly, in the same operand order.
internal sealed class Scored(int[] p, double[] s, int count)
{
    public static readonly Scored Empty = new(Array.Empty<int>(), Array.Empty<double>(), 0);
    public readonly int[] P = p;
    public readonly double[] S = s;
    public readonly int Count = count;

    public bool Contains(int passage) => Array.BinarySearch(P, 0, Count, passage) >= 0;
    /// The passage's score, or 0 when it has none (GetValueOrDefault).
    public double ScoreOf(int passage) => Array.BinarySearch(P, 0, Count, passage) is var i && i >= 0 ? S[i] : 0;

    /// Enumerable.Max over the scores (NaN skipped unless every score is NaN).
    public double Max()
    {
        int i = 0;
        double v = S[i];
        while (double.IsNaN(v)) { if (++i >= Count) return v; v = S[i]; }
        for (i++; i < Count; i++) if (S[i] > v) v = S[i];
        return v;
    }

    /// Indexes by score descending, then passage ascending (the former OrderByDescending(Value).ThenBy(Key)); sorted
    /// once and shared by the hybrid, rerank and ranked-tier steps of one query.
    public int[] Order => _order ??= Ranking.Descending(S, Count);
    int[]? _order;

    /// Passages in Order.
    public int[] Ranked() { var o = Order; var r = new int[o.Length]; for (int i = 0; i < o.Length; i++) r[i] = P[o[i]]; return r; }

    public static Scored All(int n)
    {
        var p = new int[n];
        for (int i = 0; i < n; i++) p[i] = i;
        return new Scored(p, new double[n], n);
    }

    /// a ∩ b with score a + b.
    public static Scored Intersect(Scored a, Scored b)
    {
        var p = new List<int>(); var s = new List<double>();
        for (int i = 0, j = 0; i < a.Count && j < b.Count;)
        {
            int c = a.P[i].CompareTo(b.P[j]);
            if (c < 0) i++;
            else if (c > 0) j++;
            else { p.Add(a.P[i]); s.Add(a.S[i] + b.S[j]); i++; j++; }
        }
        return new Scored(p.ToArray(), s.ToArray(), p.Count);
    }

    /// a minus the passages of b, scores of a.
    public static Scored Except(Scored a, Scored b)
    {
        var p = new List<int>(); var s = new List<double>();
        for (int i = 0, j = 0; i < a.Count; i++)
        {
            while (j < b.Count && b.P[j] < a.P[i]) j++;
            if (j < b.Count && b.P[j] == a.P[i]) continue;
            p.Add(a.P[i]); s.Add(a.S[i]);
        }
        return new Scored(p.ToArray(), s.ToArray(), p.Count);
    }

    /// a ∪ b with score a.GetValueOrDefault(p) + b (b-only passages: 0.0 + b; a-only passages: a).
    public static Scored Union(Scored a, Scored b)
    {
        var p = new List<int>(); var s = new List<double>();
        int i = 0, j = 0;
        while (i < a.Count || j < b.Count)
        {
            if (j >= b.Count || (i < a.Count && a.P[i] < b.P[j])) { p.Add(a.P[i]); s.Add(a.S[i]); i++; }
            else if (i >= a.Count || b.P[j] < a.P[i]) { p.Add(b.P[j]); s.Add(0.0 + b.S[j]); j++; }
            else { p.Add(a.P[i]); s.Add(a.S[i] + b.S[j]); i++; j++; }
        }
        return new Scored(p.ToArray(), s.ToArray(), p.Count);
    }

    /// A copy in which the given passages have the given scores (replaced, or added in passage order).
    public Scored With(SortedDictionary<int, double> set)
    {
        var p = new List<int>(Count + set.Count); var s = new List<double>(Count + set.Count);
        using var e = set.GetEnumerator();
        bool more = e.MoveNext();
        for (int i = 0; i < Count; i++)
        {
            while (more && e.Current.Key < P[i]) { p.Add(e.Current.Key); s.Add(e.Current.Value); more = e.MoveNext(); }
            if (more && e.Current.Key == P[i]) { p.Add(P[i]); s.Add(e.Current.Value); more = e.MoveNext(); }
            else { p.Add(P[i]); s.Add(S[i]); }
        }
        while (more) { p.Add(e.Current.Key); s.Add(e.Current.Value); more = e.MoveNext(); }
        return new Scored(p.ToArray(), s.ToArray(), p.Count);
    }
}

internal static class Ranking
{
    /// Indexes 0..n-1 ordered by key descending, ties by index ascending: the order of LINQ's stable
    /// OrderByDescending(key) (Comparer<double>.Default) over items in index order, without its per-item overhead.
    public static int[] Descending(double[] key, int n)
    {
        var neg = new double[n];
        var idx = new int[n];
        for (int i = 0; i < n; i++)
        {
            if (double.IsNaN(key[i])) return Enumerable.Range(0, n).OrderByDescending(k => key[k]).ToArray();   // never expected; exact fallback
            neg[i] = -key[i]; idx[i] = i;
        }
        Array.Sort(neg, idx);   // ascending -key = descending key; equal keys (0.0 and -0.0 included) are adjacent
        for (int a = 0, b = 1; b <= n; b++)
            if (b == n || neg[b] != neg[a]) { if (b - a > 1) Array.Sort(idx, a, b - a); a = b; }
        return idx;
    }
}

/// C16 WP05: k-way merge of passage-ordered lists. Yields every (passage, list, index) in passage order and, for one
/// passage, in list order, so per-passage sums can be formed in the same operand order as the former dictionary
/// accumulation (list 0 first). Holds O(k) state: no per-thread or per-corpus arrays.
internal sealed class KWay
{
    readonly (int[] P, int Count)[] _lists;
    readonly int[] _pos;
    readonly int[] _heap;   // list indexes, min-heap by (current passage, list index)
    int _n;

    public KWay((int[] P, int Count)[] lists)
    {
        _lists = lists;
        _pos = new int[lists.Length];
        _heap = new int[lists.Length];
        for (int i = 0; i < lists.Length; i++) if (lists[i].Count > 0) { _heap[_n] = i; Up(_n++); }
    }

    bool Less(int a, int b)
    {
        int pa = _lists[a].P[_pos[a]], pb = _lists[b].P[_pos[b]];
        return pa < pb || (pa == pb && a < b);
    }

    void Up(int i)
    {
        while (i > 0) { int parent = (i - 1) >> 1; if (!Less(_heap[i], _heap[parent])) break; (_heap[i], _heap[parent]) = (_heap[parent], _heap[i]); i = parent; }
    }

    void Down(int i)
    {
        while (true)
        {
            int l = 2 * i + 1, r = l + 1, m = i;
            if (l < _n && Less(_heap[l], _heap[m])) m = l;
            if (r < _n && Less(_heap[r], _heap[m])) m = r;
            if (m == i) return;
            (_heap[i], _heap[m]) = (_heap[m], _heap[i]); i = m;
        }
    }

    public bool Next(out int passage, out int list, out int index)
    {
        if (_n == 0) { passage = list = index = -1; return false; }
        list = _heap[0]; index = _pos[list]; passage = _lists[list].P[index];
        if (++_pos[list] < _lists[list].Count) Down(0);
        else { _heap[0] = _heap[--_n]; if (_n > 0) Down(0); }
        return true;
    }
}
