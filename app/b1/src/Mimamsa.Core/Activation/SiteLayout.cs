// C16 B06: activation-related paths of a site (architecture section 7) and the small durable state files the
// activation tool owns. Pointer files ACTIVE / MODELS_ACTIVE hold the plain generation id, as the existing importer
// and GenerationStore.Load expect.
using System.Text;
using System.Text.Json.Nodes;
using System.Text.RegularExpressions;

namespace Mimamsa.Core.Activation;

public enum SiteState { OPEN, SWITCHING, RECOVERING, FAILED_CLOSED }

public sealed class SiteLayout
{
    public string Root { get; }
    public SiteLayout(string root) { Root = Path.GetFullPath(root); }

    public string JournalDir => Path.Combine(Root, "journal");
    public string JournalPath => Path.Combine(JournalDir, "journal.jsonl");
    public string LockRecordPath => Path.Combine(JournalDir, "LOCK.json");
    public string LockGuardPath => Path.Combine(JournalDir, "LOCK.guard");
    public string LeaseDir => Path.Combine(JournalDir, "lease");
    public string StateDir => Path.Combine(Root, "activation-state");
    public string StatePath => Path.Combine(StateDir, "STATE");
    public string AppliedPath => Path.Combine(StateDir, "APPLIED.json");
    public string InitPath => Path.Combine(StateDir, "SITE_INIT.json");
    public string HighWaterPath => Path.Combine(StateDir, "EXCLUSION_HIGHWATER.json");
    public string ActivePointer => Path.Combine(Root, "ACTIVE");
    public string ModelsPointer => Path.Combine(Root, "MODELS_ACTIVE");
    public string Pointer(string target) => target == "KNOWLEDGE" ? ActivePointer : ModelsPointer;
    public string ActivationLogPath => Path.Combine(Root, "activation-log", "activation-log.jsonl");
    public string ScratchDir => Path.Combine(Root, "scratch");
    public string GenerationsDir => Path.Combine(Root, "generations");
    public string ModelsDir => Path.Combine(Root, "models");
    public string ExclusionsDir => Path.Combine(Root, "exclusions");
    public string TrustListPath => Path.Combine(Root, "trust", "TRUST_LIST.json");
    public string ChannelKeyPath => Path.Combine(Root, "control", "channel.key");
    public string FileDbPath => Path.Combine(Root, "db", "ACTIVATION_DB.json");

    static readonly Regex IdRx = new("^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$", RegexOptions.CultureInvariant);
    public static string CheckId(string id) => IdRx.IsMatch(id) ? id : throw new ActivationRefused("INVALID_ID", "generation or model id is not a safe identifier");

    // ------------------------------------------------------------------ durable state files
    public SiteState ReadMarker()
    {
        var b = DurableFile.ReadIfExists(StatePath);
        if (b is null) return SiteState.RECOVERING;   // never initialised or lost: recover before serving
        return Enum.TryParse<SiteState>(Encoding.ASCII.GetString(b).Trim(), out var s) ? s : SiteState.RECOVERING;
    }
    public void WriteMarker(SiteState s) { Directory.CreateDirectory(StateDir); DurableFile.WriteAtomic(StatePath, Encoding.ASCII.GetBytes(s.ToString())); }

    public string? ReadPointer(string target) => DurableFile.ReadIfExists(Pointer(target)) is { } b ? Encoding.UTF8.GetString(b).Trim() : null;

    public Dictionary<string, long> ReadApplied()
    {
        var b = DurableFile.ReadIfExists(AppliedPath);
        if (b is null) return new(StringComparer.Ordinal);
        return CanonicalJson.ParseStrict(b).AsObject().ToDictionary(kv => kv.Key, kv => (long)kv.Value!, StringComparer.Ordinal);
    }
    public void WriteApplied(Dictionary<string, long> m)
    {
        Directory.CreateDirectory(StateDir);
        var o = new JsonObject();
        foreach (var (k, v) in m) o[k] = v;
        DurableFile.WriteAtomic(AppliedPath, CanonicalJson.Bytes(o));
    }

    public (string knowledge, string models) ReadInit()
    {
        var o = CanonicalJson.ParseStrict(DurableFile.ReadShared(InitPath));
        return ((string)o["initial_knowledge"]!, (string)o["initial_models"]!);
    }

    /// Fresh-site initialisation (installer / tests): the first active generation and model, an OPEN marker and the
    /// applied exclusion sequence for the active generation. Refuses an already initialised site.
    public void Initialise(string knowledge, string models, long exclusionSeq)
    {
        if (File.Exists(InitPath) || File.Exists(JournalPath)) throw new InvalidOperationException("site already initialised");
        Directory.CreateDirectory(StateDir);
        Directory.CreateDirectory(JournalDir);
        DurableFile.WriteAtomic(InitPath, CanonicalJson.Bytes(new JsonObject { ["initial_knowledge"] = CheckId(knowledge), ["initial_models"] = CheckId(models) }));
        DurableFile.WriteAtomic(ActivePointer, Encoding.UTF8.GetBytes(knowledge));
        DurableFile.WriteAtomic(ModelsPointer, Encoding.UTF8.GetBytes(models));
        WriteApplied(new Dictionary<string, long> { [knowledge] = exclusionSeq });
        WriteMarker(SiteState.OPEN);
    }
}
