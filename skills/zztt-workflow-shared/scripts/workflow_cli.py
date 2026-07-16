from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from workflow_contracts import (
    get_contract,
    recommended_next_skill,
    required_predecessors,
)
from workflow_paths import feature_directory
from workflow_validation import validate_stage_document


SCRIPT_DIR = Path(__file__).resolve().parent
SHARED_ROOT = SCRIPT_DIR.parent
TEMPLATE_ROOT = SHARED_ROOT / "assets" / "templates"
META_NAME = "meta.json"


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
        "version": 1,
        "workflow": "zztt-backend-workflow",
        "mode": args.mode,
        "feature_name": args.feature_name.strip(),
        "feature_dir": str(target),
        "created_date": date_text,
        "current_stage": requirement.key,
        "completed_stages": [],
        "artifacts": {requirement.key: requirement.artifact},
        "blocking_counts": {"p0": 0, "p1": 0, "p2": 0},
        "last_validation": None,
        "recommended_next_skill": requirement.skill,
    }
    write_meta(target, meta)
    print(str(target))
    return 0


def show_status(args: argparse.Namespace) -> int:
    meta = read_meta(Path(args.feature_dir).resolve())
    print(json.dumps(meta, ensure_ascii=False, indent=2))
    return 0


def raise_for_errors(errors: list[str]) -> None:
    if errors:
        raise ValueError("；".join(errors))


def validate_stage(args: argparse.Namespace) -> int:
    feature_dir = Path(args.feature_dir).resolve()
    meta = read_meta(feature_dir)
    mode = str(meta["mode"])
    contract = get_contract(mode, args.stage)
    errors, _ = validate_stage_document(
        feature_dir / contract.artifact,
        mode,
        contract.key,
    )
    raise_for_errors(errors)
    print(json.dumps({"stage": contract.key, "valid": True}, ensure_ascii=False))
    return 0


def complete_stage(args: argparse.Namespace) -> int:
    feature_dir = Path(args.feature_dir).resolve()
    meta = read_meta(feature_dir)
    mode = str(meta["mode"])
    contract = get_contract(mode, args.stage)
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
    if contract.key not in completed:
        completed.append(contract.key)

    meta["current_stage"] = contract.key
    meta["completed_stages"] = completed
    artifacts = dict(meta.get("artifacts", {}))
    artifacts[contract.key] = contract.artifact
    meta["artifacts"] = artifacts
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
    meta["last_validation"] = {
        "stage": contract.key,
        "valid": True,
        "kind": "predecessors",
    }
    write_meta(feature_dir, meta)
    print(str(target))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ZZTT 后端工作流状态与门禁工具")
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
