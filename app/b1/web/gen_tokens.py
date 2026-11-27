"""Generate wwwroot/assets/tokens.css from app/design/tokens/design-tokens.json (the single source of design values).
`python web/gen_tokens.py --check` fails when the committed CSS is stale (run in CI and by the B1 tests)."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOKENS = HERE.parents[1] / "design" / "tokens" / "design-tokens.json"
OUT = HERE.parent / "src" / "Mimamsa.Web" / "wwwroot" / "assets" / "tokens.css"


def var(name: str) -> str:
    return "--" + name.replace(".", "-")


def render() -> str:
    t = json.loads(TOKENS.read_text(encoding="utf-8"))
    lines = [f"/* GENERATED from app/design/tokens/design-tokens.json v{t['version']} by app/b1/web/gen_tokens.py. Do not edit. */"]

    def block(selector, colors, extra=()):
        lines.append(f"{selector} {{")
        for k, v in colors.items():
            lines.append(f"  {var(k)}: {v};")
        lines.extend(extra)
        lines.append("}")

    ty = t["typography"]
    common = [f"  --font-ui: {ty['font.ui']};", f"  --font-reading: {ty['font.reading']};", f"  --font-mono: {ty['font.mono']};",
              f"  --font-devanagari: {ty['font.devanagari']};"]
    common += [f"  --size-{k}: {v}px;" for k, v in ty["size"].items()]
    common += [f"  --lh-{k}: {v};" for k, v in ty["line_height"].items()]
    common += [f"  --space-{k}: {v}px;" for k, v in t["space"].items()]
    common += [f"  --radius-{k}: {v}px;" for k, v in t["radius"].items()]
    common += [f"  --bw-{k}: {v}px;" for k, v in t["border_width"].items()]
    common += [f"  --elevation-overlay: {t['elevation']['overlay']};", f"  --motion-state: {t['motion']['state_change_ms']}ms;"]
    lay = t["layout"]
    common += [f"  --pane-min-{k}: {v}px;" for k, v in lay["pane_min_px"].items()]
    common += [f"  --row-{k}: {v}px;" for k, v in lay["row_height_px"].items()]
    common += [f"  --banner-h: {lay['chrome_px']['banner']}px;", f"  --banner-h-condensed: {lay['chrome_px']['banner_condensed']}px;",
               f"  --topbar-h: {lay['chrome_px']['topbar']}px;", f"  --footer-h: {lay['chrome_px']['footer']}px;"]
    common += [f"  --z-{k}: {v};" for k, v in t["z"].items()]
    block(":root", t["color"]["light"], common)
    lines.append("@media (prefers-color-scheme: dark) {")
    block("  :root:not([data-theme=\"light\"])", t["color"]["dark"])
    lines.append("}")
    block(":root[data-theme=\"dark\"]", t["color"]["dark"])
    lines.append("@media (prefers-reduced-motion: reduce) { :root { --motion-state: 0ms; } }")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    css = render()
    if "--check" in sys.argv:
        if not OUT.exists() or OUT.read_text(encoding="utf-8") != css:
            print("tokens.css is stale: run python app/b1/web/gen_tokens.py", file=sys.stderr)
            sys.exit(1)
        print("tokens.css matches design-tokens.json")
    else:
        OUT.write_text(css, encoding="utf-8")
        print(f"wrote {OUT}")
