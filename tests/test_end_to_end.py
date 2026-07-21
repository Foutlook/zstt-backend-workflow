from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tests.test_workflow_cli import (
    fill_stage_document,
    init_feature,
    replace_frontmatter_value,
    run_cli,
)


ROOT = Path(__file__).resolve().parents[1]


def complete_document(feature_dir: Path, stage: str, artifact: str) -> None:
    fill_stage_document(feature_dir / artifact, stage)
    completed = run_cli(
        "complete-stage",
        "--feature-dir",
        str(feature_dir),
        "--stage",
        stage,
    )
    if completed.returncode != 0:
        raise AssertionError(completed.stderr)


class WorkflowEndToEndTest(unittest.TestCase):
    def test_full_workflow_runs_one_explicit_stage_at_a_time(self) -> None:
        stages = (
            ("requirement_clarification", "00-requirement.md"),
            ("repo_research", "01-research.md"),
            ("technical_design", "02-design.md"),
            ("task_breakdown", "03-tasks.md"),
            ("implementation", "04-implementation.md"),
            ("code_review", "05-code-review.md"),
            ("test_verify", "06-test-report.md"),
        )
        with tempfile.TemporaryDirectory() as tmp:
            feature_dir = init_feature(Path(tmp))

            for index, (stage, artifact) in enumerate(stages):
                if index > 0:
                    prepared = run_cli(
                        "prepare-stage",
                        "--feature-dir",
                        str(feature_dir),
                        "--stage",
                        stage,
                    )
                    self.assertEqual(0, prepared.returncode, prepared.stderr)
                complete_document(feature_dir, stage, artifact)

            meta = json.loads((feature_dir / "meta.json").read_text(encoding="utf-8"))
            self.assertEqual([stage for stage, _ in stages], meta["completed_stages"])
            self.assertIsNone(meta["recommended_next_skill"])
            self.assertEqual([], meta["recommended_next_skills"])
            self.assertEqual(
                {"meta.json", *(artifact for _, artifact in stages)},
                {path.name for path in feature_dir.iterdir()},
            )

    def test_quick_can_skip_review_but_keeps_fixed_artifact_numbers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            feature_dir = init_feature(Path(tmp), mode="quick")
            complete_document(feature_dir, "requirement_clarification", "00-requirement.md")
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
            complete_document(feature_dir, "implementation", "01-implementation.md")
            self.assertEqual(
                0,
                run_cli(
                    "prepare-stage",
                    "--feature-dir",
                    str(feature_dir),
                    "--stage",
                    "test_verify",
                ).returncode,
            )
            complete_document(feature_dir, "test_verify", "03-test-report.md")

            self.assertFalse((feature_dir / "02-code-review.md").exists())
            meta = json.loads((feature_dir / "meta.json").read_text(encoding="utf-8"))
            self.assertNotIn("code_simplification", meta["artifacts"])
            self.assertIsNone(meta["recommended_next_skill"])
            self.assertEqual([], meta["recommended_next_skills"])

    def test_upstream_edit_blocks_then_allows_retry_after_correction(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            feature_dir = init_feature(Path(tmp))
            complete_document(feature_dir, "requirement_clarification", "00-requirement.md")
            requirement = feature_dir / "00-requirement.md"
            replace_frontmatter_value(requirement, "blocking_p0_count", "1")

            blocked = run_cli(
                "prepare-stage",
                "--feature-dir",
                str(feature_dir),
                "--stage",
                "repo_research",
            )
            self.assertNotEqual(0, blocked.returncode)
            self.assertIn("已修改", blocked.stderr)
            self.assertFalse((feature_dir / "01-research.md").exists())
            meta = json.loads((feature_dir / "meta.json").read_text(encoding="utf-8"))
            self.assertEqual([], meta["completed_stages"])

            replace_frontmatter_value(requirement, "blocking_p0_count", "0")
            recompleted = run_cli(
                "complete-stage",
                "--feature-dir",
                str(feature_dir),
                "--stage",
                "requirement_clarification",
            )
            self.assertEqual(0, recompleted.returncode, recompleted.stderr)
            retried = run_cli(
                "prepare-stage",
                "--feature-dir",
                str(feature_dir),
                "--stage",
                "repo_research",
            )
            self.assertEqual(0, retried.returncode, retried.stderr)

    def test_semantic_upstream_edit_invalidates_completed_downstream(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            feature_dir = init_feature(Path(tmp))
            complete_document(feature_dir, "requirement_clarification", "00-requirement.md")
            self.assertEqual(
                0,
                run_cli(
                    "prepare-stage",
                    "--feature-dir",
                    str(feature_dir),
                    "--stage",
                    "repo_research",
                ).returncode,
            )
            complete_document(feature_dir, "repo_research", "01-research.md")

            requirement = feature_dir / "00-requirement.md"
            requirement.write_text(
                requirement.read_text(encoding="utf-8")
                + "\n- 用户修订：统计范围改为全部历史数据。\n",
                encoding="utf-8",
                newline="\n",
            )
            prepared = run_cli(
                "prepare-stage",
                "--feature-dir",
                str(feature_dir),
                "--stage",
                "technical_design",
            )

            self.assertNotEqual(0, prepared.returncode)
            self.assertIn("上游已完成产物已修改", prepared.stderr)
            meta = json.loads((feature_dir / "meta.json").read_text(encoding="utf-8"))
            self.assertEqual([], meta["completed_stages"])
            self.assertEqual("requirement_clarification", meta["current_stage"])
            self.assertFalse((feature_dir / "02-design.md").exists())

    def test_readme_documents_install_and_recovery_workflow(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for token in (
            "安装",
            "workflow_cli.py init",
            "prepare-stage",
            "complete-stage",
            "用户修改",
            "重新校验",
            ".zstt/features",
            ".zstt/quick",
        ):
            self.assertIn(token, readme)

    def test_workflow_eval_prompts_are_present(self) -> None:
        eval_path = ROOT / "evals" / "evals.json"
        data = json.loads(eval_path.read_text(encoding="utf-8"))
        self.assertEqual("zstt-backend-workflow", data["skill_name"])
        self.assertGreaterEqual(len(data["evals"]), 12)
        for item in data["evals"]:
            self.assertIn("prompt", item)
            self.assertIn("expected_output", item)
            self.assertIn("forbidden_output", item)
            self.assertTrue(item["forbidden_output"])


if __name__ == "__main__":
    unittest.main()
