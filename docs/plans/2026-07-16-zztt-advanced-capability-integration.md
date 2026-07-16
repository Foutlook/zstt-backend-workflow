# ZZTT Advanced Capability Integration Implementation Plan

> **For Codex:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将 `agent-skills` 与 `ggg-backend-skills` 的高级能力分层融合到现有 ZZTT 阶段 Skill，同时保持显式调用、单主产物、`.zztt` 路径和门禁契约兼容。

**Architecture:** 每个阶段 `SKILL.md` 继续承担触发、阶段边界和主流程，并显式加载自己的 `references/advanced-playbook.md`。跨阶段能力探测、文档权威、证据和纠正规则进入 `zztt-workflow-shared/references/`；模板、README、评测和契约测试保证高级能力既能被发现，也能在工具缺失时降级。

**Tech Stack:** Codex Skills Markdown、Python 3 标准库、`unittest`、JSON、Git。

---

### Task 1: 建立高级能力共享契约

**Files:**
- Create: `tests/test_advanced_capabilities.py`
- Create: `skills/zztt-workflow-shared/references/capability-fallback.md`
- Create: `skills/zztt-workflow-shared/references/document-authority-and-corrections.md`
- Modify: `skills/zztt-workflow-shared/SKILL.md`
- Modify: `skills/zztt-workflow-shared/references/workflow-protocol.md`
- Modify: `skills/zztt-workflow-shared/references/evidence-rules.md`

**Step 1: 写失败测试**

在 `tests/test_advanced_capabilities.py` 增加 `SharedAdvancedCapabilityContractTest`，验证：

```python
def test_shared_capability_and_fallback_contract_exists(self) -> None:
    text = read_reference("zztt-workflow-shared", "capability-fallback.md")
    for token in ("能力探测", "增强路径", "标准降级", "工具不可用", "证据置信度"):
        self.assertIn(token, text)

def test_shared_document_authority_and_correction_contract_exists(self) -> None:
    text = read_reference(
        "zztt-workflow-shared", "document-authority-and-corrections.md"
    )
    for token in ("权威主产物", "auxiliary", "用户纠正", "上游回写", "不得自动推进"):
        self.assertIn(token, text)
```

同时断言共享 `SKILL.md` 会加载两个新参考文件，`evidence-rules.md` 包含 Claim Ledger 的最小字段。

**Step 2: 运行测试确认失败**

Run: `python -m unittest tests.test_advanced_capabilities.SharedAdvancedCapabilityContractTest -v`

Expected: FAIL，提示两个参考文件不存在。

**Step 3: 实现共享参考**

`capability-fallback.md` 必须定义：

- 只探测当前阶段需要的工具；
- 远程仓库 MCP、CodeGraph、非文本读取、Codex 子任务、API/token 环境的增强路径；
- 每项能力对应的标准降级路径；
- 工具失败、部分可用和结果不可验证时的记录规则；
- 工具缺失不等于业务失败，但关键事实无法证明时形成阻塞或开放风险。

`document-authority-and-corrections.md` 必须定义：

- 每阶段一份权威主产物；
- `auxiliary/` 只保存详细证据和附件；
- 主产物必须索引附件并保留关键结论；
- 用户纠正、下游发现冲突和并行结果汇总时的回写方式；
- 附件冲突时以主产物为准并同步修正。

扩展 `evidence-rules.md`，加入 Claim Ledger 字段：结论 ID、结论、证据等级、代码位置、反证、置信度、运行时缺口、验证动作。

**Step 4: 运行测试确认通过**

Run: `python -m unittest tests.test_advanced_capabilities.SharedAdvancedCapabilityContractTest -v`

Expected: PASS。

**Step 5: 提交**

```powershell
git add tests/test_advanced_capabilities.py skills/zztt-workflow-shared
git commit -m "完善高级能力共享契约"
```

### Task 2: 融合高级需求澄清能力

**Files:**
- Create: `skills/zztt-requirement-clarification/references/advanced-playbook.md`
- Modify: `skills/zztt-requirement-clarification/SKILL.md`
- Modify: `skills/zztt-workflow-shared/assets/templates/full/00-requirement.md`
- Modify: `skills/zztt-workflow-shared/assets/templates/quick/00-requirement.md`
- Modify: `tests/test_advanced_capabilities.py`

**Source references:**
- `C:/codex-me/agent-skills/prd-clarifier/SKILL.md`
- `C:/codex-me/ggg-backend-skills/skills/ggg-prd-intake/SKILL.md`

**Step 1: 写失败测试**

