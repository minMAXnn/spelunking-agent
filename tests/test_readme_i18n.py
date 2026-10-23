"""Every translated README is a faithful mirror of README.md: same language switcher, same links and URLs, same code fences, same section count."""
import os, re, glob, pytest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CODES = ["zh-CN", "hi", "es", "ar", "fr", "bn", "pt", "ru", "ur", "id", "de", "ja", "zh-TW", "mr", "vi", "te", "ha", "tr", "pa", "sw", "tl", "ta", "ko", "fa"]
SWITCHER = open(os.path.join(ROOT, "tests", "_readme_switcher.txt"), encoding="utf-8").read()
EN = open(os.path.join(ROOT, "README.md"), encoding="utf-8").read()


def urls(s): return set(re.findall(r"https?://[^\s)\"'>`（）]+", s))  # a URL ends at whitespace, a closing paren, a quote or a backtick; CJK parens too
def rel_links(s): return set(re.findall(r"\]\((?!https?://)([^)#]+)", s)) | set(re.findall(r'href="(?!https?://)([^"]+)"', s))


def test_english_has_the_switcher_and_one_license_section():
    assert SWITCHER in EN and EN.count("\n## License") == 1


@pytest.mark.parametrize("code", CODES)
def test_translation_mirrors_english(code):
    p = os.path.join(ROOT, f"README.{code}.md"); assert os.path.exists(p), f"README.{code}.md missing"
    t = open(p, encoding="utf-8").read()
    assert SWITCHER in t, "language switcher must be identical in every README"
    assert urls(t) == urls(EN), f"URL set differs: {urls(t) ^ urls(EN)}"
    assert rel_links(t) >= rel_links(EN) - {f"README.{c}.md" for c in CODES} - {"README.md"}, "a relative link from the English README is missing"
    assert t.count("```") == EN.count("```"), "code fence count differs"
    assert len(re.findall(r"^## ", t, re.M)) == len(re.findall(r"^## ", EN, re.M)), "section count differs"
    assert "pip install git+https://github.com/minMAXnn/spelunking-agent" in t and "https://spelunking.ai/mcp" in t
