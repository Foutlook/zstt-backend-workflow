# ZSTT 高级能力融合矩阵

本文记录 `agent-skills` 与 `ggg-backend-skills` 的高级能力如何进入 ZSTT。目标不是照搬目录或文案，而是在“用户显式选择 Skill、阶段只推荐不自动执行、每阶段一个权威主产物、产物写入业务仓库 `.zstt/`”的产品约束下完成能力融合。

状态含义：

- `已融合`：语义和执行方式可直接保留；
- `适配后融合`：保留能力，但按 Codex、ZSTT 阶段或产物权威规则调整实现；
- `明确排除`：与已确认产品边界冲突，不进入当前版本。

## 共享工作流能力

| 来源 | 原能力 | ZSTT 落点 | 状态 | 适配说明 |
|---|---|---|---|---|
| 两套来源 | 证据优先、事实与推断分离 | `.zstt-kit/rules/workflow/evidence.md` | 已融合 | 增加 Claim Ledger、反证、置信度、运行时缺口和验证动作 |
| ggg-backend-skills | 阶段状态、上游门禁、P0 阻断 | `.zstt-kit/rules/workflow/protocol.md`、`.zstt-kit/runtime/workflow_*.py` | 适配后融合 | 阶段由用户显式调用；门禁检查实质内容和追溯 ID，并用内容指纹使修改阶段及下游旧结论失效 |
| 两套来源 | 工具增强和不可用降级 | `.zstt-kit/rules/workflow/capability-fallback.md` | 适配后融合 | 统一为能力探测、增强路径、标准降级和证据置信度 |
| agent-skills | 用户纠正与证据回写 | `.zstt-kit/rules/workflow/document-authority.md` | 适配后融合 | 当前阶段一个唯一权威主产物，细节只进 `auxiliary/` |
| ggg-backend-skills | full/quick 两种强度 | `.zstt-kit/templates/` 和 `.zstt-kit/runtime/workflow_cli.py` | 已融合 | 路径和固定编号保持稳定，不因跳过可选阶段重排 |

## 动态规则能力

| 能力 | ZSTT 落点 | 规则类型 | 选择方式 |
|---|---|---|---|
| 工作流和 Java 硬约束 | `.zstt-kit/rules/workflow/`、`java/core.md` 等 | `constraint` | 当前 Skill 的固定 profile |
| 抽象、设计模式和 DDD | `java/abstraction.md`、`design-patterns.md`、`ddd.md` | `decision` | 真实调用链和变化压力满足条件后追加上下文 |
| 并发、资源和验证 | `java/concurrency-resource.md`、`verification.md` | `checklist` | 当前改动实际触达对应风险面时追加 |
| 具体代码与命令示例 | `java/examples.md` | `reference` | 需要例子时显式追加 `examples` |
| 目录、选择原因与 SHA-256 | `.zstt-kit/rules/catalog.json`、`.zstt-kit/runtime/rule_resolver.py` | 确定性运行时 | profile 与显式上下文标签合并，输出规则集指纹 |

上下文标签必须由完整目标文件、真实调用链、最终数据源和行为边界证明。文件名、类名和关键词只用于定位，不直接触发抽象或设计模式规则。

## 需求澄清

| 来源 | 原能力 | ZSTT 落点 | 状态 | 适配说明 |
|---|---|---|---|---|
| `agent-skills/prd-clarifier` | PRD、PDF、截图、流程图、表格等混合材料 | `zstt-requirement-clarification/references/advanced-playbook.md` | 已融合 | 先做输入盘点和可读性边界，再提炼需求 |
| `agent-skills/prd-clarifier` | 冲突扫描、多轮澄清、确认日志 | 同上及 `00-requirement.md` 模板 | 已融合 | P0/P1/P2 分级，保留用户逐轮确认结果 |
| `ggg-prd-intake` | quick/full 推荐、用户选择或授权 | 同上 | 适配后融合 | AI 给推荐和依据，用户选择；明确授权 AI 决定时记录来源，不自动升级 |
| `ggg-prd-intake` | 原始材料、需求基线和疑问的逐条追溯 | `00-requirement.md` 模板及运行时校验 | 适配后融合 | 使用 `Sxx → Rxx/Qxx`；每个材料要点收口，每个 Rxx 有来源和验收覆盖 |
| `ggg-prd-intake` | 问题类型、Owner、阶段承接和最终反向确认 | 同上 | 适配后融合 | 用户意图不能转下游；代码事实和设计选择明确承接阶段，最终确认来源可回查 |
| 两套来源 | 产物完成后继续下一阶段 | Skill 推荐语 | 适配后融合 | 只推荐 `zstt-repo-research`，不会自动执行 |

