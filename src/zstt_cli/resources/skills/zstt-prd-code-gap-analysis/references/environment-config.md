# DMS 环境与项目数据库映射

仅在需求差异结论需要真实数据库证据时读取。ZSTT 将测试和生产凭据放在 Kit 的本机配置中，由 `runtime/with_env.py` 按环境和 Scope 注入给子进程；Skill 不读取、打印、复制或持久化凭据值。

## 环境文件

- `test`：`{ZSTT_KIT}/.env/.env.local`，必须声明 `ZSTT_ENV=test`；
- `prod`：`{ZSTT_KIT}/.env/.env.prod.local`，必须声明 `ZSTT_ENV=prod`。

`dms` Scope 只读取当前环境的：

- `ZSTT_DMS_ALIBABA_CLOUD_ACCESS_KEY_ID`；
- `ZSTT_DMS_ALIBABA_CLOUD_ACCESS_KEY_SECRET`；
- 可选 `ZSTT_DMS_ALIBABA_CLOUD_SECURITY_TOKEN`。

`with_env.py` 只在 DMS 子进程中把它们映射为标准 `ALIBABA_CLOUD_*`。测试和生产使用不同文件，DMS 凭据不得与 Observability、ES 或其他 Scope 交叉注入。默认查询按 `prod` → `test` 顺序分别启动独立子进程；回退只切换环境配置，不得复用或复制另一环境的凭据。

启动形式固定为：

```text
{PYTHON} "{ZSTT_KIT}/runtime/with_env.py" <test|prod> dms -- {PYTHON} "{ZSTT_KIT}/runtime/dms_mcp_client.py" <command> ...
```

配置文件缺失、`ZSTT_ENV` 不匹配或必需键为空时停止查询，仅报告缺失键名，不显示值，也不读取其他 `.env`、系统环境变量或旧的 `ZSTT_MYSQL_*` 补救。

## project-databases.json

项目到 DMS Schema 的映射保存在 `{ZSTT_KIT}/project-databases.json`。该文件由 ZSTT 初始化创建，属于用户配置，不进入安装清单，后续 `zstt update` 不覆盖。

支持格式：

```json
{
  "$productionSameAsTest": true,
  "service-a": "service_a_test",
  "group/service-b": {
    "test": "service_b_test",
    "prod": {
      "schema": "service_b",
      "instanceAlias": "service-b-prod-primary"
    }
  }
}
```

解析规则：

1. Kit 位于业务目录祖先时，以 Kit 安装根目录为基准计算当前项目相对路径；全局 Kit 则按用户明确项目名匹配。
2. 只有当前相对路径等于配置键，或以“配置键 + `/`”开头时才匹配；从候选中选择最长配置项。以 `$` 开头的键不参与路径匹配。
3. 映射值是字符串时默认只表示测试库；对象可以分别包含 `test`、`prod`，环境值可以是 Schema 字符串或 `schema` + 可选 `instanceAlias` 对象。
4. 缺失、冲突或无法唯一匹配时询问用户，不猜测、不自动修改配置。用户明确要求时才可补映射。
5. 字符串映射只有在 `"$productionSameAsTest": true` 时可同时作为生产库名。该标记只允许库名相同，不允许复用测试凭据；生产仍必须使用 `prod dms`。
6. 取得 Schema 和可选实例别名后，必须通过 `searchDatabase` 与 `getInstance` 校验：测试只接受 `EnvType=test`，生产只接受 `EnvType=product`。同环境仍不唯一时让用户确认脱敏后的实例别名。
7. 文件不得保存 DMS 实例 ID、AccessKey、Token、主机、端口、URL、数据库账号或密码。

默认生产映射缺失、冲突或无法唯一匹配时，记录失败原因后可以解析测试映射继续验证；用户明确指定单一环境时仍按第 4 条停止确认，不跨环境回退。

项目映射与代码配置、运行配置或用户说明冲突时停止并确认，以当前任务中最新、明确、可验证的证据为准。
