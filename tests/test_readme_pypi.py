"""README.md is also the PyPI and Hugging Face page, where a relative path has nothing to resolve against:
every image and link in it must be absolute."""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _readme():
    with open(os.path.join(ROOT, "README.md"), encoding="utf-8") as f:
        return f.read()


def test_readme_has_no_relative_images_or_links():
    s = _readme()
    html = re.findall(r'(?:src|href)="([^"]+)"', s)
    md = re.findall(r'\]\(([^)\s]+)\)', s)
    relative = [u for u in html + md if not re.match(r'^(https?://|mailto:|#)', u)]
    assert relative == [], f"relative references break on PyPI: {relative}"


def test_banner_points_at_the_repo_file():
    assert 'src="https://raw.githubusercontent.com/minMAXnn/spelunking-agent/main/docs/brand/social-1280x640.png"' in _readme()
