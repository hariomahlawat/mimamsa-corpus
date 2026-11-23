# Rule policy options for owner decision (no behaviour changed at rule version 1)

Version zero implements the current behaviour as **rule version 1**. Any change below that alters authentication eligibility must arrive as a separately reviewed rule-version transition, with its own `--as-of` diff. Historical versions keep rule 1.

## A. Positive verification state for retrieval records
- **Current rule 1:** a retrieval record is a locator unless it **disclaims** authenticity (`authenticity=UNCONFIRMED`) or reports `NOT_FOUND` or `CONFLICTING`. This is a deny-list.
- **Data:** the 229 retrieval records split by `verification_state` into 119 SOURCE_LOCATED, 94 SOURCE_VERIFIED, 8 NOT_FOUND and 8 CONFLICTING.

| Option | Effect | Risk |
| --- | --- | --- |
| A1. Keep the deny-list | no change | SOURCE_LOCATED records (located, content not verified) can carry FULL provenance, for example the R23 S-REVD Gazette records, Navjot S-REVB-012 and the Rajbir rendition S-JUD-005 |
| A2. Require SOURCE_VERIFIED | strictest | demotes the 7 R23 Gazette proposals and some court proposals to partial, although their byte identity is proven by sha256 |
| **A3 (recommended).** Separate the two questions: a SOURCE_LOCATED record proves **retrieval provenance** (URL plus the record's own sha256) but not **content verification**. FULL locator strength is kept; the entry must also carry identity evidence (already required), and its limitations must say "retrieval record SOURCE_LOCATED: content verified by the identity check only" | matches the evidence: byte identity comes from the hash, identity from the image check | needs a rule-2 transition that adds the field `retrieval_verification_state` to entries and tests it |

## B. Legacy page-image records without a result field
- **Current rule 1:** a row in an older image-check register counts as identity evidence when it names the sha256 and carries a 64-hex render hash. Only C6 checks have `identity_result` (CONFIRMED or PARTIAL).

| Option | Effect | Risk |
| --- | --- | --- |
| B1. Accept as now | no change | an old row that read something other than the identity elements still counts |
| **B2 (recommended).** Accept with limitation, and require a fresh check for entries that carry exact anchors. For court and Gazette entries whose approval would create an EXACT_ANCHOR, the decision record must cite either a C6-style check with `identity_result=CONFIRMED` or a reviewer statement that the legacy reading names the identity elements | targets the risk where it matters; Gazette rows with no crosswalk effect can rely on legacy rows with a stated limitation | small extra review work per SC tranche |
| B3. Require fresh review for all | strongest | re-review of about 20 Gazette rows with no coverage effect |

## C. URL normalisation for contradiction detection
- **Current rule 1:** exact string comparison. Variants such as `/jonew/judis/` versus `/judgment/judis/`, a trailing slash, or `http` versus `https` are not equated.

| Normalisation | Safe? | Why |
| --- | --- | --- |
| lower-case scheme and host; drop default port; drop a fragment | **yes** | RFC 3986 equivalence; cannot merge different resources |
| strip a trailing slash | no | can merge a directory and an index document |
| `http` to `https` | no | different origins; a downgrade may serve other bytes |
| equate known mirror paths (`/jonew/judis/` and `/judgment/judis/`) | no, not automatically | needs evidence that both paths serve one resource; record as an explicit alias table with a decision reference |
| drop query strings | no | query endpoints (`showfile?filename=`) identify different documents |

**Recommended C2:** apply only the RFC-safe normalisation in rule 2, plus an explicit, decision-referenced alias table. A match under normalisation is reported as a **contradiction candidate** requiring review, never silently merged and never silently ignored.

## D. Copy-fidelity classification (controlled vocabulary)
The overlay keeps fidelity separate from identity, provenance, authority, completeness, currency and applicability.

| Fidelity class | Meaning | Primary eligibility at rule 1 | Examples |
| --- | --- | --- | --- |
| `SCANNED_FACSIMILE` | page images of a printed official publication | yes (as in Cycle 4) | 1954-1991 Army Rules Gazettes on archive.org |
| `BORN_DIGITAL_SIGNED_RANGE_SPANS_FILE` | e-Gazette whose embedded signature byte range spans the file (**not** a validated signature) | yes (provisionally) | S.R.O. 2(E)/2018, 17(E)/2019 |
| `BORN_DIGITAL_REWRITTEN` | signature range does not span the file (re-hosted and re-written) | **no** | TRA 2026 (India Code) |
| `ARCHIVE_DERIVATIVE` | re-rendered by archive.org, not the uploaded file | **no** | S.R.O. 6(E)/2022 |
| `OFFICIAL_COURT_ISSUED` | court-host copy of a judgment, as issued | yes | api.sci.gov.in copies |
| `COURT_SYSTEM_RENDITION` | court-system text rendition with unknown carrier | **no** | Rajbir bosir copy |
| `INCOMPLETE` | missing parts | **no** | ER 2023 13 MB copy |

**Owner decisions:**
- adopt A3, B2 and C2 as a reviewed rule-2 transition, or keep rule 1;
- confirm the fidelity table;
- decide whether `BORN_DIGITAL_SIGNED_RANGE_SPANS_FILE` stays primary without cryptographic validation. The recommendation is **yes, provisionally**, with the limitation recorded, until signature validation with trust evidence is available offline.
