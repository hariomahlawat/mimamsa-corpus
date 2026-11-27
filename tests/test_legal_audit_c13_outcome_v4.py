"""C13 A2: judicial outcome extractor V4 (fast, synthetic texts; no corpus access needed).

Covers the deferred C11 findings F05 (extent-qualified relief) and F08 (operative sentence after a closing quote),
the V4 structural layers (opinion roles, proceeding map, transfer, elliptical dispositions), the driver's exclusion
and anchor rules, and the frozen status of the V2/V3 comparators."""
import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

AW = Path(__file__).resolve().parents[1] / "legal_knowledge" / "audit_work"
TOOLS = AW / "C13-A2-OUTCOME" / "tools"
sys.dont_write_bytecode = True
sys.path.insert(0, str(TOOLS))
import v4core  # noqa: E402
import v4_proceedings  # noqa: E402
import v4_quotes  # noqa: E402
import extract_v4  # noqa: E402

U = v4core.UNVERIFIED
HEAD = ("[[page 1]]\nIN THE HIGH COURT OF DELHI AT NEW DELHI\nW.P.(C) 1234/2024\nRAM KUMAR ..... Petitioner\nversus\n"
        "UNION OF INDIA AND ORS ..... Respondents\nCORAM:\nHON'BLE MR. JUSTICE A\nJUDGMENT\n")
FILL = ("The petitioner, a retired soldier, challenges the orders of the respondents concerning his service record and "
        "the benefits that he says were wrongly withheld. The respondents have filed a counter affidavit and the record "
        "has been produced before us. We have heard learned counsel for both sides at length on every aspect. ")
META = {"judgment_id": "J-test", "sha256": "0" * 64, "doc_ids": ["d"], "case_numbers_meta": "W.P.(C)/1234/2024", "court": "x"}


def run(body, meta=META):
    rows, diag = v4core.analyze(HEAD + "1. " + FILL * 6 + "\n" + body + "\n\nA, J.\nJANUARY 1, 2025\n", meta)
    return rows, diag


def one(body, meta=META):
    rows, _ = run(body, meta)
    own = [r for r in rows if r["proceeding"] == "WP(C) 1234/2024"]
    return own[0] if own else rows[0]


class F05ExtentQualifiedRelief(unittest.TestCase):
    def test_extent_phrase_referring_to_complete_quashing_is_allowed(self):
        # V3H139 pattern: every impugned decision quashed, nothing refused
        r = one("2. The impugned notice dated 31.03.2021 issued on 01.04.2021, being without jurisdiction, cannot be "
                "sustained and is hereby quashed. Consequently, the order dated 19.03.2022 and the Reassessment Order dated "
                "29.03.2022 can also not be sustained and are hereby quashed.\n3. For all the reasons afore-stated, the writ "
                "petition is allowed to the extent and in terms herein above.")
        self.assertEqual((r["printed_disposal"], r["substantive_result"]), ("allowed", "relief_granted"))

    def test_extent_phrase_with_refused_relief_is_partly_allowed(self):
        r = one("2. The impugned order dated 05.08.2003 is set aside. In a situation where the liability is yet to be decided, "
                "the relief of reinstatement cannot be granted. We, therefore, decline the same.\n3. Accordingly, the writ "
                "petition is allowed to the extent indicated above.")
        self.assertEqual((r["printed_disposal"], r["substantive_result"]), ("partly_allowed", "relief_partly_granted"))

    def test_c11_f05_corpus_sentence_without_context_abstains(self):
        # sentence quoted in C11 F05 (J-123f221f41ed354a); with no limitation and no quashing in view, V4 abstains
        r = one("2. We have considered the matter.\n3. To the aforesaid extent, this petition is allowed.")
        self.assertEqual(r["printed_disposal"], U)
        self.assertIn("EXTENT_QUALIFIED", r["abstain_reason"])

    def test_c11_f05_partly_succeeds(self):
        # sentence quoted in C11 F05 (H011)
        r = one("2. In the result, the appeal partly succeeds in the above terms.")
        self.assertEqual(r["printed_disposal"], "partly_allowed")

    def test_limited_extent_is_partly_allowed(self):
        r = one("2. Accordingly, we allow the present petition to the above limited extent.")
        self.assertEqual(r["printed_disposal"], "partly_allowed")


