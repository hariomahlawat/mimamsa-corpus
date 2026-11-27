"""Regenerates canonical_vectors.jsonl: golden cases for the .NET port of contract canonical JSON (C16 B03).

Each line: {"input": <JSON text>, "canonical": <canonical JSON text from mimamsa_contract.c16.canonical, or null>}.
null means the Python reference refuses the value (CanonicalError, a non-finite number or an unencodable string).
Run from the repository root:  python -I app/b1/tests/Mimamsa.Tests/make_canonical_vectors.py
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "app" / "contract"))
from mimamsa_contract.c16 import canonical  # noqa: E402

CASES = [
    '{"b":1,"a":2,"c":{"z":null,"y":[true,false,null]}}',
    '"plain ascii"',
    '"quote \\" backslash \\\\ slash / tab \\t nl \\n cr \\r bs \\b ff \\f"',
    '"controls \\u0000 \\u0001 \\u001f \\u007f"',
    '"non-ascii: \\u00e9 \\u0928\\u094d\\u092f\\u093e\\u092f \\u2028 \\u2029 \\ufeff \\ufffd"',
    '"astral: \\ud83d\\ude00 \\ud834\\udd1e"',
    '"not NFC: e\\u0301"',
    '"lone surrogate \\ud800"',
    '{"\\ufffd":1,"\\ud83d\\ude00":2,"a":3,"\\u00e9":4,"Z":5}',
    '[0, -0, 1, -1, 9007199254740991, -9007199254740991]',
    '9007199254740992',
    '[0.898, 0.1, 0.0001, 1234.5, 99999999999999.9, 0.5, -2.25]',
    '[12.0, 1e2, 1E0, 1.0e3, 100.000]',
    '0.00015',
    '-0.0',
    '1e15',
    '1000000000000000.5',
    '1e400',
    'NaN',
    '[[], {}, [[{}]], ""]',
    '{"doc_id":"x\'; DROP TABLE site.app_users; --","n":1}',
]


def main():
    out = []
    for text in CASES:
        try:
            canon = canonical.canonical_bytes(json.loads(text)).decode("utf-8")
        except (canonical.CanonicalError, ValueError, UnicodeEncodeError):
            canon = None
        out.append(json.dumps({"input": text, "canonical": canon}, ensure_ascii=True, sort_keys=True))
    (pathlib.Path(__file__).parent / "canonical_vectors.jsonl").write_text("\n".join(out) + "\n", encoding="ascii", newline="\n")


if __name__ == "__main__":
    main()
