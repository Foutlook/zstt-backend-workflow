# ZSTT Backend Workflow Implementation Plan

> 历史实施记录：本文描述 0.1.x 的初始落地路径。0.2.0 已将内部共享 Skill 和 Java 规范 Skill 迁移为动态 Rules（规则）与 Runtime（运行时），不应按本文旧路径继续新增文件。

> **For Codex:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 构建一套 Codex-first、Java 后端专用、quick/full 双轨、由用户显式调用阶段 Skill 的 ZSTT 后端开发工作流。

**Architecture:** 八个对外 Skill 负责阶段判断和内容生成，一个共享底座通过 Python 标准库提供目录、元数据、模板与门禁校验，一个团队 Java 规范 Skill 提供编码和评审基线。业务产物始终写入目标仓库 `.zstt/`，固定阶段由 `meta.json` 记录事实但不自动串行执行。

**Tech Stack:** Codex Skills（Markdown/YAML）、Python 3 标准库、`unittest`、Git、PowerShell。

---

### Task 1: 建立项目骨架与基础质量检查

**Files:**
- Create: `README.md`
- Create: `.gitignore`
- Create: `tests/test_project_structure.py`

**Step 1: Write the failing test**

创建结构测试，断言 README、九个 Skill 目录和共享脚本目录存在；扫描所有文本文件，断言无 UTF-8 BOM。

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_project_structure -v`
Expected: FAIL，提示项目文件和 Skill 目录不存在。

**Step 3: Write minimal implementation**

创建 README 和目录骨架。README 说明安装方式、固定流程、quick/full、显式调用规则、`.zstt` 产物目录及非目标。

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_project_structure -v`
Expected: PASS。

**Step 5: Commit**

```powershell
git add README.md .gitignore tests skills
git commit -m "初始化 ZSTT 后端工作流项目骨架"
```

### Task 2: 以测试定义阶段契约和路径规则

**Files:**
- Create: `tests/test_workflow_contracts.py`
- Create: `skills/zstt-workflow-shared/scripts/workflow_contracts.py`
- Create: `skills/zstt-workflow-shared/scripts/workflow_paths.py`

**Step 1: Write the failing tests**

覆盖：

- full 阶段顺序和主产物命名；
- quick 阶段顺序和主产物命名；
- `zstt-code-simplification` 不属于固定阶段；
- feature 名称清理后不能逃逸仓库根目录；
- `.zstt/features` 与 `.zstt/quick` 路径解析。

**Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.test_workflow_contracts -v`
Expected: FAIL，模块尚不存在。

**Step 3: Write minimal implementation**

在 `workflow_contracts.py` 定义不可变阶段契约：

```python
FULL_STAGES = (
    ("requirement_clarification", "00-requirement.md", "zstt-requirement-clarification"),
    ("repo_research", "01-research.md", "zstt-repo-research"),
    ("technical_design", "02-design.md", "zstt-technical-design"),
    ("task_breakdown", "03-tasks.md", "zstt-task-breakdown"),
    ("implementation", "04-implementation.md", "zstt-implementation"),
    ("code_review", "05-code-review.md", "zstt-code-review"),
    ("test_verify", "06-test-report.md", "zstt-test-verify"),
)
```

quick 契约只包含需求澄清、实现、可选 Review 和可选测试。路径模块使用 `pathlib.Path.resolve()` 校验最终路径仍在仓库 `.zstt` 内。

**Step 4: Run tests to verify they pass**

Run: `python -m unittest tests.test_workflow_contracts -v`
Expected: PASS。

**Step 5: Commit**

```powershell
git add tests/test_workflow_contracts.py skills/zstt-workflow-shared/scripts
git commit -m "新增工作流阶段与路径契约"
```

### Task 3: 以测试实现元数据、初始化和状态查询

**Files:**
- Create: `tests/test_workflow_cli.py`
- Create: `skills/zstt-workflow-shared/scripts/workflow_cli.py`
- Create: `skills/zstt-workflow-shared/assets/templates/full/00-requirement.md`
- Create: `skills/zstt-workflow-shared/assets/templates/quick/00-requirement.md`

**Step 1: Write the failing tests**

使用临时业务仓库验证：

- `init --mode full` 只创建 `meta.json` 和 full `00-requirement.md`；
- `init --mode quick` 只创建 quick 对应文件；
- 已有需求目录默认拒绝覆盖；
- `status` 返回模式、当前阶段、产物和推荐 Skill；
- 所有生成文本为 UTF-8 无 BOM。

**Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.test_workflow_cli.WorkflowCliInitTest -v`
Expected: FAIL，CLI 尚不存在。

**Step 3: Write minimal implementation**

使用 `argparse` 实现：

```text
workflow_cli.py init --repo-root <path> --mode full|quick --feature-name <name> [--date YYYYMMDD]
workflow_cli.py status --feature-dir <path>
```

