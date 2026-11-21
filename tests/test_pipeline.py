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


# ------------------------------------------------- repealed central Acts
def test_repeal_title_pattern():
    m = records.REPEAL_TITLE.match("The Code of Criminal Procedure 1973, 02 of 1974 (Rep., Act 46 of 2023)")
    assert (m.group("title"), m.group("no"), m.group("year"), m.group("by")) == \
        ("The Code of Criminal Procedure 1973", "02", "1974", "Act 46 of 2023")
    assert records.REPEAL_TITLE.match("The Army Act, 1950") is None


def test_repealed_record_becomes_a_repealed_act_with_an_edge(corpus):
    pdf = corpus.root / "tmp.pdf"
    make_pdf(pdf, [ENGLISH])
    body = pdf.read_bytes()
    pdf.unlink()
    sha = hashlib.sha256(body).hexdigest()
    rel = f"data/raw/indiacode/1911/{sha}.pdf"
    (corpus.root / rel).parent.mkdir(parents=True, exist_ok=True)
    (corpus.root / rel).write_bytes(body)

    def add(db, doc_id, name, by):
        url = f"{API}/core/bitstreams/{doc_id}/content"
        db.enqueue(url, "indiacode", "indiacode.gov.in", "document", doc_id_hint=doc_id, meta={
            "parent_doc_id": doc_id, "category": "act", "filename": "A1911-8.pdf", "language_by_filename": "en",
            "item_uuid": "u-" + doc_id,
            "repeal_record": {"title": f"{name} (Rep., {by})", "handle": "123456789/1", "date_issued": "1911",
                              "state_name": None, "collection_name": "Repeal Acts"}})
        db.record_file(sha256=sha, raw_path=rel, url=url, nbytes=len(body), content_type="application/pdf")
        db.mark_fetched(url, status_code=200, sha256=sha, nbytes=len(body), content_type="application/pdf")
    with StateDB(corpus.db) as db:
        add(db, "act-indian-army-1911", "The Indian Army Act, 8 of 1911", "Act 46 of 1950")      # repealer in corpus
        add(db, "act-old-thing-1850", "Old Thing Act, 6 of 1850", "Act 29 of 1861")              # repealer not in corpus
    res = records.build_indiacode(corpus)
    assert res["problems"] == []
    old = load(corpus, "meta/act-indian-army-1911.json")
    assert old["status"] == "repealed" and old["title"] == "The Indian Army Act" and old["number"] == "8 of 1911"
    assert old["issue_date"] is None and "Repeal Acts" in old["status_note"]              # a bare year is not a date
    army = load(corpus, "meta/act-army-1950.json")
    e = [r for r in army["relations"] if r["type"] == "repeals"][0]
    assert e["target_doc_id"] == "act-indian-army-1911" and e["target_ref_raw"] == "Act 46 of 1950"
    orphan = load(corpus, "meta/act-old-thing-1850.json")["relations"][0]
    assert orphan["type"] == "superseded_by" and orphan["target_doc_id"] is None and orphan["target_ref_raw"] == "Act 29 of 1861"
    assert validate.run(corpus)["errors"] == []


# ------------------------------------------- sections cut from a PDF
from pipeline import split_pdf  # noqa: E402


