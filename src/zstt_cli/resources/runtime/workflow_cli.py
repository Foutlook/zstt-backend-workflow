from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

from workflow_contracts import (
    get_contract,
    recommended_next_skill,
    required_predecessors,
    stages_for,
)
from workflow_paths import feature_directory
from workflow_validation import (
    SQL_DESIGN_ARTIFACT,
    artifact_fingerprint,
    sql_gate_fingerprint,
    validate_sql_artifact,
    validate_sql_checkpoint_document,
    validate_stage_document,
)


SCRIPT_DIR = Path(__file__).resolve().parent
KIT_ROOT = SCRIPT_DIR.parent
TEMPLATE_ROOT = KIT_ROOT / "templates"
META_NAME = "meta.json"


def default_sql_gate() -> dict[str, object]:
    return {
        "status": "not_evaluated",
        "impact": "pending",
        "artifact": None,
        "fingerprint": None,
        "confirmation_source": None,
        "confirmed_at": None,
        "stale_reason": None,
    }


def read_meta(feature_dir: Path) -> dict[str, object]:
    meta_path = feature_dir / META_NAME
    if not meta_path.is_file():
        raise ValueError(f"状态文件不存在: {meta_path}")
    return json.loads(meta_path.read_text(encoding="utf-8"))


def write_meta(feature_dir: Path, meta: dict[str, object]) -> None:
    content = json.dumps(meta, ensure_ascii=False, indent=2) + "\n"
    (feature_dir / META_NAME).write_text(content, encoding="utf-8", newline="\n")


def render_template(template_path: Path, values: dict[str, str]) -> str:
    content = template_path.read_text(encoding="utf-8")
    for key, value in values.items():
        content = content.replace("{{" + key + "}}", value)
    return content


def replace_frontmatter_fields(path: Path, updates: dict[str, str]) -> None:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        raise ValueError(f"技术方案缺少 frontmatter: {path}")
    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        raise ValueError(f"技术方案 frontmatter 未闭合: {path}") from exc
    for key, value in updates.items():
        prefix = f"{key}:"
        for index in range(1, end):
            if lines[index].startswith(prefix):
                lines[index] = f"{key}: {value}"
                break
        else:
            lines.insert(end, f"{key}: {value}")
            end += 1
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def replace_design_field(path: Path, label: str, value: str) -> None:
    text = path.read_text(encoding="utf-8")
    pattern = re.compile(rf"^(\s*-\s*{re.escape(label)}[：:]).*$", re.MULTILINE)
    if pattern.search(text):
        text = pattern.sub(lambda match: f"{match.group(1)} {value}", text, count=1)
    else:
        heading = "## 7. 数据存储与查询设计"
        if heading not in text:
            raise ValueError(f"技术方案缺少章节: {heading}")
        text = text.replace(heading, f"{heading}\n\n- {label}：{value}", 1)
    path.write_text(text, encoding="utf-8", newline="\n")


def update_design_sql_gate(
    path: Path,
    *,
    impact: str,
    status: str,
    fingerprint: str,
    source: str,
) -> None:
    replace_frontmatter_fields(
        path,
        {
            "sql_impact": impact,
            "sql_gate_status": status,
            "sql_fingerprint": fingerprint,
            "sql_confirmation_source": (
                json.dumps(source, ensure_ascii=False) if source else ""
            ),
        },
    )
    replace_design_field(path, "SQL 影响类型", impact)
    replace_design_field(path, "SQL Gate 状态", status)
    replace_design_field(path, "SQL 指纹", fingerprint)
    replace_design_field(path, "用户确认来源", source)


def sql_gate_from_meta(meta: dict[str, object]) -> dict[str, object]:
    raw = meta.get("sql_gate")
    return dict(raw) if isinstance(raw, dict) else default_sql_gate()


def sql_gate_is_stale(feature_dir: Path, meta: dict[str, object]) -> bool:
    gate = sql_gate_from_meta(meta)
    status = str(gate.get("status", "not_evaluated"))
    if status == "stale":
        return True
    if status not in {"not_involved", "confirmed"}:
        return False
    current = sql_gate_fingerprint(feature_dir / "02-design.md")
    return not current or current != gate.get("fingerprint")


