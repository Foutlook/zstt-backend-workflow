from __future__ import annotations

import hashlib
import re
from pathlib import Path


COMMON_FRONTMATTER_KEYS = {
    "workflow",
    "mode",
    "stage",
    "status",
    "blocking_p0_count",
    "open_p1_count",
    "open_p2_count",
}

REQUIRED_HEADINGS: dict[tuple[str, str], tuple[str, ...]] = {
    ("full", "requirement_clarification"): (
        "## 1. 输入材料与模式",
        "## 2. 目标与范围",
        "## 3. 用户路径与角色权限",
        "## 4. 数据来源与数据身份",
        "## 5. 状态流转与业务规则",
        "## 6. 边界、异常与历史兼容",
        "## 7. 验收标准",
        "## 8. 事实、归纳、推断与冲突",
        "## 9. 未决问题与阻塞项",
        "## 10. 确认记录",
        "## 11. 下游交接",
    ),
    ("quick", "requirement_clarification"): (
        "## 1. 输入与目标",
        "## 2. 修改范围与不做事项",
        "## 3. 关键规则与风险",
        "## 4. 验收信号",
        "## 5. 未决问题与阻塞项",
        "## 6. 确认记录",
        "## 7. 下游交接",
    ),
    ("full", "repo_research"): (
        "## 1. 输入与调研范围",
        "## 2. 仓库与模块边界",
        "## 3. 入口与真实调用链",
        "## 4. Guard 条件与真实业务依赖",
        "## 5. 最终数据源与关键参数",
        "## 6. 旧链路副作用与影响面",
        "## 7. 跨仓库契约",
        "## 8. 结论账本与证据索引",
        "## 9. 风险与运行时缺口",
        "## 10. 方案阶段交接",
    ),
    ("full", "technical_design"): (
        "## 1. 输入与代码基线",
        "## 2. 需求与现状差距",
        "## 3. 设计原则与决策",
        "## 4. 数据身份、状态与职责边界",
        "## 5. 整体方案与主流程",
        "## 6. 接口与契约设计",
        "## 7. 数据存储与查询设计",
        "## 8. 代码改动落点",
        "## 9. 兼容、发布与回滚",
        "## 10. 可观测性与测试策略",
        "## 11. 风险、阻塞与任务交接",
    ),
    ("full", "task_breakdown"): (
        "## 1. 输入与覆盖矩阵",
        "## 2. 执行顺序与依赖",
        "## 3. 任务清单",
        "## 4. 文件范围与并行安全",
        "## 5. 验证命令与完成标准",
        "## 6. 阻塞项与实现交接",
    ),
    ("full", "implementation"): (
        "## 1. 实现前检查",
        "## 2. 执行计划",
        "## 3. 实际修改与任务状态",
        "## 4. 设计偏差与回写",
        "## 5. 质量自检",
        "## 6. 验证命令与结果",
        "## 7. Review 交接",
    ),
    ("quick", "implementation"): (
        "## 1. 实现前检查",
        "## 2. 简短执行计划",
        "## 3. 实际修改",
        "## 4. 边界偏差与风险",
        "## 5. 验证结果",
        "## 6. 下一步建议",
    ),
    ("full", "code_review"): (
        "## 1. 评审范围与输入",
        "## 2. 需求、方案、任务与实现一致性",
        "## 3. 真实执行链与数据源复核",
        "## 4. 问题清单",
        "## 5. Java 后端质量检查",
        "## 6. 验证证据复核",
        "## 7. 评审结论与下一步",
    ),
    ("quick", "code_review"): (
        "## 1. 评审范围",
        "## 2. 边界与实现一致性",
        "## 3. 问题清单",
        "## 4. 验证证据",
        "## 5. 评审结论",
    ),
    ("full", "test_verify"): (
        "## 1. 输入与验证范围",
        "## 2. 应测场景与前置条件",
        "## 3. 需求、方案、实现与用例映射",
        "## 4. 执行记录与实际结果",
        "## 5. 差异分类与证据链",
        "## 6. 覆盖缺口与风险",
        "## 7. 交付结论",
    ),
    ("quick", "test_verify"): (
        "## 1. 验证范围",
        "## 2. 场景与前置条件",
        "## 3. 执行结果",
        "## 4. 差异与风险",
        "## 5. 交付结论",
    ),
}

PLACEHOLDER_PATTERN = re.compile(r"\{\{[^{}\n]+}}")
EMPTY_SCAFFOLD_PATTERN = re.compile(
    r"^\s*[-*]\s+[^\n：:]+[：:]\s*$",
    re.MULTILINE,
)
TRACEABILITY_PATTERNS: dict[tuple[str, str], tuple[tuple[str, str], ...]] = {
    ("full", "repo_research"): (
        (r"\bC\d+\b", "调研结论 ID（如 C01）"),
        (r"\bE\d+\b", "调研证据 ID（如 E01）"),
    ),
    ("full", "technical_design"): (
        (r"\bD\d+\b", "设计决策 ID（如 D01）"),
        (r"\bC\d+\b", "调研结论引用（如 C01）"),
    ),
    ("full", "task_breakdown"): (
        (r"\bT\d+\b", "任务 ID（如 T01）"),
        (r"\b[CD]\d+\b", "调研或设计来源引用（如 C01/D01）"),
    ),
}


def artifact_fingerprint(path: Path) -> str:
    if not path.is_file():
        return ""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_frontmatter(text: str) -> dict[str, str]:
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        return {}
    try:
        end = lines.index("---", 1)
    except ValueError:
        return {}

    values: dict[str, str] = {}
    for line in lines[1:end]:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip()
    return values


