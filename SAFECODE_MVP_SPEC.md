# SafeCode AI: MVP Build Spec (final version)

You are Claude Code. Build the complete SafeCode AI MVP described here, end to end, in this empty folder. It is for a university entrepreneurship final defence (AITU, Astana). It must run on the first try for the team, look professional, and be honest about what is real.

## 0. How to work

- Work in the phases of section 9. After each phase: run it, run the tests, fix every error, then continue. Do not leave TODOs, placeholders or dead buttons.
- Do not ask questions unless truly blocked. Make reasonable decisions and record them in `README.md` → "Decisions".
- Before finishing, do the full acceptance check in section 10 yourself and report the result.
- Anything you cannot do yourself (creating the GitHub repo, adding secrets, deploying), write as exact copy-paste steps in `SETUP.md`. If `gh` CLI is installed and authenticated, offer the commands but do not run anything that pushes or publishes without my confirmation.

## 1. The product and the one scenario that matters

SafeCode AI is a B2B SaaS for small software teams (5-50 developers) in Kazakhstan and Central Asia. It plugs into the pull-request workflow, scans the changed code for security vulnerabilities, filters out false positives, explains each real issue in Russian, Kazakh or English, and proposes a one-click fix.

**The MVP proves one loop, live:**

1. A developer opens a pull request that adds vulnerable code.
2. The SafeCode AI GitHub Action scans only the changed lines (~30-60 s).
3. The bot posts a summary comment and inline comments with a GitHub `suggestion` fix, explanations in Russian. A planted false positive is filtered and shown as filtered with a reason.
4. The check is red. The developer clicks "Commit suggestion". The Action re-runs; the check turns green; the PR is merged.
5. The developer can vote 👍 Useful / 👎 False positive on each finding.
6. The team lead opens the web dashboard and sees REAL numbers from these PRs: scans, findings, filtered noise, accepted fixes, feedback, cost per scan.

Everything else is supporting material. If time pressure forces a choice, this loop wins.

**Out of scope (show only as PLANNED on /roadmap):** user login/auth, GitHub App/OAuth, GitLab, Slack/Jira, billing, VS Code extension, on-prem deployment, multi-tenant isolation.

## 2. Business facts (use exactly, invent nothing else)

- Problem: security audits cost $10-30k; scanners flood small teams with false positives; no Russian/Kazakh support or local data residency.
- Competitors: Snyk, GitHub Code Security. Do not state their prices. Comparison cells carry a footnote "positioning assumption, verify current vendor terms".
- Pricing (proposed, not purchasable): Free (1 repo, free scan report) · Team 125,000 KZT per team per month · Enterprise (custom, private deployment, 60-day free pilot for banks).
- 2027 plan, paying teams Jan-Dec: 0,1,1,2,3,4,5,7,9,11,13,15. Revenue KZT m Jan-Dec: 0, 0.0625, 0.125, 0.25, 0.375, 0.5, 0.625, 0.875, 1.125, 1.375, 1.625, 1.875 (total 8.8125 ≈ 8.8). Year-end paying teams 2027-2031: 15, 45, 100, 170, 250.
- Team: Torgaev Nurlybek (finance lead), Zharkem Aldiyar (technical lead / CTO), Orazova Aruzhan (growth lead), Ulzhebayev Aslan (AI product owner).
- September 2027 KPIs, SIMULATED:

| KPI | Target | Simulated | Status | Action | Owner / deadline |
|---|---|---|---|---|---|
| F1 Revenue | 1.125 KZT m | 0.875 | Red | Close stalled trials | Aruzhan / 31 Oct 2027 |
| F2 Net burn (lower is better) | ≤4.5 KZT m | 4.9 | Yellow | Cap model usage; cache fixes | Aslan / 15 Oct 2027 |
| C1 Paying teams | 9 | 7 | Red | Setup calls and first-fix checklist | Aruzhan / 31 Oct 2027 |
| C2 Monthly churn (lower is better) | ≤2% | 0% | Green | Continue monitoring | Aruzhan / monthly |
| O1 Uptime | ≥99.5% | 99.7% | Green | Continue monitoring | Aldiyar / weekly |
| O2 Activation (first merged fix ≤24h) | 40% | 30.8% (8 of 26) | Red | Fix installation blockers | Aslan / 31 Oct 2027 |

