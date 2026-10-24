"""The plugin installs from this repo's root, so everything here ships to every user. The Cloudflare app lives in
minMAXnn/spelunking-worker: no npm or wrangler files here, and no script line too long for the directory's scanner."""
import glob, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_no_worker_or_npm_files():
    for p in ("worker", "package.json", "package-lock.json", "wrangler.jsonc", "wrangler.toml", "node_modules"):
        assert not os.path.exists(os.path.join(ROOT, p)), p


def test_every_readme_points_at_the_worker_repo():
    for p in glob.glob(os.path.join(ROOT, "README*.md")):
        s = open(p, encoding="utf-8").read()
        assert "https://github.com/minMAXnn/spelunking-worker" in s and "tree/main/worker" not in s, os.path.basename(p)
        assert not any(l.startswith("worker/ ") for l in s.splitlines()), os.path.basename(p)


def test_scripts_have_no_overlong_lines():
    for p in glob.glob(os.path.join(ROOT, "**", "*.py"), recursive=True):
        for n, l in enumerate(open(p, encoding="utf-8"), 1):
            assert len(l.rstrip("\n")) <= 400, f"{os.path.relpath(p, ROOT)}:{n}"