增加 `RequirementAdvancedCapabilityTest`，验证主 Skill 显式加载 `advanced-playbook.md`，高级参考包含：

```python
REQUIRED = (
    "混合材料", "PDF", "截图", "流程图", "输入盘点", "冲突扫描",
    "多轮澄清", "确认日志", "不可读范围", "quick/full",
)
```

验证 full/quick 模板都有“材料可读性与冲突”“工具与降级记录”位置。

**Step 2: 运行测试确认失败**

Run: `python -m unittest tests.test_advanced_capabilities.RequirementAdvancedCapabilityTest -v`

Expected: FAIL，提示高级参考不存在或主 Skill 未加载。

**Step 3: 编写高级参考并接入主 Skill**

高级参考按以下顺序编写：请求模式识别、输入材料清单、非文本材料读取、骨架初始化、冲突扫描、P0/P1/P2 多轮澄清、用户回答回写、完成检查。明确不因 PRD 看似完整而跳过澄清，也不在本阶段分析代码落点。

主 Skill 的“开始前”必须完整读取该参考，并根据输入类型读取相关章节。模板在现有权威章节内增加材料可读性、冲突、确认轮次和工具降级记录，不能增加平行需求文档。

**Step 4: 运行相关测试**

Run: `python -m unittest tests.test_advanced_capabilities.RequirementAdvancedCapabilityTest tests.test_skill_contracts.AnalysisSkillContractTest -v`

Expected: PASS。

**Step 5: 提交**

```powershell
git add skills/zztt-requirement-clarification skills/zztt-workflow-shared/assets/templates tests/test_advanced_capabilities.py
git commit -m "融合高级需求澄清能力"
```

### Task 3: 融合跨仓库与证据化调研能力

**Files:**
- Create: `skills/zztt-repo-research/references/advanced-playbook.md`
- Modify: `skills/zztt-repo-research/SKILL.md`
- Modify: `skills/zztt-workflow-shared/assets/templates/full/01-research.md`
- Modify: `tests/test_advanced_capabilities.py`

**Source references:**
- `C:/codex-me/agent-skills/clarified-requirement-repo-research/SKILL.md`
- `C:/codex-me/ggg-backend-skills/skills/ggg-requirement-alignment/SKILL.md`

**Step 1: 写失败测试**

增加 `RepositoryResearchAdvancedCapabilityTest`，检查：

```python
REQUIRED = (
    "仓库边界", "主项目", "远程仓库", "本地 checkout", "CodeGraph",
    "索引新鲜度", "跨仓库", "旧链路副作用", "Claim Ledger",
    "反证", "证据覆盖度", "运行时验证",
)
```

另断言高级参考为远程仓库、CodeGraph 和本地源码分别定义选择条件与降级方式。

**Step 2: 运行测试确认失败**

Run: `python -m unittest tests.test_advanced_capabilities.RepositoryResearchAdvancedCapabilityTest -v`

Expected: FAIL。

**Step 3: 实现调研 playbook**

写入能力探测、仓库列表确认、主项目识别、代码验证清单、入口到最终数据源追踪、旧链路副作用、跨仓库契约、Claim Ledger 和证据覆盖度检查。CodeGraph 不存在或索引过期时必须回退 `rg`、本地源码和逐层调用追踪，并记录降级边界。

扩展 `01-research.md` 模板，在现有“结论账本与证据索引”中加入结论 ID、反证、覆盖度、工具来源和待验证动作。

**Step 4: 运行相关测试**

Run: `python -m unittest tests.test_advanced_capabilities.RepositoryResearchAdvancedCapabilityTest tests.test_skill_contracts.AnalysisSkillContractTest -v`

Expected: PASS。

**Step 5: 提交**

```powershell
git add skills/zztt-repo-research skills/zztt-workflow-shared/assets/templates/full/01-research.md tests/test_advanced_capabilities.py
git commit -m "融合跨仓库证据化调研能力"
```

### Task 4: 融合完整后端技术方案能力

**Files:**
- Create: `skills/zztt-technical-design/references/advanced-playbook.md`
- Modify: `skills/zztt-technical-design/SKILL.md`
- Modify: `skills/zztt-workflow-shared/assets/templates/full/02-design.md`
- Modify: `tests/test_advanced_capabilities.py`

**Source references:**
- `C:/codex-me/agent-skills/writing-backend-technical-solutions/SKILL.md`
- `C:/codex-me/ggg-backend-skills/skills/ggg-technical-design/SKILL.md`

**Step 1: 写失败测试**

增加 `TechnicalDesignAdvancedCapabilityTest`，要求：

