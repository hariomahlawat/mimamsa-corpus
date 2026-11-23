#!/usr/bin/env python3
"""Offline tests for build_reconciliation.py. They need the git objects of the pinned commits in the repository that
contains this file (a full clone). Each test builds once and checks an invariant; none writes outside a temp dir."""
import csv, io, json, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_reconciliation as br  # noqa: E402

REPO = str(HERE.parents[3])


def have_commits():
    for c in (br.RAW_DATA_COMMIT, br.REGISTER_COMMIT):
        if subprocess.run(["git", "-C", REPO, "cat-file", "-e", c], capture_output=True).returncode != 0:
            return False
    return True


def rows(text):
    return list(csv.DictReader(io.StringIO(text)))


@unittest.skipUnless(have_commits(), "pinned raw-data / staging commits are not in this clone (fetch origin raw-data)")
class Reconciliation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = br.build(REPO)
        cls.inv = rows(cls.out["UNIFIED_CORPUS_INVENTORY.csv"])
        cls.man = json.loads(cls.out["RECONCILIATION_MANIFEST.json"])

    def test_committed_outputs_reproduce(self):
        for k, v in self.out.items():
            self.assertEqual((br.OUT / k).read_text(encoding="utf-8"), v, k)

    def test_one_row_per_distinct_sha(self):
        shas = [r["sha256"] for r in self.inv]
        self.assertEqual(len(shas), len(set(shas)))
        self.assertTrue(all(len(s) == 64 for s in shas))

    def test_every_github_raw_file_rehashed_and_matches(self):
        s = self.man["summary"]
        self.assertEqual(s["gh_raw_rehash_match"], s["gh_raw_files"])
        self.assertFalse(any(r["gh_byte_verification"] == "REHASHED_MISMATCH" for r in self.inv))

    def test_hf_bytes_never_claimed_verified_by_listing(self):
        for r in self.inv:
            if "hf_data_raw" in r["presence"].lower() or r["hf_paths"].startswith("data/raw/"):
                self.assertNotIn("REHASHED", r["hf_byte_verification"])
        self.assertIn("NOT_CHECKED", self.man["huggingface"]["byte_level_verification"])
        self.assertTrue(self.man["huggingface"]["revision_pinned"].startswith("NO"))

    def test_counts_are_copies_and_add_up(self):
        s = self.man["summary"]
        self.assertEqual(sum(s["presence"].values()), s["distinct_copies"])
        self.assertEqual(sum(s["register_state"].values()), s["distinct_copies"])

    def test_registered_copies_all_present_and_never_unregistered(self):
        reg = {r["sha256"] for r in self.inv if r["register_state"] == "REGISTERED"}
        c5 = br.rcsv_bytes(br.Git(REPO).show(br.REGISTER_COMMIT, br.REG["copy_register"]))
        self.assertTrue({c["sha256"] for c in c5} <= reg)

    def test_working_store_only_copies_listed_as_missing_evidence(self):
        ws = {r["sha256"] for r in self.inv if r["presence"] == "C5_WORKING_STORE_ONLY_NOT_IN_HF_OR_GITHUB"}
        miss = {r["sha256"] for r in rows(self.out["MISSING_SOURCE_EVIDENCE.csv"]) if r["kind"] == "REGISTERED_COPY_BYTES_NOT_IN_CANONICAL_STORE"}
        self.assertEqual(ws, miss)

    def test_anchor_copy_preservation_gap_is_reported(self):
        anchor = [r for r in self.inv if r["sha256"].startswith("c5ef95a9")]
        self.assertEqual(len(anchor), 1)
        self.assertEqual(anchor[0]["presence"], "C5_WORKING_STORE_ONLY_NOT_IN_HF_OR_GITHUB")
        self.assertGreater(int(anchor[0]["kb_exact_anchor_rows"]), 0)

    def test_authentication_never_asserted(self):
        self.assertEqual({r["authentication_state"] for r in self.inv}, {"NOT_AUTHENTICATED_BY_THIS_RECONCILIATION"})

    def test_equivalence_same_bytes_groups_have_single_sha(self):
        for r in rows(self.out["COPY_EQUIVALENCE_REGISTER.csv"]):
            if r["classification"] == "SAME_BYTES_SAME_DOCUMENT":
                self.assertNotIn(";", r["sha256s"])
            else:
                self.assertIn(";", r["sha256s"])

    def test_manifest_pins_inputs_and_outputs(self):
        self.assertEqual(self.man["github"]["raw_data_commit"], br.RAW_DATA_COMMIT)
        for k, v in self.out.items():
            if k != "RECONCILIATION_MANIFEST.json":
                import hashlib
                self.assertEqual(self.man["outputs"][k], hashlib.sha256(v.encode()).hexdigest())
        self.assertIn("lk_declared_sidecars.tsv", self.man["hf_snapshot_inputs"])


class SnapshotGuards(unittest.TestCase):
    """The builder must fail closed on a damaged HF snapshot; these run on a copy of the snapshot folder."""
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        shutil.copytree(br.SNAP, self.tmp / "hf_snapshot")
        self.orig = br.SNAP
        br.SNAP = self.tmp / "hf_snapshot"

    def tearDown(self):
        br.SNAP = self.orig
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_truncated_marker_fails_closed(self):
        with open(br.SNAP / "listing_sci.tsv", "a", encoding="utf-8") as f:
            f.write("TRUNCATED\t0\t0\tdata/raw/sci\n")
        with self.assertRaises(SystemExit):
            br.load_hf_listing()

    def test_conflicting_duplicate_path_fails_closed(self):
        line = (br.SNAP / "listing_sci.tsv").read_text(encoding="utf-8").splitlines()[0].split("\t")
        line[1] = str(int(line[1]) + 1)
        with open(br.SNAP / "listing_extra.tsv", "w", encoding="utf-8") as f:
            f.write("\t".join(line) + "\n")
        with self.assertRaises(SystemExit):
            br.load_hf_listing()

    def test_listing_loads(self):
        files, used = br.load_hf_listing()
        self.assertGreater(len(files), 4000)
        self.assertIn("listing_sci.tsv", used)



@unittest.skipUnless(have_commits(), "pinned raw-data / staging commits are not in this clone")
class DatasetIntegrity(unittest.TestCase):
    def test_integrity_outputs_reproduce_and_raw_hashes_match(self):
        import check_dataset_integrity as ci
        out = ci.run(REPO)
        for k, v in out.items():
            self.assertEqual((ci.OUT / k).read_text(encoding="utf-8"), v, k)
        summ = {r["item"]: r["value"] for r in rows(out["DATASET_INTEGRITY_SUMMARY.csv"])}
        self.assertEqual(summ["raw_files_rehashed_equal_to_SHA256SUMS"], summ["raw_files"])
        self.assertNotIn("issue:META_SCHEMA", summ)
        self.assertNotIn("issue:SHA256SUMS_MISMATCH", summ)


if __name__ == "__main__":
    unittest.main()
