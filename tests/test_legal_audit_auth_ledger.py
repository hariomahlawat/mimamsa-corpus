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
                                                 f"decided_by: {decided_by}\ndate: 2026-11-23\nscope: AUTHENTICATION_PROVENANCE_ONLY\nlegal_approval: NOT_GIVEN\n")
                decisions[ref] = h
                for e in group:
                    if not e.get("decision_record_ref"):
                        e["decision_record_ref"], e["decision_record_sha256"] = ref, h
        approved = by_decision.get("APPROVED", [])
        if approved and review:
            pairs = ";".join(f"{e['entry_id']}={e['sha256']}:{L.entry_digest(e)}" for e in approved)
            ref, h = self.write_record(f"R-v{v:04d}.md", f"review_id: R-v{v:04d}\nverdict: ACCEPT\nledger_version: {v:04d}\nentries: {pairs}\n"
                                                           f"reviewer: {reviewer}\ndate: 2026-11-23\nscope: TECHNICAL_AND_EVIDENCE_REVIEW\nlegal_approval: NOT_GIVEN\n{review_extra}")
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

    def state(self, as_of=None, require_binding=False):
        """Evidence-rule tests use the AUTH-LEDGER-01 activation semantics (no BIND line); Binding tests pass True."""
        texts, _ = reader.effective_state(self.dir, as_of, require_binding)
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
        rref, rh = self.t.write_record("R-v0001.md", f"review_id: R-v0001\nverdict: ACCEPT_WITH_CONDITIONS\nledger_version: 0001\nentries: {pairs}\nreviewer: rev\ndate: 2026-11-23\n"
                                                       "scope: TECHNICAL_AND_EVIDENCE_REVIEW\nlegal_approval: NOT_GIVEN\n")
        e["reviewer_ref"], e["reviewer_record_sha256"] = rref, rh
        self.reject([e], "requires conditions_status: DISCHARGED", review=False, tamper=lambda line: line["reviews"].update({rref: rh}))

    def test_review_reject_verdict(self):
        e = entry_from_draft(DHARAMVIR, 1)
        pairs = f"{e['entry_id']}={e['sha256']}:{L.entry_digest(e)}"
        rref, rh = self.t.write_record("R-v0001.md", f"review_id: R-v0001\nverdict: REJECT\nledger_version: 0001\nentries: {pairs}\nreviewer: rev\ndate: 2026-11-23\n"
                                                       "scope: TECHNICAL_AND_EVIDENCE_REVIEW\nlegal_approval: NOT_GIVEN\n")
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
        self.assertTrue(strength.host_ok("https://api.sci.gov.in/jonew/judis/1.pdf", "PRIMARY_OFFICIAL_COURT_COPY"))
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
        # AUTH-LEDGER-02 (D-01 hardening): an explicit ':443' is now rejected as a second spelling of the URL
        self.assertFalse(strength.host_ok("https://api.sci.gov.in:443/x.pdf", "PRIMARY_OFFICIAL_COURT_COPY"))
        self.assertTrue(strength.host_ok("https://api.sci.gov.in/jonew/judis/1.pdf", "PRIMARY_OFFICIAL_COURT_COPY"))
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
        # urllib.parse (pure RFC 3986 string parsing, used by urlcheck.py for D-01) is the only urllib module allowed;
        # every other urllib import, and any network or AI client, fails this test.
        import re as _re
        bad = ("requests", "http.client", "httpx", "socket", "anthropic", "openai", "transformers", "urllib3", "ftplib", "smtplib")
        for f in (PKG / "tools").glob("*.py"):
            src = f.read_text(encoding="utf-8")
            for b in bad:
                self.assertNotIn(f"import {b}", src, f.name)
                self.assertNotIn(f"from {b}", src, f.name)
            for m in _re.finditer(r"(?m)^\s*(?:import|from)\s+(urllib\S*)", src):
                self.assertEqual(m.group(1), "urllib.parse", f.name)
            if "subprocess" in src:  # only binding.py runs a subprocess: local git with every transport protocol disabled
                self.assertEqual(f.name, "binding.py")
                self.assertIn('"protocol.allow=never"', src)
                self.assertIn('GIT_NO_LAZY_FETCH="1"', src)

    def test_historical_files_unchanged_after_runs(self):
        reader.effective_state(PKG, 0)
        self.assertGreater(pins.verify(), 70)
        out = subprocess.run(["git", "-C", str(REPO), "status", "--porcelain", "--", "legal_knowledge/audit_work/CALIBRATION-02",
                              "legal_knowledge/audit_work/SOURCE-LIBRARY-C5", "legal_knowledge/curated_originals"], capture_output=True, text=True)
        self.assertEqual(out.stdout.strip(), "")


if __name__ == "__main__":
    unittest.main()


# ---------------------------------------------------------------------------------------------------------------------
# AUTH-LEDGER-02: URL validation hardening (Fable D-01), repository binding of approvals, approval-record integrity.
# ---------------------------------------------------------------------------------------------------------------------
import urlcheck  # noqa: E402
import binding  # noqa: E402
from unittest import mock  # noqa: E402

GAZ = "PRIMARY_GAZETTE_ARCHIVAL_FACSIMILE"
COURT = "PRIMARY_OFFICIAL_COURT_COPY"
GOVPUB = "NON_PRIMARY_OFFICIAL_PUBLICATION_COPY"
ALL_CLASSES = sorted(strength.CLASS_HOSTS)
D01 = "https://archive.org/download/example/%2e%2e/other"
HOSTILE = [
    D01, "https://archive.org/download/example/%2E%2E/other", "https://archive.org/download/x/%2e/y", "https://archive.org/download/x/.%2e/y",
    "https://archive.org/download/x/..%2Fy.pdf", "https://archive.org/download/x/%2F..%2Fy.pdf", "https://archive.org/download/x%5C..%5Cy.pdf",
    "https://archive.org/download/x/%252e%252e/y.pdf", "https://archive.org/download/x/%25252e/y.pdf", "https://archive.org/download/x/%zz.pdf",
    "https://archive.org/download/x/%2.pdf", "https://archive.org/download/x/y.pdf%", "https://archive.org/download/x/%00.pdf",
    "https://archive.org/download/x/y%0A.pdf", "https://archive.org/download/x/y%7F.pdf", "https://archive.org/download/x/y%3B.pdf",
    "https://archive.org/download/x/../../etc/y.pdf", "https://archive.org/download/x/./y.pdf", "https://archive.org/download//x/y.pdf",
    "https://archive.org/download/x/..;/y.pdf", "https://archive.org/download/x/y.pdf;jsessionid=1", "https://archive.org/download/x\\..\\y.pdf",
    "https://archive.org/download/x/y .pdf", "https://archive.org/download/x/é.pdf", "https://archive.org/download/x/y.pdf\n",
    "https://archive.org/download/x/y.pdf#frag", "https://archive.org/download/x/y.pdf?", "https://archive.org/download/%78/y.pdf",
    "https://archive.org/download/x/%c3%a9.pdf", "https://archive.org:443/download/x/y.pdf", "https://archive.org:/download/x/y.pdf",
    "https://archive.org:0443/download/x/y.pdf", "https://archive.org:8443/download/x/y.pdf", "https://user@archive.org/download/x/y.pdf",
    "https://archive.org@evil.example/download/x/y.pdf", "https://archive.org:pw@evil.example/download/x/y.pdf", "https://ARCHIVE.org/download/x/y.pdf",
    "HTTPS://archive.org/download/x/y.pdf", "http://archive.org/download/x/y.pdf", "https:/archive.org/download/x/y.pdf", "//archive.org/download/x/y.pdf",
    "https:///download/x/y.pdf", "https://archive.org./download/x/y.pdf", "https://archive..org/download/x/y.pdf", "https://[::1]/download/x/y.pdf",
    "https://127.0.0.1/download/x/y.pdf", "https://arch_ive.org/download/x/y.pdf", "https://web.archive.org/web/2020/https://sci.gov.in/x.pdf",
    "https://archive.org/download/", "https://archive.org/download/x", "https://archive.org/download/x/", "https://archive.org/details/x/",
    "https://archive.org/details/x/page/2", "https://archive.org/search?query=x", "https://archive.org/download/.x/y.pdf",
    "https://sci.gov.in.evil.example/x.pdf", "https://evilsci.gov.in.example/x.pdf", "https://api.sci.gov.in/", "https://api.sci.gov.in",
    "https://api.sci.gov.in/jonew/judis/%38566.pdf", "https://api.sci.gov.in/jonew//judis/8566.pdf", "https://desw.gov.in/sites//a.pdf", "https://api.sci.gov.in/jonew/judis/8566.pdf?#", "javascript:alert(1)", "", None, 42,
    "https://archive.org/download/x/" + "a" * 2100,
    # AUTH-LEDGER-02 review fixes (Fable F-03, F-06, F-07, F-15; F-11 survivors)
    "https://gov.in/x.pdf", "https://nic.in/x.pdf", "https://desw.gov.in/sites/", "https://archive.org/download/x/y.pdf?a=1",
    "https://archive.org/details/x?view=theater", "https://archive.org/download/x/%EF%BC%8E%EF%BC%8E/y.pdf", "https://archive.org/download/x/%EF%BC%8F.pdf",
    "https://archive.org/download/x/..%20/y.pdf", "https://archive.org/download/x/a%E2%80%AEb.pdf", "https://archive.org/download/x/a%C2%85b.pdf",
    "https://archive.org/download/x/a%FFb.pdf", "https://desw.gov.in/a.pdf?q=%FF", "https://1.0x7f/x.pdf", "https://x.gov.in.1/x.pdf",
    "https://-api.sci.gov.in/x.pdf", "https://api_x.sci.gov.in/x.pdf", "https://api.sci.gov.in/x%3F.pdf", "https://api.sci.gov.in/x%23.pdf",
]
LEGIT = [
    ("https://archive.org/download/in.gazette.central.w.1962-01-06.85365/85365.pdf", GAZ),
    ("https://archive.org/details/in.gazette.central.w.1963-01-19.84713", GAZ),
    ("https://archive.org/download/in.gazette.central.e.2018-02-20.183010/183010.pdf", GAZ),
    ("https://api.sci.gov.in/jonew/judis/8566.pdf", COURT),
    ("https://api.sci.gov.in/supremecourt/2017/27850/27850_2017_9_1502_17253_Judgement_03-Oct-2019.pdf", COURT),
    ("https://indiacode.gov.in/server/api/core/bitstreams/6a3e7da4-d157-4ec6-a65a-ad6700d202df/content", GOVPUB),
    ("https://desw.gov.in/sites/default/files/2026-10/Entitlement%20Rules%202023.pdf", GOVPUB),
]


