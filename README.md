# ZZTT Backend Workflow（知识跳跳）

面向小组的 Codex Java 后端开发工作流。它统一了需求澄清、代码调研、技术方案、任务拆分、编码实现、代码评审和测试验证，同时保留 quick/full 两种处理强度。

## 核心原则

- 用户显式调用具体阶段 Skill，工作流不会自动串行执行。
- 每次只完成当前阶段，并在业务仓库 `.zztt/` 生成一份唯一权威主产物。
- 当前阶段结束后只推荐下一步；用户可先修改产物，也可暂时停止。
- 用户调用下一阶段即表示同意推进，但上游产物必须重新校验且不存在 P0 阻塞。
- 首版仅支持 Codex 和 Java 后端项目。
- 流程止于测试验证完成，不自动 commit、push、合并或部署。

## 固定阶段

```text
$zztt-requirement-clarification
  -> $zztt-repo-research
  -> $zztt-technical-design
  -> $zztt-task-breakdown
  -> $zztt-implementation
  -> $zztt-code-review
  -> $zztt-test-verify
```

`$zztt-code-simplification` 是可随时使用的行为保持型辅助 Skill，不属于固定流程，也不推进阶段状态。

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
.zztt/features/YYYYMMDD-feature-name/
```

quick 小需求写入：

```text
.zztt/quick/YYYYMMDD-quick-name/
```

## 安装

在本项目根目录执行：

```powershell
Copy-Item -Recurse .\skills\* "$env:USERPROFILE\.codex\skills\"
```

如果 `CODEX_HOME` 使用自定义路径，把 `skills` 下的全部目录复制到 `<CODEX_HOME>\skills\`。复制后刷新或重启 Codex。

## 使用方式

### 1. 从需求澄清开始

用户显式调用：

```text
$zztt-requirement-clarification
请按 full 澄清这份需求：<PRD 或需求材料>
```

Skill 会在业务仓库创建 `00-requirement.md`，完成后只推荐 `$zztt-repo-research`，不会自动执行。

### 2. 用户决定是否修改

每个阶段完成后，用户可以直接修改 `.zztt` 下的权威主产物。CLI 会保存已完成产物的内容指纹；任何已完成产物被修改后，从该阶段起的完成状态都会失效。用户需要先重新确认并完成被修改阶段，才能继续下游，不允许沿用旧结论。

### 3. 显式执行下一阶段

```text
$zztt-repo-research
继续处理 .zztt/features/20260716-learning-report
```

后续阶段同理。固定流程没有统一自动入口。

## Full 产物

```text
.zztt/features/YYYYMMDD-feature-name/
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
.zztt/quick/YYYYMMDD-quick-name/
├─ meta.json
├─ 00-requirement.md
├─ 01-implementation.md
├─ 02-code-review.md
├─ 03-test-report.md
└─ auxiliary/
```

quick 必须先做轻量需求澄清。Review 和测试由用户决定是否调用；即使跳过 Review，测试报告仍固定使用 `03-test-report.md`。

## 状态和门禁工具

正常使用时由阶段 Skill 调用共享 CLI。维护或排查时可以直接运行：

```text
python skills/zztt-workflow-shared/scripts/workflow_cli.py init --repo-root <repo> --mode full --feature-name <name>
python skills/zztt-workflow-shared/scripts/workflow_cli.py status --feature-dir <feature-dir>
python skills/zztt-workflow-shared/scripts/workflow_cli.py prepare-stage --feature-dir <feature-dir> --stage repo_research
python skills/zztt-workflow-shared/scripts/workflow_cli.py complete-stage --feature-dir <feature-dir> --stage requirement_clarification
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

`$zztt-code-simplification` 可在任何时间对当前 diff、指定提交、文件或符号做行为保持型简化。它不属于固定流程，不修改阶段状态；关联需求时可在 `auxiliary/` 下记录结果。

`zztt-java-backend-standard` 是实现和 Review 共用的团队规范，不保留个人风格命名。

## 验证

```powershell
python -m unittest discover -s tests -v
```

项目测试覆盖阶段顺序、路径安全、UTF-8 无 BOM、实质内容门禁、追溯 ID、内容指纹、上游失效、P0 阻断、Codex 元数据、quick 可选阶段和 full/quick 端到端流程。

## 非目标

- 不自动串行执行阶段。
- 不自动选择 quick/full。
- 首版不支持非 Java 技术栈或自动多 Agent 编码。
- 不自动 commit、push、合并、发布或部署。
