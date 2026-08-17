# 排查环境配置

仅在排查需要本地命令使用 Observability、DMS MCP 或 ES 凭据时读取。项目已注册的 MCP 或连接器自行安全管理凭据时，不读取本地环境文件。

先按 `references/runtime-bootstrap.md` 解析 `{PYTHON}` 和 `{ZSTT_KIT}`。本文件中的占位符必须替换为解析出的绝对路径；不得退回当前目录下的固定相对路径。

## 环境文件

- 测试环境：`{ZSTT_KIT}/.env/.env.local`，文件内必须声明 `ZSTT_ENV=test`；后端 Observability、客户端 Observability 和测试 DMS MCP AK 使用不同字段保存在这个文件中。
- 生产环境：`{ZSTT_KIT}/.env/.env.prod.local`，文件内必须声明 `ZSTT_ENV=prod`；后端 Observability、客户端 Observability、生产 DMS MCP AK 和 ES 使用彼此隔离的字段保存在这个文件中。
- 字段模板：`.env.example` 和 `.env.prod.example`；复制模板后只在本机填写，禁止提交真实值。
- ZSTT 安装和更新只管理模板及 `.gitignore`，不创建、读取、覆盖或记录任何 `*.local` 文件。

生产配置缺失、声明不匹配或权限不足时立即停止，不得回退到测试配置。用户没有明确环境时必须先确认，不得仅凭域名、类名或历史经验选择。

## 隔离执行

使用以下入口启动需要凭据的本地只读工具：

```text
{PYTHON} "{ZSTT_KIT}/runtime/with_env.py" <test|prod> <observability|observability-client|dms|es> -- <command> [args...]
```

- `observability`：使用后端 `ALIBABA_CLOUD_*`，只注入标准 Observability 变量。
- `observability-client`：读取当前环境文件中的 `ZSTT_CLIENT_ALIBABA_CLOUD_*`，向子进程临时映射为标准 `ALIBABA_CLOUD_*`；不会注入后端 AK，也不会跨测试/生产文件回退。
- `dms`：读取目标环境文件中的 `ZSTT_DMS_ALIBABA_CLOUD_ACCESS_KEY_ID`、`ZSTT_DMS_ALIBABA_CLOUD_ACCESS_KEY_SECRET` 和可选的 `ZSTT_DMS_ALIBABA_CLOUD_SECURITY_TOKEN`，向 DMS MCP 子进程映射为 `ALIBABA_CLOUD_ACCESS_KEY_ID`、`ALIBABA_CLOUD_ACCESS_KEY_SECRET` 和 `ALIBABA_CLOUD_SECURITY_TOKEN`；`test dms` 与 `prod dms` 分别读取测试和生产文件，不会注入 Observability AK，也不会跨环境回退。
- `es`：只注入 `ZSTT_ES_*`。

入口会先清除当前进程继承的全部受管变量，再只注入目标 Scope。不同 Scope 的凭据不得交叉注入。DMS 身份必须只授予目标数据库查询权限，ES 账号必须只读；Skill 仍禁止数据写入、索引修改、删除、缓存清理和消息重放。

DMS MCP Server 要求的标准变量名是 `ALIBABA_CLOUD_*`，但本地文件不得直接复用 Observability 的同名字段作为数据库凭据；统一由 `dms` Scope 在子进程内完成映射。当前会话未注册 DMS MCP 时，由 `runtime/dms_mcp_client.py` 通过已安装的 `uvx` 启动固定版本 Server 并管理单次查询会话；ZSTT 不保存数据库登录凭据或连接地址，也不自动执行系统级安装。

## 项目、数据库与日志映射

项目与 DMS 中的 MySQL 库名映射保存在 `{ZSTT_KIT}/project-databases.json`。该文件由 ZSTT 首次初始化或更新时创建为空 JSON 对象，属于用户配置，不进入安装清单，后续 `zstt update` 不覆盖。

文件使用“项目相对路径 → 库名或分环境库名”的格式：