def make_act_pdf(path: Path, drop: tuple = ()) -> None:
    """A small Act in the Legislative Department layout: table of sections, bold section numbers,
    superscript markers, footnotes in small type, a watermark."""
    doc = pymupdf.open()
    toc = doc.new_page()
    y = 60
    for line in ["THE SAMPLE ACT, 1900", "ARRANGEMENT OF SECTIONS", "CHAPTER I", "PRELIMINARY", "SECTIONS",
                 "1. Short title.", "2. [Repealed.]", "3. Definitions.", "CHAPTER II", "OFFENCES", "4. Punishment.",
                 "4A. Abetment.", "5. Saving."]:
        toc.insert_text((72, y), line, fontsize=11)
        y += 16

    def section(page, y, num, head, body, marker=None, bold=True, sep=".--"):
        x = 90
        if marker:
            page.insert_text((x, y - 3), marker, fontsize=7)
            x += 5
            page.insert_text((x, y), "[", fontsize=11)
            x += 4
        first = f"{num}. {head}" if head else f"{num}."
        page.insert_text((x, y), first, fontsize=11, fontname="hebo" if bold else "helv")
        w = pymupdf.get_text_length(first, fontname="hebo" if bold else "helv", fontsize=11)
        page.insert_text((x + w, y), f"{sep}{body}" if head else f" {body}", fontsize=11)

    p = doc.new_page()
    p.insert_text((230, 50), "THE SAMPLE ACT, 1900", fontsize=12)
    p.insert_text((250, 66), "ACT NO. 7 OF 1900", fontsize=12)
    p.insert_text((270, 90), "CHAPTER I", fontsize=11)
    p.insert_text((265, 104), "PRELIMINARY", fontsize=11)
    section(p, 130, "1", "Short title", "This Act may be called the Sample Act, 1900.")
    p.insert_text((90, 150), "2. [Repeal of enactments.] Rep. by the Repealing Act, 1938 (1 of 1938), s. 2.", fontsize=11)
    if "3" not in drop:
        section(p, 170, "3", "Definitions", "In this Act, court includes every tribunal")
        p.insert_text((72, 184), "and every officer acting judicially.", fontsize=11)
        p.insert_text((330, 181), "1", fontsize=7)
        p.insert_text((336, 184), "[or under the Army Act]", fontsize=11)
    p.insert_text((72, 700), "1. Ins. by Act 10 of 1927, s. 2 (w.e.f. 1-4-1927).", fontsize=9)
    p.insert_text((300, 800), "2", fontsize=11)
    q = doc.new_page()
    q.insert_text((270, 60), "CHAPTER II", fontsize=11)
    q.insert_text((275, 74), "OFFENCES", fontsize=11)
    section(q, 100, "4", "Punishment", "Whoever offends shall be punished with fine.")
    q.insert_text((108, 116), "1. the first of a numbered list inside the section, in body type", fontsize=11)
    section(q, 140, "4A", "Abetment", "Whoever abets an offence shall be punished likewise.]", marker="1")
    section(q, 160, "5", "Saving", "Nothing in this Act affects any other law.")
    q.insert_text((72, 700), "1. Ins. by Act 3 of 1951, s. 4 (w.e.f. 1-4-1951).", fontsize=9)
    for page in list(doc)[1:]:
        page.insert_text(pymupdf.Point(150, 500), "IndiaCode", fontsize=30,
                         morph=(pymupdf.Point(150, 500), pymupdf.Matrix(45)))
    doc.save(path)
    doc.close()


def test_split_pdf_follows_the_acts_own_table(tmp_path):
    pdf = tmp_path / "act.pdf"
    make_act_pdf(pdf)
    secs, st = split_pdf.split_pdf(pdf, "act-sample-1900", "The Act is repealed.")
    assert st["reason"] is None and st["toc_sections"] == 6 and st["found"] == 6 and st["missing"] == []
    by = {s["number"]: s for s in secs}
    assert list(by) == ["1", "2", "3", "4", "4A", "5"]
    assert by["1"]["heading"] == "Short title." and by["1"]["text"] == "This Act may be called the Sample Act, 1900."
    assert by["1"]["chapter"] == {"number": "I", "title": "PRELIMINARY"} and by["4"]["chapter"]["title"] == "OFFENCES"
    assert by["1"]["status"] == "repealed" and by["1"]["status_note"] == "The Act is repealed."
    assert by["2"]["heading"] == "[Repeal of enactments]" and by["2"]["amendment_history"][0]["action"] == "repealed"
    assert by["2"]["amendment_history"][0]["origin"] == "inline" and "Repealing Act, 1938" in by["2"]["status_note"]
    # wrapped line joined, superscript kept as a marker, its footnote attached, watermark and footnote text excluded
    assert "tribunal and every officer acting judicially. [1][or under the Army Act]" in by["3"]["text"]
    h = by["3"]["amendment_history"][0]
    assert (h["action"], h["by_ref_raw"], h["effective_date"]) == ("inserted", "Act 10 of 1927", "1927-04-01")
    assert "IndiaCode" not in json.dumps(secs) and "Ins. by Act 10" not in by["3"]["text"]
    # a numbered list inside section 4 does not start a new section; 4A's marker is page-local
    assert "1. the first of a numbered list" in by["4"]["text"]
    assert by["4A"]["amendment_history"][0]["by_ref_raw"] == "Act 3 of 1951" and by["4A"]["page_start"] == 3
    assert by["4A"]["section_id"] == "act-sample-1900#s4a"


def test_split_pdf_writes_nothing_when_the_table_is_not_matched(tmp_path):
    pdf = tmp_path / "act.pdf"
    make_act_pdf(pdf, drop=("3",))
    secs, st = split_pdf.split_pdf(pdf, "act-sample-1900")
    assert secs == [] and st["found"] == 5 and st["missing"] == ["3"] and "nothing written" in st["reason"]
    scan = tmp_path / "scan.pdf"
    make_pdf(scan, [ENGLISH, ENGLISH])
    secs, st = split_pdf.split_pdf(scan, "act-x")
    assert secs == [] and "ACT NO" in st["reason"]


