# DMS MCP 只读数据取证

只在需求差异或变更范围确实依赖实际数据事实时使用。用户未指定环境时默认先验证 `prod`，生产验证失败再以相同目标验证 `test`。ZSTT 通过 Alibaba Cloud DMS MCP 多实例模式读取托管数据库，不使用主机、端口、数据库用户名和密码直连。

## 能力与边界

- 优先使用当前会话已注册的 Alibaba Cloud DMS MCP 或等价只读工具，但必须确认它能够执行本节的环境隔离、实例选择和只读限制。
- 当前会话没有合适 Provider 时，使用同一 `{ZSTT_KIT}` 的 `runtime/dms_mcp_client.py`。它通过 `uvx` 启动固定版本的官方 DMS MCP Server；缺少 `uvx` 时只报告能力缺口，不自动进行系统级安装。
- 本地客户端只能通过 `runtime/with_env.py <test|prod> dms` 启动。测试与生产分别读取 `.env.local`、`.env.prod.local` 中独立的 `ZSTT_DMS_ALIBABA_CLOUD_*`，不得复用其他 Scope；回退时必须关闭生产子进程，再以测试环境的独立配置启动新子进程。
- 数据库实例必须已托管到 DMS，当前身份必须具备目标库的只读查询权限。ZSTT 不自动注册实例、申请权限或发起审批。

## 命令

```text
{PYTHON} "{ZSTT_KIT}/runtime/with_env.py" <test|prod> dms -- {PYTHON} "{ZSTT_KIT}/runtime/dms_mcp_client.py" resolve --schema <schemaName> [--instance-alias <alias>]
{PYTHON} "{ZSTT_KIT}/runtime/with_env.py" <test|prod> dms -- {PYTHON} "{ZSTT_KIT}/runtime/dms_mcp_client.py" tables --schema <schemaName> --search <tableName> [--instance-alias <alias>]
{PYTHON} "{ZSTT_KIT}/runtime/with_env.py" <test|prod> dms -- {PYTHON} "{ZSTT_KIT}/runtime/dms_mcp_client.py" table --schema <schemaName> --table <tableName> [--instance-alias <alias>]
{PYTHON} "{ZSTT_KIT}/runtime/with_env.py" <test|prod> dms -- {PYTHON} "{ZSTT_KIT}/runtime/dms_mcp_client.py" query --schema <schemaName> --sql <readOnlySql> [--instance-alias <alias>]
```

`query` 只接受一条 `SELECT`、`SHOW`、`DESC`、`DESCRIBE`、`EXPLAIN` 或只读 CTE，并拒绝 DDL、DML、锁定读、文件输出和高风险函数。禁止修改客户端或参数绕过校验。

## 查询顺序

1. 先从适用版本源码、Mapper/Repository、SQL、Schema 和配置定位数据库、表、关联键、状态值、租户条件与时间字段；不从需求名猜表。
2. 按 `project-databases.json` 的最长唯一项目映射取得目标环境的 `schemaName` 和可选 `instanceAlias`。
3. 使用 `searchDatabase` 查找 Schema，再对候选调用 `getInstance`。`test` 只保留 `EnvType=test`，`prod` 只保留 `EnvType=product`；存在 `instanceAlias` 时做大小写不敏感的精确别名匹配。
4. 目标环境仍有多个实例时向用户展示脱敏后的别名并确认；不得选择第一个或复用另一环境实例。
5. 需要结构时使用 `tables`、`table`，只读取当前需求涉及的表和字段。
6. 把数据事实改写为最小查询目标，例如总量、空值率、去重覆盖数、状态分布、时间边界、关联缺失数或目标范围内是否存在记录。
7. 通过 `query` 间接调用官方 MCP 的 `executeScript`。按业务主键或有限时间范围查询，稳定排序并限制行数；优先聚合和脱敏统计。
8. 同时检查 MCP 外层状态和工具载荷。工具调用成功但 DMS 返回失败、审批要求或权限错误，仍视为失败。

不得调用 `addInstance`、`createDataChangeOrder`、`submitOrderApproval`、`approveOrder`，不得执行任何 DDL/DML、锁表、写存储过程、临时对象创建或会改变会话外状态的动作。

## 环境门禁

- 用户未指定环境：默认通过 `prod dms` 查询唯一 `EnvType=product` 实例；查询必须收敛、限量、脱敏。
- 默认生产验证因映射、凭据声明、实例校验、权限、网络、超时或工具能力失败，无法形成生产数据事实时，记录错误类别，并以完全相同的业务目标通过 `test dms` 查询唯一 `EnvType=test` 实例。
- 生产查询成功但返回零行、覆盖不足或“不支持”结论属于有效生产证据，不触发测试回退。
- 用户明确指定 `test` 或 `prod` 时只查询该环境，失败即停止，不跨环境回退。
- 测试回退结果只能证明测试环境，不能替代或推断生产环境。输出必须同时标明生产失败原因、测试证据范围和结论限制。

## 数据最小化与降级

默认只返回统计、结构或经过脱敏的必要字段。需要样本时限制最少行数，并隐藏姓名、手机号、证件、地址、内容正文、Token 等敏感信息。任何输出不得包含 AccessKey、Secret、Security Token、连接地址或完整敏感记录。

已注册 DMS MCP 和运行时客户端都不可用、目标库不唯一、实例未托管、权限不足、超时、表不存在或查询为空时：

1. 记录环境、目标 Schema、错误类别和证据限制；
2. 将结论标记为 `待补证`，不把“查不到”写成“不支持”或“不存在”；
3. 给出可由有权限平台执行的只读 SQL、筛选条件、字段和行数限制；
4. 不读取旧的 `ZSTT_MYSQL_*`，不改用直连，不要求用户在聊天中粘贴凭据。
