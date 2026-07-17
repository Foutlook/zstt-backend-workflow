from __future__ import annotations

import argparse
import sys
from pathlib import Path

from zztt_cli import __version__
from zztt_cli.installer import (
    ConflictError,
    InstallResult,
    InstallationError,
    check_project,
    init_project,
    update_project,
)


def _add_project_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("path", nargs="?", help="业务仓库路径，默认使用当前目录")
    parser.add_argument(
        "--here",
        action="store_true",
        help="显式使用当前目录；不能与 path 同时使用",
    )


def _project_root(args: argparse.Namespace) -> Path:
    if args.here and args.path:
        raise InstallationError("--here 不能与业务仓库路径同时使用")
    return Path.cwd() if args.here or not args.path else Path(args.path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="zztt",
        description="安装和维护业务仓库中的 ZZTT Codex 项目级 Skills",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="初始化项目级 ZZTT Skills")
    _add_project_argument(init_parser)
    init_parser.add_argument(
        "--force",
        action="store_true",
        help="覆盖冲突的 ZZTT 受管文件，不影响其他 Skills 或 .zztt 业务产物",
    )

    update_parser = subparsers.add_parser("update", help="更新项目级 ZZTT Skills")
    _add_project_argument(update_parser)
    update_parser.add_argument(
        "--force",
        action="store_true",
        help="覆盖冲突的 ZZTT 受管文件，不影响其他 Skills 或 .zztt 业务产物",
    )

    check_parser = subparsers.add_parser("check", help="检查项目级安装状态")
    _add_project_argument(check_parser)

    subparsers.add_parser("version", help="显示 ZZTT CLI 版本")
    return parser


def _print_install_result(
    action: str,
    project_root: Path,
    result: InstallResult,
) -> None:
    print(f"{action}完成: {project_root}")
    print(
        "新增 {0.created}，更新 {0.updated}，删除 {0.deleted}，未变化 {0.unchanged}".format(
            result
        )
    )
    print("请新建 Codex 任务以加载更新后的项目级 Skills。")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "version":
            print(f"zztt-cli {__version__}")
            return 0

        project_root = _project_root(args).resolve()
        if args.command == "init":
            result = init_project(project_root, force=args.force)
            _print_install_result("初始化", project_root, result)
            return 0
        if args.command == "update":
            result = update_project(project_root, force=args.force)
            _print_install_result("更新", project_root, result)
            return 0

        status = check_project(project_root)
        print(f"项目: {project_root}")
        print(f"CLI 版本: {__version__}")
        print(f"项目安装版本: {status.installed_version}")
        if status.modified:
            print("已修改文件:")
            for path in status.modified:
                print(f"  - {path}")
        if status.missing:
            print("缺失文件:")
            for path in status.missing:
                print(f"  - {path}")
        if status.outdated:
            print("状态: 需要执行 zztt update")
        elif status.modified or status.missing:
            print("状态: 安装内容存在本地变化")
        else:
            print("状态: 正常")
        return 1 if status.outdated or status.modified or status.missing else 0
    except ConflictError as exc:
        print("检测到受管文件冲突，未写入任何文件：", file=sys.stderr)
        for conflict in exc.conflicts:
            print(f"  - {conflict}", file=sys.stderr)
        print("请人工合并，或确认后使用 --force 覆盖 ZZTT 受管文件。", file=sys.stderr)
        return 2
    except InstallationError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
