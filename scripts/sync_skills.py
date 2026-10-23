#!/usr/bin/env python3
"""Mirror the live Agent Skills into skills/<name>/SKILL.md and check them against the digests the site publishes.

The site is the source of truth: https://spelunking.ai/.well-known/agent-skills/index.json (agentskills.io discovery 0.2.0).
The repo copy may carry extra frontmatter for registries (ClawHub's metadata.openclaw), so the check pins the BODY after the
frontmatter: sha256(body) must equal sha256(live body). On a fresh pull the whole file is byte-exact, so whole-file digest == live digest too.

  python3 scripts/sync_skills.py --pull     # write/refresh skills/ from the site
  python3 scripts/sync_skills.py --check    # exit 1 if any body drifted from the live file
Standard library only.
"""
import argparse, hashlib, json, os, sys, urllib.request

INDEX_URL = "https://spelunking.ai/.well-known/agent-skills/index.json"


def _fetch(url):
    with urllib.request.urlopen(url, timeout=20) as r:
        data = r.read()
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


def _dir(root, name): return os.path.join(root, "skills", name)


def pull(root, fetch=_fetch, index_url=INDEX_URL):
    names = []
    for s in fetch(index_url)["skills"]:
        live = fetch(s["url"])
        got = "sha256:" + hashlib.sha256(live.encode("utf-8")).hexdigest()
        if got != s["digest"]: raise RuntimeError(f"{s['name']}: live file does not match its own index digest ({got} vs {s['digest']})")
        os.makedirs(_dir(root, s["name"]), exist_ok=True)
        with open(os.path.join(_dir(root, s["name"]), "SKILL.md"), "w", encoding="utf-8", newline="") as f: f.write(live)
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
