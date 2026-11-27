# Cycle 15 review supplement

The supplement adds 52 distinct contextual assessments to the 48 baseline assessments and leaves the baseline JSONL unchanged. The baseline's separate extraction quarantine is excluded from the quotas.

| Category | Baseline | Supplement | Total |
|---|---:|---:|---:|
| Military disciplinary proceedings and courts-martial | 3 | 17 | 20 |
| Service conditions, promotion and administrative action | 10 | 10 | 20 |
| Disability and service pensions | 9 | 11 | 20 |
| AFT jurisdiction and procedure | 20 | 0 | 20 |
| Constitutional and statutory interpretation | 6 | 14 | 20 |
| **Total** | **48** | **52** | **100** |

The 52 additional assessments comprise 44 regional tribunal decisions whose official PDF and local derivative were rehashed, and eight High Court decisions drawn from the verified package-v5 SQLite. The supplement includes separate orders on related proceedings only where the document identity and contextual grounds or directions can be assessed. In the interpretation category, decisions include construction of legislation, service regulations, notices, and public law limits on actions by military-associated bodies. The AFT-GUW-426 interpretation arises in a bail order. The AFT-GUW-1036 tribunal construed the 2022 policy and recorded that the pleading did not seek a ruling on constitutionality.

The supplemental build checks for duplicate document IDs and source digests, binds selected markers to unique substrings, and reopens the output to verify every page digest and exact character span. For official local pairs, it recomputes both hashes and checks the physical page count and journal source identity. The JSONL retains which records have an HF revision and which use official-local pair provenance. No Hugging Face publication or application import is part of the review.

This is a scoped contextual review of selected findings. Independent original-page review for all claims, complete legal treatment research, statutory version validation, and approval for application use are pending. All authority remains unreviewed. The targeted baseline retrieval probes exercised package-v5's search implementation. The local-pair supplement uses exact source replay, and a search release containing it remains unverified.

Reproduce the supplemental artifact and receipt from this directory with `python build_supplement.py`. Inspect `supplement-assessments.txt` for the human-selected text and `context-reviews-supplement.jsonl` for the resolved page anchors. Use `supplement-qa.json` for the immutable baseline digest, supplement digest, category counts and total checks.
