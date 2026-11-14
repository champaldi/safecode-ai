import re

_HUNK = re.compile(r"^@@ -\d+(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


def parse_diff(text: str) -> dict[str, set[int]]:
    """Unified diff -> {path: added line numbers in the new file}."""
    out: dict[str, set[int]] = {}
    cur, ln, old_left, new_left = None, 0, 0, 0
    for line in text.splitlines():
        if old_left > 0 or new_left > 0:  # inside a hunk: '+++ x' here is a content line
            if line.startswith("+"):
                if cur:
                    out[cur].add(ln)
                ln += 1; new_left -= 1
            elif line.startswith("-"):
                old_left -= 1
            elif line.startswith("\\"):
                pass
            else:
                ln += 1; old_left -= 1; new_left -= 1
            continue
        if line.startswith("+++ "):
            p = line[4:].split("\t")[0].strip()
            cur = None if p == "/dev/null" else (p[2:] if p.startswith("b/") else p)
            if cur:
                out.setdefault(cur, set())
        elif (m := _HUNK.match(line)):
            old_left = int(m.group(1) if m.group(1) is not None else 1)
            ln = int(m.group(2))
            new_left = int(m.group(3) if m.group(3) is not None else 1)
    return out
