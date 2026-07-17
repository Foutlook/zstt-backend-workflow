# ZZTT 高级能力融合矩阵

本文记录 `agent-skills` 与 `ggg-backend-skills` 的高级能力如何进入 ZZTT。目标不是照搬目录或文案，而是在“用户显式选择 Skill、阶段只推荐不自动执行、每阶段一个权威主产物、产物写入业务仓库 `.zztt/`”的产品约束下完成能力融合。

状态含义：

- `已融合`：语义和执行方式可直接保留；
- `适配后融合`：保留能力，但按 Codex、ZZTT 阶段或产物权威规则调整实现；
- `明确排除`：与已确认产品边界冲突，不进入当前版本。

## 共享工作流能力

| 来源 | 原能力 | ZZTT 落点 | 状态 | 适配说明 |
|---|---|---|---|---|
| 两套来源 | 证据优先、事实与推断分离 | `zztt-workflow-shared/references/evidence-rules.md` | 已融合 | 增加 Claim Ledger、反证、置信度、运行时缺口和验证动作 |
| ggg-backend-skills | 阶段状态、上游门禁、P0 阻断 | `workflow-protocol.md`、`workflow_cli.py`、`workflow_validation.py` | 适配后融合 | 阶段由用户显式调用；门禁检查实质内容和追溯 ID，并用内容指纹使修改阶段及下游旧结论失效 |
| 两套来源 | 工具增强和不可用降级 | `capability-fallback.md` | 适配后融合 | 统一为能力探测、增强路径、标准降级和证据置信度 |
| agent-skills | 用户纠正与证据回写 | `document-authority-and-corrections.md` | 适配后融合 | 当前阶段一个唯一权威主产物，细节只进 `auxiliary/` |
| ggg-backend-skills | full/quick 两种强度 | 共享模板和 CLI | 已融合 | 路径和固定编号保持稳定，不因跳过可选阶段重排 |

## 需求澄清

| 来源 | 原能力 | ZZTT 落点 | 状态 | 适配说明 |
|---|---|---|---|---|
| `agent-skills/prd-clarifier` | PRD、PDF、截图、流程图、表格等混合材料 | `zztt-requirement-clarification/references/advanced-playbook.md` | 已融合 | 先做输入盘点和可读性边界，再提炼需求 |
| `agent-skills/prd-clarifier` | 冲突扫描、多轮澄清、确认日志 | 同上及 `00-requirement.md` 模板 | 已融合 | P0/P1/P2 分级，保留用户逐轮确认结果 |
| `ggg-prd-intake` | quick/full 分流和范围边界 | 同上 | 适配后融合 | 模式由用户选择或确认，不自动升级 |
| 两套来源 | 产物完成后继续下一阶段 | Skill 推荐语 | 适配后融合 | 只推荐 `zztt-repo-research`，不会自动执行 |

## 仓库调研

| 来源 | 原能力 | ZZTT 落点 | 状态 | 适配说明 |
|---|---|---|---|---|
| `clarified-requirement-repo-research` | 仓库边界、主项目、跨仓库证据链 | `zztt-repo-research/references/advanced-playbook.md` | 已融合 | 每个结论绑定证据 ID、反证和覆盖度 |
| 同上 | 入口到最终 fetch/calculation/assignment 的真实调用链 | 同上 | 已融合 | 显式区分历史 guard 与真实业务依赖 |
| `ggg-requirement-alignment` | 远程仓库优先、本地 checkout 降级 | 同上 | 适配后融合 | 远程能力不可用时回退本地源码，不伪造远程证据 |
| `ggg-requirement-alignment` | CodeGraph 图谱分析和索引新鲜度 | 同上 | 适配后融合 | CodeGraph 不可用或索引过期时用 `rg` + 逐层源码并标记 `pending` |
| 两套来源 | 旧链路副作用、运行时验证缺口 | `01-research.md` 模板 | 已融合 | 不能把静态推断写成运行事实 |

## 技术方案

