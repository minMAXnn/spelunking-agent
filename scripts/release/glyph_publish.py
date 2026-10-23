#!/usr/bin/env python3
"""Filter a mixed glyph folder down to metadata-embedded PNGs and publish them, with an append-only log.

Runs where the files are (the Windows PC, D:\\spelunking.ai\\<subfolder>). Standard library only.

  py -3 glyph_publish.py --src D:\\spelunking.ai\\glyphs --out D:\\spelunking.ai\\publish --dry-run
  py -3 glyph_publish.py --src ... --out ... --ipfs                      # add + pin each PNG on the local Kubo (RPC :5001)
  py -3 glyph_publish.py --src ... --out ... --torrent glyphs-2026-10    # write <out>\\glyphs-2026-10.torrent (+ magnet)
  py -3 glyph_publish.py --src ... --out ... --ipfs --torrent glyphs-2026-10

Filter: *.png only; the file must parse as a PNG and carry at least one text chunk (tEXt / iTXt / zTXt) — that is the
"metadata embedded in the PNG". Anything else (webp, svg, json, encrypted blobs, drafts) is excluded, plus --exclude globs.

Log: <out>\\publish-log.jsonl, one JSON object per line, append-only. Kinds: "run" (summary) and "file" (per published
file: relative path, size, sha256, metadata keys, cid when added to IPFS, torrent name when included). Re-runs are
idempotent: a file whose sha256 is already logged as added to IPFS is not added again; the torrent always covers the
current filtered set and logs which sha256s it contains.

Torrent: libtorrent (v2-only, per docs/WORLDMESH.md) when importable; otherwise a pure-Python v1 torrent (piece 4 MiB,
sha1) is written with a warning in the log, so the step never silently does nothing. --private marks it private
(trackers only, no DHT/PEX); public otherwise. --tracker may repeat.
"""
import argparse, fnmatch, hashlib, io, json, os, struct, sys, time, urllib.request, uuid, zlib

PNG_SIG = b"\x89PNG\r\n\x1a\n"
TEXT_CHUNKS = (b"tEXt", b"iTXt", b"zTXt")
REQUIRE_ANY = ("Sigil", "Title")   # a glyph carries these; raw ComfyUI output has only "prompt"
DEFAULT_EXCLUDES = ("*.webp", "*.log", "*.json", "*.txt")


# --------------------------------------------------------------------------------------------------- PNG metadata ---
def png_text_keys(path, max_bytes=4 * 1024 * 1024):
    """Keys of the text chunks in a PNG (list, in file order), or None if not a PNG. Reads until IDAT or max_bytes."""
    keys = []
    with open(path, "rb") as f:
        if f.read(8) != PNG_SIG:
            return None
        read = 8
        while read < max_bytes:
            head = f.read(8)
            if len(head) < 8:
                break
            length, ctype = struct.unpack(">I4s", head)
            if ctype in TEXT_CHUNKS:
                data = f.read(length)
                key = data.split(b"\x00", 1)[0].decode("latin-1", "replace")
                keys.append(key)
                f.read(4)  # crc
            else:
                f.seek(length + 4, io.SEEK_CUR)
            read += 12 + length
            if ctype in (b"IDAT", b"IEND"):
                break
    return keys


def png_text_values(path):
    """{key: value} for tEXt and iTXt (uncompressed) chunks; zTXt values are inflated. For the log sample only."""
    out = {}
    with open(path, "rb") as f:
        if f.read(8) != PNG_SIG:
            return out
        while True:
            head = f.read(8)
            if len(head) < 8:
                break
            length, ctype = struct.unpack(">I4s", head)
            data = f.read(length); f.read(4)
            if ctype == b"tEXt":
                k, _, v = data.partition(b"\x00"); out[k.decode("latin-1", "replace")] = v.decode("latin-1", "replace")
            elif ctype == b"zTXt":
                k, _, rest = data.partition(b"\x00")
                try: out[k.decode("latin-1", "replace")] = zlib.decompress(rest[1:]).decode("latin-1", "replace")
                except Exception: out[k.decode("latin-1", "replace")] = "<zTXt undecodable>"
            elif ctype == b"iTXt":
                k, _, rest = data.partition(b"\x00")
                comp = rest[:1] == b"\x01"; rest = rest[2:]
                _lang, _, rest = rest.partition(b"\x00"); _tkey, _, text = rest.partition(b"\x00")
                try: out[k.decode("latin-1", "replace")] = (zlib.decompress(text) if comp else text).decode("utf-8", "replace")
                except Exception: out[k.decode("latin-1", "replace")] = "<iTXt undecodable>"
            if ctype == b"IEND":
                break
    return out


