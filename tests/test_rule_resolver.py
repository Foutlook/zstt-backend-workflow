from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESOURCES = ROOT / "src" / "zstt_cli" / "resources"
RULES = RESOURCES / "rules"
RUNTIME = RESOURCES / "runtime"
RESOLVER = RUNTIME / "rule_resolver.py"
sys.path.insert(0, str(RUNTIME))

from rule_resolver import (  # noqa: E402
    RuleResolutionError,
    available_contexts,
    load_catalog,
    resolve_rules,
)


class RuleResolverTest(unittest.TestCase):
    def test_catalog_supports_four_rule_types_and_nine_profiles(self) -> None:
        catalog, _ = load_catalog()

        self.assertEqual(
            {"constraint", "decision", "checklist", "reference"},
            set(catalog["ruleTypes"]),
        )
        self.assertEqual(9, len(catalog["profiles"]))
        self.assertEqual(16, len(catalog["rules"]))
        self.assertNotIn("zstt-workflow-shared", catalog["profiles"])
        self.assertNotIn("zstt-java-backend-standard", catalog["profiles"])

    def test_profile_loads_baseline_without_speculative_context_rules(self) -> None:
        result = resolve_rules("zstt-implementation")
        rule_ids = [rule["id"] for rule in result["rules"]]

        self.assertIn("workflow.protocol", rule_ids)
        self.assertIn("java.core", rule_ids)
        self.assertIn("java.comments", rule_ids)
        self.assertIn("java.verification", rule_ids)
        self.assertNotIn("java.jackson", rule_ids)
        self.assertNotIn("java.data-access", rule_ids)
        self.assertNotIn("java.abstraction", rule_ids)
        self.assertNotIn("java.design-patterns", rule_ids)

    def test_explicit_contexts_add_only_matching_rules_and_reasons(self) -> None:
        result = resolve_rules(
            "zstt-implementation",
            ["jackson", "data_access", "design-patterns"],
        )
        rules = {rule["id"]: rule for rule in result["rules"]}

        self.assertEqual(
            ["jackson", "data-access", "design-patterns"],
            result["contexts"],
        )
        self.assertEqual(["context:jackson"], rules["java.jackson"]["reasons"])
        self.assertEqual(
            ["context:data-access"],
            rules["java.data-access"]["reasons"],
        )
        self.assertEqual(
            ["context:design-patterns"],
            rules["java.design-patterns"]["reasons"],
        )
        self.assertNotIn("java.abstraction", rules)

    def test_resolution_is_deterministic_and_fingerprinted(self) -> None:
        first = resolve_rules("zstt-code-review", ["jackson", "data-access"])
        second = resolve_rules("zstt-code-review", ["jackson", "data-access"])

        self.assertEqual(first, second)
        self.assertRegex(first["catalogSha256"], r"^[0-9a-f]{64}$")
        self.assertRegex(first["rulesetFingerprint"], r"^[0-9a-f]{64}$")
        for rule in first["rules"]:
            self.assertTrue(Path(rule["path"]).is_file())
            self.assertTrue(rule["relativePath"].startswith(".zstt-kit/rules/"))
            self.assertRegex(rule["sha256"], r"^[0-9a-f]{64}$")

    def test_unknown_skill_and_context_are_rejected(self) -> None:
        with self.assertRaisesRegex(RuleResolutionError, "未知 Skill profile"):
            resolve_rules("zstt-unknown")
        with self.assertRaisesRegex(RuleResolutionError, "未知上下文标签"):
            resolve_rules("zstt-implementation", ["guessed-from-file-name"])

    def test_catalog_path_cannot_escape_rules_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rules_root = Path(tmp)
            catalog = {
                "schemaVersion": 1,
                "rulesetVersion": "test",
                "ruleTypes": {"constraint": "test"},
                "profiles": {"zstt-test": ["escape"]},
                "rules": [
                    {
                        "id": "escape",
                        "type": "constraint",
                        "path": "../outside.md",
                        "description": "test",
                        "selectors": ["escape"],
                    }
                ],
            }
            catalog_path = rules_root / "catalog.json"
            catalog_path.write_text(
                json.dumps(catalog, ensure_ascii=False),
                encoding="utf-8",
                newline="\n",
            )

            with self.assertRaisesRegex(RuleResolutionError, "规则路径无效"):
                load_catalog(rules_root, catalog_path)

    def test_invalid_utf8_rule_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rules_root = Path(tmp)
            (rules_root / "broken.md").write_bytes(b"\xff")
            catalog = {
                "schemaVersion": 1,
                "rulesetVersion": "test",
                "ruleTypes": {"constraint": "test"},
                "profiles": {"zstt-test": ["broken"]},
                "rules": [
                    {
                        "id": "broken",
                        "type": "constraint",
                        "path": "broken.md",
                        "description": "test",
                        "selectors": ["broken"],
                    }
                ],
            }
            catalog_path = rules_root / "catalog.json"
            catalog_path.write_text(
                json.dumps(catalog, ensure_ascii=False),
                encoding="utf-8",
                newline="\n",
            )

            with self.assertRaisesRegex(RuleResolutionError, "有效 UTF-8"):
                load_catalog(rules_root, catalog_path)

    def test_list_contexts_cli_is_machine_readable(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(RESOLVER), "list-contexts"],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

        self.assertEqual(0, completed.returncode, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertIn("jackson", result["contexts"])
        self.assertIn("java.jackson", result["contexts"]["jackson"])

    def test_available_contexts_include_extensible_engineering_rules(self) -> None:
        catalog, _ = load_catalog()
        contexts = available_contexts(catalog)

        for context in (
            "jackson",
            "data-access",
            "sql-design",
            "abstraction",
            "design-patterns",
            "ddd",
            "concurrency",
            "examples",
        ):
            self.assertIn(context, contexts)


if __name__ == "__main__":
    unittest.main()
