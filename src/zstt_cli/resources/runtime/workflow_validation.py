from __future__ import annotations

import hashlib
import json
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

REQUIREMENT_CONFIRMATION_KEYS = {
    "confirmation_status",
    "confirmation_source",
}

RESEARCH_SCOPE_KEYS = {
    "research_scope",
    "shared_semantic_impact",
    "current_sql_impact",
}

TECHNICAL_DESIGN_SQL_KEYS = {
    "sql_impact",
    "sql_gate_status",
    "sql_fingerprint",
    "sql_confirmation_source",
}

SQL_IMPACTS = {"pending", "none", "query_dml", "ddl"}
SQL_GATE_STATUSES = {
    "not_evaluated",
    "pending_confirmation",
    "not_involved",
    "confirmed",
    "stale",
}
SQL_DESIGN_ARTIFACT = Path("auxiliary/sql-design.sql")
RESEARCH_IMPACTS = {"pending", "none", "involved"}
RESEARCH_SCOPES = {"focused", "full"}
REQUIREMENT_QUESTION_TYPES = {"用户意图", "代码事实", "设计选择"}
REQUIREMENT_QUESTION_STATUSES = {"待确认", "已确认", "转下游", "已关闭"}
RESEARCH_QUESTION_TYPES = {"用户意图", "代码事实", "运行时证据", "设计选择"}
RESEARCH_QUESTION_STATUSES = {"待处理", "已解决", "转下游"}
EVIDENCE_LEVELS = {
    "Proven",
    "Framework inferred",
    "Requirement claim",
    "Runtime dependent",
    "Unknown",
}
EVIDENCE_TYPES = {
    "本地源码",
    "远程源码",
    "运行证据",
    "配置",
    "数据库",
    "日志/Trace",
    "消息/任务",
    "用户口径",
    "需求材料",
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
        "## 2. 仓库边界与每仓 ChangeScope",
        "## 3. 入口与真实调用链",
        "## 4. Guard 条件与真实业务依赖",
        "## 5. 最终数据源与关键参数",
        "## 6. 共享语义反向影响",
        "## 7. 当前 SQL 事实与影响",
        "## 8. 旧链路副作用与影响面",
        "## 9. 跨仓库契约",
        "## 10. 结论账本与证据索引",
        "## 11. 调研问题与阶段承接",
        "## 12. 风险与运行时缺口",
        "## 13. 方案阶段交接",
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

TECHNICAL_DESIGN_PRE_SQL_HEADINGS = REQUIRED_HEADINGS[("full", "technical_design")][:7]

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


def sql_gate_fingerprint(design_path: Path) -> str:
    """Fingerprint SQL decisions while ignoring gate bookkeeping fields."""
    if not design_path.is_file():
        return ""
    text = design_path.read_text(encoding="utf-8")
    section = section_body(text, "## 7. 数据存储与查询设计")
    stable_lines = [
        line
        for line in section.splitlines()
        if not re.match(
            r"^\s*-\s*(SQL Gate 状态|SQL 指纹|用户确认来源)[：:]",
            line,
        )
    ]
    sql_path = design_path.parent / SQL_DESIGN_ARTIFACT
    sql_bytes = sql_path.read_bytes() if sql_path.is_file() else b""
    digest = hashlib.sha256()
    digest.update("\n".join(stable_lines).encode("utf-8"))
    digest.update(b"\0")
    digest.update(sql_bytes)
    return digest.hexdigest()


def validate_sql_artifact(design_path: Path, impact: str) -> list[str]:
    errors: list[str] = []
    sql_path = design_path.parent / SQL_DESIGN_ARTIFACT
    if impact == "none":
        if sql_path.exists():
            errors.append(f"SQL 影响为 none 时不得保留 SQL 草案: {sql_path}")
        return errors

    if impact not in {"query_dml", "ddl"}:
        return [f"不支持的 SQL 影响类型: {impact}"]
    if not sql_path.is_file():
        return [f"涉及 SQL 时必须提供精确 SQL 草案: {sql_path}"]
    text = sql_path.read_text(encoding="utf-8").strip()
    if not text:
        return [f"SQL 草案不能为空: {sql_path}"]
    executable = re.sub(r"/\*(?!\!)[\s\S]*?\*/", " ", text)
    executable = re.sub(r"--[^\n]*", " ", executable)
    if not re.search(
        r"\b(select|insert|update|delete|create|alter|drop|truncate|rename)\b",
        executable,
        flags=re.IGNORECASE,
    ):
        errors.append("SQL 草案缺少可执行的 SELECT/INSERT/UPDATE/DELETE/DDL")
    has_ddl = bool(
        re.search(
            r"\b(create|alter|drop|truncate|rename)\b",
            executable,
            flags=re.IGNORECASE,
        )
    )
    if impact == "ddl" and not has_ddl:
        errors.append("SQL 影响类型为 ddl，但草案中未发现 DDL")
    if impact == "query_dml" and has_ddl:
        errors.append("SQL 草案包含 DDL，影响类型必须使用 ddl")
    return errors


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
        parsed_value = value.strip()
        if parsed_value.startswith('"') and parsed_value.endswith('"'):
            try:
                parsed_value = json.loads(parsed_value)
            except json.JSONDecodeError:
                pass
        values[key.strip()] = parsed_value
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


def normalized_table_header(value: str) -> str:
    return re.sub(r"\s+", "", value.strip())


def markdown_tables(text: str) -> list[tuple[list[str], list[dict[str, str]]]]:
    """Parse simple Markdown tables for deterministic workflow validation."""
    lines = text.splitlines()
    groups: list[list[str]] = []
    group: list[str] = []
    for line in lines + [""]:
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            group.append(stripped)
            continue
        if group:
            groups.append(group)
            group = []

    parsed: list[tuple[list[str], list[dict[str, str]]]] = []
    for table in groups:
        if len(table) < 2:
            continue
        headers = [
            normalized_table_header(cell)
            for cell in table[0].strip("|").split("|")
        ]
        separators = [
            cell.strip()
            for cell in table[1].strip("|").split("|")
        ]
        if len(headers) != len(separators) or not all(
            re.fullmatch(r":?-{3,}:?", cell) for cell in separators
        ):
            continue

        rows: list[dict[str, str]] = []
        for line in table[2:]:
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            cells.extend([""] * (len(headers) - len(cells)))
            row = {
                header: cells[index] if index < len(cells) else ""
                for index, header in enumerate(headers)
            }
            if any(row.values()):
                rows.append(row)
        parsed.append((headers, rows))
    return parsed


def find_markdown_table(
    text: str,
    required_headers: tuple[str, ...],
) -> tuple[list[str], list[dict[str, str]]]:
    normalized = {
        normalized_table_header(header)
        for header in required_headers
    }
    for headers, rows in markdown_tables(text):
        if normalized.issubset(set(headers)):
            return headers, rows
    return [], []


def table_value(row: dict[str, str], header: str) -> str:
    return row.get(normalized_table_header(header), "").strip()


def referenced_ids(value: str, prefix: str) -> set[str]:
    return set(re.findall(rf"\b{re.escape(prefix)}\d+\b", value))


def duplicate_ids(values: list[str]) -> list[str]:
    return sorted({value for value in values if values.count(value) > 1})


def artifact_project_root(path: Path) -> Path | None:
    for parent in path.parents:
        if parent.name == ".zstt":
            return parent.parent
    return None


def is_meaningful_value(value: str) -> bool:
    stripped = value.strip().strip('"').strip("'")
    return bool(
        stripped
        and stripped.lower() not in {"pending", "todo", "tbd", "unknown", "未确认", "待确认"}
        and not PLACEHOLDER_PATTERN.search(stripped)
    )


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


def validate_sql_checkpoint_document(path: Path) -> list[str]:
    errors, _ = validate_stage_document(
        path,
        "full",
        "technical_design",
        require_completed=False,
    )
    if not path.is_file():
        return errors
    text = path.read_text(encoding="utf-8")
    empty_sections = [
        heading
        for heading in TECHNICAL_DESIGN_PRE_SQL_HEADINGS
        if heading in text and not section_has_substance(section_body(text, heading))
    ]
    if empty_sections:
        errors.append(
            "SQL 确认前的技术方案章节缺少实质内容: " + ", ".join(empty_sections)
        )
    errors.extend(validate_traceability(path, "full", "technical_design", text))
    return errors


def extract_requirement_ids(text: str) -> set[str]:
    _headers, rows = find_markdown_table(
        text,
        ("需求 ID", "来源 Sxx/Qxx", "状态"),
    )
    return {
        value
        for row in rows
        for value in [table_value(row, "需求 ID")]
        if re.fullmatch(r"R\d+", value)
    }


def extract_requirement_questions_for_research(text: str) -> set[str]:
    """Keep transferred code facts visible so changing a Qxx status cannot erase work."""
    _headers, rows = find_markdown_table(
        text,
        ("问题 ID", "问题类型", "确认人/承接阶段", "状态"),
    )
    transferred: set[str] = set()
    for row in rows:
        question_id = table_value(row, "问题 ID")
        question_type = table_value(row, "问题类型")
        owner = table_value(row, "确认人/承接阶段")
        status = table_value(row, "状态")
        if (
            re.fullmatch(r"Q\d+", question_id)
            and question_type == "代码事实"
            and status == "转下游"
            and re.search(r"仓库|代码|调研", owner)
        ):
            transferred.add(question_id)
    return transferred


def validate_requirement_traceability(
    text: str,
    mode: str,
    frontmatter: dict[str, str],
) -> list[str]:
    """Validate the Sxx -> Rxx/Qxx -> acceptance chain used as downstream truth."""
    errors: list[str] = []

    material_headers, material_rows = find_markdown_table(
        text,
        ("来源 ID", "原始要点", "处理结果", "对应 Rxx/Qxx"),
    )
    if not material_headers:
        errors.append("00-requirement.md 缺少原始材料要点覆盖表")
        material_rows = []
    if not material_rows:
        errors.append("00-requirement.md 原始材料要点覆盖表没有已填写的 Sxx")

    source_ids: list[str] = []
    material_refs: list[tuple[str, str, set[str], set[str]]] = []
    for index, row in enumerate(material_rows, start=1):
        source_id = table_value(row, "来源 ID")
        outcome = table_value(row, "处理结果")
        refs_value = table_value(row, "对应 Rxx/Qxx")
        r_refs = referenced_ids(refs_value, "R")
        q_refs = referenced_ids(refs_value, "Q")
        if not re.fullmatch(r"S\d+", source_id):
            errors.append(f"00-requirement.md 原始材料第 {index} 行缺少合法 Sxx")
            continue
        source_ids.append(source_id)
        if not table_value(row, "原始要点"):
            errors.append(f"00-requirement.md {source_id} 缺少原始要点")
        if outcome not in {"形成需求", "形成疑问", "明确不适用"}:
            errors.append(
                f"00-requirement.md {source_id} 处理结果必须是形成需求/形成疑问/明确不适用"
            )
        if outcome == "形成需求" and not r_refs:
            errors.append(f"00-requirement.md {source_id} 形成需求但未引用 Rxx")
        if outcome == "形成疑问" and not q_refs:
            errors.append(f"00-requirement.md {source_id} 形成疑问但未引用 Qxx")
        if outcome == "明确不适用" and not table_value(row, "处理说明"):
            errors.append(f"00-requirement.md {source_id} 明确不适用时必须说明原因")
        material_refs.append((source_id, outcome, r_refs, q_refs))
    for source_id in duplicate_ids(source_ids):
        errors.append(f"00-requirement.md 来源 ID 重复: {source_id}")

    requirement_headers, requirement_rows = find_markdown_table(
        text,
        ("需求 ID", "来源 Sxx/Qxx", "状态"),
    )
    if not requirement_headers:
        errors.append("00-requirement.md 缺少正式需求基线表")
        requirement_rows = []
    if not requirement_rows:
        errors.append("00-requirement.md 正式需求基线没有已填写的 Rxx")

    requirement_ids: list[str] = []
    requirement_sources: dict[str, tuple[set[str], set[str]]] = {}
    for index, row in enumerate(requirement_rows, start=1):
        requirement_id = table_value(row, "需求 ID")
        source_value = table_value(row, "来源 Sxx/Qxx")
        status = table_value(row, "状态")
        if not re.fullmatch(r"R\d+", requirement_id):
            errors.append(f"00-requirement.md 正式需求第 {index} 行缺少合法 Rxx")
            continue
        requirement_ids.append(requirement_id)
        s_refs = referenced_ids(source_value, "S")
        q_refs = referenced_ids(source_value, "Q")
        requirement_sources[requirement_id] = (s_refs, q_refs)
        if not s_refs and not q_refs:
            errors.append(f"00-requirement.md {requirement_id} 缺少 Sxx/Qxx 来源")
        if status != "已确认":
            errors.append(f"00-requirement.md {requirement_id} 状态必须为已确认")
        conclusion_headers = (
            ("已确认业务结论", "已确认边界/规则")
            if mode in {"full", "quick"}
            else ()
        )
        if not any(table_value(row, header) for header in conclusion_headers):
            errors.append(f"00-requirement.md {requirement_id} 缺少实质业务结论")
    for requirement_id in duplicate_ids(requirement_ids):
        errors.append(f"00-requirement.md 需求 ID 重复: {requirement_id}")

    question_headers, question_rows = find_markdown_table(
        text,
        (
            "问题 ID",
            "优先级",
            "问题类型",
            "准确来源 Sxx",
            "确认人/承接阶段",
            "确认结论/转交说明",
            "状态",
        ),
    )
    if not question_headers:
        errors.append("00-requirement.md 缺少 Qxx 疑问台账")
        question_rows = []

    source_id_set = set(source_ids)
    requirement_id_set = set(requirement_ids)
    question_ids: list[str] = []
    question_states: dict[str, str] = {}
    open_counts = {"P0": 0, "P1": 0, "P2": 0}
    for index, row in enumerate(question_rows, start=1):
        question_id = table_value(row, "问题 ID")
        priority = table_value(row, "优先级")
        question_type = table_value(row, "问题类型")
        source_value = table_value(row, "准确来源 Sxx")
        owner = table_value(row, "确认人/承接阶段")
        result = table_value(row, "确认结论/转交说明")
        status = table_value(row, "状态")
        if not re.fullmatch(r"Q\d+", question_id):
            errors.append(f"00-requirement.md 疑问第 {index} 行缺少合法 Qxx")
            continue
        question_ids.append(question_id)
        question_states[question_id] = status
        if priority not in open_counts:
            errors.append(f"00-requirement.md {question_id} 优先级必须是 P0/P1/P2")
        if question_type not in REQUIREMENT_QUESTION_TYPES:
            errors.append(f"00-requirement.md {question_id} 问题类型非法")
        source_refs = referenced_ids(source_value, "S")
        if not source_refs:
            errors.append(f"00-requirement.md {question_id} 准确来源必须引用 Sxx")
        for source_ref in sorted(source_refs - source_id_set):
            errors.append(f"00-requirement.md {question_id} 引用了不存在的来源: {source_ref}")
        if status not in REQUIREMENT_QUESTION_STATUSES:
            errors.append(f"00-requirement.md {question_id} 状态非法")
        if status == "待确认" and priority in open_counts:
            open_counts[priority] += 1
        if status in {"已确认", "已关闭", "转下游"} and not result:
            errors.append(f"00-requirement.md {question_id} 缺少确认结论或转交说明")
        if question_type == "用户意图" and status == "转下游":
            errors.append(f"00-requirement.md {question_id} 用户意图问题不得转下游")
        if status == "转下游":
            if question_type == "代码事实" and not re.search(r"仓库|代码|调研", owner):
                errors.append(f"00-requirement.md {question_id} 代码事实必须转交仓库调研")
            if question_type == "设计选择" and "设计" not in owner:
                errors.append(f"00-requirement.md {question_id} 设计选择必须转交技术设计")
    for question_id in duplicate_ids(question_ids):
        errors.append(f"00-requirement.md 问题 ID 重复: {question_id}")

    question_id_set = set(question_ids)
    for source_id, _outcome, r_refs, q_refs in material_refs:
        for ref in sorted(r_refs - requirement_id_set):
            errors.append(f"00-requirement.md {source_id} 引用了不存在的需求: {ref}")
        for ref in sorted(q_refs - question_id_set):
            errors.append(f"00-requirement.md {source_id} 引用了不存在的问题: {ref}")

    for requirement_id, (s_refs, q_refs) in requirement_sources.items():
        for ref in sorted(s_refs - source_id_set):
            errors.append(f"00-requirement.md {requirement_id} 引用了不存在的来源: {ref}")
        for ref in sorted(q_refs - question_id_set):
            errors.append(f"00-requirement.md {requirement_id} 引用了不存在的问题: {ref}")
        for ref in sorted(q_refs & question_id_set):
            if question_states.get(ref) not in {"已确认", "已关闭"}:
                errors.append(
                    f"00-requirement.md {requirement_id} 不能引用尚未确认的问题 {ref} 作为需求事实"
                )

    acceptance_headers = (
        ("需求 ID", "场景", "预期结果", "验证方式")
        if mode == "full"
        else ("需求 ID", "前置/输入", "用户可见结果", "最小验证信号")
    )
    found_headers, acceptance_rows = find_markdown_table(text, acceptance_headers)
    if not found_headers:
        errors.append("00-requirement.md 缺少可追溯验收表")
        acceptance_rows = []
    covered_requirements: set[str] = set()
    for index, row in enumerate(acceptance_rows, start=1):
        row_ids = referenced_ids(table_value(row, "需求 ID"), "R")
        if not row_ids:
            errors.append(f"00-requirement.md 验收第 {index} 行缺少 Rxx")
        covered_requirements.update(row_ids)
    missing_acceptance = sorted(requirement_id_set - covered_requirements)
    unknown_acceptance = sorted(covered_requirements - requirement_id_set)
    if missing_acceptance:
        errors.append("00-requirement.md 验收遗漏需求: " + ", ".join(missing_acceptance))
    if unknown_acceptance:
        errors.append("00-requirement.md 验收引用未知需求: " + ", ".join(unknown_acceptance))

    for priority, key in (
        ("P0", "blocking_p0_count"),
        ("P1", "open_p1_count"),
        ("P2", "open_p2_count"),
    ):
        try:
            actual = int(frontmatter.get(key, ""))
        except ValueError:
            continue
        if actual != open_counts[priority]:
            errors.append(
                f"00-requirement.md {key}={actual}，但 Qxx 台账实际为 {open_counts[priority]}"
            )

    if frontmatter.get("confirmation_status") != "confirmed":
        errors.append("00-requirement.md 未完成最终反向确认")
    if not is_meaningful_value(frontmatter.get("confirmation_source", "")):
        errors.append("00-requirement.md 缺少可回查的最终确认来源")
    return errors


def validate_local_evidence(
    artifact_path: Path,
    repository: str,
    location: str,
    locator: str,
    evidence_id: str,
) -> list[str]:
    """Reject plausible-looking path:line citations that cannot be opened locally."""
    errors: list[str] = []
    project_root = artifact_project_root(artifact_path)
    if project_root is None:
        return [f"01-research.md {evidence_id} 无法确定本地项目根目录"]

    raw_location = location.strip().strip("`")
    embedded_line = ""
    match = re.fullmatch(r"(.+):(\d+(?:-\d+)?)", raw_location)
    if match:
        raw_location = match.group(1)
        embedded_line = match.group(2)
    raw_location = raw_location.split("#", 1)[0].strip()
    if not raw_location:
        return [f"01-research.md {evidence_id} 本地源码证据缺少文件路径"]

    location_path = Path(raw_location)
    candidates: list[Path] = []
    if location_path.is_absolute():
        candidates.append(location_path)
    else:
        candidates.append(project_root / location_path)
        if repository:
            candidates.append(project_root.parent / repository / location_path)
    resolved = next((candidate for candidate in candidates if candidate.is_file()), None)
    if resolved is None:
        errors.append(
            f"01-research.md {evidence_id} 本地源码文件不存在: {raw_location}"
        )
        return errors

    effective_locator = locator.strip() or embedded_line
    line_match = re.fullmatch(r"(\d+)(?:-(\d+))?", effective_locator)
    if not line_match:
        errors.append(f"01-research.md {evidence_id} 本地源码证据缺少有效行号")
        return errors
    start = int(line_match.group(1))
    end = int(line_match.group(2) or line_match.group(1))
    line_count = len(resolved.read_text(encoding="utf-8").splitlines())
    if start < 1 or end < start or end > line_count:
        errors.append(
            f"01-research.md {evidence_id} 行号越界: {effective_locator}，文件共 {line_count} 行"
        )
    return errors


def validate_research_traceability(
    path: Path,
    text: str,
    frontmatter: dict[str, str],
) -> list[str]:
    """Close requirement, repository, claim, evidence and stage-transfer references."""
    errors: list[str] = []
    requirement_path = path.parent / "00-requirement.md"
    requirement_text = (
        requirement_path.read_text(encoding="utf-8")
        if requirement_path.is_file()
        else ""
    )
    expected_requirement_ids = extract_requirement_ids(requirement_text)
    if not expected_requirement_ids:
        errors.append("01-research.md 无法从 00-requirement.md 取得有效 Rxx")

    claim_headers, claim_rows = find_markdown_table(
        text,
        (
            "结论 ID",
            "结论",
            "证据 ID",
            "证据等级",
            "代码位置",
            "反证",
            "覆盖度",
            "置信度",
            "运行时缺口",
            "待验证动作",
        ),
    )
    if not claim_headers:
        errors.append("01-research.md 缺少完整 Claim Ledger")
        claim_rows = []
    if not claim_rows:
        errors.append("01-research.md Claim Ledger 没有已填写的 Cxx")

    claim_ids: list[str] = []
    claim_evidence_refs: dict[str, set[str]] = {}
    claim_levels: dict[str, str] = {}
    claim_confidence: dict[str, str] = {}
    for index, row in enumerate(claim_rows, start=1):
        claim_id = table_value(row, "结论 ID")
        if not re.fullmatch(r"C\d+", claim_id):
            errors.append(f"01-research.md Claim Ledger 第 {index} 行缺少合法 Cxx")
            continue
        claim_ids.append(claim_id)
        evidence_refs = referenced_ids(table_value(row, "证据 ID"), "E")
        claim_evidence_refs[claim_id] = evidence_refs
        level = table_value(row, "证据等级")
        confidence = table_value(row, "置信度")
        claim_levels[claim_id] = level
        claim_confidence[claim_id] = confidence
        if not table_value(row, "结论"):
            errors.append(f"01-research.md {claim_id} 缺少结论")
        if not evidence_refs:
            errors.append(f"01-research.md {claim_id} 至少引用一个 Exx")
        if level not in EVIDENCE_LEVELS:
            errors.append(f"01-research.md {claim_id} 证据等级非法: {level}")
        if confidence not in {"高", "中", "低"}:
            errors.append(f"01-research.md {claim_id} 置信度必须是高/中/低")
        if level == "Proven" and not table_value(row, "代码位置"):
            errors.append(f"01-research.md {claim_id} Proven 结论缺少代码或运行位置")
    for claim_id in duplicate_ids(claim_ids):
        errors.append(f"01-research.md 结论 ID 重复: {claim_id}")
    claim_id_set = set(claim_ids)

    evidence_headers, evidence_rows = find_markdown_table(
        text,
        (
            "证据 ID",
            "证据类型",
            "仓库",
            "文件/符号/运行证据",
            "行号/定位",
            "支持结论",
            "限制",
        ),
    )
    if not evidence_headers:
        errors.append("01-research.md 缺少完整证据索引")
        evidence_rows = []
    if not evidence_rows:
        errors.append("01-research.md 证据索引没有已填写的 Exx")

    evidence_ids: list[str] = []
    evidence_types: dict[str, str] = {}
    evidence_claim_refs: dict[str, set[str]] = {}
    for index, row in enumerate(evidence_rows, start=1):
        evidence_id = table_value(row, "证据 ID")
        if not re.fullmatch(r"E\d+", evidence_id):
            errors.append(f"01-research.md 证据索引第 {index} 行缺少合法 Exx")
            continue
        evidence_ids.append(evidence_id)
        evidence_type = table_value(row, "证据类型")
        evidence_types[evidence_id] = evidence_type
        if evidence_type not in EVIDENCE_TYPES:
            errors.append(f"01-research.md {evidence_id} 证据类型非法: {evidence_type}")
        supported_claims = referenced_ids(table_value(row, "支持结论"), "C")
        evidence_claim_refs[evidence_id] = supported_claims
        if not supported_claims:
            errors.append(f"01-research.md {evidence_id} 未声明支持的 Cxx")
        for claim_id in sorted(supported_claims - claim_id_set):
            errors.append(f"01-research.md {evidence_id} 支持不存在的结论: {claim_id}")
        if evidence_type == "本地源码":
            errors.extend(
                validate_local_evidence(
                    path,
                    table_value(row, "仓库"),
                    table_value(row, "文件/符号/运行证据"),
                    table_value(row, "行号/定位"),
                    evidence_id,
                )
            )
        elif not table_value(row, "文件/符号/运行证据"):
            errors.append(f"01-research.md {evidence_id} 缺少证据定位")
    for evidence_id in duplicate_ids(evidence_ids):
        errors.append(f"01-research.md 证据 ID 重复: {evidence_id}")
    evidence_id_set = set(evidence_ids)

    for claim_id, evidence_refs in claim_evidence_refs.items():
        for evidence_id in sorted(evidence_refs - evidence_id_set):
            errors.append(f"01-research.md {claim_id} 引用了不存在的证据: {evidence_id}")
        for evidence_id in sorted(evidence_refs & evidence_id_set):
            if claim_id not in evidence_claim_refs.get(evidence_id, set()):
                errors.append(
                    f"01-research.md {claim_id} 引用 {evidence_id}，但证据索引未声明支持该结论"
                )
        if claim_confidence.get(claim_id) == "高":
            strong_types = {
                evidence_types.get(evidence_id)
                for evidence_id in evidence_refs
            }
            if claim_levels.get(claim_id) != "Proven" or not (
                strong_types & {"本地源码", "远程源码", "运行证据", "数据库", "日志/Trace"}
            ):
                errors.append(
                    f"01-research.md {claim_id} 高置信结论缺少 Proven 源码或运行证据"
                )
    for evidence_id, supported_claims in evidence_claim_refs.items():
        for claim_id in sorted(supported_claims & claim_id_set):
            if evidence_id not in claim_evidence_refs.get(claim_id, set()):
                errors.append(
                    f"01-research.md {evidence_id} 声明支持 {claim_id}，但 Claim Ledger 未引用该证据"
                )

    validation_headers, validation_rows = find_markdown_table(
        text,
        ("需求 ID", "需求主张", "代码验证问题", "验证状态", "结论 ID", "证据 ID", "风险/RQxx"),
    )
    if not validation_headers:
        errors.append("01-research.md 缺少需求验证矩阵")
        validation_rows = []
    actual_requirement_ids: list[str] = []
    for index, row in enumerate(validation_rows, start=1):
        requirement_id = table_value(row, "需求 ID")
        if not re.fullmatch(r"R\d+", requirement_id):
            errors.append(f"01-research.md 需求验证第 {index} 行缺少合法 Rxx")
            continue
        actual_requirement_ids.append(requirement_id)
        status = table_value(row, "验证状态")
        c_refs = referenced_ids(table_value(row, "结论 ID"), "C")
        e_refs = referenced_ids(table_value(row, "证据 ID"), "E")
        rq_refs = referenced_ids(table_value(row, "风险/RQxx"), "RQ")
        if status not in {"已验证", "部分验证", "未覆盖", "阻塞"}:
            errors.append(f"01-research.md {requirement_id} 验证状态非法")
        if status in {"未覆盖", "阻塞"}:
            errors.append(f"01-research.md {requirement_id} 尚未完成验证: {status}")
        if not c_refs or not e_refs:
            errors.append(f"01-research.md {requirement_id} 缺少 Cxx/Exx")
        if status == "部分验证" and not rq_refs:
            errors.append(f"01-research.md {requirement_id} 部分验证时必须引用 RQxx")
        for claim_id in sorted(c_refs - claim_id_set):
            errors.append(f"01-research.md {requirement_id} 引用了不存在的结论: {claim_id}")
        for evidence_id in sorted(e_refs - evidence_id_set):
            errors.append(f"01-research.md {requirement_id} 引用了不存在的证据: {evidence_id}")
    for requirement_id in duplicate_ids(actual_requirement_ids):
        errors.append(f"01-research.md 需求验证重复: {requirement_id}")
    actual_requirement_id_set = set(actual_requirement_ids)
    missing_requirements = sorted(expected_requirement_ids - actual_requirement_id_set)
    unknown_requirements = sorted(actual_requirement_id_set - expected_requirement_ids)
    if missing_requirements:
        errors.append("01-research.md 需求验证遗漏: " + ", ".join(missing_requirements))
    if unknown_requirements:
        errors.append("01-research.md 需求验证引用未知需求: " + ", ".join(unknown_requirements))

    repo_headers, repo_rows = find_markdown_table(
        text,
        ("仓库", "角色", "分类", "判断依据", "结论 ID", "证据 ID", "置信度"),
    )
    if not repo_headers:
        errors.append("01-research.md 缺少权威仓库分类表")
        repo_rows = []
    if not repo_rows:
        errors.append("01-research.md 权威仓库分类表为空")
    repositories: list[str] = []
    for index, row in enumerate(repo_rows, start=1):
        repository = table_value(row, "仓库")
        classification = table_value(row, "分类")
        if not repository:
            errors.append(f"01-research.md 仓库分类第 {index} 行缺少仓库名")
            continue
        repositories.append(repository)
        if classification not in {
            "Must change",
            "May change",
            "No code change",
            "Runtime/config only",
            "Unknown",
        }:
            errors.append(f"01-research.md {repository} 仓库分类非法: {classification}")
        if classification == "Unknown" and not referenced_ids(
            table_value(row, "判断依据"), "RQ"
        ):
            errors.append(f"01-research.md {repository} 为 Unknown 时必须引用 RQxx")
        if not referenced_ids(table_value(row, "结论 ID"), "C"):
            errors.append(f"01-research.md {repository} 仓库分类缺少 Cxx")
        if not referenced_ids(table_value(row, "证据 ID"), "E"):
            errors.append(f"01-research.md {repository} 仓库分类缺少 Exx")
    for repository in duplicate_ids(repositories):
        errors.append(f"01-research.md 仓库分类重复: {repository}")

    scope_headers, scope_rows = find_markdown_table(
        text,
        ("仓库", "变更对象/排除范围", "结论/证据"),
    )
    if not scope_headers:
        errors.append("01-research.md 缺少每仓 ChangeScope 表")
        scope_rows = []
    scope_repositories = {
        table_value(row, "仓库")
        for row in scope_rows
        if table_value(row, "仓库")
    }
    missing_scopes = sorted(set(repositories) - scope_repositories)
    extra_scopes = sorted(scope_repositories - set(repositories))
    if missing_scopes:
        errors.append("01-research.md 缺少每仓 ChangeScope: " + ", ".join(missing_scopes))
    if extra_scopes:
        errors.append("01-research.md ChangeScope 引用未知仓库: " + ", ".join(extra_scopes))
    for row in scope_rows:
        repository = table_value(row, "仓库") or "未命名仓库"
        refs = table_value(row, "结论/证据")
        if not table_value(row, "变更对象/排除范围"):
            errors.append(f"01-research.md {repository} ChangeScope 缺少变更对象或排除范围")
        if not referenced_ids(refs, "C") or not referenced_ids(refs, "E"):
            errors.append(f"01-research.md {repository} ChangeScope 缺少 Cxx/Exx")

    question_headers, question_rows = find_markdown_table(
        text,
        (
            "问题 ID",
            "优先级",
            "问题类型",
            "来源 Qxx/Cxx/Exx",
            "Owner",
            "承接阶段",
            "状态",
            "影响与解锁动作",
        ),
    )
    if not question_headers:
        errors.append("01-research.md 缺少 RQxx 调研问题台账")
        question_rows = []
    research_question_ids: list[str] = []
    open_counts = {"P0": 0, "P1": 0, "P2": 0}
    for index, row in enumerate(question_rows, start=1):
        question_id = table_value(row, "问题 ID")
        priority = table_value(row, "优先级")
        question_type = table_value(row, "问题类型")
        source = table_value(row, "来源 Qxx/Cxx/Exx")
        owner = table_value(row, "Owner")
        next_stage = table_value(row, "承接阶段")
        status = table_value(row, "状态")
        if not re.fullmatch(r"RQ\d+", question_id):
            errors.append(f"01-research.md 调研问题第 {index} 行缺少合法 RQxx")
            continue
        research_question_ids.append(question_id)
        if priority not in open_counts:
            errors.append(f"01-research.md {question_id} 优先级必须是 P0/P1/P2")
        if question_type not in RESEARCH_QUESTION_TYPES:
            errors.append(f"01-research.md {question_id} 问题类型非法")
        if status not in RESEARCH_QUESTION_STATUSES:
            errors.append(f"01-research.md {question_id} 状态非法")
        if not (
            referenced_ids(source, "Q")
            or referenced_ids(source, "C")
            or referenced_ids(source, "E")
        ):
            errors.append(f"01-research.md {question_id} 缺少 Qxx/Cxx/Exx 来源")
        if status == "待处理" and priority in open_counts:
            open_counts[priority] += 1
        if not table_value(row, "影响与解锁动作"):
            errors.append(f"01-research.md {question_id} 缺少影响与解锁动作")
        if status == "转下游":
            if question_type == "用户意图" and "需求" not in next_stage:
                errors.append(f"01-research.md {question_id} 用户意图必须转回需求澄清")
            if question_type == "设计选择" and "设计" not in next_stage:
                errors.append(f"01-research.md {question_id} 设计选择必须转交技术设计")
            if not owner:
                errors.append(f"01-research.md {question_id} 转下游时缺少 Owner")
    for question_id in duplicate_ids(research_question_ids):
        errors.append(f"01-research.md 调研问题 ID 重复: {question_id}")
    research_question_id_set = set(research_question_ids)

    for transferred_question in sorted(
        extract_requirement_questions_for_research(requirement_text)
    ):
        if not re.search(rf"\b{re.escape(transferred_question)}\b", text):
            errors.append(
                f"01-research.md 未承接需求阶段转交的代码事实问题: {transferred_question}"
            )

    all_claim_refs = set(re.findall(r"\bC\d+\b", text))
    all_evidence_refs = set(re.findall(r"\bE\d+\b", text))
    all_research_question_refs = set(re.findall(r"\bRQ\d+\b", text))
    unknown_claim_refs = sorted(all_claim_refs - claim_id_set)
    unknown_evidence_refs = sorted(all_evidence_refs - evidence_id_set)
    unknown_question_refs = sorted(
        all_research_question_refs - research_question_id_set
    )
    if unknown_claim_refs:
        errors.append("01-research.md 引用了未定义的结论: " + ", ".join(unknown_claim_refs))
    if unknown_evidence_refs:
        errors.append("01-research.md 引用了未定义的证据: " + ", ".join(unknown_evidence_refs))
    if unknown_question_refs:
        errors.append("01-research.md 引用了未定义的调研问题: " + ", ".join(unknown_question_refs))

    for priority, key in (
        ("P0", "blocking_p0_count"),
        ("P1", "open_p1_count"),
        ("P2", "open_p2_count"),
    ):
        try:
            actual = int(frontmatter.get(key, ""))
        except ValueError:
            continue
        if actual != open_counts[priority]:
            errors.append(
                f"01-research.md {key}={actual}，但 RQxx 台账实际为 {open_counts[priority]}"
            )

    research_scope = frontmatter.get("research_scope", "")
    if research_scope not in RESEARCH_SCOPES:
        errors.append("01-research.md research_scope 必须是 focused/full")
    elif research_scope != "full":
        errors.append("完整仓库调研完成时 research_scope 必须为 full")
    for key, heading, required_headers in (
        (
            "shared_semantic_impact",
            "## 6. 共享语义反向影响",
            ("语义对象", "生产方", "持久化/传播", "消费方", "结论 ID", "证据 ID"),
        ),
        (
            "current_sql_impact",
            "## 7. 当前 SQL 事实与影响",
            ("SQL 事实 ID", "仓库与位置", "类型", "当前语义", "结论 ID", "证据 ID"),
        ),
    ):
        impact = frontmatter.get(key, "")
        if impact not in RESEARCH_IMPACTS:
            errors.append(f"01-research.md {key} 必须是 pending/none/involved")
            continue
        if impact == "pending":
            errors.append(f"01-research.md {key} 尚未完成判定")
            continue
        section = section_body(text, heading)
        basis_match = re.search(r"(?m)^-\s*判定依据[：:]\s*(.+)$", section)
        basis = basis_match.group(1) if basis_match else ""
        if (
            not referenced_ids(basis, "C")
            or not referenced_ids(basis, "E")
        ):
            errors.append(f"01-research.md {key} 判定依据必须引用 Cxx/Exx")
        _impact_headers, impact_rows = find_markdown_table(section, required_headers)
        if impact == "involved" and not impact_rows:
            errors.append(f"01-research.md {key}=involved 但影响矩阵为空")
        if impact == "none" and impact_rows:
            errors.append(f"01-research.md {key}=none 时不应保留影响矩阵数据行")
        sql_fact_ids: list[str] = []
        for row in impact_rows:
            c_refs = referenced_ids(table_value(row, "结论 ID"), "C")
            e_refs = referenced_ids(table_value(row, "证据 ID"), "E")
            if not c_refs or not e_refs:
                errors.append(f"01-research.md {key} 影响行缺少 Cxx/Exx")
            if key == "shared_semantic_impact":
                for header in ("语义对象", "生产方", "持久化/传播", "消费方"):
                    if not table_value(row, header):
                        errors.append(
                            f"01-research.md 共享语义影响行缺少{header}"
                        )
            else:
                sql_id = table_value(row, "SQL 事实 ID")
                if not re.fullmatch(r"SQL\d+", sql_id):
                    errors.append("01-research.md 当前 SQL 事实缺少合法 SQLxx")
                else:
                    sql_fact_ids.append(sql_id)
                sql_type = table_value(row, "类型")
                if sql_type not in {"SELECT", "INSERT", "UPDATE", "DELETE", "DDL"}:
                    errors.append(f"01-research.md {sql_id or 'SQL事实'} 类型非法: {sql_type}")
                for header in (
                    "仓库与位置",
                    "当前语义",
                    "JOIN/过滤/排序/分页/写入条件",
                    "可能受影响原因",
                    "是否交技术设计",
                ):
                    if not table_value(row, header):
                        errors.append(
                            f"01-research.md {sql_id or 'SQL事实'} 缺少{header}"
                        )
        if key == "current_sql_impact":
            for sql_id in duplicate_ids(sql_fact_ids):
                errors.append(f"01-research.md SQL 事实 ID 重复: {sql_id}")

    return errors


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
    if stage == "requirement_clarification":
        missing_keys.extend(
            sorted(REQUIREMENT_CONFIRMATION_KEYS - frontmatter.keys())
        )
    if mode == "full" and stage == "repo_research":
        missing_keys.extend(
            sorted(RESEARCH_SCOPE_KEYS - frontmatter.keys())
        )
    if mode == "full" and stage == "technical_design":
        missing_keys.extend(
            sorted(TECHNICAL_DESIGN_SQL_KEYS - frontmatter.keys())
        )
    if missing_keys:
        errors.append("frontmatter 缺少字段: " + ", ".join(missing_keys))
    if frontmatter.get("workflow") != "zstt-backend-workflow":
        errors.append("workflow 必须是 zstt-backend-workflow")
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

    if mode == "full" and stage == "technical_design":
        sql_impact = frontmatter.get("sql_impact", "")
        sql_gate_status = frontmatter.get("sql_gate_status", "")
        if sql_impact not in SQL_IMPACTS:
            errors.append(
                "frontmatter 的 sql_impact 必须是 pending/none/query_dml/ddl"
            )
        if sql_gate_status not in SQL_GATE_STATUSES:
            errors.append(
                "frontmatter 的 sql_gate_status 无效"
            )
        if require_completed:
            expected_status = "not_involved" if sql_impact == "none" else "confirmed"
            if sql_impact == "pending":
                errors.append("尚未完成 SQL 影响判定")
            elif sql_gate_status != expected_status:
                errors.append(
                    f"SQL Gate 尚未满足: {sql_impact}/{sql_gate_status}"
                )
            if not frontmatter.get("sql_fingerprint"):
                errors.append("frontmatter 缺少 SQL 指纹")
            if sql_impact in {"query_dml", "ddl"} and not frontmatter.get(
                "sql_confirmation_source"
            ):
                errors.append("frontmatter 缺少用户 SQL 确认来源")

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
        if stage == "requirement_clarification":
            errors.extend(
                validate_requirement_traceability(text, mode, frontmatter)
            )
        if mode == "full" and stage == "repo_research":
            errors.extend(
                validate_research_traceability(path, text, frontmatter)
            )
    return errors, frontmatter
