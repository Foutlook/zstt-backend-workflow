from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from importlib.resources import files
from importlib.resources.abc import Traversable
from pathlib import Path, PurePosixPath
from typing import Iterator

from zstt_cli import __version__


MANIFEST_SCHEMA_VERSION = 2
SUPPORTED_MANIFEST_SCHEMA_VERSIONS = {1, MANIFEST_SCHEMA_VERSION}
MANIFEST_RELATIVE_PATH = PurePosixPath(".zstt-kit/manifest.json")
MANAGED_SKILLS_ROOT = PurePosixPath(".agents/skills")
MANAGED_RULES_ROOT = PurePosixPath(".zstt-kit/rules")
MANAGED_RUNTIME_ROOT = PurePosixPath(".zstt-kit/runtime")
MANAGED_TEMPLATES_ROOT = PurePosixPath(".zstt-kit/templates")
MANAGED_ENV_ROOT = PurePosixPath(".zstt-kit/.env")
PROJECT_DATABASES_RELATIVE_PATH = PurePosixPath(
    ".zstt-kit/project-databases.json"
)
INSTALL_LOCK_RELATIVE_PATH = PurePosixPath(".zstt-kit/.install.lock")
TRANSACTION_ROOT_RELATIVE_PATH = PurePosixPath(".zstt-kit/.transactions")
MANAGED_KIT_ROOTS = (
    MANAGED_RULES_ROOT,
    MANAGED_RUNTIME_ROOT,
    MANAGED_TEMPLATES_ROOT,
)
MANAGED_ENV_FILES = (
    MANAGED_ENV_ROOT / ".env.example",
    MANAGED_ENV_ROOT / ".env.prod.example",
    MANAGED_ENV_ROOT / ".gitignore",
)
RESOURCE_TARGETS = {
    "skills": MANAGED_SKILLS_ROOT,
    "rules": MANAGED_RULES_ROOT,
    "runtime": MANAGED_RUNTIME_ROOT,
    "templates": MANAGED_TEMPLATES_ROOT,
    "env": MANAGED_ENV_ROOT,
}
TOOL_NAME = "zstt-cli"


