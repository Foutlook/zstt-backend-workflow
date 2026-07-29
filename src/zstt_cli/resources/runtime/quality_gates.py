from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from workflow_contracts import get_contract
from workflow_validation import artifact_fingerprint, count_value, parse_frontmatter


QUALITY_GATE_SCHEMA_VERSION = 1
QUALITY_GATE_STATUSES = {"draft", "passed", "conditional", "blocked"}


@dataclass(frozen=True)
class QualityGateContract:
    key: str
    report: Path
    modes: tuple[str, ...]
    source_stages: tuple[str, ...]
    required_headings: tuple[str, ...]


QUALITY_GATES = (
    QualityGateContract(
        "requirement_checklist",
        Path("checklists/requirements.md"),
        ("full", "quick"),
        ("requirement_clarification",),
        (
            "## 检查范围",
            "## 规则加载记录",
            "## Checklist",
            "## 级别摘要",
            "## 建议回写",
            "## 未覆盖领域",
        ),
    ),
    QualityGateContract(
        "artifact_analysis",
        Path("analysis/artifact-analysis.md"),
        ("full",),
        (
            "requirement_clarification",
            "repo_research",
            "technical_design",
            "task_breakdown",
        ),
        (
            "## 结论",
            "## 规则加载记录",
            "## 问题",
            "## 覆盖摘要",
            "## 未验证边界",
            "## 下一步",
        ),
    ),
)

SOURCE_FINGERPRINT_FIELDS = {
    "requirement_clarification": "requirement_fingerprint",
    "repo_research": "research_fingerprint",
    "technical_design": "design_fingerprint",
    "task_breakdown": "tasks_fingerprint",
}

CHECKLIST_ITEM_PATTERN = re.compile(
    r"^- \[(?P<mark>[ xX])\] (?P<id>CHK\d{3}) "
    r"\[(?P<severity>P[012])\] (?P<body>.+)$",
    flags=re.MULTILINE,
)
ANALYSIS_FINDING_PATTERN = re.compile(
    r"^\|\s*(?P<id>(?:COV|CON|DAT|DEP|POL)-\d{3})\s*"
    r"\|\s*(?P<severity>P[012])\s*\|",
    flags=re.MULTILINE,
)
TRACEABILITY_PATTERN = re.compile(
    r"\b[RSQ]\d+\b|\[(?:Gap|Ambiguity|Conflict|Assumption)\]|§|章节"
)


def get_quality_gate(gate_key: str) -> QualityGateContract:
    for gate in QUALITY_GATES:
        if gate.key == gate_key:
            return gate
    raise ValueError(f"未知质量门禁: {gate_key}")


def supported_quality_gates(mode: str) -> tuple[QualityGateContract, ...]:
    return tuple(gate for gate in QUALITY_GATES if mode in gate.modes)


def quality_gates_before_stage(mode: str, stage_key: str) -> tuple[str, ...]:
    if stage_key == "repo_research" and mode == "full":
        return ("requirement_checklist",)
    if stage_key == "implementation" and mode == "full":
        return ("artifact_analysis",)
    if stage_key == "implementation" and mode == "quick":
        return ("requirement_checklist",)
    return ()


def quality_gate_report_path(feature_dir: Path, gate_key: str) -> Path:
    return feature_dir / get_quality_gate(gate_key).report


def quality_gate_source_fingerprints(
    feature_dir: Path,
    mode: str,
    gate_key: str,
) -> dict[str, str]:
    gate = get_quality_gate(gate_key)
    if mode not in gate.modes:
        raise ValueError(f"{gate_key} 不支持 {mode} 模式")
    fingerprints: dict[str, str] = {}
    for stage_key in gate.source_stages:
        artifact = get_contract(mode, stage_key).artifact
        fingerprint = artifact_fingerprint(feature_dir / artifact)
        if not fingerprint:
            raise FileNotFoundError(f"质量门禁输入产物不存在: {feature_dir / artifact}")
        fingerprints[stage_key] = fingerprint
    return fingerprints


