import base64
from contextlib import contextmanager
import datetime as dt
import hashlib
import hmac
import html
import json
import mimetypes
import os
import re
import secrets
import shutil
import sqlite3
import subprocess
import sys
import threading
import time
import tempfile
from socketserver import ThreadingMixIn
from pathlib import Path, PurePosixPath
from urllib.parse import parse_qsl, quote, unquote, urlencode, urlparse
from wsgiref.simple_server import WSGIServer

import bleach
import markdown
try:
    import dns.exception
    import dns.resolver
except ImportError:
    dns = None
from bottle import (
    Bottle,
    HTTPResponse,
    TEMPLATE_PATH,
    abort,
    redirect,
    request,
    response,
    run,
    static_file,
    template,
)


def env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def env_int(name, default, minimum=0):
    try:
        value = int(os.environ.get(name, str(default)))
    except ValueError:
        return default
    return max(minimum, value)


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = Path(os.environ.get("GITMAN_DB", DATA_DIR / "gitman.sqlite3"))
REPO_ROOT = Path(os.environ.get("GITMAN_REPO_ROOT", DATA_DIR / "repos"))
DEFAULT_SECRET_KEY = "dev-secret-change-me"
SECRET_KEY = os.environ.get("SECRET_KEY", DEFAULT_SECRET_KEY)
DEBUG = env_bool("GITMAN_DEBUG")
PASSWORD_ITERATIONS = 260_000
SQLITE_BUSY_TIMEOUT_MS = 30_000
MAX_FORM_BYTES = env_int("GITMAN_MAX_FORM_BYTES", 64 * 1024)
MAX_IMPORT_BYTES = env_int("GITMAN_MAX_IMPORT_BYTES", 2 * 1024 * 1024 * 1024)
IMPORT_UPLOAD_CHUNK_BYTES = 1024 * 1024
IMPORT_UPLOAD_STALE_SECONDS = env_int("GITMAN_IMPORT_UPLOAD_STALE_SECONDS", 6 * 60 * 60, minimum=60)
GIT_IMPORT_TIMEOUT_SECONDS = env_int("GITMAN_IMPORT_TIMEOUT_SECONDS", 3600, minimum=1)
# Gunicorn reads these when app.py is used as its config file.
timeout = env_int("GITMAN_GUNICORN_TIMEOUT_SECONDS", GIT_IMPORT_TIMEOUT_SECONDS + 300, minimum=1)
graceful_timeout = timeout
GIT_IMPORT_NICE = env_int("GITMAN_GIT_IMPORT_NICE", 10, minimum=0)
GIT_IMPORT_PACK_THREADS = env_int("GITMAN_GIT_IMPORT_PACK_THREADS", 1, minimum=1)
GIT_HTTP_NICE = env_int("GITMAN_GIT_HTTP_NICE", 10, minimum=0)
GIT_HTTP_PACK_THREADS = env_int("GITMAN_GIT_HTTP_PACK_THREADS", 1, minimum=1)
MAX_RENDER_BYTES = env_int("GITMAN_MAX_RENDER_BYTES", 256 * 1024)
MAX_GIT_RESPONSE_BYTES = env_int("GITMAN_MAX_GIT_RESPONSE_BYTES", 256 * 1024 * 1024)
PERF_LOG_THRESHOLD_MS = env_int("GITMAN_PERF_LOG_THRESHOLD_MS", 250, minimum=0)
REF_PICKER_LIMIT = env_int("GITMAN_REF_PICKER_LIMIT", 25, minimum=1)
REF_LIST_LIMIT = env_int("GITMAN_REF_LIST_LIMIT", 200, minimum=1)
REF_SEARCH_COMMIT_LIMIT = env_int("GITMAN_REF_SEARCH_COMMIT_LIMIT", 100, minimum=1)
GIT_BINARY = os.environ.get("GITMAN_GIT_BINARY", "git")
PAGES_DOMAIN = os.environ.get("GITMAN_PAGES_DOMAIN", "gitman.io").strip().lower().rstrip(".")
DEFAULT_EXEC_PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
RATE_LIMIT_ENABLED = env_bool("GITMAN_RATE_LIMIT_ENABLED", True)
RATE_LIMIT_MAX_FAILURES = env_int("GITMAN_RATE_LIMIT_MAX_FAILURES", 5, minimum=1)
RATE_LIMIT_WINDOW_SECONDS = env_int("GITMAN_RATE_LIMIT_WINDOW_SECONDS", 300, minimum=1)
RATE_LIMIT_COOLDOWN_SECONDS = env_int("GITMAN_RATE_LIMIT_COOLDOWN_SECONDS", 300, minimum=1)
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{1,62}$")
HOSTNAME_LABEL_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
REV_RE = re.compile(r"^(null|[0-9a-fA-F]{1,40})$")
REF_TYPE_BRANCH = "branch"
REF_TYPE_TAG = "tag"
REF_TYPE_TIP = "tip"
REF_TYPE_COMMIT = "commit"
REF_TYPES = {REF_TYPE_BRANCH, REF_TYPE_TAG, REF_TYPE_TIP, REF_TYPE_COMMIT}
PULL_REQUEST_REF_TYPES = {REF_TYPE_BRANCH, REF_TYPE_TIP}
TARGET_PULL_REQUEST_REF_TYPES = {REF_TYPE_BRANCH}
REF_PICKER_TABS = {"overview", "source", "commits", "tags", "branches"}
REF_QUERY_KEYS = {"ref", "ref_type", "ref_value"}
REF_VALUE_SEPARATOR = "|"
REPO_INDEX_READY = "ready"
REPO_INDEX_INDEXING = "indexing"
DEFAULT_BRANCH_CANDIDATES = ("main", "master")
SCRIPT_STYLE_RE = re.compile(r"(?is)<(script|style)\b[^>]*>.*?</\1>")
PAGES_VERIFY_TXT_PREFIX = "_gitman-pages"
PAGES_VERIFY_VALUE_PREFIX = "gitman-pages-verification="
RESERVED_USERNAMES = {
    "dashboard",
    "favicon.ico",
    "git",
    "hg",
    "login",
    "logout",
    "new",
    "settings",
    "signup",
    "static",
    "harrisonerd",
}
CSRF_COOKIE_NAME = "csrf_token"
CSRF_FORM_FIELD = "_csrf_token"
NULL_REV = "null"
NULL_NODE = "0" * 40
EMPTY_TREE_NODE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
README_CANDIDATES = ("README.md", "README.rst", "README.txt", "README")
MARKDOWN_EXTENSIONS = ("extra", "sane_lists")
MARKDOWN_TAGS = {
    "a",
    "abbr",
    "acronym",
    "blockquote",
    "br",
    "code",
    "del",
    "details",
    "em",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "hr",
    "img",
    "li",
    "ol",
    "p",
    "pre",
    "strong",
    "summary",
    "table",
    "tbody",
    "td",
    "th",
    "thead",
    "tr",
    "ul",
}
MARKDOWN_ATTRIBUTES = {
    "a": ["href", "title"],
    "abbr": ["title"],
    "acronym": ["title"],
    "img": ["alt", "src", "title"],
    "td": ["align"],
    "th": ["align"],
}
MARKDOWN_LINK_TAGS = {"a"}
MARKDOWN_LINK_ATTRIBUTES = {"a": ["href", "title"]}
HIGHLIGHT_LANGUAGE_BY_EXTENSION = {
    ".c": "language-c",
    ".cc": "language-cpp",
    ".cpp": "language-cpp",
    ".cs": "language-csharp",
    ".css": "language-css",
    ".go": "language-go",
    ".h": "language-c",
    ".hpp": "language-cpp",
    ".html": "language-html",
    ".ini": "language-ini",
    ".java": "language-java",
    ".js": "language-javascript",
    ".json": "language-json",
    ".jsx": "language-javascript",
    ".lua": "language-lua",
    ".md": "language-markdown",
    ".php": "language-php",
    ".py": "language-python",
    ".rb": "language-ruby",
    ".rs": "language-rust",
    ".sh": "language-bash",
    ".sql": "language-sql",
    ".toml": "language-ini",
    ".ts": "language-typescript",
    ".tsx": "language-typescript",
    ".txt": "language-plaintext",
    ".xml": "language-xml",
    ".yaml": "language-yaml",
    ".yml": "language-yaml",
}
HIGHLIGHT_LANGUAGE_BY_NAME = {
    "dockerfile": "language-dockerfile",
    "makefile": "language-makefile",
}
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "same-origin",
    "X-Frame-Options": "DENY",
}
CSP_HEADER = (
    "default-src 'self'; "
    "base-uri 'self'; "
    "frame-ancestors 'none'; "
    "form-action 'self'; "
    "object-src 'none'; "
    "img-src 'self' data: http: https:; "
    "style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; "
    "script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com"
)
AUTH_FAILURES = {}
REPO_INDEX_THREADS = set()
REPO_INDEX_LOCK = threading.Lock()

POST_RECEIVE_HOOK = """#!/bin/sh
set_default_head() {
    for candidate in refs/heads/main refs/heads/master
    do
        if git rev-parse --verify -q "$candidate^{commit}" >/dev/null
        then
            git symbolic-ref HEAD "$candidate"
            return 0
        fi
    done

    fallback_ref=$(git for-each-ref --sort=-committerdate --format='%(refname)' refs/heads | sed -n '1p')
    if [ -n "$fallback_ref" ]
    then
        git symbolic-ref HEAD "$fallback_ref"
    fi
}

current_head=$(git symbolic-ref -q HEAD || true)
if [ -n "$current_head" ] && git rev-parse --verify -q "$current_head^{commit}" >/dev/null
then
    exit 0
fi

set_default_head
"""


TEMPLATE_PATH.insert(0, str(BASE_DIR / "templates"))
app = Bottle()


class GitCommandError(RuntimeError):
    def __init__(self, message, returncode=1):
        super().__init__(message)
        self.returncode = returncode


class GitResponseTooLarge(RuntimeError):
    pass


class UploadTooLarge(ValueError):
    pass


class StreamingUpload:
    def __init__(self, filename, file):
        self.filename = filename
        self.file = file


UPLOAD_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,80}$")


def validate_startup_config():
    if not DEBUG and SECRET_KEY == DEFAULT_SECRET_KEY:
        raise RuntimeError("SECRET_KEY must be set to a non-default value when GITMAN_DEBUG is disabled.")


def utcnow():
    return dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def ensure_dirs():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPO_ROOT.mkdir(parents=True, exist_ok=True)


def configure_db_connection(conn):
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute(f"PRAGMA busy_timeout = {SQLITE_BUSY_TIMEOUT_MS}")
    conn.execute("PRAGMA synchronous = NORMAL")


def open_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=SQLITE_BUSY_TIMEOUT_MS / 1000)
    conn.row_factory = sqlite3.Row
    configure_db_connection(conn)
    return conn


@contextmanager
def db_connect():
    conn = open_db_connection()
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def init_db():
    ensure_dirs()
    with db_connect() as conn:
        conn.execute("PRAGMA journal_mode = WAL")
    with db_connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                display_name TEXT NOT NULL DEFAULT '',
                bio TEXT NOT NULL DEFAULT '',
                website TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS repositories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                pages_docs_enabled INTEGER NOT NULL DEFAULT 0,
                forked_from_repo_id INTEGER REFERENCES repositories(id) ON DELETE SET NULL,
                forked_at TEXT,
                forked_from_node TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(owner_id, name)
            );

            CREATE TABLE IF NOT EXISTS issues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                repo_id INTEGER NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
                author_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                number INTEGER NOT NULL,
                title TEXT NOT NULL,
                body TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'open',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                closed_at TEXT,
                UNIQUE(repo_id, number)
            );

            CREATE TABLE IF NOT EXISTS issue_comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                issue_id INTEGER NOT NULL REFERENCES issues(id) ON DELETE CASCADE,
                author_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                body TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS repo_contributors (
                repo_id INTEGER NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                added_by_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                created_at TEXT NOT NULL,
                PRIMARY KEY (repo_id, user_id)
            );

            CREATE TABLE IF NOT EXISTS repo_stars (
                repo_id INTEGER NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                created_at TEXT NOT NULL,
                PRIMARY KEY (repo_id, user_id)
            );

            CREATE TABLE IF NOT EXISTS pull_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target_repo_id INTEGER NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
                source_repo_id INTEGER NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
                author_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                number INTEGER NOT NULL,
                title TEXT NOT NULL,
                body TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'open',
                base_node TEXT NOT NULL,
                source_node TEXT NOT NULL,
                target_ref_type TEXT NOT NULL DEFAULT '',
                target_ref_name TEXT NOT NULL DEFAULT '',
                source_ref_type TEXT NOT NULL DEFAULT '',
                source_ref_name TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                closed_at TEXT,
                merged_at TEXT,
                merged_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                merge_node TEXT NOT NULL DEFAULT '',
                UNIQUE(target_repo_id, number)
            );

            CREATE TABLE IF NOT EXISTS pull_request_comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pull_request_id INTEGER NOT NULL REFERENCES pull_requests(id) ON DELETE CASCADE,
                author_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                body TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS commit_comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                repo_id INTEGER NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
                commit_node TEXT NOT NULL,
                author_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                body TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS custom_domains (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                domain TEXT NOT NULL,
                verification_token TEXT NOT NULL,
                verified_at TEXT,
                last_checked_at TEXT,
                status TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(user_id, domain)
            );

            CREATE TABLE IF NOT EXISTS repo_metadata (
                repo_id INTEGER PRIMARY KEY REFERENCES repositories(id) ON DELETE CASCADE,
                head_node TEXT NOT NULL DEFAULT '',
                default_branch TEXT NOT NULL DEFAULT '',
                commit_count INTEGER NOT NULL DEFAULT 0,
                branch_count INTEGER NOT NULL DEFAULT 0,
                tag_count INTEGER NOT NULL DEFAULT 0,
                branch_refs_json TEXT NOT NULL DEFAULT '[]',
                tag_refs_json TEXT NOT NULL DEFAULT '[]',
                status TEXT NOT NULL DEFAULT '',
                indexed_at TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_repositories_owner ON repositories(owner_id);
            CREATE INDEX IF NOT EXISTS idx_issues_repo_number ON issues(repo_id, number);
            CREATE INDEX IF NOT EXISTS idx_issues_repo_status ON issues(repo_id, status);
            CREATE INDEX IF NOT EXISTS idx_issue_comments_issue ON issue_comments(issue_id);
            CREATE INDEX IF NOT EXISTS idx_repo_contributors_user ON repo_contributors(user_id);
            CREATE INDEX IF NOT EXISTS idx_repo_stars_user ON repo_stars(user_id);
            CREATE INDEX IF NOT EXISTS idx_pull_requests_target_status ON pull_requests(target_repo_id, status);
            CREATE INDEX IF NOT EXISTS idx_pull_requests_source ON pull_requests(source_repo_id);
            CREATE INDEX IF NOT EXISTS idx_pull_request_comments_pull_request ON pull_request_comments(pull_request_id);
            CREATE INDEX IF NOT EXISTS idx_commit_comments_commit ON commit_comments(repo_id, commit_node);
            CREATE INDEX IF NOT EXISTS idx_custom_domains_domain ON custom_domains(domain);
            CREATE INDEX IF NOT EXISTS idx_custom_domains_user ON custom_domains(user_id);
            """
        )
        ensure_user_profile_columns(conn)
        ensure_repository_collaboration_columns(conn)
        ensure_repository_pages_columns(conn)
        ensure_pull_request_ref_columns(conn)
        ensure_repo_metadata_table(conn)


def ensure_user_profile_columns(conn):
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(users)")}
    profile_columns = {
        "display_name": "ALTER TABLE users ADD COLUMN display_name TEXT NOT NULL DEFAULT ''",
        "bio": "ALTER TABLE users ADD COLUMN bio TEXT NOT NULL DEFAULT ''",
        "website": "ALTER TABLE users ADD COLUMN website TEXT NOT NULL DEFAULT ''",
    }
    for name, ddl in profile_columns.items():
        if name not in columns:
            conn.execute(ddl)


def ensure_repository_collaboration_columns(conn):
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(repositories)")}
    collaboration_columns = {
        "forked_from_repo_id": (
            "ALTER TABLE repositories "
            "ADD COLUMN forked_from_repo_id INTEGER REFERENCES repositories(id) ON DELETE SET NULL"
        ),
        "forked_at": "ALTER TABLE repositories ADD COLUMN forked_at TEXT",
        "forked_from_node": "ALTER TABLE repositories ADD COLUMN forked_from_node TEXT NOT NULL DEFAULT ''",
    }
    for name, ddl in collaboration_columns.items():
        if name not in columns:
            conn.execute(ddl)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_repositories_forked_from ON repositories(forked_from_repo_id)")


def ensure_repository_pages_columns(conn):
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(repositories)")}
    if "pages_docs_enabled" not in columns:
        conn.execute("ALTER TABLE repositories ADD COLUMN pages_docs_enabled INTEGER NOT NULL DEFAULT 0")


def ensure_pull_request_ref_columns(conn):
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(pull_requests)")}
    ref_columns = {
        "target_ref_type": "ALTER TABLE pull_requests ADD COLUMN target_ref_type TEXT NOT NULL DEFAULT ''",
        "target_ref_name": "ALTER TABLE pull_requests ADD COLUMN target_ref_name TEXT NOT NULL DEFAULT ''",
        "source_ref_type": "ALTER TABLE pull_requests ADD COLUMN source_ref_type TEXT NOT NULL DEFAULT ''",
        "source_ref_name": "ALTER TABLE pull_requests ADD COLUMN source_ref_name TEXT NOT NULL DEFAULT ''",
    }
    for name, ddl in ref_columns.items():
        if name not in columns:
            conn.execute(ddl)


def ensure_repo_metadata_table(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS repo_metadata (
            repo_id INTEGER PRIMARY KEY REFERENCES repositories(id) ON DELETE CASCADE,
            head_node TEXT NOT NULL DEFAULT '',
            default_branch TEXT NOT NULL DEFAULT '',
            commit_count INTEGER NOT NULL DEFAULT 0,
            branch_count INTEGER NOT NULL DEFAULT 0,
            tag_count INTEGER NOT NULL DEFAULT 0,
            branch_refs_json TEXT NOT NULL DEFAULT '[]',
            tag_refs_json TEXT NOT NULL DEFAULT '[]',
            status TEXT NOT NULL DEFAULT '',
            indexed_at TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL
        )
        """
    )


def normalize_slug(value, label):
    slug = (value or "").strip().lower()
    if not SLUG_RE.match(slug):
        raise ValueError(f"{label} must be 2-63 characters: lowercase letters, numbers, dots, dashes, or underscores.")
    if label.lower().startswith("username") and slug in RESERVED_USERNAMES:
        raise ValueError("Username is reserved.")
    if slug in {".", ".."} or slug.endswith(".git"):
        raise ValueError(f"{label} is reserved.")
    return slug


def clean_repo_path(path):
    raw = (path or "").strip("/")
    if not raw:
        return ""
    raw_parts = raw.split("/")
    if any(part in {"", ".", ".."} for part in raw_parts):
        abort(400, "Invalid repository path.")
    parts = PurePosixPath(raw).parts
    if any(part in {"", ".", ".."} for part in parts):
        abort(400, "Invalid repository path.")
    return "/".join(parts)


def hash_password(password):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("ascii"),
        PASSWORD_ITERATIONS,
    ).hex()
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${salt}${digest}"


def verify_password(password, stored_hash):
    try:
        algorithm, iterations, salt, expected = stored_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("ascii"),
            int(iterations),
        ).hex()
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(digest, expected)


def get_user_by_id(user_id):
    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        return None
    with db_connect() as conn:
        return conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def get_user_by_username(username):
    with db_connect() as conn:
        return conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()


def current_user():
    return request.environ.get("gitman.user")


def request_is_secure():
    forwarded = request.get_header("X-Forwarded-Proto", "")
    if forwarded:
        return forwarded.split(",", 1)[0].strip().lower() == "https"
    return request.urlparts.scheme == "https"


def is_git_request_path():
    path = request.environ.get("PATH_INFO", request.path) or ""
    return path == "/git" or path.startswith("/git/")


