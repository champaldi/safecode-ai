import logging

import pytest

from action_runner import __main__ as cli
from action_runner import runner
from action_runner.github import FakeGH

from .conftest import apply_fixes

CFG = {"language": "en", "fail_on": "high", "api_url": "", "ingest_token": ""}


def summary(gh):
    return next(c["body"] for c in gh.s["issue"])


def test_summary_headline_and_filtered_reasons(pr):
    gh = FakeGH()
    res = runner.run(gh, "o/r", 1, "sha1aaaaaaa", CFG, pr.diff(), pr.root)
    body = summary(gh)
    assert "### 5 raw → 2 real, 3 filtered (60% noise removed)" in body.splitlines()
    details = body.split("<details>")[1]
    assert "Filtered findings (3)" in details and "SQL string is constant" in details
    assert res["conclusion"] == "failure" and gh.s["checks"][-1]["conclusion"] == "failure"
    assert len(gh.s["review"]) == 2 and "```suggestion" in gh.s["review"][0]["body"]


def test_rerun_updates_in_place_and_marks_resolved(pr):
    gh = FakeGH()
    first = runner.run(gh, "o/r", 1, "sha1aaaaaaa", CFG, pr.diff(), pr.root)
    apply_fixes(pr.root, first["findings"])  # developer clicks "Commit suggestion"
    second = runner.run(gh, "o/r", 1, "sha2bbbbbbb", CFG, pr.diff(), pr.root)
    assert len(gh.s["issue"]) == 1  # same comment, updated in place
    body = summary(gh)
    assert "### 3 raw → 0 real, 3 filtered (100% noise removed)" in body
    assert body.count("~~") == 4 and "Resolved since last run" in body  # two struck-through titles
    assert len(gh.s["review"]) == 2  # no duplicate inline comments
    assert any(e[0].startswith("reply to inline") for e in gh.events)
    assert second["conclusion"] == "success" and gh.s["checks"][-1]["conclusion"] == "success"


def test_ingest_failure_and_missing_api_url_dont_change_check(pr, caplog):
    caplog.set_level(logging.WARNING)
    gh = FakeGH()
    runner.run(gh, "o/r", 1, "s1", CFG, pr.diff(), pr.root)  # no api-url
    assert "api-url not set" in caplog.text and gh.s["checks"][-1]["conclusion"] == "failure"
    caplog.clear()
    gh = FakeGH()
    runner.run(gh, "o/r", 1, "s1", {**CFG, "api_url": "http://127.0.0.1:9", "ingest_token": "t"}, pr.diff(), pr.root)
    assert "ingest failed" in caplog.text and gh.s["checks"][-1]["conclusion"] == "failure"


def test_scan_engine_error_is_a_failed_check_never_success(pr, monkeypatch, tmp_path):
    def boom(*a, **k):
        raise RuntimeError("engine exploded")

    monkeypatch.setattr(runner, "scan_diff", boom)
    gh = FakeGH()
    res = runner.run(gh, "o/r", 1, "s1", CFG, pr.diff(), pr.root)
    chk = gh.events[-1]
    assert gh.s["checks"][-1] == {"conclusion": "failure", "title": "SafeCode AI: scan failed"}
    assert "engine exploded" in chk[1] and res["error"]
    # CLI exit code is non-zero too
    d = tmp_path / "x.diff"
    d.write_text(pr.diff())
    assert cli.main(["--dry-run", "--diff", str(d), "--root", str(pr.root)]) == 1


def test_comment_api_failure_still_yields_correct_check(pr):
    class Broken(FakeGH):
        def create_issue_comment(self, *a):
            raise OSError("403")

    gh = Broken()
    runner.run(gh, "o/r", 1, "s1", CFG, pr.diff(), pr.root)
    assert gh.s["checks"][-1]["conclusion"] == "failure"


def test_fail_on_critical_ignores_high(pr):
    gh = FakeGH()
    runner.run(gh, "o/r", 1, "s1", {**CFG, "fail_on": "critical"}, pr.diff(), pr.root)
    assert gh.s["checks"][-1]["title"] == "SafeCode AI: 1 blocking finding(s)"


def test_dry_run_state_persists_between_cli_runs(pr, tmp_path, capsys):
    d, st = tmp_path / "x.diff", tmp_path / "state.json"
    d.write_text(pr.diff())
    args = ["--dry-run", "--diff", str(d), "--root", str(pr.root), "--state", str(st), "--language", "en"]
    assert cli.main(args) == 0
    assert "summary comment (created)" in capsys.readouterr().out
    cli.main(args)
    assert "summary comment (updated in place)" in capsys.readouterr().out