| 来源 | 原能力 | ZZTT 落点 | 状态 | 适配说明 |
|---|---|---|---|---|
| `writing-backend-technical-solutions` | 输入清单、高影响歧义、当前基线与差距 | `zztt-technical-design/references/advanced-playbook.md` | 已融合 | 未闭合的高影响歧义继续作为 P0 |
| 同上 | Dxx/Cxx 决策、候选方案和未采用理由 | 同上及 `02-design.md` 模板 | 已融合 | 主方案与取舍均可评审 |
| 同上 | Mermaid 架构/流程/时序图及实现映射 | 同上 | 已融合 | 图只表达可被代码证据支持的角色和链路 |
| 同上 | 接口、错误码、幂等、Jackson、兼容性 | 同上 | 已融合 | JavaBean 高风险字段要求显式绑定测试 |
| 同上 | MySQL/Redis/ES/MQ、索引、事务、缓存、迁移 | 同上 | 已融合 | 每个存储选择必须有准入理由和回滚策略 |
| `ggg-technical-design` | 灰度、监控、发布、回滚和压力测试 | 同上 | 已融合 | 附件可进 `auxiliary/`，主结论仍回写权威方案 |

## 任务拆分与实现

| 来源 | 原能力 | ZZTT 落点 | 状态 | 适配说明 |
|---|---|---|---|---|
| `ggg-task-breakdown` | 需求/设计到任务覆盖矩阵 | `zztt-task-breakdown/references/advanced-playbook.md` | 已融合 | 接口、SQL、代码和测试均能追到任务 |
| 同上 | 关键路径、阻塞点、精确命令和预期信号 | 同上及 `03-tasks.md` | 已融合 | 每个任务具备可执行和可验证边界 |
| 同上 | L0/L1/L2 并行等级与冲突文件 | 同上 | 适配后融合 | 只描述安全性；实际并行仍需用户明确要求或批准 |
| `ggg-implementation` | 范围冻结、失败信号、最小实现顺序 | `zztt-implementation/references/advanced-playbook.md` | 已融合 | 先写当前阶段计划，再修改业务代码 |
| 同上 | worker 分工、文件锁、分组验证、主协调复核 | 同上 | 适配后融合 | Codex 子任务只在当前实现阶段、L2 且用户批准时使用 |
| 两套来源 | 发现上游偏差后回写 | 同上及共享权威规则 | 已融合 | 纠正对应上游主产物，不用实现记录覆盖需求或方案 |

## 代码评审

| 来源 | 原能力 | ZZTT 落点 | 状态 | 适配说明 |
|---|---|---|---|---|
| `ggg-code-review` | 冻结 diff、暂存区和未跟踪业务文件 | `zztt-code-review/references/advanced-playbook.md` | 已融合 | 默认只读，不静默漏掉新业务文件 |
| 同上 | 需求/调研/方案/任务/实现一致性矩阵 | 同上及 `05-code-review.md` | 已融合 | 以权威上游和实际代码双向核验 |
| 同上 | 并行实现审计和幻觉审计 | 同上 | 已融合 | 检查不存在符号、错误位置、未落地宣称和伪验证 |
| 同上 | 专项并行审查 | 同上 | 适配后融合 | 仅用户批准时使用只读子任务；主上下文去重、位置复核 |
| 同上 | Review 轮次和修复复审 | 主产物索引 + `auxiliary/review-rounds/` | 适配后融合 | 历史轮次不覆盖，当前主报告始终唯一权威 |

## 测试验证

| 来源 | 原能力 | ZZTT 落点 | 状态 | 适配说明 |
|---|---|---|---|---|
| `verify-implementation-with-test-cases` | 需求→方案→实现→用例→实际结果证据链 | `zztt-test-verify/references/advanced-playbook.md` | 已融合 | 用例不是天然需求真相 |
| 同上 | 六类差异归因和发布判断 | 同上及测试模板 | 已融合 | 需求歧义、方案遗漏、实现偏差、用例偏差、环境/数据、覆盖不足 |
| `ggg-test-verify` | 测试资产优先级、环境、token、权限和前置数据 | 同上 | 已融合 | 凭证只记录角色和脱敏范围，不泄露秘密 |
| 同上 | JSON、Content-Type、DTO 类型和 Jackson 绑定 | 同上 | 已融合 | 区分请求没发与框架没绑定 |
| 同上 | API、SQL、缓存、MQ、ES、WebSocket 和回归 | 同上 | 已融合 | 按实际改动风险纳入应测清单 |
| 同上 | 测试轮次、原始请求响应和报告资产化 | 主产物索引 + `auxiliary/test-rounds/` | 适配后融合 | 缺少环境或 token 时标准降级，不得伪造通过 |

