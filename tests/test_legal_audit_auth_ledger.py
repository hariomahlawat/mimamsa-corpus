"""AUTH-LEDGER (Cycle 7): zero-entry reproduction, ledger integrity, approval controls, evidence rules, state
transitions, crosswalk versioning and offline operation. Synthetic ledgers are built in temporary directories only;
nothing here approves or activates any entry in the committed ledger."""
import csv, json, shutil, socket, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
AW = REPO / "legal_knowledge/audit_work"
PKG = AW / "AUTH-LEDGER"
sys.path.insert(0, str(PKG / "tools"))
import common  # noqa: E402
import ledger as L  # noqa: E402
import pins  # noqa: E402
import reader  # noqa: E402
import rules_v1 as R  # noqa: E402
import strength  # noqa: E402
import auth_ledger as CLI  # noqa: E402

EXPECTED_HEAD = "0 c62c7769d6f5df66ea2afce5a494b81b6b9dbc945a3a86fe4baf9a9b3deda3ac"  # a ledger change must change this too
ISAAC = "3f49a31464fec174cdbff5d9e194fa888ca00529b6246eacdc8ac2368eab4653"
DRAFT = {r["sha256"]: r for r in csv.DictReader(open(AW / "C6-01-PROVENANCE/addendum/authentication_addendum_v1_draft.csv", encoding="utf-8"))}
PROPS = {r["sha256"]: r for r in csv.DictReader(open(AW / "C6-01-PROVENANCE/registers/source_authentication_proposals.csv", encoding="utf-8"))}


def sha_of(prefix, pool):
    hits = [s for s in pool if s.startswith(prefix)]
    assert len(hits) == 1, prefix
    return hits[0]


RECOVERY = [r["sha256"] for r in csv.DictReader(open(AW / "C6-01-PROVENANCE/registers/provenance_recovery_register.csv", encoding="utf-8"))]
DHARAMVIR = sha_of("3056712c", DRAFT)
RAJBIR_C1 = sha_of("970b9680", DRAFT)
RAJBIR_BOSIR = sha_of("6b495f14", DRAFT)
GAZETTE_1962 = sha_of("b76bf4aa", DRAFT)
TRA = sha_of("be619533", DRAFT)


def entry_from_draft(sha, n, version=1, **over):
    d, p = DRAFT[sha], PROPS[sha]
    e = {k: "" for k in L.COLS}
    e.update({"entry_id": f"AL-v{version:04d}-{n:03d}", "entry_version": f"{version:04d}", "entry_type": "ADD", "sha256": sha,
              "source_id": d["source_id"], "copy_id": d["copy_id"], "document_identity": d["document_identity"],
              "evidence_refs": d["evidence_refs"], "first_class_record_ref": d["first_class_record_ref"], "identity_refs": d["identity_refs"],
              "proposed_authentication_state": "PROVENANCE_DOCUMENTED", "proposed_class": d["proposed_class"], "carrier": p["carrier"],
              "official_locator_recorded": p["official_locator_recorded"], "limitations": d["limitations"], "justification": "synthetic test entry",
              "rule_version": "1", "owner_decision": "APPROVED"})
    e.update(over)
    return e


