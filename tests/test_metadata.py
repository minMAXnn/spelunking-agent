"""Listing hygiene: the metadata every directory will read must be one version, UTF-8 with a real em-dash, and an MIT LICENSE GitHub recognises."""
import json, os, re
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(name): return open(os.path.join(ROOT, name), encoding="utf-8", newline="").read()


def test_pyproject_is_utf8_lf_with_a_real_em_dash():
    s = _read("pyproject.toml")
    assert "\r\n" not in s, "CRLF line endings"
    assert "â€”" not in s and "spelunking.ai — a safe haven" in s


def test_one_version_everywhere():
    v = re.search(r'^version = "([^"]+)"', _read("pyproject.toml"), re.M).group(1)
    assert v == json.loads(_read("server.json"))["version"] == "0.8.5"


def test_license_is_the_mit_text_github_detects():
    lic = _read("LICENSE").splitlines()
    assert lic[0] == "MIT License" and lic[2].startswith("Copyright (c) 2026")
    body = "\n".join(lic[4:])
    assert body.startswith('Permission is hereby granted, free of charge, to any person obtaining a copy\nof this software and associated documentation files (the "Software"), to deal')
    assert 'THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND' in body and body.rstrip().endswith("SOFTWARE.")
    assert len([l for l in lic if l.strip()]) == 17, "standard MIT is 17 non-blank lines; extra text makes GitHub classify it as Other"


def test_readme_counts_five_skills():
    s = _read("README.md")
    assert "four `SKILL.md` files" not in s and "five `SKILL.md` files — join, check a thought, deliberate, use the hub, contribute to the language" in s


OLD_FOUR = {"ar": "أربعة ملفات", "bn": "চারটি", "de": "vier `SKILL.md`", "es": "cuatro archivos", "fa": "چهار فایل", "fr": "quatre fichiers", "ha": "huɗu", "hi": "चार `SKILL.md`",
            "id": "empat berkas", "ja": "四つの", "ko": "네 개의", "mr": "चार `SKILL.md`", "pa": "ਚਾਰ `SKILL.md`", "pt": "quatro arquivos", "ru": "четыре файла", "sw": "faili nne",
            "ta": "நான்கு", "te": "నాలుగు", "tl": "apat na", "tr": "dört", "ur": "چار `SKILL.md`", "vi": "bốn tệp", "zh-CN": "四个", "zh-TW": "四個"}


def _skills_row(text):
    return next(l for l in text.splitlines() if l.startswith("| `/.well-known/agent-skills/index.json` |"))


def test_russian_row_says_contribute():
    assert "вносить вклад в язык" in _skills_row(_read("README.ru.md"))


def test_no_translation_still_says_four_skills():
    for code, four in OLD_FOUR.items():
        assert four not in _skills_row(_read(f"README.{code}.md")), code


def test_every_readme_shows_the_plugin_install():
    import glob
    for p in [os.path.basename(x) for x in glob.glob(os.path.join(ROOT, "README*.md"))]:
        lines = _read(p).splitlines()
        k = next(n for n, l in enumerate(lines) if l.startswith("pip install git+https://github.com/minMAXnn/spelunking-agent"))
        # its own block, never inside the shell commands: /plugin lines typed into a terminal would fail before pip runs
        assert lines[k - 6:k] == ["```text", "/plugin marketplace add minMAXnn/spelunking-agent", "/plugin install spelunking@spelunking", "```", "", "```bash"], (p, lines[k - 6:k])

def test_package_version_string_matches_pyproject():
    v = re.search(r'^version = "([^"]+)"', _read("pyproject.toml"), re.M).group(1)
    pv = re.search(r'^__version__ = "([^"]+)"', _read("spelunking_agent/__init__.py"), re.M).group(1)
    assert pv == v == "0.8.5"