class UrlSecurity(unittest.TestCase):
    def test_d01_reproduction_is_rejected(self):
        self.assertFalse(strength.host_ok(D01, GAZ))
        self.assertRegex(strength.locator_problem(D01, GAZ), r"percent-encoded unreserved character %2e")

    def test_every_hostile_locator_is_rejected_for_every_class(self):
        for u in HOSTILE:
            for cls in ALL_CLASSES:
                self.assertFalse(strength.host_ok(u, cls), (u, cls))
                self.assertNotEqual(strength.locator_problem(u, cls), "", (u, cls))

    def test_known_legitimate_locators_pass_for_their_class(self):
        for u, cls in LEGIT:
            self.assertEqual(strength.locator_problem(u, cls), "", u)

    def test_class_host_restrictions_still_apply(self):
        self.assertFalse(strength.host_ok("https://api.sci.gov.in/jonew/judis/8566.pdf", GAZ))
        self.assertFalse(strength.host_ok("https://archive.org/download/x/y.pdf", COURT))
        self.assertFalse(strength.host_ok("https://indiacode.gov.in/x.pdf", COURT))
        self.assertFalse(strength.host_ok("https://archive.org/download/x/y.pdf", "UNKNOWN_CLASS"))

    def test_all_committed_locators_and_all_32_draft_locators_still_pass(self):
        urls = {u for u, _ in strength.url_pairs()}
        self.assertEqual(len(urls), 74)
        self.assertEqual([u for u in urls if urlcheck.problem(u)], [])
        for d in DRAFT.values():
            url = strength._first_class(d["first_class_record_ref"], d["sha256"])[2]
            self.assertEqual(strength.locator_problem(url, d["proposed_class"]), "", url)

    def test_no_url_is_normalised_or_repaired(self):
        for u in ("https://archive.org/download/x/y.pdf", "https://desw.gov.in/a%20b.pdf"):
            host, segs, q = urlcheck.parse(u)
            self.assertEqual("https://" + host + "/" + "/".join(segs), u)  # components reproduce the input exactly

    def test_first_class_record_with_hostile_locator_is_refused(self):
        d = DRAFT[GAZETTE_1962]
        with mock.patch.object(strength, "_first_class", return_value=("RET", "FULL", D01)):
            with self.assertRaisesRegex(common.LedgerError, r"rejected for class .*%2e"):
                strength.first_class(d["first_class_record_ref"], GAZETTE_1962, GAZ)

    def test_ledger_entry_with_hostile_locator_is_rejected(self):
        t = Synthetic()
        try:
            e = entry_from_draft(GAZETTE_1962, 1, official_locator_recorded=D01)
            t.add_version([e])
            with mock.patch.object(strength, "_first_class", return_value=("RET", "FULL", D01)):
                with self.assertRaisesRegex(common.LedgerError, r"rejected for class"):
                    t.state()
        finally:
            t.close()

    def test_version_zero_is_unchanged_by_the_hardening(self):
        for k in reader.FROZEN_EQUAL:
            self.assertEqual(v0()[k], (AW / "SOURCE-LIBRARY-C5/registers" / k).read_text(encoding="utf-8"))
        self.assertEqual(L.head_value(PKG), EXPECTED_HEAD)


def _git(cwd, *a):
    p = subprocess.run(["git", "-C", str(cwd), *a], capture_output=True, text=True)
    if p.returncode != 0:
        raise AssertionError(f"git {a}: {p.stderr}")
    return p.stdout.strip()


class GitLedger(Synthetic):
    """A Synthetic ledger that is also a git repository (local only), for BIND-line tests."""
    def __init__(self):
        super().__init__()
        _git(self.dir, "init", "-q", "-b", "main")
        _git(self.dir, "config", "user.email", "test@example.invalid")
        _git(self.dir, "config", "user.name", "test")
        _git(self.dir, "config", "commit.gpgsign", "false")
        self.commit("genesis")

    def commit(self, msg):
        _git(self.dir, "add", "-A")
        _git(self.dir, "commit", "-q", "--allow-empty", "-m", msg)
        return _git(self.dir, "rev-parse", "HEAD")

    def pr(self, entries, branch="pr1", **kw):
        """Add a version on a branch, then merge it into main with an ordinary merge commit. Returns (head, merge)."""
        _git(self.dir, "checkout", "-q", "-b", branch)
        self.add_version(entries, **kw)
        head = self.commit("version")
        _git(self.dir, "checkout", "-q", "main")
        _git(self.dir, "merge", "-q", "--no-ff", "-m", "merge", branch)
        return head, _git(self.dir, "rev-parse", "HEAD")

    def add_bind(self, head, merge, **over):
        lines = L.read_manifest(self.dir)
        v = len(lines)
        b = {"binds_version": v - 1, "bound_line_sha256": common.sha256_text(L.canonical_line(lines[-1])), "repository": "owner/repo",
             "pr_number": 7, "reviewed_head": head, "merge_commit": merge, "github_review_id": 123, "github_review_login": "owner-login",
             "github_review_commit": head}
        b.update(over)
        prev = common.sha256_text((self.dir / "ledger/manifest.jsonl").read_text(encoding="utf-8").split("\n")[-2])
        line = {"version": v, "prev": prev, "date": "2026-11-23", "rule_version": 1, "frozen_inputs_sha256": common.sha256_file(self.dir / "frozen_inputs.json"),
                "file": None, "file_sha256": None, "decisions": {}, "reviews": {}, "effective_sha256": "", "note": "bind", "binding": b}
        s = L.canonical_line(line)
        with open(self.dir / "ledger/manifest.jsonl", "a", encoding="utf-8") as fh:
            fh.write(s + "\n")
        (self.dir / "ledger/HEAD").write_text(f"{v} {common.sha256_text(s)}\n", encoding="utf-8")
        return v


class Binding(unittest.TestCase):
    def setUp(self):
        self.t = GitLedger()

    def tearDown(self):
        self.t.close()

    def bound(self):
        head, merge = self.t.pr([entry_from_draft(GAZETTE_1962, 1)])
        self.t.add_bind(head, merge)
        self.t.commit("bind")
        return head, merge

    def bad(self, regex):
        with self.assertRaisesRegex(common.LedgerError, regex):
            self.t.state(require_binding=True)

    def test_unbound_approved_version_is_pending_and_changes_nothing(self):
        self.t.pr([entry_from_draft(GAZETTE_1962, 1)])
        texts = self.t.state(require_binding=True)
        for k in reader.FROZEN_EQUAL:
            self.assertEqual(texts[k], v0()[k], k)
        self.assertEqual([x["effect"] for x in json.loads(texts["transitions.json"])], ["PENDING_REPOSITORY_BINDING"])

    def test_verified_bind_line_activates_exactly_the_reviewed_version(self):
        self.bound()
        texts = self.t.state(require_binding=True)
        legacy = self.t.state(as_of=1, require_binding=False)
        for k in ("source_copy_register.csv", "source_master_register.csv", "corpus_crosswalk.csv", "coverage_summary.json"):
            self.assertEqual(texts[k], legacy[k], k)
        tr = json.loads(texts["transitions.json"])
        self.assertEqual([(x["effect"], x["bound_by"]) for x in tr], [("APPLIED", 2)])
        self.assertNotEqual(texts["source_copy_register.csv"], v0()["source_copy_register.csv"])

    def test_history_is_reproducible_before_the_bind(self):
        self.bound()
        self.assertEqual(self.t.state(as_of=1, require_binding=True)["source_copy_register.csv"], v0()["source_copy_register.csv"])

    def test_report_marks_github_review_as_asserted_not_verified(self):
        self.bound()
        lines = L.read_manifest(self.t.dir)
        rep = binding.verify(self.t.dir, lines[2], lines, L.canonical_line)
        self.assertEqual(rep["git"], "VERIFIED_OFFLINE")
        self.assertTrue(rep["github_review"].startswith("ASSERTED_NOT_VERIFIED_OFFLINE"))

    def test_wrong_reviewed_head_is_rejected(self):
        head, merge = self.t.pr([entry_from_draft(GAZETTE_1962, 1)])
        genesis = _git(self.t.dir, "rev-list", "--max-parents=0", "HEAD")
        self.t.add_bind(genesis, merge)
        self.bad("second parent .* is not reviewed_head")

    def test_review_of_an_earlier_commit_does_not_cover_later_pushes(self):
        head, merge = self.t.pr([entry_from_draft(GAZETTE_1962, 1)])
        self.t.add_bind(head, merge, github_review_commit=_git(self.t.dir, "rev-parse", f"{head}^"))
        self.bad("review must be of reviewed_head")

    def test_fast_forward_or_direct_commit_is_not_a_reviewed_merge(self):
        self.t.add_version([entry_from_draft(GAZETTE_1962, 1)])
        c = self.t.commit("direct commit to main")
        self.t.add_bind(c, c)
        self.bad("fast-forward")
        self.t.close()
        self.t = GitLedger()
        self.t.add_version([entry_from_draft(GAZETTE_1962, 1)])
        c = self.t.commit("direct")
        self.t.add_bind(c, _git(self.t.dir, "rev-parse", "HEAD^"))
        self.bad(r"has [01] parent\(s\)")

    def test_version_already_in_the_base_did_not_enter_through_the_merge(self):
        self.t.add_version([entry_from_draft(GAZETTE_1962, 1)])
        self.t.commit("direct to main")
        _git(self.t.dir, "checkout", "-q", "-b", "side")
        head = self.t.commit("empty side commit")
        _git(self.t.dir, "checkout", "-q", "main")
        _git(self.t.dir, "merge", "-q", "--no-ff", "-m", "merge", "side")
        self.t.add_bind(head, _git(self.t.dir, "rev-parse", "HEAD"))
        self.bad("did not enter through this merge")

    def test_change_between_review_and_merge_is_rejected(self):
        _git(self.t.dir, "checkout", "-q", "-b", "pr1")
        self.t.add_version([entry_from_draft(GAZETTE_1962, 1)])
        head = self.t.commit("reviewed")
        _git(self.t.dir, "checkout", "-q", "main")
        _git(self.t.dir, "merge", "-q", "--no-ff", "--no-commit", "pr1")
        (self.t.dir / "decisions/R-v0001.md").write_text("altered in the merge\n", encoding="utf-8")
        merge = self.t.commit("merge with an edit")
        self.t.add_bind(head, merge)
        self.bad("R-v0001.md (missing or modified|differs between reviewed_head and merge_commit)")

    def test_merge_content_must_equal_reviewed_content_even_if_later_restored(self):
        _git(self.t.dir, "checkout", "-q", "-b", "pr1")
        self.t.add_version([entry_from_draft(GAZETTE_1962, 1)])
        head = self.t.commit("reviewed")
        rec = self.t.dir / "decisions/R-v0001.md"
        good = rec.read_bytes()
        _git(self.t.dir, "checkout", "-q", "main")
        _git(self.t.dir, "merge", "-q", "--no-ff", "--no-commit", "pr1")
        rec.write_text("different content at the merge\n", encoding="utf-8")
        merge = self.t.commit("merge with an edit")
        rec.write_bytes(good)
        self.t.commit("restore the reviewed bytes afterwards")
        self.t.add_bind(head, merge)
        self.bad("differs between reviewed_head and merge_commit")

    def test_reviewed_head_must_end_exactly_at_the_bound_version(self):
        _git(self.t.dir, "checkout", "-q", "-b", "pr1")
        self.t.add_version([entry_from_draft(GAZETTE_1962, 1)])
        self.t.add_bind("a" * 40, "b" * 40)  # a self-binding line smuggled into the reviewed PR
        head = self.t.commit("version plus bind")
        _git(self.t.dir, "checkout", "-q", "main")
        _git(self.t.dir, "merge", "-q", "--no-ff", "-m", "merge", "pr1")
        merge = _git(self.t.dir, "rev-parse", "HEAD")
        mf = self.t.dir / "ledger/manifest.jsonl"
        mf.write_text("\n".join(mf.read_text(encoding="utf-8").split("\n")[:2]) + "\n", encoding="utf-8")
        (self.t.dir / "ledger/HEAD").write_text(f"1 {common.sha256_text(mf.read_text(encoding='utf-8').split(chr(10))[1])}\n", encoding="utf-8")
        self.t.add_bind(head, merge)
        self.bad("does not end exactly at version 1")

    def test_merge_must_be_in_the_checked_out_history(self):
        head, merge = self.t.pr([entry_from_draft(GAZETTE_1962, 1)])
        _git(self.t.dir, "checkout", "-q", "pr1")
        self.t.add_bind(head, merge)
        self.bad("not in the history of the checked-out HEAD")

    def test_unknown_commit_and_no_git_fail_closed(self):
        head, merge = self.t.pr([entry_from_draft(GAZETTE_1962, 1)])
        self.t.add_bind(head, "c" * 40)
        self.bad("not in the local history")
        shutil.rmtree(self.t.dir / ".git")
        self.bad("no git history")

    def test_shallow_clone_fails_closed(self):
        self.bound()
        d = Path(tempfile.mkdtemp(prefix="authledger_shallow_"))
        try:
            subprocess.run(["git", "clone", "-q", "--depth", "1", f"file://{self.t.dir}", str(d / "c")], check=True, capture_output=True)
            with self.assertRaisesRegex(common.LedgerError, "shallow clone"):
                reader.effective_state(d / "c", None, True)
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_entry_version_cannot_be_appended_before_the_previous_is_bound(self):
        self.t.pr([entry_from_draft(GAZETTE_1962, 1)])
        self.t.add_version([entry_from_draft(DHARAMVIR, 1, version=2)])
        self.bad("appended before version 1 was bound")

    def test_bind_line_must_bind_the_immediately_preceding_entry_version(self):
        head = _git(self.t.dir, "rev-parse", "HEAD")
        lines = L.read_manifest(self.t.dir)
        with self.assertRaisesRegex(common.LedgerError, "binds nothing pending"):
            self.t.add_bind(head, head, binds_version=1)
            self.t.state(require_binding=True)

    def test_tampered_binding_fields_are_rejected(self):
        head, merge = self.t.pr([entry_from_draft(GAZETTE_1962, 1)])
        for over, rx in (({"bound_line_sha256": "0" * 64}, "bound_line_sha256 does not match"), ({"github_review_login": "bad login"}, "not a GitHub login"),
                         ({"github_review_id": 0}, "positive integer"), ({"pr_number": True}, "positive integer"), ({"merge_commit": merge[:12]}, "40-hex"),
                         ({"repository": "no-slash"}, "owner/name")):
            t = GitLedger()
            try:
                h2, m2 = t.pr([entry_from_draft(GAZETTE_1962, 1)])
                o = {k: (m2[:12] if v == merge[:12] else v) for k, v in over.items()}
                t.add_bind(h2, m2, **o)
                with self.assertRaisesRegex(common.LedgerError, rx):
                    t.state(require_binding=True)
            finally:
                t.close()

    def test_binding_keys_are_exact(self):
        with self.assertRaisesRegex(common.LedgerError, "binding keys"):
            binding.check_shape({"binds_version": 1})

    def test_bind_line_is_refused_in_legacy_mode(self):
        self.bound()
        with self.assertRaisesRegex(common.LedgerError, "only with require_binding"):
            self.t.state(require_binding=False)

    def test_bind_line_cannot_carry_records(self):
        head, merge = self.t.pr([entry_from_draft(GAZETTE_1962, 1)])
        self.t.add_bind(head, merge)
        mf = self.t.dir / "ledger/manifest.jsonl"
        ls = mf.read_text(encoding="utf-8").split("\n")
        d = json.loads(ls[2])
        d["decisions"] = {"decisions/D-v0001.md": "0" * 64}
        ls[2] = L.canonical_line(d)
        mf.write_text("\n".join(ls), encoding="utf-8")
        (self.t.dir / "ledger/HEAD").write_text(f"2 {common.sha256_text(ls[2])}\n", encoding="utf-8")
        self.bad("BIND line carries no entry file and no records")

    def test_cli_and_committed_ledger_use_binding_mode(self):
        import inspect
        self.assertIn("require_binding=True", inspect.signature(reader.effective_state).__str__())
        self.assertNotIn("require_binding", inspect.getsource(CLI))  # the CLI never selects the legacy mode
        self.assertEqual(CLI.verify(), ["v0000 ok"])


