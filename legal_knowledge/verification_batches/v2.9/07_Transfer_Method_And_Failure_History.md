# Judgments source acquisition outcome (22 November 2026)

## Direct official JUDIS attempt
Legacy `api.sci.gov.in/jonew/judis/9884.pdf` returned a non-PDF payload to the authenticated GitHub Actions runner even though it is visible in an external browser/search context. The direct archive task correctly rejected it; no invalid file was committed. The older JUDIS 8566 PDF was not reached during that all-or-nothing task.

## Canonical-corpus source reuse
The existing *private Mimamsa* crawled source collection already contained a Supreme Court Reports PDF for each decision. Both original corpus PDFs were downloaded from Hugging Face, checked byte-for-byte against their `data/raw_manifest.csv` SHA-256 values, and their extractable text was checked for the specific case title and year. The procedure **did not** establish a byte-identical match with the official JUDIS URL; this limitation is preserved.

- [Verified identity crosswalk](https://huggingface.co/datasets/hariomahlawat/mimamsa-corpus/blob/main/legal_knowledge/crosswalk/v2.9/01_Original_Source_Matches.csv)
- [Workflow receipt](https://github.com/hariomahlawat/mimamsa-corpus/actions/runs/45000152998)

Neither source is designated `legal_holding_verified`, `subsequent_treatment_verified`, nor JAG approved. No source binaries were duplicated or overwritten.
