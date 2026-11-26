// Loads the ACTIVE importer generation (app/importer) and exposes ONLY importer-verified evidence:
//   generations/<release>/generation.json   servable ids, served candidate anchors, page counts
//   generations/<release>/records/*.jsonl    verified documents, derived_text, candidates (materialized by the importer)
//   generations/<release>/derived/<sha>.txt  verified derivative text (re-hashed here before use)
//   generations/<release>/research/*.jsonl   signed research aids (A4 provision versions, abbreviation lexicon)
//   vault/sha256/<aa>/<sha>                  originals (re-hashed here before any byte is served)
// Anything that fails a check is left out and counted by reason code; nothing is guessed or repaired.
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Text.RegularExpressions;
using Mimamsa.Core.Delivery;

namespace Mimamsa.Core.Generation;

/// Python str offsets are code points; .NET strings are UTF-16. Identity when the text has no surrogate pairs.
public static class CodePoints
{
    public static bool TryMap(string s, int cpStart, int cpEnd, out int start, out int end)
    {
        start = end = -1;
        if (cpStart < 0 || cpEnd < cpStart) return false;
        if (!s.Any(char.IsSurrogate)) { start = cpStart; end = cpEnd; return cpEnd <= s.Length; }
        int cp = 0, i = 0;
        while (i <= s.Length)
        {
            if (cp == cpStart) start = i;
            if (cp == cpEnd) { end = i; break; }
            if (i == s.Length) break;
            i += char.IsHighSurrogate(s[i]) && i + 1 < s.Length && char.IsLowSurrogate(s[i + 1]) ? 2 : 1;
            cp++;
        }
        return start >= 0 && end >= 0;
    }

    public static int Length(string s) => s.Any(char.IsSurrogate) ? s.EnumerateRunes().Count() : s.Length;
}

public sealed class GenerationLoadException(string code) : Exception(code) { public string Code { get; } = code; }

public sealed partial class GenerationStore
{
    public required string SiteRoot { get; init; }
    public required string GenerationId { get; init; }
    public required ReleaseInfo Release { get; init; }
    public required IReadOnlyDictionary<string, DocumentRecord> Documents { get; init; }
    public required IReadOnlyDictionary<string, HeldCopy> HeldCopies { get; init; }
    public required IReadOnlyList<ProvisionVersion> ProvisionVersions { get; init; }
    public required IReadOnlyList<Abbreviation> Abbreviations { get; init; }
    public required IReadOnlyDictionary<string, int> LoadIssues { get; init; }
    public required JsonArray Quarantine { get; init; }

    Statutes.StatuteRelations? _relations;
    /// Statutory relationships derived from verified held text (C14 F03), built once on first use.
    public Statutes.StatuteRelations Relations => LazyInitializer.EnsureInitialized(ref _relations, () => Statutes.StatuteRelations.Build(this));

    [GeneratedRegex(@"^\[\[page (\d+)\]\]\n", RegexOptions.Multiline)] private static partial Regex Marker();

    static string Sha(byte[] b) => Convert.ToHexString(SHA256.HashData(b)).ToLowerInvariant();
    static string Sha(string s) => Sha(Encoding.UTF8.GetBytes(s));

    /// Importer page format: page N is the text after its marker line up to the next marker line; the single newline
    /// before the next marker (or the end of the file) is removed. Returns null when malformed (same rule as importer).
    public static Dictionary<int, string>? SplitPages(string text)
    {
        var marks = Marker().Matches(text);
        if (marks.Count == 0 || marks[0].Index != 0) return null;
        var pages = new Dictionary<int, string>();
        for (int i = 0; i < marks.Count; i++)
        {
            int start = marks[i].Index + marks[i].Length;
            int end = i + 1 < marks.Count ? marks[i + 1].Index : text.Length;
            var body = text[start..end];
            if (body.EndsWith('\n')) body = body[..^1];
            int n = int.Parse(marks[i].Groups[1].Value);
            if (!pages.TryAdd(n, body)) return null;
        }
        return pages;
    }