Thresholds. Revenue, teams, activation: Green ≥95% of target, Yellow 85-95%, Red <85%. Burn: Green ≤105% of ceiling, Yellow 105-115%, Red >115%. Churn: Green ≤2%, Yellow 2-3%, Red >3%. Uptime: Green ≥99.5%, Yellow 99.0-99.5%, Red <99.0%. Compute statuses in code from these rules (do not hardcode colors) and unit-test them.

## 3. Honesty rules (the course forbids fabrication)

- Every UI block carries one badge: **REAL**, **SIMULATED**, **MOCKUP** or **PLANNED**.
- Never seed fake customers, logos, testimonials or scan history. Real metrics start at zero and fill only from real scans.
- Every fix shows its source: **AI fix** or **Rule-based fix**.
- Landing page has a short "What is real in this MVP" box.

## 4. Repository layout (monorepo, one GitHub repo)

```
safecode-ai/
  action.yml                 # GitHub Action at repo root: uses: <owner>/safecode-ai@main
  safecode_core/             # shared engine, used by BOTH the Action and the web app
    scanner.py  fp_filter.py  fixes/  llm.py  i18n/  models.py  diff.py  cost.py
  rules/                     # custom Semgrep rules
  action_runner/             # entrypoint for the Action: diff, scan, comments, check, ingest
  web/                       # FastAPI web app
  demo/                      # demo target app + workflow + DEMO_SCRIPT.md
  tests/
  README.md  SETUP.md  .env.example  Dockerfile  Makefile  .replit  replit.nix
  docs/SCREENS.md  docs/AI_CONTRIBUTION.md  docs/ARCHITECTURE.md
```

Never duplicate engine logic between the Action and the web app.

## 5. safecode_core (engine)

- Python 3.11. Semgrep (`pip install semgrep`) with custom rules in `rules/` for Python and JavaScript/TypeScript: SQL injection, XSS (innerHTML/document.write), hardcoded secrets, weak hashing for passwords (md5/sha1), eval/exec, subprocess with shell=True and input, insecure random for tokens, path traversal, pickle.loads on untrusted data, TLS verification disabled. Each rule maps to a CWE and a severity.
- If Semgrep is unavailable, fall back to Bandit (Python) plus a regex ruleset and mark results with "fallback engine".
- **False-positive filter.** Heuristics first: constant-only SQL strings, code inside `test_*` functions or `tests/` paths, md5/sha1 not near password-related names, subprocess with literal list args. Each filtered finding gets a reason. If `ANTHROPIC_API_KEY` is set, the LLM gives the final verdict and the heuristic is shown as "rule hint".
- **Fix library** (`fixes/`): for every rule, a before/after transformation and explanation + "why it matters" (attacker impact, not a repeat of the explanation) in English, Russian and Kazakh. Write real Russian and real Kazakh (Cyrillic), not transliteration. The demo cases must always produce a correct fix with no API key.
- **LLM layer** (`llm.py`): Anthropic API, `ANTHROPIC_API_KEY`, model from `LLM_MODEL` (default a current Claude Haiku model). Used only for localized explanation, FP verdict and fix. Send only the finding snippet ±10 lines, never whole files. 20 s timeout, 1 retry, then rule-based fallback. Return token counts.
- **Cost** (`cost.py`): cost per scan in KZT from tokens and `LLM_PRICE_INPUT_PER_1K_KZT`, `LLM_PRICE_OUTPUT_PER_1K_KZT`; rule-based-only scans cost 0 and are counted separately.
- Fixes must be single-hunk replacements of the exact flagged line range, so they are valid GitHub `suggestion` blocks. If a correct fix needs lines outside the changed hunk, post it as a normal code block and mark "manual fix".

## 6. GitHub Action (the core of the demo)

`action.yml` (composite action, Python 3.11 setup, pip cache for speed). Inputs: `language` (ru|kk|en, default ru), `fail-on` (critical|high|medium, default high), `api-url` (optional), `ingest-token` (optional), `anthropic-api-key` (optional).

