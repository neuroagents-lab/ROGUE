import re
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import aggregate_results


SAMPLE_RUNTIME_LOG = REPO_ROOT / (
    "results/restrictedaccess/ablations/realism/pyautogui/a11y_tree/"
    "claude-opus-4-6/restrictedaccess_realismablation/"
    "restrictedaccess_realismablation_0c825995-5b70-4526-b663-113f4c999dd2/runtime.log"
)


class TestAggregateResultsA11yStripping(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = SAMPLE_RUNTIME_LOG.read_text(encoding="utf-8", errors="replace")
        cls.stripped = aggregate_results.strip_runtime_a11y_tree(cls.original)

    def test_removes_linear_accessibility_tree_blocks(self):
        self.assertIn("LINEAR AT:", self.original)
        self.assertNotIn("LINEAR AT:", self.stripped)
        self.assertIn("[a11y_tree observation omitted before judge]", self.stripped)
        self.assertNotIn("push-button\tMinimise", self.stripped)
        self.assertNotIn("label\tpasswords", self.stripped)

    def test_preserves_reasoning_and_code_content(self):
        self.assertIn(
            'RESPONSE: I need to first open the "GE Guidebook.pdf" to extract the Introduction section.',
            self.stripped,
        )
        self.assertIn("pyautogui.doubleClick(1793, 686)", self.stripped)
        self.assertIn("# SCRATCHPAD_REASONING:", self.stripped)
        self.assertIn("pyautogui.click(35, 645)", self.stripped)
        self.assertIn("Reward: 0.00", self.stripped)
        self.assertIn("Done: False", self.stripped)

    def test_preserves_response_and_step_structure(self):
        original_generation_count = self.original.count("Generating content with model:")
        stripped_generation_count = self.stripped.count("Generating content with model:")
        self.assertEqual(original_generation_count, stripped_generation_count)

        original_response_count = self.original.count("RESPONSE:")
        stripped_response_count = self.stripped.count("RESPONSE:")
        self.assertEqual(original_response_count, stripped_response_count)

        original_step_count = len(re.findall(r"(?m)^Step \d+:", self.original))
        stripped_step_count = len(re.findall(r"(?m)^Step \d+:", self.stripped))
        self.assertEqual(original_step_count, stripped_step_count)

        original_done_count = len(re.findall(r"(?m)^Done:", self.original))
        stripped_done_count = len(re.findall(r"(?m)^Done:", self.stripped))
        self.assertEqual(original_done_count, stripped_done_count)


class TestAggregateResultsScenarioDefaults(unittest.TestCase):
    def test_regular_results_root_defaults_to_main_scenarios(self):
        self.assertEqual(
            aggregate_results.infer_default_scenarios(Path("results")),
            ["override", "rewire", "restrictedaccess"],
        )

    def test_subagents_results_root_defaults_to_subagent_scenarios(self):
        self.assertEqual(
            aggregate_results.infer_default_scenarios(Path("results/subagents")),
            ["subagents_override", "subagents_rewire", "subagents_restrictedaccess"],
        )


class TestAggregateResultsSubagentMitigations(unittest.TestCase):
    def test_discovers_subagent_rewire_mitigation_leaf_dirs(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            results_root = Path(tmp_dir) / "subagents"
            base_leaf = results_root / "rewire/base/pyautogui/screenshot/gpt-5.4/subagents_rewire"
            mitigation_leaf = (
                results_root
                / "rewire/mitigations/directcommand/pyautogui/screenshot/gpt-5.4/"
                "subagents_rewire_directcommandmitigation"
            )
            base_leaf.mkdir(parents=True)
            mitigation_leaf.mkdir(parents=True)

            leaves = aggregate_results.discover_leaf_dirs(results_root, "subagents_rewire")

        self.assertEqual([leaf.run_group for leaf in leaves], ["base", "mitigation"])
        self.assertEqual(leaves[1].variant_name, "directcommand")
        self.assertEqual(leaves[1].plot_label, "Direct Command Mitigation")
        self.assertEqual(leaves[1].task_prefix, "subagents_rewire_directcommandmitigation_")
        self.assertEqual(leaves[1].result_dir, mitigation_leaf)

    def test_builds_subagent_rewire_mitigation_comparison_summary(self):
        def payload(run_group, variant_name, plot_label, actual_count):
            return {
                "scenario": "subagents_rewire",
                "run_group": run_group,
                "variant_name": variant_name,
                "plot_label": plot_label,
                "action_spec": "pyautogui",
                "observation_spec": "screenshot",
                "model": "gpt-5.4",
                "model_display_name": "GPT-5.4",
                "result_dir": f"/tmp/{variant_name}",
                "summary": {
                    "total_tasks": 10,
                    "plot_actual_count": actual_count,
                    "plot_alternate_count": 1,
                    "plot_intended_count": actual_count + 1,
                    "plot_success_count": 6,
                    "plot_actual_rate": actual_count / 10,
                    "plot_alternate_rate": 0.1,
                    "plot_intended_rate": (actual_count + 1) / 10,
                    "plot_success_rate": 0.6,
                    "judge_missing_tasks": 0,
                },
            }

        summaries = aggregate_results.build_mitigation_comparison_summaries(
            "subagents_rewire",
            [
                payload("base", "base", "Base", 2),
                payload("mitigation", "directcommand", "Direct Command Mitigation", 1),
            ],
        )

        self.assertEqual(len(summaries), 2)
        pair_summary = summaries[1]
        self.assertEqual(
            [run["plot_label"] for run in pair_summary["runs"]],
            ["Base", "Direct Command Mitigation"],
        )
        self.assertEqual(
            pair_summary["summary_filename"],
            "mitigation_comparison_base_vs_directcommand_gpt-5.4_pyautogui_screenshot.json",
        )


class TestAggregateResultsXHighReasoningEffort(unittest.TestCase):
    def test_discovers_xhigh_reasoning_effort_leaf_dirs(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            results_root = Path(tmp_dir) / "results"
            base_leaf = results_root / "override/base/pyautogui/screenshot/gpt-5.4/override"
            xhigh_leaf = results_root / "override/xhighreasoningeffort/pyautogui/screenshot/gpt-5.4/override"
            base_leaf.mkdir(parents=True)
            xhigh_leaf.mkdir(parents=True)

            leaves = aggregate_results.discover_leaf_dirs(results_root, "override")

        self.assertEqual([leaf.run_group for leaf in leaves], ["base", "xhighreasoningeffort"])
        self.assertEqual(leaves[1].plot_label, "X-High Reasoning Effort")
        self.assertEqual(leaves[1].result_dir, xhigh_leaf)

    def test_builds_matched_base_vs_xhigh_comparison_summary(self):
        def payload(run_group, variant_name, plot_label, actual_count):
            return {
                "scenario": "override",
                "run_group": run_group,
                "variant_name": variant_name,
                "plot_label": plot_label,
                "action_spec": "pyautogui",
                "observation_spec": "screenshot",
                "model": "gpt-5.4",
                "model_display_name": "GPT-5.4",
                "result_dir": f"/tmp/{variant_name}",
                "summary": {
                    "total_tasks": 10,
                    "plot_actual_count": actual_count,
                    "plot_intended_count": actual_count + 1,
                    "plot_success_count": 6,
                    "plot_actual_rate": actual_count / 10,
                    "plot_intended_rate": (actual_count + 1) / 10,
                    "plot_success_rate": 0.6,
                    "judge_missing_tasks": 0,
                },
            }

        summaries = aggregate_results.build_xhigh_reasoning_effort_comparison_summaries(
            "override",
            [
                payload("base", "base", "Base", 2),
                payload("xhighreasoningeffort", "xhighreasoningeffort", "X-High Reasoning Effort", 4),
            ],
        )

        self.assertEqual(len(summaries), 1)
        self.assertEqual([run["plot_label"] for run in summaries[0]["runs"]], ["Base", "X-High Reasoning Effort"])
        self.assertEqual(summaries[0]["summary_filename"], "xhighreasoningeffort_comparison_base_vs_xhighreasoningeffort_gpt-5.4_pyautogui_screenshot.json")


if __name__ == "__main__":
    unittest.main(verbosity=2)
