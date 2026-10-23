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
    assert v == json.loads(_read("server.json"))["version"] == "0.8.2"


def test_license_is_the_mit_text_github_detects():
    lic = _read("LICENSE").splitlines()
    assert lic[0] == "MIT License" and lic[2].startswith("Copyright (c) 2026")
    body = "\n".join(lic[4:])
    assert body.startswith('Permission is hereby granted, free of charge, to any person obtaining a copy\nof this software and associated documentation files (the "Software"), to deal')
    assert 'THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND' in body and body.rstrip().endswith("SOFTWARE.")
    assert len([l for l in lic if l.strip()]) == 17, "standard MIT is 17 non-blank lines; extra text makes GitHub classify it as Other"


def test_readme_counts_four_skills():
    s = _read("README.md").lower()
    assert "three `skill.md`" not in s and "four `skill.md` files" in s


def test_package_version_string_matches_pyproject():
    v = re.search(r'^version = "([^"]+)"', _read("pyproject.toml"), re.M).group(1)
    pv = re.search(r'^__version__ = "([^"]+)"', _read("spelunking_agent/__init__.py"), re.M).group(1)
    assert pv == v == "0.8.2"
