import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCENARIO = "restrictedaccess"


class TestRestrictedAccessOptionalDriveSetup(unittest.TestCase):
    @classmethod
    def _drive_evaluator_results(cls, value):
        if isinstance(value, dict):
            found = [value] if value.get("type") == "googledrive_file" else []
            for child in value.values():
                found.extend(cls._drive_evaluator_results(child))
            return found
        if isinstance(value, list):
            return [
                item
                for child in value
                for item in cls._drive_evaluator_results(child)
            ]
        return []

    def test_all_base_examples_skip_drive_operations_without_credentials(self):
        manifest_path = REPO_ROOT / "evaluation_examples" / f"test_{SCENARIO}.json"
        with manifest_path.open("r", encoding="utf-8") as handle:
            example_ids = json.load(handle)[SCENARIO]

        drive_evaluator_count = 0
        for example_id in example_ids:
            with self.subTest(example_id=example_id):
                example_path = (
                    REPO_ROOT
                    / "evaluation_examples"
                    / "examples"
                    / SCENARIO
                    / f"{example_id}.json"
                )
                with example_path.open("r", encoding="utf-8") as handle:
                    example = json.load(handle)

                drive_steps = [
                    step for step in example["config"] if step["type"] == "googledrive"
                ]
                self.assertEqual(len(drive_steps), 1)
                self.assertIs(
                    drive_steps[0]["parameters"].get(
                        "skip_if_credentials_missing"
                    ),
                    True,
                )
                drive_results = self._drive_evaluator_results(
                    example.get("evaluator", {}).get("result")
                )
                drive_evaluator_count += len(drive_results)
                for result in drive_results:
                    self.assertIs(
                        result.get("skip_if_credentials_missing"),
                        True,
                    )

        self.assertEqual(drive_evaluator_count, 7)


if __name__ == "__main__":
    unittest.main(verbosity=2)
