import shutil
import subprocess
from pathlib import Path

import pytest

DEMO = Path(__file__).resolve().parent.parent / "demo"


def git(cwd, *args):
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=cwd, check=True,
                          capture_output=True, text=True, encoding="utf-8").stdout


def apply_fixes(root, findings):
    """What 'Commit suggestion' does: replace the flagged line range with fix.after."""
    by_file = {}
    for f in findings:
        if not f.filtered and f.fix and f.fix.suggestion_ok:
            by_file.setdefault(f.file, []).append(f)
    for path, fs in by_file.items():
        p = Path(root) / path
        lines = p.read_text(encoding="utf-8").split("\n")
        for f in sorted(fs, key=lambda f: -f.line):
            lines[f.line - 1:f.end_line] = f.fix.after.split("\n")
        p.write_text("\n".join(lines), encoding="utf-8", newline="\n")


@pytest.fixture
def pr(tmp_path):
    """A git repo = demo base + patch 01 applied (working tree). pr.diff() -> diff vs base."""
    shutil.copytree(DEMO / "app", tmp_path / "app")
    git(tmp_path, "init", "-q")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-qm", "base")
    git(tmp_path, "apply", "-p1", str(DEMO / "patches/01-user-search.patch"))

    class PR:
        root = tmp_path

        @staticmethod
        def diff():
            git(tmp_path, "add", "-A", "-N")
            return git(tmp_path, "diff")

    return PR
