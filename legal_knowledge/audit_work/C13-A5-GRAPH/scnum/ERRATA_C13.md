# Errata: SC case-number reconfirmation (C13-A5)

## E1. Anchor page for `sc-2016-union-of-india-and-anr-2016insc173` (review f915ac11, F09)

**What is wrong.** `evidence.anchor_page` is 11. It appears in both:
- `SCNUM_RECONFIRMATION_C13.csv`;
- `SC_CASE_NUMBER_OVERLAY_C13.jsonl`, the overlay published to HF at `844383f5` as `data/meta_overlays/c13_2026-11-25_sc_case_numbers.jsonl`.

The case numbers ("Civil Appeal Diary Nos. 11682 and 10623 of 2015") are printed on **PDF page 12**. Three sources agree: `PAGE_IMAGE_CHECKS_C13.csv`, the independent reviewer, and the page itself.

**Why it happened.** The tool takes the anchor page from the first page whose text layer contains the first staged number. On page 11 that number is matched as text, but not as the case-number block.

**Effect.** The overlay values (`overlay_value`) are correct and unaffected. Only the evidence pointer is off by one page.

**Disposition.**
- The published HF file is not rewritten: originals and published overlays are additive-only.
- The correction will be carried in the next overlay version (C13-v2 or later) if one is issued. Until then, this erratum records it.
- The tool is unchanged, so `--check` still reproduces the published bytes.

## E2. Scope of "printed" (review f915ac11, F07)

The reconfirmation is a **presence check, not a completeness check**.
- **What it confirms:** every staged (number, year) is printed in the cover or jurisdiction-heading text, or on the page image.
- **What it does not confirm:** that every printed number was staged. For example, Union Carbide (1991) prints the lead "Civil Appeal Nos. 3187-88 of 1988", which is not in the staged list.
- **How literal the match is:**
  - the text-layer match applies OCR digit repair (I, l, ! → 1 and O → 0, next to digits);
  - the type-label check is not bound to the number (for example, `CA` accepts any "appeal" on the cover).
