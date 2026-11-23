# STATUTORY_C10_FINDINGS: Cycle 10 workstream B (statutory and regulatory sources)

**Scope:** database and legal-source research only. Nothing here changes a register, the AUTH-LEDGER (still at version 0), or any legal status. No download was made and no network was used. Hugging Face holdings come only from the C10 capture listings, whose bytes are NOT_CHECKED.

**Readings:** every page reading made in this workstream is an AI agent reading, not human-confirmed. Each one is listed in `readings_c10.csv` with its page number. For rendered pages the file also gives the render SHA-256 prefix, which the builder re-verifies; that hash depends on PyMuPDF 1.2x at the stated dpi.

**Dates:** no commencement date is inferred from a publication date or a printer's date.

**Rebuild:**

```
python3 -I -B tools/build_statutory_c10.py [--check]
```

The builder runs with the scratchpad venv's Python, which has PyMuPDF. It reads these pinned inputs:
- `raw-data` at `ad77758d`;
- the registers at `21e73b83`;
- the C9 PR #41 files at `cfc52d57`;
- five C10 output files and the HF legal_knowledge listing, each checked against its SHA-256.

`--check` regenerated all 9 files identically.

## 1. Primary-source status (`primary_source_status_c10.csv`, 66 rows)

| Status | Rows |
| --- | --- |
| HELD_AUTHENTICATED | 0 (impossible at AUTH-LEDGER version 0; the builder enforces this) |
| HELD_UNREGISTERED | 13 |
| HELD_PROVENANCE_UNCERTAIN | 8 |
| HELD_SECONDARY_COMPILATION_ONLY | 13 |
| HELD_INCOMPLETE | 7 |
| AVAILABLE_OTHER_REPOSITORY | 0 |
| LOCATED_NOT_ACQUIRED | 14 |
| NOT_FOUND_AFTER_DOCUMENTED_SEARCH | 11 |
| PRESERVATION_RISK flag (every held copy is in the working store only) | 9 rows |

The 9 PRESERVATION_RISK rows are:
- the Army Rules 1954 Gazette;
- the 24 Army Rules amendment Gazettes (one row);
- Act 19/1955;
- Act 13/1975;
- Act 37/1992 (all three copies);
- ER 2023;
- the Regulations for the Army 1987, Chapter V extract;
- the Delhi High Court Rules, Chapter 6;
- the Rajya Sabha 1987 record.

**How the rows are split:** the major Acts have separate rows for the as-enacted (Gazette) layer and the consolidated layer, because their status differs between the two. Each row lists:
- the full SHA-256 of every held copy;
- where each copy is held, and its register state;
- the copy evidence class in the C5 register;
- related copies of other layers;
- C5 and C9 references.

LOCATED and NOT_FOUND rows also carry a deterministic search: one regex run over all 4,103 inventory titles, the first-two-page text of all 88 India Code and official-copy raw files, and the HF legal_knowledge paths. Every hit was inspected. The hits are footnotes in India Code JSON listings, entries in amending-Act lists, or the held S.R.O. 14(E)/2009 references. None is a copy of the instrument sought.

**Builder checks:**
- A non-HELD status cannot list held copies.
- HELD_UNREGISTERED is refused if any copy is registered or held only in the working store.
- HELD_AUTHENTICATED is refused while the ledger is at version 0.

**Vocabulary gap (stated, not resolved):** no allowed state means "registered, documented provenance, not authenticated". The Army Rules 1954 Gazette, the Act 37/1992 Gazette scan and three amendment Gazettes are DOCUMENTED_PRIMARY_COPY in C5. They are labelled HELD_PROVENANCE_UNCERTAIN only because no authentication record exists. The `held_copy_evidence_class` column keeps the C5 class.

### Corrections to register "not held" statements (copies exist in HF and GitHub)

