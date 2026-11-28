#!/usr/bin/env bash
# C16 S3-C (B07, FG-DISK-PREFLIGHT mechanism, Linux portability WD-4): the measured disk preflight refuses on a
# deliberately FILLED volume (a 128 MiB tmpfs) and accepts once space is freed. CI only (needs sudo to mount).
#   test-filled-volume.sh <Mimamsa.Activation.dll> <work dir> <out dir>
set -euo pipefail
TOOL="$1"; WORK="$2"; OUT="$3"
mkdir -p "$WORK" "$OUT"
MNT=/mnt/s3cfill
sudo mkdir -p "$MNT"
sudo mount -t tmpfs -o size=128m tmpfs "$MNT"
sudo chown "$(id -u):$(id -g)" "$MNT"
cleanup() { sudo umount "$MNT" || true; }
trap cleanup EXIT
python3 - "$WORK/install-filled.json" "$MNT" <<'PY'
import json, sys
roots = {k: f"{sys.argv[2]}/Mimamsa/{k.replace('_', '-')}" for k in
         ("application", "site", "text_store", "search_index", "vectors", "uploads", "config", "backup", "logs", "import", "scratch")}
json.dump({"format": "mimamsa-dev-install/1", "mode": "test", "roots": roots, "headroom_fraction": 0.1, "retention": {"keep_previous": 2}},
          open(sys.argv[1], "w"))
PY
mkdir -p "$WORK/payload"
head -c 41943040 /dev/zero > "$WORK/payload/release.bin"
FREE=$(df -B1 --output=avail "$MNT" | tail -1)
head -c $((FREE - 20*1024*1024)) /dev/zero > "$MNT/filler.bin"
set +e
dotnet "$TOOL" install-layout --config "$WORK/install-filled.json" --payload "release=import=$WORK/payload" > "$OUT/preflight-filled.json"
C1=$?
set -e
python3 - "$OUT/preflight-filled.json" "$C1" "$MNT" <<'PY'
import json, sys
o = json.loads(open(sys.argv[1]).read().strip().splitlines()[-1])
assert int(sys.argv[2]) == 2 and o["code"] == "PREFLIGHT_FAILED", o
v = [x for x in o["preflight"]["volumes"] if x["volume"] == sys.argv[3]]
assert v and v[0]["required_bytes"] > v[0]["free_bytes"] and v[0]["measured_payload_bytes"] == 41943040, o
print("refused:", v[0]["free_bytes"], "free <", v[0]["required_bytes"], "required")
PY
test ! -e "$MNT/Mimamsa/site"
rm -f "$MNT/filler.bin"
dotnet "$TOOL" install-layout --config "$WORK/install-filled.json" --payload "release=import=$WORK/payload" > "$OUT/preflight-freed.json"
test -d "$MNT/Mimamsa/site/journal"
echo "filled-volume preflight: refused, then accepted after freeing space"
