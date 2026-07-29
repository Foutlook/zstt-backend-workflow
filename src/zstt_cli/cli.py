from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from zstt_cli import __version__
from zstt_cli.diagnostics import (
    DoctorResult,
    diagnose_project,
    project_layout_warnings,
)
from zstt_cli.installer import (
    ConflictError,
    InstallResult,
    InstallationError,
    check_project,
    init_project,
    update_project,
)


def _configure_redirected_utf8() -> None:
    # Windows CI may redirect Python through CP1252 even though CLI messages are Chinese.
    # Keep interactive terminals unchanged, but make redirected output deterministic UTF-8.
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None and not stream.isatty():
            reconfigure(encoding="utf-8")


def _add_project_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("path", nargs="?", help="业务仓库路径，默认使用当前目录")
    parser.add_argument(
        "--here",
        action="store_true",
        help="显式使用当前目录；不能与 path 同时使用",
    )


def _add_json_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--json",
        action="store_true",
        help="输出机器可读的 JSON 结果",
    )


def _project_root(args: argparse.Namespace) -> Path:
    if args.here and args.path:
        raise InstallationError(
            "--here 不能与业务仓库路径同时使用",
            code="ZSTT_USAGE_INVALID",
        )
    return Path.cwd() if args.here or not args.path else Path(args.path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="zstt",
        description="安装和维护业务仓库中的 ZSTT Codex Skills、规则与运行时",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="初始化项目级 ZSTT 工作流")
    _add_project_argument(init_parser)
    init_parser.add_argument(
        "--force",
        action="store_true",
        help="覆盖冲突的 ZSTT 受管 Skills 和 .zstt-kit 内容，不影响业务产物",
    )
    _add_json_argument(init_parser)

    update_parser = subparsers.add_parser("update", help="更新项目级 ZSTT 工作流")
    _add_project_argument(update_parser)
    update_parser.add_argument(
        "--force",
        action="store_true",
        help="覆盖冲突的 ZSTT 受管 Skills 和 .zstt-kit 内容，不影响业务产物",
    )
    _add_json_argument(update_parser)

    check_parser = subparsers.add_parser("check", help="检查项目级安装状态")
    _add_project_argument(check_parser)
    _add_json_argument(check_parser)

    doctor_parser = subparsers.add_parser(
        "doctor",
        help="诊断 Git 仓库边界、Codex Skill 发现和安装状态",
    )
    _add_project_argument(doctor_parser)
    doctor_parser.add_argument(
        "--json",
        action="store_true",
        help="输出机器可读的 JSON 诊断结果",
    )

    subparsers.add_parser("version", help="显示 ZSTT CLI 版本")
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


def _print_layout_warnings(project_root: Path) -> None:
    for warning in project_layout_warnings(project_root):
        print(f"警告: {warning}", file=sys.stderr)


def _print_doctor_result(result: DoctorResult) -> None:
    data = result.as_dict()
    print(f"项目目录: {data['projectRoot']}")
    print(f"Git 根目录: {data['gitRoot'] or '未检测到'}")
    print(f"安装检查目录: {data['installationRoot']}")
    print(f"Skills 目录: {data['skillsRoot']}")
    print(
        "Skills: 已安装 {installed}/{expected}，缺失 {missing}".format(
            installed=len(data["installedSkills"]),
            expected=len(data["expectedSkills"]),
            missing=len(data["missingSkills"]),
        )
    )
    print(f"Codex 可发现: {'是' if data['codexDiscoverable'] else '否'}")
    print(f"安装状态: {data['installationStatus']}")
    for warning in data["warnings"]:
        print(f"警告: {warning}")
    print(f"诊断结果: {'正常' if data['healthy'] else '需要处理'}")


def _error_payload(
    operation: str,
    error: InstallationError,
    project_root: Path | None,
) -> dict[str, object]:
    return {
        "status": "BLOCKED",
        "operation": operation,
        "projectRoot": str(project_root) if project_root else None,
        "error": {
            "code": error.code,
            "message": str(error),
            "details": error.details,
        },
    }


def main(argv: list[str] | None = None) -> int:
    _configure_redirected_utf8()
    parser = build_parser()
    args = parser.parse_args(argv)
    project_root: Path | None = None
    layout_warnings: tuple[str, ...] = ()

    try:
        if args.command == "version":
            print(f"zstt-cli {__version__}")
            return 0

        project_root = _project_root(args).resolve()
        if args.command == "init":
            layout_warnings = project_layout_warnings(project_root)
            if not args.json:
                _print_layout_warnings(project_root)
            result = init_project(project_root, force=args.force)
            if args.json:
                print(
                    json.dumps(
                        {
                            "status": "PASS",
                            "operation": "init",
                            "projectRoot": str(project_root),
                            "changes": result.as_dict(),
                            "warnings": list(layout_warnings),
                        },
                        ensure_ascii=False,
                        indent=2,
                    )
                )
            else:
                _print_install_result("初始化", project_root, result)
            return 0
        if args.command == "update":
            layout_warnings = project_layout_warnings(project_root)
            if not args.json:
                _print_layout_warnings(project_root)
            result = update_project(project_root, force=args.force)
            if args.json:
                print(
                    json.dumps(
                        {
                            "status": "PASS",
                            "operation": "update",
                            "projectRoot": str(project_root),
                            "changes": result.as_dict(),
                            "warnings": list(layout_warnings),
                        },
                        ensure_ascii=False,
                        indent=2,
                    )
                )
            else:
                _print_install_result("更新", project_root, result)
            return 0
        if args.command == "doctor":
            result = diagnose_project(project_root)
            if args.json:
                print(json.dumps(result.as_dict(), ensure_ascii=False, indent=2))
            else:
                _print_doctor_result(result)
            return 0 if result.healthy else 1
        status = check_project(project_root)
        if args.json:
            healthy = not status.outdated and not status.modified and not status.missing
            print(
                json.dumps(
                    {
                        "status": "PASS" if healthy else "BLOCKED",
                        "operation": "check",
                        "projectRoot": str(project_root),
                        "installation": status.as_dict(),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 0 if healthy else 1
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
            print("状态: 需要执行 zstt update")
        elif status.modified or status.missing:
            print("状态: 安装内容存在本地变化")
        else:
            print("状态: 正常")
        return 1 if status.outdated or status.modified or status.missing else 0
    except ConflictError as exc:
        if getattr(args, "json", False):
            print(
                json.dumps(
                    _error_payload(args.command, exc, project_root),
                    ensure_ascii=False,
                    indent=2,
                )
            )
        else:
            print(
                f"[{exc.code}] 检测到受管文件冲突，未写入任何文件：",
                file=sys.stderr,
            )
            for conflict in exc.conflicts:
                print(f"  - {conflict}", file=sys.stderr)
            print(
                "请人工合并，或确认后使用 --force 覆盖 ZSTT 受管文件。",
                file=sys.stderr,
            )
        return 2
    except InstallationError as exc:
        if getattr(args, "json", False):
            payload = _error_payload(args.command, exc, project_root)
            if layout_warnings:
                payload["warnings"] = list(layout_warnings)
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(f"[{exc.code}] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
