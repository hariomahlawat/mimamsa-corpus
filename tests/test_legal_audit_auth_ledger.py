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

EXPECTED_HEAD = "0 443c4bdf348b2a1bcd603d2701f097aa90a8155efd43c10760f5fd86c76c6b6b"  # a ledger change must change this too
ISAAC = "3f49a31464fec174cdbff5d9e194fa888ca00529b6246eacdc8ac2368eab4653"
DRAFT = {r["sha256"]: r for r in common.read_csv(AW / "C6-01-PROVENANCE/addendum/authentication_addendum_v1_draft.csv")}
PROPS = {r["sha256"]: r for r in common.read_csv(AW / "C6-01-PROVENANCE/registers/source_authentication_proposals.csv")}


def sha_of(prefix, pool):
    hits = [s for s in pool if s.startswith(prefix)]
    assert len(hits) == 1, prefix
    return hits[0]


RECOVERY = [r["sha256"] for r in common.read_csv(AW / "C6-01-PROVENANCE/registers/provenance_recovery_register.csv")]
DHARAMVIR = sha_of("3056712c", DRAFT)
RAJBIR_C1 = sha_of("970b9680", DRAFT)
RAJBIR_BOSIR = sha_of("6b495f14", DRAFT)
GAZETTE_1962 = sha_of("b76bf4aa", DRAFT)
TRA = sha_of("be619533", DRAFT)


C5COPY = {r["sha256"]: r for r in common.read_csv(AW / "SOURCE-LIBRARY-C5/registers/source_copy_register.csv")}


