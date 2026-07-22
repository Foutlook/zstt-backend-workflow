from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from importlib.resources import files
from importlib.resources.abc import Traversable
from pathlib import Path, PurePosixPath

from zstt_cli import __version__


MANIFEST_SCHEMA_VERSION = 2
SUPPORTED_MANIFEST_SCHEMA_VERSIONS = {1, MANIFEST_SCHEMA_VERSION}
MANIFEST_RELATIVE_PATH = PurePosixPath(".zstt-kit/manifest.json")
MANAGED_SKILLS_ROOT = PurePosixPath(".agents/skills")
MANAGED_RULES_ROOT = PurePosixPath(".zstt-kit/rules")
MANAGED_RUNTIME_ROOT = PurePosixPath(".zstt-kit/runtime")
MANAGED_TEMPLATES_ROOT = PurePosixPath(".zstt-kit/templates")
MANAGED_ENV_ROOT = PurePosixPath(".zstt-kit/.env")
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


class ConflictError(InstallationError):
    def __init__(self, conflicts: list[str]) -> None:
        super().__init__("受管文件存在本地修改")
        self.conflicts = conflicts


@dataclass(frozen=True)
class InstallResult:
    created: int
    updated: int
    deleted: int
    unchanged: int


@dataclass(frozen=True)
class CheckResult:
    installed_version: str
    modified: tuple[str, ...]
    missing: tuple[str, ...]
    outdated: bool


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
            raise InstallationError(f"ZSTT CLI 包中缺少资源目录: {resource_name}")
        walk(source, (), target_root)
    if not result:
        raise InstallationError("ZSTT CLI 包中没有可安装资源")
    return result


def _normalize_project_root(project_root: Path) -> Path:
    resolved = project_root.resolve()
    if not resolved.is_dir():
        raise InstallationError(f"业务仓库目录不存在: {resolved}")
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
    relative = PurePosixPath(relative_path)
    parts = relative.parts
    if (
        relative.is_absolute()
        or ".." in parts
        or _managed_root(relative) is None
    ):
        raise InstallationError(f"manifest 包含越界受管路径: {relative_path}")
    return relative


def _target_path(project_root: Path, relative_path: str) -> Path:
    relative = _validate_managed_path(relative_path)
    target = project_root.joinpath(*relative.parts)
    if not target.resolve(strict=False).is_relative_to(project_root):
        raise InstallationError(f"受管路径超出业务仓库: {relative_path}")
    return target


def _manifest_path(project_root: Path) -> Path:
    path = project_root.joinpath(*MANIFEST_RELATIVE_PATH.parts)
    if not path.resolve(strict=False).is_relative_to(project_root):
        raise InstallationError(".zstt-kit/manifest.json 超出业务仓库")
    return path


def _load_manifest(project_root: Path, required: bool) -> dict[str, object] | None:
    path = _manifest_path(project_root)
    if not path.is_file():
        if required:
            raise InstallationError("项目尚未初始化，请先执行 zstt init --here")
        return None

    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InstallationError(f"无法读取安装清单: {path}") from exc

    if manifest.get("schemaVersion") not in SUPPORTED_MANIFEST_SCHEMA_VERSIONS:
        raise InstallationError("不支持的 .zstt-kit/manifest.json 版本")
    if manifest.get("tool") != TOOL_NAME:
        raise InstallationError(".zstt-kit/manifest.json 不属于 zstt-cli")
    managed_files = manifest.get("managedFiles")
    if not isinstance(managed_files, dict):
        raise InstallationError("安装清单缺少 managedFiles")
    for relative_path, metadata in managed_files.items():
        _validate_managed_path(str(relative_path))
        if not isinstance(metadata, dict) or not isinstance(metadata.get("sha256"), str):
            raise InstallationError(f"安装清单文件指纹无效: {relative_path}")
    return manifest


def _current_hash(path: Path) -> str | None:
    return _sha256(path.read_bytes()) if path.is_file() else None


def _atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.zstt-tmp")
    try:
        temporary.write_bytes(content)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _write_manifest(project_root: Path, resource_files: dict[str, bytes]) -> None:
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
    content = json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8") + b"\n"
    _atomic_write(_manifest_path(project_root), content)


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

    for relative_path in deletes:
        target = _target_path(project_root, relative_path)
        target.unlink()
        _remove_empty_parents(target, project_root, relative_path)
    for relative_path, content in writes.items():
        _atomic_write(_target_path(project_root, relative_path), content)
    _write_manifest(project_root, resource_files)

    return InstallResult(
        created=created,
        updated=updated,
        deleted=len(deletes),
        unchanged=unchanged,
    )


def init_project(project_root: Path, force: bool = False) -> InstallResult:
    project_root = _normalize_project_root(project_root)
    old_manifest = _load_manifest(project_root, required=False)
    if old_manifest is not None and not force:
        raise InstallationError("项目已初始化，请使用 zstt update --here")
    return _apply_install(project_root, old_manifest, force=force)


def update_project(project_root: Path, force: bool = False) -> InstallResult:
    project_root = _normalize_project_root(project_root)
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