def csrf_token():
    token = request.environ.get("gitman.csrf_token")
    if token:
        return token

    token = request.get_cookie(CSRF_COOKIE_NAME, secret=SECRET_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        response.set_cookie(
            CSRF_COOKIE_NAME,
            token,
            secret=SECRET_KEY,
            httponly=True,
            secure=request_is_secure(),
            samesite="Lax",
            path="/",
        )
    request.environ["gitman.csrf_token"] = token
    return token


def csrf_field():
    return (
        f'<input type="hidden" name="{CSRF_FORM_FIELD}" '
        f'value="{html.escape(csrf_token(), quote=True)}">'
    )


def request_content_type():
    return (request.environ.get("CONTENT_TYPE") or request.get_header("Content-Type") or "").lower()


def validate_csrf_token():
    expected = request.get_cookie(CSRF_COOKIE_NAME, secret=SECRET_KEY)
    submitted = request.get_header("X-CSRF-Token", "") or request.query.get(CSRF_FORM_FIELD, "")
    if not submitted and not request_content_type().startswith("application/octet-stream"):
        submitted = request.forms.get(CSRF_FORM_FIELD, "")
    if not expected or not submitted or not hmac.compare_digest(expected, submitted):
        abort(403, "Invalid CSRF token.")


def request_content_length():
    try:
        return int(request.environ.get("CONTENT_LENGTH") or 0)
    except ValueError:
        return 0


def is_repo_settings_multipart_request():
    path = request.environ.get("PATH_INFO", request.path) or ""
    return path.endswith("/settings") and request_content_type().startswith("multipart/form-data")


def is_repo_settings_import_stream_request():
    path = request.environ.get("PATH_INFO", request.path) or ""
    return (
        (
            path.endswith("/settings/import-bundle")
            or path.endswith("/settings/import-bundle/chunk")
        )
        and request_content_type().startswith("application/octet-stream")
    )


def browser_post_size_limit():
    if is_repo_settings_multipart_request() or is_repo_settings_import_stream_request():
        return MAX_IMPORT_BYTES
    return MAX_FORM_BYTES


def auth_rate_key(kind, identifier=""):
    identifier = (identifier or "").strip().lower()[:100]
    remote_addr = request.environ.get("REMOTE_ADDR", "")
    return f"{kind}:{remote_addr}:{identifier}"


def rate_limit_blocked(kind, identifier=""):
    if not RATE_LIMIT_ENABLED:
        return False
    now = time.time()
    prune_auth_failures(now)
    record = AUTH_FAILURES.get(auth_rate_key(kind, identifier))
    return bool(record and record.get("blocked_until", 0) > now)


def prune_auth_failures(now=None):
    now = now or time.time()
    for key, record in list(AUTH_FAILURES.items()):
        if record.get("reset_at", 0) <= now and record.get("blocked_until", 0) <= now:
            AUTH_FAILURES.pop(key, None)


def record_auth_failure(kind, identifier=""):
    if not RATE_LIMIT_ENABLED:
        return
    now = time.time()
    prune_auth_failures(now)
    key = auth_rate_key(kind, identifier)
    record = AUTH_FAILURES.get(key)
    if not record or record.get("reset_at", 0) <= now:
        record = {"count": 0, "reset_at": now + RATE_LIMIT_WINDOW_SECONDS, "blocked_until": 0}
    record["count"] += 1
    if record["count"] >= RATE_LIMIT_MAX_FAILURES:
        record["blocked_until"] = now + RATE_LIMIT_COOLDOWN_SECONDS
    AUTH_FAILURES[key] = record


def clear_auth_failures(kind, identifier=""):
    AUTH_FAILURES.pop(auth_rate_key(kind, identifier), None)


def too_many_requests_response():
    headers = {"Retry-After": str(RATE_LIMIT_COOLDOWN_SECONDS)}
    return HTTPResponse(
        "Too many failed attempts. Try again later.\n",
        status=429,
        headers=headers,
        content_type="text/plain; charset=utf-8",
    )


@app.hook("before_request")
def load_current_user():
    user_id = request.get_cookie("session", secret=SECRET_KEY)
    request.environ["gitman.user"] = get_user_by_id(user_id) if user_id else None


@app.hook("before_request")
def dispatch_pages_host():
    response_for_host = pages_response_for_request_host()
    if response_for_host is not None:
        raise response_for_host


@app.hook("before_request")
def enforce_browser_post_security():
    if request.method != "POST" or is_git_request_path():
        return
    size_limit = browser_post_size_limit()
    if size_limit and request_content_length() > size_limit:
        abort(413, "Request body too large.")
    validate_csrf_token()


@app.hook("after_request")
def add_security_headers():
    if request.environ.get("gitman.pages_response"):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        return
    for key, value in SECURITY_HEADERS.items():
        response.headers.setdefault(key, value)
    if not is_git_request_path():
        response.headers.setdefault("Content-Security-Policy", CSP_HEADER)


def render(template_name, **context):
    context.setdefault("user", current_user())
    context.setdefault("error", None)
    context.setdefault("notice", None)
    context.setdefault("csrf_field", csrf_field)
    context.setdefault("render_markdown_links", render_markdown_links)
    context.setdefault("render_repo_description", render_repo_description)
    context.setdefault("format_ref_label", format_ref_label)
    context.setdefault("url_with_ref", url_with_ref)
    context.setdefault("current_url_with_ref", current_url_with_ref)
    context.setdefault("ref_option_label", ref_option_label)
    return template(template_name, **context)


def login_user(user):
    response.set_cookie(
        "session",
        str(user["id"]),
        secret=SECRET_KEY,
        httponly=True,
        secure=request_is_secure(),
        samesite="Lax",
        path="/",
    )


def logout_user():
    response.delete_cookie("session", path="/")


def require_login():
    user = current_user()
    if user:
        return user
    next_url = request.fullpath if request.query_string else request.path
    redirect("/login?next=" + quote(next_url, safe="/?=&"))


def safe_next_url(value):
    if value and value.startswith("/") and not value.startswith("//"):
        return value
    return "/"


def repo_path(owner_username, repo_name):
    path = REPO_ROOT / owner_username / repo_name
    root = REPO_ROOT.resolve()
    resolved = path.resolve()
    if root != resolved and root not in resolved.parents:
        abort(400, "Invalid repository path.")
    return path


def get_repo(owner_username, repo_name):
    with db_connect() as conn:
        return conn.execute(
            """
            SELECT repositories.*, users.username AS owner_username
            FROM repositories
            JOIN users ON users.id = repositories.owner_id
            WHERE users.username = ? AND repositories.name = ?
            """,
            (owner_username, repo_name),
        ).fetchone()


def get_repo_by_id(repo_id):
    with db_connect() as conn:
        return conn.execute(
            """
            SELECT repositories.*, users.username AS owner_username
            FROM repositories
            JOIN users ON users.id = repositories.owner_id
            WHERE repositories.id = ?
            """,
            (repo_id,),
        ).fetchone()


def list_public_repos(limit=100):
    with db_connect() as conn:
        return conn.execute(
            """
            SELECT repositories.*, users.username AS owner_username
            FROM repositories
            JOIN users ON users.id = repositories.owner_id
            ORDER BY repositories.updated_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()


def fuzzy_match_score(value, query):
    value = (value or "").lower()
    query = (query or "").lower()
    if not value or not query:
        return None
    if query == value:
        return (0, len(value))
    if value.startswith(query):
        return (1, len(value))
    if query in value:
        return (2, value.index(query), len(value))

    positions = []
    start = 0
    for char in query:
        index = value.find(char, start)
        if index < 0:
            return None
        positions.append(index)
        start = index + 1
    return (3, positions[-1] - positions[0], positions[0], len(value))


def compact_search_text(value):
    return re.sub(r"[^a-z0-9]+", "", (value or "").lower())


def repository_search_score(repo, query):
    query = (query or "").strip().lower()
    if not query:
        return None

    name = repo["name"]
    full_name = f"{repo['owner_username']}/{repo['name']}"
    query_compact = compact_search_text(query)
    candidates = [
        (0, name, query),
        (1, compact_search_text(name), query_compact),
        (2, full_name, query),
        (3, compact_search_text(full_name), query_compact),
    ]

    scores = []
    for weight, value, candidate_query in candidates:
        if not candidate_query:
            continue
        score = fuzzy_match_score(value, candidate_query)
        if score is not None:
            scores.append((weight, *score))
    return min(scores) if scores else None


def repo_search_result(repo):
    full_name = f"{repo['owner_username']}/{repo['name']}"
    result = {
        "owner_username": repo["owner_username"],
        "name": repo["name"],
        "full_name": full_name,
        "url": f"/{full_name}",
        "description": text_preview(repo["description"], 120),
        "updated_at": repo["updated_at"],
    }
    if "star_count" in repo.keys():
        result["star_count"] = repo["star_count"]
    return result


def search_public_repos(query, limit=10):
    query = (query or "").strip()[:100]
    if not query:
        return []

    with db_connect() as conn:
        repos = conn.execute(
            """
            SELECT
                repositories.*,
                users.username AS owner_username,
                (
                    SELECT COUNT(*)
                    FROM repo_stars
                    WHERE repo_stars.repo_id = repositories.id
                ) AS star_count
            FROM repositories
            JOIN users ON users.id = repositories.owner_id
            ORDER BY repositories.updated_at DESC
            """
        ).fetchall()

    matches = []
    for repo in repos:
        score = repository_search_score(repo, query)
        if score is not None:
            matches.append((score, repo))
    matches.sort(key=lambda match: (match[0], match[1]["name"], match[1]["owner_username"]))
    return [repo_search_result(repo) for _, repo in matches[: max(1, min(int(limit), 25))]]


def text_preview(value, limit=180):
    text = " ".join((value or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def parse_activity_time(value):
    raw = (value or "").strip()
    if not raw:
        return dt.datetime.min.replace(tzinfo=dt.UTC)
    candidates = [raw]
    if raw.endswith("Z"):
        candidates.append(raw[:-1] + "+00:00")
    for candidate in candidates:
        try:
            parsed = dt.datetime.fromisoformat(candidate)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=dt.UTC)
            return parsed.astimezone(dt.UTC)
        except ValueError:
            pass
    for date_format in ("%Y-%m-%d %H:%M:%S %z", "%Y-%m-%d %H:%M %z"):
        try:
            return dt.datetime.strptime(raw, date_format).astimezone(dt.UTC)
        except ValueError:
            pass
    return dt.datetime.min.replace(tzinfo=dt.UTC)


def activity_sort_key(action):
    return (
        parse_activity_time(action["occurred_at"]),
        action["kind"],
        action["target_url"],
    )


def normalize_activity_action(row):
    action = dict(row)
    actor_username = action.get("actor_username") or ""
    action["actor_label"] = f"@{actor_username}" if actor_username else ""
    action["actor_url"] = f"/{actor_username}" if actor_username else ""
    action["detail"] = text_preview(action["detail"])
    return action


def list_activity_repositories():
    with db_connect() as conn:
        return conn.execute(
            """
            SELECT repositories.*, users.username AS owner_username
            FROM repositories
            JOIN users ON users.id = repositories.owner_id
            ORDER BY repositories.created_at DESC
            """
        ).fetchall()


def list_commit_activity_actions(limit):
    actions = []
    for repo in list_activity_repositories():
        path = repo_path(repo["owner_username"], repo["name"])
        try:
            commits = commit_log(path, limit=limit)
        except (GitCommandError, OSError):
            continue
        for commit in commits:
            actions.append(
                {
                    "kind": "commit_created",
                    "occurred_at": commit["date"],
                    "actor_username": "",
                    "actor_label": commit["author"],
                    "actor_url": "",
                    "repo_owner_username": repo["owner_username"],
                    "repo_name": repo["name"],
                    "target_url": f"/{repo['owner_username']}/{repo['name']}/commits/{commit['node']}",
                    "target_label": commit["short_node"],
                    "summary": "committed",
                    "detail": text_preview(commit["summary"]),
                }
            )
    return actions


def list_recent_actions(limit=50):
    limit = max(1, min(int(limit), 100))
    with db_connect() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM (
                SELECT
                    CASE
                        WHEN repositories.forked_from_repo_id IS NULL THEN 'repo_created'
                        ELSE 'repo_forked'
                    END AS kind,
                    repositories.created_at AS occurred_at,
                    owner.username AS actor_username,
                    owner.username AS repo_owner_username,
                    repositories.name AS repo_name,
                    '/' || owner.username || '/' || repositories.name AS target_url,
                    owner.username || '/' || repositories.name AS target_label,
                    CASE
                        WHEN repositories.forked_from_repo_id IS NULL THEN 'created repository'
                        ELSE 'forked repository'
                    END AS summary,
                    repositories.description AS detail
                FROM repositories
                JOIN users AS owner ON owner.id = repositories.owner_id

                UNION ALL

                SELECT
                    'repo_starred' AS kind,
                    repo_stars.created_at AS occurred_at,
                    actor.username AS actor_username,
                    owner.username AS repo_owner_username,
                    repositories.name AS repo_name,
                    '/' || owner.username || '/' || repositories.name AS target_url,
                    owner.username || '/' || repositories.name AS target_label,
                    'starred repository' AS summary,
                    '' AS detail
                FROM repo_stars
                JOIN users AS actor ON actor.id = repo_stars.user_id
                JOIN repositories ON repositories.id = repo_stars.repo_id
                JOIN users AS owner ON owner.id = repositories.owner_id

                UNION ALL

                SELECT
                    'contributor_added' AS kind,
                    repo_contributors.created_at AS occurred_at,
                    actor.username AS actor_username,
                    owner.username AS repo_owner_username,
                    repositories.name AS repo_name,
                    '/' || owner.username || '/' || repositories.name AS target_url,
                    owner.username || '/' || repositories.name AS target_label,
                    'added contributor' AS summary,
                    contributor.username AS detail
                FROM repo_contributors
                JOIN users AS actor ON actor.id = repo_contributors.added_by_id
                JOIN users AS contributor ON contributor.id = repo_contributors.user_id
                JOIN repositories ON repositories.id = repo_contributors.repo_id
                JOIN users AS owner ON owner.id = repositories.owner_id

                UNION ALL

                SELECT
                    'issue_opened' AS kind,
                    issues.created_at AS occurred_at,
                    actor.username AS actor_username,
                    owner.username AS repo_owner_username,
                    repositories.name AS repo_name,
                    '/' || owner.username || '/' || repositories.name || '/issues/' || issues.number AS target_url,
                    '#' || issues.number || ' ' || issues.title AS target_label,
                    'opened issue' AS summary,
                    issues.body AS detail
                FROM issues
                JOIN users AS actor ON actor.id = issues.author_id
                JOIN repositories ON repositories.id = issues.repo_id
                JOIN users AS owner ON owner.id = repositories.owner_id

                UNION ALL

                SELECT
                    'issue_commented' AS kind,
                    issue_comments.created_at AS occurred_at,
                    actor.username AS actor_username,
                    owner.username AS repo_owner_username,
                    repositories.name AS repo_name,
                    '/' || owner.username || '/' || repositories.name || '/issues/' || issues.number AS target_url,
                    '#' || issues.number || ' ' || issues.title AS target_label,
                    'commented on issue' AS summary,
                    issue_comments.body AS detail
                FROM issue_comments
                JOIN users AS actor ON actor.id = issue_comments.author_id
                JOIN issues ON issues.id = issue_comments.issue_id
                JOIN repositories ON repositories.id = issues.repo_id
                JOIN users AS owner ON owner.id = repositories.owner_id

                UNION ALL

                SELECT
                    'pull_request_opened' AS kind,
                    pull_requests.created_at AS occurred_at,
                    actor.username AS actor_username,
                    owner.username AS repo_owner_username,
                    repositories.name AS repo_name,
                    '/' || owner.username || '/' || repositories.name || '/pulls/' || pull_requests.number AS target_url,
                    '#' || pull_requests.number || ' ' || pull_requests.title AS target_label,
                    'opened pull request' AS summary,
                    pull_requests.body AS detail
                FROM pull_requests
                JOIN users AS actor ON actor.id = pull_requests.author_id
                JOIN repositories ON repositories.id = pull_requests.target_repo_id
                JOIN users AS owner ON owner.id = repositories.owner_id

                UNION ALL

                SELECT
                    'pull_request_commented' AS kind,
                    pull_request_comments.created_at AS occurred_at,
                    actor.username AS actor_username,
                    owner.username AS repo_owner_username,
                    repositories.name AS repo_name,
                    '/' || owner.username || '/' || repositories.name || '/pulls/' || pull_requests.number AS target_url,
                    '#' || pull_requests.number || ' ' || pull_requests.title AS target_label,
                    'commented on pull request' AS summary,
                    pull_request_comments.body AS detail
                FROM pull_request_comments
                JOIN users AS actor ON actor.id = pull_request_comments.author_id
                JOIN pull_requests ON pull_requests.id = pull_request_comments.pull_request_id
                JOIN repositories ON repositories.id = pull_requests.target_repo_id
                JOIN users AS owner ON owner.id = repositories.owner_id

                UNION ALL

                SELECT
                    'pull_request_merged' AS kind,
                    pull_requests.merged_at AS occurred_at,
                    actor.username AS actor_username,
                    owner.username AS repo_owner_username,
                    repositories.name AS repo_name,
                    '/' || owner.username || '/' || repositories.name || '/pulls/' || pull_requests.number AS target_url,
                    '#' || pull_requests.number || ' ' || pull_requests.title AS target_label,
                    'merged pull request' AS summary,
                    pull_requests.merge_node AS detail
                FROM pull_requests
                JOIN users AS actor ON actor.id = pull_requests.merged_by_id
                JOIN repositories ON repositories.id = pull_requests.target_repo_id
                JOIN users AS owner ON owner.id = repositories.owner_id
                WHERE pull_requests.merged_at IS NOT NULL

                UNION ALL

                SELECT
                    'commit_commented' AS kind,
                    commit_comments.created_at AS occurred_at,
                    actor.username AS actor_username,
                    owner.username AS repo_owner_username,
                    repositories.name AS repo_name,
                    '/' || owner.username || '/' || repositories.name || '/commits/' || commit_comments.commit_node AS target_url,
                    substr(commit_comments.commit_node, 1, 12) AS target_label,
                    'commented on commit' AS summary,
                    commit_comments.body AS detail
                FROM commit_comments
                JOIN users AS actor ON actor.id = commit_comments.author_id
                JOIN repositories ON repositories.id = commit_comments.repo_id
                JOIN users AS owner ON owner.id = repositories.owner_id

                UNION ALL

                SELECT
                    'user_joined' AS kind,
                    users.created_at AS occurred_at,
                    users.username AS actor_username,
                    '' AS repo_owner_username,
                    '' AS repo_name,
                    '/' || users.username AS target_url,
                    '@' || users.username AS target_label,
                    'joined' AS summary,
                    '' AS detail
                FROM users
            )
            WHERE occurred_at IS NOT NULL
            ORDER BY occurred_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    actions = [normalize_activity_action(row) for row in rows]
    actions.extend(list_commit_activity_actions(limit))
    actions.sort(key=activity_sort_key, reverse=True)
    return actions[:limit]


def list_owned_repos(owner_id):
    with db_connect() as conn:
        return conn.execute(
            """
            SELECT repositories.*, users.username AS owner_username, COUNT(repo_stars.user_id) AS star_count
            FROM repositories
            JOIN users ON users.id = repositories.owner_id
            LEFT JOIN repo_stars ON repo_stars.repo_id = repositories.id
            WHERE repositories.owner_id = ?
            GROUP BY repositories.id
            ORDER BY repositories.updated_at DESC
            """,
            (owner_id,),
        ).fetchall()


def list_starred_repos(user_id):
    with db_connect() as conn:
        return conn.execute(
            """
            SELECT
                repositories.*,
                users.username AS owner_username,
                repo_stars.created_at AS starred_at,
                (
                    SELECT COUNT(*)
                    FROM repo_stars AS counts
                    WHERE counts.repo_id = repositories.id
                ) AS star_count
            FROM repo_stars
            JOIN repositories ON repositories.id = repo_stars.repo_id
            JOIN users ON users.id = repositories.owner_id
            WHERE repo_stars.user_id = ?
            ORDER BY repo_stars.created_at DESC
            """,
            (user_id,),
        ).fetchall()


def list_user_forks_for_target(user_id, target_repo_id):
    with db_connect() as conn:
        return conn.execute(
            """
            SELECT repositories.*, users.username AS owner_username
            FROM repositories
            JOIN users ON users.id = repositories.owner_id
            WHERE repositories.owner_id = ?
              AND repositories.forked_from_repo_id = ?
            ORDER BY repositories.updated_at DESC
            """,
            (user_id, target_repo_id),
        ).fetchall()


def user_has_fork_for_target(user_id, target_repo_id):
    with db_connect() as conn:
        row = conn.execute(
            """
            SELECT 1
            FROM repositories
            WHERE owner_id = ?
              AND forked_from_repo_id = ?
            LIMIT 1
            """,
            (user_id, target_repo_id),
        ).fetchone()
    return bool(row)


def list_repo_contributors(repo_id):
    with db_connect() as conn:
        return conn.execute(
            """
            SELECT users.*, repo_contributors.created_at AS contributor_since
            FROM repo_contributors
            JOIN users ON users.id = repo_contributors.user_id
            WHERE repo_contributors.repo_id = ?
            ORDER BY users.username
            """,
            (repo_id,),
        ).fetchall()


def repo_contributor_usernames(repo_id):
    return [row["username"] for row in list_repo_contributors(repo_id)]


def repo_star_count(repo_id):
    with db_connect() as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM repo_stars WHERE repo_id = ?",
            (repo_id,),
        ).fetchone()[0]


def user_starred_repo(user, repo):
    if not user or not repo:
        return False
    with db_connect() as conn:
        row = conn.execute(
            "SELECT 1 FROM repo_stars WHERE repo_id = ? AND user_id = ?",
            (repo["id"], user["id"]),
        ).fetchone()
    return bool(row)


def star_repo(user, repo):
    with db_connect() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO repo_stars (repo_id, user_id, created_at)
            VALUES (?, ?, ?)
            """,
            (repo["id"], user["id"], utcnow()),
        )


def unstar_repo(user, repo):
    with db_connect() as conn:
        conn.execute(
            "DELETE FROM repo_stars WHERE repo_id = ? AND user_id = ?",
            (repo["id"], user["id"]),
        )


def normalize_website(value):
    website = (value or "").strip()
    if not website:
        return ""
    if any(char.isspace() for char in website):
        raise ValueError("Website must be a valid http(s) URL.")
    if "://" not in website:
        website = "https://" + website
    parsed = urlparse(website)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Website must be a valid http(s) URL.")
    return website[:255]


def profile_form_values(form, fallback=None):
    fallback = dict(fallback) if fallback else {}
    return {
        "username": fallback.get("username", ""),
        "display_name": (form.get("display_name", fallback.get("display_name", "")) or "").strip()[:80],
        "bio": (form.get("bio", fallback.get("bio", "")) or "").strip()[:1000],
        "website": (form.get("website", fallback.get("website", "")) or "").strip(),
        "created_at": fallback.get("created_at", ""),
    }


def install_repo_hooks(path):
    hooks_dir = path / "hooks"
    hooks_dir.mkdir(exist_ok=True)
    post_receive = hooks_dir / "post-receive"
    post_receive.write_text(POST_RECEIVE_HOOK, encoding="utf-8")
    post_receive.chmod(0o755)


def prepare_repo_for_receive(path):
    install_repo_hooks(path)
    run_git(["config", "receive.denyDeleteCurrent", "warn"], cwd=path)


def write_git_metadata(path, owner_username, repo_name, description):
    safe_description = " ".join((description or "").splitlines()).strip()
    description_file = path / "description"
    if description_file.exists():
        description_file.write_text(safe_description or f"{owner_username}/{repo_name}", encoding="utf-8")
    prepare_repo_for_receive(path)
    run_git(["config", "gitman.owner", owner_username], cwd=path)
    run_git(["config", "gitman.name", repo_name], cwd=path)
    run_git(["config", "gitman.description", safe_description], cwd=path)
    run_git(["config", "http.receivepack", "true"], cwd=path)


def sync_repo_git_config(repo):
    path = repo_path(repo["owner_username"], repo["name"])
    write_git_metadata(path, repo["owner_username"], repo["name"], repo["description"])


def git_env():
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    path_parts = [part for part in env.get("PATH", "").split(os.pathsep) if part]
    for part in DEFAULT_EXEC_PATH.split(os.pathsep):
        if part not in path_parts:
            path_parts.append(part)
    env["PATH"] = os.pathsep.join(path_parts)
    return env


def git_executable(env):
    if os.path.isabs(GIT_BINARY):
        return GIT_BINARY
    executable = shutil.which(GIT_BINARY, path=env.get("PATH"))
    if executable:
        return executable
    raise GitCommandError(
        "Git executable not found. Install git or set GITMAN_GIT_BINARY to the full path, such as /usr/bin/git.",
        127,
    )


def log_perf(label, elapsed_seconds, detail=""):
    if PERF_LOG_THRESHOLD_MS <= 0:
        return
    elapsed_ms = int(elapsed_seconds * 1000)
    if elapsed_ms < PERF_LOG_THRESHOLD_MS:
        return
    suffix = f" {detail}" if detail else ""
    print(f"[gitman-perf] {label} took {elapsed_ms}ms{suffix}", file=sys.stderr, flush=True)


def run_git(args, cwd=None, timeout=15, check=True, text=True, nice_value=0, git_config=None):
    env = git_env()
    command = [git_executable(env)]
    for key, value in (git_config or {}).items():
        command.extend(["-c", f"{key}={value}"])
    command.extend(args)
    if nice_value > 0:
        command = ["nice", "-n", str(nice_value), *command]
    started = time.monotonic()
    completed = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=text,
        encoding="utf-8" if text else None,
        errors="replace" if text else None,
        timeout=timeout,
        env=env,
    )
    log_perf("git", time.monotonic() - started, " ".join(args[:4]))
    if check and completed.returncode != 0:
        stderr = completed.stderr if text else completed.stderr.decode("utf-8", "replace")
        raise GitCommandError(stderr.strip() or "Git command failed.", completed.returncode)
    return completed


