"""C16 Tranche B stream B02: the central knowledge-build pipeline (skeleton).

One command, ``python -m mimamsa_kbuild build --spec <spec.json>``, runs the stages S0-S9 of
docs/architecture/c16/interfaces/B02_CENTRAL_BUILD_SPEC.md with chained stage manifests
(``mimamsa_contract.c16.build_spec``), the contract resume rule, deterministic output and a shared-host resource
budget. Stage 2 scope: enough of every stage to build a DEVELOPMENT-signed, explicitly DEGRADED (lexical-only) MKR-1
knowledge release from fixtures for the CP-1 vertical slice. The full pipeline is Stage 3.
"""
from __future__ import annotations

import sys
from pathlib import Path

VERSION = "0.1.0"
PACKAGE_DIR = Path(__file__).resolve().parent
KBUILD_DIR = PACKAGE_DIR.parent
REPO = KBUILD_DIR.parents[1]

for _p in (REPO / "app" / "contract", REPO / "app" / "importer"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
