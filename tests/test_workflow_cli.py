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


if __name__ == "__main__":
    unittest.main()
