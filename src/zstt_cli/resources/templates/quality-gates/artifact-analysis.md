---
quality_gate_schema_version: 1
quality_gate: artifact_analysis
mode: full
status: draft
blocking_p0_count: 0
open_p1_count: 0
open_p2_count: 0
ruleset_version: ""
ruleset_fingerprint: ""
requirement_fingerprint: "{{REQUIREMENT_FINGERPRINT}}"
research_fingerprint: "{{RESEARCH_FINGERPRINT}}"
design_fingerprint: "{{DESIGN_FINGERPRINT}}"
tasks_fingerprint: "{{TASKS_FINGERPRINT}}"
---

# ZSTT 实现前一致性分析

- Feature：{{FEATURE_NAME}}
- Created：{{CREATED_DATE}}
- 权威输入：`00-requirement.md`、`01-research.md`、`02-design.md`、`03-tasks.md`

## 结论

- 状态：待分析
- 最早应返回阶段：
- 规则选择依据：

## 规则加载记录

- rulesetVersion：
- rulesetFingerprint：

| 规则 ID | 选择原因 |
|---|---|

## 问题

| ID | 级别 | 类型 | 位置 | 证据链 | 问题 | 建议回写位置 |
|---|---|---|---|---|---|---|
<!-- | COV-001 | P0 | 覆盖 | R03/D02/T04 | R03 -> C02 -> D02 -> T04 | 示例问题 | 03-tasks.md | -->

## 覆盖摘要

| 指标 | 结果 | 缺口 |
|---|---|---|
| Rxx 下游覆盖 |  |  |
| USxx 任务覆盖 |  |  |
| 核心 Dxx 任务覆盖 |  |  |
| 无来源 Txx |  |  |

## 未验证边界

- 运行时、环境或外部系统边界：

## 下一步

- 应修正的权威产物：
- 修正后重新执行 `$zstt-artifact-analysis`：