    static IEnumerable<JsonObject> Jsonl(string path)
    {
        if (!File.Exists(path)) yield break;
        foreach (var line in File.ReadLines(path, Encoding.UTF8))
            if (!string.IsNullOrWhiteSpace(line)) yield return JsonNode.Parse(line)!.AsObject();
    }

    static string? S(JsonNode? n) => n is JsonValue v && v.TryGetValue<string>(out var s) ? s : null;
    static List<string> L(JsonNode? n) => n is JsonArray a ? a.Select(x => S(x)).Where(x => x is not null).Select(x => x!).ToList() : new();

    public static GenerationStore Load(string siteRoot, Vault? vault = null)
    {
        siteRoot = Path.GetFullPath(siteRoot);
        var activePath = Path.Combine(siteRoot, "ACTIVE");
        if (!File.Exists(activePath)) throw new GenerationLoadException("NO_ACTIVE_GENERATION");
        var gid = File.ReadAllText(activePath).Trim();
        if (gid.Length == 0 || gid.Contains('/') || gid.Contains('\\') || gid.Contains("..")) throw new GenerationLoadException("ACTIVE_INVALID");
        var gdir = Path.Combine(siteRoot, "generations", gid);
        var gen = JsonNode.Parse(File.ReadAllText(Path.Combine(gdir, "generation.json")))!.AsObject();
        if (gen["materialized"]?["format"]?.GetValue<int>() != 1) throw new GenerationLoadException("GENERATION_NOT_MATERIALIZED");
        var issues = new Dictionary<string, int>();
        void Issue(string code) => issues[code] = issues.GetValueOrDefault(code) + 1;

        var servable = gen["servable"]!.AsObject();
        var okDocs = L(servable["documents"]).ToHashSet();
        var okDer = L(servable["derived_text"]).ToHashSet();
        var okCand = L(servable["candidates"]).ToHashSet();
        var itemDoc = gen["item_document"]!.AsObject();
        var evidence = gen["candidate_evidence"]?.AsObject() ?? new JsonObject();

        var rel = JsonNode.Parse(File.ReadAllText(Path.Combine(gdir, "release", "RELEASE.json")))!.AsObject();
        var release = new ReleaseInfo(S(rel["release_id"]) ?? gid, rel["release_sequence"]?.GetValue<long>() ?? 0, S(rel["created_at"]) ?? "",
            S(rel["pinned"]?["hf_repo"]), S(rel["pinned"]?["hf_revision"]), S(rel["pinned"]?["tools_commit"]),
            S(rel["candidate_banner"]?["text"]) ?? "Research and candidate data. Not legally verified.",
            rel["auth_ledger_version"]?.GetValue<int>() ?? 0, S(gen["exclusion_channel"]) ?? "signed", S(rel["restricted_material"]?["config_sha256"]));

        vault ??= new Vault(siteRoot);
        var docs = new Dictionary<string, DocumentRecord>(StringComparer.Ordinal);
        foreach (var d in Jsonl(Path.Combine(gdir, "records", "documents.jsonl")))
        {
            var id = S(d["doc_id"])!;
            if (!okDocs.Contains(id)) { Issue("DOCUMENT_NOT_SERVABLE"); continue; }
            var sc = d["source_copy"]!.AsObject();
            var sha = S(sc["sha256"])!;
            if (S(itemDoc["documents"]?[id]?[1]) != sha) { Issue("DOCUMENT_COPY_MISMATCH"); continue; }
            var j = d["judicial"] as JsonObject;
            var rec = new DocumentRecord
            {
                DocId = id, DocType = S(d["doc_type"]) ?? "other", Title = S(d["title"]), Number = S(d["number"]),
                IssuingAuthority = S(d["issuing_authority"]), IssueDate = S(d["issue_date"]), EffectiveDate = S(d["effective_date"]),
                Language = S(d["language"]), CorpusStatus = S(d["corpus_status"]) ?? "unknown", CorpusStatusNote = S(d["corpus_status_note"]),
                CorpusStatusAsOf = S(d["corpus_status_as_of"]), TextMethod = S(d["text_method"]),
                OcrConfidence = d["ocr_confidence"] is JsonValue ov && ov.TryGetValue<double>(out var oc) ? oc : null,
                CopySha = sha, CopyBytes = sc["bytes"]!.GetValue<long>(),
                PageCount = gen["page_counts"]?[sha]?.GetValue<int>() ?? sc["page_count"]?.GetValue<int>() ?? 0,
                Completeness = S(sc["completeness"]),
                Publication = S(d["status_axes"]?["publication"]?["value"]) ?? "UNKNOWN",
                AccessMarking = S(d["restriction"]?["access_marking"]),
                Judicial = j is null ? null : new Judicial(S(j["court"]), S(j["bench"]), L(j["case_numbers"]), S(j["neutral_citation"]),
                    L(j["reported_citations"]), S(j["parties"]?["petitioner"]), S(j["parties"]?["respondent"]), L(j["judges"])),
                Provenance = d["provenance"]!.DeepClone().AsObject(), StatusAxes = d["status_axes"]!.DeepClone().AsObject(),
                Restriction = d["restriction"]!.DeepClone().AsObject(), FieldOrigin = (d["field_origin"] as JsonObject)?.DeepClone().AsObject() ?? new(),
            };
            rec.OriginalVerified = vault.Verify(sha, out var len) && len == rec.CopyBytes;
            if (!rec.OriginalVerified) Issue("ORIGINAL_HASH_MISMATCH_OR_MISSING");
            docs[id] = rec;
        }

        foreach (var t in Jsonl(Path.Combine(gdir, "records", "derived_text.jsonl")))
        {
            var docId = S(t["doc_id"])!;
            var pname = S(t["pipeline"]?["name"])!; var pver = S(t["pipeline"]?["version"])!;
            var did = $"{docId}@{pname}/{pver}";
            if (!okDer.Contains(did) || !docs.TryGetValue(docId, out var doc) || S(t["source_copy_sha256"]) != doc.CopySha)
            { Issue("DERIVATIVE_NOT_SERVABLE"); continue; }
            var tsha = S(t["text_sha256"])!;
            if (ServingState.CanonicalSha(tsha) is null) { Issue("DERIVATIVE_BAD_HASH"); continue; }
            var path = Path.Combine(gdir, "derived", tsha + ".txt");
            if (!File.Exists(path)) { Issue("DERIVATIVE_TEXT_MISSING"); continue; }
            var bytes = File.ReadAllBytes(path);
            if (Sha(bytes) != tsha) { Issue("DERIVATIVE_TEXT_HASH_MISMATCH"); continue; }
            var pages = SplitPages(Encoding.UTF8.GetString(bytes));
            if (pages is null) { Issue("DERIVATIVE_MARKERS_MALFORMED"); continue; }
            if (doc.DerivativeId is not null) { Issue("DERIVATIVE_DUPLICATE_IGNORED"); continue; }
            doc.DerivativeId = did; doc.DerivativeTextSha = tsha; doc.PipelineName = pname; doc.PipelineVersion = pver;
            doc.QuotingPermitted = t["quoting_permitted"]?.GetValue<bool>() ?? false;
            foreach (var pg in t["pages"]!.AsArray())
            {
                int n = pg!["page"]!.GetValue<int>();
                if (!pages.TryGetValue(n, out var body)) continue;
                doc.Pages[n] = new PageText(n, body, S(pg["method"]) ?? "pdf_text", pg["low_confidence"]?.GetValue<bool>() ?? false,
                    pg["ocr_mean_confidence"] is JsonValue cv && cv.TryGetValue<double>(out var c) ? c : null);
            }
            foreach (var ps in t["passages"]!.AsArray())
            {
                int n = ps!["page"]!.GetValue<int>(), cps = ps["char_start"]!.GetValue<int>(), cpe = ps["char_end"]!.GetValue<int>();
                // Contract offsets count Unicode code points (producer and importer are Python); map to UTF-16 indexes.
                if (!doc.Pages.TryGetValue(n, out var body) || !CodePoints.TryMap(body.Text, cps, cpe, out var cs, out var ce))
                { Issue("PASSAGE_OUT_OF_RANGE"); continue; }
                var text = body.Text[cs..ce];
                if (Sha(text) != S(ps["text_sha256"])) { Issue("PASSAGE_HASH_MISMATCH"); continue; }
                doc.Passages.Add(new Passage(docId, S(ps["passage_id"])!, n, cs, ce, S(ps["paragraph_label"]), text));
            }
        }

        foreach (var doc in docs.Values) TextQuality.Apply(doc);

        foreach (var c in Jsonl(Path.Combine(gdir, "records", "candidates.jsonl")))
        {
            var cid = S(c["candidate_id"])!;
            if (!okCand.Contains(cid) || !docs.TryGetValue(S(c["source_doc_id"])!, out var doc)) { Issue("CANDIDATE_NOT_SERVABLE"); continue; }
            var served = evidence[cid]?["anchors"] as JsonArray;
            if (served is null) { Issue("CANDIDATE_NO_SERVED_EVIDENCE"); continue; }
            var raw = c["anchors"]!.AsArray();
            var anchors = new List<ServedAnchor>();
            for (int i = 0; i < served.Count; i++)
            {
                var a = served[i]!;
                bool pageOnly = a["page_only"]?.GetValue<bool>() ?? true;
                // Quotes are producer text: shown only as "quoted by extractor", never as source text.
                var quote = i < raw.Count ? S(raw[i]?["quote"]) : null;
                anchors.Add(new ServedAnchor(S(a["source_copy_sha256"])!, a["page"]!.GetValue<int>(), pageOnly,
                    pageOnly ? null : S(a["passage_id"]), pageOnly ? null : a["char_start"]?.GetValue<int>(),
                    pageOnly ? null : a["char_end"]?.GetValue<int>(), quote));
            }
            doc.Candidates.Add(new Candidate(cid, S(c["candidate_type"])!, doc.DocId, S(c["status"])!, S(c["capability_restriction"])!,
                L(c["deferred_findings"]), c["evaluation_ref"] as JsonObject is { } er ? er.DeepClone().AsObject() : null,
                c["payload"]!.DeepClone().AsObject(), c["extractor"]!.DeepClone().AsObject(), anchors));
        }

        var held = LoadHeldCopies(siteRoot, gen, vault);
        var bySha = docs.Values.GroupBy(d => d.CopySha).ToDictionary(g => g.Key, g => g.OrderBy(d => d.DocId, StringComparer.Ordinal).First());
        var versions = new List<ProvisionVersion>();
        var abbrevs = new List<Abbreviation>();
        foreach (var rp in L(gen["materialized"]?["research"]))
        {
            var path = Path.Combine(gdir, rp.Replace('/', Path.DirectorySeparatorChar));
            if (!File.Exists(path)) { Issue("RESEARCH_FILE_MISSING"); continue; }
            if (rp.EndsWith("a4_provision_versions.jsonl", StringComparison.Ordinal))
                foreach (var v in Jsonl(path)) versions.Add(ToVersion(v, bySha));
            else if (rp.EndsWith("abbreviations_v1.0.jsonl", StringComparison.Ordinal))
                foreach (var a in Jsonl(path))
                    abbrevs.Add(new Abbreviation(S(a["code"])!, L(a["preferred"]), S(a["origin"]) ?? "lexicon"));
        }
        return new GenerationStore
        {
            SiteRoot = siteRoot, GenerationId = gid, Release = release, Documents = docs, HeldCopies = held,
            ProvisionVersions = versions, Abbreviations = abbrevs, LoadIssues = issues,
            Quarantine = gen["quarantine"] as JsonArray ?? new JsonArray(),
        };
    }

