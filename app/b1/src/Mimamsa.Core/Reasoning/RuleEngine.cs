// C15 WP4: deterministic rule-evaluation foundation (DETERMINISTIC_LEGAL_ENGINE §2–§3, §8, §10).
// - Three-valued (strong Kleene) predicate logic: UNKNOWN is never coerced to false.
// - Typed decision tables with a UNIQUE hit policy: a pack whose rows can both match the same complete input is
//   rejected at construction (no implicit row order, no latest-date preference).
// - Two-stage gate: evaluation admission and definitive delivery. At AUTH-LEDGER v0, and whenever no approved grant
//   covers the exact request, BOTH are denied and the table is NOT invoked (§10: "deny both and do not invoke
//   evaluator, even for uncertainty"). No real rule pack or grant exists in this installation; tests use synthetic
//   tables only, never as legal rules.
namespace Mimamsa.Core.Reasoning;

public enum Tri { False = 0, True = 1, Unknown = 2 }

public static class Kleene
{
    public static Tri Not(Tri a) => a switch { Tri.True => Tri.False, Tri.False => Tri.True, _ => Tri.Unknown };
    public static Tri And(params Tri[] xs) => xs.Contains(Tri.False) ? Tri.False : xs.Contains(Tri.Unknown) ? Tri.Unknown : Tri.True;
    public static Tri Or(params Tri[] xs) => xs.Contains(Tri.True) ? Tri.True : xs.Contains(Tri.Unknown) ? Tri.Unknown : Tri.False;
    public static Tri Of(bool? b) => b is null ? Tri.Unknown : b.Value ? Tri.True : Tri.False;
}

/// A row: required value per input (inputs not named are "any"), and its output.
public sealed record DecisionRow(IReadOnlyDictionary<string, bool> When, string Output);

public sealed class RulePackRejectedException(string reason) : Exception(reason);

public sealed record TableResult(string State, string? Output, IReadOnlyList<string> Trace)
{
    public const string Decided = "DECIDED", Unknown = "UNKNOWN", NoRuleMatched = "NO_RULE_MATCHED";
}

public sealed class DecisionTable
{
    public string Id { get; }
    public IReadOnlyList<string> Inputs { get; }
    public IReadOnlyList<DecisionRow> Rows { get; }
    public int Invocations { get; private set; }

    public DecisionTable(string id, IReadOnlyList<string> inputs, IReadOnlyList<DecisionRow> rows)
    {
        if (inputs.Count is 0 or > 12) throw new RulePackRejectedException("a table needs 1 to 12 boolean inputs");
        foreach (var r in rows)
            foreach (var k in r.When.Keys)
                if (!inputs.Contains(k)) throw new RulePackRejectedException($"row names undeclared input '{k}'");
        // UNIQUE hit policy, checked exhaustively over all complete boolean assignments
        for (int mask = 0; mask < 1 << inputs.Count; mask++)
        {
            int hits = rows.Count(r => r.When.All(kv => ((mask >> IndexOf(inputs, kv.Key)) & 1) == 1 == kv.Value));
            if (hits > 1) throw new RulePackRejectedException($"rows overlap for assignment {mask}: unique hit policy violated");
        }
        (Id, Inputs, Rows) = (id, inputs, rows);
    }

    static int IndexOf(IReadOnlyList<string> xs, string k) { for (int i = 0; i < xs.Count; i++) if (xs[i] == k) return i; return -1; }

    /// Strong Kleene evaluation. A row whose match is UNKNOWN prevents a decision unless another row is definitely matched
    /// (which cannot happen together with uniqueness when the unknown row could also match: the result is UNKNOWN).
    public TableResult Evaluate(IReadOnlyDictionary<string, Tri> facts)
    {
        Invocations++;
        var trace = new List<string>();
        var definite = new List<DecisionRow>(); bool possible = false;
        foreach (var r in Rows)
        {
            var m = Kleene.And(r.When.Select(kv => facts.TryGetValue(kv.Key, out var f) ? f == Tri.Unknown ? Tri.Unknown : Kleene.Of(f == Tri.True == kv.Value) : Tri.Unknown).ToArray());
            trace.Add($"row {r.Output}: {m}");
            if (m == Tri.True) definite.Add(r); else if (m == Tri.Unknown) possible = true;
        }
        if (definite.Count == 1 && !possible) return new TableResult(TableResult.Decided, definite[0].Output, trace);
        if (definite.Count == 0 && !possible) return new TableResult(TableResult.NoRuleMatched, null, trace);
        return new TableResult(TableResult.Unknown, null, trace);
    }
}

public sealed record GateDecision(bool EvaluationAdmitted, bool DeliveryAuthorized, IReadOnlyList<string> Blockers);

/// Gate over the trusted ledger state and approved grants. No grant can be created by this code or any model.
public static class RuleGate
{
    public static GateDecision Decide(int authLedgerVersion, bool approvedGrantCoversExactScope)
    {
        var b = new List<string>();
        if (authLedgerVersion <= 0) b.Add("AUTH-LEDGER is at version 0: no approval, appointment or legal promotion exists, so no rule pack may be evaluated.");
        if (!approvedGrantCoversExactScope) b.Add("No approved grant covers the exact requested scope (service, procedure, dates, output class, pack revision).");
        bool ok = b.Count == 0;
        return new GateDecision(ok, ok, b);
    }

    /// Evaluates only when admitted; otherwise returns NOT_CHECKED without invoking the table.
    public static (string state, TableResult? result, GateDecision gate) Evaluate(DecisionTable table, IReadOnlyDictionary<string, Tri> facts, int authLedgerVersion, bool approvedGrantCoversExactScope)
    {
        var gate = Decide(authLedgerVersion, approvedGrantCoversExactScope);
        if (!gate.EvaluationAdmitted) return ("NOT_CHECKED", null, gate);
        return ("EVALUATED", table.Evaluate(facts), gate);
    }
}