class F08OperativeSentenceAfterQuote(unittest.TestCase):
    def test_disposition_after_closing_quote_is_court_voice(self):
        # H055 / QP14 pattern: provision quoted, then the court's own transfer direction
        body = ("2. Section 34 of the Act provides (relevant portion) as under:-\n\"34. Transfer of pending cases.-(1) Every suit "
                "or other proceeding pending before any court including a High Court shall stand transferred on that date "
                "to such Tribunal;\" For the forgoing reasons, the matter is not adjudicated on merit by this Court but "
                "transmitted to the Armed Forces Tribunal. Accordingly, Registry is directed to send paper book of this case "
                "to the Armed Forces Tribunal.")
        r = one(body)
        self.assertEqual((r["printed_disposal"], r["substantive_result"]), ("transferred", "no_adjudication"))
        self.assertRegex(r["excerpt"], r"transmitted|Registry")   # the anchor is the court's sentence, after the quote

    def test_intro_block_ends_at_the_quotation_it_introduces(self):
        t = ("The rule reads as under:\n\"The petition shall stand dismissed if the fee is not paid within time.\" "
             "Accordingly, the petition is dismissed.")
        spans = v4_quotes.quote_spans_v4(t)
        starts = [s[0] for s in spans]
        pos = t.index("Accordingly")
        self.assertEqual(v4_quotes.voice_at(spans, starts, pos), "court")
        self.assertEqual(v4_quotes.voice_at(spans, starts, t.index("shall stand dismissed")), "quoted")

    def test_mis_paired_quote_cut_at_courts_next_paragraph(self):
        t = ("7. The Board recorded: “The officer is unfit. " + "x " * 400 + "\n8. Accordingly, the petition is "
             "dismissed. No costs.” stray")
        spans = v4_quotes.quote_spans_v4(t)
        self.assertEqual(v4_quotes.voice_at(spans, [s[0] for s in spans], t.index("8. Accordingly") + 3), "court")

    def test_genuine_quote_with_its_own_numbering_not_cut(self):
        t = ("7. The earlier judgment held:\n“28. In the present case the order is bad. " + "y " * 400 +
             "\n29. Accordingly, the petition is allowed.”\n8. We respectfully agree.")
        spans = v4_quotes.quote_spans_v4(t)
        self.assertEqual(v4_quotes.voice_at(spans, [s[0] for s in spans], t.index("29. Accordingly") + 4), "quoted")

    def test_doubled_single_quotes(self):
        t = "Para 32 is relevant:\n’’32. The appeal is dismissed for want of merit.’’\n16. We agree."
        spans = v4_quotes.quote_spans_v4(t)
        self.assertEqual(v4_quotes.voice_at(spans, [s[0] for s in spans], t.index("dismissed")), "quoted")


