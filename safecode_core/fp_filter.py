from . import fixes, llm


def heuristic(f):
    c = f.ctx
    if c.get("in_test"):
        return "test"
    if f.rule == "sql-injection" and c.get("constant_sql"):
        return "const_sql"
    if f.rule == "weak-hash" and not c.get("password_ctx"):
        return "hash_nonpw"
    if f.rule == "insecure-random" and not c.get("sec_ctx"):
        return "random_nonsec"
    if f.rule == "shell-injection" and c.get("literal_cmd"):
        return "literal_cmd"
    return ""


def apply(findings, sources, lang="en"):
    """Mutates findings. Returns {"tin","tout","ai"}. With ANTHROPIC_API_KEY the LLM verdict is final
    and the heuristic becomes the 'rule hint'; on LLM failure the heuristic stands."""
    tin = tout = 0
    use_llm = llm.enabled()
    for f in findings:
        key = heuristic(f)
        f.filtered, f.reason_key = bool(key), key
        f.reason = fixes.reason_text(key, lang) if key else ""
        if not use_llm:
            continue
        lines = sources[f.file].split("\n")
        snip = "\n".join(lines[max(0, f.line - 11):f.end_line + 10])
        v = llm.verdict(f.rule, snip, f.reason)
        if v:
            tin += v["tin"]
            tout += v["tout"]
            f.ai_verdict, f.filtered = True, not v["real"]
            f.reason_key, f.reason = "", (v["reason"] if not v["real"] else "")
    return {"tin": tin, "tout": tout, "ai": any(f.ai_verdict for f in findings)}
