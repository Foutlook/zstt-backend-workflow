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

库名、索引名、地域、Workspace、Project 和 Logstore 都属于业务项目配置，不写入通用 Skill。必须从当前项目运行配置、用户说明或收敛式元数据发现中确认，不能套用其他项目的历史映射。
