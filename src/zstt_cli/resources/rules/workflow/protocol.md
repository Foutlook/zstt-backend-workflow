# ZSTT 工作流协议

## 1. 调用边界

- 用户显式调用某个 `$zstt-*` 阶段 Skill，才执行该阶段。
- 用户调用下一阶段，视为同意推进；仍需重新校验所有必需上游产物。
- 当前阶段结束后可以推荐下一步，但不得自动执行推荐的下一阶段。
- 用户可以随时修改阶段产物。阶段完成时记录内容指纹；已完成产物变化后，该阶段及其下游完成状态失效，必须由用户重新确认并完成被修改阶段。

## 2. 目录和权威产物

full：

```text
.zstt/features/YYYYMMDD-feature-name/
```

quick：

```text
.zstt/quick/YYYYMMDD-quick-name/
```

每个固定阶段只有一份权威主产物。不要生成同阶段的 `final-v2`、`new`、`补充版` 等平行文档。用户纠正后直接回写权威主产物，并保留有意义的确认或决策记录。

详细接口、SQL、Claim Ledger、Review 轮次和测试原始记录可以写入 `auxiliary/`，但主产物必须保存附件索引、关键结论和当前权威状态。附件不得自动推进阶段；具体规则见 `document-authority.md`。

## 3. 模式和阶段

full 顺序：需求澄清、仓库调研、技术方案、任务拆分、编码实现、代码评审、测试验证。

quick 必须先做轻量需求澄清，随后可执行实现；Review 和测试由用户决定是否调用。quick 中一旦发现接口契约、SQL、跨仓库、核心状态模型或历史链路影响不清，应建议升级 full，但不得自动升级。

## 4. 状态语义

阶段文档 frontmatter：

- `status: draft`：仍在编写或确认。
- `status: completed`：当前阶段内容已完成，可执行门禁校验。
- `blocking_p0_count`：阻塞下一阶段的问题数。
- `open_p1_count`、`open_p2_count`：可带风险推进的问题数。

P0 大于 0 时不得完成阶段。P1/P2 可以推进，但当前阶段必须写清影响、处理计划和下游注意事项。

`meta.json` 只记录已验证事实和完成产物指纹，不负责自动触发 Skill。禁止直接手工修改它。

`status: completed` 只是完成声明，不等于通过门禁。必需章节必须有实质内容，模板空标签和占位符必须清理，full 调研、方案和任务还必须分别保留 Cxx/Exx、Dxx/Cxx、Txx/Cxx-Dxx 追溯关系。

## 5. CLI 协议

工作流命令统一使用业务仓库中的 `.zstt-kit/runtime/workflow_cli.py`。

初始化：

```text
python .zstt-kit/runtime/workflow_cli.py init --repo-root <业务仓库> --mode full|quick --feature-name <需求名>
```

准备当前阶段：

```text
python .zstt-kit/runtime/workflow_cli.py prepare-stage --feature-dir <需求目录> --stage <阶段键>
```

完成当前阶段：

```text
python .zstt-kit/runtime/workflow_cli.py complete-stage --feature-dir <需求目录> --stage <阶段键>
```

查看状态：

```text
python .zstt-kit/runtime/workflow_cli.py status --feature-dir <需求目录>
```

CLI 失败时停止阶段推进，修正文档或阻塞项后重试。若错误指出已完成产物被修改，先重新执行被修改阶段的 `complete-stage`；工具会保留文件，但撤销该阶段及下游的旧完成结论。不要通过手工创建后续文档或只修改 `status` 绕过门禁。

## 6. 动态规则加载

- 用户仍然显式选择具体 Skill；规则解析器只为当前 Skill 返回约束，不自动调用任何 Skill。
- 开始工作前运行 `.zstt-kit/runtime/rule_resolver.py resolve --skill <skill-name>`，并按实际代码范围追加 `--context <标签>`。
- 上下文标签必须来自已经读取的文件、真实调用链、数据源和行为边界；文件名、类名或关键词只能作为继续核实的线索。
- 完整读取解析结果中每个规则的 `path`，并在当前主产物或辅助记录中保存 `rulesetVersion`、`rulesetFingerprint`、规则 ID 和选择原因。
- 规则缺失、损坏或解析失败时停止当前阶段，先执行 `zstt check --here`；不得凭记忆补写规则内容。
- 工作范围扩大后重新解析规则，并记录新增上下文和规则变化。

## 7. 能力探测与降级

阶段开始时只探测当前任务需要的增强能力。工具可用时按增强路径取证；工具不可用、权限不足或结果不完整时走标准降级，并记录失败边界和证据置信度。具体规则见 `capability-fallback.md`。

工具缺失不能被写成验证通过，也不能通过增加业务 fallback 来补偿。若降级后仍无法证明关键口径，应形成 P0 或开放风险。

## 8. 阶段交付格式

最终回复只需包含：

1. 当前阶段结论；
2. 主产物路径；
3. 校验结果及仍开放的 P1/P2；
4. 推荐下一阶段 Skill；
5. 明确说明推荐项尚未自动执行。