def quality_gate_template_values(
    feature_dir: Path,
    mode: str,
    gate_key: str,
) -> dict[str, str]:
    fingerprints = quality_gate_source_fingerprints(feature_dir, mode, gate_key)
    values = {
        "MODE": mode,
        "REQUIREMENT_FINGERPRINT": fingerprints.get(
            "requirement_clarification",
            "",
        ),
        "RESEARCH_FINGERPRINT": fingerprints.get("repo_research", ""),
        "DESIGN_FINGERPRINT": fingerprints.get("technical_design", ""),
        "TASKS_FINGERPRINT": fingerprints.get("task_breakdown", ""),
    }
    return values


def validate_quality_gate_document(
    feature_dir: Path,
    mode: str,
    gate_key: str,
) -> tuple[list[str], dict[str, str]]:
    gate = get_quality_gate(gate_key)
    if mode not in gate.modes:
        return [f"{gate_key} 不支持 {mode} 模式"], {}

    report_path = quality_gate_report_path(feature_dir, gate_key)
    if not report_path.is_file():
        return [f"质量门禁产物不存在: {report_path}"], {}

    text = report_path.read_text(encoding="utf-8")
    frontmatter = parse_frontmatter(text)
    errors: list[str] = []
    required_keys = {
        "quality_gate_schema_version",
        "quality_gate",
        "mode",
        "status",
        "blocking_p0_count",
        "open_p1_count",
        "open_p2_count",
        "ruleset_version",
        "ruleset_fingerprint",
        *(SOURCE_FINGERPRINT_FIELDS[stage] for stage in gate.source_stages),
    }
    missing = sorted(required_keys - frontmatter.keys())
    if missing:
        errors.append("质量门禁 frontmatter 缺少字段: " + ", ".join(missing))

    if frontmatter.get("quality_gate_schema_version") != str(
        QUALITY_GATE_SCHEMA_VERSION
    ):
        errors.append(
            "quality_gate_schema_version 必须为 "
            f"{QUALITY_GATE_SCHEMA_VERSION}"
        )
    if frontmatter.get("quality_gate") != gate.key:
        errors.append(f"quality_gate 必须为 {gate.key}")
    if frontmatter.get("mode") != mode:
        errors.append(f"质量门禁 mode 必须为 {mode}")

    status = frontmatter.get("status", "")
    if status not in QUALITY_GATE_STATUSES:
        errors.append(
            "质量门禁 status 必须是 draft/passed/conditional/blocked"
        )

    for key in ("ruleset_version", "ruleset_fingerprint"):
        value = frontmatter.get(key, "").strip()
        if not value or value in {"pending", "待填写"} or "{{" in value:
            errors.append(f"质量门禁 {key} 必须记录本次真实规则快照")

    try:
        expected_fingerprints = quality_gate_source_fingerprints(
            feature_dir,
            mode,
            gate_key,
        )
    except FileNotFoundError as exc:
        errors.append(str(exc))
        expected_fingerprints = {}
    for stage_key, expected in expected_fingerprints.items():
        field = SOURCE_FINGERPRINT_FIELDS[stage_key]
        if frontmatter.get(field) != expected:
            artifact = get_contract(mode, stage_key).artifact
            errors.append(f"输入指纹已过期: {artifact}")

    for heading in gate.required_headings:
        if heading not in text.splitlines():
            errors.append(f"质量门禁缺少章节: {heading}")

    counts = {
        "p0": count_value(frontmatter, "blocking_p0_count", errors),
        "p1": count_value(frontmatter, "open_p1_count", errors),
        "p2": count_value(frontmatter, "open_p2_count", errors),
    }
    if gate.key == "requirement_checklist":
        actual_counts = validate_requirement_checklist(text, errors)
    else:
        actual_counts = validate_artifact_analysis(text, errors)
    for severity, actual in actual_counts.items():
        if counts[severity] != actual:
            field = {
                "p0": "blocking_p0_count",
                "p1": "open_p1_count",
                "p2": "open_p2_count",
            }[severity]
            errors.append(f"{field}={counts[severity]} 与正文未解决项 {actual} 不一致")

    expected_status = quality_gate_status_for_counts(actual_counts)
    if status != expected_status:
        errors.append(
            f"质量门禁 status={status or '<empty>'}，"
            f"按正文未解决项应为 {expected_status}"
        )
    return errors, frontmatter


