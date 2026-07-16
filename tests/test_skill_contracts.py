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


if __name__ == "__main__":
    unittest.main()
