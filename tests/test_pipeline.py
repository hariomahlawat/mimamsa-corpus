"""Phase 2 pipeline tests. Section data comes from the recorded real India Code pages."""
import hashlib
import json
import shutil
from pathlib import Path

import pymupdf
import pytest

from crawler.state import StateDB
from pipeline import extract, records, report, validate
from pipeline.amendments import parse_note, split_footnotes
from pipeline.common import Paths, html_to_text, iso_date, slug
from pipeline.__main__ import main

FIX = Path(__file__).parent / "fixtures" / "indiacode_api"
API = "https://indiacode.gov.in/server/api"
ACT_UUID = "60fd2882-1df9-4b4d-8a70-3add0a9f5b6b"


# ------------------------------------------------------------------ helpers
def test_iso_date_never_guesses():
    assert iso_date("1950-05-20") == "1950-05-20" and iso_date("22-07-1950") == "1950-07-22"
    assert iso_date("6-9-1992") == "1992-09-06"
    assert iso_date("6-9-192") is None and iso_date("2026") is None and iso_date("31-02-2020") is None
    assert iso_date(None) is None


def test_html_to_text_keeps_footnote_markers():
    h = '<span style="margin-left: 15px;"></span>shall be liable, <sup>1</sup>[the Chief] &amp; others<br/><hr/> (a) one'
    assert html_to_text(h) == "shall be liable, [1][the Chief] & others\n\n(a) one"


def test_slug():
    assert slug("Army Rules,1954") == "army-rules-1954" and slug("") == "untitled"


def test_split_footnotes():
    assert split_footnotes("[1]. Subs. by Act 19 of 1955.\n[2]. Ins. by Act 37 of 1992.") == \
        ["Subs. by Act 19 of 1955.", "Ins. by Act 37 of 1992."]


@pytest.mark.parametrize("note,action,by,eff,raw", [
    ('Subs. by Act 19 of 1955, s. 2 and the Schedule, for "the Commander-in-Chief".', "substituted", "Act 19 of 1955", None, None),
    ("[Field punishment.] Omitted by the Army (Amendment) Act, 1992 (37 of 1992), s. 2 (w.e.f. 6-9-192).",
     "omitted", "Army (Amendment) Act, 1992 (37 of 1992)", None, "6-9-192"),
    ("Omitted by the Army (Amendment) Act, 1992 (37 of 1992), s. 11 (w.e.f. 6-9-1992)", "omitted",
     "Army (Amendment) Act, 1992 (37 of 1992)", "1992-09-06", None),
    ("Ins. by s. 7, ibid. (w.e.f. 16-12-1974).", "inserted", "s. 7, ibid.", "1974-12-16", None),
    ("Subs. ibid., for clause (h).", "substituted", "ibid.", None, None),
    ('The words and letter "or the land forces of a Part B State" omitted, ibid.', "omitted", "ibid.", None, None),
    ("Section 52 renumbered as sub-section (1) thereof by s. 12, ibid. (w.e.f. 16-12-1974).", "renumbered",
     "s. 12, ibid.", "1974-12-16", None),
    ("Ins. s. 6, ibid. (w.e.f. 23-6-2005).", "inserted", "s. 6, ibid.", "2005-06-23", None),
    ('Subs. Act, 48 of 1982, s. 5, for "and (2)" (w.e.f. 16-10-1982).', "substituted", "Act, 48 of 1982",
     "1982-10-16", None),
    ("Subs. by Act 53 of 1974, s. 3 (w.e.f. 16-12-74).", "substituted", "Act 53 of 1974", None, "16-12-74"),
    ("Rep. by the Repealing and Amending Act, 1957 (36 of 1957), s. 2 and the First Schedule.", "repealed",
     "Repealing and Amending Act, 1957 (36 of 1957)", None, None),
])
def test_parse_note(note, action, by, eff, raw):
    e = parse_note(note, "footnote")
    assert (e["action"], e["by_ref_raw"], e["effective_date"], e["effective_date_raw"]) == (action, by, eff, raw)
    assert e["footnote_text"] == note and e["confidence"] == "extracted"


def test_commencement_note_is_not_an_amendment():
    assert parse_note("22nd July, 1950, vide notification No. S.R.O. 120, dated the 22nd July, 1950.", "footnote") is None


