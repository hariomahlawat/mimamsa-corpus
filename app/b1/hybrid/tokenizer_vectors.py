"""Reference token ids from the model's own tokenizer.json (HF `tokenizers`), for the C# parity test.

  python -I tokenizer_vectors.py <model-dir> > ../tests/Mimamsa.Tests/hybrid_tokenizer_vectors.json
The strings are generic legal/military and Hindi text, not retrieval-oracle case text.
"""
import json
import re
import sys
from pathlib import Path

from tokenizers import Tokenizer

TEXTS = [
    "query: summary court martial procedure",
    "passage: 69. Civil offences.—Subject to the provisions of section 70, any person subject to this Act",
    "Disability pension attributable to or aggravated by military service (Entitlement Rules, 1982).",
    "सेना अधिनियम, 1950 की धारा 69",
    "OA 411/2021; (2013) 7 SCC 316; 2013 INSC 408 — Rule 22(3)(a)",
    "  multiple   spaces\tand\nnewlines  ",
]
tok = Tokenizer.from_file(str(Path(sys.argv[1]) / "onnx" / "tokenizer.json"))
norm = lambda t: re.sub(r"\s+", " ", t).strip()  # noqa: E731  same input convention as E5Embedder.Encode
print(json.dumps([{"text": t, "ids": tok.encode(norm(t)).ids} for t in TEXTS], ensure_ascii=False, indent=1))
