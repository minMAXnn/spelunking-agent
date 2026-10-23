"""skills/ mirrors the live Agent Skills. The body (after the frontmatter) must hash to the digest the site publishes; the repo
frontmatter may carry extra registry metadata (ClawHub), so the body is what is pinned."""
import os, sys, json, hashlib, tempfile, shutil
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(ROOT, "scripts"))
import sync_skills

INDEX = {"skills": [{"name": "demo-skill", "type": "skill-md", "url": "https://x/demo-skill/SKILL.md", "digest": None}]}
LIVE = "---\nname: demo-skill\ndescription: d\n---\n\n# Demo\n\nbody text\n"


def _setup(tmp, live=LIVE):
    idx = json.loads(json.dumps(INDEX)); idx["skills"][0]["digest"] = "sha256:" + hashlib.sha256(live.encode()).hexdigest()
    fetch = {"index": idx, "https://x/demo-skill/SKILL.md": live}
    return idx, (lambda url: fetch["index"] if url.endswith("index.json") else fetch[url])


def test_split_frontmatter_and_body_digest():
    fm, body = sync_skills.split(LIVE)
    assert fm["name"] == "demo-skill" and body.startswith("# Demo")
    assert sync_skills.body_digest(LIVE) == sync_skills.body_digest("---\nname: demo-skill\ndescription: d\nmetadata:\n  openclaw: {}\n---\n\n# Demo\n\nbody text\n")


def test_pull_writes_the_live_file_and_check_passes():
    tmp = tempfile.mkdtemp(); idx, fetch = _setup(tmp)
    try:
        assert sync_skills.pull(tmp, fetch=fetch) == ["demo-skill"]
        assert open(os.path.join(tmp, "skills", "demo-skill", "SKILL.md")).read() == LIVE
        assert sync_skills.check(tmp, fetch=fetch) == {"demo-skill": True}
    finally: shutil.rmtree(tmp)


def test_check_fails_on_a_tampered_body_but_not_on_extra_frontmatter():
    tmp = tempfile.mkdtemp(); idx, fetch = _setup(tmp)
    try:
        sync_skills.pull(tmp, fetch=fetch); p = os.path.join(tmp, "skills", "demo-skill", "SKILL.md")
        open(p, "w").write(LIVE.replace("---\n\n# Demo", "metadata:\n  openclaw:\n    requires: {}\n---\n\n# Demo", 1))
        assert sync_skills.check(tmp, fetch=fetch) == {"demo-skill": True}
        open(p, "w").write(LIVE.replace("body text", "other text"))
        assert sync_skills.check(tmp, fetch=fetch) == {"demo-skill": False}
    finally: shutil.rmtree(tmp)


def test_pull_keeps_registry_frontmatter_and_takes_the_live_body():
    """The repo copy carries ClawHub's metadata.openclaw block, which the site never serves. A re-pull must keep it,
    take the live description, and replace the body — otherwise every site change wipes the registry block (2026-10-23)."""
    tmp = tempfile.mkdtemp(); idx, fetch = _setup(tmp)
    try:
        sync_skills.pull(tmp, fetch=fetch); p = os.path.join(tmp, "skills", "demo-skill", "SKILL.md")
        local = open(p, encoding="utf-8").read().replace("---\n\n", "metadata:\n  openclaw:\n    emoji: \"🪔\"\n    homepage: https://x/\n---\n\n", 1)
        assert "metadata:" in local; open(p, "w", encoding="utf-8").write(local)
        new_live = LIVE.replace("body text", "changed text").replace("description: d\n", "description: d2\n")
        idx2, fetch2 = _setup(tmp, live=new_live)
        sync_skills.pull(tmp, fetch=fetch2); got = open(p, encoding="utf-8").read()
        assert "metadata:\n  openclaw:" in got and "homepage: https://x/" in got, "registry block dropped"
        assert "changed text" in got and "body text" not in got, "live body not taken"
        assert "description: d2\n" in got and "description: d\n" not in got, "live description not taken"
        assert sync_skills.check(tmp, fetch=fetch2) == {"demo-skill": True}
    finally: shutil.rmtree(tmp)