## 仓库调研

| 来源 | 原能力 | ZSTT 落点 | 状态 | 适配说明 |
|---|---|---|---|---|
| `clarified-requirement-repo-research` | 仓库边界、主项目、跨仓库证据链 | `zstt-repo-research/references/advanced-playbook.md` | 已融合 | 每个结论绑定证据 ID、反证和覆盖度 |
| 同上 | 入口到最终 fetch/calculation/assignment 的真实调用链 | 同上 | 已融合 | 显式区分历史 guard 与真实业务依赖 |
| `clarified-requirement-repo-research` | 远程仓库读取、本地 checkout 降级 | 同上 | 适配后融合 | 改为显式本地路径最高优先；未指定路径时才检查本机私有配置与会话 MCP，失败后进入默认降级，私有连接值不入库 |
| `ggg-requirement-alignment` | CodeGraph 图谱分析和索引新鲜度 | 同上 | 适配后融合 | CodeGraph 不可用或索引过期时用 `rg` + 逐层源码并标记 `pending` |
| `ggg-requirement-alignment` | 上游需求逐条覆盖 | `01-research.md` 需求验证矩阵及运行时校验 | 适配后融合 | 完整调研必须且只能覆盖全部 `Rxx`；聚焦调研保持 draft |
| `ggg-requirement-alignment` | 共享状态、枚举和类型码反向影响 | `01-research.md` 共享语义矩阵 | 已融合 | 覆盖生产、持久化/传播、消费者、SQL/XML、任务、缓存和历史值 |
| `ggg-requirement-alignment` | SQL 影响提前识别 | `01-research.md` 当前 SQL 事实表 | 适配后融合 | 调研只记录 `SQLxx` 当前事实；未来 SQL 草案、确认和 Gate 保留在技术设计 |
| 两套来源 | 权威需改仓库清单与每仓范围 | `01-research.md` 仓库分类和 ChangeScope | 已融合 | 汇总与每仓范围一一对应，No code change 也记录排除证据 |
| `ggg-requirement-alignment` | 严格 Claim/Evidence/Question 校验 | `.zstt-kit/runtime/workflow_validation.py` | 适配后融合 | 校验 R/C/E/RQ 唯一性、引用、证据等级、本地文件行号、问题数量和阶段承接 |
| 两套来源 | 旧链路副作用、运行时验证缺口 | `01-research.md` 模板 | 已融合 | 不能把静态推断写成运行事实 |

## 现有功能分析

| 来源 | 原能力 | ZSTT 落点 | 状态 | 适配说明 |
|---|---|---|---|---|
| `sdd-mini/product-feature-analysis` | 面向产品、测试或开发说明已有功能的当前行为 | `zstt-product-feature-analysis/SKILL.md` | 适配后融合 | 聚焦 Java 后端，不要求需求目录，不推进 Full/Quick；默认只在当前任务交付 |
| 同上 | 产品意图、代码实现、运行观察、持久状态和推断分离 | `zstt-product-feature-analysis/SKILL.md`、`references/advanced-playbook.md` | 已融合 | PRD 不证明已实现，静态代码不证明本次执行，一条运行记录不代表所有场景 |
| 同上 | 有界代码来源、真实调用链、最终数据源和关键参数 | `references/advanced-playbook.md` | 适配后融合 | 用户指定本地路径时只读该路径；未指定时才检查只读 MCP，失败后安全降级 |
| 同上 | 只有明确要求时才分析变更影响 | `zstt-product-feature-analysis/SKILL.md` | 已融合 | 新需求转需求澄清，疑似契约违反转 Bug Fix，不在本 Skill 中设计或修复 |
| ZSTT 产品约束 | 阶段中立和可选留档 | `assets/feature-analysis-template.md` | 适配后融合 | 默认不创建文件；明确要求时写 `.zstt/analyses/features/`，不得替代需求、调研或方案 |

## 需求与现状差异分析