```python
REQUIRED = (
    "设计输入清单", "高影响歧义", "当前代码基线", "候选方案",
    "未采用理由", "Mermaid", "时序图", "接口明细", "错误码",
    "幂等", "索引", "事务", "缓存", "数据迁移", "灰度", "监控", "回滚",
)
```

同时检查主 Skill 读取高级参考，模板包含设计取舍、图表、数据迁移和附件索引位置。

**Step 2: 运行测试确认失败**

Run: `python -m unittest tests.test_advanced_capabilities.TechnicalDesignAdvancedCapabilityTest -v`

Expected: FAIL。

**Step 3: 实现设计 playbook**

按预检、代码基线、差距、核心身份/状态、候选方案、接口、存储、主流程图、时序图、代码落点、发布回滚、可观测性和测试策略组织。图表必须映射真实参与者和调用关系；不能用架构图代替业务流程。接口、SQL 等辅助附件可以存在，但主结论必须回写 `02-design.md`。

**Step 4: 运行相关测试**

Run: `python -m unittest tests.test_advanced_capabilities.TechnicalDesignAdvancedCapabilityTest tests.test_skill_contracts.AnalysisSkillContractTest -v`

Expected: PASS。

**Step 5: 提交**

```powershell
git add skills/zztt-technical-design skills/zztt-workflow-shared/assets/templates/full/02-design.md tests/test_advanced_capabilities.py
git commit -m "融合完整后端技术方案能力"
```

### Task 5: 融合可执行任务编排能力

**Files:**
- Create: `skills/zztt-task-breakdown/references/advanced-playbook.md`
- Modify: `skills/zztt-task-breakdown/SKILL.md`
- Modify: `skills/zztt-workflow-shared/assets/templates/full/03-tasks.md`
- Modify: `tests/test_advanced_capabilities.py`

**Source reference:**
- `C:/codex-me/ggg-backend-skills/skills/ggg-task-breakdown/SKILL.md`

**Step 1: 写失败测试**

增加 `TaskBreakdownAdvancedCapabilityTest`，检查覆盖矩阵、关键路径、阻塞点、并行等级、冲突文件、接口/SQL/测试映射、精确命令和预期信号。

**Step 2: 运行测试确认失败**

Run: `python -m unittest tests.test_advanced_capabilities.TaskBreakdownAdvancedCapabilityTest -v`

Expected: FAIL。

**Step 3: 实现任务 playbook**

定义任务字段和拆分算法：先做覆盖清单，再按可验证闭环拆任务，最后标记依赖、关键路径和并行安全。共享 Java 文件、Mapper XML、SQL、接口契约和配置的任务不得标成可直接并行。

**Step 4: 运行相关测试**

Run: `python -m unittest tests.test_advanced_capabilities.TaskBreakdownAdvancedCapabilityTest tests.test_skill_contracts.ExecutionSkillContractTest -v`

Expected: PASS。

**Step 5: 提交**

```powershell
git add skills/zztt-task-breakdown skills/zztt-workflow-shared/assets/templates/full/03-tasks.md tests/test_advanced_capabilities.py
git commit -m "融合任务编排与并行安全能力"
```

### Task 6: 融合高级实现执行能力

**Files:**
- Create: `skills/zztt-implementation/references/advanced-playbook.md`
- Modify: `skills/zztt-implementation/SKILL.md`
- Modify: `skills/zztt-workflow-shared/assets/templates/full/04-implementation.md`
- Modify: `skills/zztt-workflow-shared/assets/templates/quick/01-implementation.md`
- Modify: `tests/test_advanced_capabilities.py`

**Source reference:**
- `C:/codex-me/ggg-backend-skills/skills/ggg-implementation/SKILL.md`

**Step 1: 写失败测试**

增加 `ImplementationAdvancedCapabilityTest`，检查范围冻结、失败信号、最小实现顺序、任务状态、并行安全评估、Codex 子任务、冲突文件、主上下文复核、分组验证和上游回写。

测试必须同时确认：并行只在当前阶段可选启用，不能自动触发下一阶段，也不能跳过 `prepare-stage`/`complete-stage`。

**Step 2: 运行测试确认失败**

Run: `python -m unittest tests.test_advanced_capabilities.ImplementationAdvancedCapabilityTest -v`

Expected: FAIL。

**Step 3: 实现高级执行 playbook**

定义串行默认路径和可选并行增强路径。只有任务独立、写集不重叠、契约已稳定且验证方式独立时才允许 Codex 子任务；主上下文必须重新阅读 diff、运行验证并汇总产物。保留最小修改、TDD、用户改动保护和 Java 硬门禁。

