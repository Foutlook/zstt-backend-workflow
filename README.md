# ZZTT Backend Workflow（知识跳跳）

面向小组的 Codex Java 后端开发工作流。它统一了需求澄清、代码调研、技术方案、任务拆分、编码实现、代码评审和测试验证，同时保留 quick/full 两种处理强度。

## 核心原则

- 用户显式调用具体阶段 Skill，工作流不会自动串行执行。
- 每次只完成当前阶段，并在业务仓库 `.zztt/` 生成一份权威主产物。
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

每个阶段完成后，用户可以直接修改 `.zztt` 下的权威主产物。用户调用下一阶段时，Skill 会重新校验所有必需上游文档；修改后出现 P0、缺失章节或状态不完整时，当前阶段不会创建后续产物。

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

- `prepare-stage` 在创建当前产物前重新校验上游。
- `complete-stage` 校验当前文档结构、完成状态和 P0 数量。
- `meta.json` 由工具维护，不要手工编辑。

## 错误恢复

- 缺少上游文件：回到对应阶段 Skill 补齐，不手工创建后续文档。
- P0 阻塞：在上游权威产物完成确认并清零，再重新调用当前阶段。
- 用户修改导致校验失败：按 CLI 报出的文件和章节修正，然后重试。
- 运行时证据不足：在调研、方案或测试产物中记录缺口和验证动作，不把静态推断写成事实。
- quick 影响面扩大：建议重新执行需求澄清并升级 full，不自动改变模式。

## 辅助 Skill

`$zztt-code-simplification` 可在任何时间对当前 diff、指定提交、文件或符号做行为保持型简化。它不属于固定流程，不修改阶段状态；关联需求时可在 `auxiliary/` 下记录结果。

`zztt-java-backend-standard` 是实现和 Review 共用的团队规范，不保留个人风格命名。

## 验证

```powershell
python -m unittest discover -s tests -v
```

项目测试覆盖阶段顺序、路径安全、UTF-8 无 BOM、初始化、上游重新校验、P0 阻断、quick 可选阶段和 full/quick 端到端流程。

## 非目标

- 不自动串行执行阶段。
- 不自动选择 quick/full。
- 首版不支持非 Java 技术栈或自动多 Agent 编码。
- 不自动 commit、push、合并、发布或部署。
