# 运行时发现与跨平台启动

在执行规则解析、环境注入或 Observability 工具前读取。目标是解析两个值：

- `{PYTHON}`：可用的 Python 3.11+ 启动器；
- `{ZSTT_KIT}`：包含 `runtime/rule_resolver.py` 的 `.zstt-kit` 绝对路径。

花括号只表示占位符，执行时必须替换为真实值并正确处理路径空格。

## Python 启动器

优先复用当前工具或运行环境已经提供且验证可执行的 Python 3.11+。否则按平台探测：

- macOS/Linux：依次尝试 `python3`、`python`；
- Windows：依次尝试 `py -3`、`python`、`python3`。

对候选执行版本检查，选择第一个 Python 3.11+。`py -3` 是启动器和参数的组合，不得当成单个文件路径。某个命令不存在时继续尝试下一个；在等价 Python 3 启动器之间切换属于安全兼容动作，不询问用户。

只有所有候选都不可用或版本过低时，才报告实际探测结果并停止需要本地 Python 的动作。不得把“系统没有 `python`，但存在 `python3`”写成环境门禁。

## ZSTT Kit 查找

按以下顺序查找，候选必须同时包含 `runtime/rule_resolver.py`、`runtime/with_env.py`、`runtime/dms_mcp_client.py` 和 `rules/catalog.json`：

1. 环境变量 `ZSTT_KIT_ROOT` 指向的目录；允许值是 `.zstt-kit` 本身或其父目录。
2. 从当前工作目录逐级向上查找 `.zstt-kit`。
3. 根据已加载的 Skill 位置查找：
   - `<root>/.agents/skills/zstt-bug-fix/SKILL.md` 对应 `<root>/.zstt-kit`；
   - `<codex-home>/skills/zstt-bug-fix/SKILL.md` 对应 `<codex-home>/zstt-kit`。
4. `CODEX_HOME/zstt-kit`；`CODEX_HOME` 未设置时检查用户目录下的 `.codex/zstt-kit`。

选择第一个完整候选并保存其绝对路径。不要受 Git 仓库边界限制：测试角色可以使用聚合目录或全局共享 Kit；开发角色仍从真实业务 Git 仓库读取代码。存在多个完整候选且配置目标不一致时，说明候选和选择依据，再按用户明确指定的项目或环境确认，不能混用凭据。

找不到完整 Kit 时，报告已检查的位置和缺失文件；不要猜路径，不读取其他目录的 `*.local` 凭据。

## 规则解析与 CLI 降级

找到 `{PYTHON}` 和 `{ZSTT_KIT}` 后，直接执行：

```text
{PYTHON} "{ZSTT_KIT}/runtime/rule_resolver.py" resolve --skill zstt-bug-fix
```

项目内规则解析器存在时不要求全局 `zstt` 命令。只有解析器实际返回配置、清单或规则错误时才做安装检查：

1. PATH 中存在 `zstt`：执行 `zstt check <ZSTT 安装根目录>`；
2. 当前 Python 可以导入 `zstt_cli`：执行 `{PYTHON} -m zstt_cli check <ZSTT 安装根目录>`；
3. 两者都不可用：保留原始解析错误，报告 CLI 能力缺口和可执行的修复命令。

命令名不存在、当前目录不是安装根目录或一次候选路径失败，都不等于规则无效。完成所有兼容探测前不得停止，也不得要求用户批准改用等价启动器。

## 后续命令

本次任务后续所有本地凭据命令都复用同一组解析结果：

```text
{PYTHON} "{ZSTT_KIT}/runtime/with_env.py" <test|prod> <scope> -- <command> [args...]
```

不得重新使用相对路径 `.zstt-kit/...`，不得在后续步骤静默切换到另一个 Kit，也不得回显解析出的凭据值。
