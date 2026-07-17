---
name: zztt-repo-research
description: ZZTT 仓库与代码调研阶段。仅当用户明确指定 $zztt-repo-research，或明确要求执行“ZZTT 仓库调研阶段”时使用；基于已完成的 00-requirement.md 追踪真实代码、数据源和跨仓库依赖，生成 01-research.md，不自动写技术方案。
---

# ZZTT Repository Research

## 定位

用源码证据回答“需要改哪些仓库、真实链路如何运行、哪些参数真正影响结果”。仅当用户明确指定本 Skill 时执行。

阶段结束后可以推荐 `$zztt-technical-design`，但不得自动执行推荐的下一阶段。

## 开始前

1. 读取 `../zztt-workflow-shared/references/workflow-protocol.md`、`evidence-rules.md`、`capability-fallback.md` 和 `document-authority-and-corrections.md`。
2. 完整读取本阶段 `references/advanced-playbook.md`，按可用工具选择增强或标准降级路径。
3. 读取 `meta.json` 与 `00-requirement.md`。
4. 运行 `prepare-stage --stage repo_research`，让 CLI 重新校验需求产物。
5. 如果 P0、文件缺失或结构校验失败，停止调研并报告上游修复点。

## 调研强度

1. 用户要求确定完整变更面、跨仓库依赖或完成仓库调研阶段时，执行完整调研：覆盖全部需求验证目标、仓库分类、主链、副作用、跨仓库契约和完整 Claim Ledger。
2. 用户只问单个接口、字段、异常或数据来源时，执行聚焦调研：仍需从直接行为点追到最终查询、计算或赋值，并核对关键参数、Guard/真实依赖和相关数据源范围。
3. 聚焦调研只记录影响当前问题或下游决策的重要结论；能力矩阵压缩为实际使用、失败和降级说明，不为每个搜索命中建立 Claim Ledger。
4. 聚焦过程中发现跨仓库契约、schema、核心状态、副作用或未闭合数据范围时，只扩展受影响维度并说明原因，不无边界扫描。
5. 聚焦结果不足以满足完整完成检查时，保持 `01-research.md` 为草稿，不运行完成命令；交付已证结论、未覆盖范围，并由用户决定是否继续完整调研。

## 调研顺序

1. 从需求目标形成代码验证清单，不从熟悉的模块随意扫仓库。
2. 找到直接失败点或目标行为点：Controller、Job、MQ、任务、RPC/HTTP 入口。
3. 追踪真实调用链：Service、Manager、Facade、Client、Repository、Mapper、SQL。
4. 找到最终数据源、计算、赋值或持久化点。
5. 记录真正影响结果的关键参数、状态、时间范围、权限、租户和上下文。
6. 明确区分 Guard 条件与真实业务依赖。字段只出现在非空检查中，不代表它参与结果计算。
7. 检查旧链路副作用、调用方和反向影响，给出可直接复用、需扩展、仅参考、禁止复用或必须新增的结论。
8. 按仓库列出 API/DTO、服务逻辑、SQL、配置、消息、任务、测试和发布依赖。

开始源码分析前先确认仓库边界、主项目和依赖仓库，并探测远程仓库、CodeGraph 与本地 checkout 能力。增强工具不可用时执行标准降级，记录索引新鲜度、pending 文件、未覆盖范围和证据置信度。

## 数据源一致性

列表、聚合、图表和映射补全场景必须核对：

- 响应字段最终赋值点；
- 最终实体集来自哪里；
- ownership、章节、状态等映射来自哪里；
- 两个来源是否有代码、schema、查询或契约证据证明范围一致。

发现来源分裂时优先收口为同一上游关系源，不用 fallback 或平行查询隐藏问题。

## 证据写法

每个重要结论标注证据等级：Proven、Framework inferred、Requirement claim、Runtime dependent 或 Unknown。

Proven 结论记录仓库、文件、行号或符号。重要判断进入 Claim Ledger，并记录反证、证据覆盖度和待验证动作。源码不能证明配置、运行 Bean、消息状态或远程服务时，记录运行时验证缺口，不把推断写成事实。

## 完成

1. 将调研写入 `01-research.md`，包含需改仓库清单、真实调用链、最终数据源、关键参数、结论账本和证据索引。
2. 重算完成检查和 P0/P1/P2；聚焦调研未覆盖完整变更面、仍有 P0 或完成检查未通过时保持 `status: draft`，交付已证结论、缺口和继续动作，不运行完成命令。
3. 仅当完整完成检查通过且 P0 清零后，才更新 frontmatter 为 `status: completed` 和真实问题数量。
4. 运行 `complete-stage --stage repo_research`；CLI 失败时停止推进，保留产物并报告失败原因，不手改 `meta.json`。
5. 仅在 CLI 成功后输出阶段完成结论、产物路径和未验证风险，并推荐 `$zztt-technical-design`；草稿或失败状态不推荐执行下游阶段。

## 禁止事项

- 不生成技术方案或任务清单。
- 不只凭类名、Guard 条件、字段透传或测试断言下结论。
- 不把全仓文本搜索结果当作完整调用链。
- 不在循环中设计单 ID 数据库或远程查询。
