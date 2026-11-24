#!/usr/bin/env python3
"""SYNTHETIC first-transaction demonstration of the Project Mimamsa AUTH-LEDGER (offline, deterministic).

Nothing here is an approval. Every decision (D-) and review (R-) record written by this script is SYNTHETIC, lives only
in a temporary git repository created under TXN-DEMO/work/, and is deleted at the end of the run. The real ledger is only READ
(its package code, schema, frozen pins, genesis line and pinned input files are copied); it stays at version 0.

What the script does, through the REAL AUTH-LEDGER code copied from --source:
  0. builds a temporary repository with the real layout legal_knowledge/audit_work/AUTH-LEDGER (+ every pinned input file),
     commits it as genesis and verifies it with the real command-line tool (HEAD must equal the real genesis HEAD);
  a. version 1: a proposed ADD of two real C6-01 draft rows, labelled SYNTHETIC, with synthetic D-/R- records, on a PR
     branch merged with --no-ff; the version is shown PENDING_REPOSITORY_BINDING and changes no register;
  b. version 2: a BIND line in a later PR; verify; the version is APPLIED and the effective state changes;
  c. historical reproduction: build --as-of 0, 1, 2 (and every later version) and their hashes;
  d. CORRECTION (version 3) + BIND (version 4);
  e. WITHDRAW (version 5) + BIND (version 6);
  f. re-authentication after the withdrawal: new ADD (version 7) + BIND (version 8);
  g. negative cases, each in a fresh clone: owner record naming an AI agent; decision before review; unbound version
     followed by another entry version; tampered pinned record; BIND naming a fast-forward; WITHDRAW of a CORRECTION.
The CLI (auth_ledger.py verify / build --as-of N) is invoked by its absolute path inside the temporary repository, so the
tool treats that package as the committed ledger (COMMITTED_PACKAGE, layout check, pinned repository top).

Usage:
  synthetic_transaction_demo.py [--source REPO]            run, write TXN-DEMO/TRANSCRIPT.md and TXN-DEMO/expected_hashes.json
  synthetic_transaction_demo.py --check [--source REPO]    run, compare with expected_hashes.json and TRANSCRIPT.md
Options: --keep (do not delete the temporary repository), --work DIR (parent for the temporary directory)."""
import argparse, csv, hashlib, importlib, io, json, os, re, shutil, subprocess, sys, tempfile
from pathlib import Path

TXN = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = TXN.parents[3]  # repository root that contains this TXN-DEMO folder
PKG_REL = "legal_knowledge/audit_work/AUTH-LEDGER"
CLI_REL = PKG_REL + "/tools/auth_ledger.py"
REAL_GENESIS_HEAD = "0 443c4bdf348b2a1bcd603d2701f097aa90a8155efd43c10760f5fd86c76c6b6b"
DATE = "2026-11-23"
OWNER = "SYNTHETIC OWNER (test)"
REVIEWER = "SYNTHETIC REVIEWER (test)"
REPOSITORY = "synthetic/mimamsa-demo"
REVIEW_LOGIN = "synthetic-reviewer"
DHARAMVIR_PREFIX, GAZETTE_PREFIX = "3056712c", "b76bf4aa"
NOTICE = ("# SYNTHETIC TEST RECORD. Demonstration only, in a temporary repository that is deleted after the run.\n"
          "# It is not an owner decision, not an approval and not a review of any real ledger version.\n")
sys.dont_write_bytecode = True


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha256_text(s):
    return sha256_bytes(s.encode("utf-8"))


