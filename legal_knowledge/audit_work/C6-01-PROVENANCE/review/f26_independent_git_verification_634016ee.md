# F-26 closure: independent git diff-scope and hash verification of PR #33 at `634016ee`

## 1. Identity and scope
- **Reviewer:** a separate Claude Code subagent of type `database-validator`, requested with model `fable`. Its transcript records the serving model as **`claude-fable-5-2` (Claude Fable 5.2)**, and it identified itself as Fable 5.2.
- **Independence:** it was not the agent that ran the four Fable review rounds and it did not prepare the package. It was spawned by the coordinator (Claude Opus 5.5) and given only the base and head SHAs, the expected hashes and the checks to run. It was not given the coordinator's results.
- **Access:** shell access, used read-only. It was instructed not to modify, commit, push or fetch, and not to use the network.
- **Base:** `04665eb17d2a1e4c8626d38346f17fa76b417548`, `origin/legal-knowledge/v2.5-staging`.
- **Head:** `634016eebdbf57646193df27a8f30ae57973106b`, `claude/c6-source-provenance`, the PR #33 head at the time.
- **Run:** 2026-11-23, after the head was pushed (about 07:53 UTC).
- **Evidence source:** the commands and outputs in section 3 are copied verbatim from that subagent's session transcript, extracted mechanically by the coordinator on 2026-11-23. Transcript file sha256: `582cf37c8722c2b5c7afd33863b8b69654706f55b88ee5a8a345f938ba1e7650`. The transcript itself is session-local and not committed.

## 2. Verdict
**PASS on every check. F-26 is closed for `634016ee`.**

| # | Check | Result (independently executed) |
| --- | --- | --- |
| 1 | Paths changed, base..head | 51 files, all added (`A`): 39 C6-01-PROVENANCE, 11 C6-PREP, 1 test file. 0 modified, 0 deleted, 0 renamed. **0 outside** the three authorised locations |
| 2a | `records_658.jsonl` sha256 at head | `9a8f0d193065762ffa987116dc761bcb734008d2a87a946f5591741f5befcfc1`; same blob at base and head (`e82b1f3d…`) |
| 2b | `cases_53.jsonl` sha256 at head | `8b8d53cd1434f7c1c6eaebe77f1fe295fb8b81b755e93276999b4b40b3c8f89a`; same blob (`cb641e94…`) |
| 2c | Cycle 4 `source_authentication_register.csv` sha256 at head | `cfe5f4081997abbcb88061cd7a8e5cc5b949c585cd7835fa48df51ae1a0c1ece`; same blob (`676eaf5a…`) |
| 3 | Protected trees (SOURCE-LIBRARY-C5, CALIBRATION-02, config, crawler, .github) | **identical tree IDs** at base and head; no diff |
| 4 | History | 12 commits, linear, base is an ancestor of head (`merge-base --is-ancestor` rc=0); head..base = 0 |
| - | Working tree | clean (empty `git status --porcelain`) |

**Note recorded by the reviewer:** there is no local branch named `legal-knowledge/v2.5-staging`, so its first `rev-parse` failed. The base was verified through `origin/legal-knowledge/v2.5-staging` and the explicit SHA. Nothing was fetched, so remote movement after the last fetch was outside its scope. The coordinator re-fetched on 2026-11-23 before closeout; staging was still `04665eb1`.

