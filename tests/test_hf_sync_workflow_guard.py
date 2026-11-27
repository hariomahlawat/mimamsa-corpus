"""HF sync safeguard: prove that ordinary pushes and unapproved dispatches cannot run the general corpus upload,
that source-acquisition scripts need their own approval, and that the abbreviation upload stays separately controlled.
Offline. Evaluates the workflow's own `if:` expressions for simulated events (minimal GitHub-expression evaluator)."""
import re
import unittest
from pathlib import Path

import yaml

WF = Path(__file__).resolve().parent.parent / ".github" / "workflows" / "sync-legal-knowledge-hf.yml"
CORPUS_PHRASE = "I-APPROVE-CORPUS-UPLOAD"
ACQ_PHRASE = "I-APPROVE-SOURCE-ACQUISITION"
ACQ_SCRIPT = re.compile(r"(?m)^\s*python\s+scripts/(archive_|acquire_|probe_)[a-z0-9_]+\.py")  # execution, not py_compile
UPLOAD_SCRIPTS = re.compile(r"scripts/(push_legal_knowledge|push_mml_originals)\.py")


def load():
    return yaml.safe_load(WF.read_text(encoding="utf-8"))


def evaluate(expr, event, inputs=None, message="", files_present=False):
    """Evaluate a GitHub Actions `if:` expression for the constructs used in this workflow."""
    if expr is None:
        return True
    e = expr.strip()
    if e.startswith("${{") and e.endswith("}}"):
        e = e[3:-2].strip()
    inputs = inputs or {}
    e = re.sub(r"contains\(\s*github\.event\.head_commit\.message\s*,\s*('[^']*')\s*\)", r"(\1 in _msg)", e)
    e = re.sub(r"hashFiles\([^)]*\)", "_hash", e)
    e = re.sub(r"inputs\.([A-Za-z0-9_]+)", r"_inputs.get('\1', '')", e)
    e = e.replace("github.event_name", "_event")
    e = e.replace("&&", " and ").replace("||", " or ")
    e = re.sub(r"!(?!=)", " not ", e)
    if re.search(r"github\.|secrets\.|vars\.", e):
        raise AssertionError(f"unsupported construct in expression: {expr}")
    return bool(eval(e, {"__builtins__": {}}, {"_msg": message, "_hash": "abc" if files_present else "",
                                              "_inputs": inputs, "_event": event}))


def steps_running(job, **ctx):
    return [s for s in job["steps"] if evaluate(s.get("if"), **ctx)]


class HFSyncGuard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.wf = load()
        cls.on = cls.wf[True] if True in cls.wf else cls.wf["on"]
        cls.upload = cls.wf["jobs"]["upload"]
        cls.abbr = cls.wf["jobs"]["upload_abbreviations"]

    def test_triggers_are_push_and_dispatch_only(self):
        self.assertEqual(set(self.on), {"push", "workflow_dispatch"})
        self.assertNotIn("pull_request", self.on)
        self.assertNotIn("pull_request_target", self.on)

    def test_dispatch_inputs_default_to_no(self):
        inputs = self.on["workflow_dispatch"]["inputs"]
        self.assertEqual(inputs["approve_corpus_upload"]["default"], "no")
        self.assertEqual(inputs["run_source_acquisition"]["default"], "no")

    def test_ordinary_push_runs_nothing(self):
        for msg in ("Integrate audit work", "Merge pull request #6", "[skip ci] merge", ""):
            self.assertFalse(evaluate(self.upload["if"], event="push", message=msg), msg)
            self.assertFalse(evaluate(self.abbr["if"], event="push", message=msg), msg)

    def test_push_with_abbreviation_tag_runs_only_abbreviations(self):
        msg = "[abbreviations-hf] Upload lexicon"
        self.assertFalse(evaluate(self.upload["if"], event="push", message=msg))
        self.assertTrue(evaluate(self.abbr["if"], event="push", message=msg))

    def test_dispatch_without_or_with_wrong_approval_cannot_upload(self):
        for val in ("no", "", "yes", "i-approve-corpus-upload", CORPUS_PHRASE + " ", "APPROVE"):
            self.assertFalse(evaluate(self.upload["if"], event="workflow_dispatch",
                                      inputs={"approve_corpus_upload": val}), repr(val))
        self.assertFalse(evaluate(self.abbr["if"], event="workflow_dispatch",
                                  inputs={"approve_corpus_upload": CORPUS_PHRASE}))

    def test_approved_dispatch_runs_upload_job(self):
        self.assertTrue(evaluate(self.upload["if"], event="workflow_dispatch",
                                 inputs={"approve_corpus_upload": CORPUS_PHRASE}))

    def test_other_events_cannot_upload(self):
        for ev in ("pull_request", "pull_request_target", "schedule", "repository_dispatch", "workflow_run"):
            self.assertFalse(evaluate(self.upload["if"], event=ev, inputs={"approve_corpus_upload": CORPUS_PHRASE}), ev)

    def test_upload_job_has_environment_gate_and_refusal_first_step(self):
        self.assertEqual(self.upload.get("environment"), "hf-corpus-upload")
        first = self.upload["steps"][0]
        self.assertIn("Refuse", first["name"])
        script = first["run"]
        self.assertIn('"$EVENT_NAME" != "workflow_dispatch"', script)
        self.assertIn(CORPUS_PHRASE, script)
        self.assertIn("exit 1", script)
        self.assertNotIn("continue-on-error", first)

    def test_every_acquisition_step_requires_its_own_approval(self):
        acq = [s for s in self.upload["steps"] if ACQ_SCRIPT.search(str(s.get("run", "")))]
        self.assertGreaterEqual(len(acq), 10)
        approved = {"approve_corpus_upload": CORPUS_PHRASE}
        running = steps_running(self.upload, event="workflow_dispatch", inputs=approved)
        for s in acq:
            self.assertNotIn(s, running, s["name"])
        both = dict(approved, run_source_acquisition=ACQ_PHRASE)
        running = steps_running(self.upload, event="workflow_dispatch", inputs=both)
        for s in acq:
            self.assertIn(s, running, s["name"])

    def test_no_acquisition_or_corpus_upload_in_abbreviation_job(self):
        for s in self.abbr["steps"]:
            run = str(s.get("run", ""))
            self.assertIsNone(ACQ_SCRIPT.search(run), s.get("name"))
            self.assertIsNone(UPLOAD_SCRIPTS.search(run), s.get("name"))

    def test_corpus_upload_scripts_only_inside_guarded_job(self):
        for name, job in self.wf["jobs"].items():
            for s in job["steps"]:
                if UPLOAD_SCRIPTS.search(str(s.get("run", ""))):
                    self.assertEqual(name, "upload", s.get("name"))

    def test_no_job_continues_on_error(self):
        for name, job in self.wf["jobs"].items():
            self.assertFalse(job.get("continue-on-error", False), name)


if __name__ == "__main__":
    unittest.main()