def create_repository(owner, name, description):
    now = utcnow()
    path = repo_path(owner["username"], name)
    if path.exists():
        raise ValueError("Repository directory already exists.")
    path.parent.mkdir(parents=True, exist_ok=True)

    with db_connect() as conn:
        try:
            conn.execute(
                """
                INSERT INTO repositories (owner_id, name, description, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (owner["id"], name, description, now, now),
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError("Repository already exists.") from exc

    try:
        run_git(["init", "--bare", str(path)], timeout=20)
        run_git(["symbolic-ref", "HEAD", "refs/heads/main"], cwd=path)
        write_git_metadata(path, owner["username"], name, description)
        repo = get_repo(owner["username"], name)
        if repo:
            write_repo_metadata(repo, path)
    except Exception:
        with db_connect() as conn:
            conn.execute(
                "DELETE FROM repositories WHERE owner_id = ? AND name = ?",
                (owner["id"], name),
            )
        if path.exists():
            shutil.rmtree(path)
        raise


def fork_repository(owner, source_repo, name, description):
    now = utcnow()
    source_path = repo_path(source_repo["owner_username"], source_repo["name"])
    path = repo_path(owner["username"], name)
    if path.exists():
        raise ValueError("Repository directory already exists.")
    path.parent.mkdir(parents=True, exist_ok=True)
    upstream_repo_id = source_repo["forked_from_repo_id"] or source_repo["id"]
    forked_from_node = (
        source_repo["forked_from_node"]
        if source_repo["forked_from_repo_id"] and source_repo["forked_from_node"]
        else default_code_ref(source_path).get("node") or NULL_REV
    )

    with db_connect() as conn:
        try:
            conn.execute(
                """
                INSERT INTO repositories (
                    owner_id, name, description, forked_from_repo_id,
                    forked_at, forked_from_node, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    owner["id"],
                    name,
                    description,
                    upstream_repo_id,
                    now,
                    forked_from_node,
                    now,
                    now,
                ),
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError("Repository already exists.") from exc

    try:
        run_git(["clone", "--bare", str(source_path), str(path)], timeout=60)
        write_git_metadata(path, owner["username"], name, description)
        repo = get_repo(owner["username"], name)
        if repo:
            mark_repo_indexing(repo["id"], path)
            schedule_repo_metadata_refresh(repo["id"])
    except Exception:
        with db_connect() as conn:
            conn.execute(
                "DELETE FROM repositories WHERE owner_id = ? AND name = ?",
                (owner["id"], name),
            )
        if path.exists():
            shutil.rmtree(path)
        raise


def run_git_import(args, cwd=None, check=True):
    git_config = {"pack.threads": GIT_IMPORT_PACK_THREADS}
    try:
        return run_git(
            args,
            cwd=cwd,
            timeout=GIT_IMPORT_TIMEOUT_SECONDS,
            check=check,
            nice_value=GIT_IMPORT_NICE,
            git_config=git_config,
        )
    except subprocess.TimeoutExpired as exc:
        raise GitCommandError("Git import timed out.", 124) from exc


def apply_git_config_env(env, git_config):
    if not git_config:
        return
    base_count = int(env.get("GIT_CONFIG_COUNT", "0") or 0)
    for offset, (key, value) in enumerate(git_config.items()):
        index = base_count + offset
        env[f"GIT_CONFIG_KEY_{index}"] = str(key)
        env[f"GIT_CONFIG_VALUE_{index}"] = str(value)
    env["GIT_CONFIG_COUNT"] = str(base_count + len(git_config))


def repo_is_empty(path):
    return commit_count(path) == 0


def save_bundle_upload(upload, destination):
    if not upload or not getattr(upload, "filename", ""):
        raise ValueError("Choose a Git bundle to import.")

    size = 0
    source = upload.file
    try:
        source.seek(0)
    except (AttributeError, OSError):
        pass

    try:
        with destination.open("wb") as target:
            while True:
                chunk = source.read(IMPORT_UPLOAD_CHUNK_BYTES)
                if not chunk:
                    break
                size += len(chunk)
                if MAX_IMPORT_BYTES and size > MAX_IMPORT_BYTES:
                    raise UploadTooLarge("Request body too large.")
                target.write(chunk)
    except UploadTooLarge:
        if destination.exists():
            destination.unlink()
        raise

    if size == 0:
        raise ValueError("Uploaded bundle is empty.")


def import_upload_chunks_dir():
    path = Path(tempfile.gettempdir()) / "gitman-import-chunks"
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    cleanup_stale_upload_chunks(path)
    return path


def cleanup_stale_upload_chunks(path):
    if not IMPORT_UPLOAD_STALE_SECONDS:
        return
    cutoff = time.time() - IMPORT_UPLOAD_STALE_SECONDS
    for chunk_path in path.glob("*.bundle"):
        try:
            if chunk_path.stat().st_mtime < cutoff:
                chunk_path.unlink()
        except OSError:
            pass


def parse_nonnegative_int(value, name):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        abort(400, f"Invalid {name}.")
    if parsed < 0:
        abort(400, f"Invalid {name}.")
    return parsed


def save_upload_chunk(source, destination, expected_size, offset):
    written = 0
    with destination.open("ab") as target:
        remaining = expected_size
        while remaining > 0:
            chunk = source.read(min(IMPORT_UPLOAD_CHUNK_BYTES, remaining))
            if not chunk:
                break
            target.write(chunk)
            written += len(chunk)
            remaining -= len(chunk)
    if written != expected_size:
        try:
            with destination.open("r+b") as target:
                target.truncate(offset)
        except OSError:
            pass
        raise ValueError("Upload chunk was incomplete.")
    return written


def discard_upload_chunk(source, expected_size):
    remaining = expected_size
    while remaining > 0:
        chunk = source.read(min(IMPORT_UPLOAD_CHUNK_BYTES, remaining))
        if not chunk:
            break
        remaining -= len(chunk)


def import_complete_upload_chunk(repo, path, filename, chunk_path):
    with chunk_path.open("rb") as bundle_file:
        import_git_bundle(repo, path, StreamingUpload(filename, bundle_file))
    updated_repo = get_repo(repo["owner_username"], repo["name"])
    return render_repo_settings_page(updated_repo, path, notice="Git bundle imported.")


def bundle_ref_names(bundle_path):
    completed = run_git_import(["bundle", "list-heads", str(bundle_path)])
    refs = []
    for line in completed.stdout.splitlines():
        parts = line.strip().split(maxsplit=1)
        if len(parts) == 2:
            refs.append(parts[1])
    return refs


def origin_branch_refspecs_for_bundle(bundle_path):
    refs = bundle_ref_names(bundle_path)
    branch_names = {ref.removeprefix("refs/heads/") for ref in refs if ref.startswith("refs/heads/")}
    refspecs = []
    prefix = "refs/remotes/origin/"
    for ref in refs:
        if not ref.startswith(prefix):
            continue
        branch_name = ref[len(prefix) :]
        if not branch_name or branch_name == "HEAD" or branch_name in branch_names:
            continue
        refspecs.append(f"+{ref}:refs/heads/{branch_name}")
        branch_names.add(branch_name)
    return refspecs


def fetch_bundle_refspecs(bundle_path, staging_path, refspecs):
    for index in range(0, len(refspecs), 100):
        run_git_import(["fetch", str(bundle_path), *refspecs[index : index + 100]], cwd=staging_path)


def import_git_bundle(repo, path, upload):
    if not path.exists():
        raise ValueError("Repository directory does not exist.")
    if not repo_is_empty(path):
        raise ValueError("Git bundles can only be imported into empty repositories.")

    owner = repo["owner_username"]
    name = repo["name"]
    bundle_path = None
    staging_path = None
    backup_path = None
    moved_target_to_backup = False
    installed_staging = False
    success = False

    try:
        with tempfile.NamedTemporaryFile(prefix="gitman-import-", suffix=".bundle", delete=False) as bundle_file:
            bundle_path = Path(bundle_file.name)
        save_bundle_upload(upload, bundle_path)

        verification = run_git_import(["bundle", "verify", str(bundle_path)], cwd=path, check=False)
        if verification.returncode != 0:
            raise ValueError("Uploaded file is not a valid Git bundle.")

        staging_path = Path(tempfile.mkdtemp(prefix=f".{name}-import-", dir=path.parent))
        shutil.rmtree(staging_path)
        run_git_import(["init", "--bare", str(staging_path)])
        run_git_import(
            [
                "fetch",
                str(bundle_path),
                "+refs/heads/*:refs/heads/*",
                "+refs/tags/*:refs/tags/*",
            ],
            cwd=staging_path,
        )
        fetch_bundle_refspecs(bundle_path, staging_path, origin_branch_refspecs_for_bundle(bundle_path))
        if not list_repo_branches(staging_path):
            raise ValueError("Uploaded Git bundle does not contain any branches.")
        default_code_ref(staging_path)
        write_git_metadata(staging_path, owner, name, repo["description"])

        if not repo_is_empty(path):
            raise ValueError("Repository is no longer empty.")

        backup_path = path.with_name(f".{name}-import-backup-{secrets.token_hex(8)}")
        path.rename(backup_path)
        moved_target_to_backup = True
        staging_path.rename(path)
        installed_staging = True
        staging_path = None

        with db_connect() as conn:
            conn.execute("UPDATE repositories SET updated_at = ? WHERE id = ?", (utcnow(), repo["id"]))
        mark_repo_indexing(repo["id"], path)
        schedule_repo_metadata_refresh(repo["id"])
        success = True
    except Exception:
        if installed_staging and path.exists():
            shutil.rmtree(path)
        if moved_target_to_backup and backup_path and backup_path.exists() and not path.exists():
            backup_path.rename(path)
        raise
    finally:
        if bundle_path and bundle_path.exists():
            bundle_path.unlink()
        if staging_path and staging_path.exists():
            shutil.rmtree(staging_path)
        if success and backup_path and backup_path.exists():
            shutil.rmtree(backup_path)


def delete_repository(repo, path):
    with db_connect() as conn:
        conn.execute("DELETE FROM repositories WHERE id = ?", (repo["id"],))
    if path.exists():
        shutil.rmtree(path)


def add_repo_contributor(repo, added_by, username):
    username = (username or "").strip().lower()
    contributor = get_user_by_username(username)
    if not contributor:
        raise ValueError("User not found.")
    if contributor["id"] == repo["owner_id"]:
        raise ValueError("The owner already has access.")
    now = utcnow()
    with db_connect() as conn:
        try:
            conn.execute(
                """
                INSERT INTO repo_contributors (repo_id, user_id, added_by_id, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (repo["id"], contributor["id"], added_by["id"], now),
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError("User is already a contributor.") from exc
    sync_repo_git_config(repo)


def remove_repo_contributor(repo, user_id):
    with db_connect() as conn:
        conn.execute(
            "DELETE FROM repo_contributors WHERE repo_id = ? AND user_id = ?",
            (repo["id"], user_id),
        )
    sync_repo_git_config(repo)


def git_files(path, revision="HEAD"):
    if not revision or is_null_revision(revision):
        return []
    completed = run_git(["ls-tree", "-r", "--name-only", revision], cwd=path, check=False)
    if completed.returncode != 0:
        stderr = (completed.stderr or "").lower()
        stdout = completed.stdout or ""
        if (
            not stderr and not stdout
        ) or "unknown revision" in stderr or "bad revision" in stderr or "not a valid object name" in stderr:
            return []
        raise GitCommandError(completed.stderr.strip() or "Unable to list files.", completed.returncode)
    return [line.strip() for line in completed.stdout.splitlines() if line.strip()]


def git_tree_entries(path, revision="HEAD", subpath=""):
    if not revision or is_null_revision(revision):
        return []
    treeish = f"{revision}:{subpath}" if subpath else revision
    completed = run_git(["ls-tree", "-z", treeish], cwd=path, check=False)
    if completed.returncode != 0:
        stderr = (completed.stderr or "").lower()
        if "not a tree object" in stderr or "not a valid object name" in stderr or "does not exist" in stderr:
            return []
        raise GitCommandError(completed.stderr.strip() or "Unable to list tree.", completed.returncode)
    entries = []
    prefix = f"{subpath}/" if subpath else ""
    for record in completed.stdout.split("\0"):
        if not record:
            continue
        meta, _, name = record.partition("\t")
        parts = meta.split()
        if len(parts) < 2 or not name:
            continue
        entries.append(
            {
                "name": name,
                "path": f"{prefix}{name}" if prefix else name,
                "type": "dir" if parts[1] == "tree" else "file",
            }
        )
    return sorted(entries, key=lambda item: (item["type"] != "dir", item["name"].lower()))


def git_cat(path, file_path, revision="HEAD", text=True):
    completed = run_git(["show", f"{revision}:{file_path}"], cwd=path, check=True, text=text)
    return completed.stdout if text else completed.stdout


def truncate_bytes_for_render(content):
    if not MAX_RENDER_BYTES or len(content) <= MAX_RENDER_BYTES:
        return content, False
    return content[:MAX_RENDER_BYTES], True


def truncate_text_for_render(content, label="Preview"):
    encoded = (content or "").encode("utf-8", "replace")
    truncated, was_truncated = truncate_bytes_for_render(encoded)
    text = truncated.decode("utf-8", "replace")
    if was_truncated:
        text = text.rstrip() + f"\n\n[{label} truncated. Use the raw view or local clone for the full content.]\n"
    return text, was_truncated


def read_file_bytes(path, file_path, revision="HEAD"):
    if not revision or is_null_revision(revision):
        raise GitCommandError("File not found.")
    object_type = run_git(["cat-file", "-t", f"{revision}:{file_path}"], cwd=path, check=False)
    if object_type.returncode != 0 or object_type.stdout.strip() != "blob":
        raise GitCommandError("File not found.")
    completed = run_git(["show", f"{revision}:{file_path}"], cwd=path, check=False, text=False)
    if completed.returncode != 0:
        raise GitCommandError(completed.stderr.decode("utf-8", "replace").strip() or "Unable to read file.")
    return completed.stdout


def build_tree(files, subpath):
    prefix = f"{subpath}/" if subpath else ""
    entries = {}
    for file_path in files:
        if prefix and not file_path.startswith(prefix):
            continue
        rest = file_path[len(prefix) :]
        if not rest:
            continue
        name, _, _remaining = rest.partition("/")
        full_path = f"{prefix}{name}" if prefix else name
        entries[name] = {
            "name": name,
            "path": full_path,
            "type": "dir" if "/" in rest else "file",
        }
    return sorted(entries.values(), key=lambda item: (item["type"] != "dir", item["name"].lower()))


def readme_for_repo(path, files=None, revision="HEAD"):
    by_lower = {file_path.lower(): file_path for file_path in (files or [])}
    for candidate in README_CANDIDATES:
        actual = by_lower.get(candidate.lower()) if by_lower else candidate
        if actual:
            try:
                return actual, git_cat(path, actual, revision=revision)
            except GitCommandError:
                if by_lower:
                    return actual, ""
    return None, None


def readme_preview_for_repo(path, files=None, revision="HEAD"):
    name, readme = readme_for_repo(path, files, revision=revision)
    if readme is None:
        return name, readme, False
    readme, truncated = truncate_text_for_render(readme, label="README preview")
    return name, readme, truncated


def is_markdown_file(file_path):
    return bool(file_path and file_path.lower().endswith((".md", ".markdown", ".mdown")))


def highlight_language_class(file_path):
    path = Path(file_path)
    by_name = HIGHLIGHT_LANGUAGE_BY_NAME.get(path.name.lower())
    if by_name:
        return by_name
    return HIGHLIGHT_LANGUAGE_BY_EXTENSION.get(path.suffix.lower(), "")


def render_markdown(text):
    text = SCRIPT_STYLE_RE.sub("", text or "")
    rendered = markdown.markdown(
        text,
        extensions=MARKDOWN_EXTENSIONS,
        output_format="html5",
    )
    return bleach.clean(
        rendered,
        tags=MARKDOWN_TAGS,
        attributes=MARKDOWN_ATTRIBUTES,
        protocols={"http", "https", "mailto"},
        strip=True,
    )


def render_markdown_links(text):
    rendered = markdown.markdown(
        html.escape(text or "", quote=False),
        output_format="html5",
    )
    return bleach.clean(
        rendered,
        tags=MARKDOWN_LINK_TAGS,
        attributes=MARKDOWN_LINK_ATTRIBUTES,
        protocols={"http", "https", "mailto"},
        strip=True,
    ).strip()


def render_repo_description(text):
    return render_markdown_links(text)


def normalize_request_host(value):
    host = (value or "").split(",", 1)[0].strip().lower()
    if not host:
        return ""
    if host.startswith("["):
        return host.rstrip(".")
    if ":" in host:
        hostname, port = host.rsplit(":", 1)
        if port.isdigit():
            host = hostname
    return host.rstrip(".")


def valid_hostname(hostname):
    if not hostname or len(hostname) > 253:
        return False
    labels = hostname.rstrip(".").split(".")
    return all(HOSTNAME_LABEL_RE.match(label) for label in labels)


def normalize_custom_domain(value):
    raw = (value or "").strip()
    if not raw:
        raise ValueError("CNAME must contain a domain name.")
    if "://" in raw or "/" in raw or "\\" in raw or any(char.isspace() for char in raw):
        raise ValueError("CNAME must contain only a domain name.")
    domain = raw.lower().rstrip(".")
    if not valid_hostname(domain):
        raise ValueError("CNAME must contain a valid domain name.")
    if PAGES_DOMAIN and (domain == PAGES_DOMAIN or domain.endswith(f".{PAGES_DOMAIN}")):
        raise ValueError(f"Use the {PAGES_DOMAIN} Pages host directly instead of a CNAME.")
    return domain


def user_site_repo_name(username):
    return f"{username}.{PAGES_DOMAIN}"


def is_user_site_repo(repo):
    return bool(repo and PAGES_DOMAIN and repo["name"] == user_site_repo_name(repo["owner_username"]))


def pages_host_for_owner(username):
    return f"{username}.{PAGES_DOMAIN}"


def pages_url_for_repo(repo):
    host = pages_host_for_owner(repo["owner_username"])
    if is_user_site_repo(repo):
        return f"https://{host}/"
    return f"https://{host}/{repo['name']}/"


def custom_domain_txt_name(domain):
    return f"{PAGES_VERIFY_TXT_PREFIX}.{domain}"


def custom_domain_txt_value(token):
    return f"{PAGES_VERIFY_VALUE_PREFIX}{token}"


def resolve_dns_txt(record_name):
    if dns is None:
        raise ValueError("DNS lookup support is unavailable. Install dnspython to verify custom domains.")
    try:
        answers = dns.resolver.resolve(record_name, "TXT", lifetime=5)
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
        return []
    except dns.exception.DNSException as exc:
        raise ValueError(f"DNS lookup failed: {exc}") from exc

    values = []
    for answer in answers:
        strings = getattr(answer, "strings", None)
        if strings is not None:
            values.append(b"".join(strings).decode("utf-8", "replace"))
        else:
            values.append(answer.to_text().strip('"'))
    return values


def get_custom_domain_for_user(user_id, domain):
    with db_connect() as conn:
        return conn.execute(
            """
            SELECT *
            FROM custom_domains
            WHERE user_id = ? AND domain = ?
            """,
            (user_id, domain),
        ).fetchone()


def ensure_custom_domain_for_user(user_id, domain):
    domain = normalize_custom_domain(domain)
    existing = get_custom_domain_for_user(user_id, domain)
    if existing:
        return existing

    now = utcnow()
    token = secrets.token_urlsafe(32)
    with db_connect() as conn:
        conn.execute(
            """
            INSERT INTO custom_domains (
                user_id, domain, verification_token, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, domain, token, now, now),
        )
    return get_custom_domain_for_user(user_id, domain)


def custom_domains_for_domain(domain):
    with db_connect() as conn:
        return conn.execute(
            """
            SELECT custom_domains.*, users.username AS owner_username
            FROM custom_domains
            JOIN users ON users.id = custom_domains.user_id
            WHERE custom_domains.domain = ?
            ORDER BY custom_domains.verified_at DESC, custom_domains.id DESC
            """,
            (domain,),
        ).fetchall()


def update_custom_domain_check(custom_domain, verified, status):
    now = utcnow()
    verified_at = now if verified else None
    with db_connect() as conn:
        conn.execute(
            """
            UPDATE custom_domains
            SET verified_at = ?, last_checked_at = ?, status = ?, updated_at = ?
            WHERE id = ?
            """,
            (verified_at, now, status[:500], now, custom_domain["id"]),
        )
    return get_custom_domain_for_user(custom_domain["user_id"], custom_domain["domain"])


def read_cname_domain_for_repo(repo):
    if not repo:
        return "", ""
    path = repo_path(repo["owner_username"], repo["name"])
    try:
        revision = ref_revision(default_code_ref(path))
        files = git_files(path, revision)
    except (GitCommandError, OSError):
        return "", ""

    by_lower = {file_path.lower(): file_path for file_path in files}
    cname_path = by_lower.get("cname")
    if not cname_path:
        return "", ""

    try:
        content = read_file_bytes(path, cname_path, revision=revision).decode("utf-8", "replace")
    except GitCommandError:
        return "", ""

    raw_domain = ""
    for line in content.splitlines():
        if line.strip():
            raw_domain = line.strip()
            break
    if not raw_domain:
        return "", "CNAME is empty."
    try:
        return normalize_custom_domain(raw_domain), ""
    except ValueError as exc:
        return "", str(exc)


def verify_custom_domain_for_repo(repo):
    if not is_user_site_repo(repo):
        raise ValueError("Custom domains can only be verified from the user Pages repository.")
    domain, cname_error = read_cname_domain_for_repo(repo)
    if cname_error:
        raise ValueError(cname_error)
    if not domain:
        raise ValueError("Add a root CNAME file before verifying a custom domain.")

    custom_domain = ensure_custom_domain_for_user(repo["owner_id"], domain)
    txt_name = custom_domain_txt_name(domain)
    expected = custom_domain_txt_value(custom_domain["verification_token"])
    try:
        values = resolve_dns_txt(txt_name)
    except ValueError as exc:
        update_custom_domain_check(custom_domain, False, str(exc))
        raise

    if expected not in values:
        message = f'TXT verification record was not found at "{txt_name}".'
        update_custom_domain_check(custom_domain, False, message)
        raise ValueError(message)

    return update_custom_domain_check(custom_domain, True, "Domain verified.")


def pages_settings_context(repo):
    docs_publishable = bool(repo and not is_user_site_repo(repo))
    context = {
        "domain": PAGES_DOMAIN,
        "url": pages_url_for_repo(repo),
        "docs_publishable": docs_publishable,
        "docs_enabled": bool(repo["pages_docs_enabled"]) if docs_publishable else False,
        "is_user_site_repo": is_user_site_repo(repo),
        "cname_domain": "",
        "cname_error": "",
        "custom_domain": None,
        "txt_name": "",
        "txt_value": "",
    }
    if not context["is_user_site_repo"]:
        return context

    domain, cname_error = read_cname_domain_for_repo(repo)
    context["cname_domain"] = domain
    context["cname_error"] = cname_error
    if domain and not cname_error:
        custom_domain = ensure_custom_domain_for_user(repo["owner_id"], domain)
        context["custom_domain"] = custom_domain
        context["txt_name"] = custom_domain_txt_name(domain)
        context["txt_value"] = custom_domain_txt_value(custom_domain["verification_token"])
    return context


def clean_pages_request_path(path_info):
    raw = unquote(path_info or "/")
    trailing_slash = raw.endswith("/") and raw != "/"
    stripped = raw.strip("/")
    if not stripped:
        return "", trailing_slash
    parts = stripped.split("/")
    if any(part in {"", ".", "..", ".git"} for part in parts):
        return None, trailing_slash
    pure_parts = PurePosixPath(stripped).parts
    if any(part in {"", ".", "..", ".git"} for part in pure_parts):
        return None, trailing_slash
    return "/".join(pure_parts), trailing_slash


def join_pages_path(*parts):
    return "/".join(part.strip("/") for part in parts if part)


def pages_file_candidates(base_path, request_path, trailing_slash=False):
    target = join_pages_path(base_path, request_path)
    candidates = []
    if target and not trailing_slash:
        candidates.append(target)
    index_path = join_pages_path(target, "index.html") if target else "index.html"
    candidates.append(index_path)
    if request_path and target and not trailing_slash and "." not in PurePosixPath(request_path).name:
        candidates.append(f"{target}.html")

    seen = set()
    unique = []
    for candidate in candidates:
        if candidate and candidate not in seen:
            seen.add(candidate)
            unique.append(candidate)
    return unique


def pages_content_type(file_path):
    content_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
    if (
        content_type.startswith("text/")
        or content_type in {"application/javascript", "application/json", "application/xml", "image/svg+xml"}
    ):
        content_type += "; charset=utf-8"
    return content_type


def pages_http_response(body, status=200, content_type="text/plain; charset=utf-8"):
    request.environ["gitman.pages_response"] = True
    if request.method == "HEAD":
        body = b""
    return HTTPResponse(body=body, status=status, content_type=content_type)


def pages_not_found_response(repo=None, base_path="", revision=None, files=None):
    if repo and revision and files:
        not_found_path = join_pages_path(base_path, "404.html")
        if not_found_path in files:
            path = repo_path(repo["owner_username"], repo["name"])
            content = read_file_bytes(path, not_found_path, revision=revision)
            return pages_http_response(content, status=404, content_type=pages_content_type(not_found_path))
    return pages_http_response("Not found.\n", status=404)


def pages_response_for_repo(repo, base_path, request_path, trailing_slash=False):
    path = repo_path(repo["owner_username"], repo["name"])
    try:
        revision = ref_revision(default_code_ref(path))
        files = git_files(path, revision)
    except (GitCommandError, OSError):
        return pages_not_found_response()

    for candidate in pages_file_candidates(base_path, request_path, trailing_slash=trailing_slash):
        if candidate in files:
            content = read_file_bytes(path, candidate, revision=revision)
            return pages_http_response(content, content_type=pages_content_type(candidate))
    return pages_not_found_response(repo, base_path=base_path, revision=revision, files=files)


def pages_repo_for_request(owner_username, request_path):
    first, separator, rest = request_path.partition("/")
    if first:
        project_repo = get_repo(owner_username, first.lower())
        if (
            project_repo
            and project_repo["pages_docs_enabled"]
            and not is_user_site_repo(project_repo)
        ):
            return project_repo, "docs", rest if separator else ""

    site_repo = get_repo(owner_username, user_site_repo_name(owner_username))
    if site_repo:
        return site_repo, "", request_path
    return None, "", request_path


def pages_response_for_owner(owner_username):
    if request.method not in {"GET", "HEAD"}:
        request.environ["gitman.pages_response"] = True
        return HTTPResponse(
            "Method not allowed.\n",
            status=405,
            headers={"Allow": "GET, HEAD"},
            content_type="text/plain; charset=utf-8",
        )

    owner_username = (owner_username or "").lower()
    if not SLUG_RE.match(owner_username) or not get_user_by_username(owner_username):
        return pages_not_found_response()

    request_path, trailing_slash = clean_pages_request_path(request.environ.get("PATH_INFO", request.path) or "/")
    if request_path is None:
        return pages_not_found_response()

    repo, base_path, repo_request_path = pages_repo_for_request(owner_username, request_path)
    if not repo:
        return pages_not_found_response()
    return pages_response_for_repo(repo, base_path, repo_request_path, trailing_slash=trailing_slash)


def pages_owner_from_host(host):
    if not PAGES_DOMAIN or host == PAGES_DOMAIN:
        return None, False
    suffix = f".{PAGES_DOMAIN}"
    if not host.endswith(suffix):
        return None, False
    return host[: -len(suffix)], True


def custom_domain_site_for_host(host):
    try:
        domain = normalize_custom_domain(host)
    except ValueError:
        return None, False

    rows = custom_domains_for_domain(domain)
    if not rows:
        return None, False

    for row in rows:
        if not row["verified_at"]:
            continue
        site_repo = get_repo(row["owner_username"], user_site_repo_name(row["owner_username"]))
        cname_domain, cname_error = read_cname_domain_for_repo(site_repo)
        if not cname_error and cname_domain == domain:
            return {"owner_username": row["owner_username"], "domain": domain}, True
    return None, True


def pages_response_for_request_host():
    host = normalize_request_host(request.get_header("Host", ""))
    owner_username, is_pages_subdomain = pages_owner_from_host(host)
    if is_pages_subdomain:
        return pages_response_for_owner(owner_username)

    site, registered_domain = custom_domain_site_for_host(host)
    if site:
        return pages_response_for_owner(site["owner_username"])
    if registered_domain:
        return pages_not_found_response()
    return None


def is_null_revision(value):
    return (value or "").strip().lower() in {NULL_REV, NULL_NODE}


def strip_git_record_separator(value):
    value = (value or "").rstrip("\n")
    if value.endswith("\x1e"):
        value = value[:-1]
    return value


def newest_revision_sort_key(item):
    return (item.get("date", ""), item.get("name", ""))


def commit_log(path, limit=50, revision=None):
    revision = revision_or_default(path, revision)
    if is_null_revision(revision):
        return []
    format_arg = "%H%x1f%h%x1f%an%x1f%ad%x1f%s%x1e"
    completed = run_git(
        ["log", "-n", str(limit), "--date=iso-strict", f"--format={format_arg}", revision],
        cwd=path,
        check=False,
    )
    if completed.returncode != 0:
        stderr = (completed.stderr or "").lower()
        if "does not have any commits" in stderr or "bad revision" in stderr:
            return []
        raise GitCommandError(completed.stderr.strip() or "Unable to read commit log.", completed.returncode)
    commits = []
    for record in completed.stdout.split("\x1e"):
        record = record.strip("\n")
        if not record:
            continue
        parts = record.split("\x1f")
        if len(parts) != 5:
            continue
        commits.append(
            {
                "rev": "",
                "node": parts[0],
                "short_node": parts[1],
                "author": parts[2],
                "date": parts[3],
                "summary": parts[4],
            }
        )
    return commits


def all_commit_refs(path, limit=REF_SEARCH_COMMIT_LIMIT):
    format_arg = "%H%x1f%h%x1f%ad%x1f%s%x1e"
    completed = run_git(
        ["log", "--all", "-n", str(limit), "--date=iso-strict", f"--format={format_arg}"],
        cwd=path,
        check=False,
    )
    if completed.returncode != 0:
        stderr = (completed.stderr or "").lower()
        if "does not have any commits" in stderr or "bad revision" in stderr:
            return []
        raise GitCommandError(completed.stderr.strip() or "Unable to search commits.", completed.returncode)

    commits = []
    for record in completed.stdout.split("\x1e"):
        record = record.strip("\n")
        if not record:
            continue
        parts = record.split("\x1f")
        if len(parts) != 4:
            continue
        commits.append(
            {
                "type": REF_TYPE_COMMIT,
                "name": parts[0],
                "label": f"commit {parts[1]} {parts[3]}".strip(),
                "node": parts[0],
                "short_node": parts[1],
                "date": parts[2],
                "summary": parts[3],
            }
        )
    return commits


def list_repo_tags(path, limit=None):
    args = ["for-each-ref", "--sort=-creatordate", "--format=%(refname:short)"]
    if limit:
        args.extend(["--count", str(limit)])
    args.append("refs/tags")
    completed = run_git(args, cwd=path, check=False)
    if completed.returncode != 0:
        raise GitCommandError(completed.stderr.strip() or "Unable to read repository tags.", completed.returncode)

    tags = []
    for name in completed.stdout.splitlines():
        name = name.strip()
        if not name:
            continue
        commit = revision_info(path, f"refs/tags/{name}^{{commit}}")
        if not commit:
            continue
        tags.append(
            {
                "type": REF_TYPE_TAG,
                "name": name,
                "label": f"tag {name}",
                "rev": "",
                "node": commit["node"],
                "short_node": commit["short_node"],
                "branch": "",
                "active": False,
                "closed": False,
                "local": False,
                "is_default": False,
                "date": commit["date"],
                "summary": commit["summary"],
            }
        )
    tags.sort(key=newest_revision_sort_key, reverse=True)
    return tags


def tag_ref(path, name):
    name = (name or "").strip()
    if not name:
        return None
    completed = run_git(["show-ref", "--verify", "--quiet", f"refs/tags/{name}"], cwd=path, check=False)
    if completed.returncode != 0:
        return None
    commit = revision_info(path, f"refs/tags/{name}^{{commit}}")
    if not commit:
        return None
    return {
        "type": REF_TYPE_TAG,
        "name": name,
        "label": f"tag {name}",
        "rev": "",
        "node": commit["node"],
        "short_node": commit["short_node"],
        "branch": "",
        "active": False,
        "closed": False,
        "local": False,
        "is_default": False,
        "date": commit["date"],
        "summary": commit["summary"],
    }


def revision_info(path, revision):
    if not revision:
        return None
    format_arg = "%H%x1f%h%x1f%ad%x1f%s%x1e"
    completed = run_git(
        ["show", "-s", "--date=iso-strict", f"--format={format_arg}", revision],
        cwd=path,
        check=False,
    )
    if completed.returncode != 0 or not completed.stdout:
        return None
    parts = strip_git_record_separator(completed.stdout).split("\x1f")
    if len(parts) != 4:
        return None
    if is_null_revision(parts[0]):
        return None
    return {
        "rev": "",
        "node": parts[0],
        "short_node": parts[1],
        "branch": "",
        "date": parts[2],
        "summary": parts[3],
    }


def empty_tip_ref(is_default=False):
    return {
        "type": REF_TYPE_TIP,
        "name": "",
        "label": "HEAD",
        "rev": "",
        "node": None,
        "short_node": "",
        "branch": "",
        "date": "",
        "summary": "",
        "active": False,
        "closed": False,
        "is_default": is_default,
    }


def tip_ref(path, is_default=False):
    info = revision_info(path, "HEAD")
    if not info:
        return empty_tip_ref(is_default=is_default)
    info.update(
        {
            "type": REF_TYPE_TIP,
            "name": "",
            "label": "HEAD",
            "active": False,
            "closed": False,
            "is_default": is_default,
        }
    )
    return info


def commit_ref(path, revision):
    revision = (revision or "").strip()
    if not REV_RE.match(revision) or revision == NULL_REV:
        raise ValueError("Commit not found.")
    info = revision_info(path, revision)
    if not info:
        raise ValueError("Commit not found.")
    info.update(
        {
            "type": REF_TYPE_COMMIT,
            "name": info["node"],
            "label": f"commit {info['short_node']}",
            "active": False,
            "closed": False,
            "is_default": False,
        }
    )
    return info


def parse_branch_record(record, head_branch=""):
    parts = record.split("\x00")
    if len(parts) != 5:
        return None
    return {
        "type": REF_TYPE_BRANCH,
        "name": parts[0],
        "label": f"branch {parts[0]}",
        "node": parts[1],
        "short_node": parts[2],
        "rev": "",
        "active": parts[0] == head_branch,
        "closed": False,
        "date": parts[3],
        "summary": parts[4],
        "is_default": False,
    }


def branch_ref(path, name):
    name = (name or "").strip()
    if not name:
        return None
    exists = run_git(["show-ref", "--verify", "--quiet", f"refs/heads/{name}"], cwd=path, check=False)
    if exists.returncode != 0:
        return None
    format_arg = "%(refname:short)%00%(objectname)%00%(objectname:short)%00%(committerdate:iso-strict)%00%(subject)"
    completed = run_git(
        ["for-each-ref", f"--format={format_arg}", f"refs/heads/{name}"],
        cwd=path,
        check=False,
    )
    if completed.returncode != 0:
        raise GitCommandError(completed.stderr.strip() or "Unable to read repository branch.", completed.returncode)
    record = completed.stdout.splitlines()[0] if completed.stdout.splitlines() else ""
    branch = parse_branch_record(record, repo_head_branch(path)) if record else None
    return branch if branch and branch["name"] == name else None


def list_repo_branches(path, limit=None):
    format_arg = "%(refname:short)%00%(objectname)%00%(objectname:short)%00%(committerdate:iso-strict)%00%(subject)"
    args = ["for-each-ref", "--sort=-committerdate", f"--format={format_arg}"]
    if limit:
        args.extend(["--count", str(limit)])
    args.append("refs/heads")
    completed = run_git(
        args,
        cwd=path,
        check=False,
    )
    if completed.returncode != 0:
        raise GitCommandError(completed.stderr.strip() or "Unable to read repository branches.", completed.returncode)

    head_branch = repo_head_branch(path)
    branches = []
    for record in completed.stdout.splitlines():
        if not record:
            continue
        branch = parse_branch_record(record, head_branch)
        if branch:
            branches.append(branch)
    branches.sort(key=newest_revision_sort_key, reverse=True)
    return branches


def choose_default_branch(branches, head_branch=""):
    for branch in branches:
        if branch["name"] == head_branch:
            return branch
    for branch_name in DEFAULT_BRANCH_CANDIDATES:
        for branch in branches:
            if branch["name"] == branch_name:
                return branch
    return branches[0] if branches else None


def default_code_ref(path):
    head_branch = repo_head_branch(path)
    selected_branch = branch_ref(path, head_branch)
    if not selected_branch:
        for branch_name in DEFAULT_BRANCH_CANDIDATES:
            selected_branch = branch_ref(path, branch_name)
            if selected_branch:
                break
    if not selected_branch:
        branches = list_repo_branches(path, limit=1)
        selected_branch = branches[0] if branches else None
    if selected_branch:
        selected = dict(selected_branch)
        selected["active"] = True
        selected["is_default"] = True
        if selected["name"] != head_branch:
            set_repo_head_branch(path, selected["name"])
        return selected
    return tip_ref(path, is_default=True)


def revision_or_default(path, revision):
    if revision is None:
        revision = default_code_ref(path).get("node")
    return revision or NULL_REV


def resolve_repo_ref(path, ref_type, ref_name=""):
    ref_type = (ref_type or "").strip().lower()
    ref_name = ref_name or ""
    if ref_type == REF_TYPE_TIP:
        return tip_ref(path)
    if ref_type == REF_TYPE_COMMIT:
        return commit_ref(path, ref_name)
    if ref_type == REF_TYPE_BRANCH:
        branch = branch_ref(path, ref_name)
        if branch:
            return dict(branch)
        raise ValueError("Branch not found.")
    if ref_type == REF_TYPE_TAG:
        tag = tag_ref(path, ref_name)
        if tag:
            return dict(tag)
        raise ValueError("Tag not found.")
    raise ValueError("Ref not found.")


def ref_option_value(ref_type, ref_name=""):
    return REF_VALUE_SEPARATOR.join((ref_type, quote(ref_name or "", safe="")))


def source_ref_option_value(repo_id, ref_type, ref_name=""):
    return REF_VALUE_SEPARATOR.join((str(repo_id), ref_type, quote(ref_name or "", safe="")))


def parse_ref_option_value(value, allowed_types=REF_TYPES):
    parts = (value or "").split(REF_VALUE_SEPARATOR, 1)
    if len(parts) != 2 or parts[0] not in allowed_types:
        raise ValueError("Invalid ref.")
    return parts[0], unquote(parts[1])


def parse_source_ref_option_value(value):
    parts = (value or "").split(REF_VALUE_SEPARATOR, 2)
    if len(parts) != 3 or parts[1] not in PULL_REQUEST_REF_TYPES:
        raise ValueError("Invalid source ref.")
    try:
        repo_id = int(parts[0])
    except ValueError as exc:
        raise ValueError("Invalid source repository.") from exc
    return repo_id, parts[1], unquote(parts[2])


def selected_repo_ref(path):
    ref_value = request.query.get("ref_value")
    if ref_value:
        try:
            ref_type, ref_name = parse_ref_option_value(ref_value)
            return resolve_repo_ref(path, ref_type, ref_name)
        except ValueError as exc:
            abort(404, str(exc))

    ref_type = (request.query.get("ref_type") or "").strip().lower()
    if not ref_type:
        return default_code_ref(path)
    if ref_type not in REF_TYPES:
        abort(404, "Ref not found.")
    try:
        return resolve_repo_ref(path, ref_type, request.query.get("ref") or "")
    except ValueError as exc:
        abort(404, str(exc))


def ref_revision(ref_info):
    if not ref_info:
        return None
    return ref_info.get("node") or NULL_REV


def ref_query_string(ref_info, force=False):
    if not ref_info or (ref_info.get("is_default") and not force):
        return ""
    ref_type = ref_info.get("type") or REF_TYPE_TIP
    params = {"ref_type": ref_type}
    if ref_type != REF_TYPE_TIP:
        params["ref"] = ref_info.get("name", "")
    return urlencode(params)


def url_with_ref(url, ref_info=None, force=False):
    query = ref_query_string(ref_info, force=force)
    if not query:
        return url
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}{query}"