| C5 source (C5 holding_state) | Held copy | C10 status |
| --- | --- | --- |
| C5-SRC-P0-AFT-ACT-2007 (NOT_HELD_CANDIDATE_LOCATED) | `338d43ad…`: Gazette Extraordinary Part II s.1 No. 66, 28-12-2007. The crawl filed it as category "rule" | HELD_UNREGISTERED |
| C5-SRC-P1-AFT-PROC-RULES (NOT_HELD_NOT_CHECKED; 46 crosswalk rows MISSING_EVIDENCE) | `590cf7cd…`, `fc27032f…`; `c57b113a…` (no masthead) | HELD_UNREGISTERED / HELD_INCOMPLETE |
| C5-SRC-P1-IPC-CRPC-IEA (NOT_HELD_NOT_CHECKED) | `fa8878e0…`, `865cc3e1…`, `982059ca…`, `06729a1f…` | HELD_SECONDARY_COMPILATION_ONLY |
| C5-SRC-P1-DPP-ACT-1950 (NOT_HELD) | `0884f3b5…`, `6ca297a1…`; Rules 1953 `d969593b…` | compilation / HELD_UNREGISTERED |
| C5-SRC-P2-RAF-1964 (NOT_HELD) | `4284820e…`: Regulations for the Air Force, Reprinted Edition 2000. **Prints "For Official Use Only" on p.1** | HELD_UNREGISTERED; access decision needed |
| C5-SRC-P2-RNAVY-PT1/PT2/PT3, C5-SRC-P2-INAS-1973 (NOT_HELD) | `68dd1cea…`, `884a893c…`, `272e4c22…`, `e4148ee0…` (Part IV is the INAS Regulations 1973) | HELD_UNREGISTERED |
| C5-SRC-P2-PEN-REGS-AF-NAVY (NOT_HELD) | `f9e11e04…`: Navy (Pension) Regulations 1964. The Air Force part is not held | HELD_UNREGISTERED |
| C5-SRC-P1-BNS-2023, P0-BNSS-2023, P0-BSA-2023 (NOT_HELD; C9 also NOT_HELD) | `d163e785…`, `60d145c5…`, `72fc9a75…` | HELD_INCOMPLETE |

**New finding on the three Sanhitas:** the Hindi files are Hindi-language texts in Gazette Extraordinary Section 1A pagination (BNS pp.9-153; BNSS pp.155-473; BSA pp.475-535), with an India Code watermark. The masthead, issue number and issue date are absent from every held page (C10R-BNS/BNSS/BSA-H-01/02).
- The BSA file ends with the Secretary's signature and a Government of India Press imprint "MGIPMRND—793GI(S3)—27-03-2024". That is a printer's date, not a publication date.
- The BNS and BNSS files end without a signature or imprint.
- None of the three is the English Gazette that the C5 sources name. The English Gazettes stay pinned and not acquired.

C9 named the AFT Gazette and the AFT rules. The table above adds the Sanhita Hindi Gazette texts, the cross-service regulations, the second S.R.O. 9(E)/2009 copy, and the 13 AFT bench notifications.

## 2. Registration proposals and AP-C9-02 (`registration_proposals_c10.csv`)

All 60 held, unregistered statutory copies in HF and GitHub have a proposal row. Each row gives:
- identity, issuing authority and completeness;
- fidelity class: Gazette facsimile, Gazette extract without masthead, text rendition, government compilation, compiler note, or secondary reference;
- source_url and retrieved_at from raw_manifest, and HF byte status (NOT_CHECKED);
- equivalence groups, the target C5 source and its holding_state;
- the crosswalk rows for that target;
- a proposed classification and the verification still needed.

The 7 registered compilations named in AP-C9-02 and the 21 India Code `linked_records` JSON listings are also listed. Nothing is activated.

**How AP-C9-02 should change.** C9 scoped it as "15 raw-store documents + 7 held compilations".

1. **Keep the 15 raw-store copies:**
   - AFT Gazette `338d43ad`;
   - AFT rules `590cf7cd`, `fc27032f`, `c57b113a`;
   - AFT order and notification `1c6db257`, `8d774f1f`;
   - Finance Act 2017 `7a5551ba` and TRA 2021 `0c2f4e9e`;
   - BNS compilation `d4449e99` and DPP Act `0884f3b5`;
   - IPC `fa8878e0`, IEA `06729a1f`, CrPC `865cc3e1`;
   - Air Force Act `ef50375e` and Navy Act `db6d2b3e`.

   Correct `338d43ad`'s crawl category from "rule" to "act" (conflict IC-CATEGORY-338d43addeaa). Record `c57b113a` as incomplete (no masthead).
