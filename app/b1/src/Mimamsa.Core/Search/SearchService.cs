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
                                  IReadOnlyList<IReadOnlyList<string>> HighlightPhrases, IReadOnlyList<string> Notes);

public sealed class SearchService
{
    public const int MaxHits = 200;
    readonly SearchIndex _ix;
    readonly Func<string, bool> _docHidden;   // withdrawn (serving fence) -> hidden from every surface

    public SearchService(SearchIndex ix, Func<string, bool> docHidden) { _ix = ix; _docHidden = docHidden; }
    public SearchIndex Index => _ix;

    sealed class Ctx
    {
        public bool Exact;
        public readonly HashSet<string> Highlight = new(StringComparer.Ordinal);
        public readonly List<IReadOnlyList<string>> Phrases = new();
        public readonly Dictionary<int, Dictionary<string, int>> Matched = new();   // passage -> display term -> count
        public readonly List<Chip> Chips = new();
    }

    public SearchResult Search(string raw, SearchFilters filters, bool plainAfterConfirmation = false)
    {
        ParsedQuery q;
        try { q = plainAfterConfirmation ? QueryParser.PlainWords(raw) : QueryParser.Parse(raw); }
        catch (ParseException e)
        {
            return new SearchResult("parser_error", "parser_error", Array.Empty<Chip>(), Array.Empty<Hit>(), 0, 0,
                new Dictionary<string, IReadOnlyList<FacetValue>>(), e.Message, e.Position, Array.Empty<string>(), Array.Empty<IReadOnlyList<string>>(), Array.Empty<string>());
        }
        var ctx = new Ctx { Exact = q.Exact };
        var notes = new List<string> { "Lexical search (BM25 word and phrase matching). Semantic search is not part of B1." };
        var ordered = new List<Hit>();
        var seen = new HashSet<int>();
        string mode = "lexical";
        if (q.Exact) ctx.Chips.Add(new Chip("mode", "Exact: lexical only, no abbreviation expansion", null));

        if (q.Plain)
        {
            var (pinned, mentions, rest) = IdentifierTiers(q.Raw, ctx);
            foreach (var h in pinned) if (seen.Add(h.PassageIndex)) ordered.Add(h);
            if (ordered.Count > 0) mode = "identifier";
            foreach (var h in mentions) if (seen.Add(h.PassageIndex)) ordered.Add(h);
            if (rest.Count > 0)
            {
                // Short-title match: plain words that are exactly an instrument's title (ignoring years/stopwords) put
                // that instrument's first passage first, labelled as a title match.
                var words = rest.SelectMany(w => Text.Tokenize(w)).Select(t => t.Term).Where(t => !Text.Stopwords.Contains(t) && !t.All(char.IsDigit)).ToHashSet();
                if (words.Count >= 2)
                    for (int d = 0; d < _ix.Docs.Count; d++)
                        if (_ix.Docs[d].IsStatute && NormTitle(_ix.Docs[d].Title).Split(' ').ToHashSet().SetEquals(words) && seen.Add(_ix.DocPassages[d][0]))
                            ordered.Add(new Hit(_ix.DocPassages[d][0], "title", 5e8, new[] { $"title match: {_ix.Docs[d].Title}" }));
                var scores = PlainScores(rest, ctx);
                foreach (var (p, s) in scores.OrderByDescending(kv => kv.Value).ThenBy(kv => kv.Key))
                    if (seen.Add(p)) ordered.Add(new Hit(p, "lexical", s, Reasons(p, ctx)));
            }
        }
        else
        {
            var scores = Eval(q.Root!, ctx);
            foreach (var (p, s) in scores.OrderByDescending(kv => kv.Value).ThenBy(kv => kv.Key))
                if (seen.Add(p)) ordered.Add(new Hit(p, "lexical", s, Reasons(p, ctx)));
            DescribeChips(q.Root!, ctx);
        }

        ordered = ordered.Where(h => !_docHidden(_ix.Passages[h.PassageIndex].DocId)).ToList();
        var facets = Facets(ordered, filters);
        var filtered = ordered.Where(h => Pass(_ix.Docs[_ix.DocOf(h.PassageIndex)], filters, null)).ToList();
        int docs = filtered.Select(h => _ix.DocOf(h.PassageIndex)).Distinct().Count();
        var state = filtered.Count > 0 ? "results" : "empty";
        return new SearchResult(state, mode, ctx.Chips, filtered.Take(MaxHits).ToList(), filtered.Count, docs, facets, null, null,
            ctx.Highlight.ToList(), ctx.Phrases, notes);
    }

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
            ctx.Chips.Add(new Chip("identifier", $"{label} · {id.Raw.Trim()}", docs.Count + cover.Count > 0 ? $"{docs.Count + cover.Count} matching document(s)" : "no document carries this identifier"));
            ctx.Phrases.Add(idToks);
            var mentionHits = PhraseOccurrences(idToks);
            // A document-level identifier pins ONE representative passage per matching document: a passage that
            // contains the identifier (labelled as such), else the document's first passage (labelled as a document
            // match, not an identifier hit). Other passages are not inflated into identifier hits (review F05).
            foreach (var (set, why) in new[] { (docs, $"{label} {id.Raw.Trim()} in document metadata"), (cover, $"{label} {id.Raw.Trim()} printed at the top of p.1 (extracted, not verified)") })
                foreach (var d in set)
                {
                    var ps = _ix.DocPassages[d];
                    var withId = ps.Where(mentionHits.ContainsKey).ToList();
                    if (withId.Count > 0)
                        foreach (var p in withId.Take(3))
                            pinned.Add(new Hit(p, "identifier", 1e9, new[] { why, "the identifier appears in this passage" }));
                    else
                        pinned.Add(new Hit(ps[0], "document", 1e9, new[] { why + "; this passage is the document's first passage and does not itself contain the identifier" }));
                }
            foreach (var (p, n) in mentionHits.OrderByDescending(kv => kv.Value).ThenBy(kv => kv.Key))
                if (!docs.Contains(_ix.DocOf(p)) && !cover.Contains(_ix.DocOf(p)))
                    mentions.Add(new Hit(p, "mention", 1e6 + n, new[] { $"mentions {id.Raw.Trim()} ({n}); a mention is not the identified document" }));
        }

        foreach (var id in ids.Where(i => i.Kind == IdKind.Section))
        {
            var actWords = restWords.Select(w => Text.Tokenize(w)).SelectMany(t => t).Select(t => t.Term)
                                    .Where(t => !Text.Stopwords.Contains(t)).ToList();
            // Instrument scoping (review F05): among Acts/Rules whose title contains every query word, keep only the
            // closest titles (fewest extra title words, ignoring years and stopwords). Distinct closest titles are
            // ambiguous: nothing is pinned and a disambiguation chip lists them.
            // Instrument scoping (review F05, F14), general rules:
            //  - no instrument words: provision in any Act/Rules/Regulations;
            //  - only generic words ("Rules", "Act"): ambiguous; nothing pinned; candidate instruments offered;
            //  - instrument words that match no held title: say so; nothing pinned; the words run as lexical text;
            //  - otherwise keep the closest titles (fewest extra words); distinct closest titles are ambiguous.
            var scoped = new List<int>();
            string? ambiguous = null, notHeld = null;
            var specific = actWords.Where(w => !GenericInstrumentWords.Contains(w) && !w.All(char.IsDigit)).ToList();
            if (actWords.Count > 0 && specific.Count == 0)
            {
                var kinds = actWords.Where(GenericInstrumentWords.Contains).ToHashSet();
                // candidates ordered by closeness (fewest other title words), then title; count always stated
                var all = Enumerable.Range(0, _ix.Docs.Count)
                    .Where(d => _ix.Docs[d].IsStatute && kinds.All(k => _ix.TitleTerms[d].Contains(k) || _ix.TitleTerms[d].Contains(k + "s") || _ix.TitleTerms[d].Contains(k.TrimEnd('s'))))
                    .OrderBy(d => _ix.TitleTerms[d].Count(t => !kinds.Contains(t) && !Text.Stopwords.Contains(t) && !t.All(char.IsDigit)))
                    .ThenBy(d => _ix.Docs[d].Title, StringComparer.OrdinalIgnoreCase)
                    .Select(d => _ix.Docs[d].Title).Distinct().ToList();
                ambiguous = all.Count == 0 ? "" : $"{all.Count} candidate instrument(s): " + string.Join("; ", all.Take(8)) + (all.Count > 8 ? $"; +{all.Count - 8} more" : "");
                if (ambiguous.Length == 0) ambiguous = "no instrument of that kind is held";
            }
            else if (actWords.Count > 0)
            {
                var cands = new List<(int d, int extra)>();
                for (int d = 0; d < _ix.Docs.Count; d++)
                    if (_ix.Docs[d].IsStatute && actWords.All(w => _ix.TitleTerms[d].Contains(w)))
                        cands.Add((d, _ix.TitleTerms[d].Count(t => !actWords.Contains(t) && !Text.Stopwords.Contains(t) && !t.All(char.IsDigit))));
                if (cands.Count == 0) notHeld = string.Join(" ", restWords);
                else
                {
                    int best = cands.Min(c => c.extra);
                    var top = cands.Where(c => c.extra == best).Select(c => c.d).ToList();
                    var titles = top.Select(d => NormTitle(_ix.Docs[d].Title)).Distinct().ToList();
                    if (titles.Count == 1) scoped = top;
                    else ambiguous = string.Join("; ", top.Select(d => _ix.Docs[d].Title).Distinct().Take(6));
                }
            }
            string scopeText;
            if (notHeld is not null)
            {
                ctx.Chips.Add(new Chip("not_held", $"No instrument titled \u201c{notHeld}\u201d in this library",
                    $"{id.ProvisionWord} {id.Base}{id.Sub} was not looked up in any other instrument. The words are searched as plain text. Absence here is not evidence that the instrument or provision does not exist."));
                ctx.Phrases.Add(Text.Tokenize(id.Raw).Select(t => t.Term).ToList());
                continue;
            }
            if (ambiguous is not null)
            {
                ctx.Chips.Add(new Chip("ambiguous", $"{id.ProvisionWord} {id.Base}{id.Sub}: which instrument?", "Several instruments could be meant: " + ambiguous + ". Add the full title or year."));
                restWords.Clear();
                continue;
            }
            if (scoped.Count > 0) { scopeText = _ix.Docs[scoped[0]].Title ?? string.Join(" ", restWords); restWords.Clear(); }
            else
            {
                scopeText = "any Act, Rules or Regulations in the library";
                for (int d = 0; d < _ix.Docs.Count; d++) if (_ix.Docs[d].IsStatute) scoped.Add(d);
            }
            var label = $"{id.ProvisionWord} {id.Base}{id.Sub}";
            ctx.Chips.Add(new Chip("identifier", $"{label} · {scopeText}", null));
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
                foreach (var (p, _) in PhraseOccurrences(actPhrase))
                    if (!scoped.Contains(_ix.DocOf(p)) && Identifiers.PassageHasProvision(_ix.Passages[p].Text, id.Base!, id.Sub, false))
                        mentions.Add(new Hit(p, "mention", 1e6, new[] { $"refers to {label} of {string.Join(" ", actWords)}" }));
            }
            ctx.Phrases.Add(Text.Tokenize(id.Raw).Select(t => t.Term).ToList());
        }
        return (pinned, mentions, restWords);
    }

    static readonly HashSet<string> GenericInstrumentWords = new(StringComparer.Ordinal)
    { "act", "acts", "rule", "rules", "regulation", "regulations", "order", "orders", "notification", "notifications", "code", "manual" };

    static string NormTitle(string? t) => string.Join(" ", Text.Tokenize(t ?? "").Select(x => x.Term).Where(x => !x.All(char.IsDigit) && !Text.Stopwords.Contains(x)));

    Dictionary<int, int> PhraseOccurrences(IReadOnlyList<string> terms)
    {
        var res = new Dictionary<int, int>();
        if (terms.Count == 0 || terms.Any(t => !_ix.Postings.ContainsKey(t))) return res;
        var first = _ix.Postings[terms[0]];
        var others = terms.Skip(1).Select(t => _ix.Postings[t].ToDictionary(x => x.P, x => x.Pos.ToHashSet())).ToList();
        foreach (var post in first)
        {
            int n = 0;
            foreach (var pos in post.Pos)
            {
                bool ok = true;
                for (int k = 0; k < others.Count && ok; k++)
                    ok = others[k].TryGetValue(post.P, out var set) && set.Contains(pos + k + 1);
                if (ok) n++;
            }
            if (n > 0) res[post.P] = n;
        }
        return res;
    }

    // ------------------------------------------------------------------ plain words (ranked any-word match)
    Dictionary<int, double> PlainScores(List<string> words, Ctx ctx)
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
        if (clauses.Count == 0) return new();
        var total = clauses.Count(c => c.weight >= 1.0);
        var acc = new Dictionary<int, (double s, int hits)>();
        foreach (var (display, node, weight) in clauses)
            foreach (var (p, s) in Eval(node, ctx))
            {
                acc.TryGetValue(p, out var cur);
                acc[p] = (cur.s + s * weight, cur.hits + (weight >= 1.0 ? 1 : 0));
            }
        // coordination: passages matching more of the user's words rank higher (Lucene classic coord)
        return acc.ToDictionary(kv => kv.Key, kv => kv.Value.s * (0.5 + 0.5 * Math.Min(1.0, (double)Math.Max(kv.Value.hits, 1) / Math.Max(total, 1))));
    }

    // ------------------------------------------------------------------ Boolean evaluation
    IEnumerable<string> Variants(string term, bool prefix, Ctx ctx)
    {
        if (prefix) return _ix.Postings.Keys.Where(k => k.StartsWith(term, StringComparison.Ordinal)).Take(256);
        if (ctx.Exact) return new[] { term };
        return _ix.StemGroups.TryGetValue(Text.Stem(term), out var g) ? g.Append(term).Distinct() : new[] { term };
    }

    void Note(Ctx ctx, int p, string display, int n)
    {
        if (!ctx.Matched.TryGetValue(p, out var m)) ctx.Matched[p] = m = new();
        m[display] = m.GetValueOrDefault(display) + n;
    }

    Dictionary<int, double> Eval(QNode node, Ctx ctx)
    {
        switch (node)
        {
            case QTerm t:
            {
                var res = new Dictionary<int, double>();
                var tf = new Dictionary<int, int>();
                foreach (var v in Variants(t.Term, t.Prefix, ctx))
                {
                    if (!_ix.Postings.TryGetValue(v, out var post)) continue;
                    ctx.Highlight.Add(v);
                    foreach (var x in post) tf[x.P] = tf.GetValueOrDefault(x.P) + x.Pos.Length;
                }
                double idf = _ix.Idf(tf.Count);
                foreach (var (p, n) in tf) { res[p] = idf * _ix.TfNorm(n, p); Note(ctx, p, t.Term + (t.Prefix ? "*" : ""), n); }
                return res;
            }
            case QPhrase ph:
            {
                var occ = PhraseOccurrences(ph.Terms);
                ctx.Phrases.Add(ph.Terms);
                var res = new Dictionary<int, double>();
                double idf = ph.Terms.Sum(t => _ix.Postings.TryGetValue(t, out var l) ? _ix.Idf(l.Count) : 0);
                // A phrase that is itself a provision identifier ("Rule 8(3)(a)"): the provision's own text in an Act or
                // Rules document ranks before passages that merely mention it (exact-identifier rule, design 03 §2).
                var ids = Identifiers.Recognise(ph.Display);
                var prov = ids.Count == 1 && ids[0].Kind == IdKind.Section && ids[0].Start == 0 && ids[0].End >= ph.Display.TrimEnd().Length ? ids[0] : null;
                foreach (var (p, n) in occ)
                {
                    res[p] = idf * _ix.TfNorm(n, p);
                    Note(ctx, p, "\u201c" + ph.Display + "\u201d", n);
                    if (prov is not null && _ix.Docs[_ix.DocOf(p)].IsStatute)
                    {
                        int st = Identifiers.ProvisionStrength(_ix.Passages[p].Text, prov.Base!, prov.Sub, true);
                        if (st >= 2) { res[p] += 1000 * st; Note(ctx, p, $"{prov.ProvisionWord} {prov.Base}{prov.Sub} provision text", 1); }
                    }
                }
                return res;
            }
            case QAnd a:
            {
                var pos = a.Items.Where(i => i is not QNot).ToList();
                var neg = a.Items.OfType<QNot>().ToList();
                Dictionary<int, double>? acc = null;
                foreach (var i in pos)
                {
                    var r = Eval(i, ctx);
                    acc = acc is null ? r : acc.Where(kv => r.ContainsKey(kv.Key)).ToDictionary(kv => kv.Key, kv => kv.Value + r[kv.Key]);
                }
                acc ??= Enumerable.Range(0, _ix.N).ToDictionary(p => p, _ => 0.0);
                foreach (var n in neg)
                {
                    var r = Eval(n.Item, new Ctx { Exact = ctx.Exact });
                    acc = acc.Where(kv => !r.ContainsKey(kv.Key)).ToDictionary(kv => kv.Key, kv => kv.Value);
                }
                return acc;
            }
            case QOr o:
            {
                var acc = new Dictionary<int, double>();
                foreach (var i in o.Items) foreach (var (p, s) in Eval(i, ctx)) acc[p] = acc.GetValueOrDefault(p) + s;
                return acc;
            }
            case QNot n:
            {
                var r = Eval(n.Item, new Ctx { Exact = ctx.Exact });
                return Enumerable.Range(0, _ix.N).Where(p => !r.ContainsKey(p)).ToDictionary(p => p, _ => 0.0);
            }
            case QNear nr:
            {
                var l = Eval(nr.Left, ctx); var r = Eval(nr.Right, ctx);
                var res = new Dictionary<int, double>();
                foreach (var p in l.Keys.Where(r.ContainsKey))
                {
                    var ls = Spans(nr.Left, p, ctx); var rs = Spans(nr.Right, p, ctx);
                    if (ls.Any(x => rs.Any(y => Math.Max(0, Math.Max(x.s, y.s) - Math.Min(x.e, y.e) - 1) <= nr.Distance)))
                        res[p] = l[p] + r[p];
                }
                return res;
            }
            case QField f: return EvalField(f, ctx);
            default: return new();
        }
    }

    List<(int s, int e)> Spans(QNode node, int p, Ctx ctx)
    {
        var res = new List<(int, int)>();
        switch (node)
        {
            case QTerm t:
                foreach (var v in Variants(t.Term, t.Prefix, ctx))
                    if (_ix.Postings.TryGetValue(v, out var post))
                        foreach (var x in post.Where(x => x.P == p)) res.AddRange(x.Pos.Select(i => (i, i)));
                break;
            case QPhrase ph:
                if (ph.Terms.All(_ix.Postings.ContainsKey))
                {
                    var sets = ph.Terms.Select(t => _ix.Postings[t].FirstOrDefault(x => x.P == p).Pos?.ToHashSet() ?? new()).ToList();
                    foreach (var st in sets[0])
                        if (Enumerable.Range(1, sets.Count - 1).All(k => sets[k].Contains(st + k))) res.Add((st, st + sets.Count - 1));
                }
                break;
            case QOr o: foreach (var i in o.Items) res.AddRange(Spans(i, p, ctx)); break;
            default: throw new ParseException("NEAR works between words or phrases.", 0);
        }
        return res;
    }

    Dictionary<int, double> DocPassages(Func<DocumentRecord, bool> pred, double score = 0)
    {
        var res = new Dictionary<int, double>();
        for (int d = 0; d < _ix.Docs.Count; d++)
            if (pred(_ix.Docs[d])) foreach (var p in _ix.DocPassages[d]) res[p] = score;
        return res;
    }

    static bool Contains(string? hay, IReadOnlyList<string> terms)
    {
        if (hay is null || terms.Count == 0) return false;
        var toks = Text.Tokenize(hay).Select(t => t.Term).ToList();
        for (int i = 0; i + terms.Count <= toks.Count; i++)
            if (Enumerable.Range(0, terms.Count).All(k => toks[i + k] == terms[k])) return true;
        return false;
    }

    Dictionary<int, double> EvalField(QField f, Ctx ctx)
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
                var res = new Dictionary<int, double>();
                if (!_ix.Postings.TryGetValue(baseNo.ToLowerInvariant(), out var post)) return res;
                foreach (var x in post)
                {
                    int st = Identifiers.ProvisionStrength(_ix.Passages[x.P].Text, baseNo, sub, _ix.Docs[_ix.DocOf(x.P)].IsStatute);
                    if (st > 0) { res[x.P] = st >= 2 ? 1000.0 * st : 1.0; Note(ctx, x.P, st >= 2 ? $"provision {baseNo}{sub} (text)" : $"reference to {baseNo}{sub}", 1); }
                }
                ctx.Highlight.Add(baseNo.ToLowerInvariant());
                return res;
            }
            case "act":
            {
                var res = DocPassages(d => d.IsStatute && Contains(d.Title, f.Terms), 0.5);
                ctx.Phrases.Add(f.Terms);
                foreach (var (p, n) in PhraseOccurrences(f.Terms)) { res[p] = res.GetValueOrDefault(p) + 1.0; Note(ctx, p, "“" + f.Value + "”", n); }
                return res;
            }
            default: return new();
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

    List<string> Reasons(int p, Ctx ctx) =>
        ctx.Matched.TryGetValue(p, out var m) && m.Count > 0
            ? new List<string> { "Matched: " + string.Join(", ", m.OrderByDescending(kv => kv.Value).Take(4).Select(kv => $"{(kv.Key.StartsWith('“') ? kv.Key : "'" + kv.Key + "'")} ({kv.Value})")) }
            : new List<string> { "Matched the query filters" };

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

    Dictionary<string, IReadOnlyList<FacetValue>> Facets(List<Hit> hits, SearchFilters f)
    {
        var docs = hits.Select(h => _ix.DocOf(h.PassageIndex)).Distinct().Select(d => _ix.Docs[d]).ToList();
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
}
