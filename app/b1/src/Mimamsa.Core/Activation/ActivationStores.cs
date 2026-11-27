// C16 B06: the commit domains other than the journal (architecture section 8.2): the database (knowledge views and
// RELEASE_ACTIVATION publication rows keyed by txn), the activation log (hash chain, one record per DECIDED txn, keyed
// by txn) and the generation catalogue (verified staged generations and models, measured sizes, prune). Every effect is
// idempotent so recovery can replay it.
using System.Text;
using System.Text.Json.Nodes;

namespace Mimamsa.Core.Activation;

public sealed record PublicationRow(string TxnId, string Release, string Channel, string Target);

/// Database commit domain. ApplyAsync runs in ONE database transaction: (KNOWLEDGE) repoint the views, and insert the
/// publication row keyed by txn (no-op when present).
public interface IActivationDatabase
{
    void Apply(string txnId, string target, string to);
    /// Recovery reconciliation: views to `knowledge`, a publication row for every committed transaction.
    void Reconcile(string knowledge, IEnumerable<PublicationRow> committed);
    string? Views();
    int PublicationCount();
    /// Backup/restore of the site database rows (scenario backup/restore; real backups are B08).
    byte[] Backup();
    void Restore(byte[] backup);
}

/// File-backed database domain for fixture sites and crash tests: one canonical JSON document replaced atomically.
public sealed class FileActivationDatabase : IActivationDatabase
{
    readonly string _path;
    public Action<string>? InsideHook { get; set; }
    public FileActivationDatabase(string path) { _path = path; }

    JsonObject Load()
    {
        var b = DurableFile.ReadIfExists(_path);
        return b is null ? new JsonObject { ["views"] = null, ["publication"] = new JsonObject(), ["site_rows"] = new JsonObject { ["users"] = 1 } }
                         : CanonicalJson.ParseStrict(b).AsObject();
    }
    void Save(JsonObject o) { Directory.CreateDirectory(Path.GetDirectoryName(_path)!); DurableFile.WriteAtomic(_path, CanonicalJson.Bytes(o)); }

    public void Initialise(string knowledge) { var o = Load(); o["views"] = knowledge; Save(o); }

    public void Apply(string txnId, string target, string to)
    {
        var o = Load();
        if (target == "KNOWLEDGE") o["views"] = to;
        var pub = o["publication"]!.AsObject();
        if (!pub.ContainsKey(txnId)) pub[txnId] = new JsonObject { ["release"] = to, ["channel"] = "RELEASE_ACTIVATION", ["target"] = target };
        InsideHook?.Invoke("DB_APPLIED:inside");
        Save(o);
    }

    public void Reconcile(string knowledge, IEnumerable<PublicationRow> committed)
    {
        var o = Load();
        o["views"] = knowledge;
        var pub = o["publication"]!.AsObject();
        foreach (var r in committed)
            if (!pub.ContainsKey(r.TxnId)) pub[r.TxnId] = new JsonObject { ["release"] = r.Release, ["channel"] = r.Channel, ["target"] = r.Target };
        Save(o);
    }

    public string? Views() => (string?)Load()["views"];
    public int PublicationCount() => Load()["publication"]!.AsObject().Count;
    public byte[] Backup() => CanonicalJson.Bytes(Load());
    public void Restore(byte[] backup) => Save(CanonicalJson.ParseStrict(backup).AsObject());
}

/// The activation log: activation-log\activation-log.jsonl, one canonical record per DECIDED transaction, keyed by
/// txn (idempotent), each naming the sha256 of the previous line. This core record is the reference model's log entry;
/// the full KNOWLEDGE_ACTIVATION_RECORD_SCHEMA record (components, preflight, service level) is B06-integrated work.
public sealed class ActivationLog
{
    readonly string _path;
    public ActivationLog(string path) { _path = path; }

