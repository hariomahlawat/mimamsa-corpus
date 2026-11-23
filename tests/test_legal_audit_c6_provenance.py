"""C6-01 provenance-recovery package: reproducibility and safeguards (offline; no held binaries needed)."""
import csv, hashlib, io, json, subprocess, sys, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PKG = REPO / "legal_knowledge/audit_work/C6-01-PROVENANCE"
sys.path.insert(0, str(PKG / "tools"))
import build_provenance as P  # noqa: E402


def read(name):
    with open(PKG / "registers" / name, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class C6Provenance(unittest.TestCase):
    def test_rebuild_identical(self):
        for k, t in P.outputs().items():
            self.assertEqual((PKG / "registers" / k).read_text(encoding="utf-8"), t, k)

    def test_originals_and_c4_register_unchanged(self):
        h = lambda p: hashlib.sha256((REPO / p).read_bytes()).hexdigest()
        self.assertEqual(h("legal_knowledge/curated_originals/knowledge_base/v0.9/records_658.jsonl"), "9a8f0d193065762ffa987116dc761bcb734008d2a87a946f5591741f5befcfc1")
        self.assertEqual(h("legal_knowledge/curated_originals/case_law/v0.9/cases_53.jsonl"), "8b8d53cd1434f7c1c6eaebe77f1fe295fb8b81b755e93276999b4b40b3c8f89a")
        self.assertEqual(h("legal_knowledge/audit_work/CALIBRATION-02/registers/source_authentication_register.csv"),
                         "cfe5f4081997abbcb88061cd7a8e5cc5b949c585cd7835fa48df51ae1a0c1ece")  # proposals never edit the Cycle 4 register

    def test_scope_and_denominators(self):
        s = json.loads((PKG / "registers/c6_01_summary.json").read_text())
        self.assertEqual(s["denominators"], {"held_unique_binaries_c5": 67, "held_binary_paths_c5": 93, "undocumented_copies_c5": 54,
                                             "scope_sources": 34, "scope_copies": 36})
        self.assertEqual(sum(s["outcomes_by_copy"].values()), 36)

    def test_classification_rules(self):
        allowed = {"PROVENANCE_DOCUMENTED", "PROVENANCE_PARTIALLY_DOCUMENTED", "IDENTITY_VERIFIED_PROVENANCE_UNDOCUMENTED",
                   "NO_RECOVERABLE_PROVENANCE", "AUTHENTICATION_PENDING"}
        for r in read("provenance_recovery_register.csv"):
            self.assertIn(r["proposed_outcome"], allowed)
            ids = r["identity_verification"]
            if r["proposed_outcome"] == "PROVENANCE_DOCUMENTED":
                self.assertEqual(r["locator_strength"], "FULL", r["copy_id"])
                court = "-J-" in r["source_id"]
                self.assertTrue(("I:" in ids) or (court and "T:" in ids), r["copy_id"])
                self.assertEqual(r["contradictions"], "NONE_FOUND_IN_SEARCHED_REGISTERS")
            if "T:" in ids and "I:" not in ids:
                self.assertIn("-J-", r["source_id"], "text-layer identity accepted only for court copies")

    def test_proposals_match_documented_rows_and_c4_rule_inputs(self):
        rec = {r["sha256"]: r for r in read("provenance_recovery_register.csv")}
        held = {}
        with open(REPO / "legal_knowledge/audit_work/CALIBRATION-02/registers/held_sources_scratchpad.csv", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                held.setdefault(r["sha256"], set()).add(r["scratchpad_relative_path"])
        props = read("source_authentication_proposals.csv")
        self.assertEqual({p["sha256"] for p in props}, {s for s, r in rec.items() if r["proposed_outcome"] == "PROVENANCE_DOCUMENTED"})
        for p in props:
            self.assertEqual(p["authentication_state"], "PROVENANCE_DOCUMENTED")
            self.assertTrue(p["provenance_references"].strip())
            self.assertEqual({x.strip() for x in p["held_paths"].split(";")}, held[p["sha256"]])
            self.assertIn("PROPOSAL - not incorporated", p["limitations"])

    def test_scope_split_publications_and_judgments(self):
        rec = read("provenance_recovery_register.csv")
        court = [r for r in rec if "-J-" in r["source_id"]]
        pub = [r for r in rec if "-J-" not in r["source_id"]]
        self.assertEqual((len({r["source_id"] for r in pub}), len(pub)), (26, 26))
        self.assertEqual((len({r["source_id"] for r in court}), len(court)), (8, 10))
        readme = (PKG / "README.md").read_text(encoding="utf-8")
        self.assertIn("26 publication or record sources with 26 copies", readme)
        self.assertIn("8 Supreme Court judgment sources with 10 copies", readme)
        self.assertNotIn("(28 copies)", readme)

    def test_weaker_locators_never_documented(self):
        for strength in ("MD5_SIZE", "IDENTIFIER_SHA", "MD5", "NONE"):
            for lead in (True, False):
                self.assertNotEqual(P.classify(strength, True, False, strength != "NONE", lead), "PROVENANCE_DOCUMENTED", strength)
        self.assertEqual(P.classify("FULL", True, False, True, False), "PROVENANCE_DOCUMENTED")
        self.assertEqual(P.classify("FULL", False, False, True, False), "PROVENANCE_PARTIALLY_DOCUMENTED")
        self.assertEqual(P.classify("FULL", True, True, True, False), "AUTHENTICATION_PENDING")
        method = (PKG / "reports/C6-01_METHOD.md").read_text(encoding="utf-8")
        self.assertNotIn("FULL or MD5_SIZE", method)
        self.assertNotIn("needs FULL or MD5_SIZE", (PKG / "tools/build_provenance.py").read_text(encoding="utf-8"))

    def test_proposal_ids_stable_unique_and_traceable(self):
        props = read("source_authentication_proposals.csv")
        ids = [p["proposal_id"] for p in props]
        self.assertEqual(len(ids), len(set(ids)))
        for p in props:
            self.assertEqual(p["proposal_id"], "C6-01-AP-" + p["sha256"][:8])
        # removing one proposal from the build does not change any other proposal's ID
        orig = P.build
        def drop_first():
            rec, pr, un, co = orig()
            return rec, pr[1:], un, co
        P.build = drop_first
        try:
            t = P.outputs()["source_authentication_proposals.csv"]
        finally:
            P.build = orig
        self.assertEqual([r["proposal_id"] for r in csv.DictReader(io.StringIO(t))], ids[1:])
        # duplicate IDs are rejected
        def dup():
            rec, pr, un, co = orig()
            return rec, pr + [pr[0]], un, co
        P.build = dup
        try:
            with self.assertRaises(SystemExit):
                P.outputs()
        finally:
            P.build = orig
        with open(PKG / "review/legacy_proposal_id_map.csv", newline="", encoding="utf-8") as f:
            legacy = list(csv.DictReader(f))
        cur = {p["sha256"]: p["proposal_id"] for p in props}
        for r in legacy:
            self.assertEqual(r["current_proposal_id"], cur.get(r["sha256"], ""), r["sha256"])
        first = [r["id_in_first_verification_9b4ad44d"] for r in legacy if r["id_in_first_verification_9b4ad44d"]]
        self.assertEqual(len(first), 34)  # all 34 sequential IDs of the first verification remain traceable
        self.assertEqual(len(set(first)), 34)
        self.assertEqual({r["sha256"] for r in legacy} >= set(cur), True)
        # synthetic prefix collision: two different sha256 with the same 8-hex prefix must stop the build
        orig = P.build
        def collide():
            rec, pr, un, co = orig()
            twin = dict(pr[0], sha256=pr[0]["sha256"][:8] + "f" * 56)
            return rec, pr + [twin], un, co
        P.build = collide
        try:
            with self.assertRaises(SystemExit) as cm:
                P.outputs()
            self.assertIn("ONLY the colliding", str(cm.exception))
        finally:
            P.build = orig
        ap22 = [r for r in legacy if r["id_in_first_verification_9b4ad44d"] == "C6-01-AP-22"][0]
        self.assertTrue(ap22["sha256"].startswith("8358d2b3") and ap22["current_proposal_id"] == "")

    def test_report_counts_match_summary(self):
        s = json.loads((PKG / "registers/c6_01_summary.json").read_text())
        d, pt, n = s["outcomes_by_copy"]["PROVENANCE_DOCUMENTED"], s["outcomes_by_copy"]["PROVENANCE_PARTIALLY_DOCUMENTED"], s["proposals"]
        nonp = sum(v for k, v in s["proposals_by_class"].items() if k.startswith("NON_PRIMARY"))
        self.assertEqual((d, pt, n, nonp), (32, 4, 32, 4))
        d6 = (PKG / "reports/D6_CYCLE6_READINESS.md").read_text(encoding="utf-8")
        status = d6[d6.index("## C6-01 status"):d6.index("## What C6-01 cannot fix")]
        self.assertIn(f"{d} copies are proposed PROVENANCE_DOCUMENTED", status)
        self.assertIn(f"{pt} are PROVENANCE_PARTIALLY_DOCUMENTED", status)
        self.assertIn(f"{n} additions", status)
        self.assertIn(f"{nonp} non-primary", status)
        d3 = (PKG / "reports/D3_INDEPENDENT_VERIFICATION.md").read_text(encoding="utf-8")
        self.assertIn(f"**Current outcomes:** {d} DOCUMENTED and {pt} PARTIALLY_DOCUMENTED", d3)
        d2 = (PKG / "reports/D2_SOURCE_AUTHENTICATION_PROPOSALS.md").read_text(encoding="utf-8")
        self.assertIn(f"{n} proposed **additions**", d2)
        self.assertIn("TRA 2026", d2)
        d4 = (PKG / "reports/D4_COVERAGE_IMPACT.md").read_text(encoding="utf-8")
        self.assertIn("overlay design", d4)
        self.assertNotIn("relabel", d6)
        self.assertIn("WITHHELD", d6)
        self.assertEqual(subprocess.run([sys.executable, str(PKG / "tools/build_reports.py"), "--check"], capture_output=True).returncode, 0)

    def test_c6_page_image_checks(self):
        with open(PKG / "inputs/page_image_checks_c6.csv", newline="", encoding="utf-8") as f:
            checks = list(csv.DictReader(f))
        for c in checks:
            png = PKG / c["render_file"]
            self.assertEqual(hashlib.sha256(png.read_bytes()).hexdigest(), c["render_png_sha256"], c["check_id"])
            self.assertIn(c["identity_result"], ("CONFIRMED", "PARTIAL"))
        rec = {r["source_id"]: r for r in read("provenance_recovery_register.csv")}
        self.assertEqual(rec["C5-SRC-P0-TRA-2026"]["proposed_outcome"], "PROVENANCE_DOCUMENTED")
        self.assertEqual(rec["C5-SRC-P0-TRA-2026"]["proposed_effective_source_class"], "NON_PRIMARY_OFFICIAL_PUBLICATION_COPY")
        dhc = rec["C5-SRC-P2-DHC-RULES-CH6"]
        self.assertEqual(dhc["proposed_outcome"], "PROVENANCE_PARTIALLY_DOCUMENTED")  # PARTIAL image check never counts as I
        self.assertNotIn("I:", dhc["identity_verification"].replace("Ip:", ""))
        act13 = rec["C5-SRC-P0-AA-AMD-ACT13-1975"]
        self.assertEqual((act13["proposed_outcome"], act13["locator_strength"]), ("PROVENANCE_PARTIALLY_DOCUMENTED", "IDENTIFIER_SHA"))
        self.assertIn("Hindi issue No.16 but English issue No.15", act13["remaining_gaps"])
        self.assertEqual(act13["retrieval_date"], "register dated 2026-11-22")  # no invented retrieval date

    def test_so4010_date_dispute_and_rs_withheld(self):
        props = {p["sha256"]: p for p in read("source_authentication_proposals.csv")}
        self.assertFalse([s for s in props if s.startswith("fa51a4b1")])
        rec = {r["source_id"]: r for r in read("provenance_recovery_register.csv")}["C5-SRC-P2-RS-PAPERS-LAID-1987"]
        self.assertEqual(rec["proposed_outcome"], "PROVENANCE_PARTIALLY_DOCUMENTED")
        self.assertIn("DISPUTED", rec["source_identity"])
        self.assertIn("NOT_VERIFIED", rec["source_identity"])
        self.assertIn("WITHHELD", rec["remaining_gaps"])
        self.assertIn("L3x:", rec["evidence_items"])
        for k in ("08-12-1986", "RV-01", "D7_INDEPENDENT_REVIEW_REPORT", "Gazette of S.O. 4010/1986"):
            self.assertIn(k, rec["remaining_gaps"])
        self.assertIn("6th December", rec["remaining_gaps"])  # the transcription is preserved, attributed
        # the Cycle 5 records are not rewritten
        c5 = (REPO / "legal_knowledge/audit_work/SOURCE-LIBRARY-C5/reports/D7_INDEPENDENT_REVIEW_REPORT.md").read_text(encoding="utf-8")
        self.assertIn("OPEN, documentary", c5)
        s = json.loads((PKG / "registers/c6_01_summary.json").read_text())
        self.assertEqual(s["proposals_by_status"], {"PROPOSED": 32})

    def test_locator_rules_after_fable_review(self):
        rec = {r["copy_id"]: r for r in read("provenance_recovery_register.csv")}
        c2 = rec["C5-SRC-J-SC-2015-RAJBIR~C2"]
        self.assertEqual(c2["proposed_outcome"], "PROVENANCE_PARTIALLY_DOCUMENTED")
        self.assertIn("L3lead:", c2["evidence_items"])
        self.assertNotIn("L3:", c2["evidence_items"].replace("L3lead:", ""))
        self.assertIn("Record of Proceedings", c2["remaining_gaps"])
        # every documented row rests on a locator that is not a mention inside another copy's record and not disclaimed
        for r in rec.values():
            if r["proposed_outcome"] == "PROVENANCE_DOCUMENTED":
                kinds = {x.split(":")[0] for x in r["evidence_items"].split(" | ")}
                self.assertTrue(kinds & {"L1", "L2", "L3", "L4"}, r["copy_id"])
        # S.R.O. 34 identity is not written as fact
        sro34 = [p for p in read("source_authentication_proposals.csv") if p["sha256"].startswith("4acdb1a8")][0]
        self.assertIn("UNVERIFIED", sro34["document_identity"])
        self.assertIn("UNVERIFIED", sro34["limitations"])
        # T rule needs the year or case number too
        for r in rec.values():
            for x in r["identity_verification"].split("; "):
                if x.startswith("T:"):
                    self.assertTrue(r["source_id"].split("-")[4].isdigit())
        # direct file URL preferred over an archive.org item page
        for p in read("source_authentication_proposals.csv"):
            self.assertNotIn("archive.org/details/", p["official_locator_recorded"], p["proposal_id"])

    def test_copy_structure_and_fidelity_rule(self):
        with open(PKG / "inputs/copy_structure_c6.csv", newline="", encoding="utf-8") as f:
            st = {r["sha256"]: r for r in csv.DictReader(f)}
        self.assertEqual(len(st), 36)
        for p in read("source_authentication_proposals.csv"):
            s = st[p["sha256"]]
            if p["effective_source_class"].startswith("PRIMARY_GAZETTE"):
                self.assertNotEqual(s["signed_range_covers_file"], "NO", p["proposal_id"])
        self.assertEqual(st[[k for k in st if k.startswith("be619533")][0]]["eof_markers"], "1")  # rewrite, not incremental (F-12)

    def test_isaac_untouched(self):
        isaac = "3f49a31464fec174cdbff5d9e194fa888ca00529b6246eacdc8ac2368eab4653"
        self.assertNotIn(isaac, {r["sha256"] for r in read("provenance_recovery_register.csv")})
        self.assertNotIn(isaac, {p["sha256"] for p in read("source_authentication_proposals.csv")})

    def test_non_primary_classes_for_records_and_incomplete_copies(self):
        cls = {p["sha256"][:8]: p["effective_source_class"] for p in read("source_authentication_proposals.csv")}
        self.assertNotIn("fa51a4b1", cls)  # RS papers-laid: PARTIALLY_DOCUMENTED by rule (Fable F-02) and WITHHELD
        self.assertNotIn("c6ec489d", cls)  # Rajbir C2: locator only inside C1's record (Fable F-01)
        self.assertEqual(cls.get("2bdab5b7"), "NON_PRIMARY_OFFICIAL_PUBLICATION_COPY")  # archive.org derivative (Fable F-04)
        self.assertEqual(cls.get("7c12a7ec"), "PRIMARY_GAZETTE_ARCHIVAL_FACSIMILE")  # signature range covers the file
        self.assertEqual(cls.get("138c1da0"), "PRIMARY_GAZETTE_ARCHIVAL_FACSIMILE")
        self.assertEqual(cls.get("be619533"), "NON_PRIMARY_OFFICIAL_PUBLICATION_COPY")
        self.assertEqual(cls.get("29f6fa2c"), "NON_PRIMARY_OFFICIAL_PUBLICATION_COPY")  # incomplete ER 2023 copy
        self.assertEqual(cls.get("6b495f14"), "NON_PRIMARY_OFFICIAL_COURT_RENDITION")  # Rajbir bosir rendition
        self.assertNotIn("8358d2b3", cls)  # Act 13/1975 downgraded (identifier-only download record)

    def test_coverage_baseline_matches_cycle5(self):
        s = json.loads((PKG / "registers/c6_01_summary.json").read_text())["coverage_impact"]
        c5 = json.loads((REPO / "legal_knowledge/audit_work/SOURCE-LIBRARY-C5/registers/coverage_summary.json").read_text())
        for k in ("crosswalk_kb_items_by_status", "crosswalk_case_rows_by_status", "kb_records_by_anchor_class"):
            self.assertEqual(s["baseline"][k], c5[k])

    def test_simulation_does_not_leak_into_cycle5_registers(self):
        sys.path.insert(0, str(REPO / "legal_knowledge/audit_work/SOURCE-LIBRARY-C5/tools"))
        import build_registers as B
        P.coverage_impact(read("source_authentication_proposals.csv"))
        for k, t in B.build().items():
            self.assertEqual((REPO / "legal_knowledge/audit_work/SOURCE-LIBRARY-C5/registers" / k).read_text(encoding="utf-8"), t, k)


class C6Addendum(unittest.TestCase):
    def test_addendum_draft_reproducible_and_pending(self):
        import build_addendum_plan as A
        out = PKG / "addendum/authentication_addendum_v1_draft.csv"
        self.assertEqual(out.read_text(encoding="utf-8"), A.text())
        rows = list(csv.DictReader(out.open(encoding="utf-8")))
        self.assertEqual(len(rows), len(read("source_authentication_proposals.csv")))
        for r in rows:
            self.assertEqual(r["locator_strength"], "FULL")
            self.assertTrue(r["reviewer_decision"].startswith("PENDING"))
            self.assertEqual((r["entry_type"], r["entry_status"], r["owner_decision"]), ("ADD", "DRAFT", "PENDING"))
            self.assertTrue(r["first_class_record_ref"] and "(locator)" not in r["first_class_record_ref"])
            self.assertTrue(A.resolves(r["first_class_record_ref"]))
            if True:
                if r["primary_or_non_primary"] == "NON_PRIMARY":  # non-primary never yields an exact anchor
                    self.assertTrue(r["crosswalk_effect_this_entry_alone"].startswith("none"), r["proposal_id"])
            self.assertTrue(r["prior_effective_state"].startswith("C4: NO_ROW"))
        self.assertEqual(A.validate(rows), [])
        bad = dict(rows[0], first_class_record_ref="PILOT-01/sources/nonexistent.json#X")
        self.assertTrue(A.validate([bad]))  # an unresolvable reference is rejected
        bad = dict(rows[0], owner_decision="APPROVED")
        self.assertTrue(A.validate([bad]))  # APPROVED without decision record and reviewer is rejected
        changed = {r["crosswalk_effect_this_entry_alone"].split(":")[0] for r in rows if not r["crosswalk_effect_this_entry_alone"].startswith("none")}
        self.assertEqual(len(changed), 7)  # the seven SC case records, matching D4


class C6Prep(unittest.TestCase):
    PREP = REPO / "legal_knowledge/audit_work/C6-PREP/registers"

    def rows(self, name):
        with open(self.PREP / name, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def test_no_approval_no_correspondence(self):
        for r in self.rows("c6_02_batch_a_files.csv"):
            self.assertEqual(r["approval_state"], "NOT_APPROVED")
            self.assertNotIn("aftjabalpur", r["download_url"])
        for r in self.rows("c6_03_desw_package.csv"):
            self.assertIn(r["approval_state"], ("NOT_APPROVED", "n/a"))
        for r in self.rows("c6_04_custodian_request_inventory.csv"):
            self.assertEqual(r["correspondence"], "NONE SENT (not authorised)")

    def test_incomplete_er2023_kept_separate(self):
        self.assertTrue(any("29f6fa2c" in r["size_pin"] and r["acq_c5_id"].startswith("HELD") for r in self.rows("c6_03_desw_package.csv")))

    def test_batch_a_pins_and_fail_closed_metadata_attempt(self):
        rows = self.rows("c6_02_batch_a_files.csv")
        self.assertEqual(sum(r["pin_status"].startswith("PINNED") for r in rows), 18)
        unpinned = [r for r in rows if r["pin_status"].startswith("NOT_PINNED")]
        self.assertEqual({r["candidate_id"] for r in unpinned}, {"C5C-026", "C5C-027"})
        self.assertTrue(all(r["expected_md5"] == "NOT_PINNED" for r in unpinned))
        sys.path.insert(0, str(REPO / "legal_knowledge/audit_work/SOURCE-LIBRARY-C5/tools"))
        import discovery_guard as G
        with open(REPO / "legal_knowledge/audit_work/C6-PREP/discovery/c6_02_metadata_requests_v2.tsv", newline="", encoding="utf-8") as f:
            log = list(csv.DictReader(f, delimiter="\t"))
        self.assertEqual(G.validate_log_v2(log), [])
        self.assertFalse([r for r in log if r["method"] == "GET" and r["purpose"] != "robots"])  # no non-robots GET was made

    def test_dv_handbook_lead_not_imported(self):
        with open(REPO / "legal_knowledge/audit_work/C6-PREP/inputs/c6_04_discovery_candidates.csv", newline="", encoding="utf-8") as f:
            cands = list(csv.DictReader(f))
        lead = [c for c in cands if c["candidate_id"] == "DV-SOH-2014"][0]
        self.assertEqual(lead["location_type"], "THIRD_PARTY_UPLOAD")
        self.assertTrue(lead["examined"].startswith("NO"))
        self.assertTrue(all(c["reference_status"] in ("DISCOVERY_LEAD", "UNVERIFIED_EXTRACTION_CANDIDATE") for c in cands))
        req = {r["request_id"]: r for r in self.rows("c6_04_custodian_request_inventory.csv")}
        self.assertEqual(req["DV-SOH-2014"]["correspondence"], "NONE SENT (not authorised)")
        self.assertIn("AO-13-2006-PS", req)

    def test_adviser_pack_unchanged_and_no_determination(self):
        s = json.loads((self.PREP / "c6_05_adviser_pack_status.json").read_text())
        self.assertEqual((s["c4_adviser_topics"], s["c4_calibration_escalations"], s["ws_b_inconsistencies_open"], s["determinations_made"]), (13, 29, 13, 0))
        self.assertEqual(s["reserved_states"]["C5-CF-C-01"], "CONFLICTING (r.23(3))")
        self.assertEqual(s["reserved_states"]["C5-CF-SC4-01"], "OPEN (r.182)")


if __name__ == "__main__":
    unittest.main()
