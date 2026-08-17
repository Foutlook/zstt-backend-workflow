# ZSTT Quick Start

用 10 分钟把 ZSTT 安装到 Java 后端业务仓库，并跑通第一个 Full 或 Quick 工作流。

> ZSTT 面向 Codex 和 Java 后端项目。每个 Skill 都需要用户显式调用；系统只推荐下一步，不会自动推进，也不会自动 commit、push、合并或部署。

## 1. 管理员安装 CLI

环境要求：

- Windows PowerShell；
- Python 3.11+；
- 推荐安装 [`uv`](https://docs.astral.sh/uv/)。

安装最新版本：

```powershell
uv tool install zstt-cli --force --from "git+https://github.com/Foutlook/zstt-backend-workflow.git"
zstt version
```

## 2. 初始化业务仓库

进入真实的业务 Git 仓库根目录：

```powershell
cd C:\projects\learning-service
zstt init --here
zstt doctor --here
```

初始化后主要生成：

```text
.agents/skills/zstt-*/         # 13 个 Codex 项目级 Skill
.zstt-kit/rules/               # 动态工作流和 Java 规则
.zstt-kit/runtime/             # 状态、指纹和门禁工具
.zstt-kit/templates/           # Full、Quick 和质量门禁模板
.zstt-kit/manifest.json        # CLI 版本与受管文件校验值
```

确认 `zstt doctor --here` 输出正常后，将 `.agents/skills/zstt-*` 和 `.zstt-kit/` 提交到业务仓库。

> `.agents/skills` 必须安装在实际 Git 仓库内。若当前目录只是包含多个子仓库的聚合目录，应分别进入每个子仓库初始化。

## 3. 团队成员开始使用

团队成员拉取管理员提交的文件后，不需要重复安装或初始化。请在业务仓库根目录新建 Codex 任务。

### 选择 Full

适用于正式需求、跨模块修改、接口/消息/数据结构变化、SQL 变化或高风险业务逻辑：

```text
$zstt-requirement-clarification
请按 full 模式澄清这份需求：<粘贴 PRD、截图、流程图、表格或口头说明>
```

Full 固定链路：

```text
需求澄清
  → 仓库调研
  → 技术方案
  → 任务拆分
  → 编码实现
  → 代码评审
  → 测试验证
```

对应 Skill：

```text
$zstt-requirement-clarification
$zstt-repo-research
$zstt-technical-design
$zstt-task-breakdown
$zstt-implementation
$zstt-code-review
$zstt-test-verify
```

### 选择 Quick

适用于范围明确、影响面小、风险较低且不需要独立方案评审的小改动：

```text
$zstt-requirement-clarification
请按 quick 模式澄清这个小改动：<问题描述与验收标准>
```

Quick 固定链路：

```text
需求澄清 → 编码实现
              ├─ 代码评审（可选）
              └─ 测试验证（可选）
```

Quick 需求只保留目标、允许修改、明确不做、升级 Full 条件和验收信号；无关维度不展开。模式评估、用户决定和决定来源会写入产物；决定升级 Full 时当前 Quick 保持 draft。实现阶段引用这些 `Rxx` 契约，只补充实际增量和偏差。

如果没有指定模式，需求澄清 Skill 会给出 Full/Quick 推荐和依据，最终仍由用户选择。

若完成实现后决定同时跳过 Review 和测试，可以显式关闭 Quick：

```powershell
python .zstt-kit/runtime/workflow_cli.py close --current --repo-root .
```

## 4. 审阅产物后继续

需求澄清会创建：

```text
# Full
.zstt/features/YYYYMMDD-feature-name/

# Quick
.zstt/quick/YYYYMMDD-quick-name/
```

每个需求目录都包含 Runtime 管理的 `meta.json` 和当前阶段主产物。请先审阅当前产物，再显式调用下一 Skill。

Full 示例：

```text
$zstt-repo-research
继续处理 .zstt/features/20260729-learning-report
```

Quick 示例：

```text
$zstt-implementation
继续处理 .zstt/quick/20260729-fix-learning-report
```

准备实现时，Runtime 会自动创建 `auxiliary/implementation-evidence.json` 并保存当前 Git 基线。需要执行非交互验证时，Skill 会使用：

```powershell
python .zstt-kit/runtime/workflow_cli.py run-validation --feature-dir <feature-dir> -- mvn test
```

该命令记录脱敏后的命令、退出码、耗时和执行时工作区指纹。完成实现时 Runtime 再采集当前工作区，区分基线后出现变化、相对基线继续变化和未变化的既存改动；代码后来变化时旧验证会标为过期。实现完成门禁要求至少一条成功验证匹配最终快照，且同一快照不能仍有失败验证；文件分类仍不能代替完整 diff 归属复核。

> 不要手工修改 `meta.json`。直接修改已完成的主产物是允许的，但 Runtime 会使该阶段及下游旧状态失效；修正后需要重新执行对应阶段。

## 5. 按需执行两个质量门禁

两个门禁都可以跳过，不改变固定链路。

### 需求 Checklist

在 Full 仓库调研前或 Quick 实现前，检查需求是否完整、清晰、一致、可度量和可追溯：

```text
$zstt-requirement-checklist
检查 .zstt/features/20260729-learning-report
```

报告写入：

```text
checklists/requirements.md
```

### 实现前一致性分析

仅用于 Full，在任务拆分完成、编码开始前检查需求、调研、方案和任务是否对齐：

```text
$zstt-artifact-analysis
分析 .zstt/features/20260729-learning-report
```

报告写入：

```text
analysis/artifact-analysis.md
```

质量报告不存在表示跳过；一旦存在，下游就会校验。报告存在 P0、无效或输入过期时会阻断；只有 P1/P2 时记录风险后可以继续。

发现问题时，应返回对应阶段修改权威主产物，再重新执行质量 Skill。不要只在对话中修正，也不要只修改质量报告。

## 6. 其他常用入口

这四个辅助 Skill 不推进 Full/Quick 阶段：

| 场景 | Skill | 关键边界 |
| --- | --- | --- |
| 说明已有功能、规则、接口或数据来源 | `$zstt-product-feature-analysis` | 默认只说明当前行为；新需求转需求澄清，疑似缺陷转 Bug Fix |
| Bug、线上/偶现问题、数据或日志异常 | `$zstt-bug-fix` | 先确认缺陷/非缺陷/有界未解决；支持缺陷且开发角色得到二次确认后才修改代码 |
| 功能正确，只需要行为保持型简化 | `$zstt-code-simplification` | 不混入 Bug 修复或架构重构 |
| 多文件职责、模块/DDD 边界或资源治理 | `$zstt-module-refactor` | 重大重构和行为变化先获得用户审批 |

## 7. 暂停和恢复

可以随时关闭当前 Codex 任务。工作进度保存在 `.zstt/`，新任务中继续使用同一需求目录即可：

```text
$zstt-technical-design
继续处理 .zstt/features/20260729-learning-report
```

需要查看当前分支上的需求时：

```powershell
python .zstt-kit/runtime/workflow_cli.py list --repo-root .
python .zstt-kit/runtime/workflow_cli.py current --repo-root .
python .zstt-kit/runtime/workflow_cli.py status --current --repo-root .
```

Runtime 只按当前 Git 分支选择唯一活动需求，不会按日期或最近修改时间猜测。

## 8. 常见问题

### Codex 找不到 `$zstt-*`

```powershell
zstt doctor --here
```

确认 Skill 位于当前业务 Git 仓库的 `.agents/skills/` 内，然后新建 Codex 任务。

### 上游产物修改后无法继续

这是输入指纹门禁生效。重新检查修改影响，显式调用被修改阶段，完成校验后再继续下游。

### 质量报告显示 `stale`

上游权威产物已经变化。重新运行 `$zstt-requirement-checklist` 或 `$zstt-artifact-analysis`。

### Quick 改动过程中发现影响面扩大

重新执行 `$zstt-requirement-clarification`，由用户确认升级为 Full，不要用 Quick 绕过调研、方案或 SQL Gate。

### 如何升级项目工作流

```powershell
uv tool install zstt-cli --force --from "git+https://github.com/Foutlook/zstt-backend-workflow.git"
cd C:\projects\learning-service
zstt check --here
zstt update --here
zstt doctor --here
```

若受管文件存在人工修改，升级会在写入前报告冲突并停止。只有明确接受覆盖时才使用 `zstt update --here --force`。

## 下一步

- 完整能力、13 个 Skill、产物契约和命令参考：[README.md](README.md)
- 高级能力来源、融合位置和边界：[高级能力融合矩阵](docs/advanced-capability-matrix.md)
- 版本变化：[CHANGELOG.md](CHANGELOG.md)
