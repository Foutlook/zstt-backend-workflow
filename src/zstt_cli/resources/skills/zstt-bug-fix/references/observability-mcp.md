# Observability MCP 取证指南

仅在问题涉及日志、Trace、服务可用性、Pod/实例或明确时间窗口时读取。本指南只允许只读查询。

## 能力探测

- 优先探测项目是否已注册 Alibaba Cloud Observability MCP 或提供等价只读工具。
- 推荐工具：`umodel_get_traces`、`umodel_search_traces`、`sls_execute_sql`、`sls_get_context_logs`。
- 元数据发现：`list_workspace`、`umodel_search_entity_set`、`umodel_list_data_set`、`sls_list_projects`、`sls_list_logstores`。
- 不假设工具名称前缀固定；已注册时通常表现为 `mcp__observability__<tool>`。
- ZSTT 不打包 MCP Server 二进制或凭据。项目未注册工具时执行“标准降级”，不要临时下载不受信任的二进制。

## Trace 优先流程

1. 记录 Trace ID、入口服务、接口、环境和不超过必要范围的时间窗口。
2. 已知 Workspace、实体集和 TraceSet 时直接调用 `umodel_get_traces`。
3. 缺少元数据时依次调用一次：
   - `list_workspace(regionId="cn-hangzhou")`；
   - `umodel_search_entity_set(search_text="apm", ...)`；
   - `umodel_list_data_set(data_set_types="trace_set", ...)`。
4. 只有没有明确 Trace ID 时才调用 `umodel_search_traces`，并按服务实体、错误状态和分钟级时间范围收敛。
5. UModel 和 `cms_natural_language_query` 的 `time_range` 只传单个合法表达式，例如 `last_1h`、`last_24h`、Unix 时间戳或单个日期时间；不要传开始/结束拼接范围。固定历史窗口使用 SLS 的 `from_time`、`to_time`。
6. 同时检查 MCP 外层 `isError` 和响应载荷的 `error`；外层成功但载荷 `error=true` 仍是查询失败。
7. 对每个关键 Span 记录服务、操作、开始/结束时间、状态、错误标签、上游和下游；不要把没有服务端 Span 自动解释为业务代码异常。
8. 以失败 Span 的时间范围和服务名转查日志，建立请求到失败点的时间线。

## SLS 日志流程

1. 查询应用日志时，先确认环境并区分后端和客户端：测试后端读取 `$testBackendSls` 并使用 `test observability`，测试客户端读取 `$testClientSls` 并使用 `test observability-client`；生产后端读取 `$prodBackendSls` 并使用 `prod observability`，生产客户端读取 `$prodClientSls` 并使用 `prod observability-client`。`region`、`project`、`logstore` 完整时直接调用 `sls_execute_sql`。其他场景已知 Project 和 Logstore 时也直接查询；未知或已配置目标失效时，分别只调用一次 `sls_list_projects`、`sls_list_logstores` 做收敛发现。
2. 查询必须包含 Trace ID、业务 ID、接口或服务/Pod 条件之一，并限定开始、结束时间和 `limit`。
3. 需要上下文时，在首次查询中追加 `|with_pack_meta`，取得 `__pack_id__` 和 `__pack_meta__` 后调用 `sls_get_context_logs`。
4. `cms_natural_language_query` 只作为实体/数据源不明确时的辅助发现，不代替精确 Trace 或 SLS 查询。
5. 查询无结果时记录 Project、Logstore、时间范围、索引字段和权限覆盖范围；结论标为 `Runtime dependent` 或 `Unknown`。
6. 四个 SLS 映射仅指对应环境和端的应用日志，不用于 Trace、Istio 或 Kubernetes 事件；不得混用测试/生产、后端/客户端 AK，也不得因为名称相似静默切换 Logstore。

## 安全边界

- 不读取、打印、复制或写入 `.env` 中的凭据值。
- 不把完整 Token、Cookie、Authorization、AccessKey、Secret、账号或密码传给 MCP、写进报告或发到聊天。
- 日志中出现凭据时，在摘录前只保留凭据类型和“已脱敏”标记。
- 不调用告警修改、配置修改、数据写入、删除、回放或补偿能力。
- 不遍历所有地域、Workspace、Project 或 Logstore；发现范围超过一个合理候选时，向用户确认目标环境。

## 标准降级

MCP 不可用时输出以下最小查询包，等待用户回传脱敏结果：

- Trace：Trace ID、入口服务、时间范围、需要的 Span 字段。
- SLS：地域、Project、Logstore、查询语句、时间范围、limit、需要回传的字段。
- Kubernetes：Namespace、Pod/Service/EndpointSlice 的只读状态和目标时间段日志。

不得因为工具缺失而跳过代码调用链、运行时缺口和证据等级记录。
