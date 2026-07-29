---
workflow: zstt-backend-workflow
mode: full
stage: implementation
status: draft
blocking_p0_count: 0
open_p1_count: 0
open_p2_count: 0
---

# 编码实现记录：{{FEATURE_NAME}}

## 1. 实现前检查

### 规则加载记录

- rulesetVersion：
- rulesetFingerprint：

| 规则 ID | 类型 | 选择原因 | SHA-256 |
|---|---|---|---|


### 范围冻结

| 任务 | 允许修改 | 只读参考 | 明确不改 | 用户已有改动 | 验证方式 |
|---|---|---|---|---|---|

### 工具与降级记录

| 能力 | 探测结果 | 实际/降级路径 | 未验证范围 |
|---|---|---|---|

## 2. 任务增量

> 这里只引用 `Txx/Dxx` 并记录本阶段新增事实，不复述需求、调研、方案和任务正文。

| 任务 Txx | 来源 Dxx | 实际文件/符号 | 相对计划的增量或偏差 | 状态 |
|---|---|---|---|---|

## 3. 自动派生实现证据

> 本节由 Runtime 根据准备实现时的 Git 基线、当前工作区和 `run-validation` 结果维护。文件归属仍需结合完整 diff 复核。

<!-- ZSTT_AUTO_IMPLEMENTATION_EVIDENCE_START -->
- 证据文件：`auxiliary/implementation-evidence.json`
- Git 基线：准备实现时自动采集
- 当前工作区：待完成阶段时自动采集
- 自动记录的验证：暂无
<!-- ZSTT_AUTO_IMPLEMENTATION_EVIDENCE_END -->

## 4. 上游偏差与回写

| 来源 Rxx/Cxx/Dxx/Txx | 新事实或偏差 | 应回写产物 | 处理状态 |
|---|---|---|---|

## 5. 人工质量结论

- 关键业务行为：
- Java 规则自检：
- 未验证边界与残余风险：

## 6. Review 交接

- 完成的 Txx：
- 需要重点 Review 的文件/符号：
- 需要重点复核的风险：
