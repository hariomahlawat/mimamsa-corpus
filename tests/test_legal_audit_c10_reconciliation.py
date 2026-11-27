"""CI entry point for the C10 unified corpus reconciliation tests (offline; needs the pinned raw-data commit in the clone).
The tests live beside the tool in legal_knowledge/audit_work/C10-RECONCILIATION/tools/."""
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "legal_knowledge/audit_work/C10-RECONCILIATION/tools"
sys.path.insert(0, str(TOOLS))
from test_build_reconciliation import *  # noqa: E402,F401,F403
