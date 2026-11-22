# Uploaded Manual of Military Law sources

The user authorised keeping all eight supplied MML documents in the **private** Mimamsa dataset. The original binaries must be preserved byte-for-byte under `legal_knowledge/manual_sources/originals/`.

The accompanying manifest gives the SHA-256 digest of each upload; no law/version authenticity or accuracy is implied. Format overlap and suspected transcription defects must be separately reconciled. Some material may contain access markings: check redistribution restrictions before release, even from private storage.

**Current upload status:** Manifest staged on private GitHub; original eight binaries are not in this GitHub branch or the Hugging Face dataset through this operation. The local source package `Mimamsa_MML_Original_Sources_2026-11-22.zip` carries the originals.

For an authorised workstation, extract that package and run the dedicated upload script `scripts/push_mml_originals.py --source-dir <EXTRACTED_FOLDER>/originals` after `hf auth login` with a dataset-write credential. The script checks source digests and restricts uploads to the private named dataset. It doesn't run the main `push_hf.py` checkpoint, and never modifies crawler-derived `data/` files.

All materials remain unverified and are not JAG-approved.
