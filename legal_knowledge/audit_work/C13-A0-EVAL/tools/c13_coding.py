#!/usr/bin/env python3
"""C13-A0 double-coding toolkit.

  packets            build blinded coder sheets for the three holdouts (two coders each) + evaluator item maps
  leakcheck SHEET    fail if a sheet carries anything beyond source pointers and blank coding fields
                     (--completed --coder ID --packet PACKET to check a returned sheet)
  agree              inter-coder agreement (strict unit level, Cohen's kappa, Krippendorff's alpha, span F1)
  adjsheet           adjudication sheet showing the competing codings anonymised as X / Y (+ sealed key)
  truth              reference annotations from agreed units + adjudication (asserts coverage, C12 tools F03/F09)
  store / verify     versioned reference-annotation storage with sha256 manifests

`python -I -B c13_coding.py [--check]` (no subcommand) builds the packets, leak-checks every packet and
writes/compares outputs/packets/** and outputs/holdouts/*/ITEM_MAP.csv.
"""
import argparse
import csv
import io
import json
import re
import shutil
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from c13_common import OUT, PKG, read_csv, render_csv, render_json, seeded_hash, sha256_file, write_or_check  # noqa
from c13_tasks import POINTER_COLS, TASKS, HOLDOUT_TASK, content_tokens, norm_ws  # noqa: E402
import c13_stats as S  # noqa: E402

PACKET_SEED = "mimamsa-c13-packets"
CODER_SLOTS = ("coder_1", "coder_2")
ITEM_ID_RE = re.compile(r"^(HO|HH|HR)13-[0-9a-f]{10}$")
RAW_PATH_RE = re.compile(r"^(data/raw/[a-z_]+/\d{4}/[0-9a-f]{64}\.pdf|legal_knowledge/[A-Za-z0-9_./\-]+\.pdf)$")
STORES = {"HF@5524c3d9 (C12 hash ledger)", "HF@15bd03cc (C12 staged)"}
FORBIDDEN_COL_RE = re.compile(r"stratum|weight|prob|rank|pred|extract|model|crawler|meta|agree|adjud|design|"
                              r"court|year|scope|spent|quality|^n_|_n$|^pi$|truth|gold|label_", re.I)
FORBIDDEN_VALUE_TOKENS = ("BATCH_OR_MULTI", "PARTY_SPECIFIC", "PENSION_OR_DISCIPLINARY", "disagreement",
                          "batch_or_multi", "pension_or_disciplinary", "MULTI_OPINION", "LONG_15P", "MEDIUM_5_14P",
                          "SHORT_UNDER_15P", "TREATMENT_CUE", "RESOLVED_CITATION", "NO_DETECTED_CITATION",
                          "UNRESOLVED_CITATION", "design_weight", "inclusion_probability", "AUTOMATED_CANDIDATE",
                          "OUTCOME_UNVERIFIED", "V3H", "V4")
PREFIX = {"H-OUT-C13": "HO13", "H-HOLD-C13": "HH13", "H-REL-C13": "HR13"}


class LeakError(ValueError):
    pass


# ------------------------------------------------------------------------------------------------ packets
def item_id(holdout, unit):
    return f"{PREFIX[holdout]}-{seeded_hash(PACKET_SEED + '|' + holdout, unit)[:10]}"


