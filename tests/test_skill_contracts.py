from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "src" / "zstt_cli" / "resources" / "skills"
RULES = ROOT / "src" / "zstt_cli" / "resources" / "rules"


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
        "zstt-requirement-clarification",
        "zstt-repo-research",
        "zstt-technical-design",
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
                self.assertIn("rule_resolver.py", text)
                self.assertIn("rulesetFingerprint", text)

    def test_requirement_skill_preserves_clarification_loop(self) -> None:
        text = read_skill("zstt-requirement-clarification")
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
        text = read_skill("zstt-repo-research")
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
        text = read_skill("zstt-technical-design")
        for token in (
            "接口契约",
            "Jackson",
            "数据源一致性",
            "SQL 用户确认门禁",
            "prepare-sql-gate",
            "不改数据库",
            "create_user",
            "发布与回滚",
            "测试策略",
            "fallback",
            "02-design.md",
        ):
            self.assertIn(token, text)

    def test_workflow_rules_exist(self) -> None:
        rule_root = RULES / "workflow"
        protocol = (rule_root / "protocol.md").read_text(encoding="utf-8")
        evidence = (rule_root / "evidence.md").read_text(encoding="utf-8")
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
        "zstt-task-breakdown",
        "zstt-implementation",
        "zstt-code-review",
        "zstt-test-verify",
    )

    def test_skill_frontmatter_and_explicit_selection(self) -> None:
        for name in self.SKILL_NAMES:
            with self.subTest(name=name):
                text = read_skill(name)
                self.assertEqual(name, frontmatter_value(text, "name"))
                self.assertIn("仅当用户明确指定", text)
                self.assertIn("不得自动执行推荐的下一阶段", text)
                self.assertIn("rule_resolver.py", text)
                self.assertIn("rulesetFingerprint", text)
                self.assertLess(len(text.splitlines()), 500)

    def test_task_breakdown_is_traceable_and_executable(self) -> None:
        text = read_skill("zstt-task-breakdown")
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
        text = read_skill("zstt-implementation")
        for token in (
            "N+1",
            "循环远程调用",
            "无关重构",
            "保留既有注释",
            "java.jackson",
            "rule_resolver.py",
            "04-implementation.md",
        ):
            self.assertIn(token, text)


class SupportingSkillContractTest(unittest.TestCase):
    def test_java_rules_cover_team_guardrails(self) -> None:
        text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in sorted((RULES / "java").glob("*.md"))
        )
        for token in (
            "项目约束",
            "局部一致性",
            "保留既有注释",
            "@JsonProperty",
            "@JsonAlias",
            "ObjectMapper",
            "N+1",
            "循环远程调用",
            "单一关系源",
            "-Dsmart-doc.phase=verify",
            "Strategy（策略）",
            "DDD（领域驱动设计）",
            "SQL 设计约束",
            "不改数据库",
            "create_user",
        ):
            self.assertIn(token, text)

    def test_abstraction_and_patterns_are_evidence_gated(self) -> None:
        abstraction = (RULES / "java" / "abstraction.md").read_text(encoding="utf-8")
        patterns = (RULES / "java" / "design-patterns.md").read_text(encoding="utf-8")
        for token in ("变化轴", "不抽象", "不适用", "真实使用点"):
            self.assertIn(token, abstraction)
        for token in ("候选解法", "不适用", "不应使用", "例子"):
            self.assertIn(token, patterns)

    def test_code_simplification_is_optional_and_phase_neutral(self) -> None:
        text = read_skill("zstt-code-simplification")
        self.assertEqual("zstt-code-simplification", frontmatter_value(text, "name"))
        for token in (
            "仅当用户明确指定",
            "不属于固定流程",
            "不推进",
            "行为保持",
            "当前 diff",
            "指定提交",
            "文件",
            "符号",
            "auxiliary",
        ):
            self.assertIn(token, text)

    def test_supporting_skills_stay_under_500_lines(self) -> None:
        for name in (
            "zstt-code-simplification",
            "zstt-module-refactor",
            "zstt-bug-fix",
        ):
            with self.subTest(name=name):
                self.assertLess(len(read_skill(name).splitlines()), 500)

    def test_module_refactor_is_optional_and_approval_gated(self) -> None:
        text = read_skill("zstt-module-refactor")
        self.assertEqual("zstt-module-refactor", frontmatter_value(text, "name"))
        for token in (
            "仅当用户明确指定",
            "不属于固定流程",
            "不修改 `.zstt/meta.json`",
            "Fast path",
            "Plan review path",
            "Behavior-change path",
            "characterization test",
            ".zstt/refactors",
            "等待用户明确批准",
        ):
            self.assertIn(token, text)

    def test_bug_fix_is_evidence_first_and_requires_second_confirmation(self) -> None:
        text = read_skill("zstt-bug-fix")
        self.assertEqual("zstt-bug-fix", frontmatter_value(text, "name"))
        for token in (
            "仅当用户明确指定",
            "不属于 Full/Quick 固定阶段",
            "代码证据",
            "数据证据",
            "过程证据",
            "线上环境",
            "二次确认",
            "禁止修改业务代码",
            "SQL Gate",
            ".zstt/bugs",
            "不自动 commit、push、合并、部署",
        ):
            self.assertIn(token, text)

    def test_code_review_is_read_only_and_evidence_first(self) -> None:
        text = read_skill("zstt-code-review")
        for token in (
            "默认只读",
            "需求、方案、任务与实现",
            "最终数据源",
            "P0/P1/P2/P3",
            "05-code-review.md",
        ):
            self.assertIn(token, text)

    def test_test_verify_classifies_differences(self) -> None:
        text = read_skill("zstt-test-verify")
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