    static ProvisionVersion ToVersion(JsonObject v, Dictionary<string, DocumentRecord> bySha)
    {
        var ev = new List<ResolvedEvidence>();
        foreach (var e in v["text_evidence"] as JsonArray ?? new JsonArray())
        {
            var sha = ServingState.CanonicalSha(S(e?["sha256"]));
            int? page = int.TryParse(S(e?["pdf_page"]), out var p) ? p : null;
            string res; string? doc = null;
            if (sha is null) res = "NO_COPY_NAMED";
            else if (!bySha.TryGetValue(sha, out var d)) res = "COPY_NOT_HELD_IN_THIS_INSTALLATION";
            else if (page is null) { res = "PAGE_NOT_STATED"; doc = d.DocId; }
            else if (page < 1 || page > d.PageCount) { res = "PAGE_NOT_IN_COPY"; doc = d.DocId; }
            else { res = "RESOLVED_TO_VERIFIED_COPY"; doc = d.DocId; }
            ev.Add(new ResolvedEvidence(S(e?["role"]) ?? "unknown", sha, doc, res == "RESOLVED_TO_VERIFIED_COPY" ? page : null, S(e?["edition"]), res));
        }
        return new ProvisionVersion(S(v["version_id"]) ?? "", S(v["family"]) ?? "", S(v["provision"]) ?? "", S(v["version_kind"]) ?? "",
            S(v["change_summary"]), S(v["effective_from"]?["status"]), S(v["effective_from"]?["date"]), S(v["effective_from"]?["reported_date"]),
            S(v["effective_to"]?["status"]), S(v["currency"]?["status"]), S(v["determination_state"]) ?? "AUTOMATED_CANDIDATE_NOT_VERIFIED",
            ev, v);
    }

