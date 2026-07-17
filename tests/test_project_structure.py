from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = ROOT / "plugins" / "zztt-backend-workflow"
SKILLS = PLUGIN_ROOT / "skills"

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

    def test_plugin_and_team_marketplace_manifests_exist(self) -> None:
        self.assertTrue((PLUGIN_ROOT / ".codex-plugin" / "plugin.json").is_file())
        self.assertTrue((ROOT / ".agents" / "plugins" / "marketplace.json").is_file())

    def test_plugin_and_team_marketplace_names_and_paths_match(self) -> None:
        plugin_manifest = json.loads(
            (PLUGIN_ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        marketplace = json.loads(
            (ROOT / ".agents" / "plugins" / "marketplace.json").read_text(
                encoding="utf-8"
            )
        )
        entry = next(
            item
            for item in marketplace["plugins"]
            if item["name"] == "zztt-backend-workflow"
        )

        self.assertEqual("zztt-backend-workflow", plugin_manifest["name"])
        self.assertEqual("zztt-team", marketplace["name"])
        self.assertEqual("./plugins/zztt-backend-workflow", entry["source"]["path"])
        self.assertEqual("AVAILABLE", entry["policy"]["installation"])
        self.assertEqual("ON_INSTALL", entry["policy"]["authentication"])

    def test_maintenance_scripts_exist(self) -> None:
        for name in ("validate.ps1", "dev-install.ps1", "release-check.ps1"):
            self.assertTrue((ROOT / "scripts" / name).is_file(), name)

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