`meta.json` 至少记录版本、模式、需求名、当前阶段、完成阶段、产物映射、阻塞计数、最近校验和推荐 Skill。

**Step 4: Run tests to verify they pass**

Run: `python -m unittest tests.test_workflow_cli.WorkflowCliInitTest -v`
Expected: PASS。

**Step 5: Commit**

```powershell
git add tests/test_workflow_cli.py skills/zstt-workflow-shared
git commit -m "实现需求目录初始化与状态查询"
```

### Task 4: 以测试实现阶段文档校验和推进门禁

**Files:**
- Modify: `tests/test_workflow_cli.py`
- Create: `skills/zstt-workflow-shared/scripts/workflow_validation.py`
- Modify: `skills/zstt-workflow-shared/scripts/workflow_cli.py`
- Create: `skills/zstt-workflow-shared/assets/templates/full/01-research.md`
- Create: `skills/zstt-workflow-shared/assets/templates/full/02-design.md`
- Create: `skills/zstt-workflow-shared/assets/templates/full/03-tasks.md`
- Create: `skills/zstt-workflow-shared/assets/templates/full/04-implementation.md`
- Create: `skills/zstt-workflow-shared/assets/templates/full/05-code-review.md`
- Create: `skills/zstt-workflow-shared/assets/templates/full/06-test-report.md`
- Create: `skills/zstt-workflow-shared/assets/templates/quick/01-implementation.md`
- Create: `skills/zstt-workflow-shared/assets/templates/quick/02-code-review.md`
- Create: `skills/zstt-workflow-shared/assets/templates/quick/03-test-report.md`

**Step 1: Write the failing tests**

覆盖：

- `validate` 检查 frontmatter、必需章节、`status: completed` 和 P0 数量；
- P0 大于 0 时拒绝完成；
- `prepare-stage` 每次重新校验全部必需上游文档；
- 用户修改已完成上游文档后，校验失败并阻止推进；
- full 不允许跳阶段；
- quick 允许只执行实现，也允许实现后直接测试；Review 存在时一并校验；
- 失败时不创建目标文档、不推进 `meta.json`；
- 成功时只创建当前目标文档。

**Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.test_workflow_cli.WorkflowCliGateTest -v`
Expected: FAIL，校验和推进命令尚不存在。

**Step 3: Write minimal implementation**

新增命令：

```text
workflow_cli.py validate --feature-dir <path> [--stage <stage>]
workflow_cli.py complete-stage --feature-dir <path> --stage <stage>
workflow_cli.py prepare-stage --feature-dir <path> --stage <stage>
```

解析简单 YAML frontmatter，不引入第三方依赖。`prepare-stage` 先重新验证上游，再复制唯一模板；`complete-stage` 校验当前产物后记录完成事实和推荐 Skill。

**Step 4: Run tests to verify they pass**

Run: `python -m unittest tests.test_workflow_cli -v`
Expected: PASS。

**Step 5: Commit**

```powershell
git add tests/test_workflow_cli.py skills/zstt-workflow-shared
git commit -m "实现阶段校验与显式推进门禁"
```

### Task 5: 创建共享协议和需求、调研、方案 Skill

**Files:**
- Create: `skills/zstt-workflow-shared/SKILL.md`
- Create: `skills/zstt-workflow-shared/references/workflow-protocol.md`
- Create: `skills/zstt-workflow-shared/references/evidence-rules.md`
- Create: `skills/zstt-requirement-clarification/SKILL.md`
- Create: `skills/zstt-repo-research/SKILL.md`
- Create: `skills/zstt-technical-design/SKILL.md`
- Create: `tests/test_skill_contracts.py`

**Step 1: Write the failing tests**

扫描 Skill：

- frontmatter 名称与目录一致；
- description 明确触发场景且只允许显式阶段请求触发；
- 固定阶段 Skill 引用共享协议和对应模板；
- Skill 明确禁止自动执行推荐的下一阶段；
- requirement 包含 P0/P1/P2、事实/推断/冲突规则；
- research 包含真实调用链、guard/依赖、最终数据源和证据等级；
- design 包含接口/Jackson、数据源一致性、发布回滚和测试策略。

**Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.test_skill_contracts -v`
Expected: FAIL，Skill 文件尚不存在。

**Step 3: Write minimal implementation**

每个 Skill 保持在 500 行以内，使用命令式说明，明确输入、门禁、执行步骤、主产物、禁止事项和下一步推荐。共享协议说明目录、元数据、权威产物、用户修改和重新校验规则。

**Step 4: Run tests to verify they pass**

Run: `python -m unittest tests.test_skill_contracts -v`
Expected: PASS。

**Step 5: Commit**

```powershell
git add skills/zstt-workflow-shared skills/zstt-requirement-clarification skills/zstt-repo-research skills/zstt-technical-design tests/test_skill_contracts.py
git commit -m "新增需求调研与技术方案技能"
```

