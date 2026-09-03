from __future__ import annotations

import importlib.util
import json
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLIENT_PATH = ROOT / "src" / "zstt_cli" / "resources" / "runtime" / "repo_mcp_client.py"
SPEC = importlib.util.spec_from_file_location("zstt_repo_mcp_client", CLIENT_PATH)
assert SPEC is not None and SPEC.loader is not None
REPO_MCP = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = REPO_MCP
SPEC.loader.exec_module(REPO_MCP)


class _McpHandler(BaseHTTPRequestHandler):
    requests: list[dict] = []

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length).decode("utf-8"))
        self.__class__.requests.append(
            {
                "payload": payload,
                "session": self.headers.get("Mcp-Session-Id"),
                "protocol": self.headers.get("MCP-Protocol-Version"),
            }
        )
        method = payload.get("method")
        if method == "notifications/initialized":
            self.send_response(202)
            self.end_headers()
            return
        if method == "initialize":
            result = {
                "protocolVersion": REPO_MCP.MCP_PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "test", "version": "1"},
            }
        elif method == "tools/list":
            result = {"tools": [{"name": REPO_MCP.REPOSITORY_TOOL}]}
        elif method == "tools/call":
            result = {
                "content": [{"type": "text", "text": "remote source result"}],
                "isError": False,
            }
        else:
            self.send_error(400)
            return
        body = json.dumps(
            {"jsonrpc": "2.0", "id": payload["id"], "result": result}
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Mcp-Session-Id", "test-session")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:
        return None


class RepositoryMcpClientTest(unittest.TestCase):
    def setUp(self) -> None:
        _McpHandler.requests = []
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), _McpHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.endpoint = f"http://127.0.0.1:{self.server.server_port}/mcp"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def test_streamable_http_session_and_read_only_tool_call(self) -> None:
        with REPO_MCP.StreamableHttpMcpClient(self.endpoint, timeout=2) as client:
            self.assertEqual(
                [tool["name"] for tool in client.list_tools()],
                [REPO_MCP.REPOSITORY_TOOL],
            )
            result = client.call_repository_tool(
                {"repository": "sample-repo", "query": "SampleService", "maxFiles": 2}
            )

        self.assertEqual(result, "remote source result")
        methods = [item["payload"]["method"] for item in _McpHandler.requests]
        self.assertEqual(
            methods,
            ["initialize", "notifications/initialized", "tools/list", "tools/call"],
        )
        for request in _McpHandler.requests[1:]:
            self.assertEqual(request["session"], "test-session")
            self.assertEqual(request["protocol"], REPO_MCP.MCP_PROTOCOL_VERSION)

    def test_endpoint_rejects_embedded_credentials(self) -> None:
        with self.assertRaises(REPO_MCP.RepositoryMcpClientError):
            REPO_MCP._validate_endpoint("https://user:secret@example.test/mcp")

    def test_explore_arguments_enforce_read_bounds(self) -> None:
        args = REPO_MCP._parser().parse_args(
            [
                "explore",
                "--repository",
                "sample-repo",
                "--query",
                "SampleService",
                "--max-files",
                "2",
            ]
        )
        self.assertEqual(
            {
                "repository": "sample-repo",
                "query": "SampleService",
                "maxFiles": 2,
            },
            REPO_MCP._explore_arguments(args),
        )

        invalid = REPO_MCP._parser().parse_args(
            ["explore", "--query", "SampleService", "--max-files", "21"]
        )
        with self.assertRaises(REPO_MCP.RepositoryMcpClientError):
            REPO_MCP._explore_arguments(invalid)


if __name__ == "__main__":
    unittest.main()
