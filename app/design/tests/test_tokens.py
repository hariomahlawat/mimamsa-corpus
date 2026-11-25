"""Design token checks: WCAG 2.2 AA contrast for every declared pair in both themes, token integrity, offline fonts."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

TOKENS = json.loads((Path(__file__).resolve().parents[1] / "tokens" / "design-tokens.json").read_text(encoding="utf-8"))
THEMES = ("light", "dark")
HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")


def _lum(h: str) -> float:
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4  # noqa: E731
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def contrast(a: str, b: str) -> float:
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def test_contrast_formula_reference_values():
    assert round(contrast("#000000", "#FFFFFF"), 1) == 21.0
    assert round(contrast("#767676", "#FFFFFF"), 2) == 4.54


def test_themes_define_identical_token_sets():
    assert set(TOKENS["color"]["light"]) == set(TOKENS["color"]["dark"])


@pytest.mark.parametrize("theme", THEMES)
def test_all_colours_are_hex(theme):
    for k, v in TOKENS["color"][theme].items():
        assert HEX.match(v), (theme, k, v)


@pytest.mark.parametrize("theme", THEMES)
@pytest.mark.parametrize("pair", TOKENS["contrast_pairs"], ids=lambda p: f"{p['fg']}|{p['bg']}")
def test_wcag_aa_contrast(theme, pair):
    pal = TOKENS["color"][theme]
    ratio = contrast(pal[pair["fg"]], pal[pair["bg"]])
    assert ratio >= pair["min"], f"{theme}: {pair['fg']} on {pair['bg']} = {ratio:.2f} < {pair['min']} ({pair['use']})"


def test_text_pairs_use_aa_text_threshold():
    for p in TOKENS["contrast_pairs"]:
        if not p["fg"].startswith(("border.", "focus.", "edge.")):
            assert p["min"] >= 4.5, p


def test_every_status_chip_has_a_checked_pair():
    declared = {(p["fg"], p["bg"]) for p in TOKENS["contrast_pairs"]}
    for name in ("candidate", "checked", "warning", "error", "gated"):
        assert (f"status.{name}.fg", f"status.{name}.bg") in declared


def test_no_network_fonts_or_urls():
    blob = json.dumps(TOKENS)
    assert "http://" not in blob and "https://" not in blob and "url(" not in blob


def test_spacing_scale_is_monotonic_and_even():
    vals = [TOKENS["space"][k] for k in sorted(TOKENS["space"], key=int)]
    assert vals == sorted(vals) and all(v % 2 == 0 for v in vals)


def test_restrained_rounding_and_motion():
    assert max(TOKENS["radius"].values()) <= 4
    assert TOKENS["motion"]["decorative"] == "none" and TOKENS["motion"]["respect_reduced_motion"] is True


def test_minimum_target_width_fits_three_panes():
    pm = TOKENS["layout"]["pane_min_px"]
    # at 1366 px: results + document + context minimums plus two 6 px dividers must fit
    assert pm["results"] + pm["document"] + pm["context"] + 12 <= 1366
