from __future__ import annotations

import tomllib
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = ROOT / "src" / "zstt_cli"
SKILLS = PACKAGE_ROOT / "resources" / "skills"
RULES = PACKAGE_ROOT / "resources" / "rules"
RUNTIME = PACKAGE_ROOT / "resources" / "runtime"
TEMPLATES = PACKAGE_ROOT / "resources" / "templates"
ENV_TEMPLATES = PACKAGE_ROOT / "resources" / "env"

EXPECTED_SKILLS = {
    "zstt-artifact-analysis",
    "zstt-bug-fix",
    "zstt-product-feature-analysis",
    "zstt-requirement-clarification",
    "zstt-repo-research",
    "zstt-requirement-checklist",
    "zstt-technical-design",
    "zstt-task-breakdown",
    "zstt-implementation",
    "zstt-code-review",
    "zstt-test-verify",
    "zstt-code-simplification",
    "zstt-module-refactor",
}


class ProjectStructureTest(unittest.TestCase):
    def test_readme_exists(self) -> None:
        self.assertTrue((ROOT / "README.md").is_file())

    def test_cli_package_and_entry_point_exist(self) -> None:
        self.assertTrue((PACKAGE_ROOT / "__init__.py").is_file())
        self.assertTrue((PACKAGE_ROOT / "cli.py").is_file())
        self.assertTrue((PACKAGE_ROOT / "installer.py").is_file())
        project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        self.assertEqual("zstt-cli", project["project"]["name"])
        self.assertEqual("zstt_cli.cli:main", project["project"]["scripts"]["zstt"])
        package_init = (PACKAGE_ROOT / "__init__.py").read_text(encoding="utf-8")
        self.assertIn(
            f'__version__ = "{project["project"]["version"]}"',
            package_init,
        )

    def test_codex_plugin_manifests_are_removed(self) -> None:
        self.assertFalse((ROOT / ".agents" / "plugins" / "marketplace.json").exists())
        self.assertFalse((ROOT / "plugins").exists())

    def test_maintenance_scripts_exist(self) -> None:
        self.assertTrue((ROOT / "scripts" / "validate.ps1").is_file())
        self.assertTrue((ROOT / "scripts" / "validate_skills.py").is_file())
        self.assertTrue((ROOT / ".github" / "workflows" / "ci.yml").is_file())
        self.assertTrue((ROOT / "CHANGELOG.md").is_file())

    def test_repository_skill_validator_passes_all_thirteen_skills(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "-X",
                "utf8",
                str(ROOT / "scripts" / "validate_skills.py"),
            ],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertIn("13 个 Skill 校验通过", completed.stdout)

    def test_all_skill_directories_exist(self) -> None:
        actual = {
            path.name
            for path in SKILLS.iterdir()
            if path.is_dir()
        }
        self.assertEqual(EXPECTED_SKILLS, actual)

    def test_internal_resources_are_not_exposed_as_skills(self) -> None:
        self.assertFalse((SKILLS / "zstt-workflow-shared").exists())
        self.assertFalse((SKILLS / "zstt-java-backend-standard").exists())
        self.assertTrue((RULES / "catalog.json").is_file())
        self.assertTrue((RUNTIME / "rule_resolver.py").is_file())
        self.assertTrue((RUNTIME / "quality_gates.py").is_file())
        self.assertTrue((RUNTIME / "implementation_evidence.py").is_file())
        self.assertTrue((RUNTIME / "workflow_cli.py").is_file())
        self.assertTrue((RUNTIME / "with_env.py").is_file())
        self.assertTrue((TEMPLATES / "full" / "00-requirement.md").is_file())
        self.assertTrue(
            (TEMPLATES / "quality-gates" / "requirement-checklist.md").is_file()
        )
        self.assertTrue(
            (TEMPLATES / "quality-gates" / "artifact-analysis.md").is_file()
        )
        self.assertTrue((ENV_TEMPLATES / ".env.example").is_file())
        self.assertTrue((ENV_TEMPLATES / ".env.prod.example").is_file())
        self.assertFalse((ENV_TEMPLATES / ".env.local").exists())

    def test_all_skills_have_explicit_only_codex_metadata(self) -> None:
        for skill in EXPECTED_SKILLS:
            metadata = SKILLS / skill / "agents" / "openai.yaml"
            self.assertTrue(metadata.is_file(), skill)
            text = metadata.read_text(encoding="utf-8")
            self.assertIn(f'display_name: "{skill}"', text, skill)
            self.assertIn("short_description:", text, skill)
            self.assertIn(f"${skill}", text, skill)
            self.assertIn("allow_implicit_invocation: false", text, skill)

    def test_text_files_do_not_have_utf8_bom(self) -> None:
        text_suffixes = {".md", ".py", ".ps1", ".json", ".yaml", ".yml", ".txt"}
        paths = [
            ROOT / ".gitignore",
            ENV_TEMPLATES / ".env.example",
            ENV_TEMPLATES / ".env.prod.example",
            ENV_TEMPLATES / ".gitignore",
        ]
        paths.extend(
            path
            for path in ROOT.rglob("*")
            if path.is_file() and path.suffix.lower() in text_suffixes
        )

        bom_paths = [
            str(path.relative_to(ROOT))
            for path in paths
            if path.read_bytes().startswith(b"\xef\xbb\xbf")
        ]
        self.assertEqual([], bom_paths)


if __name__ == "__main__":
    unittest.main()