def build_packets():
    outputs = {}
    for h, task_name in HOLDOUT_TASK.items():
        task = TASKS[task_name]
        sample = read_csv(OUT / "holdouts" / h / "SAMPLE.csv")
        items, imap = [], []
        for r in sample:
            unit = r["judgment_key"] + (f"#p{r['page']}" if r["page"] else "")
            iid = item_id(h, unit)
            items.append({"item_id": iid, "rep_sha256": r["rep_sha256"], "rep_raw_path": r["rep_raw_path"],
                          "rep_raw_store": r["rep_raw_store"], "pages_to_code": r["page"] or "all"})
            imap.append(dict(item_id=iid, judgment_key=r["judgment_key"], page=r["page"], rep_sha256=r["rep_sha256"]))
        if len({i["item_id"] for i in items}) != len(items):
            raise ValueError(f"{h}: item id collision")
        outputs[f"holdouts/{h}/ITEM_MAP.csv"] = render_csv(sorted(imap, key=lambda x: x["item_id"]))
        cols = POINTER_COLS + task.coding_fields
        for slot in CODER_SLOTS:
            order = sorted(items, key=lambda i: seeded_hash(f"{PACKET_SEED}|{h}|{slot}", i["item_id"]))
            text = render_csv([dict(i, **{f: "" for f in task.coding_fields}) for i in order], cols)
            check_blank_sheet_text(text, task_name)
            outputs[f"packets/{h}/{slot}/CODER_SHEET.csv"] = text
        outputs[f"packets/{h}/adjudicator/ADJUDICATOR_INSTRUCTIONS.json"] = render_json(dict(
            holdout=h, task=task_name,
            input="ADJUDICATION_SHEET.csv produced by `c13_coding.py adjsheet` after both coders return: only the "
                  "items whose codings differ, each shown as coding X and coding Y (which coder is X is decided per "
                  "item by a seeded hash; the key is sealed in ADJUDICATION_KEY.csv and is not given to you)",
            result_columns=["item_id"] + task.coding_fields + ["agrees_with", "reason"],
            agrees_with=["X", "Y", "NEITHER"],
            rules=["Read the source PDF yourself (verify sha256) before deciding; do not choose by majority or "
                   "by which coding looks more careful.", "Return one row per unit for every item on the sheet "
                   "and no other item.", "Use the same vocabulary as the coding guide; 'unclear' is allowed."]))
    return outputs


# ------------------------------------------------------------------------------------------------ leakage check
def _scan_values(rows, where):
    for r in rows:
        for k, v in r.items():
            for tok in FORBIDDEN_VALUE_TOKENS:
                if tok in (v or ""):
                    raise LeakError(f"{where}: column {k} carries forbidden token '{tok}'")


def check_header(header, expected, where):
    bad = [c for c in header if c not in expected]
    if bad:
        raise LeakError(f"{where}: unexpected column(s) {bad}")
    for c in header:
        if c not in POINTER_COLS and c != "coder_id" and FORBIDDEN_COL_RE.search(c):
            raise LeakError(f"{where}: forbidden column name {c}")
    if list(header) != list(expected):
        raise LeakError(f"{where}: header differs from the task layout {expected}")


def check_pointer(r, where):
    if not ITEM_ID_RE.match(r["item_id"]):
        raise LeakError(f"{where}: item_id {r['item_id']!r} is not opaque")
    if not re.fullmatch(r"[0-9a-f]{64}", r["rep_sha256"]):
        raise LeakError(f"{where}: rep_sha256 malformed")
    if not RAW_PATH_RE.match(r["rep_raw_path"]):
        raise LeakError(f"{where}: rep_raw_path {r['rep_raw_path']!r} not a pinned-store path")
    if r["rep_raw_store"] not in STORES:
        raise LeakError(f"{where}: rep_raw_store {r['rep_raw_store']!r} not an allowed store")
    if not (r["pages_to_code"] == "all" or r["pages_to_code"].isdigit()):
        raise LeakError(f"{where}: pages_to_code malformed")


def check_blank_sheet_text(text, task_name, where="sheet"):
    task = TASKS[task_name]
    rd = csv.DictReader(io.StringIO(text))
    rows = list(rd)
    check_header(rd.fieldnames, POINTER_COLS + task.coding_fields, where)
    ids = Counter(r["item_id"] for r in rows)
    if any(v > 1 for v in ids.values()):
        raise LeakError(f"{where}: duplicate item rows in a blank sheet")
    for r in rows:
        check_pointer(r, where)
        filled = [f for f in task.coding_fields if (r.get(f) or "").strip()]
        if filled:
            raise LeakError(f"{where}: item {r['item_id']} has pre-filled coding field(s) {filled}")
    _scan_values(rows, where)
    return len(rows)