# -------------------------------------------------------------------------------------------------------- filter ---
def select(src, excludes=(), require_any=REQUIRE_ANY):
    """Sorted list of (relpath, abspath) for metadata-embedded PNGs under src, minus --exclude globs (relative)."""
    out = []
    src = os.path.abspath(src)
    for root, _dirs, files in os.walk(src):
        for name in files:
            if not name.lower().endswith(".png"):
                continue
            ab = os.path.join(root, name); rel = os.path.relpath(ab, src).replace(os.sep, "/")
            if any(fnmatch.fnmatch(rel, pat) for pat in excludes):
                continue
            keys = png_text_keys(ab)
            if not keys or (require_any and not any(k in keys for k in require_any)):
                continue
            out.append((rel, ab))
    return sorted(out)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ----------------------------------------------------------------------------------------------------------- log ---
class Log:
    def __init__(self, out_dir):
        self.dir = out_dir
        self.path = os.path.join(out_dir, "publish-log.jsonl")
        self._cids = {}  # sha256 -> cid, built once, kept current by append(); was an O(n^2) re-read per file
        for e in self.entries():
            if e.get("kind") == "file" and e.get("sha256") and e.get("cid"):
                self._cids.setdefault(e["sha256"], e["cid"])

    def entries(self):
        if not os.path.exists(self.path):
            return []
        with open(self.path, encoding="utf-8") as f:
            return [json.loads(l) for l in f if l.strip()]

    def ipfs_cid_for(self, sha):
        return self._cids.get(sha)

    def append(self, obj):
        os.makedirs(self.dir, exist_ok=True)
        obj = dict(obj); obj.setdefault("ts", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")
        if obj.get("kind") == "file" and obj.get("sha256") and obj.get("cid"):
            self._cids.setdefault(obj["sha256"], obj["cid"])
        return obj


# ---------------------------------------------------------------------------------------------------------- IPFS ---
def ipfs_add(path, api="http://127.0.0.1:5001", pin=True):
    """Add one file via the Kubo RPC (multipart POST). Returns the CIDv1 string. Raises on failure."""
    boundary = "----spk" + uuid.uuid4().hex
    with open(path, "rb") as f:
        data = f.read()
    body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{os.path.basename(path)}\"\r\n"
            f"Content-Type: application/octet-stream\r\n\r\n").encode() + data + f"\r\n--{boundary}--\r\n".encode()
    url = f"{api}/api/v0/add?cid-version=1&raw-leaves=true&pin={'true' if pin else 'false'}&quieter=true"
    req = urllib.request.Request(url, data=body, method="POST", headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    with urllib.request.urlopen(req, timeout=600) as r:
        last = None
        for line in r.read().decode().splitlines():
            if line.strip():
                last = json.loads(line)
    if not last or "Hash" not in last:
        raise RuntimeError(f"ipfs add returned no hash for {path}")
    return last["Hash"]


# ------------------------------------------------------------------------------------------------------- torrent ---
def bencode(x):
    if isinstance(x, int): return b"i%de" % x
    if isinstance(x, bytes): return b"%d:%s" % (len(x), x)
    if isinstance(x, str): return bencode(x.encode())
    if isinstance(x, list): return b"l" + b"".join(bencode(i) for i in x) + b"e"
    if isinstance(x, dict): return b"d" + b"".join(bencode(k) + bencode(v) for k, v in sorted((k.encode() if isinstance(k, str) else k, v) for k, v in x.items())) + b"e"
    raise TypeError(type(x))


def torrent_v1(name, files, src, trackers=(), private=False, piece_len=4 * 1024 * 1024):
    """Pure-Python single-tracker v1 multi-file torrent. files = [(rel, abs)]. Returns (bytes, infohash_hex)."""
    pieces = hashlib.sha1(); out_pieces = []; buf = b""; flist = []
    for rel, ab in files:
        flist.append({"length": os.path.getsize(ab), "path": rel.split("/")})
        with open(ab, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                buf += chunk
                while len(buf) >= piece_len:
                    out_pieces.append(hashlib.sha1(buf[:piece_len]).digest()); buf = buf[piece_len:]
    if buf:
        out_pieces.append(hashlib.sha1(buf).digest())
    info = {"name": name, "piece length": piece_len, "pieces": b"".join(out_pieces), "files": flist}
    if private:
        info["private"] = 1
    meta = {"info": info, "created by": "glyph_publish.py", "creation date": int(time.time())}
    if trackers:
        meta["announce"] = trackers[0]; meta["announce-list"] = [[t] for t in trackers]
    infohash = hashlib.sha1(bencode(info)).hexdigest()
    return bencode(meta), infohash


def torrent_libtorrent(name, files, src, trackers=(), private=False):
    import libtorrent as lt  # noqa
    fs = lt.file_storage()
    for rel, ab in files:
        fs.add_file(name + "/" + rel, os.path.getsize(ab))
    t = lt.create_torrent(fs, flags=lt.create_torrent.v2_only)
    for tr in trackers:
        t.add_tracker(tr)
    t.set_priv(bool(private)); t.set_creator("glyph_publish.py")
    lt.set_piece_hashes(t, os.path.abspath(src))
    data = lt.bencode(t.generate()); ti = lt.torrent_info(data)
    return data, str(ti.info_hashes().v2) if hasattr(ti, "info_hashes") else str(ti.info_hash())


def magnet(infohash_hex, name, trackers=(), v2=False, webseeds=()):
    tag = ("urn:btmh:1220" if v2 else "urn:btih:") + infohash_hex
    m = f"magnet:?xt={tag}&dn={urllib.request.quote(name)}"
    for tr in trackers:
        m += "&tr=" + urllib.request.quote(tr, safe="")
    for ws in webseeds:
        m += "&ws=" + urllib.request.quote(ws, safe="")
    return m


PUBLIC_TRACKERS = (  # long-lived open trackers (ngosang/trackerslist best, 2026-10-23); announce data only, no accounts
    "udp://tracker.opentrackr.org:1337/announce",
    "udp://open.stealth.si:80/announce",
    "udp://tracker.torrent.eu.org:451/announce",
    "udp://open.demonii.com:1337/announce",
    "udp://explodie.org:6969/announce",
)


def _bdec(b, i):
    c = b[i:i + 1]
    if c == b"i":
        j = b.index(b"e", i); return int(b[i + 1:j]), j + 1
    if c == b"l":
        out = []; i += 1
        while b[i:i + 1] != b"e":
            v, i = _bdec(b, i); out.append(v)
        return out, i + 1
    if c == b"d":
        out = {}; i += 1
        while b[i:i + 1] != b"e":
            k, i = _bdec(b, i); v, i = _bdec(b, i); out[k] = v
        return out, i + 1
    if c.isdigit():
        colon = b.index(b":", i); n = int(b[i:colon]); return b[colon + 1:colon + 1 + n], colon + 1 + n
    raise ValueError("bad bencode at %d" % i)


def bdecode(b):
    v, end = _bdec(b, 0)
    if end != len(b): raise ValueError("trailing bytes")
    return v


def _info_span(b):
    """Byte span of the top-level info value, so the infohash is taken over the exact original bytes."""
    i = 1
    while b[i:i + 1] != b"e":
        k, i = _bdec(b, i); start = i; _, i = _bdec(b, i)
        if k == b"info": return start, i
    raise ValueError("no info dict")


def retrack(torrent_bytes, trackers=(), webseeds=()):
    """Add trackers (announce/announce-list) and BEP 19 web seeds (url-list) to an existing .torrent.
    Both live outside the info dict, so the infohash is unchanged; existing entries are kept, none duplicated.
    Returns (bytes, infohash_hex) — sha1 for v1/hybrid, sha256 for v2-only (meta version 2 without pieces)."""
    meta = bdecode(torrent_bytes); s, e = _info_span(torrent_bytes); raw_info = torrent_bytes[s:e]
    have = [t[0] for t in meta.get(b"announce-list", [])] or ([meta[b"announce"]] if b"announce" in meta else [])
    for t in trackers:
        t = t.encode()
        if t not in have: have.append(t)
    if have:
        meta[b"announce"] = have[0]; meta[b"announce-list"] = [[t] for t in have]
    ul = meta.get(b"url-list", []); ul = [ul] if isinstance(ul, bytes) else list(ul)
    for w in webseeds:
        w = w.encode()
        if w not in ul: ul.append(w)
    if ul: meta[b"url-list"] = ul
    out = bencode(meta)
    s2, e2 = _info_span(out)
    if out[s2:e2] != raw_info: raise RuntimeError("info dict changed on re-encode; refusing")
    info = meta[b"info"]
    v2only = info.get(b"meta version") == 2 and b"pieces" not in info
    return out, (hashlib.sha256 if v2only else hashlib.sha1)(raw_info).hexdigest()


# ---------------------------------------------------------------------------------------------------------- main ---
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--exclude", action="append", default=[], help="glob on the relative path, repeatable (e.g. '*/drafts/*', '*.enc.png')")
    ap.add_argument("--ipfs", action="store_true"); ap.add_argument("--api", default="http://127.0.0.1:5001")
    ap.add_argument("--torrent", metavar="NAME", help="write <out>/<NAME>.torrent for the filtered set")
    ap.add_argument("--tracker", action="append", default=[]); ap.add_argument("--private", action="store_true")
    ap.add_argument("--any-metadata", action="store_true", help="accept any text chunk instead of requiring Sigil or Title")
    ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--sample", type=int, default=3, help="log metadata values for the first N files")
    a = ap.parse_args(argv)
    try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # XMP chunks start with a BOM; cp1252 consoles would raise
    except Exception: pass

    files = select(a.src, list(DEFAULT_EXCLUDES) + a.exclude, () if a.any_metadata else REQUIRE_ANY)
    total = sum(os.path.getsize(ab) for _, ab in files)
    log = Log(a.out); run_id = uuid.uuid4().hex[:12]
    print(f"filtered: {len(files)} metadata PNGs, {total / 1e9:.2f} GB (run {run_id})")
    if not files:
        print("nothing to publish"); return 1
    if a.dry_run:
        for rel, ab in files[: a.sample]:
            print(" ", rel, json.dumps({k: v[:80] for k, v in png_text_values(ab).items()}, ensure_ascii=False))
        print(f"  … {len(files)} files; log would go to {log.path}"); return 0

    log.append({"kind": "run", "run": run_id, "src": os.path.abspath(a.src), "n": len(files), "bytes": total, "ipfs": a.ipfs, "torrent": a.torrent, "private": a.private, "exclude": a.exclude})
    cids = {}; added = 0; skipped = 0; failed = 0
    for i, (rel, ab) in enumerate(files):
        sha = sha256_file(ab); entry = {"kind": "file", "run": run_id, "path": rel, "size": os.path.getsize(ab), "sha256": sha, "keys": png_text_keys(ab)}
        if i < a.sample:
            entry["sample"] = {k: v[:200] for k, v in png_text_values(ab).items()}
        if a.ipfs:
            prev = log.ipfs_cid_for(sha)
            if prev:
                entry["cid"] = prev; entry["ipfs"] = "already"; skipped += 1
            else:
                try:
                    entry["cid"] = ipfs_add(ab, a.api); entry["ipfs"] = "added"; added += 1
                except Exception as e:
                    entry["ipfs"] = "failed: " + str(e)[:160]; failed += 1
            cids[rel] = entry.get("cid")
        if a.torrent:
            entry["torrent"] = a.torrent
        log.append(entry)
        if (i + 1) % 500 == 0:
            print(f"  {i + 1}/{len(files)} …")
    summary = {"kind": "run_end", "run": run_id, "ipfs_added": added, "ipfs_already": skipped, "ipfs_failed": failed}
    if a.torrent:
        try:
            data, ih = torrent_libtorrent(a.torrent, files, a.src, a.tracker, a.private); v2 = True; how = "libtorrent v2"
        except ImportError:
            data, ih = torrent_v1(a.torrent, files, a.src, a.tracker, a.private); v2 = False; how = "pure-python v1 (libtorrent not importable)"
        os.makedirs(a.out, exist_ok=True)
        tpath = os.path.join(a.out, a.torrent + ".torrent")
        with open(tpath, "wb") as f:
            f.write(data)
        mg = magnet(ih, a.torrent, a.tracker, v2)
        summary.update({"torrent_file": tpath, "infohash": ih, "magnet": mg, "torrent_how": how, "torrent_private": a.private})
        print(f"torrent: {tpath}\ninfohash: {ih}\nmagnet: {mg}\n({how})")
    log.append(summary)
    print(f"ipfs: added {added}, already {skipped}, failed {failed}; log: {log.path}")
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