class Synthetic:
    """A temporary ledger root: committed frozen pins and genesis, plus versions appended by tests."""
    def __init__(self):
        self.dir = Path(tempfile.mkdtemp(prefix="authledger_"))
        shutil.copy(PKG / "frozen_inputs.json", self.dir / "frozen_inputs.json")
        (self.dir / "ledger").mkdir()
        (self.dir / "decisions").mkdir()
        shutil.copy(PKG / "ledger/manifest.jsonl", self.dir / "ledger/manifest.jsonl")
        shutil.copy(PKG / "ledger/HEAD", self.dir / "ledger/HEAD")

    def add_version(self, entries, decision=True, review=True, rule_version=1, tamper=None):
        lines = L.read_manifest(self.dir)
        v = len(lines)
        decisions, reviews = {}, {}
        approved = [e for e in entries if e["owner_decision"] == "APPROVED"]
        pairs = ";".join(f"{e['entry_id']}={e['sha256']}" for e in approved)
        if approved and decision:
            ref = f"decisions/D-v{v:04d}.md"
            (self.dir / ref).write_text(f"decision_id: D-v{v:04d}\ndecision: APPROVED\nledger_version: {v:04d}\nentries: {pairs}\n"
                                        "decided_by: test owner\ndate: 2026-11-23\n", encoding="utf-8")
            decisions[ref] = common.sha256_file(self.dir / ref)
        if approved and review:
            ref = f"decisions/R-v{v:04d}.md"
            (self.dir / ref).write_text(f"review_id: R-v{v:04d}\nverdict: ACCEPT\nledger_version: {v:04d}\nentries: {pairs}\n"
                                        "reviewer: test reviewer\ndate: 2026-11-23\n", encoding="utf-8")
            reviews[ref] = common.sha256_file(self.dir / ref)
        for e in approved:
            if decision and not e.get("decision_record_ref"):
                e["decision_record_ref"] = f"decisions/D-v{v:04d}.md"
                e["decision_record_sha256"] = decisions[e["decision_record_ref"]]
            if review and not e.get("reviewer_ref"):
                e["reviewer_ref"] = f"decisions/R-v{v:04d}.md"
                e["reviewer_record_sha256"] = reviews[e["reviewer_ref"]]
        f = f"ledger/v{v:04d}.csv"
        (self.dir / f).write_text(common.csv_text(L.COLS, entries), encoding="utf-8")
        prev = common.sha256_text((self.dir / "ledger/manifest.jsonl").read_text(encoding="utf-8").split("\n")[-2])
        line = {"version": v, "prev": prev, "date": "2026-11-23", "rule_version": rule_version,
                "frozen_inputs_sha256": common.sha256_file(self.dir / "frozen_inputs.json"), "file": f,
                "file_sha256": common.sha256_file(self.dir / f), "decisions": decisions, "reviews": reviews, "effective_sha256": "", "note": "test"}
        if tamper:
            tamper(line)
        s = L.canonical_line(line)
        with open(self.dir / "ledger/manifest.jsonl", "a", encoding="utf-8") as fh:
            fh.write(s + "\n")
        (self.dir / "ledger/HEAD").write_text(f"{v} {common.sha256_text(s)}\n", encoding="utf-8")
        return v

    def state(self, as_of=None):
        texts, _ = reader.effective_state(self.dir, as_of)
        return texts

    def close(self):
        shutil.rmtree(self.dir, ignore_errors=True)


def rows(text):
    return list(csv.DictReader(text.splitlines()))


def case_status(texts, case_id):
    return [r["evidence_status"] for r in rows(texts["corpus_crosswalk.csv"]) if r["case_id"] == case_id][0]


V0 = None


def v0():
    global V0
    if V0 is None:
        V0, _ = reader.effective_state(PKG, 0)
    return V0


class Baseline(unittest.TestCase):
    def test_committed_ledger_verifies_and_head_is_pinned(self):
        self.assertEqual(CLI.verify(), ["v0000 ok"])
        self.assertEqual(L.head_value(PKG), EXPECTED_HEAD)
        self.assertEqual(len(L.read_manifest(PKG)), 1)  # zero approved entries: genesis only
        self.assertEqual(sorted(p.name for p in (PKG / "ledger").iterdir()), ["HEAD", "manifest.jsonl"])

    def test_v0000_byte_identical_to_cycle5(self):
        for k in reader.FROZEN_EQUAL:
            self.assertEqual(v0()[k], (AW / "SOURCE-LIBRARY-C5/registers" / k).read_text(encoding="utf-8"), k)
        st = rows(v0()["source_states.csv"])
        self.assertTrue(all(r["frozen_holding_state"] == r["effective_holding_state"] for r in st))
        self.assertEqual(rows(v0()["transitions.csv"]), [])
        self.assertEqual(rows(v0()["newly_withdrawn.csv"]), [])

    def test_rule_v1_equals_frozen_cycle4_rule_on_every_held_sha(self):
        reader.frozen_builder()
        import evidence_classification as EC
        ev = EC.Evidence.from_dir(AW / "CALIBRATION-02")
        held = reader._held_index()
        for s in held:
            self.assertEqual(R.copy_status(s, held[s], ev.register.get(s))[0], ev.source_status(s)[0], s[:12])
        self.assertEqual(R.copy_status(ISAAC, held[ISAAC], ev.register[ISAAC])[0], R.PENDING)
        self.assertEqual(len(ev.register), 13)

    def test_no_c6_proposal_active(self):
        cop = {r["sha256"]: r for r in rows(v0()["source_copy_register.csv"])}
        for s in PROPS:
            self.assertEqual(cop[s]["c4_register_state"], "NO_REGISTER_ROW")
            self.assertEqual(cop[s]["eligible_for_exact_anchor"], "NO")

    def test_frozen_file_mismatch_fails_closed(self):
        t = Synthetic()
        try:
            pj = json.loads((t.dir / "frozen_inputs.json").read_text())
            k = "legal_knowledge/audit_work/CALIBRATION-02/registers/source_authentication_register.csv"
            pj["files"][k] = "0" * 64
            (t.dir / "frozen_inputs.json").write_text(json.dumps(pj))
            with self.assertRaises(common.LedgerError):
                pins.verify(t.dir)
            with self.assertRaises(common.LedgerError):
                t.state()
        finally:
            t.close()

    def test_pins_cover_every_file_the_frozen_builder_reads(self):
        import builtins, os
        seen, orig = set(), builtins.open
        def tr(f, *a, **k):
            p = Path(f).resolve() if isinstance(f, (str, os.PathLike)) else None
            if p and str(p).startswith(str(REPO)):
                seen.add(str(p.relative_to(REPO)))
            return orig(f, *a, **k)
        builtins.open = tr
        try:
            reader.effective_state(PKG, 0)
        finally:
            builtins.open = orig
        pinned = set(json.loads((PKG / "frozen_inputs.json").read_text())["files"])
        own = {x for x in seen if x.startswith("legal_knowledge/audit_work/AUTH-LEDGER/")}
        self.assertEqual(sorted(seen - pinned - own), [])