def mark_sql_gate_stale(meta: dict[str, object], reason: str) -> None:
    gate = sql_gate_from_meta(meta)
    gate["status"] = "stale"
    gate["stale_reason"] = reason
    meta["sql_gate"] = gate


def validate_sql_gate_for_completion(
    feature_dir: Path,
    meta: dict[str, object],
    frontmatter: dict[str, str],
) -> None:
    gate = sql_gate_from_meta(meta)
    impact = str(gate.get("impact", "pending"))
    status = str(gate.get("status", "not_evaluated"))
    expected = "not_involved" if impact == "none" else "confirmed"
    if impact not in {"none", "query_dml", "ddl"} or status != expected:
        raise ValueError(
            f"SQL Gate 尚未满足: impact={impact}, status={status}；"
            "先执行 prepare-sql-gate，涉及 SQL 时等待用户确认后再执行 confirm-sql"
        )
    if frontmatter.get("sql_impact") != impact:
        raise ValueError("02-design.md 与 meta.json 的 SQL 影响类型不一致")
    if frontmatter.get("sql_gate_status") != status:
        raise ValueError("02-design.md 与 meta.json 的 SQL Gate 状态不一致")
    if frontmatter.get("sql_fingerprint") != gate.get("fingerprint"):
        raise ValueError("02-design.md 与 meta.json 的 SQL 指纹不一致")
    if impact != "none" and frontmatter.get("sql_confirmation_source") != gate.get(
        "confirmation_source"
    ):
        raise ValueError("02-design.md 与 meta.json 的用户 SQL 确认来源不一致")
    artifact_errors = validate_sql_artifact(feature_dir / "02-design.md", impact)
    raise_for_errors(artifact_errors)
    current = sql_gate_fingerprint(feature_dir / "02-design.md")
    if not current or current != gate.get("fingerprint"):
        mark_sql_gate_stale(meta, "SQL 设计或确认范围在门禁后发生变化")
        write_meta(feature_dir, meta)
        raise ValueError(
            "SQL 设计已在确认后变化，SQL Gate 已失效，必须重新确认"
        )


