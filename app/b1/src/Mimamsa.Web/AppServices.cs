using Mimamsa.Core.Delivery;
using Mimamsa.Core.Generation;
using Mimamsa.Core.Identity;
using Mimamsa.Core.Search;

namespace Mimamsa.Web;

/// Composition root for one serving process: the ACTIVE generation (verified evidence only), its search index, the
/// durable serving policy mirror and the identity store. The generation is immutable for the process lifetime; a new
/// generation is served after a service restart (B1 has no hot switch).
public sealed class AppServices
{
    public const string SessionCookie = "mimamsa_session";
    public required GenerationStore Generation { get; init; }
    public required SearchService Search { get; init; }
    public required ServingState State { get; init; }
    public required PolicyStore Policy { get; init; }
    public required IdentityStore Identity { get; init; }
    public required CreditLedger Ledger { get; init; }
    public required Vault Vault { get; init; }
    public required bool TestMode { get; init; }
    public required bool SecureCookies { get; init; }
    readonly Dictionary<string, bool> _heldVerified = new();
    readonly object _heldLock = new();

    public Task<Principal?> AuthenticateAsync(HttpContext ctx)
    {
        if (ctx.Items.TryGetValue("principal", out var p)) return Task.FromResult(p as Principal);
        return AuthenticateUncachedAsync(ctx);
    }

    async Task<Principal?> AuthenticateUncachedAsync(HttpContext ctx)
    {
        var token = ctx.Request.Cookies[SessionCookie];
        var p = await Identity.AuthenticateAsync(token);
        ctx.Items["principal"] = p;
        return p;
    }

    /// Document visible to Users and Admins alike (PR-15): verified in the ACTIVE generation, PUBLISHED, original
    /// re-hashed at load, and not withdrawn. Anything else is "not available" (one indistinguishable answer).
    public DocumentRecord? VisibleDocument(string docId) =>
        Generation.Documents.TryGetValue(docId, out var d) && SearchIndex.Indexable(d) && !State.IsWithdrawn(d.DocId, d.CopySha) ? d : null;

    /// The exact copy a request may receive: the current copy of a visible document, or (for exact citation opening,
    /// ASR-E06) a copy held by an earlier activated generation that is not withdrawn and re-hashes to its address.
    public (string sha, long length, int pages)? AuthorizedCopy(string docId, string? sha)
    {
        var d = VisibleDocument(docId);
        if (d is not null && (sha is null || sha == d.CopySha)) return (d.CopySha, d.CopyBytes, d.PageCount);
        if (sha is null || !Generation.HeldCopies.TryGetValue(sha, out var h) || h.DocId != docId || State.IsWithdrawn(docId, sha)) return null;
        lock (_heldLock)
        {
            if (!_heldVerified.TryGetValue(sha, out var ok)) _heldVerified[sha] = ok = Vault.Verify(sha, out _);
            return ok ? (h.Sha, h.Bytes, h.PageCount) : null;
        }
    }
}
