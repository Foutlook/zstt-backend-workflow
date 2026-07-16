from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"


def read_skill(name: str) -> str:
    return (SKILLS / name / "SKILL.md").read_text(encoding="utf-8")


def frontmatter_value(text: str, key: str) -> str | None:
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        return None
    for line in lines[1:]:
        if line == "---":
            break
        if line.startswith(f"{key}:"):
            return line.split(":", 1)[1].strip()
    return None


class AnalysisSkillContractTest(unittest.TestCase):
    SKILL_NAMES = (
        "zztt-requirement-clarification",
        "zztt-repo-research",
        "zztt-technical-design",
    )

    def test_skill_frontmatter_matches_directory(self) -> None:
        for name in self.SKILL_NAMES:
            with self.subTest(name=name):
                text = read_skill(name)
                self.assertEqual(name, frontmatter_value(text, "name"))
                self.assertIsNotNone(frontmatter_value(text, "description"))

    def test_stage_skills_require_explicit_user_selection(self) -> None:
        for name in self.SKILL_NAMES:
            with self.subTest(name=name):
                text = read_skill(name)
                self.assertIn("仅当用户明确指定", text)
                self.assertIn("不得自动执行推荐的下一阶段", text)
                self.assertIn("workflow-protocol.md", text)

    def test_requirement_skill_preserves_clarification_loop(self) -> None:
        text = read_skill("zztt-requirement-clarification")
        for token in (
            "P0/P1/P2",
            "原始事实",
            "整理归纳",
            "推断",
            "冲突",
            "验收标准",
            "00-requirement.md",
        ):
            self.assertIn(token, text)

    def test_research_skill_requires_real_execution_evidence(self) -> None:
        text = read_skill("zztt-repo-research")
        for token in (
            "直接失败点",
            "真实调用链",
            "Guard 条件",
            "真实业务依赖",
            "最终数据源",
            "关键参数",
            "证据等级",
            "01-research.md",
        ):
            self.assertIn(token, text)

    def test_design_skill_covers_backend_decisions_without_fallback_guessing(self) -> None:
        text = read_skill("zztt-technical-design")
        for token in (
            "接口契约",
            "Jackson",
            "数据源一致性",
            "发布与回滚",
            "测试策略",
            "fallback",
            "02-design.md",
        ):
            self.assertIn(token, text)

    def test_shared_references_exist(self) -> None:
        reference_root = SKILLS / "zztt-workflow-shared" / "references"
        protocol = (reference_root / "workflow-protocol.md").read_text(encoding="utf-8")
        evidence = (reference_root / "evidence-rules.md").read_text(encoding="utf-8")
        self.assertIn("用户显式调用", protocol)
        self.assertIn("重新校验", protocol)
        self.assertIn("不得自动执行", protocol)
        self.assertIn("Proven", evidence)
        self.assertIn("Runtime dependent", evidence)

    def test_skill_files_stay_under_500_lines(self) -> None:
        for name in self.SKILL_NAMES:
            with self.subTest(name=name):
                self.assertLess(len(read_skill(name).splitlines()), 500)


class ExecutionSkillContractTest(unittest.TestCase):
    SKILL_NAMES = (
        "zztt-task-breakdown",
        "zztt-implementation",
        "zztt-code-review",
        "zztt-test-verify",
    )

    def test_skill_frontmatter_and_explicit_selection(self) -> None:
        for name in self.SKILL_NAMES:
            with self.subTest(name=name):
                text = read_skill(name)
                self.assertEqual(name, frontmatter_value(text, "name"))
                self.assertIn("仅当用户明确指定", text)
                self.assertIn("不得自动执行推荐的下一阶段", text)
                self.assertIn("workflow-protocol.md", text)
                self.assertLess(len(text.splitlines()), 500)

    def test_task_breakdown_is_traceable_and_executable(self) -> None:
        text = read_skill("zztt-task-breakdown")
        for token in (
            "来源依据",
            "预期文件",
            "依赖",
            "完成标准",
            "验证命令",
            "03-tasks.md",
        ):
            self.assertIn(token, text)

    def test_implementation_enforces_backend_guardrails(self) -> None:
        text = read_skill("zztt-implementation")
        for token in (
            "N+1",
            "循环远程调用",
            "无关重构",
            "保留既有注释",
            "zztt-java-backend-standard",
            "04-implementation.md",
        ):
            self.assertIn(token, text)

    def test_code_review_is_read_only_and_evidence_first(self) -> None:
        text = read_skill("zztt-code-review")
        for token in (
            "默认只读",
            "需求、方案、任务与实现",
            "最终数据源",
            "P0/P1/P2/P3",
            "05-code-review.md",
        ):
            self.assertIn(token, text)

    def test_test_verify_classifies_differences(self) -> None:
        text = read_skill("zztt-test-verify")
        for token in (
            "需求歧义",
            "方案遗漏",
            "实现偏差",
            "测试用例偏差",
            "环境/数据问题",
            "覆盖不足",
            "证据链",
            "06-test-report.md",
        ):
            self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()
