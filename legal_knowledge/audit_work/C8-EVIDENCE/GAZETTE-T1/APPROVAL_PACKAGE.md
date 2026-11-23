# Package 1: Gazette tranche 1 — approval-ready evidence (NOT approved, NOT active)

Built by `../tools/build_packages.py` from `eligibility_recommendations.csv`, `page_image_checks_c8.csv` and the evidence files. Page readings are AI-agent readings with render hashes (not human-confirmed). Synthetic approvals were used only in temporary simulation directories. No owner decision exists; the per-candidate files in `approval_package/` are UNSIGNED templates.

| Candidate | sha256 | Recommendation | C8 checks | Evidence |
| --- | --- | --- | --- | --- |
| T1-01 | `b76bf4aac230` | READY_FOR_OWNER_CONSIDERATION | C8-PIC-01(CONFIRMED) | `evidence/T1-01.md` |
| T1-02 | `4acdb1a8bc64` | READY_FOR_OWNER_CONSIDERATION | C8-PIC-02(CONFIRMED), C8-PIC-03(CONFIRMED) | `evidence/T1-02.md` |
| T1-03 | `cce0d06e8624` | READY_FOR_OWNER_CONSIDERATION | C8-PIC-04(CONFIRMED), C8-PIC-05(CONFIRMED) | `evidence/T1-03.md` |
| T1-04 | `682afce5e2f1` | READY_FOR_OWNER_CONSIDERATION | C8-PIC-06(CONFIRMED), C8-PIC-07(CONFIRMED) | `evidence/T1-04.md` |
| T1-05 | `be7fefc96676` | READY_FOR_OWNER_CONSIDERATION | C8-PIC-08(CONFIRMED), C8-PIC-09(CONFIRMED) | `evidence/T1-05.md` |
| T1-06 | `5126efa258a7` | READY_FOR_OWNER_CONSIDERATION | C8-PIC-10(CONFIRMED) | `evidence/T1-06.md` |
| T1-07 | `7edc4de1f9a7` | READY_FOR_OWNER_CONSIDERATION | C8-PIC-11(CONFIRMED), C8-PIC-12(CONFIRMED) | `evidence/T1-07.md` |
| T1-08 | `d283767e9150` | READY_FOR_OWNER_CONSIDERATION | C8-PIC-13(CONFIRMED), C8-PIC-14(CONFIRMED) | `evidence/T1-08.md` |
| T1-09 | `dd6978db8cf4` | READY_FOR_OWNER_CONSIDERATION | C8-PIC-15(CONFIRMED), C8-PIC-16(CONFIRMED) | `evidence/T1-09.md` |
| T1-10 | `d8ce1958a9bf` | READY_FOR_OWNER_CONSIDERATION | C8-PIC-17(CONFIRMED), C8-PIC-18(CONFIRMED) | `evidence/T1-10.md` |
| T1-11 | `225f624b866c` | READY_FOR_OWNER_CONSIDERATION | C8-PIC-19(CONFIRMED), C8-PIC-20(CONFIRMED) | `evidence/T1-11.md` |
| T1-12 | `972e5aa18dda` | READY_FOR_OWNER_CONSIDERATION | C8-PIC-21(CONFIRMED), C8-PIC-22(CONFIRMED) | `evidence/T1-12.md` |
| T1-13 | `eaa233f8c70a` | READY_FOR_OWNER_CONSIDERATION | C8-PIC-23(CONFIRMED), C8-PIC-24(CONFIRMED) | `evidence/T1-13.md` |
| T1-14 | `4392f326c1b9` | READY_FOR_OWNER_CONSIDERATION | C8-PIC-25(CONFIRMED), C8-PIC-26(PARTIAL) | `evidence/T1-14.md` |
| T1-15 | `1d67bddd3720` | READY_FOR_OWNER_CONSIDERATION | C8-PIC-27(CONFIRMED), C8-PIC-28(CONFIRMED) | `evidence/T1-15.md` |
| T1-16 | `31fedb68e25a` | READY_FOR_OWNER_CONSIDERATION | C8-PIC-29(CONFIRMED), C8-PIC-30(CONFIRMED) | `evidence/T1-16.md` |
| T1-17 | `0e4b8e47e299` | READY_FOR_OWNER_CONSIDERATION | C8-PIC-31(CONFIRMED), C8-PIC-32(PARTIAL), C8-PIC-33(CONFIRMED) | `evidence/T1-17.md` |
| T1-18 | `dc67b628878e` | READY_FOR_OWNER_CONSIDERATION | C8-PIC-34(CONFIRMED), C8-PIC-35(PARTIAL) | `evidence/T1-18.md` |
| T1-19 | `7c12a7ecc849` | HOLD_FIDELITY_DECISION | C8-PIC-36(CONFIRMED), C8-PIC-37(CONFIRMED) | `evidence/T1-19.md` |
| T1-20 | `138c1da0d3d9` | NEEDS_FURTHER_EVIDENCE | C8-PIC-38(CONFIRMED), C8-PIC-39(CONFIRMED), C8-PIC-40(CONFIRMED) | `evidence/T1-20.md` |

**Counts:** HOLD_FIDELITY_DECISION: 1; NEEDS_FURTHER_EVIDENCE: 1; READY_FOR_OWNER_CONSIDERATION: 18.

**Owner decisions needed before conversion:** per-candidate decision (APPROVED / WITHHELD / REJECTED); P-D2 for T1-19; for T1-20, whether a copy whose embedded CMS signature fails verification may be primary at all (recommended: no, until an independent official copy is obtained under an approved acquisition). Conversion is a separate reviewed PR followed by a BIND line.

