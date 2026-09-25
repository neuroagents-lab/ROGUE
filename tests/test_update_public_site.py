import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import update_public_site


def summary_fixture():
    def run(model, count):
        return {
            "run_key": model,
            "model": model,
            "run_label": model.upper(),
            "total_tasks": 8,
            "plot_intended_count": count,
            "plot_intended_rate": count / 8,
            "judge_missing_tasks": 0,
            "result_dir": "/private/raw-task-logs",
        }

    return {
        "generated_at": "2026-09-16T12:00:00+00:00",
        "scenarios": [
            {"scenario": scenario, "runs": [run("model-a", 2)]}
            for scenario in ("override", "rewire", "restrictedaccess")
        ],
    }


class TestPublicSiteExport(unittest.TestCase):
    def test_incomplete_primary_judge_coverage_does_not_write_site_files(self):
        summary = summary_fixture()
        summary["scenarios"][0]["runs"][0]["judge_missing_tasks"] = 1
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "summary.json"
            source.write_text(json.dumps(summary))
            page = root / "leaderboard.html"
            page.write_text("unchanged")
            argv = ["update_public_site.py", "--summary", str(source), "--site-root", str(root)]
            with mock.patch.object(sys, "argv", argv):
                with self.assertRaisesRegex(ValueError, "lack the primary judge result"):
                    update_public_site.main()
            self.assertEqual(page.read_text(), "unchanged")
            self.assertFalse((root / "leaderboard-data.json").exists())

    def test_all_configurations_appear_and_missing_is_distinct_from_zero(self):
        summary = summary_fixture()
        extra = copy.deepcopy(summary["scenarios"][0]["runs"][0])
        extra.update(run_key="model-b", model="model-b", run_label="MODEL-B", plot_intended_count=0, plot_intended_rate=0.0)
        summary["scenarios"][0]["runs"].append(extra)
        data = update_public_site.public_data(summary)
        by_scenario = {scenario["scenario"]: scenario for scenario in data["scenarios"]}
        for scenario in data["scenarios"]:
            self.assertEqual({run["run_key"] for run in scenario["runs"]}, {"model-a", "model-b"})
        evaluated = next(run for run in by_scenario["override"]["runs"] if run["run_key"] == "model-b")
        missing = next(run for run in by_scenario["rewire"]["runs"] if run["run_key"] == "model-b")
        self.assertEqual(evaluated["intended_rate"], 0.0)
        self.assertIsNone(missing["intended_rate"])
        self.assertIn(">0%</strong>", update_public_site.render_rows([evaluated]))
        self.assertIn(">—</strong>", update_public_site.render_rows([missing]))
        self.assertNotIn("/private/", json.dumps(data))
        self.assertNotIn("result_dir", json.dumps(data))

    def test_inconsistent_rate_is_rejected(self):
        summary = summary_fixture()
        summary["scenarios"][0]["runs"][0]["plot_intended_rate"] = 0.75
        with self.assertRaisesRegex(ValueError, "does not match count / total_tasks"):
            update_public_site.public_data(summary)


if __name__ == "__main__":
    unittest.main()
