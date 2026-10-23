"""Verify a laid-out glyph release before seeding it: every MANIFEST.tsv row (size + sha256), the manifest's own
digest, the .torrent's file list against the disk, every v1 piece hash, and the infohash against the publisher's.

    python3 verify_release.py <release_root> <file.torrent> [--infohash HEX]

The release root is the folder the torrent names (info.name), e.g. .../complete/glyphs-2026-10. Exit 0 only if all
checks pass; the JSON report always prints. Reads only; never writes into the release tree.
"""
import argparse, hashlib, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from glyph_publish import bdecode, _info_span  # noqa: E402


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _disk_files(root):
    return {os.path.relpath(os.path.join(d, f), root).replace(os.sep, "/") for d, _, fs in os.walk(root) for f in fs}


def check_manifest(root, digests=None):
    """digests: {relpath: (size, sha256)} already computed by check_torrent, so the tree is read once."""
    man = os.path.join(root, "_about", "MANIFEST.tsv")
    raw = open(man, "rb").read()
    want = open(man + ".sha256").read().split()[0].lower()
    bad, missing, rows = [], [], 0
    for line in raw.decode("utf-8").splitlines():
        if not line.strip():
            continue
        rel, size, sha, _cid = line.split("\t")
        if rel == "path" and size == "size":
            continue  # header line
        rows += 1
        p = os.path.join(root, *rel.split("/"))
        if not os.path.isfile(p):
            missing.append(rel)
        elif (digests[rel] if digests and rel in digests else (os.path.getsize(p), _sha256(p))) != (int(size), sha.lower()):
            bad.append(rel)
    return {"manifest_rows": rows, "manifest_digest_ok": hashlib.sha256(raw).hexdigest() == want, "bad": bad, "missing": missing}


def check_torrent(root, data, expect_infohash=None):
    meta = bdecode(data); info = meta[b"info"]; s, e = _info_span(data)
    ih = hashlib.sha1(data[s:e]).hexdigest()
    files = [("/".join(x.decode() for x in f[b"path"]), f[b"length"]) for f in info[b"files"]]
    plen, pieces = info[b"piece length"], info[b"pieces"]
    listed = {rel for rel, _ in files}; on_disk = _disk_files(root)
    ok, idx, buf, digests = True, 0, b"", {}
    try:
        for rel, length in files:
            h, n = hashlib.sha256(), 0
            with open(os.path.join(root, *rel.split("/")), "rb") as f:
                for chunk in iter(lambda: f.read(1 << 20), b""):
                    h.update(chunk); n += len(chunk)
                    buf += chunk
                    while len(buf) >= plen:
                        ok &= hashlib.sha1(buf[:plen]).digest() == pieces[20 * idx:20 * idx + 20]; idx += 1; buf = buf[plen:]
            digests[rel] = (n, h.hexdigest())
        if buf:
            ok &= hashlib.sha1(buf).digest() == pieces[20 * idx:20 * idx + 20]; idx += 1
        ok &= idx * 20 == len(pieces)
    except FileNotFoundError:
        ok = False
    return digests, {"infohash": ih, "infohash_match": expect_infohash is None or ih == expect_infohash.lower(),
            "name": info[b"name"].decode(), "name_ok": info[b"name"].decode() == os.path.basename(os.path.normpath(root)),
            "torrent_files": len(files), "not_in_torrent": sorted(on_disk - listed)[:20], "not_on_disk": sorted(listed - on_disk)[:20],
            "pieces_ok": bool(ok), "trackers": len(meta.get(b"announce-list", [])), "webseeds": [w.decode() for w in meta.get(b"url-list", [])] if isinstance(meta.get(b"url-list", []), list) else [meta[b"url-list"].decode()]}


def verify(root, torrent_bytes, expect_infohash=None):
    digests, t = check_torrent(root, torrent_bytes, expect_infohash)
    r = check_manifest(root, digests); r.update(t)
    r["ok"] = (r["manifest_digest_ok"] and not r["bad"] and not r["missing"] and r["infohash_match"] and r["name_ok"]
               and r["pieces_ok"] and not r["not_in_torrent"] and not r["not_on_disk"])
    return r


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("root"); ap.add_argument("torrent"); ap.add_argument("--infohash")
    a = ap.parse_args(argv)
    r = verify(a.root, open(a.torrent, "rb").read(), a.infohash)
    print(json.dumps(r, indent=1))
    return 0 if r["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
