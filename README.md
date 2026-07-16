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

完整安装与使用说明将在实现收口阶段补齐。
