"""C13 A1: explicit relevance states and the text-quality detector (fast, no PDFs, no network)."""
from __future__ import annotations

from pipeline import relevance_states as rs
from pipeline import text_quality as tq

ENGLISH = ("The petitioner was enrolled in the service and the respondents passed the order under the rules. "
           "Learned counsel for the petitioner submits that the order is bad in law and that the court should set "
           "it aside, since the provisions of the rules were not followed by the authority concerned. ") * 6
AFT_TEXT = ("This writ petition challenges the order of the Armed Forces Tribunal, Regional Bench, Chandigarh. "
            "The petitioner, a Havildar, was invalided out and claims disability pension under the Entitlement Rules. ") * 4
NO_KW_MILITARY = ("The petitioner, a Havildar of the Indian Army, was discharged by the Records Office. "
                  "He claims service pension as an ex-serviceman and the Ministry of Defence opposed the claim. ") * 6
CIVIL = ("The plaintiff sued for recovery of rent of a shop in the market. The trial court decreed the suit and "
         "the first appellate court affirmed the decree; this second appeal is by the tenant who was the defendant. ") * 6


def ok_quality(text):
    return {"verdict": "TEXT_OK", "usable_share": 1.0, "unusable_pages": [], "flags": []}


def decide_ok(text, **kw):
    """decide() with complete quality data and OCR quality established (the only route to IRRELEVANT)."""
    return rs.decide(text=text, quality=ok_quality(text), ocr_quality_ok=True, **kw)


def bad_quality():
    return {"verdict": "OCR_REQUIRED", "usable_share": 0.0, "unusable_pages": [1, 2], "flags": ["control_chars"]}


# ----------------------------------------------------------------- detector
def test_clean_english_page_is_usable():
    v = tq.page_verdict(ENGLISH)
    assert v["usable"], v


def test_control_char_glyph_ids_flagged():
    garbled = "".join(chr(1 + (i % 30)) for i in range(400)) + " I attest to the accuracy and integrity of this document"
    v = tq.page_verdict(garbled)
    assert not v["usable"] and "control_chars" in v["flags"]


def test_private_use_and_cid_flagged():
    assert "private_use" in tq.page_verdict(" " * 60)["flags"]
    assert "cid_glyphs" in tq.page_verdict("(cid:12)(cid:45)(cid:3) " * 40)["flags"]


def test_image_only_and_blank():
    assert tq.page_verdict("", image_cover=0.95)["flags"] == ["image_only"]
    assert tq.page_verdict("", image_cover=0.0)["flags"] == ["blank"]


def test_low_dictionary_and_implausible():
    gibberish = " ".join("qzxv bnmk rtps lkjh wqrt" for _ in range(60))
    v = tq.page_verdict(gibberish)
    assert not v["usable"] and ("low_dictionary" in v["flags"] or "implausible_chars" in v["flags"])


def test_reversed_order_flagged():
    rev = " ".join(w[::-1] for w in ENGLISH.split())
    assert "reversed_order" in tq.page_verdict(rev)["flags"]


def test_vertical_order_flagged():
    vertical = "\n".join(ch for ch in ENGLISH[:300] if not ch.isspace())
    assert "vertical_order" in tq.page_verdict(vertical)["flags"]


def test_devanagari_page_is_not_a_defect():
    hindi = "यह याचिका भारतीय सेना के एक सिपाही द्वारा दायर की गई है और न्यायालय ने आदेश पारित किया " * 6
    v = tq.page_verdict(hindi)
    assert v["usable"] and "non_latin_ok" in v["flags"]


def test_truncation_detected_from_bytes():
    assert tq.has_eof(b"%PDF-1.4 ... trailer\n%%EOF\n")
    assert not tq.has_eof(b"%PDF-1.4 ... stream data cut off")


def test_document_summary_rollup():
    a = {"truncated": False, "page_errors": [], "open_error": None,
         "pages": [{"page": 1, **tq.page_verdict(ENGLISH)}, {"page": 2, **tq.page_verdict("", 0.9)}]}
    s = tq.document_summary(a)
    assert s["verdict"] == "OCR_REQUIRED" and s["unusable_pages"] == [2] and s["usable_share"] == 0.5
    assert tq.document_summary({"pages": [], "open_error": "x"})["verdict"] == "EXTRACTION_FAILED"


