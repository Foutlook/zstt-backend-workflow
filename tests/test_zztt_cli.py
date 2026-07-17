from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from zztt_cli.cli import main  # noqa: E402
from zztt_cli.installer import (  # noqa: E402
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
        (project_root / ".zztt-kit" / "manifest.json").read_text(encoding="utf-8")
    )


def write_manifest(project_root: Path, manifest: dict[str, object]) -> None:
    (project_root / ".zztt-kit" / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


class ProjectInstallerTest(unittest.TestCase):
    def test_init_installs_project_skills_and_preserves_business_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            other_skill = project_root / ".agents" / "skills" / "other-skill" / "SKILL.md"
            other_skill.parent.mkdir(parents=True)
            other_skill.write_text("other\n", encoding="utf-8")
            business_artifact = project_root / ".zztt" / "features" / "existing" / "spec.md"
            business_artifact.parent.mkdir(parents=True)
            business_artifact.write_text("business\n", encoding="utf-8")

            result = init_project(project_root)

            self.assertGreater(result.created, 50)
            self.assertTrue(
                (
                    project_root
                    / ".agents"
                    / "skills"
                    / "zztt-requirement-clarification"
                    / "SKILL.md"
                ).is_file()
            )
            self.assertEqual("other\n", other_skill.read_text(encoding="utf-8"))
            self.assertEqual("business\n", business_artifact.read_text(encoding="utf-8"))
            manifest_path = project_root / ".zztt-kit" / "manifest.json"
            self.assertFalse(manifest_path.read_bytes().startswith(b"\xef\xbb\xbf"))
            manifest = read_manifest(project_root)
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

    def test_init_does_not_claim_an_existing_different_zztt_skill(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            existing = (
                project_root
                / ".agents"
                / "skills"
                / "zztt-repo-research"
                / "SKILL.md"
            )
            existing.parent.mkdir(parents=True)
            existing.write_text("existing local skill\n", encoding="utf-8")

            with self.assertRaises(ConflictError):
                init_project(project_root)

            self.assertEqual("existing local skill\n", existing.read_text(encoding="utf-8"))
            self.assertFalse((project_root / ".zztt-kit" / "manifest.json").exists())

    def test_update_replaces_an_unmodified_old_managed_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            init_project(project_root)
            relative = ".agents/skills/zztt-repo-research/SKILL.md"
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
            relative = ".agents/skills/zztt-repo-research/SKILL.md"
            target = project_root.joinpath(*relative.split("/"))
            target.write_text("local customization\n", encoding="utf-8")
            manifest_before = (project_root / ".zztt-kit" / "manifest.json").read_bytes()

            with self.assertRaises(ConflictError) as context:
                update_project(project_root)

            self.assertIn(relative, context.exception.conflicts)
            self.assertEqual("local customization\n", target.read_text(encoding="utf-8"))
            self.assertEqual(
                manifest_before,
                (project_root / ".zztt-kit" / "manifest.json").read_bytes(),
            )

    def test_force_only_overwrites_zztt_managed_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            init_project(project_root)
            target = (
                project_root
                / ".agents"
                / "skills"
                / "zztt-repo-research"
                / "SKILL.md"
            )
            expected = (
                ROOT
                / "src"
                / "zztt_cli"
                / "resources"
                / "skills"
                / "zztt-repo-research"
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
            relative = ".agents/skills/zztt-obsolete/SKILL.md"
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
            relative = ".agents/skills/zztt-obsolete/SKILL.md"
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

    def test_check_reports_modified_and_missing_managed_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            init_project(project_root)
            modified_relative = ".agents/skills/zztt-repo-research/SKILL.md"
            missing_relative = ".agents/skills/zztt-technical-design/SKILL.md"
            project_root.joinpath(*modified_relative.split("/")).write_text(
                "changed\n", encoding="utf-8"
            )
            project_root.joinpath(*missing_relative.split("/")).unlink()

            status = check_project(project_root)

            self.assertIn(modified_relative, status.modified)
            self.assertIn(missing_relative, status.missing)

    def test_manifest_cannot_expand_force_scope_outside_zztt_skills(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            init_project(project_root)
            manifest = read_manifest(project_root)
            manifest["managedFiles"][".zztt/features/business/spec.md"] = {
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
        self.assertIn("zztt-cli 0.1.0", stdout.getvalue())

    def test_check_returns_nonzero_for_local_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            init_project(project_root)
            target = (
                project_root
                / ".agents"
                / "skills"
                / "zztt-repo-research"
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


if __name__ == "__main__":
    unittest.main()