def entry_from_draft(sha, n, version=1, **over):
    d, p = DRAFT[sha], PROPS[sha]
    e = {k: "" for k in L.COLS}
    e.update({"entry_id": f"AL-v{version:04d}-{n:03d}", "entry_version": f"{version:04d}", "entry_type": "ADD", "sha256": sha,
              "source_id": d["source_id"], "copy_id": d["copy_id"], "document_identity": d["document_identity"],
              "evidence_refs": d["evidence_refs"], "first_class_record_ref": d["first_class_record_ref"],
              "identity_refs": d["identity_refs"].replace("T:C6-01-PROVENANCE/inputs/held_copy_facts.csv#", "T:AUTH-LEDGER/evidence/copy_facts.csv#"),
              "proposed_authentication_state": "PROVENANCE_DOCUMENTED", "proposed_class": d["proposed_class"], "carrier": C5COPY[sha]["copy_carrier_provenance"],
              "official_locator_recorded": strength._first_class(d["first_class_record_ref"], sha)[2], "limitations": d["limitations"], "justification": "synthetic test entry",
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

    def write_record(self, name, text):
        (self.dir / "decisions" / name).write_text(text, encoding="utf-8")
        return f"decisions/{name}", common.sha256_file(self.dir / "decisions" / name)

    def add_version(self, entries, decision=True, review=True, rule_version=1, tamper=None, reviewer="test reviewer", decided_by="test owner",
                    review_extra=""):
        lines = L.read_manifest(self.dir)
        v = len(lines)
        decisions, reviews = {}, {}
        by_decision = {}
        for e in entries:
            by_decision.setdefault(e["owner_decision"], []).append(e)
        if decision:
            for dec, group in sorted(by_decision.items()):
                name = f"D-v{v:04d}.md" if dec == "APPROVED" else f"D-v{v:04d}-{dec.lower()}.md"
                pairs = ";".join(f"{e['entry_id']}={e['sha256']}:{L.entry_digest(e)}" for e in group)
                ref, h = self.write_record(name, f"decision_id: {name[:-3]}\ndecision: {dec}\nledger_version: {v:04d}\nentries: {pairs}\n"
                                                 f"decided_by: {decided_by}\ndate: 2026-11-23\n")
                decisions[ref] = h
                for e in group:
                    if not e.get("decision_record_ref"):
                        e["decision_record_ref"], e["decision_record_sha256"] = ref, h
        approved = by_decision.get("APPROVED", [])
        if approved and review:
            pairs = ";".join(f"{e['entry_id']}={e['sha256']}:{L.entry_digest(e)}" for e in approved)
            ref, h = self.write_record(f"R-v{v:04d}.md", f"review_id: R-v{v:04d}\nverdict: ACCEPT\nledger_version: {v:04d}\nentries: {pairs}\n"
                                                           f"reviewer: {reviewer}\ndate: 2026-11-23\n{review_extra}")
            reviews[ref] = h
            for e in approved:
                if not e.get("reviewer_ref"):
                    e["reviewer_ref"], e["reviewer_record_sha256"] = ref, h
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
        self.assertEqual(json.loads(v0()["transitions.json"]), [])
        self.assertEqual(json.loads(v0()["newly_withdrawn.json"]), [])

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
        ref, h = self.t.write_record("D-v0001.md", "APPROVED APPROVED\ndecision: APPROVED\n")
        e["decision_record_ref"], e["decision_record_sha256"] = ref, h
        self.t.add_version([e], decision=False, tamper=lambda line: line["decisions"].update({ref: h}))  # pinned, so content is checked
        with self.assertRaisesRegex(common.LedgerError, "decision_id must equal its file name"):
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
                             first_class_record_ref="PILOT-01/sources/independent-reviewer-blind.json#S-BLIND-013",
                             evidence_refs="L3:PILOT-01/sources/independent-reviewer-blind.json#S-BLIND-013")
        self.reject(e, "does not concern this sha256")
        with self.assertRaisesRegex(common.LedgerError, "own sha256 is not the entry key"):
            strength.first_class("PILOT-01/sources/independent-reviewer-blind.json#S-BLIND-013", c2)

    def test_disclaimed_retrieval_record_rejected(self):
        with self.assertRaisesRegex(common.LedgerError, "disclaims authenticity"):
            strength.first_class("PILOT-01/sources/independent-reviewer-A.json#S-REVA-021", sha_of("fa51a4b1", RECOVERY))

    def test_identifier_only_download_record_rejected(self):
        act13 = [r for r in common.read_csv(AW / "C6-01-PROVENANCE/registers/provenance_recovery_register.csv") if "ACT13" in r["source_id"]][0]
        with self.assertRaisesRegex(common.LedgerError, "identifier, not a URL"):
            strength.first_class("PILOT-01/registers/source_discovery_2026-11-22.csv#T6-03", act13["sha256"])

    def test_snapshot_entry_is_not_first_class(self):
        with self.assertRaisesRegex(common.LedgerError, "not a first-class record type"):
            strength.first_class("ACQ-01/archive_org_metadata_snapshot.json#in.gazette.central.e.2022-06-06.236353/236353.pdf", sha_of("2bdab5b7", DRAFT))

    def test_unresolved_and_prefix_references_rejected(self):
        self.reject(entry_from_draft(DHARAMVIR, 1, first_class_record_ref="PILOT-01/sources/nonexistent.json#S-X",
                                     evidence_refs="L3:PILOT-01/sources/nonexistent.json#S-X"), "not found")
        for bad in ("PILOT-01/registers/source_code_resolution_v3.csv#SRC-RANJI", "PILOT-01/sources/independent-reviewer-blind.json#S-BLIND-01"):
            with self.assertRaises(common.LedgerError):
                strength.resolve(bad)
        self.assertTrue(strength.resolve("PILOT-01/registers/source_code_resolution_v3.csv#SRC-RANJIT"))

    def test_wrong_copy_association_rejected(self):
        self.reject(entry_from_draft(DHARAMVIR, 1, copy_id="C5-SRC-J-SC-2015-RAJBIR~C1"), "is not the Cycle 5 copy")

    def test_unsupported_class_rejected(self):
        self.reject(entry_from_draft(DHARAMVIR, 1, proposed_class="PRIMARY_INVENTED_CLASS"), "proposed_class.*not allowed")

    def test_primary_class_failing_fidelity_rejected(self):
        self.reject(entry_from_draft(sha_of("2bdab5b7", DRAFT), 1, proposed_class="PRIMARY_GAZETTE_ARCHIVAL_FACSIMILE"), "fails copy fidelity")

    def test_scan_class_needs_scanned_copy(self):
        self.reject(entry_from_draft(TRA, 1, proposed_class="PRIMARY_GAZETTE_GOVERNMENT_HOSTED_SCAN"), "needs a scanned copy")

    def test_court_class_on_publication_rejected(self):
        self.reject(entry_from_draft(GAZETTE_1962, 1, proposed_class="NON_PRIMARY_PARLIAMENTARY_RECORD"), "does not fit publication type")

    def test_locator_host_must_suit_class(self):
        self.reject(entry_from_draft(GAZETTE_1962, 1, proposed_class="PRIMARY_OFFICIAL_COURT_COPY"), "does not suit class")

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


def withdraw(sha, n, version, target, reason="OTHER", resulting=""):
    return entry_from_draft(sha, n, version=version, entry_type="WITHDRAW", target_entry_id=target, withdrawal_reason=reason,
                            resulting_state=resulting, first_class_record_ref="", proposed_authentication_state="", proposed_class="",
                            justification="test withdrawal")


class Controls(unittest.TestCase):
    """One negative test per control (Fable review F-06 mutation survivors and F-01..F-13), each asserting its own message."""
    def setUp(self):
        self.t = Synthetic()

    def tearDown(self):
        self.t.close()

    def reject(self, entries, why, **kw):
        self.t.add_version(entries, **kw)
        with self.assertRaisesRegex(common.LedgerError, why):
            self.t.state()

    def test_record_must_name_entry_sha_and_digest(self):  # M02, F-03
        e = entry_from_draft(DHARAMVIR, 1, proposed_class="NON_PRIMARY_OFFICIAL_COURT_RENDITION")
        self.t.add_version([e])
        f = self.t.dir / "ledger/v0001.csv"  # change what was decided after the records were pinned, re-pin the file consistently
        rows_ = common.read_csv(f)
        rows_[0]["proposed_class"] = "PRIMARY_OFFICIAL_COURT_COPY"
        f.write_text(common.csv_text(L.COLS, rows_), encoding="utf-8")
        m = self.t.dir / "ledger/manifest.jsonl"
        line = json.loads(m.read_text().split("\n")[1])
        line["file_sha256"] = common.sha256_file(f)
        s0 = m.read_text().split("\n")[0]
        s1 = L.canonical_line(line)
        m.write_text(s0 + "\n" + s1 + "\n")
        (self.t.dir / "ledger/HEAD").write_text(f"1 {common.sha256_text(s1)}\n")
        with self.assertRaisesRegex(common.LedgerError, "content digest"):
            self.t.state()

    def test_record_version_must_match(self):  # M01
        e = entry_from_draft(DHARAMVIR, 1)
        pairs = f"{e['entry_id']}={e['sha256']}:{L.entry_digest(e)}"
        dref, dh = self.t.write_record("D-v0001.md", f"decision_id: D-v0001\ndecision: APPROVED\nledger_version: 0007\nentries: {pairs}\ndecided_by: owner\ndate: 2026-11-23\n")
        e["decision_record_ref"], e["decision_record_sha256"] = dref, dh
        self.reject([e], "is for ledger version '0007'", decision=False, tamper=lambda line: line["decisions"].update({dref: dh}))

    def test_accept_with_conditions_needs_discharge(self):
        e = entry_from_draft(DHARAMVIR, 1)
        pairs = f"{e['entry_id']}={e['sha256']}:{L.entry_digest(e)}"
        rref, rh = self.t.write_record("R-v0001.md", f"review_id: R-v0001\nverdict: ACCEPT_WITH_CONDITIONS\nledger_version: 0001\nentries: {pairs}\nreviewer: rev\ndate: 2026-11-23\n")
        e["reviewer_ref"], e["reviewer_record_sha256"] = rref, rh
        self.reject([e], "requires conditions_status: DISCHARGED", review=False, tamper=lambda line: line["reviews"].update({rref: rh}))

    def test_review_reject_verdict(self):
        e = entry_from_draft(DHARAMVIR, 1)
        pairs = f"{e['entry_id']}={e['sha256']}:{L.entry_digest(e)}"
        rref, rh = self.t.write_record("R-v0001.md", f"review_id: R-v0001\nverdict: REJECT\nledger_version: 0001\nentries: {pairs}\nreviewer: rev\ndate: 2026-11-23\n")
        e["reviewer_ref"], e["reviewer_record_sha256"] = rref, rh
        self.reject([e], "does not support approval", review=False, tamper=lambda line: line["reviews"].update({rref: rh}))

    def test_decided_by_and_date_required(self):  # M04
        self.reject([entry_from_draft(DHARAMVIR, 1)], "lacks decided_by", decided_by="?")

    def test_same_person_cannot_decide_and_review(self):  # F-04
        self.reject([entry_from_draft(DHARAMVIR, 1)], "different persons", decided_by="Same Person", reviewer="same person")

    def test_one_file_cannot_be_both_records(self):  # F-04 A1
        e = entry_from_draft(DHARAMVIR, 1)
        pairs = f"{e['entry_id']}={e['sha256']}:{L.entry_digest(e)}"
        ref, h = self.t.write_record("D-v0001.md", f"decision_id: D-v0001\ndecision: APPROVED\nverdict: ACCEPT\nledger_version: 0001\nentries: {pairs}\n"
                                                    "decided_by: me\nreviewer: you\ndate: 2026-11-23\n")
        e.update(decision_record_ref=ref, decision_record_sha256=h, reviewer_ref=ref, reviewer_record_sha256=h)
        self.reject([e], "both a decision record and a review record", decision=False, review=False,
                    tamper=lambda line: (line["decisions"].update({ref: h}), line["reviews"].update({ref: h})))

    def test_duplicate_keys_in_record_rejected(self):  # F-04 A6
        e = entry_from_draft(DHARAMVIR, 1)
        pairs = f"{e['entry_id']}={e['sha256']}:{L.entry_digest(e)}"
        ref, h = self.t.write_record("D-v0001.md", f"decision_id: D-v0001\ndecision: APPROVED\nledger_version: 0001\nentries: {pairs}\n"
                                                    "decided_by: owner\ndate: 2026-11-23\ndecision: REJECTED\n")
        e["decision_record_ref"], e["decision_record_sha256"] = ref, h
        self.reject([e], "appears more than once", decision=False, tamper=lambda line: line["decisions"].update({ref: h}))

    def test_non_approved_entry_needs_decision_record(self):  # F-04 A10
        self.reject([entry_from_draft(DHARAMVIR, 1, owner_decision="REJECTED")], "missing decision record", decision=False)

    def test_identity_evidence_required(self):  # M08
        self.reject([entry_from_draft(DHARAMVIR, 1, identity_refs="I:SOURCE-LIBRARY-C5/inputs/page_image_checks_c5.csv#C5-PIC-01")], "no valid identity evidence")

    def test_text_identity_only_for_court_copies(self):  # M42
        g = entry_from_draft(GAZETTE_1962, 1)
        g["identity_refs"] = f"T:AUTH-LEDGER/evidence/copy_facts.csv#{g['copy_id']}"
        self.reject([g], "no valid identity evidence")

    def test_court_primary_needs_issuing_carrier(self):  # M05
        self.reject([entry_from_draft(RAJBIR_BOSIR, 1, proposed_class="PRIMARY_OFFICIAL_COURT_COPY")], "does not fit copy carrier UNKNOWN")

    def test_incomplete_copy_never_primary(self):  # F-01
        er = sha_of("29f6fa2c", DRAFT)
        self.reject([entry_from_draft(er, 1, proposed_class="PRIMARY_GAZETTE_GOVERNMENT_HOSTED_SCAN")], "does not fit publication type REGULATION")
        t2 = Synthetic()
        try:  # the archival class is refused too (its desw.gov.in locator does not suit an archival facsimile)
            t2.add_version([entry_from_draft(er, 1, proposed_class="PRIMARY_GAZETTE_ARCHIVAL_FACSIMILE")])
            with self.assertRaisesRegex(common.LedgerError, "does not suit class PRIMARY_GAZETTE_ARCHIVAL_FACSIMILE"):
                t2.state()
        finally:
            t2.close()
        rec = {r["source_id"]: r for r in common.read_csv(AW / "SOURCE-LIBRARY-C5/registers/source_master_register.csv")}
        g = entry_from_draft(GAZETTE_1962, 1)
        fake = dict(rec[g["source_id"]], completeness_status="INCOMPLETE: test")
        held = reader._held_index()
        ctx = L.Context(held, {}, {r["sha256"]: r for r in common.read_csv(AW / "SOURCE-LIBRARY-C5/registers/source_copy_register.csv")},
                        dict(rec, **{g["source_id"]: fake}))
        with self.assertRaisesRegex(common.LedgerError, "incomplete or extract"):
            L._evidence_checks(g, ctx, g["proposed_class"])

    def test_secondary_authenticity_and_host_not_first_class(self):  # F-02
        with self.assertRaisesRegex(common.LedgerError, "authenticity 'SECONDARY'"):
            strength.first_class("PILOT-01/sources/judgment-auditor.json#S-JUD-008", ISAAC)
        self.assertFalse(strength.host_ok("https://www.livelaw.in/x", "PRIMARY_OFFICIAL_COURT_COPY"))
        self.assertTrue(strength.host_ok("https://api.sci.gov.in/x.pdf", "PRIMARY_OFFICIAL_COURT_COPY"))
        self.assertFalse(strength.host_ok("https://evilsci.gov.in.example.com/x", "PRIMARY_OFFICIAL_COURT_COPY"))
        held = reader._held_index()
        self.assertEqual(R.copy_status(ISAAC, held[ISAAC], {"authentication_state": "PROVENANCE_DOCUMENTED", "effective_source_class": "NON_PRIMARY_OFFICIAL_COURT_RENDITION",
                                                            "provenance_references": "x", "held_paths": "; ".join(held[ISAAC])})[0], R.PENDING)

    def test_csv_record_own_sha(self):  # M20
        with self.assertRaisesRegex(common.LedgerError, "own sha256 is not the entry key"):
            strength.first_class("PILOT-01/registers/source_code_resolution_v3.csv#SRC-RANJIT", DHARAMVIR)

    def test_archive_match_must_be_complete(self):  # M22
        key = "ACQ-02/supplement_inventory.csv"
        strength._rows(key)
        orig = strength._cache[key]
        strength._cache[key] = [dict(r, archive_sha1_ok="False") if r["supp_id"] == "ACQ02-02" else r for r in orig]
        try:
            with self.assertRaisesRegex(common.LedgerError, "not all OK"):
                strength.first_class("ACQ-02/supplement_inventory.csv#ACQ02-02", GAZETTE_1962)
        finally:
            strength._cache[key] = orig

    def test_exactly_one_record(self):  # M40, M25
        key = "ACQ-02/supplement_inventory.csv"
        strength._rows(key)
        orig = strength._cache[key]
        strength._cache[key] = orig + [r for r in orig if r["supp_id"] == "ACQ02-02"]
        try:
            with self.assertRaisesRegex(common.LedgerError, "resolves to 2 records"):
                strength.resolve("ACQ-02/supplement_inventory.csv#ACQ02-02")
        finally:
            strength._cache[key] = orig
        with self.assertRaisesRegex(common.LedgerError, "resolves to 0 records"):
            strength.resolve("ACQ-02/supplement_inventory.csv#ACQ02-99")

    def test_per_type_schema_rules(self):  # M33, M34
        self.reject([entry_from_draft(DHARAMVIR, 1, withdrawal_reason="OTHER")], "withdrawal_reason must be empty for ADD")
        t2 = Synthetic()
        try:
            t2.add_version([entry_from_draft(DHARAMVIR, 1)])
            t2.add_version([withdraw(DHARAMVIR, 1, 2, "AL-v0001-001", reason="")])
            with self.assertRaisesRegex(common.LedgerError, "withdrawal_reason must be set for WITHDRAW"):
                t2.state()
        finally:
            t2.close()

    def test_chain_prev_and_canonical_form(self):  # M27, M28
        self.t.add_version([entry_from_draft(DHARAMVIR, 1)], tamper=lambda line: line.update(prev="0" * 64))
        with self.assertRaisesRegex(common.LedgerError, "hash chain broken"):
            L.read_manifest(self.t.dir)
        t2 = Synthetic()
        try:
            m = t2.dir / "ledger/manifest.jsonl"
            s = m.read_text().split("\n")[0]
            spaced = json.dumps(json.loads(s))
            m.write_text(spaced + "\n")
            (t2.dir / "ledger/HEAD").write_text(f"0 {common.sha256_text(spaced)}\n")
            with self.assertRaisesRegex(common.LedgerError, "not in canonical form"):
                L.read_manifest(t2.dir)
        finally:
            t2.close()

    def test_frozen_data_pin_checked_before_frozen_code_runs(self):  # M14
        pj = json.loads((self.t.dir / "frozen_inputs.json").read_text())
        pj["files"]["legal_knowledge/audit_work/WS-D-QUALITY/canonical_coverage.csv"] = "1" * 64
        (self.t.dir / "frozen_inputs.json").write_text(json.dumps(pj))
        m = self.t.dir / "ledger/manifest.jsonl"  # re-derive a consistent genesis so only the data pin itself is wrong
        g = json.loads(m.read_text().split("\n")[0])
        g["frozen_inputs_sha256"] = common.sha256_file(self.t.dir / "frozen_inputs.json")
        s = L.canonical_line(g)
        m.write_text(s + "\n")
        (self.t.dir / "ledger/HEAD").write_text(f"0 {common.sha256_text(s)}\n")
        with self.assertRaisesRegex(common.LedgerError, "frozen inputs: hash mismatch"):
            reader.frozen_builder(self.t.dir)

    def test_frozen_code_executed_from_pinned_bytes_not_imported(self):  # F-05
        src = (PKG / "tools/reader.py").read_text(encoding="utf-8")
        self.assertNotIn("import build_registers", src)
        decoy = Path(tempfile.mkdtemp())
        (decoy / "build_registers.py").write_text("raise RuntimeError('decoy imported')\n")
        (decoy / "evidence_classification.py").write_text("raise RuntimeError('decoy imported')\n")
        sys.path.insert(0, str(decoy))
        try:
            texts, _ = reader.effective_state(PKG, 0)
        finally:
            sys.path.remove(str(decoy))
            shutil.rmtree(decoy)
        self.assertEqual(texts["corpus_crosswalk.csv"], (AW / "SOURCE-LIBRARY-C5/registers/corpus_crosswalk.csv").read_text(encoding="utf-8"))

    def test_extra_columns_rejected(self):  # F-08
        e = entry_from_draft(DHARAMVIR, 1)
        self.t.add_version([e])
        f = self.t.dir / "ledger/v0001.csv"
        txt = f.read_text().split("\n")
        txt[0] += ",legal_status"
        txt[1] += ",IN_FORCE"
        f.write_text("\n".join(txt))
        m = self.t.dir / "ledger/manifest.jsonl"
        line = json.loads(m.read_text().split("\n")[1])
        line["file_sha256"] = common.sha256_file(f)
        s0, s1 = m.read_text().split("\n")[0], L.canonical_line(line)
        m.write_text(s0 + "\n" + s1 + "\n")
        (self.t.dir / "ledger/HEAD").write_text(f"1 {common.sha256_text(s1)}\n")
        with self.assertRaisesRegex(common.LedgerError, "header must equal the schema columns"):
            self.t.state()

    def test_withdraw_of_correction_and_resulting_state_and_association(self):  # F-09
        self.t.add_version([entry_from_draft(DHARAMVIR, 1)])
        self.t.add_version([entry_from_draft(DHARAMVIR, 1, version=2, entry_type="CORRECTION", target_entry_id="AL-v0001-001",
                                             proposed_class="NON_PRIMARY_OFFICIAL_COURT_RENDITION", justification="c")])
        self.reject([withdraw(DHARAMVIR, 1, 3, "AL-v0002-001")], "may target only an ADD or a BASELINE")
        t2 = Synthetic()
        try:
            held = reader._held_index()
            cop = {r["sha256"]: r for r in rows(v0()["source_copy_register.csv"])}[ISAAC]
            w = {k: "" for k in L.COLS}
            w.update(entry_id="AL-v0001-001", entry_version="0001", entry_type="WITHDRAW", sha256=ISAAC, source_id=cop["source_id"], copy_id=cop["copy_id"],
                     document_identity="Isaac", target_entry_id="BASELINE:" + ISAAC, withdrawal_reason="OTHER", resulting_state="PROVENANCE_UNKNOWN",
                     justification="test", rule_version="1", owner_decision="APPROVED")
            t2.add_version([w])
            with self.assertRaisesRegex(common.LedgerError, "derived copy status is AUTHENTICATION_PENDING"):
                t2.state()
            self.assertTrue(held[ISAAC])
        finally:
            t2.close()
        t3 = Synthetic()
        try:
            t3.add_version([entry_from_draft(DHARAMVIR, 1)])
            t3.add_version([withdraw(DHARAMVIR, 1, 2, "AL-v0001-001") | {"copy_id": "NOT-A-COPY"}])
            with self.assertRaisesRegex(common.LedgerError, "is not the Cycle 5 copy"):
                t3.state()
        finally:
            t3.close()

    def test_evidence_refs_bound_to_this_copy(self):  # F-10
        d = entry_from_draft(DHARAMVIR, 1)
        self.reject([dict(d, evidence_refs=d["evidence_refs"] + "; OFFICIALGAZETTE:ACQ-02/supplement_inventory.csv#ACQ02-02")], "not KIND:path#key")
        for over, why in ((dict(evidence_refs=d["evidence_refs"] + "; L2:ACQ-02/supplement_inventory.csv#ACQ02-02"), "does not concern this sha256"),
                          (dict(identity_refs="T:this/does/not/exist#nothing"), "must name this copy's row in the pinned evidence/copy_facts.csv"),
                          (dict(official_locator_recorded="https://api.sci.gov.in/other.pdf"), "must equal the first-class record's URL"),
                          (dict(carrier="ISSUING_AUTHORITY (edited)"), "carrier must equal"),
                          (dict(evidence_refs="WSB:" + [x for x in d["evidence_refs"].split("; ") if x.startswith("WSB:")][0].split(":", 1)[1]), "must also be listed")):
            t2 = Synthetic()
            try:
                t2.add_version([dict(entry_from_draft(DHARAMVIR, 1), **over)])
                with self.assertRaisesRegex(common.LedgerError, why):
                    t2.state()
            finally:
                t2.close()

    def test_paths_and_ids_confined(self):  # F-12
        self.assertRaises(common.LedgerError, L._safe_ref, "decisions/../ledger/R.md", "decisions/")
        self.reject([entry_from_draft(DHARAMVIR, 1, entry_id="AL-v0009-001")], "entry_id version part differs")
        t2 = Synthetic()
        try:
            t2.add_version([entry_from_draft(DHARAMVIR, 1)], tamper=lambda line: line.update(file="anything.txt"))
            with self.assertRaisesRegex(common.LedgerError, "entry file must be ledger/v0001.csv"):
                L.read_manifest(t2.dir)
        finally:
            t2.close()
        (self.t.dir / "decisions/stray.md").write_text("x")
        self.assertIn("decisions/stray.md", L.unexpected_files(self.t.dir, L.read_manifest(self.t.dir)))

    def test_cli_fails_closed_uniformly(self):  # F-13
        orig = reader.effective_state
        reader.effective_state = lambda *a, **k: (_ for _ in ()).throw(KeyError("boom"))
        argv = sys.argv
        sys.argv = ["auth_ledger.py", "build", "--out", tempfile.mkdtemp()]
        try:
            self.assertEqual(CLI.main(), 2)
        finally:
            reader.effective_state, sys.argv = orig, argv

    def test_all_32_drafts_jointly_acceptable_but_inactive(self):  # F-16: the validator is not over-strict for the drafts
        es = [entry_from_draft(s, i + 1) for i, s in enumerate(sorted(DRAFT))]
        self.t.add_version(es)
        s = self.t.state()
        a = json.loads(s["coverage_summary.json"])
        self.assertEqual((a["authentication"]["documented_primary_copies"], a["crosswalk_case_rows_by_status"]["EXACT_ANCHOR"]), (40, 13))
        self.assertEqual(json.loads(v0()["coverage_summary.json"])["authentication"]["documented_primary_copies"], 12)  # committed ledger unchanged


class ReReview(unittest.TestCase):
    """Fable re-review N-01..N-05 and the surviving mutants of its second mutation run, one assertion each."""
    def setUp(self):
        self.t = Synthetic()

    def tearDown(self):
        self.t.close()

    def reject(self, entries, why, **kw):
        self.t.add_version(entries, **kw)
        with self.assertRaisesRegex(common.LedgerError, why):
            self.t.state()

    def test_n01_recertify_after_withdrawal_with_resulting_state(self):
        self.t.add_version([entry_from_draft(DHARAMVIR, 1)])
        self.t.add_version([withdraw(DHARAMVIR, 1, 2, "AL-v0001-001", reason="CONTRADICTION", resulting="AUTHENTICATION_PENDING")])
        self.t.add_version([entry_from_draft(DHARAMVIR, 1, version=3, entry_type="CORRECTION", target_entry_id="AL-v0002-001", justification="re-verified")])
        self.assertEqual(case_status(self.t.state(), "DCLR-SC-2013-N08"), "EXACT_ANCHOR")  # R1
        self.assertEqual(case_status(self.t.state(2), "DCLR-SC-2013-N08"), "PARTIAL_MATCH")
        t2 = Synthetic()
        try:  # R2: withdrawal to PROVENANCE_UNKNOWN, then a new ADD
            t2.add_version([entry_from_draft(DHARAMVIR, 1)])
            t2.add_version([withdraw(DHARAMVIR, 1, 2, "AL-v0001-001", resulting="PROVENANCE_UNKNOWN")])
            t2.add_version([entry_from_draft(DHARAMVIR, 1, version=3)])
            self.assertEqual(case_status(t2.state(), "DCLR-SC-2013-N08"), "EXACT_ANCHOR")
        finally:
            t2.close()

    def test_n02_frozen_inputs_checked_against_manifest_before_frozen_code(self):  # also M11
        p = self.t.dir / "frozen_inputs.json"
        p.write_text(p.read_text() + "\n")  # same pins, different file hash than the genesis line recorded
        with self.assertRaisesRegex(common.LedgerError, "frozen_inputs.json changed since this version was recorded"):
            reader.frozen_builder(self.t.dir)
        before = list(sys.path)
        reader.frozen_builder()
        self.assertEqual(sys.path, before)  # sys.path restored after executing frozen code

    def test_n03_hosts(self):
        self.assertFalse(strength.host_ok("https://web.archive.org/web/2020/https://www.livelaw.in/x.pdf", "PRIMARY_GAZETTE_ARCHIVAL_FACSIMILE"))
        self.assertFalse(strength.host_ok("http://archive.org/download/x/y.pdf", "PRIMARY_GAZETTE_ARCHIVAL_FACSIMILE"))
        self.assertFalse(strength.host_ok("https://archive.org/search?q=x", "PRIMARY_GAZETTE_ARCHIVAL_FACSIMILE"))
        self.assertTrue(strength.host_ok("https://archive.org/download/x/y.pdf", "PRIMARY_GAZETTE_ARCHIVAL_FACSIMILE"))
        self.assertFalse(strength.host_ok("https://user@api.sci.gov.in/x", "PRIMARY_OFFICIAL_COURT_COPY"))
        # confirmation C-01: userinfo on any host, and dot segments, never pass
        self.assertFalse(strength.host_ok("https://x.gov.in@evil.example/x", "PRIMARY_GAZETTE_GOVERNMENT_HOSTED_SCAN"))
        self.assertFalse(strength.host_ok("https://api.sci.gov.in:pw@evil.example/x", "PRIMARY_OFFICIAL_COURT_COPY"))
        self.assertFalse(strength.host_ok("https://archive.org/download/../web/x", "PRIMARY_GAZETTE_ARCHIVAL_FACSIMILE"))
        self.assertTrue(strength.host_ok("https://api.sci.gov.in:443/x.pdf", "PRIMARY_OFFICIAL_COURT_COPY"))
        self.assertTrue(strength.host_ok("https://indiacode.gov.in/server/api/core/bitstreams/x/content", "PRIMARY_GAZETTE_GOVERNMENT_HOSTED_SCAN"))

    def test_n04_record_parsing(self):
        self.reject([entry_from_draft(DHARAMVIR, 1)], "different persons", decided_by="A. Owner", reviewer="A Owner")
        e = entry_from_draft(DHARAMVIR, 1)
        pairs = f"{e['entry_id']}={e['sha256']}:{L.entry_digest(e)}"
        t2 = Synthetic()
        try:
            ref, h = t2.write_record("D-v0001.md", f"decision_id: D-v0001\ndecision: APPROVED\nledger_version: 0001\nentries: {pairs}\n"
                                                    "decided_by: owner\ndate: 2026-11-23\n   Decision: REJECTED\n")
            e["decision_record_ref"], e["decision_record_sha256"] = ref, h
            t2.add_version([e], decision=False, tamper=lambda line: line["decisions"].update({ref: h}))
            with self.assertRaisesRegex(common.LedgerError, "appears more than once"):
                t2.state()
        finally:
            t2.close()

    def test_m04b_reviewer_and_m04c_date(self):
        self.reject([entry_from_draft(DHARAMVIR, 1)], "review record lacks reviewer", reviewer="?")
        e = entry_from_draft(DHARAMVIR, 1)
        pairs = f"{e['entry_id']}={e['sha256']}:{L.entry_digest(e)}"
        t2 = Synthetic()
        try:
            ref, h = t2.write_record("D-v0001.md", f"decision_id: D-v0001\ndecision: APPROVED\nledger_version: 0001\nentries: {pairs}\n"
                                                    "decided_by: owner\ndate: 9999-99-99\n")
            e["decision_record_ref"], e["decision_record_sha256"] = ref, h
            t2.add_version([e], decision=False, tamper=lambda line: line["decisions"].update({ref: h}))
            with self.assertRaisesRegex(common.LedgerError, "valid YYYY-MM-DD date"):
                t2.state()
        finally:
            t2.close()

    def test_m14b_per_module_pin_and_n67_not_imported(self):
        pinmap = json.loads((PKG / "frozen_inputs.json").read_text())["files"]
        bad = dict(pinmap, **{"legal_knowledge/audit_work/" + reader.FROZEN_CODE["build_registers"]: "2" * 64})
        with self.assertRaisesRegex(common.LedgerError, "does not match its pin"):
            reader._exec_pinned("build_registers", reader.FROZEN_CODE["build_registers"], bad)
        B = reader.frozen_builder()
        self.assertIsNone(B.__spec__)  # executed from bytes, not loaded by the import system
        self.assertFalse(getattr(B, "__cached__", None))

    def test_m17_entry_version_must_match_file(self):
        self.reject([entry_from_draft(DHARAMVIR, 1, version=2)], "entry_version 0002 in version file 1")

    def test_m19_partial_c6_check_is_not_identity(self):
        dhc = [r["sha256"] for r in common.read_csv(AW / "C6-01-PROVENANCE/registers/provenance_recovery_register.csv") if "DHC-RULES" in r["source_id"]][0]
        with self.assertRaisesRegex(common.LedgerError, "identity_result PARTIAL"):
            strength.identity_ok(["I:C6-01-PROVENANCE/inputs/page_image_checks_c6.csv#C6-PIC-03"], dhc, False, "x", "")

    def test_m23_add_records_documented_only(self):
        self.reject([entry_from_draft(DHARAMVIR, 1, proposed_authentication_state="AUTHENTICATION_PENDING")], "records documented provenance only")

    def test_m25c_snapshot_must_match_copy(self):
        d = entry_from_draft(GAZETTE_1962, 1)
        snap = "L2:ACQ-01/archive_org_metadata_snapshot.json#in.gazette.central.e.2022-06-06.236353/236353.pdf"
        self.reject([dict(d, evidence_refs=d["evidence_refs"] + "; " + snap)], "does not match this copy's md5 and size")

    def test_m31_correction_target_must_be_this_sha(self):
        self.t.add_version([entry_from_draft(DHARAMVIR, 1), entry_from_draft(GAZETTE_1962, 2)])
        self.reject([entry_from_draft(DHARAMVIR, 1, version=2, entry_type="CORRECTION", target_entry_id="AL-v0001-002", justification="x")], "not the live row")

    def test_m35_retrieval_record_needs_url(self):
        ref = DRAFT[DHARAMVIR]["first_class_record_ref"]
        path = ref.split("#")[0]
        strength._rows(path)
        orig = strength._cache[path]
        strength._cache[path] = [dict(o, locator="no url here") if o.get("source_id") == ref.split("#")[1] else o for o in orig]
        try:
            with self.assertRaisesRegex(common.LedgerError, "no URL locator"):
                strength.first_class(ref, DHARAMVIR)
        finally:
            strength._cache[path] = orig

    def test_m36_pending_correction_class(self):
        self.t.add_version([entry_from_draft(DHARAMVIR, 1)])
        self.reject([entry_from_draft(DHARAMVIR, 1, version=2, entry_type="CORRECTION", target_entry_id="AL-v0001-001",
                                      proposed_authentication_state="AUTHENTICATION_PENDING", justification="x")], "must carry class AUTHENTICATION_PENDING")

    def test_m38_pin_set_must_match_declared_list(self):
        pj = json.loads((self.t.dir / "frozen_inputs.json").read_text())
        pj["files"]["legal_knowledge/audit_work/C6-PREP/README.md"] = common.sha256_file(AW / "C6-PREP/README.md")
        (self.t.dir / "frozen_inputs.json").write_text(json.dumps(pj))
        with self.assertRaisesRegex(common.LedgerError, "pin set differs"):
            pins.verify(self.t.dir)

    def test_m43_held_index_required(self):
        e = entry_from_draft(DHARAMVIR, 1)
        ctx = L.Context({}, {}, {r["sha256"]: r for r in common.read_csv(AW / "SOURCE-LIBRARY-C5/registers/source_copy_register.csv")}, {})
        with self.assertRaisesRegex(common.LedgerError, "not in the held-source index"):
            L._association(e, ctx)

    def test_n56_record_file_name_and_n58_safe_ref(self):
        e = entry_from_draft(DHARAMVIR, 1)
        pairs = f"{e['entry_id']}={e['sha256']}:{L.entry_digest(e)}"
        ref, h = self.t.write_record("X.md", f"decision_id: X\ndecision: APPROVED\nledger_version: 0001\nentries: {pairs}\ndecided_by: o\ndate: 2026-11-23\n")
        e["decision_record_ref"], e["decision_record_sha256"] = ref, h
        self.reject([e], "must be decisions/D-v0001", decision=False, tamper=lambda line: line["decisions"].update({ref: h}))
        with self.assertRaisesRegex(common.LedgerError, "normalised path"):
            L._check_record(self.t.dir, {"decisions": {}, "reviews": {}}, "decision", "decisions/./D-v0001.md", "", entry_from_draft(DHARAMVIR, 1))

    def test_n63_build_refuses_output_differing_from_manifest(self):
        orig = reader.effective_state
        def altered(*a, **k):
            texts, lines = orig(*a, **k)
            return dict(texts, **{"corpus_crosswalk.csv": texts["corpus_crosswalk.csv"] + "x\n"}), lines
        reader.effective_state = altered
        argv = sys.argv
        sys.argv = ["auth_ledger.py", "build", "--as-of", "0", "--out", tempfile.mkdtemp()]
        try:
            self.assertEqual(CLI.main(), 2)
        finally:
            reader.effective_state, sys.argv = orig, argv

    def test_n64_verify_reports_unexpected_files(self):
        shutil.copytree(PKG / "effective", self.t.dir / "effective")
        self.assertEqual(CLI.verify(self.t.dir), ["v0000 ok"])
        (self.t.dir / "decisions/stray.md").write_text("x")
        with self.assertRaisesRegex(common.LedgerError, "not accounted for"):
            CLI.verify(self.t.dir)

    def test_n05_header_kind_and_t_reference(self):
        f = self.t.dir / "ledger/v0001.csv"
        f.write_text("legal_status,in_force\n")
        prev = common.sha256_text((self.t.dir / "ledger/manifest.jsonl").read_text().split("\n")[0])
        line = {"version": 1, "prev": prev, "date": "2026-11-23", "rule_version": 1, "frozen_inputs_sha256": common.sha256_file(self.t.dir / "frozen_inputs.json"),
                "file": "ledger/v0001.csv", "file_sha256": common.sha256_file(f), "decisions": {}, "reviews": {}, "effective_sha256": "", "note": "x"}
        s = L.canonical_line(line)
        with open(self.t.dir / "ledger/manifest.jsonl", "a") as fh:
            fh.write(s + "\n")
        (self.t.dir / "ledger/HEAD").write_text(f"1 {common.sha256_text(s)}\n")
        with self.assertRaisesRegex(common.LedgerError, "header must equal the schema columns"):
            self.t.state()
        t2 = Synthetic()
        try:
            d = entry_from_draft(DHARAMVIR, 1)
            wsb = [x for x in d["evidence_refs"].split("; ") if x.startswith("WSB:")][0]
            t2.add_version([dict(d, evidence_refs=d["evidence_refs"].replace(wsb, "L6:" + wsb.split(":", 1)[1]))])
            with self.assertRaisesRegex(common.LedgerError, "does not belong to file"):
                t2.state()
        finally:
            t2.close()
        t3 = Synthetic()
        try:
            d = entry_from_draft(DHARAMVIR, 1)
            t3.add_version([dict(d, identity_refs=d["identity_refs"].replace("T:AUTH-LEDGER/evidence/copy_facts.csv#", "T:C6-01-PROVENANCE/inputs/held_copy_facts.csv#"))])
            with self.assertRaisesRegex(common.LedgerError, "pinned evidence/copy_facts.csv"):
                t3.state()
        finally:
            t3.close()


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
        self.assertEqual(len(json.loads(s["newly_withdrawn.json"])), 1)
        self.assertEqual(len(json.loads(s["transitions.json"])), 2)  # the record stays

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
        with self.assertRaisesRegex(common.LedgerError, "may target only an ADD or a BASELINE"):
            self.t.state()

    def test_loss_of_only_primary_copy_of_baseline_source(self):
        base = next(r for r in common.read_csv(AW / "CALIBRATION-02/registers/source_authentication_register.csv")
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
