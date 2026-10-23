#!/usr/bin/env python3
"""Render the brand set (PNG) from HTML templates that use the site's own colours, headless in Chromium (Playwright).

  python3 scripts/brand/build_brand.py [--out docs/brand] [--also <dir>]
Dark paper and text from themes/spelunking/style.css; ring / dot / gold from the site's logo.svg and og.png.
"""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import templates as T

DARK = {"paper": "#0e1116", "paper2": "#0b0d12", "text": "#e6e9ee", "text2": "#a7b0bd", "line": "#2b323d", "ring": "#7dd3c0", "dot": "#bfe9ff", "gold": "#f2c14e", "ember": "#f0913f"}
LIGHT = {"paper": "#ffffff", "paper2": "#0b0d12", "text": "#171b21", "text2": "#4a525e", "line": "#d8dce3", "ring": "#2a8f7a", "dot": "#3b7fb6", "gold": "#b8860b", "ember": "#b4530a"}
SIZES = {"logo-512": (512, 512), "logo-240": (240, 240), "social-1280x640": (1280, 640), "og-1200x630": (1200, 630),
         "gallery-1270x760": (1270, 760), "banner-1200x300": (1200, 300), "social-1280x640-light": (1280, 640), "og-1200x630-light": (1200, 630)}


def html_for(name):
    w, h = SIZES[name]; c = LIGHT if name.endswith("-light") else DARK
    if name.startswith("logo"): return T.logo(w, c)
    if name.startswith("gallery"): return T.gallery(w, h, c)
    if name.startswith("banner"): return T.banner(w, h, c)
    return T.social(w, h, c)


def build(out, also=None):
    from playwright.sync_api import sync_playwright
    os.makedirs(out, exist_ok=True); written = []
    with sync_playwright() as pw:
        b = pw.chromium.launch(args=["--use-gl=swiftshader"])
        for name, (w, h) in SIZES.items():
            pg = b.new_page(viewport={"width": w, "height": h}, device_scale_factor=1); pg.set_content(html_for(name)); pg.wait_for_timeout(150)
            p = os.path.join(out, name + ".png"); pg.screenshot(path=p, clip={"x": 0, "y": 0, "width": w, "height": h}); pg.close(); written.append(p)
        b.close()
    with open(os.path.join(out, "mark.svg"), "w") as f: f.write(T.MARK.format(s=64, paper2=DARK["paper2"], ring=DARK["ring"], gold=DARK["gold"]))
    if also:
        import shutil; os.makedirs(also, exist_ok=True)
        for p in written + [os.path.join(out, "mark.svg")]: shutil.copy2(p, also)
    return written


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "docs", "brand")); ap.add_argument("--also")
    a = ap.parse_args()
    for p in build(a.out, a.also): print("wrote", p)