class Demo:
    def __init__(self, source, work_parent):
        self.source = Path(source).resolve()
        self.work_parent = Path(work_parent).resolve()
        self.work_parent.mkdir(parents=True, exist_ok=True)
        self.tmp = Path(tempfile.mkdtemp(prefix="txn_", dir=str(self.work_parent))).resolve()
        assert str(self.tmp).startswith(str(self.work_parent) + os.sep), "temporary directory escaped the work folder"
        self.gitcfg = self.tmp / "empty_gitconfig"
        self.gitcfg.write_text("", encoding="utf-8")
        self.tick = 0
        self.steps = []          # transcript: list of dicts
        self.expected = {}       # key -> value for --check
        self.failures = []       # assertion failures (demo-level)
        self.findings = []       # unexpected behaviour of the AUTH-LEDGER code

    # ------------------------------------------------------------------ git / cli helpers
    def git_env(self):
        env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        self.tick += 1
        stamp = f"{DATE}T09:{self.tick // 60:02d}:{self.tick % 60:02d}+0000"
        env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=str(self.gitcfg), GIT_AUTHOR_NAME="SYNTHETIC DEMO",
                   GIT_AUTHOR_EMAIL="synthetic-demo@example.invalid", GIT_COMMITTER_NAME="SYNTHETIC DEMO",
                   GIT_COMMITTER_EMAIL="synthetic-demo@example.invalid", GIT_AUTHOR_DATE=stamp, GIT_COMMITTER_DATE=stamp,
                   GIT_TERMINAL_PROMPT="0", TZ="UTC", LC_ALL="C")
        return env

    def git(self, top, *args, check=True):
        p = subprocess.run(["git", "-c", "commit.gpgsign=false", "-c", "core.autocrlf=false", "-c", "protocol.allow=never",
                            "-C", str(top), *args], capture_output=True, env=self.git_env(), text=True)
        if check and p.returncode != 0:
            raise RuntimeError(f"git {' '.join(args)} failed: {p.stderr.strip()}")
        return p.stdout.strip()

    def commit(self, top, msg):
        self.git(top, "add", "-A")
        self.git(top, "commit", "-q", "--allow-empty", "-m", msg)
        return self.git(top, "rev-parse", "HEAD")

    def cli(self, top, *args):
        """Run the REAL command-line tool of the temporary package by its absolute path (cwd = repository top)."""
        env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        env.update(PYTHONDONTWRITEBYTECODE="1", PWD=str(top), LC_ALL="C")
        p = subprocess.run([sys.executable, "-B", str(Path(top) / CLI_REL), *args], cwd=str(top), capture_output=True, text=True, env=env)
        return p.returncode, self.clean(p.stdout), self.clean(p.stderr)

    def clean(self, s):
        return s.replace(str(self.tmp), "$WORK").strip()

    # ------------------------------------------------------------------ transcript helpers
    def step(self, sid, title):
        self.cur = {"id": sid, "title": title, "items": []}
        self.steps.append(self.cur)
        print(f"\n== {sid}: {title}")

    def note(self, text):
        self.cur["items"].append(("note", text))
        print("   " + text)

    def run(self, top, label, *args, expect_ok=True, expect_err=None, key=None):
        rc, out, err = self.cli(top, *args)
        cmd = "python " + CLI_REL + " " + " ".join(a if not a.startswith(str(self.tmp)) else self.clean(a) for a in args)
        ok = (rc == 0) if expect_ok else (rc == 2 and (expect_err is None or re.search(expect_err, err)))
        self.cur["items"].append(("cmd", cmd, rc, out, err, "PASS" if ok else "FAIL"))
        print(f"   $ {cmd}\n     rc={rc} {out[-300:]} {err[-400:]} -> {'PASS' if ok else 'FAIL'}")
        if not ok:
            self.failures.append(f"{self.cur['id']} {label}: rc={rc} out={out[-200:]} err={err[-300:]}")
        if key:
            self.rec(key, {"rc": rc, "stdout": out, "stderr": err})
        return rc, out, err

    def rec(self, key, value):
        if key in self.expected:
            raise RuntimeError(f"duplicate expected key {key}")
        self.expected[key] = value

    def check(self, cond, what):
        self.cur["items"].append(("check", what, "PASS" if cond else "FAIL"))
        print(f"   [{'PASS' if cond else 'FAIL'}] {what}")
        if not cond:
            self.failures.append(f"{self.cur['id']}: {what}")

    # ------------------------------------------------------------------ repository construction
    def build_repo(self, name="repo"):
        top = self.tmp / name
        pkg_src = self.source / PKG_REL
        top.mkdir()
        pins = json.loads((pkg_src / "frozen_inputs.json").read_text(encoding="utf-8"))["files"]
        files = list(pins)
        for sub in ("tools", "schema"):
            files += [f"{PKG_REL}/{sub}/{p.name}" for p in sorted((pkg_src / sub).iterdir()) if p.is_file() and p.suffix in (".py", ".json")]
        files += [f"{PKG_REL}/{x}" for x in ("frozen_inputs.json", "ledger/manifest.jsonl", "ledger/HEAD", "decisions/README.md",
                                             "evidence/EVIDENCE_PROVENANCE.json")]
        files += [f"{PKG_REL}/effective/v0000/{p.name}" for p in sorted((pkg_src / "effective/v0000").iterdir()) if p.is_file()]
        for rel in sorted(set(files)):
            dst = top / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes((self.source / rel).read_bytes())
            os.chmod(dst, 0o644)
        (top / "SYNTHETIC_DEMO_README.txt").write_text(
            "SYNTHETIC AUTH-LEDGER transaction demonstration repository (temporary).\n"
            "Every decision and review record in it is synthetic. Nothing here approves anything.\n", encoding="utf-8")
        tmpl = self.tmp / "empty_template"
        tmpl.mkdir(exist_ok=True)
        self.git(top, "init", "-q", "-b", "main", f"--template={tmpl}")
        (top / ".git/info").mkdir(exist_ok=True)
        (top / ".git/info/exclude").write_text("__pycache__/\n*.pyc\n", encoding="utf-8")
        return top, len(pins), len(set(files))

    def load_package(self, top):
        """Import the REAL tools from the temporary package (helpers only: entry_digest, canonical_line, COLS, locator)."""
        tools = str(top / PKG_REL / "tools")
        for m in ("common", "ledger", "pins", "reader", "rules_v1", "strength", "binding", "urlcheck", "auth_ledger"):
            sys.modules.pop(m, None)
        sys.path.insert(0, tools)
        self.L = importlib.import_module("ledger")
        self.common = importlib.import_module("common")
        self.strength = importlib.import_module("strength")
        assert Path(self.common.PKG) == (top / PKG_REL).resolve(), "tools imported from the wrong package"
        aw = self.source / "legal_knowledge/audit_work"
        self.draft = {r["sha256"]: r for r in self.common.read_csv(aw / "C6-01-PROVENANCE/addendum/authentication_addendum_v1_draft.csv")}
        self.c5copy = {r["sha256"]: r for r in self.common.read_csv(top / "legal_knowledge/audit_work/SOURCE-LIBRARY-C5/registers/source_copy_register.csv")}

    def sha_of(self, prefix):
        hits = [s for s in self.draft if s.startswith(prefix)]
        assert len(hits) == 1, prefix
        return hits[0]

    def entry_from_draft(self, sha, n, version, **over):
        """A ledger entry from a real C6-01 draft row (same conversion as the test fixture), labelled SYNTHETIC."""
        d = self.draft[sha]
        e = {k: "" for k in self.L.COLS}
        e.update({"entry_id": f"AL-v{version:04d}-{n:03d}", "entry_version": f"{version:04d}", "entry_type": "ADD", "sha256": sha,
                  "source_id": d["source_id"], "copy_id": d["copy_id"], "document_identity": d["document_identity"],
                  "evidence_refs": d["evidence_refs"], "first_class_record_ref": d["first_class_record_ref"],
                  "identity_refs": d["identity_refs"].replace("T:C6-01-PROVENANCE/inputs/held_copy_facts.csv#", "T:AUTH-LEDGER/evidence/copy_facts.csv#"),
                  "proposed_authentication_state": "PROVENANCE_DOCUMENTED", "proposed_class": d["proposed_class"],
                  "carrier": self.c5copy[sha]["copy_carrier_provenance"],
                  "official_locator_recorded": self.strength._first_class(d["first_class_record_ref"], sha)[2],
                  "limitations": "SYNTHETIC DEMONSTRATION ENTRY. " + d["limitations"],
                  "justification": f"SYNTHETIC DEMONSTRATION ENTRY built from C6-01 draft row {d['entry_id']}; not an approval. {d['justification']}",
                  "rule_version": "1", "owner_decision": "APPROVED"})
        e.update(over)
        return e

    def withdraw_entry(self, sha, n, version, target, reason, resulting):
        return self.entry_from_draft(sha, n, version, entry_type="WITHDRAW", target_entry_id=target, withdrawal_reason=reason,
                                     resulting_state=resulting, first_class_record_ref="", proposed_authentication_state="",
                                     proposed_class="", justification=f"SYNTHETIC DEMONSTRATION WITHDRAWAL of {target} ({reason}); not a real finding")

    # ------------------------------------------------------------------ ledger writing (file layer only; validation is the real code's)
    def pkg(self, top):
        return top / PKG_REL

    def manifest_lines(self, top):
        return [json.loads(x) for x in (self.pkg(top) / "ledger/manifest.jsonl").read_text(encoding="utf-8").splitlines()]

    def append_line(self, top, line):
        s = self.L.canonical_line(line)
        p = self.pkg(top)
        with open(p / "ledger/manifest.jsonl", "a", encoding="utf-8") as fh:
            fh.write(s + "\n")
        (p / "ledger/HEAD").write_text(f"{line['version']} {sha256_text(s)}\n", encoding="utf-8")

    def replace_last_line(self, top, line):
        p = self.pkg(top)
        raw = (p / "ledger/manifest.jsonl").read_text(encoding="utf-8").split("\n")[:-1]
        raw[-1] = self.L.canonical_line(line)
        (p / "ledger/manifest.jsonl").write_text("\n".join(raw) + "\n", encoding="utf-8")
        (p / "ledger/HEAD").write_text(f"{line['version']} {sha256_text(raw[-1])}\n", encoding="utf-8")

    def write_record(self, top, name, fields):
        body = NOTICE + "".join(f"{k}: {v}\n" for k, v in fields)
        f = self.pkg(top) / "decisions" / name
        f.write_text(body, encoding="utf-8")
        return f"decisions/{name}", sha256_bytes(f.read_bytes())

    def record_version(self, top, entries, decided_by=OWNER, reviewer=REVIEWER, dec_date=DATE, rev_date=DATE, note="", finalize=True):
        lines = self.manifest_lines(top)
        v = len(lines)
        pairs = ";".join(f"{e['entry_id']}={e['sha256']}:{self.L.entry_digest(e)}" for e in entries)
        dref, dh = self.write_record(top, f"D-v{v:04d}.md", [
            ("decision_id", f"D-v{v:04d}"), ("decision", "APPROVED"), ("ledger_version", f"{v:04d}"), ("entries", pairs),
            ("decided_by", decided_by), ("date", dec_date), ("scope", "AUTHENTICATION_PROVENANCE_ONLY"), ("legal_approval", "NOT_GIVEN"),
            ("synthetic_notice", "SYNTHETIC demonstration record; approves nothing")])
        rref, rh = self.write_record(top, f"R-v{v:04d}.md", [
            ("review_id", f"R-v{v:04d}"), ("verdict", "ACCEPT"), ("ledger_version", f"{v:04d}"), ("entries", pairs),
            ("reviewer", reviewer), ("date", rev_date), ("scope", "TECHNICAL_AND_EVIDENCE_REVIEW"), ("legal_approval", "NOT_GIVEN"),
            ("synthetic_notice", "SYNTHETIC demonstration record; reviews nothing real")])
        for e in entries:
            e["decision_record_ref"], e["decision_record_sha256"] = dref, dh
            e["reviewer_ref"], e["reviewer_record_sha256"] = rref, rh
        f = f"ledger/v{v:04d}.csv"
        (self.pkg(top) / f).write_text(self.common.csv_text(self.L.COLS, entries), encoding="utf-8")
        prev = sha256_text(self.L.canonical_line(lines[-1]))
        line = {"version": v, "prev": prev, "date": DATE, "rule_version": 1,
                "frozen_inputs_sha256": sha256_bytes((self.pkg(top) / "frozen_inputs.json").read_bytes()), "file": f,
                "file_sha256": sha256_bytes((self.pkg(top) / f).read_bytes()), "decisions": {dref: dh}, "reviews": {rref: rh},
                "effective_sha256": "", "note": "SYNTHETIC DEMONSTRATION VERSION. " + note}
        self.append_line(top, line)
        if finalize:
            self.finalize(top, v)
        return v

    def add_bind(self, top, head, merge, pr_number, review_id, finalize=True, **over):
        lines = self.manifest_lines(top)
        v = len(lines)
        b = {"binds_version": v - 1, "bound_line_sha256": sha256_text(self.L.canonical_line(lines[-1])), "repository": REPOSITORY,
             "pr_number": pr_number, "reviewed_head": head, "merge_commit": merge, "github_review_id": review_id,
             "github_review_login": REVIEW_LOGIN, "github_review_commit": head}
        b.update(over)
        line = {"version": v, "prev": sha256_text(self.L.canonical_line(lines[-1])), "date": DATE, "rule_version": 1,
                "frozen_inputs_sha256": sha256_bytes((self.pkg(top) / "frozen_inputs.json").read_bytes()), "file": None, "file_sha256": None,
                "decisions": {}, "reviews": {}, "effective_sha256": "",
                "note": f"SYNTHETIC DEMONSTRATION BIND of version {v - 1} (PR and review values are invented)", "binding": b}
        self.append_line(top, line)
        if finalize:
            self.finalize(top, v)
        return v

    def finalize(self, top, v):
        """Pin effective_sha256 the way genesis does: build the version with the REAL CLI, then record the output manifest
        hash in the manifest line and commit the outputs as effective/vNNNN."""
        out = self.tmp / f"fin_{top.name}_{v}"
        rc, o, err = self.cli(top, "build", "--as-of", str(v), "--out", str(out))
        if rc != 0:
            raise RuntimeError(f"build of version {v} failed while pinning: {err}")
        line = self.manifest_lines(top)[-1]
        line["effective_sha256"] = sha256_bytes((out / "OUTPUT_MANIFEST.json").read_bytes())
        self.replace_last_line(top, line)
        d = self.pkg(top) / f"effective/v{v:04d}"
        shutil.copytree(out, d)
        shutil.rmtree(out)

    def pr(self, top, branch, build, pr_number, title):
        """Create a PR branch from main, let build() write a version, commit, and merge with --no-ff. Returns (head, merge)."""
        self.git(top, "checkout", "-q", "-b", branch)
        build()
        head = self.commit(top, f"SYNTHETIC {title}")
        self.git(top, "checkout", "-q", "main")
        self.git(top, "merge", "-q", "--no-ff", "-m", f"Merge pull request #{pr_number} from {branch} (SYNTHETIC)", branch)
        merge = self.git(top, "rev-parse", "HEAD")
        return head, merge

    def built(self, top, v):
        out = self.tmp / f"asof_{top.name}_{v}"
        shutil.rmtree(out, ignore_errors=True)
        rc, o, err = self.cli(top, "build", "--as-of", str(v), "--out", str(out))
        if rc != 0:
            raise RuntimeError(f"build --as-of {v}: {err}")
        texts = {p.name: p.read_text(encoding="utf-8") for p in sorted(out.iterdir())}
        shutil.rmtree(out)
        return texts

    # ------------------------------------------------------------------ effective-state description
    @staticmethod
    def rows(text):
        return list(csv.DictReader(io.StringIO(text)))

    def describe(self, texts):
        tr = json.loads(texts["transitions.json"])
        return {"effective_sha256": sha256_text(texts["OUTPUT_MANIFEST.json"]),
                "files": {k: sha256_text(v) for k, v in sorted(texts.items()) if k != "OUTPUT_MANIFEST.json"},
                "transitions": [{k: t.get(k, "") for k in ("version", "entry_id", "entry_type", "effect", "before", "after", "bound_by")}
                                for t in tr],
                "newly_withdrawn": [w["entry_id"] for w in json.loads(texts["newly_withdrawn.json"])]}

    def diff(self, a, b):
        out = []
        sa = {r["source_id"]: r for r in self.rows(a["source_states.csv"])}
        for r in self.rows(b["source_states.csv"]):
            x = sa[r["source_id"]]
            if x["effective_holding_state"] != r["effective_holding_state"]:
                out.append(f"source {r['source_id']}: {x['effective_holding_state']} -> {r['effective_holding_state']} ({r['basis']})")
        ca = {r["copy_id"]: r for r in self.rows(a["source_copy_register.csv"])}
        for r in self.rows(b["source_copy_register.csv"]):
            x = ca[r["copy_id"]]
            if x["copy_effective_status"] != r["copy_effective_status"] or x["c4_effective_source_class"] != r["c4_effective_source_class"]:
                out.append(f"copy {r['copy_id']}: {x['copy_effective_status']}/{x['c4_effective_source_class'] or '-'} -> "
                           f"{r['copy_effective_status']}/{r['c4_effective_source_class'] or '-'}")
        key = lambda r: (r["source_id"], r["provision_id"], r["knowledge_base_record_id"], r["case_id"], r["relationship_type"])
        xa = {}
        for r in self.rows(a["corpus_crosswalk.csv"]):
            xa.setdefault(key(r), []).append(r["evidence_status"])
        xb = {}
        for r in self.rows(b["corpus_crosswalk.csv"]):
            xb.setdefault(key(r), []).append(r["evidence_status"])
        for k in sorted(set(xa) | set(xb)):
            if xa.get(k) != xb.get(k):
                label = k[3] or k[2] or k[1] or k[0]
                out.append(f"crosswalk {k[0]} {label}: {','.join(xa.get(k, ['-']))} -> {','.join(xb.get(k, ['-']))}")
        for k in ("source_master_register.csv", "coverage_summary.json"):
            if a[k] != b[k]:
                out.append(f"{k} changed")
        return out or ["no register change"]

    # ------------------------------------------------------------------ the demonstration
    def main_sequence(self):
        self.step("0", "Temporary repository with the real package layout; genesis; verify")
        top, npins, nfiles = self.build_repo()
        self.top = top
        self.load_package(top)
        self.note(f"copied {nfiles} files from the source repository (package tools/schema/genesis/effective v0000 + {npins} pinned input files)")
        # The tools tree id, not the commit id, is recorded, so --check stays stable when unrelated files move (C9).
        src_tree = subprocess.run(["git", "-C", str(self.source), "rev-parse", "HEAD:" + PKG_REL + "/tools"], capture_output=True,
                                  text=True, env={k: v for k, v in os.environ.items() if not k.startswith("GIT_")}).stdout.strip()
        self.note(f"source AUTH-LEDGER tools tree {src_tree}")
        self.rec("source_package_tools_sha256", {p.name: sha256_bytes(p.read_bytes())
                                                 for p in sorted((self.source / PKG_REL / "tools").glob("*.py"))})
        g = self.commit(top, "SYNTHETIC genesis: copy of the AUTH-LEDGER package at version 0 and its pinned inputs")
        self.rec("commit.genesis", g)
        self.run(top, "verify genesis", "verify", key="cli.verify.v0")
        head0 = (self.pkg(top) / "ledger/HEAD").read_text(encoding="utf-8").strip()
        self.check(head0 == REAL_GENESIS_HEAD, f"temporary ledger HEAD equals the real genesis HEAD ({head0})")
        texts = {0: self.built(top, 0)}
        self.check(all(texts[0][k] == (self.source / PKG_REL / "effective/v0000" / k).read_text(encoding="utf-8")
                       for k in texts[0]), "build --as-of 0 equals the committed effective/v0000 of the real ledger")

        D = self.sha_of(DHARAMVIR_PREFIX)
        G = self.sha_of(GAZETTE_PREFIX)
        self.D, self.G = D, G

        # a. proposed ADD
        self.step("a", "Version 1: proposed ADD (two real C6-01 draft rows, SYNTHETIC records) on a PR branch, merged with --no-ff")
        v1 = [self.entry_from_draft(D, 1, 1), self.entry_from_draft(G, 2, 1)]
        self.note("AL-v0001-001 ADD Dharamvir Singh (SC 2013) copy, class PRIMARY_OFFICIAL_COURT_COPY, from draft C6-ADD-v1-3056712c")
        self.note("AL-v0001-002 ADD Army Rules amendment Gazette S.R.O. 1 (1962) copy, class PRIMARY_GAZETTE_ARCHIVAL_FACSIMILE, from draft C6-ADD-v1-b76bf4aa")
        self.note(f"records: decisions/D-v0001.md (decided_by: {OWNER}), decisions/R-v0001.md (reviewer: {REVIEWER}); "
                  "scope and legal_approval: NOT_GIVEN lines present")
        h1, m1 = self.pr(top, "pr/9001-v0001-add", lambda: self.record_version(top, v1, note="proposed ADD"), 9001, "v0001: proposed ADD")
        self.rec("commit.v0001.reviewed_head", h1)
        self.rec("commit.v0001.merge", m1)
        self.note(f"reviewed_head {h1}; merge_commit {m1} (parents: {' '.join(self.git(top, 'rev-list', '--parents', '-n', '1', m1).split()[1:])})")
        self.run(top, "verify v1 pending", "verify", key="cli.verify.v1")
        texts[1] = self.built(top, 1)
        d1 = self.describe(texts[1])
        self.check([t["effect"] for t in d1["transitions"]] == ["PENDING_REPOSITORY_BINDING"] * 2,
                   "transitions at version 1: both entries PENDING_REPOSITORY_BINDING")
        self.check(all(texts[1][k] == texts[0][k] for k in ("source_copy_register.csv", "source_master_register.csv",
                                                            "corpus_crosswalk.csv", "coverage_summary.json", "source_states.csv")),
                   "registers, crosswalk, coverage and source states at version 1 are byte-identical to version 0 (nothing effective yet)")
        self.note("effective-state change 0 -> 1: " + "; ".join(self.diff(texts[0], texts[1])))

        # b. BIND
        self.step("b", "Version 2: BIND line in a later PR; verify; APPLIED")
        hb, mb = self.pr(top, "pr/9002-v0002-bind", lambda: self.add_bind(top, h1, m1, 9001, 900001), 9002, "v0002: BIND version 1")
        self.note(f"BIND PR head {hb}; merge {mb}; the BIND line names reviewed_head {h1[:12]} and merge_commit {m1[:12]}")
        self.rec("commit.v0002.head", hb)
        self.rec("commit.v0002.merge", mb)
        self.run(top, "verify v2", "verify", key="cli.verify.v2")
        texts[2] = self.built(top, 2)
        d2 = self.describe(texts[2])
        self.check([(t["effect"], t["bound_by"]) for t in d2["transitions"]] == [("APPLIED", 2)] * 2,
                   "transitions at version 2: both entries APPLIED, bound_by 2")
        tr2 = json.loads(texts[2]["transitions.json"])
        self.note("binding_assurance: " + tr2[0].get("binding_assurance", "(missing)"))
        self.check(tr2[0].get("binding_assurance", "").startswith("git topology VERIFIED_OFFLINE; GitHub review ASSERTED_NOT_VERIFIED_OFFLINE"),
                   "the GitHub review is reported as asserted, not verified")
        chg = self.diff(texts[1], texts[2])
        self.note("effective-state change 1 -> 2: " + "; ".join(chg))
        self.check(any("DCLR-SC-2013-N08: PARTIAL_MATCH -> EXACT_ANCHOR" in c for c in chg),
                   "crosswalk DCLR-SC-2013-N08 moves PARTIAL_MATCH -> EXACT_ANCHOR (as the C6-01 draft predicted)")

        # d. CORRECTION
        self.step("d", "Version 3: CORRECTION of AL-v0001-002 (class demoted to NON_PRIMARY_OFFICIAL_PUBLICATION_COPY) + version 4 BIND")
        v3 = [self.entry_from_draft(G, 1, 3, entry_type="CORRECTION", target_entry_id="AL-v0001-002",
                                    proposed_class="NON_PRIMARY_OFFICIAL_PUBLICATION_COPY",
                                    justification="SYNTHETIC DEMONSTRATION CORRECTION: class demoted to non-primary to exercise the CORRECTION path; not a real finding")]
        h3, m3 = self.pr(top, "pr/9003-v0003-correction", lambda: self.record_version(top, v3, note="CORRECTION"), 9003, "v0003: CORRECTION")
        self.run(top, "verify v3 pending", "verify", key="cli.verify.v3")
        texts[3] = self.built(top, 3)
        self.check([t["effect"] for t in self.describe(texts[3])["transitions"]][-1] == "PENDING_REPOSITORY_BINDING",
                   "version 3 CORRECTION is PENDING_REPOSITORY_BINDING")
        self.check(texts[3]["source_states.csv"] == texts[2]["source_states.csv"], "source states unchanged until the BIND line")
        h4, m4 = self.pr(top, "pr/9004-v0004-bind", lambda: self.add_bind(top, h3, m3, 9003, 900003), 9004, "v0004: BIND version 3")
        self.run(top, "verify v4", "verify", key="cli.verify.v4")
        texts[4] = self.built(top, 4)
        self.note("effective-state change 3 -> 4: " + "; ".join(self.diff(texts[3], texts[4])))
        self.check(self.describe(texts[4])["transitions"][-1]["effect"] == "APPLIED", "version 3 CORRECTION APPLIED after BIND 4")
        self.rec("commit.v0003", [h3, m3])
        self.rec("commit.v0004", [h4, m4])

        # e. WITHDRAW
        self.step("e", "Version 5: WITHDRAW of AL-v0001-001 (resulting_state PROVENANCE_UNKNOWN) + version 6 BIND")
        v5 = [self.withdraw_entry(D, 1, 5, "AL-v0001-001", "EVIDENCE_REVOKED", "PROVENANCE_UNKNOWN")]
        h5, m5 = self.pr(top, "pr/9005-v0005-withdraw", lambda: self.record_version(top, v5, note="WITHDRAW"), 9005, "v0005: WITHDRAW")
        self.run(top, "verify v5 pending", "verify", key="cli.verify.v5")
        texts[5] = self.built(top, 5)
        self.check(texts[5]["corpus_crosswalk.csv"] == texts[4]["corpus_crosswalk.csv"],
                   "staged WITHDRAW: crosswalk unchanged before its BIND line (current O5-A semantics)")
        h6, m6 = self.pr(top, "pr/9006-v0006-bind", lambda: self.add_bind(top, h5, m5, 9005, 900005), 9006, "v0006: BIND version 5")
        self.run(top, "verify v6", "verify", key="cli.verify.v6")
        texts[6] = self.built(top, 6)
        chg = self.diff(texts[5], texts[6])
        self.note("effective-state change 5 -> 6: " + "; ".join(chg))
        self.check(any("DCLR-SC-2013-N08: EXACT_ANCHOR -> PARTIAL_MATCH" in c for c in chg), "withdrawal drops the EXACT_ANCHOR")
        self.check(self.describe(texts[6])["newly_withdrawn"] == ["AL-v0005-001"], "newly_withdrawn.json lists AL-v0005-001")
        self.rec("commit.v0005", [h5, m5])
        self.rec("commit.v0006", [h6, m6])

        # f. re-authentication
        self.step("f", "Version 7: re-authentication after withdrawal (new ADD, new entry id and new records) + version 8 BIND")
        v7 = [self.entry_from_draft(D, 1, 7)]
        h7, m7 = self.pr(top, "pr/9007-v0007-readd", lambda: self.record_version(top, v7, note="re-ADD after withdrawal"), 9007, "v0007: re-ADD")
        self.run(top, "verify v7 pending", "verify", key="cli.verify.v7")
        h8, m8 = self.pr(top, "pr/9008-v0008-bind", lambda: self.add_bind(top, h7, m7, 9007, 900007), 9008, "v0008: BIND version 7")
        self.run(top, "verify v8", "verify", key="cli.verify.v8")
        texts[7], texts[8] = self.built(top, 7), self.built(top, 8)
        chg = self.diff(texts[7], texts[8])
        self.note("effective-state change 7 -> 8: " + "; ".join(chg))
        self.check(any("DCLR-SC-2013-N08: PARTIAL_MATCH -> EXACT_ANCHOR" in c for c in chg), "re-ADD restores the EXACT_ANCHOR")
        self.rec("commit.v0007", [h7, m7])
        self.rec("commit.v0008", [h8, m8])
        self.rec("ledger.HEAD.final", (self.pkg(top) / "ledger/HEAD").read_text(encoding="utf-8").strip())
        self.rec("ledger.manifest_sha256.final", sha256_bytes((self.pkg(top) / "ledger/manifest.jsonl").read_bytes()))

        # c. historical reproduction (run at the end, with HEAD at version 8)
        self.step("c", "Historical reproduction with HEAD at version 8: build --as-of N for every N; hashes")
        lines = self.manifest_lines(top)
        for v in range(len(lines)):
            again = self.built(top, v)
            d = self.describe(again)
            committed = {p.name: p.read_text(encoding="utf-8") for p in sorted((self.pkg(top) / f"effective/v{v:04d}").iterdir())}
            same = again == texts[v] == committed and d["effective_sha256"] == lines[v]["effective_sha256"]
            self.cur["items"].append(("asof", v, d["effective_sha256"], d["transitions"], same))
            self.check(same, f"--as-of {v}: identical to the build made when version {v} was recorded, to committed effective/v{v:04d}, "
                             f"and to the manifest pin {d['effective_sha256'][:16]}")
            self.rec(f"asof.{v}", d)
        for v in (1, 2):
            self.run(top, f"build as-of {v}", "build", "--as-of", str(v), "--out", str(self.tmp / f"cli_asof_{v}"), key=f"cli.build.asof{v}")

        self.step("final", "Final verify of the whole synthetic chain (versions 0-8) through the real CLI")
        self.run(top, "final verify", "verify", key="cli.verify.final")
        self.note("git log --first-parent main: " + " | ".join(self.git(top, "log", "--first-parent", "--format=%h %s", "main").splitlines()[::-1]))

    # ------------------------------------------------------------------ negative cases
    def clone(self, name, commit):
        dst = self.tmp / name
        self.git(self.tmp, "-c", "protocol.file.allow=always", "clone", "-q", "--no-local", str(self.top), str(dst))
        self.git(dst, "checkout", "-q", "-B", "main", commit)
        (dst / ".git/info/exclude").write_text("__pycache__/\n*.pyc\n", encoding="utf-8")
        return dst

    def negatives(self):
        g = self.expected["commit.genesis"]
        D, G = self.D, self.G

        self.step("g1", "Negative: owner decision record naming an AI agent")
        t = self.clone("neg1", g)
        self.pr(t, "pr/neg1", lambda: self.record_version(t, [self.entry_from_draft(D, 1, 1), self.entry_from_draft(G, 2, 1)],
                                                          decided_by="Claude Code (AI agent)", finalize=False), 9101, "neg1")
        self.run(t, "agent owner", "verify", expect_ok=False, expect_err="decided_by names an AI model or agent", key="neg.agent_owner")

        self.step("g2", "Negative: owner decision dated before the independent review")
        t = self.clone("neg2", g)
        self.pr(t, "pr/neg2", lambda: self.record_version(t, [self.entry_from_draft(D, 1, 1)], dec_date="2026-11-22", rev_date=DATE,
                                                          finalize=False), 9102, "neg2")
        self.run(t, "decision before review", "verify", expect_ok=False, expect_err="predates the independent review", key="neg.decision_before_review")

        self.step("g3", "Negative: unbound entry version followed by another entry version")
        t = self.clone("neg3", g)
        self.pr(t, "pr/neg3a", lambda: self.record_version(t, [self.entry_from_draft(D, 1, 1)]), 9103, "neg3 v1")
        self.pr(t, "pr/neg3b", lambda: self.record_version(t, [self.entry_from_draft(G, 1, 2)], finalize=False), 9104, "neg3 v2")
        self.run(t, "unbound then entry", "verify", expect_ok=False, expect_err="entry version appended before version 1 was bound",
                 key="neg.unbound_then_entry")

        self.step("g4", "Negative: pinned decision record tampered after recording (final chain, one byte changed, direct commit)")
        t = self.clone("neg4", self.git(self.top, "rev-parse", "HEAD"))
        f = self.pkg(t) / "decisions/D-v0001.md"
        f.write_text(f.read_text(encoding="utf-8").replace("decision: APPROVED", "decision: APPROVED "), encoding="utf-8")
        self.commit(t, "SYNTHETIC tamper of a pinned record")
        self.run(t, "tampered record", "verify", expect_ok=False, expect_err="pinned record decisions/D-v0001.md missing or modified",
                 key="neg.tampered_record")

        self.step("g5", "Negative: BIND line naming a fast-forward (PR branch merged with --ff-only)")
        t = self.clone("neg5", g)
        self.git(t, "checkout", "-q", "-b", "pr/neg5")
        self.record_version(t, [self.entry_from_draft(D, 1, 1)])
        h = self.commit(t, "SYNTHETIC neg5 v1")
        self.git(t, "checkout", "-q", "main")
        self.git(t, "merge", "-q", "--ff-only", "pr/neg5")
        ff = self.git(t, "rev-parse", "HEAD")
        self.note(f"after --ff-only merge HEAD {ff[:12]} == PR head {h[:12]}: {ff == h}")
        self.add_bind(t, h, ff, 9105, 900105, finalize=False)
        self.commit(t, "SYNTHETIC neg5 bind")
        self.run(t, "ff bind", "verify", expect_ok=False, expect_err="fast-forward is not a reviewed merge", key="neg.bind_fast_forward")
        # variant: name the PR head's parent (genesis, a root commit) as the merge commit
        t2 = self.clone("neg5b", g)
        self.git(t2, "checkout", "-q", "-b", "pr/neg5b")
        self.record_version(t2, [self.entry_from_draft(D, 1, 1)])
        h2 = self.commit(t2, "SYNTHETIC neg5b v1")
        self.git(t2, "checkout", "-q", "main")
        self.git(t2, "merge", "-q", "--ff-only", "pr/neg5b")
        self.add_bind(t2, h2, g, 9106, 900106, finalize=False)
        self.commit(t2, "SYNTHETIC neg5b bind")
        self.run(t2, "ff bind naming a non-merge", "verify", expect_ok=False, expect_err=r"merge_commit has [01] parent\(s\)",
                 key="neg.bind_non_merge")

        self.step("g6", "Negative (design rule): WITHDRAW targeting a CORRECTION row")
        t = self.clone("neg6", self.expected["commit.v0004"][1])
        self.pr(t, "pr/neg6", lambda: self.record_version(t, [self.withdraw_entry(G, 1, 5, "AL-v0003-001", "OTHER", "")], finalize=False),
                9107, "neg6")
        self.run(t, "withdraw of correction", "verify", expect_ok=False, expect_err="a WITHDRAW may target only an ADD or a BASELINE row",
                 key="neg.withdraw_of_correction")

    def close(self, keep):
        if not keep:
            shutil.rmtree(self.tmp, ignore_errors=True)


