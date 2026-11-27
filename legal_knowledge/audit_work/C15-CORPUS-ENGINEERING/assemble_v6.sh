#!/usr/bin/env bash
set -euo pipefail
umask 077
cd /workspace/c15-durable
generation=${1:?generation}
repair=/workspace/c15-page-repair/run
validation=/workspace/c15-validation
python=/tmp/mim-c14-corrective-venv/bin/python
work="build-$generation"
portable="candidate-$generation"
"$python" build_candidates_v6.py /workspace/c14-collection "$work" --consolidation /workspace/c14-consolidation --repair "$repair"
PYTHONPATH=/workspace/mimamsa-c14-pr59/app/contract "$python" /workspace/c15-durable/verify_package_v6.py "$work" >"$work/anchor-verification.json"
python portable_package.py export "$work" "$portable"
cp portable_package.py build_candidates_v6.py candidate_coverage.py "$work/anchor-verification.json" "$portable/"
cp /workspace/c15-durable/verify_package_v6.py "$portable/"
cp "$validation/context-reviews.jsonl" "$validation/anchor-qa.json" "$validation/retrieval-qa.json" "$portable/"
for file in "$validation"/context-reviews-supplement.jsonl "$validation"/supplement-qa.json; do
 if test -f "$file"; then cp "$file" "$portable/"; fi
done
cp /workspace/c15-qa/{verification.json,FINDINGS.md,verify_reviews.py} "$portable/"
cp "$repair/manifest.json" "$portable/repair-manifest.json"
tar --sort=name --mtime=@0 --owner=0 --group=0 -C "$repair" -cf - manifest.json repair-register.jsonl documents | gzip -n >"$portable/repair-derivatives.tar.gz"
python candidate_coverage.py "$portable/records.jsonl" "$portable/coverage.json" "$portable/context-reviews.jsonl" "$portable/context-reviews-supplement.jsonl"
tmp=$(mktemp -d)
cp "$portable"/{portable_package.py,portable-manifest.json,records.jsonl,source-manifest.json,pages.jsonl.gz} "$tmp/"
(cd "$tmp" && env -i PATH=/usr/bin:/bin python3 -I portable_package.py rebuild . reconstructed)
cp "$tmp/reconstructed/receipt.json" "$portable/fresh-reconstruction.json"
