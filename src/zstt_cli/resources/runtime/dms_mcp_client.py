from __future__ import annotations

import argparse
import json
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from typing import Any


DMS_MCP_PACKAGE = "alibabacloud-dms-mcp-server@0.1.23"
MCP_PROTOCOL_VERSION = "2024-11-05"
EXPECTED_ENV_TYPES = {
    "test": {"test"},
    "prod": {"product", "prod", "production"},
}
FORBIDDEN_SQL_TOKENS = {
    "ALTER",
    "ANALYZE",
    "APPROVE",
    "CALL",
    "CREATE",
    "DELETE",
    "DO",
    "DROP",
    "GRANT",
    "HANDLER",
    "INSERT",
    "LOAD",
    "LOCK",
    "MERGE",
    "OPTIMIZE",
    "RENAME",
    "REPAIR",
    "REPLACE",
    "REVOKE",
    "SET",
    "SUBMIT",
    "TRUNCATE",
    "UNLOCK",
    "UPDATE",
    "USE",
}
FORBIDDEN_SQL_FUNCTIONS = {"BENCHMARK", "GET_LOCK", "LOAD_FILE", "RELEASE_LOCK", "SLEEP"}
ALLOWED_FIRST_SQL_TOKENS = {"DESC", "DESCRIBE", "EXPLAIN", "SELECT", "SHOW", "WITH"}
SENSITIVE_OUTPUT_KEYS = {
    "accesskeyid",
    "accesskeysecret",
    "alibabacloudsecuritytoken",
    "connectionstring",
    "host",
    "hostname",
    "password",
    "port",
    "securitytoken",
}


class DmsClientError(RuntimeError):
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


