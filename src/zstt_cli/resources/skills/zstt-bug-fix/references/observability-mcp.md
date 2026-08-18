# SLS 凭证直查与 Trace MCP 取证指南

仅在问题涉及日志、Trace、服务可用性、Pod/实例或明确时间窗口时读取。本指南只允许程序化只读查询。

## 固定能力顺序

1. 确认唯一的测试或生产环境，以及后端或客户端日志意图。
2. 从已解析 Kit 的 `project-databases.json` 读取对应 `$testBackendSls`、`$testClientSls`、`$prodBackendSls` 或 `$prodClientSls`。映射完整时默认通过 `runtime/with_env.py` 注入对应 Scope 凭据，并调用 `runtime/sls_client.py` 直查 SLS。
3. 不得先探测、搜索或枚举 Observability MCP。只有 SLS 日志证据还需要补充 Trace/Span 拓扑，才使用当前会话已经注册的 UModel Trace MCP；只有凭证直查被具体证明不可用时，才可使用已经注册且环境匹配的 SLS MCP 作为程序化降级。
4. 程序化只读路径均不可用时，输出精确查询条件并等待用户回传脱敏结果。

ZSTT 不打包 Observability MCP Server 或凭据。任何查询都不得修改告警、配置、数据或资源。

## SLS 凭证直查流程

1. 查询应用日志时先区分环境和端：测试后端使用 `$testBackendSls` 与 `test observability`，测试客户端使用 `$testClientSls` 与 `test observability-client`，生产后端使用 `$prodBackendSls` 与 `prod observability`，生产客户端使用 `$prodClientSls` 与 `prod observability-client`。
2. `region`、`project`、`logstore` 完整时直接执行以下结构的命令，不重复发现 Project 和 Logstore：

   ```text
   {PYTHON} "{ZSTT_KIT}/runtime/with_env.py" <test|prod> <observability|observability-client> -- {PYTHON} "{ZSTT_KIT}/runtime/sls_client.py" --region <region> --project <project> --logstore <logstore> --from-time <unix-seconds> --to-time <unix-seconds> --query <收敛查询> --line <1-100>
   ```

3. 查询必须包含 Trace ID、业务 ID、接口或服务/Pod 条件之一，使用分钟级必要时间窗口；运行时客户端强制时间范围不超过 7 天、单次返回不超过 100 条。
4. 有 Trace ID 时先用它精确查询入口、异常和上下游日志，记录真实服务、Pod、接口、时间、错误和处理结果。无 Trace ID 时按接口、业务 ID、Pod/服务名和分钟级时间范围查入口日志，再从结果提取 Trace ID。
5. 需要更多上下文时，优先根据同一 Trace ID、服务和相邻时间扩大收敛查询；不得无边界扫描或枚举其他环境、Project、Logstore。
6. 查询无结果时记录环境、Scope、Project、Logstore、时间范围、查询条件、索引字段和权限覆盖范围；零命中不能被解释为事件不存在。
7. 四个 SLS 映射仅指对应环境和端的应用日志，不用于 Trace、Istio 或 Kubernetes 事件；不得混用测试/生产、后端/客户端 AK，也不得因为名称相似静默切换 Logstore。

## Trace MCP 补充流程

- 推荐工具：`umodel_get_traces`、`umodel_search_traces`。已知 Workspace、实体集和 TraceSet 时直接调用 `umodel_get_traces`；缺少元数据时，每类元数据最多做一次收敛发现。
- 只有没有明确 Trace ID 时才调用 `umodel_search_traces`，并按服务实体、错误状态和分钟级时间范围收敛。
- UModel 的 `time_range` 只传单个合法表达式，例如 `last_1h`、`last_24h`、Unix 时间戳或单个日期时间；固定历史窗口仍以 SLS 的 `from-time`、`to-time` 为准。
- 同时检查 MCP 外层 `isError` 和响应载荷的 `error`；外层成功但载荷 `error=true` 仍是查询失败。
- 对每个关键 Span 记录服务、操作、开始/结束时间、状态、错误标签、上游和下游；不要把没有服务端 Span 自动解释为业务代码异常。
- `sls_execute_sql` 和 `sls_get_context_logs` 只允许在凭证直查被具体证明不可用、当前会话已经注册匹配环境的只读 Observability MCP 时降级使用。不得为了寻找这些工具而延迟凭证直查。

## 安全边界

- 不读取、打印、复制或写入 `.env` 中的凭据值；只允许 `runtime/with_env.py` 把目标 Scope 注入子进程。
- 不把完整 Token、Cookie、Authorization、AccessKey、Secret、账号或密码传给 MCP、写进报告或发到聊天。
- 日志中出现凭据时，在摘录前只保留凭据类型和“已脱敏”标记。
- 不调用告警修改、配置修改、数据写入、删除、回放或补偿能力。
- 不遍历所有地域、Workspace、Project 或 Logstore；发现范围超过一个合理候选时，向用户确认目标环境。

## 程序化路径不可用时

凭证直查失败且不存在已注册、环境匹配的只读 MCP 时，输出以下最小查询包，等待用户回传脱敏结果：

- SLS：环境、后端/客户端 Scope、地域、Project、Logstore、查询语句、时间范围、line、需要回传的字段。
- Trace：Trace ID、入口服务、时间范围、需要的 Span 字段。
- Kubernetes：Namespace、Pod/Service/EndpointSlice 的只读状态和目标时间段日志。

不得因为程序化能力缺失而跳过代码调用链、运行时缺口和证据等级记录。