| 来源 | 原能力 | ZSTT 落点 | 状态 | 适配说明 |
|---|---|---|---|---|
| `agent-skills/prd-code-gap-analysis` | 原子需求、当前行为和变更范围逐项判定 | `zstt-prd-code-gap-analysis/SKILL.md` | 适配后融合 | 保持阶段中立和默认聊天交付，不生成正式需求、调研、方案或实现 |
| `agent-skills/read-code-with-codegraph` | 最新 release/bugfix 识别、远程 CodeGraph 优先和安全本地切换 | 同上 | 适配后融合 | 每仓记录来源、目标分支与提交；工作区不干净或无法快进时停止切换 |
| ZSTT DMS Runtime | 结构、链路和实际数据覆盖三层核验 | `references/environment-config.md`、`references/dms-mcp.md` | 已融合 | 通过 `project-databases.json`、`with_env.py` 和 `dms_mcp_client.py` 隔离 test/prod；prod 必须显式指定，失败不跨环境回退 |

## 技术方案

| 来源 | 原能力 | ZSTT 落点 | 状态 | 适配说明 |
|---|---|---|---|---|
| `writing-backend-technical-solutions` | 输入清单、高影响歧义、当前基线与差距 | `zstt-technical-design/references/advanced-playbook.md` | 已融合 | 未闭合的高影响歧义继续作为 P0 |
| 同上 | Dxx/Cxx 决策、候选方案和未采用理由 | 同上及 `02-design.md` 模板 | 已融合 | 主方案与取舍均可评审 |
| 同上 | Mermaid 架构/流程/时序图及实现映射 | 同上 | 已融合 | 图只表达可被代码证据支持的角色和链路 |
| 同上 | 接口、错误码、幂等、Jackson、兼容性 | 同上 | 已融合 | JavaBean 高风险字段要求显式绑定测试 |
| 同上 | MySQL/Redis/ES/MQ、索引、事务、缓存、迁移 | 同上 | 已融合 | 每个存储选择必须有准入理由和回滚策略 |
| `ggg-technical-design` | 灰度、监控、发布、回滚和压力测试 | 同上 | 已融合 | 附件可进 `auxiliary/`，主结论仍回写权威方案 |

## 任务拆分与实现

| 来源 | 原能力 | ZSTT 落点 | 状态 | 适配说明 |
|---|---|---|---|---|
| `ggg-task-breakdown` | 需求/设计到任务覆盖矩阵 | `zstt-task-breakdown/references/advanced-playbook.md` | 已融合 | 接口、SQL、代码和测试均能追到任务 |
| 同上 | 关键路径、阻塞点、精确命令和预期信号 | 同上及 `03-tasks.md` | 已融合 | 每个任务具备可执行和可验证边界 |
| 同上 | L0/L1/L2 并行等级与冲突文件 | 同上 | 适配后融合 | 只描述安全性；实际并行仍需用户明确要求或批准 |
| `ggg-implementation` | 范围冻结、失败信号、最小实现顺序 | `zstt-implementation/references/advanced-playbook.md` | 已融合 | 引用 `Txx/Dxx` 记录本阶段增量，不复制上游正文 |
| 同上 | worker 分工、文件锁、分组验证、主协调复核 | 同上 | 适配后融合 | Codex 子任务只在当前实现阶段、L2 且用户批准时使用 |
| 两套来源 | 发现上游偏差后回写 | 同上及共享权威规则 | 已融合 | 纠正对应上游主产物，不用实现记录覆盖需求或方案 |
| ZSTT 产品约束 | Git 基线、文件变化与验证结果自动取证 | `.zstt-kit/runtime/implementation_evidence.py`、实现模板 | 已融合 | 自动区分基线后出现变化、相对基线继续变化与未变化的既存改动；验证绑定工作区指纹，归属仍需复核 |

## 代码评审

