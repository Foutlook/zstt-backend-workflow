from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path


IMPLEMENTATION_EVIDENCE_SCHEMA_VERSION = 1
IMPLEMENTATION_EVIDENCE_PATH = Path("auxiliary/implementation-evidence.json")
AUTO_EVIDENCE_START = "<!-- ZSTT_AUTO_IMPLEMENTATION_EVIDENCE_START -->"
AUTO_EVIDENCE_END = "<!-- ZSTT_AUTO_IMPLEMENTATION_EVIDENCE_END -->"
SENSITIVE_ARGUMENT = re.compile(
    r"(?:password|passwd|secret|token|authorization|cookie|access[_-]?key)",
    flags=re.IGNORECASE,
)
SENSITIVE_HEADER = re.compile(
    r"^\s*(?:authorization|cookie)\s*:",
    flags=re.IGNORECASE,
)


def project_root_for_feature(feature_dir: Path) -> Path:
    resolved = feature_dir.resolve()
    for parent in resolved.parents:
        if parent.name == ".zstt":
            return parent.parent
    raise ValueError(f"需求目录不在 .zstt 下: {resolved}")


def evidence_path(feature_dir: Path) -> Path:
    return feature_dir / IMPLEMENTATION_EVIDENCE_PATH


def load_evidence(feature_dir: Path) -> dict[str, object]:
    path = evidence_path(feature_dir)
    if not path.is_file():
        return {
            "schemaVersion": IMPLEMENTATION_EVIDENCE_SCHEMA_VERSION,
            "artifact": IMPLEMENTATION_EVIDENCE_PATH.as_posix(),
            "baseline": None,
            "validations": [],
            "final": None,
            "changeSummary": None,
            "validationSummary": None,
        }
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"无法读取实现证据: {path}") from exc
    if (
        not isinstance(payload, dict)
        or payload.get("schemaVersion") != IMPLEMENTATION_EVIDENCE_SCHEMA_VERSION
    ):
        raise ValueError(f"不支持的实现证据版本: {path}")
    validations = payload.get("validations")
    if not isinstance(validations, list):
        raise ValueError(f"实现证据 validations 必须是数组: {path}")
    return payload


def write_evidence(feature_dir: Path, payload: dict[str, object]) -> None:
    path = evidence_path(feature_dir)
    content = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    _atomic_write_text(path, content)


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            stream.write(content)
            temporary_path = Path(stream.name)
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def ensure_implementation_baseline(
    feature_dir: Path,
    implementation_path: Path,
) -> dict[str, object]:
    payload = load_evidence(feature_dir)
    if payload.get("baseline") is None:
        repo_root = project_root_for_feature(feature_dir)
        payload["baseline"] = capture_git_snapshot(repo_root)
        payload["final"] = None
        payload["changeSummary"] = None
        write_evidence(feature_dir, payload)
    refresh_implementation_document(implementation_path, payload)
    return payload


def finalize_implementation_evidence(
    feature_dir: Path,
    implementation_path: Path,
) -> dict[str, object]:
    payload = ensure_implementation_baseline(feature_dir, implementation_path)
    baseline = payload.get("baseline")
    base_head = (
        str(baseline.get("head"))
        if isinstance(baseline, dict) and baseline.get("head")
        else (
            ""
            if isinstance(baseline, dict) and baseline.get("gitAvailable")
            else None
        )
    )
    repo_root = project_root_for_feature(feature_dir)
    final = capture_git_snapshot(repo_root, base_head=base_head)
    payload["final"] = final
    payload["changeSummary"] = compare_snapshots(baseline, final)
    payload["validationSummary"] = summarize_validations(
        payload.get("validations"),
        final,
    )
    write_evidence(feature_dir, payload)
    refresh_implementation_document(implementation_path, payload)
    return payload