def check_completed_sheet(path, task_name, coder_id, packet_path, other_coder_ids=()):
    """A returned sheet: only its own coder's labels, pointers unchanged, every packet item present."""
    task = TASKS[task_name]
    where = str(path)
    with open(path, encoding="utf-8", newline="") as f:
        rd = csv.DictReader(f)
        rows = list(rd)
    check_header(rd.fieldnames, ["coder_id"] + POINTER_COLS + task.coding_fields, where)
    packet = {r["item_id"]: r for r in read_csv(packet_path)}
    if {r["coder_id"] for r in rows} != {coder_id}:
        raise LeakError(f"{where}: coder_id values {sorted({r['coder_id'] for r in rows})} != {{{coder_id}}}")
    for r in rows:
        if r["item_id"] not in packet:
            raise LeakError(f"{where}: item {r['item_id']} not in packet")
        for c in POINTER_COLS:
            if r[c] != packet[r["item_id"]][c]:
                raise LeakError(f"{where}: pointer {c} of {r['item_id']} changed")
        for oc in other_coder_ids:
            if any(oc in (v or "") for v in r.values()):
                raise LeakError(f"{where}: mentions another coder ({oc})")
    missing = set(packet) - {r["item_id"] for r in rows}
    if missing:
        raise LeakError(f"{where}: {len(missing)} packet item(s) not returned")
    _scan_values([{k: v for k, v in r.items() if k not in ("excerpt", "notes", "legal_issue")} for r in rows], where)
    errors = [(r["item_id"], e) for r in rows for e in task.validate_row(r)]
    return rows, errors


def independence_report(rows_a, rows_b):
    """Evidence for (not proof of) independent coding: identical free-text notes / excerpts (C12 tools F04)."""
    na = Counter(norm_ws(r.get("notes")) for r in rows_a if len(norm_ws(r.get("notes"))) >= 20)
    nb = Counter(norm_ws(r.get("notes")) for r in rows_b if len(norm_ws(r.get("notes"))) >= 20)
    same = sum(min(na[k], nb[k]) for k in na if k in nb)
    return dict(identical_long_notes=same, notes_a=sum(na.values()), notes_b=sum(nb.values()),
                flag=same >= 3, note="identical notes of >= 20 characters; >= 3 is flagged for the reviewer")


# ------------------------------------------------------------------------------------------------ agreement
def group(rows):
    g = defaultdict(list)
    for r in rows:
        g[r["item_id"]].append(r)
    return g


def align(task, a, b):
    """Pairs (row_a|None, row_b|None) for one item."""
    if task.name == "holdings":
        cand = sorted(((len(content_tokens(ra["excerpt"]) & content_tokens(rb["excerpt"])), i, j)
                       for i, ra in enumerate(a) for j, rb in enumerate(b) if task.spans_match(ra, rb)),
                      key=lambda t: (-t[0], t[1], t[2]))
        ua, ub, pairs = set(), set(), []
        for _, i, j in cand:
            if i not in ua and j not in ub:
                ua.add(i); ub.add(j); pairs.append((a[i], b[j]))
        return pairs + [(a[i], None) for i in range(len(a)) if i not in ua] + \
            [(None, b[j]) for j in range(len(b)) if j not in ub]
    if task.name == "outcome" and len(a) == 1 and len(b) == 1:
        return [(a[0], b[0])]        # single-proceeding judgments align directly (C12 rule)
    pairs, used = [], set()
    for ra in a:
        k = task.unit_key(ra)
        hit = next((j for j, rb in enumerate(b) if j not in used and task.unit_key(rb) == k), None)
        if hit is None:
            pairs.append((ra, None))
        else:
            used.add(hit)
            pairs.append((ra, b[hit]))
    return pairs + [(None, b[j]) for j in range(len(b)) if j not in used]


def field_value(task, row, f):
    v = (row.get(f) or "").strip()
    return norm_ws(v).upper() if f == "target" else v