def validate_requirement_checklist(
    text: str,
    errors: list[str],
) -> dict[str, int]:
    # 模板和人工说明可以使用 HTML 注释；注释不是已执行检查，不能污染门禁计数。
    visible_text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    matches = list(CHECKLIST_ITEM_PATTERN.finditer(visible_text))
    if not matches:
        errors.append("需求质量 Checklist 至少需要一个已执行的 CHK 检查项")
        return {"p0": 0, "p1": 0, "p2": 0}

    ids = [match.group("id") for match in matches]
    if len(ids) != len(set(ids)):
        errors.append("需求质量 Checklist 的 CHK ID 必须唯一")
    expected_ids = [f"CHK{index:03d}" for index in range(1, len(ids) + 1)]
    if ids != expected_ids:
        errors.append("需求质量 Checklist 的 CHK ID 必须从 CHK001 连续编号")

    traceable = sum(
        bool(TRACEABILITY_PATTERN.search(match.group("body")))
        for match in matches
    )
    if traceable / len(matches) < 0.8:
        errors.append("需求质量 Checklist 至少 80% 的检查项必须可追溯")
    for match in matches:
        if "证据：" not in match.group("body"):
            errors.append(f"{match.group('id')} 必须在同一行记录“证据：”")

    counts = {"p0": 0, "p1": 0, "p2": 0}
    for match in matches:
        if match.group("mark") == " ":
            counts[match.group("severity").lower()] += 1
    return counts


def validate_artifact_analysis(
    text: str,
    errors: list[str],
) -> dict[str, int]:
    visible_text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    matches = list(ANALYSIS_FINDING_PATTERN.finditer(visible_text))
    ids = [match.group("id") for match in matches]
    if len(ids) != len(set(ids)):
        errors.append("实现前一致性分析的问题 ID 必须唯一")

    counts = {"p0": 0, "p1": 0, "p2": 0}
    for match in matches:
        counts[match.group("severity").lower()] += 1
    return counts


def quality_gate_status_for_counts(counts: dict[str, int]) -> str:
    if counts["p0"] > 0:
        return "blocked"
    if counts["p1"] > 0 or counts["p2"] > 0:
        return "conditional"
    return "passed"


def quality_gate_summary(
    feature_dir: Path,
    mode: str,
    gate_key: str,
) -> dict[str, object]:
    gate = get_quality_gate(gate_key)
    report_path = quality_gate_report_path(feature_dir, gate_key)
    base: dict[str, object] = {
        "path": gate.report.as_posix(),
        "exists": report_path.is_file(),
    }
    if not report_path.is_file():
        return {**base, "state": "skipped", "errors": []}

    errors, frontmatter = validate_quality_gate_document(
        feature_dir,
        mode,
        gate_key,
    )
    stale = any(error.startswith("输入指纹已过期:") for error in errors)
    status = frontmatter.get("status", "draft")
    if stale:
        state = "stale"
    elif errors or status in {"draft", "blocked"}:
        state = "blocked"
    else:
        state = status
    return {
        **base,
        "state": state,
        "status": status,
        "blocking_counts": {
            "p0": _safe_count(frontmatter.get("blocking_p0_count")),
            "p1": _safe_count(frontmatter.get("open_p1_count")),
            "p2": _safe_count(frontmatter.get("open_p2_count")),
        },
        "errors": errors,
    }


def quality_gate_summaries(
    feature_dir: Path,
    mode: str,
) -> dict[str, dict[str, object]]:
    return {
        gate.key: quality_gate_summary(feature_dir, mode, gate.key)
        for gate in supported_quality_gates(mode)
    }


def _safe_count(value: str | None) -> int:
    try:
        return max(0, int(value or "0"))
    except ValueError:
        return 0
