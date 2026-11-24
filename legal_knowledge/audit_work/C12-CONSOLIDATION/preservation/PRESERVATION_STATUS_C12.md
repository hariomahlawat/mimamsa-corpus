# Cycle 12 preservation status: the 48 working-store-only copies

| Step | Result |
| --- | --- |
| Availability and SHA-256 reconfirmed (2026-11-24T10:17Z, `C11 preservation_c11.py --check`) | 48 of 48 present and equal to the register |
| Text-layer marking scan (C11) | No restriction marking on text pages |
| **Visual inspection of the 73 text-less pages** (`VISUAL_MARKING_INSPECTION.csv`) | **No restriction or access marking on any page.** The pages are Hindi halves of bilingual Gazettes, blank pages, a 2003 Extraordinary Gazette, a Rajya Sabha extract, and the Entitlement Rules 2023 scan with annexures. Faint edge text re-rendered at 250 dpi: copying artefacts. **Limit:** a marking too faint to see at 110 dpi, or cut off by the scan, cannot be ruled out. |
| Staging package | `C11 preservation/stage_and_verify.sh` stages 48 byte-identical copies with sidecars and verifies them (tested in C11 and C12) |
| **Persistent destination** | **BLOCKED.** I proposed preserving the copies on a dedicated orphan branch of this private, access-controlled repository, which already holds source PDFs on `raw-data`. The session's permission control denied the push as sensitive-information leakage, and it was not attempted another way. |
| Hugging Face | Not used: no write credential, and an upload needs owner approval |

**Still at risk.** The copies exist only in the session scratchpad, which is temporary. They include the 1954 Army Rules Gazette `c5ef95a9`, which supports all 42 Army Rules anchors (47 anchor rows across six copies).

**Owner action (any one of these):**
1. Permit the orphan-branch push, `claude/c12-preservation-c5`, in this private repository.
2. Run `stage_and_verify.sh` and upload the result to the private Hugging Face dataset.
3. Name another approved store.

After any of these, run `sha256sum -c` on a fresh download of the stored copies to confirm the bytes survived.

## Update 2026-11-24: owner-approved preservation run

**Approval.** The owner approved preserving the 48 copies to the private HF dataset `hariomahlawat/mimamsa-corpus` at `legal_knowledge/preservation/c5_working_store/`.

| Step | Result |
| --- | --- |
| 1. Reconfirm | 48 of 48 present. SHA-256 and byte size match the register (2026-11-24T11:57:47Z). |
| 2. `stage_and_verify.sh` | "staged and verified"; "OK: 48 staged copies equal the manifest". Original filenames kept; one sidecar per copy. |
| 3. ZIP package | `mimamsa_c5_working_store_preservation_c12.zip`. The 48 PDFs are stored uncompressed, byte for byte. It also contains 48 sidecars, `STAGED_SHA256SUMS`, `_provenance/` (inventory, manifest, marking scans, visual inspection, package notes, script), a README, and `PACKAGE_SHA256SUMS` (106 entries; copy: `PACKAGE_SHA256SUMS_C12.txt`). ZIP SHA-256 `214f11e8713ec44d095fb29459d45cb336fdaf737afc40cfc7f99af93e8dcd62`, 37,396,714 bytes. |
| Restoration test | ZIP extracted into a fresh directory. `sha256sum -c PACKAGE_SHA256SUMS`: 0 failures. The restored PDF hash set equals `SOURCE_MANIFEST.sha256` (48 of 48). |
| 4. HF upload | **Not possible from this session.** No HF write credential is injected into the environment, and no `hf` CLI is present. The HF connector is authenticated as the owner, but it offers read-only operations (`ls`, `cat`, `stat`, `find`, `search`) and no write tool. The upload was not attempted any other way. |
| 5. Byte verification of the upload | Pending the upload. |
| 6. Fallback | The ZIP and its `.sha256` were delivered to the owner as a downloadable artefact for transfer. |
| 7. Exclusions | None needed among the 48: no restricted or FOUO marking was found by the text scan or the visual inspection, within the faint-marking limit already noted. The separately identified FOUO copy (RAF 2000, `4284820e…`) is not among the 48 and is not in the package. |
| 8. Temporary copies | **Not deleted.** The working store and the staged directory both remain in the session scratchpad. |

**Owner steps to finish.**
1. Upload the extracted `c5_working_store/` folder to the dataset path `legal_knowledge/preservation/c5_working_store/`, for example:

       hf upload hariomahlawat/mimamsa-corpus c5_working_store legal_knowledge/preservation/c5_working_store --repo-type dataset

2. Do not use the commit message token `[abbreviations-hf]`, and do not trigger the sync workflow.
3. Re-download into a fresh directory and run:

       sha256sum -c PACKAGE_SHA256SUMS

   A session with a read credential can also verify the upload, revision-pinned.

Release of the temporary copies waits for that verification.