class LedgerIntegrity(unittest.TestCase):
    def setUp(self):
        self.t = Synthetic()

    def tearDown(self):
        self.t.close()

    def test_valid_add_and_chain(self):
        self.t.add_version([entry_from_draft(DHARAMVIR, 1)])
        self.assertEqual(len(L.read_manifest(self.t.dir)), 2)

    def test_modified_earlier_version_detected(self):
        self.t.add_version([entry_from_draft(DHARAMVIR, 1)])
        self.t.add_version([entry_from_draft(GAZETTE_1962, 1, version=2)])
        p = self.t.dir / "ledger/v0001.csv"
        p.write_text(p.read_text().replace("synthetic test entry", "edited"))
        with self.assertRaisesRegex(common.LedgerError, "modified after it was recorded"):
            self.t.state()

    def test_edited_manifest_line_detected(self):
        self.t.add_version([entry_from_draft(DHARAMVIR, 1)])
        m = self.t.dir / "ledger/manifest.jsonl"
        lines = m.read_text().split("\n")
        lines[1] = lines[1].replace('"note":"test"', '"note":"tampered"')
        m.write_text("\n".join(lines))
        with self.assertRaises(common.LedgerError):
            L.read_manifest(self.t.dir)

    def test_deleted_or_reordered_lines_detected(self):
        self.t.add_version([entry_from_draft(DHARAMVIR, 1)])
        self.t.add_version([entry_from_draft(GAZETTE_1962, 1, version=2)])
        m = self.t.dir / "ledger/manifest.jsonl"
        ls = m.read_text().split("\n")
        m.write_text("\n".join([ls[0], ls[2], ls[1], ""]))
        with self.assertRaises(common.LedgerError):
            L.read_manifest(self.t.dir)
        m.write_text("\n".join([ls[0], ls[2], ""]))
        with self.assertRaises(common.LedgerError):
            L.read_manifest(self.t.dir)

    def test_head_must_match(self):
        self.t.add_version([entry_from_draft(DHARAMVIR, 1)])
        (self.t.dir / "ledger/HEAD").write_text(EXPECTED_HEAD + "\n")  # rolled back HEAD
        with self.assertRaises(common.LedgerError):
            L.read_manifest(self.t.dir)

    def test_duplicate_active_entry_rejected(self):
        self.t.add_version([entry_from_draft(DHARAMVIR, 1), entry_from_draft(DHARAMVIR, 2)])
        with self.assertRaisesRegex(common.LedgerError, "live row already exists"):
            self.t.state()

    def test_duplicate_entry_id_rejected(self):
        self.t.add_version([entry_from_draft(DHARAMVIR, 1), entry_from_draft(GAZETTE_1962, 1)])
        with self.assertRaisesRegex(common.LedgerError, "duplicate entry id"):
            self.t.state()

    def test_missing_decision_or_reviewer_rejected(self):
        self.t.add_version([entry_from_draft(DHARAMVIR, 1)], decision=False)
        with self.assertRaisesRegex(common.LedgerError, "missing decision record"):
            self.t.state()
        t2 = Synthetic()
        try:
            t2.add_version([entry_from_draft(DHARAMVIR, 1)], review=False)
            with self.assertRaisesRegex(common.LedgerError, "missing review record"):
                t2.state()
        finally:
            t2.close()

    def test_forged_or_altered_decision_rejected(self):
        self.t.add_version([entry_from_draft(DHARAMVIR, 1)])
        d = self.t.dir / "decisions/D-v0001.md"
        d.write_text(d.read_text() + "note: altered after pinning\n")
        with self.assertRaisesRegex(common.LedgerError, "missing or modified"):
            self.t.state()

    def test_decision_not_pinned_in_manifest_rejected(self):
        self.t.add_version([entry_from_draft(DHARAMVIR, 1)], tamper=lambda line: line.update(decisions={}))
        with self.assertRaisesRegex(common.LedgerError, "manifest pin"):
            self.t.state()

    def test_file_merely_saying_approved_is_not_enough(self):
        e = entry_from_draft(DHARAMVIR, 1)
        (self.t.dir / "decisions/fake.md").write_text("APPROVED APPROVED decision: APPROVED\n")
        e["decision_record_ref"] = "decisions/fake.md"
        e["decision_record_sha256"] = common.sha256_file(self.t.dir / "decisions/fake.md")
        self.t.add_version([e], decision=False)
        with self.assertRaisesRegex(common.LedgerError, "manifest pin|does not name this entry"):
            self.t.state()

    def test_decision_contradicting_entry_rejected(self):
        e = entry_from_draft(DHARAMVIR, 1)
        self.t.add_version([e])
        d = self.t.dir / "decisions/D-v0001.md"
        # rebuild a consistent-hash version whose decision says REJECTED while the entry says APPROVED
        t2 = Synthetic()
        try:
            e2 = entry_from_draft(DHARAMVIR, 1)
            (t2.dir / "decisions/D-v0001.md").write_text(d.read_text().replace("decision: APPROVED", "decision: REJECTED"))
            e2["decision_record_ref"] = "decisions/D-v0001.md"
            e2["decision_record_sha256"] = common.sha256_file(t2.dir / "decisions/D-v0001.md")
            t2.add_version([e2], decision=False, tamper=lambda line: line["decisions"].update({"decisions/D-v0001.md": e2["decision_record_sha256"]}))
            with self.assertRaisesRegex(common.LedgerError, "decision record says 'REJECTED'"):
                t2.state()
        finally:
            t2.close()

    def test_non_approved_entry_has_no_effect(self):
        self.t.add_version([entry_from_draft(DHARAMVIR, 1, owner_decision="WITHHELD")])
        s = self.t.state()
        for k in reader.FROZEN_EQUAL:
            self.assertEqual(s[k], v0()[k])

    def test_rule_version_2_not_activated(self):
        self.t.add_version([entry_from_draft(DHARAMVIR, 1)], rule_version=2)
        with self.assertRaisesRegex(common.LedgerError, "rule version 2 is not implemented"):
            self.t.state()


