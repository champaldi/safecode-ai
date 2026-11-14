"""Optional LLM layer: final FP verdict only. OFF unless ANTHROPIC_API_KEY or OPENAI_API_KEY is set.
Anthropic wins if both are set. Model: LLM_MODEL (defaults below)."""
import json
import logging
import os
import urllib.request

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
OPENAI_URL = "https://api.openai.com/v1/chat/completions"


def provider() -> str:
    return "anthropic" if os.environ.get("ANTHROPIC_API_KEY") else "openai" if os.environ.get("OPENAI_API_KEY") else ""


def enabled() -> bool:
    return bool(provider())


def _post(url: str, headers: dict, payload: dict) -> dict:
    req = urllib.request.Request(url, json.dumps(payload).encode(), {"content-type": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def _call(prompt: str):
    """Returns (text, tokens_in, tokens_out)."""
    model = os.environ.get("LLM_MODEL")
    if provider() == "anthropic":
        r = _post(ANTHROPIC_URL, {"x-api-key": os.environ["ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01"},
                  {"model": model or "claude-haiku-5-5", "max_tokens": 150,
                   "messages": [{"role": "user", "content": prompt}]})
        u = r.get("usage", {})
        return r["content"][0]["text"], u.get("input_tokens", 0), u.get("output_tokens", 0)
    r = _post(OPENAI_URL, {"authorization": "Bearer " + os.environ["OPENAI_API_KEY"]},
              {"model": model or "gpt-4o-mini", "max_completion_tokens": 150,
               "response_format": {"type": "json_object"}, "messages": [{"role": "user", "content": prompt}]})
    u = r.get("usage", {})
    return r["choices"][0]["message"]["content"], u.get("prompt_tokens", 0), u.get("completion_tokens", 0)


def verdict(rule: str, snippet: str, hint: str) -> dict | None:
    """snippet = flagged lines +-10 only, never a whole file. Returns None on any failure (caller falls back)."""
    prompt = (f"Security rule '{rule}' flagged this Python code. Rule-based hint (why it may be a false positive): "
              f"{hint or 'none'}.\n```python\n{snippet}\n```\n"
              "Judge only the flagged line. Not a vulnerability: an SQL string with no interpolated input; "
              "md5/sha1 used for checksums or cache keys (not passwords); code in tests; a fully literal command. "
              "Keep the hint's conclusion unless the code clearly contradicts it. Is it a real vulnerability? "
              'Reply with JSON only: {"real": true|false, "reason": "<one short sentence>"}')
    last = None
    for _ in range(2):  # 1 retry
        try:
            txt, tin, tout = _call(prompt)
            d = json.loads(txt[txt.index("{"):txt.rindex("}") + 1])
            return {"real": bool(d["real"]), "reason": str(d.get("reason", "")), "tin": tin, "tout": tout}
        except Exception as e:
            last = e
    logging.getLogger("safecode").warning("LLM call failed, using rule-based result: %s", type(last).__name__)
    return None
