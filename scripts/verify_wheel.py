from __future__ import annotations

import sys
import zipfile
from pathlib import Path


REQUIRED_SUFFIXES = (
    "zstt_cli/cli.py",
    "zstt_cli/diagnostics.py",
    "zstt_cli/installer.py",
    "zstt_cli/resources/skills/zstt-artifact-analysis/SKILL.md",
    "zstt_cli/resources/skills/zstt-artifact-analysis/agents/openai.yaml",
    "zstt_cli/resources/skills/zstt-artifact-analysis/test-prompts.json",
    "zstt_cli/resources/skills/zstt-requirement-clarification/SKILL.md",
    "zstt_cli/resources/skills/zstt-requirement-checklist/SKILL.md",
    "zstt_cli/resources/skills/zstt-requirement-checklist/agents/openai.yaml",
    "zstt_cli/resources/skills/zstt-requirement-checklist/test-prompts.json",
    "zstt_cli/resources/rules/catalog.json",
    "zstt_cli/resources/rules/java/design-patterns.md",
    "zstt_cli/resources/runtime/rule_resolver.py",
    "zstt_cli/resources/runtime/quality_gates.py",
    "zstt_cli/resources/runtime/implementation_evidence.py",
    "zstt_cli/resources/runtime/with_env.py",
    "zstt_cli/resources/runtime/workflow_cli.py",
    "zstt_cli/resources/env/.env.example",
    "zstt_cli/resources/env/.env.prod.example",
    "zstt_cli/resources/env/.gitignore",
    "zstt_cli/resources/templates/full/00-requirement.md",
    "zstt_cli/resources/templates/quality-gates/requirement-checklist.md",
    "zstt_cli/resources/templates/quality-gates/artifact-analysis.md",
)

FORBIDDEN_SUFFIXES = (
    "zstt_cli/resources/skills/zstt-workflow-shared/SKILL.md",
    "zstt_cli/resources/skills/zstt-java-backend-standard/SKILL.md",
)


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: verify_wheel.py <wheel>", file=sys.stderr)
        return 2

    wheel_path = Path(sys.argv[1])
    with zipfile.ZipFile(wheel_path) as archive:
        names = set(archive.namelist())

    missing = [suffix for suffix in REQUIRED_SUFFIXES if suffix not in names]
    forbidden = [
        name
        for name in names
        if name in FORBIDDEN_SUFFIXES
        or name.endswith(".codex-plugin/plugin.json")
        or name.endswith(".agents/plugins/marketplace.json")
        or "/__pycache__/" in name
        or name.endswith((".pyc", ".pyo"))
    ]
    if missing:
        print(f"wheel is missing required files: {missing}", file=sys.stderr)
        return 1
    if forbidden:
        print(f"wheel contains plugin metadata: {forbidden}", file=sys.stderr)
        return 1
    print(f"Wheel content verified: {wheel_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
