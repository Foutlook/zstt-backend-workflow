---
name: zztt-module-refactor
description: ZZTT 行为保持型模块重构 Skill。仅当用户明确指定 $zztt-module-refactor，或明确要求按 ZZTT 安全重构模块、拆分 Service、调整职责或架构边界、处理模块内已有性能/并发/锁/线程安全/内存/GC/资源泄漏/可靠性问题时使用；先锁定真实调用链和行为基线，重大重构或任何可能改变业务行为的方案必须等待用户审批。
---

# ZZTT Module Refactor

## 定位

对用户指定模块做有证据、可审阅、可验证的行为保持型重构。它适合多文件职责拆分、模块化、解耦、DDD 边界调整，以及有证据的性能、并发和资源生命周期治理。

它不同于 `$zztt-code-simplification`：代码简化处理局部 cleanup；模块重构处理需要行为基线、计划审批和分步验证的结构性改造。

本 Skill 可在任何时刻显式调用，不属于固定流程，不推进或回退阶段，不修改 `.zztt/meta.json`。不得自动执行 Review、测试或其他 Skill。

## 开始前

1. 读取 `../zztt-workflow-shared/references/capability-fallback.md`、`evidence-rules.md` 和 `document-authority-and-corrections.md`。
2. 完整读取 `references/advanced-playbook.md`；Java 项目再读取 `../zztt-java-backend-standard/SKILL.md` 及其要求的参考文件。
3. 检查项目 `AGENTS.md`、Git 状态和用户已有改动，冻结目标模块、只读参考范围和明确不改范围。
4. 从 `assets/refactor-record-template.md` 创建唯一重构记录并替换全部占位符：
   - 独立重构：`.zztt/refactors/YYYYMMDD-<module-name>.md`；
   - 用户明确关联某个 ZZTT 需求：`<feature-dir>/auxiliary/refactors/YYYYMMDD-<module-name>.md`。
5. 始终更新同一记录，不创建 `final-v2`、`新版` 或第二份当前结论。

## 证据链

计划前必须确认：

- 用户指定的模块边界和真实入口；
- 入口到最终查询、计算、持久化和外部副作用的真实调用链；
- 真正影响结果的参数、数据源和状态所有者；
- Guard 条件与真实业务依赖的区别；
- DB、RPC、MQ、缓存、锁、定时器、WebSocket、after-commit 等运行通道；
- 当前接口、校验、权限、异常、事务、调用顺序和兼容行为；
- 现有测试与缺失的 characterization test（特征测试）。

不能只因字段出现在判空或 guard 中就认定它是核心依赖；必须追到最终 fetch/calculation 点。

## 选择审阅路径

### Fast path

仅用于范围窄、局部、行为保持且验证直接的小改造。仍要先在重构记录写简短计划、行为不变依据和验证命令；项目没有额外审批要求时可以继续执行。

### Plan review path

多文件移动、职责拆分、新抽象、DDD 边界、并发/锁、内存生命周期、性能优化或测试策略变化，必须先把计划写入重构记录，设置 `status: awaiting_approval`，等待用户明确批准后再改代码。

### Behavior-change path

任何可能改变数据结果、接口、权限、校验、异常、事务、持久化、外部调用、重试、超时、锁范围或通知时机的内容，都必须单独写“业务逻辑变更提案”，设置 `behavior_change: proposed` 并等待明确批准。用户说“直接改”也不能绕过此门禁。

无法确定是否影响行为时，选择 Behavior-change path。

## 实施

获得所需批准后：

1. 先补足行为保护测试或记录可复现基线信号。
2. 按计划做小而闭合的修改，每一步只解决一个已证明问题。
3. 优先明确职责、依赖和数据流；只有代码已出现真实模式压力时才使用设计模式或 DDD 构件。
4. 保持批量边界，禁止引入 N+1、循环数据库查询或循环远程调用。
5. 保留无关注释和用户已有改动；非平凡新边界解释“为什么”。
6. 发现计划外行为变化、数据源变化或跨模块扩张时停止，更新记录并重新请求审批。

只有用户明确要求或批准并行、写集可证明独立时，才可使用 Codex 子任务；主上下文必须建立文件锁、复核全部 diff，并统一验证。

## 验证与完成

- 修改前后使用同一组命令和判定口径；验证接口、数据结果、查询/远程调用参数、持久化副作用、权限校验、错误语义和运行通道边界。
- 并发场景核对锁范围、所有权、可见性、中断、重试窗口和清理；资源场景核对关闭、释放、容量边界和生命周期。
- 检查最终 diff、暂存区和未跟踪业务文件，确认没有范围扩张、注释丢失或用户改动覆盖。
- 将实际修改、计划偏差、命令、退出码、关键结果和剩余风险更新到同一重构记录；全部完成后设置 `status: completed`。
- 无法运行验证时写清未证明边界，不得宣称行为已保持。

## 输出

说明重构记录路径、审阅路径、当前是否等待审批、实际修改、行为保持依据、验证结果和剩余风险。关联固定流程时可以推荐用户重新执行 `$zztt-code-review` 或 `$zztt-test-verify`，但不得自动调用，也不得自动 commit、push、合并或部署。