    /// Copies held by activated generations (release_sequence at or below the ACTIVE one), as importer.held_copies(),
    /// keyed by (sha, doc_id), with the publication value each copy had in the generation that held it.
    static Dictionary<string, HeldCopy> LoadHeldCopies(string siteRoot, JsonObject active, Vault vault)
    {
        var held = new Dictionary<string, HeldCopy>();
        long activeSeq = active["release_sequence"]?.GetValue<long>() ?? 0;
        var gens = new List<(long seq, string id, JsonObject g)>();
        foreach (var dir in Directory.EnumerateDirectories(Path.Combine(siteRoot, "generations")))
        {
            var name = Path.GetFileName(dir);
            if (name.StartsWith('.')) continue;
            var f = Path.Combine(dir, "generation.json");
            if (!File.Exists(f)) continue;
            var g = JsonNode.Parse(File.ReadAllText(f))!.AsObject();
            long seq = g["release_sequence"]?.GetValue<long>() ?? 0;
            if (seq <= activeSeq) gens.Add((seq, name, g));
        }
        foreach (var (_, id, g) in gens.OrderBy(x => x.seq))
        {
            var published = new HashSet<string>();
            foreach (var d in Jsonl(Path.Combine(siteRoot, "generations", id, "records", "documents.jsonl")))
                if (S(d["status_axes"]?["publication"]?["value"]) == "PUBLISHED" && S(d["restriction"]?["eligibility"]) == "ELIGIBLE_ALL_USERS")
                    published.Add(S(d["source_copy"]?["sha256"]) + "|" + S(d["doc_id"]));
            foreach (var (_, v) in g["item_document"]?["documents"]?.AsObject() ?? new JsonObject())
            {
                var docId = S(v![0])!; var sha = S(v[1])!;
                var key = sha + "|" + docId;
                if (held.ContainsKey(key)) continue;
                int pc = g["page_counts"]?[sha]?.GetValue<int>() ?? 0;
                long len = File.Exists(vault.PathFor(sha)) ? new FileInfo(vault.PathFor(sha)).Length : 0;
                held[key] = new HeldCopy(sha, docId, pc, S(g["release_id"]) ?? id, id, len, published.Contains(key));
            }
        }
        return held;
    }
}
