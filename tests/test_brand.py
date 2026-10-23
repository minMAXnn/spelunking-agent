"""The brand set: every PNG exists at its venue size, and the dark set is really drawn on the site's dark paper."""
import os, sys, struct, zlib, pytest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(ROOT, "scripts", "brand"))
import build_brand

EXPECTED = {"logo-512": (512, 512), "logo-240": (240, 240), "social-1280x640": (1280, 640), "og-1200x630": (1200, 630),
            "gallery-1270x760": (1270, 760), "banner-1200x300": (1200, 300), "social-1280x640-light": (1280, 640), "og-1200x630-light": (1200, 630)}


def png_size_and_first_pixel(path):
    d = open(path, "rb").read(); assert d[:8] == b"\x89PNG\r\n\x1a\n"
    w, h, depth, ctype = struct.unpack(">IIBB", d[16:26]); bpp = {2: 3, 6: 4}[ctype]
    idat = b""; i = 8
    while i < len(d):
        n, = struct.unpack(">I", d[i:i + 4]); t = d[i + 4:i + 8]
        if t == b"IDAT": idat += d[i + 8:i + 8 + n]
        i += 12 + n
    raw = zlib.decompress(idat); px = raw[1:1 + bpp]   # first scanline's filter byte, then the first pixel (no neighbours → raw)
    return (w, h), "#%02x%02x%02x" % tuple(px[:3])


def test_sizes_declared():
    assert build_brand.SIZES == EXPECTED


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_png_exists_at_size_and_on_the_right_paper(name):
    p = os.path.join(ROOT, "docs", "brand", name + ".png"); assert os.path.exists(p), "run scripts/brand/build_brand.py"
    size, px = png_size_and_first_pixel(p)
    assert size == EXPECTED[name]
    assert px == ("#ffffff" if name.endswith("-light") else build_brand.DARK["paper"])
