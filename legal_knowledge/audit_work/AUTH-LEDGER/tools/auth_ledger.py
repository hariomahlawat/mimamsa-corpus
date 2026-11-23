"""AUTH-LEDGER command line (offline).
  python auth_ledger.py verify            pins + hash chain + HEAD + every version's entries + every committed effective/vNNNN
                                          rebuilt byte-for-byte; v0000 must equal the frozen Cycle 5 registers
  python auth_ledger.py build --as-of N --out DIR    write the effective outputs of version N to DIR (no repository change)
  python auth_ledger.py genesis           create ledger/manifest.jsonl line 0, ledger/HEAD and effective/v0000 (only if absent)"""
import argparse, json, sys, os
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # not resolved: keeps a symlinked path detectable (C8)
from common import AW, PKG, LedgerError, sha256_file, sha256_text  # noqa: E402
import ledger as L  # noqa: E402
import reader  # noqa: E402

GENESIS_DATE = "2026-11-23"


def output_manifest(texts):
    return json.dumps({k: sha256_text(v) for k, v in sorted(texts.items())}, indent=1, sort_keys=True) + "\n"


def write_outputs(texts, d):
    d.mkdir(parents=True, exist_ok=True)
    for k, v in texts.items():
        (d / k).write_text(v, encoding="utf-8")
    (d / "OUTPUT_MANIFEST.json").write_text(output_manifest(texts), encoding="utf-8")


def genesis(root=PKG):
    root = Path(root)
    if (root / "ledger/manifest.jsonl").exists():
        raise LedgerError("ledger already initialised; genesis is written once")
    line = {"version": 0, "prev": "GENESIS", "date": GENESIS_DATE, "rule_version": 1,
            "frozen_inputs_sha256": sha256_file(root / "frozen_inputs.json"), "file": None, "file_sha256": None,
            "decisions": {}, "reviews": {}, "effective_sha256": "",
            "note": "zero-entry baseline: the frozen Cycle 4 register (13 rows) and the frozen Cycle 5 snapshot; no authentication entry"}
    (root / "ledger").mkdir(exist_ok=True)
    (root / "ledger/manifest.jsonl").write_text(L.canonical_line(line) + "\n", encoding="utf-8")
    (root / "ledger/HEAD").write_text(f"0 {sha256_text(L.canonical_line(line))}\n", encoding="utf-8")
    texts, _ = reader.effective_state(root, 0)
    line["effective_sha256"] = sha256_text(output_manifest(texts))
    s = L.canonical_line(line)
    (root / "ledger/manifest.jsonl").write_text(s + "\n", encoding="utf-8")
    (root / "ledger/HEAD").write_text(f"0 {sha256_text(s)}\n", encoding="utf-8")
    write_outputs(texts, root / "effective/v0000")


def verify(root=PKG):
    root = Path(root)
    L.check_committed_layout(root)  # before any file is read (C8, Fable C-02)
    lines = L.read_manifest(root)
    report = []
    for line in lines:
        v = line["version"]
        texts, _ = reader.effective_state(root, v)
        d = root / f"effective/v{v:04d}"
        if sha256_text(output_manifest(texts)) != line["effective_sha256"]:
            raise LedgerError(f"version {v}: rebuilt outputs do not match effective_sha256 in the manifest")
        for k, t in texts.items():
            if not (d / k).is_file() or (d / k).read_text(encoding="utf-8") != t:
                raise LedgerError(f"version {v}: committed effective/v{v:04d}/{k} differs from the rebuild")
        if (d / "OUTPUT_MANIFEST.json").read_text(encoding="utf-8") != output_manifest(texts):
            raise LedgerError(f"version {v}: OUTPUT_MANIFEST.json differs")
        if v == 0:
            for k in reader.FROZEN_EQUAL:
                if texts[k] != (AW / "SOURCE-LIBRARY-C5/registers" / k).read_text(encoding="utf-8"):
                    raise LedgerError(f"v0000 {k} is not byte-identical to the frozen Cycle 5 register")
        report.append(f"v{v:04d} ok")
    extra = L.unexpected_files(root, lines)
    if extra:
        raise LedgerError(f"files in ledger/ or decisions/ not accounted for by the manifest: {extra}")
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["verify", "build", "genesis"])
    ap.add_argument("--as-of", type=int)
    ap.add_argument("--out")
    a = ap.parse_args()
    # The package as INVOKED (argv[0], not symlink-resolved): Python resolves the script directory on sys.path, so the
    # module paths alone cannot see a symlinked package (Fable review of be861ec0, F-01). Residual: if the caller's
    # working directory is already inside a symlink target and the script is named relatively, the OS reports the
    # resolved path and the link cannot be seen; run the tool by its repository path from outside the package.
    invoked = Path(os.path.abspath(sys.argv[0]))
    if invoked.name == "auth_ledger.py" and invoked.parent.name == "tools":
        L.COMMITTED_PACKAGE = invoked.parents[1]
    root = L.COMMITTED_PACKAGE
    try:
        if a.cmd == "genesis":
            genesis()
            print("genesis written")
        elif a.cmd == "build":
            if not a.out:
                raise LedgerError("--out is required")
            texts, lines = reader.effective_state(root, a.as_of)
            pinned = lines[-1]["effective_sha256"]
            if pinned and sha256_text(output_manifest(texts)) != pinned:
                raise LedgerError(f"rebuilt outputs of version {lines[-1]['version']} do not match the manifest pin")
            write_outputs(texts, Path(a.out))
            print(f"built as of version {lines[-1]['version']} -> {a.out}")
        else:
            for r in verify(root):
                print(r)
            print(f"HEAD {L.head_value(root)}; frozen pins ok; ledger verified")
    except (LedgerError, reader.R.RuleError, KeyError, TypeError, ValueError, SystemExit) as e:  # fail closed, uniformly (F-13)
        print(f"LEDGER ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
