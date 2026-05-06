# GitMan

GitMan is a small Bottle app for hosting public Git repositories with local user accounts. It includes repository browsing, README rendering, issues, forks, comments, pull requests, stars, Pages-style static sites, and Git over HTTP for clone, fetch, and push.

## Getting Started

Install dependencies and run the app:

```sh
python3 -m pip install -r requirements.txt
python3 app.py
```

Then open `http://127.0.0.1:8080`, sign up, and create a repository. Instructions will be provided on how to commit to the newly created repo.

## Configuration

- `SECRET_KEY`: Bottle signed-cookie secret
- `GITMAN_DB`: SQLite database path, default `./data/gitman.sqlite3`
- `GITMAN_REPO_ROOT`: Git repository root, default `./data/repos`
- `GITMAN_DEBUG`: set to `1` for debug mode and reloader
- `GITMAN_GIT_BINARY`: Git executable name or full path, default `git`
- `GITMAN_PAGES_DOMAIN`: wildcard Pages domain, default `gitman.io`
- `PORT`: HTTP port, default `8080`

When `GITMAN_DEBUG` is off, `SECRET_KEY` must be set to a non-default value before startup.

Repositories and their Git data live on local disk, so keep the database and repo root on persistent storage.

## License

GitMan is licensed under the BSD 3-Clause License. See [LICENSE](https://gitman.io/patx/gitman/src/LICENSE).