def run_and_record_validation(
    feature_dir: Path,
    implementation_path: Path,
    command: list[str],
) -> int:
    if not command:
        raise ValueError("run-validation 缺少待执行命令")
    payload = ensure_implementation_baseline(feature_dir, implementation_path)
    repo_root = project_root_for_feature(feature_dir)
    started = time.perf_counter()
    try:
        completed = subprocess.run(command, cwd=repo_root, check=False)
    except OSError as exc:
        raise ValueError(f"无法启动验证命令: {command[0]}: {exc}") from exc
    duration_ms = round((time.perf_counter() - started) * 1000)
    baseline = payload.get("baseline")
    base_head = (
        str(baseline.get("head"))
        if isinstance(baseline, dict) and baseline.get("head")
        else (
            ""
            if isinstance(baseline, dict) and baseline.get("gitAvailable")
            else None
        )
    )
    validated_snapshot = capture_git_snapshot(repo_root, base_head=base_head)
    validations = list(payload.get("validations", []))
    validations.append(
        {
            "recordedAt": _now(),
            "command": redact_command(command),
            "exitCode": completed.returncode,
            "durationMs": duration_ms,
            "gitAvailable": validated_snapshot.get("gitAvailable"),
            "head": validated_snapshot.get("head"),
            "workspaceFingerprint": validated_snapshot.get("fingerprint"),
        }
    )
    payload["validations"] = validations
    payload["validationSummary"] = summarize_validations(
        validations,
        validated_snapshot,
    )
    write_evidence(feature_dir, payload)
    refresh_implementation_document(implementation_path, payload)
    return completed.returncode


