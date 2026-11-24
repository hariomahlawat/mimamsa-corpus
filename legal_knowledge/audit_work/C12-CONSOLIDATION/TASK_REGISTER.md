# Cycle 12 task and dependency register (living document; updated at each milestone)

| WS | Scope | Execution agent | Independent reviewer | Depends on | Deliverables | Acceptance | Status | Refs |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | Integration into staging: #40→#41→#42→#44→#43→#47; TXN-DEMO regenerated; CI gate | Opus (lead) | Opus, independent instance | Accepted heads | PR #48, TXN-DEMO regeneration, CI step, negative-control test | Gate green on the combined tree; review with no open P1/P2; protected hashes intact; ledger v0; no HF upload | Review running | `claude/c12-integration` 24a77a3f, PR #48 |
| B | Preservation of the 48 copies; HF byte verification | Opus (lead) + Opus visual inspector | Opus | Visual inspection of the 73 pages | Preservation copy, restoration test, inspection record | Byte-identical restore verified | In progress. HF bytes blocked (no credential) | `preservation/` |
| C | Product blueprint PR #46 | Opus (fixes) | **Fable 5.2** (confirmation, then delta) | — | Fixes for F-01..F-10, closure table | No open P1/P2; owner decision on the Legal Reviewer designation recorded | Delta review running | `claude/c12-blueprint-fixes` ebeab659 |
| D | Outcome extractor V3 | Opus | Opus (blind scoring by the lead + independent review) | V3 holdout coded and adjudicated | `extractor_v3/`, holdout evaluation | Strict precision ≥95% and coverage ≥85%, or an honest shortfall report | Implementation running; holdout 150 judgments double-coded (136/150 agree), adjudication running | `holdout_v3/` |
| E | Holdings extraction and benchmark | Opus | Opus blind annotator (reference set) | — | `holdings/`, `holdings_reference/` | Measured precision and recall against the blind reference | Running | — |
| F | Statutory citation quality (983 items) | Opus | Opus | — | `statutory_citations/` | Traceable proposals; no evidence-state inflation | Running | — |
| G | Form and template registry | Opus | Opus | Blueprint register definition | `forms_registry/` | Every form source-backed with page references; nothing invented | Running | — |
| H | Targeted acquisition | Opus | Opus | Allow-list policy | `acquisition/` | Policy-compliant; hashes verified | Done: 25 first-tier judgments acquired; other targets blocked (see README) | — |
| I | SC case-number corrections; adviser package; backlog | Opus | Opus (reconfirmation is itself independent) | C11 scnum review | `metadata/`, `adviser_package/` | 73 reviewed-correct + reconfirmed corrections as a versioned overlay; nothing applied in bulk | Running | — |
