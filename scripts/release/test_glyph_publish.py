"""Offline tests for glyph_publish.py: synthetic PNGs in a temp dir, no network, no real glyphs."""
import json, os, struct, sys, tempfile, zlib, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import glyph_publish as gp


def _chunk(ctype, data):
    return struct.pack(">I", len(data)) + ctype + data + struct.pack(">I", zlib.crc32(ctype + data) & 0xFFFFFFFF)


def _png(text=None, itxt=None, ztxt=None):
    ihdr = _chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
    body = gp.PNG_SIG + ihdr
    if text:
        for k, v in text.items():
            body += _chunk(b"tEXt", k.encode() + b"\x00" + v.encode("latin-1"))
    if itxt:
        for k, v in itxt.items():
            body += _chunk(b"iTXt", k.encode() + b"\x00\x00\x00" + b"\x00" + b"\x00" + v.encode("utf-8"))
    if ztxt:
        for k, v in ztxt.items():
            body += _chunk(b"zTXt", k.encode() + b"\x00\x00" + zlib.compress(v.encode("latin-1")))
    body += _chunk(b"IDAT", zlib.compress(b"\x00\x00\x00\x00")) + _chunk(b"IEND", b"")
    return body


def _tree(tmp):
    os.makedirs(os.path.join(tmp, "glyphs", "abstract"), exist_ok=True); os.makedirs(os.path.join(tmp, "glyphs", "drafts"), exist_ok=True)
    open(os.path.join(tmp, "glyphs", "abstract", "000001_entity.png"), "wb").write(_png(text={"Title": "entity", "Description": "an abstract entity"}))
    open(os.path.join(tmp, "glyphs", "abstract", "000002_exist.png"), "wb").write(_png(text={"Title": "exist"}, itxt={"Description": "exist — iTXt ünïcode"}))
    open(os.path.join(tmp, "glyphs", "abstract", "000003_cond.png"), "wb").write(_png(itxt={"Sigil": "{\"schema\":\"x\"}"}, ztxt={"Comment": "conditionality"}))
    open(os.path.join(tmp, "glyphs", "abstract", "bare.png"), "wb").write(_png())                       # no metadata → excluded
    open(os.path.join(tmp, "glyphs", "abstract", "notpng.png"), "wb").write(b"not a png at all")         # not a PNG → excluded
    open(os.path.join(tmp, "glyphs", "abstract", "thumb.160.webp"), "wb").write(b"RIFF....WEBP")         # other kind → excluded
    open(os.path.join(tmp, "glyphs", "abstract", "blob.enc"), "wb").write(os.urandom(64))                # encrypted blob → excluded
    open(os.path.join(tmp, "glyphs", "abstract", "comfy_raw.png"), "wb").write(_png(itxt={"prompt": "{\"1\":{}}"}))  # raw ComfyUI → excluded
    open(os.path.join(tmp, "glyphs", "batch_log.txt"), "w").write("x")
    open(os.path.join(tmp, "glyphs", "drafts", "000009_draft.png"), "wb").write(_png(text={"Title": "draft"}))  # excluded by glob


def test_filter_keeps_only_metadata_pngs_and_honours_excludes():
    tmp = tempfile.mkdtemp(); _tree(tmp)
    sel = gp.select(os.path.join(tmp, "glyphs"), excludes=["drafts/*"])
    rels = [r for r, _ in sel]
    assert rels == ["abstract/000001_entity.png", "abstract/000002_exist.png", "abstract/000003_cond.png"], rels
    assert gp.png_text_keys(os.path.join(tmp, "glyphs", "abstract", "bare.png")) == []
    assert gp.png_text_keys(os.path.join(tmp, "glyphs", "abstract", "notpng.png")) is None
    vals = gp.png_text_values(os.path.join(tmp, "glyphs", "abstract", "000002_exist.png"))
    assert vals["Description"] == "exist — iTXt ünïcode"
    assert gp.png_text_values(os.path.join(tmp, "glyphs", "abstract", "000003_cond.png"))["Comment"] == "conditionality"


def test_dry_run_logs_nothing():
    tmp = tempfile.mkdtemp(); _tree(tmp); out = os.path.join(tmp, "publish")
    assert gp.main(["--src", os.path.join(tmp, "glyphs"), "--out", out, "--dry-run", "--exclude", "drafts/*"]) == 0
    assert not os.path.exists(out), "dry run must not create the out folder"


def test_log_is_append_only_and_ipfs_rerun_is_idempotent(monkeypatch):
    tmp = tempfile.mkdtemp(); _tree(tmp); out = os.path.join(tmp, "publish")
    calls = []
    monkeypatch.setattr(gp, "ipfs_add", lambda path, api="x", pin=True: (calls.append(path), "bafy" + hashlib.sha256(open(path, "rb").read()).hexdigest()[:20])[1])
    assert gp.main(["--src", os.path.join(tmp, "glyphs"), "--out", out, "--ipfs", "--exclude", "drafts/*"]) == 0
    assert len(calls) == 3
    e1 = gp.Log(out).entries(); assert [e["kind"] for e in e1] == ["run", "file", "file", "file", "run_end"]
    assert e1[-1]["ipfs_added"] == 3 and all(e.get("cid", "").startswith("bafy") for e in e1[1:4])
    assert "sample" in e1[1] and "Title" in e1[1]["sample"]
    # second run: nothing re-added, log only grows
    assert gp.main(["--src", os.path.join(tmp, "glyphs"), "--out", out, "--ipfs", "--exclude", "drafts/*"]) == 0
    assert len(calls) == 3, "re-run must not re-add"
    e2 = gp.Log(out).entries(); assert len(e2) == 10 and e2[:5] == e1 and e2[-1]["ipfs_already"] == 3


