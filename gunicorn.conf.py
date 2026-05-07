import os


def env_int(name, default, minimum=1):
    try:
        value = int(os.environ.get(name, str(default)))
    except ValueError:
        return default
    return max(minimum, value)


import_timeout = env_int("GITMAN_IMPORT_TIMEOUT_SECONDS", 3600, minimum=1)
timeout = env_int("GITMAN_GUNICORN_TIMEOUT_SECONDS", import_timeout + 300, minimum=1)
graceful_timeout = timeout
