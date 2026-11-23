# Corpus authority matrix (Cycle 10; proposal, not adopted)

**Status:** an analytical model for owner decision.
- It changes no register, ledger rule or legal status.
- Rule version 1 and AUTH-LEDGER version 0 stay in force.
- Authority is assigned by documented provenance and source characteristics, **never by storage location**. The same bytes in Hugging Face, GitHub or a working store carry the same evidential weight; only their preservation differs.

## 1. Repository roles (as documented)
| Store | Documented role | What this audit could verify | Authority effect |
| --- | --- | --- | --- |
| Hugging Face `datasets/hariomahlawat/mimamsa-corpus` (private) | **Primary canonical data store** (`legal_knowledge/DATA_AUTHORITY.md`). Production snapshots go here | Paths and sizes of all `data/raw` files, `legal_knowledge/`, `schema/`, `reports/`; counts for `data/meta`, `data/text`, `data/sections`. **Bytes NOT_CHECKED**; revision not pinnable with the access available | Canonical for **preservation**: where a copy should live. Not a source of legal authority |
| GitHub `raw-data` @ `ad77758d` | Size-limited backup of crawler products | Every one of 4,039 raw files re-hashed and equal to `data/SHA256SUMS`; same paths and sizes as Hugging Face | Byte-verifiable mirror of the Hugging Face `data/raw` set |
| GitHub staging (`legal-knowledge/v2.5-staging`) | Code, schemas, audit work, registers | Registers read at `21e73b83` | Holds the **records about** sources, not the sources |
| C5 working store (`downloads/`, `mml_x/` in an agent scratchpad) | Research working copies, re-hashed in C5 | 67 distinct registered copies. **48 exist nowhere else**, including the 1954 Army Rules Gazette that all 42 exact anchors rest on | **Preservation risk.** Evidential weight unchanged, but the bytes are not in a durable store |

## 2. Twelve layers kept distinct
| # | Layer | What it is | Example | Never treated as |
| --- | --- | --- | --- | --- |
| 1 | Original source document | The instrument or judgment as issued by its authority | The Gazette of India issue of 27-11-1954 carrying S.R.O. 484 | Any held file (we hold copies, never the original) |
| 2 | Held document copy | Specific bytes, identified by SHA-256 | `c5ef95a9…` (archival facsimile of that Gazette) | The document itself; a hash proves identity of bytes only |
| 3 | Retrieved file | A copy plus its retrieval record (URL, time, tool) | `raw_manifest.csv` row: source_url, retrieved_at | Proof of authorship or currency |
| 4 | Source metadata | Descriptive fields about a document | `data/meta/<doc_id>.json`, C5 master register | Evidence of content |
| 5 | Extracted text | Text-layer or OCR output | `data/text/*.txt`, `full_text_working/` | Quotable law where it differs from the page image; OCR text is never authoritative |
| 6 | Normalised statutory provision | A section split from a compilation | `data/sections/act-army-1950/*` | The enacted text; a compilation does not reproduce amendment history by itself |
| 7 | Historical provision version | The text in force for an interval, with its amending instrument | the C9 amendment graph's EVIDENCED intervals | Current law unless the chain is complete to date |
| 8 | Judicial rendition | A carrier of a judgment: signed PDF, court-system text rendition (JUDIS), law report (SCR), mirror | Ranjit Thakur JUDIS rendition; Tarsem SCR-format copy | The signed judgment, without fidelity evidence |
| 9 | Curated research record | A KB statement or case record | `records_658.jsonl`, `cases_53.jsonl` (protected) | Primary authority |
| 10 | Citation and cross-reference | A link from a record to a source or provision | `corpus_crosswalk.csv` | Proof that the source supports the statement, unless anchored |
| 11 | Authentication evidence | Identity, provenance and fidelity evidence for a copy, and ledger entries | C8 page checks; AUTH-LEDGER (version 0: none active) | Legal validation |
| 12 | Legal review determination | A qualified adviser's or JAG decision on status or applicability | none recorded | Anything an AI agent produced |

## 3. Evidence hierarchy by source type (highest first; a lower tier never overrides a higher one on content)
**Acts of Parliament**
1. Gazette of India Extraordinary as enacted: archival facsimile, or born-digital with an integrity-valid signature.
2. Official Government compilations such as India Code: useful for current consolidated text, but not proof of amendment history or commencement.
3. Government text renderings.
4. Secondary compilations and commentaries.

Commencement is evidenced by the instrument's own commencement provision (which may state that it commences on publication) or by the commencement notification it requires. A publication date is never assumed to be the commencement date. This is an evidence rule for this corpus, not a statement of law (review RC-03).

**Rules, orders and notifications (S.R.O. and S.O.)**
1. The Gazette issue carrying the instrument.
2. The official compilation's footnotes, which are only a pointer to the amending instrument.
3. Government notes listing amendments, which are leads only. The S.R.O. 34/1963 date conflict shows why.

**Supreme Court judgments**
1. The signed judgment from the court's own portal: the `api.sci.gov.in` judgment PDF.
2. The corrected or reportable version, where the court issues one. Record which version a pinpoint uses (Mullikote has two versions in one file).
3. A court-system text rendition (JUDIS). Good evidence of identity; headnotes and editorial matter are not judgment text (P-D3 option (c)).
4. Open-data bulk copies of court judgments, such as the AWS S3 buckets that supplied all 346 `data/raw/sci` and 3,605 `data/raw/hc` files. Provenance of the copy is documented, but the copy is not court-hosted or certified (review RC-03).
5. Law-report renditions (SCR and others). A comparator only, after its own identity and provenance are recorded; it is never treated as a signed original.
6. Third-party mirrors. They establish identity at most.

**High Court and AFT judgments**
1. The court's own portal copy.
2. Open-data bulk copies of court judgments (the AWS buckets in `raw_manifest`). Provenance is documented, but these are not court-certified.
3. Mirrors.

**Manuals (MML)**
- Owner-supplied originals: SHA-256 preserved, edition and access marking not yet assessed.
- **Never current law.** They are commentary that needs the underlying statute.

**Generated layers** (extracted text, sections, AI summaries, AI page readings)
- These support review only. They never outrank the page image of the held copy, and an AI reading is never human confirmation.

## 4. Rules derived from the reconciliation
1. **Register before acquiring.** Before any acquisition is proposed, check the unified inventory. 4,036 held copies are unregistered, nearly all of them crawler judgments.
2. **Preserve before relying.** A registered copy that exists only in a working store should be placed in the canonical dataset by the owner before any ledger entry relies on it. This covers 48 copies.
3. **Byte identity does not upgrade anything.** A copy found in Hugging Face, or matching a GitHub file, gains no authentication, currency or applicability from that fact.
4. **Hugging Face byte verification is outstanding.** A read-only token, or an owner-run `sha256sum -c data/SHA256SUMS` on a full download, would turn `HF_PATH_SIZE_MATCH_DECLARED` into a byte-level result. Until then it stays `NOT_CHECKED`.
