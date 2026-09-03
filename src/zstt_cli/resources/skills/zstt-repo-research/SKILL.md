---
name: zstt-repo-research
description: ZSTT 仓库与代码调研阶段。仅当用户明确指定 $zstt-repo-research，或明确要求执行“ZSTT 仓库调研阶段”时使用；基于已完成的 00-requirement.md 追踪真实代码、数据源和跨仓库依赖，生成 01-research.md，不自动写技术方案。
---

# ZSTT Repository Research

## 定位

用源码证据回答“需要改哪些仓库、真实链路如何运行、哪些参数真正影响结果”。仅当用户明确指定本 Skill 时执行。

阶段结束后可以推荐 `$zstt-technical-design`，但不得自动执行推荐的下一阶段。

## 开始前

1. 运行 `python .zstt-kit/runtime/rule_resolver.py resolve --skill zstt-repo-research`。
2. 以 UTF-8 完整读取解析结果中每个规则的 `path`，记录 `rulesetVersion`、`rulesetFingerprint`、规则 ID 和选择原因。解析失败或规则缺失时停止，并执行 `zstt check --here`。
3. 完整读取本阶段 `references/advanced-playbook.md`，按可用工具选择增强或标准降级路径。
4. 读取 `meta.json` 与 `00-requirement.md`；根据真实入口、调用链和数据源追加 `call-chain`、`data-source`、`data-access` 等已证明上下文并重新解析。类名和关键词不能替代代码证据。
5. 用户显式给出的需求目录优先；未给目录时运行 `current --repo-root <业务仓库>`，仅接受当前 Git 分支上的唯一未完成需求。0 个或多个候选时运行 `list --repo-root <业务仓库>` 展示候选并要求用户选择，禁止按日期猜测。
6. 运行 `python .zstt-kit/runtime/workflow_cli.py prepare-stage --stage repo_research --feature-dir <需求目录>`，让 CLI 重新校验需求产物。
7. Full 如果 `checklists/requirements.md` 不存在，Runtime 视为用户跳过可选检查；如果存在，则校验其结构、问题计数和 `00-requirement.md` 输入指纹。报告为 P0 阻塞、已过期或无效时停止调研，要求先修正权威需求并重新执行 `$zstt-requirement-checklist`；只有 P1/P2 时记录风险后继续。
8. 如果上游 P0、文件缺失或结构校验失败，停止调研并报告上游修复点。

## 调研强度

1. 用户要求确定完整变更面、跨仓库依赖或完成仓库调研阶段时，执行完整调研：必须且只能覆盖 `00-requirement.md` 中全部 `Rxx`，并填写仓库分类、每仓 ChangeScope、主链、副作用、跨仓库契约、共享语义与当前 SQL 事实、完整 Claim Ledger。
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
8. 按仓库列出 API/DTO、服务逻辑、SQL、配置、消息、任务、测试和发布依赖，确保权威仓库分类与每仓 ChangeScope 一一对应。
9. 需求涉及共享状态、枚举、类型码、序列化值或历史魔法值时，从生产方沿持久化与传播路径反查所有消费者，覆盖 SQL/XML 条件、RPC/JSON、MQ、缓存、任务和历史数据兼容。
10. 识别当前 SELECT/INSERT/UPDATE/DELETE/DDL 的位置和语义，记录 JOIN、过滤、排序、分页、写入与并发条件；本阶段不设计未来 SQL，SQL 草案和用户确认继续由技术设计阶段负责。

## 仓库来源门禁

开始源码分析前先确定唯一的代码来源路径，严格按以下优先级执行：

