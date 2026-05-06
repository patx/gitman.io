# GitMan

A small Bottle app that hosts public Git repositories with local user accounts.

Features include public user profiles, repository browsing, commit/branch diffs with comments, README rendering, issues, pull requests, repository contributors, stars, Pages-style static sites, and HTTP Git clone, fetch, and push.

## Run locally

```sh
python3 -m pip install -r requirements.txt
SECRET_KEY=change-me GITMAN_DEBUG=1 python3 app.py
```

Then open `http://127.0.0.1:8080`, create an account, and create a repository.

## Site layout

- `/`: home page and recent activity feed. Logged-in users also get the global repository search box here.
- `/signup` and `/login`: account creation and sign-in.
- `/settings/profile`: edit your display name, bio, and website.
- `/new`: create a new repository under your account.
- `/<username>`: a user profile with owned repositories and starred repositories.
- `/<owner>/<repo>`: repository overview with the README, description, star/fork actions, and clone URL.
- `/<owner>/<repo>/src`: browse files and directories. File pages include syntax-highlighted previews and a raw file link.
- `/<owner>/<repo>/commits`: view commits for the selected branch, tag, commit, or `HEAD`.
- `/<owner>/<repo>/tags` and `/<owner>/<repo>/branches`: inspect repository tags and branches.
- `/<owner>/<repo>/issues`: list, create, comment on, close, and reopen issues.
- `/<owner>/<repo>/pulls`: list, create, comment on, close, and merge pull requests.
- `/<owner>/<repo>/settings`: owner-only repository settings for descriptions, contributors, and deletion.
- `/git/<owner>/<repo>`: the Git HTTP remote used by `git clone`, `git fetch`, and `git push`.
- `<username>.gitman.io`: static Pages site from `<username>/<username>.gitman.io`.
- `<username>.gitman.io/<repo>`: static project docs from `<username>/<repo>/docs` when enabled in repository settings.

Repository pages share a tab bar for Overview, Source, Commits, Issues, Pull requests, Star, Fork, and owner Settings. Repository pages that display code also show a ref picker next to the repository title. Use it to switch branches, tags, commits, or `HEAD`; its footer links to the full Tags and Branches pages.

## Search

- Search all public repositories from the search box on `/` after logging in. It searches repository names and `owner/repo` names, with fuzzy matching. The JSON endpoint is `/-/repos/search?q=<query>`.
- Search branches, tags, and commits inside a repository from the ref picker on Overview, Source, Commits, Tags, and Branches pages. The JSON endpoint is `/<owner>/<repo>/refs/search?q=<query>`.
- Browse files from the Source tab. GitMan does not currently provide full-text code search, so clone the repository locally and use tools such as `rg` or `git grep` when you need content search.
- Issues and pull requests can be filtered by status. They do not currently have keyword search.

## Common workflows

### Create an account and profile

1. Sign up at `/signup`.
2. Open your profile from the header.
3. Use `/settings/profile` to add a display name, bio, and website.

Usernames and repository names must be 2-63 characters and may contain lowercase letters, numbers, dots, dashes, and underscores.

### Create a repository

1. Log in and open `/new`.
2. Pick a repository name and optional description.
3. Open the new repository page and copy the clone URL.

For a new local checkout:

```sh
git clone http://127.0.0.1:8080/git/<user>/<repo>
cd <repo>
echo "# <repo>" > README.md
git add README.md
git commit -m "Initial commit"
git push -u origin main
```

For an existing local Git repository:

```sh
cd /path/to/existing-repo
git remote add origin http://127.0.0.1:8080/git/<user>/<repo>
git push -u origin HEAD:main
```

### Browse code and refs

- Use Overview for the README and clone URL.
- Use Source to browse directories, view files, and open raw files.
- Use Commits for commit history and commit diffs. Logged-in users can comment on commits.
- Use the ref picker to switch branch, tag, commit, or `HEAD` context while browsing code.
- Use Tags and Branches from the ref picker footer to inspect all tags and branches.
- Download a zip archive from `/<owner>/<repo>/archive/<commit>.zip`.

### Issues

1. Open the Issues tab.
2. Use New issue to create an issue.
3. Comment from the issue detail page.
4. Repository owners and contributors can close or reopen issues.

### Pull requests

Pull requests can come from another branch in the same repository or from one of your forks.

1. Fork the repository when you do not have direct write access.
2. Push your changes to a branch in your repository or fork.
3. Open `/<owner>/<repo>/pulls/new`.
4. Choose the source repository/ref and target branch.
5. Submit the pull request.

Repository owners and contributors can comment, close, and merge pull requests. Merges are attempted with Git: fast-forward when possible, otherwise a merge commit is created. Merge conflicts are reported in the pull request page.

### Collaboration and maintenance

- Star repositories from the repository tab bar. Starred repositories appear on your profile under the Starred tab.
- Owners can add contributors from repository Settings. Contributors can push, maintain issues, and maintain pull requests.
- Only the owner can edit repository settings, add or remove contributors, or delete the repository.
- Deleting a repository permanently removes its database records and Git data from disk.

### Pages sites

- Create `<username>.gitman.io` under your account and push static files to its default branch root. Requests to `<username>.gitman.io` serve those files.
- For other repositories, add static files under `docs/`, then enable Pages in repository Settings. The docs site is served at `<username>.gitman.io/<repo>/`.
- Pages serves exact files, directory `index.html`, extensionless `.html` paths, and a repository `404.html` fallback when present.
- To use a custom domain, add a root `CNAME` file to `<username>/<username>.gitman.io`, open that repository's Settings page, create the shown DNS TXT record, then click Verify DNS. Custom domains also serve enabled project docs paths.

