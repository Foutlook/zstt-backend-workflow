from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SKILLS_ROOT = ROOT / "src" / "zstt_cli" / "resources" / "skills"
EXPECTED_SKILLS = {
    "zstt-artifact-analysis",
    "zstt-bug-fix",
    "zstt-code-review",
    "zstt-code-simplification",
    "zstt-implementation",
    "zstt-module-refactor",
    "zstt-product-feature-analysis",
    "zstt-repo-research",
    "zstt-prd-code-gap-analysis",
    "zstt-requirement-checklist",
    "zstt-requirement-clarification",
    "zstt-task-breakdown",
    "zstt-technical-design",
    "zstt-test-verify",
}
NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _read_utf8(path: Path) -> str:
    content = path.read_bytes()
    if content.startswith(b"\xef\xbb\xbf"):
        raise ValueError("文件包含 UTF-8 BOM")
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("文件不是有效的 UTF-8") from exc


def _parse_frontmatter(content: str) -> tuple[dict[str, str], str]:
    lines = content.splitlines()
    if not lines or lines[0] != "---":
        raise ValueError("缺少 YAML frontmatter")
    try:
        closing = lines.index("---", 1)
    except ValueError as exc:
        raise ValueError("YAML frontmatter 未闭合") from exc

    metadata: dict[str, str] = {}
    for line in lines[1:closing]:
        if not line.strip():
            continue
        if line[0].isspace():
            raise ValueError("frontmatter 只允许 name 和 description 平面字段")
        key, separator, value = line.partition(":")
        if not separator or not key.strip() or not value.strip():
            raise ValueError(f"frontmatter 字段格式无效: {line}")
        key = key.strip()
        if key in metadata:
            raise ValueError(f"frontmatter 字段重复: {key}")
        metadata[key] = value.strip().strip('"\'')
    return metadata, "\n".join(lines[closing + 1 :]).strip()


def validate_skill(skill_dir: Path) -> list[str]:
    errors: list[str] = []
    skill_md = skill_dir / "SKILL.md"
    metadata_path = skill_dir / "agents" / "openai.yaml"
    if not skill_md.is_file():
        return ["缺少 SKILL.md"]

    try:
        content = _read_utf8(skill_md)
        frontmatter, body = _parse_frontmatter(content)
    except (OSError, ValueError) as exc:
        return [str(exc)]

    unexpected = set(frontmatter).difference({"name", "description"})
    missing = {"name", "description"}.difference(frontmatter)
    if unexpected:
        errors.append("frontmatter 包含额外字段: " + ", ".join(sorted(unexpected)))
    if missing:
        errors.append("frontmatter 缺少字段: " + ", ".join(sorted(missing)))

    name = frontmatter.get("name", "")
    description = frontmatter.get("description", "")
    if name != skill_dir.name:
        errors.append(f"name 与目录名不一致: {name!r}")
    if not NAME_PATTERN.fullmatch(name) or len(name) > 64:
        errors.append("name 必须是不超过 64 字符的 hyphen-case")
    if not description:
        errors.append("description 不能为空")
    elif len(description) > 1024:
        errors.append("description 不能超过 1024 字符")
    elif "<" in description or ">" in description:
        errors.append("description 不能包含尖括号")
    if f"${skill_dir.name}" not in description:
        errors.append("description 必须声明显式 $skill-name 触发方式")
    if not body:
        errors.append("SKILL.md 正文不能为空")
    if len(content.splitlines()) >= 500:
        errors.append("SKILL.md 必须少于 500 行")

    if not metadata_path.is_file():
        errors.append("缺少 agents/openai.yaml")
    else:
        try:
            metadata = _read_utf8(metadata_path)
        except (OSError, ValueError) as exc:
            errors.append(f"agents/openai.yaml: {exc}")
        else:
            required_tokens = (
                f'display_name: "{skill_dir.name}"',
                "short_description:",
                "default_prompt:",
                f"${skill_dir.name}",
                "allow_implicit_invocation: false",
            )
            for token in required_tokens:
                if token not in metadata:
                    errors.append(f"agents/openai.yaml 缺少: {token}")
    return errors


def validate_all(skills_root: Path) -> list[str]:
    if not skills_root.is_dir():
        return [f"Skills 目录不存在: {skills_root}"]
    actual = {path.name for path in skills_root.iterdir() if path.is_dir()}
    errors: list[str] = []
    if actual != EXPECTED_SKILLS:
        missing = EXPECTED_SKILLS.difference(actual)
        unexpected = actual.difference(EXPECTED_SKILLS)
        if missing:
            errors.append("缺少 Skill 目录: " + ", ".join(sorted(missing)))
        if unexpected:
            errors.append("存在未登记 Skill 目录: " + ", ".join(sorted(unexpected)))

    for name in sorted(EXPECTED_SKILLS.intersection(actual)):
        for error in validate_skill(skills_root / name):
            errors.append(f"{name}: {error}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="校验 ZSTT Codex Skills 契约")
    parser.add_argument(
        "--skills-root",
        type=Path,
        default=DEFAULT_SKILLS_ROOT,
        help="Skills 根目录，默认校验仓库内资源",
    )
    args = parser.parse_args(argv)
    errors = validate_all(args.skills_root.resolve())
    if errors:
        for error in errors:
            print(f"错误: {error}", file=sys.stderr)
        return 1
    print(f"{len(EXPECTED_SKILLS)} 个 Skill 校验通过: {args.skills_root.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
