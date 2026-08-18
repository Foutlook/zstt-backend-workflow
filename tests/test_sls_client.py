from __future__ import annotations

import importlib.util
import json
import os
import sys
import unittest
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError


ROOT = Path(__file__).resolve().parents[1]
CLIENT_PATH = ROOT / "src" / "zstt_cli" / "resources" / "runtime" / "sls_client.py"
SPEC = importlib.util.spec_from_file_location("zstt_sls_client", CLIENT_PATH)
assert SPEC is not None and SPEC.loader is not None
sls_client = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = sls_client
SPEC.loader.exec_module(sls_client)


class FakeResponse:
    def __init__(self, payload: object, headers: dict[str, str] | None = None) -> None:
        self.payload = json.dumps(payload).encode("utf-8")
        self.headers = headers or {}

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None

    def read(self) -> bytes:
        return self.payload


class SlsClientTest(unittest.TestCase):
    def setUp(self) -> None:
        self.query = sls_client.SlsQuery(
            region="cn-hangzhou",
            project="example-project",
            logstore="prod-app-log",
            from_time=1776477540,
            to_time=1776477600,
            query="traceId: abc | select *",
            line=20,
        )

    def test_signature_is_stable_for_known_request(self) -> None:
        _, resource, params = self.query.request_parts()
        headers = {
            "Date": "Tue, 18 Aug 2026 02:00:00 GMT",
            "x-log-apiversion": "0.6.0",
            "x-log-signaturemethod": "hmac-sha1",
        }

        authorization = sls_client._authorization(
            "test-id",
            "test-secret",
            "GET",
            resource,
            params,
            headers,
        )

        self.assertEqual("LOG test-id:mWmyFVUI3QLDaZ3mBuzlsTGkj4U=", authorization)

    def test_query_uses_scoped_credentials_and_returns_bounded_result(self) -> None:
        captured: dict[str, object] = {}

        def open_request(request: object, timeout: float) -> FakeResponse:
            captured["request"] = request
            captured["timeout"] = timeout
            return FakeResponse(
                [{"traceId": "abc", "message": "failed"}],
                {
                    "x-log-count": "1",
                    "x-log-progress": "Complete",
                    "x-log-requestid": "request-1",
                },
            )

        with patch.dict(
            os.environ,
            {
                "ALIBABA_CLOUD_ACCESS_KEY_ID": "test-id",
                "ALIBABA_CLOUD_ACCESS_KEY_SECRET": "test-secret",
            },
            clear=True,
        ):
            result = sls_client.query_logs(
                self.query,
                request_open=open_request,
                now=datetime(2026, 8, 18, 2, 0, tzinfo=timezone.utc),
                timeout=12.0,
            )

        request = captured["request"]
        self.assertEqual("GET", request.get_method())
        self.assertEqual(12.0, captured["timeout"])
        self.assertTrue(
            request.full_url.startswith(
                "https://example-project.cn-hangzhou.log.aliyuncs.com/logstores/prod-app-log?"
            )
        )
        self.assertIn("query=traceId%3A+abc+%7C+select+%2A", request.full_url)
        self.assertEqual(
            "LOG test-id:mWmyFVUI3QLDaZ3mBuzlsTGkj4U=",
            request.get_header("Authorization"),
        )
        self.assertEqual(1, result["count"])
        self.assertEqual("Complete", result["progress"])
        self.assertEqual("request-1", result["requestId"])
        self.assertEqual("abc", result["logs"][0]["traceId"])

    def test_query_rejects_unbounded_or_unsafe_targets(self) -> None:
        invalid_queries = (
            sls_client.SlsQuery(
                "cn-hangzhou.example.com",
                "project",
                "logstore",
                1,
                2,
                "*",
            ),
            sls_client.SlsQuery(
                "cn-hangzhou",
                "project",
                "logstore",
                1,
                1 + sls_client.MAX_QUERY_SECONDS + 1,
                "*",
            ),
            sls_client.SlsQuery(
                "cn-hangzhou",
                "project",
                "logstore",
                1,
                2,
                "*",
                line=sls_client.MAX_LINE_COUNT + 1,
            ),
        )

        for query in invalid_queries:
            with self.subTest(query=query), self.assertRaises(sls_client.SlsClientError):
                query.validate()

    def test_http_error_redacts_injected_credentials(self) -> None:
        def fail_request(request: object, timeout: float) -> FakeResponse:
            raise HTTPError(
                request.full_url,
                403,
                "Forbidden",
                {},
                BytesIO(b'{"message":"secret-id / secret-key"}'),
            )

        with patch.dict(
            os.environ,
            {
                "ALIBABA_CLOUD_ACCESS_KEY_ID": "secret-id",
                "ALIBABA_CLOUD_ACCESS_KEY_SECRET": "secret-key",
            },
            clear=True,
        ):
            with self.assertRaises(sls_client.SlsClientError) as context:
                sls_client.query_logs(self.query, request_open=fail_request)

        self.assertNotIn("secret-id", str(context.exception))
        self.assertNotIn("secret-key", str(context.exception))
        self.assertIn("***", str(context.exception))


if __name__ == "__main__":
    unittest.main()
