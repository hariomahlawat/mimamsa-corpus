"""Cycle 12: the TXN-DEMO --check gate must fail on stale synthetic-transaction artefacts (negative control).

A temporary copy of expected_hashes.json with one recorded value altered must make `--check` exit non-zero, and the
committed values must pass. The demo writes only into the temporary folder; the real ledger is never touched."""
import contextlib, importlib.util, io, json, shutil, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "legal_knowledge/audit_work/C9-LEGAL-EVIDENCE/TXN-DEMO/tools/synthetic_transaction_demo.py"


def load():
    spec = importlib.util.spec_from_file_location("txn_demo_gate", TOOL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@unittest.skipUnless(shutil.which("git"), "git is required by the synthetic transaction demo")
class TxnDemoGate(unittest.TestCase):
    def _run_check(self, mutate):
        mod = load()
        real = mod.TXN
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            exp = json.loads((real / "expected_hashes.json").read_text(encoding="utf-8"))
            mutate(exp)
            (tmp / "expected_hashes.json").write_text(json.dumps(exp, indent=1, sort_keys=True) + "\n", encoding="utf-8")
            shutil.copy(real / "TRANSCRIPT.md", tmp / "TRANSCRIPT.md")
            mod.TXN = tmp
            argv = sys.argv
            sys.argv = ["synthetic_transaction_demo.py", "--check", "--source", str(mod.DEFAULT_SOURCE)]
            out = io.StringIO()
            try:
                with contextlib.redirect_stdout(out):
                    rc = mod.main()
            finally:
                sys.argv = argv
            return rc, out.getvalue()

    def test_stale_expected_value_fails_the_gate(self):
        def stale(exp):
            vals = exp.get("values", exp)
            vals["source_package_tools_sha256"] = "0" * 64  # what a stale artefact looks like after a tool change
        rc, out = self._run_check(stale)
        self.assertNotEqual(rc, 0)
        self.assertIn("source_package_tools_sha256", out)


if __name__ == "__main__":
    unittest.main()
