import pytest
from fastapi.testclient import TestClient

from action_runner import runner
from action_runner.github import FakeGH
from web import kpis
from web.app import app

from .conftest import apply_fixes

H = {"Authorization": "Bearer tok"}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("SAFECODE_DB", str(tmp_path / "t.db"))
    monkeypatch.setenv("INGEST_TOKEN", "tok")
    return TestClient(app)


def test_fresh_db_is_zeros_and_pages_load(client):
    r = client.get("/api/stats").json()["real"]
    assert r["pr_scans"] == 0 and r["filtered_pct"] == 0 and r["accepted_fixes"] == 0 and r["recent"] == []
    assert "No PR scans yet" in client.get("/dashboard").text
    assert client.get("/healthz").status_code == 200


def test_ingest_requires_bearer_token(client, monkeypatch):
    body = {"repo": "o/r", "pr": 1, "sha": "a", "conclusion": "success", "duration_s": 1, "findings": []}
    assert client.post("/api/ingest", json=body).status_code == 401
    assert client.post("/api/ingest", json=body, headers={"Authorization": "Bearer nope"}).status_code == 401
    assert client.post("/api/ingest", json=body, headers=H).status_code == 200
    monkeypatch.delenv("INGEST_TOKEN")  # unset token must reject everything, not allow everything
    assert client.post("/api/ingest", json=body, headers={"Authorization": "Bearer "}).status_code == 401


def test_accepted_fix_counter_increments_after_rerun(client, pr, monkeypatch):
    monkeypatch.setattr(runner, "post_ingest", lambda url, tok, p: client.post("/api/ingest", json=p, headers=H).raise_for_status())
    cfg = {"language": "en", "fail_on": "high", "api_url": "http://x", "ingest_token": "tok"}
    gh = FakeGH()
    first = runner.run(gh, "o/r", 7, "sha1aaaaaaa", cfg, pr.diff(), pr.root)
    s = client.get("/api/stats").json()["real"]
    assert (s["pr_scans"], s["findings"], s["filtered_pct"], s["accepted_fixes"]) == (1, 2, 60, 0)
    runner.run(gh, "o/r", 7, "sha1aaaaaaa", cfg, pr.diff(), pr.root)  # same SHA re-run: not a fix
    assert client.get("/api/stats").json()["real"]["accepted_fixes"] == 0
    apply_fixes(pr.root, first["findings"])
    runner.run(gh, "o/r", 7, "sha2bbbbbbb", cfg, pr.diff(), pr.root)
    s = client.get("/api/stats").json()["real"]
    assert s["accepted_fixes"] == 2 and s["pr_scans"] == 3 and s["prs"] == 1
    assert s["recent"][0]["conclusion"] == "success"


@pytest.mark.parametrize("kind,target,sim,expected", [
    ("higher", 100, 95, "green"), ("higher", 100, 94.99, "yellow"), ("higher", 100, 85, "yellow"),
    ("higher", 100, 84.99, "red"), ("burn", 100, 105, "green"), ("burn", 100, 105.01, "yellow"),
    ("burn", 100, 115, "yellow"), ("burn", 100, 115.01, "red"), ("churn", 2, 2, "green"),
    ("churn", 2, 3, "yellow"), ("churn", 2, 3.01, "red"), ("uptime", 99.5, 99.5, "green"),
    ("uptime", 99.5, 99.0, "yellow"), ("uptime", 99.5, 98.99, "red")])
def test_kpi_threshold_edges(kind, target, sim, expected):
    assert kpis.status(kind, target, sim) == expected


def test_spec_kpis_statuses():
    got = {c["id"]: c["status"] for c in kpis.cards()}
    assert got == {"F1": "red", "F2": "yellow", "C1": "red", "C2": "green", "O1": "green", "O2": "red"}
    assert len(kpis.cards()) == 6
