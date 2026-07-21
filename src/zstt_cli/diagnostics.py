from __future__ import annotations

from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path

from zstt_cli.installer import InstallationError, check_project


@dataclass(frozen=True)
class DoctorResult:
    project_root: Path
    git_root: Path | None
    installation_root: Path
    skills_root: Path
    expected_skills: tuple[str, ...]
    installed_skills: tuple[str, ...]
    missing_skills: tuple[str, ...]
    codex_discoverable: bool
    parent_skill_root: Path | None
    nested_git_roots: tuple[Path, ...]
    installation_status: str
    warnings: tuple[str, ...]
    healthy: bool

    def as_dict(self) -> dict[str, object]:
        return {
            "projectRoot": str(self.project_root),
            "gitRoot": str(self.git_root) if self.git_root else None,
            "installationRoot": str(self.installation_root),
            "skillsRoot": str(self.skills_root),
            "expectedSkills": list(self.expected_skills),
            "installedSkills": list(self.installed_skills),
            "missingSkills": list(self.missing_skills),
            "codexDiscoverable": self.codex_discoverable,
            "parentSkillRoot": str(self.parent_skill_root) if self.parent_skill_root else None,
            "nestedGitRoots": [str(path) for path in self.nested_git_roots],
            "installationStatus": self.installation_status,
            "warnings": list(self.warnings),
            "healthy": self.healthy,
        }


def _normalize_directory(path: Path) -> Path:
    resolved = path.resolve()
    if not resolved.is_dir():
        raise InstallationError(f"业务仓库目录不存在: {resolved}")
    return resolved


def find_git_root(path: Path) -> Path | None:
    current = _normalize_directory(path)
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists():
            return candidate
    return None


def find_nested_git_roots(path: Path) -> tuple[Path, ...]:
    root = _normalize_directory(path)
    return tuple(
        child
        for child in sorted(root.iterdir(), key=lambda item: item.name.lower())
        if child.is_dir() and (child / ".git").exists()
    )


def expected_skill_names() -> tuple[str, ...]:
    skills = files("zstt_cli").joinpath("resources", "skills")
    if not skills.is_dir():
        raise InstallationError("ZSTT CLI 包中缺少 Skills 资源目录")
    return tuple(
        child.name
        for child in sorted(skills.iterdir(), key=lambda item: item.name)
        if child.is_dir() and child.name.startswith("zstt-")
    )


def _installed_skill_names(skills_root: Path) -> tuple[str, ...]:
    if not skills_root.is_dir():
        return ()
    return tuple(
        child.name
        for child in sorted(skills_root.iterdir(), key=lambda item: item.name)
        if child.is_dir()
        and child.name.startswith("zstt-")
        and (child / "SKILL.md").is_file()
    )


def _find_parent_skill_root(
    project_root: Path,
    expected_skills: tuple[str, ...],
) -> Path | None:
    for parent in project_root.parents:
        skills_root = parent / ".agents" / "skills"
        installed = set(_installed_skill_names(skills_root))
        if installed.intersection(expected_skills):
            return skills_root
    return None


def project_layout_warnings(project_root: Path) -> tuple[str, ...]:
    root = _normalize_directory(project_root)
    git_root = find_git_root(root)
    warnings: list[str] = []
    if git_root is None:
        warnings.append(
            "当前目录不在 Git 仓库中；Codex 无法按仓库边界稳定发现项目级 Skills。"
        )
    elif root != git_root:
        warnings.append(
            f"当前目录不是 Git 仓库根目录；建议改在 {git_root} 执行命令。"
        )

    nested = find_nested_git_roots(root)
    if nested:
        warnings.append(
            "检测到直属子 Git 仓库；父目录安装的 Skills 不会跨越这些仓库边界："
            + "、".join(str(path) for path in nested)
        )
    return tuple(warnings)


def diagnose_project(project_root: Path) -> DoctorResult:
    root = _normalize_directory(project_root)
    git_root = find_git_root(root)
    # 用户可能从仓库子目录执行 doctor；诊断应落到 Codex 实际使用的仓库根目录。
    installation_root = git_root or root
    skills_root = installation_root / ".agents" / "skills"
    expected = expected_skill_names()
    installed = _installed_skill_names(skills_root)
    missing = tuple(sorted(set(expected).difference(installed)))
    parent_skill_root = _find_parent_skill_root(installation_root, expected)
    nested = find_nested_git_roots(installation_root)
    warnings = list(project_layout_warnings(root))

    manifest_path = installation_root / ".zstt-kit" / "manifest.json"
    try:
        status = check_project(installation_root)
    except InstallationError as exc:
        installation_status = "invalid" if manifest_path.exists() else "uninitialized"
        if installation_status == "invalid":
            warnings.append(f"安装清单无效：{exc}")
        else:
            warnings.append(
                f"仓库尚未初始化；请在 {installation_root} 执行 zstt init --here。"
            )
    else:
        if status.outdated:
            installation_status = "outdated"
            warnings.append("项目安装版本已过期；请执行 zstt update --here。")
        elif status.modified or status.missing:
            installation_status = "local_changes"
            warnings.append("ZSTT 受管文件存在本地修改或缺失，请先检查差异。")
        else:
            installation_status = "normal"

    if missing:
        warnings.append("当前仓库缺少项目级 Skills：" + "、".join(missing))
    if git_root is not None and missing and parent_skill_root is not None:
        warnings.append(
            f"发现仓库边界外的 Skills：{parent_skill_root}；Codex 不会跨越 "
            f"{git_root} 的 Git 边界加载它们。"
        )

    codex_discoverable = git_root is not None and not missing
    healthy = codex_discoverable and installation_status == "normal"
    return DoctorResult(
        project_root=root,
        git_root=git_root,
        installation_root=installation_root,
        skills_root=skills_root,
        expected_skills=expected,
        installed_skills=installed,
        missing_skills=missing,
        codex_discoverable=codex_discoverable,
        parent_skill_root=parent_skill_root,
        nested_git_roots=nested,
        installation_status=installation_status,
        warnings=tuple(dict.fromkeys(warnings)),
        healthy=healthy,
    )
