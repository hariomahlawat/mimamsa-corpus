# Cycle 13 task register (living; updated at each milestone)

**Baseline verified 2026-11-25**
- staging `a4c0c382`; main `21de3531`; raw-data `ad77758d`
- HF head `3864faf3` (private)
- 4,121 distinct source copies; 4,277 judicial records
- 648 findings: P1 11/11 closed-verified; P2 116 closed-verified, 5 deferred (C11 F05–F08, WS-G R04)
- AUTH-LEDGER version 0

**Agent policy.** Every workstream has its own worktree and branch, `claude/c13-<ws>`, with `claude/c13-integration` as the integration branch. Execution agents are independent Opus instances. Each reviewer is a separate instance and never the author.

| WS | Scope | Branch | Executor | Independent reviewer | Gate | Status |
| --- | --- | --- | --- | --- | --- | --- |
| A0 | Evaluation infrastructure, fresh holdouts H-OUT/H-HOLD/H-REL | c13-a0-eval | Opus | Opus (to assign) | Must be accepted before formal A2/A3/A5 evaluations | Running |
| A1 | OCR recovery, false-negative audit (P0) | c13-a1-ocr | Opus | Opus | Benchmark + recovery measured | Running |
| A2 | Outcome V4 (resolves F05/F08) | c13-a2-outcome | Opus | Opus evaluator on H-OUT-C13 | Freeze after A0 acceptance | Running (dev) |
| A3 | Holdings V2 redesign (F06/F07) | c13-a3-holdings | Opus | Opus evaluator on H-HOLD-C13 | Freeze after A0 acceptance | Running (dev) |
| A4 | Statutory temporal version model; evidence | c13-a4-statutory | Opus | Opus | Traceable proposals | Running |
| A5 | Treatment graph; identities; 99 SC case numbers | c13-a5-graph | Opus | Opus | Reconfirmation before overlay | Running |
| A6 | Forms: R04 official transcription; register; oracle | c13-a6-forms | Opus | Opus | Independent transcription check | Running |
| A7 | Acquisition; PRs #7/#8/#9/#17/#23; allow-list; egazette | c13-a7-acquisition | Opus | Opus | Scope documented before any new host | Running |
| A8 | Legal-adviser packages | (A4/A6 outputs + gov) | Coordinator | Opus | — | Pending inputs |
| A9 | Deferred findings and P3 closeout; register regeneration | gov | Coordinator | Opus | Independent confirmation | Pending A2/A3/A6 |
| B0 | Windows-native assessment, ADR-0005 (proposed), traceability, security/deployment, contract v1, UX spec | c13-b-app | Opus | Opus technical + UI/UX reviewers | Evidence from PoCs | Running |
| B-PoC | P1–P5, P7 (P6/P8/P9 later) | c13-b-poc | Opus | Opus | Windows run via `windows-latest` CI | Running |
| B1 | Minimum functional research prototype | (after B0/PoC) | Opus (separate) | Opus functional/UI/UX/security | ADR-0005 accepted | Not started |
| GOV | RM-001 restriction; backup tooling; registers; plans | c13-gov | Coordinator | Opus | — | RM-001 and backup tool done |

**Owner or authority decisions pending:**
- RM-001 FOUO handling (see the decision note);
- second backup location;
- signing-key custody;
- Legal Reviewer appointment;
- production hardware;
- apt/system packages: Tesseract, and any others the PoCs need.

None of these blocks unrelated work.
