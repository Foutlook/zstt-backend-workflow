from __future__ import annotations

import json
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

    def test_stage_skills_use_safe_current_feature_resolution(self) -> None:
        for name in (
            "zstt-requirement-clarification",
            "zstt-repo-research",
            "zstt-technical-design",
            "zstt-task-breakdown",
            "zstt-implementation",
            "zstt-code-review",
            "zstt-test-verify",
        ):
            with self.subTest(name=name):
                text = read_skill(name)
                self.assertIn("current --repo-root", text)
                self.assertIn("list --repo-root", text)
                self.assertIn("禁止按日期", text)

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
            "设计输入去向",
            "唯一真相",
            "无持久业务实例",
            "禁止外部传字段",
            "代码改动落点",
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
            "核心 `Dxx`",
            "非编码交接事项",
            "测试执行和测试报告不拆 Txx",
            "ZSTT_TASK_SCHEMA_VERSION",
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
            "zstt-product-feature-analysis",
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
            "开发角色",
            "测试角色",
            "不要求 Git 仓库",
            "纯数据查询",
            "python3",
            "Python 3.11+",
            "当前目录不是安装根目录",
            "代码证据",
            "数据证据",
            "过程证据",
            "线上环境",
            "缺陷确认卡",
            "支持缺陷",
            "支持非缺陷",
            "有界未解决",
            "适用契约",
            "可达状态",
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
            "implementation-evidence.json",
            "changedFromBaseline",
        ):
            self.assertIn(token, text)

    def test_product_feature_analysis_is_read_only_and_stage_neutral(self) -> None:
        text = read_skill("zstt-product-feature-analysis")
        self.assertEqual(
            "zstt-product-feature-analysis",
            frontmatter_value(text, "name"),
        )
        for token in (
            "仅当用户明确指定",
            "阶段中立",
            "不要求先创建 `00-requirement.md`",
            "不推进或修改 `.zstt/meta.json`",
            "产品意图",
            "当前实现",
            "运行观察",
            "持久状态",
            "Guard",
            "最终查询、计算、赋值",
            "数据源",
            "变更影响",
            "$zstt-requirement-clarification",
            "$zstt-bug-fix",
            "不确认 Bug",
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
            "implementation-evidence.json",
            "不能替代本测试阶段",
        ):
            self.assertIn(token, text)


class PersistentQualityGateSkillContractTest(unittest.TestCase):
    SKILL_NAMES = (
        "zstt-artifact-analysis",
        "zstt-requirement-checklist",
    )

    def test_analysis_skills_persist_only_their_derived_gate_report(self) -> None:
        for name in self.SKILL_NAMES:
            with self.subTest(name=name):
                text = read_skill(name)
                self.assertEqual(name, frontmatter_value(text, "name"))
                for token in (
                    "仅当用户明确指定",
                    "不属于 Full/Quick 固定阶段",
                    "不修改 `.zstt/meta.json`",
                    "不自动",
                    "rule_resolver.py",
                    "rulesetFingerprint",
                    "prepare-quality-gate",
                    "validate-quality-gate",
                ):
                    self.assertIn(token, text)
                self.assertNotIn("只在聊天中输出", text)
                self.assertLess(len(text.splitlines()), 500)
        self.assertIn(
            "checklists/requirements.md",
            read_skill("zstt-requirement-checklist"),
        )
        self.assertIn(
            "analysis/artifact-analysis.md",
            read_skill("zstt-artifact-analysis"),
        )

    def test_artifact_analysis_covers_semantics_without_mutating_workflow(self) -> None:
        text = read_skill("zstt-artifact-analysis")
        for token in (
            "task_breakdown",
            "stale_stages",
            "SQL Gate",
            "validate --stage",
            "prepare-stage",
            "Rxx",
            "Cxx/Exx/RQxx",
            "Dxx",
            "USxx",
            "Txx",
            "覆盖与范围",
            "语义一致性",
            "契约与数据",
            "依赖与执行安全",
            "项目规则对齐",
            "覆盖摘要",
            "COV-001",
            "输入指纹",
        ):
            self.assertIn(token, text)

    def test_requirement_checklist_tests_writing_not_implementation(self) -> None:
        text = read_skill("zstt-requirement-checklist")
        for token in (
            "需求是否定义清楚",
            "不是“代码是否工作”",
            "完整性",
            "清晰度",
            "一致性",
            "可度量性",
            "量化阈值",
            "观测口径",
            "证据来源",
            "追溯性",
            "场景与非功能覆盖",
            "至少 80%",
            "CHK001",
            "[x]",
            "证据：",
            "[Gap]",
            "[Ambiguity]",
            "Quick",
            "不运行实现测试",
        ):
            self.assertIn(token, text)

    def test_analysis_skills_include_behavior_prompts(self) -> None:
        for name in self.SKILL_NAMES:
            with self.subTest(name=name):
                prompts_path = SKILLS / name / "test-prompts.json"
                prompts = json.loads(prompts_path.read_text(encoding="utf-8"))
                self.assertGreaterEqual(len(prompts), 3)
                for prompt in prompts:
                    self.assertIn(f"${name}", prompt["prompt"])
                    self.assertTrue(prompt["expected"])

    def test_requirement_checklist_forms_an_optional_correction_loop(self) -> None:
        clarification = read_skill("zstt-requirement-clarification")
        checklist = read_skill("zstt-requirement-checklist")

        self.assertIn(
            "同时暴露可选的 `$zstt-requirement-checklist` 与固定下一阶段",
            clarification,
        )
        self.assertIn(
            "只能建议回到 `$zstt-requirement-clarification` 更新唯一权威",
            checklist,
        )
        self.assertIn("ruleset_fingerprint", checklist)
        self.assertIn("frontmatter 状态", checklist)

    def test_artifact_analysis_forms_an_optional_pre_implementation_gate(self) -> None:
        task_breakdown = read_skill("zstt-task-breakdown")
        artifact_analysis = read_skill("zstt-artifact-analysis")

        self.assertIn(
            "同时暴露可选的 `$zstt-artifact-analysis` 与固定下一阶段",
            task_breakdown,
        )
        self.assertIn("`implementation` 已完成时停止", artifact_analysis)
        self.assertIn("已有任务执行、代码改动或验证记录", artifact_analysis)
        self.assertIn("`$zstt-code-review`", artifact_analysis)
        self.assertIn("ruleset_fingerprint", artifact_analysis)
        self.assertIn("四个输入指纹", artifact_analysis)


if __name__ == "__main__":
    unittest.main()
