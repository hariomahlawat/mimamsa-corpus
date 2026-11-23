#!/usr/bin/env python3
"""C10 unified corpus reconciliation: Hugging Face canonical dataset x GitHub raw-data x source registers.

Deterministic and offline. Inputs are pinned:
  * GitHub objects read with `git cat-file` at fixed commits (RAW_DATA_COMMIT for the crawler store; REGISTER_COMMIT for
    SOURCE-LIBRARY-C5 / AUTH-LEDGER / C6-01 registers and the curated MML manifest);
  * the Hugging Face snapshot captured into ../inputs/hf_snapshot/ (listings with path and size, declared sidecar hashes,
    sampled manifest checks and revision evidence). The capture method and its limits are recorded in
    ../inputs/hf_snapshot/CAPTURE.md. No network access is used and no Hugging Face file is downloaded.

Verification levels used in the outputs (never upgraded silently):
  REHASHED_MATCH                 bytes read from the pinned git object and SHA-256 recomputed here.
  HF_PATH_SIZE_MATCH_DECLARED    the HF listing shows the same path and byte size; the SHA-256 is the one the HF
                                 manifest declares (the HF manifest was compared with the GitHub copy by size and sampled
                                 byte ranges only). HF bytes were NOT downloaded or hashed: NOT_CHECKED at byte level.
  HF_UPLOAD_RUN_REMOTE_VERIFIED  an upload workflow log records a read-back SHA-256 of the HF file at an HF commit.
  HF_SIDECAR_DECLARED            the SHA-256 is declared by an HF sidecar JSON; not independently checked.
  C5_HELD_REHASHED               the C5 baseline manifest records a re-hash of a working copy (not in HF or GitHub).

Usage:
  python build_reconciliation.py --repo <git checkout>            write ../outputs/
  python build_reconciliation.py --repo <git checkout> --check    fail (exit 1) if any output differs from a rebuild
"""
import argparse, csv, hashlib, io, json, os, subprocess, sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent
SNAP = PKG / "inputs" / "hf_snapshot"
OUT = PKG / "outputs"

RAW_DATA_COMMIT = "ad77758d4569ba6aafa955cc7843d874489e10f7"
REGISTER_COMMIT = "21e73b8348767d5f1524167fcec538e1aad6e732"
C9_STAT_COMMIT = "cfc52d5792796050dcae351afda5609f7db41a5f"   # PR #41 head: C9 statutory raw-store mapping (input only)
AW = "legal_knowledge/audit_work/"
REG = {
    "copy_register": AW + "SOURCE-LIBRARY-C5/registers/source_copy_register.csv",
    "master_register": AW + "SOURCE-LIBRARY-C5/registers/source_master_register.csv",
    "held_manifest": AW + "SOURCE-LIBRARY-C5/baseline/held_binaries_manifest.csv",
    "crosswalk": AW + "SOURCE-LIBRARY-C5/registers/corpus_crosswalk.csv",
    "ledger_copy_facts": AW + "AUTH-LEDGER/evidence/copy_facts.csv",
    "mml_manifest": "legal_knowledge/manual_sources/MML_Originals_Manifest.csv",
}
STAT_HOLDINGS = AW + "C9-LEGAL-EVIDENCE/STATUTORY/tools/inputs/rawdata_statutory_holdings.csv"


class Git:
    def __init__(self, repo):
        self.repo = repo
        env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        self.env = env

    def run(self, *args):
        return subprocess.run(["git", "-c", "core.useReplaceRefs=false", "-C", self.repo, *args], capture_output=True,
                              check=True, env=self.env).stdout

    def show(self, commit, path):
        return self.run("cat-file", "blob", f"{commit}:{path}")

    def tree(self, commit, prefix):
        out = []
        for line in self.run("ls-tree", "-r", "-l", commit, "--", prefix).decode().splitlines():
            meta, path = line.split("\t", 1)
            mode, typ, oid, size = meta.split()
            out.append((path, oid, int(size)))
        return out

    def blobs(self, oids):
        """Yield (oid, bytes) for each object id via one cat-file --batch process."""
        p = subprocess.Popen(["git", "-C", self.repo, "cat-file", "--batch"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                             env=self.env)
        try:
            for oid in oids:
                p.stdin.write((oid + "\n").encode()); p.stdin.flush()
                hdr = p.stdout.readline().split()
                n = int(hdr[2]); data = p.stdout.read(n); p.stdout.read(1)
                yield oid, data
        finally:
            p.stdin.close(); p.wait()


def rcsv_bytes(b):
    return list(csv.DictReader(io.StringIO(b.decode("utf-8-sig"))))


def rcsv_path(p, delim=","):
    with open(p, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter=delim))


