# GitMan

A small Bottle app that hosts public Git repositories with local user accounts.

Features include public user profiles, repository browsing, commit/branch diffs with comments, README rendering, issues, pull requests, repository contributors, stars, and HTTP Git clone/fetch/push etc.

## Run locally

```sh
python3 -m pip install -r requirements.txt
SECRET_KEY=change-me python3 app.py
```

Then open `http://127.0.0.1:8080`, create an account, and create a repository.

## Git client use

Clone and fetch are public:

```sh
git clone http://127.0.0.1:8080/git/<user>/<repo>
```

Push requires the repository owner's or a contributor's username and password:

```sh
git push http://<user>@127.0.0.1:8080/git/<user>/<repo>
```

## Configuration

- `SECRET_KEY`: Bottle signed-cookie secret.
- `GITMAN_DB`: SQLite database path. Defaults to `./data/gitman.sqlite3`.
- `GITMAN_REPO_ROOT`: Git repository root. Defaults to `./data/repos`.
- `GITMAN_DEBUG`: set to `1` for Bottle debug/reloader.
- `GITMAN_MAX_FORM_BYTES`: maximum browser form POST size. Defaults to `65536`.
- `GITMAN_MAX_RENDER_BYTES`: maximum README/file/diff preview size. Defaults to `262144`.
- `GITMAN_MAX_GIT_RESPONSE_BYTES`: maximum buffered Git HTTP response size. Defaults to `268435456`.
- `GITMAN_GIT_BINARY`: Git executable name or full path. Defaults to `git`.
- `GITMAN_RATE_LIMIT_ENABLED`: set to `0` to disable in-memory login/signup/git auth throttling.
- `GITMAN_RATE_LIMIT_MAX_FAILURES`: failed attempts before throttling. Defaults to `5`.
- `GITMAN_RATE_LIMIT_WINDOW_SECONDS`: rate limit window. Defaults to `300`.
- `GITMAN_RATE_LIMIT_COOLDOWN_SECONDS`: throttle duration. Defaults to `300`.
- `PORT`: HTTP port. Defaults to `8080`.

When `GITMAN_DEBUG` is disabled, `SECRET_KEY` must be set to a non-default value before the app starts.

This v1 stores repositories on local disk. Do not deploy it to ephemeral filesystems unless repository storage is mounted persistently.

SQLite is configured with WAL mode and a busy timeout so a small multi-worker deployment can share one database file. Keep `GITMAN_DB` on a local persistent filesystem used by one host; network or synced filesystems can break SQLite locking semantics and should use a server database instead.
