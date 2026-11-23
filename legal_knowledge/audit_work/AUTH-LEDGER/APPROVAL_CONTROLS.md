# AUTH-LEDGER approval controls: threat review and AUTH-LEDGER-02 hardening

**Scope.** This file reviews how a ledger entry comes to count as approved, and what AUTH-LEDGER-02 adds. **No entry is approved, and no owner decision record is created, in this work package.** Version zero is unchanged: the genesis line, `ledger/HEAD` and the four Cycle 5 outputs are byte-identical.

## Four roles that must stay distinct
| Role | Who | What it establishes | What it never establishes |
| --- | --- | --- | --- |
| Technical review | an independent reviewer (human, or an AI agent such as the Fable reviews) | the code and the evidence references behave as specified | evidence authenticity, owner approval, legal effect |
| Evidence authentication | the entry, its evidence references and the rule-1 checks | that a held copy's provenance is documented to the class's standard | that the document is in force, applicable or binding |
| Owner approval | the repository owner, as a person | that the owner accepts the entry into the effective register | legal or JAG approval |
| Legal or JAG approval | a legal adviser | legal status, applicability, precedent | — (outside this ledger) |

Each decision record now has to say `scope: AUTHENTICATION_PROVENANCE_ONLY` and `legal_approval: NOT_GIVEN`. Each review record has to say `scope: TECHNICAL_AND_EVIDENCE_REVIEW` and `legal_approval: NOT_GIVEN`. A record that claims anything else is rejected.

## What AUTH-LEDGER-01 already guaranteed
- **Pinned records.** Each version's D- and R- records are pinned by sha256 in the manifest line and in each entry.
- **Bound content.** Each record names `entry_id=sha256:entry_digest` and the ledger version. Altering an entry, or reusing a record for another version, breaks the match.
- **Separation.** Decision and review must be different files with different normalised names. An ACCEPT_WITH_CONDITIONS review counts only with `conditions_status: DISCHARGED`.
- **Hygiene.** No duplicate keys; valid dates; no unexpected files under `ledger/` or `decisions/`.

## Threat review
| Threat | AUTH-LEDGER-01 | AUTH-LEDGER-02 | Residual |
| --- | --- | --- | --- |
| Identity spoofing: a writer types any name into `decided_by` or `reviewer` | not detectable | names are still text. The new BIND line ties activation to a verified merge of a reviewed head. The approving GitHub review (id, login, commit) is recorded as an **asserted** fact | who clicked "approve" on GitHub is not in git history. An auditor can check it online. Cryptographic identity needs an owner signature (owner decision O-1) |
| Forged decision record | consistent records pass | a forged record has no effect until a BIND line proves the version entered through a two-parent merge whose reviewed head holds exactly those bytes | a writer who controls the PR, the review and the merge can still do all three. That is the limit of single-owner repository control (O-1, O-2) |
| An AI agent "approves" | not detected | `decided_by` naming a model or an agent (Claude, Fable, Opus, GPT, AI, bot, assistant and others) is rejected, including forms with digits or underscores such as `Fable5` and `claude_code` (Fable F-09) | a person's name typed by an agent is not detectable without O-1. The list is over-inclusive: a person named, for example, Claude must be recorded under another form of their name |
| Unauthorised approval strings (`decision: APPROVED` with no review) | rejected: a review record is required | unchanged | — |
| Reuse of an earlier decision | rejected by the version prefix and the entry digest | also rejected by the record-set check (a record may name only entries of its own version that cite it) | — |
| Duplicate approvals (two D-records naming one entry, orphan records, a record naming extra entries) | an orphan or extra pinned record went unnoticed | rejected: each pinned record must be cited, and each named entry must exist in the version, cite that record and be named once | — |
| Approval of an altered entry | rejected (digest) | unchanged | — |
| Approval after withdrawal (CORRECTION or WITHDRAW of a withdrawn row) | rejected (target not live) | tested again | re-ADD after a withdrawal needs a new entry id and new records (by design) |
| Owner decision before the independent review | not checked | rejected (decision date earlier than review date); records dated after the manifest line are rejected | dates are self-declared |
| Mismatch between the reviewed commit and the merged commit | not checkable | BIND: the merge's second parent must be `reviewed_head`, and the approving review's commit must equal `reviewed_head` | the review commit is asserted (online check) |
| Changes introduced after review | not checkable | BIND: the whole ledger package tree (tools, records, ledger, evidence, tranches) must be identical at `reviewed_head` and at the merge (Fable F-04). The manifest and every pinned file must hash to the pins. A later restore of the bytes does not hide a change made in the merge (tested) | changes outside the package (other repository code, tests) are not covered; they are matters for the PR review. A merge whose base changed the package after the PR branched fails closed and needs the base merged into the PR, then re-reviewed |
| Version added by direct push, or by fast-forward | not checkable | BIND: an ordinary two-parent merge is required; the merge base must stop before the bound version; the merge must be in the checked-out history | a writer can open and merge a PR without review unless branch protection requires a review (O-2) |
| Missing reviewer or decision records | rejected | unchanged | — |
| History rewrite of the ledger | detected unless the whole chain and the test pin are rewritten | unchanged, plus BIND facts must re-verify against the rewritten git history | force-push is a repository setting (O-2) |