def transcript(demo, real_before, real_after, check_mode_note):
    out = ["# SYNTHETIC AUTH-LEDGER transaction demonstration: transcript", "",
           "**SYNTHETIC.** Generated by `tools/synthetic_transaction_demo.py`. Every decision and review record shown here was written by "
           "the script into a temporary repository that was deleted after the run. Nothing here is an owner decision, an approval, a "
           "review or a legal opinion. The real ledger was only read and stays at version 0.", "",
           f"- Real ledger HEAD before the run: `{real_before}`", f"- Real ledger HEAD after the run: `{real_after}`",
           "- Commands are run from the temporary repository top (`$WORK/repo`, or `$WORK/negN` for negative cases) with the real "
           "AUTH-LEDGER command-line tool invoked by its absolute path.", f"- {check_mode_note}", ""]
    for s in demo.steps:
        out += [f"## Step {s['id']}: {s['title']}", ""]
        for it in s["items"]:
            if it[0] == "note":
                out.append(f"- {it[1]}")
            elif it[0] == "check":
                out.append(f"- **{it[2]}** {it[1]}")
            elif it[0] == "cmd":
                _, cmd, rc, o, e, verdict = it
                out += ["", "```", f"$ {cmd}", f"(exit {rc})"] + ([o] if o else []) + ([e] if e else []) + ["```",
                        f"Result: **{verdict}**", ""]
            elif it[0] == "asof":
                _, v, h, trs, same = it
                eff = "; ".join(f"{t['entry_id']} {t['entry_type']} {t['effect']}" + (f" (bound_by {t['bound_by']})" if t["bound_by"] else "")
                                for t in trs) or "no transitions"
                out.append(f"- `--as-of {v}` effective_sha256 `{h}` - {eff} - reproduced: **{'PASS' if same else 'FAIL'}**")
        out.append("")
    out += ["## Summary", "", f"- Failures: {len(demo.failures)}"] + [f"  - {f}" for f in demo.failures] + [""]
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", default=os.environ.get("AUTH_LEDGER_SOURCE", str(DEFAULT_SOURCE)))
    ap.add_argument("--work", default=str(TXN / "work"))
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--keep", action="store_true")
    a = ap.parse_args()
    src = Path(a.source)
    real_pkg = src / PKG_REL
    real_before = (real_pkg / "ledger/HEAD").read_text(encoding="utf-8").strip()
    real_manifest_before = (real_pkg / "ledger/manifest.jsonl").read_bytes()
    demo = Demo(src, a.work)
    try:
        demo.main_sequence()
        demo.negatives()
    finally:
        demo.close(a.keep)
    real_after = (real_pkg / "ledger/HEAD").read_text(encoding="utf-8").strip()
    if real_after != real_before or (real_pkg / "ledger/manifest.jsonl").read_bytes() != real_manifest_before or real_before != REAL_GENESIS_HEAD:
        demo.failures.append(f"real ledger changed or is not at version 0 ({real_before} -> {real_after})")
    demo.expected["real_ledger.HEAD"] = real_after
    text = transcript(demo, real_before, real_after, "Deterministic: fixed identities and git dates; `--check` re-runs and compares "
                                                     "every recorded value with `expected_hashes.json` and this transcript byte-for-byte.")
    exp_path, tr_path = TXN / "expected_hashes.json", TXN / "TRANSCRIPT.md"
    exp_text = json.dumps(demo.expected, indent=1, sort_keys=True) + "\n"
    rc = 0
    if demo.failures:
        print("\nDEMO FAILURES:\n  " + "\n  ".join(demo.failures))
        rc = 1
    if a.check:
        want = json.loads(exp_path.read_text(encoding="utf-8"))
        bad = sorted(k for k in set(want) | set(demo.expected) if want.get(k) != demo.expected.get(k))
        if bad:
            print("CHECK: values differ from expected_hashes.json: " + ", ".join(bad))
            rc = 1
        if tr_path.read_text(encoding="utf-8") != text:
            print("CHECK: generated transcript differs from TRANSCRIPT.md")
            rc = 1
        print(f"CHECK {'OK' if rc == 0 else 'FAILED'}: {len(demo.expected)} recorded values compared; transcript compared")
    else:
        exp_path.write_text(exp_text, encoding="utf-8")
        tr_path.write_text(text, encoding="utf-8")
        print(f"wrote {tr_path} and {exp_path} ({len(demo.expected)} values)")
    return rc


if __name__ == "__main__":
    sys.exit(main())
