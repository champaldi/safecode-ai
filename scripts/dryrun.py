"""Offline rehearsal of the whole demo loop: patch 01 -> scan -> 'Commit suggestion' -> re-scan.

  python scripts/dryrun.py [--api-url http://localhost:8000 --ingest-token dev-token] [--language ru|en]

Prints the exact PR comments and check runs. With --api-url it also ingests both scans, so the dashboard fills.
Saves the output to demo/backup/dryrun-01.md (the backup plan in DEMO_SCRIPT.md).
"""
import argparse
import contextlib
import io
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from action_runner import __main__ as cli  # noqa: E402
from action_runner import runner  # noqa: E402
from tests.conftest import apply_fixes, git  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--api-url", default="")
    ap.add_argument("--ingest-token", default="")
    ap.add_argument("--language", default="ru")
    ap.add_argument("--pr", default="1")
    a = ap.parse_args()
    tmp = Path(tempfile.mkdtemp())
    shutil.copytree(ROOT / "demo/app", tmp / "app")
    git(tmp, "init", "-q"); git(tmp, "add", "-A"); git(tmp, "commit", "-qm", "base")
    git(tmp, "apply", "-p1", str(ROOT / "demo/patches/01-user-search.patch"))
    git(tmp, "add", "-A", "-N")
    (tmp / "pr.diff").write_text(git(tmp, "diff"), encoding="utf-8")
    common = ["--dry-run", "--diff", str(tmp / "pr.diff"), "--root", str(tmp), "--state", str(tmp / "state.json"),
              "--language", a.language, "--api-url", a.api_url, "--ingest-token", a.ingest_token, "--pr", a.pr]
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        print("# Run 1: PR opened with patch 01 (head sha dryrun-sha-1)")
        cli.main(common + ["--sha", "dryrun-sha-1"])
        # what clicking "Commit suggestion" does: apply every valid suggestion, then diff again
        fs, _, _ = runner.scan_diff((tmp / "pr.diff").read_text(encoding="utf-8"), tmp, a.language)
        apply_fixes(tmp, fs)
        git(tmp, "add", "-A", "-N")
        (tmp / "pr.diff").write_text(git(tmp, "diff"), encoding="utf-8")
        print("\n\n# Run 2: after Commit suggestion (head sha dryrun-sha-2)")
        cli.main(common + ["--sha", "dryrun-sha-2"])
    text = out.getvalue()
    print(text)
    dest = ROOT / "demo/backup"
    dest.mkdir(exist_ok=True)
    (dest / "dryrun-01.md").write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
