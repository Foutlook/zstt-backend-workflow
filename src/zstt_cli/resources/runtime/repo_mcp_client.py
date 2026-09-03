from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


MCP_PROTOCOL_VERSION = "2025-03-26"
REPOSITORY_TOOL = "codegraph_explore"
MAX_QUERY_LENGTH = 12_000
MAX_FILES_LIMIT = 20


class RepositoryMcpClientError(RuntimeError):
    pass


def _redact_text(value: str) -> str:
    endpoint = os.environ.get("ZSTT_REPO_MCP_URL", "")
    return value.replace(endpoint, "***") if endpoint else value


def _validate_endpoint(value: str) -> str:
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise RepositoryMcpClientError(
            "ZSTT_REPO_MCP_URL must be an absolute HTTP or HTTPS URL"
        )
    if parsed.username or parsed.password:
        raise RepositoryMcpClientError(
            "ZSTT_REPO_MCP_URL must not contain embedded credentials"
        )
    if parsed.fragment:
        raise RepositoryMcpClientError("ZSTT_REPO_MCP_URL must not contain a fragment")
    return value


def _sse_messages(body: str) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    data_lines: list[str] = []
    for line in [*body.splitlines(), ""]:
        if not line:
            if data_lines:
                payload = "\n".join(data_lines)
                data_lines.clear()
                try:
                    message = json.loads(payload)
                except json.JSONDecodeError as exc:
                    raise RepositoryMcpClientError("Repository MCP returned invalid SSE JSON") from exc
                if isinstance(message, dict):
                    messages.append(message)
            continue
        if line.startswith("data:"):
            data_lines.append(line[5:].lstrip())
    return messages


def _response_messages(content_type: str, body: bytes) -> list[dict[str, Any]]:
    if not body:
        return []
    text = body.decode("utf-8")
    if "text/event-stream" in content_type:
        return _sse_messages(text)
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RepositoryMcpClientError("Repository MCP returned invalid JSON") from exc
    if isinstance(payload, dict):
        return [payload]
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    raise RepositoryMcpClientError("Repository MCP returned an unexpected response")


