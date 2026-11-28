"""B02 Stage 3 (stream S3-A): pinned real fetch and its verification, refusal of restricted items, the canonical and
v7 layout conversions, [[page N]] re-derivation, several producer generations, DELTA assembly and determinism.
No test uses the network: the HF API is replaced by an in-memory pinned tree (fake_hf)."""
from __future__ import annotations

import copy
import hashlib
import json
import shutil
import threading
import time
from pathlib import Path

import pytest
from conftest import KBUILD, load_spec

import fake_hf
from mimamsa_contract.bundle import parse_sums
from mimamsa_contract.c16 import accounting
from mimamsa_contract.c16 import rules as c16rules
from mimamsa_kbuild import REPO, delta, generations, hf_fetch, page_format, real_corpus, stages
from mimamsa_kbuild.cli import dry_run, run_build
from mimamsa_kbuild.errors import BuildRefused
from mimamsa_kbuild.fixture_mirror import GENERATION_SHA256, prepare, revision_root

ALL = [f"S{i}" for i in range(10)]
PAGE_CFG = REPO / "app" / "kbuild" / "config" / "page_rederive.json"


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _tree(root: Path) -> dict[str, str]:
    return {p.relative_to(root).as_posix(): _sha(p.read_bytes()) for p in sorted(root.rglob("*"))
            if p.is_file() and p.name != "BUILD_RECORD.json"}


class Reg:
    """A restricted-material register stand-in."""

    def __init__(self, shas=(), paths=(), ids=()):
        self.shas, self.paths, self.ids = set(shas), set(paths), set(ids)

    def is_restricted(self, sha256=None, doc_id=None, path=None):
        return sha256 in self.shas or path in self.paths or doc_id in self.ids


# ===================================================================================== S1 pinned fetch

def _repo(tmp_path, files, **kw):
    fake = fake_hf.FakeHF({("o/r", "a" * 40): files})
    lister, opener = fake.transport("o/r", "a" * 40)
    return fake, hf_fetch.PinnedRepo("o/r", "a" * 40, tmp_path / "cache", lister=lister, opener=opener,
                                     transfer=hf_fetch.Transfer(max_workers=2, max_bytes_per_second=0, min_free_disk_bytes=1, retries=0), **kw)


@pytest.mark.parametrize("rev", ["main", "cycle15-candidates", "217020db", "A" * 40, None])
def test_fetch_refuses_an_unpinned_revision(tmp_path, rev):
    with pytest.raises(BuildRefused) as e:
        hf_fetch.PinnedRepo("o/r", rev, tmp_path)
    assert e.value.code == "BUILD_INPUT_UNPINNED"


def test_fetch_verifies_git_blob_and_lfs_ids_and_reuses_the_cache_offline(tmp_path):
    files = {"data/meta/x.json": b'{"a":1}', "data/raw/x.pdf": b"%PDF-1.4 synthetic"}
    fake, r = _repo(tmp_path, files)
    got = r.fetch(sorted(files), expected_sha256={"data/raw/x.pdf": _sha(files["data/raw/x.pdf"])})
    assert {p: e["sha256"] for p, e in got.items()} == {p: _sha(b) for p, b in files.items()}
    assert r.cas_path(_sha(files["data/raw/x.pdf"])).read_bytes() == files["data/raw/x.pdf"]
    # a second instance over the same cache needs no tree listing and no download (offline re-check)
    def boom(*_a, **_k):
        raise AssertionError("network used for a cached, verified file")
    r2 = hf_fetch.PinnedRepo("o/r", "a" * 40, tmp_path / "cache", lister=boom, opener=boom)
    assert r2.fetch(sorted(files)) == got and r2.stats.reused_files == 2


@pytest.mark.parametrize("what", ["git_blob", "lfs", "manifest"])
def test_fetch_refuses_bytes_that_do_not_match_the_pin(tmp_path, what):
    files = {"data/meta/x.json": b'{"a":1}', "data/raw/x.pdf": b"%PDF-1.4 synthetic"}
    fake, r = _repo(tmp_path, files)
    path = "data/meta/x.json" if what == "git_blob" else "data/raw/x.pdf"
    expected = {}
    if what == "manifest":
        expected = {path: _sha(b"another document")}
    else:
        fake.tamper[path] = files[path][:-1] + b"!"
    with pytest.raises(BuildRefused) as e:
        r.fetch([path], expected_sha256=expected)
    assert e.value.code == "BUILD_INPUT_HASH"
    assert not any((tmp_path / "cache" / "cas").rglob("*")) if (tmp_path / "cache" / "cas").exists() else True


