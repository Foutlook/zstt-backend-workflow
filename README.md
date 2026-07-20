# ZSTT Backend Workflow（知识跳跳）

面向小组的 Codex Java 后端开发工作流。它统一了需求澄清、代码调研、技术方案、任务拆分、编码实现、代码评审和测试验证，同时保留 quick/full 两种处理强度。

## 核心原则

- 用户显式调用具体阶段 Skill，工作流不会自动串行执行。
- 每次只完成当前阶段，并在业务仓库 `.zstt/` 生成一份唯一权威主产物。
- 当前阶段结束后只推荐下一步；用户可先修改产物，也可暂时停止。
- 用户调用下一阶段即表示同意推进，但上游产物必须重新校验且不存在 P0 阻塞。
- 首版仅支持 Codex 和 Java 后端项目。
- 流程止于测试验证完成，不自动 commit、push、合并或部署。

## 固定阶段

```text
$zstt-requirement-clarification
  -> $zstt-repo-research
  -> $zstt-technical-design
  -> $zstt-task-breakdown
  -> $zstt-implementation
  -> $zstt-code-review
  -> $zstt-test-verify
```

`$zstt-code-simplification` 是可随时使用的行为保持型辅助 Skill，不属于固定流程，也不推进阶段状态。

## Skill 与 Rules 分工

- Skill（技能）由用户显式选择，负责当前阶段或辅助任务的执行流程。
- Rules（规则）放在 `.zstt-kit/rules/`，由当前 Skill 在执行时动态读取，不作为用户可调用 Skill。
- Runtime（运行时）放在 `.zstt-kit/runtime/`，负责规则解析、阶段状态和确定性门禁。
- Templates（模板）放在 `.zstt-kit/templates/`，负责生成 `.zstt/` 阶段产物。

规则分为四类：`constraint`（强约束）、`decision`（条件决策）、`checklist`（检查表）和 `reference`（参考资料）。每个 Skill 先加载固定 profile（规则画像），再根据已经核实的真实代码范围追加上下文标签。例如，实现涉及 Jackson DTO 和批量查询时追加 `jackson`、`data-access`；只有出现真实变化轴或模式压力时才追加 `abstraction`、`design-patterns`。

上下文不能只凭文件名、类名或关键词推断。Skill 必须读取完整目标代码、真实调用链和最终数据源后再选择规则。解析结果包含规则集版本、规则 ID、选择原因和 SHA-256 指纹，工作范围扩大后必须重新解析。

## 高级能力

本项目不是把两套旧 Skill 改名后照搬，而是融合了 `agent-skills` 的证据化需求、方案、验收和代码简化能力，以及 `ggg-backend-skills` 的阶段门禁、跨仓库调研、任务编排、实现、评审和环境化测试能力。逐项来源和适配状态见 [高级能力融合矩阵](docs/advanced-capability-matrix.md)。

每个阶段都会先做能力探测，并记录三类结果：

- `增强路径`：远程仓库、CodeGraph、PDF/图像解析、运行环境或测试通道可用时，使用对应高级能力；
- `标准降级`：工具不可用时回退到本地源码、`rg`、静态证据或可执行的局部验证，并明确证据置信度和未验证边界；
- `阻塞`：缺少的环境、token、权限或前置数据会影响关键结论时，停止给出完成/通过结论。

工具不可用不等于可以省略能力目标，也不会成为伪造远程证据、运行结果或测试通过的理由。可选并行能力仅在用户明确要求或批准、且当前显式阶段证明安全时使用；主上下文负责去重、复核和最终写入。

每个阶段仍只有一个唯一权威主产物。接口明细、Schema、Review 轮次、测试轮次和代码简化记录等细节可写入 `auxiliary/`，但必须由主产物索引，不能形成第二份当前结论。系统可以推荐下一步，但不会自动执行任何推荐的 Skill。

## 产物目录

full 正式需求写入：

```text
.zstt/features/YYYYMMDD-feature-name/
```

quick 小需求写入：

```text
.zstt/quick/YYYYMMDD-quick-name/
```

## 安装

