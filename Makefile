.PHONY: test dev
test:
	python -m pytest -q
dev:
	INGEST_TOKEN=dev-token python -m uvicorn web.app:app --reload --port 8000
dryrun:
	python scripts/dryrun.py
