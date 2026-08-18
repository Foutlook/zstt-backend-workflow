from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import format_datetime
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


API_VERSION = "0.6.0"
SIGNATURE_METHOD = "hmac-sha1"
MAX_QUERY_SECONDS = 7 * 24 * 60 * 60
MAX_LINE_COUNT = 100
NAME_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,127}$")


class SlsClientError(RuntimeError):
    pass


def _redaction_values() -> tuple[str, ...]:
    return tuple(
        value
        for key in (
            "ALIBABA_CLOUD_ACCESS_KEY_ID",
            "ALIBABA_CLOUD_ACCESS_KEY_SECRET",
            "ALIBABA_CLOUD_SECURITY_TOKEN",
        )
        if (value := os.environ.get(key))
    )


def _redact_text(value: str) -> str:
    redacted = value
    for secret in _redaction_values():
        redacted = redacted.replace(secret, "***")
    return redacted


def _validate_name(label: str, value: str) -> None:
    if not NAME_PATTERN.fullmatch(value):
        raise SlsClientError(f"Invalid SLS {label}: {value!r}")


@dataclass(frozen=True)
class SlsQuery:
    region: str
    project: str
    logstore: str
    from_time: int
    to_time: int
    query: str
    line: int = MAX_LINE_COUNT
    offset: int = 0
    reverse: bool = False

    def validate(self) -> None:
        _validate_name("region", self.region)
        _validate_name("project", self.project)
        _validate_name("logstore", self.logstore)
        if self.from_time < 0 or self.to_time <= self.from_time:
            raise SlsClientError("SLS time range must satisfy 0 <= from_time < to_time")
        if self.to_time - self.from_time > MAX_QUERY_SECONDS:
            raise SlsClientError("SLS time range must not exceed 7 days")
        if not self.query.strip():
            raise SlsClientError("SLS query must not be empty")
        if not 1 <= self.line <= MAX_LINE_COUNT:
            raise SlsClientError(f"SLS line must be between 1 and {MAX_LINE_COUNT}")
        if self.offset < 0:
            raise SlsClientError("SLS offset must be non-negative")

    def request_parts(self) -> tuple[str, str, dict[str, str]]:
        self.validate()
        resource = f"/logstores/{quote(self.logstore, safe='')}"
        params = {
            "type": "log",
            "from": str(self.from_time),
            "to": str(self.to_time),
            "query": self.query,
            "line": str(self.line),
            "offset": str(self.offset),
            "reverse": "true" if self.reverse else "false",
        }
        endpoint = f"https://{self.project}.{self.region}.log.aliyuncs.com"
        return endpoint, resource, params


def _canonicalized_headers(headers: dict[str, str]) -> str:
    return "".join(
        f"{key.lower()}:{headers[key].strip()}\n"
        for key in sorted(headers, key=str.lower)
        if key.lower().startswith(("x-log-", "x-acs-"))
    )


def _canonicalized_resource(resource: str, params: dict[str, str]) -> str:
    return f"{resource}?{urlencode(sorted(params.items()))}"


def _authorization(
    access_key_id: str,
    access_key_secret: str,
    method: str,
    resource: str,
    params: dict[str, str],
    headers: dict[str, str],
) -> str:
    sign_text = "\n".join(
        (
            method,
            headers.get("Content-MD5", ""),
            headers.get("Content-Type", ""),
            headers["Date"],
            _canonicalized_headers(headers) + _canonicalized_resource(resource, params),
        )
    )
    signature = base64.b64encode(
        hmac.new(
            access_key_secret.encode("utf-8"),
            sign_text.encode("utf-8"),
            hashlib.sha1,
        ).digest()
    ).decode("ascii")
    return f"LOG {access_key_id}:{signature}"


def _credentials() -> tuple[str, str, str | None]:
    access_key_id = os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_ID", "")
    access_key_secret = os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_SECRET", "")
    security_token = os.environ.get("ALIBABA_CLOUD_SECURITY_TOKEN")
    if not access_key_id or not access_key_secret:
        raise SlsClientError(
            "SLS credentials are not configured; run this client through with_env.py"
        )
    return access_key_id, access_key_secret, security_token


def query_logs(
    query: SlsQuery,
    *,
    request_open: Callable[..., Any] = urlopen,
    now: datetime | None = None,
    timeout: float = 30.0,
) -> dict[str, Any]:
    endpoint, resource, params = query.request_parts()
    access_key_id, access_key_secret, security_token = _credentials()
    current_time = now or datetime.now(timezone.utc)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)
    headers = {
        "Date": format_datetime(current_time.astimezone(timezone.utc), usegmt=True),
        "x-log-apiversion": API_VERSION,
        "x-log-signaturemethod": SIGNATURE_METHOD,
    }
    if security_token:
        headers["x-acs-security-token"] = security_token
    headers["Authorization"] = _authorization(
        access_key_id,
        access_key_secret,
        "GET",
        resource,
        params,
        headers,
    )
    request = Request(
        f"{endpoint}{resource}?{urlencode(params)}",
        headers=headers,
        method="GET",
    )
    try:
        with request_open(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
            payload = json.loads(body)
            if not isinstance(payload, list):
                raise SlsClientError("SLS returned an unexpected response payload")
            return {
                "count": int(response.headers.get("x-log-count", len(payload))),
                "progress": response.headers.get("x-log-progress", "Unknown"),
                "requestId": response.headers.get("x-log-requestid", ""),
                "logs": payload,
            }
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SlsClientError(
            _redact_text(f"SLS request failed with HTTP {exc.code}: {detail}")
        ) from exc
    except URLError as exc:
        raise SlsClientError(_redact_text(f"SLS request failed: {exc.reason}")) from exc
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise SlsClientError(f"SLS returned an invalid response: {exc}") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Query Alibaba Cloud SLS logs read-only")
    parser.add_argument("--region", required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--logstore", required=True)
    parser.add_argument("--from-time", required=True, type=int)
    parser.add_argument("--to-time", required=True, type=int)
    parser.add_argument("--query", required=True)
    parser.add_argument("--line", type=int, default=MAX_LINE_COUNT)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--reverse", action="store_true")
    parser.add_argument("--timeout", type=float, default=30.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = query_logs(
            SlsQuery(
                region=args.region,
                project=args.project,
                logstore=args.logstore,
                from_time=args.from_time,
                to_time=args.to_time,
                query=args.query,
                line=args.line,
                offset=args.offset,
                reverse=args.reverse,
            ),
            timeout=args.timeout,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except SlsClientError as exc:
        print(_redact_text(str(exc)), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