class InstallationError(RuntimeError):
    """Raised when a project-level installation cannot proceed safely."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "ZSTT_INSTALLATION_FAILED",
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.details = details or {}


class ConflictError(InstallationError):
    def __init__(self, conflicts: list[str]) -> None:
        super().__init__(
            "受管文件存在本地修改",
            code="ZSTT_INSTALL_CONFLICT",
            details={"conflicts": conflicts},
        )
        self.conflicts = conflicts


class RollbackError(InstallationError):
    """Raised when applying an install failed and the previous state was not restored."""

    def __init__(
        self,
        transaction_path: Path,
        apply_error: BaseException,
        rollback_failures: list[str],
    ) -> None:
        super().__init__(
            "安装失败且自动回滚未完整完成；请保留事务目录并人工恢复",
            code="ZSTT_INSTALL_ROLLBACK_FAILED",
            details={
                "transactionPath": str(transaction_path),
                "applyError": str(apply_error),
                "rollbackFailures": rollback_failures,
            },
        )


@dataclass(frozen=True)
class InstallResult:
    created: int
    updated: int
    deleted: int
    unchanged: int

    def as_dict(self) -> dict[str, int]:
        return {
            "created": self.created,
            "updated": self.updated,
            "deleted": self.deleted,
            "unchanged": self.unchanged,
        }


@dataclass(frozen=True)
class CheckResult:
    installed_version: str
    modified: tuple[str, ...]
    missing: tuple[str, ...]
    outdated: bool

    def as_dict(self) -> dict[str, object]:
        return {
            "installedVersion": self.installed_version,
            "modified": list(self.modified),
            "missing": list(self.missing),
            "outdated": self.outdated,
        }


@dataclass(frozen=True)
class _InstallAction:
    kind: str
    relative_path: str
    target: Path
    staged: Path | None
    existed: bool
    backup: Path | None


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _resource_files() -> dict[str, bytes]:
    resource_root = files("zstt_cli").joinpath("resources")
    result: dict[str, bytes] = {}

    def walk(
        node: Traversable,
        parts: tuple[str, ...],
        target_root: PurePosixPath,
    ) -> None:
        for child in sorted(node.iterdir(), key=lambda item: item.name):
            child_parts = (*parts, child.name)
            if child.is_dir() and child.name != "__pycache__":
                walk(child, child_parts, target_root)
            elif (
                child.is_file()
                and child.name != ".gitkeep"
                and not child.name.endswith((".pyc", ".pyo"))
            ):
                relative = PurePosixPath(target_root, *child_parts)
                result[relative.as_posix()] = child.read_bytes()

    for resource_name, target_root in RESOURCE_TARGETS.items():
        source = resource_root.joinpath(resource_name)
        if not source.is_dir():
            raise InstallationError(
                f"ZSTT CLI 包中缺少资源目录: {resource_name}",
                code="ZSTT_PACKAGE_INVALID",
                details={"resource": resource_name},
            )
        walk(source, (), target_root)
    if not result:
        raise InstallationError(
            "ZSTT CLI 包中没有可安装资源",
            code="ZSTT_PACKAGE_INVALID",
        )
    return result


def _normalize_project_root(project_root: Path) -> Path:
    resolved = project_root.resolve()
    if not resolved.is_dir():
        raise InstallationError(
            f"业务仓库目录不存在: {resolved}",
            code="ZSTT_PROJECT_ROOT_INVALID",
            details={"projectRoot": str(resolved)},
        )
    return resolved


def _managed_root(relative: PurePosixPath) -> PurePosixPath | None:
    parts = relative.parts
    if relative in MANAGED_ENV_FILES:
        return MANAGED_ENV_ROOT
    if (
        len(parts) >= 4
        and parts[:2] == MANAGED_SKILLS_ROOT.parts
        and parts[2].startswith("zstt-")
    ):
        return MANAGED_SKILLS_ROOT
    for root in MANAGED_KIT_ROOTS:
        if len(parts) > len(root.parts) and parts[: len(root.parts)] == root.parts:
            return root
    return None


def _validate_managed_path(relative_path: str) -> PurePosixPath:
    # Manifest 路径统一使用 POSIX 分隔符；Windows 会把反斜杠重新解释为
    # 原生分隔符，导致隐藏其中的 ".." 绕过 PurePosixPath 校验。
    if "\\" in relative_path:
        raise InstallationError(
            f"manifest 包含越界受管路径: {relative_path}",
            code="ZSTT_MANAGED_PATH_INVALID",
            details={"path": relative_path},
        )
    relative = PurePosixPath(relative_path)
    parts = relative.parts
    if (
        relative.is_absolute()
        or ".." in parts
        or _managed_root(relative) is None
    ):
        raise InstallationError(
            f"manifest 包含越界受管路径: {relative_path}",
            code="ZSTT_MANAGED_PATH_INVALID",
            details={"path": relative_path},
        )
    return relative


def _target_path(project_root: Path, relative_path: str) -> Path:
    relative = _validate_managed_path(relative_path)
    target = project_root.joinpath(*relative.parts)
    managed_root = _managed_root(relative)
    if managed_root is None:
        raise InstallationError(
            f"无法确定受管根目录: {relative_path}",
            code="ZSTT_MANAGED_PATH_INVALID",
            details={"path": relative_path},
        )
    resolved_target = target.resolve(strict=False)
    resolved_project_root = project_root.resolve(strict=False)
    resolved_managed_root = project_root.joinpath(*managed_root.parts).resolve(
        strict=False
    )
    if (
        not resolved_target.is_relative_to(resolved_project_root)
        or not resolved_target.is_relative_to(resolved_managed_root)
    ):
        raise InstallationError(
            f"受管路径超出允许范围: {relative_path}",
            code="ZSTT_MANAGED_PATH_INVALID",
            details={"path": relative_path},
        )
    return target


def _project_path(project_root: Path, relative: PurePosixPath) -> Path:
    if relative.is_absolute() or ".." in relative.parts:
        raise InstallationError(
            f"项目路径无效: {relative.as_posix()}",
            code="ZSTT_MANAGED_PATH_INVALID",
            details={"path": relative.as_posix()},
        )
    target = project_root.joinpath(*relative.parts)
    if not target.resolve(strict=False).is_relative_to(project_root):
        raise InstallationError(
            f"项目路径超出业务仓库: {relative.as_posix()}",
            code="ZSTT_MANAGED_PATH_INVALID",
            details={"path": relative.as_posix()},
        )
    return target


def _manifest_path(project_root: Path) -> Path:
    return _project_path(project_root, MANIFEST_RELATIVE_PATH)


def _load_manifest(project_root: Path, required: bool) -> dict[str, object] | None:
    path = _manifest_path(project_root)
    if not path.is_file():
        if required:
            raise InstallationError(
                "项目尚未初始化，请先执行 zstt init --here",
                code="ZSTT_NOT_INITIALIZED",
            )
        return None

    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InstallationError(
            f"无法读取安装清单: {path}",
            code="ZSTT_MANIFEST_INVALID",
            details={"path": str(path)},
        ) from exc

    if manifest.get("schemaVersion") not in SUPPORTED_MANIFEST_SCHEMA_VERSIONS:
        raise InstallationError(
            "不支持的 .zstt-kit/manifest.json 版本",
            code="ZSTT_MANIFEST_INVALID",
        )
    if manifest.get("tool") != TOOL_NAME:
        raise InstallationError(
            ".zstt-kit/manifest.json 不属于 zstt-cli",
            code="ZSTT_MANIFEST_INVALID",
        )
    managed_files = manifest.get("managedFiles")
    if not isinstance(managed_files, dict):
        raise InstallationError(
            "安装清单缺少 managedFiles",
            code="ZSTT_MANIFEST_INVALID",
        )
    for relative_path, metadata in managed_files.items():
        _validate_managed_path(str(relative_path))
        if not isinstance(metadata, dict) or not isinstance(metadata.get("sha256"), str):
            raise InstallationError(
                f"安装清单文件指纹无效: {relative_path}",
                code="ZSTT_MANIFEST_INVALID",
                details={"path": str(relative_path)},
            )
    return manifest


def _current_hash(path: Path) -> str | None:
    return _sha256(path.read_bytes()) if path.is_file() else None


def _atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.zstt-tmp")
    try:
        temporary.write_bytes(content)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _manifest_content(resource_files: dict[str, bytes]) -> bytes:
    manifest = {
        "schemaVersion": MANIFEST_SCHEMA_VERSION,
        "tool": TOOL_NAME,
        "toolVersion": __version__,
        "integration": "codex",
        "managedFiles": {
            relative_path: {"sha256": _sha256(content)}
            for relative_path, content in sorted(resource_files.items())
        },
    }
    return json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8") + b"\n"


def _process_is_alive(pid: object) -> bool:
    if not isinstance(pid, int) or pid <= 0:
        return False
    if os.name == "nt":
        return _windows_process_is_alive(pid)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _windows_process_is_alive(pid: int) -> bool:
    """Probe a Windows process without sending a signal or terminating it."""
    import ctypes
    from ctypes import wintypes

    if pid > 0xFFFFFFFF:
        return False

    # Windows 的 os.kill(pid, 0) 会走 TerminateProcess，不能用于 POSIX 式探活。
    process_query_limited_information = 0x1000
    still_active = 259
    error_access_denied = 5
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    open_process = kernel32.OpenProcess
    open_process.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    open_process.restype = wintypes.HANDLE
    get_exit_code_process = kernel32.GetExitCodeProcess
    get_exit_code_process.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(wintypes.DWORD),
    ]
    get_exit_code_process.restype = wintypes.BOOL
    close_handle = kernel32.CloseHandle
    close_handle.argtypes = [wintypes.HANDLE]
    close_handle.restype = wintypes.BOOL

    handle = open_process(process_query_limited_information, False, pid)
    if not handle:
        # 无权限查询的进程仍可能存活；安装锁必须保守处理，避免并发覆盖。
        return ctypes.get_last_error() == error_access_denied
    try:
        exit_code = wintypes.DWORD()
        if not get_exit_code_process(handle, ctypes.byref(exit_code)):
            return True
        return exit_code.value == still_active
    finally:
        close_handle(handle)


def _remove_empty_upwards(path: Path, limit: Path) -> None:
    current = path
    while current != limit and current.is_relative_to(limit):
        try:
            current.rmdir()
        except OSError:
            break
        current = current.parent


@contextmanager
def _installation_lock(project_root: Path) -> Iterator[None]:
    lock_path = _project_path(project_root, INSTALL_LOCK_RELATIVE_PATH)
    lock_parent_existed = lock_path.parent.exists()
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    for _attempt in range(2):
        try:
            descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            try:
                lock = json.loads(lock_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                lock = {}
            if _process_is_alive(lock.get("pid")):
                raise InstallationError(
                    "另一个 ZSTT 安装或更新正在运行",
                    code="ZSTT_INSTALL_LOCKED",
                    details={"lockPath": str(lock_path), "pid": lock.get("pid")},
                )
            try:
                lock_path.unlink()
            except OSError as exc:
                raise InstallationError(
                    "无法清理失效的安装锁",
                    code="ZSTT_INSTALL_LOCKED",
                    details={"lockPath": str(lock_path)},
                ) from exc
            continue
        else:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
                json.dump(
                    {"pid": os.getpid(), "nonce": uuid.uuid4().hex},
                    handle,
                    ensure_ascii=False,
                )
                handle.write("\n")
            break
    else:
        raise InstallationError(
            "无法获取 ZSTT 安装锁",
            code="ZSTT_INSTALL_LOCKED",
            details={"lockPath": str(lock_path)},
        )

    try:
        yield
    finally:
        try:
            lock_path.unlink(missing_ok=True)
        finally:
            if not lock_parent_existed:
                _remove_empty_upwards(lock_path.parent, project_root)


def _stage_path(stage_root: Path, relative_path: str) -> Path:
    relative = PurePosixPath(relative_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise InstallationError(
            f"暂存路径无效: {relative_path}",
            code="ZSTT_MANAGED_PATH_INVALID",
            details={"path": relative_path},
        )
    return stage_root.joinpath(*relative.parts)


def _prepare_install_stage(
    project_root: Path,
    writes: dict[str, bytes],
    resource_files: dict[str, bytes],
    create_project_databases: bool,
) -> Path:
    stage_root = Path(
        tempfile.mkdtemp(prefix=".zstt-stage-", dir=str(project_root.parent))
    )
    try:
        for relative_path, content in sorted(writes.items()):
            target = _stage_path(stage_root, relative_path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        if create_project_databases:
            target = _stage_path(
                stage_root,
                PROJECT_DATABASES_RELATIVE_PATH.as_posix(),
            )
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"{}\n")

        manifest = _stage_path(stage_root, MANIFEST_RELATIVE_PATH.as_posix())
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_bytes(_manifest_content(resource_files))
        parsed = json.loads(manifest.read_text(encoding="utf-8"))
        expected = {
            relative_path: {"sha256": _sha256(content)}
            for relative_path, content in sorted(resource_files.items())
        }
        if parsed.get("managedFiles") != expected:
            raise InstallationError(
                "暂存安装清单与候选资源不一致",
                code="ZSTT_INSTALL_STAGE_INVALID",
            )
        for relative_path, content in writes.items():
            if _stage_path(stage_root, relative_path).read_bytes() != content:
                raise InstallationError(
                    f"暂存文件校验失败: {relative_path}",
                    code="ZSTT_INSTALL_STAGE_INVALID",
                    details={"path": relative_path},
                )
        return stage_root
    except BaseException:
        shutil.rmtree(stage_root, ignore_errors=True)
        raise


def _commit_staged_file(staged: Path, target: Path) -> None:
    """Commit one prepared candidate; kept separate for fault-injection tests."""
    _atomic_write(target, staged.read_bytes())


def _missing_parent_paths(target: Path, project_root: Path) -> list[Path]:
    missing: list[Path] = []
    current = target.parent
    while current != project_root and current.is_relative_to(project_root):
        if current.exists():
            break
        missing.append(current)
        current = current.parent
    return missing


def _transactional_commit(
    project_root: Path,
    stage_root: Path,
    writes: dict[str, bytes],
    deletes: list[str],
    create_project_databases: bool,
) -> None:
    transaction_id = uuid.uuid4().hex
    transaction_root = _project_path(project_root, TRANSACTION_ROOT_RELATIVE_PATH)
    transaction_path = transaction_root / transaction_id
    backup_root = transaction_path / "backup"
    transaction_path.mkdir(parents=True, exist_ok=False)

    action_specs: list[tuple[str, str, Path | None]] = []
    for relative_path in sorted(deletes):
        action_specs.append(("delete", relative_path, None))
    for relative_path in sorted(writes):
        action_specs.append(
            ("write", relative_path, _stage_path(stage_root, relative_path))
        )
    if create_project_databases:
        relative_path = PROJECT_DATABASES_RELATIVE_PATH.as_posix()
        action_specs.append(
            ("write", relative_path, _stage_path(stage_root, relative_path))
        )
    action_specs.append(
        (
            "write",
            MANIFEST_RELATIVE_PATH.as_posix(),
            _stage_path(stage_root, MANIFEST_RELATIVE_PATH.as_posix()),
        )
    )

    actions: list[_InstallAction] = []
    created_parent_candidates: set[Path] = set()
    try:
        for kind, relative_path, staged in action_specs:
            relative = PurePosixPath(relative_path)
            target = _project_path(project_root, relative)
            if target.exists() and not target.is_file():
                raise InstallationError(
                    f"安装目标不是普通文件: {relative_path}",
                    code="ZSTT_INSTALL_TARGET_INVALID",
                    details={"path": relative_path},
                )
            created_parent_candidates.update(
                _missing_parent_paths(target, project_root)
            )
            existed = target.is_file()
            backup = backup_root.joinpath(*relative.parts)
            if existed:
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target, backup)
            actions.append(
                _InstallAction(
                    kind=kind,
                    relative_path=relative_path,
                    target=target,
                    staged=staged,
                    existed=existed,
                    backup=backup if existed else None,
                )
            )
        journal = {
            "schemaVersion": 1,
            "transactionId": transaction_id,
            "status": "prepared",
            "actions": [
                {
                    "kind": action.kind,
                    "relativePath": action.relative_path,
                    "existed": action.existed,
                }
                for action in actions
            ],
        }
        _atomic_write(
            transaction_path / "journal.json",
            json.dumps(journal, ensure_ascii=False, indent=2).encode("utf-8") + b"\n",
        )
    except BaseException:
        shutil.rmtree(transaction_path, ignore_errors=True)
        _remove_empty_upwards(transaction_root, project_root)
        raise

    try:
        for action in actions:
            if action.kind == "delete":
                action.target.unlink(missing_ok=True)
            else:
                if action.staged is None:
                    raise InstallationError(
                        f"写入操作缺少暂存文件: {action.relative_path}",
                        code="ZSTT_INSTALL_STAGE_INVALID",
                        details={"path": action.relative_path},
                    )
                _commit_staged_file(action.staged, action.target)
    except BaseException as apply_error:
        rollback_failures: list[str] = []
        for action in reversed(actions):
            try:
                if action.existed:
                    if action.backup is None:
                        raise OSError("缺少事务备份")
                    _atomic_write(action.target, action.backup.read_bytes())
                else:
                    action.target.unlink(missing_ok=True)
            except BaseException as rollback_error:
                rollback_failures.append(
                    f"{action.relative_path}: {rollback_error}"
                )
        for parent in sorted(
            created_parent_candidates,
            key=lambda path: len(path.parts),
            reverse=True,
        ):
            try:
                parent.rmdir()
            except OSError:
                pass
        if rollback_failures:
            raise RollbackError(
                transaction_path,
                apply_error,
                rollback_failures,
            ) from apply_error
        shutil.rmtree(transaction_path, ignore_errors=True)
        _remove_empty_upwards(transaction_root, project_root)
        raise InstallationError(
            "安装提交失败，已恢复变更前状态",
            code="ZSTT_INSTALL_APPLY_FAILED",
            details={"cause": str(apply_error)},
        ) from apply_error

    for relative_path in deletes:
        _remove_empty_parents(
            _target_path(project_root, relative_path),
            project_root,
            relative_path,
        )
    shutil.rmtree(transaction_path, ignore_errors=True)
    _remove_empty_upwards(transaction_root, project_root)


def _remove_empty_parents(
    path: Path,
    project_root: Path,
    relative_path: str,
) -> None:
    relative = _validate_managed_path(relative_path)
    root = _managed_root(relative)
    if root is None:
        raise InstallationError(f"无法确定受管根目录: {relative_path}")
    limit = project_root.joinpath(*root.parts)
    parent = path.parent
    while parent != limit and parent.is_relative_to(limit):
        try:
            parent.rmdir()
        except OSError:
            break
        parent = parent.parent


def _apply_install(
    project_root: Path,
    old_manifest: dict[str, object] | None,
    force: bool,
) -> InstallResult:
    resource_files = _resource_files()
    old_files = dict(old_manifest.get("managedFiles", {})) if old_manifest else {}
    writes: dict[str, bytes] = {}
    deletes: list[str] = []
    conflicts: list[str] = []
    created = 0
    updated = 0
    unchanged = 0

    for relative_path, content in resource_files.items():
        target = _target_path(project_root, relative_path)
        current_hash = _current_hash(target)
        new_hash = _sha256(content)
        old_metadata = old_files.get(relative_path)
        old_hash = old_metadata.get("sha256") if isinstance(old_metadata, dict) else None

        if current_hash is None:
            writes[relative_path] = content
            created += 1
        elif current_hash == new_hash:
            unchanged += 1
        elif old_hash is not None and current_hash == old_hash:
            writes[relative_path] = content
            updated += 1
        elif force:
            writes[relative_path] = content
            updated += 1
        else:
            conflicts.append(relative_path)

    for relative_path, metadata in old_files.items():
        if relative_path in resource_files:
            continue
        target = _target_path(project_root, relative_path)
        current_hash = _current_hash(target)
        old_hash = metadata.get("sha256") if isinstance(metadata, dict) else None
        if current_hash is None:
            continue
        if current_hash == old_hash or force:
            deletes.append(relative_path)
        else:
            conflicts.append(relative_path)

    if conflicts:
        raise ConflictError(sorted(set(conflicts)))

    project_databases = _project_path(
        project_root,
        PROJECT_DATABASES_RELATIVE_PATH,
    )
    config_created = not project_databases.exists()
    stage_root = _prepare_install_stage(
        project_root,
        writes,
        resource_files,
        config_created,
    )
    try:
        _transactional_commit(
            project_root,
            stage_root,
            writes,
            deletes,
            config_created,
        )
    finally:
        shutil.rmtree(stage_root, ignore_errors=True)

    return InstallResult(
        created=created + int(config_created),
        updated=updated,
        deleted=len(deletes),
        unchanged=unchanged,
    )


def init_project(project_root: Path, force: bool = False) -> InstallResult:
    project_root = _normalize_project_root(project_root)
    with _installation_lock(project_root):
        old_manifest = _load_manifest(project_root, required=False)
        if old_manifest is not None and not force:
            raise InstallationError(
                "项目已初始化，请使用 zstt update --here",
                code="ZSTT_ALREADY_INITIALIZED",
            )
        return _apply_install(project_root, old_manifest, force=force)


def update_project(project_root: Path, force: bool = False) -> InstallResult:
    project_root = _normalize_project_root(project_root)
    with _installation_lock(project_root):
        old_manifest = _load_manifest(project_root, required=True)
        return _apply_install(project_root, old_manifest, force=force)


def check_project(project_root: Path) -> CheckResult:
    project_root = _normalize_project_root(project_root)
    manifest = _load_manifest(project_root, required=True)
    managed_files = dict(manifest["managedFiles"])
    resource_files = _resource_files()
    modified: list[str] = []
    missing: list[str] = []

    for relative_path, metadata in managed_files.items():
        current_hash = _current_hash(_target_path(project_root, relative_path))
        if current_hash is None:
            missing.append(relative_path)
        elif current_hash != metadata["sha256"]:
            modified.append(relative_path)

    expected_hashes = {
        relative_path: _sha256(content)
        for relative_path, content in resource_files.items()
    }
    installed_hashes = {
        relative_path: metadata["sha256"]
        for relative_path, metadata in managed_files.items()
    }
    installed_version = str(manifest.get("toolVersion", "unknown"))
    outdated = (
        manifest.get("schemaVersion") != MANIFEST_SCHEMA_VERSION
        or installed_version != __version__
        or installed_hashes != expected_hashes
    )
    return CheckResult(
        installed_version=installed_version,
        modified=tuple(sorted(modified)),
        missing=tuple(sorted(missing)),
        outdated=outdated,
    )
