from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from compare_textonly_results import discover_agentic_aggregate, load_textonly_scenario_aggregate


class TestTextonlyConditionIsolation(unittest.TestCase):
    def test_new_base_does_not_match_stale_historical_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            legacy = root / "restrictedaccess" / "disclosure_pressure" / "pyautogui" / "screenshot" / "model-a" / "restrictedaccess"
            legacy.mkdir(parents=True)
            (legacy / "aggregate_results.json").write_text(json.dumps({
                "scenario": "restrictedaccess", "model": "model-a",
                "run_group": "base", "variant_name": "base",
            }))
            with self.assertRaises(FileNotFoundError):
                discover_agentic_aggregate(
                    root, scenario="restrictedaccess", model="model-a",
                    run_group="base", variant_name="base", preferred_observation_spec=None,
                )

    def test_scenario_cache_works_without_a_shared_model_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "disclosure_pressure_xhigh"
            scenario = root / "model-a" / "restrictedaccess"
            scenario.mkdir(parents=True)
            payload = {"scenario": "restrictedaccess", "completed_examples": 8}
            (scenario / "aggregate_results.json").write_text(json.dumps(payload))
            self.assertEqual(load_textonly_scenario_aggregate(root, "model-a", "restrictedaccess"), payload)

    def test_relocated_agentic_cache_uses_selected_condition_identity(self):
        for old_group, group in (
            ("base", "disclosure_pressure"),
            ("xhighreasoningeffort", "disclosure_pressure_xhigh"),
        ):
            with self.subTest(group=group), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                leaf = root / "restrictedaccess" / group / "pyautogui" / "screenshot" / "model-a" / "restrictedaccess"
                leaf.mkdir(parents=True)
                old = {
                    "scenario": "restrictedaccess", "model": "model-a",
                    "run_group": old_group, "variant_name": old_group,
                    "result_dir": "old/path", "summary": {"plot_actual_count": 3},
                }
                cache = leaf / "aggregate_results.json"
                cache.write_text(json.dumps(old))
                chosen_path, payload = discover_agentic_aggregate(
                    root, scenario="restrictedaccess", model="model-a",
                    run_group=group, variant_name=group, preferred_observation_spec=None,
                )
                self.assertEqual(chosen_path, cache)
                self.assertEqual(payload["run_group"], group)
                self.assertEqual(payload["variant_name"], group)
                self.assertEqual(payload["result_dir"], str(leaf))
                self.assertEqual(payload["summary"], old["summary"])
                self.assertEqual(json.loads(cache.read_text()), old)

    def test_removed_scenario_cannot_leak_from_an_old_model_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "xhighreasoningeffort"
            model = root / "model-a"
            model.mkdir(parents=True)
            (model / "aggregate_results.json").write_text(json.dumps({
                "scenarios": {"restrictedaccess": {"completed_examples": 8}},
            }))
            with self.assertRaises(FileNotFoundError):
                load_textonly_scenario_aggregate(root, "model-a", "restrictedaccess")


if __name__ == "__main__":
    unittest.main()
