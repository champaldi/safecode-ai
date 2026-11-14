import argparse
import json
import logging
import os
import sys

from . import runner
from .github import GH, FakeGH


def main(argv=None):
    logging.basicConfig(level=logging.INFO, format="%(levelname)s safecode: %(message)s", stream=sys.stderr)
    e = os.environ.get
    ap = argparse.ArgumentParser(prog="action_runner")
    ap.add_argument("--dry-run", action="store_true", help="no GitHub calls; print the comments")
    ap.add_argument("--diff", help="unified diff file (required with --dry-run)")
    ap.add_argument("--root", default=".", help="checkout dir holding the PR head files")
    ap.add_argument("--state", help="dry-run: JSON file that keeps fake PR state between runs")
    ap.add_argument("--language", default=e("INPUT_LANGUAGE") or "ru")
    ap.add_argument("--fail-on", default=e("INPUT_FAIL_ON") or "high")
    ap.add_argument("--api-url", default=e("INPUT_API_URL") or "")
    ap.add_argument("--ingest-token", default=e("INPUT_INGEST_TOKEN") or "")
    ap.add_argument("--repo", default=e("GITHUB_REPOSITORY") or "demo/safecode-demo")
    ap.add_argument("--pr", type=int)
    ap.add_argument("--sha", default="")
    a = ap.parse_args(argv)
    cfg = {"language": a.language, "fail_on": a.fail_on, "api_url": a.api_url, "ingest_token": a.ingest_token}

    if a.dry_run:
        if not a.diff:
            ap.error("--dry-run needs --diff")
        gh, diff_text = FakeGH(a.state), open(a.diff, encoding="utf-8").read()
        pr, sha = a.pr or 1, a.sha or "dryrun0000001"
    else:
        ev = json.load(open(os.environ["GITHUB_EVENT_PATH"], encoding="utf-8"))["pull_request"]
        gh, diff_text = GH(a.repo, os.environ["GITHUB_TOKEN"]), None
        pr, sha = a.pr or ev["number"], a.sha or ev["head"]["sha"]

    res = runner.run(gh, a.repo, pr, sha, cfg, diff_text, a.root)
    if a.dry_run:
        gh.save()
        for title, body in gh.events:
            print(f"\n===== {title} =====\n{body}")
    return 1 if res.get("error") else 0


if __name__ == "__main__":
    sys.exit(main())
