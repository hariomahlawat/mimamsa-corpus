#!/usr/bin/env bash
set -euo pipefail
cd /workspace/c14-consolidation
while pgrep -f '^/tmp/mim-c14-corrective-venv/bin/python (retry.py|aft_rest.py)$' >/dev/null; do
 sleep 90
 bash publish_checkpoint.sh >>watch.log 2>&1
done
bash publish_checkpoint.sh >>watch.log 2>&1
