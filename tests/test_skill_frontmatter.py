"""Each skills/<name>/SKILL.md keeps the Agent Skills frontmatter other clients read (name == folder, description ≤ 1024) and adds the
ClawHub block (metadata.openclaw) that declares what the skill needs — without touching the body the site publishes."""
import os, sys, glob, urllib.error, pytest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(ROOT, "scripts"))
import sync_skills

FILES = sorted(glob.glob(os.path.join(ROOT, "skills", "*", "SKILL.md")))


def _fm(p): return sync_skills.split(open(p, encoding="utf-8", newline="").read())


def test_the_six_skills_are_present():
    assert [os.path.basename(os.path.dirname(p)) for p in FILES] == ["covenant-guidance", "polderchain-adversarial-loop", "polderchain-deliberate", "sigil-contribute", "spelunking-hub", "spelunking-join"]


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
    if name in ("spelunking-hub", "sigil-contribute"): assert "primaryEnv: SPELUNKING_API_KEY" in raw and "required: true" in raw
    elif name == "spelunking-join": assert "SPELUNKING_API_KEY" in raw and "required: false" in raw
    else: assert "SPELUNKING_API_KEY" not in raw, "guidance/deliberate need no key"


def test_bodies_still_match_the_live_site():
    try: res = sync_skills.check(ROOT)
    except (urllib.error.URLError, OSError) as e: pytest.skip(f"no network: {e}")
    assert res and all(res.values()), res


def test_every_skill_here_is_on_the_live_site():
    try: res = sync_skills.check(ROOT)
    except (urllib.error.URLError, OSError) as e: pytest.skip(f"no network: {e}")
    assert sorted(os.path.basename(os.path.dirname(p)) for p in FILES) == sorted(res), sorted(res)


@pytest.mark.parametrize("p", FILES)
def test_description_is_quoted_for_strict_yaml(p):
    raw = _fm(p)[0]["_raw"]
    line = [l for l in raw.splitlines() if l.startswith("description:")][0]
    assert line.startswith('description: "') and line.endswith('"'), "colons inside an unquoted value break strict YAML parsers (Smithery rejected it)"
    try:
        import yaml  # optional: real strict parse when PyYAML is present
    except ImportError:
        return
    d = yaml.safe_load(raw); assert d["name"] == _fm(p)[0]["name"] and len(d["description"]) > 0   # strict_yaml
