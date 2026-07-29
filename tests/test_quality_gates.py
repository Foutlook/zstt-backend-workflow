from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tests.test_workflow_cli import (
    fill_stage_document,
    init_feature,
    prepare_task_breakdown,
    replace_frontmatter_value,
    run_cli,
)


def prepare_gate(feature_dir: Path, gate: str) -> Path:
    completed = run_cli(
        "prepare-quality-gate",
        "--feature-dir",
        str(feature_dir),
        "--gate",
        gate,
    )
    if completed.returncode != 0:
        raise AssertionError(completed.stderr)
    return Path(json.loads(completed.stdout)["path"])


def fill_requirement_gate(path: Path, open_severity: str | None = None) -> None:
    text = path.read_text(encoding="utf-8")
    if open_severity:
        item = (
            f"- [ ] CHK001 [{open_severity}] 是否定义重复提交的业务身份键？"
            "[Gap, R01] — 证据：R01 只定义重复结果，未定义身份键"
        )
        status = "blocked" if open_severity == "P0" else "conditional"
    else:
        item = (
            "- [x] CHK001 [P1] R01 是否定义可观察的验收结果？"
            "[Clarity, R01] — 证据：R01 已定义导出文件可下载"
        )
        status = "passed"
    text = text.replace("## Checklist\n", f"## Checklist\n\n{item}\n", 1)
    path.write_text(text, encoding="utf-8", newline="\n")
    replace_frontmatter_value(path, "ruleset_version", '"test-v1"')
    replace_frontmatter_value(path, "ruleset_fingerprint", '"rules-sha256"')
    replace_frontmatter_value(path, "status", status)
    replace_frontmatter_value(
        path,
        "blocking_p0_count",
        "1" if open_severity == "P0" else "0",
    )
    replace_frontmatter_value(
        path,
        "open_p1_count",
        "1" if open_severity == "P1" else "0",
    )
    replace_frontmatter_value(
        path,
        "open_p2_count",
        "1" if open_severity == "P2" else "0",
    )


def fill_artifact_gate(path: Path, open_severity: str | None = None) -> None:
    text = path.read_text(encoding="utf-8")
    if open_severity:
        header = "|---|---|---|---|---|---|---|"
        finding = (
            f"| COV-001 | {open_severity} | 覆盖 | R01/D01/T01 | "
            "R01 -> C01 -> D01 -> T01 | 任务缺少验收信号 | 03-tasks.md |"
        )
        text = text.replace(header, f"{header}\n{finding}", 1)
        status = "blocked" if open_severity == "P0" else "conditional"
    else:
        status = "passed"
    path.write_text(text, encoding="utf-8", newline="\n")
    replace_frontmatter_value(path, "ruleset_version", '"test-v1"')
    replace_frontmatter_value(path, "ruleset_fingerprint", '"rules-sha256"')
    replace_frontmatter_value(path, "status", status)
    replace_frontmatter_value(
        path,
        "blocking_p0_count",
        "1" if open_severity == "P0" else "0",
    )
    replace_frontmatter_value(
        path,
        "open_p1_count",
        "1" if open_severity == "P1" else "0",
    )
    replace_frontmatter_value(
        path,
        "open_p2_count",
        "1" if open_severity == "P2" else "0",
    )