```json
{
  "$productionSameAsTest": true,
  "$testBackendSls": {
    "region": "cn-hangzhou",
    "project": "example-test-k8s-log",
    "logstore": "test-app-log"
  },
  "$testClientSls": {
    "region": "cn-hangzhou",
    "project": "example-client-log",
    "logstore": "client-app-log"
  },
  "$prodBackendSls": {
    "region": "cn-hangzhou",
    "project": "example-prod-k8s-log",
    "logstore": "prod-app-log"
  },
  "$prodClientSls": {
    "region": "cn-hangzhou",
    "project": "example-client-log",
    "logstore": "client-app-release"
  },
  "service-a": "service_a_test",
  "group/service-b": "service_b_test",
  "service-c": {
    "test": "service_c_test",
    "prod": {
      "schema": "service_c_prod",
      "instanceAlias": "service-c-prod-instance"
    }
  }
}
```

使用规则：

1. 使用启动指南已经选定的 `{ZSTT_KIT}/project-databases.json`。项目级或共享 Kit 位于业务目录祖先时，以 Kit 所在安装根目录为基准计算当前项目相对路径；全局 Kit 不在业务目录祖先时，根据用户明确项目名匹配配置键，缺少唯一匹配时询问用户。以 `$` 开头的键是配置项，不参与项目路径匹配。
2. 仅当当前相对路径等于配置项，或以“配置项 + `/`”开头时才算匹配；再选择最长配置项。例如当前路径是 `group/service-b/module-a` 时，优先匹配 `group/service-b`，不得误用较短的 `group`，也不得让 `service-a` 误匹配 `service-ab`。
3. 映射值是字符串时默认表示测试库名；映射值也可以是包含 `test`、`prod` 的对象。每个环境值可以直接写 schema 字符串，也可以写 `{"schema": "...", "instanceAlias": "..."}`；`instanceAlias` 可省略，存在时必须作为 `dms_mcp_client.py --instance-alias` 传入。找不到目标环境的唯一映射时询问用户，不猜测；用户确认后可以建议补入该文件，但未经用户要求不得修改。
4. 映射结果与项目运行配置、日志或用户说明冲突时停止并确认，以最新明确证据为准。
5. 取得目标环境 schema 和可选 `instanceAlias` 后，必须通过 DMS MCP `searchDatabase` 解析，并通过 `getInstance` 校验环境：测试只保留 `EnvType=test`，生产只保留 `EnvType=product`。配置了实例别名时再做大小写不敏感的精确别名匹配；同名的其他环境实例不参与选择，目标环境仍不唯一时继续确认。
6. 字符串映射只有在 `"$productionSameAsTest": true` 时才可同时作为生产库名；否则生产环境必须使用对象中的 `prod` 值或由用户确认。该标记只确认库名相同，不允许复用测试凭据，生产查询仍必须通过 `prod dms`。
7. 该文件不保存 DMS 实例 ID、AccessKey、Security Token、主机、端口、URL、账号、密码或其他凭据。
8. `$testBackendSls` 只保存测试环境后端应用日志的 `region`、`project` 和 `logstore`。三项完整时直接用于 `sls_execute_sql`，不重复调用 `sls_list_projects` 或 `sls_list_logstores`。
9. `$testBackendSls` 不代表 Trace、Istio、Kubernetes 事件或生产日志。配置缺失、查询提示目标不存在或权限不覆盖时，才做一次收敛式发现；不得静默改用其他 Logstore。
10. `$testClientSls` 只保存测试客户端应用日志映射。查询时必须使用 `test observability-client` Scope，不得使用后端 `observability` AK；它同样不代表 Trace、Istio、Kubernetes 事件或生产日志。
11. `$prodBackendSls`、`$prodClientSls` 只保存生产后端、客户端应用日志映射。只有用户明确指定生产环境时，才分别使用 `prod observability`、`prod observability-client` Scope 做只读日志查询；不得回退到测试 AK。这些日志映射不授权 DMS 或 ES，生产数据库查询必须单独满足 `prod dms` 的映射、凭据和实例环境校验。

其他索引名、地域、Workspace、Project 和 Logstore 仍从当前项目运行配置、用户说明或收敛式元数据发现中确认，不能套用其他项目的历史映射。