def test_fetch_never_downloads_restricted_material(tmp_path):
    files = {"data/raw/ok.pdf": b"%PDF ok", "data/raw/secret.pdf": b"%PDF secret", "data/meta/bad-id.json": b"{}"}
    fake, r = _repo(tmp_path, files)
    reg = Reg(shas={_sha(files["data/raw/secret.pdf"])}, ids={"bad-id"})
    got = r.fetch(sorted(files), register=reg, doc_ids={"data/meta/bad-id.json": "bad-id"})
    assert set(got) == {"data/raw/ok.pdf"}
    assert "data/raw/secret.pdf" not in fake.opened and "data/meta/bad-id.json" not in fake.opened   # never requested
    assert r.stats.restricted_skipped == 2


def test_fetch_concurrency_and_rate_are_bounded(tmp_path):
    files = {f"data/raw/{i}.pdf": bytes([i]) * 4096 for i in range(8)}
    fake = fake_hf.FakeHF({("o/r", "a" * 40): files})
    lister, _ = fake.transport("o/r", "a" * 40)
    live, peak, lock = [0], [0], threading.Lock()

    def opener(path):
        with lock:
            live[0] += 1
            peak[0] = max(peak[0], live[0])
        time.sleep(0.05)
        yield files[path]
        with lock:
            live[0] -= 1
    r = hf_fetch.PinnedRepo("o/r", "a" * 40, tmp_path / "c", lister=lister, opener=opener,
                            transfer=hf_fetch.Transfer(max_workers=2, max_bytes_per_second=0, min_free_disk_bytes=1, retries=0))
    r.fetch(sorted(files))
    assert peak[0] <= 2
    rl = hf_fetch.RateLimiter(64 * 1024)
    t0 = time.monotonic()
    for _ in range(3):
        rl.take(64 * 1024)
    assert time.monotonic() - t0 >= 1.5   # 192 KiB at 64 KiB/s with one second of burst


def test_fetch_disk_floor_pauses_the_fetch(tmp_path):
    fake, r = _repo(tmp_path, {"data/raw/x.pdf": b"%PDF"})
    r.transfer.min_free_disk_bytes = 1 << 62
    with pytest.raises(BuildRefused) as e:
        r.fetch(["data/raw/x.pdf"])
    assert e.value.code == "BUILD_DISK_FLOOR"


def test_fetch_module_has_no_write_path():
    """Read-only by construction: the module never calls an upload, commit, delete or branch API."""
    src = (KBUILD / "mimamsa_kbuild" / "hf_fetch.py").read_text(encoding="utf-8")
    for call in ("upload_", "create_commit", "delete_", "create_branch", "create_repo", "update_repo", "push_to_hub", "HfFileSystem"):
        assert call not in src, call


# ===================================================================================== plan and v7 conversion

def test_committed_real_sample_plan_is_pinned_by_its_spec():
    spec = json.loads((KBUILD / "specs" / "real-sample-290.spec.json").read_text(encoding="utf-8"))
    plan_path = KBUILD / "specs" / "real-sample-290.fetch.json"
    plan, data = real_corpus.load_plan(plan_path, spec)
    assert _sha(data) == real_corpus.plan_pin(spec)
    assert len(plan["canonical"]["doc_ids"]) == 290 and plan["v7"][0]["revision"] == "217020dbd969e14c2373697f4094fa00557962a6"
    assert real_corpus.plan_pin(spec, page_format.TOOL) == _sha(PAGE_CFG.read_bytes())
    sample = json.loads((REPO / "app" / "b1" / "sample" / "SAMPLE_MANIFEST.json").read_text(encoding="utf-8"))
    assert plan["canonical"]["doc_ids"] == sorted(d["doc_id"] for d in sample["documents"])
    bad = dict(spec, inputs=dict(spec["inputs"], tools=[dict(t, config_sha256="0" * 64) if t["name"] == real_corpus.PLAN_TOOL else t
                                                       for t in spec["inputs"]["tools"]]))
    with pytest.raises(BuildRefused) as e:
        real_corpus.load_plan(plan_path, bad)
    assert e.value.code == "BUILD_PIN_MISMATCH"
    with pytest.raises(BuildRefused) as e:
        real_corpus.load_plan(None, spec)
    assert e.value.code == "BUILD_INPUT_MISSING"