def csv_text(fields, rows):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n", extrasaction="raise")
    w.writeheader()
    for r in rows:
        w.writerow({k: r.get(k, "") for k in fields})
    return buf.getvalue()


def load_hf_listing():
    """All HF FILE rows from the snapshot listings: {path: (size, lfs)}; plus the list of listing files read."""
    files, used = {}, []
    for p in sorted(SNAP.glob("listing_*.tsv")):
        used.append(p.name)
        for line in p.read_text(encoding="utf-8").splitlines():
            t = line.split("\t")
            if t[0] != "FILE":
                if t[0] == "TRUNCATED":
                    raise SystemExit(f"{p.name}: snapshot contains a TRUNCATED marker ({t[3]}); recapture before building")
                continue
            if t[3] in files and files[t[3]][0] != int(t[1]):
                raise SystemExit(f"{p.name}: path listed twice with different sizes: {t[3]}")
            files[t[3]] = (int(t[1]), t[2])
    return files, used


def ext_of(path):
    name = path.rsplit("/", 1)[-1]
    return name.rsplit(".", 1)[-1].lower() if "." in name else ""


def build(repo):
    g = Git(repo)
    hf, listing_files = load_hf_listing()
    totals = rcsv_path(SNAP / "dir_totals.tsv", "\t")
    sidecars = {r["path"]: r for r in rcsv_path(SNAP / "lk_declared_sidecars.tsv", "\t")}
    remote = rcsv_path(SNAP / "upload_run_remote_verified.tsv", "\t")
    rev = json.loads((SNAP / "hf_revision_evidence.json").read_text(encoding="utf-8"))
    samples = json.loads((SNAP / "hf_manifest_samples.json").read_text(encoding="utf-8"))

    # ---------------- GitHub raw-data: re-hash every raw file
    raw_tree = g.tree(RAW_DATA_COMMIT, "data/")
    raw_files = [(p, o, s) for p, o, s in raw_tree if p.startswith("data/raw/")]
    gh_all = {p: s for p, o, s in raw_tree}
    sums_text = g.show(RAW_DATA_COMMIT, "data/SHA256SUMS").decode()
    sums = {}
    for line in sums_text.splitlines():
        h, p = line.split(None, 1)
        sums[p.strip()] = h
    oid2path = defaultdict(list)
    for p, o, s in raw_files:
        oid2path[o].append(p)
    gh_hash = {}
    for oid, data in g.blobs(sorted(oid2path)):
        h = hashlib.sha256(data).hexdigest()
        for p in oid2path[oid]:
            gh_hash[p] = h
    raw_manifest = {r["raw_path"]: r for r in rcsv_bytes(g.show(RAW_DATA_COMMIT, "data/raw_manifest.csv"))}

    # ---------------- registers at REGISTER_COMMIT
    reg = {k: rcsv_bytes(g.show(REGISTER_COMMIT, v)) for k, v in REG.items()}
    try:
        stat = rcsv_bytes(g.show(C9_STAT_COMMIT, STAT_HOLDINGS))
    except subprocess.CalledProcessError:
        raise SystemExit(f"pinned C9 statutory mapping {C9_STAT_COMMIT[:8]}:{STAT_HOLDINGS} is not in this clone (fetch PR #41); refusing to build without it")
    copy_by_sha = defaultdict(list)
    for r in reg["copy_register"]:
        copy_by_sha[r["sha256"]].append(r)
    master = {r["source_id"]: r for r in reg["master_register"]}
    held_by_sha = defaultdict(list)
    for r in reg["held_manifest"]:
        held_by_sha[r["rehashed_sha256"]].append(r)
    ledger_by_sha = defaultdict(list)
    for r in reg["ledger_copy_facts"]:
        ledger_by_sha[r["sha256"]].append(r["copy_id"])
    xw_copy = Counter(r["anchor_copy_id"] for r in reg["crosswalk"] if r["anchor_copy_id"])
    xw_source = Counter(r["source_id"] for r in reg["crosswalk"] if r["source_id"])
    mml_by_sha = {r["sha256"]: r for r in reg["mml_manifest"]}
    stat_by_sha = {r["sha256"]: r for r in stat}
    remote_by_path = {}
    for r in remote:
        remote_by_path.setdefault(r["hf_path"], r)

    # ---------------- per-location sha maps
    loc = defaultdict(lambda: defaultdict(list))   # sha -> location -> [paths]
    sizes = {}
    for p, o, s in raw_files:
        h = gh_hash[p]
        loc[h]["gh_raw_data"].append(p); sizes[h] = s
    hf_raw_status = {}
    for p, (s, lfs) in hf.items():
        if p.startswith("data/raw/"):
            h = sums.get(p)
            if h is None:
                hf_raw_status[p] = "HF_FILE_NOT_IN_DECLARED_MANIFEST"
                continue
            hf_raw_status[p] = "HF_PATH_SIZE_MATCH_DECLARED" if gh_all.get(p) == s else "HF_SIZE_DIFFERS_FROM_GITHUB"
            loc[h]["hf_data_raw"].append(p); sizes.setdefault(h, s)
    lk_binary_ext = {"pdf", "doc", "docx"}
    hf_lk_status = {}
    for p, (s, lfs) in hf.items():
        if p.startswith("legal_knowledge/") and ext_of(p) in lk_binary_ext:
            sc = sidecars.get(p)
            mml = next((m for m in reg["mml_manifest"] if m["repository_path"] == p), None)
            h, lvl = "", "NOT_CHECKED_NO_DECLARED_HASH"
            if p in remote_by_path and remote_by_path[p]["sha256"]:
                h, lvl = remote_by_path[p]["sha256"], "HF_UPLOAD_RUN_REMOTE_VERIFIED"
            elif sc:
                h, lvl = sc["declared_sha256"], "HF_SIDECAR_DECLARED"
            elif mml:
                h, lvl = mml["sha256"], "GITHUB_MML_MANIFEST_DECLARED"
            if sc and int(sc["declared_bytes"]) != s:
                lvl += ";DECLARED_BYTES_DIFFER_FROM_LISTING"
            hf_lk_status[p] = (h, lvl, s)
            if h:
                loc[h]["hf_legal_knowledge"].append(p); sizes.setdefault(h, s)
    for h, rows in held_by_sha.items():
        for r in rows:
            loc[h]["c5_held_working_store"].append(r["held_path"])
        sizes.setdefault(h, int(rows[0]["bytes"]))
    for h in copy_by_sha:
        loc[h]  # registered copies always get a row

    # ---------------- UNIFIED_CORPUS_INVENTORY (one row per distinct SHA-256)
    inv = []
    for h in sorted(loc):
        L = loc[h]
        paths = sorted(set(L.get("gh_raw_data", []) + L.get("hf_data_raw", []) + L.get("hf_legal_knowledge", [])))
        rm = next((raw_manifest[p] for p in sorted(L.get("gh_raw_data", [])) if p in raw_manifest), {})
        cr = copy_by_sha.get(h, [])
        src_ids = sorted({c["source_id"] for c in cr})
        lk_paths = L.get("hf_legal_knowledge", [])
        sc = sidecars.get(lk_paths[0]) if lk_paths else None
        mml = mml_by_sha.get(h)
        st = stat_by_sha.get(h)
        cat = rm.get("category", "") or ("judgment" if any("/judgment" in p for p in lk_paths) else "") or (
            "manual" if mml else "") or (master[src_ids[0]]["publication_type"] if src_ids and src_ids[0] in master else "")
        title = rm.get("title", "") or (sc and sc.get("declared_case_name", "")) or (mml and mml["filename"]) or (
            master[src_ids[0]]["title"] if src_ids and src_ids[0] in master else "")
        in_hf = bool(L.get("hf_data_raw") or L.get("hf_legal_knowledge"))
        in_gh = bool(L.get("gh_raw_data"))
        in_held = bool(L.get("c5_held_working_store"))
        hf_lvl = ""
        if L.get("hf_data_raw"):
            hf_lvl = ";".join(sorted({hf_raw_status[p] for p in L["hf_data_raw"]}))
        elif lk_paths:
            hf_lvl = ";".join(sorted({hf_lk_status[p][1] for p in lk_paths}))
        if in_hf and in_gh:
            pres = "HF_AND_GITHUB_RAW_DATA"
        elif in_hf:
            pres = "HF_ONLY"
        elif in_gh:
            pres = "GITHUB_RAW_DATA_ONLY"
        elif in_held:
            pres = "C5_WORKING_STORE_ONLY_NOT_IN_HF_OR_GITHUB"
        else:
            pres = "REGISTERED_COPY_NOT_FOUND"
        registered = "C5_COPY_REGISTER" if cr else ("MML_MANIFEST" if mml else "")
        if not registered:
            reg_state = "UNREGISTERED_HELD" if (in_hf or in_gh or in_held) else "NOT_HELD"
        else:
            reg_state = "REGISTERED"
        kb_refs = sum(xw_copy.get(c["copy_id"], 0) for c in cr)
        kb_src_refs = sum(xw_source.get(s, 0) for s in src_ids)
        inv.append(dict(
            sha256=h, bytes=sizes.get(h, ""), format=ext_of(paths[0] if paths else (L.get("c5_held_working_store") or [""])[0]),
            category=cat, title=title, doc_id=rm.get("doc_id", ""), parent_doc_id=rm.get("parent_doc_id", ""),
            source_url=rm.get("source_url", "") or (sc and sc.get("declared_source_url", "")) or "",
            retrieved_at=rm.get("retrieved_at", ""),
            presence=pres, hf_paths=";".join(sorted(L.get("hf_data_raw", []) + lk_paths)),
            gh_raw_data_paths=";".join(sorted(L.get("gh_raw_data", []))),
            c5_working_store_paths=";".join(sorted(L.get("c5_held_working_store", []))),
            gh_byte_verification="REHASHED_MATCH" if in_gh and all(sums.get(p) == h for p in L["gh_raw_data"]) else (
                "REHASHED_MISMATCH" if in_gh else ""),
            hf_byte_verification=hf_lvl or ("" if not in_hf else "NOT_CHECKED"),
            register_state=reg_state, registered_in=registered, c5_copy_ids=";".join(sorted(c["copy_id"] for c in cr)),
            c5_source_ids=";".join(src_ids),
            c5_copy_evidence_class=";".join(sorted({c["copy_evidence_class"] for c in cr})),
            auth_ledger_copy_facts=";".join(sorted(ledger_by_sha.get(h, []))),
            kb_exact_anchor_rows=kb_refs, kb_source_rows=kb_src_refs,
            c9_statutory_raw_store="YES" if st else "",
            authentication_state="NOT_AUTHENTICATED_BY_THIS_RECONCILIATION",
            hf_snapshot="UNPINNED_LISTING_2026-11-24" if in_hf else "",
        ))
    inv_fields = ["sha256", "bytes", "format", "category", "title", "doc_id", "parent_doc_id", "source_url", "retrieved_at",
                  "presence", "hf_paths", "gh_raw_data_paths", "c5_working_store_paths", "gh_byte_verification",
                  "hf_byte_verification", "register_state", "registered_in", "c5_copy_ids", "c5_source_ids",
                  "c5_copy_evidence_class", "auth_ledger_copy_facts", "kb_exact_anchor_rows", "kb_source_rows",
                  "c9_statutory_raw_store", "authentication_state", "hf_snapshot"]

    # ---------------- REPOSITORY_RECONCILIATION (per tree segment)
    def seg(path):
        parts = path.split("/")
        if parts[0] == "data" and len(parts) > 2 and parts[1] in ("raw", "sections"):
            return "/".join(parts[:3])
        if parts[0] == "data":
            return "/".join(parts[:2]) if len(parts) > 2 else path
        if parts[0] == "legal_knowledge":
            return "/".join(parts[:2]) if len(parts) > 2 else path
        return parts[0] if len(parts) > 1 else path
    gh_lk = {p: s for p, o, s in g.tree(REGISTER_COMMIT, "legal_knowledge/") if not p.startswith(AW)}
    gh_lk.update({p: s for p, o, s in g.tree(REGISTER_COMMIT, "schema/")})
    gh_map = dict(gh_all); gh_map.update(gh_lk)
    segs = defaultdict(lambda: Counter())
    for p, s in gh_map.items():
        segs[seg(p)]["gh_files"] += 1; segs[seg(p)]["gh_bytes"] += s
    for p, (s, lfs) in hf.items():
        k = seg(p)
        segs[k]["hf_files_listed"] += 1; segs[k]["hf_bytes_listed"] += s
        if p in gh_map:
            segs[k]["same_path_same_size" if gh_map[p] == s else "same_path_size_differs"] += 1
        else:
            segs[k]["hf_only"] += 1
    for p in gh_map:
        if p not in hf:
            segs[seg(p)]["gh_only_or_not_listed"] += 1
    tot = {r["dir"]: r for r in totals}
    rep = []
    for k in sorted(segs):
        c = segs[k]
        t = tot.get(k)
        listed = c["hf_files_listed"]
        if t:
            hf_total, how = int(t["hf_total_files"]), t["how_obtained"]
        else:
            hf_total, how = listed, "full listing" if listed else ""
        if k.startswith("data/raw/"):
            lvl = "GITHUB_REHASHED;HF_PATH_SIZE_DECLARED"
        elif listed:
            lvl = "PATH_SIZE_ONLY"
        elif t:
            lvl = "COUNT_ONLY"
        else:
            lvl = "NOT_LISTED_ON_HF"
        rep.append(dict(segment=k, gh_commit=RAW_DATA_COMMIT if k.startswith("data") else REGISTER_COMMIT,
                        gh_files=c["gh_files"], gh_bytes=c["gh_bytes"], hf_total_files=hf_total, hf_total_how=how,
                        hf_files_listed=listed, hf_bytes_listed=c["hf_bytes_listed"],
                        same_path_same_size=c["same_path_same_size"], same_path_size_differs=c["same_path_size_differs"],
                        hf_only=c["hf_only"], gh_not_in_hf_listing=c["gh_only_or_not_listed"] if listed else "NOT_COMPARED",
                        verification_level=lvl, hf_snapshot="UNPINNED_LISTING_2026-11-24" if listed or t else ""))
    rep_fields = ["segment", "gh_commit", "gh_files", "gh_bytes", "hf_total_files", "hf_total_how", "hf_files_listed",
                  "hf_bytes_listed", "same_path_same_size", "same_path_size_differs", "hf_only", "gh_not_in_hf_listing",
                  "verification_level", "hf_snapshot"]

    # ---------------- COPY_EQUIVALENCE_REGISTER
    eq = []
    for r in inv:
        locs = [x for x in ("hf_data_raw", "hf_legal_knowledge", "gh_raw_data", "c5_held_working_store") if loc[r["sha256"]].get(x)]
        npaths = sum(len(set(loc[r["sha256"]].get(x, []))) for x in locs)
        if len(locs) > 1 or npaths > 1:
            mirror = set(locs) == {"hf_data_raw", "gh_raw_data"} and set(loc[r["sha256"]]["hf_data_raw"]) == set(loc[r["sha256"]]["gh_raw_data"])
            has_hf = any(x.startswith("hf_") for x in locs)
            hashed = [x for x in locs if not x.startswith("hf_")]
            basis = ("SHA-256 re-hashed identical across " + ", ".join(hashed) if len(hashed) > 1 or npaths > len(locs) else
                     "SHA-256 re-hashed for " + ", ".join(hashed) if hashed else "declared SHA-256 only")
            if has_hf:
                basis += "; HF copy: same path and size with the HF-declared SHA-256, HF bytes NOT_CHECKED (review RC-01)"
            eq.append(dict(group_id=f"SB-{r['sha256'][:12]}", classification="SAME_BYTES_SAME_DOCUMENT",
                           kind="HF_GITHUB_MIRROR_SAME_PATH" if mirror else "CROSS_STORE_OR_MULTI_PATH",
                           basis=basis + " (byte identity only; not authenticity or legal status)",
                           sha256s=r["sha256"], locations=";".join(locs), copies=npaths, identity=r["title"],
                           c5_source_ids=r["c5_source_ids"], review="HF_BYTES_NOT_CHECKED" if has_hf else "NONE_NEEDED_FOR_IDENTITY"))
    by_source = defaultdict(set)
    for c in reg["copy_register"]:
        by_source[c["source_id"]].add(c["sha256"])
    for s, hs in sorted(by_source.items()):
        if len(hs) > 1:
            roles = sorted({c["copy_role"] for c in reg["copy_register"] if c["source_id"] == s})
            eq.append(dict(group_id=f"SD-{s}", classification="SAME_C5_SOURCE_ID_DIFFERENT_BYTES",
                           basis=f"one C5 source_id, {len(hs)} distinct copies (copy roles: {', '.join(roles)})",
                           sha256s=";".join(sorted(hs)), locations="", copies=len(hs), identity=master.get(s, {}).get("title", ""),
                           c5_source_ids=s, review="RENDITION_LANGUAGE_OR_EDITION_REVIEW: a shared C5 source id does not prove the same legal text (see copy_role; review RC-06)"))
    by_doc = defaultdict(set)
    for p, r in raw_manifest.items():
        key = r.get("doc_id") or r.get("parent_doc_id")
        if key:
            by_doc[key].add(r["sha256"])
    for d, hs in sorted(by_doc.items()):
        if len(hs) > 1:
            eq.append(dict(group_id=f"RD-{d}", classification="SAME_DOC_ID_DIFFERENT_BYTES_REQUIRES_IDENTITY_REVIEW",
                           basis=f"crawler manifest doc_id/parent_doc_id {d} carries {len(hs)} distinct files",
                           sha256s=";".join(sorted(hs)), locations="gh_raw_data;hf_data_raw", copies=len(hs), identity=d,
                           c5_source_ids="", review="IDENTITY_REVIEW (attachments, alternate renditions or versions)"))
    by_url = defaultdict(set)
    for p, r in raw_manifest.items():
        if r.get("source_url"):
            by_url[r["source_url"]].add(r["sha256"])
    for u, hs in sorted(by_url.items()):
        if len(hs) > 1:
            eq.append(dict(group_id=f"SU-{hashlib.sha256(u.encode()).hexdigest()[:12]}",
                           classification="SAME_SOURCE_URL_DIFFERENT_BYTES",
                           basis="same retrieval URL served different bytes (watermarking, version or re-issue)",
                           sha256s=";".join(sorted(hs)), locations="gh_raw_data;hf_data_raw", copies=len(hs), identity=u,
                           c5_source_ids="", review="VERSION_OR_RENDITION_REVIEW"))
    eq_fields = ["group_id", "classification", "kind", "basis", "sha256s", "locations", "copies", "identity", "c5_source_ids", "review"]

    # ---------------- SOURCE_IDENTITY_CONFLICTS
    conf = []
    for h, cs in sorted(copy_by_sha.items()):
        srcs = sorted({c["source_id"] for c in cs})
        if len(srcs) > 1:
            conf.append(dict(conflict_id=f"IC-MULTISRC-{h[:12]}", kind="ONE_COPY_TWO_SOURCE_IDS", sha256=h,
                             detail="the same bytes are registered under " + ", ".join(srcs), status="REVIEW"))
    for p, (h, lvl, s) in sorted(hf_lk_status.items()):
        if "DECLARED_BYTES_DIFFER" in lvl:
            conf.append(dict(conflict_id=f"IC-SIZE-{h[:12]}", kind="SIDECAR_BYTES_DIFFER_FROM_LISTING", sha256=h, detail=p, status="REVIEW"))
        if h and h in held_by_sha and int(held_by_sha[h][0]["bytes"]) != s:
            conf.append(dict(conflict_id=f"IC-HELDSIZE-{h[:12]}", kind="SAME_HASH_DIFFERENT_SIZE", sha256=h, detail=p, status="ERROR"))
    for p in sorted(hf_raw_status):
        if hf_raw_status[p] != "HF_PATH_SIZE_MATCH_DECLARED":
            conf.append(dict(conflict_id=f"IC-HFRAW-{hashlib.sha256(p.encode()).hexdigest()[:12]}", kind=hf_raw_status[p],
                             sha256=sums.get(p, ""), detail=p, status="REVIEW"))
    for p, h in sorted(gh_hash.items()):
        if sums.get(p) != h:
            conf.append(dict(conflict_id=f"IC-GHRAW-{h[:12]}", kind="GITHUB_RAW_HASH_DIFFERS_FROM_SHA256SUMS", sha256=h, detail=p, status="ERROR"))
        if p.rsplit("/", 1)[1].split(".")[0] != h:
            conf.append(dict(conflict_id=f"IC-NAME-{h[:12]}", kind="FILENAME_IS_NOT_CONTENT_HASH", sha256=h, detail=p, status="REVIEW"))
    for p, r in sorted(raw_manifest.items()):
        if gh_hash.get(p) and r["sha256"] != gh_hash[p]:
            conf.append(dict(conflict_id=f"IC-MANIFEST-{r['sha256'][:12]}", kind="RAW_MANIFEST_HASH_DIFFERS", sha256=r["sha256"], detail=p, status="ERROR"))
    for h, r in sorted(stat_by_sha.items()):
        if r.get("category") == "rule" and "Act" in r.get("title", "") and "rule" not in r.get("title", "").lower():
            conf.append(dict(conflict_id=f"IC-CATEGORY-{h[:12]}", kind="CRAWLER_CATEGORY_DOUBTFUL",
                             sha256=h, detail=f"category '{r['category']}' for title '{r['title']}' (C9 finding: Act filed as rule)",
                             status="REVIEW"))
    conf_fields = ["conflict_id", "kind", "sha256", "detail", "status"]

    # ---------------- UNREGISTERED_HELD_SOURCES
    unreg = []
    for r in inv:
        if r["register_state"] != "UNREGISTERED_HELD":
            continue
        if r["category"] == "judgment" and not r["hf_paths"].startswith("legal_knowledge/") and not r["c5_working_store_paths"]:
            continue  # bulk crawler judgments are summarised below, not listed one by one
        unreg.append(dict(sha256=r["sha256"], presence=r["presence"], category=r["category"], title=r["title"],
                          doc_id=r["doc_id"] or r["parent_doc_id"], hf_paths=r["hf_paths"], gh_raw_data_paths=r["gh_raw_data_paths"],
                          source_url=r["source_url"], hf_byte_verification=r["hf_byte_verification"],
                          c9_statutory_raw_store=r["c9_statutory_raw_store"],
                          proposed_action="REGISTRATION_PROPOSAL (copy identity, provenance and fidelity review before any register change)"))
    bulk = [r for r in inv if r["register_state"] == "UNREGISTERED_HELD" and r["category"] == "judgment"
            and not r["hf_paths"].startswith("legal_knowledge/") and not r["c5_working_store_paths"]]
    unreg.append(dict(sha256="(summary)", presence="HF_AND_GITHUB_RAW_DATA", category="judgment",
                      title=f"{len(bulk)} crawler judgment files (HC and SC) not in the C5 copy register",
                      doc_id="", hf_paths="data/raw/hc/*; data/raw/sci/*", gh_raw_data_paths="data/raw/hc/*; data/raw/sci/*",
                      source_url="see data/raw_manifest.csv", hf_byte_verification="HF_PATH_SIZE_MATCH_DECLARED",
                      c9_statutory_raw_store="", proposed_action="JUDGMENT_RECONCILIATION (match to curated cases by citation and case number; no automatic merge)"))
    unreg_fields = ["sha256", "presence", "category", "title", "doc_id", "hf_paths", "gh_raw_data_paths", "source_url",
                    "hf_byte_verification", "c9_statutory_raw_store", "proposed_action"]

    # ---------------- MISSING_SOURCE_EVIDENCE
    miss = []
    for r in inv:
        if r["presence"] == "C5_WORKING_STORE_ONLY_NOT_IN_HF_OR_GITHUB":
            miss.append(dict(item=r["c5_copy_ids"] or r["sha256"], kind="REGISTERED_COPY_BYTES_NOT_IN_CANONICAL_STORE",
                             sha256=r["sha256"], source_ids=r["c5_source_ids"], title=r["title"],
                             detail=f"held only in the C5 working store ({r['c5_working_store_paths'].split(';')[0]}); "
                                    f"KB exact-anchor rows: {r['kb_exact_anchor_rows']}",
                             action="PRESERVATION: owner to place the registered bytes in the canonical HF dataset (not done here)"))
        elif r["presence"] == "REGISTERED_COPY_NOT_FOUND":
            miss.append(dict(item=r["c5_copy_ids"], kind="REFERENCED_COPY_NOT_FOUND", sha256=r["sha256"], source_ids=r["c5_source_ids"],
                             title=r["title"], detail="registered SHA-256 not found in HF, GitHub raw-data or the C5 working store",
                             action="LOCATE_OR_MARK_LOST"))
    held_src = {s for c in reg["copy_register"] for s in [c["source_id"]]}
    for s, m in sorted(master.items()):
        if m["holding_state"].startswith("NOT_HELD") and s not in held_src:
            miss.append(dict(item=s, kind="SOURCE_NOT_HELD_IN_C5_REGISTER", sha256="", source_ids=s, title=m["title"],
                             detail=f"holding_state {m['holding_state']}; acquisition_state {m['acquisition_state']}",
                             action="CHECK_UNIFIED_INVENTORY_BEFORE_ACQUISITION (see statutory and judicial recomputation)"))
    miss_fields = ["item", "kind", "sha256", "source_ids", "title", "detail", "action"]

    # ---------------- counts, report, manifest
    cnt = Counter(r["presence"] for r in inv)
    by_cat = Counter((r["category"] or "unknown") for r in inv)
    regc = Counter(r["register_state"] for r in inv)
    eqc = Counter(r["classification"] + (f" ({r['kind']})" if r.get("kind") else "") for r in eq)
    confc = Counter(r["kind"] for r in conf)
    missc = Counter(r["kind"] for r in miss)
    hf_raw_files = sum(1 for p in hf if p.startswith("data/raw/"))
    hf_raw_match = sum(1 for v in hf_raw_status.values() if v == "HF_PATH_SIZE_MATCH_DECLARED")
    gh_raw_ok = sum(1 for p, h in gh_hash.items() if sums.get(p) == h)
    out = {}
    out["UNIFIED_CORPUS_INVENTORY.csv"] = csv_text(inv_fields, inv)
    out["REPOSITORY_RECONCILIATION.csv"] = csv_text(rep_fields, rep)
    out["COPY_EQUIVALENCE_REGISTER.csv"] = csv_text(eq_fields, eq)
    out["SOURCE_IDENTITY_CONFLICTS.csv"] = csv_text(conf_fields, conf)
    out["UNREGISTERED_HELD_SOURCES.csv"] = csv_text(unreg_fields, unreg)
    out["MISSING_SOURCE_EVIDENCE.csv"] = csv_text(miss_fields, miss)
    summary = dict(
        distinct_copies=len(inv), presence=dict(sorted(cnt.items())), category=dict(sorted(by_cat.items())),
        register_state=dict(sorted(regc.items())), equivalence=dict(sorted(eqc.items())), conflicts=dict(sorted(confc.items())),
        missing=dict(sorted(missc.items())), gh_raw_files=len(raw_files), gh_raw_rehash_match=gh_raw_ok,
        hf_raw_files_listed=hf_raw_files, hf_raw_same_path_size=hf_raw_match,
        hf_files_listed_total=len(hf), hf_legal_knowledge_binaries=len(hf_lk_status),
        unregistered_listed=len(unreg) - 1, bulk_unregistered_judgments=len(bulk))
    out["CORPUS_RECONCILIATION_REPORT.md"] = report_md(summary, rev, samples, rep, listing_files)
    in_hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(SNAP.iterdir()) if p.is_file()}
    manifest = dict(
        schema="c10-reconciliation-manifest/1",
        github=dict(repository="hariomahlawat/mimamsa-corpus", raw_data_commit=RAW_DATA_COMMIT, register_commit=REGISTER_COMMIT,
                    c9_statutory_mapping_commit=C9_STAT_COMMIT, register_paths=REG, sha256sums_sha256=hashlib.sha256(sums_text.encode()).hexdigest()),
        huggingface=dict(repository="datasets/hariomahlawat/mimamsa-corpus", visibility="private",
                         revision_pinned=rev.get("revision_pinned"), last_recorded_commit=rev.get("last_recorded_commit"),
                         capture=rev.get("capture"), byte_level_verification="NOT_CHECKED (no download access)"),
        hf_snapshot_inputs=in_hashes, summary=summary,
        outputs={k: hashlib.sha256(v.encode()).hexdigest() for k, v in sorted(out.items())},
        companion_files={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(OUT.glob("*"))
                         if p.is_file() and p.name not in out and p.name != "RECONCILIATION_MANIFEST.json"})
    out["RECONCILIATION_MANIFEST.json"] = json.dumps(manifest, indent=1, sort_keys=True) + "\n"
    return out


