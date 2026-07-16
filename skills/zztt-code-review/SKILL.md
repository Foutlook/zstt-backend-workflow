---
name: zztt-code-review
description: ZZTT Java 后端代码评审阶段。仅当用户明确指定 $zztt-code-review，或明确要求执行“ZZTT 代码评审阶段”时使用；默认只读核对需求、方案、任务、实现、Git diff 和代码事实，生成评审产物，不自动修复代码。
---

# ZZTT Code Review

## 定位

这是实现后的独立证据化评审。默认只读，不直接修改代码；用户要求修复时，也先完成评审产物，再推荐重新调用实现阶段。

仅当用户明确指定本 Skill 时执行。Review 通过后可以推荐 `$zztt-test-verify`，但不得自动执行推荐的下一阶段。

## 开始前

1. 读取 `../zztt-workflow-shared/references/workflow-protocol.md`、`evidence-rules.md`、`capability-fallback.md` 和 `document-authority-and-corrections.md`。
2. 读取 `../zztt-java-backend-standard/SKILL.md` 及相关参考。
3. 完整读取本阶段 `references/advanced-playbook.md`。
4. 运行 `prepare-stage --stage code_review`，重新校验上游。
5. 读取当前 Git diff、完整被改文件、相关调用方、测试和实现记录。不要只看局部 diff。

## 评审顺序

1. 固定评审范围：基线、工作区状态、diff、修改文件和未跟踪业务文件。
2. 建立需求、方案、任务与实现一致性矩阵，检查遗漏和越界修改。
3. 反向追踪真实入口、调用链、最终数据源、最终赋值/计算点和关键参数。
4. 区分 Guard 条件与真实业务依赖，检查数据源范围是否闭环。
5. 检查接口、DTO/Jackson、SQL、事务、状态、权限、异常、兼容、并发和安全。
6. 检查 N+1、循环远程调用、批量性能、无效抽象和过度设计。
7. 检查注释保留、关键原因注释、日志/Trace 和验证证据是否真实。
8. 执行幻觉审计；范围足够大且工具可用时可进行只读专项并行审查，但所有候选问题必须由主上下文复核。

## 问题输出

问题按 P0/P1/P2/P3 排序：

- P0：会造成严重数据、安全、不可逆发布或核心链路故障；
- P1：明确的功能错误、需求偏差或高概率回归；
- P2：边界、性能、可维护性或测试缺口；
- P3：低风险但值得修正的问题。

每条问题必须包含代码位置、失败条件、影响、证据链和最小修复方向。没有可操作问题时明确写“未发现阻塞性问题”，不要为了显得严格而制造建议。

## 主产物

full 写 `05-code-review.md`，quick 写 `02-code-review.md`。报告包含评审输入、一致性矩阵、真实执行链、幻觉审计、问题清单、Java 质量检查、验证复核和结论；详细 Review 轮次可写入 `auxiliary/review-rounds/`，主产物保持当前权威结论。

## 完成

1. 有 P0 时将 `blocking_p0_count` 设为真实数量；P1/P2/P3 在正文完整列出。
2. 只有不存在 P0 且评审结论可交付时才设置 `status: completed`。
3. 运行 `complete-stage --stage code_review`。
4. 有问题时推荐 `$zztt-implementation`；通过时推荐 `$zztt-test-verify`。

## 禁止事项

- 不自动修复代码，不自动执行推荐步骤。
- 不把风格偏好当作功能缺陷。
- 不只凭测试为绿就判断实现正确。
