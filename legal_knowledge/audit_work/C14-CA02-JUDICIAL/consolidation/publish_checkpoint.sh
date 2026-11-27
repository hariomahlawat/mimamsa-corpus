#!/usr/bin/env bash
set -euo pipefail
cd /workspace/c14-consolidation
repo=/workspace/mimamsa-c14-consolidation-receipts
path=legal_knowledge/audit_work/C14-CA02-JUDICIAL/consolidation
install -d "$repo/$path"
exec 9>publish.lock
flock 9
cp build_candidates.py verify_package.py exercise_ca03.py enrich_reviewed_sample.py source_recheck.py reconcile_markings.py fetch_marking_pages.py gather_staged.py upload_staged_verified.py "$repo/$path/"
cp package-v5/manifest.json "$repo/$path/CANDIDATE_PACKAGE_MANIFEST.json"
cp package-v5-verification.json ca03-isolated-receipt.json source-recheck.json marking-dispositions.json marking-visual-fetch.jsonl manual-enrichment.jsonl "$repo/$path/"
cp staged-upload/official-upload.json "$repo/$path/STAGED_UPLOAD_RECEIPT.json"
cp official-discovery-rechecks.json "$repo/$path/"
cp official-new-discovery.json cda-pension-result.jsonl screen_cda_pension.py fetch_cleared_originals.py marking-assurance-a.json marking-assurance-b.json "$repo/$path/"
for receipt in staged-upload-*/official-upload.json; do
 if test -f "$receipt"; then
  slot=${receipt%/official-upload.json}
  cp "$receipt" "$repo/$path/STAGED_UPLOAD_RECEIPT_${slot##*-}.json"
 fi
done
cp judicial-retry/retry.py "$repo/$path/retry_judicial.py"
cp judicial-retry/extended.jsonl "$repo/$path/JUDICIAL_RETRY_RECEIPTS.jsonl"
cp aft-expansion/aft-expansion.jsonl "$repo/$path/AFT_EXPANSION_RECEIPTS.jsonl"
cp aft-expansion/aft-rest.jsonl "$repo/$path/AFT_REMAINING_SCREENING.jsonl"
cp README.md "$repo/$path/"
cp publish_checkpoint.sh watch_checkpoint.sh finish_staging.sh "$repo/$path/"
git -C "$repo" add "$path"
git -C "$repo" diff --cached --check
if ! git -C "$repo" diff --cached --quiet; then
 git -C "$repo" -c user.name=Codex -c user.email=codex@openai.com commit -m 'Record Cycle 14 consolidation, isolated candidate checks and acquisition receipts'
fi
git -C "$repo" push origin HEAD:refs/heads/corpus/c14-collection-discovery-20261126