    public List<JsonObject> Read()
    {
        var b = DurableFile.ReadIfExists(_path);
        if (b is null) return [];
        var lines = Encoding.UTF8.GetString(b).Split('\n');
        var outl = new List<JsonObject>();
        string? prev = null;
        for (int i = 0; i < lines.Length - 1; i++)
        {
            var bytes = Encoding.UTF8.GetBytes(lines[i]);
            JsonObject o;
            try { o = CanonicalJson.ParseStrict(bytes).AsObject(); }
            catch (Exception) when (i == lines.Length - 2) { break; }       // torn last record: absent, rewritten by recovery
            if ((string?)o["previous_record_sha256"] != prev || (long)o["seq"]! != outl.Count + 1)
                throw new JournalCorruptException("activation log chain broken");
            prev = CanonicalJson.Sha256Hex(bytes);
            outl.Add(o);
        }
        return outl;
    }

    public void AppendOnce(string txn, string target, string release, string action, long exclusionSeq)
    {
        var recs = Read();
        if (recs.Any(r => (string?)r["txn"] == txn)) return;
        var b = DurableFile.ReadIfExists(_path) ?? [];
        var lines = Encoding.UTF8.GetString(b).Split('\n');
        long validLen = 0;
        for (int i = 0; i < recs.Count; i++) validLen += Encoding.UTF8.GetByteCount(lines[i]) + 1;
        string? prev = recs.Count == 0 ? null : CanonicalJson.Sha256Hex(Encoding.UTF8.GetBytes(lines[recs.Count - 1]));
        var o = new JsonObject
        {
            ["seq"] = recs.Count + 1, ["txn"] = txn, ["target"] = target, ["release"] = release, ["action"] = action,
            ["previous_record_sha256"] = prev, ["exclusion_seq"] = exclusionSeq, ["at"] = ActivationJournal.NowIso(),
        };
        Directory.CreateDirectory(Path.GetDirectoryName(_path)!);
        using var f = new FileStream(_path, FileMode.OpenOrCreate, FileAccess.Write, FileShare.Read, 4096, FileOptions.WriteThrough);
        f.SetLength(validLen);
        f.Seek(0, SeekOrigin.End);
        var line = CanonicalJson.Bytes(o);
        f.Write(line); f.WriteByte((byte)'\n');
        f.Flush(true);
    }
}

public sealed record StagedModel(bool Verified, IReadOnlySet<string> VectorsFor);

/// Verified, staged knowledge generations and models on disk. A generation is installed when
/// generations\<id>\C16_VERIFIED.json exists (written by the importer after staging verification, B01/B04);
/// a model when models\<id>\MODEL_VERIFIED.json exists ({verified, vectors_for}).
public sealed class GenerationCatalog
{
    readonly SiteLayout _s;
    public GenerationCatalog(SiteLayout s) { _s = s; }
    public const string Marker = "C16_VERIFIED.json";

    public List<string> Installed() =>
        Directory.Exists(_s.GenerationsDir)
            ? Directory.GetDirectories(_s.GenerationsDir).Where(d => File.Exists(Path.Combine(d, Marker))).Select(Path.GetFileName).Select(x => x!).Order(StringComparer.Ordinal).ToList()
            : [];

    public long MeasuredBytes(string gen)
    {
        var b = DurableFile.ReadIfExists(Path.Combine(_s.GenerationsDir, gen, Marker));
        return b is null ? 0 : (long?)CanonicalJson.ParseStrict(b)["measured_bytes"] ?? 0;
    }

    /// 2.1 (B06 interface, lexical-only releases): the classification recorded when the generation was staged. A
    /// missing or unreadable record counts as NOT lexical-only, the stricter case (K1: a model with vectors is required).
    public bool IsLexicalOnly(string gen)
    {
        var b = DurableFile.ReadIfExists(Path.Combine(_s.GenerationsDir, gen, Marker));
        try { return b is not null && (bool?)CanonicalJson.ParseStrict(b)["lexical_only"] == true; }
        catch (Exception) { return false; }
    }

    public StagedModel? Model(string? id)
    {
        if (id is null) return null;
        var b = DurableFile.ReadIfExists(Path.Combine(_s.ModelsDir, SiteLayout.CheckId(id), "MODEL_VERIFIED.json"));
        if (b is null) return null;
        var o = CanonicalJson.ParseStrict(b);
        return new StagedModel((bool)o["verified"]!, o["vectors_for"]!.AsArray().Select(x => (string)x!).ToHashSet(StringComparer.Ordinal));
    }