def count_value(frontmatter: dict[str, str], key: str, errors: list[str]) -> int:
    try:
        value = int(frontmatter.get(key, ""))
    except ValueError:
        errors.append(f"frontmatter 的 {key} 必须是非负整数")
        return 0
    if value < 0:
        errors.append(f"frontmatter 的 {key} 必须是非负整数")
        return 0
    return value


def section_body(text: str, heading: str) -> str:
    lines = text.splitlines()
    try:
        start = lines.index(heading) + 1
    except ValueError:
        return ""
    end = len(lines)
    for index in range(start, len(lines)):
        if lines[index].startswith("## "):
            end = index
            break
    return "\n".join(lines[start:end])


def table_has_data(lines: list[str]) -> bool:
    group: list[str] = []
    groups: list[list[str]] = []
    for line in lines + [""]:
        if line.strip().startswith("|") and line.strip().endswith("|"):
            group.append(line.strip())
            continue
        if group:
            groups.append(group)
            group = []

    for table in groups:
        separator_index = next(
            (
                index
                for index, row in enumerate(table)
                if all(
                    re.fullmatch(r":?-{3,}:?", cell.strip())
                    for cell in row.strip("|").split("|")
                )
            ),
            None,
        )
        if separator_index is None:
            continue
        for row in table[separator_index + 1 :]:
            if any(cell.strip() for cell in row.strip("|").split("|")):
                return True
    return False


def section_has_substance(body: str) -> bool:
    lines = body.splitlines()
    if table_has_data(lines):
        return True

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("|"):
            continue
        if stripped in {"---", "```"}:
            continue
        if re.fullmatch(r"[-*_]{3,}", stripped):
            continue
        if EMPTY_SCAFFOLD_PATTERN.fullmatch(line):
            continue
        if stripped in {"-", "*", "+"}:
            continue
        return True
    return False


def validate_traceability(path: Path, mode: str, stage: str, text: str) -> list[str]:
    errors: list[str] = []
    for pattern, label in TRACEABILITY_PATTERNS.get((mode, stage), ()):
        if not re.search(pattern, text):
            errors.append(f"缺少可追溯的{label}")

    if mode == "full" and stage == "technical_design":
        research_path = path.parent / "01-research.md"
        if research_path.is_file():
            research_ids = set(re.findall(r"\bC\d+\b", research_path.read_text(encoding="utf-8")))
            unknown_ids = sorted(set(re.findall(r"\bC\d+\b", text)) - research_ids)
            if unknown_ids:
                errors.append("设计引用了调研中不存在的结论 ID: " + ", ".join(unknown_ids))

    if mode == "full" and stage == "task_breakdown":
        design_path = path.parent / "02-design.md"
        if design_path.is_file():
            design_ids = set(re.findall(r"\bD\d+\b", design_path.read_text(encoding="utf-8")))
            unknown_ids = sorted(set(re.findall(r"\bD\d+\b", text)) - design_ids)
            if unknown_ids:
                errors.append("任务引用了方案中不存在的设计 ID: " + ", ".join(unknown_ids))
    return errors


def validate_stage_document(
    path: Path,
    mode: str,
    stage: str,
    require_completed: bool = True,
) -> tuple[list[str], dict[str, str]]:
    if not path.is_file():
        return [f"阶段产物不存在: {path}"], {}
    raw = path.read_bytes()
    errors: list[str] = []
    if raw.startswith(b"\xef\xbb\xbf"):
        errors.append("阶段产物包含 UTF-8 BOM")

    text = raw.decode("utf-8")
    placeholders = sorted(set(PLACEHOLDER_PATTERN.findall(text)))
    if placeholders:
        errors.append("仍有未替换模板占位符: " + ", ".join(placeholders))
    empty_scaffolds = sorted(
        {match.group(0).strip() for match in EMPTY_SCAFFOLD_PATTERN.finditer(text)}
    )
    if require_completed and empty_scaffolds:
        errors.append("仍有未填写模板项: " + ", ".join(empty_scaffolds))

    frontmatter = parse_frontmatter(text)
    missing_keys = sorted(COMMON_FRONTMATTER_KEYS - frontmatter.keys())
    if missing_keys:
        errors.append("frontmatter 缺少字段: " + ", ".join(missing_keys))
    if frontmatter.get("workflow") != "zztt-backend-workflow":
        errors.append("workflow 必须是 zztt-backend-workflow")
    if frontmatter.get("mode") != mode:
        errors.append(f"mode 必须是 {mode}")
    if frontmatter.get("stage") != stage:
        errors.append(f"stage 必须是 {stage}")
    if require_completed and frontmatter.get("status") != "completed":
        errors.append("status 必须是 completed")

    p0_count = count_value(frontmatter, "blocking_p0_count", errors)
    count_value(frontmatter, "open_p1_count", errors)
    count_value(frontmatter, "open_p2_count", errors)
    if p0_count > 0:
        errors.append(f"仍有 {p0_count} 个 P0 阻塞项")

    missing_headings = [
        heading
        for heading in REQUIRED_HEADINGS.get((mode, stage), ())
        if heading not in text
    ]
    if missing_headings:
        errors.append("缺少必需章节: " + ", ".join(missing_headings))
    if require_completed:
        empty_sections = [
            heading
            for heading in REQUIRED_HEADINGS.get((mode, stage), ())
            if heading in text and not section_has_substance(section_body(text, heading))
        ]
        if empty_sections:
            errors.append("必需章节缺少实质内容: " + ", ".join(empty_sections))
        errors.extend(validate_traceability(path, mode, stage, text))
    return errors, frontmatter
