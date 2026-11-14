import json
import os
import urllib.request


class GH:
    """Minimal GitHub REST client (stdlib only, uses the built-in GITHUB_TOKEN)."""

    def __init__(self, repo, token, api=None):
        self.repo, self.token = repo, token
        self.api = (api or os.environ.get("GITHUB_API_URL") or "https://api.github.com").rstrip("/")

    def _req(self, method, path, body=None, accept="application/vnd.github+json"):
        req = urllib.request.Request(
            f"{self.api}/repos/{self.repo}{path}", None if body is None else json.dumps(body).encode(), method=method,
            headers={"Authorization": f"Bearer {self.token}", "Accept": accept, "X-GitHub-Api-Version": "2022-11-28",
                     "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = r.read().decode()
            return data if accept.endswith("diff") else (json.loads(data) if data else None)

    def _paged(self, path):
        out, page = [], 1
        while True:
            chunk = self._req("GET", f"{path}?per_page=100&page={page}")
            out += chunk
            if len(chunk) < 100:
                return out
            page += 1

    def get_diff(self, pr):
        return self._req("GET", f"/pulls/{pr}", accept="application/vnd.github.v3.diff")

    def list_issue_comments(self, pr):
        return self._paged(f"/issues/{pr}/comments")

    def create_issue_comment(self, pr, body):
        return self._req("POST", f"/issues/{pr}/comments", {"body": body})

    def update_issue_comment(self, cid, body):
        return self._req("PATCH", f"/issues/comments/{cid}", {"body": body})

    def list_review_comments(self, pr):
        return self._paged(f"/pulls/{pr}/comments")

    def create_review_comment(self, pr, sha, path, body, line, start_line=None):
        d = {"body": body, "commit_id": sha, "path": path, "line": line, "side": "RIGHT"}
        if start_line and start_line != line:
            d.update(start_line=start_line, start_side="RIGHT")
        return self._req("POST", f"/pulls/{pr}/comments", d)

    def reply(self, pr, cid, body):
        return self._req("POST", f"/pulls/{pr}/comments/{cid}/replies", {"body": body})

    def create_check(self, sha, conclusion, title, summary):
        return self._req("POST", "/check-runs", {
            "name": "SafeCode AI", "head_sha": sha, "status": "completed", "conclusion": conclusion,
            "output": {"title": title, "summary": summary[:65000]}})


class FakeGH:
    """In-memory GitHub for --dry-run and tests. Optional JSON persistence so a 2nd run sees the 1st."""

    def __init__(self, state_path=None):
        self.path = state_path
        self.s = {"n": 0, "issue": [], "review": [], "checks": []}
        if state_path and os.path.exists(state_path):
            self.s = json.load(open(state_path, encoding="utf-8"))
        self.events = []  # what THIS run did, for printing

    def _id(self):
        self.s["n"] += 1
        return self.s["n"]

    def save(self):
        if self.path:
            json.dump(self.s, open(self.path, "w", encoding="utf-8"), ensure_ascii=False)

    def get_diff(self, pr):
        raise RuntimeError("dry-run needs --diff")

    def list_issue_comments(self, pr):
        return list(self.s["issue"])

    def create_issue_comment(self, pr, body):
        c = {"id": self._id(), "body": body}
        self.s["issue"].append(c)
        self.events.append(("summary comment (created)", body))
        return c

    def update_issue_comment(self, cid, body):
        for c in self.s["issue"]:
            if c["id"] == cid:
                c["body"] = body
        self.events.append(("summary comment (updated in place)", body))

    def list_review_comments(self, pr):
        return list(self.s["review"])

    def create_review_comment(self, pr, sha, path, body, line, start_line=None):
        c = {"id": self._id(), "path": path, "line": line, "body": body}
        self.s["review"].append(c)
        self.events.append((f"inline comment {path}:{start_line or line}-{line}", body))
        return c

    def reply(self, pr, cid, body):
        self.events.append((f"reply to inline comment {cid}", body))

    def create_check(self, sha, conclusion, title, summary):
        self.s["checks"].append({"conclusion": conclusion, "title": title})
        self.events.append((f"check run SafeCode AI: {conclusion.upper()}", f"{title}\n\n{summary}"))