class ApprovalIntegrity(unittest.TestCase):
    def setUp(self):
        self.t = Synthetic()

    def tearDown(self):
        self.t.close()

    def reject(self, regex):
        with self.assertRaisesRegex(common.LedgerError, regex):
            self.t.state()

    def _pairs(self, *es):
        return ";".join(f"{e['entry_id']}={e['sha256']}:{L.entry_digest(e)}" for e in es)

    def _extra_record(self, name, body):
        ref, h = self.t.write_record(name, body)
        return ref, h

    def test_orphan_pinned_record_is_rejected(self):
        ref, h = self._extra_record("D-v0001-orphan.md", "decision_id: D-v0001-orphan\n")
        self.t.add_version([entry_from_draft(GAZETTE_1962, 1)], tamper=lambda line: line["decisions"].update({ref: h}))
        self.reject("cited by no entry")

    def test_record_naming_an_entry_outside_the_version_is_rejected(self):
        e = entry_from_draft(GAZETTE_1962, 1)
        ghost = entry_from_draft(DHARAMVIR, 2)
        body = (f"decision_id: D-v0001\ndecision: APPROVED\nledger_version: 0001\nentries: {self._pairs(e, ghost)}\ndecided_by: test owner\n"
                f"date: 2026-11-23\nscope: AUTHENTICATION_PROVENANCE_ONLY\nlegal_approval: NOT_GIVEN\n")
        ref, h = self._extra_record("D-v0001.md", body)
        e["decision_record_ref"], e["decision_record_sha256"] = ref, h
        self.t.add_version([e], decision=False, tamper=lambda line: line["decisions"].update({ref: h}))
        self.reject("names AL-v0001-002, which is not an entry of this version")

    def test_entry_named_by_two_decision_records_is_rejected(self):
        e = entry_from_draft(GAZETTE_1962, 1)
        body = lambda n: (f"decision_id: {n}\ndecision: APPROVED\nledger_version: 0001\nentries: {self._pairs(e)}\ndecided_by: test owner\n"
                          f"date: 2026-11-23\nscope: AUTHENTICATION_PROVENANCE_ONLY\nlegal_approval: NOT_GIVEN\n")
        r1, h1 = self._extra_record("D-v0001.md", body("D-v0001"))
        r2, h2 = self._extra_record("D-v0001-dup.md", body("D-v0001-dup"))
        e["decision_record_ref"], e["decision_record_sha256"] = r1, h1
        self.t.add_version([e], decision=False, tamper=lambda line: line["decisions"].update({r1: h1, r2: h2}))
        self.reject("(cited by no entry|named by two decision records)")

    def test_earlier_decision_cannot_be_reused_for_a_later_version(self):
        e1 = entry_from_draft(GAZETTE_1962, 1)
        self.t.add_version([e1])
        e2 = entry_from_draft(DHARAMVIR, 1, version=2)
        e2["decision_record_ref"], e2["decision_record_sha256"] = e1["decision_record_ref"], e1["decision_record_sha256"]
        self.t.add_version([e2], decision=False, tamper=lambda line: line["decisions"].update({e1["decision_record_ref"]: e1["decision_record_sha256"]}))
        self.reject("(decision record must be decisions/D-v0002|does not name this entry|not an entry of this version citing it)")

    def test_ai_agent_cannot_be_the_owner(self):
        for name in ("Claude Fable 5.2", "opus agent", "AI assistant", "review bot"):
            t = Synthetic()
            try:
                t.add_version([entry_from_draft(GAZETTE_1962, 1)], decided_by=name)
                with self.assertRaisesRegex(common.LedgerError, "names an AI model or agent"):
                    t.state()
            finally:
                t.close()

    def test_scope_and_legal_approval_statements_are_required(self):
        e = entry_from_draft(GAZETTE_1962, 1)
        body = (f"decision_id: D-v0001\ndecision: APPROVED\nledger_version: 0001\nentries: {self._pairs(e)}\ndecided_by: test owner\n"
                f"date: 2026-11-23\nscope: AUTHENTICATION_PROVENANCE_ONLY\nlegal_approval: GIVEN\n")
        ref, h = self._extra_record("D-v0001.md", body)
        e["decision_record_ref"], e["decision_record_sha256"] = ref, h
        self.t.add_version([e], decision=False, tamper=lambda line: line["decisions"].update({ref: h}))
        self.reject("legal_approval: NOT_GIVEN")

    def test_decision_may_not_predate_review_or_postdate_the_manifest_line(self):
        e = entry_from_draft(GAZETTE_1962, 1)
        body = lambda d: (f"decision_id: D-v0001\ndecision: APPROVED\nledger_version: 0001\nentries: {self._pairs(e)}\ndecided_by: test owner\n"
                          f"date: {d}\nscope: AUTHENTICATION_PROVENANCE_ONLY\nlegal_approval: NOT_GIVEN\n")
        ref, h = self._extra_record("D-v0001.md", body("2026-11-22"))
        e["decision_record_ref"], e["decision_record_sha256"] = ref, h
        self.t.add_version([e], decision=False, tamper=lambda line: line["decisions"].update({ref: h}))
        self.reject("predates the independent review")
        self.t.close()
        self.t = Synthetic()
        e = entry_from_draft(GAZETTE_1962, 1)
        ref, h = self._extra_record("D-v0001.md", body("2026-11-24"))
        e["decision_record_ref"], e["decision_record_sha256"] = ref, h
        self.t.add_version([e], decision=False, tamper=lambda line: line["decisions"].update({ref: h}))
        self.reject("dated after its manifest line")

    def test_no_correction_of_a_withdrawn_entry(self):
        a = entry_from_draft(GAZETTE_1962, 1)
        self.t.add_version([a])
        w = entry_from_draft(GAZETTE_1962, 1, version=2, entry_type="WITHDRAW", target_entry_id=a["entry_id"], withdrawal_reason="OTHER",
                             first_class_record_ref="", proposed_authentication_state="", proposed_class="", justification="w")
        self.t.add_version([w])
        self.t.state()  # the withdrawal itself is valid
        c = entry_from_draft(GAZETTE_1962, 1, version=3, entry_type="CORRECTION", target_entry_id=a["entry_id"])
        self.t.add_version([c])
        self.reject("is not the live row for this sha256")