| 来源 | 原能力 | ZSTT 落点 | 状态 | 适配说明 |
|---|---|---|---|---|
| `ggg-code-review` | 冻结 diff、暂存区和未跟踪业务文件 | `zstt-code-review/references/advanced-playbook.md` | 已融合 | 默认只读，不静默漏掉新业务文件 |
| 同上 | 需求/调研/方案/任务/实现一致性矩阵 | 同上及 `05-code-review.md` | 已融合 | 以权威上游和实际代码双向核验 |
| 同上 | 并行实现审计和幻觉审计 | 同上 | 已融合 | 检查不存在符号、错误位置、未落地宣称和伪验证 |
| 同上 | 专项并行审查 | 同上 | 适配后融合 | 仅用户批准时使用只读子任务；主上下文去重、位置复核 |
| 同上 | Review 轮次和修复复审 | 主产物索引 + `auxiliary/review-rounds/` | 适配后融合 | 历史轮次不覆盖，当前主报告始终唯一权威 |

## 测试验证

| 来源 | 原能力 | ZSTT 落点 | 状态 | 适配说明 |
|---|---|---|---|---|
| `verify-implementation-with-test-cases` | 需求→方案→实现→用例→实际结果证据链 | `zstt-test-verify/references/advanced-playbook.md` | 已融合 | 用例不是天然需求真相 |
| 同上 | 六类差异归因和发布判断 | 同上及测试模板 | 已融合 | 需求歧义、方案遗漏、实现偏差、用例偏差、环境/数据、覆盖不足 |
| `ggg-test-verify` | 测试资产优先级、环境、token、权限和前置数据 | 同上 | 已融合 | 凭证只记录角色和脱敏范围，不泄露秘密 |
| 同上 | JSON、Content-Type、DTO 类型和 Jackson 绑定 | 同上 | 已融合 | 区分请求没发与框架没绑定 |
| 同上 | API、SQL、缓存、MQ、ES、WebSocket 和回归 | 同上 | 已融合 | 按实际改动风险纳入应测清单 |
| 同上 | 测试轮次、原始请求响应和报告资产化 | 主产物索引 + `auxiliary/test-rounds/` | 适配后融合 | 缺少环境或 token 时标准降级，不得伪造通过 |

## 随时可用的代码简化

| 来源 | 原能力 | ZSTT 落点 | 状态 | 适配说明 |
|---|---|---|---|---|
| `code-simplification-refactor` | 范围优先级和 cleanup-only 定位 | `zstt-code-simplification/references/advanced-playbook.md` | 已融合 | 用户显式调用后默认应用安全清理，可切报告模式 |
| 同上 | Code Reuse、Simplification、Efficiency、Abstraction Level | 同上 | 已融合 | 四视角独立分析后统一去重 |
| 同上 | 四路并行审查 | 同上 | 适配后融合 | 仅用户明确要求或批准时并行，主上下文统一应用 |
| 同上 | 行为保持、风险跳过、同基线前后验证 | 同上 | 已融合 | 疑似 Bug 不混入 cleanup 修复 |
| ZSTT 产品约束 | 任意时刻调用且不占阶段 | 主 Skill | 已融合 | 不修改 `.zstt/meta.json`，不推荐固定下一阶段 |

## 随时可用的 Bug 排查与修复

| 来源 | 原能力 | ZSTT 落点 | 状态 | 适配说明 |
|---|---|---|---|---|
| `sdd-mini/issue-analysis` | 先确认契约违反，再分析责任和修复 | `zstt-bug-fix/SKILL.md`、`references/advanced-playbook.md` | 适配后融合 | 保留现有 Bug Fix 两阶段结构，在根因前增加确认卡和支持缺陷/非缺陷/有界未解决三分支 |
| `ggg-bug-fix` | 代码、日志、MySQL、ES 和时间线联合取证 | `zstt-bug-fix/references/advanced-playbook.md` | 已融合 | 测试环境和用户明确指定的生产环境均可通过环境隔离的只读 Scope 做收敛查询；目标或程序化能力不可用时生成精确条件并等待脱敏结果 |
| 同上 | 先排查结论、后二次确认修复 | `zstt-bug-fix/SKILL.md` 及 Bug 报告模板 | 已融合 | 用户最初要求修复只授权目标确认和只读取证；只有支持缺陷且看到完整结论后才能确认修复 |
| 同上 | 常见时序、缓存、MQ、ES、幂等和状态源问题模型 | Bug Fix 高级手册 | 已融合 | 问题模型只作为调查假设，必须补齐代码、数据和过程证据 |
| ZSTT 产品约束 | 独立辅助 Skill 和按需排查记录 | 当前任务或用户明确要求的 Bug 报告 | 适配后融合 | 默认只在当前任务交付，不修改固定流程 `meta.json`；契约、SQL 或核心行为变化时转入 Full/Quick 和 SQL Gate |

