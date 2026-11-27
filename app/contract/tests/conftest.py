"""Test fixtures. The restricted-material register is always read from config/restricted_material.json.

Resolution order (no list is ever hard-coded here):
1. $MIMAMSA_RESTRICTED_MATERIAL_CONFIG, if set;
2. <repository root>/config/restricted_material.json (present once the governance branch is integrated);
3. pre-integration only: the same file read from the governance branch with `git show claude/c13-gov:config/...`.
If none is available the tests FAIL (they never skip): the exclusion rule cannot be shown to work without the register.
"""
from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

CONTRACT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CONTRACT_DIR))

from mimamsa_contract.restricted import ENV_OVERRIDE, load_register, repository_root  # noqa: E402

EXAMPLES = CONTRACT_DIR / "examples"
GOV_BRANCH_REFS = ("claude/c13-gov:config/restricted_material.json", "origin/claude/c13-gov:config/restricted_material.json")


def _resolve_register_path(tmp_dir: Path) -> Path:
    env = os.environ.get(ENV_OVERRIDE)
    if env:
        return Path(env)
    repo_copy = repository_root() / "config" / "restricted_material.json"
    if repo_copy.is_file():
        return repo_copy
    data = None
    for ref in GOV_BRANCH_REFS:
        try:
            data = subprocess.run(["git", "-C", str(repository_root()), "show", ref],
                                  check=True, capture_output=True, timeout=30).stdout
            break
        except (OSError, subprocess.SubprocessError):
            continue
    if data is None:
        pytest.fail("config/restricted_material.json not found in the repository or on the governance branch; "
                    "the restricted-material tests cannot run without the register (they fail rather than skip)")
    p = tmp_dir / "restricted_material.json"
    p.write_bytes(data)
    return p


@pytest.fixture(scope="session")
def register_path(tmp_path_factory) -> Path:
    return _resolve_register_path(tmp_path_factory.mktemp("register"))


@pytest.fixture(scope="session")
def register(register_path):
    return load_register(register_path)


@pytest.fixture(autouse=True)
def _pin_register_env(register_path, monkeypatch):
    # Make every default load_register() call in the code under test use the resolved register.
    monkeypatch.setenv(ENV_OVERRIDE, str(register_path))


def load_example(name: str) -> dict:
    return json.loads((EXAMPLES / f"{name}.example.json").read_text(encoding="utf-8"))


@pytest.fixture
def example():
    return lambda name: copy.deepcopy(load_example(name))
