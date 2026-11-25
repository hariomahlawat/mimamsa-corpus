# Independent review: C13 B0 (branch `claude/c13-b-app` @ `dc811848`)

- **Reviewer:** independent technical and UX reviewer (not an author of the work). Read-only review; no commits.
- **Date:** 2026-11-25.
- **Scratch clone:** `reviews/b0/repo`, made with `git clone --shared` and checked out at `dc811848`.
- **Base:** `a4c0c382` (staging). The diff touches only `app/`, `docs/` and `.github/workflows/app-ci.yml`.
- **Reproducible probes:** everything is under `reviews/b0/negctl/`:
  - `negctl.py` / `results.txt` hold the contract negative controls and probes;
  - `tokens_extra.py` / `tokens_extra.txt` check contrast for undeclared token pairs;
  - `matrix_check.py` / `matrix_check.txt` check matrix consistency.
- **Findings register:** `review_c13_b0_dc811848_findings.csv`.

## Verdict

**ACCEPT WITH REQUIRED CHANGES.** I found no P1. I raise **12 P2** and **14 P3**.

The P2s must be closed or dispositioned before GB1. The contract-level P2s (F01–F05) should be fixed before any bundle is produced for B1.

The architecture follows the owner directive in substance:
- Windows-native deployment, with Docker, WSL and VMs withdrawn;
- a two-role model with an inert Legal Reviewer designation;
- seven separate status axes;
- an Ed25519-signed bundle validated against the restricted register;
- gated features.

The weaknesses are mainly:
- in the edges of the contract: smuggling across status axes, unchecked references to restricted items, and path rules that are POSIX-only on a Windows target;
- in how withdrawals and restrictions propagate over time;
- in the UX's fit with Windows browsers and with professional legal-research workflows.

## 1. Tests and negative controls (check 1)

| Run | Result |
| --- | --- |
| `pytest app/contract/tests app/design/tests` (venv: Python 3.13, pins as in `requirements.txt`) | **131 passed, 1 skipped**. The skipped test is `test_parity_with_repository_guard_when_integrated`: `scripts/restricted_material.py` is not on this branch until the governance branch is integrated |
| Register used | `origin/claude/c13-gov:config/restricted_material.json` (RM-001), resolved by the fixture through `git show`. Nothing is hard-coded under `app/` (a test enforces this) |

My own negative controls, written independently of the authors' tests:

| ID | Control | Outcome |
| --- | --- | --- |
| N01–N03 | Invalid records: missing required field, malformed sha256, `doc_type` outside the enum | Rejected (`SCHEMA`) |
| N04–N08 | Collapsed status axis: top-level `verified`, a single `overall` axis, one axis dropped, an approval value on `publication`, a nested `legal_approval` key inside `publication` | Rejected (`SCHEMA`) |
| N09–N11 | Restricted sha, restricted doc_id, and restricted doc_id in section form `#s12` in a record | Rejected (`RESTRICTED_MATERIAL`) |
| N12, N14 | A bundle with a restricted doc_id record; a bundle with a restricted hosted path | Rejected |
| N15–N16 | Tampered file; tampered `SHA256SUMS` entry | Rejected (`CHECKSUM_MISMATCH`, plus `SIGNATURE_INVALID` for N16) |
| N17–N19 | Bad signature bytes, other key, missing signature | Rejected (`SIGNATURE_INVALID` / `_KEY_MISMATCH` / `_MISSING`) |
| N20 | Clean bundle (positive control) | Accepted |

**All required negative controls behave as specified.** Further probes found gaps; they are the basis for F01–F05 and F13–F15:

| ID | Probe | Outcome |
| --- | --- | --- |
| P13 | `publication.policy_v1 = {"legal_approval":"T2…","verified":true}` | **Accepted.** `axis_value` allows `policy_v1: {}` (any content) on every axis |
| P01–P03, P15 | `evidence_fidelity=FIDELITY_VERIFIED`, `legal_applicability=EVIDENCED` and `source_authenticity=IDENTITY_CONFIRMED` (with policy fields still UNKNOWN/HASH_ONLY), each with only a free-text basis; `PUBLISHED` while `source_integrity=MISMATCH` | **Accepted** |
| P06, P07 | Graph-edge `target.node_id` set to the restricted doc_id; `parent_doc_id` set to the restricted doc_id | **Accepted** |
| P08 | Restricted text under an upper-cased doc_id path (Windows paths are case-insensitive), with new bytes | **Accepted** |
| P09–P11 | Bundle paths with an alternate data stream (`notes.txt:hidden`), a device name (`CON.txt`) and a trailing-dot alias (`documents.jsonl.`) | **Accepted** |
| P12 | Bad signature | Rejected, but the 4 records were still parsed. The validator is not fail-fast |
| N20 | Clean bundle with `key_id` `dev-<fp>` and the dev key pinned | Accepted with no warning. Security §8.1 says a production importer refuses `dev-` key ids |
| P05 | Manifest asserts `auth_ledger_version: 1` to carry a T1 approval | Accepted. The manifest asserts the ledger version itself, and nothing cross-checks it against the AUTH-LEDGER HEAD |
| P14 | `approval_ref: "anything"` | Accepted. It is a free string |
| P04 | T1 approval when the caller gives no ledger version | Accepted, which is by design: the CLI default is 0. Informational only |

## 2. Requirements versus contract and architecture (check 2)

| Directive requirement | Assessment |
| --- | --- |
| Windows-native, no Docker, WSL or VM | Met in ADR-0005, the assessment and the security document. The execution plan still has unmarked stale text: GB2 "air-gapped VM" (l.576), l.497, and old B-numbering at l.344/587 (F20) |
| ASP.NET Core vs Django, IIS/Service, React/TS, PostgreSQL FTS, pgvector, relational graph, PDF.js, Python workers, ONNX, local accounts plus AD | All present as candidates. The decision is correctly deferred to P1–P9 and GB1 |
| **Signed offline installer** | **Contradicted.** The assessment §12.1 and security §8.1 make installer code-signing "optional but recommended" (F08) |
| Signed updates, key with the owner | Custody is described well. The trust list's change authority is undefined, and the validator accepts `dev-` ids (F05) |
| Update sequence | The steps exist (security §8.2, assessment §12.2). Gaps: the reference validator is not fail-fast (F05); "record dependencies" is implicit (impact triggers only); rollback does not say how it treats Admin uploads made after activation (F23) |
| Data layers: vault, derivatives, provenance, candidates, reviewed, authenticated, publication state, indexes, working docs | Vault, derivatives, provenance, candidates, indexes and working sessions are present. **Reviewed records, authenticated/approval records and publication-state history have no schema or storage model.** `review_ref` and `approval_ref` are unverifiable strings. Publication is a producer-set field in the bundle, although ADR-0002 makes publication a site Admin act (F09) |
| Seven separate status axes, never collapsed | Structurally met (N04–N08), but leaky: P13 smuggling, and elevated values need no evidence (F01, F02) |
| Stable identifiers, versioned schemas | Met for doc_id, release_id, `$id …/v1/`, semver and migrations. There is no stability policy for `candidate_id` across releases (F26, P3) |
| Two roles; Legal Reviewer as an inert designation; backend authorisation | Met (security §7.3; design 01). Holdings are an Admin-only diagnostic (CAP-JI-05), which departs from PR-01/ADR-0002 equal access. Record it as an owner-approved exception (F21) |
| Zero runtime internet | Met at design level: §5, §11, T-NET-01, no URLs in the tokens |
| Threat list (11 classes) | All mapped in security §9.1 (check 3) |
| Restricted rule keyed on `config/restricted_material.json` | Met: fail-closed, no second list, the config hash is pinned in the manifest. Reference gaps in F03, F13. Admin uploads of restricted bytes are quarantined and kept, which conflicts with the register's `routine_operations_forbidden: copy` (F06) |
| Capability matrix §18.1–18.8; commander assistant and legal rules gated | All 8 areas and 52 capabilities are covered. CA-01/02/03/05, SE-03/06, DS-03/04, JI-07 and KA-06 are gated. CA-04 (presentation layout) is ungated, consistent with design 03 §7 |

