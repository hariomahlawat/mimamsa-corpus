"""Shared helpers for the C13 A6 forms workstream. Python 3.11+ compatible.

Roots (override with environment variables):
  A6_SCRATCH  session scratchpad (read-only use of the held working store)
  A6_C7       git object store holding raw-data commit C7_COMMIT
Every source is sha256-verified before use; a mismatch raises.
The FOUO-marked Regulations for the Air Force 2000 copy is refused outright.
"""
import hashlib
import os
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
A6_DIR = os.path.dirname(HERE)
REPO = os.path.abspath(os.path.join(A6_DIR, "..", "..", ".."))
C12_FR = os.path.join(REPO, "legal_knowledge", "audit_work", "C12-CONSOLIDATION", "forms_registry")

DEFAULT_SCRATCH = "/tmp/claude-0/-home-user-mimamsa-corpus/9dd71a54-b050-5d1e-a2e9-2ceef8ac3e20/scratchpad"
SCRATCH = os.environ.get("A6_SCRATCH", DEFAULT_SCRATCH)
C7 = os.environ.get("A6_C7", "/home/user/c7")
C7_COMMIT = "ad77758d"

# Restricted material (owner directive C13 s.31). Single source of truth is
# config/restricted_material.json with scripts/restricted_material.py (branch
# claude/c13-gov). When that file is present in the checkout it is loaded and
# merged; the embedded mirror below (RM-001) is the fallback and is checked
# against the gov-branch file by tests/test_legal_audit_c13_forms_restricted.py.
RESTRICTED_MIRROR = {
    "restriction_id": "RM-001",
    "doc_id": "regs-regulations-for-the-air-force-reprinted-edition-2000",
    "source_sha256": "4284820e5bc2fb7f52ae9fbe8a61650f1579e9b6389ba206a916a69fed016b14",
    "derived_sha256": [
        "212ac873869bf3298b8194f6ad8a1a994b990242a3dab5d0f927e3e4c4ce2cea",
        "f26d3de7dfda70143b10b02dc664f13de342a74f0bee767387492363ac1421c5",
    ],
    "hosted_paths": [
        "data/raw/indiacode/0000/4284820e5bc2fb7f52ae9fbe8a61650f1579e9b6389ba206a916a69fed016b14.pdf",
        "data/meta/regs-regulations-for-the-air-force-reprinted-edition-2000.json",
        "data/text/regs-regulations-for-the-air-force-reprinted-edition-2000.txt",
    ],
}


def _restricted_sets():
    import json
    items = [RESTRICTED_MIRROR]
    cfg = os.path.join(REPO, "config", "restricted_material.json")
    if os.path.isfile(cfg):
        with open(cfg, encoding="utf-8") as fh:
            items = items + json.load(fh)["items"]
    shas, ids, paths = set(), set(), set()
    for it in items:
        shas.add(it["source_sha256"].lower())
        shas.update(x.lower() for x in it.get("derived_sha256", []))
        ids.add(it["doc_id"])
        paths.update(it.get("hosted_paths", []))
    return shas, ids, paths


EXCLUDED_SHA256, EXCLUDED_DOC_IDS, EXCLUDED_PATHS = _restricted_sets()


def is_restricted(sha256=None, doc_id=None, path=None):
    if sha256 and sha256.lower() in EXCLUDED_SHA256:
        return True
    if doc_id and doc_id in EXCLUDED_DOC_IDS:
        return True
    if path:
        p = path.replace("\\", "/").lstrip("./")
        if p in EXCLUDED_PATHS or any(x in p for x in EXCLUDED_SHA256) or any(i in p for i in EXCLUDED_DOC_IDS):
            return True
    return False


