# 排查环境配置

仅在排查需要本地命令使用 Observability、MySQL 或 ES 凭据时读取。项目已注册的 MCP 或连接器自行安全管理凭据时，不读取本地环境文件。

## 环境文件

- 测试环境：`.zstt-kit/.env/.env.local`，文件内必须声明 `ZSTT_ENV=test`。
- 生产环境：`.zstt-kit/.env/.env.prod.local`，文件内必须声明 `ZSTT_ENV=prod`。
- 字段模板：`.env.example` 和 `.env.prod.example`；复制模板后只在本机填写，禁止提交真实值。
- ZSTT 安装和更新只管理模板及 `.gitignore`，不创建、读取、覆盖或记录任何 `*.local` 文件。

生产配置缺失、声明不匹配或权限不足时立即停止，不得回退到测试配置。用户没有明确环境时必须先确认，不得仅凭域名、类名或历史经验选择。

## 隔离执行

使用以下入口启动需要凭据的本地只读工具：

```text
python .zstt-kit/runtime/with_env.py <test|prod> <observability|mysql|es> -- <command> [args...]
```

- `observability`：只注入 `ALIBABA_CLOUD_*`。
- `mysql`：只注入 `ZSTT_MYSQL_*`。
- `es`：只注入 `ZSTT_ES_*`。

入口会先清除当前进程继承的全部受管变量，再只注入目标 Scope。不同 Scope 的凭据不得交叉注入。MySQL 和 ES 账号必须只读；Skill 仍禁止数据写入、索引修改、删除、缓存清理和消息重放。

## 项目映射

项目与 MySQL 库名映射保存在安装根目录的 `.zstt-kit/project-databases.json`。该文件由 ZSTT 首次初始化或更新时创建为空 JSON 对象，属于用户配置，不进入安装清单，后续 `zstt update` 不覆盖。

文件使用“项目相对路径 → 测试库名”的简单格式：

```json
{
  "$productionSameAsTest": true,
  "service-a": "service_a_test",
  "group/service-b": "service_b_test"
}
```

使用规则：

1. 从当前目录向上找到 `.zstt-kit/project-databases.json`，以其所在安装根目录为基准计算当前项目相对路径。以 `$` 开头的键是配置项，不参与项目路径匹配。
2. 仅当当前相对路径等于配置项，或以“配置项 + `/`”开头时才算匹配；再选择最长配置项。例如当前路径是 `group/service-b/module-a` 时，优先匹配 `group/service-b`，不得误用较短的 `group`，也不得让 `service-a` 误匹配 `service-ab`。
3. 找不到唯一匹配时询问用户库名，不猜测；用户确认后可以建议把映射补入文件，但未经用户要求不得修改。
4. 映射结果与项目运行配置、日志或用户说明冲突时停止并确认，以最新明确证据为准。
5. 默认把映射值视为测试库名。只有用户明确确认生产库名与测试相同并设置 `"$productionSameAsTest": true` 后，才可把同一库名写进生产只读 SQL；该标记不授权连接生产数据库，也不允许复用测试凭据。
6. 该文件不保存主机、端口、URL、账号、密码或其他凭据。生产环境默认只生成带库名的只读 SQL，交给用户或有权限的人员执行并回传结果。

索引名、地域、Workspace、Project 和 Logstore 仍从当前项目运行配置、用户说明或收敛式元数据发现中确认，不能套用其他项目的历史映射。
