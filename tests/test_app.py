import atexit
import base64
import json
from http.cookies import SimpleCookie
from io import BytesIO, StringIO
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlencode, urlsplit, unquote

import pytest
from bottle import HTTPError


REPO_ROOT_FOR_IMPORTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT_FOR_IMPORTS))
BOOTSTRAP_DIR = Path(tempfile.mkdtemp(prefix="gitman-test-bootstrap-"))
atexit.register(shutil.rmtree, BOOTSTRAP_DIR, ignore_errors=True)
os.environ["GITMAN_DB"] = str(BOOTSTRAP_DIR / "gitman.sqlite3")
os.environ["GITMAN_REPO_ROOT"] = str(BOOTSTRAP_DIR / "repos")
os.environ["SECRET_KEY"] = "test-secret"

import app as gitman  # noqa: E402


class WsgiResponse:
    def __init__(self, status_line, headers, body):
        self.status_line = status_line
        self.status_code = int(status_line.split(" ", 1)[0])
        self.headers = headers
        self.body = body
        self.text = body.decode("utf-8", "replace")

    def header(self, name, default=None):
        name = name.lower()
        for key, value in self.headers:
            if key.lower() == name:
                return value
        return default

    @property
    def location(self):
        return self.header("Location")

    @property
    def location_path(self):
        location = self.location
        if not location:
            return None
        split = urlsplit(location)
        if not split.scheme and not split.netloc:
            return location
        return split.path + (f"?{split.query}" if split.query else "")


class WsgiClient:
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app
        self.cookies = {}
        self.csrf_token = None

    def get(self, path, headers=None):
        return self.request("GET", path, headers=headers)

    def post(self, path, data=None, headers=None):
        return self.request("POST", path, data=data, headers=headers)

    def request(self, method, path, data=None, headers=None):
        headers = headers or {}
        split = urlsplit(path)
        body = b""
        if method == "POST" and data is None and not split.path.startswith("/git/") and self.csrf_token:
            data = {}
        if data is not None:
            if (
                method == "POST"
                and not split.path.startswith("/git/")
                and gitman.CSRF_FORM_FIELD not in data
                and self.csrf_token
            ):
                data = {**data, gitman.CSRF_FORM_FIELD: self.csrf_token}
            body = urlencode(data, doseq=True).encode("utf-8")
            headers = {"Content-Type": "application/x-www-form-urlencoded", **headers}
        environ = {
            "REQUEST_METHOD": method,
            "SCRIPT_NAME": "",
            "PATH_INFO": unquote(split.path),
            "QUERY_STRING": split.query,
            "SERVER_NAME": "example.test",
            "SERVER_PORT": "80",
            "SERVER_PROTOCOL": "HTTP/1.1",
            "HTTP_HOST": "example.test",
            "wsgi.version": (1, 0),
            "wsgi.url_scheme": "http",
            "wsgi.input": BytesIO(body),
            "wsgi.errors": StringIO(),
            "wsgi.multithread": False,
            "wsgi.multiprocess": False,
            "wsgi.run_once": False,
            "CONTENT_LENGTH": str(len(body)),
            "REMOTE_ADDR": "127.0.0.1",
        }
        if self.cookies:
            environ["HTTP_COOKIE"] = "; ".join(f"{key}={value}" for key, value in self.cookies.items())
        for key, value in headers.items():
            env_key = key.upper().replace("-", "_")
            if env_key == "CONTENT_TYPE":
                environ["CONTENT_TYPE"] = value
            elif env_key == "CONTENT_LENGTH":
                environ["CONTENT_LENGTH"] = value
            else:
                environ[f"HTTP_{env_key}"] = value

        captured = {}

        def start_response(status, response_headers, exc_info=None):
            captured["status"] = status
            captured["headers"] = response_headers

        body_iter = self.wsgi_app(environ, start_response)
        try:
            response_body = b"".join(
                chunk if isinstance(chunk, bytes) else chunk.encode("utf-8") for chunk in body_iter
            )
        finally:
            close = getattr(body_iter, "close", None)
            if close:
                close()
        response = WsgiResponse(captured["status"], captured["headers"], response_body)
        self._store_cookies(response.headers)
        self._store_csrf_token(response.text)
        return response

    def _store_cookies(self, headers):
        for key, value in headers:
            if key.lower() != "set-cookie":
                continue
            cookie = SimpleCookie()
            cookie.load(value)
            for name, morsel in cookie.items():
                if morsel.value == "" and (morsel["expires"] or morsel["max-age"] == "0"):
                    self.cookies.pop(name, None)
                else:
                    self.cookies[name] = morsel.value

    def _store_csrf_token(self, text):
        match = re.search(r'name="_csrf_token"\s+value="([^"]+)"', text)
        if match:
            self.csrf_token = match.group(1)


def login_client(client, username, password="correct horse battery staple", next_url="/"):
    client.get("/login")
    return client.post("/login", {"username": username, "password": password, "next": next_url})


@pytest.fixture()
def isolated_app(tmp_path, monkeypatch):
    monkeypatch.setattr(gitman, "DB_PATH", tmp_path / "gitman.sqlite3")
    monkeypatch.setattr(gitman, "REPO_ROOT", tmp_path / "repos")
    gitman.AUTH_FAILURES.clear()
    gitman.init_db()
    return gitman


def create_user(username, password="correct horse battery staple"):
    with gitman.db_connect() as conn:
        conn.execute(
            "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
            (username, gitman.hash_password(password), gitman.utcnow()),
        )
    return gitman.get_user_by_username(username)


def commit_file(repo_path, relative_path, content, message="initial commit", user="alice", branch=None):
    with tempfile.TemporaryDirectory(prefix="gitman-test-work-") as tempdir:
        work_path = Path(tempdir) / "work"
        gitman.run_git(["clone", str(repo_path), str(work_path)], timeout=60)
        gitman.run_git(["config", "user.name", user], cwd=work_path)
        gitman.run_git(["config", "user.email", "gitman-tests@example.test"], cwd=work_path)
        if branch:
            checkout = gitman.run_git(["checkout", branch], cwd=work_path, check=False)
            if checkout.returncode != 0:
                gitman.run_git(["checkout", "-b", branch], cwd=work_path)
        target = work_path / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        gitman.run_git(["add", relative_path], cwd=work_path)
        gitman.run_git(["commit", "-m", message], cwd=work_path)
        node = gitman.run_git(["rev-parse", "HEAD"], cwd=work_path).stdout.strip()
        current_branch = gitman.run_git(["branch", "--show-current"], cwd=work_path).stdout.strip() or "main"
        gitman.run_git(["push", "origin", f"HEAD:refs/heads/{current_branch}"], cwd=work_path, timeout=60)
        return node


def basic_auth(username, password):
    token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
    return {"Authorization": f"Basic {token}"}


def create_repo_with_refs(owner):
    gitman.create_repository(owner, "demo", "Demo repository")
    path = gitman.repo_path(owner["username"], "demo")
    default_node = commit_file(path, "README.md", "# Demo\n", message="initial", user=owner["username"])

    feature_node = commit_file(
        path,
        "feature.txt",
        "feature work\n",
        message="add feature",
        user=owner["username"],
        branch="feature",
    )
    gitman.run_git(["tag", "v1.0", feature_node], cwd=path)

    old_node = commit_file(
        path,
        "old.txt",
        "old branch\n",
        message="old branch work",
        user=owner["username"],
        branch="old",
    )

    return {
        "path": path,
        "default_node": default_node,
        "feature_node": feature_node,
        "old_node": old_node,
    }


def test_normalize_slug_accepts_trimmed_lowercase_values():
    assert gitman.normalize_slug(" Demo_Repo-1 ", "Repository name") == "demo_repo-1"
    assert gitman.normalize_slug("My.Name", "Repository name") == "my.name"


