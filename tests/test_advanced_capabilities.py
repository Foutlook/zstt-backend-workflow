from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "src" / "zstt_cli" / "resources" / "skills"
RULES = ROOT / "src" / "zstt_cli" / "resources" / "rules"
TEMPLATES = ROOT / "src" / "zstt_cli" / "resources" / "templates"


def read_skill(name: str) -> str:
    return (SKILLS / name / "SKILL.md").read_text(encoding="utf-8")


def read_reference(skill_name: str, reference_name: str) -> str:
    return (
        SKILLS / skill_name / "references" / reference_name
    ).read_text(encoding="utf-8")


def read_rule(group: str, rule_name: str) -> str:
    return (RULES / group / rule_name).read_text(encoding="utf-8")


class SharedAdvancedCapabilityContractTest(unittest.TestCase):
    def test_shared_capability_and_fallback_contract_exists(self) -> None:
        text = read_rule("workflow", "capability-fallback.md")
        for token in (
            "能力探测",
            "增强路径",
            "标准降级",
            "工具不可用",
            "证据置信度",
        ):
            self.assertIn(token, text)

    def test_shared_document_authority_and_correction_contract_exists(self) -> None:
        text = read_rule("workflow", "document-authority.md")
        for token in (
            "权威主产物",
            "auxiliary",
            "用户纠正",
            "上游回写",
            "不得自动推进",
        ):
            self.assertIn(token, text)

    def test_public_skills_load_dynamic_rules(self) -> None:
        for skill in (
            "zstt-artifact-analysis",
            "zstt-requirement-clarification",
            "zstt-requirement-checklist",
            "zstt-repo-research",
            "zstt-technical-design",
            "zstt-task-breakdown",
            "zstt-implementation",
            "zstt-code-review",
            "zstt-test-verify",
            "zstt-code-simplification",
            "zstt-module-refactor",
            "zstt-bug-fix",
        ):
            with self.subTest(skill=skill):
                text = read_skill(skill)
                self.assertIn("rule_resolver.py", text)
                self.assertIn("规则", text)

    def test_evidence_rules_define_claim_ledger(self) -> None:
        text = read_rule("workflow", "evidence.md")
        for token in (
            "Claim Ledger",
            "结论 ID",
            "反证",
            "置信度",
            "运行时缺口",
            "验证动作",
        ):
            self.assertIn(token, text)

    def test_all_stage_templates_record_resolved_rules(self) -> None:
        for template in TEMPLATES.rglob("*.md"):
            with self.subTest(template=template.relative_to(TEMPLATES)):
                text = template.read_text(encoding="utf-8")
                self.assertIn("规则加载记录", text)
                self.assertIn("rulesetVersion", text)
                self.assertIn("rulesetFingerprint", text)
                self.assertIn("选择原因", text)


class RequirementAdvancedCapabilityTest(unittest.TestCase):
    def test_requirement_skill_loads_advanced_playbook(self) -> None:
        text = read_skill("zstt-requirement-clarification")
        self.assertIn("references/advanced-playbook.md", text)

    def test_requirement_playbook_covers_advanced_clarification(self) -> None:
        text = read_reference(
            "zstt-requirement-clarification",
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
            "Sxx",
            "Rxx",
            "Qxx",
            "用户意图",
            "最终反向确认",
            "confirmation_source",
        ):
            self.assertIn(token, text)

    def test_requirement_templates_record_traceable_baseline_and_confirmation(self) -> None:
        for mode in ("full", "quick"):
            with self.subTest(mode=mode):
                text = (
                    TEMPLATES
                    / mode
                    / "00-requirement.md"
                ).read_text(encoding="utf-8")
                self.assertIn("材料可读性与冲突", text)
                self.assertIn("工具与降级记录", text)
                self.assertIn("原始材料要点覆盖", text)
                self.assertIn("来源 ID", text)
                self.assertIn("需求 ID", text)
                self.assertIn("问题 ID", text)
                self.assertIn("confirmation_status", text)
                self.assertIn("confirmation_source", text)