ZSTT 使用与 Spec Kit 类似的项目初始化方式，不依赖 Codex 插件或 Marketplace。项目管理员安装 `zstt-cli`，把 Codex 项目级 Skills 写入业务仓库并随代码提交；普通成员拉取仓库后即可使用。

运行环境要求 Python 3.11+，推荐使用 `uv` 管理命令行工具。将占位符替换为真实团队 Git 地址和发布版本：

```powershell
uv tool install zstt-cli --from "git+<团队Git仓库地址>@v0.2.0"
zstt version
```

私有仓库使用团队已有的 HTTPS 凭证或 SSH Key，不要把 token 写入命令或脚本。

### 项目管理员首次初始化

进入业务仓库执行：

```powershell
cd C:\projects\learning-service
zstt init --here
```

初始化写入下列工具文件：

```text
.agents/skills/zstt-*/
.zstt-kit/rules/
.zstt-kit/runtime/
.zstt-kit/templates/
.zstt-kit/manifest.json
```

`.zstt-kit/manifest.json` 记录 CLI 版本和受管文件 SHA-256。CLI 不覆盖 `AGENTS.md`、其他项目级 Skill、业务源码或 `.zstt/features`、`.zstt/quick` 下的需求产物。初始化完成后新建 Codex 任务，让 Codex 加载 `$zstt-*` Skills。

确认生成内容后，把 `.agents/skills/zstt-*` 和 `.zstt-kit/` 提交到业务仓库。普通团队成员只需拉取代码并新建 Codex 任务，不需要重复执行 `zstt init`；只有新项目初始化和工作流升级需要安装 `zstt-cli`。

### 项目工作流升级

先升级全局 CLI，再在每个业务仓库刷新受管文件：

```powershell
uv tool install zstt-cli --force --from "git+<团队Git仓库地址>@v0.2.0"
cd C:\projects\learning-service
zstt check --here
zstt update --here
```

如果受管 Skill、Rules、Runtime 或 Templates 被人工修改，`zstt update` 会在写文件前报告全部冲突并停止。人工合并后重试；只有明确接受覆盖时才使用 `zstt update --here --force`。`--force` 只作用于清单记录的 `.agents/skills/zstt-*`、`.zstt-kit/rules/`、`.zstt-kit/runtime/` 和 `.zstt-kit/templates/`，不能扩张到 `AGENTS.md`、`.zstt` 业务产物或其他 Skill。

从 0.1.x 升级时，清单 v1 会被兼容读取并升级为 v2。未修改的 `zstt-workflow-shared` 和 `zstt-java-backend-standard` 旧目录会被移除；存在本地修改时升级停止并报告冲突。

升级完成后新建 Codex 任务。

升级者应评审生成文件的 Git diff 并提交。其他成员拉取该提交后自动获得同一版本的项目级 Skills。CI 也可以安装清单记录的 CLI 版本后执行 `zstt check --here`，检测受管文件缺失、人工修改或版本未同步。

### 维护者本地开发

在本仓库安装当前工作区版本：

```powershell
uv tool install zstt-cli --force .
zstt version
```

再进入一个测试业务仓库执行 `zstt init --here` 或 `zstt update --here`。正式发布前运行：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\validate.ps1
```

验证脚本运行全部测试、编译 Python 源码、构建 Wheel，并检查 Wheel 包含完整 Skill、Rules、Runtime 和 Templates，且不包含 Codex 插件元数据。脚本不会自动 commit、push、合并或发布。

## 使用方式

### 1. 从需求澄清开始

用户显式调用：

```text
$zstt-requirement-clarification
请按 full 澄清这份需求：<PRD 或需求材料>
```

Skill 会在业务仓库创建 `00-requirement.md`，完成后只推荐 `$zstt-repo-research`，不会自动执行。

### 2. 用户决定是否修改

每个阶段完成后，用户可以直接修改 `.zstt` 下的权威主产物。CLI 会保存已完成产物的内容指纹；任何已完成产物被修改后，从该阶段起的完成状态都会失效。用户需要先重新确认并完成被修改阶段，才能继续下游，不允许沿用旧结论。

### 3. 显式执行下一阶段

```text
$zstt-repo-research
继续处理 .zstt/features/20260716-learning-report
```

后续阶段同理。固定流程没有统一自动入口。

## Full 产物

```text
.zstt/features/YYYYMMDD-feature-name/
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

