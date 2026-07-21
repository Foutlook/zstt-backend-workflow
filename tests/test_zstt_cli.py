from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from zstt_cli.cli import main  # noqa: E402
from zstt_cli.installer import (  # noqa: E402
    ConflictError,
    InstallationError,
    check_project,
    init_project,
    update_project,
)


def sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def read_manifest(project_root: Path) -> dict[str, object]:
    return json.loads(
        (project_root / ".zstt-kit" / "manifest.json").read_text(encoding="utf-8")
    )


def write_manifest(project_root: Path, manifest: dict[str, object]) -> None:
    (project_root / ".zstt-kit" / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def downgrade_to_v1_install_state(project_root: Path) -> tuple[Path, Path]:
    """Build a minimal 0.1-style state from a current temporary installation."""
    manifest = read_manifest(project_root)
    manifest["schemaVersion"] = 1
    manifest["toolVersion"] = "0.1.0"
    manifest["managedFiles"] = {
        path: metadata
        for path, metadata in manifest["managedFiles"].items()
        if path.startswith(".agents/skills/")
    }
    for directory in ("rules", "runtime", "templates"):
        shutil.rmtree(project_root / ".zstt-kit" / directory)

    shared = (
        project_root
        / ".agents"
        / "skills"
        / "zstt-workflow-shared"
        / "SKILL.md"
    )
    java_standard = (
        project_root
        / ".agents"
        / "skills"
        / "zstt-java-backend-standard"
        / "SKILL.md"
    )
    for path, content in (
        (shared, b"old shared skill\n"),
        (java_standard, b"old java standard\n"),
    ):
        path.parent.mkdir(parents=True)
        path.write_bytes(content)
        relative = path.relative_to(project_root).as_posix()
        manifest["managedFiles"][relative] = {"sha256": sha256(content)}
    write_manifest(project_root, manifest)
    return shared, java_standard


class ProjectInstallerTest(unittest.TestCase):
    def test_init_installs_project_skills_and_preserves_business_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            other_skill = project_root / ".agents" / "skills" / "other-skill" / "SKILL.md"
            other_skill.parent.mkdir(parents=True)
            other_skill.write_text("other\n", encoding="utf-8")
            business_artifact = project_root / ".zstt" / "features" / "existing" / "spec.md"
            business_artifact.parent.mkdir(parents=True)
            business_artifact.write_text("business\n", encoding="utf-8")

            result = init_project(project_root)

            self.assertGreater(result.created, 50)
            self.assertTrue(
                (
                    project_root
                    / ".agents"
                    / "skills"
                    / "zstt-requirement-clarification"
                    / "SKILL.md"
                ).is_file()
            )
            self.assertTrue(
                (project_root / ".zstt-kit" / "rules" / "catalog.json").is_file()
            )
            self.assertTrue(
                (project_root / ".zstt-kit" / "runtime" / "rule_resolver.py").is_file()
            )
            self.assertTrue(
                (project_root / ".zstt-kit" / "templates" / "full" / "00-requirement.md").is_file()
            )
            self.assertFalse(
                (project_root / ".agents" / "skills" / "zstt-workflow-shared").exists()
            )
            self.assertFalse(
                (project_root / ".agents" / "skills" / "zstt-java-backend-standard").exists()
            )
            self.assertEqual("other\n", other_skill.read_text(encoding="utf-8"))
            self.assertEqual("business\n", business_artifact.read_text(encoding="utf-8"))
            manifest_path = project_root / ".zstt-kit" / "manifest.json"
            self.assertFalse(manifest_path.read_bytes().startswith(b"\xef\xbb\xbf"))
            manifest = read_manifest(project_root)
            self.assertEqual(2, manifest["schemaVersion"])
            self.assertEqual("codex", manifest["integration"])
            self.assertFalse(
                any(
                    "__pycache__" in path or path.endswith((".pyc", ".pyo"))
                    for path in manifest["managedFiles"]
                )
            )
            self.assertFalse(check_project(project_root).outdated)

    def test_init_refuses_an_existing_install_without_force(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            init_project(project_root)

            with self.assertRaises(InstallationError):
                init_project(project_root)

    def test_init_does_not_claim_an_existing_different_zstt_skill(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            existing = (
                project_root
                / ".agents"
                / "skills"
                / "zstt-repo-research"
                / "SKILL.md"
            )
            existing.parent.mkdir(parents=True)
            existing.write_text("existing local skill\n", encoding="utf-8")

            with self.assertRaises(ConflictError):
                init_project(project_root)

            self.assertEqual("existing local skill\n", existing.read_text(encoding="utf-8"))
            self.assertFalse((project_root / ".zstt-kit" / "manifest.json").exists())

    def test_update_replaces_an_unmodified_old_managed_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            init_project(project_root)
            relative = ".agents/skills/zstt-repo-research/SKILL.md"
            target = project_root.joinpath(*relative.split("/"))
            expected = target.read_bytes()
            old_content = b"old managed content\n"
            target.write_bytes(old_content)
            manifest = read_manifest(project_root)
            manifest["managedFiles"][relative]["sha256"] = sha256(old_content)
            manifest["toolVersion"] = "0.0.1"
            write_manifest(project_root, manifest)

            result = update_project(project_root)

            self.assertGreaterEqual(result.updated, 1)
            self.assertEqual(expected, target.read_bytes())
            self.assertFalse(check_project(project_root).outdated)

    def test_update_reports_all_conflicts_before_writing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            init_project(project_root)
            relative = ".agents/skills/zstt-repo-research/SKILL.md"
            target = project_root.joinpath(*relative.split("/"))
            target.write_text("local customization\n", encoding="utf-8")
            manifest_before = (project_root / ".zstt-kit" / "manifest.json").read_bytes()

            with self.assertRaises(ConflictError) as context:
                update_project(project_root)

            self.assertIn(relative, context.exception.conflicts)
            self.assertEqual("local customization\n", target.read_text(encoding="utf-8"))
            self.assertEqual(
                manifest_before,
                (project_root / ".zstt-kit" / "manifest.json").read_bytes(),
            )

    def test_force_only_overwrites_zstt_managed_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            init_project(project_root)
            target = (
                project_root
                / ".agents"
                / "skills"
                / "zstt-repo-research"
                / "SKILL.md"
            )
            expected = (
                ROOT
                / "src"
                / "zstt_cli"
                / "resources"
                / "skills"
                / "zstt-repo-research"
                / "SKILL.md"
            ).read_bytes()
            target.write_text("local customization\n", encoding="utf-8")
            other_skill = project_root / ".agents" / "skills" / "other-skill" / "SKILL.md"
            other_skill.parent.mkdir(parents=True)
            other_skill.write_text("other\n", encoding="utf-8")

            update_project(project_root, force=True)

            self.assertEqual(expected, target.read_bytes())
            self.assertEqual("other\n", other_skill.read_text(encoding="utf-8"))

    def test_update_deletes_only_an_unmodified_obsolete_managed_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            init_project(project_root)
            relative = ".agents/skills/zstt-obsolete/SKILL.md"
            obsolete = project_root.joinpath(*relative.split("/"))
            obsolete.parent.mkdir(parents=True)
            content = b"obsolete\n"
            obsolete.write_bytes(content)
            manifest = read_manifest(project_root)
            manifest["managedFiles"][relative] = {"sha256": sha256(content)}
            write_manifest(project_root, manifest)

            result = update_project(project_root)

            self.assertEqual(1, result.deleted)
            self.assertFalse(obsolete.exists())

    def test_update_preserves_a_modified_obsolete_managed_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            init_project(project_root)
            relative = ".agents/skills/zstt-obsolete/SKILL.md"
            obsolete = project_root.joinpath(*relative.split("/"))
            obsolete.parent.mkdir(parents=True)
            original = b"obsolete\n"
            obsolete.write_bytes(original)
            manifest = read_manifest(project_root)
            manifest["managedFiles"][relative] = {"sha256": sha256(original)}
            write_manifest(project_root, manifest)
            obsolete.write_text("locally preserved\n", encoding="utf-8")

            with self.assertRaises(ConflictError):
                update_project(project_root)

            self.assertEqual("locally preserved\n", obsolete.read_text(encoding="utf-8"))

    def test_update_migrates_v1_manifest_and_removes_unmodified_internal_skills(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            init_project(project_root)
            shared, java_standard = downgrade_to_v1_install_state(project_root)

            result = update_project(project_root)

            self.assertGreaterEqual(result.created, 1)
            self.assertEqual(2, result.deleted)
            self.assertFalse(shared.exists())
            self.assertFalse(java_standard.exists())
            self.assertEqual(2, read_manifest(project_root)["schemaVersion"])
            self.assertTrue(
                (project_root / ".zstt-kit" / "runtime" / "rule_resolver.py").is_file()
            )
            self.assertFalse(check_project(project_root).outdated)

    def test_v1_migration_stops_when_an_internal_skill_was_modified(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            init_project(project_root)
            _, java_standard = downgrade_to_v1_install_state(project_root)
            java_standard.write_text("local java rules\n", encoding="utf-8")

            with self.assertRaises(ConflictError) as context:
                update_project(project_root)

            self.assertIn(
                ".agents/skills/zstt-java-backend-standard/SKILL.md",
                context.exception.conflicts,
            )
            self.assertEqual("local java rules\n", java_standard.read_text(encoding="utf-8"))
            self.assertFalse(
                (project_root / ".zstt-kit" / "runtime" / "rule_resolver.py").exists()
            )

    def test_force_updates_managed_rules_but_preserves_unmanaged_kit_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            init_project(project_root)
            rule = project_root / ".zstt-kit" / "rules" / "java" / "core.md"
            expected = rule.read_bytes()
            rule.write_text("local customization\n", encoding="utf-8")
            unmanaged = project_root / ".zstt-kit" / "team-notes.md"
            unmanaged.write_text("keep\n", encoding="utf-8")

            update_project(project_root, force=True)

            self.assertEqual(expected, rule.read_bytes())
            self.assertEqual("keep\n", unmanaged.read_text(encoding="utf-8"))

    def test_check_reports_modified_and_missing_managed_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            init_project(project_root)
            modified_relative = ".agents/skills/zstt-repo-research/SKILL.md"
            missing_relative = ".agents/skills/zstt-technical-design/SKILL.md"
            project_root.joinpath(*modified_relative.split("/")).write_text(
                "changed\n", encoding="utf-8"
            )
            project_root.joinpath(*missing_relative.split("/")).unlink()

            status = check_project(project_root)

            self.assertIn(modified_relative, status.modified)
            self.assertIn(missing_relative, status.missing)

    def test_manifest_cannot_expand_force_scope_outside_managed_roots(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            init_project(project_root)
            manifest = read_manifest(project_root)
            manifest["managedFiles"][".zstt/features/business/spec.md"] = {
                "sha256": sha256(b"business\n")
            }
            write_manifest(project_root, manifest)

            with self.assertRaises(InstallationError):
                update_project(project_root, force=True)


class CliTest(unittest.TestCase):
    def test_version_command(self) -> None:
        stdout = StringIO()
        with redirect_stdout(stdout):
            exit_code = main(["version"])

        self.assertEqual(0, exit_code)
        self.assertIn("zstt-cli 0.3.0", stdout.getvalue())

    def test_check_returns_nonzero_for_local_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            init_project(project_root)
            target = (
                project_root
                / ".agents"
                / "skills"
                / "zstt-repo-research"
                / "SKILL.md"
            )
            target.write_text("changed\n", encoding="utf-8")
            stdout = StringIO()
            stderr = StringIO()

            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = main(["check", str(project_root)])

            self.assertEqual(1, exit_code)
            self.assertIn("已修改文件", stdout.getvalue())
            self.assertEqual("", stderr.getvalue())

    def test_doctor_reports_healthy_git_repository_as_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            (project_root / ".git").mkdir()
            init_project(project_root)
            stdout = StringIO()

            with redirect_stdout(stdout):
                exit_code = main(["doctor", str(project_root), "--json"])

            result = json.loads(stdout.getvalue())
            self.assertEqual(0, exit_code)
            self.assertTrue(result["healthy"])
            self.assertTrue(result["codexDiscoverable"])
            self.assertEqual("normal", result["installationStatus"])
            self.assertEqual(9, len(result["expectedSkills"]))
            self.assertEqual([], result["missingSkills"])

    def test_doctor_uses_git_root_when_called_from_repository_subdirectory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            (project_root / ".git").mkdir()
            subdirectory = project_root / "module" / "src"
            subdirectory.mkdir(parents=True)
            init_project(project_root)
            stdout = StringIO()

            with redirect_stdout(stdout):
                exit_code = main(["doctor", str(subdirectory), "--json"])

            result = json.loads(stdout.getvalue())
            self.assertEqual(0, exit_code)
            self.assertEqual(str(project_root.resolve()), result["installationRoot"])
            self.assertTrue(result["codexDiscoverable"])

    def test_doctor_detects_parent_skills_outside_nested_git_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            init_project(workspace)
            nested_repository = workspace / "backend"
            (nested_repository / ".git").mkdir(parents=True)
            stdout = StringIO()

            with redirect_stdout(stdout):
                exit_code = main(["doctor", str(nested_repository), "--json"])

            result = json.loads(stdout.getvalue())
            self.assertEqual(1, exit_code)
            self.assertFalse(result["codexDiscoverable"])
            self.assertEqual(
                str(workspace / ".agents" / "skills"),
                result["parentSkillRoot"],
            )
            self.assertTrue(
                any("不会跨越" in warning for warning in result["warnings"])
            )

    def test_init_warns_when_parent_contains_nested_git_repositories(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            nested_repository = workspace / "backend"
            (nested_repository / ".git").mkdir(parents=True)
            stderr = StringIO()
            stdout = StringIO()

            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = main(["init", str(workspace)])

            self.assertEqual(0, exit_code)
            self.assertIn("直属子 Git 仓库", stderr.getvalue())
            self.assertIn(str(nested_repository), stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