## 3. Commands and outputs (verbatim from the reviewer's transcript)
```
<<<COMMAND>>>
export PYTHONDONTWRITEBYTECODE=1 GIT_OPTIONAL_LOCKS=0; R=/home/user/c6; B=04665eb17d2a1e4c8626d38346f17fa76b417548; H=634016eebdbf57646193df27a8f30ae57973106b
echo "--refs"; git -C $R rev-parse legal-knowledge/v2.5-staging claude/c6-source-provenance HEAD 2>&1; git -C $R rev-parse --verify origin/legal-knowledge/v2.5-staging origin/claude/c6-source-provenance 2>&1
git -C $R cat-file -t $B; git -C $R cat-file -t $H
echo "--status counts"; git -C $R diff --name-status --no-renames $B $H | cut -f1 | sort | uniq -c
echo "--total"; git -C $R diff --name-only --no-renames $B $H | wc -l
echo "--with renames"; git -C $R diff --name-status $B $H | cut -f1 | sort | uniq -c
echo "--outside"; git -C $R diff --name-status --no-renames $B $H | grep -vP '\t(legal_knowledge/audit_work/C6-01-PROVENANCE/|legal_knowledge/audit_work/C6-PREP/|tests/test_legal_audit_c6_provenance\.py$)'
echo "--per-area"; git -C $R diff --name-only --no-renames $B $H | awk -F/ '{ if ($1=="tests") print $0; else print $1"/"$2"/"$3}' | sort | uniq -c
echo "--hashes"; for p in legal_knowledge/curated_originals/knowledge_base/v0.9/records_658.jsonl legal_knowledge/curated_originals/case_law/v0.9/cases_53.jsonl legal_knowledge/audit_work/CALIBRATION-02/registers/source_authentication_register.csv; do git -C $R show $H:$p | sha256sum; echo "pipe=${PIPESTATUS[0]}"; git -C $R ls-tree $H -- $p; git -C $R ls-tree $B -- $p; done
echo "--protected diff"; git -C $R diff --name-status --no-renames $B $H -- legal_knowledge/audit_work/SOURCE-LIBRARY-C5/ legal_knowledge/audit_work/CALIBRATION-02/ config/ crawler/ .github/; echo "rc=$?"
for d in legal_knowledge/audit_work/SOURCE-LIBRARY-C5 legal_knowledge/audit_work/CALIBRATION-02 config crawler .github; do echo "$d base=$(git -C $R rev-parse $B:$d 2>&1) head=$(git -C $R rev-parse $H:$d 2>&1)"; done
echo "--commits"; git -C $R rev-list --count $B..$H; git -C $R rev-list --count $H..$B; git -C $R merge-base --is-ancestor $B $H; echo "ancestor_rc=$?"; git -C $R log --format='%H %P | %s' $B..$H
echo "--wt"; git -C $R status --porcelain | head; git -C $R rev-parse --abbrev-ref HEAD
<<<OUTPUT>>>
--refs
fatal: ambiguous argument 'legal-knowledge/v2.5-staging': unknown revision or path not in the working tree.
Use '--' to separate paths from revisions, like this:
'git <command> [<revision>...] -- [<file>...]'
legal-knowledge/v2.5-staging
fatal: Needed a single revision
commit
commit
--status counts
     51 A
--total
51
--with renames
     51 A
--outside
--per-area
     39 legal_knowledge/audit_work/C6-01-PROVENANCE
     11 legal_knowledge/audit_work/C6-PREP
      1 tests/test_legal_audit_c6_provenance.py
--hashes
9a8f0d193065762ffa987116dc761bcb734008d2a87a946f5591741f5befcfc1  -
pipe=0
100644 blob e82b1f3d50c1cf0ae07d76efd8517e48ed4f8464	legal_knowledge/curated_originals/knowledge_base/v0.9/records_658.jsonl
100644 blob e82b1f3d50c1cf0ae07d76efd8517e48ed4f8464	legal_knowledge/curated_originals/knowledge_base/v0.9/records_658.jsonl
8b8d53cd1434f7c1c6eaebe77f1fe295fb8b81b755e93276999b4b40b3c8f89a  -
pipe=0
100644 blob cb641e94790013c5b132fc3a0b8eef0bc7d29258	legal_knowledge/curated_originals/case_law/v0.9/cases_53.jsonl
100644 blob cb641e94790013c5b132fc3a0b8eef0bc7d29258	legal_knowledge/curated_originals/case_law/v0.9/cases_53.jsonl
cfe5f4081997abbcb88061cd7a8e5cc5b949c585cd7835fa48df51ae1a0c1ece  -
pipe=0
100644 blob 676eaf5a3da4c1bf9566e6e9f8904b2ca86d3010	legal_knowledge/audit_work/CALIBRATION-02/registers/source_authentication_register.csv
100644 blob 676eaf5a3da4c1bf9566e6e9f8904b2ca86d3010	legal_knowledge/audit_work/CALIBRATION-02/registers/source_authentication_register.csv
--protected diff
rc=0
legal_knowledge/audit_work/SOURCE-LIBRARY-C5 base=3e20290143bf8a063e8dfce2c8f6b2b792be8c88 head=3e20290143bf8a063e8dfce2c8f6b2b792be8c88
legal_knowledge/audit_work/CALIBRATION-02 base=19b915627bce3cf70d4c0d5c3f32a63731e17b1d head=19b915627bce3cf70d4c0d5c3f32a63731e17b1d
config base=794ef1bc4007d3e6eb0ee748911ebe493b17e776 head=794ef1bc4007d3e6eb0ee748911ebe493b17e776
crawler base=e63110b9428491acb7cc40215faecf3fb2fa8eae head=e63110b9428491acb7cc40215faecf3fb2fa8eae
.github base=9265ad89a4783fc434ba8cacb47c7ab7ea912e47 head=9265ad89a4783fc434ba8cacb47c7ab7ea912e47
--commits
12
0
ancestor_rc=0
634016eebdbf57646193df27a8f30ae57973106b 2964a477fe06abfee607bffbb01ef85d89f7b63b | C6-01: Fable 5.2 focused re-review (2964a477) ACCEPT WITH CONDITIONS (no P1/P2); M-01..M-04 corrected
2964a477fe06abfee607bffbb01ef85d89f7b63b 4bf0a96a41c10e87324dd96dde82a7af4036e73e | C6-01: Fable 5.2 re-review (4bf0a96a) addressed: N-01 (P2) first-class record enforcement; N-02..N-09
4bf0a96a41c10e87324dd96dde82a7af4036e73e a165b0f35c2f9bd0636013923d1a07b4c809d68b | C6-01: Fable 5.2 review (a165b0f3) recorded and addressed: 9 P2 + 17 P3
a165b0f35c2f9bd0636013923d1a07b4c809d68b 08042c5381d5226e8c9dc1296acfe7c232fd7ef7 | C6-01: S.O. 4010/1986 date dispute preserved; RS papers-laid entry WITHHELD; integration architecture; TRA comparison; evidence-recovery requirements; owner proposals
08042c5381d5226e8c9dc1296acfe7c232fd7ef7 c3235312f924748a8194430cb8c9353bc48c3ac8 | C6-01: re-review ACCEPT recorded; documentation-only P3 corrections (RR-01..RR-05)
c3235312f924748a8194430cb8c9353bc48c3ac8 e7a10e27bde9cc6889740350b21f59cdd7c906c1 | C6-01: final-review corrections (R-01/R-02 + P3s); versioned addendum plan (draft); C6-02..05 readiness and D&V handbook lead
e7a10e27bde9cc6889740350b21f59cdd7c906c1 f0cd16a7f5380d9759b93b04a7ab4c21909956ce | C6-01 closeout: denominator and FULL-only documentation fixes; TRA 2026 and Delhi HC identity-page checks; ID traceability
f0cd16a7f5380d9759b93b04a7ab4c21909956ce 15eefec7769b8772a49f66328ec12c0d4abd1039 | C6-01: re-verification P3s (stable proposal IDs, gap-specific next steps, explicit evidence folders, statute-class rule removed)
15eefec7769b8772a49f66328ec12c0d4abd1039 d58894c4a94b41528555dc778e7b63bcc9446a48 | C6: D6 readiness report and Cycle 5 carry-over correction record
d58894c4a94b41528555dc778e7b63bcc9446a48 ff03fe7fd264f5574a948aeb5c183c99366ad103 | C6-01: apply independent verification (AP-22 downgraded; FULL-strength bar; R23 retrieval records collected; non-primary rendition; caveats)
ff03fe7fd264f5574a948aeb5c183c99366ad103 9b4ad44d2fbfa6fdfb64902f35b4c959377fd04b | C6-02..C6-05 preparation packages (no downloads, no correspondence, no determinations)
9b4ad44d2fbfa6fdfb64902f35b4c959377fd04b 04665eb17d2a1e4c8626d38346f17fa76b417548 | C6-01: provenance recovery for 36 held copies (34 sources); proposals only
--wt
claude/c6-source-provenance
<<<COMMAND>>>
export GIT_OPTIONAL_LOCKS=0; R=/home/user/c6
for r in HEAD claude/c6-source-provenance legal-knowledge/v2.5-staging origin/claude/c6-source-provenance origin/legal-knowledge/v2.5-staging; do echo "$r -> $(git -C $R rev-parse --verify -q "$r^{commit}" || echo MISSING)"; done
git -C $R for-each-ref --format='%(refname) %(objectname)'
git -C $R status --porcelain | wc -l
<<<OUTPUT>>>
HEAD -> 634016eebdbf57646193df27a8f30ae57973106b
claude/c6-source-provenance -> 634016eebdbf57646193df27a8f30ae57973106b
legal-knowledge/v2.5-staging -> MISSING
origin/claude/c6-source-provenance -> 634016eebdbf57646193df27a8f30ae57973106b
origin/legal-knowledge/v2.5-staging -> 04665eb17d2a1e4c8626d38346f17fa76b417548
refs/heads/claude/acq-01-config 1b948727eeb359da45886c208e6433c394d251ba
refs/heads/claude/acq-02-config b8ee3176cfbb587b0df10f8344f0665503a0de80
refs/heads/claude/acq-03-config 60715342b3f002dc4c08778c3eef672abcd1226f
refs/heads/claude/audit-pilot-01 1a420f254ee20719d3800f8933ba06712eff2505
refs/heads/claude/baseline-register-fix c166dac33887cefb6f5d1cb49ee47069e33bd0db
refs/heads/claude/c4-rev-a 22808e7f17e45d1f40d98ec5e9d68118e4cf4a42
refs/heads/claude/c4-rev-b fee2fb0b13ae823bd7d118c1f56d50eacac4f10b
refs/heads/claude/c4-rev-c 2c47a3d11f825c71256e460c4aa408a590623b5d
refs/heads/claude/c4-rev-d 1802c455bb90a80cd39269639a990748aff433a9
refs/heads/claude/c4-rev-e edd848c3502447062de275527ad1a084fc1cf7ef
refs/heads/claude/c6-source-provenance 634016eebdbf57646193df27a8f30ae57973106b
refs/heads/claude/crawler-security-aftjabalpur feec010375bc029d82569552651cb35124c78841
refs/heads/claude/cycle3-planning 28e3092cc7ac718eed9d8fab72e65b7e37495b82
refs/heads/claude/cycle4-calibration 936abfebe41275b61191f5a36cea36de02bfbfff
refs/heads/claude/cycle5-source-acquisition a37f1c23840a8e001e8d84aa1bd10af031b6375c
refs/heads/claude/desw-allowlist 97933ccf4e7deb27715c18ea767eeec01cdcd802
refs/heads/claude/gifted-bardeen-byeim6 b20843d6f3638fa637084ac49ea49c14ad2d3100
refs/heads/claude/hf-sync-guard-staging 4ebbeb893caea60de72332210bd29f7a552eb286
refs/heads/claude/integration-cycle2 6b27abd457fe494f917a49c675a63c1d0900dab5
refs/heads/claude/integration-cycle3 5dd2cb9f59f7ecc3c04a6bf88f0f712382741c27
refs/heads/claude/next-stage-proposal 3c9fd63ba7bbb635fca563d2accd8fa45be2d575
refs/heads/claude/ws-a-cycle3 2a09a14a9dd0ec20beed2d0b5bf3666d6d4f79bc
refs/heads/claude/ws-a-cycle3-reconcile 18ae107866dd3cf388fbd247b373b23661f8124c
refs/heads/claude/ws-a-statutory 2fc75160251fc9aa2b13592c3e5af5be7670b5d4
refs/heads/claude/ws-b-cycle3 6bdd9eb26c98250b199fec3e6bb1de918f7dc748
refs/heads/claude/ws-b-cycle3-reconcile e41911141245ba7c4727d3106a3257c73d97e456
refs/heads/claude/ws-b-judgments 97de40b3d17c8ed722539c6cc4a2aea9068867bf
refs/heads/claude/ws-c-cycle3 e9729c66d49002c01fddafea1f2cfd8931ca1752
refs/heads/claude/ws-c-cycle3-reconcile ac351546eed1053e3bd1c14e0ab76c4a22af3003
refs/heads/claude/ws-c-mml ba3d370eb3b86ded2f34194fa8530ed944a5a950
refs/heads/claude/ws-d-cycle3 1f47b7be353d909d67829ac91e080384711eeb51
refs/heads/claude/ws-d-cycle3-reconcile a824686b3de00ccba9f7d0e2e8e82b598e81fb34
refs/heads/claude/ws-d-quality dcd877b493ee226a445082382c3c3c247b4114f7
refs/heads/main 9a4b8a3815c53eee21c09b5bd6fdc8644227f075
refs/remotes/origin/claude/acq-01-config 1b948727eeb359da45886c208e6433c394d251ba
refs/remotes/origin/claude/acq-02-config b8ee3176cfbb587b0df10f8344f0665503a0de80
refs/remotes/origin/claude/acq-03-config 60715342b3f002dc4c08778c3eef672abcd1226f
refs/remotes/origin/claude/audit-pilot-01 71bc88208039f042098e350d952b31b69a638875
refs/remotes/origin/claude/baseline-register-fix c166dac33887cefb6f5d1cb49ee47069e33bd0db
refs/remotes/origin/claude/c4-rev-a 22808e7f17e45d1f40d98ec5e9d68118e4cf4a42
refs/remotes/origin/claude/c4-rev-b fee2fb0b13ae823bd7d118c1f56d50eacac4f10b
refs/remotes/origin/claude/c4-rev-c 2c47a3d11f825c71256e460c4aa408a590623b5d
refs/remotes/origin/claude/c4-rev-d 1802c455bb90a80cd39269639a990748aff433a9
refs/remotes/origin/claude/c4-rev-e edd848c3502447062de275527ad1a084fc1cf7ef
refs/remotes/origin/claude/c6-source-provenance 634016eebdbf57646193df27a8f30ae57973106b
refs/remotes/origin/claude/crawler-security-aftjabalpur feec010375bc029d82569552651cb35124c78841
refs/remotes/origin/claude/cycle3-planning 28e3092cc7ac718eed9d8fab72e65b7e37495b82
refs/remotes/origin/claude/cycle4-calibration 936abfebe41275b61191f5a36cea36de02bfbfff
refs/remotes/origin/claude/cycle5-source-acquisition a37f1c23840a8e001e8d84aa1bd10af031b6375c
refs/remotes/origin/claude/desw-allowlist 97933ccf4e7deb27715c18ea767eeec01cdcd802
refs/remotes/origin/claude/gifted-bardeen-byeim6 b20843d6f3638fa637084ac49ea49c14ad2d3100
refs/remotes/origin/claude/hf-sync-guard-staging 4ebbeb893caea60de72332210bd29f7a552eb286
refs/remotes/origin/claude/integration-cycle2 6b27abd457fe494f917a49c675a63c1d0900dab5
refs/remotes/origin/claude/integration-cycle3 5dd2cb9f59f7ecc3c04a6bf88f0f712382741c27
refs/remotes/origin/claude/next-stage-proposal 3c9fd63ba7bbb635fca563d2accd8fa45be2d575
refs/remotes/origin/claude/ws-a-cycle3 2a09a14a9dd0ec20beed2d0b5bf3666d6d4f79bc
refs/remotes/origin/claude/ws-a-cycle3-reconcile 18ae107866dd3cf388fbd247b373b23661f8124c
refs/remotes/origin/claude/ws-a-statutory 2fc75160251fc9aa2b13592c3e5af5be7670b5d4
refs/remotes/origin/claude/ws-b-cycle3 6bdd9eb26c98250b199fec3e6bb1de918f7dc748
refs/remotes/origin/claude/ws-b-cycle3-reconcile e41911141245ba7c4727d3106a3257c73d97e456
refs/remotes/origin/claude/ws-b-judgments 97de40b3d17c8ed722539c6cc4a2aea9068867bf
refs/remotes/origin/claude/ws-c-cycle3 e9729c66d49002c01fddafea1f2cfd8931ca1752
refs/remotes/origin/claude/ws-c-cycle3-reconcile ac351546eed1053e3bd1c14e0ab76c4a22af3003
refs/remotes/origin/claude/ws-c-mml ba3d370eb3b86ded2f34194fa8530ed944a5a950
refs/remotes/origin/claude/ws-d-cycle3 1f47b7be353d909d67829ac91e080384711eeb51
refs/remotes/origin/claude/ws-d-cycle3-reconcile a824686b3de00ccba9f7d0e2e8e82b598e81fb34
refs/remotes/origin/claude/ws-d-quality dcd877b493ee226a445082382c3c3c247b4114f7
refs/remotes/origin/legal-knowledge/claude-audit-agents-v1 c729f53e1abdfa909a8e6f7db65f61136c000629
refs/remotes/origin/legal-knowledge/v2.5-staging 04665eb17d2a1e4c8626d38346f17fa76b417548
refs/remotes/origin/main 21de35313397d77c915a9b11c9ea0493be00f4bd
refs/remotes/origin/raw-data ad77758d4569ba6aafa955cc7843d874489e10f7
refs/remotes/pr/18 dcd877b493ee226a445082382c3c3c247b4114f7
refs/remotes/pr/19 2fc75160251fc9aa2b13592c3e5af5be7670b5d4
refs/remotes/pr/20 ba3d370eb3b86ded2f34194fa8530ed944a5a950
refs/remotes/pr/21 97de40b3d17c8ed722539c6cc4a2aea9068867bf
refs/remotes/pr/22 6b27abd457fe494f917a49c675a63c1d0900dab5
refs/remotes/pr/24 2a09a14a9dd0ec20beed2d0b5bf3666d6d4f79bc
refs/remotes/pr/25 1f47b7be353d909d67829ac91e080384711eeb51
refs/remotes/pr/26 6bdd9eb26c98250b199fec3e6bb1de918f7dc748
refs/remotes/pr/27 e9729c66d49002c01fddafea1f2cfd8931ca1752
refs/remotes/pr/28 c166dac33887cefb6f5d1cb49ee47069e33bd0db
0
```

## 4. Independently executed versus reported by the coordinator
| Item | Independently executed by the F-26 reviewer | Executed or reported by the coordinator only |
| --- | --- | --- |
| Diff scope at `634016ee` | yes (section 3) | also in the coordinator's gate |
| Protected-tree identity | yes | - |
| 658/53/Cycle 4 register sha256 | yes (`git show <head>:<path> \| sha256sum`) | also in the coordinator's gate |
| Held-binary re-hash (`check_c5 --verify-files`) | no | coordinator gate only |
| Builders, validators, unit tests (24 checks; 363 tests) | no | coordinator gate only; GitHub CI `audit-kit-tests` independently ran the unit tests (run 45134303519, success) |
| Content correctness of the 51 files | no (out of scope) | reviewed by the Fable 5.2 review rounds (read-only, no git) |

## 5. Limitations
- The check covers byte identity and scope. It does not show that sources are authentic, current or legally correct.
- The 51 added files' content, schema conformance and tests were not examined by this reviewer.
- Commit subjects that state review outcomes were not verified by this reviewer.
- **This record is committed after `634016ee`.** The commit that adds it is therefore not covered by the check above. The final PR head (this file only, relative to `634016ee`) was verified by a separate narrow review, recorded in the PR #33 description and the closeout report.
