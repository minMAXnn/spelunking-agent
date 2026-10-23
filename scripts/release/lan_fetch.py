"""Lay a published glyph release out on local disk from a LAN IPFS gateway, verifying as it writes.

    python3 lan_fetch.py <file.torrent> <gateway_dir_url> <dest_root> [--workers 16]

gateway_dir_url is the release folder on a trusted gateway, e.g. http://<lan-host>:8080/ipfs/<name-dir-CID>.
Every path in the torrent is fetched to dest_root/<path>.part, its sha256 is checked against _about/MANIFEST.tsv
(the manifest itself first, against MANIFEST.tsv.sha256), and only then renamed into place. Files already present
with the right size and sha256 are skipped, so a rerun resumes. The final gate is still verify_release.py.
"""
import argparse, concurrent.futures as cf, hashlib, os, sys, time, urllib.parse, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from glyph_publish import bdecode  # noqa: E402


def _get(url, dest, want_sha=None, want_size=None, tries=4):
    for attempt in range(tries):
        try:
            h, n, part = hashlib.sha256(), 0, dest + ".part"
            with urllib.request.urlopen(url, timeout=60) as r, open(part, "wb") as f:
                for chunk in iter(lambda: r.read(1 << 20), b""):
                    f.write(chunk); h.update(chunk); n += len(chunk)
            if (want_sha and h.hexdigest() != want_sha) or (want_size is not None and n != want_size):
                raise ValueError("digest/size mismatch")
            os.replace(part, dest)
            return n
        except Exception as e:  # retry transport and mismatch alike; the gateway serves content-addressed bytes
            err = e; time.sleep(1 + 2 * attempt)
    raise RuntimeError("%s: %s" % (url, err))


def _have(path, sha, size):
    if not os.path.isfile(path) or os.path.getsize(path) != size:
        return False
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest() == sha


def main(argv=None):
    ap = argparse.ArgumentParser(); ap.add_argument("torrent"); ap.add_argument("base"); ap.add_argument("dest")
    ap.add_argument("--workers", type=int, default=16); a = ap.parse_args(argv)
    info = bdecode(open(a.torrent, "rb").read())[b"info"]
    files = [("/".join(x.decode() for x in f[b"path"]), f[b"length"]) for f in info[b"files"]]
    url = lambda rel: a.base.rstrip("/") + "/" + urllib.parse.quote(rel)
    about = os.path.join(a.dest, "_about"); os.makedirs(about, exist_ok=True)
    _get(url("_about/MANIFEST.tsv.sha256"), os.path.join(about, "MANIFEST.tsv.sha256"))
    msha = open(os.path.join(about, "MANIFEST.tsv.sha256")).read().split()[0]
    _get(url("_about/MANIFEST.tsv"), os.path.join(about, "MANIFEST.tsv"), want_sha=msha)
    want = {}
    for line in open(os.path.join(about, "MANIFEST.tsv"), encoding="utf-8"):
        p = line.rstrip("\n").split("\t")
        if len(p) == 4 and p[0] != "path":
            want[p[0]] = (int(p[1]), p[2])
    jobs = []
    for rel, length in files:
        dest = os.path.join(a.dest, *rel.split("/")); os.makedirs(os.path.dirname(dest), exist_ok=True)
        size, sha = want.get(rel, (length, None))
        if size != length:
            sys.exit("manifest and torrent disagree on %s" % rel)
        if sha and _have(dest, sha, size):
            continue
        jobs.append((rel, dest, sha, length))
    t0, done, nbytes, fails = time.time(), 0, 0, []
    print("to fetch: %d of %d files" % (len(jobs), len(files)), flush=True)
    with cf.ThreadPoolExecutor(a.workers) as ex:
        futs = {ex.submit(_get, url(r), d, s, n): r for r, d, s, n in jobs}
        for fu in cf.as_completed(futs):
            try:
                nbytes += fu.result(); done += 1
            except Exception as e:
                fails.append(futs[fu]); print("FAIL", e, flush=True)
            if done % 5000 == 0:
                dt = time.time() - t0; print("%d/%d  %.1f GB  %.0f MB/s" % (done, len(jobs), nbytes / 1e9, nbytes / 1e6 / max(dt, 1e-9)), flush=True)
    print("done %d, failed %d, %.1f GB in %.0f s" % (done, len(fails), nbytes / 1e9, time.time() - t0), flush=True)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