@pytest.mark.parametrize(
    ("value", "label"),
    [
        ("x", "Repository name"),
        ("bad/name", "Repository name"),
        ("-bad", "Repository name"),
        ("demo.git", "Repository name"),
        ("login", "Username"),
        ("harrisonerd", "Username"),
    ],
)
def test_normalize_slug_rejects_invalid_or_reserved_values(value, label):
    with pytest.raises(ValueError):
        gitman.normalize_slug(value, label)


def test_clean_repo_path_normalizes_and_rejects_traversal():
    assert gitman.clean_repo_path("/docs/readme.md/") == "docs/readme.md"
    assert gitman.clean_repo_path("") == ""

    for value in ("../secret", "docs/../secret", "./file"):
        with pytest.raises(HTTPError) as exc_info:
            gitman.clean_repo_path(value)
        assert exc_info.value.status_code == 400


def test_password_hashes_verify_and_reject_bad_inputs():
    stored = gitman.hash_password("correct-password")

    assert stored.startswith("pbkdf2_sha256$")
    assert gitman.verify_password("correct-password", stored)
    assert not gitman.verify_password("wrong-password", stored)
    assert not gitman.verify_password("correct-password", "not-a-valid-hash")


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("example.com", "https://example.com"),
        (" http://example.com/path ", "http://example.com/path"),
        ("https://example.com", "https://example.com"),
    ],
)
def test_normalize_website_accepts_http_urls_and_adds_scheme(value, expected):
    assert gitman.normalize_website(value) == expected


@pytest.mark.parametrize("value", ["ftp://example.com", "https://", "not a url"])
def test_normalize_website_rejects_invalid_urls(value):
    with pytest.raises(ValueError):
        gitman.normalize_website(value)


def test_render_markdown_strips_scripts_and_unsafe_links():
    rendered = gitman.render_markdown(
        """
# Title

<script>alert("x")</script>

[safe](https://example.com) [unsafe](javascript:alert(1))

| A |
| - |
| B |
"""
    )

    assert "<h1>Title</h1>" in rendered
    assert "script" not in rendered.lower()
    assert "javascript:" not in rendered.lower()
    assert 'href="https://example.com"' in rendered
    assert "<table>" in rendered


def test_render_markdown_links_allows_only_links():
    rendered = gitman.render_markdown_links("[site](https://example.com) **bold** <strong>x</strong>")

    assert rendered == '<a href="https://example.com">site</a> bold &lt;strong&gt;x&lt;/strong&gt;'


def test_startup_config_rejects_default_secret_outside_debug(monkeypatch):
    monkeypatch.setattr(gitman, "DEBUG", False)
    monkeypatch.setattr(gitman, "SECRET_KEY", gitman.DEFAULT_SECRET_KEY)

    with pytest.raises(RuntimeError):
        gitman.validate_startup_config()

    monkeypatch.setattr(gitman, "SECRET_KEY", "production-secret")
    gitman.validate_startup_config()


def test_security_headers_and_secure_cookie_flags(isolated_app):
    client = WsgiClient(isolated_app.app)

    response = client.get("/login", headers={"X-Forwarded-Proto": "https"})
    assert response.status_code == 200
    assert response.header("X-Content-Type-Options") == "nosniff"
    assert response.header("Referrer-Policy") == "same-origin"
    assert response.header("X-Frame-Options") == "DENY"
    assert "frame-ancestors 'none'" in response.header("Content-Security-Policy")
    csrf_cookie = response.header("Set-Cookie")
    assert "csrf_token=" in csrf_cookie
    assert "HttpOnly" in csrf_cookie
    assert "samesite=lax" in csrf_cookie.lower()
    assert "Secure" in csrf_cookie

    create_user("alice")
    response = client.post(
        "/login",
        {"username": "alice", "password": "correct horse battery staple", "next": "/"},
        headers={"X-Forwarded-Proto": "https"},
    )
    assert response.status_code == 303
    session_cookie = response.header("Set-Cookie")
    assert "session=" in session_cookie
    assert "HttpOnly" in session_cookie
    assert "samesite=lax" in session_cookie.lower()
    assert "Secure" in session_cookie


def test_styles_support_system_dark_mode(isolated_app):
    css = (REPO_ROOT_FOR_IMPORTS / "static" / "styles.css").read_text(encoding="utf-8")
    client = WsgiClient(isolated_app.app)
    response = client.get("/")

    assert "@media (prefers-color-scheme: dark)" in css
    assert "color-scheme: dark" in css
    assert "var(--page-bg)" in css
    assert "github-dark.min.css" in response.text
    assert 'media="(prefers-color-scheme: dark)"' in response.text


def test_index_public_repo_search_finds_repositories_by_fuzzy_name(isolated_app):
    owner = create_user("alice")
    other = create_user("bob")
    isolated_app.create_repository(owner, "gitman", "Local git hosting")
    isolated_app.create_repository(owner, "api-client", "HTTP integration")
    isolated_app.create_repository(other, "docs", "GitMan docs should not match by description")
    client = WsgiClient(isolated_app.app)

    anonymous_index_response = client.get("/")
    assert anonymous_index_response.status_code == 200
    assert 'data-repo-search-url="/-/repos/search"' not in anonymous_index_response.text

    login_client(client, "alice")
    index_response = client.get("/")
    assert index_response.status_code == 200
    assert 'data-repo-search-url="/-/repos/search"' in index_response.text
    assert 'aria-controls="repo-search-results"' in index_response.text

    fuzzy_response = client.get("/-/repos/search?q=gmn")
    fuzzy_results = json.loads(fuzzy_response.text)["results"]
    assert fuzzy_response.status_code == 200
    assert fuzzy_response.header("Content-Type").startswith("application/json")
    assert [result["full_name"] for result in fuzzy_results] == ["alice/gitman"]
    assert fuzzy_results[0]["url"] == "/alice/gitman"

    compact_response = client.get(f"/-/repos/search?{urlencode({'q': 'api client'})}")
    compact_results = json.loads(compact_response.text)["results"]
    assert [result["full_name"] for result in compact_results] == ["alice/api-client"]

    empty_response = client.get("/-/repos/search")
    assert json.loads(empty_response.text)["results"] == []


def test_csrf_required_for_browser_posts_and_git_is_exempt(isolated_app):
    owner = create_user("alice", password="owner-password")
    isolated_app.create_repository(owner, "demo", "")
    client = WsgiClient(isolated_app.app)

    response = client.post("/login", {"username": "alice", "password": "owner-password", "next": "/"})
    assert response.status_code == 403
    assert "Invalid CSRF token." in response.text

    client.get("/login")
    response = client.post(
        "/login",
        {"username": "alice", "password": "owner-password", "next": "/", gitman.CSRF_FORM_FIELD: "bad-token"},
    )
    assert response.status_code == 403

    response = client.post("/git/alice/demo/git-receive-pack")
    assert response.status_code == 401
    assert response.header("WWW-Authenticate") == 'Basic realm="GitMan"'
    assert response.header("Connection") is None


def test_browser_form_size_limit(isolated_app, monkeypatch):
    monkeypatch.setattr(gitman, "MAX_FORM_BYTES", 40)
    client = WsgiClient(isolated_app.app)
    client.get("/login")

    response = client.post("/login", {"username": "a" * 100, "password": "bad", "next": "/"})
    assert response.status_code == 413
    assert "Request body too large." in response.text


