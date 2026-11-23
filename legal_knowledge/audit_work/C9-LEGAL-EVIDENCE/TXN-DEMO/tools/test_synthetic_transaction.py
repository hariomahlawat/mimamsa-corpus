"""unittest wrapper: re-run the SYNTHETIC AUTH-LEDGER transaction demonstration with --check (deterministic hashes and
transcript). Offline. The demo builds and deletes its own temporary repository under TXN/work/; the real ledger is only read.

  python -m unittest discover -s TXN/tools -p 'test_synthetic_transaction.py'
Set AUTH_LEDGER_SOURCE to the repository whose AUTH-LEDGER package is to be exercised (default: the demo's built-in path)."""
import os, subprocess, sys, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEMO = HERE / "synthetic_transaction_demo.py"
sys.path.insert(0, str(HERE))
import synthetic_transaction_demo as demo  # noqa: E402

SOURCE = Path(os.environ.get("AUTH_LEDGER_SOURCE", str(demo.DEFAULT_SOURCE)))


@unittest.skipUnless((SOURCE / demo.PKG_REL / "tools/auth_ledger.py").is_file(), f"AUTH-LEDGER source not found at {SOURCE}")
class SyntheticTransaction(unittest.TestCase):
    def test_demo_check_is_deterministic_and_passes(self):
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        p = subprocess.run([sys.executable, "-B", str(DEMO), "--check", "--source", str(SOURCE)], capture_output=True, text=True,
                           env=env, timeout=900)
        self.assertEqual(p.returncode, 0, p.stdout[-4000:] + p.stderr[-4000:])
        self.assertIn("CHECK OK", p.stdout)
        self.assertNotIn("DEMO FAILURES", p.stdout)

    def test_real_ledger_stays_at_version_zero(self):
        head = (SOURCE / demo.PKG_REL / "ledger/HEAD").read_text(encoding="utf-8").strip()
        self.assertEqual(head, demo.REAL_GENESIS_HEAD)
        lines = (SOURCE / demo.PKG_REL / "ledger/manifest.jsonl").read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 1)


if __name__ == "__main__":
    unittest.main()