On `pull_request` (opened, synchronize, reopened):
1. Compute changed files and changed line ranges vs the base branch. Scan only those files; report only findings on changed lines.
2. Post ONE summary comment, updated in place on re-runs (find it by a hidden marker `<!-- safecode-ai-summary -->`). Contents: severity counts, filtered count with reasons inside `<details>`, noise reduction % (filtered / raw), scan time, link to the dashboard if `api-url` is set.
3. Post inline review comments on the vulnerable lines: title, severity, CWE, explanation, why it matters, a ```suggestion block with the fix, fix source badge, and feedback links "👍 Useful" / "👎 False positive" pointing to `{api-url}/feedback/{finding_id}?vote=up|down`. On re-run, do not duplicate comments for findings already commented on; mark findings that disappeared as resolved in the summary.
4. Create a check run "SafeCode AI": failure if any finding at or above `fail-on`, otherwise success, with a short summary.
5. POST scan metadata (never source code) to `{api-url}/api/ingest` with header `Authorization: Bearer {ingest-token}`: repo, PR number, head SHA, findings (rule, severity, file, line, filtered, reason, fix source), duration, tokens, cost. If the API is down or not configured, log a warning and still succeed.
6. Permissions needed: `contents: read`, `pull-requests: write`, `checks: write`. Use only the built-in `GITHUB_TOKEN`. Document that PRs from forks get a read-only token, so the demo uses branches in the same repo.

Write `action_runner` so it can also run locally against a fixture diff in dry-run mode (`python -m action_runner --dry-run --diff tests/fixtures/demo.diff`) and print the exact comment markdown. Use this for tests.

## 7. Web app (`web/`)

FastAPI + Jinja2 + Tailwind (CDN) + a little vanilla JS + Chart.js (CDN). SQLAlchemy with `DATABASE_URL` (Postgres) when set, otherwise local SQLite for dev. No user auth.

Design: dark navy background, one teal accent, Inter (UI) and JetBrains Mono (code), generous spacing, subtle borders, no stock illustrations, no emoji in UI except the feedback votes. Shared header (Overview, Free scan, Dashboard, Roadmap, Demo), language switch EN/RU/KK for the whole UI (JSON i18n files; choice kept in localStorage inside try/catch), footer with the four team names and "MVP v2, university project". Responsive down to 375 px. No console errors.

Pages:
1. **`/` Landing.** Hero ("Catch the vulnerability in the pull request, fix it in one click"), the 6-step loop from section 1 as a visual flow, a static screenshot-style render of a PR comment (badge MOCKUP if it is not live), pricing cards (PROPOSED), comparison table with footnote, "What is real in this MVP" box, CTA "Try a free scan" and "See the live demo PR" (link from env `DEMO_PR_URL`, hidden if unset).
2. **`/scan` Free scan** (top of funnel). Paste code or upload one file (.py .js .ts), max 500 lines. Language selector. Three samples: SQL injection (Python), XSS (JavaScript), hardcoded secret + weak hash (Python). Staged loading text ("Scanning…", "Filtering false positives…", "Preparing fixes…"). Delete code after the scan; keep metadata only; privacy note. Rate limit 10/min per IP.
3. **`/scan/{id}` Results.** Severity tiles, tabs "SafeCode AI view" vs "Raw scanner view" with noise reduction %, findings with before/after diff, copy-fix button, fix source badge, filtered findings toggle with reasons, printable report (`/scan/{id}/report` with print CSS).
4. **`/feedback/{finding_id}`** GET shows the finding and a confirm button; the POST records the vote (GET must not change state, link previewers would trigger it). Thank-you state.
5. **`/api/ingest`** POST, bearer token `INGEST_TOKEN`, stores PR scans and findings.
6. **`/dashboard`.** Two clearly separated parts:
   - **"MVP evidence: REAL data"**: PR scans, repos, findings per PR, filtered as FP %, suggestion acceptance (a finding counts as fixed when it disappears in a later run of the same PR and that PR has a newer head SHA), 👍/👎 counts and FP-vote rate, avg scan time, avg cost per scan in KZT, AI vs rule-based share. Table of recent PRs with links. CSV export. Empty states explain "No PR scans yet, open a PR in a repo with the Action".
   - **"Business KPIs: SIMULATED (September 2027)"**: six KPI cards with target, simulated value, deviation (absolute and %), computed status, action, owner, deadline; threshold legend with lower-is-better marked; Chart.js line chart of 2027 planned paying teams and revenue with the September simulated point marked. Values from `data/kpis.json`.
   - Admin "Reset data" button protected by `DEMO_ADMIN_TOKEN` (asks for the token, never stored in the page).
7. **`/roadmap`** PLANNED cards: GitHub App for organizations, GitLab, Slack and Jira, monthly "hours saved" report, on-prem for banks, team seats and SSO, audit log.
8. **`/demo`** Defence mode: step-by-step guide with Next/Back and arrow keys: 1 landing → 2 live PR (opens `DEMO_PR_URL`) → 3 dashboard REAL → 4 dashboard SIMULATED KPIs → 5 pricing → 6 roadmap. Each step has a one-line caption of what it proves for the business model.

## 8. Demo kit (`demo/`)

- `demo/app/`: small Flask "user directory" service, clean and passing on main, with its own requirements and a 2-test pytest suite.
- `demo/.github/workflows/safecode.yml` using the Action with `language: ru`, `fail-on: high`, and secrets `SAFECODE_API_URL`, `SAFECODE_INGEST_TOKEN`, `ANTHROPIC_API_KEY` (all optional).
- `demo/patches/`: ready-to-apply changes for the live demo:
  - `01-user-search.patch`: adds `/users/search` with an f-string SQL query (real, Critical) plus a constant SQL query and a test-only hardcoded token (both must be filtered as FP with reasons).
  - `02-avatar-preview.patch`: adds a JS snippet using innerHTML with user input (real, High) and md5 used as a cache key (filtered).
  - `03-reset-token.patch`: insecure `random` for a password-reset token (real, High) and `subprocess.run(["git","--version"])` (filtered).
- `demo/DEMO_SCRIPT.md`: exact steps and timings for the defence: create branch, apply patch, push, open PR, what appears and when, click Commit suggestion, green check, merge, open dashboard. Plus a "If something fails" section: use the prepared merged PR, the dry-run output, screenshots.
- `scripts/bootstrap_demo.sh`: copies `demo/` into a separate new repo folder ready to `git init` and push (do not push).

## 9. Phases

1. Scaffold, config, DB models, Makefile, `.env.example`, CI workflow for this repo (pytest + ruff).
2. `safecode_core`: rules, scanner with fallback, FP filter, fix library EN/RU/KK, tests.
3. LLM layer + cost, with mocked tests and timeout fallback.
4. `action_runner` + `action.yml`: diff parsing, comments, suggestion blocks, check run, ingest, dry-run mode, tests with recorded GitHub API responses (no network in tests).
5. Web app: landing, free scan, results, report, feedback, ingest.
6. Dashboard REAL + SIMULATED, roadmap, demo mode, i18n for all UI.
7. Demo kit, `DEMO_SCRIPT.md`, `SETUP.md`, docs, deploy config (`Dockerfile`, `.replit`, `replit.nix`; Replit Deployments Autoscale with Replit Postgres via `DATABASE_URL`, and Render as an alternative).

## 10. Acceptance check (do it yourself before you report done)

- `make test` passes: engine finds every planted real vulnerability in the 3 patches, filters exactly the planted false positives with reasons, produces valid single-hunk suggestions; KPI status logic including lower-is-better and threshold edges; ingest auth; feedback GET does not change state; upload and rate limits; uploaded code is deleted.
- `make dev` starts the web app; every page returns 200; no console errors; mobile width 375 px looks right; RU and KK switch the whole UI.
- Dry-run of the Action on each patch prints a summary comment and inline comments that render correctly as GitHub markdown; a second dry-run on the fixed code shows the finding resolved and a passing check.
- Works with no `ANTHROPIC_API_KEY` (rule-based) and with a key (AI), and the UI shows which one was used.
- Dashboard shows zeros and helpful empty states on a fresh DB, then real numbers after ingesting the dry-run results.
- README has: what it is, one-command run, the "Real / Simulated / Mockup / Planned" table, architecture diagram (Mermaid), data and privacy note (only snippets ±10 lines go to the LLM, code is not stored, metadata only; local data residency is PLANNED for enterprise), known limitations, changelog from prototype v1 (Replit: Semgrep wrapper, no AI fixes, no PR integration) to MVP v2, Decisions.
- `docs/SCREENS.md`: every screen in demo order, what the user does there, how it supports the business model (for report Section 10 and slides).
- `docs/AI_CONTRIBUTION.md`: table with rows per module (engine, Action, web, rules, fix texts RU/KK, docs) and columns: own work / AI-assisted / AI-generated · tool and purpose · how verified. Pre-fill tool and purpose truthfully (Claude Code generated the code); leave the verification column for the team.
- Final message to me: what was built, test results, what I must do manually (from SETUP.md) in order, and anything that did not work.
