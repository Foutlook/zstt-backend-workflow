from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "skills" / "zztt-workflow-shared" / "scripts" / "workflow_cli.py"


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def replace_frontmatter_value(path: Path, key: str, value: str) -> None:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    prefix = f"{key}:"
    for index, line in enumerate(lines):
        if line.startswith(prefix):
            lines[index] = f"{key}: {value}"
            path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
            return
    raise AssertionError(f"frontmatter key not found: {key}")


def init_feature(repo_root: Path, mode: str = "full") -> Path:
    name = "学习报告"
    completed = run_cli(
        "init",
        "--repo-root",
        str(repo_root),
        "--mode",
        mode,
        "--feature-name",
        name,
        "--date",
        "20260716",
    )
    if completed.returncode != 0:
        raise AssertionError(completed.stderr)
    category = "features" if mode == "full" else "quick"
    return repo_root / ".zztt" / category / f"20260716-{name}"


class WorkflowCliInitTest(unittest.TestCase):
    def test_init_full_creates_only_meta_and_requirement(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)

            completed = run_cli(
                "init",
                "--repo-root",
                str(repo_root),
                "--mode",
                "full",
                "--feature-name",
                "学习报告",
                "--date",
                "20260716",
            )

            self.assertEqual(0, completed.returncode, completed.stderr)
            feature_dir = repo_root / ".zztt" / "features" / "20260716-学习报告"
            self.assertEqual(
                {"meta.json", "00-requirement.md"},
                {path.name for path in feature_dir.iterdir()},
            )
            meta = json.loads((feature_dir / "meta.json").read_text(encoding="utf-8"))
            self.assertEqual("full", meta["mode"])
            self.assertEqual("requirement_clarification", meta["current_stage"])
            self.assertEqual([], meta["completed_stages"])
            self.assertEqual(
                "zztt-requirement-clarification",
                meta["recommended_next_skill"],
            )

    def test_init_quick_uses_quick_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)

            completed = run_cli(
                "init",
                "--repo-root",
                str(repo_root),
                "--mode",
                "quick",
                "--feature-name",
                "修正文案",
                "--date",
                "20260716",
            )

            self.assertEqual(0, completed.returncode, completed.stderr)
            feature_dir = repo_root / ".zztt" / "quick" / "20260716-修正文案"
            requirement = (feature_dir / "00-requirement.md").read_text(encoding="utf-8")
            self.assertIn("mode: quick", requirement)

    def test_init_refuses_to_overwrite_existing_feature(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            args = (
                "init",
                "--repo-root",
                tmp,
                "--mode",
                "full",
                "--feature-name",
                "学习报告",
                "--date",
                "20260716",
            )
            self.assertEqual(0, run_cli(*args).returncode)

            second = run_cli(*args)

            self.assertNotEqual(0, second.returncode)
            self.assertIn("已存在", second.stderr)

    def test_status_outputs_machine_readable_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_cli(
                "init",
                "--repo-root",
                tmp,
                "--mode",
                "full",
                "--feature-name",
                "学习报告",
                "--date",
                "20260716",
            )
            feature_dir = Path(tmp) / ".zztt" / "features" / "20260716-学习报告"

            completed = run_cli("status", "--feature-dir", str(feature_dir))

            self.assertEqual(0, completed.returncode, completed.stderr)
            status = json.loads(completed.stdout)
            self.assertEqual("full", status["mode"])
            self.assertEqual("00-requirement.md", status["artifacts"]["requirement_clarification"])

    def test_generated_text_has_no_utf8_bom(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_cli(
                "init",
                "--repo-root",
                tmp,
                "--mode",
                "full",
                "--feature-name",
                "学习报告",
                "--date",
                "20260716",
            )
            feature_dir = Path(tmp) / ".zztt" / "features" / "20260716-学习报告"
            for path in feature_dir.iterdir():
                self.assertFalse(path.read_bytes().startswith(b"\xef\xbb\xbf"), path.name)


class WorkflowCliGateTest(unittest.TestCase):
    def test_complete_stage_requires_completed_status_and_required_headings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            feature_dir = init_feature(Path(tmp))
            requirement = feature_dir / "00-requirement.md"
            replace_frontmatter_value(requirement, "status", "completed")
            text = requirement.read_text(encoding="utf-8")
            requirement.write_text(
                text.replace("## 7. 验收标准\n", ""),
                encoding="utf-8",
                newline="\n",
            )

            completed = run_cli(
                "complete-stage",
                "--feature-dir",
                str(feature_dir),
                "--stage",
                "requirement_clarification",
            )

            self.assertNotEqual(0, completed.returncode)
            self.assertIn("缺少必需章节", completed.stderr)

    def test_p0_blocks_completion_without_advancing_meta(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            feature_dir = init_feature(Path(tmp))
            requirement = feature_dir / "00-requirement.md"
            replace_frontmatter_value(requirement, "status", "completed")
            replace_frontmatter_value(requirement, "blocking_p0_count", "1")

            completed = run_cli(
                "complete-stage",
                "--feature-dir",
                str(feature_dir),
                "--stage",
                "requirement_clarification",
            )

            self.assertNotEqual(0, completed.returncode)
            self.assertIn("P0", completed.stderr)
            meta = json.loads((feature_dir / "meta.json").read_text(encoding="utf-8"))
            self.assertEqual([], meta["completed_stages"])

    def test_complete_then_prepare_creates_only_requested_stage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            feature_dir = init_feature(Path(tmp))
            requirement = feature_dir / "00-requirement.md"
            replace_frontmatter_value(requirement, "status", "completed")
            complete = run_cli(
                "complete-stage",
                "--feature-dir",
                str(feature_dir),
                "--stage",
                "requirement_clarification",
            )
            self.assertEqual(0, complete.returncode, complete.stderr)

            prepared = run_cli(
                "prepare-stage",
                "--feature-dir",
                str(feature_dir),
                "--stage",
                "repo_research",
            )

            self.assertEqual(0, prepared.returncode, prepared.stderr)
            self.assertTrue((feature_dir / "01-research.md").is_file())
            self.assertFalse((feature_dir / "02-design.md").exists())
            meta = json.loads((feature_dir / "meta.json").read_text(encoding="utf-8"))
            self.assertEqual("repo_research", meta["current_stage"])

    def test_prepare_revalidates_user_modified_upstream(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            feature_dir = init_feature(Path(tmp))
            requirement = feature_dir / "00-requirement.md"
            replace_frontmatter_value(requirement, "status", "completed")
            self.assertEqual(
                0,
                run_cli(
                    "complete-stage",
                    "--feature-dir",
                    str(feature_dir),
                    "--stage",
                    "requirement_clarification",
                ).returncode,
            )
            replace_frontmatter_value(requirement, "blocking_p0_count", "1")

            prepared = run_cli(
                "prepare-stage",
                "--feature-dir",
                str(feature_dir),
                "--stage",
                "repo_research",
            )

            self.assertNotEqual(0, prepared.returncode)
            self.assertIn("P0", prepared.stderr)
            self.assertFalse((feature_dir / "01-research.md").exists())

    def test_full_mode_cannot_skip_required_stages(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            feature_dir = init_feature(Path(tmp))

            prepared = run_cli(
                "prepare-stage",
                "--feature-dir",
                str(feature_dir),
                "--stage",
                "technical_design",
            )

            self.assertNotEqual(0, prepared.returncode)
            self.assertIn("前置阶段尚未完成", prepared.stderr)
            self.assertFalse((feature_dir / "02-design.md").exists())

    def test_quick_can_prepare_test_without_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            feature_dir = init_feature(Path(tmp), mode="quick")
            requirement = feature_dir / "00-requirement.md"
            replace_frontmatter_value(requirement, "status", "completed")
            self.assertEqual(
                0,
                run_cli(
                    "complete-stage",
                    "--feature-dir",
                    str(feature_dir),
                    "--stage",
                    "requirement_clarification",
                ).returncode,
            )
            self.assertEqual(
                0,
                run_cli(
                    "prepare-stage",
                    "--feature-dir",
                    str(feature_dir),
                    "--stage",
                    "implementation",
                ).returncode,
            )
            implementation = feature_dir / "01-implementation.md"
            replace_frontmatter_value(implementation, "status", "completed")
            self.assertEqual(
                0,
                run_cli(
                    "complete-stage",
                    "--feature-dir",
                    str(feature_dir),
                    "--stage",
                    "implementation",
                ).returncode,
            )

            prepared = run_cli(
                "prepare-stage",
                "--feature-dir",
                str(feature_dir),
                "--stage",
                "test_verify",
            )

            self.assertEqual(0, prepared.returncode, prepared.stderr)
            self.assertTrue((feature_dir / "03-test-report.md").is_file())
            self.assertFalse((feature_dir / "02-code-review.md").exists())


if __name__ == "__main__":
    unittest.main()
