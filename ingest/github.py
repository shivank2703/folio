"""Talk to GitHub's REST API: upload a release asset, commit files to main.

Adding a company from the deployed app has to leave its result somewhere
that survives the container: Community Cloud's disk is gone after the next
restart or sleep. So the app does what a maintainer does by hand after
`ingest.add` (ingest/publish.py, then a commit), through the API, because the
gh CLI is not installed on the host.

The token comes from GITHUB_TOKEN (Streamlit secrets on the deployed app): a
fine-grained token limited to this one repository with "Contents: read and
write", which covers both commits and release assets. Locally, with no token
set, the gh CLI's own login is borrowed (`gh auth token`). Standard library
only: two endpoints do not justify a dependency.
"""

from __future__ import annotations

import base64
import json
import os
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://api.github.com"
REPO = os.environ.get("FOLIO_REPO", "shivank2703/folio")


class GitHubError(Exception):
    pass


def token() -> str:
    """GITHUB_TOKEN if set, else the local gh login; never printed or logged."""
    found = os.environ.get("GITHUB_TOKEN", "").strip()
    if not found:
        try:
            found = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, check=True).stdout.strip()
        except (OSError, subprocess.CalledProcessError):
            found = ""
    if not found:
        raise GitHubError("no GitHub token: set GITHUB_TOKEN (Streamlit secrets) or log in with gh")
    return found


def call(method: str, url: str, body: dict | bytes | None = None, content_type: str = "application/json"):
    """One authenticated API request; returns the decoded JSON reply, or raises GitHubError."""
    data = json.dumps(body).encode() if isinstance(body, dict) else body
    request = urllib.request.Request(url if url.startswith("http") else API + url, data=data, method=method, headers={
        "Authorization": f"Bearer {token()}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "Folio",
        **({"Content-Type": content_type} if data is not None else {}),
    })
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            raw = response.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as error:
        # The message names the endpoint and GitHub's reason, never the token.
        raise GitHubError(f"{method} {url.split('?')[0]}: {error.code} {error.read()[:300].decode(errors='replace')}") from None


def ensure_release(tag: str, title: str, notes: str) -> dict:
    """The release for this tag, created as a pre-release if it does not exist yet."""
    try:
        return call("GET", f"/repos/{REPO}/releases/tags/{tag}")
    except GitHubError as error:
        if " 404 " not in str(error):
            raise
    return call("POST", f"/repos/{REPO}/releases",
                {"tag_name": tag, "name": title, "body": notes, "prerelease": True})


def upload_asset(release: dict, path: Path) -> str:
    """Attach a file to a release; return its public download URL."""
    upload = release["upload_url"].split("{")[0] + "?" + urllib.parse.urlencode({"name": path.name})
    asset = call("POST", upload, path.read_bytes(), content_type="application/gzip")
    return asset["browser_download_url"]


def commit_files(files: dict[str, str], message: str, branch: str = "main") -> str:
    """Commit several text files to a branch in one commit; return the commit's SHA.

    Built from the Git Data API (one tree, one commit, then move the branch)
    so a company's four record files land together or not at all. The branch
    is moved without force: if someone pushed in between, this fails rather
    than overwriting their commit.
    """
    head = call("GET", f"/repos/{REPO}/git/ref/heads/{branch}")["object"]["sha"]
    base_tree = call("GET", f"/repos/{REPO}/git/commits/{head}")["tree"]["sha"]
    tree = call("POST", f"/repos/{REPO}/git/trees", {
        "base_tree": base_tree,
        "tree": [{"path": path, "mode": "100644", "type": "blob",
                  "content": text} for path, text in files.items()],
    })["sha"]
    commit = call("POST", f"/repos/{REPO}/git/commits", {"message": message, "tree": tree, "parents": [head]})["sha"]
    call("PATCH", f"/repos/{REPO}/git/refs/heads/{branch}", {"sha": commit, "force": False})
    return commit


def file_text(path: str, ref: str = "main") -> str:
    """A file's current text on GitHub, to check the app's copy is not stale before overwriting it."""
    found = call("GET", f"/repos/{REPO}/contents/{urllib.parse.quote(path)}?ref={ref}")
    return base64.b64decode(found["content"]).decode("utf-8")
