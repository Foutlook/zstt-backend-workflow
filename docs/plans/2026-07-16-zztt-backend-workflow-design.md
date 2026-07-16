# ZZTT Backend Workflow 设计

## 1. 背景与目标

`agent-skills` 已沉淀需求澄清、依赖仓库调研、后端技术方案、行为保持型简化和实现后验收等高质量单点能力；`ggg-backend-skills` 已沉淀 quick/full 双轨、显式阶段 Skill、阶段文档、状态记录、模板和自动校验。

本项目将两者统一为一套面向小组使用的 Codex Java 后端开发工作流，名称为 `ZZTT Backend Workflow（知识跳跳）`，项目目录为 `zztt-backend-workflow`。

目标：

- 首版只支持 Codex 和 Java 后端项目。
- 保留 quick/full 双轨，兼顾小改动效率和正式需求可追溯性。
- 每个固定阶段由用户显式指定 Skill，不提供自动串行总入口。
- 每个被调用阶段生成一个可独立修改、评审和校验的主产物。
- 系统只推荐下一步，不自动进入下一阶段。
- 工作流止于测试验证完成，不自动 commit、push、合并或部署。

## 2. 已确认决策

### 2.1 命名

- 项目：`zztt-backend-workflow`
- Skill 前缀：`zztt-`
- 业务仓库产物目录：`.zztt/`
- 工作流名称：`ZZTT Backend Workflow（知识跳跳）`

### 2.2 使用方式

- 用户明确调用具体阶段 Skill。
- Skill 只执行当前阶段，不提前生成后续阶段文档。
- 当前阶段结束后，输出产物路径、校验结论和推荐的下一阶段 Skill。
- 用户可自由修改阶段产物。
- 用户显式调用下一阶段，视为同意推进；无需额外说“确认通过”。
- 下一阶段仍须校验上游主产物完整且无阻塞项。

### 2.3 固定阶段 Skill

1. `zztt-requirement-clarification`
2. `zztt-repo-research`
3. `zztt-technical-design`
4. `zztt-task-breakdown`
5. `zztt-implementation`
6. `zztt-code-review`
7. `zztt-test-verify`

辅助 Skill `zztt-code-simplification` 不属于固定流程，可在任何时候显式执行，不推进阶段状态，也不占用固定阶段编号。

## 3. 工作流模型

### 3.1 Full 正式需求

```text
zztt-requirement-clarification
  -> zztt-repo-research
  -> zztt-technical-design
  -> zztt-task-breakdown
  -> zztt-implementation
  -> zztt-code-review
  -> zztt-test-verify
```

默认目录：

```text
.zztt/
└─ features/
   └─ YYYYMMDD-feature-name/
      ├─ meta.json
      ├─ 00-requirement.md
      ├─ 01-research.md
      ├─ 02-design.md
      ├─ 03-tasks.md
      ├─ 04-implementation.md
      ├─ 05-code-review.md
      ├─ 06-test-report.md
      └─ auxiliary/
```

每个阶段只维护一份权威主产物。接口、SQL、状态、发布和测试设计均写入 `02-design.md`，避免同阶段出现多个互相冲突的权威文档。

### 3.2 Quick 小需求

quick 使用相同的需求澄清 Skill，但采用轻量模板。后续只执行用户明确调用的阶段。

```text
.zztt/
└─ quick/
   └─ YYYYMMDD-quick-name/
      ├─ meta.json
      ├─ 00-requirement.md
      ├─ 01-implementation.md
      ├─ 02-code-review.md
      ├─ 03-test-report.md
      └─ auxiliary/
```

规则：

- quick 仍需澄清目标、范围、风险和验收信号。
- 实现前在 `01-implementation.md` 中先记录简短执行计划，再修改代码。
- Review 和测试仅在用户显式调用对应 Skill 时生成。
- quick 中发现接口契约、SQL、跨仓库、状态模型或历史链路影响不清时，建议升级为 full；不自动升级。

