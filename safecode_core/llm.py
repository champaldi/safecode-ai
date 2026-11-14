"""Optional LLM layer: final FP verdict only. OFF unless ANTHROPIC_API_KEY is set."""
import json
import os
import urllib.request

API = "https://api.anthropic.com/v1/messages"


def enabled() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def _post(payload: dict) -> dict:
    req = urllib.request.Request(API, json.dumps(payload).encode(), {
        "x-api-key": os.environ["ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01",
        "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def verdict(rule: str, snippet: str, hint: str) -> dict | None:
    """snippet = flagged lines +-10 only, never a whole file. Returns None on any failure (caller falls back)."""
    prompt = (f"Security rule '{rule}' flagged this Python code. Rule-based hint: {hint or 'none'}.\n"
              f"```python\n{snippet}\n```\nIs it a real vulnerability? "
              'Reply with JSON only: {"real": true|false, "reason": "<one short sentence>"}')
    payload = {"model": os.environ.get("LLM_MODEL", "claude-haiku-5-5"), "max_tokens": 150,
               "messages": [{"role": "user", "content": prompt}]}
    for _ in range(2):  # 1 retry
        try:
            r = _post(payload)
            txt = r["content"][0]["text"]
            d = json.loads(txt[txt.index("{"):txt.rindex("}") + 1])
            u = r.get("usage", {})
            return {"real": bool(d["real"]), "reason": str(d.get("reason", "")),
                    "tin": u.get("input_tokens", 0), "tout": u.get("output_tokens", 0)}
        except Exception:
            continue
    return None