2. **Restate the 7 compilations** (`e47a4265`, `48f52219`, `665863d1`, `48f57c81`, `572c7988`, `554b2b4a`, `be619533`). They are already registered, so for them the package is the attachment of a retrieval record to the existing copy rows. It is not registration, and it changes no class without an owner decision under rule 1.
3. **Add 32 copies:**
   - the second S.R.O. 9(E)/2009 copy `03961b02`;
   - the 13 AFT bench and jurisdiction notifications;
   - the three Hindi Sanhita Gazette texts `d163e785`, `60d145c5`, `72fc9a75`, each as a new Hindi-text source row and not as the English Gazette;
   - CrPC consolidated `982059ca`;
   - the Hindi compilations of the Army Act, Air Force Act, Navy Act and DPP Act;
   - the BNSS and BSA Schedule files and the Army Act Schedule note `3a551c1f` (components only);
   - DPP Rules 1953 `d969593b`;
   - Regulations for the Navy Parts I-IV and the Navy (Pension) Regulations 1964.
4. **Add later or differently:**
   - `4284820e` (RAF 2000) only after an access-marking decision, because it prints FOUO;
   - the 3 CAPT Bhopal correspondence tables as secondary references only;
   - the 9 AFT administrative and recruitment rules as optional, low priority.
5. **Exclude the 21 `linked_records` JSON files.** They are discovery metadata, not source copies.
6. **Evidence basis:** registration should cite the GitHub-rehashed bytes, with the HF path recorded as the preservation location. HF byte integrity is NOT_CHECKED.
7. **Preservation is separate.** It is not part of AP-C9-02 (section 5).

## 3. Recomputed amendment graph (`amendment_graph_c10.csv`, 116 edges)

The file keeps the C9 columns and adds `c10_status`, `c10_change` and `evidence`.

| Status | C9 | C10 |
| --- | --- | --- |
| EVIDENCED | 17 | 17 |
| UNRESOLVED_COMMENCEMENT | 41 | **43** |
| NOT_LOCATED | 43 | **41** |
| DISPUTED_PRESERVE_BOTH | 15 | 15 |

**Status changes (2):**
- **C9-AG-BNSS-REPEAL:** NOT_LOCATED → UNRESOLVED_COMMENCEMENT. The repealing instrument (BNSS s.531) is held in HF and GitHub: the registered compilation `572c7988` (p.174) and the Hindi Gazette text `60d145c5`. C9 kept the C8 matrix's NOT_LOCATED, yet classed the parallel BNS repeal edge UNRESOLVED_COMMENCEMENT on a compilation copy. S.O. 848(E) is not held, so commencement is not evidenced.
- **C9-AG-BSA-REPEAL:** NOT_LOCATED → UNRESOLVED_COMMENCEMENT, for the same reason. The held copies are `554b2b4a` (p.51) and `72fc9a75`. S.O. 849(E) is not held.

**Evidence added, status unchanged (6):**
- **C9-AG-AFT-00:** the held S.R.O. 02(E)/2015 refers to an "S.R.O. 14(E), dated 21st October, 2009" (bench jurisdiction). That number collides with S.O. 14(E) of 13-06-2008 but is a different instrument.
- **C9-AG-AA-C3-03:** the India Code Schedule note `3a551c1f` says the Schedule was repealed by RAA 1957. This is a compiler statement.
- **C9-AG-AFTSRO9E2009:** a second copy, `03961b02`.
- **C9-AG-BNS-COMM, BNSS-COMM, BSA-COMM:** the Hindi Gazette texts carry the Acts, not the notifications.

Every other NOT_LOCATED edge carries its search regex and hit counts. No other NOT_LOCATED amending instrument or commencement notification is held in HF, GitHub or the working store.

**Preserved readings and escalation status (`escalation_matters_c10.csv`):**

