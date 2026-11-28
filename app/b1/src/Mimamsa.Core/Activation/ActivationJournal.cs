// C16 B06: the durable activation journal (architecture section 8.2; interface B06 section 1;
// ACTIVATION_JOURNAL_RECORD_SCHEMA.json). journal\journal.jsonl, append-only, one canonical JSON record per line,
// LF-terminated, written through and flushed to the device (FlushFileBuffers / fsync) before the caller performs the
// next effect. Steps: BEGIN, DECIDED (the ONE commit decision), OPEN, ABORTED. Each record chains to the sha256 of the
// previous line's bytes (without the LF) and carries the writer's lock epoch; epochs never decrease along the file.
// Reader rules: an unterminated or unparseable LAST line is a torn tail and is treated as absent (the next writer
// truncates it during recovery); any other damage (unparseable or non-canonical line in the middle, a broken chain, an
// epoch that goes down, an impossible step order) is corruption: JournalCorruptException, and the site fails closed.
using System.Text;
using System.Text.Json.Nodes;
using System.Text.RegularExpressions;

namespace Mimamsa.Core.Activation;

public sealed record JournalEntry(long Seq, string TxnId, string Step, string? Target, string? From, string? To, string? Action,
    long? ExclusionSeq, string WriterId, long LockEpoch, string At, string LineSha256);

public sealed class JournalCorruptException(string message) : Exception(message);

public sealed class JournalState
{
    public IReadOnlyList<JournalEntry> Entries { get; init; } = [];
    /// Byte length of the valid prefix (everything after it is a torn tail).
    public long ValidLength { get; init; }
    public bool TornTail { get; init; }
    public long MaxEpoch => Entries.Count == 0 ? 0 : Entries[^1].LockEpoch;
    public string? LastLineSha256 => Entries.Count == 0 ? null : Entries[^1].LineSha256;

    public IEnumerable<string> Steps(string txn) => Entries.Where(e => e.TxnId == txn).Select(e => e.Step);
    public bool Has(string txn, string step) => Entries.Any(e => e.TxnId == txn && e.Step == step);
    public JournalEntry Begin(string txn) => Entries.First(e => e.TxnId == txn && e.Step == "BEGIN");
    public IEnumerable<string> Transactions => Entries.Where(e => e.Step == "BEGIN").Select(e => e.TxnId);

    /// The transaction with BEGIN but neither OPEN nor ABORTED, if any (at most one by construction).
    public string? InFlight => Transactions.FirstOrDefault(t => !Has(t, "OPEN") && !Has(t, "ABORTED"));

    /// The last OPEN transaction per target (the journal head the pointers and views must follow).
    public JournalEntry? HeadBegin(string target) =>
        Transactions.Where(t => Has(t, "OPEN")).Select(Begin).LastOrDefault(b => b.Target == target);

    public long LastOpenExclusionSeq => Entries.LastOrDefault(e => e.Step == "OPEN")?.ExclusionSeq ?? 0;
}

public static class ActivationJournal
{
    public const string Contract = "mimamsa-corpus-contract/2.1";
    static readonly Regex TxnRx = new("^TX-[0-9]{8}-[0-9a-f]{12}$", RegexOptions.CultureInvariant);
    static readonly HashSet<string> StepNames = ["BEGIN", "DECIDED", "OPEN", "ABORTED"];

    public static JournalState Read(string path)
    {
        var bytes = DurableFile.ReadIfExists(path) ?? [];
        var entries = new List<JournalEntry>();
        long pos = 0, valid = 0;
        bool torn = false;
        string? prevSha = null;
        long maxEpoch = 0;
        while (pos < bytes.Length)
        {
            int nl = Array.IndexOf(bytes, (byte)'\n', (int)pos);
            if (nl < 0) { torn = true; break; }                        // unterminated last line: torn tail
            var line = bytes.AsSpan((int)pos, nl - (int)pos).ToArray();
            bool isLast = nl == bytes.Length - 1;
            JsonObject? o = null;
            try { o = CanonicalJson.ParseStrict(line).AsObject(); }
            catch (Exception) when (isLast) { torn = true; break; }     // unparseable LAST line: torn tail
            catch (Exception) { throw new JournalCorruptException($"journal line {entries.Count + 1} unparseable (not the last line)"); }
            if (!CanonicalJson.Bytes(o).AsSpan().SequenceEqual(line)) throw new JournalCorruptException($"journal line {entries.Count + 1} is not canonical");
            var e = Validate(o, entries, prevSha, ref maxEpoch, CanonicalJson.Sha256Hex(line));
            entries.Add(e);
            prevSha = e.LineSha256;
            pos = nl + 1;
            valid = pos;
        }
        return new JournalState { Entries = entries, ValidLength = valid, TornTail = torn || valid < bytes.Length };
    }

    /// Best-effort step list for diagnostics and observation (never used for decisions).
    public static List<string> DiagnosticSteps(string path)
    {
        var outl = new List<string>();
        var bytes = DurableFile.ReadIfExists(path) ?? [];
        var text = Encoding.UTF8.GetString(bytes);
        var lines = text.Split('\n');
        for (int i = 0; i < lines.Length - 1; i++)       // complete lines only
        {
            try { if ((string?)JsonNode.Parse(lines[i])?["step"] is { } s) outl.Add(s); } catch (Exception) { }
        }
        return outl;
    }

