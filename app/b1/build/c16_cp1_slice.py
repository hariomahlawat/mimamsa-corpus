"""C16 Tranche B CP-1: the integrated, explicitly DEGRADED vertical slice on an isolated development site (fixture
acceptance only: not synthetic-scale, not full-corpus; closes no FG-* gate on real data).

    python -I app/b1/build/c16_cp1_slice.py run --work <dir outside the repo> [--evidence <json>] [--configuration Debug]
           [--oracle-site <syn site> --oracle-map <fixture_map.json> --oracle-db <Npgsql DSN>]
    python -I app/b1/build/c16_cp1_slice.py exclude --site <site> --sequence <n> --doc <doc_id>      (called by the journey)

Environment (never printed): MIMAMSA_TEST_DB (Npgsql DSN of the app role; owner of the disposable c16cp1_* databases)
and optionally MIMAMSA_TEST_PG_ADMIN (a role with CREATEDB/CREATEROLE: needed where the app role is not a superuser,
e.g. windows-latest). Nothing here touches an operational site, database, key or trust list; every key is a fixed
DEVELOPMENT key derived from a public string.

Steps (each a stream's own code; this driver only sequences them):
  1. B02  builds two development-signed degraded MKR-1 releases from fixtures: G1 = cp1-fixture (contract 2.0 positive
          exchange, SYN v1 corpus), G2 = cp1-slice (contract 2.1 exchange with real bytes and typed receipts; one copy
          admitted and also a v1 document, one held, one C16-only).
  2. B01  imports G1 into a fresh isolated site (signed exclusion channel, Python ExclusionStore with a development
          register key) and imports G2 STAGE-ONLY (generation written; ACTIVE is left to the activation journal).
  3. The C# journey (Mimamsa.Tests C16Cp1SliceTests, MIMAMSA_CP1_CONTEXT): B03 migration on a CLONED disposable DB,
          the restricted loader stages/verifies the knowledge and graph rows of both generations, B04 adopts the shipped
          text stores, B06 initialises the journal on G1 and activates G2 with Mimamsa:Activation:Enabled in a real
          Kestrel process (serving checks), then an exclusion after activation and a rollback.
  4. The outcome is computed with the reference `components.activation_outcome` from what the site verified: it must be
          ACTIVE_DEGRADED / DEGRADED_LEXICAL_ONLY, never ACTIVE_FULL; embedder calls 0.
  5. Optional: the PR #54 retrieval oracle in DEFAULT mode (activation off, memory/memory), unmodified.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
for p in (REPO / "app" / "contract", REPO / "app" / "importer", REPO / "app" / "kbuild"):
    sys.path.insert(0, str(p))

DEV_RELEASE_SEED = "4d696d616d73612d6b6275696c642d746573742d6f6e6c792d6465762d6b6579"   # = app/kbuild/tests conftest DEV_SEED
REGISTER_SEED = b"mimamsa-c16-cp1-development-register-key"                              # DEVELOPMENT only
REGISTER_PATH = REPO / "config" / "restricted_material.json"


# ------------------------------------------------------------------ exclusion store (Python ExclusionStore, dev key)

def _register_key():
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    sk = Ed25519PrivateKey.from_private_bytes(hashlib.sha256(REGISTER_SEED).digest())
    pub = sk.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return sk, pub


def register_trust_list() -> dict:
    _, pub = _register_key()
    return {"contract_version": "1.0.0", "record_kind": "trust_list", "sequence": 1, "issued_at": "2026-11-28T00:00:00Z",
            "keys": [{"key_id": "dev-" + hashlib.sha256(pub).hexdigest(), "public_key_hex": pub.hex(), "holder": "DEVELOPMENT",
                      "purposes": ["register"], "revoked": False}]}


def append_exclusion(site: Path, sequence: int, withdraw_doc_ids: list[str], withdraw_shas: list[str] = ()) -> dict:
    """One signed exclusion update appended with the REAL Python ExclusionStore (development mode)."""
    from mimamsa_contract.exclusions import ExclusionStore
    from mimamsa_contract.trust import parse_trust_list
    sk, _ = _register_key()
    trust = parse_trust_list(json.loads((site / "trust" / "TRUST_LIST.json").read_text(encoding="utf-8")))
    reg = REGISTER_PATH.read_text(encoding="utf-8")
    u = {"contract_version": "1.0.0", "record_kind": "exclusion_update", "sequence": sequence, "issued_at": "2026-11-28T00:00:00Z",
         "register_sha256": hashlib.sha256(reg.encode("utf-8")).hexdigest(), "register_json": reg,
         "withdrawals": [{"doc_id": d, "reason": "CP-1 slice: withdrawn after activation (fixture)"} for d in withdraw_doc_ids]
                        + [{"source_copy_sha256": s, "reason": "CP-1 slice: copy withdrawn after activation (fixture)"} for s in withdraw_shas]}
    b = json.dumps(u, sort_keys=True).encode("utf-8")
    return ExclusionStore(site / "exclusions").append(b, sk.sign(b), trust, mode="development")


def exclusion_state(site: Path):
    from mimamsa_contract.exclusions import ExclusionStore
    from mimamsa_contract.trust import parse_trust_list
    trust = parse_trust_list(json.loads((site / "trust" / "TRUST_LIST.json").read_text(encoding="utf-8")))
    return ExclusionStore(site / "exclusions").effective_state(trust, mode="development")


# ------------------------------------------------------------------ the run

def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def build_releases(work: Path) -> dict:
    from mimamsa_kbuild.cli import build_accel, run_build
    from mimamsa_kbuild.fixture_mirror import prepare
    key = work / "keys" / "release-dev.key"
    key.parent.mkdir(parents=True, exist_ok=True)
    key.write_text(DEV_RELEASE_SEED + "\n", encoding="ascii")
    accel = build_accel(work / "tools")
    out = {}
    for name, exchange, spec_file in (("G1", "positive", "cp1-fixture.spec.json"), ("G2", "cp1", "cp1-slice.spec.json")):
        mirror = work / f"mirror-{name}"
        prepare(mirror, exchange=exchange)
        spec = json.loads((REPO / "app" / "kbuild" / "specs" / spec_file).read_text(encoding="utf-8"))
        res = run_build(spec, work / f"out-{name}", mirror=mirror, dev_key=key, accel=accel, apply_budget=False)
        root = work / f"out-{name}" / spec["output_dir"]
        verify = json.loads((root / "S9" / "VERIFY.json").read_text(encoding="utf-8"))
        out[name] = {"spec": spec_file, "release_id": spec["release"]["release_id"], "release_sequence": spec["release"]["release_sequence"],
                     "bundle": str(root / "S8" / "bundle"), "trust": str(root / "S8" / "dev-trust" / "trust_list.json"),
                     "build_outcome": json.loads((root / "BUILD_RECORD.json").read_text(encoding="utf-8"))["outcome"], "stages_ran": res["ran"], "expected_activation": verify["expected_activation"],
                     "bundle_sha256sums": _sha(root / "S8" / "bundle" / "SHA256SUMS")}
    return out


def import_site(work: Path, builds: dict) -> dict:
    from mimamsa_contract.restricted import register_from_bytes
    from mimamsa_contract.trust import parse_trust_list
    from mimamsa_importer import configure_site, import_release
    site = work / "site"
    if site.exists():
        def _writable(fn, path, _exc):   # vault objects are written read-only
            os.chmod(path, 0o644)
            fn(path)
        shutil.rmtree(site, onexc=_writable) if sys.version_info >= (3, 12) else shutil.rmtree(site, onerror=_writable)
    configure_site(site, exclusion_channel="signed")
    (site / "trust").mkdir(parents=True)
    (site / "trust" / "TRUST_LIST.json").write_text(json.dumps(register_trust_list(), sort_keys=True), encoding="utf-8")
    append_exclusion(site, 1, [])                     # signed baseline (nothing withdrawn)
    reg = register_from_bytes(REGISTER_PATH.read_bytes(), "config/restricted_material.json")
    out = {}
    for name, stage_only in (("G1", False), ("G2", True)):
        b = builds[name]
        trust = parse_trust_list(json.loads(Path(b["trust"]).read_text(encoding="utf-8")))
        r = import_release(Path(b["bundle"]), site, trust_list=trust, mode="development", register=reg,
                           exclusions=exclusion_state(site), stage_only=stage_only)
        if not (r.staged if stage_only else r.activated):
            raise SystemExit(f"B01 import of {name} refused: {r.refused_reasons}")
        gen = json.loads((site / "generations" / r.release_id / "generation.json").read_text(encoding="utf-8"))
        out[name] = {"release_id": r.release_id, "activated": r.activated, "staged": r.staged,
                     "served_documents": sorted(gen["servable"]["documents"]),
                     "c16_served_copies": [c[0] for c in (gen.get("c16") or {}).get("served_copies", [])],
                     "c16_codes": (gen.get("c16") or {}).get("codes"), "accounting": (gen.get("c16") or {}).get("accounting"),
                     "knowledge_release": bool((gen.get("c16") or {}).get("knowledge_release"))}
    out["active_after_import"] = (site / "ACTIVE").read_text(encoding="utf-8").strip()
    return out


def run_journey(work: Path, context: dict, configuration: str) -> dict:
    ctx_path = work / "context.json"
    ctx_path.write_text(json.dumps(context, indent=1, sort_keys=True), encoding="utf-8")
    env = dict(os.environ, MIMAMSA_CP1_CONTEXT=str(ctx_path))
    if not env.get("MIMAMSA_TEST_SITE"):
        raise SystemExit("MIMAMSA_TEST_SITE (a SYN site from build_fixture_site.py) is required: the journey seeds its source DB with it")
    cmd = ["dotnet", "test", str(REPO / "app" / "b1" / "tests" / "Mimamsa.Tests"), "-c", configuration, "--no-build", "-nologo",
           "--filter", "FullyQualifiedName~C16Cp1SliceTests", "--logger", "console;verbosity=normal"]
    p = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=1800)
    (work / "journey.log").write_text(p.stdout + p.stderr, encoding="utf-8")
    if p.returncode != 0:
        raise SystemExit("CP-1 journey failed; see " + str(work / "journey.log") + "\n" + p.stdout[-4000:])
    return json.loads(Path(context["results"]).read_text(encoding="utf-8"))


def outcome(journey: dict) -> dict:
    """The reference outcome rule over what the SITE verified (not what the build claimed)."""
    from mimamsa_contract.c16 import components
    contracts = {k: json.loads((REPO / "app" / "contract" / "fixtures" / "c16" / "v2_1" / "component_contracts" / f"{k}.json").read_text(encoding="utf-8"))
                 for k in ("GRAPH", "KNOWLEDGE_ROWS", "LEXICAL_INDEX", "TEXT_STORE", "VECTOR_PACK")}
    o = components.activation_outcome(journey["component_results"], contracts, mode="development")
    if o["result"] == "ACTIVE_FULL" or o["service_level"] == "FULL":
        raise SystemExit("CP-1 must never be ACTIVE_FULL")
    if o["result"] != "ACTIVE_DEGRADED" or o["service_level"] != "DEGRADED_LEXICAL_ONLY" or o["site_embedding"] != "NEVER":
        raise SystemExit(f"unexpected CP-1 outcome {o}")
    if journey["embedder_calls"] != 0:
        raise SystemExit("the site embedded something")
    return o


def oracle(site: str, fmap: str, db: str, work: Path, configuration: str) -> dict:
    """PR #54 retrieval oracle, unmodified, against the real service in DEFAULT mode (activation off)."""
    out = work / "oracle"
    dll = REPO / "app" / "b1" / "src" / "Mimamsa.Web" / "bin" / configuration / "net10.0" / "Mimamsa.Web.dll"
    cmd = [sys.executable, str(REPO / "app" / "b1" / "tests" / "b1server.py"), "--site", site, "--log", str(work / "oracle-service.log"),
           "--db", db, "--dll", str(dll), "--", sys.executable, str(REPO / "app" / "b1" / "tests" / "oracles" / "run_retrieval_oracle.py"), "--map", fmap, "--out", str(out)]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    (work / "oracle.log").write_text(p.stdout + p.stderr, encoding="utf-8")
    return {"exit_code": p.returncode, "out": str(out), "summary_tail": p.stdout.strip().splitlines()[-3:]}


