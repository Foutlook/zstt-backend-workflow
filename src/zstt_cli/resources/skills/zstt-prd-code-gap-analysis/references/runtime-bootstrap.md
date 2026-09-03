# 运行时发现与规则解析

执行规则解析或数据库取证前，先解析：

- `{PYTHON}`：可用的 Python 3.11+ 启动器；
- `{ZSTT_KIT}`：包含 `runtime/rule_resolver.py`、`runtime/with_env.py`、`runtime/dms_mcp_client.py`、`rules/catalog.json` 和 `project-databases.json` 的 `.zstt-kit` 绝对路径。

花括号只表示占位符，执行时必须替换为真实值并正确处理路径空格。

## Python 启动器

优先复用当前已验证的 Python 3.11+。否则：

- macOS/Linux：依次尝试 `python3`、`python`；
- Windows：依次尝试 `py -3`、`python`、`python3`。

对候选执行版本检查，选择第一个 Python 3.11+。`py -3` 是启动器和参数的组合。等价 Python 3 启动器之间切换是兼容动作，不要求用户批准；全部不可用或版本过低时才停止本地运行时动作。

## ZSTT Kit 查找

按顺序检查，选择第一个完整候选：

1. `ZSTT_KIT_ROOT` 指向的 `.zstt-kit` 或其父目录；
2. 从当前工作目录逐级向上查找 `.zstt-kit`；
3. 根据 Skill 位置查找：`<root>/.agents/skills/zstt-prd-code-gap-analysis/SKILL.md` 对应 `<root>/.zstt-kit`；
4. `CODEX_HOME/zstt-kit`；未设置 `CODEX_HOME` 时检查用户目录下的 `.codex/zstt-kit`。

项目级 Kit 位于业务目录祖先时，其安装根目录也是计算 `project-databases.json` 项目相对路径的基准。全局 Kit 不在业务目录祖先时，数据库映射必须根据用户明确的项目名唯一匹配。

不要因为当前目录不是安装根目录就放弃已找到的完整 Kit，也不要求必须存在全局 `zstt` 命令。找不到完整候选时，报告缺少的运行时文件和 `zstt init --here` / `zstt update --here` 的最小修复动作。

## 规则解析

使用解析出的同一组路径执行：

```text
{PYTHON} "{ZSTT_KIT}/runtime/rule_resolver.py" resolve --skill zstt-prd-code-gap-analysis
```

完整读取返回的每个规则路径并保存 `rulesetVersion`、`rulesetFingerprint`、规则 ID 和选择原因。不得手工猜测 Profile 或跳过缺失规则。
