// Withdrawal scope (C14, owner policy): a withdrawal always covers every copy of the named document (current and
// earlier editions held under the same doc_id; review F01). Beyond that it distinguishes:
//   - VERIFIED DUPLICATES: other doc_ids whose current copy is byte-identical (same SHA-256) and whose original
//     re-hashed at load. They are listed and included ONLY on explicit opt-in, one by one.
//   - DISTINCT EDITIONS: other doc_ids that look like the same instrument (same type and normalised title, or same
//     number) but hold different bytes (another print, language or edition). They are listed for information and are
//     never included by this action; each needs its own withdrawal decision.
// Pure function over the active generation so it can be tested without a database.
using System.Text.RegularExpressions;
using Mimamsa.Core.Generation;

namespace Mimamsa.Core.Delivery;

public sealed record ScopeEntry(string DocId, string? Title, string Sha, string? Language, bool Verified);

public sealed record WithdrawalScopeResult(string DocId, IReadOnlyList<string> OwnCopies, IReadOnlyList<ScopeEntry> VerifiedDuplicates,
                                           IReadOnlyList<ScopeEntry> DistinctEditions);

public static partial class WithdrawalScope
{
    [GeneratedRegex(@"[^a-z0-9]+")] private static partial Regex NonWord();

    static string Norm(string? s) => NonWord().Replace((s ?? "").ToLowerInvariant(), " ").Trim();

    public static WithdrawalScopeResult Compute(IReadOnlyDictionary<string, DocumentRecord> docs, IEnumerable<HeldCopy> held, string docId)
    {
        var d = docs[docId];
        var own = held.Where(h => h.DocId == docId).Select(h => h.Sha).Append(d.CopySha).Distinct().ToList();
        var dup = new List<ScopeEntry>(); var ed = new List<ScopeEntry>();
        var title = Norm(d.Title); var number = Norm(d.Number);
        foreach (var o in docs.Values)
        {
            if (o.DocId == docId) continue;
            var entry = new ScopeEntry(o.DocId, o.Title, o.CopySha, o.Language, o.OriginalVerified);
            if (o.CopySha == d.CopySha) { if (o.OriginalVerified && d.OriginalVerified) dup.Add(entry); else ed.Add(entry); }
            else if (o.DocType == d.DocType && ((title.Length > 0 && Norm(o.Title) == title) || (number.Length > 0 && Norm(o.Number) == number)))
                ed.Add(entry);
        }
        return new WithdrawalScopeResult(docId, own, dup.OrderBy(x => x.DocId).ToList(), ed.OrderBy(x => x.DocId).ToList());
    }
}