# ----------------------------------------------- a small corpus on disk
def make_pdf(path: Path, pages: list[str], watermark: bool = True) -> None:
    doc = pymupdf.open()
    for text in pages:
        page = doc.new_page()
        if text:
            page.insert_textbox(pymupdf.Rect(50, 50, 550, 780), text, fontsize=10)
        if watermark:
            page.insert_text(pymupdf.Point(150, 500), "IndiaCode", fontsize=30,
                             morph=(pymupdf.Point(150, 500), pymupdf.Matrix(45)))
    doc.save(path)
    doc.close()


ENGLISH = ("Subject to the provisions of this Act, any person who is subject to the Act shall be liable to be tried "
           "by a court-martial for any offence under the Act, and such person shall be dealt with in the manner "
           "provided by the rules made under this Act. ") * 3


@pytest.fixture
def corpus(tmp_path):
    """Crawl state + raw files as the crawler leaves them: the three recorded Army Act pages,
    an Act PDF, a second (empty, scan-like) file and the Army Rules PDF."""
    paths = Paths.default(tmp_path)
    index = json.loads((FIX / "index.json").read_text())
    rule_uuid = None
    with StateDB(paths.db) as db:
        def add(url, content: bytes, ext, ctype, hint=None, **meta):
            sha = hashlib.sha256(content).hexdigest()
            rel = f"data/raw/indiacode/1950/{sha}{ext}"
            (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
            (tmp_path / rel).write_bytes(content)
            db.enqueue(url, "indiacode", "indiacode.gov.in", "document", doc_id_hint=hint,
                       meta={"parent_doc_id": "act-army-1950", **meta})
            db.record_file(sha256=sha, raw_path=rel, url=url, nbytes=len(content), content_type=ctype)
            db.mark_fetched(url, status_code=200, sha256=sha, nbytes=len(content), content_type=ctype)

        for url, entry in index.items():
            if "f.act_id=" not in url:
                continue
            body = (FIX / entry["file"]).read_bytes()
            add(url, body, ".json", "application/hal+json", category="linked_records")
            for o in json.loads(body)["_embedded"]["searchResult"]["_embedded"]["objects"]:
                rec = o["_embedded"]["indexableObject"]
                if rec["metadata"]["dc.identifier.collection"][0]["value"] == "RULE":
                    rule_uuid = rec["uuid"]
        pdf = tmp_path / "tmp.pdf"
        make_pdf(pdf, ["For Official Use Only\n\n" + ENGLISH, ENGLISH, ""])
        add(f"{API}/core/bitstreams/act/content", pdf.read_bytes(), ".pdf", "application/pdf", hint="act-army-1950",
            category="act", filename="a1950-46.pdf", language_by_filename="en", item_uuid=ACT_UUID)
        make_pdf(pdf, ["", "", ""], watermark=False)
        add(f"{API}/core/bitstreams/hindi/content", pdf.read_bytes(), ".pdf", "application/pdf",
            category="act", filename="H195046.pdf", language_by_filename="hi", item_uuid=ACT_UUID)
        make_pdf(pdf, [ENGLISH])
        add(f"{API}/core/bitstreams/rules/content", pdf.read_bytes(), ".pdf", "application/pdf",
            category="rule", filename="armyrules1954.pdf", item_uuid=rule_uuid)
        pdf.unlink()
    return paths


def load(paths, rel):
    return json.loads((paths.data / rel).read_text(encoding="utf-8"))


def test_records_from_real_army_act_pages(corpus):
    res = records.build_indiacode(corpus)
    assert res["problems"] == [] and res["sections"] == 198 and res["documents"] == 3
    act = load(corpus, "meta/act-army-1950.json")
    assert act["title"] == "The Army Act, 1950" and act["number"] == "46 of 1950"
    assert act["issue_date"] == "1950-05-20" and act["effective_date"] == "1950-07-22"
    assert act["status"] == "amended" and act["language"] == "en" and act["parent_doc_id"] is None
    assert act["source_record"]["record_id"] == ACT_UUID
    hindi = load(corpus, "meta/act-army-1950-hi.json")
    assert hindi["parent_doc_id"] == "act-army-1950" and hindi["language"] == "hi"
    rules = load(corpus, "meta/rules-army-rules-1954.json")
    assert rules["doc_type"] == "rules" and rules["issue_date"] == "1954-11-27"
    assert rules["relations"][0]["type"] == "implements" and rules["relations"][0]["target_doc_id"] == "act-army-1950"

    s75 = load(corpus, "sections/act-army-1950/s75.json")
    assert s75["status"] == "omitted" and "37 of 1992" in s75["status_note"]
    h = s75["amendment_history"][0]
    assert h["action"] == "omitted" and h["origin"] == "inline"
    assert h["effective_date"] is None and h["effective_date_raw"] == "6-9-192"      # source typo kept, not fixed
    s127 = load(corpus, "sections/act-army-1950/s127.json")
    assert s127["status"] == "omitted" and s127["amendment_history"][0]["effective_date"] == "1992-09-06"
    s69 = load(corpus, "sections/act-army-1950/s69.json")
    assert s69["status"] == "in_force" and s69["heading"] == "Civil offences." and s69["text"].startswith("Subject to")
    s96 = load(corpus, "sections/act-army-1950/s96.json")
    assert s96["status"] == "amended" and s96["amendment_history"][0]["by_ref_raw"] == "Act 19 of 1955"
    assert "[1][the Chief of the Army Staff]" in s96["text"]
    edges = [json.loads(l) for l in (corpus.data / "relations.jsonl").read_text().splitlines()]
    assert any(e["source_doc_id"] == "act-army-1950#s75" and e["type"] == "amended_by" for e in edges)


def test_extract_drops_watermark_marks_pages_and_flags_scans(corpus):
    records.build_indiacode(corpus)
    stats = extract.run(corpus)
    assert stats["extracted"] == 2 and stats["needs_ocr"] == 1 and stats["errors"] == []
    act = load(corpus, "meta/act-army-1950.json")
    text = (corpus.root / act["text_path"]).read_text()
    assert "[[page 1]]" in text and "[[page 3]]" in text and "IndiaCode" not in text
    assert "court-martial" in text
    assert act["text_method"] == "pdf_text" and act["text_quality"] == "ok" and act["page_count"] == 3
    assert act["pages_without_text"] == [3] and act["access_marking"].lower() == "for official use only"
    hindi = load(corpus, "meta/act-army-1950-hi.json")
    assert hindi["needs_ocr"] is True and hindi["text_method"] is None and hindi["text_path"] is None
    assert not (corpus.text / "act-army-1950-hi.txt").exists()                # no text kept for a scan
    # the word inside a sentence is not a marking
    assert extract.MARKING.search("includes confidential\nNavy Orders.") is None


def test_records_rerun_keeps_extraction_results(corpus):
    records.build_indiacode(corpus)
    extract.run(corpus)
    records.build_indiacode(corpus)
    assert load(corpus, "meta/act-army-1950.json")["text_method"] == "pdf_text"


def test_validate_passes_then_catches_damage(corpus):
    records.build_indiacode(corpus)
    extract.run(corpus)
    assert validate.run(corpus)["errors"] == []
    p = corpus.meta / "rules-army-rules-1954.json"
    rec = json.loads(p.read_text())
    rec["issue_date"] = "27-11-1954"
    rec["sha256"] = "0" * 64
    p.write_text(json.dumps(rec))
    shutil.rmtree(corpus.sections / "act-army-1950")
    (corpus.sections / "act-army-1950").mkdir()
    errs = validate.run(corpus)["errors"]
    assert any("issue_date" in e for e in errs) and any("does not match its sha256" in e for e in errs)
    assert any("unknown source" in e for e in errs)                           # edges from sections that are gone


def test_cli_all_writes_manifest_and_report(corpus, capsys):
    assert main(["all", "--root", str(corpus.root)]) == 0
    manifest = (corpus.data / "manifest.csv").read_text().splitlines()
    assert manifest[0] == "doc_id,type,status,source_url,sha256,retrieved_at" and len(manifest) == 4
    rep = (corpus.reports / "phase2_report.md").read_text()
    assert "[x] Field punishment (s.75) omitted in 1992" in rep and "act-army-1950-hi" in rep
    assert "`6-9-192`" in rep


# ---------------------------------------------------------------------- OCR
from pipeline import ocr  # noqa: E402


def _w(text, box, conf=90.0, line=(1, 1, 1)):
    return {"text": text, "conf": conf, "box": box, "line": line}


def test_merge_numbers_takes_digits_from_the_second_pass_only():
    base = [_w("जुलाई,", (0, 0, 100, 40)), _w("200", (110, 0, 200, 40)), _w("3]", (210, 0, 250, 40)),
            _w("प्रदत्त", (260, 0, 360, 40)), _w("2007", (370, 0, 450, 40))]
    alt = [_w("जुलाई,", (0, 0, 100, 40)), _w("2010", (108, 0, 202, 40), conf=80.0), _w("31", (210, 0, 250, 40)),
           _w("Wed", (260, 0, 360, 40)), _w("2007", (370, 0, 450, 40)),
           _w("1999", (110, 400, 200, 440))]                      # same column, another line: must not be used
    assert ocr.merge_numbers(base, alt) == 2
    assert [w["text"] for w in base] == ["जुलाई,", "2010", "31", "प्रदत्त", "2007"]
    assert base[1]["conf"] == 80.0                                # the lower confidence of the two readings


def test_parse_tsv_groups_lines_and_drops_watermark():
    head = "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"
    rows = ["5\t1\t1\t1\t1\t1\t0\t0\t10\t10\t90\tArmed", "5\t1\t1\t1\t1\t2\t12\t0\t10\t10\t70\tForces",
            "5\t1\t1\t1\t2\t1\t0\t12\t10\t10\t80\tTribunal", "5\t1\t2\t1\t1\t1\t0\t40\t10\t10\t60\tIndiaCode",
            "5\t1\t2\t1\t1\t2\t12\t40\t10\t10\t40\tAct", "4\t1\t2\t1\t1\t0\t0\t40\t30\t10\t-1\t"]
    text, conf, n = ocr.parse_tsv(head + "\n".join(rows) + "\n")
    assert text == "Armed Forces\nTribunal\n\nAct" and n == 4 and conf == 70.0


@pytest.mark.skipif(ocr.tesseract_version() is None, reason="tesseract not installed")
def test_ocr_reads_a_scanned_document_and_resumes(corpus, monkeypatch):
    records.build_indiacode(corpus)
    # Replace the "Hindi" file with an image-only scan of English text.
    hindi = load(corpus, "meta/act-army-1950-hi.json")
    src = pymupdf.open()
    page = src.new_page()
    page.insert_textbox(pymupdf.Rect(60, 60, 540, 700), "Armed Forces Tribunal Act, 2007\n\n" + ENGLISH, fontsize=13)
    pix = page.get_pixmap(dpi=200)
    scan = pymupdf.open()
    spage = scan.new_page(width=page.rect.width, height=page.rect.height)
    spage.insert_image(spage.rect, pixmap=pix)
    spage2 = scan.new_page()                                       # a blank page
    raw = corpus.raw_file(hindi["raw_path"])
    scan.save(raw)
    hindi["sha256"] = hashlib.sha256(raw.read_bytes()).hexdigest()
    (corpus.meta / "act-army-1950-hi.json").write_text(json.dumps(hindi))
    extract.run(corpus, ["act-army-1950-hi"])
    assert load(corpus, "meta/act-army-1950-hi.json")["needs_ocr"] is True

    stats = ocr.run(corpus, workers=2, langs="eng", dpi=200)
    assert stats["errors"] == [] and stats["documents"] == 1 and stats["pages"] == 2
    meta = load(corpus, "meta/act-army-1950-hi.json")
    assert meta["text_method"] == "ocr" and meta["needs_ocr"] is False and meta["ocr_confidence"] > 80
    assert meta["pages_without_text"] == [2]
    text = (corpus.root / meta["text_path"]).read_text()
    assert "[[page 1]]" in text and "Armed Forces Tribunal Act, 2007" in text and "court-martial" in text
    assert (corpus.reports / "ocr_review.md").exists()

    # Second run: pages come from the cache, tesseract is not called again.
    def boom(*a, **k):
        raise AssertionError("tesseract called despite cache")
    meta["needs_ocr"] = True
    (corpus.meta / "act-army-1950-hi.json").write_text(json.dumps(meta))
    real_run = ocr.subprocess.run
    monkeypatch.setattr(ocr.subprocess, "run", lambda cmd, **k: real_run(cmd, **k) if "--version" in cmd else boom())
    assert ocr.run(corpus, workers=1, langs="eng", dpi=200)["pages"] == 2
    monkeypatch.undo()
    assert validate.run(corpus, check_files=False)["errors"] == []


def test_low_confidence_pages_are_listed_not_hidden(corpus, monkeypatch):
    records.build_indiacode(corpus)
    extract.run(corpus)
    monkeypatch.setattr(ocr, "tesseract_version", lambda: "tesseract (test)")
    monkeypatch.setattr(ocr, "ocr_page", lambda pdf, i, cache, langs, dpi: {
        "page": i + 1, "text": "readable text" if i == 0 else "g@rb1e", "confidence": 91.0 if i == 0 else 42.0,
        "words": 2})
    stats = ocr.run(corpus)
    meta = load(corpus, "meta/act-army-1950-hi.json")
    assert meta["ocr_low_confidence_pages"] == [2, 3] and meta["text_quality"] == "suspect"
    assert stats["low_confidence_pages"] == 2
    assert "p.2 (42)" in (corpus.reports / "ocr_review.md").read_text()
