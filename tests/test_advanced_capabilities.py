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


if __name__ == "__main__":
    unittest.main()
