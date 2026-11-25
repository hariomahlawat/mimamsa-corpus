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
        if not p["fg"].startswith(("border.", "focus.", "edge.", "pdf.highlight.")):
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


# ---- review fixes (F11, F17)
TEXT_FG = [k for k in TOKENS["color"]["light"] if k.startswith("fg.") and k != "fg.on-accent"] + ["accent.interactive"]
ALL_BG = [k for k in TOKENS["color"]["light"] if k.startswith("bg.")]


@pytest.mark.parametrize("theme", THEMES)
def test_every_text_token_on_every_background(theme):
    """F17: undeclared pairs are also tested (a text token may appear on any background)."""
    pal = TOKENS["color"][theme]
    bad = [(f, b, round(contrast(pal[f], pal[b]), 2)) for f in TEXT_FG for b in ALL_BG if contrast(pal[f], pal[b]) < 4.5]
    assert bad == []


def test_pdf_highlight_tokens_theme_independent():
    for k in ("pdf.page", "pdf.text", "pdf.highlight.search", "pdf.highlight.ocr", "pdf.highlight.ocr-outline"):
        assert TOKENS["color"]["light"][k] == TOKENS["color"]["dark"][k]


def test_search_and_ocr_highlights_differ_by_more_than_hue():
    """F17: OCR-box hits must be distinguishable without colour perception: an outline token with >=3:1 exists."""
    pal = TOKENS["color"]["light"]
    assert contrast(pal["pdf.highlight.ocr-outline"], pal["pdf.page"]) >= 3.0


def _layout(css_w: int, coarse_pointer: bool) -> str:
    bp = TOKENS["layout"]["breakpoints"]
    if coarse_pointer:
        return "tablet"
    if css_w >= bp["wide"]:
        return "wide"
    if css_w >= bp["standard"]:
        return "standard"
    if css_w >= bp["compact"]:
        return "compact"
    return "narrow"


def _panes(css_w: int) -> dict:
    pm = TOKENS["layout"]["pane_min_px"]
    divider = 6
    # context collapses to a drawer first, then results; the rail is icon-only (48 px) below 'standard'
    rail = 48 if css_w < TOKENS["layout"]["breakpoints"]["standard"] else pm["rail"]
    avail = css_w - rail
    panes = {"results": True, "context": True}
    if avail < pm["results"] + pm["document"] + pm["context"] + 2 * divider:
        panes["context"] = False
    if avail < pm["results"] + pm["document"] + divider:
        panes["results"] = False
    doc = avail - (pm["results"] + divider if panes["results"] else 0) - (pm["context"] + divider if panes["context"] else 0)
    return {"document": doc, **panes}


@pytest.mark.parametrize("phys", TOKENS["layout"]["scaling_matrix"]["physical"])
@pytest.mark.parametrize("scale", TOKENS["layout"]["scaling_matrix"]["scales"])
def test_windows_display_scaling_never_selects_touch_layout(phys, scale):
    """F11: 1366x768 at 125% is ~1093 CSS px and 1920x1080 at 175% ~1097 CSS px: still a desktop layout with a usable
    document pane, because touch layout is chosen by pointer type, not width."""
    w = int(phys.split("x")[0])
    css = round(w / scale)
    assert _layout(css, coarse_pointer=False) != "tablet"
    assert _panes(css)["document"] >= TOKENS["layout"]["pane_min_px"]["document"]


def test_effective_widths_for_common_settings():
    assert round(1920 / 1.25) == 1536 and _layout(1536, False) == "compact"
    assert round(1366 / 1.25) == 1093 and _layout(1093, False) == "narrow"
    assert _layout(1093, True) == "tablet"


def test_vertical_budget_at_1366x768_125pct_leaves_reading_space():
    """F18: realistic budget with browser UI and taskbar, condensed banner."""
    c = TOKENS["layout"]["chrome_px"]
    css_h = round(768 / 1.25)
    content = css_h - c["browser_ui_estimate"] / 1.25 - c["taskbar_estimate"] / 1.25 - c["banner_condensed"] - c["topbar"] - c["footer"]
    assert content >= 380, content