def current_url_with_ref(ref_info=None, force=False):
    params = [
        (key, value)
        for key, value in request.query.allitems()
        if key not in REF_QUERY_KEYS
    ]
    query = ref_query_string(ref_info, force=force)
    if query:
        params.extend(parse_qsl(query, keep_blank_values=True))
    encoded = urlencode(params)
    return request.path + (f"?{encoded}" if encoded else "")


def format_ref_label(ref_type, ref_name=""):
    ref_type = (ref_type or REF_TYPE_TIP).strip().lower()
    if ref_type == REF_TYPE_BRANCH:
        return f"branch {ref_name}"
    if ref_type == REF_TYPE_TAG:
        return f"tag {ref_name}"
    if ref_type == REF_TYPE_COMMIT:
        return f"commit {ref_name[:12]}" if ref_name else "commit"
    return "HEAD"


def ref_option_label(ref):
    label = format_ref_label(ref["type"], ref.get("name", ""))
    return label


def ref_option_from_ref(ref, repo_id=None):
    if repo_id is None:
        value = ref_option_value(ref["type"], ref.get("name", ""))
    else:
        value = source_ref_option_value(repo_id, ref["type"], ref.get("name", ""))
    return {
        "value": value,
        "label": ref_option_label(ref),
        "ref": ref,
    }


