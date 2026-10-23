#!/usr/bin/env python3
"""Mirror the live Agent Skills into skills/<name>/SKILL.md and check them against the digests the site publishes.

The site is the source of truth: https://spelunking.ai/.well-known/agent-skills/index.json (agentskills.io discovery 0.2.0).
The repo copy may carry extra frontmatter for registries (ClawHub's metadata.openclaw), so the check pins the BODY after the
frontmatter: sha256(body) must equal sha256(live body). On a fresh pull the whole file is byte-exact, so whole-file digest == live digest too.

  python3 scripts/sync_skills.py --pull     # write/refresh skills/ from the site
  python3 scripts/sync_skills.py --check    # exit 1 if any body drifted from the live file
Standard library only.
"""
import argparse, hashlib, json, os, sys, time, urllib.error, urllib.request

INDEX_URL = "https://spelunking.ai/.well-known/agent-skills/index.json"


def _fetch(url, attempts=3, wait=5, opener=urllib.request.urlopen, sleep=time.sleep):
    """A 5xx (Cloudflare's 52x origin errors included) or a network failure is retried; a 4xx is an answer and is not."""
    for i in range(attempts):
        try:
            with opener(url, timeout=20) as r:
                data = r.read()
            break
        except urllib.error.HTTPError as e:
            if e.code < 500 or i == attempts - 1: raise
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            if i == attempts - 1: raise
        sleep(wait * (i + 1))
    return json.loads(data) if url.endswith(".json") else data.decode("utf-8")


def split(text):
    """-> (frontmatter dict of simple `key: value` lines, body). Nested keys are kept raw under '_raw'."""
    if not text.startswith("---\n"): return {}, text
    end = text.find("\n---", 4)
    if end < 0: return {}, text
    fm_text, body = text[4:end], text[end + 4:].lstrip("\n")
    fm = {"_raw": fm_text}
    for line in fm_text.splitlines():
        if line[:1] not in (" ", "\t") and ":" in line:
            k, v = line.split(":", 1); v = v.strip()
            if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'": v = v[1:-1].replace('\\"', '"')
            fm[k.strip()] = v
    return fm, body


def body_digest(text): return "sha256:" + hashlib.sha256(split(text)[1].encode("utf-8")).hexdigest()


def merge(local, live):
    """Keep the repo copy's frontmatter (it may carry registry-only keys such as ClawHub's metadata.openclaw), but take the
    live `name:` and `description:` lines and the whole live body. The body is what the digest pins."""
    lfm, _ = split(local); vfm, vbody = split(live)
    if "_raw" not in lfm or "_raw" not in vfm: return live
    live_lines = {ln.split(":", 1)[0].strip(): ln for ln in vfm["_raw"].splitlines() if ln[:1] not in (" ", "\t") and ":" in ln}
    out, seen = [], set()
    for ln in lfm["_raw"].splitlines():
        key = ln.split(":", 1)[0].strip() if ln[:1] not in (" ", "\t") and ":" in ln else None
        if key in ("name", "description") and key in live_lines: out.append(live_lines[key]); seen.add(key)
        else: out.append(ln)
    for key in ("name", "description"):
        if key in live_lines and key not in seen and key not in lfm: out.insert(0, live_lines[key])
    return "---\n" + "\n".join(out) + "\n---\n\n" + vbody


def _dir(root, name): return os.path.join(root, "skills", name)


def pull(root, fetch=_fetch, index_url=INDEX_URL):
    names = []
    for s in fetch(index_url)["skills"]:
        live = fetch(s["url"])
        got = "sha256:" + hashlib.sha256(live.encode("utf-8")).hexdigest()
        if got != s["digest"]: raise RuntimeError(f"{s['name']}: live file does not match its own index digest ({got} vs {s['digest']})")
        os.makedirs(_dir(root, s["name"]), exist_ok=True)
        path = os.path.join(_dir(root, s["name"]), "SKILL.md")
        text = merge(open(path, encoding="utf-8", newline="").read(), live) if os.path.exists(path) else live
        with open(path, "w", encoding="utf-8", newline="") as f: f.write(text)
        names.append(s["name"])
    return names


def check(root, fetch=_fetch, index_url=INDEX_URL):
    out = {}
    for s in fetch(index_url)["skills"]:
        p = os.path.join(_dir(root, s["name"]), "SKILL.md")
        if not os.path.exists(p): out[s["name"]] = False; continue
        out[s["name"]] = body_digest(open(p, encoding="utf-8", newline="").read()) == body_digest(fetch(s["url"]))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True); g.add_argument("--pull", action="store_true"); g.add_argument("--check", action="store_true")
    ap.add_argument("--root", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    a = ap.parse_args(argv)
    if a.pull:
        for n in pull(a.root): print("pulled", n)
        return 0
    res = check(a.root)
    for n, ok in res.items(): print(("ok      " if ok else "DRIFTED ") + n)
    return 0 if res and all(res.values()) else 1


if __name__ == "__main__": sys.exit(main())
