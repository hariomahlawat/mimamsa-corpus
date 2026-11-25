# C13-A0: evaluation infrastructure

This folder holds reusable, deterministic evaluation tooling and three fresh holdouts for Outcome V4 (A2), Holdings V2 (A3) and graph relations (A5). [`PROTOCOL_C13.md`](PROTOCOL_C13.md) is binding on those workstreams.

**Status:** automated classification and sampling. Nothing here is legally verified. The holdouts are **drawn, not coded**, and their texts were not read.

The GA0 independent review of `5e07e010` returned **ACCEPT WITH CONDITIONS**, with no P1; it is in `reviews/`. Protocol **v1.1** addresses conditions F01–F05 and the P3 findings without redrawing any holdout (see `PROTOCOL_C13.md` section 9.1). Reviewer confirmation of v1.1 is the gate for the freezes.

All tools use only the Python 3.11+ standard library. Every tool's `--check` option writes nothing and compares a fresh in-memory rebuild with the committed bytes.

## Layout

| Path | Content |
| --- | --- |
| `tools/c13_common.py` | Paths, pinned commits, deterministic CSV/JSON rendering, write-or-check, read-only corpus blob reader |
| `tools/c13_features.py` | **Stage 1.** Text features per judicial record: page letter-share, usable pages, party-specific, multi-opinion and connected-matter cues, plus the metadata fields stage 2 needs. Needs corpus commit `ad77758d` and a sha-verified copy of the C12 HF additions |
| `tools/c13_frame.py` | **Stage 2.** Classification frame: court, year band, structural strata, text quality, in-scope flag, raw-path validation, spent sets, judgment-level eligibility. Committed inputs only |
| `tools/c13_exclusions.py` | Spent-set manifests (C10, C11 and C12 holdouts, references, dev and review sets) mapped to judgment keys |
| `tools/c13_sampler.py` | Sampler v2: stratified selection with recorded inclusion probabilities and refusals (F05/F06). Draws H-OUT-C13, H-HOLD-C13 (+ reserve) and H-REL-C13, with size calculations |
| `tools/c13_stats.py` | Wilson, Horvitz–Thompson ratio, Kish design effect, stratified judgment-cluster bootstrap, sample-size and power calculations, ICC, Cohen's kappa, Krippendorff's alpha |
| `tools/c13_tasks.py` | Pluggable task definitions (outcome, holdings, relations): fields, exact vocabularies, families, unit keys, span matcher |
| `tools/c13_coding.py` | Double-coding toolkit: blinded packets, leakage check, agreement, X/Y adjudication sheet with sealed key, reference builder, versioned annotation store |
| `tools/c13_score.py` | Generic scoring harness. `--check` runs its synthetic self-test |
| `tools/c13_ci_sim.py` | v1.1 coverage simulation of the validated interval (design-effect Clopper–Pearson) on the registered designs |
| `tools/c13_power.py` | v1.1 weighted size restatement: what each holdout can and cannot show |
| `tools/c13_sensitivity.py` | v1.1 pre-exposed holdout subsets (curated/KB content, near-identical spent siblings, case-number review) |
| `tools/c13_check_all.py` | Runs every check and verifies `SHA256SUMS` |
| `reviews/` | GA0 independent review (report, findings, reviewer scripts and evidence; the reviewer's 244 MB repository exports are not copied) |
| `packets/CODING_GUIDE_*.md` | Coder guides. The holdings guide is an interim layout until A3 commits its versioned guideline |
| `outputs/frame/` | `TEXT_FEATURES.csv`, `FRAME_RECORDS.csv` (4,281), `FRAME_JUDGMENTS.csv` (3,637), `STRATUM_COUNTS.csv`, `NON_USABLE_POPULATION.csv`, `FRAME_SUMMARY.json` |
| `outputs/exclusions/` | `SPENT_SET_MEMBERS.csv`, `EXCLUDED_JUDGMENTS.csv` (682 keys), `EXCLUSION_SUMMARY.json` (source files and their sha256) |
| `outputs/holdouts/<H>/` | **Evaluator only:** `SAMPLE.csv` (strata, N_h, n_h, π, weights), `DESIGN.json` (size justification, reallocations), `ITEM_MAP.csv`. `RESERVE.csv` for H-HOLD. `HOLDOUT_REGISTRATION.json` holds the sample hashes |
| `outputs/packets/<H>/coder_{1,2}/CODER_SHEET.csv` | **Coder view:** opaque item id, file sha256, raw path, store, pages to code, blank fields |
| `outputs/packets/<H>/adjudicator/ADJUDICATOR_INSTRUCTIONS.json` | Adjudicator result columns and rules |
| `outputs/packets/H-HOLD-C13-RESERVE/` | Reserve packets; sent only under the pre-registered decision (PROTOCOL section 3.1) |
| `outputs/ci_validation/` | `CI_COVERAGE.csv` and `CI_COVERAGE_SUMMARY.json` (validated: min coverage 0.954; outcome ≥ 0.965 for p = 0.90–0.99) |
| `outputs/holdouts/SIZE_RESTATEMENT_V1_1.json`, `PRE_EXPOSED_SUBSET.csv` | v1.1 restatement and sensitivity subsets |

## Measured frame (automated; `FRAME_SUMMARY.json`)

The frame covers 4,281 judicial records: 4,259 at `ad77758d`, 18 ingested in C12 and 4 C12 held-original derived records. These make up 3,973 files and 3,637 judgments.

**Judgments by court and structural stratum, with text quality:**

| Court | Batch/multi | Party-specific (cand.) | Pension/disciplinary | Other | Total | Usable | Garbled | Image-only | Truncated | Unreadable |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SC | 65 | 3 | 208 | 80 | 356 | 356 | 0 | 0 | 0 | 0 |
| Delhi | 123 | 11 | 827 | 448 | 1,409 | 1,390 | 0 | 3 | 9 | 7 |
| P&H | 127 | 36 | 656 | 382 | 1,201 | 1,134 | 45 | 22 | 0 | 0 |
| J&K | 18 | 1 | 167 | 176 | 362 | 360 | 1 | 1 | 0 | 0 |
| Allahabad | 7 | 0 | 96 | 206 | 309 | 308 | 1 | 0 | 0 | 0 |
| **Total** | 340 | 51 | 1,954 | 1,292 | **3,637** | 3,548 | 47 | 26 | 9 | 7 |

**Records:** 4,160 usable, 55 garbled, 45 image-only (OCR text of image PDFs), 12 truncated and 9 unreadable. The 121 non-usable records (89 judgments) are listed in `NON_USABLE_POPULATION.csv`.

**Scope (judgments):** 3,169 in scope, 403 uncertain, 65 out of scope.

**Eligibility:** 2,812 judgments are eligible for fresh holdouts. The rest are excluded for these reasons:
- spent: 679;
- out of scope: 65;
- garbled: 47;
- image-only: 26;
- truncated: 9;
- unreadable: 7;
- access marking: 3.

A judgment can have more than one reason.

**Caveats:**
- Measured by the GA0 reviewer on 40 records: court 40/40, text quality 40/40, structural stratum 63% (24/38).
- The party-specific cue has a PPV of about 11% (3/27). Noise affects efficiency, not the validity of the weighted estimates. The party-specific breakdown is descriptive only.
- The 26 OCR-only judgments are excluded by rule, not because all of them are unreadable.
- Topic-based subject strata come from C10 automated keyword topics.

## Fresh holdouts (drawn, not coded)

| Holdout | Size | Basis |
| --- | --- | --- |
| H-OUT-C13 | 300 judgments (SC/DEL/PH 70, J&K/ALL 45) | **Weighted (v1.1):** Kish design effect 2.0, n_eff about 127 covered judgments, validated half-width about ±3.7pp at p = 0.95. `MET_LOWER_BOUND` is practically reachable only if the true precision is about 0.99 or higher (simulated probability 0.49 at 0.98) |
| H-HOLD-C13 | 75 judgments (30 SC, 45 HC) + 38 reserve | **Weighted (v1.1):** about ±8.5pp at recall 0.6 (not ±7pp). With the full reserve (113), about ±6.7pp. A pre-registered reserve decision is due before the first packet. **The HC holdings density (2.5 per judgment) is an assumption** |
| H-REL-C13 | 160 pages (SC 80 / HC 80) | Every citation on each page is coded. Overall weighted recall is descriptive (Kish design effect 7.5). Per-type precision about ±9pp on treatment-cue pages |

The three holdouts are independent samples of the same eligible frame. Their overlaps are reported. Packets for two coders and an adjudicator are ready.

## Commands

```
python3 -I -B tools/c13_features.py [--check]   # stage 1 (corpus + C12 additions copy; about 50 s)
python3 -I -B tools/c13_exclusions.py [--check]
python3 -I -B tools/c13_frame.py [--check]
python3 -I -B tools/c13_sampler.py [--check]
python3 -I -B tools/c13_coding.py [--check]     # packets + leak checks
python3 -I -B tools/c13_score.py --check        # harness self-test
python3 -I -B tools/c13_sensitivity.py [--check]
python3 -I -B tools/c13_ci_sim.py [--check]     # coverage simulation (about 1 minute)
python3 -I -B tools/c13_power.py [--check]
python3 -I -B tools/c13_check_all.py            # everything + SHA256SUMS
python3 -m unittest discover -s tests -p "test_legal_audit_c13_eval_*.py"   # from the repository root
```

- **Corpus location:** `MIMAMSA_CORPUS_GIT` points to a git directory that holds `ad77758d`. The default is `/home/user/c7`, then this repository.
- **C12 additions copy:** `MIMAMSA_C12_ADDITIONS` points to the copy. **It is required whenever the tools run outside this worktree layout** (GA0 F16). The default is `<scratchpad>/c13/cache_a0/c12_additions`. It was downloaded from HF commits `af7f9d06` and `15bd03cc` and is sha256-verified against `judicial_recovery_c12/STAGED_MANIFEST.csv` on every read.
- **Full stage 1 in tests:** `MIMAMSA_C13_FULL=1` adds the stage-1 reproduction to the tests.

## Coding workflow

1. Send `outputs/packets/<H>/coder_N/CODER_SHEET.csv` and the guide to coder N. Run `c13_coding.py leakcheck <sheet> --task <task>` first.
2. On return, run `leakcheck <returned> --task <task> --completed --coder <id> --packet <sheet> --other-coder <other id>`. The other coder's id is required. Uncodable items come back as `UNCODABLE:<CODE>` rows and are never replaced.
3. Run `agree --task <task> --a A.csv --b B.csv --out AGREEMENT.json`. Report agreement before any scoring.
4. Run `adjsheet ...`. Give the adjudicator only `ADJUDICATION_SHEET.csv` and keep `ADJUDICATION_KEY.csv` sealed.
5. Run `truth ... --adjudicated ADJ.csv --out TRUTH.csv`, then store it with `store_version` and check with `verify <store>`.
6. After the extractor freeze, an independent evaluator runs `c13_score.py --task ... --holdout ... --truth TRUTH.csv --pred PRED.csv --store <store> --pages PAGES.jsonl --out-dir ...`.

## Known limitations

- The frame is automated. Text-quality and stratum rules are heuristics, fixed in advance; they are not legal findings.
- Estimates generalise only to the eligible, non-spent, USABLE-text population. The spent sets (about 19% of judgments) and non-usable files (2.4%) are outside it.
- The HC holdings density is assumed. The reserve rule covers a shortfall, and the decision is recorded at GA2.
- C12 coordinator-tools F08 (scnum overlay) is outside A0 and is not addressed here.
- Party-specific results cannot be demonstrated with this holdout (about 2–6 gold judgments expected).
- Results must be reported with and without the pre-exposed subsets.
- Coder independence rests on process: separate instances and assignment logs. The tools can detect leakage but cannot prove independence.