def test_login_and_git_auth_failures_are_rate_limited(isolated_app, monkeypatch):
    monkeypatch.setattr(gitman, "RATE_LIMIT_MAX_FAILURES", 2)
    monkeypatch.setattr(gitman, "RATE_LIMIT_COOLDOWN_SECONDS", 60)
    create_user("alice", password="owner-password")
    client = WsgiClient(isolated_app.app)
    client.get("/login")

    for _ in range(2):
        response = client.post("/login", {"username": "alice", "password": "wrong", "next": "/"})
        assert response.status_code == 200
    response = client.post("/login", {"username": "alice", "password": "wrong", "next": "/"})
    assert response.status_code == 429
    assert response.header("Retry-After") == "60"

    gitman.AUTH_FAILURES.clear()
    owner = gitman.get_user_by_username("alice")
    isolated_app.create_repository(owner, "demo", "")
    for _ in range(2):
        response = client.post("/git/alice/demo/git-receive-pack", headers=basic_auth("alice", "wrong"))
        assert response.status_code == 401
        assert response.header("Connection") is None
    response = client.post("/git/alice/demo/git-receive-pack", headers=basic_auth("alice", "wrong"))
    assert response.status_code == 429
    assert response.header("Connection") is None


def test_readme_preview_is_truncated_but_source_files_render_fully(isolated_app, monkeypatch):
    monkeypatch.setattr(gitman, "MAX_RENDER_BYTES", 32)
    owner = create_user("alice")
    isolated_app.create_repository(owner, "demo", "")
    readme_content = "line 1\nline 2\nline 3\n" + ("A" * 200)
    commit_file(isolated_app.repo_path("alice", "demo"), "README.md", readme_content, message="large readme")
    client = WsgiClient(isolated_app.app)

    response = client.get("/alice/demo")
    assert response.status_code == 200
    assert "README preview truncated." in response.text

    response = client.get("/alice/demo/src/README.md")
    assert response.status_code == 200
    assert "File preview truncated." not in response.text
    assert readme_content in response.text
    assert '<div class="copyable-code" data-code-viewer>' in response.text


def test_build_tree_deduplicates_entries_and_sorts_directories_first():
    files = ["README.md", "src/app.py", "src/utils/helpers.py", "docs/index.md", "src/z.txt"]

    assert gitman.build_tree(files, "") == [
        {"name": "docs", "path": "docs", "type": "dir"},
        {"name": "src", "path": "src", "type": "dir"},
        {"name": "README.md", "path": "README.md", "type": "file"},
    ]
    assert gitman.build_tree(files, "src") == [
        {"name": "utils", "path": "src/utils", "type": "dir"},
        {"name": "app.py", "path": "src/app.py", "type": "file"},
        {"name": "z.txt", "path": "src/z.txt", "type": "file"},
    ]


def test_ref_option_values_round_trip_quoted_names():
    branch_name = "feature/a|b c"
    value = gitman.ref_option_value(gitman.REF_TYPE_BRANCH, branch_name)

    assert value == "branch|feature%2Fa%7Cb%20c"
    assert gitman.parse_ref_option_value(value) == (gitman.REF_TYPE_BRANCH, branch_name)

    tag_name = "release/a|b c"
    tag_value = gitman.ref_option_value(gitman.REF_TYPE_TAG, tag_name)

    assert tag_value == "tag|release%2Fa%7Cb%20c"
    assert gitman.parse_ref_option_value(tag_value) == (gitman.REF_TYPE_TAG, tag_name)


def test_source_ref_option_values_round_trip_and_validate_source_repo():
    branch_name = "feature/a|b"
    value = gitman.source_ref_option_value(42, gitman.REF_TYPE_BRANCH, branch_name)

    assert gitman.parse_source_ref_option_value(value) == (42, gitman.REF_TYPE_BRANCH, branch_name)

    with pytest.raises(ValueError, match="Invalid source repository"):
        gitman.parse_source_ref_option_value(f"not-int|{gitman.REF_TYPE_BRANCH}|main")

    with pytest.raises(ValueError, match="Invalid source ref"):
        gitman.parse_source_ref_option_value(f"42|{gitman.REF_TYPE_COMMIT}|abc123")


def test_ref_query_and_url_helpers_skip_default_refs_unless_forced():
    ref = {"type": gitman.REF_TYPE_BRANCH, "name": "main", "is_default": True}

    assert gitman.ref_query_string(ref) == ""
    assert gitman.ref_query_string(ref, force=True) == "ref_type=branch&ref=main"
    assert gitman.url_with_ref("/alice/demo", ref, force=True) == "/alice/demo?ref_type=branch&ref=main"
    assert gitman.url_with_ref("/alice/demo?tab=files", ref, force=True) == (
        "/alice/demo?tab=files&ref_type=branch&ref=main"
    )


def test_format_ref_label_and_option_label():
    assert gitman.format_ref_label(gitman.REF_TYPE_TIP) == "HEAD"
    assert gitman.format_ref_label(gitman.REF_TYPE_TAG, "v1.0") == "tag v1.0"
    assert gitman.format_ref_label(gitman.REF_TYPE_COMMIT, "abcdef1234567890") == "commit abcdef123456"
    assert gitman.ref_option_label({"type": gitman.REF_TYPE_BRANCH, "name": "old", "closed": False}) == "branch old"
    assert gitman.ref_option_label({"type": gitman.REF_TYPE_TAG, "name": "v1.0", "local": False}) == "tag v1.0"


