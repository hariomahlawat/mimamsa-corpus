"""CA-03 initial acceptance contract. Run explicitly on a disposable worktree:
python -m pytest -q legal_knowledge/audit_work/C14-CA03-PIPELINE/acceptance_relevance.py

These tests target the future adoption; failures on the C13 legacy pipeline
are expected. They do not access any corpus, network or credentials.
"""
import hashlib
import json
from pipeline.common import Paths
from pipeline import judgments

CIVIL = ("The plaintiff sued the tenant for the rent of the shop. The court "
         "heard the appeal and affirmed the order of the trial court. ") * 20

def fixture(tmp_path, text, *, shared=False):
    paths = Paths.default(tmp_path)
    paths.meta.mkdir(parents=True)
    paths.text.mkdir()
    raw = paths.data / "raw" / "case.pdf"
    raw.parent.mkdir()
    # Deliberately malformed fixture: no valid PDF page tree. Never ingest.
    original = b"%PDF-1.4\ninvalid fixture\n"
    raw.write_bytes(original)
    sha = hashlib.sha256(original).hexdigest()
    files = []
    for doc_id in (("case-a", "case-b") if shared else ("case-a",)):
        txt = paths.text / (doc_id + ".txt")
        meta = paths.meta / (doc_id + ".json")
        rec = {"doc_id": doc_id, "doc_type": "judgment", "title": "Civil case",
               "court": "Test Court", "source_url": "https://example.invalid/case.pdf",
               "retrieved_at": "2026-01-01T00:00:00Z", "sha256": sha,
               "raw_path": "data/raw/case.pdf", "text_method": "pdf_text",
               "text_path": ("data/text/" + txt.name) if text is not None else None,
               "page_count": 1, "relations": []}
        if text is not None:
            txt.write_text(text, encoding="utf-8")
            files.append((txt, txt.read_bytes()))
        meta.write_text(json.dumps(rec), encoding="utf-8")
        files.append((meta, None))
    return paths, raw, original, files

def assert_preserved(raw, original, files):
    assert raw.is_file() and raw.read_bytes() == original
    for p, content in files:
        assert p.is_file(), f"lost {p.name}"
        if content is not None:
            assert p.read_bytes() == content, f"modified {p.name}"
        else:
            assert json.loads(p.read_text(encoding="utf-8"))["relevance"]["status"] != "rejected"

def test_missing_text_retained(tmp_path):
    paths, raw, original, files = fixture(tmp_path, None)
    judgments.run(paths)
    assert_preserved(raw, original, files)

def test_garbled_text_retained(tmp_path):
    paths, raw, original, files = fixture(tmp_path, "\u0001\u0002\u0003" * 500)
    judgments.run(paths)
    assert_preserved(raw, original, files)

def test_malformed_raw_clean_text_not_negative(tmp_path):
    paths, raw, original, files = fixture(tmp_path, CIVIL)
    judgments.run(paths)
    assert_preserved(raw, original, files)

def test_shared_raw_and_aliases_retained(tmp_path):
    paths, raw, original, files = fixture(tmp_path, CIVIL, shared=True)
    judgments.run(paths)
    assert_preserved(raw, original, files)