class StructuralLayers(unittest.TestCase):
    def test_transfer_direction_then_disposed_of(self):
        r = one("2. We direct the Registry of this Court to transmit the record of this writ petition to the Armed Forces "
                "Tribunal which shall register it as a transfer application.\n3. Writ petition is disposed of accordingly.")
        self.assertEqual((r["printed_disposal"], r["substantive_result"]), ("transferred", "no_adjudication"))

    def test_elliptical_disposition(self):
        self.assertEqual(one("2. In the result, all the petitions dismissed. No costs.")["printed_disposal"], "dismissed")

    def test_liberty_alone_is_not_a_direction(self):
        r = one("2. If the petitioner has any grievance, he is at liberty to agitate it in appropriate proceedings.\n"
                "3. The petition is disposed of.")
        self.assertEqual(r["printed_disposal"], "disposed_of")

    def test_dissenting_opinion_does_not_supply_disposition(self):
        body = ("2. For the reasons above, the writ petition is allowed and the impugned order is quashed.\n\n"
                "B. C. DEF, J.\n1. I have gone through the judgment of my learned Brother. I respectfully disagree with the "
                "conclusion. " + FILL * 3 + "\n2. In my view, the writ petition is dismissed.")
        rows, diag = run(body)
        r = [x for x in rows if x["proceeding"] == "WP(C) 1234/2024"][0]
        self.assertEqual(r["printed_disposal"], "allowed")
        self.assertIn("DISSENTING_OPINION_EXCLUDED", diag["flags"])

    def test_abbreviated_ranges_and_and_lists(self):
        self.assertEqual(v4_proceedings._expand("8452-53"), {8452, 8453})
        self.assertEqual(v4_proceedings._expand("2825, 2826 And 2827"), {2825, 2826, 2827})

    def test_every_answered_row_is_anchored(self):
        r = one("2. In the result, the petition is dismissed.")
        self.assertEqual(r["printed_disposal"], "dismissed")
        self.assertTrue(r["page"] and r["char_start"] != "" and r["char_end"] != "" and r["excerpt"])
        self.assertEqual(r["status"], "AUTOMATED_CANDIDATE_NOT_VERIFIED")
        self.assertIn(r["confidence"], ("high", "medium", "low"))


class Driver(unittest.TestCase):
    def test_read_ids_formats_and_exclusion_rows(self):
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "ids.csv")
            Path(p).write_text("holdout_id,judgment_id\nX1,J-a\n# note\nX2,J-b\n", encoding="utf-8")
            self.assertEqual(extract_v4.read_ids(p), ["J-a", "J-b"])
            Path(p).write_text("J-c\nJ-d\n", encoding="utf-8")
            self.assertEqual(extract_v4.read_ids(p), ["J-c", "J-d"])
        info = {"judgment_id": "J-a", "sha256": "1" * 64, "doc_ids": ["d"], "court": "c", "text_doc": ""}
        out = extract_v4.run_batch(["J-a"], {"J-a": info}, None, frozenset({"J-a"}))
        self.assertEqual(out[0]["abstain_reason"], extract_v4.EXCLUDED_REASON)
        self.assertEqual(extract_v4.validate_rows(out), [])

    def test_restricted_copy_never_loaded(self):
        self.assertIn("4284820e5bc2fb7f52ae9fbe8a61650f1579e9b6389ba206a916a69fed016b14", extract_v4.RESTRICTED_SHA256)

    def test_unanchored_answer_fails_validation(self):
        r = {k: "" for k in extract_v4.OUTCOME_COLS}
        r.update({"printed_disposal": "dismissed", "substantive_result": "relief_refused", "final_or_interim": "final",
                  "status": v4core.STATUS})
        self.assertTrue(extract_v4.validate_rows([r]))

    def test_tools_never_reference_the_fresh_holdout(self):
        for p in TOOLS.glob("*.py"):
            t = p.read_text(encoding="utf-8")
            self.assertNotIn("C13-A0-EVAL", t, p.name)
            self.assertNotIn("H-OUT-C13/", t, p.name)


class FrozenComparators(unittest.TestCase):
    def test_v3_tools_unchanged(self):
        frz = json.loads((AW / "C12-CONSOLIDATION/extractor_v3/outputs/FREEZE_V3.json").read_text(encoding="utf-8"))
        blob = json.dumps(frz)
        for fn in ("v3core.py", "extract_v3.py"):
            h = hashlib.sha256((AW / "C12-CONSOLIDATION/extractor_v3/tools" / fn).read_bytes()).hexdigest()
            self.assertIn(h, blob, fn)

    def test_v2_outputs_checksummed(self):
        sums = (AW / "C11-JUDICIAL-QUALITY/extraction/outputs/OUTPUT_SHA256SUMS").read_text(encoding="utf-8")
        h = hashlib.sha256((AW / "C11-JUDICIAL-QUALITY/extraction/outputs/OUTCOMES_V2.csv").read_bytes()).hexdigest()
        self.assertIn(h, sums)


if __name__ == "__main__":
    unittest.main()
