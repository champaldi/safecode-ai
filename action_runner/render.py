import json
import re

from safecode_core import fixes

MARK = "<!-- safecode-ai-summary -->"
FMARK = "<!-- safecode-finding:{} -->"


def pct(raw, filtered):
    return round(100 * filtered / raw) if raw else 0


def headline(raw, real, filtered):
    return f"{raw} raw → {real} real, {filtered} filtered ({pct(raw, filtered)}% noise removed)"


def encode_state(state):
    return "<!-- safecode-ai-state:" + json.dumps(state).replace("-", "\\u002d") + " -->"


def decode_state(body):
    m = re.search(r"<!-- safecode-ai-state:(\{.*?\}) -->", body or "", re.S)
    try:
        return json.loads(m.group(1)) if m else {"open": {}, "resolved": {}}
    except ValueError:
        return {"open": {}, "resolved": {}}


def summary(findings, resolved, state, cfg, dur, usage, skipped, blocking):
    lang = cfg["language"]
    L = fixes.LABELS.get(lang, fixes.LABELS["en"])
    real = [f for f in findings if not f.filtered]
    filt = [f for f in findings if f.filtered]
    o = [MARK, encode_state(state), f"### {headline(len(findings), len(real), len(filt))}", ""]
    o.append(f"**SafeCode AI: {L['fail'] if blocking else L['pass']}** — "
             f"{blocking} finding(s) at or above `{cfg['fail_on']}`" if blocking else f"**SafeCode AI: {L['pass']}**")
    o.append("")
    if real:
        for f in real:
            t = fixes.texts(f.rule, lang)[0]
            o.append(f"- `{f.file}:{f.line}` **{t}** (`{f.severity}`, {f.cwe})")
    else:
        o.append(L["none"])
    if resolved:
        o += ["", f"**{L['resolved']}:**"]
        o += [f"- ~~**{t}**~~ `{fl}`" for t, fl, *_ in resolved.values()]
    if filt:
        o += ["", f"<details><summary>{L['filtered']} ({len(filt)})</summary>", ""]
        o += [f"- `{f.file}:{f.line}` {fixes.texts(f.rule, lang)[0]} — {f.reason}" for f in filt]
        o += ["", "</details>"]
    if skipped:
        o += ["", f"{L['skipped']}: " + ", ".join(f"`{s}`" for s in skipped)]
    eng = L["engine_ai"] if usage["ai"] else L["engine"]
    foot = f"{L['scan']} {dur:.1f}s · {eng}"
    if cfg.get("api_url"):
        foot += f" · [{L['dash']}]({cfg['api_url'].rstrip('/')}/dashboard)"
    return "\n".join(o + ["", f"<sub>{foot}</sub>"])


def inline(f, lang):
    L = fixes.LABELS.get(lang, fixes.LABELS["en"])
    title, explain, why = fixes.texts(f.rule, lang)
    o = [FMARK.format(f.id), f"**{title}** · `{f.severity}` · {f.cwe}", "", explain, "", f"**{L['why']}:** {why}", ""]
    if f.fix and f.fix.suggestion_ok:
        o += ["```suggestion", f.fix.after, "```"]
    elif f.fix:
        o += [f"**{L['manual']}**" + (f" ({f.fix.note})" if f.fix.note else "") + ":", "```python", f.fix.after, "```"]
    else:
        o.append(L["nofix"])
    if f.fix:
        o += ["", f"<sub>{f.fix.source}</sub>"]
    return "\n".join(o)
