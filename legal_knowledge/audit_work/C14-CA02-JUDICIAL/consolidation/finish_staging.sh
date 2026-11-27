#!/usr/bin/env bash
set -euo pipefail
cd /workspace/c14-consolidation
while pgrep -f '^/tmp/mim-c14-corrective-venv/bin/python retry.py$' >/dev/null; do sleep 25; done
python - <<'PY'
import json
journal=[json.loads(line) for line in open('judicial-retry/extended.jsonl')]
jobs=json.load(open('judicial-retry/extended-queue.json'))['jobs']
expected={x+3 for x in range(0,len(jobs),15)}
completed={x['first_offset'] for x in journal if x.get('complete')}
assert completed==expected, 'Judicial writer did not finish. Reconcile its journal before further writes.'
PY
for slot in $(seq 3 30); do
 stage=staged-upload-$slot
 C14_STAGE_ROOT="$stage" C14_STAGE_CAP=70 python gather_staged.py
 (
  cd "$stage"
  timeout 240 env HF_HOME=/workspace/c14-collection/.hf-runtime HF_HUB_DISABLE_XET=1 /tmp/mim-c14-corrective-venv/bin/python ../upload_staged_verified.py >upload.log 2>&1
 )
 if ! bash publish_checkpoint.sh; then
  printf '%s\n' 'GitHub checkpoint retained locally after push failure.' >&2
 fi
 count=$(python -c 'import json,sys;print(len(json.load(open(sys.argv[1]))["files"]))' "$stage/official-upload.json")
 if test "$count" = 0; then
  if ! pgrep -f '^/tmp/mim-c14-corrective-venv/bin/python aft_rest.py$' >/dev/null; then exit 0; fi
  sleep 45
 fi
done
