"""B02 build tests. Outputs go under pytest's basetemp; run with --basetemp outside the repository, e.g.
    python -m pytest app/kbuild/tests --basetemp E:/Mimamsa-Data/c16b02/pytest
The .NET S6 helper is built once per session (local NuGet cache) unless MIMAMSA_KBUILD_ACCEL names a built
KBuildAccel.dll. Without the .NET SDK the build tests are skipped (the spec, rule and unit tests still run).
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

KBUILD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KBUILD))

import mimamsa_kbuild  # noqa: E402,F401  (sets the contract and importer paths)
from mimamsa_kbuild.cli import build_accel, run_build  # noqa: E402
from mimamsa_kbuild.fixture_mirror import prepare  # noqa: E402

SPEC = KBUILD / "specs" / "cp1-fixture.spec.json"
DEV_SEED = "4d696d616d73612d6b6275696c642d746573742d6f6e6c792d6465762d6b6579"   # fixed DEVELOPMENT test seed (not a secret)


def load_spec() -> dict:
    return json.loads(SPEC.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def accel_tool(tmp_path_factory):
    import os
    env = os.environ.get("MIMAMSA_KBUILD_ACCEL")
    if env and Path(env).is_file():
        return Path(env)
    if shutil.which("dotnet") is None:
        pytest.skip(".NET SDK not available: the S6 accelerator builder cannot run")
    return build_accel(tmp_path_factory.mktemp("dotnet"))


@pytest.fixture(scope="session")
def dev_key(tmp_path_factory):
    p = tmp_path_factory.mktemp("keys") / "dev.key"
    p.write_text(DEV_SEED + "\n", encoding="ascii")
    return p


@pytest.fixture(scope="session")
def mirror(tmp_path_factory):
    m = tmp_path_factory.mktemp("mirror")
    prepare(m)
    return m


@pytest.fixture(scope="session")
def built(tmp_path_factory, mirror, dev_key, accel_tool):
    """One complete CP-1 build (session-wide); tests that mutate copy it first."""
    out = tmp_path_factory.mktemp("build-a")
    res = run_build(load_spec(), out, mirror=mirror, dev_key=dev_key, accel=accel_tool, apply_budget=False)
    return {"out": out, "res": res, "root": out / load_spec()["output_dir"]}


def copy_build(src_out: Path, dst_out: Path) -> Path:
    shutil.copytree(src_out, dst_out)
    return dst_out