**ADR-0001..0004 / docs/product:** I found no hard contradiction. Two items need a recorded owner disposition:
- the Admin-only holdings diagnostic versus ADR-0002 d.1 and PR-01 (F21);
- the bundle-carried `publication=PUBLISHED` versus the ADR-0002 Admin publication gate (F09).

PR-20 and PR-29 are not referenced by the matrix (F19).

## 3. Security architecture (check 3)

**Strengths:**
- per-service virtual accounts;
- NTFS ACL matrix;
- outbound firewall per service SID;
- parser children in Job Objects;
- default-deny router with service-layer guards;
- owner checks that bind Admin too;
- metadata-only audit;
- a detailed T-* catalogue that covers all 11 directive threat classes.

**Weaknesses:**
- **F04:** the reference validator has POSIX-only path rules (ADS, device names, trailing dot or space, no junction check). Security §8.2 claims the validator implements steps 1–5, and T-PARSE-04 lists exactly these cases.
- **F05:** `dev-` key ids are accepted silently. The validator is not fail-fast after a signature failure. Who may change the pinned trust list is unspecified; if a site Admin can add a key, the owner's custody of the production key is bypassed.
- **F06:** the retained N-1 generation and rollback can resurrect withdrawn or newly restricted items. No channel delivers a register update, and there is no purge across existing generations, derivatives and backups. Quarantined restricted uploads persist and get backed up.
- **F07:** client-side persistence on shared office desktops is not covered:
  - recent queries are kept "local to the user";
  - tabs are persisted;
  - there is a "read-only cached view of open tabs" while offline;
  - there is no `Cache-Control: no-store` or purge on logout;
  - T-VIS-02 omits browser caches.
- **F08:** a signed installer is optional.
- **P3:**
  - no at-rest encryption (BitLocker) for the vault, backups or offline media (F25);
  - no size or line limits for JSONL in bundle parsing, and duplicate JSON keys create parser-differential risk (F15);
  - the validator has no downgrade or replay check (F16);
  - the W-11 "choose bundle folder" step does not say whether it is a browser upload or a server path (F24).

## 4. UX specification (check 4)

**Positive:**
- research comes first;
- no home dashboard;
- no metric cards or relevance scores;
- seven axis rows that never merge;
- status is never shown by colour alone;
- "absence ≠ no authority" notices;
- a graph list view as the keyboard and screen-reader primary;
- static skeletons;
- gate notices without sample output;
- identity built on a 4 px grid.

I found no generic dashboard pattern. The status footer and the backup page are text-only.

**Problems:**
- **F10:** the keyboard map collides with shortcuts that Windows browsers reserve or will not reliably pass to the page:
  - Edge `Ctrl+Shift+P` opens an InPrivate window; Chrome `Ctrl+Shift+N` opens Incognito;
  - `Ctrl+W`, `Ctrl+Tab` and `Ctrl+1…5` control browser tabs;
  - the offered alternates `Alt+←/→` are browser Back and Forward;
  - `Ctrl+Shift+C` opens the DevTools inspector;
  - `Ctrl+Shift+O` opens favourites or bookmarks;
  - `F6` cycles to the address bar.
- **F11:** breakpoints are in CSS px and ignore Windows display scaling. A 1920×1080 screen at the common 125% setting is 1536 CSS px, which lands in the compact layout. A 1366×768 screen at 125% is about 1093 CSS px, which triggers the **tablet touch layout** on a desktop.
- **F12:** legal-research gaps:
  - no Boolean or proximity operators;
  - no field search (judge, party, bench, decision-date range);
  - "Copy citation" produces internal ids (`doc_id · sha12 · release`) rather than a legal citation (case title, neutral or reported citation, para);
  - no export of a research set as a citation list;
  - no search history.
