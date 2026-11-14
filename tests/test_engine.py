import ast

from action_runner import runner
from safecode_core import cost, diff, fp_filter, llm
from safecode_core.scanner import scan_source

from .conftest import apply_fixes


def test_patch01_exactly_5_raw_2_real_3_filtered(pr):
    fs, usage, skipped = runner.scan_diff(pr.diff(), pr.root, "ru")
    assert len(fs) == 5
    assert sorted(f.rule for f in fs if not f.filtered) == ["sql-injection", "weak-hash"]
    filtered = {f.rule: f.reason_key for f in fs if f.filtered}
    assert filtered == {"weak-hash": "hash_nonpw", "sql-injection": "const_sql", "hardcoded-secret": "test"}
    assert all(f.reason for f in fs if f.filtered)
    assert not usage["ai"] and usage["tin"] == 0


def test_fixes_are_single_hunk_and_resolve_findings(pr):
    fs, _, _ = runner.scan_diff(pr.diff(), pr.root, "en")
    real = [f for f in fs if not f.filtered]
    assert all(f.fix and f.fix.suggestion_ok and f.fix.source == "Rule-based fix" for f in real)
    apply_fixes(pr.root, fs)
    for f in real:
        ast.parse((pr.root / f.file).read_text())
    again, _, _ = runner.scan_diff(pr.diff(), pr.root, "en")
    assert [f for f in again if not f.filtered] == []
    assert len(again) == 3  # the filtered ones remain, still filtered


def test_each_rule_and_its_fix():
    src = '''import hashlib, random, secrets, subprocess, os
API_KEY = "abcdefgh12345"
def a(db, q):
    db.execute(f"SELECT * FROM t WHERE a = '{q}' AND b = {q}")
def b(password):
    return hashlib.sha1(password.encode()).hexdigest()
def c():
    reset_token = random.choice("abc")
    page = random.randint(1, 5)
def d(x):
    subprocess.run(f"ls {x}", shell=True)
    subprocess.run("ls", shell=True)
'''
    fs = {(f.rule, f.line): f for f in scan_source("m.py", src)}
    assert fs[("sql-injection", 4)].fix.after == '    db.execute("SELECT * FROM t WHERE a = ? AND b = ?", (q, q))'
    assert fs[("hardcoded-secret", 2)].fix.after == 'API_KEY = os.environ["API_KEY"]'
    assert fs[("weak-hash", 6)].fix.after == "    return hashlib.sha256(password.encode()).hexdigest()"
    assert fs[("insecure-random", 8)].fix.after == '    reset_token = secrets.choice("abc")'
    assert fs[("shell-injection", 11)].fix.after == '    subprocess.run(["ls", x])'
    for f in fs.values():
        fp_filter.apply([f], {"m.py": src})
    assert not fs[("insecure-random", 9)].ctx["sec_ctx"] and fs[("insecure-random", 9)].filtered
    assert fs[("shell-injection", 12)].filtered and not fs[("shell-injection", 11)].filtered


def test_fix_needing_missing_import_is_manual():
    f = scan_source("m.py", 'TOKEN = "abcdefgh123"\n')[0]
    assert not f.fix.suggestion_ok and "import os" in f.fix.note


def test_diff_parser():
    d = "--- a/x.py\n+++ b/x.py\n@@ -1,2 +1,4 @@\n a\n+b\n c\n+++ x\n"  # last line is added content, not a header
    assert diff.parse_diff(d) == {"x.py": {2, 4}}


def test_llm_off_without_key_and_fallback(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert not llm.enabled()
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    monkeypatch.setattr(llm, "_post", lambda *a: (_ for _ in ()).throw(TimeoutError()))
    assert llm.verdict("r", "x", "") is None  # timeout -> caller falls back


def test_llm_verdict_is_final_and_counts_tokens(monkeypatch, pr):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    monkeypatch.setenv("LLM_PRICE_INPUT_PER_1K_KZT", "2")
    monkeypatch.setattr(llm, "_post", lambda *a: {"content": [{"text": '{"real": false, "reason": "ok to ignore"}'}],
                                                  "usage": {"input_tokens": 1000, "output_tokens": 0}})
    fs, usage, _ = runner.scan_diff(pr.diff(), pr.root, "en")
    assert usage["ai"] and usage["tin"] == 5000 and all(f.filtered for f in fs)
    assert cost.cost_kzt(usage["tin"], 0) == 10


def test_openai_provider_request_and_response(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    seen = {}

    def fake(url, headers, payload):
        seen.update(url=url, auth=headers["authorization"], model=payload["model"])
        return {"choices": [{"message": {"content": '{"real": true, "reason": "user input reaches SQL"}'}}],
                "usage": {"prompt_tokens": 300, "completion_tokens": 20}}

    monkeypatch.setattr(llm, "_post", fake)
    assert llm.provider() == "openai"
    v = llm.verdict("sql-injection", "x", "")
    assert v == {"real": True, "reason": "user input reaches SQL", "tin": 300, "tout": 20}
    assert seen == {"url": llm.OPENAI_URL, "auth": "Bearer sk-test", "model": "gpt-4o-mini"}
