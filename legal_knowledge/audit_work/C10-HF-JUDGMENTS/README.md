# C10-HF-JUDGMENTS: complete audit of the Hugging Face judicial corpus (Cycle 10, mandatory workstream)

**Status:** an automated document-level audit of every judgment in the canonical Hugging Face dataset, with explicit completion accounting.
- **Nothing is legally verified.** Every extracted value (dates, case numbers, citations, statutes, issues, outcome, propositions, relevance) is an automated candidate read from the PDF text layer.
- Independent AI document review (not legal review) covers only the sample recorded in `review/`.
- Original judgment documents are not modified.
- Published judgment text is not masked (owner's judicial publication policy).

## What is enumerated (all four collections; every item has a disposition)
| Collection | Source | Count | Disposition file |
| --- | --- | --- | --- |
| Judgment metadata records | HF `data/meta/*.json` with `doc_type = judgment`. The bytes read are the GitHub `raw-data` copy; counts are identical on HF | 4,259 | `HF_JUDGMENT_METADATA_AUDIT.csv`, `HF_JUDGMENT_MASTER_INVENTORY.csv` |
| Judgment source files | HF `data/raw/sci/**`, `data/raw/hc/**` (3,951), plus the curated HF `legal_knowledge` judgment binaries (8) | 3,959 distinct files | `HF_JUDGMENT_COPY_REGISTER.csv`, master inventory |
| Excluded judgments | HF `data/excluded_judgments.jsonl` (crawler log; files not retained) | 120,185 | `HF_JUDGMENT_EXCLUDED_DISPOSITIONS.csv.gz` |
| Unprocessed remainder | — | see `CONTINUATION_MANIFEST.csv` | exact list with the reason and what is needed |

"About 3,413 judgment records" was a historical figure. It is superseded by the counts recomputed here.

## How to run (deterministic, resumable)
```
MIMAMSA_WORKING_STORE=<dir holding downloads/> python -I -B tools/audit_judgments.py extract  --repo <full clone> [--workers 4]
python -I -B tools/audit_judgments.py assemble --repo <full clone> [--check]
```
- `extract` processes distinct files in deterministic batches of 200, sorted by SHA-256.
- Each batch is written to `work/batches/batch_NNNN.jsonl` together with its input key and extractor version. The input key covers the batch's SHA-256 list and a fingerprint of the extractor source, so a batch made by different code is never reused. A complete matching batch is skipped, so an interrupted run resumes where it stopped.
- **Truncated copies.** A copy with no `%%EOF` marker anywhere is truncated. If it still opens it is `PROCESSED_TRUNCATED_COPY` (content may be missing): possibly partial extraction, marked in every research output, counted as unresolved, and listed for a complete copy. If it does not open it is `INCOMPLETE_COPY_TRUNCATED`.
- `assemble` builds every output from the batches and the pinned inputs, asserts the accounting identities, and writes the continuation manifest.

**Byte source.**
- **Store files:** the GitHub `raw-data` object at `ad77758d`. Its re-hash must equal the SHA-256 that HF's own `SHA256SUMS` declares.
- **Curated HF-only binaries:** an identical-SHA working copy where one is held; otherwise `NOT_PROCESSED_BYTES_UNAVAILABLE`.
- **HF-hosted bytes:** never downloaded (no access); recorded as `NOT_CHECKED`. The HF revision is unpinned.

## Outputs (`outputs/`)
| File | Content |
| --- | --- |
| `HF_JUDGMENT_MASTER_INVENTORY.csv` | every file and record, with its disposition, plus the excluded-log reference |
| `HF_JUDGMENT_COPY_REGISTER.csv` | per distinct file: SHA-256, location, byte source, verification, pages, text-layer status, C5 register link |
| `HF_JUDGMENT_METADATA_AUDIT.csv` | per record: case number, decision date and neutral citation checked against the text; missing metadata; contradictions |
| `HF_JUDGMENT_RELEVANCE.csv` | per judgment: one of five relevance classes, with the rule and term counts |
| `HF_JUDGMENT_LEGAL_ISSUES.jsonl` | statutes (with provisions), issue topics, citations |
| `HF_JUDGMENT_HOLDINGS.jsonl` | outcome phrase (page and evidence), up to six candidate propositions with page and paragraph |
| `HF_JUDGMENT_DUPLICATES.csv` | common judgments (one file, many records), same case number in different files, same neutral citation in different files, correction markers |
| `HF_JUDGMENT_RELATIONSHIPS.csv` | judgment-to-judgment citations resolved through metadata citations; deterministic matches to the 53 curated cases |
| `HF_JUDGMENT_VERIFICATION_QUEUE.csv` | every judgment ranked by risk and impact, for human or legal review |
| `HF_JUDGMENT_AUDIT_SUMMARY.md` | counts, accounting identities, and three separate coverage measures (automated processing, source-document verification, independent legal review) |
| `HF_JUDGMENT_EXCLUDED_DISPOSITIONS.csv.gz` | the 120,185 excluded records, each with a disposition; titles re-screened for military or service terms |
| `CONTINUATION_MANIFEST.csv`, `BATCH_STATUS.csv`, `AUDIT_MANIFEST.json` | remaining work, batch checkpoints, hashes |

## Method notes and limits
- **Decision date.** Only explicit decision labels (pronounced, decided, date of decision or judgment, order date) and the signature-block date count as decision evidence. Plain "dated …" references to earlier orders are excluded. A record is reported `DIFFERS` only when such evidence exists and disagrees with the metadata.
- **Case number.** A metadata number missing from the case numbers read from the opening text is `NOT_CONFIRMED_IN_TEXT`, not a contradiction, because long cause lists and unusual formats limit extraction.
- **Relevance.** Fixed term rules. The crawler removed 120,185 judgments for lacking military keywords and did not keep their files. Their titles were re-screened, and re-screening their text for general-law relevance needs re-acquisition, which is not authorised here.
- **Outcome and propositions.** These are phrase-based candidates. Conflicting outcome phrases, and any disagreement with the crawler outcome, are flagged for review. Measured reliability is low (see the summary); prefer the crawler metadata.
