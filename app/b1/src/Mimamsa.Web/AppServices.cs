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
    public required Eligibility Eligible { get; init; }
    /// C15 WP6: per-user private working documents (never corpus, search or graph).
    public Mimamsa.Core.Studio.StudioStore Studio { get; init; } = null!;
    /// C15 WP5: the only way the Commander workspace reads the corpus (switchable to the C15 graph API at integration).
    public Mimamsa.Core.Commander.ICommanderSource Commander { get; init; } = null!;

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

    /// Document visible to Users and Admins alike (PR-15). Delegates to the single eligibility decision (F01).
    public DocumentRecord? VisibleDocument(string docId) => Eligible.Visible(docId);

    /// The exact copy a request may receive (current or an eligible earlier edition), else null (generic notice).
    public (string sha, long length, int pages)? AuthorizedCopy(string docId, string? sha) => Eligible.Copy(docId, sha);
}
