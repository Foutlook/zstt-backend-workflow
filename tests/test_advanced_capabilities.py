from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"


def read_skill(name: str) -> str:
    return (SKILLS / name / "SKILL.md").read_text(encoding="utf-8")


def read_reference(skill_name: str, reference_name: str) -> str:
    return (
        SKILLS / skill_name / "references" / reference_name
    ).read_text(encoding="utf-8")


class SharedAdvancedCapabilityContractTest(unittest.TestCase):
    def test_shared_capability_and_fallback_contract_exists(self) -> None:
        text = read_reference("zztt-workflow-shared", "capability-fallback.md")
        for token in (
            "能力探测",
            "增强路径",
            "标准降级",
            "工具不可用",
            "证据置信度",
        ):
            self.assertIn(token, text)

    def test_shared_document_authority_and_correction_contract_exists(self) -> None:
        text = read_reference(
            "zztt-workflow-shared",
            "document-authority-and-corrections.md",
        )
        for token in (
            "权威主产物",
            "auxiliary",
            "用户纠正",
            "上游回写",
            "不得自动推进",
        ):
            self.assertIn(token, text)

    def test_shared_skill_loads_advanced_contracts(self) -> None:
        text = read_skill("zztt-workflow-shared")
        self.assertIn("capability-fallback.md", text)
        self.assertIn("document-authority-and-corrections.md", text)

    def test_evidence_rules_define_claim_ledger(self) -> None:
        text = read_reference("zztt-workflow-shared", "evidence-rules.md")
        for token in (
            "Claim Ledger",
            "结论 ID",
            "反证",
            "置信度",
            "运行时缺口",
            "验证动作",
        ):
            self.assertIn(token, text)


class RequirementAdvancedCapabilityTest(unittest.TestCase):
    def test_requirement_skill_loads_advanced_playbook(self) -> None:
        text = read_skill("zztt-requirement-clarification")
        self.assertIn("references/advanced-playbook.md", text)

    def test_requirement_playbook_covers_advanced_clarification(self) -> None:
        text = read_reference(
            "zztt-requirement-clarification",
            "advanced-playbook.md",
        )
        for token in (
            "混合材料",
            "PDF",
            "截图",
            "流程图",
            "输入盘点",
            "冲突扫描",
            "多轮澄清",
            "确认日志",
            "不可读范围",
            "quick/full",
        ):
            self.assertIn(token, text)

    def test_requirement_templates_record_material_and_tool_boundaries(self) -> None:
        for mode in ("full", "quick"):
            with self.subTest(mode=mode):
                text = (
                    SKILLS
                    / "zztt-workflow-shared"
                    / "assets"
                    / "templates"
                    / mode
                    / "00-requirement.md"
                ).read_text(encoding="utf-8")
                self.assertIn("材料可读性与冲突", text)
                self.assertIn("工具与降级记录", text)


class RepositoryResearchAdvancedCapabilityTest(unittest.TestCase):
    def test_research_skill_loads_advanced_playbook(self) -> None:
        text = read_skill("zztt-repo-research")
        self.assertIn("references/advanced-playbook.md", text)

    def test_research_playbook_covers_repository_archaeology(self) -> None:
        text = read_reference("zztt-repo-research", "advanced-playbook.md")
        for token in (
            "仓库边界",
            "主项目",
            "远程仓库",
            "本地 checkout",
            "CodeGraph",
            "索引新鲜度",
            "跨仓库",
            "旧链路副作用",
            "Claim Ledger",
            "反证",
            "证据覆盖度",
            "运行时验证",
        ):
            self.assertIn(token, text)

    def test_research_playbook_defines_tool_fallbacks(self) -> None:
        text = read_reference("zztt-repo-research", "advanced-playbook.md")
        for token in (
            "远程优先",
            "CodeGraph 不可用",
            "rg",
            "逐层源码",
            "pending",
        ):
            self.assertIn(token, text)

    def test_research_template_has_traceable_claim_ledger(self) -> None:
        text = (
            SKILLS
            / "zztt-workflow-shared"
            / "assets"
            / "templates"
            / "full"
            / "01-research.md"
        ).read_text(encoding="utf-8")
        for token in (
            "结论 ID",
            "证据 ID",
            "反证",
            "覆盖度",
            "工具与降级记录",
            "待验证动作",
        ):
            self.assertIn(token, text)


class TechnicalDesignAdvancedCapabilityTest(unittest.TestCase):
    def test_design_skill_loads_advanced_playbook(self) -> None:
        text = read_skill("zztt-technical-design")
        self.assertIn("references/advanced-playbook.md", text)

    def test_design_playbook_covers_reviewable_backend_design(self) -> None:
        text = read_reference("zztt-technical-design", "advanced-playbook.md")
        for token in (
            "设计输入清单",
            "高影响歧义",
            "当前代码基线",
            "候选方案",
            "未采用理由",
            "Mermaid",
            "时序图",
            "接口明细",
            "错误码",
            "幂等",
            "索引",
            "事务",
            "缓存",
            "数据迁移",
            "灰度",
            "监控",
            "回滚",
        ):
            self.assertIn(token, text)

    def test_design_template_exposes_advanced_review_sections(self) -> None:
        text = (
            SKILLS
            / "zztt-workflow-shared"
            / "assets"
            / "templates"
            / "full"
            / "02-design.md"
        ).read_text(encoding="utf-8")
        for token in (
            "设计取舍与未采用方案",
            "图表与实现映射",
            "数据迁移",
            "附件索引",
            "扩展性与维护性",
            "性能、安全与质量",
        ):
            self.assertIn(token, text)


class TaskBreakdownAdvancedCapabilityTest(unittest.TestCase):
    def test_task_skill_loads_advanced_playbook(self) -> None:
        text = read_skill("zztt-task-breakdown")
        self.assertIn("references/advanced-playbook.md", text)

    def test_task_playbook_covers_execution_orchestration(self) -> None:
        text = read_reference("zztt-task-breakdown", "advanced-playbook.md")
        for token in (
            "覆盖矩阵",
            "关键路径",
            "阻塞点",
            "并行等级",
            "冲突文件",
            "接口",
            "SQL",
            "测试映射",
            "精确验证命令",
            "预期信号",
        ):
            self.assertIn(token, text)

    def test_task_template_exposes_parallel_safety_fields(self) -> None:
        text = (
            SKILLS
            / "zztt-workflow-shared"
            / "assets"
            / "templates"
            / "full"
            / "03-tasks.md"
        ).read_text(encoding="utf-8")
        for token in (
            "L0/L1/L2",
            "关键路径",
            "冲突文件",
            "允许修改",
            "禁止修改",
            "预期信号",
        ):
            self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()