def _strict_units(pair_labels, fields):
    """Share of units (aligned or unmatched) on which every scored field agrees; unmatched units disagree."""
    n = len(pair_labels[fields[0]])
    if not n:
        return None
    ok = sum(all(pair_labels[f][i][0] == pair_labels[f][i][1] != "__MISSING__" for f in fields) for i in range(n))
    return S.rnd(ok / n)


def agreement(task_name, rows_a, rows_b):
    task = TASKS[task_name]
    errs = [("A", r["item_id"], e) for r in rows_a for e in task.validate_row(r)] + \
           [("B", r["item_id"], e) for r in rows_b for e in task.validate_row(r)]
    if errs:
        raise ValueError(f"invalid coded rows (first 5): {errs[:5]}")
    A, B = group(rows_a), group(rows_b)
    fields = task.scored_fields
    items, pair_labels = [], {f: [] for f in fields}
    n_pairs = n_unmatched = 0
    for iid in sorted(set(A) | set(B)):
        ra_ = [r for r in A.get(iid, []) if not task.is_null_row(r)]
        rb_ = [r for r in B.get(iid, []) if not task.is_null_row(r)]
        both_returned = iid in A and iid in B
        pairs = align(task, ra_, rb_)
        unmatched = sum(1 for x, y in pairs if x is None or y is None)
        same = all(x is not None and y is not None and all(field_value(task, x, f) == field_value(task, y, f)
                                                           for f in fields) for x, y in pairs)
        for x, y in pairs:
            for f in fields:
                pair_labels[f].append((field_value(task, x, f) if x else "__MISSING__",
                                       field_value(task, y, f) if y else "__MISSING__"))
        n_pairs += len(pairs) - unmatched
        n_unmatched += unmatched
        items.append(dict(item_id=iid, rows_a=len(A.get(iid, [])), rows_b=len(B.get(iid, [])),
                          aligned_units=len(pairs) - unmatched, unmatched_units=unmatched,
                          status="AGREE" if same and both_returned else "DISAGREE"))
    n = len(items)
    summary = dict(task=task_name, items=n, items_agree=sum(i["status"] == "AGREE" for i in items),
                   strict_item_agreement=S.rnd(sum(i["status"] == "AGREE" for i in items) / n) if n else None,
                   aligned_units=n_pairs, unmatched_units=n_unmatched,
                   strict_unit_agreement=_strict_units(pair_labels, fields),
                   fields={})
    for f in fields:
        pl = pair_labels[f]
        matched = [(a, b) for a, b in pl if "__MISSING__" not in (a, b)]
        summary["fields"][f] = dict(
            units_including_unmatched=len(pl), raw_agreement=S.rnd(sum(a == b for a, b in pl) / len(pl)) if pl else None,
            cohen_kappa_including_unmatched=S.rnd(S.cohen_kappa(pl)),
            cohen_kappa_matched_only=S.rnd(S.cohen_kappa(matched)),
            krippendorff_alpha_nominal=S.rnd(S.krippendorff_alpha_nominal(
                [[None if a == "__MISSING__" else a, None if b == "__MISSING__" else b] for a, b in pl])))
    if task_name == "holdings":
        na, nb = len(rows_a), len(rows_b)
        summary["span_f1"] = S.rnd(2 * n_pairs / (na + nb)) if na + nb else None
    return items, summary


# ------------------------------------------------------------------------------------------------ adjudication
def adjudication_sheet(task_name, rows_a, rows_b, items, seed="mimamsa-c13-adjudication"):
    """Competing codings for DISAGREE items, anonymised: per item, which coder is X is seeded; the key is sealed."""
    task = TASKS[task_name]
    dis = [i["item_id"] for i in items if i["status"] == "DISAGREE"]
    A, B = group(rows_a), group(rows_b)
    sheet, key = [], []
    for iid in sorted(dis, key=lambda x: seeded_hash(seed, x)):
        x_is_a = int(seeded_hash(seed + "|xy", iid)[0], 16) < 8
        X, Y = (A, B) if x_is_a else (B, A)
        key.append(dict(item_id=iid, X="A" if x_is_a else "B", Y="B" if x_is_a else "A"))
        for lab, src in (("X", X), ("Y", Y)):
            rs = src.get(iid, []) or [{}]
            for r in rs:
                row = {"item_id": iid, "coding": lab}
                row.update({c: (r.get(c, "") if r else "") for c in POINTER_COLS[1:]})
                row.update({f: r.get(f, "") for f in task.coding_fields})
                sheet.append(row)
    cols = ["item_id", "coding"] + POINTER_COLS[1:] + task.coding_fields
    return render_csv(sheet, cols), render_csv(key, ["item_id", "X", "Y"])


