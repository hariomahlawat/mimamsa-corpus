"""AUTH-LEDGER shared helpers (stdlib only; offline; deterministic)."""
import csv, hashlib, io, json
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
AW = PKG.parent
REPO = AW.parents[1]
HEX64 = __import__("re").compile(r"[0-9a-f]{64}")


class LedgerError(Exception):
    """Any integrity, schema, evidence or approval failure. The reader fails closed on it."""


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def csv_text(cols, rows):
    b = io.StringIO()
    w = csv.DictWriter(b, fieldnames=cols, lineterminator="\n", extrasaction="raise")
    w.writeheader()
    for r in rows:
        w.writerow({c: r.get(c, "") for c in cols})
    return b.getvalue()


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def sha256_text(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)
