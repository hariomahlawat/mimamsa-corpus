"""B01 site importer for contract 2.0/2.1 (Tranche B Stage 2): strict and signed-import validation, typed receipts
(I-1), byte checks (I4, I8), label readings (D1, D2), I-5 legacy rules (SG-1), per-source accounting, crash points.

Two kinds of input:
- the contract fixtures (app/contract/fixtures/c16, 2.0 and 2.1, NR01-NR18, N01-N54, X01-X35), which carry no
  original bytes: receipt resolution is driven with the fixtures' stand-in site facts, never in the import path;
- the synthetic real-bytes exchange (c16_cases.py), imported end to end through signed development bundles.
"""
from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import c16_cases as cc  # noqa: E402
from mimamsa_contract.c16 import adapters, canonical, receipts  # noqa: E402
from mimamsa_contract.exclusions import ExclusionState  # noqa: E402
from mimamsa_importer import ImporterError, active_generation, c16, cite, held_copies, importer, safe_archive, servable  # noqa: E402

FIX = HERE.parent / "contract" / "fixtures" / "c16"
V21 = FIX / "v2_1"
MANIFEST = json.loads((FIX / "FIXTURES.json").read_text(encoding="utf-8"))
FIX_REGISTER = json.loads((V21 / "exchange" / "GENERATION.json").read_text(encoding="utf-8"))["pinned_inputs"]["restricted_register_sha256"]
OFFICIAL = "sc-2019-example-v-union-of-india-ca0001"
CP = cc.Corpus()
DOC_E = adapters.local_doc_id(cc.h(CP.e))


