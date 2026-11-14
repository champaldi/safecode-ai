# SETUP: exact steps

Nothing here has been run for you: no repo created, nothing pushed. Replace `YOU` with your GitHub username.

## 1. Local check (5 min)

```bash
pip install -r requirements.txt
python -m pytest -q
python scripts/dryrun.py
```
Expected: `32 passed`, and the dry-run prints `5 raw → 2 real, 3 filtered (60% noise removed)` then `3 raw → 0 real, 3 filtered (100% noise removed)`.

## 2. Push the engine repo

```bash
git init -b main
git add -A
git commit -m "SafeCode AI MVP"
gh repo create YOU/safecode-ai --public --source . --push
```
Keep it public. If it is private, go to Settings → Actions → General → Access and allow other repositories of yours to use it, otherwise the demo repo cannot load the Action.

## 3. Run the dashboard so GitHub can reach it

GitHub runners need a public URL. Easiest for the defence: run it on your laptop behind a tunnel.

```bash
INGEST_TOKEN=pick-a-long-random-string python -m uvicorn web.app:app --port 8765
```
In a second terminal (install `cloudflared` first, https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/):
```bash
cloudflared tunnel --url http://localhost:8765
```
Copy the printed `https://….trycloudflare.com` URL. The URL changes every time you restart the tunnel, so update the secret in step 5 if you do.

Alternative: deploy the `Dockerfile` on Render (Web Service, set `INGEST_TOKEN`). Its free disk is erased on restart, so data resets; use a persistent disk mounted at `/data` if you want it to stay.

## 4. Create the demo repo

```bash
bash scripts/bootstrap_demo.sh ../safecode-demo
cd ../safecode-demo
```
Edit `.github/workflows/safecode.yml`: replace `OWNER` with `YOU`. Then:
```bash
git init -b main
git add -A
git commit -m "demo app"
gh repo create YOU/safecode-demo --public --source . --push
```

## 5. Secrets (demo repo → Settings → Secrets and variables → Actions)

```bash
gh secret set SAFECODE_API_URL --repo YOU/safecode-demo --body "https://YOUR-TUNNEL-URL"
gh secret set SAFECODE_INGEST_TOKEN --repo YOU/safecode-demo --body "pick-a-long-random-string"
```
The token must equal the `INGEST_TOKEN` you started the dashboard with. `ANTHROPIC_API_KEY` is optional; skip it and the demo runs rule-based.

## 6. Branch protection (so the red check blocks the merge)

Demo repo → Settings → Branches → add a rule for `main` → require status check **SafeCode AI**. (The check appears in the list only after the first run.)

## 7. Rehearse the whole loop once (do this before the defence)

```bash
git checkout -b feature/user-search
git apply patches/01-user-search.patch
git add -A && git commit -m "Add user search" && git push -u origin feature/user-search
gh pr create --fill
```
Wait about a minute. Expect: summary comment `5 raw → 2 real, 3 filtered (60% noise removed)`, two inline suggestions, red check **SafeCode AI**. Click "Add suggestion to batch" on both, then "Commit suggestions". The workflow re-runs; the comment updates in place with the two findings struck through, and the check turns green. Open `/dashboard`: 1+ PR scan, 2 real findings, 60% filtered, 2 accepted fixes.

If something is wrong: the Actions run log has the `safecode:` warnings (ingest failure, inline-comment failure). Fork PRs get a read-only token and cannot comment, so always use branches in the same repo.

To reset the numbers before the real defence, stop the dashboard and delete `data/safecode.db`.