def test_v7_conversion_gives_canonical_candidate_sets_and_never_admits():
    pkg = {"name": "syn-v7", "namespace": fake_hf.V7_NS, "files": ["records.jsonl", "pages.jsonl.gz"]}
    files = fake_hf.v7_package("ab" * 32, "syn-doc")
    out, rep = real_corpus.convert_v7(files.get, pkg, register=Reg())
    data = out["v7/candidate_sets/syn-v7.txt"]
    assert accounting.candidate_set_bytes(data.decode().split("\n")) == data and not data.endswith(b"\n")
    assert rep["candidate_originals"] == 2 and rep["candidate_set_sha256"] == _sha(data)
    assert rep["from_v7_record"]["anchors"] == 1 and rep["from_v7_record"]["relationships"] == 1
    # a restricted candidate is left out of the set (its hash is never named in a release)
    out2, rep2 = real_corpus.convert_v7(files.get, pkg, register=Reg(shas={"ab" * 32}))
    assert rep2["candidate_originals"] == 1 and rep2["restricted_omitted_from_set"] == 1
    with pytest.raises(BuildRefused) as e:   # a record claiming eligibility refuses the conversion
        real_corpus.convert_v7(fake_hf.v7_package("ab" * 32, "syn-doc", eligible=True).get, pkg, register=Reg())
    assert e.value.code == "BUILD_INPUT_V7"


# ===================================================================================== S3 page format

@pytest.mark.parametrize("pages", [{1: "a"}, {1: "", 2: "b\n"}, {3: "x\n\ny", 1: "first"}, {1: "ends with blank\n\n"}])
def test_render_is_the_inverse_of_the_importer_page_reader(pages):
    from mimamsa_importer.importer import _split_pages
    cfg = page_format.load_config(PAGE_CFG.read_bytes())
    data, got, kind = page_format.rederive(page_list=pages, config=cfg)
    assert kind == "PAGE_LIST" and got == pages and _split_pages(data.decode()) == pages


def test_rederive_refuses_what_it_cannot_reproduce():
    cfg = page_format.load_config(PAGE_CFG.read_bytes())
    with pytest.raises(ValueError):
        page_format.rederive(page_list={1: "x\n[[page 2]]\ny"}, config=cfg)   # a body that contains a marker line
    with pytest.raises(ValueError):
        page_format.rederive("no markers and no form feeds", config=cfg)
    data, pages, kind = page_format.rederive("one\fTWO\f", config=cfg)
    assert pages == {1: "one", 2: "TWO"} and kind == "FORM_FEED"
    with pytest.raises(ValueError):
        page_format.load_config(json.dumps({"record_kind": "kbuild_page_rederive_config", "ocr": "TESSERACT"}).encode())


def _pin_page_config(spec):
    spec["inputs"]["tools"] = [t for t in spec["inputs"]["tools"] if t["name"] != page_format.TOOL] + [
        {"name": page_format.TOOL, "version": "1", "commit": None, "config_sha256": _sha(PAGE_CFG.read_bytes())}]
    return spec