class Provenance(unittest.TestCase):
    def setUp(self):
        self.t = Synthetic()

    def tearDown(self):
        self.t.close()

    def reject(self, e, why):
        self.t.add_version([e])
        with self.assertRaisesRegex(common.LedgerError, why):
            self.t.state()

    def test_sibling_copy_provenance_rejected(self):
        c2 = sha_of("c6ec489d", RECOVERY)
        e = entry_from_draft(RAJBIR_C1, 1, sha256=c2, copy_id="C5-SRC-J-SC-2015-RAJBIR~C2",
                             first_class_record_ref="PILOT-01/sources/independent-reviewer-blind.json#S-BLIND-013")
        self.reject(e, "own sha256 is not the entry key")

    def test_disclaimed_retrieval_record_rejected(self):
        with self.assertRaisesRegex(common.LedgerError, "disclaims authenticity"):
            strength.first_class("PILOT-01/sources/independent-reviewer-A.json#S-REVA-021", sha_of("fa51a4b1", RECOVERY))

    def test_identifier_only_download_record_rejected(self):
        act13 = [r for r in csv.DictReader(open(AW / "C6-01-PROVENANCE/registers/provenance_recovery_register.csv", encoding="utf-8")) if "ACT13" in r["source_id"]][0]
        with self.assertRaisesRegex(common.LedgerError, "identifier, not a URL"):
            strength.first_class("PILOT-01/registers/source_discovery_2026-11-22.csv#T6-03", act13["sha256"])

    def test_snapshot_entry_is_not_first_class(self):
        with self.assertRaisesRegex(common.LedgerError, "not a first-class record type"):
            strength.first_class("ACQ-01/archive_org_metadata_snapshot.json#in.gazette.central.e.2022-06-06.236353/236353.pdf", sha_of("2bdab5b7", DRAFT))

    def test_unresolved_and_prefix_references_rejected(self):
        self.reject(entry_from_draft(DHARAMVIR, 1, first_class_record_ref="PILOT-01/sources/nonexistent.json#S-X"), "not found")
        for bad in ("PILOT-01/registers/source_code_resolution_v3.csv#SRC-RANJI", "PILOT-01/sources/independent-reviewer-blind.json#S-BLIND-01"):
            with self.assertRaises(common.LedgerError):
                strength.resolve(bad)
        self.assertTrue(strength.resolve("PILOT-01/registers/source_code_resolution_v3.csv#SRC-RANJIT"))

    def test_wrong_copy_association_rejected(self):
        self.reject(entry_from_draft(DHARAMVIR, 1, copy_id="C5-SRC-J-SC-2015-RAJBIR~C1"), "is not the Cycle 5 copy")

    def test_unsupported_class_rejected(self):
        self.reject(entry_from_draft(DHARAMVIR, 1, proposed_class="PRIMARY_INVENTED_CLASS"), "proposed_class.*not allowed")

    def test_primary_class_failing_fidelity_rejected(self):
        self.reject(entry_from_draft(TRA, 1, proposed_class="PRIMARY_GAZETTE_GOVERNMENT_HOSTED_SCAN"), "fails copy fidelity")

    def test_court_class_on_publication_rejected(self):
        self.reject(entry_from_draft(GAZETTE_1962, 1, proposed_class="PRIMARY_OFFICIAL_COURT_COPY"), "does not fit publication type")

    def test_contradiction_rejected_and_urls_not_silently_equated(self):
        url = strength.first_class(DRAFT[DHARAMVIR]["first_class_record_ref"], DHARAMVIR)[2]
        orig = strength.url_pairs
        strength.url_pairs = lambda: orig() | {(url, "f" * 64)}
        try:
            self.reject(entry_from_draft(DHARAMVIR, 1), "contradiction")
            self.assertEqual(strength.contradiction(url + "/", DHARAMVIR), [])  # rule 1 is exact-string: variants are not merged
        finally:
            strength.url_pairs = orig

    def test_ledger_has_no_legal_status_field(self):
        for k in L.COLS:
            self.assertFalse(any(w in k for w in ("legal", "in_force", "currency", "applicab")), k)