def test_init_db_creates_expected_tables_and_is_idempotent(isolated_app):
    isolated_app.init_db()

    with isolated_app.db_connect() as conn:
        tables = {
            row["name"]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
        user_columns = {row["name"] for row in conn.execute("PRAGMA table_info(users)")}
        repo_columns = {row["name"] for row in conn.execute("PRAGMA table_info(repositories)")}
        pr_columns = {row["name"] for row in conn.execute("PRAGMA table_info(pull_requests)")}

    assert {"users", "repositories", "issues", "pull_requests", "repo_stars", "custom_domains"}.issubset(tables)
    assert {"display_name", "bio", "website"}.issubset(user_columns)
    assert {"forked_from_repo_id", "forked_at", "forked_from_node", "pages_docs_enabled"}.issubset(repo_columns)
    assert {"target_ref_type", "target_ref_name", "source_ref_type", "source_ref_name"}.issubset(pr_columns)


def test_db_connect_configures_sqlite_for_worker_contention(isolated_app):
    isolated_app.init_db()

    with isolated_app.db_connect() as conn:
        foreign_keys = conn.execute("PRAGMA foreign_keys").fetchone()[0]
        busy_timeout = conn.execute("PRAGMA busy_timeout").fetchone()[0]
        synchronous = conn.execute("PRAGMA synchronous").fetchone()[0]
        journal_mode = conn.execute("PRAGMA journal_mode").fetchone()[0]

    assert foreign_keys == 1
    assert busy_timeout == gitman.SQLITE_BUSY_TIMEOUT_MS
    assert synchronous == 1
    assert journal_mode.lower() == "wal"


def test_sqlite_accepts_concurrent_worker_writes(isolated_app):
    isolated_app.init_db()
    repo_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(repo_root) if not existing_pythonpath else f"{repo_root}{os.pathsep}{existing_pythonpath}"

    worker_script = """
import os
import sys
import time

os.environ["GITMAN_DB"] = sys.argv[1]
os.environ["GITMAN_REPO_ROOT"] = sys.argv[2]
os.environ["SECRET_KEY"] = "test-secret"

import app as gitman

with gitman.db_connect() as conn:
    conn.execute("BEGIN IMMEDIATE")
    conn.execute(
        "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
        (sys.argv[3], "hash", gitman.utcnow()),
    )
    time.sleep(0.2)
"""

    processes = [
        subprocess.Popen(
            [
                sys.executable,
                "-c",
                worker_script,
                str(isolated_app.DB_PATH),
                str(isolated_app.REPO_ROOT),
                f"worker-{index}",
            ],
            cwd=repo_root,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for index in range(3)
    ]

    results = []
    try:
        for process in processes:
            stdout, stderr = process.communicate(timeout=15)
            results.append((process.returncode, stdout, stderr))
    finally:
        for process in processes:
            if process.poll() is None:
                process.kill()

    assert results
    for returncode, stdout, stderr in results:
        assert returncode == 0, stdout + stderr

    with isolated_app.db_connect() as conn:
        count = conn.execute("SELECT COUNT(*) FROM users WHERE username LIKE 'worker-%'").fetchone()[0]

    assert count == 3


def test_create_repository_persists_metadata_and_writes_git_config(isolated_app):
    owner = create_user("alice")

    isolated_app.create_repository(owner, "demo", "line one\nline two")

    repo = isolated_app.get_repo("alice", "demo")
    path = isolated_app.repo_path("alice", "demo")

    assert repo["owner_username"] == "alice"
    assert repo["name"] == "demo"
    assert path.joinpath("objects").is_dir()
    assert path.joinpath("HEAD").read_text(encoding="utf-8").strip() == "ref: refs/heads/main"
    assert path.joinpath("description").read_text(encoding="utf-8") == "line one line two"
    assert isolated_app.run_git(["config", "gitman.owner"], cwd=path).stdout.strip() == "alice"
    assert isolated_app.run_git(["config", "gitman.name"], cwd=path).stdout.strip() == "demo"
    assert isolated_app.run_git(["config", "gitman.description"], cwd=path).stdout.strip() == "line one line two"
    assert isolated_app.run_git(["config", "http.receivepack"], cwd=path).stdout.strip() == "true"
    assert isolated_app.run_git(["config", "receive.denyDeleteCurrent"], cwd=path).stdout.strip() == "warn"


def test_create_repository_rolls_back_database_and_files_when_git_init_fails(isolated_app, monkeypatch):
    owner = create_user("alice")

    def fail_git(*args, **kwargs):
        raise gitman.GitCommandError("init failed")

    monkeypatch.setattr(isolated_app, "run_git", fail_git)

    with pytest.raises(gitman.GitCommandError, match="init failed"):
        isolated_app.create_repository(owner, "broken", "")

    assert isolated_app.get_repo("alice", "broken") is None
    assert not isolated_app.repo_path("alice", "broken").exists()


def test_star_and_contributor_helpers_update_database_and_git_config(isolated_app):
    owner = create_user("alice")
    contributor = create_user("bob")
    isolated_app.create_repository(owner, "demo", "")
    repo = isolated_app.get_repo("alice", "demo")

    isolated_app.star_repo(contributor, repo)
    assert isolated_app.repo_star_count(repo["id"]) == 1
    assert isolated_app.user_starred_repo(contributor, repo)

    isolated_app.add_repo_contributor(repo, owner, "bob")
    assert isolated_app.user_can_maintain_repo(contributor, repo)
    repo_path = isolated_app.repo_path("alice", "demo")
    assert isolated_app.run_git(["config", "http.receivepack"], cwd=repo_path).stdout.strip() == "true"

    isolated_app.unstar_repo(contributor, repo)
    isolated_app.remove_repo_contributor(repo, contributor["id"])
    assert isolated_app.repo_star_count(repo["id"]) == 0
    assert not isolated_app.user_starred_repo(contributor, repo)
    assert not isolated_app.user_can_maintain_repo(contributor, repo)


def test_issue_queries_count_filter_and_order_comments(isolated_app):
    owner = create_user("alice")
    isolated_app.create_repository(owner, "demo", "")
    repo = isolated_app.get_repo("alice", "demo")
    now = isolated_app.utcnow()

    with isolated_app.db_connect() as conn:
        conn.execute(
            """
            INSERT INTO issues (repo_id, author_id, number, title, body, status, created_at, updated_at)
            VALUES (?, ?, 1, 'open issue', 'body', 'open', ?, ?)
            """,
            (repo["id"], owner["id"], now, now),
        )
        conn.execute(
            """
            INSERT INTO issues (repo_id, author_id, number, title, body, status, created_at, updated_at, closed_at)
            VALUES (?, ?, 2, 'closed issue', '', 'closed', ?, ?, ?)
            """,
            (repo["id"], owner["id"], now, now, now),
        )
        issue_id = conn.execute("SELECT id FROM issues WHERE number = 1").fetchone()["id"]
        conn.execute(
            """
            INSERT INTO issue_comments (issue_id, author_id, body, created_at, updated_at)
            VALUES (?, ?, 'second', '2026-01-01T00:00:02Z', '2026-01-01T00:00:02Z')
            """,
            (issue_id, owner["id"]),
        )
        conn.execute(
            """
            INSERT INTO issue_comments (issue_id, author_id, body, created_at, updated_at)
            VALUES (?, ?, 'first', '2026-01-01T00:00:01Z', '2026-01-01T00:00:01Z')
            """,
            (issue_id, owner["id"]),
        )

    assert isolated_app.issue_counts(repo["id"]) == {"open": 1, "closed": 1}
    assert [issue["number"] for issue in isolated_app.list_issues(repo["id"], "all")] == [2, 1]
    assert [issue["number"] for issue in isolated_app.list_issues(repo["id"], "invalid")] == [1]
    assert [comment["body"] for comment in isolated_app.list_issue_comments(issue_id)] == ["first", "second"]


def test_git_read_helpers_return_files_readme_commits_and_default_ref(isolated_app):
    owner = create_user("alice")
    isolated_app.create_repository(owner, "demo", "")
    path = isolated_app.repo_path("alice", "demo")
    node = commit_file(path, "README.md", "# Demo\n", message="add readme", user="Alice <alice@example.com>")

    files = isolated_app.git_files(path)
    readme_name, readme = isolated_app.readme_for_repo(path, files)
    commits = isolated_app.commit_log(path)
    ref = isolated_app.default_code_ref(path)

    assert files == ["README.md"]
    assert (readme_name, readme) == ("README.md", "# Demo\n")
    assert commits[0]["summary"] == "add readme"
    assert isolated_app.commit_count(path) == 1
    assert ref["type"] == isolated_app.REF_TYPE_BRANCH
    assert ref["name"] == "main"
    assert ref["node"] == node
    assert isolated_app.repo_has_revision(path, node)
    assert isolated_app.is_ancestor(path, isolated_app.NULL_REV, node)


def test_pages_host_serves_user_site_and_enabled_project_docs(isolated_app):
    owner = create_user("alice")
    isolated_app.create_repository(owner, "alice.gitman.io", "")
    site_path = isolated_app.repo_path("alice", "alice.gitman.io")
    commit_file(site_path, "index.html", "<h1>Alice Site</h1>\n", message="site index", user="alice")
    commit_file(site_path, "about.html", "<p>About Alice</p>\n", message="about page", user="alice")
    commit_file(site_path, "404.html", "<h1>Missing page</h1>\n", message="not found page", user="alice")

    isolated_app.create_repository(owner, "project", "")
    project_path = isolated_app.repo_path("alice", "project")
    commit_file(project_path, "docs/index.html", "<h1>Project Docs</h1>\n", message="docs index", user="alice")
    commit_file(project_path, "docs/guide.html", "<h1>Guide</h1>\n", message="docs guide", user="alice")

    client = WsgiClient(isolated_app.app)
    response = client.get("/", headers={"Host": "alice.gitman.io"})
    assert response.status_code == 200
    assert "<h1>Alice Site</h1>" in response.text
    assert response.header("Content-Type").startswith("text/html")
    assert response.header("Content-Security-Policy") is None

    response = client.get("/about", headers={"Host": "alice.gitman.io"})
    assert response.status_code == 200
    assert "About Alice" in response.text

    response = client.get("/project/", headers={"Host": "alice.gitman.io"})
    assert response.status_code == 404
    assert "Missing page" in response.text

    login_client(client, "alice")
    settings_response = client.get("/alice/project/settings")
    assert settings_response.status_code == 200
    assert "Publish this repository" in settings_response.text
    assert 'type="checkbox"' not in settings_response.text
    assert 'name="pages_docs_enabled" value="1"' in settings_response.text
    assert "Publish Pages" in settings_response.text

    response = client.post("/alice/project/settings", {"action": "update_pages", "pages_docs_enabled": "1"})
    assert response.status_code == 200
    assert "Pages settings updated." in response.text
    assert 'name="pages_docs_enabled" value="0"' in response.text
    assert "Unpublish Pages" in response.text

    response = client.get("/project/", headers={"Host": "alice.gitman.io"})
    assert response.status_code == 200
    assert "Project Docs" in response.text

    response = client.get("/project/guide", headers={"Host": "alice.gitman.io"})
    assert response.status_code == 200
    assert "Guide" in response.text

    response = client.get("/.git/config", headers={"Host": "alice.gitman.io"})
    assert response.status_code == 404


def test_custom_pages_domain_requires_dns_txt_verification_and_current_cname(isolated_app, monkeypatch):
    owner = create_user("alice")
    attacker = create_user("bob")
    isolated_app.create_repository(owner, "alice.gitman.io", "")
    site_path = isolated_app.repo_path("alice", "alice.gitman.io")
    commit_file(site_path, "index.html", "<h1>Alice Custom Site</h1>\n", message="site index", user="alice")
    commit_file(site_path, "404.html", "<h1>Alice Missing</h1>\n", message="site 404", user="alice")
    commit_file(site_path, "CNAME", "www.example.com\n", message="custom domain", user="alice")

    alice_client = WsgiClient(isolated_app.app)
    login_client(alice_client, "alice")
    settings_response = alice_client.get("/alice/alice.gitman.io/settings")
    assert settings_response.status_code == 200
    assert "_gitman-pages.www.example.com" in settings_response.text
    assert "Verify DNS" in settings_response.text
    assert "Reverify DNS" not in settings_response.text

    custom_domain = isolated_app.get_custom_domain_for_user(owner["id"], "www.example.com")
    expected_txt = isolated_app.custom_domain_txt_value(custom_domain["verification_token"])
    assert expected_txt in settings_response.text

    response = alice_client.get("/", headers={"Host": "www.example.com"})
    assert response.status_code == 404

    monkeypatch.setattr(isolated_app, "resolve_dns_txt", lambda record_name: [])
    response = alice_client.post("/alice/alice.gitman.io/settings", {"action": "verify_custom_domain"})
    assert response.status_code == 200
    assert "TXT verification record was not found" in response.text
    assert "Verify DNS" in response.text
    assert isolated_app.get_custom_domain_for_user(owner["id"], "www.example.com")["verified_at"] is None

    monkeypatch.setattr(isolated_app, "resolve_dns_txt", lambda record_name: [expected_txt])
    response = alice_client.post("/alice/alice.gitman.io/settings", {"action": "verify_custom_domain"})
    assert response.status_code == 200
    assert "Custom domain verified." in response.text
    assert "Reverify DNS" in response.text
    assert isolated_app.get_custom_domain_for_user(owner["id"], "www.example.com")["verified_at"]

    response = alice_client.get("/", headers={"Host": "www.example.com"})
    assert response.status_code == 200
    assert "Alice Custom Site" in response.text

    isolated_app.create_repository(attacker, "bob.gitman.io", "")
    attacker_path = isolated_app.repo_path("bob", "bob.gitman.io")
    commit_file(attacker_path, "index.html", "<h1>Bob Site</h1>\n", message="site index", user="bob")
    commit_file(attacker_path, "CNAME", "www.example.com\n", message="custom domain", user="bob")

    bob_client = WsgiClient(isolated_app.app)
    login_client(bob_client, "bob")
    bob_settings = bob_client.get("/bob/bob.gitman.io/settings")
    assert bob_settings.status_code == 200
    assert "_gitman-pages.www.example.com" in bob_settings.text

    response = bob_client.post("/bob/bob.gitman.io/settings", {"action": "verify_custom_domain"})
    assert response.status_code == 200
    assert "TXT verification record was not found" in response.text

    response = bob_client.get("/", headers={"Host": "www.example.com"})
    assert response.status_code == 200
    assert "Alice Custom Site" in response.text
    assert "Bob Site" not in response.text

    commit_file(site_path, "CNAME", "other.example.com\n", message="change custom domain", user="alice")
    response = alice_client.get("/", headers={"Host": "www.example.com"})
    assert response.status_code == 404
    assert "Alice Custom Site" not in response.text


def test_first_pushed_master_branch_becomes_default_and_stale_head_falls_back(isolated_app):
    owner = create_user("alice")
    isolated_app.create_repository(owner, "demo", "")
    path = isolated_app.repo_path("alice", "demo")
    node = commit_file(path, "README.md", "# Demo\n", message="initial", user="alice", branch="master")

    assert isolated_app.repo_head_branch(path) == "master"
    assert isolated_app.default_code_ref(path)["name"] == "master"
    assert isolated_app.default_code_ref(path)["node"] == node
    assert isolated_app.commit_count(path) == 1
    assert isolated_app.commit_log(path)[0]["node"] == node

    isolated_app.run_git(["symbolic-ref", "HEAD", "refs/heads/main"], cwd=path)
    assert isolated_app.repo_tip_node(path) is None

    client = WsgiClient(isolated_app.app)
    overview = client.get("/alice/demo")
    commits = client.get("/alice/demo/commits")

    assert overview.status_code == 200
    assert "<h1>Demo</h1>" in overview.text
    assert "This repository is empty." not in overview.text
    assert "branch master" in overview.text
    assert commits.status_code == 200
    assert "initial" in commits.text
    assert "Commits (1)" in commits.text
    assert isolated_app.repo_head_branch(path) == "master"


def test_deleting_current_branch_moves_head_to_surviving_branch(isolated_app):
    owner = create_user("alice")
    isolated_app.create_repository(owner, "demo", "")
    path = isolated_app.repo_path("alice", "demo")
    main_node = commit_file(path, "README.md", "# Demo\n", message="initial", user="alice")
    commit_file(path, "LEGACY.md", "legacy\n", message="legacy branch", user="alice", branch="master")
    isolated_app.run_git(["symbolic-ref", "HEAD", "refs/heads/master"], cwd=path)

    with tempfile.TemporaryDirectory(prefix="gitman-delete-branch-") as tempdir:
        work_path = Path(tempdir) / "work"
        isolated_app.run_git(["clone", str(path), str(work_path)], timeout=60)
        isolated_app.run_git(["push", "origin", "--delete", "master"], cwd=work_path, timeout=60)

    assert isolated_app.run_git(["show-ref", "--verify", "refs/heads/master"], cwd=path, check=False).returncode != 0
    assert isolated_app.repo_head_branch(path) == "main"
    assert isolated_app.default_code_ref(path)["node"] == main_node


def test_create_pull_request_between_fork_repositories(isolated_app):
    owner = create_user("alice")
    author = create_user("bob")
    isolated_app.create_repository(owner, "demo", "")
    target_path = isolated_app.repo_path("alice", "demo")
    base_node = commit_file(target_path, "README.md", "# Demo\n", message="initial", user="alice")
    target_repo = isolated_app.get_repo("alice", "demo")

    isolated_app.fork_repository(author, target_repo, "demo-fork", "forked copy")
    source_repo = isolated_app.get_repo("bob", "demo-fork")
    source_path = isolated_app.repo_path("bob", "demo-fork")
    source_node = commit_file(source_path, "feature.txt", "new feature\n", message="add feature", user="bob")

    number = isolated_app.create_pull_request(
        target_repo,
        source_repo,
        author,
        "Add feature",
        "Please merge this",
        isolated_app.REF_TYPE_TIP,
        "",
        isolated_app.REF_TYPE_BRANCH,
        "main",
    )
    pr = isolated_app.get_pull_request(target_repo["id"], number)
    diff, current_source_node, source_ref = isolated_app.pull_request_diff(pr)

    assert number == 1
    assert pr["base_node"] == base_node
    assert pr["source_node"] == source_node
    assert pr["source_owner_username"] == "bob"
    assert pr["target_owner_username"] == "alice"
    assert current_source_node == source_node
    assert source_ref["type"] == isolated_app.REF_TYPE_TIP
    assert "feature.txt" in diff
    assert "new feature" in diff


def test_pull_request_source_refs_can_use_fork_branches(isolated_app):
    owner = create_user("alice")
    author = create_user("bob")
    isolated_app.create_repository(owner, "demo", "")
    target_path = isolated_app.repo_path("alice", "demo")
    commit_file(target_path, "README.md", "# Demo\n", message="initial", user="alice")
    target_repo = isolated_app.get_repo("alice", "demo")

    isolated_app.fork_repository(author, target_repo, "demo-fork", "forked copy")
    source_repo = isolated_app.get_repo("bob", "demo-fork")
    source_path = isolated_app.repo_path("bob", "demo-fork")
    branch_node = commit_file(
        source_path,
        "feature.txt",
        "branch feature\n",
        message="branch feature",
        user="bob",
        branch="feature/pr",
    )

    source_labels = [option["label"] for option in isolated_app.source_repo_ref_options(source_repo)]

    assert "bob/demo-fork branch feature/pr" in source_labels
    assert not any(" tag " in label for label in source_labels)

    branch_pr_number = isolated_app.create_pull_request(
        target_repo,
        source_repo,
        author,
        "Branch PR",
        "",
        isolated_app.REF_TYPE_BRANCH,
        "feature/pr",
        isolated_app.REF_TYPE_BRANCH,
        "main",
    )
    branch_pr = isolated_app.get_pull_request(target_repo["id"], branch_pr_number)
    branch_diff, branch_source_node, branch_source_ref = isolated_app.pull_request_diff(branch_pr)

    assert branch_pr["source_ref_type"] == isolated_app.REF_TYPE_BRANCH
    assert branch_pr["source_ref_name"] == "feature/pr"
    assert branch_pr["source_node"] == branch_node
    assert branch_source_node == branch_node
    assert branch_source_ref["type"] == isolated_app.REF_TYPE_BRANCH
    assert "branch feature" in branch_diff


def test_pull_requests_can_use_branches_from_the_target_repository(isolated_app):
    owner = create_user("alice")
    create_user("bob")
    isolated_app.create_repository(owner, "demo", "")
    path = isolated_app.repo_path("alice", "demo")
    base_node = commit_file(path, "README.md", "# Demo\n", message="initial", user="alice")
    source_node = commit_file(
        path,
        "feature.txt",
        "in repo branch\n",
        message="add in-repo feature",
        user="alice",
        branch="feature/in-repo",
    )
    target_repo = isolated_app.get_repo("alice", "demo")

    bob_client = WsgiClient(isolated_app.app)
    login_client(bob_client, "bob")
    response = bob_client.get("/alice/demo/pulls/new")
    assert response.status_code == 200
    assert "alice/demo branch feature/in-repo" in response.text
    assert "This repository has no source branches yet." not in response.text

    response = bob_client.post(
        "/alice/demo/pulls/new",
        {
            "source_ref": isolated_app.source_ref_option_value(
                target_repo["id"], isolated_app.REF_TYPE_BRANCH, "feature/in-repo"
            ),
            "target_ref": isolated_app.ref_option_value(isolated_app.REF_TYPE_BRANCH, "main"),
            "title": "Add in-repo feature",
            "body": "Please merge this branch",
        },
    )
    assert response.status_code == 303
    assert response.location_path == "/alice/demo/pulls/1"

    pr = isolated_app.get_pull_request(target_repo["id"], 1)
    assert pr["source_repo_id"] == target_repo["id"]
    assert pr["base_node"] == base_node
    assert pr["source_node"] == source_node
    assert pr["source_ref_type"] == isolated_app.REF_TYPE_BRANCH
    assert pr["source_ref_name"] == "feature/in-repo"

    diff, current_source_node, source_ref = isolated_app.pull_request_diff(pr)
    assert current_source_node == source_node
    assert source_ref["name"] == "feature/in-repo"
    assert "feature.txt" in diff

    owner_client = WsgiClient(isolated_app.app)
    login_client(owner_client, "alice")
    response = owner_client.post("/alice/demo/pulls/1", {"action": "merge"})
    assert response.status_code == 303
    assert isolated_app.run_git(["rev-parse", "refs/heads/main"], cwd=path).stdout.strip() == source_node


def test_branch_tag_helpers_resolve_and_filter_refs(isolated_app):
    owner = create_user("alice")
    nodes = create_repo_with_refs(owner)
    path = nodes["path"]

    branches = {branch["name"]: branch for branch in isolated_app.list_repo_branches(path)}
    tags = isolated_app.list_repo_tags(path)
    target_labels = [option["label"] for option in isolated_app.target_repo_ref_options(path)]
    all_labels = [option["label"] for option in isolated_app.repo_ref_options(path)]
    source_labels = [
        option["label"] for option in isolated_app.source_repo_ref_options(isolated_app.get_repo("alice", "demo"))
    ]

    assert {"main", "feature", "old"}.issubset(branches)
    assert branches["main"]["node"] == nodes["default_node"]
    assert branches["feature"]["closed"] is False
    assert branches["old"]["closed"] is False
    assert tags[0]["name"] == "v1.0"
    assert tags[0]["type"] == isolated_app.REF_TYPE_TAG
    assert tags[0]["node"] == nodes["feature_node"]
    assert isolated_app.default_code_ref(path)["node"] == nodes["default_node"]
    assert isolated_app.resolve_repo_ref(path, isolated_app.REF_TYPE_BRANCH, "feature")["name"] == "feature"
    assert isolated_app.resolve_repo_ref(path, isolated_app.REF_TYPE_TAG, "v1.0")["node"] == nodes["feature_node"]
    assert isolated_app.commit_ref(path, nodes["feature_node"])["type"] == isolated_app.REF_TYPE_COMMIT
    assert "tag v1.0" in all_labels
    assert "tag v1.0" not in target_labels
    assert "HEAD" not in target_labels
    assert "branch old" in target_labels
    assert "branch old" in all_labels
    assert "alice/demo tag v1.0" not in source_labels


def test_repo_ref_options_mark_ten_newest_named_refs_for_picker(isolated_app):
    owner = create_user("alice")
    isolated_app.create_repository(owner, "many", "")
    path = isolated_app.repo_path("alice", "many")
    node = commit_file(path, "README.md", "# Many\n", message="initial", user=owner["username"])
    for index in range(12):
        isolated_app.run_git(["tag", f"v{index:02d}", node], cwd=path)

    options = isolated_app.repo_ref_options(path)
    named_options = [option for option in options if option["ref"]["type"] != isolated_app.REF_TYPE_TIP]
    initial_options = [option for option in named_options if option["is_initial"]]

    assert len(named_options) == 13
    assert len(initial_options) == 10
    assert not any(
        option["is_initial"] for option in options if option["ref"]["type"] == isolated_app.REF_TYPE_TIP
    )

    response = WsgiClient(isolated_app.app).get("/alice/many")
    assert response.text.count('data-ref-label="') == 10
    assert response.text.count('data-ref-initial="true"') == 10
    assert 'data-ref-label="tag v00"' not in response.text
    assert '[hidden] { display: none !important; }' in Path("static/styles.css").read_text(encoding="utf-8")


def test_repo_ref_picker_limits_branch_recents_but_searches_all_branches(isolated_app):
    owner = create_user("alice")
    isolated_app.create_repository(owner, "branches", "")
    path = isolated_app.repo_path("alice", "branches")
    node = commit_file(path, "README.md", "# Branches\n", message="initial", user=owner["username"])
    for index in range(12):
        isolated_app.run_git(["update-ref", f"refs/heads/topic{index:02d}", node], cwd=path)

    response = WsgiClient(isolated_app.app).get("/alice/branches")
    assert response.text.count('data-ref-label="') == 10
    assert response.text.count('data-ref-initial="true"') == 10
    assert 'data-ref-label="branch topic00"' not in response.text

    search_response = WsgiClient(isolated_app.app).get("/alice/branches/refs/search?q=topic00")
    assert search_response.status_code == 200
    assert any(
        result["type"] == isolated_app.REF_TYPE_BRANCH and result["name"] == "topic00"
        for result in json.loads(search_response.text)["results"]
    )


def test_repo_ref_search_finds_refs_outside_initial_picker_options(isolated_app):
    owner = create_user("alice")
    isolated_app.create_repository(owner, "many", "")
    path = isolated_app.repo_path("alice", "many")
    node = commit_file(path, "README.md", "# Many\n", message="initial", user=owner["username"])
    for index in range(12):
        isolated_app.run_git(["tag", f"v{index:02d}", node], cwd=path)
        isolated_app.run_git(["update-ref", f"refs/heads/topic{index:02d}", node], cwd=path)

    initial_labels = {
        option["label"]
        for option in isolated_app.repo_ref_options(path)
        if option["is_initial"]
    }
    assert "branch topic00" not in initial_labels
    assert "tag v00" not in initial_labels

    client = WsgiClient(isolated_app.app)
    branch_response = client.get("/alice/many/refs/search?q=topic00")
    tag_response = client.get("/alice/many/refs/search?q=v00")
    empty_response = client.get("/alice/many/refs/search")

    assert branch_response.status_code == 200
    assert branch_response.header("Content-Type").startswith("application/json")
    assert any(
        result["type"] == isolated_app.REF_TYPE_BRANCH and result["name"] == "topic00"
        for result in json.loads(branch_response.text)["results"]
    )
    assert any(
        result["type"] == isolated_app.REF_TYPE_TAG and result["name"] == "v00"
        for result in json.loads(tag_response.text)["results"]
    )
    assert json.loads(empty_response.text)["results"] == []


def test_repo_ref_search_finds_commits_by_subject_and_sha_across_all_refs(isolated_app):
    owner = create_user("alice")
    nodes = create_repo_with_refs(owner)
    client = WsgiClient(isolated_app.app)

    subject_response = client.get(f"/alice/demo/refs/search?{urlencode({'q': 'old branch work'})}")
    sha_response = client.get(f"/alice/demo/refs/search?{urlencode({'q': nodes['old_node'][:12]})}")

    assert subject_response.status_code == 200
    assert any(
        result["type"] == isolated_app.REF_TYPE_COMMIT
        and result["name"] == nodes["old_node"]
        and "old branch work" in result["label"]
        for result in json.loads(subject_response.text)["results"]
    )
    assert any(
        result["type"] == isolated_app.REF_TYPE_COMMIT and result["name"] == nodes["old_node"]
        for result in json.loads(sha_response.text)["results"]
    )


def test_bottle_signup_login_logout_and_new_repo_flow(isolated_app):
    client = WsgiClient(isolated_app.app)

    response = client.get("/new")
    assert response.status_code == 303
    assert response.location_path == "/login?next=/new"

    response = client.get("/signup?next=/new")
    assert response.status_code == 200
    response = client.post(
        "/signup",
        {"username": "alice", "password": "password123", "next": "/new"},
    )
    assert response.status_code == 303
    assert response.location_path == "/new"
    assert "session" in client.cookies

    response = client.get("/new")
    assert response.status_code == 200
    assert "Create repository" in response.text

    response = client.post("/new", {"name": "demo", "description": "A test repository"})
    assert response.status_code == 303
    assert response.location_path == "/alice/demo"
    assert isolated_app.get_repo("alice", "demo") is not None

    response = client.get("/alice/demo")
    assert response.status_code == 200
    assert "This repository is empty." in response.text
    assert "http://example.test/git/alice/demo" in response.text

    response = client.post("/logout")
    assert response.status_code == 303
    assert response.location_path == "/"
    assert "session" not in client.cookies

    response = client.get("/new")
    assert response.status_code == 303
    assert response.location_path == "/login?next=/new"


def test_bottle_repository_pages_render_refs_files_raw_and_errors(isolated_app):
    owner = create_user("alice")
    nodes = create_repo_with_refs(owner)
    client = WsgiClient(isolated_app.app)
    commit_short = nodes["default_node"][:12]

    checks = [
        ("/", 200, "Recent Activity"),
        ("/alice", 200, "alice/demo"),
        ("/alice?tab=stars", 200, "No starred repositories yet."),
        ("/alice/demo", 200, "<h1>Demo</h1>"),
        ("/alice/demo/src", 200, "README.md"),
        ("/alice/demo/src/README.md", 200, "# Demo"),
        (f"/alice/demo/commits/{commit_short}", 200, "initial"),
        ("/alice/demo/commits", 200, "initial"),
        ("/alice/demo/branches", 200, "feature"),
        ("/alice/demo/branches", 200, "old"),
        ("/alice/demo/tags", 200, "v1.0"),
        ("/alice/demo/src?ref_type=branch&ref=feature", 200, "feature.txt"),
        ("/alice/demo/src/feature.txt?ref_type=branch&ref=feature", 200, "feature work"),
        ("/alice/demo/src?ref_type=tag&ref=v1.0", 200, "feature.txt"),
        ("/alice/demo/commits?ref_type=tag&ref=v1.0", 200, "add feature"),
        ("/alice/demo/issues", 200, "No open issues."),
        ("/alice/demo/pulls", 200, "No open pull requests."),
        ("/static/icon.png", 200, ""),
        ("/favicon.ico", 204, ""),
        ("/alice/missing", 404, "Repository not found."),
        ("/alice/demo/src/missing.txt", 404, "Path not found."),
        ("/alice/demo/src/docs/../secret", 400, "Invalid repository path."),
        ("/alice/demo/src?ref_type=branch&ref=missing", 404, "Branch not found."),
        ("/alice/demo/src?ref_type=tag&ref=missing", 404, "Tag not found."),
    ]

    for path, status_code, expected_text in checks:
        response = client.get(path)
        assert response.status_code == status_code, path
        assert expected_text in response.text, path

    repo_response = client.get("/alice/demo")
    issues_response = client.get("/alice/demo/issues")
    pulls_response = client.get("/alice/demo/pulls")
    assert 'data-ref-label="tag v1.0"' in repo_response.text
    assert 'data-ref-initial="true"' in repo_response.text
    assert 'class="ref-picker"' in repo_response.text
    assert 'class="ref-picker"' not in issues_response.text
    assert 'class="ref-picker"' not in pulls_response.text

    response = client.get("/alice/demo/raw/feature.txt?ref_type=branch&ref=feature")
    assert response.status_code == 200
    assert response.body == b"feature work\n"
    assert response.header("Content-Type").startswith("text/plain")


def test_bottle_profile_star_fork_and_repo_settings_flows(isolated_app):
    owner = create_user("alice")
    bob = create_user("bob")
    create_repo_with_refs(owner)

    bob_client = WsgiClient(isolated_app.app)
    response = login_client(bob_client, "bob")
    assert response.status_code == 303

    response = bob_client.post("/alice/demo/star", {"action": "star"})
    assert response.status_code == 303
    assert isolated_app.repo_star_count(isolated_app.get_repo("alice", "demo")["id"]) == 1

    response = bob_client.post("/alice/demo/fork", {"name": "demo", "description": "Forked"})
    assert response.status_code == 303
    assert response.location_path == "/bob/demo"
    assert isolated_app.get_repo("bob", "demo") is not None
    assert "Fork of <a href=\"/alice/demo\">alice/demo</a>" in bob_client.get("/bob/demo").text

    owner_client = WsgiClient(isolated_app.app)
    response = login_client(owner_client, "alice")
    assert response.status_code == 303

    response = owner_client.post(
        "/settings/profile",
        {"display_name": "Alice A.", "bio": "Git maintainer", "website": "example.com"},
    )
    assert response.status_code == 200
    assert "Profile updated." in response.text
    profile = owner_client.get("/alice")
    assert "Alice A." in profile.text
    assert "https://example.com" in profile.text
    assert 'style="color:black;"' not in profile.text
    settings_response = owner_client.get("/alice/demo/settings")
    assert settings_response.status_code == 200
    assert 'class="ref-picker"' not in settings_response.text

    response = owner_client.post("/alice/demo/settings", {"action": "save", "description": "Updated"})
    assert response.status_code == 200
    assert "Repository settings updated." in response.text
    assert isolated_app.get_repo("alice", "demo")["description"] == "Updated"

    response = owner_client.post("/alice/demo/settings", {"action": "add_contributor", "username": "bob"})
    assert response.status_code == 303
    repo = isolated_app.get_repo("alice", "demo")
    assert isolated_app.user_can_maintain_repo(bob, repo)

    response = owner_client.post("/alice/demo/settings", {"action": "remove_contributor", "user_id": str(bob["id"])})
    assert response.status_code == 303
    assert not isolated_app.user_can_maintain_repo(bob, repo)

    response = owner_client.post("/alice/demo/settings", {"action": "delete", "confirm_name": "wrong"})
    assert response.status_code == 200
    assert "Type &quot;demo&quot; to confirm deletion." in response.text


def test_bottle_issue_routes_create_comment_close_and_reopen(isolated_app):
    owner = create_user("alice")
    create_repo_with_refs(owner)
    client = WsgiClient(isolated_app.app)
    login_client(client, "alice")

    response = client.get("/alice/demo/issues/new")
    assert response.status_code == 200
    assert "Open issue" in response.text

    response = client.post("/alice/demo/issues/new", {"title": "", "body": ""})
    assert response.status_code == 200
    assert "Issue title is required." in response.text

    response = client.post("/alice/demo/issues/new", {"title": "Bug report", "body": "It fails"})
    assert response.status_code == 303
    assert response.location_path == "/alice/demo/issues/1"

    response = client.get("/alice/demo/issues/1")
    assert response.status_code == 200
    assert "Bug report" in response.text
    assert "It fails" in response.text
    assert 'class="ref-picker"' not in response.text

    response = client.post("/alice/demo/issues/1", {"action": "comment", "body": ""})
    assert response.status_code == 200
    assert "Comment body is required." in response.text

    response = client.post("/alice/demo/issues/1", {"action": "comment", "body": "I can reproduce this"})
    assert response.status_code == 303
    assert "I can reproduce this" in client.get("/alice/demo/issues/1").text

    response = client.post("/alice/demo/issues/1", {"action": "close"})
    assert response.status_code == 303
    assert isolated_app.get_issue(isolated_app.get_repo("alice", "demo")["id"], 1)["status"] == "closed"

    response = client.post("/alice/demo/issues/1", {"action": "reopen"})
    assert response.status_code == 303
    assert isolated_app.get_issue(isolated_app.get_repo("alice", "demo")["id"], 1)["status"] == "open"


def test_bottle_pull_request_routes_create_comment_forbid_and_merge(isolated_app):
    owner = create_user("alice")
    author = create_user("bob")
    isolated_app.create_repository(owner, "demo", "")
    target_path = isolated_app.repo_path("alice", "demo")
    base_node = commit_file(target_path, "README.md", "# Demo\n", message="initial", user="alice")
    target_repo = isolated_app.get_repo("alice", "demo")
    isolated_app.fork_repository(author, target_repo, "demo-fork", "forked copy")
    source_repo = isolated_app.get_repo("bob", "demo-fork")
    source_path = isolated_app.repo_path("bob", "demo-fork")
    source_node = commit_file(
        source_path,
        "feature.txt",
        "new feature\n",
        message="add feature",
        user="bob",
        branch="feature/pr",
    )

    bob_client = WsgiClient(isolated_app.app)
    login_client(bob_client, "bob")

    response = bob_client.get("/alice/demo/pulls/new")
    assert response.status_code == 200
    assert "bob/demo-fork HEAD" in response.text
    assert "bob/demo-fork branch feature/pr" in response.text
    assert 'class="ref-picker"' not in response.text

    response = bob_client.post(
        "/alice/demo/pulls/new",
        {
            "source_ref": isolated_app.source_ref_option_value(
                source_repo["id"], isolated_app.REF_TYPE_BRANCH, "feature/pr"
            ),
            "target_ref": isolated_app.ref_option_value(isolated_app.REF_TYPE_BRANCH, "main"),
            "title": "Add feature",
            "body": "Please merge this",
        },
    )
    assert response.status_code == 303
    assert response.location_path == "/alice/demo/pulls/1"

    pr = isolated_app.get_pull_request(target_repo["id"], 1)
    assert pr["base_node"] == base_node
    assert pr["source_node"] == source_node
    assert pr["source_ref_type"] == isolated_app.REF_TYPE_BRANCH
    assert pr["source_ref_name"] == "feature/pr"

    response = bob_client.get("/alice/demo/pulls/1")
    assert response.status_code == 200
    assert "feature.txt" in response.text
    assert "new feature" in response.text
    assert 'class="ref-picker"' not in response.text

    response = bob_client.post("/alice/demo/pulls/1", {"action": "comment", "body": "Looks ready"})
    assert response.status_code == 303
    assert "Looks ready" in bob_client.get("/alice/demo/pulls/1").text

    response = bob_client.post("/alice/demo/pulls/1", {"action": "close"})
    assert response.status_code == 403
    assert "Only maintainers can update pull requests." in response.text

    owner_client = WsgiClient(isolated_app.app)
    login_client(owner_client, "alice")
    response = owner_client.post("/alice/demo/pulls/1", {"action": "merge"})
    assert response.status_code == 303

    merged = isolated_app.get_pull_request(target_repo["id"], 1)
    assert merged["status"] == "merged"
    assert merged["merge_node"]
    assert isolated_app.repo_has_revision(target_path, merged["merge_node"])
    assert isolated_app.repo_has_revision(target_path, source_node)
    response = owner_client.get("/alice/demo/pulls/1")
    assert response.status_code == 200
    assert "Merged by alice" in response.text


def test_git_http_routes_are_public_for_reads_and_protect_writes(isolated_app):
    owner = create_user("alice", password="owner-password")
    create_user("bob", password="bob-password")
    isolated_app.create_repository(owner, "demo", "")
    path = isolated_app.repo_path("alice", "demo")
    commit_file(path, "README.md", "# Demo\n", message="initial", user="alice")
    client = WsgiClient(isolated_app.app)

    response = client.get("/git/alice/demo/info/refs?service=git-upload-pack")
    assert response.status_code == 200
    assert b"git-upload-pack" in response.body

    response = client.get("/git/alice/demo/info/refs?service=git-receive-pack")
    assert response.status_code == 401
    assert response.header("WWW-Authenticate") == 'Basic realm="GitMan"'
    assert response.header("Connection") is None
    assert "Authentication required." in response.text

    response = client.get(
        "/git/alice/demo/info/refs?service=git-receive-pack",
        headers=basic_auth("alice", "wrong"),
    )
    assert response.status_code == 401
    assert response.header("Connection") is None
    assert "Invalid Git credentials." in response.text

    response = client.get(
        "/git/alice/demo/info/refs?service=git-receive-pack",
        headers=basic_auth("bob", "bob-password"),
    )
    assert response.status_code == 403
    assert response.header("Connection") is None
    assert "Push not authorized" in response.text

    hook = path / "hooks" / "post-receive"
    hook.unlink()
    isolated_app.run_git(["config", "--unset", "receive.denyDeleteCurrent"], cwd=path, check=False)
    response = client.get(
        "/git/alice/demo/info/refs?service=git-receive-pack",
        headers=basic_auth("alice", "owner-password"),
    )
    assert response.status_code == 200
    assert b"git-receive-pack" in response.body
    assert hook.exists()
    assert isolated_app.run_git(["config", "receive.denyDeleteCurrent"], cwd=path).stdout.strip() == "warn"
