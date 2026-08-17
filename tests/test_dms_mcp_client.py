from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CLIENT_PATH = ROOT / "src" / "zstt_cli" / "resources" / "runtime" / "dms_mcp_client.py"
SPEC = importlib.util.spec_from_file_location("zstt_dms_mcp_client", CLIENT_PATH)
assert SPEC is not None and SPEC.loader is not None
DMS = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = DMS
SPEC.loader.exec_module(DMS)


class FakeToolClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        self.calls.append((name, arguments))
        if name == "searchDatabase":
            return [
                {
                    "DatabaseId": "test-db",
                    "Host": "test.internal",
                    "Port": "3306",
                    "SchemaName": "sample_app",
                },
                {
                    "DatabaseId": "prod-db",
                    "Host": "prod.internal",
                    "Port": "3306",
                    "SchemaName": "sample_app",
                },
                {
                    "DatabaseId": "prod-pre-db",
                    "Host": "prod-pre.internal",
                    "Port": "3306",
                    "SchemaName": "sample_app",
                },
                {
                    "DatabaseId": "other-db",
                    "Host": "other.internal",
                    "Port": "3306",
                    "SchemaName": "other",
                },
            ]
        if name == "getInstance":
            if arguments["host"] == "test.internal":
                return {"EnvType": "test", "InstanceAlias": "sample-test-primary"}
            if arguments["host"] == "prod.internal":
                return {"EnvType": "product", "InstanceAlias": "sample-prod-primary"}
            return {"EnvType": "product", "InstanceAlias": "sample-prod-secondary"}
        if name == "executeScript":
            return {"Success": True, "Rows": [{"answer": 1}]}
        raise AssertionError(name)


class DmsMcpClientTest(unittest.TestCase):
    def test_read_only_sql_validation_accepts_queries(self) -> None:
        for sql in (
            "SELECT id FROM answer_record ORDER BY id DESC LIMIT 30",
            "WITH recent AS (SELECT id FROM answer_record LIMIT 30) SELECT * FROM recent",
            "SHOW COLUMNS FROM answer_record",
            "EXPLAIN SELECT id FROM answer_record LIMIT 1",
        ):
            DMS.validate_read_only_sql(sql)

    def test_read_only_sql_validation_rejects_writes_and_bypasses(self) -> None:
        for sql in (
            "UPDATE answer_record SET status = 1",
            "WITH changed AS (DELETE FROM answer_record RETURNING id) SELECT * FROM changed",
            "SELECT 1; DELETE FROM answer_record",
            "SELECT SLEEP(10)",
            "SELECT * FROM answer_record FOR UPDATE",
            "SELECT * FROM answer_record INTO OUTFILE '/tmp/data'",
        ):
            with self.subTest(sql=sql):
                with self.assertRaises(DMS.DmsClientError):
                    DMS.validate_read_only_sql(sql)

    def test_gateway_selects_environment_before_querying(self) -> None:
        test_client = FakeToolClient()
        test_selection, test_result = DMS.DmsGateway(test_client, "test").execute_query(
            "sample_app", "SELECT 1 AS answer LIMIT 1"
        )
        self.assertEqual("test-db", test_selection.database_id)
        self.assertEqual("test", test_selection.env_type)
        self.assertEqual(True, test_result["Success"])
        self.assertEqual("test-db", test_client.calls[-1][1]["database_id"])

        prod_client = FakeToolClient()
        prod_selection, _ = DMS.DmsGateway(prod_client, "prod").execute_query(
            "sample_app",
            "SELECT 1 AS answer LIMIT 1",
            "sample-prod-primary",
        )
        self.assertEqual("prod-db", prod_selection.database_id)
        self.assertEqual("product", prod_selection.env_type)
        self.assertEqual("prod-db", prod_client.calls[-1][1]["database_id"])

    def test_gateway_requires_alias_when_environment_has_multiple_matches(self) -> None:
        client = FakeToolClient()
        with self.assertRaisesRegex(DMS.DmsClientError, "Multiple prod DMS databases"):
            DMS.DmsGateway(client, "prod").resolve_database("sample_app")

    def test_gateway_rejects_write_before_starting_database_discovery(self) -> None:
        client = FakeToolClient()
        with self.assertRaises(DMS.DmsClientError):
            DMS.DmsGateway(client, "prod").execute_query(
                "sample_app", "DELETE FROM answer_record"
            )
        self.assertEqual([], client.calls)

    def test_stdio_client_initializes_and_decodes_tool_result(self) -> None:
        server_code = """
import json
import sys

for line in sys.stdin:
    message = json.loads(line)
    if "id" not in message:
        continue
    if message["method"] == "initialize":
        result = {"protocolVersion": "2024-11-05", "capabilities": {}, "serverInfo": {"name": "fake", "version": "1"}}
    else:
        result = {"content": [{"type": "text", "text": json.dumps({"ok": True})}], "isError": False}
    print(json.dumps({"jsonrpc": "2.0", "id": message["id"], "result": result}), flush=True)
"""
        with tempfile.TemporaryDirectory() as tmp:
            server = Path(tmp) / "fake_mcp_server.py"
            server.write_text(server_code, encoding="utf-8")
            with DMS.JsonRpcStdioClient([sys.executable, str(server)], timeout=5) as client:
                self.assertEqual({"ok": True}, client.call_tool("readOnlyTool", {}))


if __name__ == "__main__":
    unittest.main()