class Transitions(unittest.TestCase):
    def setUp(self):
        self.t = Synthetic()

    def tearDown(self):
        self.t.close()

    def test_add_primary_court_copy_lifts_case(self):
        self.t.add_version([entry_from_draft(DHARAMVIR, 1)])
        s = self.t.state()
        self.assertEqual(case_status(v0(), "DCLR-SC-2013-N08"), "PARTIAL_MATCH")
        self.assertEqual(case_status(s, "DCLR-SC-2013-N08"), "EXACT_ANCHOR")
        st = {r["source_id"]: r for r in rows(s["source_states.csv"])}["C5-SRC-J-SC-2013-DHARAMVIR"]
        self.assertEqual(st["effective_holding_state"], "HELD_PRIMARY_OFFICIAL_COURT_COPY")
        changed = [a for a, b in zip(rows(v0()["corpus_crosswalk.csv"]), rows(s["corpus_crosswalk.csv"])) if a["evidence_status"] != b["evidence_status"]]
        self.assertEqual([r["case_id"] for r in changed], ["DCLR-SC-2013-N08"])  # only the supported citation changes

    def test_gazette_add_changes_no_crosswalk_row(self):
        self.t.add_version([entry_from_draft(GAZETTE_1962, 1)])
        s = self.t.state()
        self.assertEqual([r["evidence_status"] for r in rows(s["corpus_crosswalk.csv"])], [r["evidence_status"] for r in rows(v0()["corpus_crosswalk.csv"])])
        self.assertEqual(json.loads(s["coverage_summary.json"])["authentication"]["documented_primary_copies"], 13)

    def test_non_primary_never_anchors(self):
        self.t.add_version([entry_from_draft(RAJBIR_BOSIR, 1)])
        s = self.t.state()
        self.assertEqual(case_status(s, "DCLR-SC-2015-N09"), "PARTIAL_MATCH")
        cop = {r["sha256"]: r for r in rows(s["source_copy_register.csv"])}[RAJBIR_BOSIR]
        self.assertEqual((cop["copy_effective_status"], cop["eligible_for_exact_anchor"]), ("DOCUMENTED_NON_PRIMARY", "NO"))

    def test_primary_and_non_primary_coexist_and_joint_effect_is_derived(self):
        self.t.add_version([entry_from_draft(RAJBIR_C1, 1), entry_from_draft(RAJBIR_BOSIR, 2), entry_from_draft(DHARAMVIR, 3)])
        s = self.t.state()
        cw = rows(s["corpus_crosswalk.csv"])
        rajbir = [r for r in cw if r["case_id"] == "DCLR-SC-2015-N09"][0]
        self.assertEqual((rajbir["evidence_status"], rajbir["anchor_copy_id"]), ("EXACT_ANCHOR", "C5-SRC-J-SC-2015-RAJBIR~C1"))
        cases = json.loads(s["coverage_summary.json"])["crosswalk_case_rows_by_status"]
        self.assertEqual(cases["EXACT_ANCHOR"], 8)  # 6 + 2 distinct cases, not 6 + 3 entries

    def test_withdraw_restores_previous_state_columns(self):
        self.t.add_version([entry_from_draft(DHARAMVIR, 1)])
        w = entry_from_draft(DHARAMVIR, 1, version=2, entry_type="WITHDRAW", target_entry_id="AL-v0001-001", withdrawal_reason="OTHER",
                             first_class_record_ref="", proposed_authentication_state="", proposed_class="", justification="test withdrawal")
        self.t.add_version([w])
        s = self.t.state()
        for k in reader.FROZEN_EQUAL:
            self.assertEqual(s[k], v0()[k], k)
        self.assertEqual(len(rows(s["newly_withdrawn.csv"])), 1)
        self.assertEqual(len(rows(s["transitions.csv"])), 2)  # the record stays

    def test_withdraw_then_new_add(self):
        self.t.add_version([entry_from_draft(DHARAMVIR, 1)])
        self.t.add_version([entry_from_draft(DHARAMVIR, 1, version=2, entry_type="WITHDRAW", target_entry_id="AL-v0001-001", withdrawal_reason="OTHER",
                                             first_class_record_ref="", proposed_authentication_state="", proposed_class="", justification="w")])
        self.t.add_version([entry_from_draft(DHARAMVIR, 1, version=3)])
        self.assertEqual(case_status(self.t.state(), "DCLR-SC-2013-N08"), "EXACT_ANCHOR")

    def test_withdraw_for_contradiction_keeps_adverse_state(self):
        self.t.add_version([entry_from_draft(DHARAMVIR, 1)])
        self.t.add_version([entry_from_draft(DHARAMVIR, 1, version=2, entry_type="WITHDRAW", target_entry_id="AL-v0001-001",
                                             withdrawal_reason="CONTRADICTION", resulting_state="AUTHENTICATION_PENDING",
                                             first_class_record_ref="", proposed_authentication_state="", proposed_class="", justification="w")])
        s = self.t.state()
        st = {r["source_id"]: r for r in rows(s["source_states.csv"])}["C5-SRC-J-SC-2013-DHARAMVIR"]
        self.assertEqual(st["effective_holding_state"], "HELD_AUTHENTICATION_PENDING")
        self.assertEqual(case_status(s, "DCLR-SC-2013-N08"), "PARTIAL_MATCH")

    def test_withdraw_of_withdraw_invalid(self):
        self.t.add_version([entry_from_draft(DHARAMVIR, 1)])
        self.t.add_version([entry_from_draft(DHARAMVIR, 1, version=2, entry_type="WITHDRAW", target_entry_id="AL-v0001-001",
                                             withdrawal_reason="CONTRADICTION", resulting_state="AUTHENTICATION_PENDING",
                                             first_class_record_ref="", proposed_authentication_state="", proposed_class="", justification="w")])
        self.t.add_version([entry_from_draft(DHARAMVIR, 1, version=3, entry_type="WITHDRAW", target_entry_id="AL-v0002-001",
                                             withdrawal_reason="OTHER", first_class_record_ref="", proposed_authentication_state="", proposed_class="", justification="w")])
        with self.assertRaisesRegex(common.LedgerError, "WITHDRAW of a WITHDRAW"):
            self.t.state()

    def test_loss_of_only_primary_copy_of_baseline_source(self):
        base = next(r for r in csv.DictReader(open(AW / "CALIBRATION-02/registers/source_authentication_register.csv", encoding="utf-8"))
                    if r["effective_source_class"] == "PRIMARY_OFFICIAL_COURT_COPY")
        cop = {r["sha256"]: r for r in rows(v0()["source_copy_register.csv"])}[base["sha256"]]
        e = {k: "" for k in L.COLS}
        e.update({"entry_id": "AL-v0001-001", "entry_version": "0001", "entry_type": "WITHDRAW", "sha256": base["sha256"],
                  "source_id": cop["source_id"], "copy_id": cop["copy_id"], "document_identity": base["document_identity"],
                  "target_entry_id": "BASELINE:" + base["sha256"], "withdrawal_reason": "EVIDENCE_REVOKED", "justification": "test",
                  "rule_version": "1", "owner_decision": "APPROVED"})
        self.t.add_version([e])
        s = self.t.state()
        st = {r["source_id"]: r for r in rows(s["source_states.csv"])}[cop["source_id"]]
        self.assertEqual(st["effective_holding_state"], "HELD_OFFICIAL_COURT_COPY_PROVENANCE_UNDOCUMENTED")
        self.assertEqual(json.loads(s["coverage_summary.json"])["authentication"]["documented_primary_copies"], 11)

    def test_correction_to_class_removes_anchor(self):
        self.t.add_version([entry_from_draft(DHARAMVIR, 1)])
        c = entry_from_draft(DHARAMVIR, 1, version=2, entry_type="CORRECTION", target_entry_id="AL-v0001-001",
                             proposed_class="NON_PRIMARY_OFFICIAL_COURT_RENDITION", justification="test correction")
        self.t.add_version([c])
        self.assertEqual(case_status(self.t.state(), "DCLR-SC-2013-N08"), "PARTIAL_MATCH")

    def test_correction_must_target_live_row(self):
        self.t.add_version([entry_from_draft(DHARAMVIR, 1, version=1, entry_type="CORRECTION", target_entry_id="AL-v0009-001", justification="x")])
        with self.assertRaisesRegex(common.LedgerError, "not the live row"):
            self.t.state()

    def test_as_of_reproduces_earlier_versions(self):
        self.t.add_version([entry_from_draft(DHARAMVIR, 1)])
        for k in reader.FROZEN_EQUAL:
            self.assertEqual(self.t.state(0)[k], v0()[k])


