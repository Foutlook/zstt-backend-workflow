from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "src" / "zstt_cli" / "resources" / "runtime" / "with_env.py"


class ScopedEnvironmentRunnerTest(unittest.TestCase):
    def _install_runner(self, project_root: Path) -> Path:
        target = project_root / ".zstt-kit" / "runtime" / "with_env.py"
        target.parent.mkdir(parents=True)
        shutil.copy2(RUNNER, target)
        return target

    def test_dms_scope_maps_separate_credential_and_clears_other_scopes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            runner = self._install_runner(project_root)
            env_dir = project_root / ".zstt-kit" / ".env"
            env_dir.mkdir(parents=True)
            (env_dir / ".env.local").write_text(
                "\n".join(
                    (
                        "ZSTT_ENV=test",
                        "ALIBABA_CLOUD_ACCESS_KEY_ID=observability-id",
                        "ALIBABA_CLOUD_ACCESS_KEY_SECRET=observability-secret",
                        "ZSTT_DMS_ALIBABA_CLOUD_ACCESS_KEY_ID=dms-id",
                        "ZSTT_DMS_ALIBABA_CLOUD_ACCESS_KEY_SECRET=dms-secret",
                        "ZSTT_DMS_ALIBABA_CLOUD_SECURITY_TOKEN=dms-token",
                        "ZSTT_ES_URL=http://es.example:9200",
                    )
                )
                + "\n",
                encoding="utf-8",
            )
            child_code = (
                "import json, os; "
                "print(json.dumps({"
                "'env': os.getenv('ZSTT_ENV'), "
                "'id': os.getenv('ALIBABA_CLOUD_ACCESS_KEY_ID'), "
                "'secret': os.getenv('ALIBABA_CLOUD_ACCESS_KEY_SECRET'), "
                "'token': os.getenv('ALIBABA_CLOUD_SECURITY_TOKEN'), "
                "'dms_source_visible': bool(os.getenv("
                "'ZSTT_DMS_ALIBABA_CLOUD_ACCESS_KEY_ID')), "
                "'es': bool(os.getenv('ZSTT_ES_URL'))}))"
            )
            inherited = os.environ.copy()
            inherited["ALIBABA_CLOUD_ACCESS_KEY_SECRET"] = "inherited-secret"
            inherited["ZSTT_ES_URL"] = "http://inherited.example:9200"

            completed = subprocess.run(
                [
                    sys.executable,
                    str(runner),
                    "test",
                    "dms",
                    "--",
                    sys.executable,
                    "-c",
                    child_code,
                ],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                env=inherited,
            )

            self.assertEqual(0, completed.returncode, completed.stderr)
            self.assertEqual(
                {
                    "env": "test",
                    "id": "dms-id",
                    "secret": "dms-secret",
                    "token": "dms-token",
                    "dms_source_visible": False,
                    "es": False,
                },
                json.loads(completed.stdout),
            )

    def test_client_observability_scope_uses_separate_test_credential(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            runner = self._install_runner(project_root)
            env_dir = project_root / ".zstt-kit" / ".env"
            env_dir.mkdir(parents=True)
            (env_dir / ".env.local").write_text(
                "\n".join(
                    (
                        "ZSTT_ENV=test",
                        "ALIBABA_CLOUD_ACCESS_KEY_ID=backend-id",
                        "ALIBABA_CLOUD_ACCESS_KEY_SECRET=backend-secret",
                        "ZSTT_CLIENT_ALIBABA_CLOUD_ACCESS_KEY_ID=client-id",
                        "ZSTT_CLIENT_ALIBABA_CLOUD_ACCESS_KEY_SECRET=client-secret",
                        "ZSTT_CLIENT_ALIBABA_CLOUD_REGION=cn-hangzhou",
                    )
                )
                + "\n",
                encoding="utf-8",
            )
            child_code = (
                "import json, os; "
                "print(json.dumps({"
                "'id': os.getenv('ALIBABA_CLOUD_ACCESS_KEY_ID'), "
                "'region': os.getenv('ALIBABA_CLOUD_REGION'), "
                "'client_source_visible': bool(os.getenv("
                "'ZSTT_CLIENT_ALIBABA_CLOUD_ACCESS_KEY_ID'))}))"
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    str(runner),
                    "test",
                    "observability-client",
                    "--",
                    sys.executable,
                    "-c",
                    child_code,
                ],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

            self.assertEqual(0, completed.returncode, completed.stderr)
            self.assertEqual(
                {
                    "id": "client-id",
                    "region": "cn-hangzhou",
                    "client_source_visible": False,
                },
                json.loads(completed.stdout),
            )

    def test_dms_scope_maps_separate_production_credential(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            runner = self._install_runner(project_root)
            env_dir = project_root / ".zstt-kit" / ".env"
            env_dir.mkdir(parents=True)
            (env_dir / ".env.prod.local").write_text(
                "ZSTT_ENV=prod\n"
                "ZSTT_DMS_ALIBABA_CLOUD_ACCESS_KEY_ID=prod-dms-id\n"
                "ZSTT_DMS_ALIBABA_CLOUD_ACCESS_KEY_SECRET=prod-dms-secret\n",
                encoding="utf-8",
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    str(runner),
                    "prod",
                    "dms",
                    "--",
                    sys.executable,
                    "-c",
                    (
                        "import json, os; print(json.dumps({"
                        "'env': os.getenv('ZSTT_ENV'), "
                        "'id': os.getenv('ALIBABA_CLOUD_ACCESS_KEY_ID'), "
                        "'secret': os.getenv('ALIBABA_CLOUD_ACCESS_KEY_SECRET')}))"
                    ),
                ],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

            self.assertEqual(0, completed.returncode, completed.stderr)
            self.assertEqual(
                {
                    "env": "prod",
                    "id": "prod-dms-id",
                    "secret": "prod-dms-secret",
                },
                json.loads(completed.stdout),
            )

    def test_client_observability_scope_uses_separate_production_credential(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            runner = self._install_runner(project_root)
            env_dir = project_root / ".zstt-kit" / ".env"
            env_dir.mkdir(parents=True)
            (env_dir / ".env.local").write_text(
                "ZSTT_ENV=test\n"
                "ZSTT_CLIENT_ALIBABA_CLOUD_ACCESS_KEY_ID=test-client-id\n"
                "ZSTT_CLIENT_ALIBABA_CLOUD_ACCESS_KEY_SECRET=test-client-secret\n",
                encoding="utf-8",
            )
            (env_dir / ".env.prod.local").write_text(
                "ZSTT_ENV=prod\n"
                "ALIBABA_CLOUD_ACCESS_KEY_ID=prod-backend-id\n"
                "ALIBABA_CLOUD_ACCESS_KEY_SECRET=prod-backend-secret\n"
                "ZSTT_CLIENT_ALIBABA_CLOUD_ACCESS_KEY_ID=prod-client-id\n"
                "ZSTT_CLIENT_ALIBABA_CLOUD_ACCESS_KEY_SECRET=prod-client-secret\n",
                encoding="utf-8",
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    str(runner),
                    "prod",
                    "observability-client",
                    "--",
                    sys.executable,
                    "-c",
                    "import os; print(os.getenv('ALIBABA_CLOUD_ACCESS_KEY_ID'))",
                ],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

            self.assertEqual(0, completed.returncode, completed.stderr)
            self.assertEqual("prod-client-id", completed.stdout.strip())
            self.assertNotIn("test-client-id", completed.stdout)
            self.assertNotIn("prod-backend-id", completed.stdout)

    def test_production_never_falls_back_to_test_environment(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            runner = self._install_runner(project_root)
            env_dir = project_root / ".zstt-kit" / ".env"
            env_dir.mkdir(parents=True)
            (env_dir / ".env.local").write_text(
                "ZSTT_ENV=test\n"
                "ZSTT_ES_URL=http://test.example:9200\n",
                encoding="utf-8",
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    str(runner),
                    "prod",
                    "es",
                    "--",
                    sys.executable,
                    "-c",
                    "print('must-not-run')",
                ],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

            self.assertEqual(1, completed.returncode)
            self.assertIn("prod environment file not found", completed.stderr)
            self.assertNotIn("must-not-run", completed.stdout)


if __name__ == "__main__":
    unittest.main()
