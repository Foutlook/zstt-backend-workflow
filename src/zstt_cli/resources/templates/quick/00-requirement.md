---
workflow: zstt-backend-workflow
mode: quick
stage: requirement_clarification
status: draft
blocking_p0_count: 0
open_p1_count: 0
open_p2_count: 0
confirmation_status: pending
confirmation_source: ""
---

# Quick 需求澄清：{{FEATURE_NAME}}

## 1. 输入与目标

- 创建日期：{{CREATED_DATE}}
- 目标：
- 当前问题：
- 输入限制/冲突（仅存在时）：
- 降级影响（仅存在时）：

### 规则加载记录

- rulesetVersion：
- rulesetFingerprint：

| 规则 ID | 类型 | 选择原因 | SHA-256 |
|---|---|---|---|

### 原始材料要点覆盖

| 来源 ID | 原始要点 | 处理结果 | 对应 Rxx/Qxx | 处理说明 |
|---|---|---|---|---|

## 2. 最小修改契约

> Quick 只保存会改变实现或验收的契约。表内只放已确认结论；未确认的权限、风险或升级判断进入 Qxx，确认后再回写 Rxx。无关风险维度直接省略，不为填写“不适用”展开 Full 文档。

| 需求 ID | 已确认边界/规则 | 来源 Sxx/Qxx | 允许修改 | 明确不做 | 风险/升级 Full 条件 | 状态 |
|---|---|---|---|---|---|---|

## 3. 验收信号

| 需求 ID | 前置/输入 | 操作/触发 | 用户可见结果 | 最小验证信号 |
|---|---|---|---|---|

## 4. 未决问题与阻塞项

| 问题 ID | 优先级 | 问题类型 | 疑问 | 准确来源 Sxx | 影响 Rxx/章节 | 确认人/承接阶段 | 确认结论/转交说明 | 状态 |
|---|---|---|---|---|---|---|---|---|

## 5. 确认与实现交接

- 最终边界确认：
- 确认来源：
- 有效需求 ID：
- 仍开放的 P1/P2 风险：
- 实现只需读取的契约：

> 模式评估取值：保持 Quick / 建议升级 Full。用户模式决定取值：保持 Quick / 升级 Full。

- 模式评估：
- 用户模式决定：
- 模式决定来源：
