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
6. 在修改业务代码前，必须让用户明确选择开发载体：`指定分支` 或独立 `worktree`；不得替用户选择。用户还需确认开发分支名，选择 worktree 时同时确认目标路径。先运行 `git status --short` 和 `git worktree list --porcelain`，核对当前改动、分支与 worktree 占用关系。
7. 已有开发分支只按用户指定使用，不自动 merge 或 rebase。需要新建开发分支时，必须先成功执行 `git fetch --prune origin`，自动枚举并确定最新远程 `release`、`release/*`、`release-*` 候选，再用双向 `git merge-base --is-ancestor` 与 `origin/master` 比较：release 已合入 master 时以 master 为基线，master 是 release 的祖先且 release 领先时以 release 为基线；双方分叉或无法可靠确定最新 release 时停止并展示证据，不要求用户预先指定 release，也不擅自 merge、rebase 或按名称猜测。创建分支或 worktree 时使用所选基线的精确提交 ID，不使用本地旧引用。
8. 切换分支会影响未提交内容、分支已被其他 worktree 占用、目标路径非空、远程更新失败，或目标 checkout 缺少该需求的 `.zstt` 权威产物和 `.zstt-kit` 时停止并说明解除条件。不得自动 stash、commit、复制需求产物、手改 `meta.json`、强制切换或删除 worktree。已有目标 worktree 时进入其路径继续，不重复创建。
9. 进入用户确认的目标 checkout 后，重新核对仓库根目录、当前分支、HEAD、需求目录和 Runtime 可用性；后续 `prepare-stage`、代码修改、验证与完成命令必须都在该 checkout 内执行。需求状态仍绑定原分支时，向用户展示原分支和当前开发分支；只有本轮已确认开发载体时才运行 `rebind-branch --from-branch <原分支> --feature-dir <需求目录> --repo-root <目标仓库>`。原分支校验失败时停止，不得手改 `meta.json` 或靠显式路径绕过冲突。
10. 运行 `python .zstt-kit/runtime/workflow_cli.py prepare-stage --stage implementation --feature-dir <需求目录>`。CLI 重新校验上游、创建实现产物，并把目标 checkout 的当前 Git 工作区自动保存为 `auxiliary/implementation-evidence.json` 基线。
11. Runtime 按“存在即消费”处理可选质量门禁：Full 检查 `analysis/artifact-analysis.md`，Quick 检查 `checklists/requirements.md`；文件不存在表示用户跳过，存在 P0、输入指纹过期或报告无效时停止，只有 P1/P2 时记录风险后继续。不得删除报告来规避已经发现的问题。
12. 读取自动生成的实现证据并核对目标文件定向 diff。Runtime 只保存文件级路径和内容指纹，用于区分基线后出现变化、既存未变、既存继续变化和已消失基线；这些分类都不是代码归属结论。新上下文中若没有可核对的 patch、提交或会话记录，就不能从 SHA 恢复同文件的原始 hunk，必须明确无法精确归属并请求用户确认。不要使用破坏性命令回滚。

## 实现顺序

1. 从真实入口、调用链和最终数据源定位最小修改点。
2. 逐项执行任务或 quick 边界，先建立失败测试或可复现失败信号。
3. 写最小实现，运行局部验证，再继续下一项。
4. full 只按 `Txx/Dxx`、quick 只按 `Rxx` 记录当前阶段增量；不要复制上游正文。非交互编译和测试通过 `workflow_cli.py run-validation --feature-dir <需求目录> -- <命令>` 由主上下文串行执行，让 Runtime 自动记录命令、退出码、耗时和执行时工作区指纹；代码后来变化时旧验证会标为过期。
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

full 更新 `04-implementation.md`；quick 更新 `01-implementation.md`。主产物只保留可评审的增量结论，Git 基线、当前工作区和验证运行由 Runtime 写入 `auxiliary/implementation-evidence.json` 并同步到自动证据区。至少记录：

- 实现边界和改动前失败信号；
- full 的 `Txx/Dxx` 或 quick 的 `Rxx` 增量映射、实际文件与符号和状态；
- 偏差及对应上游回写；
- 注释、Jackson、数据源、N+1、异常、兼容和关键业务行为的人工结论；
- 未验证边界、残余风险和下一步。

不要手工复制 `git status`、文件清单和验证退出码。自动证据只证明工作区相对基线发生了什么，不能替代对完整 diff、真实调用链和业务行为的人工复核。

## 完成门禁

1. 运行与风险相称的编译、单测或局部验证。非交互命令使用 `run-validation` 自动留证；至少一条成功验证必须匹配最终工作区快照，且同一快照不能仍有失败验证。Maven 项目若 smart-doc 绑定早期生命周期，业务验证命令传 `-Dsmart-doc.phase=verify`。
2. 单项任务只有在主产物闭环映射中的本轮改动、验证命令和结果均可归因时才记为 `done`；既存失败必须有“改动前已失败且失败链路不受本轮影响”的证据，否则按未闭环处理。
3. 只要存在任务 `blocked`、待确认的上游偏差、P0、关键验证失败/未执行或失败归因不清，就保持 `status: draft`，更新真实问题数量和解除条件，不运行完成命令，也不把局部完成表述为阶段完成。
4. 仅当范围内任务全部 `done`、P0 为 0 且风险相称的验证闭环后，才设 `status: completed` 并运行 `complete-stage --stage implementation`。CLI 会在校验前自动采集最终 Git 快照并刷新主产物自动证据区。
5. 完成命令失败时立即停止，将 frontmatter 恢复为 `draft`，保留实现与验证证据并记录失败原因和重试条件；不得手改 `meta.json` 或宣称阶段完成。
6. 只有完成命令成功后，才输出阶段完成、实际改动、验证结果和产物路径，并推荐 `$zstt-code-review`；不得自动执行。Quick 若用户明确跳过可选 Review 与测试，应提示用户运行 `close --current --repo-root <业务仓库>` 显式关闭工作流，但不得代替用户自动关闭。

## 禁止事项

- 不自动执行代码评审、Git commit、push、合并、删除开发分支、移除 worktree 或部署。
- 不把未执行的测试写成已通过。
- 不因实现困难而扩展需求或增加未经证明的兼容逻辑。
