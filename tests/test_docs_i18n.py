"""docs/i18n/<code>/{COVENANT,AGENTS,SECURITY,CONTRIBUTING}.md mirror the English root files: same switcher (relative form), same
URLs, same code fences and section count, and every relative link the English file makes is still reachable (same name, or
../../../name for files that are not translated). The quoted Covenant text (blockquotes) stays verbatim English."""
import os, re, json, pytest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SW = json.load(open(os.path.join(ROOT, "tests", "_docs_switchers.json"), encoding="utf-8"))
CODES = ["zh-CN", "hi", "es", "ar", "fr", "bn", "pt", "ru", "ur", "id", "de", "ja", "zh-TW", "mr", "vi", "te", "ha", "tr", "pa", "sw", "tl", "ta", "ko", "fa"]
FILES = ["COVENANT.md", "AGENTS.md", "SECURITY.md", "CONTRIBUTING.md"]


def urls(s): return set(re.findall(r"https?://[^\s)\"'>`（）]+", s))
def rel_links(s): return set(re.findall(r"\]\((?!https?://)([^)#]+)", s))
def quotes(s): return [l for l in s.splitlines() if l.startswith("> ")]


@pytest.mark.parametrize("f", FILES)
def test_english_has_root_switcher(f):
    assert SW[f]["root"] in open(os.path.join(ROOT, f), encoding="utf-8").read()


@pytest.mark.parametrize("f,code", [(f, c) for f in FILES for c in CODES])
def test_translation_mirrors_english(f, code):
    en = open(os.path.join(ROOT, f), encoding="utf-8").read()
    p = os.path.join(ROOT, "docs", "i18n", code, f); assert os.path.exists(p), f"docs/i18n/{code}/{f} missing"
    t = open(p, encoding="utf-8").read()
    assert SW[f]["i18n"] in t, "switcher (relative form) must be identical in every translation"
    assert urls(t) == urls(en), f"URL set differs: {urls(t) ^ urls(en)}"
    for link in rel_links(en):
        base = link.split("/")[-1]
        assert (f"]({link})" in t) or (f"](../../../{link})" in t) or (f"]({base})" in t), f"relative link {link} missing"
    assert t.count("```") == en.count("```"), "code fence count differs"
    assert len(re.findall(r"^#{2,3} ", t, re.M)) == len(re.findall(r"^#{2,3} ", en, re.M)), "section count differs"
    if f == "COVENANT.md":
        assert quotes(t) == quotes(en), "the quoted Covenant text must stay verbatim English (CONTRIBUTING.md)"