每个阶段只生成自己的主产物，不提前创建后续空文档。

## Quick 产物

```text
.zstt/quick/YYYYMMDD-quick-name/
├─ meta.json
├─ 00-requirement.md
├─ 01-implementation.md
├─ 02-code-review.md
├─ 03-test-report.md
└─ auxiliary/
```

quick 必须先做轻量需求澄清。Review 和测试由用户决定是否调用；即使跳过 Review，测试报告仍固定使用 `03-test-report.md`。

## 状态和门禁工具

正常使用时由阶段 Skill 调用 Rules 和 Runtime。维护或排查时可以直接运行：

```text
python .zstt-kit/runtime/rule_resolver.py list-contexts
python .zstt-kit/runtime/rule_resolver.py resolve --skill zstt-implementation --context jackson --context data-access
python .zstt-kit/runtime/workflow_cli.py init --repo-root <repo> --mode full --feature-name <name>
python .zstt-kit/runtime/workflow_cli.py status --feature-dir <feature-dir>
python .zstt-kit/runtime/workflow_cli.py prepare-stage --feature-dir <feature-dir> --stage repo_research
python .zstt-kit/runtime/workflow_cli.py complete-stage --feature-dir <feature-dir> --stage requirement_clarification
```

- `prepare-stage` 在创建当前产物前重新校验上游，并对照内容指纹检测用户修改。
- `complete-stage` 校验状态、P0、必需章节实质内容、未填写模板项和阶段追溯 ID，成功后记录新指纹。
- 已完成产物发生变化时，该阶段及其下游完成状态自动撤销，但原产物文件保留；用户重新执行被修改阶段的 `complete-stage` 后才能继续。
- `meta.json` 由工具维护，不要手工编辑。

## 错误恢复

- 缺少上游文件：回到对应阶段 Skill 补齐，不手工创建后续文档。
- P0 阻塞：在上游权威产物完成确认并清零，再重新调用当前阶段。
- 用户修改已完成产物：系统撤销该阶段及下游完成状态；先核对修改影响，再重新完成被修改阶段。
- 内容门禁失败：补齐空章节、模板项和 Cxx/Exx/Dxx/Txx 追溯信息后重试，不用只改 `status` 绕过。
- 运行时证据不足：在调研、方案或测试产物中记录缺口和验证动作，不把静态推断写成事实。
- quick 影响面扩大：建议重新执行需求澄清并升级 full，不自动改变模式。

## 辅助 Skill

`$zstt-code-simplification` 可在任何时间对当前 diff、指定提交、文件或符号做行为保持型简化。它不属于固定流程，不修改阶段状态；关联需求时可在 `auxiliary/` 下记录结果。

`$zstt-module-refactor` 用于多文件职责拆分、模块化、DDD 边界和有证据的性能、并发、锁、内存/GC、资源生命周期治理。它不属于固定流程，不修改阶段状态；重大重构先生成 `.zstt/refactors/` 或需求 `auxiliary/refactors/` 下的计划并等待用户审批，可能改变业务行为的部分必须单独审批。

Java 开发规范、抽象、设计模式和 DDD 决策已经统一放入 `.zstt-kit/rules/java/`。它们由当前 Skill 动态读取，不再作为独立 Skill 暴露。

## 验证

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\validate.ps1
```

验证脚本会运行仓库测试、CLI 编译和 Wheel 内容校验。项目测试覆盖项目级 Skill/Rules/Runtime/Templates 安装、安全更新、v1→v2 升级、规则动态选择与指纹、冲突保护、阶段顺序、路径安全、UTF-8 无 BOM、实质内容门禁、追溯 ID、内容指纹、上游失效、P0 阻断、Codex 元数据、quick 可选阶段和 full/quick 端到端流程。

## 非目标

- 不自动串行执行阶段。
- 不自动选择 quick/full。
- 首版不支持非 Java 技术栈或自动多 Agent 编码。
- 不自动 commit、push、合并、发布或部署。
