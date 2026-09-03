from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path


KEY_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*$")
SCOPE_KEYS = {
    "observability": {
        "ALIBABA_CLOUD_ACCESS_KEY_ID",
        "ALIBABA_CLOUD_ACCESS_KEY_SECRET",
        "ALIBABA_CLOUD_REGION",
    },
    "observability-client": {
        "ZSTT_CLIENT_ALIBABA_CLOUD_ACCESS_KEY_ID",
        "ZSTT_CLIENT_ALIBABA_CLOUD_ACCESS_KEY_SECRET",
        "ZSTT_CLIENT_ALIBABA_CLOUD_REGION",
    },
    "dms": {
        "ZSTT_DMS_ALIBABA_CLOUD_ACCESS_KEY_ID",
        "ZSTT_DMS_ALIBABA_CLOUD_ACCESS_KEY_SECRET",
        "ZSTT_DMS_ALIBABA_CLOUD_SECURITY_TOKEN",
    },
    "es": {
        "ZSTT_ES_HOST",
        "ZSTT_ES_PORT",
        "ZSTT_ES_URL",
        "ZSTT_ES_USERNAME",
        "ZSTT_ES_PASSWORD",
        "ZSTT_ES_INDEX_PREFIX",
    },
    "repo-mcp": {
        "ZSTT_REPO_MCP_URL",
    },
}
SCOPE_EXPORT_KEYS = {
    "dms": {
        "ZSTT_DMS_ALIBABA_CLOUD_ACCESS_KEY_ID": "ALIBABA_CLOUD_ACCESS_KEY_ID",
        "ZSTT_DMS_ALIBABA_CLOUD_ACCESS_KEY_SECRET": "ALIBABA_CLOUD_ACCESS_KEY_SECRET",
        "ZSTT_DMS_ALIBABA_CLOUD_SECURITY_TOKEN": "ALIBABA_CLOUD_SECURITY_TOKEN",
    },
    "observability-client": {
        "ZSTT_CLIENT_ALIBABA_CLOUD_ACCESS_KEY_ID": "ALIBABA_CLOUD_ACCESS_KEY_ID",
        "ZSTT_CLIENT_ALIBABA_CLOUD_ACCESS_KEY_SECRET": "ALIBABA_CLOUD_ACCESS_KEY_SECRET",
        "ZSTT_CLIENT_ALIBABA_CLOUD_REGION": "ALIBABA_CLOUD_REGION",
    },
}
MANAGED_KEYS = set().union(
    *SCOPE_KEYS.values(),
    *(mapping.values() for mapping in SCOPE_EXPORT_KEYS.values()),
)
REQUIRED_KEYS = {
    "observability": {
        "ALIBABA_CLOUD_ACCESS_KEY_ID",
        "ALIBABA_CLOUD_ACCESS_KEY_SECRET",
    },
    "observability-client": {
        "ZSTT_CLIENT_ALIBABA_CLOUD_ACCESS_KEY_ID",
        "ZSTT_CLIENT_ALIBABA_CLOUD_ACCESS_KEY_SECRET",
    },
    "dms": {
        "ZSTT_DMS_ALIBABA_CLOUD_ACCESS_KEY_ID",
        "ZSTT_DMS_ALIBABA_CLOUD_ACCESS_KEY_SECRET",
    },
    "es": set(),
    "repo-mcp": {"ZSTT_REPO_MCP_URL"},
}
REQUIRED_CONNECTION_KEYS = {
    "es": {"ZSTT_ES_HOST", "ZSTT_ES_URL"},
}


class EnvironmentConfigError(RuntimeError):
    pass


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def _read_environment_file(path: Path) -> dict[str, str]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise EnvironmentConfigError(f"Cannot read ZSTT environment file: {path}") from exc

    values: dict[str, str] = {}
    for line_number, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        key = key.strip()
        if not separator or not KEY_PATTERN.fullmatch(key):
            raise EnvironmentConfigError(
                f"Invalid ZSTT environment entry at {path}:{line_number}"
            )
        if key in values:
            raise EnvironmentConfigError(
                f"Duplicate ZSTT environment key at {path}:{line_number}: {key}"
            )
        values[key] = _unquote(value.strip())
    return values


def _build_child_environment(environment: str, scope: str, env_file: Path) -> dict[str, str]:
    values = _read_environment_file(env_file)
    if values.get("ZSTT_ENV") != environment:
        declared = values.get("ZSTT_ENV", "unset")
        raise EnvironmentConfigError(
            f"Environment mismatch: requested {environment}, file declares {declared}"
        )

    missing = sorted(key for key in REQUIRED_KEYS[scope] if not values.get(key))
    if missing:
        raise EnvironmentConfigError(
            f"Required {scope} settings are not configured: {', '.join(missing)}"
        )
    connection_keys = REQUIRED_CONNECTION_KEYS.get(scope)
    if connection_keys and not any(values.get(key) for key in connection_keys):
        raise EnvironmentConfigError(
            f"Required {scope} connection is not configured; set one of: "
            + ", ".join(sorted(connection_keys))
        )

    child_env = os.environ.copy()
    child_env.pop("ZSTT_ENV", None)
    for key in MANAGED_KEYS:
        child_env.pop(key, None)
    child_env["ZSTT_ENV"] = environment
    export_keys = SCOPE_EXPORT_KEYS.get(scope, {})
    child_env.update(
        {
            export_keys.get(key, key): value
            for key, value in values.items()
            if key in SCOPE_KEYS[scope] and value
        }
    )
    return child_env


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) < 4 or args[2] != "--":
        print(
            "Usage: with_env.py <test|prod> "
            "<observability|observability-client|dms|es|repo-mcp> -- "
            "<command> [args...]",
            file=sys.stderr,
        )
        return 2

    environment, scope = args[:2]
    command = args[3:]
    if environment not in {"test", "prod"}:
        print(f"Unsupported ZSTT environment: {environment}", file=sys.stderr)
        return 2
    if scope not in SCOPE_KEYS:
        print(f"Unsupported ZSTT environment scope: {scope}", file=sys.stderr)
        return 2
    env_name = ".env.local" if environment == "test" else ".env.prod.local"
    env_file = Path(__file__).resolve().parent.parent / ".env" / env_name
    if not env_file.is_file():
        print(f"ZSTT {environment} environment file not found: {env_file}", file=sys.stderr)
        return 1

    try:
        child_env = _build_child_environment(environment, scope, env_file)
        return subprocess.run(command, env=child_env, check=False).returncode
    except EnvironmentConfigError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"Cannot start scoped command: {exc}", file=sys.stderr)
        return 127


if __name__ == "__main__":
    raise SystemExit(main())