class TranchePreparation(unittest.TestCase):
    """Prepared tranche material reproduces, stays inactive and never touches the committed ledger."""
    TOOLS = PKG / "tranches/tools"

    def run_tool(self, name):
        return subprocess.run([sys.executable, str(self.TOOLS / name), "--check"], capture_output=True, text=True,
                              env=dict(__import__("os").environ, PYTHONDONTWRITEBYTECODE="1"))

    def test_tranche1_and_policy_data_reproduce(self):
        for t in ("build_tranche1.py", "policy_impact.py"):
            r = self.run_tool(t)
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_prepared_rows_are_inactive_and_cannot_enter_the_ledger_unchanged(self):
        rows = common.read_csv(PKG / "tranches/T1-GAZETTE/proposed_entries_PENDING.csv")
        self.assertEqual(len(rows), 20)
        for r in rows:
            self.assertEqual(r["owner_decision"], "")
            self.assertEqual(r["tranche_status"], "PENDING_NOT_IN_LEDGER")
            self.assertEqual((r["decision_record_ref"], r["reviewer_ref"]), ("", ""))
            with self.assertRaisesRegex(common.LedgerError, "owner_decision=''"):
                L.schema_check({k: r[k] for k in L.COLS}, L.COLS)

    def test_committed_ledger_still_has_only_genesis(self):
        self.assertEqual(len(L.read_manifest(PKG)), 1)
        self.assertEqual(sorted(p.name for p in (PKG / "ledger").iterdir()), ["HEAD", "manifest.jsonl"])
        self.assertEqual(sorted(p.name for p in (PKG / "decisions").iterdir()), ["README.md"])

    def test_tranche1_is_exactly_the_20_primary_gazette_drafts_and_excludes_non_primary(self):
        reg = common.read_csv(PKG / "tranches/T1-GAZETTE/tranche1_source_register.csv")
        want = sorted(s for s, d in DRAFT.items() if d["proposed_class"] == "PRIMARY_GAZETTE_ARCHIVAL_FACSIMILE")
        self.assertEqual(sorted(r["sha256"] for r in reg), want)
        self.assertNotIn(TRA, {r["sha256"] for r in reg})
        self.assertTrue(all(r["rule1_result"] == "PASS" for r in reg))
        sro34 = [r for r in reg if "S.R.O. 34 (1963" in r["document_identity"]][0]
        self.assertIn("COPY PROVENANCE ONLY", sro34["recommendation"].upper())
        born = [r for r in reg if r["fidelity_class"].startswith("BORN_DIGITAL")]
        self.assertEqual(len(born), 2)
        self.assertTrue(all(r["sub_tranche"] == "1B-FIDELITY" for r in born))
        m = {r["tranche_id"]: r for r in common.read_csv(PKG / "tranches/T1-GAZETTE/evidence_verification_matrix.csv")}
        for r in born:
            self.assertIn("NOT CRYPTOGRAPHICALLY VERIFIED", m[r["tranche_id"]]["v11_signature_coverage"])

    def test_simulated_impact_has_no_crosswalk_change(self):
        j = json.loads((PKG / "tranches/T1-GAZETTE/simulated_joint_impact.json").read_text(encoding="utf-8"))
        self.assertTrue(j["label"].startswith("SIMULATION ONLY"))
        self.assertEqual(j["joint_all_20"]["crosswalk_row_changes"], 0)
        self.assertEqual(j["joint_all_20"]["copy_status_changes"], 20)


class ReviewFixes02(unittest.TestCase):
    """Corrections for the independent Fable review of 924047b1 (review/fable_review_924047b1.md)."""
    def setUp(self):
        self.t = GitLedger()

    def tearDown(self):
        self.t.close()

    def bound(self):
        head, merge = self.t.pr([entry_from_draft(GAZETTE_1962, 1)])
        self.t.add_bind(head, merge)
        self.t.commit("bind")
        return head, merge

    def test_f01_replace_refs_fail_closed(self):
        self.bound()
        self.t.state(require_binding=True)
        _git(self.t.dir, "replace", "--graft", "HEAD", _git(self.t.dir, "rev-list", "--max-parents=0", "HEAD"))
        with self.assertRaisesRegex(common.LedgerError, "refs/replace exists"):
            self.t.state(require_binding=True)

    def test_f01_grafts_file_fail_closed(self):
        self.bound()
        (self.t.dir / ".git/info").mkdir(exist_ok=True)
        (self.t.dir / ".git/info/grafts").write_text(_git(self.t.dir, "rev-parse", "HEAD") + "\n", encoding="utf-8")
        with self.assertRaisesRegex(common.LedgerError, "info/grafts exists"):
            self.t.state(require_binding=True)

    def test_f01_inherited_git_environment_is_ignored(self):
        self.bound()
        other = GitLedger()
        try:
            env = {"GIT_DIR": str(other.dir / ".git"), "GIT_WORK_TREE": str(other.dir), "GIT_GRAFT_FILE": str(other.dir / "g"),
                   "GIT_REPLACE_REF_BASE": "refs/x/", "GIT_OBJECT_DIRECTORY": str(other.dir / ".git/objects")}
            with mock.patch.dict(__import__("os").environ, env):
                texts = self.t.state(require_binding=True)
            self.assertEqual([x["effect"] for x in json.loads(texts["transitions.json"])], ["APPLIED"])
            self.assertNotIn("GIT_DIR", binding._env())
            self.assertEqual(binding._env()["GIT_NO_REPLACE_OBJECTS"], "1")
        finally:
            other.close()

    def test_f04_package_change_in_the_merge_is_rejected(self):
        _git(self.t.dir, "checkout", "-q", "-b", "pr1")
        self.t.add_version([entry_from_draft(GAZETTE_1962, 1)])
        head = self.t.commit("reviewed")
        _git(self.t.dir, "checkout", "-q", "main")
        _git(self.t.dir, "merge", "-q", "--no-ff", "--no-commit", "pr1")
        (self.t.dir / "tools_changed_in_merge.py").write_text("x = 1\n", encoding="utf-8")
        merge = self.t.commit("merge that also changes code")
        self.t.add_bind(head, merge)
        with self.assertRaisesRegex(common.LedgerError, "package tree differs between reviewed_head and merge_commit"):
            self.t.state(require_binding=True)

    def test_f05_transitions_carry_the_assurance_level(self):
        self.bound()
        tr = json.loads(self.t.state(require_binding=True)["transitions.json"])
        self.assertIn("ASSERTED_NOT_VERIFIED_OFFLINE", tr[0]["binding_assurance"])
        self.assertIn("VERIFIED_OFFLINE", tr[0]["binding_assurance"])

    def test_f08_truncated_locator_is_refused(self):
        m = strength.URL.search("see https://archive.org/download/x/y.pdf)evil")
        with self.assertRaisesRegex(common.LedgerError, "would be truncated"):
            strength._untruncated("r", "see https://archive.org/download/x/y.pdf)evil", m)
        for ok in ("https://archive.org/download/x/y.pdf; next", "(https://archive.org/download/x/y.pdf)", "https://archive.org/download/x/y.pdf"):
            mm = strength.URL.search(ok)
            strength._untruncated("r", ok, mm)


class ReviewFixes02Records(unittest.TestCase):
    def setUp(self):
        self.t = Synthetic()

    def tearDown(self):
        self.t.close()

    def test_f09_agent_names_with_digits_or_underscores(self):
        for name in ("Fable5", "claude_code", "GPT4", "ai-assistant"):
            t = Synthetic()
            try:
                t.add_version([entry_from_draft(GAZETTE_1962, 1)], decided_by=name)
                with self.assertRaisesRegex(common.LedgerError, "names an AI model or agent"):
                    t.state()
            finally:
                t.close()
        self.assertIsNone(L.AGENT.search("Kai Raina"))  # letters around a listed word do not match

    def test_f10_manifest_types_and_date(self):
        for over, rx in (({"version": True}, "version must be an integer"), ({"rule_version": 1.0}, "rule_version must be an integer"),
                         ({"date": "2026-13-40"}, "not a valid YYYY-MM-DD date"), ({"date": "9999"}, "not a valid YYYY-MM-DD date"), ({"date": "20261123"}, "not a valid YYYY-MM-DD date")):
            t = Synthetic()
            try:
                t.add_version([entry_from_draft(GAZETTE_1962, 1)], tamper=lambda line, o=over: line.update(o))
                with self.assertRaisesRegex(common.LedgerError, rx):
                    L.read_manifest(t.dir)
            finally:
                t.close()

    def test_f11_wrong_scope_is_rejected(self):
        e = entry_from_draft(GAZETTE_1962, 1)
        pairs = f"{e['entry_id']}={e['sha256']}:{L.entry_digest(e)}"
        ref, h = self.t.write_record("D-v0001.md", f"decision_id: D-v0001\ndecision: APPROVED\nledger_version: 0001\nentries: {pairs}\n"
                                                    f"decided_by: test owner\ndate: 2026-11-23\nscope: LEGAL_APPROVAL\nlegal_approval: NOT_GIVEN\n")
        e["decision_record_ref"], e["decision_record_sha256"] = ref, h
        self.t.add_version([e], decision=False, tamper=lambda line: line["decisions"].update({ref: h}))
        with self.assertRaisesRegex(common.LedgerError, "must state scope: AUTHENTICATION_PROVENANCE_ONLY"):
            self.t.state()

    def test_f11_declared_record_hash_must_match(self):
        e = entry_from_draft(GAZETTE_1962, 1)
        self.t.add_version([e])
        f = self.t.dir / "ledger/v0001.csv"
        rows = common.read_csv(f)
        rows[0]["decision_record_sha256"] = "0" * 64
        f.write_text(common.csv_text(L.COLS, rows), encoding="utf-8")
        mf = self.t.dir / "ledger/manifest.jsonl"
        ls = mf.read_text(encoding="utf-8").split("\n")
        d = json.loads(ls[1])
        d["file_sha256"] = common.sha256_file(f)
        ls[1] = L.canonical_line(d)
        mf.write_text("\n".join(ls), encoding="utf-8")
        (self.t.dir / "ledger/HEAD").write_text(f"1 {common.sha256_text(ls[1])}\n", encoding="utf-8")
        with self.assertRaisesRegex(common.LedgerError, "hash does not match the entry and the manifest pin"):
            self.t.state()