- **P3:**
  - tokens (F17), detailed in the next list;
  - at 200% and 400% zoom the sticky, non-dismissable banner plus fixed chrome take up most of the viewport, and the 1366×768 vertical budget (~580 px) is optimistic, with about 545 px realistic in Edge (F18);
  - results rows are dense with chips, and ◇ versus ◆ is hard to tell apart (F22).

Token problems (F17):
- `fg.withdrawn` on `bg.selected` measures 4.40 in light, against the 4.5 required. It is an undeclared pair.
- The dark-theme highlights drawn over white PDF.js pages give black text contrast of 2.43 (search) and 1.68 (OCR box).
- Search and OCR-box highlights differ only in hue (luminance ratio 1.01).
- Pairs not declared in `contrast_pairs` are never tested.

## 5. Traceability matrix (check 5)

`matrix_check.py` results:
- 52 rows × 16 columns, with no duplicate ids;
- MD and CSV id sets are identical;
- the phase and gated values agree row by row;
- the summary table counts match the CSV for every area.

Gaps:
- 29 empty `dependencies_limitations` cells, and about 70 cells containing only "—".
- **11 of 33 security tests are never referenced by any capability:** T-PARSE-01..05, T-PDFJS-01, T-SQL-01, T-XSS-01, T-PRIV-01, T-NET-01 and T-LEDGER-01. Examples:
  - CAP-KA-01 (upload) cites no T-PARSE test;
  - CAP-US-06 (viewer) cites no T-PDFJS-01.
- PR-20 and PR-29 are unreferenced.

These are recorded as F19 (P3).

## 6. App CI versus HF sync (check 6)

**Verified: app CI cannot trigger HF sync.**
- `app-ci.yml` has `permissions: contents: read`, no secrets, and no `workflow_run`, `workflow_call` or `repository_dispatch`. It only runs pytest and the CLI.
- `sync-legal-knowledge-hf.yml` triggers only on push to staging or main under `legal_knowledge/**`, the listed scripts and `.mml_transfer/**`, plus a gated `workflow_dispatch`. It has no `workflow_run`.
- The B branch changes no file under those paths.

Note (F20, P3): the contract job depends on `origin/claude/c13-gov` existing on GitHub. If the governance branch has not been pushed, CI fails by design, since the tests never skip. CI does not validate the matrix CSV.

## 7. Findings

See `review_c13_b0_dc811848_findings.csv`. P2 summary:

| ID | Statement |
| --- | --- |
| F01 | `policy_v1: {}` is unconstrained on every axis, so approval or verified values can be smuggled into other axes |
| F02 | Elevated axis values and inconsistent combinations are accepted with only a free-text basis |
| F03 | Restricted references through graph-edge targets and `parent_doc_id` are not checked |
| F04 | Windows path hazards (ADS, device names, trailing dot or space, junctions) are accepted by the reference validator |
| F05 | Signature trust: `dev-` ids are accepted silently, the validator is not fail-fast, and the trust-list change authority is undefined |
| F06 | Withdrawal and restriction do not propagate to the N-1 generation, rollback or backups; there is no register update channel; quarantined restricted uploads are retained |
| F07 | Client-side caches and local persistence on shared desktops are unaddressed |
| F08 | A signed installer is optional, which contradicts the directive |
| F09 | The nine-layer data separation is not specified as a whole; reviewed, authenticated and publication-state records have no model; refs are unverifiable strings; producer-set publication conflicts with the ADR-0002 Admin gate |
| F10 | The keyboard map collides with shortcuts reserved by Edge and Chrome on Windows |
| F11 | Breakpoints ignore Windows display scaling |
| F12 | Missing professional legal-research features: Boolean, proximity and field search, legal-format citation copy and export |
