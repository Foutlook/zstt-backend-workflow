---
name: zztt-requirement-clarification
description: ZZTT 需求澄清阶段。仅当用户明确指定 $zztt-requirement-clarification，或明确要求执行“ZZTT 需求澄清阶段”时使用；把 PRD、截图、流程图、表格或口头描述澄清为 full/quick 的 00-requirement.md，不自动进入代码调研。
---

# ZZTT Requirement Clarification

## 定位

完成需求澄清，而不是简单登记或摘要。输出是后续代码调研的唯一需求事实源。

仅当用户明确指定本 Skill 时执行。阶段结束后可以推荐 `$zztt-repo-research`，但不得自动执行推荐的下一阶段。

## 开始前

1. 以 UTF-8 读取项目 `AGENTS.md` 和用户提供的全部材料。
2. 完整读取 `../zztt-workflow-shared/references/workflow-protocol.md`。
3. 确认业务仓库根目录、需求名和 quick/full 模式。用户未指定模式时只问这一项，不替用户选择。
4. 使用共享 CLI 初始化目录；已有目录时读取 `meta.json` 和现有 `00-requirement.md`，继续回写而不覆盖。

## 澄清范围

至少确认：

- 业务目标、包含范围和明确不做事项；
- 用户路径、角色、权限和可见范围；
- 数据来源、核心对象的数据身份、去重维度和隔离维度；
- 状态流转、重复操作、并发、空数据和历史数据；
- 旧链路复用边界、必须保留或禁止触发的副作用；
- 主路径、边界、异常和权限相关验收标准。

## 事实与问题管理

- 显式区分 `原始事实`、`整理归纳`、`推断`、`冲突` 和 `未确认`。
- 不把缺失规则写成已确认事实。
- 按 P0/P1/P2 分级：P0 阻塞编码口径、接口、数据模型、权限或验收；P1 影响重要分支；P2 为非阻塞细节。
- P0 默认一次只问一个。低耦合的 P1/P2 最多合并 2–3 个问题。
- 每次用户回答后立即回写相关章节和确认记录，不只追加聊天记录。
- 用户无法确认的 P0 保持阻塞，不允许模型自行拍板。

## Quick 与 Full

quick 仍需明确目标、修改范围、不做事项、关键风险和验收信号，但不机械展开完整正式需求文档。

full 使用完整 `00-requirement.md`，把用户路径、数据身份、状态、权限、历史兼容和验收口径闭环。

## 完成

1. 更新 frontmatter：`status: completed` 和真实的 P0/P1/P2 数量。
2. 运行 `complete-stage --stage requirement_clarification`。
3. CLI 失败时继续澄清或修正文档，不手改 `meta.json`。
4. 交付 `00-requirement.md` 路径、澄清结论、开放风险，并推荐 `$zztt-repo-research`。

## 禁止事项

- 不在本阶段分析具体代码改动落点。
- 不生成 `01-research.md` 或技术方案。
- 不因用户提供了 PRD 就跳过澄清。
- 不静默脑补角色、状态、权限、数据模型或验收规则。