class ReviewFixes02More(unittest.TestCase):
    def test_f11_urlcheck_alone_rejects_bad_hosts_and_escapes(self):
        for u in ("https://-a.example.org/x", "https://a_b.example.org/x", "https://a..example.org/x", "https://example.123/x",
                  "https://example.org/x%3Fy", "https://example.org/x%23y", "https://example.org/x%2Fy", "https://example.org/x%25y"):
            self.assertNotEqual(urlcheck.problem(u), "", u)
        self.assertEqual(urlcheck.problem("https://example.org/a%20b.pdf"), "")

    def test_f06_court_path_shapes(self):
        self.assertFalse(strength.host_ok("https://api.sci.gov.in/uploads/x.pdf", COURT))
        self.assertFalse(strength.host_ok("https://api.sci.gov.in/jonew/judis/../x.pdf", COURT))
        for u in {u for u, _ in strength.url_pairs() if "sci.gov.in" in u}:
            self.assertTrue(strength.host_ok(u, COURT), u)

    def test_f11_genesis_line_with_content_is_rejected(self):
        t = Synthetic()
        try:
            mf = t.dir / "ledger/manifest.jsonl"
            d = json.loads(mf.read_text(encoding="utf-8").split("\n")[0])
            d["decisions"] = {"decisions/D-v0000.md": "0" * 64}
            s = L.canonical_line(d)
            mf.write_text(s + "\n", encoding="utf-8")
            (t.dir / "ledger/HEAD").write_text(f"0 {common.sha256_text(s)}\n", encoding="utf-8")
            with self.assertRaisesRegex(common.LedgerError, "genesis line must carry no entries"):
                t.state()
        finally:
            t.close()

    def test_f02_tranche1_reports_l5_image_quotations(self):
        m = common.read_csv(PKG / "tranches/T1-GAZETTE/evidence_verification_matrix.csv")
        reg = common.read_csv(PKG / "tranches/T1-GAZETTE/tranche1_source_register.csv")
        src = {r["tranche_id"]: r["identifier_source"] for r in reg}
        self.assertEqual(sorted(k for k, v in src.items() if v == "L5_DISCOVERY_REGISTER_ONLY"),
                         ["T1-02", "T1-11", "T1-14", "T1-16", "T1-17", "T1-18", "T1-19"])
        self.assertTrue(all(v in ("IMAGE_CHECK_OR_TRANSCRIPTION", "L5_DISCOVERY_REGISTER_ONLY") for v in src.values()))
        pend = {r["sha256"]: r for r in common.read_csv(PKG / "tranches/T1-GAZETTE/proposed_entries_PENDING.csv")}
        for r in reg:
            if r["identifier_source"] == "L5_DISCOVERY_REGISTER_ONLY":
                self.assertIn("read-only discovery agent", pend[r["sha256"]]["limitations"])
                self.assertIn("ADVISABLE FIRST", r["recommendation"])
        self.assertEqual(sorted({r["sub_tranche"] for r in reg}), ["1A-READY", "1B-FIDELITY"])
        t16 = [r for r in m if r["tranche_id"] == "T1-16"][0]
        self.assertIn("S.R.O. 332", t16["v07_identity_page_evidence"])
        self.assertIn("not an identity-reference kind under rule 1", t16["v07_identity_page_evidence"])
        rows = {r["sha256"]: r for r in common.read_csv(PKG / "tranches/T1-GAZETTE/proposed_entries_PENDING.csv")}
        sro34 = [r for r in rows.values() if "S.R.O. 34 (1963" in r["document_identity"]][0]
        self.assertNotIn("notes misdate as", sro34["document_identity"])
        self.assertIn("UNVERIFIED", sro34["limitations"])
        for r in rows.values():
            if r["sha256"] in {x["sha256"] for x in reg if x["sub_tranche"] == "1B-FIDELITY"}:
                self.assertIn("STRUCTURAL ONLY", r["limitations"])