## The BIND line (AUTH-LEDGER-02)
An approved version is **staged**, not effective, when it is recorded. All its checks run, so a bad version still fails CI, and its effect is reported in `transitions.json` as `PENDING_REPOSITORY_BINDING`. It becomes effective only when the **next** manifest line is a BIND line, added by a later PR after the merge, that `tools/binding.py` verifies **offline** against local git history:

1. The BIND line immediately follows the version it binds, and `bound_line_sha256` matches that line.
2. `merge_commit` is an ordinary two-parent merge; its second parent is `reviewed_head`; it is in the history of the checked-out HEAD.
3. At `reviewed_head` the manifest ends exactly at the bound version. At the merge's first parent the version is absent, so it entered through this merge.
4. The ledger package tree is identical at `reviewed_head` and at the merge. The manifest and every pinned file hash to the pins.
5. The clone is not shallow, and has no `refs/replace` and no `info/grafts`; otherwise verification fails closed. The commit-graph file is not consulted (`core.commitGraph=false`; Fable R-01). For the committed ledger, the repository top must be the repository that contains `legal_knowledge/audit_work/AUTH-LEDGER`, so a planted nested `.git` cannot divert verification (Fable R-02). git runs with a sanitised environment: every inherited `GIT_*` variable is dropped, replace objects and grafts are disabled, and no system or global config is read (Fable F-01).

Further rules:
- Only the last line may be an unbound entry version.
- History stays reproducible. `--as-of N` shows the version as pending, and `--as-of N+1` shows it applied, with `bound_by`.
- git runs with every transport protocol disabled (`protocol.allow=never`). `GIT_NO_LAZY_FETCH=1` adds protection only on git 2.44 and later; the installed git 2.43 ignores it. Verification therefore needs only a full clone or a git bundle, never a network.
- **Assurance is visible.** A bound transition carries `binding_assurance`: git topology `VERIFIED_OFFLINE`, GitHub review `ASSERTED_NOT_VERIFIED_OFFLINE` (Fable F-05). A local `--no-ff` merge with invented PR and review values would still verify topologically. The asserted values are checkable only online, and only O-2 branch protection makes a merge imply a review.
- **Withdrawals and corrections are staged too** (Fable F-14). They take effect only after their BIND line.
- **Snapshots.** An exported snapshot without `.git` cannot verify a bound ledger. Snapshots must ship a git bundle (`git bundle create`) with full history.

**Before the first BIND line,** the audit CI workflow must check out full history (`fetch-depth: 0`); otherwise verification fails closed. That is a `.github` change, so it needs its own reviewed PR and was not made here.

`require_binding=False` keeps the AUTH-LEDGER-01 semantics. It is used only for the synthetic evidence-rule tests and for the tranche simulation, both in temporary directories. The command-line tool never selects it, and a test checks that.

**Trust assumption.** Verification assumes that the local object store and `.git` directory handed to the verifier have not been tampered with beyond the mechanisms checked. The checked mechanisms are:
- replace refs, grafts and the commit-graph;
- nested repositories, with the repository top pinned from the logical package path;
- a symlinked package or a symlinked parent directory, on disk or committed as mode 120000, which fails closed before any ledger file is read (Cycle 8, closing Fable C-02);
- forged commit, tree or blob objects on every path the verdict reads (the merge, the reviewed head, both parents and every tree and blob below them), all re-hashed from their stored bytes (Cycle 8, closing C-04 and review F-02 of be861ec0);
- the inherited environment.

Every tree and blob along each path the verdict reads is re-hashed, as well as the four commit objects.

An auditor should still:
- verify from a fresh `git clone --no-local` or a bundle clone, not from a working copy supplied by the party being audited (a plain local-path clone shares or hard-links objects);
- confirm by hand that `legal_knowledge/audit_work/AUTH-LEDGER` and its parent directories are real directories;
- run the command-line tool by its repository path from outside the package. If the working directory is already inside a symlink target and the script is named relatively, the operating system reports the resolved path, and the link cannot be seen (stated residual).

## Owner decisions needed (nothing here is adopted)
- **O-1 Owner signature.** Optionally require an owner signature over each BIND line, checked against a public key supplied out of band. Options are SSH (`ssh-keygen -Y verify`) or OpenPGP.
  - Only this adds cryptographic identity to owner approval.
  - The signing tool is unavailable here (`ssh-keygen` is not installed), and no key is enrolled. So nothing is implemented, and nothing is described as signed or verified.
- **O-2 Repository settings.** On `legal-knowledge/v2.5-staging`, branch protection should require:
  - a pull request with at least one approving review;
  - dismissal of stale approvals on new pushes;
  - no force-push;
  - no bypass.

  These are GitHub settings, outside the repository files. The BIND line records the review, and an auditor can confirm it online.
- **O-3 CI full history.** Approve the `fetch-depth: 0` workflow change before the first BIND line. It is prepared as its own draft PR (Cycle 8); see `REPOSITORY_BINDING_READINESS.md`.
- **O-5 Demotions.** Should a WITHDRAW or demoting CORRECTION take effect before its BIND line? Today every version is staged (Fable F-14). Analysis and recommended procedure: `DEMOTION_SEMANTICS_O5.md`. No semantic change is implemented.
- **O-4 Who may be named.** Optionally keep a committed list of authorised owner and reviewer identities. It would be authoritative only together with O-1.
