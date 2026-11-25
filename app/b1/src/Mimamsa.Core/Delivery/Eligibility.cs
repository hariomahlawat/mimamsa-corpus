// The ONE delivery-eligibility decision of a serving process (review F01). Every surface that discloses a document or
// serves bytes (search, document, text, citation, cite, pdf-meta, range, A4 evidence, A5 targets) asks this class.
//   current copy : verified in the ACTIVE generation, PUBLISHED and eligible for all users, original re-hashed at load,
//                  document not withdrawn (withdrawal is per document: every copy), not restricted;
//   earlier copy : held by an activated generation (ASR-E06) AND published in the generation that held it AND its
//                  document is still visible in the active release AND that copy is not withdrawn or restricted AND the
//                  vault object re-hashes. A document absent from the active release is never served (a copy dropped
//                  from a later release may have been dropped for a restriction).
using System.Collections.Concurrent;
using System.Text.Json.Nodes;
using Mimamsa.Core.Generation;
using Mimamsa.Core.Search;

namespace Mimamsa.Core.Delivery;

/// Restricted-material register in the config/restricted_material.json shape (items[].source_sha256, derived_sha256,
/// doc_id). Case-insensitive; section ids (doc#sNN) inherit the restriction. Load failure is fatal (fail closed).
public sealed class RestrictedRegister
{
    readonly HashSet<string> _shas = new(StringComparer.OrdinalIgnoreCase), _ids = new(StringComparer.OrdinalIgnoreCase);
    public static readonly RestrictedRegister Empty = new();
    public int Count => _ids.Count;

    public static RestrictedRegister Load(string path)
    {
        var r = new RestrictedRegister();
        var j = JsonNode.Parse(File.ReadAllText(path))!;
        foreach (var it in j["items"]!.AsArray())
        {
            r._shas.Add(it!["source_sha256"]!.GetValue<string>());
            foreach (var d in it["derived_sha256"] as JsonArray ?? new JsonArray()) r._shas.Add(d!.GetValue<string>());
            r._ids.Add(it["doc_id"]!.GetValue<string>());
        }
        return r;
    }

    public bool IsRestricted(string? docId, string? sha) =>
        (sha is not null && _shas.Contains(sha)) || (docId is not null && _ids.Contains(docId.Split('#')[0]));
}

public sealed class Eligibility(GenerationStore g, ServingState state, RestrictedRegister register, Vault vault)
{
    readonly ConcurrentDictionary<string, bool> _rehash = new();

    public DocumentRecord? Visible(string docId) =>
        g.Documents.TryGetValue(docId, out var d) && SearchIndex.Indexable(d) && !state.IsDocWithdrawn(docId)
        && !state.IsWithdrawn(docId, d.CopySha) && !register.IsRestricted(docId, d.CopySha) ? d : null;

    public bool HeldEligible(HeldCopy h)
    {
        var cur = Visible(h.DocId);
        if (cur is null) return false;
        if (cur.CopySha == h.Sha) return true;
        return h.Published && !state.IsWithdrawn(h.DocId, h.Sha) && !register.IsRestricted(h.DocId, h.Sha)
               && _rehash.GetOrAdd(h.Sha, s => vault.Verify(s, out _));
    }

    /// Exact copy a request may receive (null sha = current copy), or null for the one generic "not available".
    public (string sha, long length, int pages)? Copy(string docId, string? sha)
    {
        var d = Visible(docId);
        if (d is null) return null;
        if (sha is null || sha == d.CopySha) return (d.CopySha, d.CopyBytes, d.PageCount);
        return g.HeldCopies.TryGetValue(sha + "|" + docId, out var h) && HeldEligible(h) ? (h.Sha, h.Bytes, h.PageCount) : null;
    }

    public string? CurrentVisibleCopy(string docId) => Visible(docId)?.CopySha;
}