def cmd_run(a) -> int:
    work = Path(a.work).resolve()
    if REPO in work.parents or work == REPO:
        raise SystemExit("--work must be outside the repository")
    work.mkdir(parents=True, exist_ok=True)
    builds = build_releases(work)
    imported = import_site(work, builds)
    import c16_cases as cc
    from mimamsa_contract.c16 import adapters
    g2 = imported["G2"]
    legacy = next(d for d in g2["served_documents"] if d != cc.DOC_A)
    # a statute with printed headings (the sections surface), withdrawn later by its copy hash (C16-CP1-01)
    g2dir = work / "site" / "generations" / g2["release_id"]
    acts = [json.loads(x) for x in (g2dir / "records" / "documents.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    statute = next(d for d in sorted(acts, key=lambda d: d["doc_id"]) if d.get("doc_type") == "act" and d["doc_id"] in g2["served_documents"])
    if statute["doc_id"] == legacy:
        legacy = next(d for d in g2["served_documents"] if d not in (cc.DOC_A, statute["doc_id"]))
    context = {
        "site": str(work / "site"), "work": str(work), "results": str(work / "journey-results.json"),
        "python": sys.executable, "driver": str(Path(__file__).resolve()), "register": str(REGISTER_PATH),
        "g1": imported["G1"]["release_id"], "g2": g2["release_id"],
        "release_sequence": {builds[k]["release_id"]: builds[k]["release_sequence"] for k in ("G1", "G2")},
        "admitted_doc": cc.DOC_A, "held_doc": cc.DOC_B, "c16_only_doc": adapters.local_doc_id(cc.h(cc.Corpus().e)),
        "legacy_doc": legacy, "admitted_query": "appellant relied on section 69",
        "statute_doc": statute["doc_id"], "statute_query": statute.get("title") or statute["doc_id"],
    }
    journey = run_journey(work, context, a.configuration)
    o = outcome(journey)
    ev = {"acceptance_level": "FIXTURE (SG-5): CP-1 vertical slice on an isolated development site; not synthetic-scale, "
                              "not full-corpus; closes no FG-* gate on real data",
          "builds": builds, "import": imported, "journey": journey, "activation_outcome": o}
    if a.oracle_site:
        ev["oracle_default_mode"] = oracle(a.oracle_site, a.oracle_map, a.oracle_db, work, a.configuration)
        if ev["oracle_default_mode"]["exit_code"] != 0:
            raise SystemExit("the PR #54 oracle failed in default mode; see " + str(work / "oracle.log"))
    text = json.dumps(ev, indent=1, sort_keys=True)
    (work / "slice-evidence.json").write_text(text, encoding="utf-8")
    if a.evidence:
        Path(a.evidence).parent.mkdir(parents=True, exist_ok=True)
        Path(a.evidence).write_text(text.replace(str(work), "<work>") + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "activation_outcome": o, "checks": journey.get("checks")}, indent=1, sort_keys=True))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--work", required=True)
    r.add_argument("--evidence")
    r.add_argument("--configuration", default="Debug")
    r.add_argument("--oracle-site")
    r.add_argument("--oracle-map")
    r.add_argument("--oracle-db")
    e = sub.add_parser("exclude")
    e.add_argument("--site", required=True)
    e.add_argument("--sequence", type=int, required=True)
    e.add_argument("--doc", action="append", default=[])
    e.add_argument("--sha", action="append", default=[], help="withdraw a copy by its source_copy_sha256")
    a = ap.parse_args(argv)
    if a.cmd == "run":
        return cmd_run(a)
    ack = append_exclusion(Path(a.site), a.sequence, a.doc, a.sha)
    print(json.dumps({"ok": True, "sequence": ack.get("sequence")}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
