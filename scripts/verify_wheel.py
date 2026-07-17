from __future__ import annotations

import sys
import zipfile
from pathlib import Path


REQUIRED_SUFFIXES = (
    "zztt_cli/cli.py",
    "zztt_cli/installer.py",
    "zztt_cli/resources/skills/zztt-requirement-clarification/SKILL.md",
    "zztt_cli/resources/skills/zztt-workflow-shared/scripts/workflow_cli.py",
    "zztt_cli/resources/skills/zztt-workflow-shared/assets/templates/full/00-requirement.md",
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
        if name.endswith(".codex-plugin/plugin.json")
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
