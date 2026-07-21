from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "src" / "zstt_cli" / "resources" / "runtime"
sys.path.insert(0, str(RUNTIME))

from workflow_contracts import (  # noqa: E402
    FULL_STAGES,
    QUICK_STAGES,
    get_contract,
    recommended_next_skill,
    recommended_next_skills,
    required_predecessors,
)
from workflow_paths import feature_directory, sanitize_feature_name  # noqa: E402


class WorkflowContractsTest(unittest.TestCase):
    def test_full_stage_order_and_artifacts_are_fixed(self) -> None:
        self.assertEqual(
            [
                "requirement_clarification",
                "repo_research",
                "technical_design",
                "task_breakdown",
                "implementation",
                "code_review",
                "test_verify",
            ],
            [stage.key for stage in FULL_STAGES],
        )
        self.assertEqual(
            [
                "00-requirement.md",
                "01-research.md",
                "02-design.md",
                "03-tasks.md",
                "04-implementation.md",
                "05-code-review.md",
                "06-test-report.md",
            ],
            [stage.artifact for stage in FULL_STAGES],
        )

    def test_quick_stage_order_keeps_review_and_test_optional(self) -> None:
        self.assertEqual(
            [
                "requirement_clarification",
                "implementation",
                "code_review",
                "test_verify",
            ],
            [stage.key for stage in QUICK_STAGES],
        )
        self.assertEqual(
            ("requirement_clarification", "implementation"),
            required_predecessors("quick", "test_verify"),
        )

    def test_full_recommends_exactly_one_next_stage(self) -> None:
        self.assertEqual(
            ("zstt-technical-design",),
            recommended_next_skills(
                "full",
                ["requirement_clarification", "repo_research"],
            ),
        )

    def test_quick_recommends_optional_review_and_test_after_implementation(self) -> None:
        completed = ["requirement_clarification", "implementation"]

        self.assertEqual(
            ("zstt-code-review", "zstt-test-verify"),
            recommended_next_skills("quick", completed),
        )
        self.assertEqual("zstt-code-review", recommended_next_skill("quick", completed))

    def test_quick_ends_after_test_without_backtracking_to_review(self) -> None:
        completed = [
            "requirement_clarification",
            "implementation",
            "test_verify",
        ]

        self.assertEqual((), recommended_next_skills("quick", completed))
        self.assertIsNone(recommended_next_skill("quick", completed))

    def test_code_simplification_is_not_a_fixed_stage(self) -> None:
        fixed_skills = {stage.skill for stage in FULL_STAGES + QUICK_STAGES}
        self.assertNotIn("zstt-code-simplification", fixed_skills)

    def test_module_refactor_is_not_a_fixed_stage(self) -> None:
        fixed_skills = {stage.skill for stage in FULL_STAGES + QUICK_STAGES}
        self.assertNotIn("zstt-module-refactor", fixed_skills)

    def test_unknown_stage_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "未知阶段"):
            get_contract("full", "unknown")

    def test_feature_name_is_sanitized_without_losing_chinese(self) -> None:
        self.assertEqual("学习报告-v2", sanitize_feature_name("  学习报告 / v2  "))

    def test_empty_feature_name_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "需求名称不能为空"):
            sanitize_feature_name("../")

    def test_feature_directory_stays_under_zstt_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            target = feature_directory(repo_root, "full", "../学习报告", "20260716")

            expected_root = (repo_root / ".zstt" / "features").resolve()
            self.assertTrue(target.is_relative_to(expected_root))
            self.assertEqual("20260716-学习报告", target.name)


if __name__ == "__main__":
    unittest.main()