class RepositoryResearchAdvancedCapabilityTest(unittest.TestCase):
    def test_research_skill_loads_advanced_playbook(self) -> None:
        text = read_skill("zstt-repo-research")
        self.assertIn("references/advanced-playbook.md", text)

    def test_research_playbook_covers_repository_archaeology(self) -> None:
        text = read_reference("zstt-repo-research", "advanced-playbook.md")
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
            "Rxx",
            "共享状态",
            "IN/NOT IN",
            "SQLxx",
            "RQxx",
            "每仓 ChangeScope",
        ):
            self.assertIn(token, text)

    def test_research_playbook_defines_tool_fallbacks(self) -> None:
        text = read_reference("zstt-repo-research", "advanced-playbook.md")
        for token in (
            "显式本地路径优先",
            "短路",
            ".zstt-kit/.env/.env.local",
            "ZSTT_REPO_MCP_*",
            "当前会话",
            "普通 HTTP",
            "默认降级",
            "CodeGraph 不可用",
            "rg",
            "逐层源码",
            "pending",
        ):
            self.assertIn(token, text)

    def test_research_skill_prioritizes_explicit_local_checkout(self) -> None:
        text = read_skill("zstt-repo-research")
        for token in (
            "仓库来源门禁",
            "用户明确提供",
            "只读取这些本地路径",
            "禁止检查私有 MCP 配置",
            "不能静默切换远程来源",
            "当前会话暴露",
            "不能把其中 URL 当作普通 HTTP 接口直接请求",
        ):
            self.assertIn(token, text)

    def test_repository_mcp_private_values_are_not_packaged(self) -> None:
        for template_name in (".env.example", ".env.prod.example"):
            with self.subTest(template=template_name):
                text = (
                    ROOT
                    / "src"
                    / "zstt_cli"
                    / "resources"
                    / "env"
                    / template_name
                ).read_text(encoding="utf-8")
                self.assertNotIn("ZSTT_REPO_MCP_", text)

        root_gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn(".zstt-kit/.env/.env.local", root_gitignore)

    def test_research_template_has_traceable_claim_ledger(self) -> None:
        text = (
            TEMPLATES
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
            "需求验证矩阵",
            "每仓 ChangeScope",
            "共享语义反向影响",
            "当前 SQL 事实与影响",
            "证据类型",
            "调研问题与阶段承接",
            "research_scope",
            "shared_semantic_impact",
            "current_sql_impact",
        ):
            self.assertIn(token, text)


class TechnicalDesignAdvancedCapabilityTest(unittest.TestCase):
    def test_design_skill_loads_advanced_playbook(self) -> None:
        text = read_skill("zstt-technical-design")
        self.assertIn("references/advanced-playbook.md", text)

    def test_design_playbook_covers_reviewable_backend_design(self) -> None:
        text = read_reference("zstt-technical-design", "advanced-playbook.md")
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
            "SQL 影响与确认",
            "prepare-sql-gate",
            "公共字段",
            "灰度",
            "监控",
            "回滚",
        ):
            self.assertIn(token, text)

    def test_design_template_exposes_advanced_review_sections(self) -> None:
        text = (
            TEMPLATES
            / "full"
            / "02-design.md"
        ).read_text(encoding="utf-8")
        for token in (
            "设计取舍与未采用方案",
            "图表与实现映射",
            "数据迁移",
            "SQL 影响类型",
            "SQL Gate 状态",
            "公共字段依据",
            "附件索引",
            "扩展性与维护性",
            "性能、安全与质量",
            "ZSTT_DESIGN_SCHEMA_VERSION",
            "设计输入去向",
            "后端推导字段/来源",
            "禁止外部传字段",
            "代码改动落点",
        ):
            self.assertIn(token, text)


class TaskBreakdownAdvancedCapabilityTest(unittest.TestCase):
    def test_task_skill_loads_advanced_playbook(self) -> None:
        text = read_skill("zstt-task-breakdown")
        self.assertIn("references/advanced-playbook.md", text)

    def test_task_playbook_covers_execution_orchestration(self) -> None:
        text = read_reference("zstt-task-breakdown", "advanced-playbook.md")
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
            TEMPLATES
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
            "ZSTT_TASK_SCHEMA_VERSION",
            "任务总览",
            "任务详情",
            "当前可执行集合",
            "非编码交接事项",
        ):
            self.assertIn(token, text)