def test_split_stage_writes_valid_sections_and_edges(corpus):
    pdf = corpus.root / "tmp.pdf"
    make_act_pdf(pdf)
    body = pdf.read_bytes()
    pdf.unlink()
    sha = hashlib.sha256(body).hexdigest()
    rel = f"data/raw/indiacode/1900/{sha}.pdf"
    (corpus.root / rel).parent.mkdir(parents=True, exist_ok=True)
    (corpus.root / rel).write_bytes(body)
    with StateDB(corpus.db) as db:
        url = f"{API}/core/bitstreams/sample/content"
        db.enqueue(url, "indiacode", "indiacode.gov.in", "document", doc_id_hint="act-sample-1900", meta={
            "parent_doc_id": "act-sample-1900", "category": "act", "filename": "A1900-7.pdf",
            "language_by_filename": "en", "item_uuid": "u-sample",
            "repeal_record": {"title": "The Sample Act, 7 of 1900 (Rep., Act 46 of 1950)", "handle": None,
                              "date_issued": "1900", "state_name": None, "collection_name": "Repeal Acts"}})
        db.record_file(sha256=sha, raw_path=rel, url=url, nbytes=len(body), content_type="application/pdf")
        db.mark_fetched(url, status_code=200, sha256=sha, nbytes=len(body), content_type="application/pdf")
    assert main(["all", "--root", str(corpus.root)]) == 0
    s3 = load(corpus, "sections/act-sample-1900/s3.json")
    assert s3["status"] == "repealed" and "Rep., Act 46 of 1950" in s3["status_note"]
    edges = [json.loads(l) for l in (corpus.data / "relations.jsonl").read_text().splitlines()]
    assert any(e["source_doc_id"] == "act-sample-1900#s3" and e["target_ref_raw"] == "Act 10 of 1927" for e in edges)
    assert any(e["source_doc_id"] == "act-army-1950#s75" for e in edges)          # the other Acts' edges survive
    # the Army Act has section records from its source, so it is not cut from the PDF
    assert load(corpus, "sections/act-army-1950/s69.json")["source_record"] is not None
    rep = (corpus.reports / "phase2_report.md").read_text()
    assert "| act-sample-1900 | 6 | 6 |" in rep
    assert main(["all", "--root", str(corpus.root)]) == 0                           # re-run: no duplicate edges
    again = (corpus.data / "relations.jsonl").read_text().splitlines()
    assert len(again) == len(edges)


# ------------------------------------------- correspondence tables
from pipeline import correspondence  # noqa: E402


def test_section_numbers_and_ref_cleaning():
    sn = correspondence.section_numbers
    assert sn("68 & 69") == ["68", "69"] and sn("2(1)(t)") == ["2"] and sn("New") == []
    assert sn("376AB, 376DA and 376DB") == ["376AB", "376DA", "376DB"] and sn("53A") == ["53A"]
    assert sn("Section 6 r/w 7") == ["6", "7"]
    assert correspondence.clean_ref("2(r )") == "2(r)" and correspondence.clean_ref("103 (1)") == "103(1)"
    assert correspondence.clean_ref("68 & 69") == "68 & 69"


def test_correspondence_rows_from_a_table(corpus, monkeypatch, tmp_path):
    records.build_indiacode(corpus)
    cfgfile = tmp_path / "sources.yaml"
    cfgfile.write_text(json.dumps({"sources": {"x": {"documents": [
        {"doc_id": "rules-army-rules-1954", "correspondence": {"key": "new-old", "new": "act-army-1950",
                                                                 "old": "act-army-1950",
                                                                 "columns": ["new", "subject", "old", "summary"]}},
        {"doc_id": "ref-not-downloaded", "correspondence": {"key": "missing", "new": "a", "old": "b",
                                                             "columns": ["new", "subject", "old", "summary"]}}]}}}))
    monkeypatch.setattr(correspondence, "read_table", lambda path, cols: [
        {"new": "69", "old": "75 & 76", "subject": "Civil offences.", "summary": "No change.", "page": 2},
        {"new": "70(2)", "old": "New", "subject": "Something new.", "summary": "New provision.", "page": 3},
        {"new": "999", "old": "see note", "subject": "Odd row.", "summary": "", "page": 3}])
    res = correspondence.run(corpus, cfgfile)
    assert res["missing"]["rows"] == 0 and "not in the corpus" in res["missing"]["reason"]
    st = res["new-old"]
    assert st["rows"] == 3 and st["new_provisions"] == 1 and st["rows_without_old_reference"] == 1
    assert st["new_sections_not_in_corpus"] == ["999"] and st["old_sections_not_in_corpus"] == []
    rows = [json.loads(l) for l in (corpus.data / "correspondence" / "new-old.jsonl").read_text().splitlines()]
    assert rows[0]["old_sections"] == ["75", "76"] and rows[0]["new_section"] == "69" and rows[0]["confidence"] == "extracted"
    assert rows[1]["is_new"] is True and rows[1]["old_sections"] == [] and rows[1]["new_section"] == "70"
    assert validate.run(corpus)["errors"] == [] and validate.run(corpus)["correspondence_rows"] == 3