def _safe_payload(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "***" if re.sub(r"[^a-z0-9]", "", key.lower()) in SENSITIVE_OUTPUT_KEYS else _safe_payload(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_safe_payload(item) for item in value]
    if isinstance(value, str):
        return _redact_text(value)
    return value


def _strip_sql_literals_and_comments(sql: str) -> str:
    result: list[str] = []
    index = 0
    state = "normal"
    while index < len(sql):
        char = sql[index]
        next_char = sql[index + 1] if index + 1 < len(sql) else ""
        if state == "normal":
            if char == "'":
                state = "single"
                result.append(" ")
            elif char == '"':
                state = "double"
                result.append(" ")
            elif char == "`":
                state = "backtick"
                result.append(" ")
            elif char == "-" and next_char == "-":
                state = "line_comment"
                result.extend((" ", " "))
                index += 1
            elif char == "#":
                state = "line_comment"
                result.append(" ")
            elif char == "/" and next_char == "*":
                state = "block_comment"
                result.extend((" ", " "))
                index += 1
            else:
                result.append(char)
        elif state in {"single", "double", "backtick"}:
            quote = {"single": "'", "double": '"', "backtick": "`"}[state]
            result.append(" ")
            if char == "\\" and next_char:
                result.append(" ")
                index += 1
            elif char == quote:
                if next_char == quote:
                    result.append(" ")
                    index += 1
                else:
                    state = "normal"
        elif state == "line_comment":
            result.append("\n" if char in "\r\n" else " ")
            if char in "\r\n":
                state = "normal"
        elif state == "block_comment":
            result.append(" ")
            if char == "*" and next_char == "/":
                result.append(" ")
                index += 1
                state = "normal"
        index += 1
    if state in {"single", "double", "backtick", "block_comment"}:
        raise DmsClientError("SQL contains an unterminated literal or comment")
    return "".join(result)


def validate_read_only_sql(sql: str) -> None:
    if not sql.strip():
        raise DmsClientError("SQL must not be empty")
    normalized = _strip_sql_literals_and_comments(sql)
    statements = [part.strip() for part in normalized.split(";") if part.strip()]
    if len(statements) != 1:
        raise DmsClientError("Only one read-only SQL statement is allowed")
    tokens = re.findall(r"[A-Za-z_][A-Za-z0-9_]*", statements[0].upper())
    if not tokens or tokens[0] not in ALLOWED_FIRST_SQL_TOKENS:
        raise DmsClientError("Only SELECT, SHOW, DESC, DESCRIBE, EXPLAIN, or read-only CTE is allowed")
    forbidden = sorted(set(tokens) & FORBIDDEN_SQL_TOKENS)
    if forbidden:
        raise DmsClientError(f"SQL contains forbidden operation: {', '.join(forbidden)}")
    dangerous_functions = sorted(set(tokens) & FORBIDDEN_SQL_FUNCTIONS)
    if dangerous_functions:
        raise DmsClientError(f"SQL contains forbidden function: {', '.join(dangerous_functions)}")
    token_pairs = set(zip(tokens, tokens[1:]))
    if ("INTO", "OUTFILE") in token_pairs or ("INTO", "DUMPFILE") in token_pairs:
        raise DmsClientError("SQL file output is not allowed")
    if ("FOR", "UPDATE") in token_pairs or ("LOCK", "IN") in token_pairs:
        raise DmsClientError("Locking reads are not allowed")


class JsonRpcStdioClient:
    def __init__(self, command: list[str] | None = None, timeout: float = 90.0) -> None:
        self.command = command or ["uvx", DMS_MCP_PACKAGE]
        self.timeout = timeout
        self.process: subprocess.Popen[str] | None = None
        self.messages: queue.Queue[str | None] = queue.Queue()
        self.request_id = 0
        self.reader_thread: threading.Thread | None = None

    def __enter__(self) -> JsonRpcStdioClient:
        executable = self.command[0]
        if shutil.which(executable) is None:
            raise DmsClientError(f"DMS MCP launcher is not installed: {executable}")
        try:
            self.process = subprocess.Popen(
                self.command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                bufsize=1,
            )
        except OSError as exc:
            raise DmsClientError(f"Cannot start DMS MCP Server: {exc}") from exc
        assert self.process.stdout is not None
        self.reader_thread = threading.Thread(
            target=self._read_stdout,
            args=(self.process.stdout,),
            daemon=True,
        )
        self.reader_thread.start()
        self.request(
            "initialize",
            {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "zstt-dms-readonly-client", "version": "1.0"},
            },
        )
        self.notify("notifications/initialized", {})
        return self

    def _read_stdout(self, stream: Any) -> None:
        try:
            for line in stream:
                self.messages.put(line)
        finally:
            self.messages.put(None)

    def _send(self, message: dict[str, Any]) -> None:
        if self.process is None or self.process.stdin is None:
            raise DmsClientError("DMS MCP Server is not running")
        try:
            self.process.stdin.write(json.dumps(message, ensure_ascii=False) + "\n")
            self.process.stdin.flush()
        except (BrokenPipeError, OSError) as exc:
            raise DmsClientError("DMS MCP Server closed its input stream") from exc

    def notify(self, method: str, params: dict[str, Any]) -> None:
        self._send({"jsonrpc": "2.0", "method": method, "params": params})

    def request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        self.request_id += 1
        current_id = self.request_id
        self._send({"jsonrpc": "2.0", "id": current_id, "method": method, "params": params})
        deadline = time.monotonic() + self.timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise DmsClientError(f"DMS MCP request timed out: {method}")
            try:
                line = self.messages.get(timeout=remaining)
            except queue.Empty as exc:
                raise DmsClientError(f"DMS MCP request timed out: {method}") from exc
            if line is None:
                code = self.process.poll() if self.process else None
                raise DmsClientError(f"DMS MCP Server exited before responding (code={code})")
            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                continue
            if message.get("id") != current_id:
                continue
            if "error" in message:
                error = message["error"]
                detail = error.get("message", "unknown MCP error") if isinstance(error, dict) else str(error)
                raise DmsClientError(_redact_text(detail))
            result = message.get("result")
            if not isinstance(result, dict):
                raise DmsClientError(f"Invalid DMS MCP response for {method}")
            return result

    def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        result = self.request("tools/call", {"name": name, "arguments": arguments})
        if result.get("isError"):
            raise DmsClientError(_redact_text(_content_text(result) or f"DMS tool failed: {name}"))
        structured = result.get("structuredContent")
        if structured is not None:
            if isinstance(structured, dict) and set(structured) == {"result"}:
                return structured["result"]
            return structured
        text = _content_text(result)
        if text is None:
            return result
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        if self.process is None:
            return
        if self.process.stdin is not None:
            try:
                self.process.stdin.close()
            except OSError:
                pass
        try:
            self.process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            self.process.terminate()
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=2)
        if self.process.stdout is not None:
            self.process.stdout.close()
        if self.reader_thread is not None:
            self.reader_thread.join(timeout=2)


