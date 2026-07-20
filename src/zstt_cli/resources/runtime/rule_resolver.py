from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path, PurePosixPath
from typing import Any


CATALOG_SCHEMA_VERSION = 1
SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_RULES_ROOT = SCRIPT_DIR.parent / "rules"
DEFAULT_CATALOG_PATH = DEFAULT_RULES_ROOT / "catalog.json"


class RuleResolutionError(ValueError):
    """Raised when the rule catalog or a resolution request is invalid."""


def sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def normalize_context(value: str) -> str:
    return value.strip().lower().replace("_", "-")


def rule_path(rules_root: Path, relative_path: str) -> Path:
    relative = PurePosixPath(relative_path)
    if relative.is_absolute() or ".." in relative.parts or relative.suffix != ".md":
        raise RuleResolutionError(f"规则路径无效: {relative_path}")
    root = rules_root.resolve()
    target = root.joinpath(*relative.parts).resolve()
    if not target.is_relative_to(root):
        raise RuleResolutionError(f"规则路径超出 rules 目录: {relative_path}")
    return target


def load_catalog(
    rules_root: Path = DEFAULT_RULES_ROOT,
    catalog_path: Path | None = None,
) -> tuple[dict[str, Any], bytes]:
    path = (catalog_path or rules_root / "catalog.json").resolve()
    try:
        content = path.read_bytes()
        catalog = json.loads(content.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuleResolutionError(f"无法读取规则目录清单: {path}") from exc

    if catalog.get("schemaVersion") != CATALOG_SCHEMA_VERSION:
        raise RuleResolutionError("不支持的规则目录清单版本")
    if not isinstance(catalog.get("rulesetVersion"), str):
        raise RuleResolutionError("规则目录清单缺少 rulesetVersion")

    rule_types = catalog.get("ruleTypes")
    if not isinstance(rule_types, dict) or not rule_types:
        raise RuleResolutionError("规则目录清单缺少 ruleTypes")

    rules = catalog.get("rules")
    if not isinstance(rules, list) or not rules:
        raise RuleResolutionError("规则目录清单缺少 rules")

    seen_ids: set[str] = set()
    for entry in rules:
        if not isinstance(entry, dict):
            raise RuleResolutionError("规则条目必须是对象")
        rule_id = entry.get("id")
        rule_type = entry.get("type")
        relative_path = entry.get("path")
        selectors = entry.get("selectors")
        if not isinstance(rule_id, str) or not rule_id:
            raise RuleResolutionError("规则条目缺少 id")
        if rule_id in seen_ids:
            raise RuleResolutionError(f"规则 ID 重复: {rule_id}")
        seen_ids.add(rule_id)
        if rule_type not in rule_types:
            raise RuleResolutionError(f"规则类型无效: {rule_id} -> {rule_type}")
        if not isinstance(relative_path, str):
            raise RuleResolutionError(f"规则路径无效: {rule_id}")
        target = rule_path(rules_root, relative_path)
        if not target.is_file():
            raise RuleResolutionError(f"规则文件不存在: {relative_path}")
        try:
            rule_content = target.read_bytes()
        except OSError as exc:
            raise RuleResolutionError(f"无法读取规则文件: {relative_path}") from exc
        if rule_content.startswith(b"\xef\xbb\xbf"):
            raise RuleResolutionError(f"规则文件包含 UTF-8 BOM: {relative_path}")
        try:
            rule_content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise RuleResolutionError(f"规则文件不是有效 UTF-8: {relative_path}") from exc
        if not isinstance(entry.get("description"), str):
            raise RuleResolutionError(f"规则缺少描述: {rule_id}")
        if not isinstance(selectors, list) or not all(
            isinstance(selector, str) and selector == normalize_context(selector)
            for selector in selectors
        ):
            raise RuleResolutionError(f"规则 selectors 无效: {rule_id}")

    profiles = catalog.get("profiles")
    if not isinstance(profiles, dict) or not profiles:
        raise RuleResolutionError("规则目录清单缺少 profiles")
    for skill, rule_ids in profiles.items():
        if not isinstance(skill, str) or not skill.startswith("zstt-"):
            raise RuleResolutionError(f"Skill profile 名称无效: {skill}")
        if not isinstance(rule_ids, list) or not all(
            isinstance(rule_id, str) and rule_id in seen_ids for rule_id in rule_ids
        ):
            raise RuleResolutionError(f"Skill profile 包含未知规则: {skill}")

    return catalog, content


def available_contexts(catalog: dict[str, Any]) -> dict[str, list[str]]:
    contexts: dict[str, list[str]] = {}
    for entry in catalog["rules"]:
        for selector in entry["selectors"]:
            contexts.setdefault(selector, []).append(entry["id"])
    return dict(sorted(contexts.items()))


def resolve_rules(
    skill: str,
    contexts: list[str] | tuple[str, ...] = (),
    rules_root: Path = DEFAULT_RULES_ROOT,
    catalog_path: Path | None = None,
) -> dict[str, Any]:
    catalog, catalog_content = load_catalog(rules_root, catalog_path)
    profiles = catalog["profiles"]
    if skill not in profiles:
        raise RuleResolutionError(
            f"未知 Skill profile: {skill}；可用值: {', '.join(sorted(profiles))}"
        )

    normalized_contexts = list(
        dict.fromkeys(normalize_context(context) for context in contexts if context.strip())
    )
    contexts_index = available_contexts(catalog)
    unknown_contexts = [
        context for context in normalized_contexts if context not in contexts_index
    ]
    if unknown_contexts:
        raise RuleResolutionError(
            "未知上下文标签: "
            + ", ".join(unknown_contexts)
            + "；请先运行 list-contexts"
        )

    entries_by_id = {entry["id"]: entry for entry in catalog["rules"]}
    selected_ids: list[str] = []
    reasons: dict[str, list[str]] = {}

    for rule_id in profiles[skill]:
        if rule_id not in selected_ids:
            selected_ids.append(rule_id)
        reasons.setdefault(rule_id, []).append(f"profile:{skill}")

    for entry in catalog["rules"]:
        matching = [
            context
            for context in normalized_contexts
            if context in entry["selectors"]
        ]
        if not matching:
            continue
        rule_id = entry["id"]
        if rule_id not in selected_ids:
            selected_ids.append(rule_id)
        reasons.setdefault(rule_id, []).extend(
            f"context:{context}" for context in matching
        )

    resolved_rules: list[dict[str, Any]] = []
    for rule_id in selected_ids:
        entry = entries_by_id[rule_id]
        target = rule_path(rules_root, entry["path"])
        try:
            content = target.read_bytes()
        except OSError as exc:
            raise RuleResolutionError(f"无法读取规则文件: {entry['path']}") from exc
        resolved_rules.append(
            {
                "id": rule_id,
                "type": entry["type"],
                "description": entry["description"],
                "relativePath": f".zstt-kit/rules/{entry['path']}",
                "path": str(target),
                "sha256": sha256(content),
                "reasons": list(dict.fromkeys(reasons[rule_id])),
            }
        )

    fingerprint_source = {
        "rulesetVersion": catalog["rulesetVersion"],
        "catalogSha256": sha256(catalog_content),
        "skill": skill,
        "contexts": normalized_contexts,
        "rules": [
            {
                "id": rule["id"],
                "sha256": rule["sha256"],
                "reasons": rule["reasons"],
            }
            for rule in resolved_rules
        ],
    }
    fingerprint = sha256(
        json.dumps(
            fingerprint_source,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    )
    return {
        "schemaVersion": CATALOG_SCHEMA_VERSION,
        "rulesetVersion": catalog["rulesetVersion"],
        "catalogSha256": sha256(catalog_content),
        "rulesetFingerprint": fingerprint,
        "skill": skill,
        "contexts": normalized_contexts,
        "rules": resolved_rules,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ZSTT 动态规则解析器")
    subparsers = parser.add_subparsers(dest="command", required=True)

    resolve_parser = subparsers.add_parser("resolve", help="解析 Skill 需要读取的规则")
    resolve_parser.add_argument("--skill", required=True)
    resolve_parser.add_argument(
        "--context",
        action="append",
        default=[],
        help="根据实际代码范围确认的上下文标签，可重复传入",
    )

    subparsers.add_parser("list-contexts", help="列出可用上下文标签")
    subparsers.add_parser("check", help="校验规则目录清单和规则文件")
    return parser


def configure_stdio() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    configure_stdio()
    args = build_parser().parse_args(argv)
    try:
        catalog, content = load_catalog()
        if args.command == "resolve":
            result = resolve_rules(args.skill, args.context)
        elif args.command == "list-contexts":
            result = {
                "rulesetVersion": catalog["rulesetVersion"],
                "contexts": available_contexts(catalog),
            }
        else:
            result = {
                "valid": True,
                "rulesetVersion": catalog["rulesetVersion"],
                "catalogSha256": sha256(content),
                "ruleCount": len(catalog["rules"]),
                "profileCount": len(catalog["profiles"]),
            }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except RuleResolutionError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
