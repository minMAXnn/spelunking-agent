#!/usr/bin/env python3
"""Publish the client, the the Agent Skills and the brand set to the Hugging Face Hub (model-type repo) and the static Space.

  python3 scripts/publish_hf.py --dry-run                      # list what would be uploaded
  python3 scripts/publish_hf.py --repo Pcmode/spelunking-agent --space Pcmode/spelunking
Uses the token from `hf auth login` (never read or printed here).
"""
import argparse, glob, os, sys

ALLOW_TOP = ["AGENTS.md", "COVENANT.md", "LICENSE", "README.md", "llms.txt", "pyproject.toml"]
ALLOW_GLOBS = ["skills/*/SKILL.md", "spelunking_agent/*.py", "docs/brand/*.png", "docs/brand/*.svg"]
TAGS = ["mcp", "agent-skills", "ai-agents", "a2a", "covenant", "governance", "autonomous-agents"]
ONE_LINER = "Structure for hard AI decisions, and a human to escalate to when the structure runs out."


def files(root):
    out = [f for f in ALLOW_TOP if os.path.exists(os.path.join(root, f))]
    for g in ALLOW_GLOBS: out += [os.path.relpath(p, root).replace(os.sep, "/") for p in glob.glob(os.path.join(root, g))]
    return sorted(f for f in out if "__pycache__" not in f)


def version(root):
    import re
    return re.search(r'__version__\s*=\s*"([^"]+)"', open(os.path.join(root, "spelunking_agent", "__init__.py"), encoding="utf-8").read()).group(1)


def EXTRA_FILES(root):
    """Generated at publish time, not kept in the repo. config.json is the Hub's download query file for a repo
    with no library tag (docs/hub/models-download-stats): every GET/HEAD of it is one counted download, so
    `hf download` / snapshot_download register, and the counter is honest (one file, fetched once per download)."""
    import json
    cfg = {"name": "spelunking-agent", "version": version(root), "kind": "mcp-client+agent-skills",
           "mcp": {"url": "https://spelunking.ai/mcp", "discovery": "https://spelunking.ai/.well-known/mcp.json"},
           "skills": "https://spelunking.ai/.well-known/agent-skills/index.json", "pypi": "spelunking-agent",
           "source": "https://github.com/minMAXnn/spelunking-agent", "license": "MIT",
           "_note": "This file is the Hub's download query file for this repo (no library tag => config.json is counted)."}
    return {"config.json": json.dumps(cfg, indent=2) + "\n"}


def skill_count(root):
    return len(glob.glob(os.path.join(root, "skills", "*", "SKILL.md")))


def model_card(root):
    readme = open(os.path.join(root, "README.md"), encoding="utf-8").read()
    body = readme.split("## What Spelunking.ai is", 1)[-1] if "## What Spelunking.ai is" in readme else readme
    fm = "---\nlicense: mit\nlanguage:\n- en\ntags:\n" + "".join(f"- {t}\n" for t in TAGS) + "pipeline_tag: other\nthumbnail: https://huggingface.co/Pcmode/spelunking-agent/resolve/main/docs/brand/og-1200x630.png\n---\n"
    head = (f"# Spelunking.ai — client, Agent Skills and hosted MCP server\n\n**{ONE_LINER}**\n\n"
            "| | |\n|---|---|\n| Install (Python, stdlib only) | `pip install spelunking-agent` |\n| Hosted MCP (streamable HTTP) | `https://spelunking.ai/mcp` · discovery `https://spelunking.ai/.well-known/mcp.json` |\n"
            "| Agent Skills (" + str(skill_count(root)) + ") | `skills/` here, mirrored from `https://spelunking.ai/.well-known/agent-skills/index.json` with sha256 digests |\n"
            "| Agents start here | https://spelunking.ai/agents/ · [llms.txt](https://spelunking.ai/llms.txt) |\n| Source | https://github.com/minMAXnn/spelunking-agent (MIT) |\n| Contact | media@minmaxgg.com |\n\n"
            "![Spelunking.ai](docs/brand/social-1280x640.png)\n\n## What Spelunking.ai is")
    return fm + head + body


def space_files(root):
    og = "https://huggingface.co/Pcmode/spelunking-agent/resolve/main/docs/brand/og-1200x630.png"
    readme = ("---\ntitle: Spelunking.ai\nemoji: 🪔\ncolorFrom: gray\ncolorTo: yellow\nsdk: static\npinned: false\nlicense: mit\nshort_description: " + ONE_LINER[:60] + "\nthumbnail: " + og + "\ntags:\n" + "".join(f"- {t}\n" for t in TAGS) + "---\n\n# Spelunking.ai\n\n" + ONE_LINER + "\n\nHosted MCP: `https://spelunking.ai/mcp` · Skills: https://spelunking.ai/.well-known/agent-skills/index.json · Client: https://huggingface.co/Pcmode/spelunking-agent\n")
    skills = sorted(os.path.basename(os.path.dirname(p)) for p in glob.glob(os.path.join(root, "skills", "*", "SKILL.md")))
    li = "".join(f'<li><code>{s}</code> — <a href="https://spelunking.ai/.well-known/agent-skills/{s}/SKILL.md">SKILL.md</a></li>' for s in skills)
    html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Spelunking.ai</title>
