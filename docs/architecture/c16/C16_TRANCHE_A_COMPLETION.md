# C16 Tranche A: completion record

- **Status:** Tranche A is integrated into `legal-knowledge/v2.5-staging`. This is a record, not an approval:
  - no production activation, corpus admission, legal approval, AUTH-LEDGER change or trust-key change follows from it;
  - the next tranche is planned in [C16_TRANCHE_B_IMPLEMENTATION_PLAN.md](C16_TRANCHE_B_IMPLEMENTATION_PLAN.md).
- **Staging head after Tranche A:** `5bdc8e68`.

## 1. What was merged

| PR | Merge commit | Reviewed head | Content |
| --- | --- | --- | --- |
| #80 | `28cd346d` | `a719da2d` | **WP04:** persistent text and passage store (ADR-0008, `DiskTextStore.Bind` on every open).<br>**WP05:** search evaluator optimisation, byte-identical results.<br>**Review fixes R01–R03.**<br>**Connection-exhaustion fix:** sign-in hold-and-wait and the ledger drain on connection close.<br>**Disk-configuration CI leg:** Linux `b1` job running the C# suite, oracle and journeys with the disk text store and disk engine.<br>**Carried-forward gates:** recorded in `app/b1/evidence/c16_integration/C16A_COMPLETION_REPORT.md` §4 |
| #77 | `5bdc8e68` | `80527921` | **Corpus integration contract `mimamsa-corpus-contract/2.0`:** schemas, validator, canonical form, rules, adapters, evidence binding, fixtures N01–N54 and X01–X35.<br>**Requirement documents:** compatibility matrix, producer requirements, consumer requirements.<br>**Knowledge release architecture (MKR-1):** with the executable activation reference model `activation.py` |

**Contract 2.0 is FROZEN** at reviewed head `80527921`. Any change from here is a versioned, separately reviewed change (contract §12), for example the additive 2.1 typed gate-receipt artefact schema. The merge did not alter the reviewed contract: `app/contract` and `docs/architecture/c16` at `5bdc8e68` are identical to `80527921`, and `app/b1` and `app/importer` are identical to `28cd346d`.

## 2. Review chain

| PR | Review | Head | Result |
| --- | --- | --- | --- |
| #80 | 6088057215 | `891a1c76` | REWORK: findings R01–R03; disposition in `app/b1/evidence/c16_integration/PR80_REVIEW_DISPOSITION.md` |
| #80 | closeout comment 7220574432 | — | ACCEPT WITH CONDITIONS (development-stage integration) |
| #80 | **6090721994** | `a719da2d` | **Final independent technical acceptance** for staging integration; workflows 46017334058 and 46017334042 green |
| #77 | 6088967174 | `4d476fab` | Architectural review: findings C01–C07 |
| #77 | 6089492803 | `7baf1b9f` | Re-review: residual corrections C01-R1, C02-R1, C03-R1, C07-R1 |
| #77 | 6090722349 | `f012a038` | Accept with one narrow validator correction (C02-R2) |
| #77 | **6091110370** | `80527921` | **Final independent acceptance** for contract freeze and staging integration; workflows 46030859732 and 46030859754 green |

All acceptances were technical and static. They convey no production or legal acceptance.

**Post-merge CI on `5bdc8e68`:** **verified green**. All seven runs succeeded: push runs 46036177306 and 46036177419, and pull-request runs 46036184727, 46036184716, 46036184710, 46036184604 and 46036184595. These cover the app contract and design checks (including `b1`), the App Windows PoC, the crawler security guards, the HF sync safeguard tests and the legal database audit kit. In the Linux `b1` job, all three disk-configuration steps passed: the unit and integration tests, the unmodified retrieval oracle, and the Playwright journeys.

## 3. Gates that remain open

None of these is met by Tranche A. All are mandatory before operational activation.

| Gate | Source |
| --- | --- |
| FG-SITE-IMPORTER | contract §10, architecture §12 |
| FG-RECEIPTS: typed receipt content resolved to the exact gate, copy, derivative, config, register and outcome; hash existence alone is not proof; contract 2.1 schema to be reviewed separately | contract §10, review 6091110370 |
| FG-ROW-LOADER | architecture §7 |
| FG-JOURNAL-DURABILITY | architecture §8.2 |
| FG-CALIBRATED-SAMPLES | architecture §12 (O4) |
| FG-REAL-RESTORE-TEST | architecture §10 |
| FG-DISK-PREFLIGHT | architecture §8.1 (D5) |
| FG-MODEL-TRUST-PURPOSE | architecture §2 and §12 (D3) |
| Real full-corpus HTTP and concurrency | `C16A_COMPLETION_REPORT.md` §4.1 |
| Memory and disk budget | §4.2 |
| Store-root ownership | §4.3 |
| Generation lifecycle | §4.4 |
| Retention (active plus two previous distinct; never prune protected generations) | §4.5 |
| Crash-safe activation and rollback | §4.6 |
| Calibrated accelerator checks | §4.7 |

## 4. What Tranche A did not deliver

- **No site importer for contract 2.0.** The C16 rules are reference code, and no bundle with `corpus-v2/` is imported by `app/importer`.
- **No knowledge release built, signed or activated.** No central build pipeline, knowledge rows, row loader, prebuilt accelerator packaging, activation journal implementation, installer, or backup and restore.
- **No consumer changes in the application:**
  - GenerationStore C16 facts (C1–C9);
  - GraphBuilder step 7 with `subject` and `chapter` nodes (G1–G7);
  - the .NET ExclusionStore reader.
- **No real full-corpus acceptance.** The 10k results are synthetic and mechanism-only.
- **No corpus admission or HF write.** Codex's PR #76 local reconciliation remains an independent producer stream, still in progress, and nothing from it is application-eligible.
- **No change to defaults:** text store and search engine stay `memory`.
- **No change to the acceptance oracles** (retrieval oracle 10/14 with hybrid off, 12/14 with hybrid on) or to AUTH-LEDGER (v0).
