from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "src" / "zstt_cli" / "resources" / "runtime"
TEMPLATES = ROOT / "src" / "zstt_cli" / "resources" / "templates"
sys.path.insert(0, str(RUNTIME))

from implementation_evidence import (  # noqa: E402
    IMPLEMENTATION_EVIDENCE_PATH,
    ensure_implementation_baseline,
    finalize_implementation_evidence,
    run_and_record_validation,
)
from workflow_validation import headings_for_document  # noqa: E402


class ImplementationEvidenceTest(unittest.TestCase):
    def _git(self, repo_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", "-C", str(repo_root), *args],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

    def _init_repo(self, repo_root: Path) -> None:
        self.assertEqual(0, self._git(repo_root, "init", "--quiet").returncode)
        self.assertEqual(
            0,
            self._git(repo_root, "config", "user.name", "ZSTT Test").returncode,
        )
        self.assertEqual(
            0,
            self._git(
                repo_root,
                "config",
                "user.email",
                "zstt-test@example.invalid",
            ).returncode,
        )
        (repo_root / "service.txt").write_text(
            "baseline\n",
            encoding="utf-8",
            newline="\n",
        )
        self.assertEqual(0, self._git(repo_root, "add", "service.txt").returncode)
        self.assertEqual(
            0,
            self._git(repo_root, "commit", "--quiet", "-m", "baseline").returncode,
        )

    def _feature(self, repo_root: Path) -> tuple[Path, Path]:
        feature_dir = repo_root / ".zstt" / "quick" / "20260729-quick"
        feature_dir.mkdir(parents=True)
        implementation = feature_dir / "01-implementation.md"
        implementation.write_text(
            (
                TEMPLATES / "quick" / "01-implementation.md"
            ).read_text(encoding="utf-8").replace("{{FEATURE_NAME}}", "quick"),
            encoding="utf-8",
            newline="\n",
        )
        return feature_dir, implementation

    def test_git_snapshots_distinguish_new_and_preexisting_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            self._init_repo(repo_root)
            feature_dir, implementation = self._feature(repo_root)
            service = repo_root / "service.txt"
            service.write_text(
                "baseline\nuser change\n",
                encoding="utf-8",
                newline="\n",
            )

            baseline = ensure_implementation_baseline(
                feature_dir,
                implementation,
            )
            baseline_entries = {
                entry["path"]
                for entry in baseline["baseline"]["entries"]
            }
            self.assertEqual({"service.txt"}, baseline_entries)

            service.write_text(
                "baseline\nuser change\nsession change\n",
                encoding="utf-8",
                newline="\n",
            )
            (repo_root / "new-file.txt").write_text(
                "session file\n",
                encoding="utf-8",
                newline="\n",
            )
            final = finalize_implementation_evidence(
                feature_dir,
                implementation,
            )

            self.assertEqual(
                ["service.txt"],
                final["changeSummary"]["changedFromBaseline"],
            )
            self.assertEqual(
                ["new-file.txt"],
                final["changeSummary"]["newlyChanged"],
            )
            self.assertNotIn(
                ".zstt/quick/20260729-quick/01-implementation.md",
                {
                    entry["path"]
                    for entry in final["final"]["entries"]
                },
            )
            rendered = implementation.read_text(encoding="utf-8")
            self.assertIn("`service.txt`", rendered)
            self.assertIn("`new-file.txt`", rendered)
            first_fingerprint = final["final"]["fingerprint"]

            self.assertEqual(
                0,
                self._git(repo_root, "add", "service.txt", "new-file.txt").returncode,
            )
            self.assertEqual(
                0,
                self._git(repo_root, "commit", "--quiet", "-m", "implementation").returncode,
            )
            committed = finalize_implementation_evidence(
                feature_dir,
                implementation,
            )
            self.assertEqual(first_fingerprint, committed["final"]["fingerprint"])
            self.assertEqual(
                ["service.txt"],
                committed["changeSummary"]["changedFromBaseline"],
            )
            self.assertEqual(
                ["new-file.txt"],
                committed["changeSummary"]["newlyChanged"],
            )

    def test_validation_runner_records_exit_code_and_redacts_secrets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            self._init_repo(repo_root)
            feature_dir, implementation = self._feature(repo_root)

            exit_code = run_and_record_validation(
                feature_dir,
                implementation,
                [
                    sys.executable,
                    "-c",
                    "raise SystemExit(0)",
                    "--token=do-not-store",
                    "Authorization: Bearer also-do-not-store",
                    "/password:still-do-not-store",
                ],
            )

            self.assertEqual(0, exit_code)
            payload = json.loads(
                (feature_dir / IMPLEMENTATION_EVIDENCE_PATH).read_text(
                    encoding="utf-8"
                )
            )
            validation = payload["validations"][0]
            self.assertEqual(0, validation["exitCode"])
            self.assertIn("--token=<redacted>", validation["command"])
            self.assertIn("<redacted-header>", validation["command"])
            self.assertIn("/password:<redacted>", validation["command"])
            self.assertNotIn("do-not-store", json.dumps(payload))
            self.assertIn(
                "V01",
                implementation.read_text(encoding="utf-8"),
            )
            (repo_root / "service.txt").write_text(
                "baseline\nchanged after validation\n",
                encoding="utf-8",
                newline="\n",
            )
            finalized = finalize_implementation_evidence(
                feature_dir,
                implementation,
            )
            self.assertEqual(
                1,
                finalized["validationSummary"]["stalePassed"],
            )
            self.assertIn(
                "快照已过期",
                implementation.read_text(encoding="utf-8"),
            )

    def test_rerunning_same_command_supersedes_failure_on_same_snapshot(self) -> None:
        with (
            tempfile.TemporaryDirectory() as tmp,
            tempfile.TemporaryDirectory() as external_tmp,
        ):
            repo_root = Path(tmp)
            self._init_repo(repo_root)
            feature_dir, implementation = self._feature(repo_root)
            external_flag = Path(external_tmp) / "ready"
            command = [
                sys.executable,
                "-c",
                (
                    "import pathlib,sys;"
                    f"sys.exit(0 if pathlib.Path({str(external_flag)!r}).exists() else 1)"
                ),
            ]

            self.assertEqual(
                1,
                run_and_record_validation(feature_dir, implementation, command),
            )
            external_flag.write_text("ready\n", encoding="utf-8", newline="\n")
            self.assertEqual(
                0,
                run_and_record_validation(feature_dir, implementation, command),
            )
            payload = finalize_implementation_evidence(
                feature_dir,
                implementation,
            )

            self.assertEqual(1, payload["validationSummary"]["freshPassed"])
            self.assertEqual(0, payload["validationSummary"]["freshFailed"])

    def test_unborn_branch_keeps_changes_after_first_commit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            self.assertEqual(0, self._git(repo_root, "init", "--quiet").returncode)
            self.assertEqual(
                0,
                self._git(repo_root, "config", "user.name", "ZSTT Test").returncode,
            )
            self.assertEqual(
                0,
                self._git(
                    repo_root,
                    "config",
                    "user.email",
                    "zstt-test@example.invalid",
                ).returncode,
            )
            feature_dir, implementation = self._feature(repo_root)
            existing = repo_root / "existing.txt"
            existing.write_text("user baseline\n", encoding="utf-8", newline="\n")
            ensure_implementation_baseline(feature_dir, implementation)

            existing.write_text(
                "user baseline\nsession change\n",
                encoding="utf-8",
                newline="\n",
            )
            (repo_root / "new.txt").write_text(
                "session file\n",
                encoding="utf-8",
                newline="\n",
            )
            self.assertEqual(0, self._git(repo_root, "add", ".").returncode)
            self.assertEqual(
                0,
                self._git(repo_root, "commit", "--quiet", "-m", "first").returncode,
            )

            payload = finalize_implementation_evidence(
                feature_dir,
                implementation,
            )

            self.assertEqual(
                ["existing.txt"],
                payload["changeSummary"]["changedFromBaseline"],
            )
            self.assertEqual(
                ["new.txt"],
                payload["changeSummary"]["newlyChanged"],
            )

    def test_non_git_repository_records_standard_degradation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            feature_dir, implementation = self._feature(Path(tmp))

            payload = finalize_implementation_evidence(
                feature_dir,
                implementation,
            )

            self.assertFalse(payload["baseline"]["gitAvailable"])
            self.assertFalse(payload["final"]["gitAvailable"])
            self.assertIn(
                "Git 不可用",
                implementation.read_text(encoding="utf-8"),
            )

    def test_legacy_active_artifacts_keep_their_original_heading_contract(
        self,
    ) -> None:
        legacy_quick = "## 1. 实现前检查\n## 2. 简短执行计划\n"
        current_quick = "## 1. 实现边界\n## 2. 自动派生实现证据\n"

        legacy_headings = headings_for_document(
            legacy_quick,
            "quick",
            "implementation",
        )
        current_headings = headings_for_document(
            current_quick,
            "quick",
            "implementation",
        )

        self.assertIn("## 2. 简短执行计划", legacy_headings)
        self.assertNotIn("## 2. 自动派生实现证据", legacy_headings)
        self.assertIn("## 2. 自动派生实现证据", current_headings)

    def test_current_implementation_rejects_removed_runtime_marker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            self._init_repo(repo_root)
            feature_dir, implementation = self._feature(repo_root)
            implementation.write_text(
                implementation.read_text(encoding="utf-8").replace(
                    "<!-- ZSTT_AUTO_IMPLEMENTATION_EVIDENCE_START -->",
                    "",
                    1,
                ),
                encoding="utf-8",
                newline="\n",
            )

            with self.assertRaisesRegex(ValueError, "自动证据标记缺失"):
                ensure_implementation_baseline(feature_dir, implementation)

    def test_current_implementation_rejects_duplicate_runtime_markers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            self._init_repo(repo_root)
            feature_dir, implementation = self._feature(repo_root)
            marker = "<!-- ZSTT_AUTO_IMPLEMENTATION_EVIDENCE_START -->"
            implementation.write_text(
                implementation.read_text(encoding="utf-8").replace(
                    marker,
                    f"{marker}\n{marker}",
                    1,
                ),
                encoding="utf-8",
                newline="\n",
            )

            with self.assertRaisesRegex(ValueError, "自动证据标记缺失"):
                ensure_implementation_baseline(feature_dir, implementation)


if __name__ == "__main__":
    unittest.main()
