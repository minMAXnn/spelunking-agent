"""The repo installs as the `spelunking` plugin in eight agents, like superpowers: one manifest per host, all pointing at
the same skills/ (site mirrors) and the same hosted MCP server, all at the package version."""
import json, os
import spelunking_agent

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFESTS = [".claude-plugin/plugin.json", ".cursor-plugin/plugin.json", ".codex-plugin/plugin.json", "gemini-extension.json",
             ".kimi-plugin/plugin.json", ".antigravity-plugin/plugin.json", ".devin-plugin/plugin.json", ".muse-plugin/plugin.json"]
MARKETPLACES = [".claude-plugin/marketplace.json", ".muse-plugin/marketplace.json"]


def load(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return json.load(f)


def test_every_manifest_is_spelunking_at_the_package_version():
    for rel in MANIFESTS:
        m = load(rel)
        assert m["name"] == "spelunking", rel
        assert m["version"] == spelunking_agent.__version__, rel
        if "license" in m: assert m["license"] == "MIT", rel
        if "homepage" in m: assert m["homepage"] == "https://spelunking.ai", rel


def test_skill_hosts_point_at_skills():
    for rel in (".claude-plugin/plugin.json", ".cursor-plugin/plugin.json", ".codex-plugin/plugin.json", ".kimi-plugin/plugin.json"):
        assert load(rel).get("skills", "./skills/") == "./skills/", rel
    assert os.path.isdir(os.path.join(ROOT, "skills"))


def test_marketplaces_install_from_this_repo():
    for rel in MARKETPLACES:
        m = load(rel)
        assert m["owner"]["name"] == "minMAXnn" and len(m["plugins"]) == 1, rel
        p = m["plugins"][0]
        assert p["name"] == "spelunking" and p["source"] == "./" and p["version"] == spelunking_agent.__version__, rel
    assert load(".claude-plugin/marketplace.json")["name"] == "spelunking"


def test_mcp_config_reaches_the_site_without_a_literal_key():
    s = load(".mcp.json")["mcpServers"]["spelunking"]
    assert s == {"type": "http", "url": "https://spelunking.ai/mcp", "headers": {"Authorization": "Bearer ${SPELUNKING_API_KEY:-}"}}
    for rel in MANIFESTS + MARKETPLACES + [".mcp.json"]:
        assert "spk_" not in open(os.path.join(ROOT, rel), encoding="utf-8").read(), rel


def test_codex_interface_brand():
    i = load(".codex-plugin/plugin.json")["interface"]
    assert i["displayName"] == "Spelunking.ai" and i["developerName"] == "minMAXnn"
    assert i["privacyPolicyURL"] == "https://spelunking.ai/privacy/" and i["termsOfServiceURL"] == "https://spelunking.ai/terms/"
    assert i["brandColor"] == "#f0913f"
    for k in ("logo", "composerIcon"):
        assert os.path.isfile(os.path.join(ROOT, i[k])), i[k]