def _j(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def _jl(b: bytes):
    return [json.loads(x) for x in b.decode("utf-8").split("\n") if x]


def snapshot(site: Path) -> dict:
    """Byte-for-byte state of a site directory (path -> sha256)."""
    if not site.exists():
        return {}
    return {p.relative_to(site).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(site.rglob("*")) if p.is_file()}


def sv(site, kind, item):
    return servable(site, kind, item, exclusions=None)


@pytest.fixture
def hn(tmp_path):
    return cc.C16Harness(tmp_path / "work")


# ============================================================ contract fixtures (no bytes: stand-in site facts)

class FixtureRegister:
    """Stand-in for the site register pinned by the fixtures (their GENERATION.json register revision)."""
    config_sha256 = FIX_REGISTER

    def match(self, **_):
        return None

    def deep_match(self, _):
        return None

    def is_restricted(self, **_):
        return False


def fixture_facts(drop=()):
    return {(f["source_copy_sha256"], f["receipt_kind"]): f["fact"] for f in _j(V21 / "site_facts.json") if f["receipt_kind"] not in drop}


def regenerate_manifest(files: dict[str, bytes]) -> dict[str, bytes]:
    """Recompute GENERATION.json's file list after a population file changed (as an honest producer would)."""
    man = json.loads(files["GENERATION.json"])
    stems = {"identities": "document_identity", "anchors": "evidence_anchor", "relationships": "corpus_relationship",
             "taxonomy": "taxonomy_node", "admissions": "corpus_admission", "reviewed_records": "reviewed_record"}
    man["files"] = [{"path": n, "record_kind": stems[n.split(".")[0]], "sha256": hashlib.sha256(b).hexdigest(),
                     "records": sum(1 for x in b.split(b"\n") if x)} for n, b in sorted(files.items()) if n.split(".")[0] in stems]
    out = dict(files)
    out["GENERATION.json"] = json.dumps(man, indent=1, sort_keys=True).encode() + b"\n"
    return out


def fixture_exchange() -> dict[str, bytes]:
    return {p.name: p.read_bytes() for p in sorted((V21 / "exchange").iterdir())}


def fixture_artefacts() -> dict[str, bytes]:
    return {f"registers/receipts/{p.name}": p.read_bytes() for p in sorted((V21 / "registers" / "receipts").iterdir())}


STAGE_RELEASE = "R16-fixture-20261127-00000001"


def fixture_accounting(exchange: dict[str, bytes], release_id=STAGE_RELEASE):
    """The 2.1 declared register for a contract fixture exchange (no v1 records in a stage-only run)."""
    from mimamsa_contract.c16 import accounting
    decl = json.loads(cc.declared_accounting(release_id, exchange, []))
    gen = json.loads(exchange["GENERATION.json"])["corpus_generation_id"]
    for s in decl["sources"]:   # the contract fixture generation, not the synthetic one
        s["source"] = f"c16:{gen}"
    return accounting.register_bytes(decl)


def run_stage(tmp: Path, exchange: dict[str, bytes], artefacts: dict[str, bytes], *, unlisted=(), facts=None, accounting=None):
    """The C16 stage alone over an unsigned directory (signature and v1 checks are the import path's job)."""
    b = tmp / "bundle"
    files = []
    payload = {**{"corpus-v2/" + n: x for n, x in exchange.items()}, **artefacts,
               "registers/source_accounting.json": accounting or fixture_accounting(exchange)}
    for rel, data in payload.items():
        (b / rel).parent.mkdir(parents=True, exist_ok=True)
        (b / rel).write_bytes(data)
        if rel not in unlisted:
            files.append({"path": rel, "kind": "other"})
    site = tmp / "site"
    site.mkdir(exist_ok=True)
    return c16.run(bundle=b, manifest={"files": files, "release_id": STAGE_RELEASE}, sums={}, site=site, docs=[], verified_docs={},
                   originals={}, copy_pages={}, register=FixtureRegister(), site_facts_override=facts if facts is not None else fixture_facts())


def official(res):
    return next(c for c in res.copies if c["doc_id"] == OFFICIAL)


def test_fixture_2_1_exchange_resolves_with_typed_receipts(tmp_path):
    res = run_stage(tmp_path, fixture_exchange(), fixture_artefacts())
    assert [str(i) for i in res.refusals] == []
    c = official(res)
    assert c["outcome"] == "ELIGIBLE" and not c["served"] and "C16_ONLY_NOT_SERVABLE" in c["codes"]  # no v1 record here
    assert {g for g, v in c["gates"].items() if v == "ASSERTED_BOUND"} == {"G04_ACCESS_MARKING_REVIEWED", "G08_RELEVANCE_ASSESSED",
                                                                          "G09_DUPLICATE_RESOLVED"}
    assert sum(v == "SITE_VERIFIED" for v in c["gates"].values()) == 6
    held = [x for x in res.copies if x["doc_id"] != OFFICIAL]
    assert held and all(not x["served"] and x["outcome"] != "ELIGIBLE" for x in held)


def test_fixture_2_0_exchange_imports_but_nothing_is_eligible(tmp_path):
    """Contract 2.0 carries no artefacts: its eligible admission fails closed (C16_RECEIPTS_REQUIRE_2_1); held,
    rejected and ineligible items stay importable and unserved."""
    ex = {p.name: p.read_bytes() for p in sorted((FIX / "positive" / "exchange").iterdir())}
    res = run_stage(tmp_path, ex, {}, accounting=fixture_accounting(ex))
    assert res.refusals == []
    c = official(res)
    assert c["outcome"] == "QUARANTINED" and "C16_RECEIPTS_REQUIRE_2_1" in c["codes"] and not c["gates"]


NR = sorted(p.stem for p in (V21 / "negative_receipts").iterdir())


@pytest.mark.parametrize("name", NR)
def test_receipt_negatives_fail_closed(tmp_path, name):
    """NR01-NR18: the official copy never becomes eligible. Problems with one admission's resolution quarantine that
    copy (item level); a malformed artefact in the signed admission register refuses the whole bundle."""
    case = _j(V21 / "negative_receipts" / f"{name}.json")
    ex = fixture_exchange()
    adms = [case["admission"] if a["admission_id"] == case["admission"]["admission_id"] else a for a in _jl(ex["admissions.jsonl"])]
    ex["admissions.jsonl"] = canonical.dumps_jsonl(adms)
    if case["exchange_contract"] != cc.C21:
        m = json.loads(ex["GENERATION.json"])
        m["contract"] = case["exchange_contract"]
        ex["GENERATION.json"] = json.dumps(m, indent=1, sort_keys=True).encode() + b"\n"
    ex = regenerate_manifest(ex)
    arts = {p: t.encode("utf-8") for p, t in case["artefacts"].items()}
    unlisted = set(arts) - set(case["inventory"]) if case["inventory"] is not None else set()
    res = run_stage(tmp_path, ex, arts, unlisted=unlisted, facts=fixture_facts(case["drop_site_facts"]))
    if res.refusals:
        # the frozen 2.0 strict rules already refuse some forgeries (C16_RECEIPT_MISMATCH) before 2.1 resolution runs
        codes = {i.code for i in res.refusals}
        assert case["expect_code"] in codes or codes == {"C16_RECEIPT_MISMATCH"}, [str(i) for i in res.refusals]
        assert not res.copies
    else:
        c = official(res)
        assert c["outcome"] == "QUARANTINED" and not c["served"]
        assert case["expect_code"] in c["codes"], c["codes"]


def test_receipt_negatives_cover_item_and_bundle_level(tmp_path):
    """Hash existence alone never passes: with no recomputed facts nothing site-recomputable verifies."""
    res = run_stage(tmp_path, fixture_exchange(), fixture_artefacts(), facts={})
    c = official(res)
    assert c["outcome"] == "QUARANTINED" and "C16_RECEIPT_UNVERIFIABLE" in c["codes"]


# ============================================================ real bytes, signed bundles, full import

def test_e2e_only_admitted_or_established_copies_are_served(hn, tmp_path):
    site = tmp_path / "site"
    r = hn.run(hn.bundle(), site)
    assert r.activated, r.refused_reasons
    assert sorted(r.verified["documents"]) == sorted([cc.DOC_A, cc.DOC_C])
    for doc in (cc.DOC_B, cc.DOC_D, cc.DOC_F, DOC_E):
        assert not sv(site, "documents", doc)
    assert sv(site, "documents", cc.DOC_A) and sv(site, "documents", cc.DOC_C)
    gen = active_generation(site)
    gdir = site / "generations" / gen["release_id"]
    # I5 materialised, verbatim and re-hashable
    for name, sha in gen["materialized"]["corpus_v2"]["files"].items():
        assert hashlib.sha256((gdir / "corpus-v2" / name).read_bytes()).hexdigest() == sha
    assert gen["materialized"]["format"] == 1
    # resolved-receipts register: only for served copies; asserted gates never reported as site-verified
    rr = json.loads((gdir / "c16" / "resolved_receipts.json").read_text())
    assert {x["doc_id"] for x in rr} == {cc.DOC_A}
    assert {x["gate_id"] for x in rr if x["verification"] == "ASSERTED_BOUND"} == {
        "G04_ACCESS_MARKING_REVIEWED", "G08_RELEVANCE_ASSESSED", "G09_DUPLICATE_RESOLVED"}
    for x in rr:
        p = gdir / "registers" / "receipts" / f"{x['receipt_sha256']}.json"
        assert hashlib.sha256(p.read_bytes()).hexdigest() == x["receipt_sha256"]
    e = next(c for c in r.c16["copies"] if c["doc_id"] == DOC_E)
    assert e["outcome"] == "ELIGIBLE" and e["gates"]["G07_EMBEDDED_IMAGES_ACCOUNTED"] == "SITE_VERIFIED" and not e["served"]
    # per-source accounting (2.1): the signed declaration verbatim, the site's recomputation beside it, both digests
    # in the generation record and the import report; the site's register passes R1-R7 and only narrows
    from mimamsa_contract.c16 import accounting
    decl_b = (gdir / "registers" / "source_accounting.json").read_bytes()
    site_b = (gdir / "registers" / "source_accounting.site.json").read_bytes()
    decl, acct = json.loads(decl_b), json.loads(site_b)
    assert decl["scope"] == "DECLARED_BY_BUILD" and acct["scope"] == "RECOMPUTED_BY_SITE"
    assert site_b == accounting.register_bytes(acct) and accounting.accounting_issues(acct) == []
    assert accounting.compare_declared(decl, acct) == []
    assert gen["c16"]["accounting"] == {"declared_sha256": hashlib.sha256(decl_b).hexdigest(),
                                        "site_sha256": hashlib.sha256(site_b).hexdigest()}
    assert r.c16["accounting_digests"] == gen["c16"]["accounting"]
    assert {s["source"]: s["served"] for s in acct["sources"]} == {f"c16:{cc.CG}": 1, "v1:RELEASE_IMPORT": 0, cc.V1_SRC: 1, "v7:cycle15": 0}
    c16src = next(s for s in acct["sources"] if s["path"] == "C16")
    assert c16src["provenance"]["generation_manifest_sha256"] == gen["materialized"]["corpus_v2"]["files"]["GENERATION.json"]
    assert c16src["not_served_reasons"] == {"C16_ONLY_NOT_SERVABLE": 1, "HELD": 1}
    # anchors: byte-verified span on the served copy
    ver = json.loads((gdir / "c16" / "verdicts.json").read_text())
    assert [a["span_verified"] for a in ver["anchors"]] == [True]
    # decision index (site, cross-generation) records every governed copy
    idx = json.loads((site / c16.DECISION_INDEX).read_text())["entries"]
    assert {(e["doc_id"], e["site_outcome"]) for e in idx} == {(cc.DOC_A, "ELIGIBLE"), (cc.DOC_B, "HELD"), (DOC_E, "ELIGIBLE")}
    # held copies (citations) never include an unserved copy
    assert set(held_copies(site)) == {cc.h(CP.a), cc.h(CP.c)}


def test_pure_v1_import_is_unchanged(hn, tmp_path):
    """No corpus-v2, no accounting, site never C16-aware: the existing v1 behaviour, byte for byte the same rules."""
    r = hn.run(hn.bundle(c16=False, accounting_bytes=False), tmp_path / "site")
    assert r.activated and not r.c16.get("active")
    assert sorted(r.verified["documents"]) == sorted([cc.DOC_A, cc.DOC_B, cc.DOC_C, cc.DOC_D, cc.DOC_F])


def refused_untouched(hn, site, bundle_path):
    if not (Path(site) / "SITE_CONFIG.json").exists():
        from mimamsa_importer import configure_site
        configure_site(site, exclusion_channel="none")
    before = snapshot(site)
    r = hn.run(bundle_path, site)
    assert not r.activated and r.refused_reasons
    assert snapshot(site) == before
    return r


@pytest.fixture
def seeded(hn, tmp_path):
    site = tmp_path / "site"
    assert hn.run(hn.bundle(), site).activated
    return site


def test_partial_exchange_refused(hn, seeded):
    files, arts, _, _ = cc.exchange(CP)
    files.pop("GENERATION.json")
    r = refused_untouched(hn, seeded, hn.bundle(exchange_files=files, artefacts=arts))
    assert "C16_MANIFEST" in r.contract_errors


def test_adapter_output_is_partial_and_refused(hn, seeded):
    row = {"sha256": cc.h(CP.e), "relative_path": "Army Rules/AR 22 - Lt Col B01 Example v Union of India.docx", "format": "DOCX",
           "size_bytes": len(CP.e), "disposition": "NEW_DOCUMENT", "inventory_id": cc.INV_E, "embedded_images": []}
    out = adapters.from_pr76_inventory([row], collection=cc.COLL, corpus_generation_id=cc.CG)
    files = {f"{k}.jsonl": canonical.dumps_jsonl(out[k]) for k in ("identities", "admissions", "relationships", "taxonomy") if out[k]}
    r = refused_untouched(hn, seeded, hn.bundle(exchange_files=files, artefacts={}))
    assert "C16_MANIFEST" in r.contract_errors


def test_missing_population_refused(hn, seeded):
    files, arts, _, _ = cc.exchange(CP)
    files.pop("anchors.jsonl")
    m = json.loads(files["GENERATION.json"])
    m["files"] = [f for f in m["files"] if f["path"] != "anchors.jsonl"]
    files["GENERATION.json"] = json.dumps(m).encode()
    r = refused_untouched(hn, seeded, hn.bundle(exchange_files=files, artefacts=arts))
    assert "C16_FILE_MISSING" in r.contract_errors


@pytest.mark.parametrize("contract", ["mimamsa-corpus-contract/3.0", "mimamsa-corpus-contract/2.9"])
def test_unknown_contract_version_refused(hn, seeded, contract):
    files, arts, _, _ = cc.exchange(CP)
    m = json.loads(files["GENERATION.json"])
    m["contract"] = contract
    files["GENERATION.json"] = json.dumps(m).encode()
    r = refused_untouched(hn, seeded, hn.bundle(exchange_files=files, artefacts=arts))
    assert r.contract_errors == ["C16_CONTRACT_UNSUPPORTED"]


def test_c16_files_must_travel_as_kind_other(hn, seeded):
    r = refused_untouched(hn, seeded, hn.bundle(kinds={"corpus-v2/identities.jsonl": "report"}))
    assert "C16_TRANSPORT" in r.contract_errors


def test_unlisted_receipt_artefact_refused(hn, seeded):
    """An artefact present (and checksummed) but not in RELEASE.json's file inventory refuses the bundle."""
    files, arts, _, _ = cc.exchange(CP)
    first = sorted(arts)[0]
    data = arts.pop(first)
    r = refused_untouched(hn, seeded, hn.bundle(exchange_files=files, artefacts=arts, unlisted={first: data}))
    assert "C16_RECEIPT_NOT_IN_INVENTORY" in r.contract_errors


def test_malformed_artefact_anywhere_in_registers_refuses(hn, seeded):
    files, arts, _, _ = cc.exchange(CP)
    p = sorted(arts)[0]
    arts["registers/other/" + p.rsplit("/", 1)[1]] = arts[p]
    r = refused_untouched(hn, seeded, hn.bundle(exchange_files=files, artefacts=arts))
    assert "C16_RECEIPT_PATH" in r.contract_errors


def _gate_path(arts, gate):
    return next(p for p, b in arts.items() if json.loads(b)["gate_id"] == gate and json.loads(b)["subject"]["doc_id"] == cc.DOC_A)


def test_missing_artefact_quarantines_the_copy(hn, tmp_path):
    files, arts, _, _ = cc.exchange(CP)
    arts.pop(_gate_path(arts, "G01_HASH_VERIFIED"))
    site = tmp_path / "s"
    r = hn.run(hn.bundle(exchange_files=files, artefacts=arts), site)
    assert r.activated
    a = next(c for c in r.c16["copies"] if c["doc_id"] == cc.DOC_A)
    assert a["outcome"] == "QUARANTINED" and "C16_RECEIPT_UNRESOLVED" in a["codes"]
    assert not sv(site, "documents", cc.DOC_A) and cc.h(CP.a) not in held_copies(site)


@pytest.mark.parametrize("gate,mutate,code", [
    ("G02_FORMAT_DETECTED", lambda p: p.update(magic_hex="504b030414"), "C16_RECEIPT_SITE_MISMATCH"),
    ("G06_TEXT_DERIVATIVE_VERIFIED", lambda p: p["unit_text_sha256"].reverse(), "C16_RECEIPT_SITE_MISMATCH"),
    ("G01_HASH_VERIFIED", lambda p: p.update(measured_bytes=p["measured_bytes"] + 1), "C16_RECEIPT_PAYLOAD"),
    ("G05_IDENTITY_RECORD_VALID", lambda p: p.update(identity_record_sha256="0" * 64), "C16_RECEIPT_PAYLOAD"),
    ("G10_SCHEMA_VALID", lambda p: p.update(copy_records_sha256="0" * 64), "C16_RECEIPT_PAYLOAD"),
], ids=["format-recomputed", "derivative-units", "hash-size", "identity-record", "copy-records"])
def test_payload_semantics_not_hashes(hn, tmp_path, gate, mutate, code):
    """A correctly named, hashed, bound and canonical artefact whose payload contradicts the bytes or the exchange
    never verifies its gate."""
    def m(key, arts):
        if key == "A":
            mutate(arts[gate]["payload"])
    files, arts, _, _ = cc.exchange(CP, mutate_arts=m)
    site = tmp_path / "s"
    r = hn.run(hn.bundle(exchange_files=files, artefacts=arts), site)
    assert r.activated, r.refused_reasons
    a = next(c for c in r.c16["copies"] if c["doc_id"] == cc.DOC_A)
    assert a["outcome"] == "QUARANTINED" and code in a["codes"] and not sv(site, "documents", cc.DOC_A)


def test_receipts_of_a_2_0_exchange_never_make_a_copy_eligible(hn, tmp_path):
    files, arts, _, _ = cc.exchange(CP, contract="mimamsa-corpus-contract/2.0")
    r = hn.run(hn.bundle(exchange_files=files, artefacts=arts), tmp_path / "s")
    assert r.activated
    a = next(c for c in r.c16["copies"] if c["doc_id"] == cc.DOC_A)
    assert "C16_RECEIPTS_REQUIRE_2_1" in a["codes"] and not a["served"]


def test_docx_image_not_in_container_quarantines(hn, tmp_path):
    """I4: the screenshot inventoried by the producer must be in the Word container at its part (safe zip read)."""
    def m(ids, pop):
        ids["E"]["embedded_images"][0]["image_sha256"] = "1" * 64
    files, arts, _, _ = cc.exchange(CP, mutate=m)
    r = hn.run(hn.bundle(exchange_files=files, artefacts=arts), tmp_path / "s")
    assert r.activated, r.refused_reasons
    e = next(c for c in r.c16["copies"] if c["doc_id"] == DOC_E)
    assert e["outcome"] == "QUARANTINED" and "C16_IMAGE_NOT_IN_CONTAINER" in e["codes"] and "C16_RECEIPT_SITE_MISMATCH" in e["codes"]


# ------------------------------------------------------------ label readings (owner decisions D1, D2)

def _with_relationship(rel_edit=None, path=None, extra_tax=(), tax_edit=None):
    def m(ids, pop):
        if rel_edit:
            for r in pop["relationships"]:
                rel_edit(r)
        pop["taxonomy"].extend(extra_tax)
        if tax_edit:
            for t in pop["taxonomy"]:
                tax_edit(t)
    return cc.exchange(CP, mutate=m, e_path=path)


def _tax_prov(code, prefix, n, parent):
    inst = cc.bf.tax(f"INSTCODE:{code}", "STATUTE", code, ["SUBJ:court_martial"], code=code, basis="GRAPH_INSTRUMENT",
                     verification="CURATED_NAVIGATION")
    prov = cc.bf.tax(f"PROV:{code}:{prefix}.{n}", "PROVISION", f"{prefix} {n}", [f"INSTCODE:{code}"], code=code,
                     prov={"prefix": prefix, "number": n, "sub_provision": None}, basis="GRAPH_PROVISION", verification="EXTRACTED_STRUCTURE")
    return [inst, prov]


def test_bare_aft_read_as_the_act_is_refused(hn, seeded):
    """D2: 'AFT 14 - ...' names the tribunal; a producer reading it as AFT Act s.14 is refused."""
    path = "Tribunal/AFT 14 - Sub B01 Example v Union of India.docx"
    files, arts, ids, _ = _with_relationship(path=path, extra_tax=_tax_prov("AFT-2007", "s", "14", None))
    # forge the reading the pinned rules never make
    rels = _jl(files["relationships.jsonl"])
    base = next(r for r in rels if r["category"] == "classified_under_subject")
    forged = copy.deepcopy(base)
    forged.update(category="associated_with_provision", target={"resolved": True, "node_id": "PROV:AFT-2007:s.14"},
                  evidentiary_basis="FILENAME_PATTERN", verification="CANDIDATE")
    forged["source"]["rule_id"] = "C16-FN-PROVLIST"
    forged["classification_provenance"].update(path_component=-1, matched_text="AFT 14", abbreviation_expansion={
        "abbreviation": "AFT", "expansion": "Armed Forces Tribunal Act, 2007", "lexicon_ref": adapters.ABBREV_LEXICON_REF, "alternatives": []})
    forged["uncertainty"] = "forged"
    forged["relationship_id"] = canonical.relationship_id(forged)
    files["relationships.jsonl"] = canonical.dumps_jsonl(sorted(rels + [forged], key=lambda r: r["relationship_id"]))
    r = refused_untouched(hn, seeded, hn.bundle(exchange_files=regenerate_manifest(files), artefacts=arts))
    assert {"C16_CLASSIFICATION_MISMATCH", "C16_READING_AFT"} <= set(r.contract_errors)


def test_explicit_aft_act_reference_is_accepted(hn, tmp_path):
    path = "Tribunal/AFT Act 14 - Sub B01 Example v Union of India.docx"
    files, arts, _, _ = _with_relationship(path=path, extra_tax=_tax_prov("AFT-2007", "s", "14", None))
    rels = _jl(files["relationships.jsonl"])
    assert any(r["target"].get("node_id") == "PROV:AFT-2007:s.14" for r in rels)
    r = hn.run(hn.bundle(exchange_files=files, artefacts=arts), tmp_path / "s")
    assert r.activated, r.refused_reasons


def test_ar_read_otherwise_than_army_rules_1954_is_refused(hn, seeded):
    """D1: AR in the local collection is Army Rules, 1954, as a candidate; another expansion is refused."""
    def edit(r):
        e = (r.get("classification_provenance") or {}).get("abbreviation_expansion")
        if e and e["abbreviation"] == "AR":
            e["expansion"] = "Army Regulations (producer reading)"
    files, arts, _, _ = _with_relationship(rel_edit=edit)
    r = refused_untouched(hn, seeded, hn.bundle(exchange_files=files, artefacts=arts))
    assert {"C16_CLASSIFICATION_MISMATCH", "C16_READING_AR"} <= set(r.contract_errors)


def test_ar_reading_outside_the_local_collection_is_refused():
    files, _, ids, _ = cc.exchange(CP)
    rels = _jl(files["relationships.jsonl"])
    for r in rels:
        if r["evidentiary_basis"] in c16.LABEL_BASES:
            r["classification_provenance"]["collection"] = "hf:owner/b01-synthetic"
    assert "C16_READING_AR" in {i.code for i in c16.classification_issues(list(ids.values()), rels, [])}


def test_taxonomy_alias_contradicting_the_owner_decisions_is_refused(hn, seeded):
    extra = _tax_prov("AFT-2007", "s", "14", None)
    extra[0]["aliases"] = ["AFT"]
    files, arts, _, _ = _with_relationship(extra_tax=extra)
    r = refused_untouched(hn, seeded, hn.bundle(exchange_files=files, artefacts=arts))
    assert "C16_READING_AFT" in r.contract_errors


def test_missing_classification_for_an_observed_local_path_is_refused():
    files, _, ids, _ = cc.exchange(CP)
    rels = [r for r in _jl(files["relationships.jsonl"]) if r["evidentiary_basis"] not in c16.LABEL_BASES]
    assert "C16_CLASSIFICATION_MISMATCH" in {i.code for i in c16.classification_issues(list(ids.values()), rels, [])}


# ------------------------------------------------------------ SG-1 / I-5: no v1-compatibility bypass

def _g_identity():
    text = cc.derivative_text(["Synthetic later-held text."])
    return cc.identity(cc.DOC_G, CP.g, mime="application/pdf", fmt="PDF", pages=1, pagination="PHYSICAL_PAGES", rep=cc.native_rep(),
                       derivs=[cc.deriv(cc.DOC_G, text, 1)], images=[],
                       research=cc._research("ELIGIBLE_FULL", True, True, False, True, ["TEXT_RELIABLE_NATIVE"]),
                       history_outputs=[cc.h(text)])


def test_hold_survives_a_dropped_sidecar_and_earlier_generations(hn, tmp_path):
    site = tmp_path / "site"
    docs = hn.default_docs() + [cc.v1_doc(CP.g, cc.DOC_G)]
    # gen 1: G is an established legacy copy, served and citable
    r1 = hn.run(hn.bundle(docs=docs), site)
    assert r1.activated and sv(site, "documents", cc.DOC_G)
    assert cite(site, cc.h(CP.g)[:12], cc.DOC_G, 1, exclusions=None)["state"] == "CITED_COPY_ELIGIBLE"
    # gen 2: the producer now holds G (sidecar present): not served, and no longer held from gen 1 either
    files, arts, _, _ = cc.exchange(CP, held=("B", "G"), mutate=lambda ids, pop: ids.update(G=_g_identity()))
    r2 = hn.run(hn.bundle(docs=docs, exchange_files=files, artefacts=arts), site)
    assert r2.activated, r2.refused_reasons
    assert not sv(site, "documents", cc.DOC_G)
    assert cc.h(CP.g) not in held_copies(site)
    assert cite(site, cc.h(CP.g)[:12], cc.DOC_G, 1, exclusions=None)["state"] == "CITED_COPY_UNAVAILABLE"
    # gen 3: the sidecar is dropped again; removal never lifts the hold
    r3 = hn.run(hn.bundle(docs=docs), site)
    assert r3.activated, r3.refused_reasons
    g = next(x for x in r3.c16["legacy"] if x["doc_id"] == cc.DOC_G)
    assert not g["established"] and not sv(site, "documents", cc.DOC_G) and cc.h(CP.g) not in held_copies(site)
    # also the HELD item B, sidecar dropped while its v1 record stays
    files, arts, _, _ = cc.exchange(CP, keys=("A", "E"))
    r4 = hn.run(hn.bundle(docs=docs, exchange_files=files, artefacts=arts), site)
    assert r4.activated, r4.refused_reasons
    assert not sv(site, "documents", cc.DOC_B)
    assert any("governed by C16" in m for x in r4.c16["legacy"] if x["doc_id"] == cc.DOC_B for m in x["reasons"])


def test_v7_candidate_relabelled_as_v1_is_not_served(hn, tmp_path):
    site = tmp_path / "s"
    r = hn.run(hn.bundle(), site)
    f = next(x for x in r.c16["legacy"] if x["doc_id"] == cc.DOC_F)
    assert not f["established"] and not sv(site, "documents", cc.DOC_F)


def test_v1_record_for_c16_bytes_under_another_doc_id_is_not_served(hn, tmp_path):
    """The bytes of a C16 copy relabelled under another doc_id in the v1 records."""
    docs = hn.default_docs() + [cc.v1_doc(CP.b, "aft-2020-b01-relabelled-held-oa0199")]
    site = tmp_path / "s"
    r = hn.run(hn.bundle(docs=docs), site)
    assert r.activated, r.refused_reasons
    assert not sv(site, "documents", "aft-2020-b01-relabelled-held-oa0199")


def test_v1_record_with_incomplete_provenance_is_not_served(hn, tmp_path):
    site = tmp_path / "s"
    r = hn.run(hn.bundle(), site)
    d = next(x for x in r.c16["legacy"] if x["doc_id"] == cc.DOC_D)
    assert not d["established"] and not sv(site, "documents", cc.DOC_D)


def _exclusions(**kw):
    return ExclusionState(sequence=1, register=cc.REGISTER, **{k: frozenset(v) for k, v in kw.items()})


def test_restricted_bytes_under_another_doc_id_are_never_named(hn, tmp_path):
    """A v1 record for bytes the site holds as restricted (exclusion state) under another doc_id: not served, not
    written to the vault, and neither its hash nor its doc_id appears anywhere the import writes."""
    other = "aft-2020-b01-restricted-relabel-oa0198"
    docs = hn.default_docs() + [cc.v1_doc(CP.g, other)]
    site = tmp_path / "s"
    r = hn.run(hn.bundle(docs=docs), site, exclusions=_exclusions(restricted_tombstone_shas={cc.h(CP.g)}))
    assert r.activated, r.refused_reasons
    assert not sv(site, "documents", other)
    for p in site.rglob("*"):
        if p.is_file():
            body = p.read_bytes()
            assert cc.h(CP.g).encode() not in body and other.encode() not in body, p
            assert body != CP.g


def test_exchange_naming_a_site_restricted_copy_is_refused(hn, seeded):
    r = hn.run(hn.bundle(), seeded, exclusions=_exclusions(restricted_tombstone_shas={cc.h(CP.b)}))
    assert not r.activated and "C16_RESTRICTED_IN_EXCHANGE" in r.contract_errors
    assert cc.h(CP.b) not in json.dumps(r.c16)


def test_register_hit_in_any_c16_record_refuses(hn, seeded):
    from da_cases import REGISTER_TEXT
    files, arts, _, _ = cc.exchange(CP, mutate=lambda ids, pop: ids["E"]["provenance"]["observations"][0].update(
        relative_path=json.loads(REGISTER_TEXT)["items"][0]["hosted_paths"][0]))
    r = refused_untouched(hn, seeded, hn.bundle(exchange_files=files, artefacts=arts))
    assert r.contract_errors  # restricted path or the ensuing classification difference: refused either way


def test_withdrawn_c16_copy_is_not_served(hn, tmp_path):
    site = tmp_path / "s"
    r = hn.run(hn.bundle(), site, exclusions=_exclusions(withdrawn_doc_ids={cc.DOC_A}))
    a = next(c for c in r.c16["copies"] if c["doc_id"] == cc.DOC_A)
    assert r.activated and not a["served"] and "C16_EXCLUDED" in a["codes"] and not sv(site, "documents", cc.DOC_A)


# ------------------------------------------------------------ per-source accounting (signed register)

def test_accounting_register_required_once_c16_aware(hn, seeded):
    r = refused_untouched(hn, seeded, hn.bundle(c16=False, accounting_bytes=False))
    assert r.contract_errors == ["C16_SOURCE_ACCOUNTING_MISSING"]


def test_c16_bundle_without_accounting_refused(hn, tmp_path):
    site = tmp_path / "fresh"
    r = refused_untouched(hn, site, hn.bundle(accounting_bytes=False))
    assert r.contract_errors == ["C16_SOURCE_ACCOUNTING_MISSING"]


@pytest.mark.parametrize("edit", [
    lambda s: s[0].update(input=s[0]["input"] + 1, identities=s[0]["identities"] + 1, held=s[0]["held"] + 1),
    lambda s: s[0].update(held=0, eligible=s[0]["eligible"] + 1),
    lambda s: s.remove(next(x for x in s if x["source"] == "v1:RELEASE_IMPORT")),
    lambda s: s.append({"source": "v1:hf:other@" + "c" * 40, "path": "V1", **cc.counts(input=1, eligible=1, served=1)}),
    lambda s: next(x for x in s if x["path"] == "V7_REFERENCE").update(served=1, eligible=1, held=0),
    lambda s: s[0].update(served=s[0]["eligible"] + 1),
    # 2.1 (PR #82): the site may only narrow; decisions and generation pins must match the bundled exchange
    lambda s: s[0].update(eligible=s[0]["eligible"] - 1, quarantined=s[0]["quarantined"] + 1,
                          served=0, not_served_reasons={**s[0]["not_served_reasons"], "NOT_ELIGIBLE": 1}),
    lambda s: s[0].update(by_decision={**{k: v for k, v in s[0]["by_decision"].items() if k != "HELD_RELEVANCE_UNRESOLVED"},
                                       "REJECTED_NOT_MILITARY_LAW": 1}),
    lambda s: s[0]["provenance"].update(generation_manifest_sha256="1" * 64),
    lambda s: next(x for x in s if x["path"] == "V7_REFERENCE")["provenance"].update(candidate_set_sha256="2" * 64),
], ids=["input", "decision", "missing-source", "extra-source", "v7-served", "served-over-eligible", "site-widens-eligible",
        "by-decision", "generation-pin", "v7-candidate-set-digest"])
def test_accounting_that_does_not_reconcile_refuses(hn, seeded, edit):
    files, arts, _, _ = cc.exchange(CP)
    decl = json.loads(hn.default_accounting("x", hn.default_docs(), files))
    edit(decl["sources"])
    release = f"R16-b01-synthetic-20261128-{hn.n + 1:08x}"
    decl["release_id"] = release
    r = refused_untouched(hn, seeded, hn.bundle(exchange_files=files, artefacts=arts, release=release,
                                                accounting_bytes=json.dumps(decl).encode()))
    assert "C16_SOURCE_ACCOUNTING" in r.contract_errors


def test_accounting_scope_and_candidate_set_are_checked(hn, seeded):
    """The shipped register must be the build's declaration (a site recomputation is never accepted as one), and a
    declared V7_REFERENCE source needs its candidate hash set in the bundle (the relabel check uses the hashes)."""
    files, arts, _, _ = cc.exchange(CP)
    release = f"R16-b01-synthetic-20261128-{hn.n + 1:08x}"
    decl = json.loads(hn.default_accounting(release, hn.default_docs(), files))
    decl["scope"] = "RECOMPUTED_BY_SITE"
    from mimamsa_contract.c16 import accounting
    r = refused_untouched(hn, seeded, hn.bundle(exchange_files=files, artefacts=arts, release=release,
                                                accounting_bytes=accounting.register_bytes(decl)))
    assert r.contract_errors == ["C16_SOURCE_ACCOUNTING"]
    release = f"R16-b01-synthetic-20261128-{hn.n + 1:08x}"
    r = refused_untouched(hn, seeded, hn.bundle(exchange_files=files, artefacts=arts, release=release,
                                                accounting_bytes=hn.default_accounting(release, hn.default_docs(), files),
                                                drop=("registers/candidate_sets/cycle15.txt",)))
    assert r.contract_errors == ["C16_SOURCE_ACCOUNTING"]


def test_accounting_for_another_release_refused(hn, seeded):
    files, arts, _, _ = cc.exchange(CP)
    r = refused_untouched(hn, seeded, hn.bundle(exchange_files=files, artefacts=arts,
                                                accounting_bytes=hn.default_accounting("R-other", hn.default_docs(), files)))
    assert "C16_SOURCE_ACCOUNTING" in r.contract_errors


# ------------------------------------------------------------ whole-bundle refusals for every contract negative

def _base_exchange_for_negatives():
    return fixture_exchange()


EXCHANGE_KINDS = {"document_identity": "identities.jsonl", "evidence_anchor": "anchors.jsonl", "corpus_relationship": "relationships.jsonl",
                  "corpus_admission": "admissions.jsonl", "taxonomy_node": "taxonomy.jsonl"}
NEG = [e for e in MANIFEST["negative"]]
ACTIVATION_ONLY = [e["file"] for e in NEG if e["kind"] == "record" and _j(FIX / e["file"]).get("record_kind") == "knowledge_activation_record"]


def _negative_bundle(hn, entry):
    """Carry the negative in a signed bundle the way a producer would have to: exchange records injected into the
    2.1 fixture exchange (manifest regenerated), knowledge release manifests as KNOWLEDGE_RELEASE.json."""
    ex = _base_exchange_for_negatives()
    extra = {}
    if entry["kind"] == "exchange_case":
        ex = {k: v.encode("utf-8") for k, v in _j(FIX / entry["file"])["files"].items()}
    elif entry["kind"] == "jsonl":
        ex["relationships.jsonl"] = (FIX / entry["file"]).read_bytes()
        ex = regenerate_manifest(ex)
    else:
        rec = _j(FIX / entry["file"])
        if rec.get("record_kind") == "knowledge_release_manifest":
            extra["KNOWLEDGE_RELEASE.json"] = (json.dumps(rec, indent=1).encode(), "other")
        else:
            name = EXCHANGE_KINDS[rec["record_kind"]]
            recs = _jl(ex[name]) + [rec]
            ex[name] = b"".join(json.dumps(r, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode() + b"\n" for r in recs)
            ex = regenerate_manifest(ex)
    release = f"R16-b01-negative-20261128-{hn.n + 1:08x}"
    acct = cc.accounting(release, cc.counts(input=1, eligible=1), {})   # well formed; refusal must come from the negative
    return hn.bundle(exchange_files=ex, artefacts=fixture_artefacts(), extra=extra, release=release, accounting_bytes=acct)


@pytest.mark.parametrize("entry", [e for e in NEG if e["file"] not in ACTIVATION_ONLY], ids=lambda e: Path(e["file"]).stem)
def test_every_contract_negative_refuses_the_whole_bundle(hn, seeded, entry):
    r = refused_untouched(hn, seeded, _negative_bundle(hn, entry))
    assert entry["expect_code"] in r.contract_errors or (entry["expect_code"] == "SCHEMA" and "SCHEMA" in r.contract_errors), r.contract_errors


def test_activation_record_negatives_are_not_bundle_content():
    """N27, N44, N45, N53 are activation-tool records (B06): the importer never reads them from a bundle."""
    assert sorted(Path(f).stem[:3] for f in ACTIVATION_ONLY) == ["N27", "N44", "N45", "N53"]


def test_negative_coverage_is_complete():
    stems = {Path(e["file"]).stem[:3] for e in NEG}
    assert {f"N{n:02d}" for n in range(1, 55)} <= stems and {f"X{n:02d}" for n in range(1, 36)} <= stems


# ------------------------------------------------------------ crash points with C16 files present

@pytest.mark.parametrize("point", ["after_c16_index", "after_vault_object", "before_rename", "before_active"])
def test_crash_then_reimport_recovers_with_governance_kept(hn, tmp_path, monkeypatch, point):
    site = tmp_path / "site"
    b = hn.bundle()

    class Crash(RuntimeError):
        pass

    def boom(name):
        if name == point:
            raise Crash(name)
    monkeypatch.setattr(importer, "_crashpoint", boom)
    with pytest.raises(Crash):
        hn.run(b, site)
    monkeypatch.setattr(importer, "_crashpoint", lambda name: None)
    if point != "after_vault_object":
        assert (site / c16.DECISION_INDEX).exists()       # governance recorded before the generation existed
    r = hn.run(b, site)
    assert r.activated, r.refused_reasons
    assert sv(site, "documents", cc.DOC_A) and not sv(site, "documents", cc.DOC_B)
    gen = active_generation(site)
    assert gen["c16"]["served_copies"] == [[cc.DOC_A, cc.h(CP.a)]]


def test_unreadable_decision_index_fails_closed(hn, seeded):
    (seeded / c16.DECISION_INDEX).write_text("{not json")
    with pytest.raises(ImporterError):
        hn.run(hn.bundle(), seeded)


def test_reimport_of_the_active_c16_bundle_is_a_noop(hn, tmp_path):
    site = tmp_path / "s"
    b = hn.bundle()
    assert hn.run(b, site).activated
    before = snapshot(site)
    assert hn.run(b, site).noop and snapshot(site) == before


# ------------------------------------------------------------ safe archive reader (I4)

def _zip(entries):
    import io
    import zipfile
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, data in entries:
            zi = zipfile.ZipInfo("placeholder", date_time=(2026, 11, 28, 0, 0, 0))
            zi.filename = name          # keep the raw name (zipfile would normalise a backslash on Windows)
            z.writestr(zi, data)
    return buf.getvalue()


@pytest.mark.parametrize("entries", [
    [("../evil.png", b"x")], [("/abs.png", b"x")], [("word\\media\\a.png", b"x")], [("a.png", b"x"), ("A.PNG", b"y")],
    [("word/./a.png", b"x")],
], ids=["dotdot", "absolute", "backslash", "case-duplicate", "dot-segment"])
def test_unsafe_containers_are_refused(entries):
    with pytest.raises(safe_archive.UnsafeArchive):
        safe_archive.read_members(_zip(entries), {"word/media/a.png"})


def test_zip_bomb_ratio_refused():
    with pytest.raises(safe_archive.UnsafeArchive):
        safe_archive.read_members(_zip_deflated([("word/media/a.png", b"\0" * 5_000_000)]), {"word/media/a.png"})


def _zip_deflated(entries):
    import io
    import zipfile
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in entries:
            z.writestr(name, data)
    return buf.getvalue()


def test_not_a_zip_is_refused():
    with pytest.raises(safe_archive.UnsafeArchive):
        safe_archive.read_members(b"%PDF-1.4 not a zip", set())


def test_byte_checks_pdf_page_count_and_coverage():
    files, _, ids, _ = cc.exchange(CP)
    a = copy.deepcopy(ids["A"])
    assert c16.byte_issues(a, CP.a, {cc.h(CP.a_text): CP.a_text}) == []
    a["source_copy"]["page_count"] = 3
    assert "C16_PAGE_COUNT_MISMATCH" in c16.byte_issues(a, CP.a, {})
    a = copy.deepcopy(ids["A"])
    a["text_derivatives"][0]["coverage"]["units_total"] = 5
    assert "C16_DERIVATIVE_COVERAGE" in c16.byte_issues(a, CP.a, {cc.h(CP.a_text): CP.a_text})
    a = copy.deepcopy(ids["A"])
    a["source_copy"]["bytes"] += 1
    assert "C16_BYTES_SIZE" in c16.byte_issues(a, CP.a, {})


def test_receipt_reference_matches_the_contract_reference():
    """The importer calls the reference resolver; it never re-implements it."""
    assert c16.receipts is receipts


def test_committed_e2e_site_is_the_importers_output():
    """The B1 C# suite loads app/b1/tests/Mimamsa.Tests/fixtures/c16_b01/site; it must be exactly what this importer
    writes (no hand edits)."""
    import subprocess
    fixture = HERE.parent / "b1" / "tests" / "Mimamsa.Tests" / "fixtures" / "c16_b01"
    out = subprocess.run([sys.executable, "-I", str(HERE / "c16_cases.py"), str(fixture), "--check"], capture_output=True, text=True)
    assert out.returncode == 0, out.stdout + out.stderr