# ----------------------------------------------------------------- states
def test_all_states_declared():
    assert set(rs.STATES) == {"RELEVANT", "IRRELEVANT", "INSUFFICIENT_TEXT", "OCR_REQUIRED", "EXTRACTION_FAILED",
                              "CLASSIFICATION_UNCERTAIN", "SOURCE_INCOMPLETE", "MANUAL_REVIEW_REQUIRED"}


def test_relevant_by_keywords():
    d = rs.decide(text=AFT_TEXT, quality=ok_quality(AFT_TEXT))
    assert d["state"] == "RELEVANT"


def test_garbled_text_is_never_irrelevant():
    garbled = "".join(chr(1 + (i % 30)) for i in range(4000))
    d = rs.decide(text=garbled, quality=bad_quality(), ocr_done=False)
    assert d["state"] == "OCR_REQUIRED" and not rs.may_remove(d)
    d2 = rs.decide(text=garbled, quality=bad_quality(), ocr_done=True)
    assert d2["state"] == "INSUFFICIENT_TEXT" and not rs.may_remove(d2)


def test_empty_text_is_never_irrelevant():
    for q in (None, bad_quality(), {"verdict": "TEXT_OK", "usable_share": 1.0}):
        d = rs.decide(text="", quality=q)
        assert d["state"] != "IRRELEVANT"


def test_extraction_failure_and_truncation():
    assert rs.decide(text=None, quality=None, extraction_error="bad xref")["state"] == "EXTRACTION_FAILED"
    assert rs.decide(text=CIVIL, quality=ok_quality(CIVIL), truncated=True)["state"] == "SOURCE_INCOMPLETE"
    # positive evidence in a truncated file still counts
    assert rs.decide(text=AFT_TEXT, quality=ok_quality(AFT_TEXT), truncated=True)["state"] == "RELEVANT"


def test_no_keyword_but_military_context_goes_to_review():
    d = decide_ok(NO_KW_MILITARY)
    assert d["state"] == "MANUAL_REVIEW_REQUIRED" and not rs.may_remove(d)
    assert len(d["second_check"]["strong_families"]) >= 2


def test_civil_case_with_usable_text_is_irrelevant():
    d = decide_ok(CIVIL)
    assert d["state"] == "IRRELEVANT" and rs.may_remove(d)


def test_short_text_is_insufficient():
    d = rs.decide(text="Order. Dismissed.", quality=ok_quality(""))
    assert d["state"] == "INSUFFICIENT_TEXT"


def test_partial_usable_text_not_irrelevant():
    q = _q(0.5, [3, 4])
    assert rs.decide(text=CIVIL, quality=q, ocr_done=False)["state"] == "OCR_REQUIRED"


def test_legacy_mapping_never_rejects_non_final_states():
    for state in rs.STATES:
        d = {"state": state, "keyword_status": "rejected", "keywords": {}, "reasons": ["x"]}
        r = rs.legacy_relevance(d)
        assert (r["status"] == "rejected") == (state == "IRRELEVANT")
        assert set(r) == {"status", "hits", "keywords", "note"}


def test_aft_abbreviation_case_sensitive():
    assert "aft_proceeding" not in rs.second_check("we left after lunch; aft deck")["families"]
    assert "aft_proceeding" in rs.second_check("order of the AFT dated")["families"]


def test_ink_without_placed_images_is_a_scan_not_blank():
    # v1 defect: scans drawn as inline images / XObjects reported no image cover and were called blank
    assert tq.page_verdict("", image_cover=0.0, ink=0.08)["flags"] == ["image_only"]
    assert tq.page_verdict("", image_cover=0.0, ink=0.0005)["flags"] == ["blank"]


# ---- review A1-02: IRRELEVANT only when every content page has usable text
def _q(share, unusable, verdict="OCR_REQUIRED"):
    return {"verdict": verdict, "usable_share": share, "unusable_pages": unusable, "flags": ["image_only"]}


def test_eighty_percent_share_without_ocr_is_not_irrelevant():
    d = rs.decide(text=CIVIL, quality=_q(0.8, [1]), ocr_done=False)
    assert d["state"] == "OCR_REQUIRED" and not rs.may_remove(d)


def test_ninety_nine_percent_share_without_ocr_is_not_irrelevant():
    d = rs.decide(text=CIVIL, quality=_q(0.99, [57]), ocr_done=False)
    assert d["state"] == "OCR_REQUIRED" and not rs.may_remove(d)


