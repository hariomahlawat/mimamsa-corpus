"""F10: the keymap must not use any browser- or OS-reserved combination."""
from __future__ import annotations

import json
from pathlib import Path

D = Path(__file__).resolve().parents[1]
KEYMAP = json.loads((D / "keymap.json").read_text(encoding="utf-8"))["bindings"]
RES = json.loads((D / "browser_reserved_keys.json").read_text(encoding="utf-8"))
RESERVED = {k.upper() for k in RES["edge_and_chrome"] + RES["windows_system"] + RES["editing_conventions_kept_native"]}
ORDER = ["CTRL", "ALT", "SHIFT"]


def norm(combo: str) -> str:
    parts = combo.split("+")
    mods = sorted((p.upper() for p in parts[:-1]), key=ORDER.index)
    return "+".join(mods + [parts[-1].upper()])


def chords():
    for b in KEYMAP:
        for step in b["keys"].split(" then "):
            yield b, norm(step)


def test_reserved_list_is_normalised():
    for k in RESERVED:
        assert norm(k) == k, k


def test_no_binding_uses_a_reserved_combination():
    hits = [(b["action"], c) for b, c in chords() if c in RESERVED]
    assert hits == []


def test_known_previous_conflicts_are_gone():
    used = {c for _, c in chords()}
    for old in ["CTRL+SHIFT+P", "CTRL+SHIFT+C", "CTRL+SHIFT+O", "CTRL+SHIFT+N", "CTRL+W", "CTRL+TAB", "CTRL+K",
                "CTRL+1", "ALT+ARROWLEFT", "ALT+ARROWRIGHT", "F6", "F3", "CTRL+G", "CTRL+B"]:
        assert old not in used, old


def test_no_duplicate_binding_within_a_scope():
    seen = {}
    for b in KEYMAP:
        key = (b["scope"], norm(b["keys"].split(" then ")[0]) if " then " not in b["keys"] else b["keys"].upper())
        assert key not in seen, (b, seen.get(key))
        seen[key] = b


def test_single_key_shortcuts_never_fire_in_text_fields():
    for b in KEYMAP:
        if b["single_key"] and b["scope"] in ("search_field",):
            raise AssertionError(b)
