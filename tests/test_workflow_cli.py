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
    traceability = {
        "repo_research": "\n- C01：测试结论，证据为 E01，位置为 src/Test.java:1。\n- E01：源码静态证据。\n",
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


class WorkflowCliInitTest(unittest.TestCase):
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
                ["zstt-repo-research"],
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


if __name__ == "__main__":
    unittest.main()