**Step 4: 运行相关测试**

Run: `python -m unittest tests.test_advanced_capabilities.ImplementationAdvancedCapabilityTest tests.test_skill_contracts.ExecutionSkillContractTest -v`

Expected: PASS。

**Step 5: 提交**

```powershell
git add skills/zztt-implementation skills/zztt-workflow-shared/assets/templates tests/test_advanced_capabilities.py
git commit -m "融合高级实现与安全并行能力"
```

### Task 7: 融合幻觉审计和多轮代码评审能力

**Files:**
- Create: `skills/zztt-code-review/references/advanced-playbook.md`
- Modify: `skills/zztt-code-review/SKILL.md`
- Modify: `skills/zztt-workflow-shared/assets/templates/full/05-code-review.md`
- Modify: `skills/zztt-workflow-shared/assets/templates/quick/02-code-review.md`
- Modify: `tests/test_advanced_capabilities.py`

**Source reference:**
- `C:/codex-me/ggg-backend-skills/skills/ggg-code-review/SKILL.md`

**Step 1: 写失败测试**

增加 `CodeReviewAdvancedCapabilityTest`，检查范围冻结、未跟踪业务文件、一致性矩阵、幻觉审计、可选专项并行审查、问题去重、位置复核、Review 轮次和修复复审。

**Step 2: 运行测试确认失败**

Run: `python -m unittest tests.test_advanced_capabilities.CodeReviewAdvancedCapabilityTest -v`

Expected: FAIL。

**Step 3: 实现 Review playbook**

定义业务正确性、数据/并发、接口兼容、性能、安全和测试六类专项检查。并行结果只是候选问题，主上下文必须验证代码位置、失败条件和影响后才能写入主报告。Review 轮次可以写入 `auxiliary/review-rounds/`，但 `05-code-review.md` 或 quick 主产物保存当前权威结论。

**Step 4: 运行相关测试**

Run: `python -m unittest tests.test_advanced_capabilities.CodeReviewAdvancedCapabilityTest tests.test_skill_contracts.SupportingSkillContractTest -v`

Expected: PASS。

**Step 5: 提交**

```powershell
git add skills/zztt-code-review skills/zztt-workflow-shared/assets/templates tests/test_advanced_capabilities.py
git commit -m "融合幻觉审计与多轮评审能力"
```

### Task 8: 融合环境化测试与差异归因能力

**Files:**
- Create: `skills/zztt-test-verify/references/advanced-playbook.md`
- Modify: `skills/zztt-test-verify/SKILL.md`
- Modify: `skills/zztt-workflow-shared/assets/templates/full/06-test-report.md`
- Modify: `skills/zztt-workflow-shared/assets/templates/quick/03-test-report.md`
- Modify: `tests/test_advanced_capabilities.py`

**Source references:**
- `C:/codex-me/agent-skills/verify-implementation-with-test-cases/SKILL.md`
- `C:/codex-me/ggg-backend-skills/skills/ggg-test-verify/SKILL.md`

**Step 1: 写失败测试**

增加 `TestVerifyAdvancedCapabilityTest`，检查测试资产优先级、环境、token、权限、前置数据、JSON 字段规则、Jackson 绑定、接口/SQL/异步验证、测试轮次、原始执行记录和六类差异归因。

测试还要确认 token 或环境缺失时不会伪造成功，而是走本地验证降级并记录未验证范围。

**Step 2: 运行测试确认失败**

Run: `python -m unittest tests.test_advanced_capabilities.TestVerifyAdvancedCapabilityTest -v`

Expected: FAIL。

**Step 3: 实现测试 playbook**

按资产盘点、场景矩阵、环境准备、输入检查、分层执行、差异归因、回归轮次和交付判断组织。敏感 token 只检查存在性和作用域，不写入产物、命令回显或日志。环境不可用时区分代码验证与环境验证。

**Step 4: 运行相关测试**

Run: `python -m unittest tests.test_advanced_capabilities.TestVerifyAdvancedCapabilityTest tests.test_skill_contracts.SupportingSkillContractTest -v`

Expected: PASS。

**Step 5: 提交**

```powershell
git add skills/zztt-test-verify skills/zztt-workflow-shared/assets/templates tests/test_advanced_capabilities.py
git commit -m "融合环境化测试与差异归因能力"
```

### Task 9: 完整融合代码简化能力

**Files:**
- Create: `skills/zztt-code-simplification/references/advanced-playbook.md`
- Modify: `skills/zztt-code-simplification/SKILL.md`
- Modify: `tests/test_advanced_capabilities.py`

