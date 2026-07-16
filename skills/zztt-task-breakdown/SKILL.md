---
name: zztt-task-breakdown
description: ZZTT 正式需求任务拆分阶段。仅当用户明确指定 $zztt-task-breakdown，或明确要求执行“ZZTT 任务拆分阶段”时使用；把已确认方案拆成可追溯、可执行、可验证的 03-tasks.md，不自动编码。
---

# ZZTT Task Breakdown

## 定位

把 `02-design.md` 变成可以逐项执行的开发计划。这里只拆 full 正式需求；quick 的简短执行计划由实现阶段写入实现记录。

仅当用户明确指定本 Skill 时执行。结束后可以推荐 `$zztt-implementation`，但不得自动执行推荐的下一阶段。

## 开始前

1. 读取 `../zztt-workflow-shared/references/workflow-protocol.md` 和 `document-authority-and-corrections.md`。
2. 完整读取本阶段 `references/advanced-playbook.md`。
3. 运行 `prepare-stage --stage task_breakdown`，重新校验需求、调研和方案。
4. 读取 `00-requirement.md`、`01-research.md`、`02-design.md` 和被主方案索引的辅助附件，建立覆盖矩阵。
5. 发现方案缺少代码落点、接口契约、数据设计或验证策略时，停止拆分并回到方案阶段修正。

## 拆分规则

每个任务必须包含：

- 唯一任务 ID 和清晰目标；
- 来源依据：需求条目、调研结论或设计决策；
- 预期文件、模块、接口、SQL 或配置范围；
- 前置依赖、后续依赖和执行顺序；
- 实现要点与明确不做事项；
- 完成标准；
- 精确验证命令和预期信号；
- 风险、阻塞状态和可否并行。

任务粒度应让实现者能在一个连续上下文中完成和验证，不按 Controller/Service/Mapper 机械切成无法独立闭环的小片段。

## 可追溯性

- `03-tasks.md` 的每个任务至少引用一个上游来源依据。
- 接口、SQL、状态、兼容、迁移和测试策略必须映射到具体任务。
- 没有任务承接的方案项是覆盖缺口；没有来源依据的任务是范围扩张。
- 不重新定义需求或技术方案。发现冲突时先修正上游权威产物。

## 并行判断

先判断 L0/L1/L2 并行等级。首版不自动启动 Codex 子任务；L2 只在用户明确要求或批准当前阶段可选并行时准备执行者分配，且必须保证 Java 文件、Mapper XML、配置、SQL 和接口契约写集不重叠。

## 完成

1. 写入 `03-tasks.md` 的覆盖矩阵、执行顺序、任务清单、文件范围、验证命令和交接信息。
2. 更新 frontmatter 为真实状态和问题数量。
3. 运行 `complete-stage --stage task_breakdown`。
4. 输出关键路径、任务数、产物路径和阻塞项，推荐 `$zztt-implementation`。

## 禁止事项

- 不单独创建 `plan.md`；`03-tasks.md` 就是可执行实施计划。
- 不生成空泛的“修改 Service”“补测试”任务。
- 不提前修改代码或生成实现记录。
