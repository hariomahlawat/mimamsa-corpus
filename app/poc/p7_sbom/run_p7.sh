#!/bin/bash
# P7: CycloneDX SBOMs, licence inventory from installed package metadata, vulnerability scans.
# Usage: run_p7.sh <venv> <dotnet_dir> <out_dir>
# Network: pip-audit (PyPI/OSV), npm audit (registry) and dotnet vulnerable-package checks (nuget.org) are ONLINE
# lookups; they ran on the connected build host, not offline.
set -u
VENV=$1; DOTNET=$2; OUT=$3
HERE=$(cd "$(dirname "$0")" && pwd)
POC=$(cd "$HERE/.." && pwd)
mkdir -p "$OUT"
export DOTNET_CLI_TELEMETRY_OPTOUT=1 DOTNET_NOLOGO=1 PATH="$DOTNET:$PATH" DOTNET_ROOT="$DOTNET" DOTNET_ROLL_FORWARD=Major  # CycloneDX 5.5.0 targets net9.0

# ---- Python: full PoC venv + per-candidate requirement sets
"$VENV/bin/cyclonedx-py" environment "$VENV" --of JSON -o "$OUT/sbom-python-bpoc-venv.cdx.json" 2>"$OUT/cyclonedx-py.log"
"$VENV/bin/pip" freeze --exclude-editable > "$OUT/python-bpoc-freeze.txt"
"$VENV/bin/pip-licenses" --python "$VENV/bin/python" --from=mixed --with-urls --format=json > "$OUT/python-licenses.json"
for set in search_stack pdf_libs django_service; do
  "$VENV/bin/cyclonedx-py" requirements "$HERE/sets/$set.txt" --of JSON -o "$OUT/sbom-python-$set.cdx.json" 2>>"$OUT/cyclonedx-py.log"
  "$VENV/bin/pip-audit" -r "$HERE/sets/$set.txt" --format json -o "$OUT/pip-audit-$set.json" --progress-spinner off 2>>"$OUT/pip-audit.log" || true
done

# ---- npm: PDF.js viewer PoC
( cd "$POC/p4_pdf/pdfjs" && npm sbom --sbom-format cyclonedx > "$OUT/sbom-npm-pdfjs.cdx.json" 2>>"$OUT/npm.log";
  npm audit --json > "$OUT/npm-audit-pdfjs.json" 2>>"$OUT/npm.log";
  npx --yes license-checker-rseidelsohn@4.4.2 --json --production > "$OUT/npm-licenses-pdfjs.json" 2>>"$OUT/npm.log" ) || true

# ---- .NET: ASP.NET Core PoC
( cd "$POC/p1_hosting/aspnet" &&
  dotnet list package --include-transitive --format json > "$OUT/dotnet-packages.json" 2>>"$OUT/dotnet.log";
  dotnet list package --vulnerable --include-transitive --format json > "$OUT/dotnet-vulnerable.json" 2>>"$OUT/dotnet.log";
  dotnet tool install --tool-path "$OUT/.tools" CycloneDX --version 5.5.0 >>"$OUT/dotnet.log" 2>&1;
  "$OUT/.tools/dotnet-CycloneDX" MimamsaPocApi.csproj -o "$OUT" -fn sbom-dotnet-aspnet.cdx.json -j >>"$OUT/dotnet.log" 2>&1 ) || true
rm -rf "$OUT/.tools"
ls -la "$OUT"