    static JournalEntry Validate(JsonObject o, List<JournalEntry> prior, string? prevSha, ref long maxEpoch, string lineSha)
    {
        string Fail(string why) => throw new JournalCorruptException($"journal record {prior.Count + 1}: {why}");
        if ((string?)o["contract"] != Contract || (string?)o["record_kind"] != "activation_journal_record") Fail("contract or record kind");
        var allowed = new HashSet<string> { "contract", "record_kind", "seq", "previous_record_sha256", "txn_id", "step", "target", "from", "to", "action", "exclusion_seq", "writer", "at" };
        foreach (var kv in o) if (!allowed.Contains(kv.Key)) Fail("unknown field " + kv.Key);
        long seq = (long?)o["seq"] ?? -1;
        if (seq != prior.Count + 1) Fail("sequence gap");
        if ((string?)o["previous_record_sha256"] != prevSha) Fail("hash chain broken");
        var txn = (string?)o["txn_id"] ?? "";
        if (!TxnRx.IsMatch(txn)) Fail("txn_id");
        var step = (string?)o["step"] ?? "";
        if (!StepNames.Contains(step)) Fail("step");
        var w = o["writer"] as JsonObject;
        var wid = (string?)w?["writer_id"];
        long epoch = (long?)w?["lock_epoch"] ?? 0;
        if (wid is null || wid.Length < 3 || epoch < 1) Fail("writer");
        if (epoch < maxEpoch) Fail("lock epoch went down (a stale writer appended after a takeover)");
        maxEpoch = epoch;
        var at = (string?)o["at"] ?? Fail("at");
        string? target = (string?)o["target"], from = (string?)o["from"], to = (string?)o["to"], action = (string?)o["action"];
        long? xs = (long?)o["exclusion_seq"];
        var steps = prior.Where(e => e.TxnId == txn).Select(e => e.Step).ToHashSet();
        switch (step)
        {
            case "BEGIN":
                if (steps.Count > 0) Fail("duplicate BEGIN");
                if (target is not ("KNOWLEDGE" or "MODELS") || to is null || !o.ContainsKey("from") || action is not ("ACTIVATE" or "ROLLBACK" or "RESTORE")) Fail("BEGIN fields");
                var open = prior.Where(e => e.Step == "BEGIN").Select(e => e.TxnId)
                    .FirstOrDefault(t => !prior.Any(e => e.TxnId == t && (e.Step == "OPEN" || e.Step == "ABORTED")));
                if (open is not null) Fail("BEGIN while another transaction is in flight");
                break;
            case "DECIDED":
                if (!steps.SetEquals(["BEGIN"])) Fail("DECIDED out of order");
                break;
            case "OPEN":
                if (!steps.Contains("DECIDED") || steps.Contains("OPEN") || steps.Contains("ABORTED")) Fail("OPEN out of order");
                if (xs is null) Fail("OPEN without exclusion_seq");
                break;
            case "ABORTED":
                if (!steps.SetEquals(["BEGIN"])) Fail("ABORTED out of order");
                break;
        }
        return new JournalEntry(seq, txn, step, target, from, to, action, xs, wid!, epoch, at, lineSha);
    }

    public static string NowIso() => DateTime.UtcNow.ToString("yyyy-MM-dd'T'HH:mm:ss.ffffff'Z'", System.Globalization.CultureInfo.InvariantCulture);

    /// Append one record. The caller holds the writer guard and has verified it is the lock holder. Refuses when the
    /// file has a torn tail (recovery truncates it first) or when the writer's epoch is below the journal's.
    public static JournalEntry Append(string path, JournalState current, string txn, string step, string writerId, long epoch,
        string? target = null, string? from = null, string? to = null, string? action = null, long? exclusionSeq = null)
    {
        if (current.TornTail) throw new InvalidOperationException("journal has a torn tail: recover first");
        if (epoch < current.MaxEpoch) throw new ActivationRefused("NOT_LOCK_HOLDER", "a lower lock epoch cannot append after a takeover");
        var o = new JsonObject
        {
            ["contract"] = Contract, ["record_kind"] = "activation_journal_record", ["seq"] = current.Entries.Count + 1,
            ["previous_record_sha256"] = current.LastLineSha256, ["txn_id"] = txn, ["step"] = step,
            ["writer"] = new JsonObject { ["writer_id"] = writerId, ["lock_epoch"] = epoch }, ["at"] = NowIso(),
        };
        if (step == "BEGIN") { o["target"] = target; o["from"] = from; o["to"] = to; o["action"] = action; }
        if (step == "OPEN") o["exclusion_seq"] = exclusionSeq ?? 0;
        var line = CanonicalJson.Bytes(o);
        long maxEpoch = current.MaxEpoch;
        var entry = Validate(CanonicalJson.ParseStrict(line).AsObject(), current.Entries.ToList(), current.LastLineSha256, ref maxEpoch, CanonicalJson.Sha256Hex(line));
        Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(path))!);
        using (var f = new FileStream(path, FileMode.OpenOrCreate, FileAccess.Write, FileShare.Read, 4096, FileOptions.WriteThrough))
        {
            if (f.Length != current.ValidLength) throw new InvalidOperationException("journal changed underneath the writer");
            f.Seek(0, SeekOrigin.End);
            var buf = new byte[line.Length + 1];
            line.CopyTo(buf, 0);
            buf[^1] = (byte)'\n';
            f.Write(buf);
            f.Flush(true);                                   // FlushFileBuffers / fsync before the next effect
        }
        return entry;
    }

    /// Recovery: drop a torn tail (the reader already treats it as absent).
    public static void TruncateTornTail(string path, JournalState s)
    {
        if (!s.TornTail) return;
        using var f = new FileStream(path, FileMode.Open, FileAccess.Write, FileShare.Read, 4096, FileOptions.WriteThrough);
        f.SetLength(s.ValidLength);
        f.Flush(true);
    }
}