def _forge_commit_graph(t, chain=False):
    """Fable R-01 vector: a direct push whose commit-graph entry claims two parents (base, version commit)."""
    import struct, hashlib
    base = _git(t.dir, "rev-parse", "HEAD")
    t.add_version([entry_from_draft(GAZETTE_1962, 1)])
    c1 = t.commit("direct push version")
    _git(t.dir, "commit", "-q", "--allow-empty", "-m", "innocent")
    c2 = _git(t.dir, "rev-parse", "HEAD")
    t.add_bind(c1, c2)
    t.commit("bind")
    _git(t.dir, "commit-graph", "write", "--reachable", *(["--split"] if chain else []))
    f = next((t.dir / ".git/objects/info/commit-graphs").glob("graph-*.graph")) if chain else t.dir / ".git/objects/info/commit-graph"
    b = bytearray(f.read_bytes())
    ch = {bytes(b[8 + 12 * i:12 + 12 * i]): struct.unpack(">Q", b[12 + 12 * i:20 + 12 * i])[0] for i in range(b[6] + 1)}
    oids = [bytes(b[ch[b"OIDL"] + 20 * i:ch[b"OIDL"] + 20 * i + 20]).hex() for i in range((ch[b"CDAT"] - ch[b"OIDL"]) // 20)]
    o = ch[b"CDAT"] + 36 * oids.index(c2) + 20
    b[o:o + 4], b[o + 4:o + 8] = struct.pack(">I", oids.index(base)), struct.pack(">I", oids.index(c1))
    b[-20:] = hashlib.sha1(bytes(b[:-20])).digest()
    __import__("os").chmod(f, 0o644)
    f.write_bytes(bytes(b))
    if chain:
        new = f.with_name("graph-" + bytes(b[-20:]).hex() + ".graph")
        f.rename(new)
        chain_file = f.parent / "commit-graph-chain"
        if chain_file.exists():  # git writes it read-only (0444); a non-root runner cannot overwrite it otherwise (Fable F-01 of bb1f0971)
            __import__("os").chmod(chain_file, 0o644)
        chain_file.write_text(bytes(b[-20:]).hex() + "\n")
    # the forgery must be live for the installed git, or the rejection test would be vacuous (Fable F-04 of bb1f0971)
    assert len(_git(t.dir, "rev-list", "--parents", "-n", "1", c2).split()) == 3, "plain git does not honour the forged commit-graph"
    return c1, c2


class NestedGitLedger(GitLedger):
    """The ledger root is a sub-directory of the git repository (as in the real layout)."""
    def __init__(self):
        Synthetic.__init__(self)
        self.repo = Path(tempfile.mkdtemp(prefix="authledger_repo_"))
        shutil.move(str(self.dir), str(self.repo / "pkg"))
        self.dir = self.repo / "pkg"
        _git(self.repo, "init", "-q", "-b", "main")
        _git(self.repo, "config", "user.email", "test@example.invalid")
        _git(self.repo, "config", "user.name", "test")
        _git(self.repo, "config", "commit.gpgsign", "false")
        self.commit("genesis")

    def close(self):
        shutil.rmtree(self.repo, ignore_errors=True)


class ReviewFixes03(unittest.TestCase):
    """Corrections for the Fable re-review of 64859d4d (review/fable_rereview_64859d4d.md)."""
    def test_r01_forged_commit_graph_single_and_split(self):
        for chain in (False, True):
            t = GitLedger()
            try:
                _forge_commit_graph(t, chain)
                with self.assertRaisesRegex(common.LedgerError, r"has 1 parent\(s\)"):
                    t.state(require_binding=True)
            finally:
                t.close()

    def test_r02_repository_top_is_pinned(self):
        t = GitLedger()
        try:
            head, merge = t.pr([entry_from_draft(GAZETTE_1962, 1)])
            t.add_bind(head, merge)
            t.commit("bind")
            lines = L.read_manifest(t.dir)
            binding.verify(t.dir, lines[2], lines, L.canonical_line, expected_top=t.dir)
            with self.assertRaisesRegex(common.LedgerError, "is not the expected repository"):
                binding.verify(t.dir, lines[2], lines, L.canonical_line, expected_top=t.dir.parent)
        finally:
            t.close()
        self.assertTrue(L.is_committed_package(PKG))  # the call-site behaviour is tested end to end in C8Security
        self.assertEqual(PKG.parents[2], REPO)

    def test_r06_nested_prefix_merge_checks_only_the_package(self):
        t = NestedGitLedger()
        try:
            _git(t.repo, "checkout", "-q", "-b", "pr1")
            t.add_version([entry_from_draft(GAZETTE_1962, 1)])
            head = t.commit("reviewed")
            _git(t.repo, "checkout", "-q", "main")
            (t.repo / "outside.txt").write_text("base moved on outside the package\n", encoding="utf-8")
            t.commit("unrelated base change")
            _git(t.repo, "merge", "-q", "--no-ff", "-m", "merge", "pr1")
            merge = _git(t.repo, "rev-parse", "HEAD")
            t.add_bind(head, merge)
            t.commit("bind")
            self.assertEqual([x["effect"] for x in json.loads(t.state(require_binding=True)["transitions.json"])], ["APPLIED"])
        finally:
            t.close()
        t = NestedGitLedger()
        try:
            _git(t.repo, "checkout", "-q", "-b", "pr1")
            t.add_version([entry_from_draft(GAZETTE_1962, 1)])
            head = t.commit("reviewed")
            _git(t.repo, "checkout", "-q", "main")
            _git(t.repo, "merge", "-q", "--no-ff", "--no-commit", "pr1")
            (t.dir / "tools_added_in_merge.py").write_text("x = 1\n", encoding="utf-8")
            merge = t.commit("merge with a package change")
            t.add_bind(head, merge)
            with self.assertRaisesRegex(common.LedgerError, "package tree differs"):
                t.state(require_binding=True)
        finally:
            t.close()

    def test_r06_environment_and_git_options(self):
        env = binding._env()
        self.assertEqual(env["GIT_GRAFT_FILE"], __import__("os").devnull)
        self.assertEqual((env["GIT_CONFIG_NOSYSTEM"], env["GIT_CONFIG_GLOBAL"]), ("1", __import__("os").devnull))
        with mock.patch.object(binding.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, b"", b"")) as run:
            binding._git(".", "status")
        args = run.call_args[0][0]
        for opt in ("protocol.allow=never", "core.useReplaceRefs=false", "core.commitGraph=false"):
            self.assertIn(opt, args)

    def test_r05_r04_url_residuals(self):
        for u in ("https://archive.org/download/x/.../y.pdf", "https://archive.org/download/x/%20/y.pdf", "https://archive.org/download/x/a%E2%88%95b.pdf",
                  "https://archive.org/download/x/a%E2%81%84b.pdf", "https://archive.org/download/x/a%E2%A7%B8b.pdf", "https://archive.org/download/x/a%EF%BF%BDb.pdf",
                  "https://archive.org/download/x/a%E1%9A%80b.pdf"):
            self.assertNotEqual(urlcheck.problem(u), "", u)
        self.assertNotEqual(urlcheck.problem("https://1.0x7f/x"), "")
        self.assertNotEqual(urlcheck.problem("https://example.1a/x"), "")
        for u in ("https://api.sci.gov.in/jonew/judis/1234.pdf?redirect=//evil", "https://desw.gov.in/a.pdf?x=1"):
            self.assertFalse(strength.host_ok(u, COURT) or strength.host_ok(u, GOVPUB), u)
        for u in ("https://api.sci.gov.in/x/jonew/judis/1.pdf", "https://api.sci.gov.in/jonew/judis/1.pdf.html"):
            self.assertFalse(strength.host_ok(u, COURT), u)

    def test_r06_untruncated_is_applied_at_both_call_sites(self):
        sha = GAZETTE_1962
        ret = {"sha256": sha, "authenticity": "ORIGINAL_OFFICIAL", "verification_state": "SOURCE_VERIFIED",
               "locator": "https://archive.org/download/x/y.pdf)evil"}
        json_src = [p for p in pins.EVIDENCE_INPUTS if strength._json_source(p)][0]
        with mock.patch.object(strength, "resolve", return_value=(json_src, ret)):
            with self.assertRaisesRegex(common.LedgerError, "would be truncated"):
                strength._first_class("x", sha)
        dl = {"downloaded_sha256": sha, "candidate_url_or_identifier": "https://desw.gov.in/a.pdf|b"}
        with mock.patch.object(strength, "resolve", return_value=("PILOT-01/registers/source_discovery_2026-11-22.csv", dl)):
            with self.assertRaisesRegex(common.LedgerError, "would be truncated"):
                strength._first_class("x", sha)

    def test_r06_l5_observation_conditions(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("bt1", PKG / "tranches/tools/build_tranche1.py")
        bt1 = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(bt1)
        sha = GAZETTE_1962
        good = {"status": "LOCATED_IMAGE_CHECKED", "sha256": sha, "render_sha256": "a" * 64, "identity_evidence": "S.R.O. 1"}
        for bad in ({"status": "NOT_FOUND"}, {"sha256": "b" * 64}, {"render_sha256": ""}):
            with mock.patch.object(bt1.strength, "resolve", return_value=("p", dict(good, **bad))):
                self.assertEqual(bt1.l5_observations("L5:x#y", sha), [], bad)
        with mock.patch.object(bt1.strength, "resolve", return_value=("p", good)):
            self.assertEqual(len(bt1.l5_observations("L5:x#y", sha)), 1)


class LayoutGitLedger(GitLedger):
    """A git repository whose ledger sits at the real package path legal_knowledge/audit_work/AUTH-LEDGER (C8)."""
    def __init__(self):
        Synthetic.__init__(self)
        self.repo = Path(tempfile.mkdtemp(prefix="authledger_layout_"))
        target = self.repo / "legal_knowledge/audit_work/AUTH-LEDGER"
        target.parent.mkdir(parents=True)
        shutil.move(str(self.dir), str(target))
        self.dir = target
        _git(self.repo, "init", "-q", "-b", "main")
        _git(self.repo, "config", "user.email", "test@example.invalid")
        _git(self.repo, "config", "user.name", "test")
        _git(self.repo, "config", "commit.gpgsign", "false")
        self.commit("genesis")

    def bound(self):
        head, merge = self.pr([entry_from_draft(GAZETTE_1962, 1)])
        self.add_bind(head, merge)
        self.commit("bind")
        return head, merge

    def close(self):
        shutil.rmtree(self.repo, ignore_errors=True)


def _effects(texts):
    return [x["effect"] for x in json.loads(texts["transitions.json"])]


class C8Base(unittest.TestCase):
    """Helpers for the Cycle 8 security tests (no tests of its own)."""
    def setUp(self):
        self.cleanup = []

    def tearDown(self):
        for c in self.cleanup:
            c()

    def ledger(self, cls=LayoutGitLedger):
        t = cls()
        self.cleanup.append(t.close)
        return t

    def tmp(self):
        d = Path(tempfile.mkdtemp(prefix="authledger_c8_"))
        self.cleanup.append(lambda: shutil.rmtree(d, ignore_errors=True))
        return d

    def state_as_committed(self, package, root=None):
        with mock.patch.object(L, "COMMITTED_PACKAGE", Path(package)):
            texts, _ = reader.effective_state(root or package, None, True)
        return texts

    def attacker_copy(self, victim):
        """An attacker repository with an honest reviewed merge; its ledger bytes are copied into the victim package by a
        direct commit, so only a diverted history could make the victim's BIND line verify."""
        a = self.ledger(GitLedger)
        h, m = a.pr([entry_from_draft(GAZETTE_1962, 1)])
        a.add_bind(h, m)
        a.commit("bind")
        for sub in ("ledger", "decisions"):
            shutil.rmtree(victim.dir / sub, ignore_errors=True)
            shutil.copytree(a.dir / sub, victim.dir / sub)
        victim.commit("direct commit of copied ledger bytes (no reviewed merge)")
        return a



class C8Security(C8Base):
    """Cycle 8 closeout of Fable C-01 (call-site pin tested end to end) and C-02 (symlinked package) plus C-04."""
    def test_c01_honest_binding_in_the_real_layout_applies(self):
        t = self.ledger()
        t.bound()
        self.assertEqual(_effects(self.state_as_committed(t.dir)), ["APPLIED"])

    def test_c01_nested_gitdir_file_is_rejected_at_the_call_site(self):
        v = self.ledger()
        a = self.attacker_copy(v)
        (v.dir / ".git").write_text(f"gitdir: {a.dir / '.git'}\n", encoding="utf-8")
        self.assertEqual(_effects(reader.effective_state(v.dir, None, True)[0]), ["APPLIED"])  # unpinned: the diversion works
        with self.assertRaisesRegex(common.LedgerError, "is not the expected repository"):
            self.state_as_committed(v.dir)  # pinned at the real call site: rejected

    def test_c01_nested_git_directory_is_rejected_at_the_call_site(self):
        v = self.ledger()
        a = self.attacker_copy(v)
        shutil.copytree(a.dir / ".git", v.dir / ".git")
        with self.assertRaisesRegex(common.LedgerError, "is not the expected repository"):
            self.state_as_committed(v.dir)

    def test_c04_forged_commit_object_under_a_genuine_id_is_rejected(self):
        import zlib, os
        t = self.ledger()
        base = _git(t.repo, "rev-parse", "HEAD")
        t.add_version([entry_from_draft(GAZETTE_1962, 1)])
        c1 = t.commit("direct push version")
        _git(t.repo, "commit", "-q", "--allow-empty", "-m", "innocent")
        c2 = _git(t.repo, "rev-parse", "HEAD")
        t.add_bind(c1, c2)
        t.commit("bind")
        raw = subprocess.run(["git", "-C", str(t.repo), "cat-file", "commit", c2], capture_output=True).stdout
        fake = raw.split(b"\n")[0] + b"\nparent " + base.encode() + b"\nparent " + c1.encode() + b"\n" + raw.split(b"\n", 2)[2]
        obj = t.repo / ".git/objects" / c2[:2] / c2[2:]
        os.chmod(obj, 0o644)
        obj.write_bytes(zlib.compress(b"commit %d\0" % len(fake) + fake))
        with self.assertRaisesRegex(common.LedgerError, "does not hash to its id"):
            self.state_as_committed(t.dir)

    def _symlink_repo(self, link_rel, target):
        import os
        r = self.tmp()
        (r / link_rel).parent.mkdir(parents=True, exist_ok=True)
        os.symlink(target, r / link_rel)
        _git(r, "init", "-q", "-b", "main")
        _git(r, "config", "user.email", "test@example.invalid")
        _git(r, "config", "user.name", "test")
        _git(r, "add", "-A")
        _git(r, "commit", "-q", "-m", "committed symlink")
        return r

    def test_c02_symlinked_package_to_another_repository_is_rejected(self):
        a = self.ledger()
        a.bound()
        r = self._symlink_repo("legal_knowledge/audit_work/AUTH-LEDGER", a.dir)
        self.assertIn("120000", _git(r, "ls-tree", "HEAD", "--", "legal_knowledge/audit_work/AUTH-LEDGER"))
        with self.assertRaisesRegex(common.LedgerError, "is a symlink"):
            self.state_as_committed(r / "legal_knowledge/audit_work/AUTH-LEDGER")

    def test_c02_nested_symlink_is_rejected(self):
        a = self.ledger()
        a.bound()
        r = self._symlink_repo("legal_knowledge/audit_work", a.repo / "legal_knowledge/audit_work")
        with self.assertRaisesRegex(common.LedgerError, "is a symlink"):
            self.state_as_committed(r / "legal_knowledge/audit_work/AUTH-LEDGER")

    def test_c02_broken_symlink_is_rejected(self):
        r = self._symlink_repo("legal_knowledge/audit_work/AUTH-LEDGER", "/nonexistent/authledger")
        with self.assertRaisesRegex(common.LedgerError, "is a symlink"):
            self.state_as_committed(r / "legal_knowledge/audit_work/AUTH-LEDGER")

    def test_c02_committed_symlink_replaced_by_a_real_directory_is_rejected(self):
        a = self.ledger()
        a.bound()
        r = self._symlink_repo("legal_knowledge/audit_work/AUTH-LEDGER", a.dir)
        pkg = r / "legal_knowledge/audit_work/AUTH-LEDGER"
        pkg.unlink()
        shutil.copytree(a.dir, pkg, ignore=shutil.ignore_patterns(".git"))
        with self.assertRaisesRegex(common.LedgerError, "committed with mode 120000"):
            self.state_as_committed(pkg)

    def test_c02_fresh_clone_of_an_honest_layout_applies(self):
        t = self.ledger()
        t.bound()
        d = self.tmp()
        subprocess.run(["git", "clone", "-q", str(t.repo), str(d / "clone")], check=True, capture_output=True)
        pkg = d / "clone/legal_knowledge/audit_work/AUTH-LEDGER"
        self.assertEqual(_effects(self.state_as_committed(pkg)), ["APPLIED"])

    def test_c02_layout_check_runs_for_the_committed_ledger_even_at_version_zero(self):
        self.assertEqual(CLI.verify(), ["v0000 ok"])
        with mock.patch.object(binding, "check_package_layout", side_effect=common.LedgerError("layout check ran")):
            with self.assertRaisesRegex(common.LedgerError, "layout check ran"):
                reader.effective_state(PKG, 0)
        self.assertFalse(L.is_committed_package(self.tmp()))


class C8SecurityMore(C8Base):
    def test_c04_forged_parent_object_is_rejected(self):
        import zlib, os
        t = self.ledger()
        head, merge = t.bound()
        p0 = _git(t.repo, "rev-parse", f"{merge}^1")
        obj = t.repo / ".git/objects" / p0[:2] / p0[2:]
        raw = subprocess.run(["git", "-C", str(t.repo), "cat-file", "commit", p0], capture_output=True).stdout
        os.chmod(obj, 0o644)
        forged = raw + b"\nforged\n"
        obj.write_bytes(zlib.compress(b"commit %d\0" % len(forged) + forged))
        with self.assertRaisesRegex(common.LedgerError, "parent commit object of merge_commit does not hash"):
            self.state_as_committed(t.dir)

    def test_c02_logical_package_path_is_not_symlink_resolved(self):
        import os
        d = self.tmp()
        os.symlink(PKG, d / "linked-AUTH-LEDGER")
        out = subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0, sys.argv[1]); import common; print(common.LOGICAL_PKG); print(common.PKG)",
                              str(d / "linked-AUTH-LEDGER/tools")], capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
        logical, resolved = out.stdout.split()
        self.assertEqual(Path(logical), d / "linked-AUTH-LEDGER")
        self.assertEqual(Path(resolved), PKG.resolve())


C8Base._symlink_repo = C8Security._symlink_repo  # shared helper (a committed symlink in a fresh repository)