### Task 6: 创建任务、实现、评审和测试 Skill

**Files:**
- Create: `skills/zstt-task-breakdown/SKILL.md`
- Create: `skills/zstt-implementation/SKILL.md`
- Create: `skills/zstt-code-review/SKILL.md`
- Create: `skills/zstt-test-verify/SKILL.md`
- Modify: `tests/test_skill_contracts.py`

**Step 1: Extend failing tests**

断言：

- task breakdown 的每个任务必须有来源、文件范围、依赖、完成标准和验证命令；
- implementation 禁止 N+1、循环远程调用、无关重构和注释丢失；
- code review 默认只读，输出按优先级排序的证据化发现；
- test verify 区分六类差异并给出证据化交付结论；
- 每个 Skill 只生成自己的主产物并推荐下一步。

**Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.test_skill_contracts -v`
Expected: FAIL，新 Skill 尚不存在。

**Step 3: Write minimal implementation**

结合设计文档和两个来源项目的有效规则，创建四个阶段 Skill；不复制旧命名、自动串行入口或个人风格约定。

**Step 4: Run tests to verify they pass**

Run: `python -m unittest tests.test_skill_contracts -v`
Expected: PASS。

**Step 5: Commit**

```powershell
git add skills/zstt-task-breakdown skills/zstt-implementation skills/zstt-code-review skills/zstt-test-verify tests/test_skill_contracts.py
git commit -m "新增实现评审与测试验证技能"
```

### Task 7: 创建团队 Java 规范和可选代码简化 Skill

**Files:**
- Create: `skills/zstt-java-backend-standard/SKILL.md`
- Create: `skills/zstt-java-backend-standard/references/java-backend-guidelines.md`
- Create: `skills/zstt-code-simplification/SKILL.md`
- Modify: `tests/test_skill_contracts.py`

**Step 1: Extend failing tests**

断言规范包含：

- 项目约束和局部一致性优先；
- 注释保留与非平凡逻辑注释；
- Jackson 高风险字段显式属性名和绑定测试；
- 禁止 N+1 和循环远程调用；
- 聚合数据源闭环；
- Maven smart-doc 本地验证规则；
- 代码简化 Skill 不推进阶段、不改业务行为、不做无关重构。

**Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.test_skill_contracts -v`
Expected: FAIL，规范和辅助 Skill 尚不存在。

**Step 3: Write minimal implementation**

把已确认、可客观评审的规则整理为团队规范；不保留“个人风格”名称。代码简化 Skill 支持 diff、提交、文件和符号范围，关联需求时只写 `auxiliary/` 记录。

**Step 4: Run tests to verify they pass**

Run: `python -m unittest tests.test_skill_contracts -v`
Expected: PASS。

**Step 5: Commit**

```powershell
git add skills/zstt-java-backend-standard skills/zstt-code-simplification tests/test_skill_contracts.py
git commit -m "新增团队代码规范与代码简化技能"
```

### Task 8: 端到端验收和文档收口

**Files:**
- Modify: `README.md`
- Create: `tests/test_end_to_end.py`

**Step 1: Write the failing end-to-end tests**

模拟：

- full 从初始化到测试报告的逐阶段准备与完成；
- quick 从需求到实现，再直接测试；
- 用户完成阶段后修改上游产物导致下一阶段被阻止；
- P0 清零后重新推进成功；
- 辅助 Skill 目录存在但不出现在固定状态链。

**Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.test_end_to_end -v`
Expected: FAIL，README 或少量集成行为尚未收口。

**Step 3: Complete documentation and integration behavior**

补齐 README 的安装、调用示例、目录示例、人工修改流程、状态命令、错误恢复和非自动化边界。

**Step 4: Run the full verification suite**

Run: `python -m unittest discover -s tests -v`
Expected: 所有测试 PASS。

Run: `git diff --check`
Expected: 无输出，退出码 0。

运行 UTF-8 BOM 扫描测试。

**Step 5: Commit**

```powershell
git add README.md tests/test_end_to_end.py
git commit -m "完成 ZSTT 后端工作流端到端验收"
```

### Task 9: 最终人工审阅边界

**Files:**
- Review: `skills/*/SKILL.md`
- Review: `skills/zstt-workflow-shared/assets/templates/**/*.md`
- Review: `skills/zstt-workflow-shared/scripts/*.py`

**Step 1: Inspect final history and worktree**

Run: `git status --short`
Expected: 空。

Run: `git log --oneline --decorate -10`
Expected: 设计、计划和各实施阶段均有中文提交记录。

**Step 2: Re-run verification**

Run: `python -m unittest discover -s tests -v`
Expected: PASS。

**Step 3: Human review reminder**

在交付说明中明确：非平凡、生产相关的工作流规则和自动门禁仍需团队在 IDE 中端到端理解并评审后再推广安装。