def check_adjudication_sheet_text(text, coder_ids):
    rows = list(csv.DictReader(io.StringIO(text)))
    for r in rows:
        if "coder_id" in r:
            raise LeakError("adjudication sheet carries coder_id")
        for cid in coder_ids:
            if any(cid in (v or "") for v in r.values()):
                raise LeakError(f"adjudication sheet names coder {cid}")
        if r["coding"] not in ("X", "Y"):
            raise LeakError("adjudication sheet coding label must be X or Y")
    return len(rows)


# ------------------------------------------------------------------------------------------------ truth
def build_truth(task_name, rows_a, rows_b, items, adjudicated, label_source="A"):
    """Agreed items: rows of the coder named by label_source (labels are identical by definition; the non-label
    fields page/para/excerpt come from that coder, documented, C12 tools F03). Disagreed items: adjudicated rows.
    Asserts the adjudicated item set equals the DISAGREE set and every adjudicated row validates (F09)."""
    task = TASKS[task_name]
    dis = {i["item_id"] for i in items if i["status"] == "DISAGREE"}
    agree = {i["item_id"] for i in items if i["status"] == "AGREE"}
    adj = group(adjudicated)
    if set(adj) != dis:
        raise ValueError(f"adjudication covers {sorted(set(adj) ^ dis)[:5]}... not exactly the DISAGREE items")
    errs = [(r["item_id"], e) for r in adjudicated for e in task.validate_row(r)]
    if errs:
        raise ValueError(f"adjudicated rows invalid: {errs[:5]}")
    src = group(rows_a if label_source == "A" else rows_b)
    out = []
    for iid in sorted(agree):
        for r in src[iid]:
            out.append(dict({f: r.get(f, "") for f in task.coding_fields}, item_id=iid, source="BOTH_CODERS_AGREE",
                            non_label_fields_from=label_source))
    for iid in sorted(dis):
        for r in adj[iid]:
            out.append(dict({f: r.get(f, "") for f in task.coding_fields}, item_id=iid, source="ADJUDICATED",
                            non_label_fields_from="adjudicator"))
    return out


# ------------------------------------------------------------------------------------------------ annotation store
def store_version(store_root, set_name, version, coder_ids, files, created_by, parent_version=None, note=""):
    """Copy files into <store_root>/<set_name>/v<NNN>/ with MANIFEST.json (sha256 per file). Never overwrites."""
    d = Path(store_root) / set_name / f"v{int(version):03d}"
    if d.exists():
        raise FileExistsError(f"{d} exists: annotation versions are immutable; use a new version")
    if parent_version is not None and not (Path(store_root) / set_name / f"v{int(parent_version):03d}").is_dir():
        raise FileNotFoundError("parent version missing")
    d.mkdir(parents=True)
    man = dict(set=set_name, version=int(version), parent_version=parent_version, coder_ids=sorted(coder_ids),
               created_by=created_by, created_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               note=note, files={})
    for f in files:
        f = Path(f)
        shutil.copyfile(f, d / f.name)
        man["files"][f.name] = sha256_file(d / f.name)
    (d / "MANIFEST.json").write_text(render_json(man), encoding="utf-8")
    return d


