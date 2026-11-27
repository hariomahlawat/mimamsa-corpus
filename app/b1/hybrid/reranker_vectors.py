"""Reference PAIR token ids from the reranker's own tokenizer.json (HF `tokenizers`), for the C# parity test.

  python -I reranker_vectors.py <model-dir> ../tests/Mimamsa.Tests/reranker_tokenizer_vectors.json
Pairs are generic legal/military and Hindi text, not retrieval-oracle case text. Truncation is not exercised here
(the C# side truncates the passage, never the query, to its token budget).
"""
import json
import re
import sys
from pathlib import Path

from tokenizers import Tokenizer

PAIRS = [
    ("absence without leave punishment", "39. Absence without leave.—Any person subject to this Act who absents himself without leave"),
    ("how to hold a summary court martial", "116. Summary court-martial.—(1) A summary court-martial may be held by the commanding officer"),
    ("disability pension attributable to military service", "Disability pension attributable to or aggravated by military service (Entitlement Rules, 1982)."),
    ("सेना अधिनियम धारा 69", "सेना अधिनियम, 1950 की धारा 69"),
    ("OA 411/2021", "OA 411/2021; (2013) 7 SCC 316; 2013 INSC 408 — Rule 22(3)(a)"),
]
tok = Tokenizer.from_file(str(Path(sys.argv[1]) / "tokenizer.json"))
tok.no_truncation()
norm = lambda t: re.sub(r"\s+", " ", t).strip()  # noqa: E731  same input convention as CrossEncoder
Path(sys.argv[2]).write_text(json.dumps([{"query": q, "passage": p, "ids": tok.encode(norm(q), norm(p)).ids} for q, p in PAIRS], ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
