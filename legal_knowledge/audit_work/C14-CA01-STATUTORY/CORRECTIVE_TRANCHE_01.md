# Cycle 14 corrective tranche 01 — development receipt

Date: 26 Nov 2026. No acquisition, HF write, corpus run, legal promotion, merge, or rebase. All changes in draft branches. Staging observed ee17b0660511b66fdd5307833e11d1268de35b56.

Review subjects before corrective changes: PR58 25c8a3a4ce1ec7999e872f42f0e51db9f79c71c3, PR59 5bf8cd5dd89b82dd141e264983c408012746967a. Corrective code heads at this receipt: PR58 0f5929412c359e5d7336300e57a63a164bf44f9f, PR59 636f3c2f866a4e9254d7c64d867dd1c331f60f93. This receipt is documentation only.

| Finding | Corrective implementation | State (not independent closure) |
|---|---|---|
| C14-01 P1 | Acquisition CLI unconditional hold; separate dual Ed25519 signature verifier binds raw approval payload, exact code commit, plan and inventory digests, targets, UTC expiry, distinct externally trusted roles. | Contained; no trusted production keys, authority provisioning, activation wiring or independent closure. Direct Python helpers are not an OS security boundary. |
| C14-02 P1 | Candidate numeric sockaddr transport with public-address policy, exact connected-peer comparison, verifying TLS and SNI; no automatic redirects; no proxy. | Prototype only; transport integration, egress policy and independent native tests pending. No live use. |
| C14-03 P2 | Interlock prevents execution of incomplete robots/timeout/receipt implementation. | Open. Correct parser semantics, process-wide limits and safe receipts still needed. |
| C14-04 P2 | Metadata-only coverage checker with revision, store, path, size and digest-basis checks; never sets acquisition eligibility. | Prototype untested; full independently attested HF and permitted local-store inventory still needed. |
| C14-05 P2 | Existing execution held; standalone verifier documented as noncommissioned. | Open native Windows handle/ACL/junction tests and isolation. |
| C14-06 P2 | README separates historical byte matches from current-head path presence. | Open current-revision byte evidence, SDK/log review and backup validation. |
| C14-07 P2 | No new render operation. | Open parser isolation, render budget, renderer binding and independent visual adjudication. |
| C14-08 P3 | README now matches actual standalone clone, optional IPv4 launcher and canonical inventory versus exact artifact digests. | Proposed documentary correction; verify instructions on Windows. |
| C14-09 P2 | All ten C5 constituents explicitly enumerated, five unresolved and disabled, five subject identified outside Army Rules including two original pin holds. | Proposed coverage correction; no legal closure. |
| C14-10 P1 | Legacy relevance and extract callable writers suspended; records writer suspended and read-only rebuild plan added, including recovered hash paths; legacy CLI mutating stages denied. | Contained on draft branch, not staging; legacy functionality deliberately suspended, not a complete non-destructive replacement. Recovery plan needs byte/path/identity checks, append-only persisted outputs and downstream importer/retrieval gate. Do not run old pipeline on staging. |
| C14-11 P2 | Shadow v2 flags hidden/translucent text and vector content; no conclusive negative, complete visual evidence or documentary eligibility without concordance. | Conservative containment; page-image concordance and OCR binding still open. |
| C14-12 P2 | Classifier receives marker-free page text joined by newline; separate page-marked evidence and classifier digests. | Implemented and injected classifier tests passed. Actual default classifier threshold/cross-page regression file committed, not executed. |
| C14-13 P2 | Scope derives all page geometry from exact SHA-256-bound raw PDF, includes viewport/crop/rotation/matrices/renderer in identity. | Nine synthetic tests passed; pixel mapping, source render and retrieval integration open. |
| C14-14 P3 | Immutable printed-page label type, canonical coordinates and controlled metadata failures; renderer/classifier mode recorded. | Partial; extractor/classifier implementation/configuration digest and broader schema validation open. |
| C14-15 P3 | Compound A4-ACQ-033 components explicitly separated and preserved-copy rehash meaning clarified. | Proposed provenance correction; independent review pending. |

## Executed tests

32/32 passed in isolated Linux Python 3.13.5 with installed PyMuPDF and cryptography. All PDF fixtures and keys synthetic; no active data or network used. Exact Git blob matches verified:

- approval_gate.py 4871084f2be075b0a5aa7d70faa2ff96aa75fd6b; test_approval_gate.py 7c48e46dacf75731a947f1ff79582356e82d8688: 12 passed.
- shadow_assessment.py 0c7e3d958c38edffa224ca72704f7a471d4307a4; test_shadow_assessment.py fa85751131339c012355921307a8ae252540c0a7: 11 passed (injected classifier and quality functions).
- instrument_scope.py a96587975232d9b4b90ce010303efa7e97afc894; test_instrument_scope.py f727deb4233bf3667ba75139983c8648e8960ffc: 9 passed.

Reproduce with python -B -m unittest on the named test modules from an isolated checkout (set PYTHONPATH to repo root and use runner directory for approval tests). test_corrective_interlocks.py is committed but unexecuted; full repository CI not established, and old tests expecting mutable CLI and writer behavior are incompatible with the temporary hold. Do not merge the interlock as a production substitute. Do not waive those tests: migrate them to the accepted versioned non-destructive contract and preserve baseline failures as regression evidence.

Next tranche: implement safe persisted assessment/recovery outputs and importer gating; test actual default classifier and records recovery with synthetic SQLite; complete acquisition process/robots/receipt controls and attested hash inventory; establish native Windows isolation and trusted approval provisioning. Only then request consolidated independent corrective review. All 15 findings remain tracked until reviewer acceptance or documented owner decision. No operational activation.