class ImplementationAdvancedCapabilityTest(unittest.TestCase):
    def test_implementation_skill_loads_advanced_playbook(self) -> None:
        text = read_skill("zstt-implementation")
        self.assertIn("references/advanced-playbook.md", text)

    def test_implementation_playbook_covers_safe_execution(self) -> None:
        text = read_reference("zstt-implementation", "advanced-playbook.md")
        for token in (
            "范围冻结",
            "失败信号",
            "最小实现顺序",
            "任务状态",
            "并行安全评估",
            "Codex 子任务",
            "冲突文件",
            "主上下文复核",
            "分组验证",
            "上游回写",
        ):
            self.assertIn(token, text)

    def test_implementation_parallelism_stays_inside_current_stage(self) -> None:
        text = read_reference("zstt-implementation", "advanced-playbook.md")
        for token in (
            "用户明确要求",
            "当前实现阶段",
            "prepare-stage",
            "complete-stage",
            "不得自动执行下一阶段",
        ):
            self.assertIn(token, text)

    def test_implementation_templates_capture_execution_evidence(self) -> None:
        for mode, artifact in (
            ("full", "04-implementation.md"),
            ("quick", "01-implementation.md"),
        ):
            with self.subTest(mode=mode):
                text = (
                    TEMPLATES
                    / mode
                    / artifact
                ).read_text(encoding="utf-8")
                self.assertIn("范围冻结", text)
                self.assertIn("失败信号", text)
                self.assertIn("工具与降级记录", text)


class CodeReviewAdvancedCapabilityTest(unittest.TestCase):
    def test_review_skill_loads_advanced_playbook(self) -> None:
        text = read_skill("zstt-code-review")
        self.assertIn("references/advanced-playbook.md", text)

    def test_review_playbook_covers_hallucination_and_rounds(self) -> None:
        text = read_reference("zstt-code-review", "advanced-playbook.md")
        for token in (
            "范围冻结",
            "未跟踪业务文件",
            "一致性矩阵",
            "幻觉审计",
            "专项并行审查",
            "问题去重",
            "位置复核",
            "Review 轮次",
            "修复复审",
        ):
            self.assertIn(token, text)

    def test_review_templates_capture_audit_and_rounds(self) -> None:
        for mode, artifact in (
            ("full", "05-code-review.md"),
            ("quick", "02-code-review.md"),
        ):
            with self.subTest(mode=mode):
                text = (
                    TEMPLATES
                    / mode
                    / artifact
                ).read_text(encoding="utf-8")
                self.assertIn("幻觉审计", text)
                self.assertIn("Review 轮次", text)
                self.assertIn("逐文件变更", text)


class TestVerifyAdvancedCapabilityTest(unittest.TestCase):
    def test_test_verify_skill_loads_advanced_playbook(self) -> None:
        text = read_skill("zstt-test-verify")
        self.assertIn("references/advanced-playbook.md", text)

    def test_test_verify_playbook_covers_environmental_verification(self) -> None:
        text = read_reference("zstt-test-verify", "advanced-playbook.md")
        for token in (
            "测试资产优先级",
            "环境",
            "token",
            "权限",
            "前置数据",
            "JSON 入参",
            "Jackson 绑定",
            "API",
            "SQL",
            "异步验证",
            "测试轮次",
            "原始执行记录",
        ):
            self.assertIn(token, text)

    def test_test_verify_playbook_preserves_six_difference_categories(self) -> None:
        text = read_reference("zstt-test-verify", "advanced-playbook.md")
        for token in (
            "需求歧义",
            "方案遗漏",
            "实现偏差",
            "测试用例偏差",
            "环境/数据问题",
            "覆盖不足",
        ):
            self.assertIn(token, text)

    def test_test_verify_missing_capabilities_cannot_fake_success(self) -> None:
        text = read_reference("zstt-test-verify", "advanced-playbook.md")
        for token in (
            "缺少环境",
            "缺少 token",
            "标准降级",
            "不得伪造",
            "不得给出通过",
        ):
            self.assertIn(token, text)

    def test_test_verify_templates_capture_rounds_and_raw_execution(self) -> None:
        for mode, artifact in (
            ("full", "06-test-report.md"),
            ("quick", "03-test-report.md"),
        ):
            with self.subTest(mode=mode):
                text = (
                    TEMPLATES
                    / mode
                    / artifact
                ).read_text(encoding="utf-8")
                self.assertIn("环境与能力", text)
                self.assertIn("原始执行记录", text)
                self.assertIn("测试轮次", text)


