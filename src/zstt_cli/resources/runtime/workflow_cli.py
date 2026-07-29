from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path, PurePosixPath

from quality_gates import (
    get_quality_gate,
    quality_gate_report_path,
    quality_gate_source_fingerprints,
    quality_gate_summaries,
    quality_gate_summary,
    quality_gate_template_values,
    quality_gates_before_stage,
    validate_quality_gate_document,
)
from implementation_evidence import (
    IMPLEMENTATION_EVIDENCE_PATH,
    finalize_implementation_evidence,
    ensure_implementation_baseline,
    load_evidence,
    run_and_record_validation,
)
from workflow_contracts import (
    get_contract,
    recommended_next_skills,
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
META_SCHEMA_VERSION = 3
SUPPORTED_META_SCHEMA_VERSIONS = {2, META_SCHEMA_VERSION}
WORKFLOW_STATUSES = {"active", "closed"}


class WorkflowError(ValueError):
    """Stable workflow failure used by Skills, CI and human-facing CLI output."""

    def __init__(
        self,
        code: str,
        message: str,
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.details = details or {}


def feature_relative_path(feature_dir: Path) -> str:
    resolved = feature_dir.resolve()
    indexes = [
        index
        for index, part in enumerate(resolved.parts)
        if part == ".zstt"
    ]
    if not indexes:
        raise WorkflowError(
            "ZSTT_FEATURE_PATH_INVALID",
            f"需求目录不在 .zstt 下: {resolved}",
            {"featureDir": str(resolved)},
        )
    relative = PurePosixPath(*resolved.parts[indexes[-1] :])
    if len(relative.parts) < 3 or relative.parts[1] not in {"features", "quick"}:
        raise WorkflowError(
            "ZSTT_FEATURE_PATH_INVALID",
            f"需求目录必须位于 .zstt/features 或 .zstt/quick: {resolved}",
            {"featureDir": str(resolved)},
        )
    return relative.as_posix()


def set_recommendations(meta: dict[str, object], skills: tuple[str, ...]) -> None:
    meta["recommended_next_skill"] = skills[0] if skills else None
    meta["recommended_next_skills"] = list(skills)


def normalize_meta(
    feature_dir: Path,
    meta: object,
) -> dict[str, object]:
    if not isinstance(meta, dict):
        raise WorkflowError("ZSTT_STATE_INVALID", "meta.json 顶层必须是对象")
    version = meta.get("version")
    if version not in SUPPORTED_META_SCHEMA_VERSIONS:
        raise WorkflowError(
            "ZSTT_STATE_INVALID",
            f"不支持的 meta.json 版本: {version}",
            {"version": version},
        )

    normalized = dict(meta)
    mode = str(normalized.get("mode", ""))
    completed_value = normalized.get("completed_stages", [])
    if not isinstance(completed_value, list) or not all(
        isinstance(stage, str) for stage in completed_value
    ):
        raise WorkflowError(
            "ZSTT_STATE_INVALID",
            "meta.json 的 completed_stages 必须是字符串数组",
        )
    current_stage = str(normalized.get("current_stage", ""))
    if current_stage and current_stage not in completed_value:
        recommendations = (get_contract(mode, current_stage).skill,)
    else:
        recommendations = recommended_next_skills(mode, completed_value)

    # v2 可能保存了本机绝对目录；v3 每次都从实际需求目录重建可提交的相对路径。
    normalized["version"] = META_SCHEMA_VERSION
    normalized["feature_dir"] = feature_relative_path(feature_dir)
    workflow_status = normalized.get("workflow_status")
    if workflow_status is None:
        # 旧状态没有显式生命周期：只有没有任何后续推荐时才能安全推断已关闭。
        workflow_status = "closed" if not recommendations else "active"
    if (
        not isinstance(workflow_status, str)
        or workflow_status not in WORKFLOW_STATUSES
    ):
        raise WorkflowError(
            "ZSTT_STATE_INVALID",
            f"meta.json 的 workflow_status 无效: {workflow_status}",
        )
    normalized["workflow_status"] = workflow_status
    if workflow_status == "closed":
        recommendations = ()
    skipped_stages = normalized.get("skipped_stages", [])
    if not isinstance(skipped_stages, list) or not all(
        isinstance(stage, str) for stage in skipped_stages
    ):
        raise WorkflowError(
            "ZSTT_STATE_INVALID",
            "meta.json 的 skipped_stages 必须是字符串数组",
        )
    normalized["skipped_stages"] = skipped_stages
    set_recommendations(normalized, recommendations)
    return normalized


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
        raise WorkflowError(
            "ZSTT_STATE_NOT_FOUND",
            f"状态文件不存在: {meta_path}",
            {"metaPath": str(meta_path)},
        )
    return normalize_meta(
        feature_dir,
        json.loads(meta_path.read_text(encoding="utf-8")),
    )


def write_meta(feature_dir: Path, meta: dict[str, object]) -> None:
    normalized = normalize_meta(feature_dir, meta)
    meta.clear()
    meta.update(normalized)
    content = json.dumps(normalized, ensure_ascii=False, indent=2) + "\n"
    (feature_dir / META_NAME).write_text(content, encoding="utf-8", newline="\n")


def current_git_branch(repo_root: Path) -> str | None:
    """Read the current symbolic branch without guessing from directory names."""
    try:
        completed = subprocess.run(
            [
                "git",
                "-C",
                str(repo_root),
                "symbolic-ref",
                "--quiet",
                "--short",
                "HEAD",
            ],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except OSError:
        return None
    branch = completed.stdout.strip()
    return branch if completed.returncode == 0 and branch else None


def feature_is_completed(
    feature_dir: Path,
    meta: dict[str, object],
    stale_stages: list[str] | None = None,
) -> bool:
    """Only an explicitly closed workflow with fresh artifacts is completed."""
    stale = (
        changed_completed_stages(feature_dir, meta)
        if stale_stages is None
        else stale_stages
    )
    return meta.get("workflow_status") == "closed" and not stale


def feature_summary(
    feature_dir: Path,
    meta: dict[str, object],
) -> dict[str, object]:
    stale_stages = changed_completed_stages(feature_dir, meta)
    mode = str(meta.get("mode", ""))
    return {
        "feature_dir": str(meta["feature_dir"]),
        "absolute_path": str(feature_dir.resolve()),
        "mode": mode,
        "feature_name": str(meta.get("feature_name", "")),
        "git_branch": meta.get("git_branch"),
        "workflow_status": meta.get("workflow_status"),
        "current_stage": str(meta.get("current_stage", "")),
        "completed_stages": list(meta.get("completed_stages", [])),
        "skipped_stages": list(meta.get("skipped_stages", [])),
        "stale_stages": stale_stages,
        "completed": feature_is_completed(feature_dir, meta, stale_stages),
        "recommended_next_skills": list(meta.get("recommended_next_skills", [])),
        "quality_gates": quality_gate_summaries(feature_dir, mode),
    }


def discover_features(
    repo_root: Path,
) -> tuple[
    list[tuple[Path, dict[str, object]]],
    list[dict[str, object]],
]:
    """Discover only direct ZSTT feature directories; never choose by newest date."""
    valid: list[tuple[Path, dict[str, object]]] = []
    invalid: list[dict[str, object]] = []
    for category in ("features", "quick"):
        category_root = repo_root / ".zstt" / category
        if not category_root.is_dir():
            continue
        for feature_dir in sorted(
            (path for path in category_root.iterdir() if path.is_dir()),
            key=lambda path: path.name,
        ):
            try:
                valid.append((feature_dir, read_meta(feature_dir)))
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                invalid.append(
                    {
                        "feature_dir": str(feature_dir.resolve()),
                        "error": str(exc),
                    }
                )
    return valid, invalid


def select_current_feature(
    repo_root: Path,
) -> tuple[Path, dict[str, object], str]:
    branch = current_git_branch(repo_root)
    if not branch:
        raise WorkflowError(
            "ZSTT_GIT_BRANCH_UNAVAILABLE",
            "无法确定当前 Git 分支；请显式传入 --feature-dir",
            {"repoRoot": str(repo_root)},
        )

    valid, invalid = discover_features(repo_root)
    if invalid:
        raise WorkflowError(
            "ZSTT_CURRENT_STATE_INVALID",
            "存在无法读取的需求状态，不能证明当前需求唯一；请先修复状态或显式传入 --feature-dir",
            {
                "gitBranch": branch,
                "invalidFeatures": invalid,
            },
        )
    unfinished = [
        (feature_dir, meta)
        for feature_dir, meta in valid
        if not feature_is_completed(feature_dir, meta)
    ]
    unbound = [
        feature_summary(feature_dir, meta)
        for feature_dir, meta in unfinished
        if not meta.get("git_branch")
    ]
    if unbound:
        raise WorkflowError(
            "ZSTT_CURRENT_BRANCH_UNBOUND",
            "存在未绑定 Git 分支的历史需求，不能安全自动选择；请显式使用 bind-branch",
            {
                "gitBranch": branch,
                "unboundFeatures": unbound,
            },
        )
    candidates = [
        (feature_dir, meta)
        for feature_dir, meta in unfinished
        if meta.get("git_branch") == branch
    ]
    candidate_summaries = [
        feature_summary(feature_dir, meta)
        for feature_dir, meta in candidates
    ]
    if not candidates:
        raise WorkflowError(
            "ZSTT_CURRENT_NOT_FOUND",
            f"当前分支 {branch} 没有唯一可用的未完成需求；请显式传入 --feature-dir",
            {
                "gitBranch": branch,
                "unfinishedFeatures": [
                    feature_summary(feature_dir, meta)
                    for feature_dir, meta in unfinished
                ],
                "invalidFeatures": invalid,
            },
        )
    if len(candidates) > 1:
        raise WorkflowError(
            "ZSTT_CURRENT_AMBIGUOUS",
            f"当前分支 {branch} 存在多个未完成需求；请显式传入 --feature-dir",
            {
                "gitBranch": branch,
                "candidates": candidate_summaries,
            },
        )
    feature_dir, meta = candidates[0]
    return feature_dir, meta, branch


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
        raise WorkflowError(
            "ZSTT_FEATURE_EXISTS",
            f"需求目录已存在，拒绝覆盖: {target}",
            {"featureDir": str(target)},
        )

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
        "version": META_SCHEMA_VERSION,
        "workflow": "zstt-backend-workflow",
        "mode": args.mode,
        "feature_name": args.feature_name.strip(),
        "feature_dir": feature_relative_path(target),
        "created_date": date_text,
        "git_branch": current_git_branch(repo_root),
        "workflow_status": "active",
        "skipped_stages": [],
        "current_stage": requirement.key,
        "completed_stages": [],
        "artifacts": {requirement.key: requirement.artifact},
        "artifact_fingerprints": {},
        "blocking_counts": {"p0": 0, "p1": 0, "p2": 0},
        "last_validation": None,
        "recommended_next_skill": requirement.skill,
        "recommended_next_skills": [requirement.skill],
    }
    if args.mode == "full":
        meta["sql_gate"] = default_sql_gate()
    write_meta(target, meta)
    print(str(target))
    return 0


def show_status(args: argparse.Namespace) -> int:
    if args.feature_dir:
        feature_dir = Path(args.feature_dir).resolve()
        meta = read_meta(feature_dir)
    elif args.current:
        feature_dir, meta, _branch = select_current_feature(
            Path(args.repo_root).resolve()
        )
    else:
        raise WorkflowError(
            "ZSTT_USAGE_INVALID",
            "status 必须显式传入 --feature-dir，或使用 --current",
        )
    status = dict(meta)
    status["stale_stages"] = changed_completed_stages(feature_dir, meta)
    mode = str(meta.get("mode"))
    status["quality_gates"] = quality_gate_summaries(feature_dir, mode)
    if mode == "full":
        gate = sql_gate_from_meta(meta)
        gate["effective_status"] = (
            "stale" if sql_gate_is_stale(feature_dir, meta) else gate["status"]
        )
        status["sql_gate"] = gate
    print(json.dumps(status, ensure_ascii=False, indent=2))
    return 0


def list_features(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    valid, invalid = discover_features(repo_root)
    payload = {
        "repo_root": str(repo_root),
        "current_git_branch": current_git_branch(repo_root),
        "features": [
            feature_summary(feature_dir, meta)
            for feature_dir, meta in valid
        ],
        "invalid_features": invalid,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def show_current(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    feature_dir, meta, branch = select_current_feature(repo_root)
    print(
        json.dumps(
            {
                "repo_root": str(repo_root),
                "current_git_branch": branch,
                "feature": feature_summary(feature_dir, meta),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def bind_branch(args: argparse.Namespace) -> int:
    """Explicitly bind one legacy feature to the current Git branch."""
    repo_root = Path(args.repo_root).resolve()
    feature_dir = Path(args.feature_dir).resolve()
    expected_root = repo_root / ".zstt"
    if (
        feature_dir.parent.parent != expected_root
        or feature_dir.parent.name not in {"features", "quick"}
    ):
        raise WorkflowError(
            "ZSTT_FEATURE_PATH_INVALID",
            "bind-branch 的需求目录必须位于指定仓库的 .zstt/features 或 .zstt/quick",
            {
                "repoRoot": str(repo_root),
                "featureDir": str(feature_dir),
            },
        )
    branch = current_git_branch(repo_root)
    if not branch:
        raise WorkflowError(
            "ZSTT_GIT_BRANCH_UNAVAILABLE",
            "无法确定当前 Git 分支，不能绑定历史需求",
            {"repoRoot": str(repo_root)},
        )
    meta = read_meta(feature_dir)
    existing = meta.get("git_branch")
    if existing and existing != branch:
        raise WorkflowError(
            "ZSTT_BRANCH_ALREADY_BOUND",
            f"需求已绑定其他 Git 分支: {existing}",
            {
                "existingBranch": existing,
                "currentGitBranch": branch,
                "featureDir": str(feature_dir),
            },
        )
    meta["git_branch"] = branch
    write_meta(feature_dir, meta)
    print(
        json.dumps(
            {
                "feature_dir": str(meta["feature_dir"]),
                "git_branch": branch,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def close_workflow(args: argparse.Namespace) -> int:
    """Close a workflow explicitly after all mandatory stages are fresh."""
    if args.feature_dir:
        feature_dir = Path(args.feature_dir).resolve()
        meta = read_meta(feature_dir)
    elif args.current:
        feature_dir, meta, _branch = select_current_feature(
            Path(args.repo_root).resolve()
        )
    else:
        raise WorkflowError(
            "ZSTT_USAGE_INVALID",
            "close 必须显式传入 --feature-dir，或使用 --current",
        )

    earliest_changed, invalidated = invalidate_changed_stages(feature_dir, meta)
    if earliest_changed:
        raise changed_stage_error(feature_dir, meta, earliest_changed, invalidated)

    mode = str(meta["mode"])
    completed = list(meta.get("completed_stages", []))
    mandatory = (
        [stage.key for stage in stages_for("full")]
        if mode == "full"
        else ["requirement_clarification", "implementation"]
    )
    missing = [stage for stage in mandatory if stage not in completed]
    if missing:
        raise WorkflowError(
            "ZSTT_WORKFLOW_NOT_CLOSABLE",
            "必需阶段尚未完成: " + ", ".join(missing),
            {"missingStages": missing},
        )

    optional = [] if mode == "full" else ["code_review", "test_verify"]
    meta["workflow_status"] = "closed"
    meta["closed_at"] = datetime.now(timezone.utc).isoformat()
    meta["skipped_stages"] = [
        stage for stage in optional if stage not in completed
    ]
    set_recommendations(meta, ())
    meta["last_validation"] = {
        "stage": str(meta.get("current_stage", "")),
        "valid": True,
        "kind": "workflow_closed",
    }
    write_meta(feature_dir, meta)
    print(json.dumps(meta, ensure_ascii=False, indent=2))
    return 0


def raise_for_errors(errors: list[str]) -> None:
    if errors:
        raise WorkflowError(
            "ZSTT_ARTIFACT_INVALID",
            "；".join(errors),
            {"validationErrors": errors},
        )


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
    meta["workflow_status"] = "active"
    meta.pop("closed_at", None)
    meta["skipped_stages"] = []
    set_recommendations(meta, (get_contract(mode, earliest).skill,))
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
) -> WorkflowError:
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
    return WorkflowError(
        "ZSTT_ARTIFACT_CHANGED",
        (
            "上游已完成产物已修改，已撤销相关完成状态: "
            + ", ".join(invalidated)
            + f"；请重新执行阶段 {earliest} 的 complete-stage"
            + detail
        ),
        {
            "earliestChangedStage": earliest,
            "invalidatedStages": invalidated,
        },
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
        raise WorkflowError(
            "ZSTT_PREDECESSOR_NOT_READY",
            "前置阶段尚未完成: " + ", ".join(missing_predecessors),
            {
                "stage": contract.key,
                "missingStages": missing_predecessors,
            },
        )
    quality_gate_results = validate_quality_gates_before_stage(
        feature_dir,
        mode,
        contract.key,
    )
    if contract.key == "implementation":
        evidence = finalize_implementation_evidence(
            feature_dir,
            feature_dir / contract.artifact,
        )
        validation_summary = evidence.get("validationSummary")
        if not isinstance(validation_summary, dict):
            validation_summary = {}
        if (
            validation_summary.get("freshPassed", 0) < 1
            or validation_summary.get("freshFailed", 0) > 0
        ):
            raise WorkflowError(
                "ZSTT_IMPLEMENTATION_VALIDATION_NOT_FRESH",
                "实现阶段缺少覆盖最终工作区快照的成功验证，"
                "或同一快照仍有失败验证；请重新运行 run-validation",
                {"validationSummary": validation_summary},
            )

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
    meta["last_validation"] = {
        "stage": contract.key,
        "valid": True,
        "quality_gates": quality_gate_results,
    }
    skipped = [
        stage
        for stage in list(meta.get("skipped_stages", []))
        if stage != contract.key
    ]
    meta["skipped_stages"] = skipped
    automatically_closed = (
        mode == "full"
        and all(stage.key in completed for stage in stages_for("full"))
    ) or (
        mode == "quick"
        and "test_verify" in completed
    )
    if automatically_closed:
        meta["workflow_status"] = "closed"
        meta["closed_at"] = datetime.now(timezone.utc).isoformat()
        if mode == "quick":
            meta["skipped_stages"] = [
                stage
                for stage in ("code_review", "test_verify")
                if stage not in completed
            ]
        set_recommendations(meta, ())
    else:
        meta["workflow_status"] = "active"
        meta.pop("closed_at", None)
        set_recommendations(meta, recommended_next_skills(mode, completed))
    write_meta(feature_dir, meta)
    print(json.dumps(meta, ensure_ascii=False, indent=2))
    return 0


def validate_predecessors(
    feature_dir: Path,
    meta: dict[str, object],
    target_stage: str,
) -> dict[str, dict[str, object]]:
    mode = str(meta["mode"])
    completed = list(meta.get("completed_stages", []))
    predecessors = required_predecessors(mode, target_stage)
    missing = [stage for stage in predecessors if stage not in completed]
    if missing:
        raise WorkflowError(
            "ZSTT_PREDECESSOR_NOT_READY",
            "前置阶段尚未完成: " + ", ".join(missing),
            {"stage": target_stage, "missingStages": missing},
        )

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
    return validate_quality_gates_before_stage(feature_dir, mode, target_stage)


def validate_quality_gates_before_stage(
    feature_dir: Path,
    mode: str,
    target_stage: str,
) -> dict[str, dict[str, object]]:
    results: dict[str, dict[str, object]] = {}
    for gate_key in quality_gates_before_stage(mode, target_stage):
        summary = quality_gate_summary(feature_dir, mode, gate_key)
        results[gate_key] = summary
        if summary["state"] in {"skipped", "passed", "conditional"}:
            continue
        raise WorkflowError(
            "ZSTT_QUALITY_GATE_BLOCKED",
            (
                f"可选质量门禁 {gate_key} 已存在但状态为 "
                f"{summary['state']}；请修正权威产物并重新执行对应 Skill"
            ),
            {
                "stage": target_stage,
                "qualityGate": gate_key,
                "summary": summary,
            },
        )
    return results


def prepare_stage(args: argparse.Namespace) -> int:
    feature_dir = Path(args.feature_dir).resolve()
    meta = read_meta(feature_dir)
    mode = str(meta["mode"])
    contract = get_contract(mode, args.stage)
    if contract.key == "requirement_clarification":
        raise WorkflowError(
            "ZSTT_STAGE_OPERATION_INVALID",
            "需求澄清阶段由 init 初始化",
            {"stage": contract.key},
        )
    completed = list(meta.get("completed_stages", []))
    if (
        contract.key in {"code_review", "test_verify"}
        and "implementation" in completed
    ):
        implementation = get_contract(mode, "implementation")
        finalize_implementation_evidence(
            feature_dir,
            feature_dir / implementation.artifact,
        )
    earliest_changed, invalidated = invalidate_changed_stages(feature_dir, meta)
    if earliest_changed:
        stage_order = [stage.key for stage in stages_for(mode)]
        if stage_order.index(earliest_changed) <= stage_order.index(contract.key):
            raise changed_stage_error(feature_dir, meta, earliest_changed, invalidated)
    quality_gate_results = validate_predecessors(feature_dir, meta, contract.key)

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
    if contract.key == "implementation":
        ensure_implementation_baseline(feature_dir, target)

    artifacts = dict(meta.get("artifacts", {}))
    artifacts[contract.key] = contract.artifact
    meta["artifacts"] = artifacts
    meta["current_stage"] = contract.key
    meta["workflow_status"] = "active"
    meta.pop("closed_at", None)
    meta["skipped_stages"] = [
        stage
        for stage in list(meta.get("skipped_stages", []))
        if stage != contract.key
    ]
    set_recommendations(meta, (contract.skill,))
    if mode == "full" and contract.key == "technical_design" and not isinstance(
        meta.get("sql_gate"), dict
    ):
        meta["sql_gate"] = default_sql_gate()
    meta["last_validation"] = {
        "stage": contract.key,
        "valid": True,
        "kind": "predecessors",
        "quality_gates": quality_gate_results,
    }
    write_meta(feature_dir, meta)
    print(str(target))
    return 0


def run_validation(args: argparse.Namespace) -> int:
    feature_dir = Path(args.feature_dir).resolve()
    meta = read_meta(feature_dir)
    mode = str(meta["mode"])
    implementation = get_contract(mode, "implementation")
    implementation_path = feature_dir / implementation.artifact
    if not implementation_path.is_file():
        raise WorkflowError(
            "ZSTT_IMPLEMENTATION_NOT_PREPARED",
            "实现阶段尚未准备，请先运行 prepare-stage --stage implementation",
            {"artifact": str(implementation_path)},
        )
    command = list(args.validation_command)
    if command and command[0] == "--":
        command = command[1:]
    exit_code = run_and_record_validation(
        feature_dir,
        implementation_path,
        command,
    )
    payload = load_evidence(feature_dir)
    validations = list(payload.get("validations", []))
    result = validations[-1] if validations else {}
    print(
        json.dumps(
            {
                "feature_dir": str(meta["feature_dir"]),
                "artifact": IMPLEMENTATION_EVIDENCE_PATH.as_posix(),
                "validation": result,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return exit_code


def prepare_quality_gate(args: argparse.Namespace) -> int:
    feature_dir = Path(args.feature_dir).resolve()
    meta = read_meta(feature_dir)
    mode = str(meta["mode"])
    gate = get_quality_gate(args.gate)
    if mode not in gate.modes:
        raise WorkflowError(
            "ZSTT_QUALITY_GATE_UNSUPPORTED",
            f"{gate.key} 不支持 {mode} 模式",
            {"qualityGate": gate.key, "mode": mode},
        )

    if gate.key == "artifact_analysis":
        completed = set(meta.get("completed_stages", []))
        missing = [stage for stage in gate.source_stages if stage not in completed]
        if missing:
            raise WorkflowError(
                "ZSTT_PREDECESSOR_NOT_READY",
                "实现前一致性分析的前置阶段尚未完成: " + ", ".join(missing),
                {"qualityGate": gate.key, "missingStages": missing},
            )
        stale = changed_completed_stages(feature_dir, meta)
        if stale:
            raise WorkflowError(
                "ZSTT_ARTIFACT_CHANGED",
                "实现前一致性分析存在失效输入: " + ", ".join(stale),
                {"qualityGate": gate.key, "staleStages": stale},
            )
        for stage_key in gate.source_stages:
            contract = get_contract(mode, stage_key)
            errors, _ = validate_stage_document(
                feature_dir / contract.artifact,
                mode,
                stage_key,
            )
            raise_for_errors(errors)
        gate_state = sql_gate_from_meta(meta)
        if gate_state.get("status") not in {"not_involved", "confirmed"}:
            raise WorkflowError(
                "ZSTT_SQL_GATE_BLOCKED",
                "实现前一致性分析要求 SQL Gate 为 not_involved 或 confirmed",
                {"sqlGate": gate_state},
            )
        if sql_gate_is_stale(feature_dir, meta):
            raise WorkflowError(
                "ZSTT_SQL_GATE_BLOCKED",
                "实现前一致性分析的 SQL Gate 已失效",
                {"sqlGate": gate_state},
            )

    values = quality_gate_template_values(feature_dir, mode, gate.key)
    values.update(
        {
            "FEATURE_NAME": str(meta["feature_name"]),
            "CREATED_DATE": date.today().isoformat(),
        }
    )
    report_path = quality_gate_report_path(feature_dir, gate.key)
    created = not report_path.exists()
    if created:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        template_path = TEMPLATE_ROOT / "quality-gates" / f"{gate.key.replace('_', '-')}.md"
        content = render_template(template_path, values)
        report_path.write_text(content, encoding="utf-8", newline="\n")

    print(
        json.dumps(
            {
                "quality_gate": gate.key,
                "path": str(report_path),
                "created": created,
                "input_fingerprints": quality_gate_source_fingerprints(
                    feature_dir,
                    mode,
                    gate.key,
                ),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def validate_quality_gate(args: argparse.Namespace) -> int:
    feature_dir = Path(args.feature_dir).resolve()
    meta = read_meta(feature_dir)
    mode = str(meta["mode"])
    errors, _frontmatter = validate_quality_gate_document(
        feature_dir,
        mode,
        args.gate,
    )
    raise_for_errors(errors)
    print(
        json.dumps(
            quality_gate_summary(feature_dir, mode, args.gate),
            ensure_ascii=False,
            indent=2,
        )
    )
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
    parser.add_argument(
        "--json",
        action="store_true",
        help="失败时输出机器可读的 JSON 结果",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="初始化 full 或 quick 需求目录")
    init_parser.add_argument("--repo-root", required=True)
    init_parser.add_argument("--mode", required=True, choices=("full", "quick"))
    init_parser.add_argument("--feature-name", required=True)
    init_parser.add_argument("--date")
    init_parser.set_defaults(handler=init_feature)

    list_parser = subparsers.add_parser("list", help="列出项目中的 ZSTT 需求")
    list_parser.add_argument("--repo-root", default=".")
    list_parser.set_defaults(handler=list_features)

    current_parser = subparsers.add_parser(
        "current",
        help="按当前 Git 分支选择唯一未完成需求",
    )
    current_parser.add_argument("--repo-root", default=".")
    current_parser.set_defaults(handler=show_current)

    status_parser = subparsers.add_parser("status", help="输出需求状态 JSON")
    status_parser.add_argument("--feature-dir")
    status_parser.add_argument(
        "--current",
        action="store_true",
        help="按当前 Git 分支选择唯一未完成需求",
    )
    status_parser.add_argument("--repo-root", default=".")
    status_parser.set_defaults(handler=show_status)

    bind_parser = subparsers.add_parser(
        "bind-branch",
        help="把一个没有分支信息的历史需求显式绑定到当前 Git 分支",
    )
    bind_parser.add_argument("--feature-dir", required=True)
    bind_parser.add_argument("--repo-root", default=".")
    bind_parser.set_defaults(handler=bind_branch)

    close_parser = subparsers.add_parser(
        "close",
        help="完成必需阶段后显式关闭工作流",
    )
    close_parser.add_argument("--feature-dir")
    close_parser.add_argument(
        "--current",
        action="store_true",
        help="按当前 Git 分支选择唯一活动需求",
    )
    close_parser.add_argument("--repo-root", default=".")
    close_parser.set_defaults(handler=close_workflow)

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

    validation_run_parser = subparsers.add_parser(
        "run-validation",
        help="执行实现阶段验证命令，并自动记录命令、退出码和耗时",
    )
    validation_run_parser.add_argument("--feature-dir", required=True)
    validation_run_parser.add_argument(
        "validation_command",
        nargs=argparse.REMAINDER,
        help="放在 -- 后的验证命令及参数",
    )
    validation_run_parser.set_defaults(handler=run_validation)

    quality_prepare_parser = subparsers.add_parser(
        "prepare-quality-gate",
        help="准备可选质量门禁产物，不推进固定阶段",
    )
    quality_prepare_parser.add_argument("--feature-dir", required=True)
    quality_prepare_parser.add_argument(
        "--gate",
        required=True,
        choices=("requirement_checklist", "artifact_analysis"),
    )
    quality_prepare_parser.set_defaults(handler=prepare_quality_gate)

    quality_validate_parser = subparsers.add_parser(
        "validate-quality-gate",
        help="校验可选质量门禁的结构、计数和输入指纹",
    )
    quality_validate_parser.add_argument("--feature-dir", required=True)
    quality_validate_parser.add_argument(
        "--gate",
        required=True,
        choices=("requirement_checklist", "artifact_analysis"),
    )
    quality_validate_parser.set_defaults(handler=validate_quality_gate)

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


def operation_error(
    operation: str,
    error: BaseException,
) -> WorkflowError:
    if isinstance(error, WorkflowError):
        return error
    if isinstance(error, json.JSONDecodeError):
        return WorkflowError(
            "ZSTT_STATE_INVALID",
            f"状态文件不是有效 JSON: {error}",
        )
    if isinstance(error, FileNotFoundError):
        return WorkflowError(
            "ZSTT_ARTIFACT_NOT_FOUND",
            str(error),
        )
    operation_codes = {
        "init": "ZSTT_FEATURE_INIT_INVALID",
        "list": "ZSTT_FEATURE_LIST_FAILED",
        "current": "ZSTT_CURRENT_RESOLUTION_FAILED",
        "status": "ZSTT_STATE_INVALID",
        "bind-branch": "ZSTT_BRANCH_BINDING_BLOCKED",
        "close": "ZSTT_WORKFLOW_CLOSE_BLOCKED",
        "validate": "ZSTT_ARTIFACT_INVALID",
        "complete-stage": "ZSTT_STAGE_COMPLETION_BLOCKED",
        "prepare-stage": "ZSTT_STAGE_PREPARATION_BLOCKED",
        "run-validation": "ZSTT_VALIDATION_EXECUTION_FAILED",
        "prepare-quality-gate": "ZSTT_QUALITY_GATE_PREPARATION_BLOCKED",
        "validate-quality-gate": "ZSTT_QUALITY_GATE_INVALID",
        "prepare-sql-gate": "ZSTT_SQL_GATE_PREPARATION_BLOCKED",
        "confirm-sql": "ZSTT_SQL_CONFIRMATION_BLOCKED",
    }
    return WorkflowError(
        operation_codes.get(operation, "ZSTT_WORKFLOW_OPERATION_FAILED"),
        str(error),
    )


def error_payload(
    operation: str,
    error: WorkflowError,
) -> dict[str, object]:
    return {
        "status": "BLOCKED",
        "operation": operation,
        "error": {
            "code": error.code,
            "message": str(error),
            "details": error.details,
        },
    }


def main() -> int:
    configure_stdio()
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.handler(args)
    except (FileExistsError, FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        error = operation_error(args.command, exc)
        if args.json:
            print(json.dumps(error_payload(args.command, error), ensure_ascii=False, indent=2))
        else:
            print(f"[{error.code}] {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
