# 排查环境配置

仅在排查需要本地命令使用 Observability、MySQL 或 ES 凭据时读取。项目已注册的 MCP 或连接器自行安全管理凭据时，不读取本地环境文件。

先按 `references/runtime-bootstrap.md` 解析 `{PYTHON}` 和 `{ZSTT_KIT}`。本文件中的占位符必须替换为解析出的绝对路径；不得退回当前目录下的固定相对路径。

## 环境文件

- 测试环境：`{ZSTT_KIT}/.env/.env.local`，文件内必须声明 `ZSTT_ENV=test`；后端与客户端 Observability AK 使用不同字段保存在这个文件中。
- 生产环境：`{ZSTT_KIT}/.env/.env.prod.local`，文件内必须声明 `ZSTT_ENV=prod`；后端与客户端 Observability AK 同样使用不同字段保存在这个文件中。
- 字段模板：`.env.example` 和 `.env.prod.example`；复制模板后只在本机填写，禁止提交真实值。
- ZSTT 安装和更新只管理模板及 `.gitignore`，不创建、读取、覆盖或记录任何 `*.local` 文件。

生产配置缺失、声明不匹配或权限不足时立即停止，不得回退到测试配置。用户没有明确环境时必须先确认，不得仅凭域名、类名或历史经验选择。

## 隔离执行

使用以下入口启动需要凭据的本地只读工具：

```text
{PYTHON} "{ZSTT_KIT}/runtime/with_env.py" <test|prod> <observability|observability-client|mysql|es> -- <command> [args...]
```

- `observability`：使用后端 `ALIBABA_CLOUD_*`，只注入标准 Observability 变量。
- `observability-client`：读取当前环境文件中的 `ZSTT_CLIENT_ALIBABA_CLOUD_*`，向子进程临时映射为标准 `ALIBABA_CLOUD_*`；不会注入后端 AK，也不会跨测试/生产文件回退。
- `mysql`：只注入 `ZSTT_MYSQL_*`。
- `es`：只注入 `ZSTT_ES_*`。

入口会先清除当前进程继承的全部受管变量，再只注入目标 Scope。不同 Scope 的凭据不得交叉注入。MySQL 和 ES 账号必须只读；Skill 仍禁止数据写入、索引修改、删除、缓存清理和消息重放。

## 项目与测试后端日志映射

项目与 MySQL 库名映射保存在 `{ZSTT_KIT}/project-databases.json`。该文件由 ZSTT 首次初始化或更新时创建为空 JSON 对象，属于用户配置，不进入安装清单，后续 `zstt update` 不覆盖。

文件使用“项目相对路径 → 测试库名”的简单格式：

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
  "group/service-b": "service_b_test"
}
```

使用规则：

1. 使用启动指南已经选定的 `{ZSTT_KIT}/project-databases.json`。项目级或共享 Kit 位于业务目录祖先时，以 Kit 所在安装根目录为基准计算当前项目相对路径；全局 Kit 不在业务目录祖先时，根据用户明确项目名匹配配置键，缺少唯一匹配时询问用户。以 `$` 开头的键是配置项，不参与项目路径匹配。
2. 仅当当前相对路径等于配置项，或以“配置项 + `/`”开头时才算匹配；再选择最长配置项。例如当前路径是 `group/service-b/module-a` 时，优先匹配 `group/service-b`，不得误用较短的 `group`，也不得让 `service-a` 误匹配 `service-ab`。
3. 找不到唯一匹配时询问用户库名，不猜测；用户确认后可以建议把映射补入文件，但未经用户要求不得修改。
4. 映射结果与项目运行配置、日志或用户说明冲突时停止并确认，以最新明确证据为准。
5. 默认把映射值视为测试库名。只有用户明确确认生产库名与测试相同并设置 `"$productionSameAsTest": true` 后，才可把同一库名写进生产只读 SQL；该标记不授权连接生产数据库，也不允许复用测试凭据。
6. 该文件不保存主机、端口、URL、账号、密码或其他凭据。生产环境默认只生成带库名的只读 SQL，交给用户或有权限的人员执行并回传结果。
7. `$testBackendSls` 只保存测试环境后端应用日志的 `region`、`project` 和 `logstore`。三项完整时直接用于 `sls_execute_sql`，不重复调用 `sls_list_projects` 或 `sls_list_logstores`。
8. `$testBackendSls` 不代表 Trace、Istio、Kubernetes 事件或生产日志。配置缺失、查询提示目标不存在或权限不覆盖时，才做一次收敛式发现；不得静默改用其他 Logstore。
9. `$testClientSls` 只保存测试客户端应用日志映射。查询时必须使用 `test observability-client` Scope，不得使用后端 `observability` AK；它同样不代表 Trace、Istio、Kubernetes 事件或生产日志。
10. `$prodBackendSls`、`$prodClientSls` 只保存生产后端、客户端应用日志映射。只有用户明确指定生产环境时，才分别使用 `prod observability`、`prod observability-client` Scope 做只读日志查询；不得回退到测试 AK，也不得据此连接生产数据库或 ES。

其他索引名、地域、Workspace、Project 和 Logstore 仍从当前项目运行配置、用户说明或收敛式元数据发现中确认，不能套用其他项目的历史映射。
