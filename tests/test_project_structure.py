from __future__ import annotations

import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = ROOT / "src" / "zztt_cli"
SKILLS = PACKAGE_ROOT / "resources" / "skills"

EXPECTED_SKILLS = {
    "zztt-requirement-clarification",
    "zztt-repo-research",
    "zztt-technical-design",
    "zztt-task-breakdown",
    "zztt-implementation",
    "zztt-code-review",
    "zztt-test-verify",
    "zztt-code-simplification",
    "zztt-java-backend-standard",
    "zztt-module-refactor",
    "zztt-workflow-shared",
}


class ProjectStructureTest(unittest.TestCase):
    def test_readme_exists(self) -> None:
        self.assertTrue((ROOT / "README.md").is_file())

    def test_cli_package_and_entry_point_exist(self) -> None:
        self.assertTrue((PACKAGE_ROOT / "__init__.py").is_file())
        self.assertTrue((PACKAGE_ROOT / "cli.py").is_file())
        self.assertTrue((PACKAGE_ROOT / "installer.py").is_file())
        project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        self.assertEqual("zztt-cli", project["project"]["name"])
        self.assertEqual("zztt_cli.cli:main", project["project"]["scripts"]["zztt"])
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

    def test_all_skill_directories_exist(self) -> None:
        actual = {
            path.name
            for path in SKILLS.iterdir()
            if path.is_dir()
        }
        self.assertEqual(EXPECTED_SKILLS, actual)

    def test_shared_script_directory_exists(self) -> None:
        self.assertTrue((SKILLS / "zztt-workflow-shared" / "scripts").is_dir())

    def test_all_skills_have_explicit_only_codex_metadata(self) -> None:
        for skill in EXPECTED_SKILLS:
            metadata = SKILLS / skill / "agents" / "openai.yaml"
            self.assertTrue(metadata.is_file(), skill)
            text = metadata.read_text(encoding="utf-8")
            self.assertIn("display_name:", text, skill)
            self.assertIn("short_description:", text, skill)
            self.assertIn(f"${skill}", text, skill)
            self.assertIn("allow_implicit_invocation: false", text, skill)

    def test_text_files_do_not_have_utf8_bom(self) -> None:
        text_suffixes = {".md", ".py", ".ps1", ".json", ".yaml", ".yml", ".txt"}
        paths = [ROOT / ".gitignore"]
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
