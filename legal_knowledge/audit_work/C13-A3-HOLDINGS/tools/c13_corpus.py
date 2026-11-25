"""Corpus access for C13-A3: judgment register and text layers read from git (no network).

Reuses the C12 loader (`holdings_c12.load_corpus`, `TextStore`) read-only: judgment_id -> sha256 / doc_id / court,
text from `<repo>:<commit>:data/text/<doc_id>.txt`.
"""
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
C12_TOOLS = os.path.normpath(os.path.join(HERE, "..", "..", "C12-CONSOLIDATION", "holdings", "tools"))
if C12_TOOLS not in sys.path:
    sys.path.insert(0, C12_TOOLS)
import holdings_c12 as c12drv  # noqa: E402

AUDIT = os.path.normpath(os.path.join(HERE, "..", ".."))
DEF_REPO = "/home/user/c7"
DEF_COMMIT = "ad77758d"
# FOUO-marked Regulations for the Air Force 2000 copy: excluded from every derivative (hard rule)
EXCLUDED_SHA256 = {"4284820e5bc2fb7f52ae9fbe8a61650f1579e9b6389ba206a916a69fed016b14"}

load_corpus = c12drv.load_corpus
TextStore = c12drv.TextStore


def read_csv(p):
    with open(p, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def read_ids(path):
    ids = []
    if not path:
        return ids
    with open(path, encoding="utf-8") as f:
        for ln in f:
            ln = ln.split("#", 1)[0].strip()
            if not ln:
                continue
            ids.append(ln.split(",")[0].strip())
    return ids


def sc_scope():
    """The C12 SC scope (280 judgments with text + 4 without), reused unchanged as the C13 full-run scope."""
    p = os.path.join(AUDIT, "C12-CONSOLIDATION", "holdings", "outputs", "SCOPE_C12.csv")
    return read_csv(p)
