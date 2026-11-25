#!/usr/bin/env python3
"""Run any C13-A5 tool with the deterministic register-provenance pin (post-freeze integration fix, review A5-01b).

  python -I -B run_check_c13.py <tool.py> [tool args...]      e.g.  run_check_c13.py treatment_c13.py --check

Needed for the two frozen tools (treatment_c13.py, predict_hrel_c13.py), which must not be edited; the non-frozen
tools apply the same pin themselves. See provenance_pin_c13.py.
"""
import runpy
import sys
from pathlib import Path

sys.dont_write_bytecode = True
TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
import provenance_pin_c13  # noqa: E402

provenance_pin_c13.apply()
if len(sys.argv) < 2:
    raise SystemExit(__doc__)
tool = (TOOLS / sys.argv[1]).resolve()
if tool.parent != TOOLS or not tool.is_file():
    raise SystemExit("not a C13-A5 tool: %s" % sys.argv[1])
sys.argv = [str(tool)] + sys.argv[2:]
runpy.run_path(str(tool), run_name="__main__")
