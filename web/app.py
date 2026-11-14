import hmac
import os
import sqlite3
import time
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import kpis

app = FastAPI(title="SafeCode AI")
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")
SCHEMA = """
CREATE TABLE IF NOT EXISTS scans (id INTEGER PRIMARY KEY, repo TEXT, pr INTEGER, sha TEXT, ts REAL,
  duration_s REAL, tokens_in INTEGER, tokens_out INTEGER, cost_kzt REAL, ai INTEGER,
  raw INTEGER, real INTEGER, filtered INTEGER, conclusion TEXT);
CREATE TABLE IF NOT EXISTS findings (id INTEGER PRIMARY KEY, scan_id INTEGER, repo TEXT, pr INTEGER, fid TEXT,
  rule TEXT, severity TEXT, file TEXT, line INTEGER, filtered INTEGER, reason TEXT, fix_source TEXT, fixed_at REAL);
"""


def db():
    path = os.environ.get("SAFECODE_DB", "data/safecode.db")
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(path)
    c.row_factory = sqlite3.Row
    c.executescript(SCHEMA)
    return c


class FindingIn(BaseModel):
    id: str
    rule: str
    severity: str
    file: str
    line: int
    filtered: bool
    reason: str | None = ""
    fix_source: str | None = None


class IngestIn(BaseModel):
    repo: str
    pr: int
    sha: str
    conclusion: str
    duration_s: float
    tokens_in: int = 0
    tokens_out: int = 0
    cost_kzt: float = 0
    ai: bool = False
    findings: list[FindingIn]


@app.post("/api/ingest")
def ingest(body: IngestIn, authorization: str = Header(default="")):
    token = os.environ.get("INGEST_TOKEN", "")
    if not token or not hmac.compare_digest(authorization, f"Bearer {token}"):
        raise HTTPException(401, "bad or missing bearer token")
    c = db()
    prev = c.execute("SELECT id FROM scans WHERE repo=? AND pr=? AND sha!=? ORDER BY id DESC LIMIT 1",
                     (body.repo, body.pr, body.sha)).fetchone()
    real = [f for f in body.findings if not f.filtered]
    cur = c.execute("INSERT INTO scans (repo,pr,sha,ts,duration_s,tokens_in,tokens_out,cost_kzt,ai,raw,real,filtered,conclusion)"
                    " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (body.repo, body.pr, body.sha, time.time(), body.duration_s, body.tokens_in, body.tokens_out,
                     body.cost_kzt, int(body.ai), len(body.findings), len(real), len(body.findings) - len(real), body.conclusion))
    for f in body.findings:
        c.execute("INSERT INTO findings (scan_id,repo,pr,fid,rule,severity,file,line,filtered,reason,fix_source)"
                  " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                  (cur.lastrowid, body.repo, body.pr, f.id, f.rule, f.severity, f.file, f.line, int(f.filtered),
                   f.reason, f.fix_source))
    fixed = 0
    if prev:  # a real finding that vanished in a newer head SHA of the same PR counts as an accepted fix
        now = {f.id for f in real}
        for r in c.execute("SELECT id, fid FROM findings WHERE scan_id=? AND filtered=0 AND fixed_at IS NULL", (prev["id"],)).fetchall():
            if r["fid"] not in now:
                c.execute("UPDATE findings SET fixed_at=? WHERE id=?", (time.time(), r["id"]))
                fixed += 1
    c.commit()
    return {"ok": True, "scan_id": cur.lastrowid, "fixed": fixed}


@app.get("/api/stats")
def stats():
    c = db()
    one = lambda q: c.execute(q).fetchone()[0]  # noqa: E731
    n = one("SELECT COUNT(*) FROM scans")
    first = "id IN (SELECT MIN(id) FROM scans GROUP BY repo, pr)"
    raw, real, filt = (c.execute(f"SELECT COALESCE(SUM(raw),0), COALESCE(SUM(real),0), COALESCE(SUM(filtered),0) FROM scans WHERE {first}").fetchone())
    recent = [dict(r) | {"url": f"https://github.com/{r['repo']}/pull/{r['pr']}"} for r in
              c.execute("SELECT repo, pr, sha, ts, raw, real, filtered, conclusion FROM scans ORDER BY id DESC LIMIT 10")]
    return {
        "now": time.time(),
        "real": {
            "pr_scans": n,
            "prs": one("SELECT COUNT(*) FROM (SELECT 1 FROM scans GROUP BY repo, pr)"),
            "raw": raw, "findings": real, "filtered": filt,
            "filtered_pct": round(100 * filt / raw) if raw else 0,
            "accepted_fixes": one("SELECT COUNT(*) FROM findings WHERE fixed_at IS NOT NULL"),
            "avg_scan_s": round(one("SELECT COALESCE(AVG(duration_s),0) FROM scans"), 2),
            "avg_cost_kzt": round(one("SELECT COALESCE(AVG(cost_kzt),0) FROM scans"), 4),
            "ai_scans": one("SELECT COALESCE(SUM(ai),0) FROM scans"),
            "recent": recent,
        },
        "simulated": kpis.cards(),
    }


@app.get("/dashboard")
def dashboard():
    return FileResponse(Path(__file__).parent / "dashboard.html")


@app.get("/")
def index():
    return FileResponse(Path(__file__).parent / "landing.html")


@app.get("/api/config")
def config():
    return {"demo_pr_url": os.environ.get("DEMO_PR_URL", "")}


@app.get("/healthz")
def healthz():
    return {"ok": True}
