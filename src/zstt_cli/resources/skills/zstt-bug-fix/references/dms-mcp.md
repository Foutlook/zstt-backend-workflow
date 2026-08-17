# DMS MCP 只读数据库取证

仅在需要查询测试环境或用户明确指定的生产环境中、已托管到 Alibaba Cloud DMS 的 MySQL 等业务数据库时读取。ZSTT 使用 DMS MCP 多实例模式，不再通过主机、端口、数据库用户名和密码直连 MySQL。

## 能力与前提

- 优先探测当前会话是否已注册 Alibaba Cloud DMS MCP 或等价的只读 DMS 工具；不要假设 MCP 工具名称前缀固定。
- 当前会话未注册时，使用已解析 Kit 中的 `runtime/dms_mcp_client.py`。该客户端通过 `uvx` 启动固定版本的官方 `alibabacloud-dms-mcp-server`，在一个 MCP 会话内完成数据库发现、环境校验、元数据或查询调用；不要求把 MCP 预先注册到当前会话。
- 数据库实例必须已注册到 DMS 并启用安全托管，当前身份还必须具有目标数据库的只读查询权限。ZSTT 不自动注册数据库实例。
- 本地客户端只能通过 `runtime/with_env.py <test|prod> dms` 启动。`dms` Scope 从目标环境文件的 `ZSTT_DMS_ALIBABA_CLOUD_*` 读取独立凭据，并在 MCP 子进程内映射成 `ALIBABA_CLOUD_ACCESS_KEY_ID`、`ALIBABA_CLOUD_ACCESS_KEY_SECRET` 和可选的 `ALIBABA_CLOUD_SECURITY_TOKEN`；禁止复用 Observability AK 或跨环境回退。
- 机器必须已有 `uvx`。缺失时报告启动能力缺口和安装要求，不自动执行系统级安装。

## 运行时客户端

以下命令中的 `{PYTHON}` 和 `{ZSTT_KIT}` 必须使用 `runtime-bootstrap.md` 已解析出的同一组值：

```text
{PYTHON} "{ZSTT_KIT}/runtime/with_env.py" <test|prod> dms -- {PYTHON} "{ZSTT_KIT}/runtime/dms_mcp_client.py" resolve --schema <schemaName> [--instance-alias <alias>]
{PYTHON} "{ZSTT_KIT}/runtime/with_env.py" <test|prod> dms -- {PYTHON} "{ZSTT_KIT}/runtime/dms_mcp_client.py" tables --schema <schemaName> --search <tableName> [--instance-alias <alias>]
{PYTHON} "{ZSTT_KIT}/runtime/with_env.py" <test|prod> dms -- {PYTHON} "{ZSTT_KIT}/runtime/dms_mcp_client.py" table --schema <schemaName> --table <tableName> [--instance-alias <alias>]
{PYTHON} "{ZSTT_KIT}/runtime/with_env.py" <test|prod> dms -- {PYTHON} "{ZSTT_KIT}/runtime/dms_mcp_client.py" query --schema <schemaName> --sql <readOnlySql> [--instance-alias <alias>]
```

`query` 只接受单条 `SELECT`、`SHOW`、`DESC`、`DESCRIBE`、`EXPLAIN` 或只读 CTE，并拒绝 DDL、DML、锁定读、文件输出和高风险函数。客户端输出会隐藏连接地址和凭据；不得通过修改脚本参数绕过只读校验。

## 查询顺序

1. 先按 `project-databases.json` 的最长唯一项目映射和目标环境取得 `schemaName` 与可选 `instanceAlias`；配置包含实例别名时直接传给 `--instance-alias`，映射缺失或冲突时询问用户，不猜测。
2. 多实例模式先调用 `searchDatabase` 按 `schemaName` 查找数据库，再对每个候选调用 `getInstance` 检查 `EnvType`。测试环境只保留 `test`，生产环境只保留 `product`；其他环境实例直接忽略。配置了实例别名时再做精确别名匹配。目标实例唯一且项目证据一致时继续；仍有多个同环境实例时向用户展示脱敏后的实例别名并确认，再用 `--instance-alias` 精确选择。
3. 需要表结构时使用 `tables`、`table`，只读取解决当前问题所需的表和字段。
4. 使用 `query` 间接调用 `executeScript` 执行收敛的只读 SQL；按业务主键或有限时间范围查询，稳定排序并限制返回数量。
5. 同时检查 MCP 外层错误和工具返回载荷。工具调用成功但 DMS 返回失败、审批要求或权限错误，仍视为查询失败。

不得调用 `addInstance`、`createDataChangeOrder`、`submitOrderApproval`、`approveOrder` 或执行 DDL/DML。官方 DMS MCP 的 `executeScript` 本身支持写 SQL，因此 ZSTT 运行时客户端的只读校验和 Skill 边界都必须保留。

## 环境边界

- 测试环境：用户确认目标后，使用 `test dms`；数据库候选必须满足 `EnvType=test`。
- 生产环境：只有用户明确指定生产环境和查询目标后才使用 `prod dms`；数据库候选必须满足 `EnvType=product`。只允许收敛、限量、脱敏的只读查询。
- 两套环境分别读取 `.env.local` 和 `.env.prod.local` 中的 DMS 凭据；任一环境缺失、声明不匹配或权限不足时停止，不得回退到另一环境。
- `project-databases.json` 只保存项目到库名的映射，不保存 DMS 实例 ID、AK、Token 或数据库登录凭据。

## 标准降级

已注册 DMS MCP 和运行时客户端都不可用、目标库不唯一、实例未托管或权限不足时：

1. 记录能力缺口和原始错误类别，不把“查不到”写成“数据不存在”；
2. 输出目标库、只读 SQL、筛选条件、返回字段和行数限制；
3. 由用户或有权限的平台执行并回传脱敏结果；
4. 不读取旧的 `ZSTT_MYSQL_*`，不回退到 MySQL 主机、用户名和密码直连。

任何 MCP 参数、命令输出、聊天回复和报告都不得包含完整 AccessKey、Secret、Security Token、数据库账号、密码或连接地址。
