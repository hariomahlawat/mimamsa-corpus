"""CI entry point for the C10 Hugging Face judicial-corpus audit tests (assembly reproducibility, accounting, rules).
The tests live beside the tools in legal_knowledge/audit_work/C10-HF-JUDGMENTS/tools/."""
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "legal_knowledge/audit_work/C10-HF-JUDGMENTS/tools"
sys.path.insert(0, str(TOOLS))
from test_audit_judgments import *  # noqa: E402,F401,F403