## 随时可用的代码简化

| 来源 | 原能力 | ZZTT 落点 | 状态 | 适配说明 |
|---|---|---|---|---|
| `code-simplification-refactor` | 范围优先级和 cleanup-only 定位 | `zztt-code-simplification/references/advanced-playbook.md` | 已融合 | 用户显式调用后默认应用安全清理，可切报告模式 |
| 同上 | Code Reuse、Simplification、Efficiency、Abstraction Level | 同上 | 已融合 | 四视角独立分析后统一去重 |
| 同上 | 四路并行审查 | 同上 | 适配后融合 | 仅用户明确要求或批准时并行，主上下文统一应用 |
| 同上 | 行为保持、风险跳过、同基线前后验证 | 同上 | 已融合 | 疑似 Bug 不混入 cleanup 修复 |
| ZZTT 产品约束 | 任意时刻调用且不占阶段 | 主 Skill | 已融合 | 不修改 `.zztt/meta.json`，不推荐固定下一阶段 |

## 随时可用的模块重构

| 来源 | 原能力 | ZZTT 落点 | 状态 | 适配说明 |
|---|---|---|---|---|
| `agent-skills/refactor-module-safely` | 模块边界、真实调用链和行为基线 | `zztt-module-refactor/references/advanced-playbook.md` | 已融合 | 重构记录统一写入 `.zztt/refactors/` 或需求 `auxiliary/refactors/` |
| 同上 | Fast、Plan review、Behavior change 三条审阅路径 | 同上及重构记录模板 | 已融合 | 重大重构先计划审批，行为变化始终单独审批 |
| 同上 | 性能、并发、锁、线程安全、内存/GC、资源、重试和超时 | 同上 | 已融合 | 只处理有代码或运行证据的问题，保持边界不明时停止 |
| 同上 | 设计模式和 DDD 适用性 | 同上 | 已融合 | 仅在真实模式压力下使用，不为术语制造层次 |
| 同上 | characterization test 与修改前后同基线验证 | 同上 | 已融合 | 具体列出接口、数据、异常、事务、时序和副作用保持项 |
| ZZTT 产品约束 | 任意时刻调用且不占阶段 | 主 Skill | 适配后融合 | 不修改 `.zztt/meta.json`，只推荐用户决定是否重新 Review/测试 |

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
| 共享能力探测、证据和产物权威 | `SharedAdvancedCapabilityContractTest` |
| 混合材料需求澄清 | `RequirementAdvancedCapabilityTest` |
| 跨仓库与 CodeGraph 降级调研 | `RepositoryResearchAdvancedCapabilityTest` |
| 完整 Java 后端技术方案 | `TechnicalDesignAdvancedCapabilityTest` |
| 任务覆盖和并行安全 | `TaskBreakdownAdvancedCapabilityTest` |
| 实现编排和主上下文复核 | `ImplementationAdvancedCapabilityTest` |
| 幻觉审计与 Review 轮次 | `CodeReviewAdvancedCapabilityTest` |
| 环境化测试和六类差异归因 | `TestVerifyAdvancedCapabilityTest` |
| 行为保持型代码简化 | `CodeSimplificationAdvancedCapabilityTest` |
| 行为保持型模块重构 | `ModuleRefactorAdvancedCapabilityTest` |
| README、能力矩阵和高级评测 | `DocumentationAndEvalContractTest` |
| 阶段门禁和 full/quick 兼容性 | `WorkflowCliGateTest`、`WorkflowEndToEndTest` |
| UTF-8 无 BOM 和 Skill 长度 | `ProjectStructureTest`、`test_skill_contracts` |

## 回归要求

任何高级能力调整都必须同时更新 Skill 正文或 playbook、对应模板（如有）、本矩阵和 `evals/evals.json`。契约测试负责检查能力关键词、显式边界、UTF-8 无 BOM、评测数量和禁止行为字段，避免能力静默丢失。