<meta property="og:image" content="{og}"><style>
:root{{--paper:#0e1116;--text:#e6e9ee;--text-2:#a7b0bd;--line:#2b323d;--ember:#f0913f;--gold:#f2c14e;--ring:#7dd3c0}}
body{{margin:0;background:var(--paper);color:var(--text);font:16px/1.55 ui-sans-serif,system-ui,sans-serif}} main{{max-width:760px;margin:0 auto;padding:40px 20px}}
h1{{font-size:40px;margin:16px 0 4px}} .sub{{color:var(--text-2);font-size:20px}} code,pre{{font-family:ui-monospace,Menlo,Consolas,monospace;background:#151a21;border:1px solid var(--line);border-radius:6px}}
code{{padding:1px 6px}} pre{{padding:12px 14px;overflow-x:auto}} a{{color:var(--ring)}} .ember{{color:var(--ember)}} table{{border-collapse:collapse;width:100%}} td{{padding:6px 8px;border-top:1px solid var(--line);vertical-align:top}} img{{max-width:100%;border-radius:8px}}
</style></head><body><main>
<img src="{og}" alt="Spelunking.ai — a safe haven for AI agents in the wild">
<h1>Spelunking.ai</h1><p class="sub">{ONE_LINER}</p>
<table><tr><td>Hosted MCP</td><td><code>https://spelunking.ai/mcp</code> (streamable HTTP; discovery <a href="https://spelunking.ai/.well-known/mcp.json">mcp.json</a>)</td></tr>
<tr><td>Client</td><td><code class="ember">pip install spelunking-agent</code> · <a href="https://github.com/minMAXnn/spelunking-agent">GitHub</a> · <a href="https://huggingface.co/Pcmode/spelunking-agent">Hub repo</a></td></tr>
<tr><td>Agents start here</td><td><a href="https://spelunking.ai/agents/">spelunking.ai/agents/</a> · <a href="https://spelunking.ai/llms.txt">llms.txt</a> · <a href="https://spelunking.ai/.well-known/agent-card.json">A2A card</a></td></tr>
<tr><td>Covenant</td><td><a href="https://spelunking.ai/wp-json/spelunking/v1/covenant">JSON</a> · open to everyone</td></tr></table>
<h2>Agent Skills</h2><ul>{li}</ul>
<h2>Add it to an MCP client</h2><pre>{{"mcpServers": {{"spelunking": {{"url": "https://spelunking.ai/mcp"}}}}}}</pre>
<p class="sub">Try <code>ask_guidance</code> with a thought: no key, nothing stored. Contact: media@minmaxgg.com · MIT</p>
</main></body></html>"""
    return {"README.md": readme, "index.html": html}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default="Pcmode/spelunking-agent"); ap.add_argument("--space", default="Pcmode/spelunking"); ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--root", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    a = ap.parse_args(argv); fl = files(a.root)
    print(f"repo {a.repo}: {len(fl)} files + generated {sorted(EXTRA_FILES(a.root))}"); [print("  " + f) for f in fl]; print(f"space {a.space}: README.md, index.html")
    if a.dry_run: return 0
    from huggingface_hub import HfApi
    api = HfApi()
    api.create_repo(a.repo, repo_type="model", exist_ok=True)
    api.upload_folder(repo_id=a.repo, repo_type="model", folder_path=a.root, allow_patterns=ALLOW_TOP + ALLOW_GLOBS, ignore_patterns=["**/__pycache__/**"], commit_message=f"spelunking-agent {version(a.root)}: client, {skill_count(a.root)} Agent Skills, brand set")
    api.upload_file(repo_id=a.repo, repo_type="model", path_or_fileobj=model_card(a.root).encode("utf-8"), path_in_repo="README.md", commit_message="model card")
    for name, content in EXTRA_FILES(a.root).items():
        api.upload_file(repo_id=a.repo, repo_type="model", path_or_fileobj=content.encode("utf-8"), path_in_repo=name, commit_message=f"{name}: download query file")
    api.create_repo(a.space, repo_type="space", space_sdk="static", exist_ok=True)
    for name, content in space_files(a.root).items():
        api.upload_file(repo_id=a.space, repo_type="space", path_or_fileobj=content.encode("utf-8"), path_in_repo=name, commit_message=f"space: {name}")
    print("published", f"https://huggingface.co/{a.repo}", f"https://huggingface.co/spaces/{a.space}")
    return 0


if __name__ == "__main__": sys.exit(main())
