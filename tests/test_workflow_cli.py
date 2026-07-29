from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "src" / "zstt_cli" / "resources" / "runtime"
CLI = RUNTIME / "workflow_cli.py"


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def set_git_branch(repo_root: Path, branch: str) -> None:
    if not (repo_root / ".git").exists():
        completed = subprocess.run(
            ["git", "init", "--quiet", str(repo_root)],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if completed.returncode != 0:
            raise AssertionError(completed.stderr)
    completed = subprocess.run(
        [
            "git",
            "-C",
            str(repo_root),
            "symbolic-ref",
            "HEAD",
            f"refs/heads/{branch}",
        ],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if completed.returncode != 0:
        raise AssertionError(completed.stderr)


def replace_frontmatter_value(path: Path, key: str, value: str) -> None:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    prefix = f"{key}:"
    for index, line in enumerate(lines):
        if line.startswith(prefix):
            lines[index] = f"{key}: {value}"
            path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
            return
    raise AssertionError(f"frontmatter key not found: {key}")


def insert_markdown_row(text: str, header: str, row: str) -> str:
    lines = text.splitlines()
    try:
        header_index = lines.index(header)
    except ValueError as exc:
        raise AssertionError(f"table header not found: {header}") from exc
    lines.insert(header_index + 2, row)
    return "\n".join(lines) + "\n"


def fill_stage_document(path: Path, stage: str) -> None:
    """Fill generated scaffolding with deterministic, substantive test evidence."""
    text = path.read_text(encoding="utf-8")
    text = re.sub(
        r"^(## .+)$",
        r"\1\n\n- 测试事实：已根据输入和实际边界核实",
        text,
        flags=re.MULTILINE,
    )
    text = re.sub(
        r"^(\s*[-*]\s+[^\n：:]+[：:])\s*$",
        r"\1 已确认",
        text,
        flags=re.MULTILINE,
    )

    if stage == "requirement_clarification":
        text = insert_markdown_row(
            text,
            "| 来源 ID | 原始材料定位 | 原始要点 | 处理结果 | 对应 Rxx/Qxx | 处理说明 |"
            if "mode: full" in text
            else "| 来源 ID | 原始要点 | 处理结果 | 对应 Rxx/Qxx | 处理说明 |",
            "| S01 | PRD 第 1 条 | 管理员导出学习报告 | 形成需求 | R01 | 已形成正式需求 |"
            if "mode: full" in text
            else "| S01 | 管理员导出学习报告 | 形成需求 | R01 | 已形成正式需求 |",
        )
        text = insert_markdown_row(
            text,
            "| 需求 ID | 类型 | 已确认业务结论 | 来源 Sxx/Qxx | 详细章节 | 状态 |"
            if "mode: full" in text
            else "| 需求 ID | 已确认边界/规则 | 来源 Sxx/Qxx | 状态 |",
            "| R01 | 功能 | 管理员可以导出学习报告 | S01 | 用户路径与验收 | 已确认 |"
            if "mode: full" in text
            else "| R01 | 管理员可以导出学习报告 | S01 | 已确认 |",
        )
        text = insert_markdown_row(
            text,
            "| 需求 ID | 场景 | 前置/输入 | 操作/触发 | 预期结果 | 验证方式 |"
            if "mode: full" in text
            else "| 需求 ID | 前置/输入 | 操作/触发 | 用户可见结果 | 最小验证信号 |",
            "| R01 | 主路径 | 管理员已登录 | 点击导出 | 获得学习报告文件 | 功能验证 |"
            if "mode: full" in text
            else "| R01 | 管理员已登录 | 点击导出 | 获得学习报告文件 | 文件可下载 |",
        )
        text = text.replace(
            "confirmation_status: pending",
            "confirmation_status: confirmed",
            1,
        ).replace(
            'confirmation_source: ""',
            "confirmation_source: 用户确认消息-1",
            1,
        )

    if stage == "repo_research":
        text = insert_markdown_row(
            text,
            "| 需求 ID | 需求主张 | 代码验证问题 | 验证状态 | 结论 ID | 证据 ID | 风险/RQxx |",
            "| R01 | 管理员导出学习报告 | 当前代码入口和数据源是什么 | 已验证 | C01 | E01 | 无 |",
        )
        text = insert_markdown_row(
            text,
            "| 仓库 | 角色 | 分类 | 判断依据 | 结论 ID | 证据 ID | 置信度 |",
            "| test-repo | 主业务仓库 | Must change | 导出入口位于本仓库 | C01 | E01 | 高 |",
        )
        text = insert_markdown_row(
            text,
            "| 仓库 | 变更对象/排除范围 | API/DTO/契约 | 服务逻辑 | SQL/配置/消息/任务 | 测试与发布依赖 | 结论/证据 |",
            "| test-repo | 导出入口 | 保持现有契约 | 调整导出逻辑 | 不涉及 | 补充聚焦测试 | C01/E01 |",
        )
        text = insert_markdown_row(
            text,
            "| 结论 ID | 结论 | 证据 ID | 证据等级 | 代码位置 | 反证 | 覆盖度 | 置信度 | 运行时缺口 | 待验证动作 |",
            "| C01 | 导出入口位于本仓库 | E01 | Proven | src/ReportService.java:1 | 未发现 | 已覆盖 R01 | 高 | 无 | 无 |",
        )
        text = insert_markdown_row(
            text,
            "| 证据 ID | 证据类型 | 仓库 | 文件/符号/运行证据 | 行号/定位 | 支持结论 | 限制 |",
            "| E01 | 本地源码 | test-repo | src/ReportService.java | 1 | C01 | 仅证明测试入口 |",
        )
        text = text.replace(
            "research_scope: full",
            "research_scope: full",
            1,
        ).replace(
            "shared_semantic_impact: pending",
            "shared_semantic_impact: none",
            1,
        ).replace(
            "current_sql_impact: pending",
            "current_sql_impact: none",
            1,
        ).replace(
            "- 判定依据： 已确认",
            "- 判定依据：C01/E01",
        )
        source_file = path.parents[3] / "src" / "ReportService.java"
        source_file.parent.mkdir(parents=True, exist_ok=True)
        source_file.write_text(
            "class ReportService {}\n",
            encoding="utf-8",
            newline="\n",
        )

    if stage == "technical_design":
        text = insert_markdown_row(
            text,
            "| 输入 ID | 处理方式 | 对应 Dxx/章节或原因 |",
            "| C01 | 进入设计 | D01 |",
        )
        text = insert_markdown_row(
            text,
            "| 差距 ID | 模块/能力 | 当前代码事实 | 目标需求 | 来源 Cxx | 结论/阻塞 |",
            "| GAP01 | 学习报告导出 | 当前入口只输出基础字段 | 增加完整学习报告 | C01 | 采用 D01 增量实现 |",
        )
        text = insert_markdown_row(
            text,
            "| 设计 ID | 决策点 | 当前事实/约束 | 最小可行方案 | 更复杂备选 | 不采用原因 | 来源 Cxx | 确认状态 | 结论 | 影响/代价 | 触发升级条件 | 验证方式 |",
            "| D01 | 学习报告导出落点 | 现有导出入口位于 Test 类 | 在现有入口增加字段组装 | 新建独立导出服务 | 当前只有一个调用方，无独立服务收益 | C01 | 已确认 | 采用 | 修改现有入口并保持接口兼容 | 出现两个以上独立调用方时拆分服务 | 执行 Python 工作流回归测试 |",
        )
        text = insert_markdown_row(
            text,
            "| 设计 ID | 调用方/触发事件 | 契约类型 | 契约标识 | 输入关键字段 | 后端推导字段/来源 | 禁止外部传字段 | 输出字段 | 副作用 | 权限/幂等/兼容 | 独立明细 | 来源 Cxx |",
            "| D01 | 管理员点击导出 | HTTP | GET /reports/export | reportType | operatorId=登录上下文 | operatorId | reportFile | 无：只读导出 | 沿用管理员鉴权，保持旧响应兼容 | 无需：简单内部接口 | C01 |",
        )
        text = insert_markdown_row(
            text,
            "| 设计 ID | 项目/仓库 | 类型 | 文件/类/表/配置/Topic | 符号/方法 | 改动类型 | 改动说明 | 来源 Cxx |",
            "| D01 | test-repo | Service | src/ReportService.java | ReportService.export | 修改 | 在现有导出入口组装完整报告字段 | C01 |",
        )
        text = text.replace(
            "- 持久业务实例：有 / 无：具体原因",
            "- 持久业务实例：无：本次只读导出不保存独立业务实例",
        ).replace(
            "- 需任务承接的核心 Dxx： 已确认",
            "- 需任务承接的核心 Dxx：D01",
        )

    if stage == "task_breakdown":
        text = insert_markdown_row(
            text,
            "| 来源类型 | 来源 ID/位置 | 要求或决策 | 对应任务/交接项 | 覆盖状态 | 缺口 |",
            "| 设计核心改动 | D01 | 修改现有导出入口 | T01 | 已覆盖 | 无 |",
        )
        text = insert_markdown_row(
            text,
            "| 任务 ID | 开发任务 | 所属项目 | 状态 | 依赖任务 |",
            "| T01 | 实现完整学习报告导出 | test-repo | ready | - |",
        )
        concrete_detail = """#### T01 实现完整学习报告导出

- 来源依据：D01 / C01
- 预计修改文件/符号：src/ReportService.java#export
- 主要实现内容：在现有导出入口组装完整报告字段
- 明确不做事项：不新增独立导出服务
- 完成标准：以下子项均需满足
  - 代码结果与关键行为：导出结果包含设计要求的完整字段并保持旧契约兼容
  - 测试代码：默认不新增
  - 精确验证命令：python -m unittest tests.test_workflow_cli
  - 预期信号：命令退出码为 0
  - 失败信号：出现断言失败或非零退出码
- 风险：保持旧响应字段和管理员权限语义
"""
        text = re.sub(
            r"#### Txx 实现具体代码能力.*?(?=## 4\. 文件范围与并行安全)",
            concrete_detail + "\n",
            text,
            flags=re.DOTALL,
        )
        text = insert_markdown_row(
            text,
            "| 任务 | 并行组 | 允许修改 | 冲突文件 | 共享依赖 | 契约/SQL/配置影响 | 冲突结论 | 执行方式 |",
            "| T01 | G1 | src/ReportService.java | 无：单任务 | D01 | 保持 HTTP 契约兼容 | 需串行 | 串行 |",
        )
        text = insert_markdown_row(
            text,
            "| 任务 | 精确验证命令 | 预期信号 | 失败信号 | 完成标准 |",
            "| T01 | python -m unittest tests.test_workflow_cli | 命令退出码为 0 | 出现断言失败或非零退出码 | 导出结果包含设计要求的完整字段并保持旧契约兼容 |",
        )
        text = text.replace(
            "- 当前可执行集合： 已确认",
            "- 当前可执行集合：T01",
        ).replace(
            "- 禁止提前执行集合： 已确认",
            "- 禁止提前执行集合：无",
        ).replace(
            "- 并行等级（L0/L1/L2）： 已确认",
            "- 并行等级（L0/L1/L2）：L0",
        ).replace(
            "- 当前可执行任务： 已确认",
            "- 当前可执行任务：T01",
        ).replace(
            "- 当前禁止执行任务： 已确认",
            "- 当前禁止执行任务：无",
        )

    traceability = {
        "technical_design": "\n- D01：基于 C01 选择最小改动方案。\n",
        "task_breakdown": "\n- T01：依据 D01 实现并执行验证。\n",
    }
    text += traceability.get(stage, "")
    path.write_text(text, encoding="utf-8", newline="\n")
    replace_frontmatter_value(path, "status", "completed")


def init_feature(repo_root: Path, mode: str = "full") -> Path:
    name = "学习报告"
    completed = run_cli(
        "init",
        "--repo-root",
        str(repo_root),
        "--mode",
        mode,
        "--feature-name",
        name,
        "--date",
        "20260716",
    )
    if completed.returncode != 0:
        raise AssertionError(completed.stderr)
    category = "features" if mode == "full" else "quick"
    return repo_root / ".zstt" / category / f"20260716-{name}"


def prepare_technical_design(repo_root: Path) -> Path:
    feature_dir = init_feature(repo_root)
    requirement = feature_dir / "00-requirement.md"
    fill_stage_document(requirement, "requirement_clarification")
    assert run_cli(
        "complete-stage",
        "--feature-dir",
        str(feature_dir),
        "--stage",
        "requirement_clarification",
    ).returncode == 0
    assert run_cli(
        "prepare-stage",
        "--feature-dir",
        str(feature_dir),
        "--stage",
        "repo_research",
    ).returncode == 0
    research = feature_dir / "01-research.md"
    fill_stage_document(research, "repo_research")
    assert run_cli(
        "complete-stage",
        "--feature-dir",
        str(feature_dir),
        "--stage",
        "repo_research",
    ).returncode == 0
    assert run_cli(
        "prepare-stage",
        "--feature-dir",
        str(feature_dir),
        "--stage",
        "technical_design",
    ).returncode == 0
    fill_stage_document(feature_dir / "02-design.md", "technical_design")
    return feature_dir


def prepare_task_breakdown(repo_root: Path) -> Path:
    feature_dir = prepare_technical_design(repo_root)
    assert run_cli(
        "prepare-sql-gate",
        "--feature-dir",
        str(feature_dir),
        "--impact",
        "none",
    ).returncode == 0
    assert run_cli(
        "complete-stage",
        "--feature-dir",
        str(feature_dir),
        "--stage",
        "technical_design",
    ).returncode == 0
    assert run_cli(
        "prepare-stage",
        "--feature-dir",
        str(feature_dir),
        "--stage",
        "task_breakdown",
    ).returncode == 0
    fill_stage_document(feature_dir / "03-tasks.md", "task_breakdown")
    return feature_dir


def complete_quick_implementation(feature_dir: Path) -> None:
    requirement = feature_dir / "00-requirement.md"
    fill_stage_document(requirement, "requirement_clarification")
    completed = run_cli(
        "complete-stage",
        "--feature-dir",
        str(feature_dir),
        "--stage",
        "requirement_clarification",
    )
    if completed.returncode != 0:
        raise AssertionError(completed.stderr)
    prepared = run_cli(
        "prepare-stage",
        "--feature-dir",
        str(feature_dir),
        "--stage",
        "implementation",
    )
    if prepared.returncode != 0:
        raise AssertionError(prepared.stderr)
    fill_stage_document(feature_dir / "01-implementation.md", "implementation")
    completed = run_cli(
        "complete-stage",
        "--feature-dir",
        str(feature_dir),
        "--stage",
        "implementation",
    )
    if completed.returncode != 0:
        raise AssertionError(completed.stderr)


def prepare_research_document(repo_root: Path) -> Path:
    feature_dir = init_feature(repo_root)
    requirement = feature_dir / "00-requirement.md"
    fill_stage_document(requirement, "requirement_clarification")
    completed = run_cli(
        "complete-stage",
        "--feature-dir",
        str(feature_dir),
        "--stage",
        "requirement_clarification",
    )
    if completed.returncode != 0:
        raise AssertionError(completed.stderr)
    prepared = run_cli(
        "prepare-stage",
        "--feature-dir",
        str(feature_dir),
        "--stage",
        "repo_research",
    )
    if prepared.returncode != 0:
        raise AssertionError(prepared.stderr)
    fill_stage_document(feature_dir / "01-research.md", "repo_research")
    return feature_dir


class WorkflowCliInitTest(unittest.TestCase):
    def test_init_records_branch_and_current_selects_unique_unfinished_feature(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            set_git_branch(repo_root, "feature/report-export")
            feature_dir = init_feature(repo_root)

            meta = json.loads(
                (feature_dir / "meta.json").read_text(encoding="utf-8")
            )
            self.assertEqual("feature/report-export", meta["git_branch"])

            current = run_cli("current", "--repo-root", str(repo_root))

            self.assertEqual(0, current.returncode, current.stderr)
            payload = json.loads(current.stdout)
            self.assertEqual(
                str(feature_dir.resolve()),
                payload["feature"]["absolute_path"],
            )
            self.assertEqual(
                "feature/report-export",
                payload["current_git_branch"],
            )

            status = run_cli(
                "status",
                "--current",
                "--repo-root",
                str(repo_root),
            )
            self.assertEqual(0, status.returncode, status.stderr)
            self.assertEqual(
                feature_dir.relative_to(repo_root).as_posix(),
                json.loads(status.stdout)["feature_dir"],
            )

    def test_status_explicit_feature_dir_has_priority_over_current(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            set_git_branch(repo_root, "feature/original")
            feature_dir = init_feature(repo_root)
            set_git_branch(repo_root, "feature/other")

            status = run_cli(
                "status",
                "--current",
                "--repo-root",
                str(repo_root),
                "--feature-dir",
                str(feature_dir),
            )

            self.assertEqual(0, status.returncode, status.stderr)
            self.assertEqual(
                feature_dir.relative_to(repo_root).as_posix(),
                json.loads(status.stdout)["feature_dir"],
            )

    def test_current_blocks_when_branch_has_multiple_unfinished_features(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            set_git_branch(repo_root, "feature/shared")
            init_feature(repo_root)
            second = run_cli(
                "init",
                "--repo-root",
                str(repo_root),
                "--mode",
                "quick",
                "--feature-name",
                "修正文案",
                "--date",
                "20260717",
            )
            self.assertEqual(0, second.returncode, second.stderr)

            current = run_cli(
                "--json",
                "current",
                "--repo-root",
                str(repo_root),
            )

            self.assertEqual(2, current.returncode)
            payload = json.loads(current.stdout)
            self.assertEqual(
                "ZSTT_CURRENT_AMBIGUOUS",
                payload["error"]["code"],
            )
            self.assertEqual(2, len(payload["error"]["details"]["candidates"]))

    def test_current_never_falls_back_to_latest_feature_on_another_branch(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            set_git_branch(repo_root, "feature/original")
            init_feature(repo_root)
            set_git_branch(repo_root, "feature/other")

            current = run_cli(
                "--json",
                "current",
                "--repo-root",
                str(repo_root),
            )

            self.assertEqual(2, current.returncode)
            payload = json.loads(current.stdout)
            self.assertEqual(
                "ZSTT_CURRENT_NOT_FOUND",
                payload["error"]["code"],
            )
            self.assertEqual(
                "feature/other",
                payload["error"]["details"]["gitBranch"],
            )
            self.assertEqual(
                1,
                len(payload["error"]["details"]["unfinishedFeatures"]),
            )

    def test_list_reports_valid_features_without_changing_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            set_git_branch(repo_root, "feature/list")
            feature_dir = init_feature(repo_root)
            before = (feature_dir / "meta.json").read_bytes()

            listed = run_cli("list", "--repo-root", str(repo_root))

            self.assertEqual(0, listed.returncode, listed.stderr)
            payload = json.loads(listed.stdout)
            self.assertEqual("feature/list", payload["current_git_branch"])
            self.assertEqual(1, len(payload["features"]))
            self.assertFalse(payload["features"][0]["completed"])
            self.assertEqual([], payload["invalid_features"])
            self.assertEqual(before, (feature_dir / "meta.json").read_bytes())

    def test_current_blocks_when_any_feature_state_is_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            set_git_branch(repo_root, "feature/safe-current")
            init_feature(repo_root)
            broken = repo_root / ".zstt" / "quick" / "broken"
            broken.mkdir(parents=True)
            (broken / "meta.json").write_text(
                "{broken json",
                encoding="utf-8",
                newline="\n",
            )

            current = run_cli(
                "--json",
                "current",
                "--repo-root",
                str(repo_root),
            )

            self.assertEqual(2, current.returncode)
            payload = json.loads(current.stdout)
            self.assertEqual(
                "ZSTT_CURRENT_STATE_INVALID",
                payload["error"]["code"],
            )
            self.assertEqual(
                1,
                len(payload["error"]["details"]["invalidFeatures"]),
            )

    def test_legacy_feature_requires_explicit_branch_binding(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            set_git_branch(repo_root, "feature/legacy")
            feature_dir = init_feature(repo_root)
            meta_path = feature_dir / "meta.json"
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            meta.pop("git_branch")
            meta_path.write_text(
                json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
                newline="\n",
            )

            blocked = run_cli(
                "--json",
                "current",
                "--repo-root",
                str(repo_root),
            )
            self.assertEqual(2, blocked.returncode)
            self.assertEqual(
                "ZSTT_CURRENT_BRANCH_UNBOUND",
                json.loads(blocked.stdout)["error"]["code"],
            )

            bound = run_cli(
                "bind-branch",
                "--feature-dir",
                str(feature_dir),
                "--repo-root",
                str(repo_root),
            )
            self.assertEqual(0, bound.returncode, bound.stderr)
            self.assertEqual(
                "feature/legacy",
                json.loads(bound.stdout)["git_branch"],
            )
            current = run_cli("current", "--repo-root", str(repo_root))
            self.assertEqual(0, current.returncode, current.stderr)

    def test_bind_branch_rejects_non_feature_category(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            set_git_branch(repo_root, "feature/invalid-category")
            invalid = repo_root / ".zstt" / "other" / "feature"
            invalid.mkdir(parents=True)

            completed = run_cli(
                "--json",
                "bind-branch",
                "--feature-dir",
                str(invalid),
                "--repo-root",
                str(repo_root),
            )

            self.assertEqual(2, completed.returncode)
            self.assertEqual(
                "ZSTT_FEATURE_PATH_INVALID",
                json.loads(completed.stdout)["error"]["code"],
            )

    def test_init_full_creates_only_meta_and_requirement(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)

            completed = run_cli(
                "init",
                "--repo-root",
                str(repo_root),
                "--mode",
                "full",
                "--feature-name",
                "学习报告",
                "--date",
                "20260716",
            )

            self.assertEqual(0, completed.returncode, completed.stderr)
            feature_dir = repo_root / ".zstt" / "features" / "20260716-学习报告"
            self.assertEqual(
                {"meta.json", "00-requirement.md"},
                {path.name for path in feature_dir.iterdir()},
            )
            meta = json.loads((feature_dir / "meta.json").read_text(encoding="utf-8"))
            self.assertEqual(3, meta["version"])
            self.assertEqual("full", meta["mode"])
            self.assertEqual(
                ".zstt/features/20260716-学习报告",
                meta["feature_dir"],
            )
            self.assertEqual("requirement_clarification", meta["current_stage"])
            self.assertEqual([], meta["completed_stages"])
            self.assertEqual(
                "zstt-requirement-clarification",
                meta["recommended_next_skill"],
            )
            self.assertEqual(
                ["zstt-requirement-clarification"],
                meta["recommended_next_skills"],
            )

    def test_init_quick_uses_quick_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)

            completed = run_cli(
                "init",
                "--repo-root",
                str(repo_root),
                "--mode",
                "quick",
                "--feature-name",
                "修正文案",
                "--date",
                "20260716",
            )

            self.assertEqual(0, completed.returncode, completed.stderr)
            feature_dir = repo_root / ".zstt" / "quick" / "20260716-修正文案"
            requirement = (feature_dir / "00-requirement.md").read_text(encoding="utf-8")
            self.assertIn("mode: quick", requirement)

    def test_init_refuses_to_overwrite_existing_feature(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            args = (
                "init",
                "--repo-root",
                tmp,
                "--mode",
                "full",
                "--feature-name",
                "学习报告",
                "--date",
                "20260716",
            )
            self.assertEqual(0, run_cli(*args).returncode)

            second = run_cli(*args)

            self.assertNotEqual(0, second.returncode)
            self.assertIn("已存在", second.stderr)

    def test_json_error_has_stable_code_and_operation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / ".zstt" / "features" / "missing"

            completed = run_cli(
                "--json",
                "status",
                "--feature-dir",
                str(missing),
            )

            self.assertEqual(2, completed.returncode)
            payload = json.loads(completed.stdout)
            self.assertEqual("BLOCKED", payload["status"])
            self.assertEqual("status", payload["operation"])
            self.assertEqual("ZSTT_STATE_NOT_FOUND", payload["error"]["code"])
            self.assertEqual("", completed.stderr)

    def test_status_outputs_machine_readable_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_cli(
                "init",
                "--repo-root",
                tmp,
                "--mode",
                "full",
                "--feature-name",
                "学习报告",
                "--date",
                "20260716",
            )
            feature_dir = Path(tmp) / ".zstt" / "features" / "20260716-学习报告"

            completed = run_cli("status", "--feature-dir", str(feature_dir))

            self.assertEqual(0, completed.returncode, completed.stderr)
            status = json.loads(completed.stdout)
            self.assertEqual("full", status["mode"])
            self.assertEqual("00-requirement.md", status["artifacts"]["requirement_clarification"])

    def test_generated_text_has_no_utf8_bom(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_cli(
                "init",
                "--repo-root",
                tmp,
                "--mode",
                "full",
                "--feature-name",
                "学习报告",
                "--date",
                "20260716",
            )
            feature_dir = Path(tmp) / ".zstt" / "features" / "20260716-学习报告"
            for path in feature_dir.iterdir():
                self.assertFalse(path.read_bytes().startswith(b"\xef\xbb\xbf"), path.name)

    def test_v2_meta_is_migrated_to_relative_v3_on_next_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            feature_dir = init_feature(Path(tmp))
            meta_path = feature_dir / "meta.json"
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            meta["version"] = 2
            meta["feature_dir"] = str(feature_dir.resolve())
            meta.pop("recommended_next_skills")
            meta_path.write_text(
                json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
                newline="\n",
            )
            requirement = feature_dir / "00-requirement.md"
            fill_stage_document(requirement, "requirement_clarification")

            completed = run_cli(
                "complete-stage",
                "--feature-dir",
                str(feature_dir),
                "--stage",
                "requirement_clarification",
            )

            self.assertEqual(0, completed.returncode, completed.stderr)
            migrated = json.loads(meta_path.read_text(encoding="utf-8"))
            self.assertEqual(3, migrated["version"])
            self.assertEqual(
                ".zstt/features/20260716-学习报告",
                migrated["feature_dir"],
            )
            self.assertEqual(
                ["zstt-requirement-checklist", "zstt-repo-research"],
                migrated["recommended_next_skills"],
            )

    def test_unknown_meta_version_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            feature_dir = init_feature(Path(tmp))
            meta_path = feature_dir / "meta.json"
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            meta["version"] = 99
            meta_path.write_text(
                json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
                newline="\n",
            )

            status = run_cli("status", "--feature-dir", str(feature_dir))

            self.assertNotEqual(0, status.returncode)
            self.assertIn("不支持的 meta.json 版本", status.stderr)


class WorkflowCliGateTest(unittest.TestCase):
    def test_technical_design_without_sql_can_complete_after_impact_recorded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            feature_dir = prepare_technical_design(Path(tmp))

            gated = run_cli(
                "prepare-sql-gate",
                "--feature-dir",
                str(feature_dir),
                "--impact",
                "none",
            )
            completed = run_cli(
                "complete-stage",
                "--feature-dir",
                str(feature_dir),
                "--stage",
                "technical_design",
            )

            self.assertEqual(0, gated.returncode, gated.stderr)
            self.assertEqual(0, completed.returncode, completed.stderr)
            meta = json.loads((feature_dir / "meta.json").read_text(encoding="utf-8"))
            self.assertEqual("not_involved", meta["sql_gate"]["status"])

    def test_sql_change_requires_explicit_confirmation_before_completion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            feature_dir = prepare_technical_design(Path(tmp))
            auxiliary = feature_dir / "auxiliary"
            auxiliary.mkdir()
            (auxiliary / "sql-design.sql").write_text(
                "ALTER TABLE lesson_record ADD COLUMN source_type tinyint NOT NULL DEFAULT 0;\n",
                encoding="utf-8",
                newline="\n",
            )

            gated = run_cli(
                "prepare-sql-gate",
                "--feature-dir",
                str(feature_dir),
                "--impact",
                "ddl",
            )
            blocked = run_cli(
                "complete-stage",
                "--feature-dir",
                str(feature_dir),
                "--stage",
                "technical_design",
            )
            confirmed = run_cli(
                "confirm-sql",
                "--feature-dir",
                str(feature_dir),
                "--source",
                "Codex task: 用户明确回复确认以上 SQL",
            )
            completed = run_cli(
                "complete-stage",
                "--feature-dir",
                str(feature_dir),
                "--stage",
                "technical_design",
            )

            self.assertEqual(0, gated.returncode, gated.stderr)
            self.assertNotEqual(0, blocked.returncode)
            self.assertIn("SQL Gate", blocked.stderr)
            self.assertEqual(0, confirmed.returncode, confirmed.stderr)
            self.assertEqual(0, completed.returncode, completed.stderr)

    def test_confirm_sql_rejects_generic_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            feature_dir = prepare_technical_design(Path(tmp))
            auxiliary = feature_dir / "auxiliary"
            auxiliary.mkdir()
            (auxiliary / "sql-design.sql").write_text(
                "SELECT id FROM lesson_record WHERE student_id = ?;\n",
                encoding="utf-8",
                newline="\n",
            )
            self.assertEqual(
                0,
                run_cli(
                    "prepare-sql-gate",
                    "--feature-dir",
                    str(feature_dir),
                    "--impact",
                    "query_dml",
                ).returncode,
            )

            confirmed = run_cli(
                "confirm-sql",
                "--feature-dir",
                str(feature_dir),
                "--source",
                "用户确认",
            )

            self.assertNotEqual(0, confirmed.returncode)
            self.assertIn("可追溯", confirmed.stderr)

    def test_confirmed_sql_change_marks_gate_stale(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            feature_dir = prepare_technical_design(Path(tmp))
            auxiliary = feature_dir / "auxiliary"
            auxiliary.mkdir()
            sql_path = auxiliary / "sql-design.sql"
            sql_path.write_text(
                "SELECT id FROM lesson_record WHERE student_id = ?;\n",
                encoding="utf-8",
                newline="\n",
            )
            self.assertEqual(
                0,
                run_cli(
                    "prepare-sql-gate",
                    "--feature-dir",
                    str(feature_dir),
                    "--impact",
                    "query_dml",
                ).returncode,
            )
            self.assertEqual(
                0,
                run_cli(
                    "confirm-sql",
                    "--feature-dir",
                    str(feature_dir),
                    "--source",
                    "当前任务用户明确回复：确认以上查询 SQL",
                ).returncode,
            )
            sql_path.write_text(
                "SELECT id FROM lesson_record WHERE student_id = ? ORDER BY id DESC;\n",
                encoding="utf-8",
                newline="\n",
            )

            completed = run_cli(
                "complete-stage",
                "--feature-dir",
                str(feature_dir),
                "--stage",
                "technical_design",
            )

            self.assertNotEqual(0, completed.returncode)
            self.assertIn("必须重新确认", completed.stderr)
            meta = json.loads((feature_dir / "meta.json").read_text(encoding="utf-8"))
            self.assertEqual("stale", meta["sql_gate"]["status"])

    def test_empty_template_cannot_complete_by_changing_status_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            feature_dir = init_feature(Path(tmp))
            requirement = feature_dir / "00-requirement.md"
            replace_frontmatter_value(requirement, "status", "completed")

            completed = run_cli(
                "complete-stage",
                "--feature-dir",
                str(feature_dir),
                "--stage",
                "requirement_clarification",
            )

            self.assertNotEqual(0, completed.returncode)
            self.assertIn("缺少实质内容", completed.stderr)

    def test_full_research_requires_claim_and_evidence_ids(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            feature_dir = init_feature(Path(tmp))
            requirement = feature_dir / "00-requirement.md"
            fill_stage_document(requirement, "requirement_clarification")
            self.assertEqual(
                0,
                run_cli(
                    "complete-stage",
                    "--feature-dir",
                    str(feature_dir),
                    "--stage",
                    "requirement_clarification",
                ).returncode,
            )
            self.assertEqual(
                0,
                run_cli(
                    "prepare-stage",
                    "--feature-dir",
                    str(feature_dir),
                    "--stage",
                    "repo_research",
                ).returncode,
            )
            research = feature_dir / "01-research.md"
            fill_stage_document(research, "implementation")

            completed = run_cli(
                "complete-stage",
                "--feature-dir",
                str(feature_dir),
                "--stage",
                "repo_research",
            )

            self.assertNotEqual(0, completed.returncode)
            self.assertIn("C01", completed.stderr)
            self.assertIn("E01", completed.stderr)

    def test_status_reports_stale_stage_without_mutating_meta(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            feature_dir = init_feature(Path(tmp))
            requirement = feature_dir / "00-requirement.md"
            fill_stage_document(requirement, "requirement_clarification")
            self.assertEqual(
                0,
                run_cli(
                    "complete-stage",
                    "--feature-dir",
                    str(feature_dir),
                    "--stage",
                    "requirement_clarification",
                ).returncode,
            )
            requirement.write_text(
                requirement.read_text(encoding="utf-8") + "\n- 用户补充：扩大历史数据范围。\n",
                encoding="utf-8",
                newline="\n",
            )

            status = run_cli("status", "--feature-dir", str(feature_dir))

            self.assertEqual(0, status.returncode, status.stderr)
            self.assertEqual(
                ["requirement_clarification"],
                json.loads(status.stdout)["stale_stages"],
            )
            persisted = json.loads((feature_dir / "meta.json").read_text(encoding="utf-8"))
            self.assertEqual(["requirement_clarification"], persisted["completed_stages"])

    def test_complete_stage_requires_completed_status_and_required_headings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            feature_dir = init_feature(Path(tmp))
            requirement = feature_dir / "00-requirement.md"
            replace_frontmatter_value(requirement, "status", "completed")
            text = requirement.read_text(encoding="utf-8")
            requirement.write_text(
                text.replace("## 7. 验收标准\n", ""),
                encoding="utf-8",
                newline="\n",
            )

            completed = run_cli(
                "complete-stage",
                "--feature-dir",
                str(feature_dir),
                "--stage",
                "requirement_clarification",
            )

            self.assertNotEqual(0, completed.returncode)
            self.assertIn("缺少必需章节", completed.stderr)

    def test_p0_blocks_completion_without_advancing_meta(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            feature_dir = init_feature(Path(tmp))
            requirement = feature_dir / "00-requirement.md"
            replace_frontmatter_value(requirement, "status", "completed")
            replace_frontmatter_value(requirement, "blocking_p0_count", "1")

            completed = run_cli(
                "complete-stage",
                "--feature-dir",
                str(feature_dir),
                "--stage",
                "requirement_clarification",
            )

            self.assertNotEqual(0, completed.returncode)
            self.assertIn("P0", completed.stderr)
            meta = json.loads((feature_dir / "meta.json").read_text(encoding="utf-8"))
            self.assertEqual([], meta["completed_stages"])

    def test_complete_then_prepare_creates_only_requested_stage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            feature_dir = init_feature(Path(tmp))
            requirement = feature_dir / "00-requirement.md"
            fill_stage_document(requirement, "requirement_clarification")
            complete = run_cli(
                "complete-stage",
                "--feature-dir",
                str(feature_dir),
                "--stage",
                "requirement_clarification",
            )
            self.assertEqual(0, complete.returncode, complete.stderr)

            prepared = run_cli(
                "prepare-stage",
                "--feature-dir",
                str(feature_dir),
                "--stage",
                "repo_research",
            )

            self.assertEqual(0, prepared.returncode, prepared.stderr)
            self.assertTrue((feature_dir / "01-research.md").is_file())
            self.assertFalse((feature_dir / "02-design.md").exists())
            meta = json.loads((feature_dir / "meta.json").read_text(encoding="utf-8"))
            self.assertEqual("repo_research", meta["current_stage"])
            self.assertIn("requirement_clarification", meta["artifact_fingerprints"])

    def test_prepare_revalidates_user_modified_upstream(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            feature_dir = init_feature(Path(tmp))
            requirement = feature_dir / "00-requirement.md"
            fill_stage_document(requirement, "requirement_clarification")
            self.assertEqual(
                0,
                run_cli(
                    "complete-stage",
                    "--feature-dir",
                    str(feature_dir),
                    "--stage",
                    "requirement_clarification",
                ).returncode,
            )
            replace_frontmatter_value(requirement, "blocking_p0_count", "1")

            prepared = run_cli(
                "prepare-stage",
                "--feature-dir",
                str(feature_dir),
                "--stage",
                "repo_research",
            )

            self.assertNotEqual(0, prepared.returncode)
            self.assertIn("P0", prepared.stderr)
            self.assertFalse((feature_dir / "01-research.md").exists())

    def test_full_mode_cannot_skip_required_stages(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            feature_dir = init_feature(Path(tmp))

            prepared = run_cli(
                "prepare-stage",
                "--feature-dir",
                str(feature_dir),
                "--stage",
                "technical_design",
            )

            self.assertNotEqual(0, prepared.returncode)
            self.assertIn("前置阶段尚未完成", prepared.stderr)
            self.assertFalse((feature_dir / "02-design.md").exists())

    def test_quick_can_prepare_test_without_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            feature_dir = init_feature(Path(tmp), mode="quick")
            requirement = feature_dir / "00-requirement.md"
            fill_stage_document(requirement, "requirement_clarification")
            self.assertEqual(
                0,
                run_cli(
                    "complete-stage",
                    "--feature-dir",
                    str(feature_dir),
                    "--stage",
                    "requirement_clarification",
                ).returncode,
            )
            self.assertEqual(
                0,
                run_cli(
                    "prepare-stage",
                    "--feature-dir",
                    str(feature_dir),
                    "--stage",
                    "implementation",
                ).returncode,
            )
            implementation = feature_dir / "01-implementation.md"
            fill_stage_document(implementation, "implementation")
            self.assertEqual(
                0,
                run_cli(
                    "complete-stage",
                    "--feature-dir",
                    str(feature_dir),
                    "--stage",
                    "implementation",
                ).returncode,
            )

            prepared = run_cli(
                "prepare-stage",
                "--feature-dir",
                str(feature_dir),
                "--stage",
                "test_verify",
            )

            self.assertEqual(0, prepared.returncode, prepared.stderr)
            self.assertTrue((feature_dir / "03-test-report.md").is_file())
            self.assertFalse((feature_dir / "02-code-review.md").exists())

    def test_quick_exposes_both_optional_recommendations_after_implementation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            feature_dir = init_feature(Path(tmp), mode="quick")
            requirement = feature_dir / "00-requirement.md"
            fill_stage_document(requirement, "requirement_clarification")
            self.assertEqual(
                0,
                run_cli(
                    "complete-stage",
                    "--feature-dir",
                    str(feature_dir),
                    "--stage",
                    "requirement_clarification",
                ).returncode,
            )
            self.assertEqual(
                0,
                run_cli(
                    "prepare-stage",
                    "--feature-dir",
                    str(feature_dir),
                    "--stage",
                    "implementation",
                ).returncode,
            )
            implementation = feature_dir / "01-implementation.md"
            fill_stage_document(implementation, "implementation")

            completed = run_cli(
                "complete-stage",
                "--feature-dir",
                str(feature_dir),
                "--stage",
                "implementation",
            )

            self.assertEqual(0, completed.returncode, completed.stderr)
            meta = json.loads((feature_dir / "meta.json").read_text(encoding="utf-8"))
            self.assertEqual(
                ["zstt-code-review", "zstt-test-verify"],
                meta["recommended_next_skills"],
            )

    def test_quick_can_close_after_mandatory_stages_and_skip_optional_stages(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            set_git_branch(repo_root, "feature/quick-close")
            feature_dir = init_feature(repo_root, mode="quick")
            complete_quick_implementation(feature_dir)

            active = run_cli("current", "--repo-root", str(repo_root))
            self.assertEqual(0, active.returncode, active.stderr)

            closed = run_cli(
                "close",
                "--current",
                "--repo-root",
                str(repo_root),
            )
            self.assertEqual(0, closed.returncode, closed.stderr)
            payload = json.loads(closed.stdout)
            self.assertEqual("closed", payload["workflow_status"])
            self.assertEqual(
                ["code_review", "test_verify"],
                payload["skipped_stages"],
            )
            self.assertEqual([], payload["recommended_next_skills"])

            current = run_cli(
                "--json",
                "current",
                "--repo-root",
                str(repo_root),
            )
            self.assertEqual(2, current.returncode)
            self.assertEqual(
                "ZSTT_CURRENT_NOT_FOUND",
                json.loads(current.stdout)["error"]["code"],
            )

    def test_changed_artifact_reopens_a_closed_feature_for_current(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            set_git_branch(repo_root, "feature/stale")
            feature_dir = init_feature(repo_root, mode="quick")
            complete_quick_implementation(feature_dir)
            closed = run_cli(
                "close",
                "--feature-dir",
                str(feature_dir),
            )
            self.assertEqual(0, closed.returncode, closed.stderr)

            implementation = feature_dir / "01-implementation.md"
            implementation.write_text(
                implementation.read_text(encoding="utf-8")
                + "\n- 用户修改：需要重新确认\n",
                encoding="utf-8",
                newline="\n",
            )

            listed = run_cli("list", "--repo-root", str(repo_root))
            self.assertEqual(0, listed.returncode, listed.stderr)
            summary = json.loads(listed.stdout)["features"][0]
            self.assertFalse(summary["completed"])
            self.assertEqual(["implementation"], summary["stale_stages"])

            current = run_cli("current", "--repo-root", str(repo_root))
            self.assertEqual(0, current.returncode, current.stderr)
            self.assertEqual(
                str(feature_dir.resolve()),
                json.loads(current.stdout)["feature"]["absolute_path"],
            )


class RequirementResearchTraceabilityGateTest(unittest.TestCase):
    def test_requirement_rejects_unknown_source_reference(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            feature_dir = init_feature(Path(tmp))
            requirement = feature_dir / "00-requirement.md"
            fill_stage_document(requirement, "requirement_clarification")
            requirement.write_text(
                requirement.read_text(encoding="utf-8").replace(
                    "| R01 | 功能 | 管理员可以导出学习报告 | S01 |",
                    "| R01 | 功能 | 管理员可以导出学习报告 | S99 |",
                    1,
                ),
                encoding="utf-8",
                newline="\n",
            )

            completed = run_cli(
                "complete-stage",
                "--feature-dir",
                str(feature_dir),
                "--stage",
                "requirement_clarification",
            )

            self.assertNotEqual(0, completed.returncode)
            self.assertIn("引用了不存在的来源: S99", completed.stderr)

    def test_requirement_rejects_missing_acceptance_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            feature_dir = init_feature(Path(tmp))
            requirement = feature_dir / "00-requirement.md"
            fill_stage_document(requirement, "requirement_clarification")
            lines = [
                line
                for line in requirement.read_text(encoding="utf-8").splitlines()
                if not line.startswith("| R01 | 主路径 |")
            ]
            requirement.write_text(
                "\n".join(lines) + "\n",
                encoding="utf-8",
                newline="\n",
            )

            completed = run_cli(
                "complete-stage",
                "--feature-dir",
                str(feature_dir),
                "--stage",
                "requirement_clarification",
            )

            self.assertNotEqual(0, completed.returncode)
            self.assertIn("验收遗漏需求: R01", completed.stderr)

    def test_requirement_counts_open_questions_from_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            feature_dir = init_feature(Path(tmp))
            requirement = feature_dir / "00-requirement.md"
            fill_stage_document(requirement, "requirement_clarification")
            text = insert_markdown_row(
                requirement.read_text(encoding="utf-8"),
                "| 问题 ID | 优先级 | 问题类型 | 疑问 | 准确来源 Sxx | 影响 Rxx/章节 | 确认人/承接阶段 | 确认结论/转交说明 | 状态 |",
                "| Q01 | P1 | 用户意图 | 导出格式是什么 | S01 | R01 | 用户 |  | 待确认 |",
            )
            requirement.write_text(text, encoding="utf-8", newline="\n")

            completed = run_cli(
                "complete-stage",
                "--feature-dir",
                str(feature_dir),
                "--stage",
                "requirement_clarification",
            )

            self.assertNotEqual(0, completed.returncode)
            self.assertIn("open_p1_count=0", completed.stderr)
            self.assertIn("Qxx 台账实际为 1", completed.stderr)

    def test_requirement_requires_final_confirmation_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            feature_dir = init_feature(Path(tmp))
            requirement = feature_dir / "00-requirement.md"
            fill_stage_document(requirement, "requirement_clarification")
            replace_frontmatter_value(requirement, "confirmation_status", "pending")
            replace_frontmatter_value(requirement, "confirmation_source", '""')

            completed = run_cli(
                "complete-stage",
                "--feature-dir",
                str(feature_dir),
                "--stage",
                "requirement_clarification",
            )

            self.assertNotEqual(0, completed.returncode)
            self.assertIn("未完成最终反向确认", completed.stderr)
            self.assertIn("缺少可回查的最终确认来源", completed.stderr)

    def test_research_requires_exact_requirement_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            feature_dir = prepare_research_document(Path(tmp))
            research = feature_dir / "01-research.md"
            research.write_text(
                research.read_text(encoding="utf-8").replace(
                    "| R01 | 管理员导出学习报告 | 当前代码入口和数据源是什么 |",
                    "| R02 | 管理员导出学习报告 | 当前代码入口和数据源是什么 |",
                    1,
                ),
                encoding="utf-8",
                newline="\n",
            )

            completed = run_cli(
                "complete-stage",
                "--feature-dir",
                str(feature_dir),
                "--stage",
                "repo_research",
            )

            self.assertNotEqual(0, completed.returncode)
            self.assertIn("需求验证遗漏: R01", completed.stderr)
            self.assertIn("需求验证引用未知需求: R02", completed.stderr)

    def test_research_rejects_duplicate_claim_and_invalid_local_line(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            feature_dir = prepare_research_document(Path(tmp))
            research = feature_dir / "01-research.md"
            text = insert_markdown_row(
                research.read_text(encoding="utf-8"),
                "| 结论 ID | 结论 | 证据 ID | 证据等级 | 代码位置 | 反证 | 覆盖度 | 置信度 | 运行时缺口 | 待验证动作 |",
                "| C01 | 重复结论 | E01 | Proven | src/ReportService.java:99 | 未发现 | 已覆盖 R01 | 高 | 无 | 无 |",
            ).replace(
                "| E01 | 本地源码 | test-repo | src/ReportService.java | 1 |",
                "| E01 | 本地源码 | test-repo | src/ReportService.java | 99 |",
                1,
            )
            research.write_text(text, encoding="utf-8", newline="\n")

            completed = run_cli(
                "complete-stage",
                "--feature-dir",
                str(feature_dir),
                "--stage",
                "repo_research",
            )

            self.assertNotEqual(0, completed.returncode)
            self.assertIn("结论 ID 重复: C01", completed.stderr)
            self.assertIn("E01 行号越界", completed.stderr)

    def test_research_requires_semantic_and_sql_detail_when_involved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            feature_dir = prepare_research_document(Path(tmp))
            research = feature_dir / "01-research.md"
            replace_frontmatter_value(research, "shared_semantic_impact", "involved")
            replace_frontmatter_value(research, "current_sql_impact", "involved")

            completed = run_cli(
                "complete-stage",
                "--feature-dir",
                str(feature_dir),
                "--stage",
                "repo_research",
            )

            self.assertNotEqual(0, completed.returncode)
            self.assertIn(
                "shared_semantic_impact=involved 但影响矩阵为空",
                completed.stderr,
            )
            self.assertIn(
                "current_sql_impact=involved 但影响矩阵为空",
                completed.stderr,
            )

    def test_research_accepts_complete_semantic_and_sql_matrices(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            feature_dir = prepare_research_document(Path(tmp))
            research = feature_dir / "01-research.md"
            text = research.read_text(encoding="utf-8").replace(
                "shared_semantic_impact: none",
                "shared_semantic_impact: involved",
                1,
            ).replace(
                "current_sql_impact: none",
                "current_sql_impact: involved",
                1,
            )
            text = insert_markdown_row(
                text,
                "| 语义对象 | 类型 | 生产方 | 持久化/传播 | 消费方 | 消费逻辑/历史值兼容 | 结论 ID | 证据 ID | 风险/RQxx |",
                "| 任务状态 | 枚举/类型码 | TaskService | 数据库/RPC/MQ | TaskJob | status=2 按历史语义读取 | C01 | E01 | 无 |",
            )
            text = insert_markdown_row(
                text,
                "| SQL 事实 ID | 仓库与位置 | 类型 | 当前语义 | JOIN/过滤/排序/分页/写入条件 | 可能受影响原因 | 结论 ID | 证据 ID | 是否交技术设计 |",
                "| SQL01 | src/Test.java:1 | SELECT | 查询可处理任务 | status IN (1,2) | status=2 语义变化 | C01 | E01 | 是 |",
            )
            research.write_text(text, encoding="utf-8", newline="\n")

            completed = run_cli(
                "complete-stage",
                "--feature-dir",
                str(feature_dir),
                "--stage",
                "repo_research",
            )

            self.assertEqual(0, completed.returncode, completed.stderr)

    def test_research_requires_change_scope_for_every_repository(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            feature_dir = prepare_research_document(Path(tmp))
            research = feature_dir / "01-research.md"
            research.write_text(
                research.read_text(encoding="utf-8").replace(
                    "| test-repo | 导出入口 | 保持现有契约 |",
                    "| other-repo | 导出入口 | 保持现有契约 |",
                    1,
                ),
                encoding="utf-8",
                newline="\n",
            )

            completed = run_cli(
                "complete-stage",
                "--feature-dir",
                str(feature_dir),
                "--stage",
                "repo_research",
            )

            self.assertNotEqual(0, completed.returncode)
            self.assertIn("缺少每仓 ChangeScope: test-repo", completed.stderr)
            self.assertIn("ChangeScope 引用未知仓库: other-repo", completed.stderr)

    def test_research_must_accept_transferred_code_fact_question(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            feature_dir = init_feature(Path(tmp))
            requirement = feature_dir / "00-requirement.md"
            fill_stage_document(requirement, "requirement_clarification")
            requirement.write_text(
                insert_markdown_row(
                    requirement.read_text(encoding="utf-8"),
                    "| 问题 ID | 优先级 | 问题类型 | 疑问 | 准确来源 Sxx | 影响 Rxx/章节 | 确认人/承接阶段 | 确认结论/转交说明 | 状态 |",
                    "| Q01 | P1 | 代码事实 | 当前导出查询在哪里 | S01 | R01 | 仓库调研 | 追踪最终 Mapper | 转下游 |",
                ),
                encoding="utf-8",
                newline="\n",
            )
            self.assertEqual(
                0,
                run_cli(
                    "complete-stage",
                    "--feature-dir",
                    str(feature_dir),
                    "--stage",
                    "requirement_clarification",
                ).returncode,
            )
            self.assertEqual(
                0,
                run_cli(
                    "prepare-stage",
                    "--feature-dir",
                    str(feature_dir),
                    "--stage",
                    "repo_research",
                ).returncode,
            )
            fill_stage_document(feature_dir / "01-research.md", "repo_research")

            completed = run_cli(
                "complete-stage",
                "--feature-dir",
                str(feature_dir),
                "--stage",
                "repo_research",
            )

            self.assertNotEqual(0, completed.returncode)
            self.assertIn(
                "未承接需求阶段转交的代码事实问题: Q01",
                completed.stderr,
            )


class DesignTaskSchemaGateTest(unittest.TestCase):
    def test_design_schema_rejects_unrouted_claim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            feature_dir = prepare_technical_design(Path(tmp))
            self.assertEqual(
                0,
                run_cli(
                    "prepare-sql-gate",
                    "--feature-dir",
                    str(feature_dir),
                    "--impact",
                    "none",
                ).returncode,
            )
            design = feature_dir / "02-design.md"
            text = design.read_text(encoding="utf-8").replace(
                "| C01 | 进入设计 | D01 |\n",
                "",
            )
            design.write_text(text, encoding="utf-8", newline="\n")

            completed = run_cli(
                "complete-stage",
                "--feature-dir",
                str(feature_dir),
                "--stage",
                "technical_design",
            )

            self.assertNotEqual(0, completed.returncode)
            self.assertIn("设计输入去向遗漏", completed.stderr)

    def test_design_schema_rejects_rejected_core_change(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            feature_dir = prepare_technical_design(Path(tmp))
            self.assertEqual(
                0,
                run_cli(
                    "prepare-sql-gate",
                    "--feature-dir",
                    str(feature_dir),
                    "--impact",
                    "none",
                ).returncode,
            )
            design = feature_dir / "02-design.md"
            text = design.read_text(encoding="utf-8").replace(
                "| C01 | 已确认 | 采用 |",
                "| C01 | 已确认 | 不采用 |",
                1,
            )
            design.write_text(text, encoding="utf-8", newline="\n")

            completed = run_cli(
                "complete-stage",
                "--feature-dir",
                str(feature_dir),
                "--stage",
                "technical_design",
            )

            self.assertNotEqual(0, completed.returncode)
            self.assertIn("必须是已确认且结论为采用", completed.stderr)

    def test_design_schema_rejects_contract_detail_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            feature_dir = prepare_technical_design(Path(tmp))
            self.assertEqual(
                0,
                run_cli(
                    "prepare-sql-gate",
                    "--feature-dir",
                    str(feature_dir),
                    "--impact",
                    "none",
                ).returncode,
            )
            design = feature_dir / "02-design.md"
            text = design.read_text(encoding="utf-8").replace(
                "无需：简单内部接口",
                "auxiliary/interface-details/export.md",
                1,
            )
            design.write_text(text, encoding="utf-8", newline="\n")
            detail = feature_dir / "auxiliary" / "interface-details" / "export.md"
            detail.parent.mkdir(parents=True, exist_ok=True)
            detail.write_text(
                """<!-- ZSTT_CONTRACT_DETAIL_VERSION: 1 -->
# 契约明细：学习报告导出
- 来源 Dxx：D01
- 来源 Cxx：C01
- 调用方/触发事件：管理员点击导出
- 契约类型：HTTP
- 契约标识：GET /reports/export
- 输入关键字段：reportType
- 后端推导字段/来源：operatorId=登录上下文
- 禁止外部传字段：operatorId
- 输出字段：wrongField
- 副作用：无：只读导出
- 权限/幂等/兼容：沿用管理员鉴权，保持旧响应兼容
""",
                encoding="utf-8",
                newline="\n",
            )

            completed = run_cli(
                "complete-stage",
                "--feature-dir",
                str(feature_dir),
                "--stage",
                "technical_design",
            )

            self.assertNotEqual(0, completed.returncode)
            self.assertIn("输出字段与 02-design.md 不一致", completed.stderr)

    def test_task_schema_rejects_claim_only_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            feature_dir = prepare_task_breakdown(Path(tmp))
            tasks = feature_dir / "03-tasks.md"
            text = tasks.read_text(encoding="utf-8").replace(
                "- 来源依据：D01 / C01",
                "- 来源依据：C01",
                1,
            )
            tasks.write_text(text, encoding="utf-8", newline="\n")

            completed = run_cli(
                "complete-stage",
                "--feature-dir",
                str(feature_dir),
                "--stage",
                "task_breakdown",
            )

            self.assertNotEqual(0, completed.returncode)
            self.assertIn("来源必须引用核心 Dxx", completed.stderr)

    def test_task_schema_rejects_missing_dependency(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            feature_dir = prepare_task_breakdown(Path(tmp))
            tasks = feature_dir / "03-tasks.md"
            text = tasks.read_text(encoding="utf-8").replace(
                "| T01 | 实现完整学习报告导出 | test-repo | ready | - |",
                "| T01 | 实现完整学习报告导出 | test-repo | pending | T09 |",
                1,
            )
            text = insert_markdown_row(
                text,
                "| 前置任务 | 后续任务 | 依赖原因 | 契约/Schema/配置耦合 |",
                "| T09 | T01 | 等待不存在的前置输出 | 无：测试非法依赖 |",
            ).replace(
                "- 当前可执行集合：T01",
                "- 当前可执行集合：无",
            ).replace(
                "- 禁止提前执行集合：无",
                "- 禁止提前执行集合：T01",
            ).replace(
                "- 当前可执行任务：T01",
                "- 当前可执行任务：无",
            ).replace(
                "- 当前禁止执行任务：无",
                "- 当前禁止执行任务：T01",
            )
            tasks.write_text(text, encoding="utf-8", newline="\n")

            completed = run_cli(
                "complete-stage",
                "--feature-dir",
                str(feature_dir),
                "--stage",
                "task_breakdown",
            )

            self.assertNotEqual(0, completed.returncode)
            self.assertIn("依赖不存在的任务: T09", completed.stderr)

    def test_task_schema_rejects_non_code_task(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            feature_dir = prepare_task_breakdown(Path(tmp))
            tasks = feature_dir / "03-tasks.md"
            text = tasks.read_text(encoding="utf-8").replace(
                "实现完整学习报告导出",
                "执行回归测试",
                1,
            )
            tasks.write_text(text, encoding="utf-8", newline="\n")

            completed = run_cli(
                "complete-stage",
                "--feature-dir",
                str(feature_dir),
                "--stage",
                "task_breakdown",
            )

            self.assertNotEqual(0, completed.returncode)
            self.assertIn("不是仓库编码任务", completed.stderr)

    def test_task_schema_rejects_unapproved_test_code(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            feature_dir = prepare_task_breakdown(Path(tmp))
            tasks = feature_dir / "03-tasks.md"
            text = tasks.read_text(encoding="utf-8").replace(
                "- 测试代码：默认不新增",
                "- 测试代码：新增 ExportServiceTest",
                1,
            )
            tasks.write_text(text, encoding="utf-8", newline="\n")

            completed = run_cli(
                "complete-stage",
                "--feature-dir",
                str(feature_dir),
                "--stage",
                "task_breakdown",
            )

            self.assertNotEqual(0, completed.returncode)
            self.assertIn("必须声明默认不新增、设计要求或用户明确要求", completed.stderr)

    def test_task_schema_rejects_l2_overlapping_write_sets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            feature_dir = prepare_task_breakdown(Path(tmp))
            tasks = feature_dir / "03-tasks.md"
            text = tasks.read_text(encoding="utf-8").replace(
                "- 并行等级（L0/L1/L2）：L0",
                "- 并行等级（L0/L1/L2）：L2",
                1,
            )
            text = insert_markdown_row(
                text,
                "| 执行者 | 任务 | 允许修改 | 禁止修改 | 只读参考 | 依赖 | 合并顺序 | 验证命令 | 预期信号 |",
                "| agent-a | T01 | src/ReportService.java | 其他任务写集 | 02-design.md | - | 1 | python -m unittest tests.test_workflow_cli | 退出码为 0 |",
            )
            text = insert_markdown_row(
                text,
                "| 执行者 | 任务 | 允许修改 | 禁止修改 | 只读参考 | 依赖 | 合并顺序 | 验证命令 | 预期信号 |",
                "| agent-b | T01 | src/ReportService.java | 其他任务写集 | 02-design.md | - | 2 | python -m unittest tests.test_workflow_cli | 退出码为 0 |",
            )
            tasks.write_text(text, encoding="utf-8", newline="\n")

            completed = run_cli(
                "complete-stage",
                "--feature-dir",
                str(feature_dir),
                "--stage",
                "task_breakdown",
            )

            self.assertNotEqual(0, completed.returncode)
            self.assertIn("L2 写集重叠", completed.stderr)


if __name__ == "__main__":
    unittest.main()
