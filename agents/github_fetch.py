"""Read a public GitHub repo's source files, safely.

The server makes the web requests here, so this is the classic place for SSRF
(tricking a server into fetching a URL the attacker chooses). The defence is
an allowlist: the only input accepted is an `owner/repo` name that matches
GitHub's own naming rules, and the only hosts ever contacted are api.github.com
and raw.githubusercontent.com. Redirects are not followed.

Size limits keep one request from pulling a huge repo: at most MAX_FILES files,
MAX_FILE_BYTES each, MAX_TOTAL_CHARS in total, text files only.
"""

import os
import re
import threading
import time
from urllib.parse import quote

import httpx

API = "https://api.github.com"
RAW = "https://raw.githubusercontent.com"
TIMEOUT_SECONDS = 15
MAX_FILES = 40
MAX_FILE_BYTES = 30_000
MAX_TOTAL_CHARS = 60_000
MAX_CHARS_PER_FILE = 12_000  # so one big file (a long page, a data dump) can't use up the budget
CACHE_SECONDS = 600  # one dashboard run asks once per model; fetch the repo only once

REPO_NAME = re.compile(r"^(?P<owner>[A-Za-z0-9](?:[A-Za-z0-9-]{0,38}))/(?P<repo>[A-Za-z0-9._-]{1,100})$")
GITHUB_URL = re.compile(r"^(?:https?://)?(?:www\.)?github\.com/([^/\s]+/[^/\s#?]+?)(?:\.git)?/?(?:[#?].*)?$")

TEXT_EXTENSIONS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".go", ".rs", ".java", ".kt", ".swift",
    ".c", ".h", ".cpp", ".hpp", ".cs", ".rb", ".php", ".sh", ".sql", ".html", ".css", ".vue",
    ".svelte", ".md", ".toml", ".yaml", ".yml", ".json", ".ini", ".cfg", ".txt", ".dockerfile",
}
TEXT_NAMES = {"Dockerfile", "Makefile", "Procfile", "README", "requirements.txt"}
SKIP_DIRS = {"node_modules", ".git", "dist", "build", ".venv", "venv", "__pycache__", "vendor",
             ".next", "coverage", "target", ".idea", ".vscode"}
SKIP_FILES = {"package-lock.json", "yarn.lock", "pnpm-lock.yaml", "uv.lock", "poetry.lock", "Cargo.lock"}
SECRET_FILES = re.compile(r"(^|/)(\.env(\..*)?|.*\.pem|.*\.key|id_rsa.*|credentials.*|secrets?\..*)$", re.I)

_cache: dict[str, tuple[float, list[tuple[str, str]]]] = {}
_lock = threading.Lock()


class FetchError(Exception):
    """Plain-English reason the repo couldn't be read."""


def parse_repo(text: str) -> str:
    """Accept 'owner/repo' or a github.com URL; return 'owner/repo' or raise."""
    text = text.strip()
    url = GITHUB_URL.match(text)
    if url:
        text = url.group(1)
    m = REPO_NAME.match(text)
    if not m or m.group("repo") in {".", ".."}:
        raise FetchError("Use a public GitHub repo as owner/repo or https://github.com/owner/repo")
    return f"{m.group('owner')}/{m.group('repo')}"


def _wanted(path: str, size: int) -> bool:
    parts = path.split("/")
    name = parts[-1]
    if any(p in SKIP_DIRS for p in parts[:-1]) or name in SKIP_FILES or SECRET_FILES.search(path):
        return False
    if size > MAX_FILE_BYTES:
        return False
    ext = os.path.splitext(name)[1].lower()
    return ext in TEXT_EXTENSIONS or name in TEXT_NAMES


CODE_EXTENSIONS = {".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".go", ".rs", ".java", ".kt",
                   ".swift", ".c", ".h", ".cpp", ".hpp", ".cs", ".rb", ".php", ".sh", ".sql", ".vue", ".svelte"}
ENTRY_NAMES = {"main.py", "app.py", "server.py", "routes.py", "api.py", "index.js", "index.ts",
               "server.js", "server.ts", "app.js", "app.ts", "main.go", "main.rs"}
CONFIG_NAMES = {"pyproject.toml", "package.json", "dockerfile", "requirements.txt", "railpack.json",
                "railway.json", "docker-compose.yml", "procfile", "makefile"}


def _rank(path: str) -> tuple[int, int, str]:
    """Read the most telling files first, so the size budget goes on what explains the project:
    README, configs, entry points, other code, then pages, docs and tests last."""
    lower = path.lower()
    name = lower.rsplit("/", 1)[-1]
    ext = os.path.splitext(name)[1]
    is_test = "/test" in f"/{lower}" or name.startswith("test_") or ".test." in name or ".spec." in name
    if is_test:
        group = 6
    elif name.startswith("readme") and "/" not in path:
        group = 0
    elif name in CONFIG_NAMES:
        group = 1
    elif name in ENTRY_NAMES:
        group = 2
    elif ext in CODE_EXTENSIONS:
        group = 3
    elif ext in {".html", ".css"}:
        group = 4
    else:
        group = 5  # docs, data, other text
    return (group, path.count("/"), path)


def _headers() -> dict[str, str]:
    h = {"Accept": "application/vnd.github+json", "User-Agent": "ai-agent-workflow"}
    token = os.environ.get("GITHUB_TOKEN")  # optional: higher rate limit
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def fetch_repo(slug: str) -> list[tuple[str, str]]:
    """Return [(path, text), ...] for a public repo, within the size limits."""
    slug = parse_repo(slug)
    with _lock:
        hit = _cache.get(slug)
        if hit and time.monotonic() - hit[0] < CACHE_SECONDS:
            return hit[1]
        files = _download(slug)
        _cache[slug] = (time.monotonic(), files)
        return files


def _download(slug: str) -> list[tuple[str, str]]:
    owner, repo = slug.split("/")
    base = f"{quote(owner, safe='')}/{quote(repo, safe='')}"
    try:
        with httpx.Client(timeout=TIMEOUT_SECONDS, follow_redirects=False, headers=_headers()) as client:
            r = client.get(f"{API}/repos/{base}/git/trees/HEAD", params={"recursive": "1"})
            if r.status_code == 404:
                raise FetchError("Repo not found, or it's private")
            if r.status_code in (403, 429):
                raise FetchError("GitHub rate limit reached; try again later")
            if r.status_code != 200:
                raise FetchError(f"GitHub error {r.status_code}")
            tree = [t for t in r.json().get("tree", []) if t.get("type") == "blob"]
            paths = sorted((t["path"] for t in tree if _wanted(t["path"], t.get("size", 0))), key=_rank)
            files, total = [], 0
            for path in paths[:MAX_FILES]:
                raw = client.get(f"{RAW}/{base}/HEAD/{quote(path)}")
                if raw.status_code != 200:
                    continue
                text = raw.text
                if "\x00" in text:  # binary file with a text-looking name
                    continue
                if len(text) > MAX_CHARS_PER_FILE:
                    text = text[:MAX_CHARS_PER_FILE] + "\n... (rest of file not shown)"
                if total + len(text) > MAX_TOTAL_CHARS:
                    text = text[: MAX_TOTAL_CHARS - total]
                files.append((path, text))
                total += len(text)
                if total >= MAX_TOTAL_CHARS:
                    break
    except httpx.TimeoutException as exc:
        raise FetchError("GitHub took too long to answer") from exc
    except httpx.HTTPError as exc:
        raise FetchError("Could not reach GitHub") from exc
    if not files:
        raise FetchError("No readable source files found in that repo")
    return files