def verify_store(store_root):
    """Every version's files match its manifest, and no unlisted file is present. Returns list of problems."""
    problems = []
    for man in sorted(Path(store_root).glob("*/v*/MANIFEST.json")):
        m = json.loads(man.read_text(encoding="utf-8"))
        d = man.parent
        for name, h in m["files"].items():
            p = d / name
            if not p.is_file():
                problems.append(f"{d}: missing {name}")
            elif sha256_file(p) != h:
                problems.append(f"{d}: sha256 mismatch {name}")
        extra = {p.name for p in d.iterdir()} - set(m["files"]) - {"MANIFEST.json"}
        if extra:
            problems.append(f"{d}: unlisted files {sorted(extra)}")
        if not m.get("coder_ids"):
            problems.append(f"{d}: no coder ids")
    return problems


# ------------------------------------------------------------------------------------------------ CLI
def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv or argv[0] in ("--check", "packets"):
        check = "--check" in argv
        outs = build_packets()
        code = write_or_check(outs, OUT, check, "c13_coding packets")
        for k, v in outs.items():
            if k.endswith("CODER_SHEET.csv"):
                check_blank_sheet_text(v, HOLDOUT_TASK[k.split("/")[1]], k)
        guides = [PKG / "packets" / f"CODING_GUIDE_{t}.md" for t in TASKS]
        for g in guides:
            t = g.read_text(encoding="utf-8")
            for tok in FORBIDDEN_VALUE_TOKENS:
                if tok in t:
                    print(f"LEAK: {g.name} mentions {tok}")
                    return 1
        return code
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("leakcheck"); p.add_argument("sheet"); p.add_argument("--task", required=True)
    p.add_argument("--completed", action="store_true"); p.add_argument("--coder"); p.add_argument("--packet")
    p.add_argument("--other-coder", action="append", default=[])
    p = sub.add_parser("agree"); p.add_argument("--task", required=True); p.add_argument("--a", required=True)
    p.add_argument("--b", required=True); p.add_argument("--out", required=True)
    p = sub.add_parser("adjsheet"); p.add_argument("--task", required=True); p.add_argument("--a", required=True)
    p.add_argument("--b", required=True); p.add_argument("--out", required=True); p.add_argument("--key-out", required=True)
    p = sub.add_parser("truth"); p.add_argument("--task", required=True); p.add_argument("--a", required=True)
    p.add_argument("--b", required=True); p.add_argument("--adjudicated", required=True); p.add_argument("--out", required=True)
    p = sub.add_parser("verify"); p.add_argument("store")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "leakcheck":
            if a.completed:
                _, errors = check_completed_sheet(a.sheet, a.task, a.coder, a.packet, a.other_coder)
                print(f"leakcheck OK ({len(errors)} vocabulary/blank error(s))")
                for e in errors[:20]:
                    print("  ", e)
                return 0 if not errors else 2
            n = check_blank_sheet_text(Path(a.sheet).read_text(encoding="utf-8"), a.task, a.sheet)
            print(f"leakcheck OK: {n} blank item rows, pointers and coding fields only")
            return 0
        if a.cmd in ("agree", "adjsheet", "truth"):
            ra, rb = read_csv(a.a), read_csv(a.b)
            items, summ = agreement(a.task, ra, rb)
            if a.cmd == "agree":
                Path(a.out).write_text(render_json(dict(summary=summ, items=items)), encoding="utf-8")
                print(render_json(summ))
            elif a.cmd == "adjsheet":
                sheet, key = adjudication_sheet(a.task, ra, rb, items)
                check_adjudication_sheet_text(sheet, {r.get("coder_id", "") for r in ra + rb} - {""})
                Path(a.out).write_text(sheet, encoding="utf-8"); Path(a.key_out).write_text(key, encoding="utf-8")
            else:
                truth = build_truth(a.task, ra, rb, items, read_csv(a.adjudicated))
                Path(a.out).write_text(render_csv(truth), encoding="utf-8")
            return 0
        if a.cmd == "verify":
            probs = verify_store(a.store)
            print("store OK" if not probs else "\n".join(probs))
            return 0 if not probs else 1
    except LeakError as e:
        print(f"LEAK CHECK FAILED: {e}")
        return 1
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
