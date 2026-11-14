import json
import logging
import re
import time
import urllib.request
from pathlib import Path

from safecode_core import cost, diff, fixes, fp_filter
from safecode_core.models import SEV_ORDER
from safecode_core.scanner import scan_source

from . import render

log = logging.getLogger("safecode")


def scan_diff(diff_text, root, lang):
    """Scan changed .py files; keep only findings touching changed lines."""
    out, sources, skipped = [], {}, []
    for path, added in diff.parse_diff(diff_text).items():
        p = Path(root) / path
        if not path.endswith(".py") or not added or not p.is_file():
            continue
        src = p.read_text(encoding="utf-8")
        try:
            fs = scan_source(path, src)
        except SyntaxError:
            skipped.append(path)
            continue
        sources[path] = src.replace("\r\n", "\n")
        for f in fs:
            rng = set(range(f.line, f.end_line + 1))
            if not rng & added:
                continue
            if f.fix and not rng <= added:
                f.fix.suggestion_ok = False  # fix would touch lines outside the PR diff -> manual
            out.append(f)
    return out, fp_filter.apply(out, sources, lang), skipped


def post_ingest(url, token, payload):
    req = urllib.request.Request(url.rstrip("/") + "/api/ingest", json.dumps(payload).encode(), method="POST",
                                 headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=10).read()


def _comments(gh, pr, sha, findings, resolved_new, state_prev, cfg):
    lang = cfg["language"]
    existing = {}
    for c in gh.list_review_comments(pr):
        if "safecode-finding:" in c["body"]:
            existing[c["body"].split("safecode-finding:")[1].split(" ")[0]] = c["id"]
    for f in findings:
        if f.filtered or f.id in existing:
            continue
        try:
            gh.create_review_comment(pr, sha, f.file, render.inline(f, lang), f.end_line, f.line)
        except Exception as e:  # e.g. line not in diff; the summary still lists the finding
            log.warning("inline comment failed for %s:%s: %s", f.file, f.line, e)
    for fid in resolved_new:
        if fid in existing:
            try:
                gh.reply(pr, existing[fid], f"Resolved in {sha[:7]}")
            except Exception as e:
                log.warning("resolve reply failed: %s", e)


def run(gh, repo, pr, sha, cfg, diff_text=None, root="."):
    """cfg: language, fail_on, api_url, ingest_token. Returns a result dict."""
    t0 = time.time()
    try:
        if diff_text is None:
            diff_text = gh.get_diff(pr)
        findings, usage, skipped = scan_diff(diff_text, root, cfg["language"])
    except Exception as e:  # never a silent success
        log.error("scan failed: %r", e)
        gh.create_check(sha, "failure", "SafeCode AI: scan failed",
                        f"The scan engine failed, so this PR was **not** checked.\n\n```\n{type(e).__name__}: {e}\n```")
        return {"conclusion": "failure", "error": str(e)}
    dur = time.time() - t0
    real = [f for f in findings if not f.filtered]
    blocking = [f for f in real if SEV_ORDER[f.severity] >= SEV_ORDER[cfg["fail_on"]]]
    lang = cfg["language"]

    try:
        prior = next((c for c in gh.list_issue_comments(pr) if render.MARK in c["body"]), None)
        prev = render.decode_state(prior["body"] if prior else "")
        cur = {f.id: [fixes.texts(f.rule, lang)[0], f.file, f.line] for f in real}
        newly = {k: v for k, v in prev["open"].items() if k not in cur}
        resolved = {k: v for k, v in {**prev["resolved"], **newly}.items() if k not in cur}
        body = render.summary(findings, resolved, {"open": cur, "resolved": resolved}, cfg, dur, usage, skipped, len(blocking))
        if prior:
            gh.update_issue_comment(prior["id"], body)
        else:
            gh.create_issue_comment(pr, body)
        _comments(gh, pr, sha, findings, list(newly), prev, cfg)
    except Exception as e:
        log.warning("could not post comments (check still reflects the scan): %s", e)
        body = render.headline(len(findings), len(real), len(findings) - len(real))

    conclusion = "failure" if blocking else "success"
    title = f"SafeCode AI: {len(blocking)} blocking finding(s)" if blocking else "SafeCode AI: passed"
    gh.create_check(sha, conclusion, title, re.sub(r"<!--.*?-->\n?", "", body, flags=re.S))

    tin, tout = usage["tin"], usage["tout"]
    payload = {"repo": repo, "pr": pr, "sha": sha, "conclusion": conclusion, "duration_s": round(dur, 3),
               "tokens_in": tin, "tokens_out": tout, "cost_kzt": cost.cost_kzt(tin, tout), "ai": usage["ai"],
               "findings": [f.ingest() for f in findings]}
    if not cfg.get("api_url"):
        log.warning("api-url not set: skipping ingest")
    else:
        try:
            post_ingest(cfg["api_url"], cfg.get("ingest_token", ""), payload)
        except Exception as e:
            log.warning("ingest failed (check unaffected): %s", e)
    return {"conclusion": conclusion, "findings": findings, "payload": payload}