## Git client use

Clone and fetch are public:

```sh
git clone http://127.0.0.1:8080/git/<owner>/<repo>
```

Push requires the repository owner's or a contributor's username and password:

```sh
git push http://<username>@127.0.0.1:8080/git/<owner>/<repo>
```

You can also set the username in the remote URL:

```sh
git remote set-url origin http://<username>@127.0.0.1:8080/git/<owner>/<repo>
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
- `GITMAN_PAGES_DOMAIN`: wildcard Pages domain. Defaults to `gitman.io`.
- `GITMAN_RATE_LIMIT_ENABLED`: set to `0` to disable in-memory login/signup/git auth throttling.
- `GITMAN_RATE_LIMIT_MAX_FAILURES`: failed attempts before throttling. Defaults to `5`.
- `GITMAN_RATE_LIMIT_WINDOW_SECONDS`: rate limit window. Defaults to `300`.
- `GITMAN_RATE_LIMIT_COOLDOWN_SECONDS`: throttle duration. Defaults to `300`.
- `PORT`: HTTP port. Defaults to `8080`.

When `GITMAN_DEBUG` is disabled, `SECRET_KEY` must be set to a non-default value before the app starts.

This v1 stores repositories on local disk. Do not deploy it to ephemeral filesystems unless repository storage is mounted persistently.

SQLite is configured with WAL mode and a busy timeout so a small multi-worker deployment can share one database file. Keep `GITMAN_DB` on a local persistent filesystem used by one host; network or synced filesystems can break SQLite locking semantics and should use a server database instead.

## Basic VPS deployment

These steps describe a small single-host deployment on a Debian or Ubuntu VPS using systemd, Gunicorn, Nginx, SQLite, and local persistent repository storage.

### 1. Install system packages

```sh
sudo apt update
sudo apt install -y python3 python3-venv git nginx sqlite3 rsync
```

### 2. Create a service user and directories

```sh
sudo useradd --system --create-home --home /opt/gitman --shell /usr/sbin/nologin gitman
sudo mkdir -p /opt/gitman/app /var/lib/gitman/repos
sudo chown -R gitman:gitman /opt/gitman /var/lib/gitman
```

### 3. Install the app

Copy or clone this repository into `/opt/gitman/app`, then install Python dependencies:

```sh
sudo -u gitman git clone <repo-url> /opt/gitman/app
cd /opt/gitman/app
sudo -u gitman python3 -m venv .venv
sudo -u gitman .venv/bin/pip install --upgrade pip
sudo -u gitman .venv/bin/pip install -r requirements.txt
```

If you copied the source instead of cloning it, make sure `/opt/gitman/app` is owned by `gitman:gitman`.

### 4. Add a systemd service

Generate a long secret:

```sh
openssl rand -hex 32
```

Create `/etc/systemd/system/gitman.service`:

```ini
[Unit]
Description=GitMan
After=network.target

[Service]
User=gitman
Group=gitman
WorkingDirectory=/opt/gitman/app
Environment=SECRET_KEY=replace-with-the-generated-secret
Environment=GITMAN_DB=/var/lib/gitman/gitman.sqlite3
Environment=GITMAN_REPO_ROOT=/var/lib/gitman/repos
Environment=PORT=8080
ExecStart=/opt/gitman/app/.venv/bin/gunicorn --workers 2 --threads 4 --bind 127.0.0.1:8080 app:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Start it:

```sh
sudo systemctl daemon-reload
sudo systemctl enable --now gitman
sudo systemctl status gitman
```

### 5. Put Nginx in front

Create `/etc/nginx/sites-available/gitman`:

```nginx
server {
    listen 80;
    server_name git.example.com;

    client_max_body_size 0;

    location /git/ {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_request_buffering off;
        proxy_buffering off;
        proxy_read_timeout 3600;
        proxy_send_timeout 3600;
    }

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 3600;
    }
}
```

Enable the site:

```sh
sudo ln -s /etc/nginx/sites-available/gitman /etc/nginx/sites-enabled/gitman
sudo nginx -t
sudo systemctl reload nginx
```

Use your DNS provider to point the hostname at the VPS. For Pages, also point the wildcard hostname for `GITMAN_PAGES_DOMAIN`, such as `*.gitman.io`, at the VPS and include that wildcard in the Nginx `server_name` values. Verified custom domains must also point at the VPS.

For HTTPS on a small VPS, I recommend Certbot with Nginx:

```sh
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d git.example.com
sudo certbot renew --dry-run
```

Certbot will install the certificate, update Nginx, and set up renewal. Use real TLS before exposing login or push access on the public internet.

### 6. Operate and update

Check logs:

```sh
sudo journalctl -u gitman -f
sudo tail -f /var/log/nginx/access.log /var/log/nginx/error.log
```

Update the app:

```sh
cd /opt/gitman/app
sudo -u gitman git pull
sudo -u gitman .venv/bin/pip install -r requirements.txt
sudo systemctl restart gitman
```

Back up both the SQLite database and the repository root together:

```sh
sudo systemctl stop gitman
sudo sqlite3 /var/lib/gitman/gitman.sqlite3 ".backup '/var/backups/gitman.sqlite3'"
sudo rsync -a /var/lib/gitman/repos/ /var/backups/gitman-repos/
sudo systemctl start gitman
```

For production, keep `/var/lib/gitman` on persistent local disk, restrict SSH access to the VPS, enable HTTPS, and monitor disk usage. GitMan does not currently include an admin panel or private repositories; repository pages and clone/fetch access are public.

## License

GitMan is licensed under the BSD 3-Clause License. See [LICENSE](https://gitman.io/patx/gitman/src/LICENSE).
