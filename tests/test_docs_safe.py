"""Docs ship inside the plugin, and the directory scanner shows any fetch-then-run recipe to users as an install-time risk.
Point at the upstream install page instead of reproducing its commands."""
import glob, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Built from parts so this file is not itself read as a recipe: a downloader piped into a shell, or a clone-and-build.
_PIPED = [("curl", "(?:ba)?sh"), ("wget", "(?:ba)?sh"), ("iwr", "iex")]
FETCH_THEN_RUN = re.compile("|".join([rf"{a}[^\n]*\|\s*{b}" for a, b in _PIPED] + [r"git\s+" + "clone", r"make\s+" + "publisher"]), re.I)


def test_no_doc_fetches_and_runs_code():
    for p in glob.glob(os.path.join(ROOT, "docs", "**", "*.md"), recursive=True) + glob.glob(os.path.join(ROOT, "*.md")):
        assert not FETCH_THEN_RUN.search(open(p, encoding="utf-8").read()), os.path.relpath(p, ROOT)