def report_md(s, rev, samples, rep, listing_files):
    L = ["# Corpus reconciliation report (generated)", "",
         "Generated by `tools/build_reconciliation.py` from pinned inputs; rebuild with `--check`. Counts are distinct SHA-256 "
         "values (copies), not documents. A matching SHA-256 proves byte identity only: not authenticity, currency or "
         "applicability. Nothing here authenticates a source or changes a register.", "",
         "## Snapshot identity", "",
         f"- GitHub `raw-data` commit `{RAW_DATA_COMMIT}`; registers at staging `{REGISTER_COMMIT}`.",
         f"- Hugging Face `datasets/hariomahlawat/mimamsa-corpus` (private). Revision pinned: **{rev.get('revision_pinned')}**. "
         f"Last commit recorded in a workflow log: `{rev.get('last_recorded_commit', {}).get('sha', '')}` "
         f"({rev.get('last_recorded_commit', {}).get('time', '')}); whether it is the current head is not verifiable "
         "with the access available.",
         f"- Hugging Face capture: {rev.get('capture', '')}. Listing files: {', '.join(listing_files)}.", "",
         "## Byte-level verification", "",
         f"- GitHub raw-data: {s['gh_raw_rehash_match']} of {s['gh_raw_files']} files re-hashed here and equal to `data/SHA256SUMS`.",
         f"- Hugging Face `data/raw`: {s['hf_raw_same_path_size']} of {s['hf_raw_files_listed']} listed files have the same path "
         "and size as GitHub; their hashes are the HF manifest's declared values. **HF bytes were not downloaded: NOT_CHECKED.**",
         f"- HF manifests: {samples.get('summary', '')}", "",
         "## Distinct copies", "", "| Presence | Copies |", "| --- | --- |"]
    L += [f"| {k} | {v} |" for k, v in s["presence"].items()]
    L += ["", f"Total distinct copies: {s['distinct_copies']}.", "", "| Register state | Copies |", "| --- | --- |"]
    L += [f"| {k} | {v} |" for k, v in s["register_state"].items()]
    L += ["", "| Category (crawler manifest or register) | Copies |", "| --- | --- |"]
    L += [f"| {k} | {v} |" for k, v in s["category"].items()]
    L += ["", "## Equivalence, conflicts and gaps", "", "| Item | Count |", "| --- | --- |"]
    L += [f"| equivalence: {k} | {v} |" for k, v in s["equivalence"].items()]
    L += [f"| conflict: {k} | {v} |" for k, v in s["conflicts"].items()]
    L += [f"| missing: {k} | {v} |" for k, v in s["missing"].items()]
    L += [f"| unregistered held copies listed individually | {s['unregistered_listed']} |",
          f"| crawler judgment copies not in the C5 register (summarised) | {s['bulk_unregistered_judgments']} |", "",
          "## Repository segments", "", "| Segment | GitHub files | HF files (total) | HF how | same path+size | size differs | HF only | level |",
          "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    L += [f"| {r['segment']} | {r['gh_files']} | {r['hf_total_files']} | {r['hf_total_how']} | {r['same_path_same_size']} | "
          f"{r['same_path_size_differs']} | {r['hf_only']} | {r['verification_level']} |" for r in rep]
    return "\n".join(L) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    out = build(a.repo)
    if a.check:
        bad = [k for k, v in out.items() if not (OUT / k).is_file() or (OUT / k).read_text(encoding="utf-8") != v]
        if bad:
            print("RECONCILIATION CHECK FAILED: " + ", ".join(bad), file=sys.stderr)
            return 1
        print(f"reconciliation outputs reproduce ({len(out)} files)")
        return 0
    OUT.mkdir(parents=True, exist_ok=True)
    for k, v in out.items():
        (OUT / k).write_text(v, encoding="utf-8")
    print(f"wrote {len(out)} files to {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
