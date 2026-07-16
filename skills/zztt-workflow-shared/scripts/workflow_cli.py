from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from workflow_contracts import get_contract
from workflow_paths import feature_directory


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
