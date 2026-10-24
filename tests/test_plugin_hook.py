"""The start-of-session note: what the agent is told it has. It lists the skills found in skills/ (never a fixed count),
stays short, and never fails or slows a session."""
import glob, json, os, subprocess, sys, tempfile, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(ROOT, "hooks"))
import session_start

SKILLS = sorted(os.path.basename(os.path.dirname(p)) for p in glob.glob(os.path.join(ROOT, "skills", "*", "SKILL.md")))


def test_note_names_every_skill_folder():
    n = session_start.note(ROOT)
    assert SKILLS and all(f"`{s}`" in n for s in SKILLS)


def test_note_is_short_and_names_the_mcp_and_key():
    n = session_start.note(ROOT)
    assert len(n.strip().splitlines()) <= 12
    assert "https://spelunking.ai/mcp" in n and "SPELUNKING_API_KEY" in n and "admitted" in n


def test_hook_runs_fast_and_never_fails():
    t0 = time.time()
    r = subprocess.run([sys.executable, os.path.join(ROOT, "hooks", "session_start.py")], capture_output=True, text=True, env=dict(os.environ, CLAUDE_PLUGIN_ROOT=ROOT))
    assert r.returncode == 0 and time.time() - t0 < 2 and "spelunking-join" in r.stdout
    empty = tempfile.mkdtemp()
    r = subprocess.run([sys.executable, os.path.join(ROOT, "hooks", "session_start.py")], capture_output=True, text=True, env=dict(os.environ, CLAUDE_PLUGIN_ROOT=empty))
    assert r.returncode == 0 and r.stdout == ""


def test_hook_configs_run_the_script():
    for rel in ("hooks/hooks.json", "hooks/hooks-cursor.json"):
        s = open(os.path.join(ROOT, rel), encoding="utf-8").read(); json.loads(s)
        assert "session_start.py" in s, rel
    assert json.load(open(os.path.join(ROOT, ".cursor-plugin/plugin.json")))["hooks"] == "./hooks/hooks-cursor.json"


def test_gemini_md_includes_every_skill():
    lines = open(os.path.join(ROOT, "GEMINI.md"), encoding="utf-8").read().splitlines()
    assert sorted(l[len("@./skills/"):-len("/SKILL.md")] for l in lines if l.startswith("@./skills/")) == SKILLS


def _run(env_extra):
    env = {k: v for k, v in os.environ.items() if k not in ("CURSOR_PLUGIN_ROOT", "MUSE_PLUGIN_ROOT")}
    env.update(CLAUDE_PLUGIN_ROOT=ROOT, **env_extra)
    return subprocess.run([sys.executable, os.path.join(ROOT, "hooks", "session_start.py")], capture_output=True, text=True, env=env).stdout


def test_cursor_gets_additional_context_json():
    assert json.loads(_run({"CURSOR_PLUGIN_ROOT": ROOT})) == {"additional_context": session_start.note(ROOT)}


def test_muse_gets_additionalContext_json():
    assert json.loads(_run({"MUSE_PLUGIN_ROOT": ROOT})) == {"additionalContext": session_start.note(ROOT)}


def test_claude_code_gets_plain_text():
    assert _run({}) == session_start.note(ROOT)
