"""CI entry point for the C8 judgment-batch reconciliation tool tests (offline, stdlib only).
The tests live beside the tool in legal_knowledge/audit_work/C8-SOURCES/CORPUS-QUALITY/tools/."""
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "legal_knowledge/audit_work/C8-SOURCES/CORPUS-QUALITY/tools"
sys.path.insert(0, str(TOOLS))
from test_reconcile_judgments import *  # noqa: E402,F401,F403
