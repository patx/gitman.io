#!/usr/bin/env python3
import argparse
import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import urlopen


def parse_args():
    parser = argparse.ArgumentParser(
        description="Compare large Git HTTP pushes across local GitMan server runtimes."
    )
    parser.add_argument("--source-repo", required=True, help="Local Git repository to push from.")
    parser.add_argument("--remote-path", required=True, help="GitMan remote path, e.g. /git/alice/demo.")
    parser.add_argument(
        "--remote-template",
        default="http://127.0.0.1:{port}{remote_path}",
        help=(
            "Remote URL template. Supports {port}, {mode}, and {remote_path}. "
            "Embed credentials here or rely on a credential helper."
        ),
    )
    parser.add_argument(
        "--modes",
        default="wsgiref,gunicorn-sync,gunicorn-gthread,gunicorn-config",
        help="Comma-separated modes: wsgiref, gunicorn-sync, gunicorn-gthread, gunicorn-config.",
    )
    parser.add_argument("--start-port", type=int, default=18080)
    parser.add_argument("--server-timeout", type=int, default=7500)
    parser.add_argument("--push-timeout", type=int, default=7200)
    parser.add_argument("--threads", type=int, default=16)
    parser.add_argument(
        "--refspec",
        default="HEAD:refs/heads/gitman-runtime-matrix-{mode}",
        help="Refspec template for the push. Supports {mode}.",
    )
    parser.add_argument("--http-version", default="HTTP/1.1", choices=["HTTP/1.1", "HTTP/2"])
    parser.add_argument("--workdir", default=str(Path(__file__).resolve().parents[1]))
    return parser.parse_args()


def redact_url(url):
    parts = urlsplit(url)
    if "@" not in parts.netloc:
        return url
    host = parts.netloc.rsplit("@", 1)[1]
    return urlunsplit((parts.scheme, f"<credentials>@{host}", parts.path, parts.query, parts.fragment))


def server_command(mode, port, args):
    if mode == "wsgiref":
        return [sys.executable, "app.py"], {"PORT": str(port)}
    if mode == "gunicorn-sync":
        return [
            "gunicorn",
            "--config",
            "/dev/null",
            "--bind",
            f"127.0.0.1:{port}",
            "--workers",
            "1",
            "--worker-class",
            "sync",
            "--timeout",
            str(args.server_timeout),
            "app:app",
        ], {}
    if mode == "gunicorn-gthread":
        return [
            "gunicorn",
            "--config",
            "/dev/null",
            "--bind",
            f"127.0.0.1:{port}",
            "--workers",
            "1",
            "--worker-class",
            "gthread",
            "--threads",
            str(args.threads),
            "--timeout",
            str(args.server_timeout),
            "app:app",
        ], {}
    if mode == "gunicorn-config":
        return ["gunicorn", "--bind", f"127.0.0.1:{port}", "app:app"], {}
    raise ValueError(f"Unsupported mode: {mode}")


def wait_for_server(port, process, timeout=20):
    deadline = time.monotonic() + timeout
    url = f"http://127.0.0.1:{port}/"
    while time.monotonic() < deadline:
        if process.poll() is not None:
            return False
        try:
            with urlopen(url, timeout=1) as response:
                return 200 <= response.status < 500
        except URLError:
            time.sleep(0.2)
    return False


def stop_process(process):
    if process.poll() is not None:
        return
    process.send_signal(signal.SIGTERM)
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)


def tail(path, limit=80):
    try:
        lines = path.read_text(errors="replace").splitlines()
    except OSError:
        return ""
    return "\n".join(lines[-limit:])


def run_mode(mode, port, args, log_dir):
    command, extra_env = server_command(mode, port, args)
    env = os.environ.copy()
    env.setdefault("SECRET_KEY", "gitman-runtime-matrix-secret")
    env.setdefault("GITMAN_GUNICORN_TIMEOUT_SECONDS", str(args.server_timeout))
    env.update(extra_env)
    log_path = log_dir / f"{mode}.server.log"
    with log_path.open("wb") as log_file:
        process = subprocess.Popen(
            command,
            cwd=args.workdir,
            env=env,
            stdout=log_file,
            stderr=subprocess.STDOUT,
        )
    if not wait_for_server(port, process):
        stop_process(process)
        return {
            "mode": mode,
            "ok": False,
            "detail": "server did not become ready",
            "server_log": tail(log_path),
        }

    remote = args.remote_template.format(port=port, mode=mode, remote_path=args.remote_path)
    refspec = args.refspec.format(mode=mode)
    push_command = [
        "git",
        "-C",
        args.source_repo,
        "-c",
        f"http.version={args.http_version}",
        "push",
        remote,
        refspec,
    ]
    started = time.monotonic()
    completed = subprocess.run(
        push_command,
        cwd=args.workdir,
        env={**env, "GIT_TERMINAL_PROMPT": "0"},
        capture_output=True,
        text=True,
        errors="replace",
        timeout=args.push_timeout,
    )
    elapsed = time.monotonic() - started
    stop_process(process)
    return {
        "mode": mode,
        "ok": completed.returncode == 0,
        "detail": f"exit={completed.returncode} elapsed={elapsed:.1f}s remote={redact_url(remote)}",
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
        "server_log": tail(log_path),
    }


def main():
    args = parse_args()
    source_repo = Path(args.source_repo)
    if not source_repo.exists():
        print(f"source repo does not exist: {source_repo}", file=sys.stderr)
        return 2
    modes = [mode.strip() for mode in args.modes.split(",") if mode.strip()]
    with tempfile.TemporaryDirectory(prefix="gitman-runtime-matrix-") as temp_dir:
        log_dir = Path(temp_dir)
        results = []
        for index, mode in enumerate(modes):
            port = args.start_port + index
            print(f"== {mode} on port {port} ==", flush=True)
            try:
                result = run_mode(mode, port, args, log_dir)
            except subprocess.TimeoutExpired as exc:
                result = {"mode": mode, "ok": False, "detail": f"push timed out: {exc}"}
            results.append(result)
            status = "PASS" if result["ok"] else "FAIL"
            print(f"{status}: {result['detail']}", flush=True)
            if result.get("stderr"):
                print(result["stderr"], flush=True)

        print("\nSummary")
        for result in results:
            status = "PASS" if result["ok"] else "FAIL"
            print(f"{status} {result['mode']}: {result['detail']}")
        if any(not result["ok"] for result in results):
            print("\nServer log tails for failures")
            for result in results:
                if not result["ok"] and result.get("server_log"):
                    print(f"\n--- {result['mode']} ---")
                    print(result["server_log"])
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