class BugFixAdvancedCapabilityTest(unittest.TestCase):
    def test_bug_fix_loads_playbook_and_report_template(self) -> None:
        text = read_skill("zstt-bug-fix")
        self.assertIn("references/advanced-playbook.md", text)
        self.assertIn("references/observability-mcp.md", text)
        self.assertIn("references/environment-config.md", text)
        self.assertIn("references/runtime-bootstrap.md", text)
        self.assertIn("assets/bug-report-template.md", text)

    def test_bug_fix_defaults_to_chat_delivery_and_scoped_credentials(self) -> None:
        text = read_skill("zstt-bug-fix")
        self.assertIn("默认不创建 Bug 报告", text)
        self.assertIn("with_env.py", text)
        self.assertIn("observability|observability-client|mysql|es", text)
        self.assertIn("查询数据是两种角色共有能力", text)
        self.assertIn("没有业务代码则选择测试角色", text)
        self.assertIn("测试角色没有本阶段", text)
        self.assertIn("没有全局 `zstt` 命令", text)
        self.assertIn("已解析 Kit", text)

        observability = read_reference("zstt-bug-fix", "observability-mcp.md")
        for token in (
            "umodel_get_traces",
            "sls_execute_sql",
            "标准降级",
            "不打包 MCP Server 二进制或凭据",
        ):
            self.assertIn(token, observability)

        environment = read_reference("zstt-bug-fix", "environment-config.md")
        for token in (
            ".env.local",
            ".env.prod.local",
            "{ZSTT_KIT}/project-databases.json",
            "$productionSameAsTest",
            "$testBackendSls",
            "$testClientSls",
            "$prodBackendSls",
            "$prodClientSls",
            "最长配置项",
            "不进入安装清单",
            "生产配置缺失",
            "不同 Scope 的凭据不得交叉注入",
        ):
            self.assertIn(token, environment)

        bootstrap = read_reference("zstt-bug-fix", "runtime-bootstrap.md")
        for token in (
            "python3",
            "python",
            "py -3",
            "Python 3.11+",
            "ZSTT_KIT_ROOT",
            "CODEX_HOME/zstt-kit",
            ".codex/zstt-kit",
            "不要求全局 `zstt` 命令",
            "不得要求用户批准改用等价启动器",
        ):
            self.assertIn(token, bootstrap)

    def test_bug_fix_playbook_covers_evidence_and_environment_safety(self) -> None:
        text = read_reference("zstt-bug-fix", "advanced-playbook.md")
        for token in (
            "开发角色",
            "测试角色",
            "纯数据查询",
            "不要求代码或 Git",
            "diagnosis",
            "awaiting_confirmation",
            "fixing",
            "verified",
            "线上环境",
            "只读查询",
            "真实调用链",
            "代码证据",
            "数据/日志证据",
            "二次确认",
            "SQL Gate",
        ):
            self.assertIn(token, text)

    def test_bug_fix_template_preserves_confirmation_and_verification(self) -> None:
        text = (
            SKILLS / "zstt-bug-fix" / "assets" / "bug-report-template.md"
        ).read_text(encoding="utf-8")
        for token in (
            "role: developer",
            "phase: diagnosis",
            "fix_authorized: false",
            "范围、基线与能力",
            "证据与候选假设",
            "修复确认门禁",
            "实际修改",
            "验证证据",
            "回归点与残余风险",
        ):
            self.assertIn(token, text)


class CodeSimplificationAdvancedCapabilityTest(unittest.TestCase):
    def test_simplification_skill_loads_advanced_playbook(self) -> None:
        text = read_skill("zstt-code-simplification")
        self.assertIn("references/advanced-playbook.md", text)

    def test_simplification_playbook_covers_cleanup_workflow(self) -> None:
        text = read_reference("zstt-code-simplification", "advanced-playbook.md")
        for token in (
            "范围优先级",
            "Code Reuse",
            "Simplification",
            "Efficiency",
            "Abstraction Level",
            "可选并行分析",
            "候选项去重",
            "统一应用",
            "P0 推荐",
            "P1 推荐",
            "P2 推荐",
            "推荐修改的原因",
            "未自动修改原因",
            "行为不变",
            "修改前后使用同一组验证",
        ):
            self.assertIn(token, text)

    def test_simplification_requires_clear_change_summary(self) -> None:
        text = read_skill("zstt-code-simplification")
        for token in (
            "### 1. 执行概览",
            "### 2. 已修改",
            "A-xx",
            "修改了什么",
            "为什么修改",
            "### 3. 推荐修改（未自动修改）",
            "P0",
            "P1",
            "P2",
            "R-xx",
            "推荐修改的原因",
            "没有自动修改的原因",
            "报告模式（用户明确限制只读）",
            "不能只写“风险较高”",
            "### 4. 验证与边界",
            "只有既无自动修改项、也无有效推荐项",
        ):
            self.assertIn(token, text)

    def test_design_contract_detail_template_keeps_one_contract_truth(self) -> None:
        text = read_reference("zstt-technical-design", "contract-detail-template.md")
        for token in (
            "ZSTT_CONTRACT_DETAIL_VERSION",
            "来源 Dxx",
            "后端推导字段/来源",
            "禁止外部传字段",
            "权限/幂等/兼容",
            "必须逐项一致",
        ):
            self.assertIn(token, text)

        prompts = (
            SKILLS / "zstt-code-simplification" / "test-prompts.json"
        ).read_text(encoding="utf-8")
        for token in (
            "A-xx",
            "改了什么",
            "为什么改",
            "P0/P1/P2",
            "R-xx",
            "推荐修改的原因",
            "没有自动修改的原因",
            "已修改明确写无",
            "报告模式（用户明确限制只读）",
            "不能把结果收口成空",
            "P0 无项目时明确写无",
        ):
            self.assertIn(token, prompts)

    def test_simplification_playbook_keeps_phase_and_risk_boundaries(self) -> None:
        text = read_reference("zstt-code-simplification", "advanced-playbook.md")
        for token in (
            "不修改 `.zstt/meta.json`",
            "报告模式",
            "没有自动修改的原因",
            "疑似 Bug",
            "不得自动触发固定流程",
        ):
            self.assertIn(token, text)