def capture_git_snapshot(
    repo_root: Path,
    *,
    base_head: str | None = None,
) -> dict[str, object]:
    branch = _git_text(repo_root, "symbolic-ref", "--quiet", "--short", "HEAD")
    head = _git_text(repo_root, "rev-parse", "--verify", "HEAD")
    status = _git_text(
        repo_root,
        "-c",
        "core.quotepath=false",
        "status",
        "--porcelain=v1",
        "-z",
        "--untracked-files=all",
    )
    if status is None:
        return {
            "capturedAt": _now(),
            "gitAvailable": False,
            "branch": branch,
            "head": head,
            "fingerprint": None,
            "entries": [],
            "reason": "当前目录不是可读取的 Git 工作区",
        }

    entries = _status_entries(repo_root, status)
    if base_head is not None and head and base_head != head:
        if base_head:
            committed = _git_text(
                repo_root,
                "-c",
                "core.quotepath=false",
                "diff",
                "--name-status",
                "-z",
                base_head,
                head,
            )
        else:
            # 未产生首个提交时没有可供 diff 的基准树；首个提交本身就是相对基线的全集。
            committed = _git_text(
                repo_root,
                "-c",
                "core.quotepath=false",
                "diff-tree",
                "--root",
                "--no-commit-id",
                "--name-status",
                "-r",
                "-z",
                head,
            )
        if committed is not None:
            for path, change_status in _committed_entries(committed).items():
                entries.setdefault(
                    path,
                    _entry(repo_root, path, f"committed:{change_status}"),
                )

    sorted_entries = [entries[path] for path in sorted(entries)]
    fingerprint_source = [
        {
            "path": entry["path"],
            "sha256": entry["sha256"],
            "exists": entry["exists"],
        }
        for entry in sorted_entries
    ]
    fingerprint = hashlib.sha256(
        json.dumps(
            fingerprint_source,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    return {
        "capturedAt": _now(),
        "gitAvailable": True,
        "branch": branch,
        "head": head,
        "fingerprint": fingerprint,
        "entries": sorted_entries,
        "reason": None,
    }


def compare_snapshots(
    baseline: object,
    final: object,
) -> dict[str, list[str]]:
    if not isinstance(baseline, dict) or not isinstance(final, dict):
        return _empty_change_summary()
    baseline_entries = _entries_by_path(baseline.get("entries"))
    final_entries = _entries_by_path(final.get("entries"))
    summary = _empty_change_summary()
    for path, entry in final_entries.items():
        before = baseline_entries.get(path)
        if before is None:
            summary["newlyChanged"].append(path)
        elif _entry_identity(before) == _entry_identity(entry):
            summary["preExistingUnchanged"].append(path)
        else:
            summary["changedFromBaseline"].append(path)
    summary["baselineResolved"] = sorted(
        set(baseline_entries) - set(final_entries)
    )
    return {key: sorted(value) for key, value in summary.items()}


def refresh_implementation_document(
    implementation_path: Path,
    payload: dict[str, object],
) -> None:
    if not implementation_path.is_file():
        return
    text = implementation_path.read_text(encoding="utf-8")
    start_count = text.count(AUTO_EVIDENCE_START)
    end_count = text.count(AUTO_EVIDENCE_END)
    uses_auto_section = "## 2. 自动派生实现证据" in text or (
        "## 3. 自动派生实现证据" in text
    )
    if (
        start_count != end_count
        or start_count > 1
        or (uses_auto_section and start_count != 1)
    ):
        raise ValueError(f"实现产物的 Runtime 自动证据标记缺失或不完整: {implementation_path}")
    if start_count == 0:
        return
    start_marker_index = text.index(AUTO_EVIDENCE_START)
    end_marker_index = text.index(AUTO_EVIDENCE_END)
    if end_marker_index < start_marker_index:
        raise ValueError(f"实现产物的 Runtime 自动证据标记顺序错误: {implementation_path}")
    start_index = start_marker_index + len(AUTO_EVIDENCE_START)
    end_index = end_marker_index
    replacement = "\n" + render_evidence_summary(payload) + "\n"
    updated = text[:start_index] + replacement + text[end_index:]
    if updated != text:
        _atomic_write_text(implementation_path, updated)


def render_evidence_summary(payload: dict[str, object]) -> str:
    baseline = payload.get("baseline")
    final = payload.get("final")
    validations = payload.get("validations", [])
    summary = payload.get("changeSummary")
    lines = [
        f"- 证据文件：`{IMPLEMENTATION_EVIDENCE_PATH.as_posix()}`",
        f"- Git 基线：{_snapshot_label(baseline)}",
        f"- 当前工作区：{_snapshot_label(final) if final else '待完成阶段时自动采集'}",
    ]
    if isinstance(summary, dict):
        lines.extend(
            [
                "- 基线后出现变化：" + _path_list(summary.get("newlyChanged")),
                "- 基线文件继续变化：" + _path_list(summary.get("changedFromBaseline")),
                "- 既存改动未变化：" + _path_list(summary.get("preExistingUnchanged")),
                "- 基线改动已消失：" + _path_list(summary.get("baselineResolved")),
            ]
        )
    if isinstance(validations, list) and validations:
        lines.append("- 自动记录的验证：")
        for index, validation in enumerate(validations, start=1):
            if not isinstance(validation, dict):
                continue
            command = validation.get("command", [])
            command_text = " ".join(str(value) for value in command)
            lines.append(
                f"  - V{index:02d}：`{command_text}`；"
                f"退出码 {validation.get('exitCode')}；"
                f"耗时 {validation.get('durationMs')} ms；"
                f"快照{_validation_freshness(validation, final)}"
            )
    else:
        lines.append("- 自动记录的验证：暂无；完成前通过 `run-validation` 执行")
    lines.append(
        "- 归属边界：基线后出现变化仍需结合完整 diff 复核；"
        "“基线文件继续变化”不能自动归因于本轮"
    )
    return "\n".join(lines)


def redact_command(command: list[str]) -> list[str]:
    redacted: list[str] = []
    redact_next = False
    for argument in command:
        if redact_next:
            redacted.append("<redacted>")
            redact_next = False
            continue
        if SENSITIVE_HEADER.search(argument):
            redacted.append("<redacted-header>")
            continue
        if "=" in argument:
            key, _separator, _value = argument.partition("=")
            if SENSITIVE_ARGUMENT.search(key):
                redacted.append(f"{key}=<redacted>")
                continue
        if ":" in argument and argument.startswith(("-", "/")):
            key, _separator, _value = argument.partition(":")
            if SENSITIVE_ARGUMENT.search(key):
                redacted.append(f"{key}:<redacted>")
                continue
        redacted.append(argument)
        if argument.startswith("-") and SENSITIVE_ARGUMENT.search(argument):
            redact_next = True
    return redacted


def _git_text(repo_root: Path, *args: str) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo_root), *args],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError:
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout.rstrip()


def _status_entries(repo_root: Path, status: str) -> dict[str, dict[str, object]]:
    entries: dict[str, dict[str, object]] = {}
    records = status.split("\0")
    index = 0
    while index < len(records):
        record = records[index]
        index += 1
        if len(record) < 4:
            continue
        change_status = record[:2]
        path = record[3:]
        # Porcelain -z 把 rename/copy 的目标路径放在当前记录，下一记录是来源路径。
        if "R" in change_status or "C" in change_status:
            index += 1
        if _is_tool_owned(path):
            continue
        entries[path] = _entry(repo_root, path, change_status)
    return entries


