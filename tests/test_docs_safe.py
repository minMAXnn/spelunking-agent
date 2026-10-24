"""Docs ship inside the plugin, and the directory scanner shows any fetch-then-run recipe to users as an install-time risk.
Point at the upstream install page instead of reproducing its commands."""
import glob, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FETCH_THEN_RUN = re.compile(r"git clone|curl[^\n]*\|\s*(?:ba)?sh|wget[^\n]*\|\s*(?:ba)?sh|make publisher|iwr[^\n]*\|\s*iex", re.I)


def test_no_doc_fetches_and_runs_code():
    for p in glob.glob(os.path.join(ROOT, "docs", "**", "*.md"), recursive=True) + glob.glob(os.path.join(ROOT, "*.md")):
        assert not FETCH_THEN_RUN.search(open(p, encoding="utf-8").read()), os.path.relpath(p, ROOT)