class ModuleRefactorAdvancedCapabilityTest(unittest.TestCase):
    def test_module_refactor_loads_advanced_playbook(self) -> None:
        text = read_skill("zstt-module-refactor")
        self.assertIn("references/advanced-playbook.md", text)
        self.assertIn("assets/refactor-record-template.md", text)

    def test_module_refactor_covers_behavior_and_runtime_boundaries(self) -> None:
        text = read_reference("zstt-module-refactor", "advanced-playbook.md")
        for token in (
            "真实调用链",
            "Guard 与真实依赖",
            "行为基线",
            "Fast path",
            "Plan review",
            "Behavior change",
            "characterization test",
            "锁等待",
            "线程安全",
            "内存、GC",
            "资源",
            "重试",
            "超时",
            "设计模式与 DDD",
            "修改前后使用同一组命令",
        ):
            self.assertIn(token, text)

    def test_module_refactor_template_keeps_one_reviewable_record(self) -> None:
        text = (
            SKILLS
            / "zstt-module-refactor"
            / "assets"
            / "refactor-record-template.md"
        ).read_text(encoding="utf-8")
        for token in (
            "status: planning",
            "review_path: plan_review",
            "behavior_change: none",
            "范围冻结",
            "rulesetFingerprint",
            "当前证据链",
            "行为基线",
            "业务逻辑变更提案",
            "修改前后验证",
            "最终 Diff 审计",
        ):
            self.assertIn(token, text)


class DocumentationAndEvalContractTest(unittest.TestCase):
    def test_capability_matrix_maps_sources_status_and_boundaries(self) -> None:
        text = (ROOT / "docs" / "advanced-capability-matrix.md").read_text(
            encoding="utf-8"
        )
        for token in (
            "agent-skills",
            "ggg-backend-skills",
            "已融合",
            "适配后融合",
            "明确排除",
            "自动串行阶段",
            "自动推进",
            "自动 commit/push/merge/deploy",
            "无边界并行",
            "个人风格命名",
            "zstt-code-simplification",
        ):
            self.assertIn(token, text)

    def test_readme_explains_advanced_capability_contract(self) -> None:
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        for token in (
            "高级能力",
            "能力探测",
            "增强路径",
            "标准降级",
            "唯一权威主产物",
            "auxiliary/",
            "不会自动执行",
        ):
            self.assertIn(token, text)

    def test_evals_cover_advanced_and_forbidden_behaviors(self) -> None:
        data = json.loads((ROOT / "evals" / "evals.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(data["evals"]), 12)
        corpus = json.dumps(data, ensure_ascii=False)
        for token in (
            "混合材料",
            "CodeGraph 不可用",
            "跨仓库",
            "候选方案",
            "冲突文件",
            "实现偏差",
            "幻觉审计",
            "缺少 token",
            "Jackson 绑定",
            "代码简化",
            "模块重构",
            "业务逻辑变更提案",
        ):
            self.assertIn(token, corpus)
        for item in data["evals"]:
            self.assertIn("forbidden_output", item)
            self.assertTrue(item["forbidden_output"])


if __name__ == "__main__":
    unittest.main()
