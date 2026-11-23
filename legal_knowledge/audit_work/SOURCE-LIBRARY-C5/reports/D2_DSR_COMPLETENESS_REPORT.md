# D2. Completeness of the Defence Services Regulations and Regulations for the Army

**Short answer:** we hold no complete edition of the Regulations for the Army (RA), in any year. The only official text held is a retyped 5-page India Code extract of the 1987 edition (Chapter V, paras 201–220). No official public copy of the full 1987 book, the 1962 edition, or any amendment or correction slip was found in the places searched. The currency of RA 1987 therefore **cannot be established** (AMENDMENT_CHAIN_INCOMPLETE).

This is a documentary assessment. It decides no legal question and gives no paragraph text. Evidence is in `discovery/A_candidates.csv` (C5A-*), `discovery/A_requests.tsv` and `registers/source_master_register.csv`.

## 1. Edition-by-edition position

| Edition / publication | Existence evidence | Official copy located | Held | Completeness | Status in registers |
| --- | --- | --- | --- | --- | --- |
| **Regulations for the Army, Revised Edition 1987** (full book) | Judicial and Gazette citations of "Regulations for the Army, 1987" (C5A-006 AFT Chandigarh TA 31/2012; C5A-026); a secondary article says RA was "last revised in 1987" with "very few amendments" since (C5A-002) | **NOT_FOUND**. DMA `central_documents` JSON (80 items) lists the Navy and Air Force regulations but not RA (C5A-001). mod.gov.in pages render client-side, and the old file links return 404. | No | Unknown: no copy seen, so volume, chapter and paragraph structure are NOT_DETERMINED | `C5-SRC-P0-RA-1987`: NOT_HELD_NOT_FOUND |
| RA 1987, **Chapter V Reserve Forces, paras 201–220** | India Code item a1465f87… (REGULATION RE_CEN_28_38_00001…) | Yes (India Code) | **Yes**: sha256 `4be12283…`, 5 pp. | **EXTRACT**. Retyped (convertapi 2019), not a facsimile of the printed page. The listed size (310212) differs from the served size (312416). | `C5-SRC-P0-RA-1987-CH5-INDIACODE`: HELD_GOVERNMENT_COMPILATION_EXTRACT |
| **Regulations for the Army, 1962** | Gazette of India Extraordinary 26-01-1987 cites "para 178 of Regulations for the Army, 1962" (C5A-008, archive.org metadata and OCR) | NOT_FOUND (C5A-007) | No | n/a | `C5-SRC-P0-RA-1962`: NOT_HELD_NOT_FOUND |
| "Regulations for the Army **1961**" | **None found.** Repository phrases such as "1961 Reg 173" and "1961 para 125" refer to the *Pension* Regulations for the Army 1961. | n/a | n/a | n/a | Recorded under PRA 1961 |
| "Regulations for the Army **2008**" | **None.** Every occurrence in the repository is a substring of "Pension Regulations for the Army 2008" (WS-D v4, PILOT-01 code registers, WS-B, C4 review A). No external source for an RA 2008 (C5A-003). | n/a | n/a | n/a | `C5-SRC-P0-RA-2008-CLAIM`: closed as an identity non-issue (documentary) |
| **Amendment / correction slips to RA 1987** | None located. Gazettes found only *cite* RA paragraphs (e.g. para 177, honorary commissions). | NOT_FOUND (C5A-005) | No | n/a | `C5-AMD-RA1987-SLIPS`: AMENDMENT_CHAIN_INCOMPLETE |
| **"DSR vol 1 / vol 2"** (Army) on Scribd | third-party uploads (C5A-025) | Not official | No (deliberately) | unknown | NOT_HELD_RESTRICTED_SUSPECTED, **do not acquire** |
| Regulations for the Army in India 1927 | archive.org DLI 548585: 530 pp., Calcutta, GoI Central Publication Branch (C5A-009) | archival facsimile | No | metadata only | historical layer |
| RA in India Part II 1940; c.1930 upload; IOR set 1925–44 (6 vols); Army Regulations, India 1887–1938 | archive.org metadata; UK National Archives / British Library catalogues (C5A-010..013) | facsimile or catalogue | No | metadata only | historical layer |
| Army Instructions (India) / India Army Orders 1911–1933; Release Regulations 1945 | archive.org (C5A-014, C5A-015) | facsimile | No | metadata only | historical layer |

## 2. Related DSR volumes

| Volume | Location | Held | Notes |
| --- | --- | --- | --- |
| Regulations for the Medical Services of the Armed Forces (RMSAF) 2010; 1983 edition | Scribd only (C5A-017); 1983 NOT_FOUND (C5A-018) | No | Needed for medical-board and invalidment procedure (PEN module). Third-party copy not acceptable. |
| Regulations for the Air Force 1964 (Reprint 2000) | dmamod.gov.in, HEAD 200 (C5A-019) | No | Search snippets report a **'For Official Use Only'** marking. The marking must be confirmed before any ingest. |
| Regulations for the Navy Parts I, II, III (1963); INAS Regulations 1973; Navy amendment regulations 2022, 2024 | dmamod.gov.in, HEAD 200 (C5A-020..024) | No | Cross-service comparators only |
| Regulations for the Medical Services (India) 1930 | archive.org DLI 548435 (C5A-016) | No | Historical layer |

## 3. What the knowledge base needs from RA

- **WS-D `SRC-RA` is cited by COI-002, COI-007, COI-029 and COI-046.** COI-002 and COI-046 say "Regulations for the Army" and give no edition, so mapping them to 1987 is an inference (recorded in `inputs/corpus_source_map.csv`).
- **Army Orders and Instructions:** ten records cite them by category only (`SRC-AO`, `AO`). No public official repository of post-1950 Army Orders or Army Instructions was reachable: indianarmy.nic.in was unreachable (C5C-030).
- **Records that may depend on RA without citing it** (honours and awards, discipline administration, honorary commissions) cannot be found by search until the text is held.

## 4. What was not checked (reported as NOT_CHECKED, not as absent)

- The egazette.gov.in search, which failed TLS certificate verification. Verification was not disabled.
- indianarmy.nic.in, which was unreachable.
- The CSL / National Library of India OPAC and WorldCat catalogue records.
- The MoD print-publication catalogue.
- The DESW archive beyond page 3.

## 5. Gaps and how each could be closed

1. **RA 1987 complete text, with its amendment-slip record.** This needs an owner or custodian route (C5-ACQ-12), and the printed access marking must be recorded. Do not use Scribd or other third-party copies.
2. **RA 1962**, for law applicable before 1987 (C5-ACQ-13).
3. **RMSAF 2010 and 1983** (C5-ACQ-14).
4. **The specific Army Orders the records rely on.** The owner should first list the orders and say whether each is publicly published (C5-ACQ-15).
5. **Retry discovery from the crawl machine:** egazette search for "Regulations for the Army", the indianarmy.nic.in publications page, and library catalogues for the 1987 printing (title page, printer, ISBN or job number).
6. **Historical layer:** RA in India 1927 is already pinned in ACQ-01 (PR #8). 1940 Part II and the 1930 Medical Services regulations can be pinned once metadata md5 values are recorded.

**Conclusion for the immediate priority:** the DSR and RA layer is the weakest part of the source base, at 0 of 1 complete current-era editions held. It cannot be closed by crawling the official sites checked so far. It needs a custodian copy and an explicit owner decision on handling any access marking.