    public void StageGeneration(string gen, long measuredBytes = 0, bool lexicalOnly = false)
    {
        var d = Path.Combine(_s.GenerationsDir, SiteLayout.CheckId(gen));
        Directory.CreateDirectory(d);
        DurableFile.WriteAtomic(Path.Combine(d, Marker), CanonicalJson.Bytes(new JsonObject
        {
            ["generation"] = gen, ["measured_bytes"] = measuredBytes, ["lexical_only"] = lexicalOnly,
        }));
    }

    /// Stage a verified generation, classifying it from its verified KNOWLEDGE_RELEASE.json (and, when given, the
    /// B04 vector-pack outcome) and recording the classification.
    public bool StageGeneration(string gen, byte[] knowledgeReleaseJson, long measuredBytes, string? vectorPackOutcome = null)
    {
        bool lex = LexicalOnly.Classify(knowledgeReleaseJson, vectorPackOutcome);
        StageGeneration(gen, measuredBytes, lex);
        return lex;
    }

    public void StageModel(string id, bool verified, IEnumerable<string> vectorsFor)
    {
        var d = Path.Combine(_s.ModelsDir, SiteLayout.CheckId(id));
        Directory.CreateDirectory(d);
        var arr = new JsonArray();
        foreach (var v in vectorsFor) arr.Add(v);
        DurableFile.WriteAtomic(Path.Combine(d, "MODEL_VERIFIED.json"), CanonicalJson.Bytes(new JsonObject { ["verified"] = verified, ["vectors_for"] = arr }));
    }

    /// Remove a generation: the marker goes first (it stops being "installed"), then the directory.
    public void Remove(string gen)
    {
        var d = Path.Combine(_s.GenerationsDir, SiteLayout.CheckId(gen));
        File.Delete(Path.Combine(d, Marker));
        try { Directory.Delete(d, recursive: true); } catch (IOException) { } catch (UnauthorizedAccessException) { }
    }
}

/// 2.1 lexical-only classification (B06 interface, "Model compatibility for lexical-only knowledge releases").
/// A knowledge release is lexical-only when it declares no VECTOR_PACK component, accounts VECTOR_PACK as
/// OMITTED_DEGRADED and declares DEGRADED_LEXICAL_ONLY; or when its vector pack failed verification and the release
/// was activated ACTIVE_DEGRADED under B04 rule 2 (effective level lexical-only). Anything unreadable or partial is NOT
/// lexical-only (fail towards the stricter rule K1).
public static class LexicalOnly
{
    public const string DegradedVectorOutcome = "ACTIVE_DEGRADED";

    public static bool Classify(byte[] knowledgeReleaseJson, string? vectorPackOutcome = null)
    {
        if (vectorPackOutcome == DegradedVectorOutcome) return true;
        try
        {
            var r = CanonicalJson.ParseStrict(knowledgeReleaseJson).AsObject();
            var comps = r["components"]?.AsArray();
            var cap = r["capability"]?.AsObject();
            if (comps is null || cap is null) return false;
            if (comps.Any(c => (string?)c?["kind"] == "VECTOR_PACK")) return false;
            var vp = cap["accounting"]?.AsArray().Where(a => (string?)a?["kind"] == "VECTOR_PACK").ToList() ?? [];
            if (vp.Count != 1 || (string?)vp[0]!["status"] != "OMITTED_DEGRADED") return false;
            return (string?)cap["declared_service_level"] == "DEGRADED_LEXICAL_ONLY";
        }
        catch (Exception) { return false; }
    }
}

public interface IDiskProbe { long FreeBytes(string path); }
public sealed class DriveDiskProbe : IDiskProbe
{
    public long FreeBytes(string path) => new DriveInfo(Path.GetPathRoot(Path.GetFullPath(path))!).AvailableFreeSpace;
}
public sealed class FixedDiskProbe(long free) : IDiskProbe { public long FreeBytes(string path) => free; }