def ref_search_result(ref):
    result = {
        "type": ref["type"],
        "name": ref.get("name", ""),
        "label": ref.get("label") or ref_option_label(ref),
    }
    if ref.get("node"):
        result["node"] = ref["node"]
    if ref.get("short_node"):
        result["short_node"] = ref["short_node"]
    return result


def ref_matches_query(ref, query):
    label = (ref.get("label") or ref_option_label(ref)).lower()
    name = (ref.get("name") or "").lower()
    if query in label or query in name:
        return True
    if ref["type"] == REF_TYPE_COMMIT:
        return (
            query in (ref.get("node") or "").lower()
            or query in (ref.get("short_node") or "").lower()
            or query in (ref.get("summary") or "").lower()
        )
    return False


def search_repo_refs(path, query):
    query = (query or "").strip().lower()
    if not query:
        return []

    refs = list_repo_branches(path, limit=REF_LIST_LIMIT)
    refs.extend(list_repo_tags(path, limit=REF_LIST_LIMIT))
    refs.extend(all_commit_refs(path, limit=REF_SEARCH_COMMIT_LIMIT))
    return [ref_search_result(ref) for ref in refs if ref_matches_query(ref, query)]


def cached_ref_rows(metadata, key):
    if not metadata or metadata["status"] != REPO_INDEX_READY:
        return []
    return decode_cached_refs(metadata[key])


def repo_ref_options(path, include_closed_branches=True, include_tip=True, include_tags=True, metadata=None):
    branches = cached_ref_rows(metadata, "branch_refs_json") or list_repo_branches(path, limit=REF_PICKER_LIMIT)
    refs = []
    for branch in branches:
        if include_closed_branches or not branch["closed"]:
            refs.append(branch)
    if include_tags:
        refs.extend(cached_ref_rows(metadata, "tag_refs_json") or list_repo_tags(path, limit=REF_PICKER_LIMIT))

    refs.sort(key=newest_revision_sort_key, reverse=True)
    options = []
    for index, ref in enumerate(refs):
        option = ref_option_from_ref(ref)
        option["is_initial"] = index < 10
        options.append(option)
    if include_tip:
        tip_option = ref_option_from_ref(tip_ref(path))
        tip_option["is_initial"] = False
        options.append(tip_option)
    return options


def repo_ref_picker_options(path, metadata=None):
    return [option for option in repo_ref_options(path, metadata=metadata) if option.get("is_initial")]


def source_repo_ref_options(source_repo, include_tip=True):
    path = repo_path(source_repo["owner_username"], source_repo["name"])
    options = repo_ref_options(
        path,
        include_closed_branches=True,
        include_tip=include_tip,
        include_tags=False,
        metadata=repo_metadata_row(source_repo["id"]),
    )
    for option in options:
        option["value"] = source_ref_option_value(
            source_repo["id"],
            option["ref"]["type"],
            option["ref"].get("name", ""),
        )
        option["label"] = f"{source_repo['owner_username']}/{source_repo['name']} {option['label']}"
    return options


def target_repo_ref_options(path):
    return repo_ref_options(path, include_closed_branches=False, include_tip=False, include_tags=False)


def git_commit_count(path, revision=None):
    revision = revision_or_default(path, revision)
    if is_null_revision(revision):
        return 0
    completed = run_git(["rev-list", "--count", revision], cwd=path, check=False)
    if completed.returncode != 0:
        stderr = (completed.stderr or "").lower()
        if "does not have any commits" in stderr or "bad revision" in stderr:
            return 0
        raise GitCommandError(completed.stderr.strip() or "Unable to count commits.", completed.returncode)
    try:
        return int(completed.stdout.strip())
    except ValueError:
        return 0


def commit_count(path, revision=None):
    return git_commit_count(path, revision)


def ref_count(path, ref_prefix):
    completed = run_git(["for-each-ref", "--format=%(refname)", ref_prefix], cwd=path, check=False)
    if completed.returncode != 0:
        raise GitCommandError(completed.stderr.strip() or "Unable to count refs.", completed.returncode)
    return len([line for line in completed.stdout.splitlines() if line.strip()])


def repo_metadata_row(repo_id):
    with db_connect() as conn:
        return conn.execute("SELECT * FROM repo_metadata WHERE repo_id = ?", (repo_id,)).fetchone()


def decode_cached_refs(value):
    try:
        refs = json.loads(value or "[]")
    except (TypeError, ValueError):
        return []
    return refs if isinstance(refs, list) else []


def repo_metadata_for_context(repo, path):
    metadata = repo_metadata_row(repo["id"])
    if metadata:
        if metadata["status"] == REPO_INDEX_INDEXING:
            schedule_repo_metadata_refresh(repo["id"])
        return metadata
    mark_repo_indexing(repo["id"], path)
    schedule_repo_metadata_refresh(repo["id"])
    return repo_metadata_row(repo["id"])


def write_repo_metadata(repo, path, status=REPO_INDEX_READY):
    head_node = repo_tip_node(path) or ""
    default_branch = repo_head_branch(path)
    branch_refs = list_repo_branches(path, limit=REF_LIST_LIMIT)
    tag_refs = list_repo_tags(path, limit=REF_LIST_LIMIT)
    now = utcnow()
    with db_connect() as conn:
        conn.execute(
            """
            INSERT INTO repo_metadata (
                repo_id, head_node, default_branch, commit_count, branch_count, tag_count,
                branch_refs_json, tag_refs_json, status, indexed_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(repo_id) DO UPDATE SET
                head_node = excluded.head_node,
                default_branch = excluded.default_branch,
                commit_count = excluded.commit_count,
                branch_count = excluded.branch_count,
                tag_count = excluded.tag_count,
                branch_refs_json = excluded.branch_refs_json,
                tag_refs_json = excluded.tag_refs_json,
                status = excluded.status,
                indexed_at = excluded.indexed_at,
                updated_at = excluded.updated_at
            """,
            (
                repo["id"],
                head_node,
                default_branch,
                git_commit_count(path, head_node),
                ref_count(path, "refs/heads"),
                ref_count(path, "refs/tags"),
                json.dumps(branch_refs),
                json.dumps(tag_refs),
                status,
                now if status == REPO_INDEX_READY else "",
                now,
            ),
        )


def mark_repo_indexing(repo_id, path=None):
    now = utcnow()
    head_node = ""
    default_branch = ""
    placeholder_count = 0
    if path is not None and path.exists():
        try:
            head_node = repo_tip_node(path) or ""
            default_branch = repo_head_branch(path)
            placeholder_count = 1 if head_node else 0
        except (GitCommandError, OSError):
            pass
    with db_connect() as conn:
        conn.execute(
            """
            INSERT INTO repo_metadata (repo_id, head_node, default_branch, commit_count, status, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(repo_id) DO UPDATE SET
                head_node = CASE WHEN excluded.head_node != '' THEN excluded.head_node ELSE repo_metadata.head_node END,
                default_branch = CASE
                    WHEN excluded.default_branch != '' THEN excluded.default_branch
                    ELSE repo_metadata.default_branch
                END,
                commit_count = CASE
                    WHEN excluded.commit_count > repo_metadata.commit_count THEN excluded.commit_count
                    ELSE repo_metadata.commit_count
                END,
                status = excluded.status,
                updated_at = excluded.updated_at
            """,
            (repo_id, head_node, default_branch, placeholder_count, REPO_INDEX_INDEXING, now),
        )


def refresh_repo_metadata(repo_id):
    repo = get_repo_by_id(repo_id)
    if not repo:
        return
    path = repo_path(repo["owner_username"], repo["name"])
    if not path.exists():
        return
    try:
        write_repo_metadata(repo, path)
    except Exception as exc:
        log_perf("repo-index-error", PERF_LOG_THRESHOLD_MS / 1000 if PERF_LOG_THRESHOLD_MS else 1, str(exc))


def schedule_repo_metadata_refresh(repo_id):
    with REPO_INDEX_LOCK:
        if repo_id in REPO_INDEX_THREADS:
            return
        REPO_INDEX_THREADS.add(repo_id)

    def worker():
        try:
            refresh_repo_metadata(repo_id)
        finally:
            with REPO_INDEX_LOCK:
                REPO_INDEX_THREADS.discard(repo_id)

    threading.Thread(target=worker, name=f"gitman-index-{repo_id}", daemon=True).start()


def cached_commit_count(repo, path, revision, metadata=None):
    metadata = metadata or repo_metadata_row(repo["id"])
    if (
        metadata
        and metadata["status"] in {REPO_INDEX_READY, REPO_INDEX_INDEXING}
        and revision
        and revision == metadata["head_node"]
        and int(metadata["commit_count"] or 0) > 0
    ):
        return int(metadata["commit_count"] or 0)
    return git_commit_count(path, revision)


def repo_head_ref(path):
    completed = run_git(["symbolic-ref", "--quiet", "HEAD"], cwd=path, check=False)
    if completed.returncode == 0:
        return completed.stdout.strip()
    return ""


def set_repo_head_branch(path, branch_name):
    if branch_name:
        run_git(["symbolic-ref", "HEAD", f"refs/heads/{branch_name}"], cwd=path, check=False)


def validate_revision_id(value, allow_null=True):
    revision = (value or "").strip()
    if not REV_RE.match(revision) or (is_null_revision(revision) and not allow_null):
        abort(404, "Revision not found.")
    return revision


def repo_head_branch(path):
    head_ref = repo_head_ref(path)
    if head_ref.startswith("refs/heads/"):
        return head_ref.removeprefix("refs/heads/") or "main"
    return "main"


def repo_tip_node(path):
    completed = run_git(["rev-parse", "--verify", "HEAD^{commit}"], cwd=path, check=False)
    if completed.returncode != 0:
        stderr = (completed.stderr or "").lower()
        if "needed a single revision" in stderr or "unknown revision" in stderr or "ambiguous argument" in stderr:
            return None
        raise GitCommandError(completed.stderr.strip() or "Unable to read repository HEAD.", completed.returncode)
    node = completed.stdout.strip()
    if is_null_revision(node):
        return None
    return node or None


def repo_has_revision(path, revision):
    revision = validate_revision_id(revision)
    if is_null_revision(revision):
        return True
    completed = run_git(["cat-file", "-e", f"{revision}^{{commit}}"], cwd=path, check=False)
    return completed.returncode == 0


def is_ancestor(path, ancestor_node, descendant_node):
    ancestor_node = validate_revision_id(ancestor_node)
    descendant_node = validate_revision_id(descendant_node, allow_null=False)
    if is_null_revision(ancestor_node) or ancestor_node == descendant_node:
        return True
    completed = run_git(["merge-base", "--is-ancestor", ancestor_node, descendant_node], cwd=path, check=False)
    return completed.returncode == 0


def commit_detail(path, node):
    node = validate_revision_id(node, allow_null=False)
    format_arg = "%H%x1f%h%x1f%an%x1f%ad%x1f%B%x1f%P%x1e"
    completed = run_git(
        ["show", "-s", "--date=iso-strict", f"--format={format_arg}", node],
        cwd=path,
        check=False,
    )
    if completed.returncode != 0 or not completed.stdout:
        abort(404, "Commit not found.")
    parts = strip_git_record_separator(completed.stdout).split("\x1f")
    if len(parts) != 6:
        abort(404, "Commit not found.")
    return {
        "rev": "",
        "node": parts[0],
        "short_node": parts[1],
        "author": parts[2],
        "date": parts[3],
        "description": parts[4].strip(),
        "parents": parts[5],
    }


def commit_diff(path, node):
    node = validate_revision_id(node, allow_null=False)
    completed = run_git(["show", "--format=", "--patch", "--find-renames", "--root", node], cwd=path, check=False)
    if completed.returncode != 0:
        raise GitCommandError(completed.stderr.strip() or "Unable to read commit diff.", completed.returncode)
    return truncate_text_for_render(completed.stdout, label="Diff")[0]


