#!/usr/bin/env python3
"""C13-A0: run every --check (exclusions, frame, sampler, pre-exposed subsets, packets, scoring self-test, coverage
simulation (about 1 minute), size restatement) and verify SHA256SUMS.
Stage 1 (text features) is included when the corpus commit and the C12 additions copy are available.
  python -I -B c13_check_all.py            # check only, writes nothing
  python -I -B c13_check_all.py --sums     # (re)write SHA256SUMS after a deliberate rebuild
"""
import io
import sys
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import c13_coding  # noqa: E402
import c13_exclusions  # noqa: E402
import c13_frame  # noqa: E402
import c13_sampler  # noqa: E402
import c13_score  # noqa: E402
import c13_ci_sim  # noqa: E402
import c13_power  # noqa: E402
import c13_sensitivity  # noqa: E402
from c13_common import OUT, PKG, additions_cache_dir, corpus_git_dir, sha256_file, write_or_check  # noqa: E402

SUMS_GLOBS = ["README.md", "PROTOCOL_C13.md", "tools/*.py", "packets/*.md", "outputs/**/*.csv", "outputs/**/*.json",
              "outputs/**/*.txt", "reviews/**/*"]


def sums_text():
    files = sorted({p for g in SUMS_GLOBS for p in PKG.glob(g) if p.is_file()})
    return "".join(f"{sha256_file(p)}  {p.relative_to(PKG).as_posix()}\n" for p in files)


def main():
    if "--sums" in sys.argv[1:]:
        (PKG / "SHA256SUMS").write_text(sums_text(), encoding="utf-8")
        print("SHA256SUMS written")
        return 0
    codes = []
    if corpus_git_dir() and additions_cache_dir().is_dir():
        import c13_features
        codes.append(write_or_check(c13_features.build(), OUT, True, "c13_features"))
    else:
        print("c13_features: SKIPPED (corpus commit or C12 additions copy not available)")
    codes.append(write_or_check(c13_exclusions.build(), OUT, True, "c13_exclusions"))
    codes.append(write_or_check(c13_frame.build(), OUT, True, "c13_frame"))
    codes.append(write_or_check(c13_sampler.build(), OUT, True, "c13_sampler"))
    codes.append(write_or_check(c13_sensitivity.build(), OUT, True, "c13_sensitivity"))
    codes.append(c13_coding.main(["--check"]))
    codes.append(write_or_check(c13_ci_sim.build(), OUT, True, "c13_ci_sim"))
    codes.append(write_or_check(c13_power.build(), OUT, True, "c13_power"))
    codes.append(c13_score.main(["--check"]))
    ok = (PKG / "SHA256SUMS").is_file() and (PKG / "SHA256SUMS").read_text(encoding="utf-8") == sums_text()
    print("SHA256SUMS: OK" if ok else "SHA256SUMS: MISMATCH")
    codes.append(0 if ok else 1)
    print("ALL CHECKS OK" if not any(codes) else "CHECK FAILED")
    return 1 if any(codes) else 0


if __name__ == "__main__":
    sys.exit(main())
