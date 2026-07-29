---
name: zstt-implementation
description: ZSTT Java 后端编码实现阶段。仅当用户明确指定 $zstt-implementation，或明确要求执行“ZSTT 编码实现阶段”时使用；按 full 任务或 quick 边界修改代码并生成实现记录，不自动进入 Review。
---

# ZSTT Implementation

## 定位

按照已确认的范围实施最小闭环改动，并留下可复现的实现与验证记录。仅当用户明确指定本 Skill 时修改代码。

结束后可以推荐 `$zstt-code-review`，但不得自动执行推荐的下一阶段。

## 开始前

1. 运行 `python .zstt-kit/runtime/rule_resolver.py resolve --skill zstt-implementation`。
2. 以 UTF-8 完整读取解析结果中每个规则的 `path`，记录 `rulesetVersion`、`rulesetFingerprint`、规则 ID 和选择原因。解析失败或规则缺失时停止，并执行 `zstt check --here`。
3. 完整读取本阶段 `references/advanced-playbook.md`。
4. full 读取 `00`–`03` 主产物；quick 读取 `00-requirement.md`。根据任务、完整目标文件、真实调用链和最终数据源追加 `jackson`、`data-access`、`transaction`、`concurrency`、`abstraction`、`design-patterns` 或 `ddd` 等上下文并重新解析；不得只凭文件名选择规则。
5. 用户显式给出的需求目录优先；未给目录时运行 `current --repo-root <业务仓库>`，仅接受当前 Git 分支上的唯一未完成需求。0 个或多个候选时运行 `list --repo-root <业务仓库>` 展示候选并要求用户选择，禁止按日期猜测。
6. 运行 `python .zstt-kit/runtime/workflow_cli.py prepare-stage --stage implementation --feature-dir <需求目录>`，让 CLI 重新校验上游，并先在实现产物写简短执行计划。
7. 记录会话基线：`git status --short`、目标文件定向 diff 和未跟踪状态；将开始前已有内容标为用户工作区基线，不把它归因于本轮，也不使用破坏性命令回滚。

## 实现顺序

1. 从真实入口、调用链和最终数据源定位最小修改点。
2. 逐项执行任务或 quick 边界，先建立失败测试或可复现失败信号。
3. 写最小实现，运行局部验证，再继续下一项。
4. 同步记录实际文件、任务状态、命令和结果。
5. 发现实现需要偏离需求、调研、方案、接口或 SQL 时停止；先让用户确认并回写权威产物。

目标文件已有改动时，先完整理解相关上下文和既存 hunk，只修改能与本轮范围隔离的部分；无法区分归属或会覆盖既存行为时停止并请求用户确认，不自动 stash、reset、暂存或提交。最终只声明相对会话基线新增的改动，并单列仍在工作区的既存变更。

full 按任务状态、依赖、关键路径和 L0/L1/L2 执行。只有用户明确要求或批准、任务写集独立且工具可用时，才在当前实现阶段启用可选 Codex 子任务；主上下文必须建立文件锁并复核全部结果。

## Java 后端硬门禁

- 禁止 N+1 查询；批量场景先收集参数，再批量查询或批量调用并在内存映射。
- 禁止在循环中按单 ID 查询数据库、Mapper、Repository、RPC 或外部 API，避免循环远程调用。
- 禁止无关重构、无关格式化、整片风格清洗和推测性 fallback。
- 保留既有注释；只更新当前逻辑相关注释，非平凡业务边界、状态、顺序、数据源和异常兜底解释“为什么”。
- Jackson 高风险字段按解析出的 `java.jackson` 规则显式声明 `@JsonProperty`，需要历史兼容时才加 `@JsonAlias`，并补绑定测试。
- 聚合与映射从同一实体范围闭环派生，不用平行数据源隐藏范围不一致。
- 不吞异常，不在事务中无依据扩大远程调用和慢操作范围。

## 主产物

full 更新 `04-implementation.md`；quick 更新 `01-implementation.md`。至少记录：

- 实现前检查和执行计划；
- 任务闭环映射：full 按 `Txx`、quick 按目标项，记录实际文件与符号、改动前失败信号、修改后验证命令与结果、残余风险和状态；共享文件中的改动逐项归属；
- 设计偏差及上游回写；
- 注释、Jackson、数据源、N+1、异常和兼容自检；
- 测试或验证命令、退出码和关键结果。

## 完成门禁

1. 运行与风险相称的编译、单测或局部验证。Maven 项目若 smart-doc 绑定早期生命周期，业务验证命令传 `-Dsmart-doc.phase=verify`。
2. 单项任务只有在主产物闭环映射中的本轮改动、验证命令和结果均可归因时才记为 `done`；既存失败必须有“改动前已失败且失败链路不受本轮影响”的证据，否则按未闭环处理。
3. 只要存在任务 `blocked`、待确认的上游偏差、P0、关键验证失败/未执行或失败归因不清，就保持 `status: draft`，更新真实问题数量和解除条件，不运行完成命令，也不把局部完成表述为阶段完成。
4. 仅当范围内任务全部 `done`、P0 为 0 且风险相称的验证闭环后，才设 `status: completed` 并运行 `complete-stage --stage implementation`。
5. 完成命令失败时立即停止，将 frontmatter 恢复为 `draft`，保留实现与验证证据并记录失败原因和重试条件；不得手改 `meta.json` 或宣称阶段完成。
6. 只有完成命令成功后，才输出阶段完成、实际改动、验证结果和产物路径，并推荐 `$zstt-code-review`；不得自动执行。Quick 若用户明确跳过可选 Review 与测试，应提示用户运行 `close --current --repo-root <业务仓库>` 显式关闭工作流，但不得代替用户自动关闭。

## 禁止事项

- 不自动执行代码评审、Git commit、push、合并或部署。
- 不把未执行的测试写成已通过。
- 不因实现困难而扩展需求或增加未经证明的兼容逻辑。