**Source reference:**
- `C:/codex-me/agent-skills/code-simplification-refactor/SKILL.md`

**Step 1: 写失败测试**

增加 `CodeSimplificationAdvancedCapabilityTest`，检查范围优先级、复用/简化/效率/抽象四路审查、可选并行分析、候选去重、统一应用、行为不变和修改前后相同验证信号。

**Step 2: 运行测试确认失败**

Run: `python -m unittest tests.test_advanced_capabilities.CodeSimplificationAdvancedCapabilityTest -v`

Expected: FAIL。

**Step 3: 实现简化 playbook**

保留原 Skill 的四路审查和安全应用语义。并行分析不能让多个上下文直接同时修改文件；主上下文统一确认候选、应用补丁并验证。继续保持不推进 `.zztt/meta.json`。

**Step 4: 运行相关测试**

Run: `python -m unittest tests.test_advanced_capabilities.CodeSimplificationAdvancedCapabilityTest tests.test_skill_contracts.SupportingSkillContractTest -v`

Expected: PASS。

**Step 5: 提交**

```powershell
git add skills/zztt-code-simplification tests/test_advanced_capabilities.py
git commit -m "完整融合代码简化能力"
```

### Task 10: 更新能力矩阵、README 和评测集

**Files:**
- Create: `docs/advanced-capability-matrix.md`
- Modify: `README.md`
- Modify: `evals/evals.json`
- Modify: `tests/test_end_to_end.py`
- Modify: `tests/test_advanced_capabilities.py`

**Step 1: 写失败测试**

扩展测试，要求：

- `docs/advanced-capability-matrix.md` 为两个来源项目的每项高级能力标明“已融合、适配后融合、明确排除”；
- README 包含“高级能力”“能力探测”“标准降级”“auxiliary”“不自动执行”；
- `evals/evals.json` 至少包含 12 个场景；
- 新场景覆盖混合需求、CodeGraph 缺失、技术方案深度、并行冲突、幻觉审计、token 缺失和高风险简化跳过。

Run: `python -m unittest tests.test_end_to_end.WorkflowEndToEndTest.test_workflow_eval_prompts_are_present tests.test_advanced_capabilities.DocumentationAndEvalContractTest -v`

Expected: FAIL。

**Step 2: 编写能力矩阵**

逐项列出来源 Skill、原能力、ZZTT 目标文件、融合状态、适配说明和验证测试。明确排除自动串行、自动阶段推进、自动 commit/push/merge/deploy，以及脱离当前阶段的无边界并行。

**Step 3: 更新 README 和评测集**

README 说明渐进加载、能力探测、附件权威边界和各阶段恢复的高级能力。新增至少 8 个高级场景评测，使总数不少于 12；`expected_output` 必须同时描述正确高级行为和不得发生的越界行为。

**Step 4: 运行测试确认通过**

Run: `python -m unittest tests.test_end_to_end tests.test_advanced_capabilities -v`

Expected: PASS。

**Step 5: 提交**

```powershell
git add docs/advanced-capability-matrix.md README.md evals/evals.json tests
git commit -m "补充高级能力文档与评测场景"
```

### Task 11: 全量验证和交付检查

**Files:**
- Verify: `skills/**/*.md`
- Verify: `skills/zztt-workflow-shared/scripts/*.py`
- Verify: `tests/*.py`
- Verify: `evals/evals.json`

**Step 1: 运行完整测试**

Run: `python -m unittest discover -s tests -v`

Expected: 原 42 项测试与新增高级能力测试全部 PASS。

**Step 2: 编译 Python 文件**

Run: `python -m compileall -q skills tests`

Expected: 退出码 0，无输出。

**Step 3: 检查 Skill 长度和编码**

Run: `python -m unittest tests.test_project_structure.ProjectStructureTest.test_text_files_do_not_have_utf8_bom tests.test_skill_contracts -v`

Expected: PASS；所有 `SKILL.md` 小于 500 行，文本为 UTF-8 无 BOM。

**Step 4: 检查 Git 差异**

Run: `git diff --check`

Expected: 退出码 0，无空白错误。

Run: `git status --short`

Expected: 只有计划内文件；没有生成缓存、临时输出或业务仓库 `.zztt` 测试残留。

**Step 5: 检查提交和能力覆盖**

Run: `git log --oneline --decorate -12`

Expected: 每组能力有中文提交，最新分支为 `feature/zztt-advanced-capabilities`。

如果最后还有仅属于验证修正的文件，执行精确暂存并提交：

```powershell
git add <仅本次验证修正的文件>
git commit -m "完成高级能力融合验收"
```