def diff_between_revisions(path, base_node, source_node):
    base_node = validate_revision_id(base_node)
    source_node = validate_revision_id(source_node, allow_null=False)
    if is_null_revision(base_node):
        args = ["diff", "--patch", "--find-renames", EMPTY_TREE_NODE, source_node]
    else:
        args = ["diff", "--patch", "--find-renames", base_node, source_node]
    completed = run_git(args, cwd=path, check=False)
    if completed.returncode != 0:
        raise GitCommandError(completed.stderr.strip() or "Unable to read diff.", completed.returncode)
    return truncate_text_for_render(completed.stdout, label="Diff")[0]


def ensure_clean_working_copy(path):
    completed = run_git(["status", "--porcelain"], cwd=path, check=False)
    if completed.returncode != 0:
        raise GitCommandError(completed.stderr.strip() or "Unable to inspect working copy.", completed.returncode)
    if completed.stdout.strip():
        raise GitCommandError("Target repository has uncommitted working copy changes.")


def issue_counts(repo_id):
    with db_connect() as conn:
        rows = conn.execute(
            "SELECT status, COUNT(*) AS count FROM issues WHERE repo_id = ? GROUP BY status",
            (repo_id,),
        ).fetchall()
    counts = {"open": 0, "closed": 0}
    for row in rows:
        counts[row["status"]] = row["count"]
    return counts


def pull_request_counts(repo_id):
    with db_connect() as conn:
        rows = conn.execute(
            "SELECT status, COUNT(*) AS count FROM pull_requests WHERE target_repo_id = ? GROUP BY status",
            (repo_id,),
        ).fetchall()
    counts = {"open": 0, "closed": 0, "merged": 0}
    for row in rows:
        counts[row["status"]] = row["count"]
    return counts


def list_issues(repo_id, status="open"):
    if status not in {"open", "closed", "all"}:
        status = "open"
    where = "WHERE issues.repo_id = ?"
    params = [repo_id]
    if status != "all":
        where += " AND issues.status = ?"
        params.append(status)
    with db_connect() as conn:
        return conn.execute(
            f"""
            SELECT issues.*, users.username AS author_username
            FROM issues
            JOIN users ON users.id = issues.author_id
            {where}
            ORDER BY issues.updated_at DESC, issues.number DESC
            """,
            params,
        ).fetchall()


def get_issue(repo_id, number):
    with db_connect() as conn:
        return conn.execute(
            """
            SELECT issues.*, users.username AS author_username
            FROM issues
            JOIN users ON users.id = issues.author_id
            WHERE issues.repo_id = ? AND issues.number = ?
            """,
            (repo_id, number),
        ).fetchone()


def list_issue_comments(issue_id):
    with db_connect() as conn:
        return conn.execute(
            """
            SELECT issue_comments.*, users.username AS author_username
            FROM issue_comments
            JOIN users ON users.id = issue_comments.author_id
            WHERE issue_comments.issue_id = ?
            ORDER BY issue_comments.created_at ASC, issue_comments.id ASC
            """,
            (issue_id,),
        ).fetchall()


def list_pull_request_comments(pull_request_id):
    with db_connect() as conn:
        return conn.execute(
            """
            SELECT pull_request_comments.*, users.username AS author_username
            FROM pull_request_comments
            JOIN users ON users.id = pull_request_comments.author_id
            WHERE pull_request_comments.pull_request_id = ?
            ORDER BY pull_request_comments.created_at ASC, pull_request_comments.id ASC
            """,
            (pull_request_id,),
        ).fetchall()


def list_commit_comments(repo_id, commit_node):
    with db_connect() as conn:
        return conn.execute(
            """
            SELECT commit_comments.*, users.username AS author_username
            FROM commit_comments
            JOIN users ON users.id = commit_comments.author_id
            WHERE commit_comments.repo_id = ? AND commit_comments.commit_node = ?
            ORDER BY commit_comments.created_at ASC, commit_comments.id ASC
            """,
            (repo_id, commit_node),
        ).fetchall()


def pull_request_select_sql(where_clause):
    return f"""
        SELECT
            pull_requests.*,
            author.username AS author_username,
            source_repo.name AS source_repo_name,
            source_owner.username AS source_owner_username,
            target_repo.name AS target_repo_name,
            target_owner.username AS target_owner_username,
            merged_by.username AS merged_by_username
        FROM pull_requests
        JOIN users AS author ON author.id = pull_requests.author_id
        JOIN repositories AS source_repo ON source_repo.id = pull_requests.source_repo_id
        JOIN users AS source_owner ON source_owner.id = source_repo.owner_id
        JOIN repositories AS target_repo ON target_repo.id = pull_requests.target_repo_id
        JOIN users AS target_owner ON target_owner.id = target_repo.owner_id
        LEFT JOIN users AS merged_by ON merged_by.id = pull_requests.merged_by_id
        {where_clause}
    """


def list_pull_requests(repo_id, status="open"):
    if status not in {"open", "closed", "merged", "all"}:
        status = "open"
    where = "WHERE pull_requests.target_repo_id = ?"
    params = [repo_id]
    if status != "all":
        where += " AND pull_requests.status = ?"
        params.append(status)
    with db_connect() as conn:
        return conn.execute(
            pull_request_select_sql(where) + " ORDER BY pull_requests.updated_at DESC, pull_requests.number DESC",
            params,
        ).fetchall()


def get_pull_request(repo_id, number):
    with db_connect() as conn:
        return conn.execute(
            pull_request_select_sql(
                "WHERE pull_requests.target_repo_id = ? AND pull_requests.number = ?"
            ),
            (repo_id, number),
        ).fetchone()


def stored_ref_name(ref):
    return "" if ref["type"] == REF_TYPE_TIP else ref.get("name", "")


def pr_ref_type(pr, prefix):
    return pr[f"{prefix}_ref_type"] or REF_TYPE_TIP


def pr_ref_name(pr, prefix):
    return pr[f"{prefix}_ref_name"] or ""


def resolve_pr_ref(path, pr, prefix):
    return resolve_repo_ref(path, pr_ref_type(pr, prefix), pr_ref_name(pr, prefix))


def pull_request_base_node(target_repo, source_repo, target_ref):
    source_path = repo_path(source_repo["owner_username"], source_repo["name"])
    target_node = target_ref.get("node") or NULL_REV
    if repo_has_revision(source_path, target_node):
        return target_node
    fork_base = source_repo["forked_from_node"] or NULL_REV
    if repo_has_revision(source_path, fork_base):
        return fork_base
    return NULL_REV