class StreamableHttpMcpClient:
    def __init__(self, endpoint: str, timeout: float = 90.0) -> None:
        self.endpoint = _validate_endpoint(endpoint)
        self.timeout = timeout
        self.request_id = 0
        self.session_id: str | None = None
        self.protocol_version = MCP_PROTOCOL_VERSION

    def __enter__(self) -> StreamableHttpMcpClient:
        result = self.request(
            "initialize",
            {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "zstt-repository-readonly-client", "version": "1.0"},
            },
            include_protocol_header=False,
        )
        negotiated = result.get("protocolVersion")
        if isinstance(negotiated, str) and negotiated:
            self.protocol_version = negotiated
        self.notify("notifications/initialized", {})
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        return None

    def _post(
        self,
        payload: dict[str, Any],
        include_protocol_header: bool = True,
    ) -> list[dict[str, Any]]:
        headers = {
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
        }
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        if include_protocol_header:
            headers["MCP-Protocol-Version"] = self.protocol_version
        request = urllib.request.Request(
            self.endpoint,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                session_id = response.headers.get("Mcp-Session-Id")
                if session_id:
                    self.session_id = session_id
                return _response_messages(
                    response.headers.get("Content-Type", "application/json"),
                    response.read(),
                )
        except urllib.error.HTTPError as exc:
            raise RepositoryMcpClientError(
                f"Repository MCP HTTP request failed with status {exc.code}"
            ) from exc
        except urllib.error.URLError as exc:
            reason = _redact_text(str(exc.reason))
            raise RepositoryMcpClientError(
                f"Repository MCP connection failed: {reason}"
            ) from exc
        except TimeoutError as exc:
            raise RepositoryMcpClientError("Repository MCP request timed out") from exc

    def notify(self, method: str, params: dict[str, Any]) -> None:
        self._post({"jsonrpc": "2.0", "method": method, "params": params})

    def request(
        self,
        method: str,
        params: dict[str, Any],
        include_protocol_header: bool = True,
    ) -> dict[str, Any]:
        self.request_id += 1
        current_id = self.request_id
        messages = self._post(
            {
                "jsonrpc": "2.0",
                "id": current_id,
                "method": method,
                "params": params,
            },
            include_protocol_header=include_protocol_header,
        )
        for message in messages:
            if message.get("id") != current_id:
                continue
            if "error" in message:
                error = message["error"]
                detail = error.get("message", "unknown MCP error") if isinstance(error, dict) else str(error)
                raise RepositoryMcpClientError(_redact_text(detail))
            result = message.get("result")
            if isinstance(result, dict):
                return result
            raise RepositoryMcpClientError(f"Invalid Repository MCP response for {method}")
        raise RepositoryMcpClientError(f"Repository MCP did not respond to {method}")

    def list_tools(self) -> list[dict[str, Any]]:
        result = self.request("tools/list", {})
        tools = result.get("tools")
        if not isinstance(tools, list):
            raise RepositoryMcpClientError("Repository MCP returned an invalid tool list")
        return [tool for tool in tools if isinstance(tool, dict)]

    def call_repository_tool(self, arguments: dict[str, Any]) -> Any:
        result = self.request(
            "tools/call",
            {"name": REPOSITORY_TOOL, "arguments": arguments},
        )
        if result.get("isError"):
            raise RepositoryMcpClientError(
                _redact_text(_content_text(result) or "Repository MCP tool call failed")
            )
        structured = result.get("structuredContent")
        if structured is not None:
            return structured
        text = _content_text(result)
        return text if text is not None else result


def _content_text(result: dict[str, Any]) -> str | None:
    texts = [
        item.get("text", "")
        for item in result.get("content", [])
        if isinstance(item, dict) and item.get("type") == "text"
    ]
    return "\n".join(texts) if texts else None


def _validate_scoped_environment() -> tuple[str, str]:
    environment = os.environ.get("ZSTT_ENV", "")
    if environment not in {"test", "prod"}:
        raise RepositoryMcpClientError(
            "Run this client through runtime/with_env.py <test|prod> repo-mcp"
        )
    endpoint = os.environ.get("ZSTT_REPO_MCP_URL", "")
    if not endpoint:
        raise RepositoryMcpClientError(
            "Repository MCP endpoint was not injected by runtime/with_env.py"
        )
    return environment, _validate_endpoint(endpoint)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ZSTT read-only remote repository MCP client")
    parser.add_argument("--timeout", type=float, default=90.0)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("probe")
    explore = subparsers.add_parser("explore")
    explore.add_argument("--query", required=True)
    source = explore.add_mutually_exclusive_group()
    source.add_argument("--repository")
    source.add_argument("--repositories", nargs="+")
    explore.add_argument("--max-files", type=int)
    explore.add_argument("--project-path")
    return parser


def _explore_arguments(args: argparse.Namespace) -> dict[str, Any]:
    query = args.query.strip()
    if not query:
        raise RepositoryMcpClientError("Repository query must not be empty")
    if len(query) > MAX_QUERY_LENGTH:
        raise RepositoryMcpClientError(
            f"Repository query exceeds {MAX_QUERY_LENGTH} characters"
        )
    if args.max_files is not None and not 1 <= args.max_files <= MAX_FILES_LIMIT:
        raise RepositoryMcpClientError(
            f"--max-files must be between 1 and {MAX_FILES_LIMIT}"
        )
    arguments: dict[str, Any] = {"query": query}
    if args.repository:
        arguments["repository"] = args.repository
    if args.repositories:
        arguments["repositories"] = args.repositories
    if args.max_files is not None:
        arguments["maxFiles"] = args.max_files
    if args.project_path:
        arguments["projectPath"] = args.project_path
    return arguments


def _print_payload(value: Any) -> None:
    if isinstance(value, str):
        print(_redact_text(value))
    else:
        print(json.dumps(value, ensure_ascii=False))


def _configure_utf8_output() -> None:
    # Remote source can contain characters outside the active Windows code page.
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    _configure_utf8_output()
    args = _parser().parse_args(argv)
    try:
        environment, endpoint = _validate_scoped_environment()
        with StreamableHttpMcpClient(endpoint, timeout=args.timeout) as client:
            if args.command == "probe":
                available = any(tool.get("name") == REPOSITORY_TOOL for tool in client.list_tools())
                if not available:
                    raise RepositoryMcpClientError(
                        f"Repository MCP does not expose {REPOSITORY_TOOL}"
                    )
                payload: Any = {
                    "environment": environment,
                    "tool": REPOSITORY_TOOL,
                    "available": True,
                }
            else:
                payload = client.call_repository_tool(_explore_arguments(args))
        _print_payload(payload)
        return 0
    except RepositoryMcpClientError as exc:
        print(_redact_text(str(exc)), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
