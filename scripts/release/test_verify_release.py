"""Offline tests for verify_release.py: a synthetic release tree, manifest and torrent."""
import hashlib, os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import glyph_publish as gp, verify_release as vr


def _release(tmp):
    root = os.path.join(tmp, "glyphs-2026-10"); os.makedirs(os.path.join(root, "abstract")); os.makedirs(os.path.join(root, "_about"))
    rows = []
    for name, body in (("abstract/a.png", b"A" * 5000), ("abstract/b.png", b"B" * 70)):
        open(os.path.join(root, name), "wb").write(body)
        rows.append("%s\t%d\t%s\tbafy%s" % (name, len(body), hashlib.sha256(body).hexdigest(), name[-5]))
    open(os.path.join(root, "_about", "README.md"), "w").write("hi")
    man = "path\tsize\tsha256\tcid\n" + "\n".join(sorted(rows)) + "\n"
    open(os.path.join(root, "_about", "MANIFEST.tsv"), "w", newline="\n").write(man)
    open(os.path.join(root, "_about", "MANIFEST.tsv.sha256"), "w").write(hashlib.sha256(man.encode()).hexdigest() + "  MANIFEST.tsv\n")
    files = sorted((os.path.relpath(os.path.join(d, f), root).replace(os.sep, "/"), os.path.join(d, f)) for d, _, fs in os.walk(root) for f in fs)
    data, ih = gp.torrent_v1("glyphs-2026-10", files, root, piece_len=1 << 14)
    return root, data, ih


def test_clean_release_verifies():
    tmp = tempfile.mkdtemp(); root, data, ih = _release(tmp)
    r = vr.verify(root, data, expect_infohash=ih)
    assert r["ok"], r
    assert r["manifest_rows"] == 2 and r["bad"] == [] and r["missing"] == [] and r["infohash"] == ih and r["pieces_ok"]


def test_corrupt_file_and_wrong_infohash_are_caught():
    tmp = tempfile.mkdtemp(); root, data, ih = _release(tmp)
    open(os.path.join(root, "abstract", "b.png"), "wb").write(b"X" * 70)        # same size, different bytes
    r = vr.verify(root, data, expect_infohash="0" * 40)
    assert not r["ok"] and r["bad"] == ["abstract/b.png"] and not r["infohash_match"] and not r["pieces_ok"]


def test_missing_file_and_bad_manifest_digest_are_caught():
    tmp = tempfile.mkdtemp(); root, data, ih = _release(tmp)
    os.remove(os.path.join(root, "abstract", "a.png"))
    open(os.path.join(root, "_about", "MANIFEST.tsv.sha256"), "w").write("0" * 64 + "  MANIFEST.tsv\n")
    r = vr.verify(root, data)
    assert not r["ok"] and r["missing"] == ["abstract/a.png"] and not r["manifest_digest_ok"]
