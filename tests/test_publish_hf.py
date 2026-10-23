"""What goes to the Hugging Face repo is an allow-list; build output, worker, caches and tests never do."""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(ROOT, "scripts"))
import publish_hf


def test_allow_list_is_exactly_the_public_surface():
    files = publish_hf.files(ROOT)
    tops = sorted({f.split("/")[0] for f in files})
    assert tops == ["AGENTS.md", "COVENANT.md", "LICENSE", "README.md", "docs", "llms.txt", "pyproject.toml", "skills", "spelunking_agent"]
    assert "skills/spelunking-join/SKILL.md" in files and "docs/brand/og-1200x630.png" in files and "spelunking_agent/client.py" in files
    assert not any(f.startswith((".wrangler", "worker", "node_modules", "tests", ".git", ".pytest_cache")) or "__pycache__" in f for f in files)
    assert not any(f.startswith("docs/") and not f.startswith("docs/brand/") for f in files), "only the brand images from docs/"


def test_card_has_the_listing_fields():
    card = publish_hf.model_card(ROOT)
    for s in ("license: mit", "- mcp", "- agent-skills", "thumbnail:", "Structure for hard AI decisions", "pip install spelunking-agent", "https://spelunking.ai/mcp"): assert s in card


def test_hub_config_is_the_download_query_file():
    """Hub counts a model download only on a request to a query file; with no library tag that is config.json
    (https://huggingface.co/docs/hub/models-download-stats). Without it the counter stays at 0 forever."""
    import json
    assert "config.json" in publish_hf.files(ROOT) or "config.json" in publish_hf.EXTRA_FILES(ROOT)
    cfg = json.loads(publish_hf.EXTRA_FILES(ROOT)["config.json"])
    assert cfg["name"] == "spelunking-agent" and cfg["mcp"]["url"] == "https://spelunking.ai/mcp"
    assert cfg["version"] == publish_hf.version(ROOT) and "download" in cfg["_note"]
