#!/usr/bin/env bash
set -euo pipefail
cd /workspace/c14-consolidation
while pgrep -f '^/tmp/mim-c14-corrective-venv/bin/python (retry.py|aft_rest.py)$' >/dev/null; do
 sleep 90
 if ! bash publish_checkpoint.sh >>watch.log 2>&1; then
  printf '%s\n' 'Remote checkpoint publication pending; local receipt retained.' >>watch.log
 fi
done
bash publish_checkpoint.sh >>watch.log 2>&1