# Official (non-MML) copies used for C13 transcription. HF path = permanent preserved copy.
SOURCES = {
    "AR54-GAZ": dict(
        root="scratch", path="downloads/discovery/ia_in.gazette.central.w.1954-11-27.103686.pdf",
        sha256="c5ef95a9d553685aa655f041b71d8360d6272e2775a19a3d6e7273c6cbd0aca6",
        hf_path="legal_knowledge/preservation/c5_working_store/c5/c5ef95a9d553685aa655f041b71d8360d6272e2775a19a3d6e7273c6cbd0aca6/ia_in.gazette.central.w.1954-11-27.103686.pdf",
        title="Gazette of India No. 47, Pt II-Sec 4, 27-11-1954: S.R.O. 484 (Army Rules, 1954) with Appendices",
        authority="Ministry of Defence (S.R.O. 484), Gazette of India", edition="as notified 27-11-1954"),
    "AR-AMD-1993": dict(
        root="scratch", path="downloads/independent-reviewer-D/amend/in.gazette.central.e.1993-12-06.16490/16490.pdf",
        sha256="e9bf2114ab633716ea954db6e100be858e45949384f9fc0667364308bff46912",
        hf_path="legal_knowledge/preservation/c5_working_store/e9/e9bf2114ab633716ea954db6e100be858e45949384f9fc0667364308bff46912/16490.pdf",
        title="Gazette of India Extraordinary Pt II-Sec 4, 06-12-1993: S.R.O. 17(E) (Army Rules amendment)",
        authority="Ministry of Defence (S.R.O. 17(E)), Gazette of India Extraordinary", edition="as published 06-12-1993"),
    "AR-AMD-1965": dict(
        root="scratch", path="downloads/independent-reviewer-D/amend/in.gazette.central.w.1965-04-10.81813/81813.pdf",
        sha256="682afce5e2f1f3ce8381e74664fb2fb8d98a4571c9fb8a92160ff11193a8c046",
        hf_path="legal_knowledge/preservation/c5_working_store/68/682afce5e2f1f3ce8381e74664fb2fb8d98a4571c9fb8a92160ff11193a8c046/81813.pdf",
        title="Gazette of India Pt II-Sec 4 No.15, 10-04-1965: S.R.O. 116 (Army Rules amendment)",
        authority="Ministry of Defence (S.R.O. 116), Gazette of India", edition="as published 10-04-1965"),
    "AR54-IC": dict(
        root="scratch", path="downloads/independent-reviewer-A/army-rules.pdf",
        sha256="48f52219121bf74d070bc832e4573f2f512b239e0a0441ba96b1daca2983a727",
        hf_path="data/raw/indiacode/0000/48f52219121bf74d070bc832e4573f2f512b239e0a0441ba96b1daca2983a727.pdf",
        title="Army Rules, 1954: India Code compilation (native text layer)",
        authority="India Code (Legislative Department) compilation", edition="as-on date not printed"),
    "AFTPR08-C7": dict(
        root="c7git", path="data/raw/indiacode/0000/590cf7cd393564eacab37566d605357662429f900ea58a96f0ce0e5bb0e0e317.pdf",
        sha256="590cf7cd393564eacab37566d605357662429f900ea58a96f0ce0e5bb0e0e317",
        hf_path="data/raw/indiacode/0000/590cf7cd393564eacab37566d605357662429f900ea58a96f0ce0e5bb0e0e317.pdf",
        title="Armed Forces Tribunal (Procedure) Rules, 2008: India Code file (Gazette Extraordinary scan)",
        authority="Ministry of Defence, Gazette of India Extraordinary (via India Code)", edition="as notified 2008 (scan)"),
    "DPPR53-C7": dict(
        root="c7git", path="data/raw/indiacode/0000/d969593bbb689144e39a406cab3d6fa806216438871ddf6321ba084e24c9b203.pdf",
        sha256="d969593bbb689144e39a406cab3d6fa806216438871ddf6321ba084e24c9b203",
        hf_path="data/raw/indiacode/0000/d969593bbb689144e39a406cab3d6fa806216438871ddf6321ba084e24c9b203.pdf",
        title="Army and Air Force (Disposal of Private Property) Rules, 1953: India Code file",
        authority="India Code", edition="India Code bitstream"),
    "NA57-C7": dict(
        root="c7git", path="data/raw/indiacode/1957/db6d2b3ef1e60d95f4d8127730430a01a3aab39637d88a39901aa20142399083.pdf",
        sha256="db6d2b3ef1e60d95f4d8127730430a01a3aab39637d88a39901aa20142399083",
        hf_path="data/raw/indiacode/1957/db6d2b3ef1e60d95f4d8127730430a01a3aab39637d88a39901aa20142399083.pdf",
        title="The Navy Act, 1957: India Code compilation",
        authority="Parliament (India Code compilation)", edition="India Code compilation; as-on date per copy"),
    "AFA50-C7": dict(
        root="c7git", path="data/raw/indiacode/1950/ef50375ea0550ddc1e6414c45bd9403d3842aa395a297e71e2e627403632ebd0.pdf",
        sha256="ef50375ea0550ddc1e6414c45bd9403d3842aa395a297e71e2e627403632ebd0",
        hf_path="data/raw/indiacode/1950/ef50375ea0550ddc1e6414c45bd9403d3842aa395a297e71e2e627403632ebd0.pdf",
        title="The Air Force Act, 1950: India Code compilation",
        authority="Parliament (India Code compilation)", edition="India Code compilation; as-on date per copy"),
    "NR65-P2-C7": dict(
        root="c7git", path="data/raw/indiacode/0000/884a893c725d4025dc95009dcd5aedf158d6726bf499e5a0690d0cdbc7b4064d.pdf",
        sha256="884a893c725d4025dc95009dcd5aedf158d6726bf499e5a0690d0cdbc7b4064d",
        hf_path="data/raw/indiacode/0000/884a893c725d4025dc95009dcd5aedf158d6726bf499e5a0690d0cdbc7b4064d.pdf",
        title="Regulations for the Navy Part II (Statutory): India Code file",
        authority="Central Government / Naval Headquarters (via India Code)", edition="imprint 'GMGIPND - JOB II - 224 Naval (JC 5833) - 21-4-65' (last page, text layer)"),
    "NR65-P4-C7": dict(
        root="c7git", path="data/raw/indiacode/0000/e4148ee0757de0adfdeb5acf68e7bd8c752f0d21d11c329f7484e108026c9f58.pdf",
        sha256="e4148ee0757de0adfdeb5acf68e7bd8c752f0d21d11c329f7484e108026c9f58",
        hf_path="data/raw/indiacode/0000/e4148ee0757de0adfdeb5acf68e7bd8c752f0d21d11c329f7484e108026c9f58.pdf",
        title="Regulations for the Navy Part IV (Indian Naval Auxiliary Service Regulations, 1973): India Code file",
        authority="Naval Headquarters (Amendment No. 82, 01-10-1977, via India Code)", edition="as inserted by Amendment No. 82 (Batch No. 26), 01-10-1977"),
}


def sha256(b):
    return hashlib.sha256(b).hexdigest()


def read_source(key):
    s = SOURCES[key]
    if is_restricted(sha256=s["sha256"], path=s["path"]):
        raise PermissionError("restricted material (RM list); refused")
    if s["root"] == "scratch":
        with open(os.path.join(SCRATCH, s["path"]), "rb") as fh:
            b = fh.read()
    else:
        b = subprocess.run(["git", "-C", C7, "cat-file", "blob", f"{C7_COMMIT}:{s['path']}"],
                           check=True, capture_output=True).stdout
    h = sha256(b)
    if h != s["sha256"]:
        raise ValueError(f"sha256 mismatch for {key}: {h}")
    return b


def open_pdf(key):
    import pymupdf
    return pymupdf.open(stream=read_source(key), filetype="pdf")