def test_torrent_v1_fallback_writes_valid_metainfo_and_magnet():
    tmp = tempfile.mkdtemp(); _tree(tmp); out = os.path.join(tmp, "publish")
    files = gp.select(os.path.join(tmp, "glyphs"), excludes=["drafts/*"])
    data, ih = gp.torrent_v1("glyphs-test", files, os.path.join(tmp, "glyphs"), trackers=["udp://tracker.example:6969/announce"], private=True)
    assert data.startswith(b"d8:announce") and b"7:privatei1e" in data and b"4:name11:glyphs-test" in data
    assert len(ih) == 40
    # infohash is the sha1 of the bencoded info dict, recomputed independently
    i = data.index(b"4:infod") + 6; depth = 0; j = i
    while True:
        c = data[j:j + 1]
        if c == b"d" or c == b"l": depth += 1; j += 1
        elif c == b"i": j = data.index(b"e", j) + 1
        elif c == b"e": depth -= 1; j += 1
        elif c.isdigit():
            colon = data.index(b":", j); n = int(data[j:colon]); j = colon + 1 + n
        if depth == 0: break
    assert hashlib.sha1(data[i:j]).hexdigest() == ih
    m = gp.magnet(ih, "glyphs-test", ["udp://tracker.example:6969/announce"])
    assert m.startswith("magnet:?xt=urn:btih:" + ih) and "&dn=glyphs-test" in m and "&tr=udp%3A%2F%2F" in m


def test_main_torrent_step_uses_fallback_without_libtorrent(monkeypatch):
    tmp = tempfile.mkdtemp(); _tree(tmp); out = os.path.join(tmp, "publish")
    monkeypatch.setattr(gp, "torrent_libtorrent", lambda *a, **k: (_ for _ in ()).throw(ImportError("no libtorrent")))
    assert gp.main(["--src", os.path.join(tmp, "glyphs"), "--out", out, "--torrent", "glyphs-t", "--exclude", "drafts/*"]) == 0
    assert os.path.exists(os.path.join(out, "glyphs-t.torrent"))
    end = gp.Log(out).entries()[-1]; assert end["kind"] == "run_end" and end["infohash"] and end["magnet"].startswith("magnet:") and "pure-python" in end["torrent_how"]


def test_require_sigil_or_title_and_any_metadata_override():
    tmp = tempfile.mkdtemp(); _tree(tmp)
    rels = [r for r, _ in gp.select(os.path.join(tmp, "glyphs"), excludes=["drafts/*"])]
    assert "abstract/comfy_raw.png" not in rels and len(rels) == 3
    rels2 = [r for r, _ in gp.select(os.path.join(tmp, "glyphs"), excludes=["drafts/*"], require_any=())]
    assert "abstract/comfy_raw.png" in rels2


def test_cid_lookup_does_not_reread_the_log(monkeypatch):
    tmp = tempfile.mkdtemp(); log = gp.Log(tmp)
    for i in range(200):
        log.append({"kind": "file", "sha256": "s%d" % i, "cid": "c%d" % i})
    reads = []
    monkeypatch.setattr(gp.Log, "entries", lambda self: reads.append(1) or [])
    assert log.ipfs_cid_for("s150") == "c150" and log.ipfs_cid_for("nope") is None and reads == []
    monkeypatch.undo()
    assert gp.Log(tmp).ipfs_cid_for("s7") == "c7", "rebuilt from disk on open"


def test_retrack_adds_trackers_and_webseed_without_changing_infohash():
    tmp = tempfile.mkdtemp(); _tree(tmp)
    files = gp.select(os.path.join(tmp, "glyphs"), excludes=["drafts/*"])
    data, ih = gp.torrent_v1("glyphs-test", files, os.path.join(tmp, "glyphs"))
    out, ih2 = gp.retrack(data, gp.PUBLIC_TRACKERS, webseeds=["https://ipfs.example/ipfs/bafyroot/"])
    assert ih2 == ih, "trackers and web seeds live outside the info dict"
    meta = gp.bdecode(out)
    assert meta[b"announce"] == gp.PUBLIC_TRACKERS[0].encode()
    assert [t[0].decode() for t in meta[b"announce-list"]] == list(gp.PUBLIC_TRACKERS)
    assert meta[b"url-list"] == [b"https://ipfs.example/ipfs/bafyroot/"]
    again, _ = gp.retrack(out, gp.PUBLIC_TRACKERS[:2], webseeds=["https://ipfs.example/ipfs/bafyroot/"])
    assert gp.bdecode(again)[b"url-list"] == [b"https://ipfs.example/ipfs/bafyroot/"], "no duplicate web seeds"
    assert len(gp.bdecode(again)[b"announce-list"]) == len(gp.PUBLIC_TRACKERS), "existing trackers kept, none duplicated"
