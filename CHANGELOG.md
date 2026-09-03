# 变更日志

本项目遵循[语义化版本](https://semver.org/lang/zh-CN/)。未发布内容先记录在“未发布”，正式发布时归入对应版本。

## 未发布

### 变更

- 新增 `zstt-prd-code-gap-analysis`，将新增或变更需求与最新 release/bugfix 代码逐项对齐，并通过 ZSTT Kit 的分环境 DMS 只读链路核验 `test` 或显式授权的 `prod` 数据支持，输出未确认点和已证变更范围。
- 新增 `zstt-product-feature-analysis`，不依赖需求目录即可只读说明已有 Java 后端功能、规则、调用链和数据来源；默认在当前任务中交付，只有明确要求时才保存派生报告。
- `zstt-bug-fix` 在根因分析前增加缺陷确认卡和三分支定性门槛：支持缺陷、支持非缺陷或有界未解决；纯数据查询保持直达，只有支持缺陷才能进入责任分析和二次修复确认。
- Quick 需求与实现模板改为最小契约和增量记录；Full 的调研、方案、任务与实现通过 `Rxx/Cxx/Dxx/Txx` 引用上游，只保存本阶段新增事实和偏差，减少重复维护。
- 实现阶段新增自动证据：准备实现时保存 Git 基线，完成及进入 Review/测试前刷新相对变化；`run-validation` 持久化脱敏命令、退出码、耗时和执行时工作区指纹，完成门禁要求存在匹配最终快照的成功验证。
- 需求 Checklist 和实现前一致性分析改为可持久化质量门禁：固定报告路径保存规则快照、输入指纹和问题状态；下游按“缺失即跳过、存在即消费”校验，Quick 固定阶段链路不变。
- Full 在需求完成后同时推荐需求 Checklist 与仓库调研，在任务拆分后同时推荐一致性分析与编码实现；两个辅助 Skill 仍不进入 `completed_stages`。
- `zstt init/update` 增加项目级安装锁、候选文件暂存、事务日志、整批提交和失败回滚，避免安装内容处于半新半旧状态。
- `zstt init/update/check` 和项目本地 Workflow Runtime 增加稳定错误码；机器调用可使用 `--json` 获取结构化失败详情。
- Workflow Runtime 增加 `list/current/status --current/bind-branch/close`，按当前 Git 分支安全定位唯一活动需求，不再按日期猜测。
- 工作流状态增加 `active/closed` 生命周期；Quick 跳过可选 Review 和测试时可显式关闭，已关闭产物失效后重新进入可恢复候选。
- `zstt-bug-fix` 默认在当前任务中交付排查结论，只有用户明确要求文档时才创建 Bug 报告。
- `zstt-bug-fix` 增加 Trace/SLS 优先取证、双层 MCP 错误判断、脱敏和标准降级规则。
- `zstt-bug-fix` 将 SLS 日志默认入口改为按环境与端隔离凭据的只读客户端，不再预先探测 Observability MCP。
- `zstt-bug-fix` 增加 Alibaba Cloud DMS MCP 只读客户端，支持按测试/生产环境解析托管实例、查询表元数据和业务数据，并在调用前拦截写 SQL。
- 安装资源增加测试/生产环境模板和按 Observability、DMS、ES Scope 隔离凭据的跨平台启动器；本机 `*.local` 配置不进入安装清单。

## 0.4.0 - 2026-07-21

### 新增

- 新增 `zstt-bug-fix`，支持基于代码、日志、MySQL、ES 和时间线的证据化排查，并在用户二次确认后执行最小修复。
- 新增独立 Bug 报告模板和动态规则 Profile；独立记录写入 `.zstt/bugs/`，关联需求时写入 `auxiliary/bugs/`。

### 修复

- 修复 Windows Runner 的短路径与规范路径别名导致的诊断测试误报。
- 修复 CLI 输出被重定向到 CP1252 等非中文编码时可能触发的 `UnicodeEncodeError`。

### 验证

- 10 个 Skill 通过结构、规则、安装和行为契约校验。
- 全部仓库测试、Wheel 构建与隔离安装资源校验通过。

## 0.3.0 - 2026-07-21

### 新增

- 新增 `zstt doctor`，诊断安装清单、9 个项目级 Skill、Git 仓库边界和 Codex 发现路径。
- 新增仓库内 Skill 契约校验器，可在本地和 CI 中重复执行。
- 新增 GitHub Actions CI，自动执行测试、Skill 校验、Wheel 构建和隔离安装冒烟验证。
- 技术方案新增阶段内 SQL Gate；涉及 SQL 变化时生成精确语句并等待用户确认，确认前不进入任务拆分。

### 变更

- Quick 实现阶段完成后同时推荐代码评审与测试验证；直接完成测试后不再倒退推荐评审。
- `meta.json` 升级到 v3，业务产物目录改存 `.zstt/...` 相对路径，并在下一次写入时兼容迁移 v2。
- README 增加多 Git 仓库 Skill 发现边界、诊断和错误恢复说明。

### 验证

- 全部仓库测试通过。
- 9 个 Skill 通过结构与显式调用契约校验。
- Wheel 构建、隔离安装、初始化、诊断和 Rules 冒烟验证通过。