## 4. 阶段职责与产物

### 4.1 需求澄清

`zztt-requirement-clarification` 读取 PRD、截图、流程图、表格和口头描述，完成：

- quick/full 模式确认；
- 用户路径、角色权限、数据来源、数据身份和状态流转澄清；
- 异常边界、历史兼容、旧链路影响和验收标准澄清；
- 原始事实、整理归纳、推断、冲突和未确认项分离；
- P0/P1/P2 问题分级和确认结果回写。

P0 未解决时，不允许进入仓库调研。该阶段不分析代码落点，不写技术方案。

### 4.2 仓库与代码调研

`zztt-repo-research` 从需求目标出发定位真实仓库、入口、调用链、最终数据源、关键参数、旧链路副作用和跨仓库契约，生成证据优先的 `01-research.md`。

关键要求：

- 先定位直接行为点或失败点，再追到最终查询、计算、赋值或持久化位置。
- 区分 guard 条件与真实业务依赖。
- 重要结论包含仓库、文件、符号或行号证据。
- 静态源码不能证明的运行时事实必须标为待验证。
- 聚合和映射场景优先检查实体集与映射数据源是否一致。

### 4.3 技术方案

`zztt-technical-design` 基于已澄清需求和代码调研生成 `02-design.md`，回答“怎么改、为什么这样改”。

至少覆盖：

- 当前代码基线与目标差距；
- 核心数据身份、状态和职责边界；
- 真实代码改动落点；
- 接口、DTO、SQL、缓存、MQ、配置和上下游契约；
- 主流程、关键时序、兼容、发布、回滚和可观测性；
- 测试策略、风险和待确认项；
- 最小闭环方案及未采用方案的原因。

不为完整而引入未经证据支持的 fallback、替代字段、平行数据源或过度抽象。

### 4.4 任务拆分

`zztt-task-breakdown` 读取 `00`、`01`、`02` 三份主产物，生成 `03-tasks.md`。

每个任务必须包含：

- 来源需求、调研结论和设计项；
- 修改范围和预期文件；
- 前置依赖和执行顺序；
- 完成标准和验证命令；
- 风险、阻塞状态及是否可并行。

不单独增加 `plan.md`。`02-design.md` 是方案，`03-tasks.md` 同时承担可执行实施计划。

### 4.5 编码实现

`zztt-implementation` 按任务、设计和代码事实实施最小闭环改动，并生成 `04-implementation.md`。

要求：

- 修改前先确认任务、文件范围和验证方式。
- 禁止无关重构、无关格式化和推测性兼容设计。
- 禁止 N+1 查询和循环单条数据库、RPC 或外部接口调用。
- 非平凡业务边界、状态、顺序、数据源和异常兜底必须有解释原因的注释。
- 保留所有与当前改动无关的既有注释。
- Jackson 高风险 JavaBean 字段显式使用 `@JsonProperty`，必要时补绑定测试。
- 记录实际修改文件、设计偏差、验证命令和结果。

### 4.6 代码评审

`zztt-code-review` 是只读评审阶段，默认不直接修改代码，生成 `05-code-review.md`。

它基于需求、调研、方案、任务、实现记录、Git diff 和真实代码检查：

- 需求、设计、任务与实现的一致性；
- 真实执行链、最终数据源和关键参数；
- 越界修改、遗漏实现和未经证实的假设；
- Java/Jackson、SQL、事务、状态、异常、兼容、性能和安全风险；
- 注释、日志、可观测性和测试覆盖；
- 实现记录中的验证是否可复现。

有问题时推荐重新调用 `zztt-implementation`；Review 通过时推荐 `zztt-test-verify`。

### 4.7 测试验证

`zztt-test-verify` 建立“需求 -> 方案 -> 实现 -> 测试 -> 实际结果”的证据链，生成 `06-test-report.md`。

它必须：