class SourceDerivation(unittest.TestCase):
    """Direct tests of the explicit transition table (reader.derive_holding)."""
    def c(self, status, cls=""):
        return {"copy_effective_status": status, "c4_effective_source_class": cls}

    def test_table(self):
        P, U, N = R.EFFECTIVE_PRIMARY, R.UNKNOWN, R.DOC_NON_PRIMARY
        court = "PRIMARY_OFFICIAL_COURT_COPY"
        dh = reader.derive_holding
        self.assertEqual(dh("HELD_OFFICIAL_COURT_COPY_PROVENANCE_UNDOCUMENTED", [self.c(P, court)], False, "JUDICIAL")[0], "HELD_PRIMARY_OFFICIAL_COURT_COPY")
        self.assertEqual(dh("HELD_PRIMARY_OFFICIAL_COURT_COPY", [self.c(P, court), self.c(P, court)], False, "JUDICIAL")[0], "HELD_PRIMARY_OFFICIAL_COURT_COPY")  # two primary copies
        self.assertEqual(dh("HELD_OFFICIAL_COURT_COPY_PROVENANCE_UNDOCUMENTED", [self.c(P, court), self.c(N, "NON_PRIMARY_OFFICIAL_COURT_RENDITION")], False, "JUDICIAL")[0],
                         "HELD_PRIMARY_OFFICIAL_COURT_COPY")  # primary plus non-primary
        self.assertEqual(dh("HELD_OFFICIAL_COURT_COPY_PROVENANCE_UNDOCUMENTED", [self.c(N, "NON_PRIMARY_OFFICIAL_COURT_RENDITION")], False, "JUDICIAL")[0],
                         "HELD_OFFICIAL_COURT_COPY_PROVENANCE_UNDOCUMENTED")  # non-primary alone changes nothing
        self.assertEqual(dh("HELD_OFFICIAL_PUBLICATION_PROVENANCE_UNDOCUMENTED", [self.c(R.PENDING)], False, "GAZETTE_NOTIFICATION")[0], "HELD_AUTHENTICATION_PENDING")
        self.assertEqual(dh("HELD_PRIMARY_GAZETTE_FACSIMILE", [self.c(U)], True, "GAZETTE_NOTIFICATION")[0], "HELD_OFFICIAL_PUBLICATION_PROVENANCE_UNDOCUMENTED")
        with self.assertRaisesRegex(common.LedgerError, "no WITHDRAW/CORRECTION touched"):
            dh("HELD_PRIMARY_GAZETTE_FACSIMILE", [self.c(U)], False, "GAZETTE_NOTIFICATION")  # loss of primary without a ledger event
        with self.assertRaisesRegex(common.LedgerError, "ambiguous"):
            dh("HELD_OFFICIAL_PUBLICATION_PROVENANCE_UNDOCUMENTED", [self.c(P, "PRIMARY_GAZETTE_ARCHIVAL_FACSIMILE"), self.c(P, "PRIMARY_GAZETTE_GOVERNMENT_HOSTED_SCAN")], False, "STATUTE")
        with self.assertRaisesRegex(common.LedgerError, "unsupported primary class"):
            dh("HELD_OFFICIAL_PUBLICATION_PROVENANCE_UNDOCUMENTED", [self.c(P, "PRIMARY_INVENTED")], False, "STATUTE")
        with self.assertRaisesRegex(common.LedgerError, "pending copy on a source"):
            dh("NOT_HELD_NOT_CHECKED", [self.c(R.PENDING)], False, "STATUTE")
        self.assertEqual(dh("HELD_GOVERNMENT_COMPILATION", [self.c(U)], False, "STATUTE")[0], "HELD_GOVERNMENT_COMPILATION")

    def test_rule_v1_rejects_unknown_documented_class(self):
        with self.assertRaises(R.RuleError):
            R.copy_status("a" * 64, ["x.pdf"], {"authentication_state": "PROVENANCE_DOCUMENTED", "effective_source_class": "NON_PRIMARY_INVENTED",
                                                "provenance_references": "x", "held_paths": "x.pdf"})


class Operational(unittest.TestCase):
    def test_offline_no_network(self):
        orig = socket.socket
        def blocked(*a, **k):
            raise AssertionError("network access attempted")
        socket.socket = blocked
        try:
            reader.effective_state(PKG, 0)
        finally:
            socket.socket = orig

    def test_no_network_or_ai_imports(self):
        bad = ("urllib", "requests", "http.client", "httpx", "socket", "anthropic", "openai", "transformers")
        for f in (PKG / "tools").glob("*.py"):
            src = f.read_text(encoding="utf-8")
            for b in bad:
                self.assertNotIn(f"import {b}", src, f.name)
                self.assertNotIn(f"from {b}", src, f.name)

    def test_historical_files_unchanged_after_runs(self):
        reader.effective_state(PKG, 0)
        self.assertGreater(pins.verify(), 70)
        out = subprocess.run(["git", "-C", str(REPO), "status", "--porcelain", "--", "legal_knowledge/audit_work/CALIBRATION-02",
                              "legal_knowledge/audit_work/SOURCE-LIBRARY-C5", "legal_knowledge/curated_originals"], capture_output=True, text=True)
        self.assertEqual(out.stdout.strip(), "")


if __name__ == "__main__":
    unittest.main()
