"""Deterministic builder for the contract 2.1 (Tranche B Stage 1) interface fixtures under fixtures/c16/v2_1/.

Additive: the frozen 2.0 fixtures (build_fixtures.py) are reused, never changed. Everything is synthetic.
Run:  python -I app/contract/fixtures/c16/build_fixtures_2_1.py [--check]
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "v2_1"
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE))

import build_fixtures as bf  # noqa: E402
from mimamsa_contract.c16 import accounting, canonical, digests, knowledge_rows, receipts, scenarios  # noqa: E402
from mimamsa_contract.c16.build_spec import STAGES, make_stage_manifest  # noqa: E402

C21 = "mimamsa-corpus-contract/2.1"
H = bf.H
REGISTER = H("register-fixture")
RECEIPT_KINDS = {"G01_HASH_VERIFIED": "HASH_REDOWNLOAD", "G02_FORMAT_DETECTED": "FORMAT_DETECTION", "G03_RESTRICTED_REGISTER": "REGISTER_CHECK",
                 "G04_ACCESS_MARKING_REVIEWED": "MARKING_SCREEN", "G05_IDENTITY_RECORD_VALID": "IDENTITY_VALIDATION",
                 "G06_TEXT_DERIVATIVE_VERIFIED": "DERIVATIVE_VERIFICATION", "G07_EMBEDDED_IMAGES_ACCOUNTED": "IMAGE_ACCOUNTING",
                 "G08_RELEVANCE_ASSESSED": "RELEVANCE_DECISION", "G09_DUPLICATE_RESOLVED": "DUPLICATE_RESOLUTION", "G10_SCHEMA_VALID": "SCHEMA_VALIDATION"}
ASSERTED = {"MARKING_SCREEN", "RELEVANCE_DECISION", "DUPLICATE_RESOLUTION"}
PRODUCER = {"name": "c16-fixture-gates", "version": "1.0.0", "commit": "c8fa5290", "config_sha256": None}


def population():
    bf.REVIEWS.clear()
    ids = bf.build_identities()
    A = bf.build_anchors(ids)
    bf.bind_native_anchor(A)
    bf.ANCHOR_KEYS.clear()
    bf.ANCHOR_KEYS.update({k: v["anchor_id"] for k, v in A.items()})
    R = bf.build_relationships(ids, A)
    return ids, {"identities": list(ids.values()), "anchors": list(A.values()), "relationships": R, "taxonomy": bf.build_taxonomy(),
                 "admissions": bf.build_admissions(), "reviewed_records": list(bf.REVIEWS)}


def official_artefacts(ids, pop):
    ident = ids["official-pdf"]
    sha, doc = ident["source_copy"]["sha256"], ident["doc_id"]
    der = ident["text_derivatives"][0]
    units = [H(f"unit:{n}") for n in range(1, 13)]
    payload = {
        "G01_HASH_VERIFIED": {"source": {"hf_repo": "owner/fixture-corpus", "hf_revision": H("hf-revision")[:40], "path": f"data/raw/fixture/{sha}.pdf"},
                              "measured_sha256": sha, "measured_bytes": ident["source_copy"]["bytes"]},
        "G02_FORMAT_DETECTED": {"magic_hex": "255044462d", "detected_format": "PDF", "mime_type": "application/pdf"},
        "G03_RESTRICTED_REGISTER": {"fields_checked": ["doc_id", "paths", "record_strings", "sha256"], "matches": 0},
        "G04_ACCESS_MARKING_REVIEWED": {"pages_screened": 12, "images_screened": 0, "markings_found": [], "method": "page text and page-image screen (fixture)", "ocr_config_sha256": None},
        "G05_IDENTITY_RECORD_VALID": {"identity_record_sha256": canonical.record_sha256(ident), "issues": 0},
        "G06_TEXT_DERIVATIVE_VERIFIED": {"units_total": 12, "units_with_text": 12, "unit_text_sha256": units},
        "G08_RELEVANCE_ASSESSED": {"decided_by_kind": "OWNER", "decided_by": "owner-fixture", "basis": "military-law judgment (fixture)"},
        "G09_DUPLICATE_RESOLVED": {"compared_scope": "fixture canonical index", "method": "BYTE_HASH_AND_TEXT_REVIEW", "result": "UNIQUE"},
        "G10_SCHEMA_VALID": {"copy_records_sha256": receipts.copy_records_digest(ident, pop["anchors"], pop["relationships"]), "issues": 0},
    }
    arts = {}
    for gate, p in payload.items():
        kind = RECEIPT_KINDS[gate]
        arts[gate] = {"contract": C21, "record_kind": "gate_receipt_artefact", "gate_id": gate, "receipt_kind": kind,
                      "verification_class": "ASSERTED_BOUND" if kind in ASSERTED else "SITE_RECOMPUTABLE",
                      "subject": {"doc_id": doc, "source_copy_sha256": sha}, "corpus_generation_id": bf.CG,
                      "derivative_sha256": der["derivative_text_sha256"] if gate == "G06_TEXT_DERIVATIVE_VERIFIED" else None,
                      "rule": {"id": "c16-gate-" + gate[:3].lower(), "version": "1.0"}, "config_sha256": H("gate-config"),
                      "register_sha256": REGISTER if gate == "G03_RESTRICTED_REGISTER" else None, "outcome": "PASS",
                      "revision": 1, "supersedes_receipt_sha256": None, "producer": PRODUCER, "payload": p}
    facts = [{"source_copy_sha256": sha, "receipt_kind": "HASH_REDOWNLOAD", "fact": {"sha256": sha, "bytes": ident["source_copy"]["bytes"]}},
             {"source_copy_sha256": sha, "receipt_kind": "FORMAT_DETECTION", "fact": {"detected_format": "PDF", "magic_hex": "255044462d"}},
             {"source_copy_sha256": sha, "receipt_kind": "REGISTER_CHECK", "fact": {"matches": 0}},
             {"source_copy_sha256": sha, "receipt_kind": "IDENTITY_VALIDATION", "fact": {"issues": 0}},
             {"source_copy_sha256": sha, "receipt_kind": "DERIVATIVE_VERIFICATION", "fact": {"unit_text_sha256": units}},
             {"source_copy_sha256": sha, "receipt_kind": "SCHEMA_VALIDATION", "fact": {"issues": 0}}]
    return arts, facts


def bind(adm, arts):
    """Point the admission's PASS receipts at the real artefacts (admission_id is unchanged: receipts are not part of
    its identity tuple)."""
    for g in adm["gates"]:
        a = arts.get(g["gate_id"])
        if a is not None and g.get("receipt"):
            g["receipt"].update(receipt_kind=a["receipt_kind"], subject_sha256=a["subject"]["source_copy_sha256"],
                                derivative_sha256=a["derivative_sha256"], rule_id=a["rule"]["id"], rule_version=a["rule"]["version"],
                                config_sha256=a["config_sha256"], register_sha256=a["register_sha256"], outcome=a["outcome"],
                                receipt_sha256=receipts.artefact_sha256(a))
    return adm


def art_files(arts: dict) -> dict[str, str]:
    return {receipts.artefact_path(a): receipts.artefact_bytes(a).decode("utf-8") for a in arts.values()}


def receipt_negatives(official_adm, arts):
    N = {}

    def case(name, code, desc, mutate_arts=None, mutate_adm=None, contract=C21, drop_facts=(), inventory=None, extra=None, rebind=True):
        a2 = copy.deepcopy(arts)
        adm = copy.deepcopy(official_adm)
        if mutate_arts:
            mutate_arts(a2)
        if rebind:
            bind(adm, a2)
        if mutate_adm:
            mutate_adm(adm, a2)
        files = art_files(a2)
        if extra:
            extra(files, a2)
        N[name] = {"expect_code": code, "description": desc, "exchange_contract": contract, "admission": adm, "artefacts": files,
                   "drop_site_facts": list(drop_facts), "inventory": inventory(files) if inventory else None}

    case("NR01_artefact_missing", "C16_RECEIPT_UNRESOLVED", "the G01 artefact is absent",
         extra=lambda f, a: f.pop(receipts.artefact_path(a["G01_HASH_VERIFIED"])))
    case("NR02_kind_inconsistent_with_gate", "SCHEMA", "an artefact claims gate G01 with kind FORMAT_DETECTION",
         mutate_arts=lambda a: a["G01_HASH_VERIFIED"].update(receipt_kind="FORMAT_DETECTION"))
    case("NR03_another_copy", "C16_RECEIPT_FIELD_MISMATCH", "the hash artefact is about another copy",
         mutate_arts=lambda a: (a["G01_HASH_VERIFIED"]["subject"].update(source_copy_sha256=H("another-copy")),
                                a["G01_HASH_VERIFIED"]["payload"].update(measured_sha256=H("another-copy"))),
         mutate_adm=lambda adm, a: next(g for g in adm["gates"] if g["gate_id"] == "G01_HASH_VERIFIED")["receipt"].update(subject_sha256=bf.SHA["official-pdf"]))
    case("NR04_another_derivative", "C16_RECEIPT_FIELD_MISMATCH", "the derivative artefact names another derivative",
         mutate_arts=lambda a: a["G06_TEXT_DERIVATIVE_VERIFIED"].update(derivative_sha256=H("another-derivative")),
         mutate_adm=lambda adm, a: next(g for g in adm["gates"] if g["gate_id"] == "G06_TEXT_DERIVATIVE_VERIFIED")["receipt"].update(
             derivative_sha256=adm["gates"][0]["receipt"]["derivative_sha256"] or H("derivative:%s:mimamsa-corpus-text:1.0.0" % bf.DOC["official-pdf"])))
    case("NR05_stale_register_revision", "C16_RECEIPT_REGISTER", "the register receipt is for an older register revision",
         mutate_arts=lambda a: a["G03_RESTRICTED_REGISTER"].update(register_sha256=H("older-register")))
    case("NR06_fail_outcome_under_pass_gate", "C16_RECEIPT_FIELD_MISMATCH", "the register artefact records FAIL (one match) under a PASS gate",
         mutate_arts=lambda a: (a["G03_RESTRICTED_REGISTER"].update(outcome="FAIL"), a["G03_RESTRICTED_REGISTER"]["payload"].update(matches=1)),
         mutate_adm=lambda adm, a: next(g for g in adm["gates"] if g["gate_id"] == "G03_RESTRICTED_REGISTER")["receipt"].update(outcome="PASS"))
    case("NR07_rule_version_differs", "C16_RECEIPT_FIELD_MISMATCH", "the artefact was produced by another rule version",
         mutate_arts=lambda a: a["G02_FORMAT_DETECTED"]["rule"].update(version="9.9"),
         mutate_adm=lambda adm, a: next(g for g in adm["gates"] if g["gate_id"] == "G02_FORMAT_DETECTED")["receipt"].update(rule_version="1.0"))
    case("NR08_config_differs", "C16_RECEIPT_FIELD_MISMATCH", "the artefact used another configuration",
         mutate_arts=lambda a: a["G02_FORMAT_DETECTED"].update(config_sha256=H("other-config")),
         mutate_adm=lambda adm, a: next(g for g in adm["gates"] if g["gate_id"] == "G02_FORMAT_DETECTED")["receipt"].update(config_sha256=H("gate-config")))
    case("NR09_artefact_of_another_gate_reused", "C16_RECEIPT_FIELD_MISMATCH", "the G02 receipt points at the G01 artefact",
         mutate_adm=lambda adm, a: next(g for g in adm["gates"] if g["gate_id"] == "G02_FORMAT_DETECTED")["receipt"].update(
             receipt_sha256=receipts.artefact_sha256(a["G01_HASH_VERIFIED"])))
    case("NR10_measured_hash_not_the_copy", "C16_RECEIPT_PAYLOAD", "re-download measured another hash but claims PASS",
         mutate_arts=lambda a: a["G01_HASH_VERIFIED"]["payload"].update(measured_sha256=H("tampered-bytes")))
    case("NR11_artefact_outside_receipts_namespace", "C16_RECEIPT_PATH", "the artefact is stored outside registers/receipts/",
         extra=lambda f, a: f.update({"registers/other/" + receipts.artefact_sha256(a["G01_HASH_VERIFIED"]) + ".json":
                                      f.pop(receipts.artefact_path(a["G01_HASH_VERIFIED"]))}))
    case("NR12_artefact_not_in_inventory", "C16_RECEIPT_NOT_IN_INVENTORY", "the artefact is not in the ADMISSION_REGISTER inventory",
         inventory=lambda f: sorted(p for p in f if not p.endswith(receipts.artefact_sha256(arts["G01_HASH_VERIFIED"]) + ".json")))
    case("NR13_contract_2_0_exchange", "C16_RECEIPTS_REQUIRE_2_1", "a 2.0 exchange with an eligible admission", contract="mimamsa-corpus-contract/2.0")
    case("NR14_site_recomputation_differs", "C16_RECEIPT_SITE_MISMATCH", "the site's recomputed format differs",
         mutate_arts=lambda a: a["G02_FORMAT_DETECTED"]["payload"].update(magic_hex="504b0304"))
    case("NR15_site_fact_missing", "C16_RECEIPT_UNVERIFIABLE", "the site supplied no recomputed hash", drop_facts=["HASH_REDOWNLOAD"])

    def supersede(f, a):
        r2 = copy.deepcopy(a["G01_HASH_VERIFIED"])
        r2.update(revision=2, supersedes_receipt_sha256=receipts.artefact_sha256(a["G01_HASH_VERIFIED"]))
        f[receipts.artefact_path(r2)] = receipts.artefact_bytes(r2).decode("utf-8")
    case("NR16_superseded_revision_referenced", "C16_RECEIPT_SUPERSEDED", "the admission references revision 1 although revision 2 exists", extra=supersede)

    def pretty(f, a):
        p = receipts.artefact_path(a["G02_FORMAT_DETECTED"])
        f.pop(p)
        text = json.dumps(a["G02_FORMAT_DETECTED"], indent=1, sort_keys=True)
        import hashlib
        f["registers/receipts/" + hashlib.sha256(text.encode()).hexdigest() + ".json"] = text
    case("NR17_non_canonical_artefact", "C16_RECEIPT_NOT_CANONICAL", "an artefact stored in non-canonical form", extra=pretty)
    case("NR18_identity_receipt_for_another_record", "C16_RECEIPT_PAYLOAD", "the identity receipt hashes another identity record",
         mutate_arts=lambda a: a["G05_IDENTITY_RECORD_VALID"]["payload"].update(identity_record_sha256=H("another-identity")))
    return N


# ----------------------------------------------------------------------------- knowledge rows
def allowlist():
    t = lambda table, owner, pk, der: {"table": table, "owner_component": owner, "primary_key": pk, "row_schema": f"#/$defs/{table}_row", "derivation": der}  # noqa: E731
    return {"contract": C21, "record_kind": "knowledge_rows_allowlist", "knowledge_schema_version": 1,
            "tables": [t("document_identities", "KNOWLEDGE_ROWS", ["doc_id"], "PYTHON_REFERENCE"),
                       t("evidence_anchors", "KNOWLEDGE_ROWS", ["anchor_id"], "PYTHON_REFERENCE"),
                       t("corpus_relationships", "KNOWLEDGE_ROWS", ["relationship_id"], "PYTHON_REFERENCE"),
                       t("taxonomy_nodes", "KNOWLEDGE_ROWS", ["node_id"], "PYTHON_REFERENCE"),
                       t("corpus_admissions", "KNOWLEDGE_ROWS", ["admission_id"], "PYTHON_REFERENCE"),
                       t("candidates", "KNOWLEDGE_ROWS", ["candidate_id"], "DOTNET_B03"),
                       t("provision_versions", "KNOWLEDGE_ROWS", ["version_id"], "DOTNET_B03"),
                       t("graph_nodes", "GRAPH", ["id"], "DOTNET_B03"),
                       t("graph_edges", "GRAPH", ["id"], "DOTNET_B03")],
            "loader": {"role": "mimamsa_kr_loader", "role_attributes": ["NOSUPERUSER", "NOCREATEROLE", "NOCREATEDB", "NOREPLICATION", "NOBYPASSRLS", "NOINHERIT"],
                       "grants": ["USAGE ON SCHEMA kr_<n>_staging", "INSERT ON ALL TABLES IN SCHEMA kr_<n>_staging"],
                       "staging_schema_pattern": "^kr_[0-9]{1,9}_staging$", "load_method": "PARAMETERISED_COPY_FROM_STDIN",
                       "forbidden": ["site schema access", "knowledge schema access", "other kr_ schemas", "CREATE FUNCTION", "CREATE TRIGGER",
                                     "CREATE RULE", "CREATE EXTENSION", "SET ROLE", "DDL of any kind"]}}


# ----------------------------------------------------------------------------- build spec
def build_spec():
    return {"contract": C21, "record_kind": "mkr_build_spec", "build_id": "B-20261201-fixture", "pinned_build_time": "2026-12-01T00:00:00Z",
            "release": {"release_id": "R16-knowledge-20261201-0a0b0c0d", "release_sequence": 16, "base_mode": "FULL", "base_release_id": None, "signing_mode": "DEVELOPMENT"},
            "inputs": {"producer_generations": [{"corpus_generation_id": bf.CG, "generation_manifest_sha256": H("generation-manifest"),
                                                 "hf_repo": "owner/fixture-corpus", "hf_revision": H("hf-revision")[:40], "path": "exchanges/fixture/GENERATION.json"}],
                       "hf": [{"repo": "owner/fixture-corpus", "revision": H("hf-revision")[:40], "purpose": "canonical corpus and producer exchange"}],
                       "git": [{"commit": bf.GIT_PIN, "purpose": "contract, tools and build code"}], "restricted_register_sha256": REGISTER,
                       "contracts": {"v1": "1.0.0", "corpus": C21},
                       "models": [{"role": "EMBEDDER", "model_id": "multilingual-e5-small (fixture)", "sha256": H("model:e5-small-onnx")}],
                       "tools": [{"name": "mimamsa_kbuild", "version": "0.1.0", "commit": "c8fa5290", "config_sha256": None}]},
            "stages": [{"stage_id": s, "name": n, "network": s == "S1", "max_workers": 2 if s in ("S3", "S6") else 1} for s, n in STAGES],
            "resources": {"shared_host": True, "measured_logical_cpus": 12, "measured_memory_bytes": 16 * 2**30, "max_workers": 2,
                          "max_memory_bytes": 6 * 2**30, "max_disk_bytes": 200 * 2**30, "cpu_priority": "BELOW_NORMAL", "io_priority": "LOW"},
            "output_dir": "build/B-20261201-fixture"}


def stage_manifests(spec):
    out, prev = {}, None
    for sid, name in STAGES:
        m = make_stage_manifest(spec, sid, prev, [{"path": f"build/{spec['build_id']}/{sid}/{name}.out", "sha256": H(f"stage:{sid}"), "bytes": 100}],
                                [{"name": "mimamsa_kbuild", "version": "0.1.0", "commit": "c8fa5290", "config_sha256": None}])
        out[sid] = m
        prev = m
    return out


# ----------------------------------------------------------------------------- scenarios
def scn(sid, covers, desc, steps, final, **init):
    initial = {"installed": ["R1", "R2", "R3"], "active": "R1", "models": "M1",
               "staged_models": {"M1": {"verified": True, "vectors_for": ["R1", "R2", "R3"]}, "M2": {"verified": True, "vectors_for": ["R1", "R2", "R3"]}},
               "keep_previous": 2, "free_bytes": 10**12, "sizes": {}, "recovery_target": None, "lock_stale_after_seconds": 30}
    initial.update(init)
    return {"contract": C21, "record_kind": "activation_scenario", "scenario_id": sid, "covers": covers, "description": desc,
            "initial": initial, "steps": [{"op": o, "args": a, "expect_error": e} for o, a, e in steps], "assert_final": final}


W1, W2 = {"writer": "activator-1"}, {"writer": "activator-2"}


def scenario_list():
    S = []
    for i, step in enumerate(("BEGIN", "DECIDED", "DB_APPLIED", "POINTER_WRITTEN", "EXCLUSIONS_APPLIED", "LOGGED", "OPEN"), 1):
        S.append(scn(f"SC{i:02d}-crash-after-{step.lower().replace('_', '-')}", ["CRASH_BOUNDARY"],
                     f"Crash after {step}; nothing is served until recovery; DECIDED is the commit decision.",
                     [("lock_acquire", W1, None), ("transition", dict(W1, target="KNOWLEDGE", to="R2", crash_after=step), "Crash"),
                      ("pin", {}, "Refused"), ("recover", W1, None), ("recover", W1, None), ("pin", {}, None)],
                     {"knowledge": "R1" if step == "BEGIN" else "R2", "serving": True, "temp_empty": True}))
    S.append(scn("SC08-exclusion-mid-switch", ["EXCLUSION_MID_SWITCH", "RESPONSE_BOUNDARY_EXCLUSION"],
                 "An exclusion accepted between LOGGED and OPEN is applied before exposure.",
                 [("lock_acquire", W1, None), ("transition", dict(W1, target="KNOWLEDGE", to="R2", exclusion_at_step="LOGGED", exclusion_items=["doc-x"]), None),
                  ("pin", {}, None), ("respond", {"items": ["doc-x", "doc-y"]}, None)],
                 {"knowledge": "R2", "last_response": ["doc-y"]}))
    S.append(scn("SC09-lock-contention", ["LOCK_CONTENTION"], "A second writer cannot take a live lock or transition.",
                 [("lock_acquire", W1, None), ("lock_acquire", W2, "Refused"), ("transition", dict(W2, target="KNOWLEDGE", to="R2"), "Refused"),
                  ("transition", dict(W1, target="KNOWLEDGE", to="R2"), None)], {"knowledge": "R2", "serving": True}))
    S.append(scn("SC10-stale-process-dies", ["STALE_PROCESS", "CRASH_BOUNDARY"],
                 "The writer dies after DECIDED; a new writer takes over (new epoch), must recover, and the dead writer is refused.",
                 [("lock_acquire", W1, None), ("transition", dict(W1, target="KNOWLEDGE", to="R2", crash_after="DECIDED"), "Crash"),
                  ("process_die", W1, None), ("lock_acquire", W2, None), ("pin", {}, "Refused"),
                  ("transition", dict(W1, target="KNOWLEDGE", to="R3"), "Refused"), ("recover", W2, None), ("pin", {}, None)],
                 {"knowledge": "R2", "serving": True}))
    S.append(scn("SC11-stale-heartbeat-takeover", ["STALE_PROCESS"], "A holder silent beyond the stale bound is taken over; recovery precedes any transition.",
                 [("lock_acquire", W1, None), ("clock_advance", {"seconds": 31}, None), ("lock_acquire", W2, None),
                  ("transition", dict(W2, target="KNOWLEDGE", to="R2"), "Refused"), ("recover", W2, None),
                  ("transition", dict(W2, target="KNOWLEDGE", to="R2"), None)], {"knowledge": "R2", "serving": True}))
    S.append(scn("SC12-participant-lost-before-begin", ["PARTICIPANT_LOSS"], "Without the web participant nothing is journaled.",
                 [("lock_acquire", W1, None), ("participant_lose", {}, None), ("transition", dict(W1, target="KNOWLEDGE", to="R2"), "Refused"),
                  ("participant_restore", {}, None), ("transition", dict(W1, target="KNOWLEDGE", to="R2"), None)], {"knowledge": "R2", "log_length": 1}))
    S.append(scn("SC13-participant-lost-after-decided", ["PARTICIPANT_LOSS"],
                 "The decision stands; nothing is served until the participant is back on the journal head.",
                 [("lock_acquire", W1, None), ("transition", dict(W1, target="KNOWLEDGE", to="R2", participant_lost_at="DECIDED"), None),
                  ("pin", {}, "Refused"), ("participant_restore", {}, None), ("pin", {}, None)], {"knowledge": "R2", "serving": True}))
    S.append(scn("SC14-torn-decided", ["TORN_JOURNAL"], "A torn DECIDED record is absent: the transaction aborts.",
                 [("lock_acquire", W1, None), ("transition", dict(W1, target="KNOWLEDGE", to="R2", crash_after="DECIDED"), "Crash"),
                  ("tear_journal_tail", {}, None), ("recover", W1, None), ("pin", {}, None)], {"knowledge": "R1", "serving": True}))
    S.append(scn("SC15-torn-open", ["TORN_JOURNAL"], "A torn OPEN record is absent: the decided transaction rolls forward again.",
                 [("lock_acquire", W1, None), ("transition", dict(W1, target="KNOWLEDGE", to="R2", crash_after="OPEN"), "Crash"),
                  ("tear_journal_tail", {}, None), ("recover", W1, None), ("pin", {}, None)], {"knowledge": "R2", "serving": True, "log_length": 1}))
    S.append(scn("SC16-journal-corruption-fails-closed", ["JOURNAL_CORRUPTION"], "Damage other than a torn tail fails closed.",
                 [("lock_acquire", W1, None), ("transition", dict(W1, target="KNOWLEDGE", to="R2"), None), ("corrupt_journal_middle", {}, None),
                  ("recover", W1, "Refused"), ("pin", {}, "Refused")], {"serving": False}))
    S.append(scn("SC17-pinned-reader-new-exclusion", ["RESPONSE_BOUNDARY_EXCLUSION"], "A reader pinned before an exclusion never bypasses it.",
                 [("pin", {}, None), ("accept_exclusion", {"items": ["doc-x"]}, None), ("respond", {"items": ["doc-x", "doc-y"]}, None)],
                 {"last_response": ["doc-y"]}))
    S.append(scn("SC18-exclusion-store-missing", ["EXCLUSION_READER_FAIL_CLOSED"], "A missing store fails closed for pins, responses and transitions.",
                 [("lock_acquire", W1, None), ("exclusion_store_remove", {}, None), ("pin", {}, "Refused"),
                  ("transition", dict(W1, target="KNOWLEDGE", to="R2"), "Refused"), ("exclusion_store_restore", {}, None), ("pin", {}, None)],
                 {"knowledge": "R1", "serving": True}))
    S.append(scn("SC19-exclusion-store-regressed", ["EXCLUSION_READER_FAIL_CLOSED"], "A store older than the state already seen (non-monotone) fails closed.",
                 [("accept_exclusion", {"items": ["doc-x"]}, None), ("pin", {}, None), ("exclusion_store_regress", {}, None),
                  ("respond", {"items": ["doc-x"]}, "Refused"), ("pin", {}, "Refused")], {"serving": False}))
    S.append(scn("SC20-exclusion-signature-invalid", ["EXCLUSION_READER_FAIL_CLOSED"], "A store whose signature does not verify fails closed.",
                 [("exclusion_signature_invalidate", {}, None), ("pin", {}, "Refused")], {"serving": False}))
    S.append(scn("SC21-model-switch-crash", ["MODEL_SWITCH", "CRASH_BOUNDARY"], "A MODELS transaction crashing after DB_APPLIED rolls forward.",
                 [("lock_acquire", W1, None), ("transition", dict(W1, target="MODELS", to="M2", crash_after="DB_APPLIED"), "Crash"),
                  ("recover", W1, None), ("pin", {}, None)], {"models": "M2", "knowledge": "R1", "serving": True}))
    S.append(scn("SC22-model-without-vectors", ["MODEL_SWITCH"], "A model without verified vectors for the active generation is refused.",
                 [("lock_acquire", W1, None), ("transition", dict(W1, target="MODELS", to="M3"), "Refused")], {"models": "M1"},
                 staged_models={"M1": {"verified": True, "vectors_for": ["R1", "R2", "R3"]}, "M3": {"verified": True, "vectors_for": ["R2"]}}))
    S.append(scn("SC23-rollback-distinct-retention", ["ROLLBACK", "RETENTION"],
                 "Rollback history repeats ids; retention keeps active plus two previous distinct releases and the recovery target.",
                 [("lock_acquire", W1, None), ("transition", dict(W1, target="KNOWLEDGE", to="R2"), None),
                  ("transition", dict(W1, target="KNOWLEDGE", to="R1", action="ROLLBACK"), None), ("transition", dict(W1, target="KNOWLEDGE", to="R2"), None),
                  ("transition", dict(W1, target="KNOWLEDGE", to="R3"), None), ("prune", {}, None)],
                 {"knowledge": "R3", "installed": ["R0", "R1", "R2", "R3"]},
                 installed=["R0", "R1", "R2", "R3", "R4"], recovery_target="R0",
                 staged_models={"M1": {"verified": True, "vectors_for": ["R0", "R1", "R2", "R3", "R4"]}}))
    S.append(scn("SC24-restore-follows-journal-head", ["RESTORE"], "A restored database follows the journal head and the latest exclusions.",
                 [("lock_acquire", W1, None), ("backup", {"name": "b1"}, None), ("transition", dict(W1, target="KNOWLEDGE", to="R2"), None),
                  ("accept_exclusion", {"items": ["doc-z"]}, None), ("restore", dict(W1, name="b1"), None), ("pin", {}, None),
                  ("respond", {"items": ["doc-z", "doc-y"]}, None)], {"knowledge": "R2", "last_response": ["doc-y"]}))
    S.append(scn("SC25-disk-preflight-refusal", ["DISK_PREFLIGHT"], "Measured bytes still to materialise plus headroom exceed free space: refused.",
                 [("lock_acquire", W1, None), ("transition", dict(W1, target="KNOWLEDGE", to="R2"), "Refused")], {"knowledge": "R1", "log_length": 0},
                 sizes={"R1": 40, "R2": 60}, free_bytes=10))
    return S


# ----------------------------------------------------------------------------- component contracts and CP-1
def component_contracts():
    def chk(cid, verifies, method, sel="FULL", size="ALL", tol="EXACT"):
        return {"check_id": cid, "verifies": verifies, "method": method, "sample": {"selection": sel, "size": size, "tolerance": tol}}
    U = "UNCALIBRATED"
    seeded = "DETERMINISTIC_SEEDED_BY_RELEASE_ID"
    return {
        "KNOWLEDGE_ROWS": [chk("SHA256_EACH_FILE", "every row file is the signed byte sequence", "sha256 of each file against the component inventory"),
                           chk("ROW_COUNTS", "row counts per table equal the manifest", "count rows in the staging schema after COPY"),
                           chk("ROWS_ALLOWLIST_AND_TYPES", "only allowlisted tables and typed columns are loaded", "knowledge_rows.row_file_issues before COPY"),
                           chk("ROWS_REDERIVE_COMPARE", "every row equals the row re-derived from authoritative records", "re-derive all rows and compare canonical bytes"),
                           chk("SOURCE_DIGEST_EQUALS_SITE", "built from the same authoritative inputs", "recompute the source digest from the verified generation")],
        "TEXT_STORE": [chk("SHA256_EACH_FILE", "store files are the signed bytes", "sha256 per file"),
                       chk("SQLITE_QUICK_CHECK", "the SQLite file is structurally sound", "PRAGMA quick_check"),
                       chk("TEXT_STORE_BIND_EXACT", "store metadata equals the generation's records exactly", "DiskTextStore.Bind on every open (ADR-0008)"),
                       chk("PAGE_HASH_ON_READ", "every page read equals the verified derivative bytes", "per-page hash check on read"),
                       chk("SOURCE_DIGEST_EQUALS_SITE", "built from the same generation's derivative records",
                           "digests.text_store_source_digest recomputed (bundle-independent, 2.1); Bind still re-derives on every open")],
        "LEXICAL_INDEX": [chk("SHA256_EACH_FILE", "index files are the signed bytes", "sha256 per file"),
                          chk("SQLITE_QUICK_CHECK", "the SQLite file is structurally sound", "PRAGMA quick_check"),
                          chk("SAMPLED_POSTINGS_REDERIVE", "postings of sampled documents equal a fresh tokenisation", "re-tokenise a seeded document sample and compare postings", seeded, U, "EXACT"),
                          chk("SAMPLED_QUERY_PARITY", "sampled queries rank identically to the memory evaluator", "run a seeded query sample against both engines", seeded, U, "EXACT"),
                          chk("SOURCE_DIGEST_EQUALS_SITE", "built from the same generation", "ADR-0007 source digest recomputed")],
        "VECTOR_PACK": [chk("SHA256_EACH_FILE", "vector files are the signed bytes", "sha256 per file"),
                        chk("VECTOR_TRAILER", "the MIMVEC01 trailer verifies", "SHA-256 trailer check"),
                        chk("VECTOR_KEYS_RECOMPUTED", "every vector key belongs to a verified passage and the pinned model", "recompute every key from verified passage text and model sha256"),
                        chk("VECTOR_SPOT_REEMBED", "sampled vectors equal a fresh embedding within tolerance", "re-embed a stratified seeded sample on site", "DETERMINISTIC_STRATIFIED_SEEDED_BY_RELEASE_ID", U, U),
                        chk("SOURCE_DIGEST_EQUALS_SITE", "built for the same passages", "recompute the sorted key set")],
        "GRAPH": [chk("SHA256_EACH_FILE", "graph row files are the signed bytes", "sha256 per file"),
                  chk("GRAPH_DIGEST", "the GraphStore digest equals the manifest", "GraphStore.VerifyAsync"),
                  chk("GRAPH_STRUCTURAL_RECHECK", "endpoints exist, evidence anchors resolve, verification values are builder-only", "check every node and edge"),
                  chk("SAMPLED_REBUILD_PARITY", "sampled source records rebuild to identical edges", "GraphBuilder on a seeded sample of source records", seeded, U, "EXACT"),
                  chk("SOURCE_DIGEST_EQUALS_SITE", "built from the same records and builder version", "recompute the source digest")],
    }


def cp1_manifest(al, row_files: dict[str, bytes]):
    """CP-1 (2.1 clarification 4): graph_nodes and graph_edges are GRAPH tables under accelerators/graph/ (shared typed
    loader), never KNOWLEDGE_ROWS tables. The KNOWLEDGE_ROWS component carries the real reference row files and its
    result_digest is digests.table_rows_digest over them. The admission register carries the accounting register."""
    cp1 = bf.knowledge_manifest("FULL", level="DEGRADED_LEXICAL_ONLY", vectors=False)
    kr = [{"table": t, "file": f"accelerators/rows/{t}.jsonl", "row_count": row_files[t].count(b"\n"),
           "rows_sha256": knowledge_rows.rows_sha256(row_files[t])} for t in sorted(row_files)]
    gt = [{"table": t, "file": f"accelerators/graph/{t}.jsonl", "row_count": 10, "rows_sha256": H("rows:" + t)}
          for t in sorted(tb["table"] for tb in al["tables"] if tb["owner_component"] == "GRAPH")]
    for i, c in enumerate(cp1["components"]):
        if c["kind"] == "KNOWLEDGE_ROWS":
            n = bf.component("knowledge-rows", "KNOWLEDGE_ROWS", "mimamsa-knowledge-rows/1", [r["file"] for r in kr], tables=kr,
                             count=sum(r["row_count"] for r in kr))
            n["files"] = [{"path": r["file"], "sha256": r["rows_sha256"], "bytes": len(row_files[r["table"]])} for r in kr]
            n["result_digest"] = digests.table_rows_digest([(r["table"], r["row_count"], r["rows_sha256"]) for r in kr])
            cp1["components"][i] = n
        elif c["kind"] == "GRAPH":
            cp1["components"][i] = bf.component("graph", "GRAPH", "c15-graph-rows-v1", [r["file"] for r in gt], tables=gt,
                                                count=sum(r["row_count"] for r in gt))
        elif c["kind"] == "ADMISSION_REGISTER":
            c["files"].append(bf.fe(accounting.FILE))
    cp1["notes"] = ("CP-1 fixture vertical slice: explicitly degraded (no vectors, uncalibrated samples); never ACTIVE_FULL; closes no FG "
                    "on real data. Graph tables belong to GRAPH (I-2).")
    return cp1


# ----------------------------------------------------------------------------- accounting register (clarification 1)
V1_HF = "v1:hf:hariomahlawat/mimamsa-corpus@" + "a" * 40


def _src(source, path, *, prov=None, n, held=0, rejected=0, quarantined=0, served=None, by_decision=None, reasons=None):
    eligible = n - held - rejected - quarantined
    served = eligible if served is None else served
    nsr = dict(reasons or {})
    for k, v in (("HELD", held), ("REJECTED", rejected), ("QUARANTINED", quarantined), ("ELIGIBLE_NOT_SERVED", eligible - served)):
        if v and k not in nsr:
            nsr[k] = v
    return {"source": source, "path": path, "provenance": prov, "input": n, "identities": n,
            "effective_admissions": n if path == "C16" else 0, "by_decision": by_decision or {}, "held": held, "rejected": rejected,
            "quarantined": quarantined, "eligible": eligible, "served": served, "not_served_reasons": nsr}


def accounting_declared():
    P = lambda **k: {"generation_manifest_sha256": None, "hf_repo": None, "hf_revision": None, "candidate_set_sha256": None, **k}  # noqa: E731
    src = [
        _src("c16:" + bf.CG, "C16", prov=P(generation_manifest_sha256=H("generation-manifest"), hf_repo="hariomahlawat/mimamsa-corpus",
                                           hf_revision="b" * 40),
             n=12, held=2, rejected=1, quarantined=1, served=7, by_decision={"ADMIT": 8, "HOLD": 2, "QUARANTINE": 1, "REJECT": 1}),
        _src(V1_HF, "V1", prov=P(hf_repo="hariomahlawat/mimamsa-corpus", hf_revision="a" * 40), n=20, held=1, served=19),
        _src("v7:candidates-2026", "V7_REFERENCE", prov=P(candidate_set_sha256=H("v7-candidate-set")), n=5, held=5,
             reasons={"HELD": 5}),
    ]
    src.sort(key=lambda s: s["source"])
    return {"contract": C21, "record_kind": "source_admission_accounting", "release_id": bf.REL_FULL, "scope": "DECLARED_BY_BUILD", "sources": src}


def accounting_fixtures() -> dict[str, dict]:
    d = accounting_declared()
    r = copy.deepcopy(d)
    r["scope"] = "RECOMPUTED_BY_SITE"
    c16 = next(s for s in r["sources"] if s["path"] == "C16")
    c16["served"] -= 1  # the site narrows: one more document withheld by a local exclusion
    c16["not_served_reasons"]["SITE_EXCLUDED"] = 1
    r["sources"].append(_src("site:local-uploads", "SITE_ONLY", n=3, served=3))
    r["sources"].sort(key=lambda s: s["source"])
    out = {"declared": d, "recomputed": r}

    def neg(name, code, mutate, *, compare=False):
        x = copy.deepcopy(r if compare else d)
        mutate(x)
        out[f"negative/{name}"] = {"expected_code": code, "check": "compare_declared" if compare else "accounting_issues",
                                   "register": x, **({"declared": d} if compare else {})}

    def s_of(x, path):
        return next(s for s in x["sources"] if s["path"] == path)
    neg("NA01_identities_differ_from_input", "C16_SOURCE_ACCOUNTING", lambda x: s_of(x, "V1").update(identities=19))
    neg("NA02_partition_does_not_sum", "C16_SOURCE_ACCOUNTING", lambda x: s_of(x, "V1").update(held=2))
    neg("NA03_served_exceeds_eligible", "C16_SOURCE_ACCOUNTING", lambda x: s_of(x, "C16").update(served=9, not_served_reasons={"HELD": 2, "REJECTED": 1}))
    neg("NA04_decisions_do_not_reconcile", "C16_SOURCE_ACCOUNTING", lambda x: s_of(x, "C16")["by_decision"].update(ADMIT=7))
    neg("NA05_v7_served", "SCHEMA", lambda x: s_of(x, "V7_REFERENCE").update(eligible=5, held=0, served=5, not_served_reasons={}))
    neg("NA06_sources_unsorted", "C16_SOURCE_ACCOUNTING", lambda x: x["sources"].reverse())
    neg("NA07_site_only_in_declared", "SCHEMA", lambda x: x["sources"].append(_src("site:local-uploads", "SITE_ONLY", n=1)))
    neg("NA08_b02_legacy_kind", "SCHEMA", lambda x: x.update(record_kind="admission_accounting"))
    neg("NA09_c16_without_generation_pin", "SCHEMA", lambda x: s_of(x, "C16").update(provenance=None))
    neg("NA10_unknown_field", "SCHEMA", lambda x: s_of(x, "V1").update(declared_servable=19))
    neg("NC01_site_widens_service", "C16_SOURCE_ACCOUNTING",
        lambda x: s_of(x, "V1").update(served=20, held=0, eligible=20, not_served_reasons={}), compare=True)
    neg("NC02_site_held_differs", "C16_SOURCE_ACCOUNTING",
        lambda x: s_of(x, "C16").update(held=3, eligible=7, served=6, not_served_reasons={"HELD": 3, "QUARANTINED": 1, "REJECTED": 1, "SITE_EXCLUDED": 1}),
        compare=True)
    neg("NC03_site_missing_source", "C16_SOURCE_ACCOUNTING", lambda x: x["sources"].remove(s_of(x, "V7_REFERENCE")), compare=True)
    neg("NC04_site_unquarantines", "C16_SOURCE_ACCOUNTING",
        lambda x: s_of(x, "C16").update(quarantined=0, eligible=9, not_served_reasons={"HELD": 2, "REJECTED": 1, "ELIGIBLE_NOT_SERVED": 2, "SITE_EXCLUDED": 1}),
        compare=True)
    return out


# ----------------------------------------------------------------------------- digest golden vectors (clarifications 2, 5)
def golden_digests(row_files: dict[str, bytes]):
    G = {"format": "mimamsa-c16-digest-golden/2.1", "reference": "app/contract/mimamsa_contract/c16/digests.py"}
    tables = [(t, row_files[t].count(b"\n"), knowledge_rows.rows_sha256(row_files[t])) for t in sorted(row_files)]
    G["KNOWLEDGE_ROWS"] = {"tables": [{"table": t, "row_count": n, "rows_sha256": s} for t, n, s in tables],
                           "preimage": "".join(f"{t}|{n}|{s}\n" for t, n, s in tables), "digest": digests.table_rows_digest(tables),
                           "wrong_no_final_lf": digests._h("\n".join(f"{t}|{n}|{s}" for t, n, s in tables).encode())}
    nodes, edges = ["GN-b", "GN-a", "GN-c"], ["GE-2", "GE-1"]
    G["GRAPH"] = {"builder_version": "c15-graph-1", "node_ids": nodes, "edge_ids": edges,
                  "preimage": "c15-graph-1|GN-a,GN-b,GN-c|GE-1,GE-2", "digest": digests.graph_digest("c15-graph-1", nodes, edges)}
    sq = b"SQLite format 3\x00" + bytes(range(16))
    G["LEXICAL_INDEX"] = {"file_hex": sq.hex(), "digest": digests.file_digest(sq)}
    G["TEXT_STORE"] = {"file_hex": sq[::-1].hex(), "digest": digests.file_digest(sq[::-1])}
    import struct
    e = [(bytes([2] + [0] * 15), struct.pack("<2f", 0.5, -1.0)), (bytes([1] + [0] * 15), struct.pack("<2f", 1.0, 0.25))]
    G["VECTOR_PACK"] = {"entries": [{"key_hex": k.hex(), "vector_hex": v.hex()} for k, v in e], "digest": digests.vector_pack_digest(e)}
    hs = [H("o2"), H("o1")]
    G["HASHSET"] = {"hashes": hs, "digest": digests.hashset_digest(hs)}
    cf = {"registers/b.jsonl": b"{\"b\":1}\n", "registers/a.jsonl": b"{\"a\":1}\n"}
    G["CONCAT"] = {"files": {k: v.decode() for k, v in cf.items()}, "digest": digests.concat_digest(cf)}
    docs = [{"doc_id": "doc-b", "copy_sha256": H("copy-b")}, {"doc_id": "doc-a", "copy_sha256": H("copy-a")}]
    der = [{"doc_id": "doc-a", "source_copy_sha256": H("copy-a"), "pipeline": {"name": "pdf-text", "version": "1.2"},
            "text_sha256": H("text-a"), "quoting_permitted": True,
            "pages": [{"page": 2, "method": "pdf_text", "char_count": 40, "text_sha256": H("pa2")},
                      {"page": 1, "method": "pdf_text", "char_count": 50, "text_sha256": H("pa1")}],
            "passages": [{"passage_id": "p1-2", "page": 1, "char_start": 20, "char_end": 50, "text_sha256": H("qa12")},
                         {"passage_id": "p1-1", "page": 1, "char_start": 0, "char_end": 20, "paragraph_label": "1.", "text_sha256": H("qa11")}]},
           {"doc_id": "doc-b", "source_copy_sha256": H("copy-b"), "pipeline": {"name": "ocr", "version": "3.0"},
            "text_sha256": H("text-b"), "quoting_permitted": False,
            "pages": [{"page": 1, "method": "ocr", "char_count": 30, "low_confidence": True, "text_sha256": None}],
            "passages": [{"passage_id": "p1-1", "page": 1, "char_start": 0, "char_end": 30, "text_sha256": H("qb11")}]}]
    G["TEXT_STORE_SOURCE"] = {"generation_id": bf.CG, "documents": docs, "derived": der,
                              "digest": digests.text_store_source_digest(bf.CG, docs, der),
                              "note": "no generation.json and no SHA256SUMS digest enter the preimage; Bind() still re-derives on every open"}
    return G


def outputs() -> dict[str, bytes]:
    ids, pop = population()
    arts, facts = official_artefacts(ids, pop)
    adm = next(a for a in pop["admissions"] if a["application_eligible"])
    bind(adm, arts)
    files = {}
    ex = bf.exchange_files(pop, manifest_edit=lambda m: m.update(contract=C21))
    files.update({f"exchange/{k}": v for k, v in ex.items()})
    for p, text in art_files(arts).items():
        files[p] = text.encode("utf-8")
    files["site_facts.json"] = json.dumps(facts, indent=1, sort_keys=True).encode() + b"\n"
    for name, case in sorted(receipt_negatives(adm, arts).items()):
        files[f"negative_receipts/{name}.json"] = json.dumps(case, indent=1, sort_keys=True).encode() + b"\n"
    al = allowlist()
    files["knowledge_rows/allowlist.json"] = json.dumps(al, indent=1, sort_keys=True).encode() + b"\n"
    derived = knowledge_rows.derive_rows(pop)
    row_files = {}
    for t in al["tables"]:
        if t["derivation"] == "PYTHON_REFERENCE":
            row_files[t["table"]] = knowledge_rows.row_file_bytes(derived[t["table"]], t["primary_key"])
            files[f"knowledge_rows/rows/{t['table']}.jsonl"] = row_files[t["table"]]
    for name, reg in accounting_fixtures().items():
        body = accounting.register_bytes(reg) if name in ("declared", "recomputed") else json.dumps(reg, indent=1, sort_keys=True).encode() + b"\n"
        files[f"accounting/{name}.json"] = body
    files["digests/golden.json"] = json.dumps(golden_digests(row_files), indent=1, sort_keys=True).encode() + b"\n"
    spec = build_spec()
    files["build/spec.json"] = json.dumps(spec, indent=1, sort_keys=True).encode() + b"\n"
    for sid, m in stage_manifests(spec).items():
        files[f"build/stages/{sid}.json"] = json.dumps(m, indent=1, sort_keys=True).encode() + b"\n"
    for s in scenario_list():
        files[f"activation_scenarios/{s['scenario_id']}.json"] = json.dumps(s, indent=1, sort_keys=True).encode() + b"\n"
        files[f"activation_scenarios/{s['scenario_id']}.expected.json"] = json.dumps(scenarios.run_scenario(s), indent=1, sort_keys=True).encode() + b"\n"
    for kind, checks in component_contracts().items():
        c = {"contract": C21, "record_kind": "component_verification_contract", "kind": kind, "checks": checks,
             "on_failure": "SERVE_LEXICAL_ONLY" if kind == "VECTOR_PACK" else "REBUILD_LOCALLY_CHEAP", "site_embedding": "NEVER"}
        files[f"component_contracts/{kind}.json"] = json.dumps(c, indent=1, sort_keys=True).encode() + b"\n"
    cp1 = cp1_manifest(al, row_files)
    files["cp1/KNOWLEDGE_RELEASE.json"] = json.dumps(cp1, indent=1, sort_keys=True).encode() + b"\n"
    rec = bf.activation_record()
    rec["components"] = [{"component_id": c["component_id"], "result": "VERIFIED_USED", "failed_checks": []} for c in cp1["components"]]
    rec["components"].append({"component_id": "vectors-e5", "result": "ACCELERATOR_DEGRADED", "failed_checks": []})
    rec.update(result="ACTIVE_DEGRADED", service_level="DEGRADED_LEXICAL_ONLY", degradation_acknowledged_by="admin-fixture",
               reason="CP-1 fixture slice: no vector pack; lexical-only service; no site embedding", release_id=cp1["release_id"],
               release_sequence=cp1["release_sequence"], previous_active_release_id=None, seq=1, previous_record_sha256=None)
    files["cp1/activation_record.json"] = json.dumps(rec, indent=1, sort_keys=True).encode() + b"\n"
    return files


def main(argv):
    check = "--check" in argv
    out = outputs()
    diff = [p for p, d in sorted(out.items()) if not (OUT / p).is_file() or (OUT / p).read_bytes() != d] if check else []
    stale = sorted(str(p.relative_to(OUT)).replace("\\", "/") for p in OUT.rglob("*") if p.is_file()
                   and str(p.relative_to(OUT)).replace("\\", "/") not in out) if OUT.exists() else []
    if check:
        if diff or stale:
            print("2.1 fixtures differ from builder output:", ", ".join(diff + [f"stale {s}" for s in stale]))
            return 1
        print("2.1 fixtures match builder output")
        return 0
    for p, d in out.items():
        (OUT / p).parent.mkdir(parents=True, exist_ok=True)
        (OUT / p).write_bytes(d)
    for s in stale:
        (OUT / s).unlink()
    print("2.1 fixtures written")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