| Matter | Escalation status |
| --- | --- |
| r.23(3) caution wording | ESCALATED_TO_LEGAL_ADVISER |
| Unsupported "r.23 amended 2022" | OPEN_UNSUPPORTED |
| r.168(2) | OWNER_TO_REGISTER_CONFLICT, then legal adviser |
| S.R.O. 34/1963 | OWNER_DISCOVERY_APPROVAL_PENDING |
| S.O. 4010/1986 | OWNER_ACQUISITION_EXECUTION_PENDING (PR #8) |
| Act 37/1992 commencement | ESCALATED_TO_LEGAL_ADVISER (AQ-05) |
| AFT commencement vs establishment | OWNER_DISCOVERY_APPROVAL_PENDING, then legal adviser |
| AFT procedural rules | OWNER_REGISTRATION_DECISION_PENDING |
| TRA 2026 commencement | OWNER_DISCOVERY_APPROVAL_PENDING |

Both readings of every matter are recorded verbatim. None is resolved.

## 4. Acquisition priorities (`acquisition_priority_c10.csv`)

**Scoring:**

```
score = 3*legal_consequence + 2*records_level + 2*source_quality_gap
        + no_alternative + 2*amend_commencement + readiness - access_penalty
```

The factor values are explicit for each item. Commencement notifications use the upper bound of dependent records, and the file says so. File counts are not used.

**Top 10:**
1. Post-06-06-2022 Army Rules S.R.O.s (10 pinned candidates).
2. S.O. 850/848/849(E) of 2024, the Sanhita commencement notifications.
3. S.R.O. 120/1950, the Army Act commencement (candidate in PR #23).
4. The Army Act 1950 Gazette as enacted.
5. S.O. 14(E)/2008, the AFT commencement (needs discovery).
6. Pension Regulations for the Army 2008, Parts I and II (blocked by robots).
7. CCCM Rules 1978 and S.O. 4010/1986 (within authorised scope; the most ready to execute).
8. The 1960 S.R.O.s 331/348/351/404 and S.R.O. 22/2010.
9. ER 2008 and the PRA/ER circulars.
10. The TRA 2026 commencement notification(s).

**Effect of C10 on two items:** the English Sanhita Gazettes drop to rank 12, because Hindi Gazette texts are now known to be held. The AFT Act and AFT rules are no longer acquisition items, because they are held; they need registration only.

## 5. Preservation: owner action list (`preservation_owner_actions_c10.csv`)

These are the 48 registered copies that exist only in the ephemeral working store. Upload is **not authorised to agents**. The list is in priority order:
1. `c5ef95a9…`, the Army Rules 1954 Gazette, on which all 42 exact anchors rest.
2. The 5 judgment copies that each carry one exact anchor.
3. The statutory copies: 24 Army Rules amendment Gazettes, Act 37/1992 ×3, Acts 19/1955 and 13/1975, ER 2023, the RA 1987 Chapter V extract, the DHC Rules and the Rajya Sabha record.
4. The remaining judgment copies.

For each copy, the owner should:
1. copy the file out of the working store;
2. confirm its SHA-256;
3. upload it to the canonical HF dataset at a path the owner chooses;
4. record a receipt with the HF revision and a read-back hash;
5. commit the receipt.

## 6. Limitations

- **Hugging Face:** HF bytes were not downloaded or hashed, and the HF revision is not pinned. "HELD in HF" means the path and size are listed and agree with the GitHub bytes, which were re-hashed.
- **Readings:** all of them are by an AI agent. The Hindi Sanhita identifications rest on rendered page images of the first and last pages only; the intervening pages were not checked for completeness. A Hindi-reading human should confirm them.
- **Search scope:** the page-text search covered the first two pages of each India Code and official-copy file. JSON listings were searched in full. Judgments were not searched, because they are not statutory copies.
- **NOT_FOUND rows:** these describe what was searched and are not proof that a document does not exist. For ST-AA-NOTIFS and ST-ISO-2023 no external discovery has ever been done; the row says so.
- **Builder dependencies:** the render hashes depend on the PyMuPDF version. The builder pins the C10 outputs by SHA-256, and other workstreams are adding files to that folder; if a pinned file changes, `--check` fails rather than silently rebasing.
- **Repository state:** C9's PR #41 files were read at `cfc52d57` from the local repository. They are identical to the C9 worktree copies.