def _committed_entries(status: str) -> dict[str, str]:
    entries: dict[str, str] = {}
    records = status.split("\0")
    index = 0
    while index < len(records):
        change_status = records[index]
        index += 1
        if not change_status or index >= len(records):
            continue
        path = records[index]
        index += 1
        if change_status.startswith(("R", "C")):
            if index >= len(records):
                continue
            path = records[index]
            index += 1
        if not _is_tool_owned(path):
            entries[path] = change_status
    return entries


def _entry(
    repo_root: Path,
    relative_path: str,
    change_status: str,
) -> dict[str, object]:
    path = repo_root / Path(relative_path)
    exists = path.is_file()
    return {
        "path": Path(relative_path).as_posix(),
        "status": change_status,
        "exists": exists,
        "sha256": _file_sha256(path) if exists else None,
    }


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_tool_owned(path: str) -> bool:
    normalized = Path(path).as_posix()
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return (
        normalized == ".zstt"
        or normalized.startswith(".zstt/")
        or normalized == ".zstt-kit"
        or normalized.startswith(".zstt-kit/")
        or normalized.startswith(".agents/skills/zstt-")
    )


def _entries_by_path(value: object) -> dict[str, dict[str, object]]:
    if not isinstance(value, list):
        return {}
    return {
        str(entry["path"]): entry
        for entry in value
        if isinstance(entry, dict) and isinstance(entry.get("path"), str)
    }


def _entry_identity(entry: dict[str, object]) -> tuple[object, object]:
    return entry.get("exists"), entry.get("sha256")


def _empty_change_summary() -> dict[str, list[str]]:
    return {
        "newlyChanged": [],
        "changedFromBaseline": [],
        "preExistingUnchanged": [],
        "baselineResolved": [],
    }


def summarize_validations(
    validations: object,
    snapshot: object,
) -> dict[str, int]:
    summary = {
        "freshPassed": 0,
        "freshFailed": 0,
        "stalePassed": 0,
        "staleFailed": 0,
        "unknown": 0,
    }
    if not isinstance(validations, list):
        return summary
    effective: dict[tuple[str, str, tuple[str, ...]], dict[str, object]] = {}
    unknown_count = 0
    for validation in validations:
        if not isinstance(validation, dict):
            unknown_count += 1
            continue
        freshness = _validation_freshness(validation, snapshot)
        command = validation.get("command")
        command_key = (
            tuple(str(value) for value in command)
            if isinstance(command, list)
            else ()
        )
        fingerprint = str(validation.get("workspaceFingerprint") or "")
        # 同一快照重跑同一命令时，以最后一次结果为准，允许修复瞬时环境失败。
        effective[(freshness, fingerprint, command_key)] = validation
    summary["unknown"] = unknown_count
    for (freshness, _fingerprint, _command), validation in effective.items():
        exit_code = validation.get("exitCode")
        if freshness == "与当前一致" and exit_code == 0:
            summary["freshPassed"] += 1
        elif freshness == "与当前一致":
            summary["freshFailed"] += 1
        elif freshness == "已过期" and exit_code == 0:
            summary["stalePassed"] += 1
        elif freshness == "已过期":
            summary["staleFailed"] += 1
        else:
            summary["unknown"] += 1
    return summary


def _validation_freshness(
    validation: dict[str, object],
    snapshot: object,
) -> str:
    if not isinstance(snapshot, dict):
        return "待判定"
    expected = validation.get("workspaceFingerprint")
    actual = snapshot.get("fingerprint")
    if not validation.get("gitAvailable") or not snapshot.get("gitAvailable"):
        return "无法比较"
    if not expected or not actual:
        return "无法比较"
    return "与当前一致" if expected == actual else "已过期"


def _snapshot_label(value: object) -> str:
    if not isinstance(value, dict):
        return "未采集"
    if not value.get("gitAvailable"):
        return f"Git 不可用（{value.get('reason', '原因未知')}）"
    fingerprint = str(value.get("fingerprint") or "")
    short_fingerprint = fingerprint[:12] if fingerprint else "无"
    branch = value.get("branch") or "detached/unborn"
    entries = value.get("entries")
    count = len(entries) if isinstance(entries, list) else 0
    return f"分支 `{branch}`；工作区条目 {count}；快照 `{short_fingerprint}`"


def _path_list(value: object) -> str:
    if not isinstance(value, list) or not value:
        return "无"
    return "、".join(f"`{path}`" for path in value)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