def _form_feed_mirror(tmp_path) -> tuple[Path, str]:
    """The CP-1 fixture mirror with one v1 derivative stored without [[page N]] markers (form feeds instead)."""
    m = tmp_path / "mirror-ff"
    prepare(m)
    root = revision_root(m, "owner/fixture-corpus", "008d447011808d3d3f9095b0dbf14125002d1642") / "v1"
    ders = [json.loads(x) for x in (root / "data" / "derived_text.jsonl").read_text(encoding="utf-8").splitlines() if x]
    # a derivative whose pages run 1..n (form feeds cannot express a gap or a first page other than 1)
    t = next(d for d in ders if sorted(p["page"] for p in d["pages"]) == list(range(1, len(d["pages"]) + 1)))
    pages = page_format.split((root / t["text_path"]).read_text(encoding="utf-8"))
    ff = "\f".join(pages[n] for n in sorted(pages)).encode("utf-8")
    assert sorted(pages) == list(range(1, len(pages) + 1)) and not any("\f" in b for b in pages.values())
    (root / t["text_path"]).write_bytes(ff)
    t["text_sha256"] = _sha(ff)
    (root / "data" / "derived_text.jsonl").write_bytes("".join(json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n" for r in ders).encode())
    return m, t["doc_id"]


def test_s3_rederives_a_derivative_under_the_pinned_config(tmp_path, dev_key, accel_tool):
    m, doc = _form_feed_mirror(tmp_path)
    spec = load_spec()
    with pytest.raises(BuildRefused) as e:   # no pinned config: the item is not silently promoted or guessed
        run_build(spec, tmp_path / "out0", mirror=m, dev_key=dev_key, accel=accel_tool, apply_budget=False)
    assert e.value.code == "BUILD_S3_REDERIVE"
    spec = _pin_page_config(load_spec())
    res = run_build(spec, tmp_path / "out", mirror=m, dev_key=dev_key, accel=accel_tool, apply_budget=False)
    root = tmp_path / "out" / spec["output_dir"]
    rep = json.loads((root / "S3" / "TEXT_REPORT.json").read_text(encoding="utf-8"))
    assert rep["v1_rederived"] == 1 and rep["v1_rederived_items"][0]["doc_id"] == doc and rep["ocr_run"] is False
    assert res["ran"] == ALL   # S9 imported the re-derived derivative through B01 and rebuilt every accelerator


# ===================================================================================== real-corpus layout end to end (fake HF)

def _fake_real(tmp_path, mirror):
    v1 = revision_root(mirror, "owner/fixture-corpus", "008d447011808d3d3f9095b0dbf14125002d1642") / "v1"
    canon = fake_hf.canonical_from_mirror(v1)
    rows = [json.loads(x) for x in (v1 / "data" / "documents.jsonl").read_text(encoding="utf-8").splitlines() if x]
    overlap = rows[0]
    v7 = fake_hf.v7_package(overlap["source_copy"]["sha256"], overlap["doc_id"])
    fake = fake_hf.FakeHF({(fake_hf.REPO, fake_hf.CANON_REV): canon, (fake_hf.REPO, fake_hf.V7_REV): v7})
    plan = fake_hf.plan([r["doc_id"] for r in rows], canon, v7)
    plan_path = tmp_path / "syn.fetch.json"
    plan_path.write_bytes(json.dumps(plan, indent=1, sort_keys=True).encode())
    spec = _pin_page_config(load_spec())
    spec["build_id"], spec["output_dir"] = "B-20261128-syn-real", "build/B-20261128-syn-real"
    spec["release"]["release_id"] = "R16-syn-real-20261128-0000000a"
    spec["inputs"]["hf"] = [{"repo": fake_hf.REPO, "revision": fake_hf.CANON_REV, "purpose": "synthetic canonical layout"},
                            {"repo": fake_hf.REPO, "revision": fake_hf.V7_REV, "purpose": "synthetic v7 package"}]
    spec["inputs"]["producer_generations"] = []
    spec["inputs"]["models"] = []
    spec["inputs"]["tools"].append({"name": real_corpus.PLAN_TOOL, "version": "1", "commit": None, "config_sha256": _sha(plan_path.read_bytes())})
    return spec, plan_path, fake, rows, overlap


@pytest.fixture(scope="module")
def syn_real(tmp_path_factory, mirror, dev_key, accel_tool):
    tmp = tmp_path_factory.mktemp("synreal")
    spec, plan_path, fake, rows, overlap = _fake_real(tmp, mirror)
    out = tmp / "out"
    res = run_build(spec, out, dev_key=dev_key, accel=accel_tool, apply_budget=False, fetch_plan=plan_path, hf_cache=tmp / "cache",
                    hf_transport=fake.routed())
    return {"tmp": tmp, "spec": spec, "plan": plan_path, "fake": fake, "rows": rows, "overlap": overlap, "out": out, "res": res,
            "root": out / spec["output_dir"]}


def test_real_layout_builds_end_to_end_from_pinned_fetches(syn_real):
    root, res = syn_real["root"], syn_real["res"]
    assert res["ran"] == ALL
    inv = json.loads((root / "S1" / "INVENTORY.json").read_text(encoding="utf-8"))
    assert inv["mode"] == "HF_PINNED" and inv["network_used"] is True and inv["fetch_plan"]["sha256"] == _sha(syn_real["plan"].read_bytes())
    assert {(h["repo"], h["revision"]) for h in inv["hf"]} == {(fake_hf.REPO, fake_hf.CANON_REV), (fake_hf.REPO, fake_hf.V7_REV)}
    val = json.loads((root / "S2" / "VALIDATION.json").read_text(encoding="utf-8"))
    conv = val["conversion"]["canonical"]
    assert conv["converted"] == len(syn_real["rows"]) and conv["dropped"] == []
    # SG-1: the canonical copy that is also a v7 candidate is emitted NOT servable (never relabelled)
    assert conv["v7_overlap_staged_not_servable"] == [syn_real["overlap"]["doc_id"]]
    assert val["legacy_sg1"]["not_servable_not_established"] == [syn_real["overlap"]["doc_id"]]
    acct = json.loads((root / "S8" / "bundle" / "registers" / "source_accounting.json").read_text(encoding="utf-8"))
    v1 = next(s for s in acct["sources"] if s["path"] == "V1")
    v7 = next(s for s in acct["sources"] if s["path"] == "V7_REFERENCE")
    assert v1["source"] == f"v1:hf:{fake_hf.REPO}@{fake_hf.CANON_REV}" and v1["input"] == len(syn_real["rows"])
    assert v1["served"] == len(syn_real["rows"]) - 1 and v1["quarantined"] == 1
    assert v7["input"] == 2 and v7["served"] == v7["eligible"] == 0
    assert accounting.accounting_issues(acct) == []
    verify = json.loads((root / "S9" / "VERIFY.json").read_text(encoding="utf-8"))
    assert verify["acceptance_level"].startswith("REAL-SAMPLE") and verify["inputs_mode"] == "HF_PINNED"
    assert verify["checks"]["site_importer"]["served_documents"] == len(syn_real["rows"]) - 1
    text = json.loads((root / "S3" / "TEXT_REPORT.json").read_text(encoding="utf-8"))
    v7r = text["v7_rederived_reference_only"][0]
    assert v7r["documents"] == 2 and v7r["page_hash_differs"] == 0 and v7r["spans_bound"] == 1 and v7r["spans_unbound"] == 0
    sums = parse_sums((root / "S8" / "bundle" / "SHA256SUMS").read_text(encoding="utf-8"))[0]
    assert not any(p.startswith("v7/") for p in sums)   # v7 derivatives are reference only: never shipped
    assert "registers/candidate_sets/syn-v7.txt" in sums


def test_real_layout_resume_is_offline_and_rebuild_is_byte_identical(syn_real, tmp_path, dev_key, accel_tool):
    s = syn_real
    def no_net(*_a, **_k):
        raise AssertionError("network used on a resume")
    again = run_build(s["spec"], s["out"], dev_key=dev_key, accel=accel_tool, apply_budget=False, fetch_plan=s["plan"],
                      hf_cache=s["tmp"] / "cache", hf_transport=(no_net, no_net))
    assert again["ran"] == []
    # a clean build with a fresh cache, fetching again: byte-identical outputs
    fake2 = fake_hf.FakeHF(s["fake"].trees)
    run_build(s["spec"], tmp_path / "out2", dev_key=dev_key, accel=accel_tool, apply_budget=False, fetch_plan=s["plan"],
              hf_cache=tmp_path / "cache2", hf_transport=fake2.routed())
    a, b = _tree(s["root"]), _tree(tmp_path / "out2" / s["spec"]["output_dir"])
    assert a == b
    assert fake2.opened   # the second build really fetched (from the fake hub)


def test_real_layout_refuses_tampered_bytes_and_skips_restricted(syn_real, tmp_path, dev_key, accel_tool):
    s = syn_real
    fake = fake_hf.FakeHF(copy.deepcopy(s["fake"].trees))
    raw = next(p for p in fake.trees[(fake_hf.REPO, fake_hf.CANON_REV)] if p.endswith(".pdf"))
    fake.tamper[raw] = b"%PDF-1.4 not the pinned bytes"
    with pytest.raises(BuildRefused) as e:
        run_build(s["spec"], tmp_path / "o", dev_key=dev_key, accel=accel_tool, apply_budget=False, fetch_plan=s["plan"],
                  hf_cache=tmp_path / "c", hf_transport=fake.routed())
    assert e.value.code == "BUILD_INPUT_HASH" and e.value.stage == "S1"
    # a register hit is never requested from the hub
    reg = Reg(ids={s["rows"][1]["doc_id"]})
    plan = json.loads(s["plan"].read_text(encoding="utf-8"))
    fake3 = fake_hf.FakeHF(s["fake"].trees)
    lister, opener = fake3.routed()
    got = real_corpus.fetch_sources(plan, cache_root=tmp_path / "c3", register=reg,
                                    transfer=hf_fetch.Transfer(max_workers=1, max_bytes_per_second=0, min_free_disk_bytes=1, retries=0),
                                    lister=lister, opener=opener)
    assert got["restricted_skipped"] >= 1
    assert not any(s["rows"][1]["doc_id"] in p for p in fake3.opened)
    assert not any(s["rows"][1]["source_copy"]["sha256"] in p for p in fake3.opened)


def test_real_layout_dry_run_uses_no_network_and_writes_nothing(syn_real, tmp_path):
    s = syn_real
    out = dry_run(s["spec"], tmp_path / "dry", fetch_plan=s["plan"], hf_cache=tmp_path / "nocache", dev_key=tmp_path / "absent.key")
    assert out["sources"][0]["documents"] == len(s["rows"]) and out["sources"][1]["layout"] == "V7_CANDIDATE_PACKAGE"
    assert out["stages_to_run"] == ALL and not (tmp_path / "dry").exists() and not (tmp_path / "nocache").exists()


# ===================================================================================== several producer generations

def _generation(mirror: Path, dirname: str, cg: str, keys=None) -> str:
    """Write a CP-1 slice exchange (B01 synthetic producer) for generation `cg` under exchanges/<dirname>/."""
    from mimamsa_kbuild import fixture_mirror as fm
    repo, rev = fm.CP1_REPO, fm.CP1_REVISION
    fm.cp1_exchange(repo, rev)   # sets the paths and the register on c16_cases
    import c16_cases as cc
    old = cc.CG
    cc.CG = cg
    try:
        def point(key, arts):
            a = arts["G01_HASH_VERIFIED"]
            a["payload"]["source"] = {"hf_repo": repo, "hf_revision": rev, "path": f"v1/originals/{a['subject']['source_copy_sha256']}.pdf"}
        files, arts, _i, _a = cc.exchange(cc.Corpus(), mutate_arts=point, keys=keys)
    finally:
        cc.CG = old
    root = revision_root(mirror, repo, rev) / "exchanges" / dirname
    for name, b in files.items():
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        (root / name).write_bytes(b)
    for p, b in arts.items():
        (root / p).parent.mkdir(parents=True, exist_ok=True)
        (root / p).write_bytes(b)
    return _sha(files["GENERATION.json"])


@pytest.fixture(scope="module")
def slice_mirror(tmp_path_factory):
    m = tmp_path_factory.mktemp("slice-mirror")
    prepare(m, exchange="cp1")
    return m


def _slice_spec():
    return json.loads((KBUILD / "specs" / "cp1-slice.spec.json").read_text(encoding="utf-8"))


def test_several_generations_ship_the_current_and_keep_earlier_holds(tmp_path, slice_mirror, dev_key, accel_tool):
    m = tmp_path / "m"
    shutil.copytree(slice_mirror, m)
    cur = "CG-20261129-b01site-1b2c3d4e"
    sha_cur = _generation(m, "current", cur)
    spec = _slice_spec()
    first = spec["inputs"]["producer_generations"][0]
    spec["inputs"]["producer_generations"].append(dict(first, corpus_generation_id=cur, generation_manifest_sha256=sha_cur,
                                                       path="exchanges/current/GENERATION.json"))
    res = run_build(spec, tmp_path / "out", mirror=m, dev_key=dev_key, accel=accel_tool, apply_budget=False)
    assert res["ran"] == ALL
    root = tmp_path / "out" / spec["output_dir"]
    val = json.loads((root / "S2" / "VALIDATION.json").read_text(encoding="utf-8"))
    assert [g["role"] for g in val["exchange"]["producer_generations"]] == ["RETAINED_GOVERNANCE", "CURRENT_SHIPPED"]
    bundle = root / "S8" / "bundle"
    assert json.loads((bundle / "corpus-v2" / "GENERATION.json").read_text(encoding="utf-8"))["corpus_generation_id"] == cur
    km = json.loads((bundle / "KNOWLEDGE_RELEASE.json").read_text(encoding="utf-8"))
    assert [g["corpus_generation_id"] for g in km["corpus_generations"]] == [first["corpus_generation_id"], cur]
    acct = json.loads((bundle / "registers" / "source_accounting.json").read_text(encoding="utf-8"))
    assert [s["source"] for s in acct["sources"] if s["path"] == "C16"] == [f"c16:{cur}"]
    # the current generation drops the earlier generation's held copy B: refused (a hold is never lifted by omission)
    m2 = tmp_path / "m2"
    shutil.copytree(slice_mirror, m2)
    sha_drop = _generation(m2, "current", cur, keys=("A", "E"))
    spec2 = _slice_spec()
    spec2["inputs"]["producer_generations"].append(dict(first, corpus_generation_id=cur, generation_manifest_sha256=sha_drop,
                                                        path="exchanges/current/GENERATION.json"))
    with pytest.raises(BuildRefused) as e:
        run_build(spec2, tmp_path / "out2", mirror=m2, dev_key=dev_key, accel=accel_tool, apply_budget=False)
    assert e.value.code == "BUILD_GENERATION_HOLD_DROPPED" and e.value.stage == "S2"


def test_generation_pin_must_name_its_manifest_generation():
    ex = {"GENERATION.json": json.dumps({"corpus_generation_id": "CG-20261128-x-00000001"}).encode()}
    issues = generations.succession_issues([{"pin": {"corpus_generation_id": "CG-20261128-y-00000002"}, "exchange": ex}])
    assert [i["code"] for i in issues] == ["BUILD_PIN_MISMATCH"]


# ===================================================================================== DELTA

@pytest.fixture(scope="module")
def delta_build(tmp_path_factory, built, slice_mirror, dev_key, accel_tool):
    """base: the CP-1 fixture build (FULL, sequence 1); delta: the CP-1 slice inputs as a DELTA on that base."""
    tmp = tmp_path_factory.mktemp("delta")
    spec = _slice_spec()
    base_m = json.loads((built["root"] / "S8" / "bundle" / "KNOWLEDGE_RELEASE.json").read_text(encoding="utf-8"))
    spec["release"].update(base_mode="DELTA", base_release_id=base_m["release_id"])
    res = run_build(spec, tmp / "out", mirror=slice_mirror, dev_key=dev_key, accel=accel_tool, apply_budget=False,
                    base_bundle=built["root"] / "S8" / "bundle")
    return {"spec": spec, "res": res, "root": tmp / "out" / spec["output_dir"], "base": built["root"] / "S8" / "bundle", "tmp": tmp}


def test_delta_release_has_kind_specific_transport_and_full_state_digests(delta_build):
    root = delta_build["root"]
    assert delta_build["res"]["ran"] == ALL
    dm = json.loads((root / "S8" / "bundle" / "KNOWLEDGE_RELEASE.json").read_text(encoding="utf-8"))
    full = json.loads((root / "S7" / "full" / "KNOWLEDGE_RELEASE.json").read_text(encoding="utf-8"))
    base_bytes = (delta_build["base"] / "KNOWLEDGE_RELEASE.json").read_bytes()
    assert dm["base"] == {"mode": "DELTA", "base_release_id": json.loads(base_bytes)["release_id"], "base_manifest_sha256": _sha(base_bytes)}
    assert c16rules.record_issues(dm, auth_ledger_version=0) == []
    by = {c["kind"]: c for c in dm["components"]}
    fby = {c["kind"]: c for c in full["components"]}
    assert by["ORIGINALS"]["transport"] == "DELTA" and len(by["ORIGINALS"]["files"]) == 1   # the slice adds one original (A)
    assert by["TEXT_DERIVATIVES"]["transport"] == "DELTA" and len(by["TEXT_DERIVATIVES"]["files"]) == 1
    assert by["RECORDS"]["transport"] == "FULL" and by["KNOWLEDGE_ROWS"]["transport"] == "FULL"
    for k, c in by.items():   # every shipped component declares the FULL-state digest and count
        assert (c["result_digest"], c["result_count"]) == (fby[k]["result_digest"], fby[k]["result_count"])
    status = {a["kind"]: a["status"] for a in dm["capability"]["accounting"]}
    assert status["RESEARCH_AIDS"] == "UNCHANGED_FROM_BASE" and "RESEARCH_AIDS" not in by
    assert status["VECTOR_PACK"] == "OMITTED_DEGRADED"
    sums = parse_sums((root / "S8" / "bundle" / "SHA256SUMS").read_text(encoding="utf-8"))[0]
    assert len([p for p in sums if p.startswith("originals/")]) == 1
    rel = json.loads((root / "S8" / "bundle" / "RELEASE.json").read_text(encoding="utf-8"))
    assert rel["compatibility"]["delta"] is True and rel["compatibility"]["previous_release_id"] == dm["base"]["base_release_id"]
    verify = json.loads((root / "S9" / "VERIFY.json").read_text(encoding="utf-8"))
    assert verify["checks"]["delta"]["base_plus_delta_equals_full_state"] is True
    assert verify["expected_activation"]["result"] == "ACTIVE_DEGRADED"


def test_delta_apply_reproduces_the_full_state(delta_build, tmp_path):
    root = delta_build["root"]
    base_m = json.loads((delta_build["base"] / "KNOWLEDGE_RELEASE.json").read_text(encoding="utf-8"))
    dm = json.loads((root / "S8" / "bundle" / "KNOWLEDGE_RELEASE.json").read_text(encoding="utf-8"))
    got = delta.apply(delta_build["base"], base_m, root / "S8" / "bundle", dm, tmp_path / "applied")
    full = root / "S7" / "full"
    want = {p.relative_to(full).as_posix(): _sha(p.read_bytes()) for p in full.rglob("*")
            if p.is_file() and p.relative_to(full).as_posix() not in delta.MANIFEST_FILES}
    assert got == want


def test_delta_is_deterministic(delta_build, tmp_path, slice_mirror, dev_key, accel_tool):
    s = delta_build
    run_build(s["spec"], tmp_path / "again", mirror=slice_mirror, dev_key=dev_key, accel=accel_tool, apply_budget=False, base_bundle=s["base"])
    assert _tree(s["root"]) == _tree(tmp_path / "again" / s["spec"]["output_dir"])


def test_delta_refusals(delta_build, built, tmp_path, mirror, slice_mirror, dev_key, accel_tool):
    spec = copy.deepcopy(delta_build["spec"])
    with pytest.raises(BuildRefused) as e:   # no base given
        run_build(spec, tmp_path / "a", mirror=slice_mirror, dev_key=dev_key, accel=accel_tool, apply_budget=False)
    assert e.value.code == "BUILD_DELTA_BASE_MISSING" and e.value.stage == "S0"
    spec2 = copy.deepcopy(spec)
    spec2["release"]["base_release_id"] = "R16-other-20261127-00000009"
    with pytest.raises(BuildRefused) as e:   # the base is not the release the spec names
        run_build(spec2, tmp_path / "b", mirror=slice_mirror, dev_key=dev_key, accel=accel_tool, apply_budget=False, base_bundle=delta_build["base"])
    assert e.value.code == "BUILD_DELTA_BASE_MISMATCH"
    # a new state that drops one of the base's originals cannot travel as a delta (originals are add-only)
    base_bundle = delta_build["root"] / "S7" / "full"   # unsigned full state of the slice: sign a copy as a FULL base
    signed = tmp_path / "slice-full"
    shutil.copytree(base_bundle, signed)
    from mimamsa_kbuild.devkeys import load_dev_key
    sk, _pub = load_dev_key(dev_key)
    (signed / "SHA256SUMS.sig").write_bytes(sk.sign((signed / "SHA256SUMS").read_bytes()))
    smaller = load_spec()
    base_id = json.loads((signed / "KNOWLEDGE_RELEASE.json").read_text(encoding="utf-8"))["release_id"]
    smaller["release"].update(base_mode="DELTA", base_release_id=base_id, release_sequence=3,
                              release_id="R16-cp1-fixture-20261127-00000003")
    with pytest.raises(BuildRefused) as e:
        run_build(smaller, tmp_path / "c", mirror=mirror, dev_key=dev_key, accel=accel_tool, apply_budget=False, base_bundle=signed)
    assert e.value.code == "BUILD_DELTA_REMOVAL" and e.value.stage == "S7"