- 先列出应测场景和测试前置条件；
- 区分需求歧义、方案遗漏、实现偏差、测试用例偏差、环境/数据问题和覆盖不足；
- 执行与风险相称的编译、单测、接口、主链路、异步、SQL 和回归验证；
- 未测或阻塞场景说明原因；
- 关键场景失败或未测时不得给出“通过”；
- 给出建议交付、有条件交付、暂缓交付或无法判断的证据化结论。

## 5. 状态与门禁

`meta.json` 只记录事实，不自动触发阶段：

- 模式：quick/full；
- 当前已完成阶段；
- 各主产物路径；
- P0/P1/P2 数量；
- 阻塞项；
- 最近校验结果和时间；
- 推荐下一阶段 Skill。

门禁原则：

1. 用户显式调用下一阶段表示同意推进。
2. 上游主产物不存在、结构不完整或有 P0 阻塞时，当前 Skill 停止并报告修复点。
3. P1/P2 可带风险推进，但必须在当前产物中继承并说明处理计划。
4. 用户修改上游产物后，下游 Skill 必须重新校验，不信任旧校验状态。
5. 阶段失败不得生成伪完成产物或推进完成状态。

## 6. 辅助能力

`zztt-code-simplification` 可在任意时点执行，作用范围为当前 diff、指定提交、文件或符号。

- 只做行为保持型简化和安全清理。
- 不查找或修复业务 Bug，不改变接口、数据范围和调用时机。
- 不推进固定阶段状态。
- 关联需求时写入 `auxiliary/code-simplification-时间戳.md`；未关联需求时不强制创建文档。

团队 Java 规范作为共享参考维护，不保留“个人风格”命名。只有已被团队认可、可以客观评审的规则进入规范。

## 7. 组件结构

```text
zztt-backend-workflow/
├─ README.md
├─ docs/plans/
├─ skills/
│  ├─ zztt-requirement-clarification/
│  ├─ zztt-repo-research/
│  ├─ zztt-technical-design/
│  ├─ zztt-task-breakdown/
│  ├─ zztt-implementation/
│  ├─ zztt-code-review/
│  ├─ zztt-test-verify/
│  ├─ zztt-code-simplification/
│  ├─ zztt-java-backend-standard/
│  └─ zztt-workflow-shared/
│     ├─ assets/templates/
│     ├─ references/
│     └─ scripts/
└─ tests/
```

阶段 Skill 负责判断和执行；共享底座负责路径、模板、元数据和确定性校验；Java 规范负责统一编码与 Review 基线。

## 8. 错误处理

- 输入不足：只报告最小缺口，不生成空洞的完整文档。
- 上游冲突：回到上游权威产物修正，不在下游增加 fallback 掩盖冲突。
- 代码或仓库不可读：记录尝试、失败边界、未验证结论和所需补充。
- 校验失败：不推进阶段，给出具体文件、缺失章节或阻塞项。
- 测试环境不可用：区分代码验证和环境验证，不把环境失败包装成代码失败。
- 用户改动存在：保留并绕开无关改动，不使用破坏性 Git 命令。

## 9. 测试策略

首版至少验证：

- full/quick 目录和 `meta.json` 初始化；
- 阶段主产物固定命名；
- 缺少上游产物时阻止推进；
- P0 阻塞时阻止推进；
- P1/P2 风险可继承；
- 用户修改上游后重新校验；
- 每个阶段模板包含必需章节；
- 任务可追溯到设计和调研；
- quick 不机械生成未调用阶段产物；
- 辅助 Skill 不改变固定阶段状态；
- 所有新建或修改的文本文件为 UTF-8 无 BOM。

## 10. 非目标

- 不提供自动串行执行所有阶段的总入口 Skill。
- 不自动选择并执行下一阶段。
- 不在首版支持非 Java 技术栈或多 Agent 并行编码。
- 不自动 commit、push、合并、发布或部署。
- 不为了兼容两套旧项目而保留旧的 `ggg`、`tob` 或个人风格命名。