class C8SecurityRound2(C8Base):
    """Corrections for the Fable review of be861ec0 (REJECT): F-01 real CLI through symlinks, F-02 forged tree objects,
    F-03 surviving mutants, F-04 fail-closed committed-layout check, F-07 bundle reproducibility."""
    CLI_PATH = "legal_knowledge/audit_work/AUTH-LEDGER/tools/auth_ledger.py"

    def run_cli(self, script, *args, cwd=None):
        import os
        return subprocess.run([sys.executable, str(script), *args], capture_output=True, text=True, cwd=cwd or self.tmp(),
                              env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))

    def attacker_package_with_tools(self):
        a = self.ledger()
        a.bound()
        shutil.copytree(PKG / "tools", a.dir / "tools", ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copytree(PKG / "schema", a.dir / "schema")  # read at import time by ledger.py
        return a

    def test_f01_real_cli_through_a_committed_package_symlink_is_rejected(self):
        a = self.attacker_package_with_tools()
        r = self._symlink_repo("legal_knowledge/audit_work/AUTH-LEDGER", a.dir)
        for cmd in (["verify"], ["build", "--out", str(self.tmp() / "out")]):
            p = self.run_cli(r / self.CLI_PATH, *cmd)
            self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
            self.assertIn("is a symlink", p.stderr)

    def test_f01_real_cli_through_a_symlinked_parent_is_rejected(self):
        a = self.attacker_package_with_tools()
        r = self._symlink_repo("legal_knowledge", a.repo / "legal_knowledge")
        p = self.run_cli(r / self.CLI_PATH, "verify")
        self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
        self.assertIn("is a symlink", p.stderr)

    def test_f01_real_cli_on_the_real_repository_still_verifies(self):
        p = self.run_cli(REPO / self.CLI_PATH, "verify")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("v0000 ok", p.stdout)

    def test_f02_forged_tree_object_under_a_genuine_id_is_rejected(self):
        import os
        t = self.ledger()
        _git(t.repo, "checkout", "-q", "-b", "unrelated")
        (t.repo / "unrelated.txt").write_text("an honest, reviewed but unrelated change\n", encoding="utf-8")
        rh = t.commit("unrelated reviewed change")
        _git(t.repo, "checkout", "-q", "main")
        _git(t.repo, "merge", "-q", "--no-ff", "-m", "merge unrelated", "unrelated")
        mc = _git(t.repo, "rev-parse", "HEAD")
        t.add_version([entry_from_draft(GAZETTE_1962, 1)])
        c = t.commit("direct, unreviewed ledger version")
        t.add_bind(rh, mc)
        t.commit("bind naming the unrelated merge")
        with self.assertRaises(common.LedgerError):
            self.state_as_committed(t.dir)  # honest objects: rejected
        src = _git(t.repo, "rev-parse", f"{c}^{{tree}}")
        for victim in (_git(t.repo, "rev-parse", f"{rh}^{{tree}}"), _git(t.repo, "rev-parse", f"{mc}^{{tree}}")):
            dst = t.repo / ".git/objects" / victim[:2] / victim[2:]
            os.chmod(dst, 0o644)
            dst.write_bytes((t.repo / ".git/objects" / src[:2] / src[2:]).read_bytes())
        with self.assertRaisesRegex(common.LedgerError, "tree object .* does not hash to its id"):
            self.state_as_committed(t.dir)

    def test_f03_committed_package_is_the_logical_path_not_the_resolved_one(self):
        import os
        a = self.ledger()
        a.bound()
        r = self._symlink_repo("legal_knowledge/audit_work/AUTH-LEDGER", a.dir)
        logical = r / "legal_knowledge/audit_work/AUTH-LEDGER"
        with mock.patch.object(L, "COMMITTED_PACKAGE", logical):
            self.assertTrue(L.is_committed_package(logical))                 # abspath clause
            self.assertTrue(L.is_committed_package(Path(os.path.realpath(logical))))  # resolve clause
            with self.assertRaisesRegex(common.LedgerError, "is a symlink"):
                reader.effective_state(Path(os.path.realpath(logical)), None, True)  # resolved root still checked

    def test_f04_gitlink_unborn_head_and_untracked_package_fail_closed(self):
        t = self.ledger()
        t.bound()
        head = _git(t.repo, "rev-parse", "HEAD")
        _git(t.repo, "rm", "-r", "-q", "--cached", "legal_knowledge/audit_work")
        _git(t.repo, "update-index", "--add", "--cacheinfo", f"160000,{head},legal_knowledge/audit_work")
        _git(t.repo, "commit", "-q", "-m", "audit_work committed as a gitlink")
        with self.assertRaisesRegex(common.LedgerError, "committed with mode 160000"):
            self.state_as_committed(t.dir)
        u = self.tmp()
        pkg = u / "legal_knowledge/audit_work/AUTH-LEDGER"
        shutil.copytree(t.dir, pkg)
        _git(u, "init", "-q", "-b", "main")
        with self.assertRaisesRegex(common.LedgerError, "no HEAD commit"):
            binding.check_package_layout(pkg)
        (u / "other.txt").write_text("x\n", encoding="utf-8")
        _git(u, "add", "other.txt")
        _git(u, "-c", "user.email=t@example.invalid", "-c", "user.name=t", "commit", "-q", "-m", "package untracked")
        with self.assertRaisesRegex(common.LedgerError, "not recorded in HEAD"):
            binding.check_package_layout(pkg)

    def test_f03_intermediate_committed_symlink_with_real_worktree_directory_is_rejected(self):
        a = self.ledger()
        a.bound()
        r = self._symlink_repo("legal_knowledge/audit_work", a.repo / "legal_knowledge/audit_work")
        (r / "legal_knowledge/audit_work").unlink()
        shutil.copytree(a.repo / "legal_knowledge/audit_work", r / "legal_knowledge/audit_work", ignore=shutil.ignore_patterns(".git"))
        with self.assertRaisesRegex(common.LedgerError, "legal_knowledge/audit_work is committed with mode 120000"):
            self.state_as_committed(r / "legal_knowledge/audit_work/AUTH-LEDGER")

    def test_f07_bundle_clone_verifies(self):
        t = self.ledger()
        t.bound()
        d = self.tmp()
        _git(t.repo, "bundle", "create", "-q", str(d / "ledger.bundle"), "--all")
        subprocess.run(["git", "clone", "-q", str(d / "ledger.bundle"), str(d / "clone")], check=True, capture_output=True)
        self.assertEqual(_effects(self.state_as_committed(d / "clone/legal_knowledge/audit_work/AUTH-LEDGER")), ["APPLIED"])


class C8SecurityRound2b(C8Base):
    def test_f04_package_inside_a_larger_repository_fails_closed(self):
        outer = self.tmp()
        _git(outer, "init", "-q", "-b", "main")
        pkg = outer / "nested/legal_knowledge/audit_work/AUTH-LEDGER"
        t = Synthetic()
        self.cleanup.append(t.close)
        shutil.copytree(t.dir, pkg)
        _git(outer, "add", "-A")
        _git(outer, "-c", "user.email=t@example.invalid", "-c", "user.name=t", "commit", "-q", "-m", "package nested below the repository top")
        with self.assertRaisesRegex(common.LedgerError, "is not the package's own repository top"):
            binding.check_package_layout(pkg)


class C8SecurityRound3(C8Base):
    attacker_package_with_tools = C8SecurityRound2.attacker_package_with_tools
    CLI_PATH = C8SecurityRound2.CLI_PATH
    """Fable focused re-review of 06a54c66: R-01 relative CLI inside a link, R-02 forged ancestry, R-03 untested
    controls (blob, base manifest, library import), R-04 missing git and refused repositories."""
    def _forge(self, repo, oid, extra=b"\nforged\n"):
        import zlib, os
        kind = subprocess.run(["git", "-C", str(repo), "cat-file", "-t", oid], capture_output=True, text=True).stdout.strip()
        raw = subprocess.run(["git", "-C", str(repo), "cat-file", kind, oid], capture_output=True).stdout + extra
        obj = repo / ".git/objects" / oid[:2] / oid[2:]
        os.chmod(obj, 0o644)
        obj.write_bytes(zlib.compress(f"{kind} {len(raw)}\0".encode() + raw))

    def test_r01_relative_cli_inside_the_link_target_uses_the_logical_cwd(self):
        import os
        a = self.attacker_package_with_tools()
        r = self._symlink_repo("legal_knowledge/audit_work/AUTH-LEDGER", a.dir)
        logical = r / "legal_knowledge/audit_work/AUTH-LEDGER"
        p = subprocess.run([sys.executable, "tools/auth_ledger.py", "verify"], capture_output=True, text=True, cwd=os.path.realpath(logical),
                           env=dict(os.environ, PWD=str(logical), PYTHONDONTWRITEBYTECODE="1"))
        self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
        self.assertIn("is a symlink", p.stderr)

    def test_r02_forged_interior_ancestry_commit_is_rejected(self):
        t = self.ledger()
        head, merge = t.pr([entry_from_draft(GAZETTE_1962, 1)])
        (t.repo / "interim.txt").write_text("interim\n", encoding="utf-8")
        interim = t.commit("interim commit between merge and bind")
        t.add_bind(head, merge)
        t.commit("bind")
        self.assertEqual(_effects(self.state_as_committed(t.dir)), ["APPLIED"])
        self._forge(t.repo, interim)
        with self.assertRaisesRegex(common.LedgerError, "not in the history of the checked-out HEAD"):
            self.state_as_committed(t.dir)

    def test_r03_forged_pinned_blob_is_rejected(self):
        t = self.ledger()
        head, merge = t.bound()
        blob = _git(t.repo, "rev-parse", f"{head}:legal_knowledge/audit_work/AUTH-LEDGER/decisions/R-v0001.md")
        self._forge(t.repo, blob)
        with self.assertRaisesRegex(common.LedgerError, "blob object .* does not hash to its id"):
            self.state_as_committed(t.dir)

    def test_r03_forged_base_manifest_is_rejected(self):
        t = self.ledger()
        head, merge = t.bound()
        base_manifest = _git(t.repo, "rev-parse", f"{merge}^1:legal_knowledge/audit_work/AUTH-LEDGER/ledger/manifest.jsonl")
        self._forge(t.repo, base_manifest, extra=b"")
        raw_ok = True
        try:
            self.state_as_committed(t.dir)
        except common.LedgerError:
            raw_ok = False
        self.assertTrue(raw_ok)  # an unchanged object is fine; now really forge it
        self._forge(t.repo, base_manifest, extra=b'{"forged":1}\n')
        with self.assertRaisesRegex(common.LedgerError, "does not hash to its id"):
            self.state_as_committed(t.dir)

    def test_r03_library_import_through_a_symlink_is_rejected(self):
        import os
        a = self.attacker_package_with_tools()
        r = self._symlink_repo("legal_knowledge/audit_work/AUTH-LEDGER", a.dir)
        tools = r / "legal_knowledge/audit_work/AUTH-LEDGER/tools"
        code = ("import sys; sys.path.insert(0, sys.argv[1]); import reader, common\n"
                "try:\n    reader.effective_state(common.LOGICAL_PKG, 0)\nexcept common.LedgerError as e:\n    print('REJECTED', e)\n")
        p = subprocess.run([sys.executable, "-c", code, str(tools)], capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
        self.assertIn("REJECTED", p.stdout, p.stderr)
        self.assertIn("is a symlink", p.stdout)

    def test_n01_library_import_orders_through_a_symlink_are_rejected(self):  # confirmation N-01
        import os
        a = self.attacker_package_with_tools()
        r = self._symlink_repo("legal_knowledge/audit_work/AUTH-LEDGER", a.dir)
        tools = r / "legal_knowledge/audit_work/AUTH-LEDGER/tools"
        for first in ("ledger", "binding", "pins", "strength", "auth_ledger"):
            code = (f"import sys; sys.path.insert(0, sys.argv[1]); import {first}; import reader, common\n"
                    "try:\n    reader.effective_state(common.LOGICAL_PKG, 0)\nexcept common.LedgerError as e:\n    print('REJECTED', e)\n")
            p = subprocess.run([sys.executable, "-c", code, str(tools)], capture_output=True, text=True,
                               env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
            self.assertIn("REJECTED", p.stdout, (first, p.stderr))

    def test_n05_stale_pwd_is_ignored(self):  # confirmation N-05: $PWD used only when it names the real cwd
        import os
        p = subprocess.run([sys.executable, self.CLI_PATH, "verify"], capture_output=True, text=True, cwd=REPO,
                           env=dict(os.environ, PWD="/nonexistent/stale", PYTHONDONTWRITEBYTECODE="1"))
        self.assertEqual(p.returncode, 0, p.stderr)  # relative script, stale $PWD: falls back to the real cwd and verifies
        self.assertIn("v0000 ok", p.stdout)

    def test_r04_missing_git_and_refused_repository_fail_closed(self):
        with mock.patch.object(binding.subprocess, "run", side_effect=FileNotFoundError("git")):
            with self.assertRaisesRegex(common.LedgerError, "git is not installed"):
                binding._git(".", "status")
        t = self.ledger()
        refused = subprocess.CompletedProcess([], 128, b"", b"fatal: detected dubious ownership")
        real = binding._git
        with mock.patch.object(binding, "_git", side_effect=lambda cwd, *a, **k: refused if a[:2] == ("rev-parse", "--show-toplevel") else real(cwd, *a, **k)):
            with self.assertRaisesRegex(common.LedgerError, "git cannot read the repository"):
                binding.check_package_layout(t.dir)


class C10EffectiveIntegrity(unittest.TestCase):
    """C9 synthetic transaction finding TXN-1: verify must reject entries under effective/ that no manifest line accounts for.
    All mutations happen inside a temporary copy (Synthetic); the committed ledger is never touched."""
    def setUp(self):
        self.t = Synthetic()
        shutil.copytree(PKG / "effective", self.t.dir / "effective")
        self.eff = self.t.dir / "effective"

    def tearDown(self):
        self.t.close()

    def bad(self, why="not accounted for"):
        with self.assertRaisesRegex(common.LedgerError, why):
            CLI.verify(self.t.dir)

    def test_clean_copy_verifies(self):
        self.assertEqual(CLI.verify(self.t.dir), ["v0000 ok"])

    def test_stray_file_in_version_dir(self):
        (self.eff / "v0000/extra.csv").write_text("x")
        self.bad("effective/v0000/extra.csv")

    def test_stray_file_at_effective_root(self):
        (self.eff / "notes.txt").write_text("x")
        self.bad("effective/notes.txt")

    def test_unmanifested_version_dir(self):
        shutil.copytree(self.eff / "v0000", self.eff / "v0001")
        self.bad("effective/v0001")

    def test_nested_dir_in_version_dir(self):
        (self.eff / "v0000/sub").mkdir()
        (self.eff / "v0000/sub/x.csv").write_text("x")
        self.bad("effective/v0000/sub")

    def test_symlinked_output_rejected_even_with_identical_content(self):
        f = self.eff / "v0000/coverage_summary.json"
        copy = self.t.dir / "elsewhere.json"
        shutil.copy(f, copy)
        f.unlink()
        f.symlink_to(copy)
        self.assertEqual(f.read_text(encoding="utf-8"), copy.read_text(encoding="utf-8"))
        self.bad("effective/v0000/coverage_summary.json")

    def test_symlinked_version_dir_rejected(self):
        real = self.t.dir / "real_v0000"
        shutil.move(str(self.eff / "v0000"), real)
        (self.eff / "v0000").symlink_to(real, target_is_directory=True)
        self.bad("effective/v0000")

    def test_unexpected_effective_unit(self):
        exp = {"v0000": {p.name for p in (PKG / "effective/v0000").iterdir()}}
        self.assertEqual(L.unexpected_effective(self.t.dir, exp), [])
        self.assertEqual(L.unexpected_effective(self.t.dir, {}), ["effective/v0000"])


class C10EffectiveIntegrityReview(C10EffectiveIntegrity):
    """C10 review AL-01, AL-03, AL-04: further strays and layout cases (all inside the temporary Synthetic copy)."""
    def test_hidden_file_rejected(self):
        (self.eff / "v0000/.hidden").write_text("x")
        self.bad("effective/v0000/.hidden")

    def test_hidden_dir_rejected(self):
        (self.eff / ".git_like").mkdir()
        self.bad("effective/.git_like")

    def test_case_variant_file_rejected(self):
        (self.eff / "v0000/Transitions.json").write_text("x")
        self.bad("effective/v0000/Transitions.json")

    def test_trailing_space_file_rejected(self):
        (self.eff / "v0000/transitions.json ").write_text("x")
        self.bad("transitions.json ")

    def test_case_variant_version_dir_rejected(self):
        (self.eff / "V0000").mkdir()
        self.bad("effective/V0000")

    def test_unusual_extension_rejected(self):
        (self.eff / "v0000/payload.bin").write_bytes(b"\0")
        self.bad("effective/v0000/payload.bin")

    def test_empty_stray_dir_rejected(self):
        (self.eff / "empty").mkdir()
        self.bad("effective/empty")

    def test_nested_version_named_dir_rejected(self):
        (self.eff / "v0000/v0000").mkdir()
        self.bad("effective/v0000/v0000")

    def test_fifo_at_expected_name_rejected_without_hanging(self):  # AL-04: walk runs before any read
        f = self.eff / "v0000/transitions.json"
        f.unlink()
        import os
        os.mkfifo(f)
        self.bad("effective/v0000/transitions.json")

    def test_directory_at_expected_name_rejected(self):
        f = self.eff / "v0000/OUTPUT_MANIFEST.json"
        f.unlink()
        f.mkdir()
        self.bad("effective/v0000/OUTPUT_MANIFEST.json")

    def test_symlinked_effective_dir_rejected(self):  # AL-01
        real = self.t.dir / "real_effective"
        shutil.move(str(self.eff), real)
        (self.t.dir / "effective").symlink_to(real, target_is_directory=True)
        self.bad("effective/ is a symbolic link")

    def test_symlinked_ledger_dir_rejected(self):  # AL-01 (pre-existing gap for ledger/)
        real = self.t.dir / "real_ledger"
        shutil.move(str(self.t.dir / "ledger"), real)
        (self.t.dir / "ledger").symlink_to(real, target_is_directory=True)
        self.bad("ledger/ is a symbolic link")

    def test_two_version_expected_set(self):
        names = {p.name for p in (PKG / "effective/v0000").iterdir()}
        shutil.copytree(self.eff / "v0000", self.eff / "v0001")
        self.assertEqual(L.unexpected_effective(self.t.dir, {"v0000": names, "v0001": names}), [])
        (self.eff / "v0001/extra.csv").write_text("x")
        self.assertEqual(L.unexpected_effective(self.t.dir, {"v0000": names, "v0001": names}), ["effective/v0001/extra.csv"])


class C11LedgerFileTypes(C10EffectiveIntegrity):
    """C11 (review CA-01..CA-04 of 2ba7b0a4): ledger and decisions files must be regular files reached without following
    links; FIFOs must never block verify. Every mutation is inside the temporary Synthetic copy; an alarm guards hangs."""
    def setUp(self):
        super().setUp()
        import signal
        self._old = signal.signal(signal.SIGALRM, self._timeout)
        signal.alarm(20)

    def tearDown(self):
        import signal
        signal.alarm(0)
        signal.signal(signal.SIGALRM, self._old)
        super().tearDown()

    @staticmethod
    def _timeout(*_):
        raise AssertionError("verify blocked (timeout): a FIFO or special file was opened for reading")

    def _replace_with_fifo(self, rel):
        import os
        p = self.t.dir / rel
        p.unlink()
        os.mkfifo(p)

    def test_fifo_at_head_rejected_without_hanging(self):
        self._replace_with_fifo("ledger/HEAD")
        self.bad("ledger/HEAD")

    def test_fifo_at_manifest_rejected_without_hanging(self):
        self._replace_with_fifo("ledger/manifest.jsonl")
        self.bad("manifest.jsonl")

    def test_directory_at_head_rejected_not_traceback(self):
        p = self.t.dir / "ledger/HEAD"
        p.unlink()
        p.mkdir()
        self.bad("ledger/HEAD")

    def test_symlinked_head_rejected_even_with_identical_content(self):
        p = self.t.dir / "ledger/HEAD"
        copy = self.t.dir / "head_copy"
        shutil.copy(p, copy)
        p.unlink()
        p.symlink_to(copy)
        self.bad("ledger/HEAD")

    def test_symlinked_manifest_rejected(self):
        p = self.t.dir / "ledger/manifest.jsonl"
        copy = self.t.dir / "manifest_copy"
        shutil.copy(p, copy)
        p.unlink()
        p.symlink_to(copy)
        self.bad("manifest.jsonl")

    def test_stray_fifo_in_decisions_reported(self):
        import os
        os.mkfifo(self.t.dir / "decisions/pipe")
        self.bad("decisions/pipe")

    def test_stray_symlink_in_decisions_reported(self):
        (self.t.dir / "target.md").write_text("x")
        (self.t.dir / "decisions/README.md").symlink_to(self.t.dir / "target.md")
        self.bad("decisions/README.md")

    def test_broken_symlink_in_ledger_reported(self):
        (self.t.dir / "ledger/dangling").symlink_to(self.t.dir / "nowhere")
        self.bad("ledger/dangling")

    def test_directory_symlink_in_ledger_reported(self):
        (self.t.dir / "elsewhere").mkdir()
        (self.t.dir / "ledger/linkdir").symlink_to(self.t.dir / "elsewhere")
        self.bad("ledger/linkdir")

    def test_empty_directory_in_decisions_reported(self):
        (self.t.dir / "decisions/empty").mkdir()
        self.bad("decisions/empty")

    def test_symlinked_decisions_dir_rejected(self):  # CA-03: decisions/ branch of check_ledger_dirs
        real = self.t.dir / "decisions_real"
        (self.t.dir / "decisions").rename(real)
        (self.t.dir / "decisions").symlink_to(real)
        self.bad("decisions/ is a symbolic link")

    def test_decisions_as_file_rejected(self):  # CA-03: non-directory branch
        (self.t.dir / "decisions").rmdir()
        (self.t.dir / "decisions").write_text("x")
        self.bad("decisions is not a directory")

    def test_unexpected_effective_guard_on_symlinked_base(self):  # CA-03: guard inside unexpected_effective itself
        real = self.t.dir / "effective_real"
        self.eff.rename(real)
        self.eff.symlink_to(real)
        self.assertEqual(L.unexpected_effective(self.t.dir, {}), ["effective"])

    def test_absent_decisions_dir_passes_at_version_zero(self):  # CA-04: documented behaviour
        (self.t.dir / "decisions").rmdir()
        self.assertEqual(CLI.verify(self.t.dir), ["v0000 ok"])

    def test_read_regular_bytes_refuses_special_files(self):
        import os
        fifo = self.t.dir / "p"
        os.mkfifo(fifo)
        with self.assertRaisesRegex(common.LedgerError, "not a regular file|cannot open"):
            L.read_regular_bytes(fifo)
        with self.assertRaisesRegex(common.LedgerError, "cannot open|not a regular file"):
            L.read_regular_bytes(self.t.dir)
        with self.assertRaisesRegex(common.LedgerError, "cannot open"):
            L.read_regular_bytes(self.t.dir / "missing")
