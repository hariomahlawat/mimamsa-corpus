"""C16 Tranche B Stage 3 S3-C: the REAL RESTORE TEST on development/test data (B07 + B08; FIXTURE acceptance level, SG-5).

    python -I app/b1/build/c16_s3c_restore.py run --work <dir outside the repo> [--configuration Release] [--evidence <json>]
    python -I app/b1/build/c16_s3c_restore.py setup-site --site <dir>                              (called by the journey)
    python -I app/b1/build/c16_s3c_restore.py import --site <dir> --release <name> --context <json> [--stage-only]
    python -I app/b1/build/c16_s3c_restore.py exclude --site <dir> --sequence <n> [--doc D]... [--sha S]...

Environment (never printed): MIMAMSA_TEST_DB (Npgsql DSN of the application role, owner of the disposable c16s3c_*
databases), MIMAMSA_TEST_PG_ADMIN (role administrator), MIMAMSA_PG_BIN (pg_dump/pg_restore), MIMAMSA_TEST_SITE (a SYN
site whose data seeds the source database). Development keys only; nothing touches an operational site, database, key or
trust list; no HF access.

The driver builds four development-signed releases with B02 (G1 = cp1-fixture, G2..G4 = cp1-slice content under distinct
release ids and sequences) and hands them, as RELEASE MEDIA, to the C# journey (Mimamsa.Tests S3cRestoreJourneyTests),
which: installs a site (layout, measured preflight, hardened database, I-3 migration on a clone), imports and STAGES each
release with the production `stage` command, activates through the journal, prunes (retention), rolls back, accepts
exclusions, serves; takes an encrypted backup; continues (activation and exclusion after the backup) and copies the
append-only stores separately; DESTROYS the site; restores onto a fresh isolated installation; re-imports the journal-head
release from media, stages it, recovers; and proves the restored site serves exactly what the destroyed site last served,
with every exclusion intact. Negative drills (wrong key, tampering, truncation, partial and stale media) run first.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parent))
for p in (REPO / "app" / "contract", REPO / "app" / "importer", REPO / "app" / "kbuild"):
    sys.path.insert(0, str(p))

import c16_cp1_slice as cp1  # noqa: E402  (the CP-1 driver: development keys, exclusion store, B02 builds)


def build_releases(work: Path) -> dict:
    from mimamsa_kbuild.cli import build_accel, run_build
    from mimamsa_kbuild.fixture_mirror import prepare
    key = work / "keys" / "release-dev.key"
    key.parent.mkdir(parents=True, exist_ok=True)
    key.write_text(cp1.DEV_RELEASE_SEED + "\n", encoding="ascii")
    accel = build_accel(work / "tools")
    out = {}
    plan = [("G1", "positive", "cp1-fixture.spec.json", None), ("G2", "cp1", "cp1-slice.spec.json", None),
            ("G3", "cp1", "cp1-slice.spec.json", 3), ("G4", "cp1", "cp1-slice.spec.json", 4)]
    mirrors = {}
    for name, exchange, spec_file, seq in plan:
        mirror = mirrors.get(exchange)
        if mirror is None:
            mirror = work / f"mirror-{exchange}"
            prepare(mirror, exchange=exchange)
            mirrors[exchange] = mirror
        spec = json.loads((REPO / "app" / "kbuild" / "specs" / spec_file).read_text(encoding="utf-8"))
        if seq is not None:   # the same content under a distinct release id and sequence (a later release)
            spec["release"]["release_id"] = spec["release"]["release_id"][:-8] + f"{seq:08d}"
            spec["release"]["release_sequence"] = seq
            spec["build_id"] = spec["build_id"] + f"-s3c{seq}"
            spec["output_dir"] = spec["output_dir"] + f"-s3c{seq}"
        run_build(spec, work / f"out-{name}", mirror=mirror, dev_key=key, accel=accel, apply_budget=False)
        root = work / f"out-{name}" / spec["output_dir"]
        out[name] = {"release_id": spec["release"]["release_id"], "release_sequence": spec["release"]["release_sequence"],
                     "bundle": str(root / "S8" / "bundle"), "trust": str(root / "S8" / "dev-trust" / "trust_list.json"),
                     "expected_activation": json.loads((root / "S9" / "VERIFY.json").read_text(encoding="utf-8"))["expected_activation"]}
    return out


def setup_site(site: Path) -> None:
    from mimamsa_importer import configure_site
    configure_site(site, exclusion_channel="signed")
    (site / "trust").mkdir(parents=True, exist_ok=True)
    (site / "trust" / "TRUST_LIST.json").write_text(json.dumps(cp1.register_trust_list(), sort_keys=True), encoding="utf-8")
    cp1.append_exclusion(site, 1, [])


def import_one(site: Path, release: dict, stage_only: bool) -> dict:
    from mimamsa_contract.restricted import register_from_bytes
    from mimamsa_contract.trust import parse_trust_list
    from mimamsa_importer import import_release
    reg = register_from_bytes(cp1.REGISTER_PATH.read_bytes(), "config/restricted_material.json")
    trust = parse_trust_list(json.loads(Path(release["trust"]).read_text(encoding="utf-8")))
    r = import_release(Path(release["bundle"]), site, trust_list=trust, mode="development", register=reg,
                       exclusions=cp1.exclusion_state(site), stage_only=stage_only)
    ok = r.staged if stage_only else r.activated
    return {"ok": bool(ok), "release_id": r.release_id, "staged": r.staged, "activated": r.activated, "refused": r.refused_reasons}


def cmd_run(a) -> int:
    work = Path(a.work).resolve()
    if REPO in work.parents or work == REPO:
        raise SystemExit("--work must be outside the repository")
    work.mkdir(parents=True, exist_ok=True)
    for k in ("MIMAMSA_TEST_DB", "MIMAMSA_PG_BIN", "MIMAMSA_TEST_SITE"):
        if not os.environ.get(k):
            raise SystemExit(f"{k} is required")
    releases = build_releases(work)
    import c16_cases as cc
    from mimamsa_contract.c16 import adapters
    context = {
        "work": str(work), "results": str(work / "journey-results.json"), "python": sys.executable, "driver": str(Path(__file__).resolve()),
        "cp1_driver": str(Path(cp1.__file__).resolve()), "register": str(cp1.REGISTER_PATH),
        "contracts": str(REPO / "app" / "contract" / "fixtures" / "c16" / "v2_1" / "component_contracts"),
        "releases": releases, "admitted_doc": cc.DOC_A, "held_doc": cc.DOC_B, "c16_only_doc": adapters.local_doc_id(cc.h(cc.Corpus().e)),
        "admitted_query": "appellant relied on section 69",
    }
    ctx_path = work / "context.json"
    ctx_path.write_text(json.dumps(context, indent=1, sort_keys=True), encoding="utf-8")
    env = dict(os.environ, MIMAMSA_S3C_CONTEXT=str(ctx_path))
    cmd = ["dotnet", "test", str(REPO / "app" / "b1" / "tests" / "Mimamsa.Tests"), "-c", a.configuration, "--no-build", "-nologo",
           "--filter", "FullyQualifiedName~S3cRestoreJourneyTests", "--logger", "console;verbosity=normal"]
    p = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=3600)
    (work / "journey.log").write_text(p.stdout + p.stderr, encoding="utf-8")
    if p.returncode != 0:
        raise SystemExit("S3-C restore journey failed; see " + str(work / "journey.log") + "\n" + p.stdout[-6000:])
    res = json.loads(Path(context["results"]).read_text(encoding="utf-8"))
    ev = {"acceptance_level": "FIXTURE (SG-5): S3-C real restore test on isolated development sites with development keys and "
                              "test data; not the owner's offline Windows host (FG-REAL-RESTORE-TEST stays open: OG-8)",
          "releases": {k: {x: v[x] for x in ("release_id", "release_sequence", "expected_activation")} for k, v in releases.items()},
          "journey": res}
    text = json.dumps(ev, indent=1, sort_keys=True)
    (work / "restore-evidence.json").write_text(text, encoding="utf-8")
    if a.evidence:
        Path(a.evidence).parent.mkdir(parents=True, exist_ok=True)
        Path(a.evidence).write_text(text.replace(str(work), "<work>").replace(str(work).replace("\\", "\\\\"), "<work>") + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "checks": len(res.get("checks", {}))}, sort_keys=True))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--work", required=True)
    r.add_argument("--evidence")
    r.add_argument("--configuration", default="Debug")
    s = sub.add_parser("setup-site")
    s.add_argument("--site", required=True)
    i = sub.add_parser("import")
    i.add_argument("--site", required=True)
    i.add_argument("--release", required=True)
    i.add_argument("--context", required=True)
    i.add_argument("--stage-only", action="store_true")
    e = sub.add_parser("exclude")
    e.add_argument("--site", required=True)
    e.add_argument("--sequence", type=int, required=True)
    e.add_argument("--doc", action="append", default=[])
    e.add_argument("--sha", action="append", default=[])
    a = ap.parse_args(argv)
    if a.cmd == "run":
        return cmd_run(a)
    if a.cmd == "setup-site":
        setup_site(Path(a.site))
        print(json.dumps({"ok": True}))
        return 0
    if a.cmd == "import":
        ctx = json.loads(Path(a.context).read_text(encoding="utf-8"))
        res = import_one(Path(a.site), ctx["releases"][a.release], a.stage_only)
        print(json.dumps(res, sort_keys=True))
        return 0 if res["ok"] else 2
    ack = cp1.append_exclusion(Path(a.site), a.sequence, a.doc, a.sha)
    print(json.dumps({"ok": True, "sequence": ack.get("sequence")}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