1. 用户明确提供一个或多个仓库路径时，先验证路径存在、确实是目标 checkout，并只读取这些本地路径；本次调研禁止检查私有 MCP 配置、探测远程仓库能力或调用远程仓库 MCP。路径无效或仓库身份不符时停止并请用户修正，不能静默切换远程来源。
2. 用户没有提供仓库路径时，按环境使用 Kit 的私有仓库 MCP 配置：用户明确指定测试环境时读取 `.zstt-kit/.env/.env.local`，其他情况默认读取 `.zstt-kit/.env/.env.prod.local`。不要直接读取或回显 `ZSTT_REPO_MCP_URL`；通过 `runtime/with_env.py <test|prod> repo-mcp` 注入给子进程。
3. 先通过同一 Kit 的 `runtime/repo_mcp_client.py probe` 验证远程端点确实暴露只读 `codegraph_explore`，再通过其 `explore` 命令读取远程仓库。该客户端是仓库 MCP 的固定安全边界，不要求 MCP 预先注册到当前 Codex 会话，也不得用 Web、curl、PowerShell 或其他通用 HTTP 客户端绕过它。
4. 私有配置不存在、不完整、权限不足、仓库不可访问、工具不匹配或客户端调用失败时，进入 Playbook 的默认降级路径；不要临时把私有配置写入受 Git 管理文件，也不要伪造远程证据。

选定来源后再确认仓库边界、主项目和依赖仓库，并探测所选本地 checkout 的 CodeGraph 能力。增强工具不可用时执行标准降级，记录来源选择、索引新鲜度、pending 文件、未覆盖范围和证据置信度。

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

每个重要 `Cxx` 至少引用一个在证据索引中定义的 `Exx`；ID 必须唯一，证据等级只能使用上述五类。可解析的本地源码证据必须指向存在的文件和有效行号，远程或运行时证据必须说明定位方式和限制。

调研产生的问题使用 `RQxx`，并标注 `用户意图`、`代码事实`、`运行时证据` 或 `设计选择`、Owner、承接阶段、状态和解锁动作。需求阶段转交给仓库调研的 `Qxx` 必须在验证矩阵、结论或 `RQxx` 中显式承接。

## 产物裁剪

- 两种强度都只维护同一份 `01-research.md`，不为聚焦问题创建平行报告。
- 完整调研填写需改仓库清单、全部验证目标、主链、最终数据源、副作用、跨仓库契约、完整 Claim Ledger 和证据索引。
- `shared_semantic_impact` 和 `current_sql_impact` 在完成前必须从 `pending` 判定为 `none` 或 `involved`。判定为 `none` 也要有 `Cxx/Exx` 排除依据；判定为 `involved` 必须填写对应影响矩阵。
- 聚焦调研保留模板固定章节，但只填写当前问题相关内容；未覆盖章节明确写“本次未覆盖，不作为阶段完成依据”，不制造仓库分类或结论。
- 聚焦交付至少包含：问题结论、直接行为点到最终查询/计算/赋值的链路、关键参数、Guard/真实依赖、最小 Claim Ledger、反证或冲突、运行时缺口和继续动作。
- 能力说明只记录实际使用、失败及降级路径；同一事实在正文给结论、Ledger 给追溯字段、证据索引给位置，不重复铺陈。

## 完成

1. 按本次调研强度将结论写入 `01-research.md`，并保留可反查的 Claim 与 Evidence ID。
2. 重算完成检查和 P0/P1/P2；聚焦调研未覆盖完整变更面、仍有 P0 或完成检查未通过时保持 `status: draft`，交付已证结论、缺口和继续动作，不运行完成命令。
3. 仅当完整完成检查通过且 P0 清零后，才更新 frontmatter 为 `status: completed` 和真实问题数量。
4. 运行 `complete-stage --stage repo_research`；CLI 失败时停止推进，保留产物并报告失败原因，不手改 `meta.json`。
5. 仅在 CLI 成功后输出阶段完成结论、产物路径和未验证风险，并推荐 `$zstt-technical-design`；草稿或失败状态不推荐执行下游阶段。

## 禁止事项

- 不生成技术方案或任务清单。
- 不只凭类名、Guard 条件、字段透传或测试断言下结论。
- 不把全仓文本搜索结果当作完整调用链。
- 不在用户已指定仓库路径时读取私有 MCP 配置或访问远程仓库。
- 不直接读取、输出或复制 `ZSTT_REPO_MCP_URL`；只允许 `with_env.py` 将它注入 `repo_mcp_client.py`。
- 不把私有 MCP 配置、地址、服务名、鉴权信息写入 Skill、代码、受 Git 管理的示例或阶段产物。
- 发现循环内按单 ID 重复调用数据库、RPC 或外部接口时，记录为 N+1 风险和设计输入；本阶段不越界设计或实现批量方案。
