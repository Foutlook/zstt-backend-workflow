---
name: zztt-workflow-shared
description: ZZTT 后端工作流的内部共享协议、模板与确定性校验底座。不要由用户直接调用；仅供 zztt-* 阶段 Skill 读取和执行。
---

# ZZTT Workflow Shared

这是内部共享底座，不是对外阶段 Skill。

阶段 Skill 必须先读取：

- `references/workflow-protocol.md`：显式调用、产物权责、状态和命令协议。
- `references/evidence-rules.md`：源码事实、推断和运行时证据等级。
- `references/capability-fallback.md`：当前阶段相关能力的探测、增强路径和标准降级。
- `references/document-authority-and-corrections.md`：权威主产物、辅助附件、用户纠正和上游回写。

确定性操作统一通过 `scripts/workflow_cli.py` 执行。不要由模型手写或猜测 `meta.json` 状态。

模板位于 `assets/templates/full/` 和 `assets/templates/quick/`。一个阶段只维护一份主产物模板。