def create_pull_request(
    target_repo,
    source_repo,
    author,
    title,
    body,
    source_ref_type,
    source_ref_name,
    target_ref_type,
    target_ref_name,
):
    if not source_repo:
        raise ValueError("Choose a source repository.")
    source_is_target = source_repo["id"] == target_repo["id"]
    if not source_is_target and (
        source_repo["owner_id"] != author["id"] or source_repo["forked_from_repo_id"] != target_repo["id"]
    ):
        raise ValueError("Choose one of your forks of this repository.")
    target_path = repo_path(target_repo["owner_username"], target_repo["name"])
    source_path = repo_path(source_repo["owner_username"], source_repo["name"])
    source_ref = resolve_repo_ref(source_path, source_ref_type, source_ref_name)
    target_ref = resolve_repo_ref(target_path, target_ref_type, target_ref_name)
    if source_ref["type"] not in PULL_REQUEST_REF_TYPES:
        raise ValueError("Choose a branch or HEAD as the source ref.")
    if source_is_target and source_ref["type"] != REF_TYPE_BRANCH:
        raise ValueError("Choose a branch from this repository.")
    if target_ref["type"] not in TARGET_PULL_REQUEST_REF_TYPES:
        raise ValueError("Choose a target branch.")
    if (
        source_is_target
        and source_ref["type"] == REF_TYPE_BRANCH
        and target_ref["type"] == REF_TYPE_BRANCH
        and source_ref["name"] == target_ref["name"]
    ):
        raise ValueError("Choose different source and target branches.")
    source_node = source_ref.get("node")
    if not source_node:
        raise ValueError("Source repository has no commits.")
    base_node = pull_request_base_node(target_repo, source_repo, target_ref)
    now = utcnow()
    with db_connect() as conn:
        number = conn.execute(
            "SELECT COALESCE(MAX(number), 0) + 1 FROM pull_requests WHERE target_repo_id = ?",
            (target_repo["id"],),
        ).fetchone()[0]
        conn.execute(
            """
            INSERT INTO pull_requests (
                target_repo_id, source_repo_id, author_id, number, title, body,
                base_node, source_node, target_ref_type, target_ref_name,
                source_ref_type, source_ref_name, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                target_repo["id"],
                source_repo["id"],
                author["id"],
                number,
                title[:200],
                body[:5000],
                base_node,
                source_node,
                target_ref["type"],
                stored_ref_name(target_ref),
                source_ref["type"],
                stored_ref_name(source_ref),
                now,
                now,
            ),
        )
    return number


def pull_request_diff(pr):
    source_repo = get_repo_by_id(pr["source_repo_id"])
    if not source_repo:
        raise GitCommandError("Source repository no longer exists.")
    source_path = repo_path(source_repo["owner_username"], source_repo["name"])
    try:
        source_ref = resolve_pr_ref(source_path, pr, "source")
    except ValueError as exc:
        raise GitCommandError(str(exc)) from exc
    source_node = source_ref.get("node")
    if not source_node:
        raise GitCommandError("Source repository has no commits.")
    base_node = pr["base_node"] or NULL_REV
    if not repo_has_revision(source_path, base_node):
        raise GitCommandError("The pull request base revision is not present in the source repository.")
    return diff_between_revisions(source_path, base_node, source_node), source_node, source_ref


def source_fetch_ref(source_ref):
    if source_ref["type"] == REF_TYPE_BRANCH:
        return f"refs/heads/{source_ref['name']}"
    return "HEAD"


def merge_pull_request(pr, user):
    if pr["status"] != "open":
        raise ValueError("Only open pull requests can be merged.")
    target_repo = get_repo_by_id(pr["target_repo_id"])
    source_repo = get_repo_by_id(pr["source_repo_id"])
    if not target_repo or not source_repo:
        raise ValueError("Pull request repositories are no longer available.")

    target_path = repo_path(target_repo["owner_username"], target_repo["name"])
    source_path = repo_path(source_repo["owner_username"], source_repo["name"])
    try:
        source_ref = resolve_pr_ref(source_path, pr, "source")
        target_ref = resolve_pr_ref(target_path, pr, "target")
    except ValueError as exc:
        raise ValueError(str(exc)) from exc
    if target_ref["type"] != REF_TYPE_BRANCH:
        raise ValueError("The target ref must be a branch.")
    source_node = source_ref.get("node")
    if not source_node:
        raise ValueError("Source repository has no commits.")

    target_node_before = target_ref.get("node") or NULL_REV
    with tempfile.TemporaryDirectory(prefix="gitman-merge-") as tempdir:
        work_path = Path(tempdir) / "work"
        clone = run_git(["clone", str(target_path), str(work_path)], check=False, timeout=60)
        if clone.returncode != 0:
            raise GitCommandError(clone.stderr.strip() or "Unable to clone target repository.", clone.returncode)

        run_git(["config", "user.name", user["username"]], cwd=work_path)
        run_git(["config", "user.email", f"{user['username']}@gitman.local"], cwd=work_path)
        checkout = run_git(
            ["checkout", "-B", target_ref["name"], target_node_before],
            cwd=work_path,
            check=False,
            timeout=30,
        )
        if checkout.returncode != 0:
            raise GitCommandError(checkout.stderr.strip() or "Unable to check out target branch.", checkout.returncode)

        fetched = run_git(
            ["fetch", str(source_path), source_fetch_ref(source_ref)],
            cwd=work_path,
            check=False,
            timeout=60,
        )
        if fetched.returncode != 0:
            raise GitCommandError(fetched.stderr.strip() or "Unable to fetch source changes.", fetched.returncode)
        fetched_node = run_git(["rev-parse", "--verify", "FETCH_HEAD"], cwd=work_path).stdout.strip()
        if fetched_node != source_node:
            source_node = fetched_node

        if not repo_has_revision(work_path, source_node):
            raise GitCommandError("Source revision was not fetched into the target repository.")

        if target_node_before != NULL_REV and is_ancestor(work_path, source_node, target_node_before):
            merge_node = target_node_before
        elif target_node_before == NULL_REV or is_ancestor(work_path, target_node_before, source_node):
            merge = run_git(["merge", "--ff-only", "FETCH_HEAD"], cwd=work_path, check=False, timeout=60)
            if merge.returncode != 0:
                raise GitCommandError(merge.stderr.strip() or "Unable to fast-forward target branch.", merge.returncode)
            merge_node = source_node
        else:
            commit_message = (
                f"Merge pull request #{pr['number']} from "
                f"{source_repo['owner_username']}/{source_repo['name']}\n\n{pr['title']}"
            )
            merge = run_git(
                ["merge", "--no-ff", "FETCH_HEAD", "-m", commit_message],
                cwd=work_path,
                check=False,
                timeout=60,
            )
            if merge.returncode != 0:
                run_git(["merge", "--abort"], cwd=work_path, check=False)
                message = merge.stderr.strip() or merge.stdout.strip() or "Merge has conflicts."
                raise GitCommandError(message, merge.returncode)
            merge_node = repo_tip_node(work_path) or source_node

        push = run_git(
            ["push", "origin", f"{merge_node}:refs/heads/{target_ref['name']}"],
            cwd=work_path,
            check=False,
            timeout=60,
        )
        if push.returncode != 0:
            raise GitCommandError(push.stderr.strip() or "Unable to update target branch.", push.returncode)

    now = utcnow()
    with db_connect() as conn:
        conn.execute(
            """
            UPDATE pull_requests
            SET status = 'merged',
                source_node = ?,
                updated_at = ?,
                closed_at = ?,
                merged_at = ?,
                merged_by_id = ?,
                merge_node = ?
            WHERE id = ?
            """,
            (source_node, now, now, now, user["id"], merge_node, pr["id"]),
        )
        conn.execute(
            "UPDATE repositories SET updated_at = ? WHERE id = ?",
            (now, target_repo["id"]),
        )
    mark_repo_indexing(target_repo["id"], target_path)
    schedule_repo_metadata_refresh(target_repo["id"])
    return merge_node


def render_pull_request_detail(repo, path, pr, error=None, notice=None, comment_value=""):
    diff = ""
    diff_error = None
    current_source_node = pr["source_node"]
    current_source_ref = None
    try:
        diff, current_source_node, current_source_ref = pull_request_diff(pr)
    except GitCommandError as exc:
        diff_error = str(exc)
    return render(
        "pull_request_detail.tpl",
        repo=repo,
        pr=pr,
        comments=list_pull_request_comments(pr["id"]),
        comment_value=comment_value,
        diff=diff,
        diff_error=diff_error,
        current_source_node=current_source_node,
        current_source_ref=current_source_ref,
        error=error,
        notice=notice,
        **repo_page_context(repo, path),
    )


def render_commit_detail(repo, path, commit, error=None, notice=None, comment_value=""):
    return render(
        "commit_detail.tpl",
        repo=repo,
        commit=commit,
        commit_source_ref=commit_ref(path, commit["node"]),
        diff=commit_diff(path, commit["node"]),
        comments=list_commit_comments(repo["id"], commit["node"]),
        comment_value=comment_value,
        error=error,
        notice=notice,
        **repo_page_context(repo, path),
    )


def user_owns_repo(user, repo):
    return bool(user and repo and user["id"] == repo["owner_id"])


def user_contributes_to_repo(user, repo):
    if not user or not repo:
        return False
    with db_connect() as conn:
        row = conn.execute(
            "SELECT 1 FROM repo_contributors WHERE repo_id = ? AND user_id = ?",
            (repo["id"], user["id"]),
        ).fetchone()
    return bool(row)


def user_can_maintain_repo(user, repo):
    return user_owns_repo(user, repo) or user_contributes_to_repo(user, repo)


def repo_page_context(repo, path=None, selected_ref=None):
    started = time.monotonic()
    if path is None:
        path = repo_path(repo["owner_username"], repo["name"])
    user = current_user()
    active_tab = repo_active_tab(repo)
    show_ref_picker = active_tab in REF_PICKER_TABS
    if selected_ref is None:
        selected_ref = selected_repo_ref(path) if show_ref_picker else default_code_ref(path)
    selected_revision = ref_revision(selected_ref)
    fork_target_id = repo["forked_from_repo_id"] or repo["id"]
    source_repo = get_repo_by_id(repo["forked_from_repo_id"]) if repo["forked_from_repo_id"] else None
    metadata = repo_metadata_for_context(repo, path)
    context = {
        "commit_count": cached_commit_count(repo, path, selected_revision, metadata),
        "issue_counts": issue_counts(repo["id"]),
        "pr_counts": pull_request_counts(repo["id"]),
        "star_count": repo_star_count(repo["id"]),
        "is_starred": user_starred_repo(user, repo),
        "is_owner": user_owns_repo(user, repo),
        "can_maintain": user_can_maintain_repo(user, repo),
        "has_fork": bool(user and user_has_fork_for_target(user["id"], fork_target_id)),
        "repo_active_tab": active_tab,
        "show_ref_picker": show_ref_picker,
        "source_repo": source_repo,
        "repo_index_status": metadata["status"] if metadata else "",
        "repo_indexing": bool(metadata and metadata["status"] == REPO_INDEX_INDEXING),
        "repo_branch_count": int(metadata["branch_count"] or 0) if metadata else 0,
        "repo_tag_count": int(metadata["tag_count"] or 0) if metadata else 0,
        "selected_ref": selected_ref,
        "selected_ref_label": ref_option_label(selected_ref) if selected_ref else "",
        "ref_options": repo_ref_picker_options(path, metadata=metadata) if show_ref_picker else [],
        "selected_ref_value": ref_option_value(
            selected_ref.get("type", REF_TYPE_TIP),
            selected_ref.get("name", ""),
        )
        if selected_ref
        else "",
    }
    log_perf("repo_page_context", time.monotonic() - started, f"{repo['owner_username']}/{repo['name']}")
    return context


def repo_active_tab(repo):
    base_path = f"/{repo['owner_username']}/{repo['name']}"
    current_path = request.path.rstrip("/")
    if current_path == base_path:
        return "overview"
    for tab, suffix in (
        ("source", "/src"),
        ("commits", "/commits"),
        ("tags", "/tags"),
        ("branches", "/branches"),
        ("issues", "/issues"),
        ("pulls", "/pulls"),
        ("settings", "/settings"),
    ):
        if current_path == base_path + suffix or current_path.startswith(base_path + suffix + "/"):
            return tab
    return ""


def quote_path(path):
    return quote(path, safe="/")


def clone_url(owner_username, repo_name):
    scheme = request.get_header("X-Forwarded-Proto") or request.urlparts.scheme
    host = request.get_header("Host")
    if host and host.startswith("0.0.0.0"):
        host = "127.0.0.1" + host[len("0.0.0.0") :]
    return f"{scheme}://{host}/git/{owner_username}/{repo_name}"


def parse_basic_auth(rate_limit_kind=None, clear_on_success=True):
    header = request.get_header("Authorization", "")
    if not header.lower().startswith("basic "):
        return None, None
    token = header.split(" ", 1)[1].strip()
    try:
        decoded = base64.b64decode(token).decode("utf-8")
        username, password = decoded.split(":", 1)
    except (ValueError, UnicodeDecodeError, base64.binascii.Error):
        if rate_limit_kind:
            if rate_limit_blocked(rate_limit_kind, ""):
                return None, "rate_limited"
            record_auth_failure(rate_limit_kind, "")
        return None, "invalid"
    username = username.strip().lower()
    if rate_limit_kind and rate_limit_blocked(rate_limit_kind, username):
        return None, "rate_limited"
    user = get_user_by_username(username)
    if user and verify_password(password, user["password_hash"]):
        if rate_limit_kind and clear_on_success:
            clear_auth_failures(rate_limit_kind, username)
        return user, None
    if rate_limit_kind:
        record_auth_failure(rate_limit_kind, username)
    return None, "invalid"


def git_service_from_request():
    service = request.query.get("service")
    if service:
        return service
    path_info = request.environ.get("PATH_INFO", "")
    parts = path_info.strip("/").split("/")
    if len(parts) >= 4 and parts[0] == "git":
        return parts[3]
    return ""


def is_git_write_request():
    return git_service_from_request() == "git-receive-pack"


def basic_auth_challenge(message="Authentication required."):
    return HTTPResponse(
        message + "\n",
        status=401,
        headers={"WWW-Authenticate": 'Basic realm="GitMan"'},
        content_type="text/plain; charset=utf-8",
    )


def git_http_backend_executable():
    found = shutil.which("git-http-backend")
    if found:
        return found
    completed = run_git(["--exec-path"], check=False)
    if completed.returncode == 0:
        candidate = Path(completed.stdout.strip()) / "git-http-backend"
        if candidate.exists():
            return str(candidate)
    raise GitCommandError("git-http-backend executable was not found.")


def spool_request_body(source, expected_size=0):
    body_file = tempfile.TemporaryFile()
    size = 0
    remaining = expected_size if expected_size > 0 else None
    try:
        while remaining is None or remaining > 0:
            read_size = IMPORT_UPLOAD_CHUNK_BYTES if remaining is None else min(IMPORT_UPLOAD_CHUNK_BYTES, remaining)
            chunk = source.read(read_size)
            if not chunk:
                break
            body_file.write(chunk)
            size += len(chunk)
            if remaining is not None:
                remaining -= len(chunk)
        body_file.seek(0)
        if expected_size > 0 and size != expected_size:
            body_file.close()
            raise ValueError("Git request body was incomplete.")
        return body_file, size
    except Exception:
        body_file.close()
        raise


def git_http_backend_response(repo, auth_user, on_success=None, buffer_response=False):
    mount = f"/git/{repo['owner_username']}/{repo['name']}"
    original_path = request.environ.get("PATH_INFO", request.path)
    rest = original_path[len(mount) :] if original_path.startswith(mount) else ""
    service = git_service_from_request()
    debug_receive = service == "git-receive-pack"
    body_file = None
    body_size = 0
    if request.method == "POST":
        body_file, body_size = spool_request_body(request.environ["wsgi.input"], request_content_length())
        if debug_receive:
            log_perf(
                "git-receive-request",
                PERF_LOG_THRESHOLD_MS / 1000 if PERF_LOG_THRESHOLD_MS else 1,
                (
                    f"path={original_path} content_length={request_content_length()} "
                    f"spooled={body_size} content_type={request.environ.get('CONTENT_TYPE', '')!r} "
                    f"transfer_encoding={request.get_header('Transfer-Encoding', '')!r} "
                    f"expect={request.get_header('Expect', '')!r}"
                ),
            )

    env = git_env()
    env.update(
        {
            "GIT_PROJECT_ROOT": str(REPO_ROOT),
            "GIT_HTTP_EXPORT_ALL": "1",
            "PATH_INFO": f"/{repo['owner_username']}/{repo['name']}{rest}",
            "REQUEST_METHOD": request.method,
            "QUERY_STRING": request.query_string or "",
            "CONTENT_TYPE": request.environ.get("CONTENT_TYPE", ""),
            "CONTENT_LENGTH": str(body_size),
            "REMOTE_ADDR": request.environ.get("REMOTE_ADDR", ""),
        }
    )
    if auth_user:
        env["REMOTE_USER"] = auth_user["username"]
    git_protocol = request.get_header("Git-Protocol", "")
    if git_protocol:
        env["HTTP_GIT_PROTOCOL"] = git_protocol
    content_encoding = request.get_header("Content-Encoding", "")
    if content_encoding:
        env["HTTP_CONTENT_ENCODING"] = content_encoding
    apply_git_config_env(env, {"pack.threads": GIT_HTTP_PACK_THREADS})

    stderr_file = tempfile.TemporaryFile()
    command = [git_http_backend_executable()]
    if GIT_HTTP_NICE > 0:
        command = ["nice", "-n", str(GIT_HTTP_NICE), *command]
    process = subprocess.Popen(
        command,
        stdin=body_file if body_file else subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=stderr_file,
        env=env,
    )
    try:
        header_lines = []
        while True:
            line = process.stdout.readline()
            if not line:
                break
            stripped = line.rstrip(b"\r\n")
            if not stripped:
                break
            header_lines.append(stripped.decode("latin-1"))

        if not header_lines and process.poll() is not None and process.returncode != 0:
            stderr_file.seek(0)
            message = stderr_file.read().decode("utf-8", "replace").strip() or "Git HTTP backend failed."
            raise GitCommandError(message, process.returncode)
        if debug_receive:
            log_perf(
                "git-receive-headers",
                PERF_LOG_THRESHOLD_MS / 1000 if PERF_LOG_THRESHOLD_MS else 1,
                f"returncode={process.poll()} headers={header_lines!r}",
            )
    except Exception:
        process.kill()
        process.wait()
        stderr_file.close()
        if body_file:
            body_file.close()
        raise

    status_code = 200
    headers = {}
    for line in header_lines:
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if key.lower() == "status":
            try:
                status_code = int(value.split(" ", 1)[0])
            except ValueError:
                status_code = 200
        else:
            headers[key] = value

    if buffer_response:
        body_chunks = []
        response_size = 0
        try:
            while True:
                chunk = process.stdout.read(1024 * 1024)
                if not chunk:
                    break
                response_size += len(chunk)
                if MAX_GIT_RESPONSE_BYTES and response_size > MAX_GIT_RESPONSE_BYTES:
                    raise GitResponseTooLarge("Git response too large.")
                body_chunks.append(chunk)
            process.wait()
            stderr_file.seek(0)
            stderr = stderr_file.read().decode("utf-8", "replace").strip()
            if debug_receive:
                log_perf(
                    "git-receive-complete",
                    PERF_LOG_THRESHOLD_MS / 1000 if PERF_LOG_THRESHOLD_MS else 1,
                    (
                        f"returncode={process.returncode} status={status_code} "
                        f"response_size={response_size} stderr={stderr!r}"
                    ),
                )
            if process.returncode != 0:
                log_perf(
                    "git-http-backend-error",
                    PERF_LOG_THRESHOLD_MS / 1000 if PERF_LOG_THRESHOLD_MS else 1,
                    stderr or f"returncode={process.returncode}",
                )
                if not body_chunks:
                    return HTTPResponse(
                        (stderr or "Git HTTP backend failed.") + "\n",
                        status=500,
                        content_type="text/plain; charset=utf-8",
                    )
            if process.returncode == 0 and status_code < 400 and on_success:
                on_success()
            return HTTPResponse(body=b"".join(body_chunks), status=status_code, headers=headers)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
            stderr_file.close()
            if body_file:
                body_file.close()

    def stream_git_response():
        try:
            while True:
                chunk = process.stdout.read(1024 * 1024)
                if not chunk:
                    break
                yield chunk
            process.wait()
            if process.returncode != 0:
                stderr_file.seek(0)
                stderr = stderr_file.read().decode("utf-8", "replace").strip()
                log_perf(
                    "git-http-backend-error",
                    PERF_LOG_THRESHOLD_MS / 1000 if PERF_LOG_THRESHOLD_MS else 1,
                    stderr or f"returncode={process.returncode}",
                )
            if process.returncode == 0 and status_code < 400 and on_success:
                try:
                    on_success()
                except Exception as exc:
                    log_perf("git-http-success-hook-error", PERF_LOG_THRESHOLD_MS / 1000 if PERF_LOG_THRESHOLD_MS else 1, str(exc))
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
            stderr_file.close()
            if body_file:
                body_file.close()

    return HTTPResponse(body=stream_git_response(), status=status_code, headers=headers)


@app.route("/static/<filename:path>")
def static_assets(filename):
    return static_file(filename, root=str(BASE_DIR / "static"))


@app.route("/favicon.ico")
def favicon():
    return HTTPResponse(status=204)


@app.route("/")
def index():
    return render("index.tpl", actions=list_recent_actions(50))


@app.route("/-/repos/search")
def public_repo_search():
    results = search_public_repos(request.query.get("q", ""))
    return HTTPResponse(json.dumps({"results": results}), content_type="application/json")


@app.route("/signup", method=["GET", "POST"])
def signup():
    if request.method == "GET":
        return render("signup.tpl", next_url=safe_next_url(request.query.get("next")))

    username_raw = request.forms.get("username", "")
    password = request.forms.get("password", "")
    next_url = safe_next_url(request.forms.get("next"))
    signup_identifier = username_raw.strip().lower()
    if rate_limit_blocked("signup", signup_identifier):
        return too_many_requests_response()
    try:
        username = normalize_slug(username_raw, "Username")
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters.")
        with db_connect() as conn:
            conn.execute(
                "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
                (username, hash_password(password), utcnow()),
            )
        user = get_user_by_username(username)
        login_user(user)
        clear_auth_failures("signup", username)
        redirect(next_url)
    except (sqlite3.IntegrityError, ValueError) as exc:
        record_auth_failure("signup", signup_identifier)
        message = "Username already exists." if isinstance(exc, sqlite3.IntegrityError) else str(exc)
        return render("signup.tpl", error=message, username=username_raw, next_url=next_url)


@app.route("/login", method=["GET", "POST"])
def login():
    if request.method == "GET":
        return render("login.tpl", next_url=safe_next_url(request.query.get("next")))

    username = request.forms.get("username", "").strip().lower()
    password = request.forms.get("password", "")
    next_url = safe_next_url(request.forms.get("next"))
    if rate_limit_blocked("login", username):
        return too_many_requests_response()
    user = get_user_by_username(username)
    if not user or not verify_password(password, user["password_hash"]):
        record_auth_failure("login", username)
        return render("login.tpl", error="Invalid username or password.", username=username, next_url=next_url)
    clear_auth_failures("login", username)
    login_user(user)
    redirect(next_url)


@app.post("/logout")
def logout():
    logout_user()
    redirect("/")


@app.route("/settings/profile", method=["GET", "POST"])
def edit_profile():
    user = require_login()
    if request.method == "GET":
        return render("edit_profile.tpl", profile=user)

    values = profile_form_values(request.forms, user)
    try:
        values["website"] = normalize_website(values["website"])
        with db_connect() as conn:
            conn.execute(
                """
                UPDATE users
                SET display_name = ?, bio = ?, website = ?
                WHERE id = ?
                """,
                (values["display_name"], values["bio"], values["website"], user["id"]),
            )
        refreshed = get_user_by_id(user["id"])
        request.environ["gitman.user"] = refreshed
        return render("edit_profile.tpl", profile=refreshed, notice="Profile updated.")
    except ValueError as exc:
        return render("edit_profile.tpl", profile=values, error=str(exc))


@app.route("/new", method=["GET", "POST"])
def new_repo():
    user = require_login()
    if request.method == "GET":
        return render("new_repo.tpl")

    repo_name_raw = request.forms.get("name", "")
    description = request.forms.get("description", "").strip()[:500]
    try:
        repo_name = normalize_slug(repo_name_raw, "Repository name")
        create_repository(user, repo_name, description)
        redirect(f"/{user['username']}/{repo_name}")
    except (ValueError, GitCommandError) as exc:
        return render("new_repo.tpl", error=str(exc), name=repo_name_raw, description=description)


@app.route("/<username>")
def user_profile(username):
    profile_user = get_user_by_username(username.lower())
    if not profile_user:
        abort(404, "User not found.")
    user = current_user()
    active_tab = request.query.get("tab", "owned")
    if active_tab not in {"owned", "stars"}:
        active_tab = "owned"
    owned_repos = list_owned_repos(profile_user["id"])
    starred_repos = list_starred_repos(profile_user["id"])
    return render(
        "profile.tpl",
        profile_user=profile_user,
        owned_repos=owned_repos,
        starred_repos=starred_repos,
        repos=starred_repos if active_tab == "stars" else owned_repos,
        active_tab=active_tab,
        is_self=bool(user and user["id"] == profile_user["id"]),
    )


@app.route("/<owner>/<repo_name>")
def repo_overview(owner, repo_name):
    repo = get_repo(owner, repo_name)
    if not repo:
        abort(404, "Repository not found.")
    path = repo_path(owner, repo_name)
    selected_ref = selected_repo_ref(path)
    revision = ref_revision(selected_ref)
    readme_name, readme, readme_truncated = readme_preview_for_repo(path, revision=revision)
    readme_is_markdown = is_markdown_file(readme_name)
    context = repo_page_context(repo, path, selected_ref=selected_ref)
    return render(
        "repo.tpl",
        repo=repo,
        clone_url=clone_url(owner, repo_name),
        readme_name=readme_name,
        readme=readme,
        readme_html=render_markdown(readme) if readme is not None and readme_is_markdown else None,
        readme_is_markdown=readme_is_markdown,
        readme_truncated=readme_truncated,
        **context,
    )


@app.post("/<owner>/<repo_name>/star")
def repo_star(owner, repo_name):
    user = require_login()
    repo = get_repo(owner, repo_name)
    if not repo:
        abort(404, "Repository not found.")
    action = request.forms.get("action", "star")
    if action == "unstar":
        unstar_repo(user, repo)
    else:
        star_repo(user, repo)
    redirect(f"/{owner}/{repo_name}")


@app.route("/<owner>/<repo_name>/fork", method=["GET", "POST"])
def fork_repo(owner, repo_name):
    user = require_login()
    source_repo = get_repo(owner, repo_name)
    if not source_repo:
        abort(404, "Repository not found.")
    default_description = source_repo["description"]
    if request.method == "GET":
        return render(
            "fork_repo.tpl",
            source_repo=source_repo,
            name=source_repo["name"],
            description=default_description,
        )

    repo_name_raw = request.forms.get("name", "")
    description = request.forms.get("description", default_description).strip()[:500]
    try:
        fork_name = normalize_slug(repo_name_raw, "Repository name")
        fork_repository(user, source_repo, fork_name, description)
        redirect(f"/{user['username']}/{fork_name}")
    except (ValueError, GitCommandError) as exc:
        return render(
            "fork_repo.tpl",
            source_repo=source_repo,
            name=repo_name_raw,
            description=description,
            error=str(exc),
        )


def render_repo_settings_page(repo, path, contributor_username="", error=None, notice=None):
    return render(
        "repo_settings.tpl",
        repo=repo,
        contributors=list_repo_contributors(repo["id"]),
        contributor_username=contributor_username,
        pages_settings=pages_settings_context(repo),
        error=error,
        notice=notice,
        **repo_page_context(repo, path),
    )


@app.post("/<owner>/<repo_name>/settings/import-bundle")
def repo_settings_import_bundle(owner, repo_name):
    user = require_login()
    repo = get_repo(owner, repo_name)
    if not repo:
        abort(404, "Repository not found.")
    if not user_owns_repo(user, repo):
        abort(403, "Only the owner can update repository settings.")
    if not request_content_type().startswith("application/octet-stream"):
        abort(400, "Git bundle uploads must use application/octet-stream.")

    path = repo_path(owner, repo_name)
    filename = os.path.basename(request.query.get("filename", "repo.bundle")) or "repo.bundle"
    upload = StreamingUpload(filename, request.environ["wsgi.input"])
    try:
        import_git_bundle(repo, path, upload)
        updated_repo = get_repo(owner, repo_name)
        return render_repo_settings_page(updated_repo, path, notice="Git bundle imported.")
    except UploadTooLarge as exc:
        abort(413, str(exc))
    except (ValueError, GitCommandError) as exc:
        repo = get_repo(owner, repo_name) or repo
        return render_repo_settings_page(repo, path, error=str(exc))


@app.post("/<owner>/<repo_name>/settings/import-bundle/chunk")
def repo_settings_import_bundle_chunk(owner, repo_name):
    user = require_login()
    repo = get_repo(owner, repo_name)
    if not repo:
        abort(404, "Repository not found.")
    if not user_owns_repo(user, repo):
        abort(403, "Only the owner can update repository settings.")
    if not request_content_type().startswith("application/octet-stream"):
        abort(400, "Git bundle uploads must use application/octet-stream.")

    path = repo_path(owner, repo_name)
    filename = os.path.basename(request.query.get("filename", "repo.bundle")) or "repo.bundle"
    upload_id = request.query.get("upload_id", "")
    if not UPLOAD_ID_RE.match(upload_id):
        abort(400, "Invalid upload id.")

    total = parse_nonnegative_int(request.query.get("total", ""), "total")
    offset = parse_nonnegative_int(request.query.get("offset", ""), "offset")
    chunk_size = request_content_length()
    if total <= 0:
        abort(400, "Upload is empty.")
    if MAX_IMPORT_BYTES and total > MAX_IMPORT_BYTES:
        abort(413, "Request body too large.")
    if chunk_size <= 0 or offset + chunk_size > total:
        abort(400, "Invalid upload chunk.")

    chunks_dir = import_upload_chunks_dir()
    chunk_path = chunks_dir / f"{user['id']}-{repo['id']}-{upload_id}.bundle"
    if offset == 0 and chunk_path.exists():
        chunk_path.unlink()

    current_size = chunk_path.stat().st_size if chunk_path.exists() else 0
    if current_size != offset:
        if current_size < offset:
            discard_upload_chunk(request.environ["wsgi.input"], chunk_size)
            if offset + chunk_size >= total and not repo_is_empty(path):
                updated_repo = get_repo(owner, repo_name)
                return render_repo_settings_page(updated_repo, path, notice="Git bundle imported.")
            return HTTPResponse(
                "Upload chunk offset mismatch.\n",
                status=409,
                content_type="text/plain; charset=utf-8",
            )
        if current_size >= offset + chunk_size:
            discard_upload_chunk(request.environ["wsgi.input"], chunk_size)
            if current_size >= total:
                if not repo_is_empty(path):
                    updated_repo = get_repo(owner, repo_name)
                    return render_repo_settings_page(updated_repo, path, notice="Git bundle imported.")
                try:
                    return import_complete_upload_chunk(repo, path, filename, chunk_path)
                except UploadTooLarge as exc:
                    abort(413, str(exc))
                except (ValueError, GitCommandError) as exc:
                    return HTTPResponse(f"{exc}\n", status=400, content_type="text/plain; charset=utf-8")
            return HTTPResponse("OK\n", content_type="text/plain; charset=utf-8")
        try:
            with chunk_path.open("r+b") as target:
                target.truncate(offset)
        except OSError:
            return HTTPResponse(
                "Upload chunk offset mismatch.\n",
                status=409,
                content_type="text/plain; charset=utf-8",
            )

    try:
        save_upload_chunk(request.environ["wsgi.input"], chunk_path, chunk_size, offset)
        current_size = chunk_path.stat().st_size
        if current_size < total:
            return HTTPResponse("OK\n", content_type="text/plain; charset=utf-8")
        if current_size != total:
            raise ValueError("Upload size mismatch.")

        return import_complete_upload_chunk(repo, path, filename, chunk_path)
    except UploadTooLarge as exc:
        abort(413, str(exc))
    except (ValueError, GitCommandError) as exc:
        return HTTPResponse(f"{exc}\n", status=400, content_type="text/plain; charset=utf-8")
    finally:
        try:
            if chunk_path.exists() and chunk_path.stat().st_size >= total:
                chunk_path.unlink()
        except OSError:
            pass


@app.route("/<owner>/<repo_name>/settings", method=["GET", "POST"])
def repo_settings(owner, repo_name):
    user = require_login()
    repo = get_repo(owner, repo_name)
    if not repo:
        abort(404, "Repository not found.")
    if not user_owns_repo(user, repo):
        abort(403, "Only the owner can update repository settings.")

    path = repo_path(owner, repo_name)
    if request.method == "GET":
        return render_repo_settings_page(repo, path)

    action = request.forms.get("action", "save")
    if action == "delete":
        confirmation = request.forms.get("confirm_name", "").strip()
        if confirmation != repo["name"]:
            return render_repo_settings_page(repo, path, error=f'Type "{repo["name"]}" to confirm deletion.')
        delete_repository(repo, path)
        redirect(f"/{owner}")

    if action == "add_contributor":
        contributor_username = request.forms.get("username", "").strip()
        try:
            add_repo_contributor(repo, user, contributor_username)
            redirect(f"/{owner}/{repo_name}/settings")
        except ValueError as exc:
            return render_repo_settings_page(repo, path, contributor_username=contributor_username, error=str(exc))

    if action == "remove_contributor":
        try:
            contributor_user_id = int(request.forms.get("user_id", ""))
        except ValueError:
            abort(400, "Invalid contributor.")
        remove_repo_contributor(repo, contributor_user_id)
        redirect(f"/{owner}/{repo_name}/settings")

    if action == "update_pages":
        pages_docs_enabled = int(not is_user_site_repo(repo) and request.forms.get("pages_docs_enabled") == "1")
        with db_connect() as conn:
            conn.execute(
                "UPDATE repositories SET pages_docs_enabled = ?, updated_at = ? WHERE id = ?",
                (pages_docs_enabled, utcnow(), repo["id"]),
            )
        updated_repo = get_repo(owner, repo_name)
        return render_repo_settings_page(updated_repo, path, notice="Pages settings updated.")

    if action == "verify_custom_domain":
        try:
            verify_custom_domain_for_repo(repo)
            repo = get_repo(owner, repo_name)
            return render_repo_settings_page(repo, path, notice="Custom domain verified.")
        except ValueError as exc:
            return render_repo_settings_page(repo, path, error=str(exc))

    if action == "import_bundle":
        try:
            import_git_bundle(repo, path, request.files.get("bundle"))
            updated_repo = get_repo(owner, repo_name)
            return render_repo_settings_page(updated_repo, path, notice="Git bundle imported.")
        except UploadTooLarge as exc:
            abort(413, str(exc))
        except (ValueError, GitCommandError) as exc:
            repo = get_repo(owner, repo_name) or repo
            return render_repo_settings_page(repo, path, error=str(exc))

    description = request.forms.get("description", "").strip()[:500]
    with db_connect() as conn:
        conn.execute(
            "UPDATE repositories SET description = ?, updated_at = ? WHERE id = ?",
            (description, utcnow(), repo["id"]),
        )
    updated_repo = get_repo(owner, repo_name)
    sync_repo_git_config(updated_repo)
    return render_repo_settings_page(updated_repo, path, notice="Repository settings updated.")


@app.route("/<owner>/<repo_name>/src")
@app.route("/<owner>/<repo_name>/src/<file_path:path>")
def repo_source(owner, repo_name, file_path=""):
    repo = get_repo(owner, repo_name)
    if not repo:
        abort(404, "Repository not found.")
    file_path = clean_repo_path(file_path)
    path = repo_path(owner, repo_name)
    selected_ref = selected_repo_ref(path)
    revision = ref_revision(selected_ref)
    if file_path:
        try:
            content = read_file_bytes(path, file_path, revision=revision)
        except GitCommandError:
            content = None
    else:
        content = None

    if content is not None:
        is_binary = b"\0" in content[:4096]
        text_content = content.decode("utf-8", "replace") if not is_binary else ""
        return render(
            "file.tpl",
            repo=repo,
            file_path=file_path,
            content=text_content,
            is_binary=is_binary,
            language_class=highlight_language_class(file_path),
            size=len(content),
            quote_path=quote_path,
            **repo_page_context(repo, path, selected_ref=selected_ref),
        )

    entries = git_tree_entries(path, revision, file_path)
    if file_path and not entries:
        abort(404, "Path not found.")

    return render(
        "source.tpl",
        repo=repo,
        current_path=file_path,
        entries=entries,
        quote_path=quote_path,
        **repo_page_context(repo, path, selected_ref=selected_ref),
    )


@app.route("/<owner>/<repo_name>/raw/<file_path:path>")
def repo_raw(owner, repo_name, file_path):
    repo = get_repo(owner, repo_name)
    if not repo:
        abort(404, "Repository not found.")
    file_path = clean_repo_path(file_path)
    path = repo_path(owner, repo_name)
    selected_ref = selected_repo_ref(path)
    revision = ref_revision(selected_ref)
    try:
        content = read_file_bytes(path, file_path, revision=revision)
    except GitCommandError:
        abort(404, "File not found.")
    content_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
    return HTTPResponse(content, content_type=content_type)


@app.route("/<owner>/<repo_name>/archive/<node>.zip")
def repo_archive(owner, repo_name, node):
    repo = get_repo(owner, repo_name)
    if not repo:
        abort(404, "Repository not found.")
    node = validate_revision_id(node, allow_null=False)
    path = repo_path(owner, repo_name)
    completed = run_git(["archive", "--format=zip", node], cwd=path, check=False, text=False)
    if completed.returncode != 0:
        abort(404, "Archive not found.")
    return HTTPResponse(
        completed.stdout,
        content_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{repo_name}-{node[:12]}.zip"'},
    )


@app.route("/<owner>/<repo_name>/commits")
def repo_commits(owner, repo_name):
    repo = get_repo(owner, repo_name)
    if not repo:
        abort(404, "Repository not found.")
    path = repo_path(owner, repo_name)
    selected_ref = selected_repo_ref(path)
    revision = ref_revision(selected_ref)
    return render(
        "commits.tpl",
        repo=repo,
        commits=commit_log(path, revision=revision),
        **repo_page_context(repo, path, selected_ref=selected_ref),
    )


@app.route("/<owner>/<repo_name>/tags")
def repo_tags(owner, repo_name):
    repo = get_repo(owner, repo_name)
    if not repo:
        abort(404, "Repository not found.")
    path = repo_path(owner, repo_name)
    metadata = repo_metadata_for_context(repo, path)
    tag_count = int(metadata["tag_count"] or 0) if metadata else 0
    tags = cached_ref_rows(metadata, "tag_refs_json") or list_repo_tags(path, limit=REF_LIST_LIMIT)
    return render(
        "tags.tpl",
        repo=repo,
        tags=tags,
        tags_truncated=bool(tag_count and tag_count > len(tags)),
        tag_count=tag_count or len(tags),
        ref_list_limit=REF_LIST_LIMIT,
        clone_url=clone_url(owner, repo_name),
        **repo_page_context(repo, path),
    )


@app.route("/<owner>/<repo_name>/branches")
def repo_branches(owner, repo_name):
    repo = get_repo(owner, repo_name)
    if not repo:
        abort(404, "Repository not found.")
    path = repo_path(owner, repo_name)
    metadata = repo_metadata_for_context(repo, path)
    branch_count = int(metadata["branch_count"] or 0) if metadata else 0
    branches = cached_ref_rows(metadata, "branch_refs_json") or list_repo_branches(path, limit=REF_LIST_LIMIT)
    return render(
        "branches.tpl",
        repo=repo,
        branches=branches,
        branches_truncated=bool(branch_count and branch_count > len(branches)),
        branch_count=branch_count or len(branches),
        ref_list_limit=REF_LIST_LIMIT,
        clone_url=clone_url(owner, repo_name),
        **repo_page_context(repo, path),
    )


@app.route("/<owner>/<repo_name>/refs/search")
def repo_ref_search(owner, repo_name):
    repo = get_repo(owner, repo_name)
    if not repo:
        abort(404, "Repository not found.")
    path = repo_path(owner, repo_name)
    results = search_repo_refs(path, request.query.get("q", ""))
    return HTTPResponse(json.dumps({"results": results}), content_type="application/json")


@app.route("/<owner>/<repo_name>/commits/<node>", method=["GET", "POST"])
def repo_commit(owner, repo_name, node):
    repo = get_repo(owner, repo_name)
    if not repo:
        abort(404, "Repository not found.")
    path = repo_path(owner, repo_name)
    commit = commit_detail(path, node)
    if request.method == "POST":
        user = require_login()
        action = request.forms.get("action")
        if action == "comment":
            body = request.forms.get("body", "").strip()
            if not body:
                return render_commit_detail(
                    repo,
                    path,
                    commit,
                    error="Comment body is required.",
                    comment_value=body,
                )
            now = utcnow()
            with db_connect() as conn:
                conn.execute(
                    """
                    INSERT INTO commit_comments (repo_id, commit_node, author_id, body, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (repo["id"], commit["node"], user["id"], body[:5000], now, now),
                )
        redirect(f"/{owner}/{repo_name}/commits/{commit['node']}")
    return render_commit_detail(repo, path, commit)


@app.route("/<owner>/<repo_name>/pulls")
def repo_pull_requests(owner, repo_name):
    repo = get_repo(owner, repo_name)
    if not repo:
        abort(404, "Repository not found.")
    path = repo_path(owner, repo_name)
    status = request.query.get("status", "open")
    counts = pull_request_counts(repo["id"])
    return render(
        "pull_requests.tpl",
        repo=repo,
        pull_requests=list_pull_requests(repo["id"], status),
        status=status if status in {"open", "closed", "merged", "all"} else "open",
        counts=counts,
        **repo_page_context(repo, path),
    )


@app.route("/<owner>/<repo_name>/pulls/new", method=["GET", "POST"])
def new_pull_request(owner, repo_name):
    user = require_login()
    repo = get_repo(owner, repo_name)
    if not repo:
        abort(404, "Repository not found.")
    path = repo_path(owner, repo_name)
    forks = list_user_forks_for_target(user["id"], repo["id"])
    source_options = source_repo_ref_options(repo, include_tip=False)
    for fork in forks:
        source_options.extend(source_repo_ref_options(fork))
    target_options = target_repo_ref_options(path)
    target_option_values = {option["value"] for option in target_options}
    selected_source_ref = request.forms.get("source_ref") if request.method == "POST" else request.query.get("source_ref")
    selected_target_ref = request.forms.get("target_ref") if request.method == "POST" else request.query.get("target_ref")
    if not selected_source_ref and source_options:
        selected_source_ref = source_options[0]["value"]
    if not selected_target_ref and target_options:
        default_target = default_code_ref(path)
        selected_target_ref = ref_option_value(default_target["type"], default_target.get("name", ""))
        if selected_target_ref not in target_option_values:
            selected_target_ref = target_options[0]["value"]
    if selected_target_ref and selected_target_ref not in target_option_values and target_options:
        selected_target_ref = target_options[0]["value"]
    title_value = request.forms.get("title", "") if request.method == "POST" else ""
    body_value = request.forms.get("body", "") if request.method == "POST" else ""

    if request.method == "POST":
        try:
            source_repo_id, source_ref_type, source_ref_name = parse_source_ref_option_value(selected_source_ref)
            target_ref_type, target_ref_name = parse_ref_option_value(
                selected_target_ref,
                allowed_types=TARGET_PULL_REQUEST_REF_TYPES,
            )
        except ValueError as exc:
            return render(
                "new_pull_request.tpl",
                repo=repo,
                forks=forks,
                source_options=source_options,
                target_options=target_options,
                selected_source_ref=selected_source_ref,
                selected_target_ref=selected_target_ref,
                title_value=title_value,
                body_value=body_value,
                error=str(exc),
                **repo_page_context(repo, path),
            )
        source_repo = get_repo_by_id(source_repo_id) if source_repo_id else None
        title = title_value.strip()
        body = body_value.strip()
        if not title:
            return render(
                "new_pull_request.tpl",
                repo=repo,
                forks=forks,
                source_options=source_options,
                target_options=target_options,
                selected_source_ref=selected_source_ref,
                selected_target_ref=selected_target_ref,
                title_value=title_value,
                body_value=body_value,
                error="Pull request title is required.",
                **repo_page_context(repo, path),
            )
        try:
            number = create_pull_request(
                repo,
                source_repo,
                user,
                title,
                body,
                source_ref_type,
                source_ref_name,
                target_ref_type,
                target_ref_name,
            )
            redirect(f"/{owner}/{repo_name}/pulls/{number}")
        except (ValueError, GitCommandError) as exc:
            return render(
                "new_pull_request.tpl",
                repo=repo,
                forks=forks,
                source_options=source_options,
                target_options=target_options,
                selected_source_ref=selected_source_ref,
                selected_target_ref=selected_target_ref,
                title_value=title_value,
                body_value=body_value,
                error=str(exc),
                **repo_page_context(repo, path),
            )

    return render(
        "new_pull_request.tpl",
        repo=repo,
        forks=forks,
        source_options=source_options,
        target_options=target_options,
        selected_source_ref=selected_source_ref,
        selected_target_ref=selected_target_ref,
        title_value=title_value,
        body_value=body_value,
        **repo_page_context(repo, path),
    )


@app.route("/<owner>/<repo_name>/pulls/<number:int>", method=["GET", "POST"])
def pull_request_detail(owner, repo_name, number):
    repo = get_repo(owner, repo_name)
    if not repo:
        abort(404, "Repository not found.")
    path = repo_path(owner, repo_name)
    pr = get_pull_request(repo["id"], number)
    if not pr:
        abort(404, "Pull request not found.")

    if request.method == "POST":
        user = require_login()
        action = request.forms.get("action")
        now = utcnow()
        if action == "comment":
            body = request.forms.get("body", "").strip()
            if not body:
                return render_pull_request_detail(
                    repo,
                    path,
                    pr,
                    error="Comment body is required.",
                    comment_value=body,
                )
            with db_connect() as conn:
                conn.execute(
                    """
                    INSERT INTO pull_request_comments (pull_request_id, author_id, body, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (pr["id"], user["id"], body[:5000], now, now),
                )
                conn.execute(
                    "UPDATE pull_requests SET updated_at = ? WHERE id = ?",
                    (now, pr["id"]),
                )
            redirect(f"/{owner}/{repo_name}/pulls/{number}")

        if not user_can_maintain_repo(user, repo):
            abort(403, "Only maintainers can update pull requests.")
        if action == "merge":
            try:
                merge_pull_request(pr, user)
                redirect(f"/{owner}/{repo_name}/pulls/{number}")
            except (ValueError, GitCommandError) as exc:
                return render_pull_request_detail(repo, path, pr, error=str(exc))
        if action == "close" and pr["status"] == "open":
            now = utcnow()
            with db_connect() as conn:
                conn.execute(
                    """
                    UPDATE pull_requests
                    SET status = 'closed', updated_at = ?, closed_at = ?
                    WHERE id = ?
                    """,
                    (now, now, pr["id"]),
                )
            redirect(f"/{owner}/{repo_name}/pulls/{number}")

    return render_pull_request_detail(repo, path, pr)


@app.route("/<owner>/<repo_name>/issues")
def repo_issues(owner, repo_name):
    repo = get_repo(owner, repo_name)
    if not repo:
        abort(404, "Repository not found.")
    path = repo_path(owner, repo_name)
    status = request.query.get("status", "open")
    counts = issue_counts(repo["id"])
    context = repo_page_context(repo, path)
    return render(
        "issues.tpl",
        repo=repo,
        issues=list_issues(repo["id"], status),
        status=status if status in {"open", "closed", "all"} else "open",
        counts=counts,
        **context,
    )


@app.route("/<owner>/<repo_name>/issues/new", method=["GET", "POST"])
def new_issue(owner, repo_name):
    user = require_login()
    repo = get_repo(owner, repo_name)
    if not repo:
        abort(404, "Repository not found.")
    path = repo_path(owner, repo_name)

    if request.method == "GET":
        return render("new_issue.tpl", repo=repo, title_value="", body_value="", **repo_page_context(repo, path))

    title = request.forms.get("title", "").strip()
    body = request.forms.get("body", "").strip()
    if not title:
        return render(
            "new_issue.tpl",
            repo=repo,
            title_value=title,
            body_value=body,
            error="Issue title is required.",
            **repo_page_context(repo, path),
        )

    now = utcnow()
    with db_connect() as conn:
        number = conn.execute(
            "SELECT COALESCE(MAX(number), 0) + 1 FROM issues WHERE repo_id = ?",
            (repo["id"],),
        ).fetchone()[0]
        conn.execute(
            """
            INSERT INTO issues (repo_id, author_id, number, title, body, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (repo["id"], user["id"], number, title[:200], body[:5000], now, now),
        )
    redirect(f"/{owner}/{repo_name}/issues/{number}")


@app.route("/<owner>/<repo_name>/issues/<number:int>", method=["GET", "POST"])
def issue_detail(owner, repo_name, number):
    repo = get_repo(owner, repo_name)
    if not repo:
        abort(404, "Repository not found.")
    path = repo_path(owner, repo_name)
    issue = get_issue(repo["id"], number)
    if not issue:
        abort(404, "Issue not found.")

    if request.method == "POST":
        user = require_login()
        action = request.forms.get("action")
        now = utcnow()
        if action == "comment":
            body = request.forms.get("body", "").strip()
            if not body:
                return render(
                    "issue_detail.tpl",
                    repo=repo,
                    issue=issue,
                    comments=list_issue_comments(issue["id"]),
                    comment_value=body,
                    error="Comment body is required.",
                    **repo_page_context(repo, path),
                )
            with db_connect() as conn:
                conn.execute(
                    """
                    INSERT INTO issue_comments (issue_id, author_id, body, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (issue["id"], user["id"], body[:5000], now, now),
                )
                conn.execute(
                    "UPDATE issues SET updated_at = ? WHERE id = ?",
                    (now, issue["id"]),
                )
        else:
            if not user_can_maintain_repo(user, repo):
                abort(403, "Only maintainers can update issues.")
            if action == "close" and issue["status"] != "closed":
                with db_connect() as conn:
                    conn.execute(
                        "UPDATE issues SET status = 'closed', updated_at = ?, closed_at = ? WHERE id = ?",
                        (now, now, issue["id"]),
                    )
            elif action == "reopen" and issue["status"] != "open":
                with db_connect() as conn:
                    conn.execute(
                        "UPDATE issues SET status = 'open', updated_at = ?, closed_at = NULL WHERE id = ?",
                        (now, issue["id"]),
                    )
        redirect(f"/{owner}/{repo_name}/issues/{number}")

    return render(
        "issue_detail.tpl",
        repo=repo,
        issue=issue,
        comments=list_issue_comments(issue["id"]),
        comment_value="",
        **repo_page_context(repo, path),
    )


@app.route("/git/<owner>/<repo_name>", method=["GET", "POST"])
@app.route("/git/<owner>/<repo_name>/<git_path:path>", method=["GET", "POST"])
def git_http(owner, repo_name, git_path=""):
    repo = get_repo(owner, repo_name)
    if not repo:
        abort(404, "Repository not found.")

    is_write = is_git_write_request()
    auth_user, auth_error = parse_basic_auth("git" if is_write else None, clear_on_success=not is_write)
    if is_write:
        if auth_error == "rate_limited":
            return too_many_requests_response()
        if auth_error:
            return basic_auth_challenge("Invalid Git credentials.")
        if not auth_user:
            return basic_auth_challenge()
        if not user_can_maintain_repo(auth_user, repo):
            record_auth_failure("git", auth_user["username"])
            return HTTPResponse(
                "Push not authorized for this repository.\n",
                status=403,
                content_type="text/plain; charset=utf-8",
            )
        clear_auth_failures("git", auth_user["username"])
        prepare_repo_for_receive(repo_path(owner, repo_name))

    def after_successful_write():
        now = utcnow()
        with db_connect() as conn:
            conn.execute("UPDATE repositories SET updated_at = ? WHERE id = ?", (now, repo["id"]))
        mark_repo_indexing(repo["id"], repo_path(owner, repo_name))
        schedule_repo_metadata_refresh(repo["id"])

    try:
        return git_http_backend_response(
            repo,
            auth_user,
            on_success=after_successful_write if is_write else None,
            buffer_response=is_write,
        )
    except ValueError as exc:
        return HTTPResponse(f"{exc}\n", status=400, content_type="text/plain; charset=utf-8")


@app.error(404)
def not_found(error):
    return render("error.tpl", title="Not found", message=getattr(error, "body", "Not found."))


@app.error(403)
def forbidden(error):
    return render("error.tpl", title="Forbidden", message=getattr(error, "body", "Forbidden."))


@app.error(413)
def request_too_large(error):
    return render("error.tpl", title="Request too large", message=getattr(error, "body", "Request body too large."))


@app.error(500)
def server_error(error):
    return render("error.tpl", title="Server error", message="Something went wrong.")


class ThreadingWSGIServer(ThreadingMixIn, WSGIServer):
    daemon_threads = True


validate_startup_config()
init_db()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    run(
        app,
        host="0.0.0.0",
        port=port,
        debug=DEBUG,
        reloader=DEBUG,
        server="wsgiref",
        server_class=ThreadingWSGIServer,
    )