class QualityGateWorkflowTest(unittest.TestCase):
    def complete_requirement(self, feature_dir: Path) -> None:
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

    def test_status_discovers_skipped_gates_without_meta_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            full = init_feature(Path(tmp) / "full", mode="full")
            quick = init_feature(Path(tmp) / "quick", mode="quick")

            full_status = run_cli("status", "--feature-dir", str(full))
            quick_status = run_cli("status", "--feature-dir", str(quick))

            self.assertEqual(0, full_status.returncode, full_status.stderr)
            self.assertEqual(0, quick_status.returncode, quick_status.stderr)
            self.assertEqual(
                {
                    "requirement_checklist": "skipped",
                    "artifact_analysis": "skipped",
                },
                {
                    key: value["state"]
                    for key, value in json.loads(full_status.stdout)[
                        "quality_gates"
                    ].items()
                },
            )
            self.assertEqual(
                "skipped",
                json.loads(quick_status.stdout)["quality_gates"][
                    "requirement_checklist"
                ]["state"],
            )
            self.assertNotIn(
                "artifact_analysis",
                json.loads(quick_status.stdout)["quality_gates"],
            )

    def test_passed_requirement_gate_allows_full_research(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            feature_dir = init_feature(Path(tmp), mode="full")
            self.complete_requirement(feature_dir)
            report = prepare_gate(feature_dir, "requirement_checklist")
            fill_requirement_gate(report)

            validated = run_cli(
                "validate-quality-gate",
                "--feature-dir",
                str(feature_dir),
                "--gate",
                "requirement_checklist",
            )
            prepared = run_cli(
                "prepare-stage",
                "--feature-dir",
                str(feature_dir),
                "--stage",
                "repo_research",
            )

            self.assertEqual(0, validated.returncode, validated.stderr)
            self.assertEqual("passed", json.loads(validated.stdout)["state"])
            self.assertEqual(0, prepared.returncode, prepared.stderr)

    def test_existing_p0_requirement_gate_blocks_but_missing_gate_skips(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skipped_feature = init_feature(Path(tmp) / "skipped", mode="full")
            self.complete_requirement(skipped_feature)
            skipped = run_cli(
                "prepare-stage",
                "--feature-dir",
                str(skipped_feature),
                "--stage",
                "repo_research",
            )
            self.assertEqual(0, skipped.returncode, skipped.stderr)

            blocked_feature = init_feature(Path(tmp) / "blocked", mode="full")
            self.complete_requirement(blocked_feature)
            report = prepare_gate(blocked_feature, "requirement_checklist")
            fill_requirement_gate(report, "P0")
            blocked = run_cli(
                "--json",
                "prepare-stage",
                "--feature-dir",
                str(blocked_feature),
                "--stage",
                "repo_research",
            )

            self.assertEqual(2, blocked.returncode)
            payload = json.loads(blocked.stdout)
            self.assertEqual(
                "ZSTT_QUALITY_GATE_BLOCKED",
                payload["error"]["code"],
            )
            self.assertEqual(
                "blocked",
                payload["error"]["details"]["summary"]["state"],
            )

    def test_conditional_quick_gate_allows_original_implementation_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            feature_dir = init_feature(Path(tmp), mode="quick")
            self.complete_requirement(feature_dir)
            report = prepare_gate(feature_dir, "requirement_checklist")
            fill_requirement_gate(report, "P1")

            prepared = run_cli(
                "prepare-stage",
                "--feature-dir",
                str(feature_dir),
                "--stage",
                "implementation",
            )

            self.assertEqual(0, prepared.returncode, prepared.stderr)
            meta = json.loads((feature_dir / "meta.json").read_text(encoding="utf-8"))
            self.assertEqual(
                "conditional",
                meta["last_validation"]["quality_gates"][
                    "requirement_checklist"
                ]["state"],
            )

    def test_changed_input_marks_persistent_report_stale(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            feature_dir = init_feature(Path(tmp), mode="full")
            report = prepare_gate(feature_dir, "requirement_checklist")
            fill_requirement_gate(report)
            with (feature_dir / "00-requirement.md").open(
                "a",
                encoding="utf-8",
                newline="\n",
            ) as stream:
                stream.write("\n新增需求事实\n")

            status = run_cli("status", "--feature-dir", str(feature_dir))

            self.assertEqual(0, status.returncode, status.stderr)
            summary = json.loads(status.stdout)["quality_gates"][
                "requirement_checklist"
            ]
            self.assertEqual("stale", summary["state"])
            self.assertIn("输入指纹已过期", "\n".join(summary["errors"]))

    def test_persistent_artifact_analysis_is_consumed_before_implementation(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            feature_dir = prepare_task_breakdown(Path(tmp))
            completed = run_cli(
                "complete-stage",
                "--feature-dir",
                str(feature_dir),
                "--stage",
                "task_breakdown",
            )
            self.assertEqual(0, completed.returncode, completed.stderr)
            report = prepare_gate(feature_dir, "artifact_analysis")
            fill_artifact_gate(report)

            validated = run_cli(
                "validate-quality-gate",
                "--feature-dir",
                str(feature_dir),
                "--gate",
                "artifact_analysis",
            )
            prepared = run_cli(
                "prepare-stage",
                "--feature-dir",
                str(feature_dir),
                "--stage",
                "implementation",
            )

            self.assertEqual(0, validated.returncode, validated.stderr)
            self.assertEqual(0, prepared.returncode, prepared.stderr)
            self.assertTrue((feature_dir / "04-implementation.md").is_file())


if __name__ == "__main__":
    unittest.main()