def test_single_unread_cover_page_blocks_irrelevant():
    q = _q(0.8, [1])
    assert rs.decide(text=CIVIL, quality=q, ocr_done=False)["state"] == "OCR_REQUIRED"
    # still unusable after OCR: insufficient, not irrelevant
    assert rs.decide(text=CIVIL, quality=q, ocr_done=True)["state"] == "INSUFFICIENT_TEXT"


def test_reviewer_repro_five_pages_cover_image_only():
    pages = [{"page": 1, **tq.page_verdict("", image_cover=0.95)}] + \
            [{"page": i, **tq.page_verdict(CIVIL)} for i in range(2, 6)]
    s = tq.document_summary({"pages": pages, "truncated": False, "open_error": None})
    assert s["usable_share"] == 0.8
    d = rs.decide(text=CIVIL * 4, quality=s, ocr_done=False)
    assert not rs.may_remove(d)


def test_low_quality_ocr_cannot_support_irrelevant():
    d = rs.decide(text=CIVIL, quality=ok_quality(CIVIL), ocr_done=True, ocr_quality_ok=False)
    assert d["state"] == "INSUFFICIENT_TEXT"


# ---- review A1-04: bare service vocabulary is a removal guard
def test_bare_army_mentions_block_irrelevant():
    t = CIVIL + " Army officers commissioned in the Army." * 15
    d = decide_ok(t)
    assert d["state"] == "CLASSIFICATION_UNCERTAIN" and not rs.may_remove(d)


def test_fuzzy_ocr_misreading_blocks_irrelevant():
    t = CIVIL + " the Arny officer and the Tribnal " * 2
    assert decide_ok(t)["state"] == "CLASSIFICATION_UNCERTAIN"


# ---- review A1-08: cover metadata
def test_aft_party_in_title_is_relevant():
    t = "Writ petition. Notice. Learned counsel heard. " * 40
    d = rs.decide(text=t, quality=ok_quality(t), title="CWP/1/2024 of X Vs ARMED FORCES TRIBUNAL AND ORS.")
    assert d["state"] == "RELEVANT"


def test_short_order_by_reference_is_uncertain():
    t = ("The appeal is disposed of in terms of the order passed in RSA No. 1582 of 2021. " +
         "The plaintiff and the defendant shall bear their own costs of the suit and of the appeal. " * 8)
    d = decide_ok(t)
    assert d["state"] == "CLASSIFICATION_UNCERTAIN"


# ---- review A1-05: truncated files
def test_truncated_file_never_text_ok_and_empty_pages_are_missing():
    pages = [{"page": 1, **tq.page_verdict(CIVIL)}, {"page": 2, "usable": False, "flags": ["missing_page"]}]
    s = tq.document_summary({"pages": pages, "truncated": True, "open_error": None})
    assert s["verdict"] == "SOURCE_INCOMPLETE" and s["unusable_pages"] == [2]


# ---- review A1-10: fail closed on missing or incomplete inputs
def test_missing_quality_never_irrelevant():
    for q in (None, {}, {"verdict": "OCR_REQUIRED", "usable_share": 0.5}, {"verdict": "EXTRACTION_FAILED"},
              {"verdict": "TEXT_OK"}, {"verdict": "TEXT_OK", "usable_share": 1.0}):
        d = rs.decide(text=CIVIL, quality=q, ocr_quality_ok=True, ocr_done=True)
        assert d["state"] in ("INSUFFICIENT_TEXT", "CLASSIFICATION_UNCERTAIN", "OCR_REQUIRED"), (q, d["state"])
        assert not rs.may_remove(d)


def test_ocr_quality_not_established_never_irrelevant():
    d = rs.decide(text=CIVIL, quality=ok_quality(CIVIL))          # ocr_quality_ok left at its default
    assert d["state"] == "INSUFFICIENT_TEXT" and not rs.may_remove(d)


# ---- review A1-12
def test_capf_and_colonel_typos_block_irrelevant():
    t = CIVIL + " The appellant, Lt. Co. retired, and the Border Security Force Sector HQ; Ltd. Col. X. "
    assert decide_ok(t)["state"] == "CLASSIFICATION_UNCERTAIN"


def test_short_procedural_order_against_union_is_uncertain():
    t = ("Delay of 8000 days in filing the appeal is not satisfactorily explained. The application is dismissed and "
         "the appeal also stands dismissed. Union of India is the respondent. " * 6)
    assert decide_ok(t)["state"] == "CLASSIFICATION_UNCERTAIN"