def init_feature(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    date_text = args.date or date.today().strftime("%Y%m%d")
    target = feature_directory(repo_root, args.mode, args.feature_name, date_text)
    if target.exists():
        raise FileExistsError(f"需求目录已存在，拒绝覆盖: {target}")

    requirement = get_contract(args.mode, "requirement_clarification")
    template_path = TEMPLATE_ROOT / args.mode / requirement.artifact
    content = render_template(
        template_path,
        {
            "FEATURE_NAME": args.feature_name.strip(),
            "CREATED_DATE": date_text,
        },
    )

    target.mkdir(parents=True)
    (target / requirement.artifact).write_text(
        content,
        encoding="utf-8",
        newline="\n",
    )
    meta: dict[str, object] = {
        "version": 3,
        "workflow": "zstt-backend-workflow",
        "mode": args.mode,
        "feature_name": args.feature_name.strip(),
        "feature_dir": str(target),
        "created_date": date_text,
        "current_stage": requirement.key,
        "completed_stages": [],
        "artifacts": {requirement.key: requirement.artifact},
        "artifact_fingerprints": {},
        "blocking_counts": {"p0": 0, "p1": 0, "p2": 0},
        "last_validation": None,
        "recommended_next_skill": requirement.skill,
    }
    if args.mode == "full":
        meta["sql_gate"] = default_sql_gate()
    write_meta(target, meta)
    print(str(target))
    return 0


def show_status(args: argparse.Namespace) -> int:
    feature_dir = Path(args.feature_dir).resolve()
    meta = read_meta(feature_dir)
    status = dict(meta)
    status["stale_stages"] = changed_completed_stages(feature_dir, meta)
    if str(meta.get("mode")) == "full":
        gate = sql_gate_from_meta(meta)
        gate["effective_status"] = (
            "stale" if sql_gate_is_stale(feature_dir, meta) else gate["status"]
        )
        status["sql_gate"] = gate
    print(json.dumps(status, ensure_ascii=False, indent=2))
    return 0


def raise_for_errors(errors: list[str]) -> None:
    if errors:
        raise ValueError("；".join(errors))


def validate_stage(args: argparse.Namespace) -> int:
    feature_dir = Path(args.feature_dir).resolve()
    meta = read_meta(feature_dir)
    mode = str(meta["mode"])
    contract = get_contract(mode, args.stage)
    errors, frontmatter = validate_stage_document(
        feature_dir / contract.artifact,
        mode,
        contract.key,
    )
    raise_for_errors(errors)
    if mode == "full" and contract.key == "technical_design":
        validate_sql_gate_for_completion(feature_dir, meta, frontmatter)
    print(json.dumps({"stage": contract.key, "valid": True}, ensure_ascii=False))
    return 0


def changed_completed_stages(
    feature_dir: Path,
    meta: dict[str, object],
) -> list[str]:
    completed = list(meta.get("completed_stages", []))
    artifacts = dict(meta.get("artifacts", {}))
    fingerprints = dict(meta.get("artifact_fingerprints", {}))
    mode = str(meta["mode"])
    changed: list[str] = []
    for stage in completed:
        contract = get_contract(mode, stage)
        artifact_name = str(artifacts.get(stage, contract.artifact))
        current = artifact_fingerprint(feature_dir / artifact_name)
        if not current or fingerprints.get(stage) != current:
            changed.append(stage)
    if (
        mode == "full"
        and "technical_design" in completed
        and sql_gate_is_stale(feature_dir, meta)
        and "technical_design" not in changed
    ):
        changed.append("technical_design")
    return changed


def invalidate_changed_stages(
    feature_dir: Path,
    meta: dict[str, object],
) -> tuple[str | None, list[str]]:
    changed = changed_completed_stages(feature_dir, meta)
    if not changed:
        return None, []

    mode = str(meta["mode"])
    stage_order = [stage.key for stage in stages_for(mode)]
    earliest = min(changed, key=stage_order.index)
    earliest_index = stage_order.index(earliest)
    sql_gate_was_stale = (
        sql_gate_is_stale(feature_dir, meta) if mode == "full" else False
    )
    completed = list(meta.get("completed_stages", []))
    invalidated = [stage for stage in completed if stage_order.index(stage) >= earliest_index]
    meta["completed_stages"] = [stage for stage in completed if stage not in invalidated]

    # 已完成产物一旦改变，旧指纹和所有下游完成结论都不再可信。
    fingerprints = dict(meta.get("artifact_fingerprints", {}))
    for stage in invalidated:
        fingerprints.pop(stage, None)
    meta["artifact_fingerprints"] = fingerprints
    meta["current_stage"] = earliest
    meta["recommended_next_skill"] = get_contract(mode, earliest).skill
    if mode == "full":
        technical_index = stage_order.index("technical_design")
        gate = sql_gate_from_meta(meta)
        if gate.get("status") in {"not_involved", "confirmed"} and (
            earliest_index < technical_index or sql_gate_was_stale
        ):
            mark_sql_gate_stale(meta, "SQL 依据或已确认 SQL 设计发生变化")
    remaining = list(meta["completed_stages"])
    if remaining:
        last_contract = get_contract(mode, remaining[-1])
        _, frontmatter = validate_stage_document(
            feature_dir / last_contract.artifact,
            mode,
            last_contract.key,
        )
        meta["blocking_counts"] = {
            "p0": int(frontmatter["blocking_p0_count"]),
            "p1": int(frontmatter["open_p1_count"]),
            "p2": int(frontmatter["open_p2_count"]),
        }
    else:
        # 没有已验证阶段时，计数只表示“无有效门禁快照”，真实问题以当前文档校验为准。
        meta["blocking_counts"] = {"p0": 0, "p1": 0, "p2": 0}
    meta["last_validation"] = {
        "stage": earliest,
        "valid": False,
        "kind": "artifact_changed",
        "changed_stages": changed,
        "invalidated_stages": invalidated,
    }
    write_meta(feature_dir, meta)
    return earliest, invalidated


def changed_stage_error(
    feature_dir: Path,
    meta: dict[str, object],
    earliest: str,
    invalidated: list[str],
) -> ValueError:
    mode = str(meta["mode"])
    contract = get_contract(mode, earliest)
    errors, _ = validate_stage_document(
        feature_dir / contract.artifact,
        mode,
        earliest,
    )
    detail = "；当前文档校验通过，但仍需用户确认并重新完成该阶段"
    if errors:
        detail = "；当前文档还存在问题: " + "；".join(errors)
    return ValueError(
        "上游已完成产物已修改，已撤销相关完成状态: "
        + ", ".join(invalidated)
        + f"；请重新执行阶段 {earliest} 的 complete-stage"
        + detail
    )


def complete_stage(args: argparse.Namespace) -> int:
    feature_dir = Path(args.feature_dir).resolve()
    meta = read_meta(feature_dir)
    mode = str(meta["mode"])
    contract = get_contract(mode, args.stage)
    earliest_changed, invalidated = invalidate_changed_stages(feature_dir, meta)
    if earliest_changed and earliest_changed != contract.key:
        raise changed_stage_error(feature_dir, meta, earliest_changed, invalidated)
    completed = list(meta.get("completed_stages", []))
    missing_predecessors = [
        stage
        for stage in required_predecessors(mode, contract.key)
        if stage not in completed
    ]
    if missing_predecessors:
        raise ValueError("前置阶段尚未完成: " + ", ".join(missing_predecessors))

    errors, frontmatter = validate_stage_document(
        feature_dir / contract.artifact,
        mode,
        contract.key,
    )
    raise_for_errors(errors)
    if mode == "full" and contract.key == "technical_design":
        validate_sql_gate_for_completion(feature_dir, meta, frontmatter)
    if contract.key not in completed:
        completed.append(contract.key)

    meta["current_stage"] = contract.key
    meta["completed_stages"] = completed
    artifacts = dict(meta.get("artifacts", {}))
    artifacts[contract.key] = contract.artifact
    meta["artifacts"] = artifacts
    fingerprints = dict(meta.get("artifact_fingerprints", {}))
    fingerprints[contract.key] = artifact_fingerprint(feature_dir / contract.artifact)
    meta["artifact_fingerprints"] = fingerprints
    meta["blocking_counts"] = {
        "p0": int(frontmatter["blocking_p0_count"]),
        "p1": int(frontmatter["open_p1_count"]),
        "p2": int(frontmatter["open_p2_count"]),
    }
    meta["last_validation"] = {"stage": contract.key, "valid": True}
    meta["recommended_next_skill"] = recommended_next_skill(mode, completed)
    write_meta(feature_dir, meta)
    print(json.dumps(meta, ensure_ascii=False, indent=2))
    return 0


def validate_predecessors(
    feature_dir: Path,
    meta: dict[str, object],
    target_stage: str,
) -> None:
    mode = str(meta["mode"])
    completed = list(meta.get("completed_stages", []))
    predecessors = required_predecessors(mode, target_stage)
    missing = [stage for stage in predecessors if stage not in completed]
    if missing:
        raise ValueError("前置阶段尚未完成: " + ", ".join(missing))

    artifacts = dict(meta.get("artifacts", {}))
    for stage in predecessors:
        contract = get_contract(mode, stage)
        artifact_name = str(artifacts.get(stage, contract.artifact))
        errors, _ = validate_stage_document(
            feature_dir / artifact_name,
            mode,
            stage,
        )
        if errors:
            raise ValueError(f"上游阶段 {stage} 校验失败: " + "；".join(errors))

    # quick 的 Review 是可选阶段；一旦已经开始或完成，就必须验证后才能继续测试。
    if mode == "quick" and target_stage == "test_verify":
        review = get_contract(mode, "code_review")
        review_path = feature_dir / review.artifact
        if review.key in completed or review_path.exists():
            errors, _ = validate_stage_document(review_path, mode, review.key)
            if errors:
                raise ValueError("可选 Review 已存在但未通过校验: " + "；".join(errors))


def prepare_stage(args: argparse.Namespace) -> int:
    feature_dir = Path(args.feature_dir).resolve()
    meta = read_meta(feature_dir)
    mode = str(meta["mode"])
    contract = get_contract(mode, args.stage)
    if contract.key == "requirement_clarification":
        raise ValueError("需求澄清阶段由 init 初始化")
    earliest_changed, invalidated = invalidate_changed_stages(feature_dir, meta)
    if earliest_changed:
        stage_order = [stage.key for stage in stages_for(mode)]
        if stage_order.index(earliest_changed) <= stage_order.index(contract.key):
            raise changed_stage_error(feature_dir, meta, earliest_changed, invalidated)
    validate_predecessors(feature_dir, meta, contract.key)

    target = feature_dir / contract.artifact
    if not target.exists():
        template_path = TEMPLATE_ROOT / mode / contract.artifact
        content = render_template(
            template_path,
            {
                "FEATURE_NAME": str(meta["feature_name"]),
                "CREATED_DATE": str(meta["created_date"]),
            },
        )
        target.write_text(content, encoding="utf-8", newline="\n")

    artifacts = dict(meta.get("artifacts", {}))
    artifacts[contract.key] = contract.artifact
    meta["artifacts"] = artifacts
    meta["current_stage"] = contract.key
    meta["recommended_next_skill"] = contract.skill
    if mode == "full" and contract.key == "technical_design" and not isinstance(
        meta.get("sql_gate"), dict
    ):
        meta["sql_gate"] = default_sql_gate()
    meta["last_validation"] = {
        "stage": contract.key,
        "valid": True,
        "kind": "predecessors",
    }
    write_meta(feature_dir, meta)
    print(str(target))
    return 0


def require_sql_gate_context(feature_dir: Path, meta: dict[str, object]) -> Path:
    if str(meta.get("mode")) != "full":
        raise ValueError("SQL Gate 仅适用于 full 技术方案阶段")
    earliest_changed, invalidated = invalidate_changed_stages(feature_dir, meta)
    if earliest_changed and earliest_changed != "technical_design":
        raise changed_stage_error(feature_dir, meta, earliest_changed, invalidated)
    validate_predecessors(feature_dir, meta, "technical_design")
    design_path = feature_dir / "02-design.md"
    if not design_path.is_file():
        raise ValueError(
            "技术方案尚未准备，请先执行 prepare-stage --stage technical_design"
        )
    return design_path


def prepare_sql_gate(args: argparse.Namespace) -> int:
    feature_dir = Path(args.feature_dir).resolve()
    meta = read_meta(feature_dir)
    design_path = require_sql_gate_context(feature_dir, meta)
    impact = str(args.impact)
    status = "not_involved" if impact == "none" else "pending_confirmation"
    source = "不涉及新增或修改 SQL，无需用户确认" if impact == "none" else ""
    update_design_sql_gate(
        design_path,
        impact=impact,
        status=status,
        fingerprint="",
        source=source,
    )
    errors = validate_sql_checkpoint_document(design_path)
    errors.extend(validate_sql_artifact(design_path, impact))
    raise_for_errors(errors)
    fingerprint = sql_gate_fingerprint(design_path)
    update_design_sql_gate(
        design_path,
        impact=impact,
        status=status,
        fingerprint=fingerprint,
        source=source,
    )
    gate = default_sql_gate()
    gate.update(
        {
            "status": status,
            "impact": impact,
            "artifact": str(SQL_DESIGN_ARTIFACT) if impact != "none" else None,
            "fingerprint": fingerprint,
            "confirmation_source": source or None,
            "confirmed_at": None,
            "stale_reason": None,
        }
    )
    completed = list(meta.get("completed_stages", []))
    if "technical_design" in completed:
        stage_order = [stage.key for stage in stages_for("full")]
        technical_index = stage_order.index("technical_design")
        invalidated = [
            stage for stage in completed if stage_order.index(stage) >= technical_index
        ]
        meta["completed_stages"] = [
            stage for stage in completed if stage not in invalidated
        ]
        fingerprints = dict(meta.get("artifact_fingerprints", {}))
        for stage in invalidated:
            fingerprints.pop(stage, None)
        meta["artifact_fingerprints"] = fingerprints
    meta["sql_gate"] = gate
    meta["current_stage"] = "technical_design"
    meta["recommended_next_skill"] = "zstt-technical-design"
    meta["last_validation"] = {
        "stage": "technical_design",
        "valid": impact == "none",
        "kind": "sql_gate",
        "status": status,
    }
    write_meta(feature_dir, meta)
    print(json.dumps(gate, ensure_ascii=False, indent=2))
    return 0


def confirm_sql(args: argparse.Namespace) -> int:
    feature_dir = Path(args.feature_dir).resolve()
    meta = read_meta(feature_dir)
    design_path = require_sql_gate_context(feature_dir, meta)
    source = str(args.source).strip()
    if "\n" in source or len(source) < 8 or source in {
        "用户确认",
        "已经确认",
        "确认通过",
    }:
        raise ValueError(
            "确认来源必须是可追溯的单行用户确认记录，"
            "不能只写泛化的“用户确认”"
        )
    gate = sql_gate_from_meta(meta)
    if gate.get("status") != "pending_confirmation" or gate.get("impact") not in {
        "query_dml",
        "ddl",
    }:
        raise ValueError("当前没有等待用户确认的 SQL Gate")
    errors = validate_sql_checkpoint_document(design_path)
    errors.extend(validate_sql_artifact(design_path, str(gate["impact"])))
    raise_for_errors(errors)
    current = sql_gate_fingerprint(design_path)
    if not current or current != gate.get("fingerprint"):
        mark_sql_gate_stale(meta, "待确认 SQL 在用户确认前发生变化")
        write_meta(feature_dir, meta)
        raise ValueError(
            "待确认 SQL 已变化，请重新执行 prepare-sql-gate 后再次请求用户确认"
        )
    confirmed_at = datetime.now(timezone.utc).isoformat()
    gate.update(
        {
            "status": "confirmed",
            "confirmation_source": source,
            "confirmed_at": confirmed_at,
            "stale_reason": None,
        }
    )
    update_design_sql_gate(
        design_path,
        impact=str(gate["impact"]),
        status="confirmed",
        fingerprint=current,
        source=source,
    )
    meta["sql_gate"] = gate
    meta["last_validation"] = {
        "stage": "technical_design",
        "valid": True,
        "kind": "sql_confirmation",
        "confirmed_at": confirmed_at,
    }
    write_meta(feature_dir, meta)
    print(json.dumps(gate, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ZSTT 后端工作流状态与门禁工具")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="初始化 full 或 quick 需求目录")
    init_parser.add_argument("--repo-root", required=True)
    init_parser.add_argument("--mode", required=True, choices=("full", "quick"))
    init_parser.add_argument("--feature-name", required=True)
    init_parser.add_argument("--date")
    init_parser.set_defaults(handler=init_feature)

    status_parser = subparsers.add_parser("status", help="输出需求状态 JSON")
    status_parser.add_argument("--feature-dir", required=True)
    status_parser.set_defaults(handler=show_status)

    validate_parser = subparsers.add_parser("validate", help="校验指定阶段产物")
    validate_parser.add_argument("--feature-dir", required=True)
    validate_parser.add_argument("--stage", required=True)
    validate_parser.set_defaults(handler=validate_stage)

    complete_parser = subparsers.add_parser("complete-stage", help="校验并完成当前阶段")
    complete_parser.add_argument("--feature-dir", required=True)
    complete_parser.add_argument("--stage", required=True)
    complete_parser.set_defaults(handler=complete_stage)

    prepare_parser = subparsers.add_parser("prepare-stage", help="重新校验上游并准备目标阶段")
    prepare_parser.add_argument("--feature-dir", required=True)
    prepare_parser.add_argument("--stage", required=True)
    prepare_parser.set_defaults(handler=prepare_stage)

    sql_prepare_parser = subparsers.add_parser(
        "prepare-sql-gate",
        help="记录技术方案 SQL 影响；涉及 SQL 时生成待用户确认门禁",
    )
    sql_prepare_parser.add_argument("--feature-dir", required=True)
    sql_prepare_parser.add_argument(
        "--impact",
        required=True,
        choices=("none", "query_dml", "ddl"),
    )
    sql_prepare_parser.set_defaults(handler=prepare_sql_gate)

    sql_confirm_parser = subparsers.add_parser(
        "confirm-sql",
        help="在用户明确确认后锁定技术方案 SQL 指纹",
    )
    sql_confirm_parser.add_argument("--feature-dir", required=True)
    sql_confirm_parser.add_argument("--source", required=True)
    sql_confirm_parser.set_defaults(handler=confirm_sql)
    return parser


def configure_stdio() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")


def main() -> int:
    configure_stdio()
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.handler(args)
    except (FileExistsError, FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
