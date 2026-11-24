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
