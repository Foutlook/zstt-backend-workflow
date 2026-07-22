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

    def test_mysql_scope_clears_other_managed_credentials(self) -> None:
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
                        "ZSTT_MYSQL_URL=mysql://test.example/db",
                        "ZSTT_MYSQL_USERNAME=readonly",
                        "ZSTT_MYSQL_PASSWORD=mysql-secret",
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
                "'mysql': bool(os.getenv('ZSTT_MYSQL_PASSWORD')), "
                "'observability': bool(os.getenv('ALIBABA_CLOUD_ACCESS_KEY_SECRET')), "
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
                    "mysql",
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
                    "mysql": True,
                    "observability": False,
                    "es": False,
                },
                json.loads(completed.stdout),
            )

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
