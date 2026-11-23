"""Cycle 5 source-library package: structural and integrity tests (no network, no held binaries needed)."""
import csv, hashlib, json, re, sys, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PKG = REPO / "legal_knowledge/audit_work/SOURCE-LIBRARY-C5"
sys.path.insert(0, str(PKG / "tools"))
import build_registers as B  # noqa: E402
import check_c5 as C  # noqa: E402
import discovery_guard as G  # noqa: E402


def read(name):
    with open(PKG / "registers" / name, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class C5Package(unittest.TestCase):
    def test_validator_clean(self):
        old = sys.argv
        try:
            sys.argv = ["check_c5.py"]
            self.assertEqual(C.main(), 0)
        finally:
            sys.argv = old

    def test_rebuild_identical(self):
        for k, t in B.build().items():
            self.assertEqual((PKG / "registers" / k).read_text(encoding="utf-8"), t, k)

    def test_schema_matches_contract(self):
        sch = json.loads((PKG / "schemas/c5_registers.schema.json").read_text())
        self.assertEqual({k: v["columns"] for k, v in sch["registers"].items()}, B.COLS)

    def test_originals_unchanged(self):
        base = json.loads((PKG / "baseline/frozen_baseline_manifest.json").read_text())
        for k, rel in {"records_658": "legal_knowledge/curated_originals/knowledge_base/v0.9/records_658.jsonl",
                       "cases_53": "legal_knowledge/curated_originals/case_law/v0.9/cases_53.jsonl"}.items():
            self.assertEqual(hashlib.sha256((REPO / rel).read_bytes()).hexdigest(), base["original_corpus_sha256"][k])
        self.assertEqual(base["original_corpus_sha256"]["records_658"], "9a8f0d193065762ffa987116dc761bcb734008d2a87a946f5591741f5befcfc1")
        self.assertEqual(base["original_corpus_sha256"]["cases_53"], "8b8d53cd1434f7c1c6eaebe77f1fe295fb8b81b755e93276999b4b40b3c8f89a")

    def test_held_rows_hash_backed(self):
        held = {r["rehashed_sha256"] for r in csv.DictReader(open(PKG / "baseline/held_binaries_manifest.csv", encoding="utf-8"))}
        for r in read("source_master_register.csv"):
            shas = [s for s in r["sha256"].split(";") if s]
            if r["holding_state"].startswith("HELD"):
                self.assertTrue(shas and all(s in held for s in shas), r["source_id"])
            else:
                self.assertEqual(shas, [], r["source_id"])

    def test_primary_only_with_register_or_held_primary_class(self):
        auth = {r["sha256"]: r for r in csv.DictReader(open(REPO / "legal_knowledge/audit_work/CALIBRATION-02/registers/source_authentication_register.csv", encoding="utf-8"))}
        for r in read("source_master_register.csv"):
            if r["holding_state"].startswith("HELD_PRIMARY"):
                self.assertTrue(any(s in auth and auth[s]["authentication_state"] == "PROVENANCE_DOCUMENTED" for s in r["sha256"].split(";")),
                                f"{r['source_id']} is HELD_PRIMARY without a PROVENANCE_DOCUMENTED register row")

    def test_no_currency_or_approval_promotion(self):
        for r in read("source_master_register.csv"):
            self.assertNotEqual(r["amendment_chain_status"].split(" ")[0], "CHECKED_FOR_RELEVANT_PERIOD")
            self.assertNotRegex(" ".join(r.values()), r"LEGALLY_APPROVED|JAG_APPROVED|CURRENT_IN_FORCE")

    def test_acquisitions_not_approved_and_ranked(self):
        rows = read("acquisition_register.csv")
        self.assertEqual([int(r["rank"]) for r in rows], list(range(1, len(rows) + 1)))
        for r in rows:
            self.assertEqual(r["approval_state"], "NOT_APPROVED")
            self.assertNotIn("aftjabalpur", r["exact_location"])

    def test_injected_promotion_rejected(self):
        master = read("source_master_register.csv")
        bad = [dict(r, approval_state="APPROVED") for r in B.read(PKG / "inputs/acquisition_batches.csv")[:1]]
        with self.assertRaises(SystemExit):
            B.acquisition_rows(master, bad)
        t = dict(B.read(PKG / "inputs/target_publications.csv")[0], holding_state="HELD_GOVERNMENT_COMPILATION", held_sha256="")
        with self.assertRaises(SystemExit):
            B.master_rows({}, {}, {}, [t])
        t2 = dict(t, held_sha256="0" * 64)
        with self.assertRaises(SystemExit):
            B.master_rows({}, {}, {}, [t2])

    def test_crosswalk_complete_and_conservative(self):
        cw = read("corpus_crosswalk.csv")
        kb = {json.loads(l)["id"] for l in open(REPO / "legal_knowledge/curated_originals/knowledge_base/v0.9/records_658.jsonl", encoding="utf-8")}
        cs = {json.loads(l)["id"] for l in open(REPO / "legal_knowledge/curated_originals/case_law/v0.9/cases_53.jsonl", encoding="utf-8")}
        self.assertEqual({r["knowledge_base_record_id"] for r in cw if r["knowledge_base_record_id"]}, kb)
        self.assertEqual({r["case_id"] for r in cw if r["case_id"]}, cs)
        master = {r["source_id"]: r for r in read("source_master_register.csv")}
        amended = B.amended_rules()
        for r in cw:
            if r["evidence_status"] == "EXACT_ANCHOR":
                self.assertTrue(master[r["source_id"]]["holding_state"].startswith("HELD_PRIMARY"), r)
                if r["source_id"] == "C5-SRC-P0-ARMY-RULES-1954":
                    self.assertFalse(set(r["provision_id"].split("#", 1)[1].split(",")) & amended, r)

    def test_reserved_states(self):
        conf = {r["conflict_id"]: r for r in read("source_conflict_register.csv")}
        for cid, st in C.EXPECTED_RESERVED.items():
            self.assertEqual(conf[cid]["reserved_status"], st)
        self.assertEqual(sum(1 for c in conf if c.startswith("C5-CF-WSB-")), 13)

    def test_discovery_logs_no_binary_get_or_blocked_host(self):
        for log in (PKG / "discovery").glob("*_requests.tsv"):
            for line in open(log, encoding="utf-8"):
                p = line.rstrip("\n").split("\t")
                if len(p) >= 3:
                    self.assertNotIn("aftjabalpur", p[2])
                    if p[1].upper() == "GET":
                        self.assertIsNone(re.search(r"\.(pdf|docx?|zip)(\?|$)", p[2], re.I), line)


def master():
    return {r["source_id"]: r for r in read("source_master_register.csv")}


class C5AuthenticationCounts(unittest.TestCase):
    """12 documented-primary sources + 1 authentication-pending source, derived from controlled metadata."""

    def test_counts_derived_from_register(self):
        reg = list(csv.DictReader(open(REPO / "legal_knowledge/audit_work/CALIBRATION-02/registers/source_authentication_register.csv", encoding="utf-8")))
        documented = [r for r in reg if r["authentication_state"] == "PROVENANCE_DOCUMENTED" and r["effective_source_class"].startswith("PRIMARY_")]
        pending = [r for r in reg if r["authentication_state"] == "AUTHENTICATION_PENDING"]
        self.assertEqual((len(reg), len(documented), len(pending)), (13, 12, 1))
        self.assertEqual(sum(1 for r in documented if "GAZETTE" in r["effective_source_class"]), 5)
        self.assertEqual(sum(1 for r in documented if r["effective_source_class"] == "PRIMARY_OFFICIAL_COURT_COPY"), 7)
        a = json.loads((PKG / "registers/coverage_summary.json").read_text())["authentication"]
        self.assertEqual(a["documented_primary_copies"], len(documented))
        self.assertEqual(a["authentication_pending_copies"], len(pending))
        self.assertEqual(a["sources_with_documented_primary_copy"], 12)
        self.assertEqual(a["sources_authentication_pending_only"], 1)

    def test_pending_never_primary_or_eligible(self):
        m = master()
        isaac = m["C5-SRC-J-SC-2026-ISAAC"]
        self.assertEqual(isaac["holding_state"], "HELD_AUTHENTICATION_PENDING")
        self.assertFalse(isaac["holding_state"].startswith("HELD_PRIMARY"))
        for c in read("source_copy_register.csv"):
            if c["copy_effective_status"] == "AUTHENTICATION_PENDING":
                self.assertEqual(c["eligible_for_exact_anchor"], "NO")
        for r in read("corpus_crosswalk.csv"):
            self.assertNotEqual(r["source_id"], "C5-SRC-J-SC-2026-ISAAC") if r["evidence_status"] == "EXACT_ANCHOR" else None

    def test_prefix_promotion_rejected(self):
        """A source labelled HELD_PRIMARY_* without a documented copy (or pending relabelled primary) fails the build."""
        m = read("source_master_register.csv")
        copies = read("source_copy_register.csv")
        bad = [dict(r, holding_state="HELD_PRIMARY_OFFICIAL_COURT_COPY") if r["source_id"] == "C5-SRC-J-SC-2026-ISAAC" else r for r in m]
        with self.assertRaises(SystemExit):
            B.check_holding_vs_copies(bad, copies)
        bad2 = [dict(r, holding_state="HELD_PRIMARY_OFFICIAL_COURT_COPY") if r["source_id"] == "C5-SRC-J-SC-2013-DHARAMVIR" else r for r in m]
        with self.assertRaises(SystemExit):
            B.check_holding_vs_copies(bad2, copies)
        B.check_holding_vs_copies(m, copies)  # the committed state passes


class C5CopyLevelProvenance(unittest.TestCase):
    def test_act37_copies_keep_their_own_status(self):
        cs = {c["sha256"][:8]: c for c in read("source_copy_register.csv") if c["source_id"] == "C5-SRC-P0-AA-AMD-ACT37-1992"}
        self.assertEqual(set(cs), {"f11d443e", "a5943b72", "f1e69a74"})
        self.assertEqual(cs["f11d443e"]["eligible_for_exact_anchor"], "YES")
        self.assertEqual(cs["a5943b72"]["eligible_for_exact_anchor"], "NO")  # page-equivalent trailer-ID variant
        self.assertTrue(cs["a5943b72"]["page_equivalent_to"].startswith("f11d443e"))
        self.assertEqual(cs["a5943b72"]["c4_register_state"], "NO_REGISTER_ROW")
        self.assertEqual(cs["f1e69a74"]["copy_role"], "GOVERNMENT_TEXT_RENDERING")
        self.assertEqual(cs["f1e69a74"]["eligible_for_exact_anchor"], "NO")

    def test_one_instrument_one_source_row(self):
        self.assertEqual(sum(1 for r in read("source_master_register.csv") if "ACT37-1992" in r["source_id"]), 1)

    def test_exact_anchor_rows_name_an_eligible_copy(self):
        el = {c["copy_id"]: c for c in read("source_copy_register.csv") if c["eligible_for_exact_anchor"] == "YES"}
        for r in read("corpus_crosswalk.csv"):
            if r["evidence_status"] == "EXACT_ANCHOR":
                self.assertIn(r["anchor_copy_id"], el)
                self.assertEqual(el[r["anchor_copy_id"]]["source_id"], r["source_id"])


class C5PreservedCorrections(unittest.TestCase):
    def test_review_corrections_do_not_regress(self):
        m = master()
        self.assertEqual(m["C5-SRC-P2-RS-PAPERS-LAID-1987"]["publication_type"], "PARLIAMENTARY_RECORD")
        self.assertTrue(m["C5-SRC-P1-CCCM-ADJ-RULES"]["holding_state"].startswith("NOT_HELD"))
        er = m["C5-SRC-P1-ER-2023-HELD-13MB"]
        self.assertIn("INCOMPLETE", er["completeness_status"])
        self.assertIn("GMO-2023 (Appendix-II) ABSENT", er["completeness_status"])
        for sid, cur in (("C5-SRC-P0-AR-AMD-AR-008", "DECLARATION_INSTRUMENT"), ("C5-SRC-P0-AR-AMD-AR-033", "DECLARATION_INSTRUMENT"),
                         ("C5-SRC-P0-AR-AMD-AR-020", "CORRIGENDUM_INSTRUMENT")):
            self.assertEqual(m[sid]["currency_status"], cur)
        for sid in ("C5-SRC-P0-BNSS-2023", "C5-SRC-P0-BSA-2023"):
            self.assertEqual(m[sid]["holding_state"], "NOT_HELD_CANDIDATE_LOCATED")
            self.assertEqual(m[sid + "-INDIACODE"]["document_authority"], "GOVERNMENT_COMPILATION")
        r95 = [r for r in read("corpus_crosswalk.csv") if r["provision_id"] == "rules-army-rules-1954#r95"]
        self.assertTrue(r95 and all(r["evidence_status"] == "PARTIAL_MATCH" for r in r95))
        pic = {r["check_id"]: r for r in csv.DictReader(open(PKG / "inputs/page_image_checks_c5.csv", encoding="utf-8"))}
        self.assertIn("disagreement", pic["C5-PIC-02"]["reader"])
        self.assertIn("S.O. 4010", (PKG / "reports/D7_INDEPENDENT_REVIEW_REPORT.md").read_text())

    def test_territorial_army_reclassification_is_evidence_bounded(self):
        m = master()
        for sid in ("C5-SRC-P1-TA-RULES-1948", "C5-SRC-P1-TA-REGULATIONS"):
            r = m[sid]
            self.assertEqual(r["holding_state"], "NOT_HELD_CANDIDATE_LOCATED")  # located, not acquired
            self.assertEqual(r["evidence_stage"], "OFFICIAL_CANDIDATE_LOCATED")
            self.assertIn("BLOCKED_ACCESS", r["verification_limitations"])
            self.assertIn("C5D-", r["discovery_candidate_ids"])
            self.assertEqual(r["sha256"], "")
            self.assertEqual(r["currency_status"], "CURRENCY_NOT_ESTABLISHED")
        self.assertEqual(m["C5-SRC-P0-RA-1987"]["evidence_stage"], "LEAD_ONLY")

    def test_evidence_stage_vocabulary(self):
        for r in read("source_master_register.csv"):
            self.assertNotEqual(r["evidence_stage"], "DOCUMENT_AUTHENTICATED")
            self.assertEqual(r["evidence_stage"], B.evidence_stage(r))


class C5AdviserIndex(unittest.TestCase):
    def test_index_makes_no_determination_and_counts_escalations(self):
        rows = read("legal_adviser_evidence_index.csv")
        self.assertEqual(sum(1 for r in rows if r["item_type"].startswith("C4_ESCALATION_")), 29)
        self.assertTrue(all(r["determination"].startswith("NONE") for r in rows))
        res = {r["origin_id"]: r["current_state"] for r in rows if r["item_type"] == "RESERVED_ITEM"}
        self.assertEqual(res["RES-r23(3)"], "CONFLICTING (unchanged)")
        self.assertEqual(res["RES-C-08"], "OPEN (unchanged)")
        self.assertEqual(res["RES-C-09"], "PROPOSAL (unchanged)")


class C5DiscoveryGuard(unittest.TestCase):
    def test_unreadable_robots_fail_closed(self):
        for kw in (dict(status=0, error="timeout"), dict(status="000"), dict(status=403), dict(status=500), dict(status=429),
                   dict(status=200, body=b"<html>error</html>", content_type="text/html"),
                   dict(status=200, body=b"User-agent: *", content_type="application/octet-stream"),
                   dict(status=200, body=b"User-agent: *", final_host="other.example", requested_host="a.example")):
            self.assertEqual(G.robots_decision(**kw)[0], "UNAVAILABLE", kw)
        robots = {"a.gov.in": G.robots_decision(status=0, error="reset")}
        self.assertEqual(G.may_request("https://a.gov.in/x", robots), (False, "ROBOTS_UNAVAILABLE"))
        self.assertEqual(G.may_request("https://b.gov.in/x", robots), (False, "ROBOTS_NOT_ESTABLISHED"))

    def test_no_robots_file_and_disallow(self):
        self.assertEqual(G.robots_decision(status=404)[0], "NO_ROBOTS_FILE")
        st = G.robots_decision(status=200, body=b"User-agent: *\nDisallow: /catalogue\n", content_type="text/plain")
        robots = {"x.gov.uk": st}
        self.assertFalse(G.may_request("https://x.gov.uk/catalogue/1", robots)[0])
        self.assertTrue(G.may_request("https://x.gov.uk/other", robots)[0])
        self.assertFalse(G.may_request("http://x.gov.uk/other", robots)[0])  # HTTPS only

    def test_blocked_hosts_and_bare_ip(self):
        robots = {h: ("NO_ROBOTS_FILE", None) for h in ("aftjabalpur.in", "www.aftjabalpur.in", "10.0.0.1")}
        for u in ("https://aftjabalpur.in/", "https://www.aftjabalpur.in/a", "https://10.0.0.1/x"):
            self.assertEqual(G.may_request(u, robots), (False, "BLOCKED_HOST"))

    def test_redirect_hops_assessed_separately(self):
        robots = {"a.gov.in": ("NO_ROBOTS_FILE", None)}
        ok, why = G.redirect_chain_allowed(["https://a.gov.in/f", "https://cdn.example.net/f.pdf"], robots)
        self.assertFalse(ok)
        self.assertIn("ROBOTS_NOT_ESTABLISHED:cdn.example.net", why)
        robots["cdn.example.net"] = ("UNAVAILABLE", None)
        self.assertFalse(G.redirect_chain_allowed(["https://a.gov.in/f", "https://cdn.example.net/f"], robots)[0])
        self.assertFalse(G.redirect_chain_allowed(["https://a.gov.in/f", "https://aftjabalpur.in/f"], robots)[0])

    def test_payload_classification_not_by_extension(self):
        # misleading extension: an HTML error page at a .pdf URL is a listing, not a document
        self.assertEqual(G.classify_response("GET", 200, "text/html; charset=utf-8", "", None, b"<!DOCTYPE")[0], "METADATA_OR_LISTING")
        # query-based endpoint with no extension in the path
        u = "https://upload.indiacode.nic.in/showfile?actid=X&filename=TA+Rules+1948.pdf&type=rule"
        self.assertTrue(G.url_suggests_document(u))
        self.assertEqual(G.classify_response("GET", 200, "application/pdf")[0], "DOCUMENT_PAYLOAD")
        # mislabelled content type but PDF signature, and attachment disposition
        self.assertEqual(G.classify_response("GET", 200, "text/html", "", None, b"%PDF-1.4")[0], "DOCUMENT_PAYLOAD")
        self.assertEqual(G.classify_response("GET", 200, "text/plain", 'attachment; filename="x.pdf"')[0], "DOCUMENT_PAYLOAD")
        self.assertEqual(G.classify_response("HEAD", 200, "application/pdf")[0], "HEADERS_ONLY_DOCUMENT_INDICATED")
        self.assertEqual(G.classify_response("GET", 200, "")[0], "UNKNOWN")

    def test_v2_log_validation(self):
        base = {c: "" for c in G.LOG_V2_COLUMNS}
        rows = [dict(base, method="GET", url="https://a.gov.in/robots.txt", http_status="000", robots_state="UNAVAILABLE", purpose="robots"),
                dict(base, method="NONE", url="https://a.gov.in/f", robots_state="UNAVAILABLE", purpose="t1"),
                dict(base, method="HEAD", url="https://a.gov.in/f", robots_state="UNAVAILABLE", purpose="t1"),
                dict(base, method="GET", url="https://b.gov.in/showfile?f=x.pdf", payload_class="DOCUMENT_PAYLOAD", robots_state="NO_ROBOTS_FILE", purpose="t2")]
        e = G.validate_log_v2(rows)
        self.assertEqual(len(e), 2)
        self.assertTrue(any("robots policy is UNAVAILABLE" in x for x in e))
        self.assertTrue(any("without an acquisition approval reference" in x for x in e))
        rows[3]["acquisition_approval_ref"] = "A-C5-1"
        self.assertEqual(len(G.validate_log_v2(rows[:2] + rows[3:])), 0)

    def test_committed_v2_log_clean_and_legacy_logs_bounded(self):
        rows = list(csv.DictReader(open(PKG / "discovery/D_requests_v2.tsv", encoding="utf-8"), delimiter="\t"))
        self.assertEqual(G.validate_log_v2([r for r in rows if r["method"] != "WEBSEARCH"]), [])
        req = [r for r in rows if r["method"] not in ("WEBSEARCH", "NONE")]
        self.assertFalse(any(r["method"] == "GET" and r["purpose"] != "robots" and r["payload_class"] != "METADATA_OR_LISTING" for r in req))
        self.assertFalse(any("DOCUMENT_PAYLOAD" == r["payload_class"] for r in req))
        for f in ("A", "B", "C"):
            lines = [l.rstrip("\n").split("\t") for l in open(PKG / f"discovery/{f}_requests.tsv", encoding="utf-8")]
            err, _sus = G.legacy_log_findings(lines)
            self.assertEqual(err, [])


if __name__ == "__main__":
    unittest.main()