def _content_text(result: dict[str, Any]) -> str | None:
    texts = [
        item.get("text", "")
        for item in result.get("content", [])
        if isinstance(item, dict) and item.get("type") == "text"
    ]
    return "\n".join(texts) if texts else None


def _list_value(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        for key in ("result", "items", "databases", "DatabaseList"):
            nested = value.get(key)
            if isinstance(nested, list):
                return [item for item in nested if isinstance(item, dict)]
    raise DmsClientError("DMS MCP returned an unexpected database list")


def _field(value: dict[str, Any], *names: str) -> Any:
    normalized = {key.lower(): item for key, item in value.items()}
    for name in names:
        if name.lower() in normalized:
            return normalized[name.lower()]
    return None


@dataclass(frozen=True)
class DatabaseSelection:
    database_id: str
    schema_name: str
    instance_alias: str
    env_type: str

    def public(self) -> dict[str, str]:
        return {
            "schemaName": self.schema_name,
            "instanceAlias": self.instance_alias,
            "envType": self.env_type,
        }


class DmsGateway:
    def __init__(self, client: JsonRpcStdioClient, environment: str) -> None:
        self.client = client
        self.environment = environment

    def resolve_database(
        self,
        schema_name: str,
        instance_alias: str | None = None,
    ) -> DatabaseSelection:
        databases = _list_value(
            self.client.call_tool(
                "searchDatabase",
                {"search_key": schema_name, "page_number": 1, "page_size": 200},
            )
        )
        exact = [
            item
            for item in databases
            if str(_field(item, "SchemaName") or "").casefold() == schema_name.casefold()
        ]
        matches: list[DatabaseSelection] = []
        seen: list[dict[str, str]] = []
        for database in exact:
            host = str(_field(database, "Host") or "")
            port = str(_field(database, "Port") or "")
            database_id = str(_field(database, "DatabaseId") or "")
            if not host or not port or not database_id:
                continue
            detail = self.client.call_tool("getInstance", {"host": host, "port": port})
            if not isinstance(detail, dict):
                continue
            env_type = str(_field(detail, "EnvType") or "").lower()
            alias = str(_field(detail, "InstanceAlias") or "unknown")
            seen.append({"instanceAlias": alias, "envType": env_type or "unknown"})
            if env_type in EXPECTED_ENV_TYPES[self.environment]:
                matches.append(DatabaseSelection(database_id, schema_name, alias, env_type))
        if instance_alias:
            matches = [
                match
                for match in matches
                if match.instance_alias.casefold() == instance_alias.casefold()
            ]
        if len(matches) == 1:
            return matches[0]
        if not matches:
            alias_hint = f" and instance alias {instance_alias}" if instance_alias else ""
            raise DmsClientError(
                f"No exact {self.environment} DMS database matched schema {schema_name}{alias_hint}; "
                f"visible candidates={json.dumps(seen, ensure_ascii=False)}"
            )
        candidates = [match.public() for match in matches]
        raise DmsClientError(
            f"Multiple {self.environment} DMS databases matched schema {schema_name}: "
            + json.dumps(candidates, ensure_ascii=False)
        )

    def list_tables(
        self,
        schema_name: str,
        search_name: str | None = None,
        instance_alias: str | None = None,
    ) -> tuple[DatabaseSelection, Any]:
        selection = self.resolve_database(schema_name, instance_alias)
        arguments: dict[str, Any] = {
            "database_id": selection.database_id,
            "page_number": 1,
            "page_size": 200,
        }
        if search_name:
            arguments["search_name"] = search_name
        return selection, self.client.call_tool("listTables", arguments)

    def table_detail(
        self,
        schema_name: str,
        table_name: str,
        instance_alias: str | None = None,
    ) -> tuple[DatabaseSelection, Any]:
        selection, tables = self.list_tables(schema_name, table_name, instance_alias)
        table_guid = _find_table_guid(tables, table_name)
        if not table_guid:
            raise DmsClientError(f"DMS table was not found: {schema_name}.{table_name}")
        return selection, self.client.call_tool("getTableDetailInfo", {"table_guid": table_guid})

    def execute_query(
        self,
        schema_name: str,
        sql: str,
        instance_alias: str | None = None,
    ) -> tuple[DatabaseSelection, Any]:
        validate_read_only_sql(sql)
        selection = self.resolve_database(schema_name, instance_alias)
        result = self.client.call_tool(
            "executeScript",
            {"database_id": selection.database_id, "script": sql, "logic": False},
        )
        return selection, result


def _find_table_guid(value: Any, table_name: str) -> str | None:
    if isinstance(value, dict):
        current_name = _field(value, "TableName", "Name")
        current_guid = _field(value, "TableGuid", "TableGUID", "Guid")
        if current_name is not None and str(current_name).casefold() == table_name.casefold() and current_guid:
            return str(current_guid)
        for item in value.values():
            if found := _find_table_guid(item, table_name):
                return found
    elif isinstance(value, list):
        for item in value:
            if found := _find_table_guid(item, table_name):
                return found
    return None


def _validate_scoped_environment() -> str:
    environment = os.environ.get("ZSTT_ENV", "")
    if environment not in EXPECTED_ENV_TYPES:
        raise DmsClientError(
            "Run this client through runtime/with_env.py <test|prod> dms; ZSTT_ENV is missing or invalid"
        )
    missing = [
        key
        for key in ("ALIBABA_CLOUD_ACCESS_KEY_ID", "ALIBABA_CLOUD_ACCESS_KEY_SECRET")
        if not os.environ.get(key)
    ]
    if missing:
        raise DmsClientError("DMS MCP credentials were not injected by runtime/with_env.py")
    return environment


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ZSTT read-only Alibaba Cloud DMS MCP client")
    parser.add_argument("--timeout", type=float, default=90.0)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("resolve", "tables", "table", "query"):
        command = subparsers.add_parser(name)
        command.add_argument("--schema", required=True)
        command.add_argument("--instance-alias")
    subparsers.choices["tables"].add_argument("--search")
    subparsers.choices["table"].add_argument("--table", required=True)
    subparsers.choices["query"].add_argument("--sql", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        environment = _validate_scoped_environment()
        if args.command == "query":
            validate_read_only_sql(args.sql)
        with JsonRpcStdioClient(timeout=args.timeout) as client:
            gateway = DmsGateway(client, environment)
            if args.command == "resolve":
                selection = gateway.resolve_database(args.schema, args.instance_alias)
                payload: Any = {"environment": environment, "database": selection.public()}
            elif args.command == "tables":
                selection, result = gateway.list_tables(args.schema, args.search, args.instance_alias)
                payload = {"environment": environment, "database": selection.public(), "result": result}
            elif args.command == "table":
                selection, result = gateway.table_detail(args.schema, args.table, args.instance_alias)
                payload = {"environment": environment, "database": selection.public(), "result": result}
            else:
                selection, result = gateway.execute_query(args.schema, args.sql, args.instance_alias)
                payload = {"environment": environment, "database": selection.public(), "result": result}
        print(json.dumps(_safe_payload(payload), ensure_ascii=False))
        return 0
    except DmsClientError as exc:
        print(_redact_text(str(exc)), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