## 随时可用的模块重构

| 来源 | 原能力 | ZSTT 落点 | 状态 | 适配说明 |
|---|---|---|---|---|
| `agent-skills/refactor-module-safely` | 模块边界、真实调用链和行为基线 | `zstt-module-refactor/references/advanced-playbook.md` | 已融合 | 重构记录统一写入 `.zstt/refactors/` 或需求 `auxiliary/refactors/` |
| 同上 | Fast、Plan review、Behavior change 三条审阅路径 | 同上及重构记录模板 | 已融合 | 重大重构先计划审批，行为变化始终单独审批 |
| 同上 | 性能、并发、锁、线程安全、内存/GC、资源、重试和超时 | 同上 | 已融合 | 只处理有代码或运行证据的问题，保持边界不明时停止 |
| 同上 | 设计模式和 DDD 适用性 | 同上 | 已融合 | 仅在真实模式压力下使用，不为术语制造层次 |
| 同上 | characterization test 与修改前后同基线验证 | 同上 | 已融合 | 具体列出接口、数据、异常、事务、时序和副作用保持项 |
| ZSTT 产品约束 | 任意时刻调用且不占阶段 | 主 Skill | 适配后融合 | 不修改 `.zstt/meta.json`，只推荐用户决定是否重新 Review/测试 |

## 明确排除

| 能力/行为 | 状态 | 原因 |
|---|---|---|
| 自动串行阶段 | 明确排除 | 用户决定具体调用哪个 Skill |
| 完成后自动推进下一阶段 | 明确排除 | 系统只推荐，用户可先修改产物或停止 |
| 自动 commit/push/merge/deploy | 明确排除 | 固定流程止于测试结论，外部状态变更另行授权 |
| 无边界并行 | 明确排除 | 并行仅限当前显式阶段、可证明无冲突的只读或 L2 子任务 |
| 自动多 Agent 编码 | 明确排除 | 当前仅保留用户批准后的 Codex 子任务能力 |
| 个人风格命名和个人偏好规则 | 明确排除 | 只保留可解释、可验证的团队 Java 后端规范 |
| 用辅助文档替代阶段主产物 | 明确排除 | `auxiliary/` 只承载细节和历史，不能形成第二权威结论 |

## 验证测试索引

| 能力域 | 主要验证测试 |
|---|---|
| 共享能力探测、证据和产物权威 | `SharedAdvancedCapabilityContractTest`、`RuleResolverTest` |
| 混合材料需求澄清 | `RequirementAdvancedCapabilityTest` |
| 跨仓库与 CodeGraph 降级调研 | `RepositoryResearchAdvancedCapabilityTest` |
| 现有功能、证据类型和变更影响 | `ProductFeatureAnalysisAdvancedCapabilityTest` |
| 完整 Java 后端技术方案 | `TechnicalDesignAdvancedCapabilityTest` |
| 任务覆盖和并行安全 | `TaskBreakdownAdvancedCapabilityTest` |
| 实现编排和主上下文复核 | `ImplementationAdvancedCapabilityTest` |
| 幻觉审计与 Review 轮次 | `CodeReviewAdvancedCapabilityTest` |
| 环境化测试和六类差异归因 | `TestVerifyAdvancedCapabilityTest` |
| 行为保持型代码简化 | `CodeSimplificationAdvancedCapabilityTest` |
| 行为保持型模块重构 | `ModuleRefactorAdvancedCapabilityTest` |
| 缺陷确认、环境取证和二次修复门禁 | `BugFixAdvancedCapabilityTest` |
| README、能力矩阵和高级评测 | `DocumentationAndEvalContractTest` |
| 阶段门禁和 full/quick 兼容性 | `WorkflowCliGateTest`、`WorkflowEndToEndTest` |
| UTF-8 无 BOM 和 Skill 长度 | `ProjectStructureTest`、`test_skill_contracts` |

## 回归要求

任何高级能力调整都必须同时更新 Skill 正文或 playbook、对应模板（如有）、本矩阵和 `evals/evals.json`。契约测试负责检查能力关键词、显式边界、UTF-8 无 BOM、评测数量和禁止行为字段，避免能力静默丢失。
