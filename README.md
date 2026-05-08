# GitMan

GitMan is a small Bottle app for hosting public Git repositories with local user accounts. It includes repository browsing, README rendering, issues, forks, comments, pull requests, stars, Pages-style static sites, and Git over HTTP for clone, fetch, and push.

## Getting Started

Install dependencies and run the app:

```sh
python3 -m pip install -r requirements.txt
python3 app.py
```

Then open `http://127.0.0.1:8080`, sign up, and create a repository. Instructions will be provided on how to commit to the newly created repo.

## How the App Works

GitMan keeps application metadata in SQLite and keeps Git data in bare repositories on disk. By default, the database is created at `./data/gitman.sqlite3` and repositories are stored under `./data/repos/<owner>/<repo>`.

All repositories are public for web browsing, clone, and fetch. Pushes go through Git over HTTP at `/git/<owner>/<repo>` and require HTTP Basic Auth with a GitMan account that owns the repository or has been added as a contributor.

Creating a repository initializes an empty bare Git repo with `HEAD` pointing at `main`. The repository page shows clone instructions until the first push lands, then renders a README preview when it finds `README.md`, `README.rst`, `README.txt`, or `README`.

Empty repositories can also be populated from a full Git bundle in repository settings. From the existing repository, run `git bundle create repo.bundle --all`, then upload `repo.bundle` before any commits have been pushed to the GitMan repository.

The web UI reads directly from Git for source browsing, raw file downloads, commit history, branches, tags, archives, diffs, and README content. Markdown README files are rendered to sanitized HTML before display, and repository descriptions plus issue, pull request, and commit comments support sanitized links.

Issues, comments, stars, contributors, forks, and pull request records are stored in SQLite. Forking creates a bare clone of the source repository. Pull requests compare a source ref against a target branch, and maintainers can close or merge them from the browser.

Pages-style static hosting is driven by the Git repository contents. A user site repository named `<username>.<GITMAN_PAGES_DOMAIN>` is served from its repository root at `https://<username>.<GITMAN_PAGES_DOMAIN>/`; project Pages can be enabled in repository settings and are served from that repository's `docs/` directory. User sites can also advertise a custom domain with a root `CNAME` file and a DNS TXT verification record.

## Configuration

- `SECRET_KEY`: Bottle signed-cookie secret
- `GITMAN_DB`: SQLite database path, default `./data/gitman.sqlite3`
- `GITMAN_REPO_ROOT`: Git repository root, default `./data/repos`
- `GITMAN_DEBUG`: set to `1` for debug mode and reloader
- `GITMAN_GIT_BINARY`: Git executable name or full path, default `git`
- `GITMAN_PAGES_DOMAIN`: wildcard Pages domain, default `gitman.io`
- `GITMAN_MAX_FORM_BYTES`: maximum browser form body size, default `65536`
- `GITMAN_MAX_IMPORT_BYTES`: maximum Git bundle import upload size, default `2147483648`
- `GITMAN_IMPORT_TIMEOUT_SECONDS`: maximum Git bundle verify/fetch time, default `3600`
- `GITMAN_GUNICORN_TIMEOUT_SECONDS`: Gunicorn worker timeout, default `GITMAN_IMPORT_TIMEOUT_SECONDS + 300`
- `GITMAN_MAX_RENDER_BYTES`: maximum file preview size, default `262144`
- `GITMAN_MAX_GIT_RESPONSE_BYTES`: maximum Git HTTP backend response size, default `268435456`
- `GITMAN_REPO_SEARCH_CANDIDATE_LIMIT`: maximum repositories loaded for fuzzy search scoring, default `1000`
- `GITMAN_ACTIVITY_REPO_SCAN_LIMIT`: maximum repositories scanned for commit activity, default `100`
- `GITMAN_RATE_LIMIT_ENABLED`: set to `0` to disable login, signup, and Git push auth rate limiting
- `GITMAN_AUTH_RATE_LIMIT_PRUNE_BATCH_SIZE`: maximum expired rate-limit rows deleted during one cleanup, default `1000`
- `PORT`: HTTP port, default `8080`

Rate-limit counters are stored in the configured SQLite database, so failed-attempt tracking is shared across worker processes.

When `GITMAN_DEBUG` is off, `SECRET_KEY` must be set to a non-default value before startup.

Repositories and their Git data live on local disk, so keep the database and repo root on persistent storage. The app uses SQLite WAL mode and shells out to Git, so the process user needs read/write access to both paths and access to the configured Git executable. It is recommended to run behind nginx/gunicorn.

## License

GitMan is licensed under the BSD 3-Clause License. See [LICENSE](https://gitman.io/patx/gitman/src/LICENSE).
