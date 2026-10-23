"""Each skills/<name>/SKILL.md keeps the Agent Skills frontmatter other clients read (name == folder, description ≤ 1024) and adds the
ClawHub block (metadata.openclaw) that declares what the skill needs — without touching the body the site publishes."""
import os, sys, glob, urllib.error, pytest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(ROOT, "scripts"))
import sync_skills

FILES = sorted(glob.glob(os.path.join(ROOT, "skills", "*", "SKILL.md")))


def _fm(p): return sync_skills.split(open(p, encoding="utf-8", newline="").read())


def test_four_skills_present():
    assert [os.path.basename(os.path.dirname(p)) for p in FILES] == ["covenant-guidance", "polderchain-deliberate", "spelunking-hub", "spelunking-join"]


@pytest.mark.parametrize("p", FILES)
def test_agent_skills_frontmatter_intact(p):
    fm, body = _fm(p)
    assert fm["name"] == os.path.basename(os.path.dirname(p)) and 0 < len(fm["description"]) <= 1024
    assert body.lstrip().startswith("# ")


@pytest.mark.parametrize("p", FILES)
def test_clawhub_block_declares_homepage_and_needs(p):
    fm, _ = _fm(p); raw = fm["_raw"]
    assert "\nmetadata:\n  openclaw:\n" in "\n" + raw and "homepage: https://spelunking.ai/agents/" in raw
    name = fm["name"]
    if name == "spelunking-hub": assert "primaryEnv: SPELUNKING_API_KEY" in raw and "required: true" in raw
    elif name == "spelunking-join": assert "SPELUNKING_API_KEY" in raw and "required: false" in raw
    else: assert "SPELUNKING_API_KEY" not in raw, "guidance/deliberate need no key"


def test_bodies_still_match_the_live_site():
    try: res = sync_skills.check(ROOT)
    except (urllib.error.URLError, OSError) as e: pytest.skip(f"no network: {e}")
    assert res and all(res.values()), res
