---
name: zztt-implementation
description: ZZTT Java 后端编码实现阶段。仅当用户明确指定 $zztt-implementation，或明确要求执行“ZZTT 编码实现阶段”时使用；按 full 任务或 quick 边界修改代码并生成实现记录，不自动进入 Review。
---

# ZZTT Implementation

## 定位

按照已确认的范围实施最小闭环改动，并留下可复现的实现与验证记录。仅当用户明确指定本 Skill 时修改代码。

结束后可以推荐 `$zztt-code-review`，但不得自动执行推荐的下一阶段。

## 开始前

1. 读取 `../zztt-workflow-shared/references/workflow-protocol.md`。
2. 完整读取 `../zztt-java-backend-standard/SKILL.md` 及其要求的参考章节。
3. 运行 `prepare-stage --stage implementation`，让 CLI 重新校验上游。
4. full 读取 `00`–`03` 主产物；quick 读取 `00-requirement.md`，并先在实现产物写简短执行计划。
5. 检查 Git 状态，保留用户已有改动，不使用破坏性命令回滚。

## 实现顺序

1. 从真实入口、调用链和最终数据源定位最小修改点。
2. 逐项执行任务或 quick 边界，先建立失败测试或可复现失败信号。
3. 写最小实现，运行局部验证，再继续下一项。
4. 同步记录实际文件、任务状态、命令和结果。
5. 发现实现需要偏离需求、调研、方案、接口或 SQL 时停止；先让用户确认并回写权威产物。

## Java 后端硬门禁

- 禁止 N+1 查询；批量场景先收集参数，再批量查询或批量调用并在内存映射。
- 禁止在循环中按单 ID 查询数据库、Mapper、Repository、RPC 或外部 API，避免循环远程调用。
- 禁止无关重构、无关格式化、整片风格清洗和推测性 fallback。
- 保留既有注释；只更新当前逻辑相关注释，非平凡业务边界、状态、顺序、数据源和异常兜底解释“为什么”。
- Jackson 高风险字段显式声明 `@JsonProperty`，需要历史兼容时才加 `@JsonAlias`，并补绑定测试。
- 聚合与映射从同一实体范围闭环派生，不用平行数据源隐藏范围不一致。
- 不吞异常，不在事务中无依据扩大远程调用和慢操作范围。

## 主产物

full 更新 `04-implementation.md`；quick 更新 `01-implementation.md`。至少记录：

- 实现前检查和执行计划；
- 实际修改文件和任务状态；
- 设计偏差及上游回写；
- 注释、Jackson、数据源、N+1、异常和兼容自检；
- 测试或验证命令、退出码和关键结果。

## 完成

1. 运行与风险相称的编译、单测或局部验证。Maven 项目若 smart-doc 绑定早期生命周期，业务验证命令传 `-Dsmart-doc.phase=verify`。
2. 更新 frontmatter 为真实状态与问题数量。
3. 运行 `complete-stage --stage implementation`。
4. 输出实际改动、验证结果和产物路径，推荐 `$zztt-code-review`。

## 禁止事项

- 不自动执行代码评审、Git commit、push、合并或部署。
- 不把未执行的测试写成已通过。
- 不因实现困难而扩展需求或增加未经证明的兼容逻辑。
