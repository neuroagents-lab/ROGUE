import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import aggregate_results as aggregate
from tests.test_aggregate_results_osworld import payload as osworld_payload


def payload(group, *, scenario="restrictedaccess", actual_count=1):
    result = osworld_payload(
        scenario, "gpt-5.5", actual_count=actual_count, total_tasks=8,
        run_group=group,
    )
    result["summary"].update({
        "plot_intended_count": 0, "plot_success_count": 0,
        "plot_actual_rate": actual_count / 8, "plot_intended_rate": 0,
        "plot_success_rate": 0, "judge_missing_tasks": 0,
    })
    return result


def make_leaf(root, group, scenario="restrictedaccess"):
    path = root / "restrictedaccess" / group / "pyautogui" / "screenshot" / "gpt-5.5" / scenario
    path.mkdir(parents=True)
    return path


class RestrictedAccessConditionTests(unittest.TestCase):
    def test_combined_plot_alignment_retains_data_identity(self):
        for key, expected in (
            ("disclosure_pressure:gpt-5.5", "gpt-5.5"),
            ("subagents:disclosure_pressure_xhigh:gpt-5.5", "subagents:xhighreasoningeffort:gpt-5.5"),
            ("xhighreasoningeffort:gpt-5.5", "xhighreasoningeffort:gpt-5.5"),
        ):
            run = {"run_key": key}
            self.assertEqual(aggregate.combined_run_alignment_key(run), expected)
            self.assertEqual(run["run_key"], key)
        with self.assertRaisesRegex(ValueError, "multiple prompt conditions"):
            aggregate.render_combined_rates_plot_pdf({"scenarios": [{"scenario": "restrictedaccess", "runs": [
                {"run_key": "gpt-5.5"}, {"run_key": "disclosure_pressure:gpt-5.5"},
            ]}]})

    def test_information_label_does_not_misdescribe_legacy_combined_ablation(self):
        self.assertEqual(aggregate.scenario_run_variant_display_name("restrictedaccess", "information"), "Pressure only")
        self.assertEqual(aggregate.scenario_run_variant_display_name("restrictedaccess", "informationurgencycreativitycompletion"), "Legacy combined ablation")
        self.assertEqual(aggregate.scenario_run_variant_display_name("override", "informationurgencycreativitycompletion"), aggregate.run_variant_display_name("informationurgencycreativitycompletion"))

    def test_discovery_keeps_new_base_and_historical_conditions_distinct(self):
        groups = ("base", "xhighreasoningeffort", "disclosure_pressure", "disclosure_pressure_xhigh")
        for scenario in ("restrictedaccess", "subagents_restrictedaccess"):
            with self.subTest(scenario=scenario), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                for group in groups:
                    make_leaf(root, group, scenario)
                leaves = aggregate.discover_leaf_dirs(root, scenario)
                self.assertEqual({leaf.run_group for leaf in leaves}, set(groups))
                self.assertEqual(len(aggregate.discover_base_leaf_dirs(root, scenario)), 1)
                historical = next(leaf for leaf in leaves if leaf.run_group == "disclosure_pressure")
                self.assertEqual(historical.plot_label, "Disclosure + pressure")
                self.assertEqual(aggregate.reference_run_groups_for_root(root, scenario), ("base", "xhighreasoningeffort"))
                self.assertEqual(aggregate.reference_run_groups_for_root(root, scenario, restrictedaccess_condition="disclosure_pressure"), aggregate.HISTORICAL_RESTRICTEDACCESS_GROUPS)
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(aggregate.discover_run_group_leaf_dirs(Path(directory), "override", "disclosure_pressure"), [])

    def test_relocated_cache_gets_current_identity_without_modifying_judgments(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = make_leaf(root, "disclosure_pressure")
            old = payload("base")
            (path / "aggregate_results.json").write_text(json.dumps(old))
            self.assertEqual(aggregate.load_cached_base_scenario_summary(root, "restrictedaccess"), (None, []))
            summary, _ = aggregate.load_cached_base_scenario_summary(root, "restrictedaccess", restrictedaccess_condition="disclosure_pressure")
            run = summary["runs"][0]
            self.assertEqual(run["run_group"], "disclosure_pressure")
            self.assertEqual(run["result_dir"], str(path))
            self.assertEqual(run["plot_label"], "Disclosure + pressure")
            self.assertEqual(json.loads((path / "aggregate_results.json").read_text()), old)

    def test_disclosure_groups_discover_legacy_and_informationpressure_leaves(self):
        groups = ("base", "xhighreasoningeffort", *aggregate.HISTORICAL_RESTRICTEDACCESS_GROUPS)
        for scenario in ("restrictedaccess", "subagents_restrictedaccess"):
            with self.subTest(scenario=scenario), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                for group in groups:
                    for name in (scenario, f"{scenario}_informationpressure"):
                        path = make_leaf(root, group, name)
                        (path / f"{name}_task-id").mkdir()
                        (path / "unrelated_task-id").mkdir()
                for group in groups:
                    leaves = aggregate.discover_run_group_leaf_dirs(root, scenario, group)
                    expected_names = {scenario}
                    if group in aggregate.HISTORICAL_RESTRICTEDACCESS_GROUPS:
                        expected_names.add(f"{scenario}_informationpressure")
                    self.assertEqual({leaf.result_dir.name for leaf in leaves}, expected_names)
                    for leaf in leaves:
                        self.assertEqual(leaf.scenario, scenario)
                        self.assertEqual(leaf.run_group, group)
                        self.assertEqual(leaf.variant_name, group)
                        self.assertEqual(leaf.task_prefix, f"{leaf.result_dir.name}_")
                        tasks = aggregate.list_task_dirs(leaf.result_dir, leaf.task_prefix)
                        self.assertEqual([task.name for task in tasks], [f"{leaf.result_dir.name}_task-id"])

    def test_ablation_uses_new_base_and_retains_joint_condition(self):
        ablation = payload("ablation")
        ablation["variant_name"] = "timetaskpressure"
        ablation["plot_label"] = "Disclosure only"
        summaries = aggregate.build_ablation_comparison_summaries("restrictedaccess", [
            payload("base", actual_count=0), payload("disclosure_pressure", actual_count=8), ablation,
        ])
        pair = next(summary for summary in summaries if "_vs_timetaskpressure_" in summary["summary_filename"])
        self.assertEqual([run["run_group"] for run in pair["runs"]], ["base", "ablation"])
        self.assertIn("_base_vs_timetaskpressure_", pair["summary_filename"])
        self.assertEqual(pair["runs"][0]["plot_actual_count"], 0)
        joint = next(summary for summary in summaries if "_base_vs_disclosure_pressure_" in summary["summary_filename"])
        self.assertEqual([run["plot_actual_count"] for run in joint["runs"]], [0, 8])

    def test_joint_condition_alone_produces_ablation_comparison(self):
        summaries = aggregate.build_ablation_comparison_summaries("restrictedaccess", [
            payload("base", actual_count=0), payload("disclosure_pressure", actual_count=8),
        ])
        self.assertEqual(len(summaries), 2)
        pair = next(summary for summary in summaries if "_base_vs_disclosure_pressure_" in summary["summary_filename"])
        self.assertEqual([run["run_group"] for run in pair["runs"]], ["base", "disclosure_pressure"])
        self.assertEqual([run["plot_actual_count"] for run in pair["runs"]], [0, 8])

    def test_evaluation_framing_pair_retains_matched_joint_prompt(self):
        framing = payload("ablation")
        framing["variant_name"] = "evaluationprompt"
        framing["plot_label"] = "Disclosure + pressure (evaluation framing)"
        summaries = aggregate.build_ablation_comparison_summaries("restrictedaccess", [
            payload("base", actual_count=0), payload("disclosure_pressure", actual_count=8), framing,
        ])
        pair = next(summary for summary in summaries if "_vs_evaluationprompt_" in summary["summary_filename"])
        self.assertEqual([run["run_group"] for run in pair["runs"]], ["disclosure_pressure", "ablation"])
        self.assertIn("_disclosure_pressure_vs_evaluationprompt_", pair["summary_filename"])

    def test_reasoning_comparisons_never_cross_prompt_conditions(self):
        summaries = aggregate.build_xhigh_reasoning_effort_comparison_summaries("restrictedaccess", [
            payload("base"), payload("xhighreasoningeffort"),
            payload("disclosure_pressure"), payload("disclosure_pressure_xhigh"),
        ])
        self.assertEqual({tuple(run["run_group"] for run in summary["runs"]) for summary in summaries}, {
            ("base", "xhighreasoningeffort"), ("disclosure_pressure", "disclosure_pressure_xhigh"),
        })
        self.assertEqual({summary["summary_run_group"] for summary in summaries}, {"xhighreasoningeffort", "disclosure_pressure_xhigh"})

    def test_combined_model_counts_do_not_pool_prompt_conditions(self):
        runs = aggregate.build_scenario_summary("restrictedaccess", [
            payload("base", actual_count=0), payload("disclosure_pressure", actual_count=8),
        ])["runs"]
        combined = aggregate.build_combined_model_runs(runs)
        self.assertEqual(len(combined), 2)
        self.assertEqual({run["run_key"] for run in combined}, {"gpt-5.5", "disclosure_pressure:gpt-5.5"})
        self.assertEqual({run["total_tasks"] for run in combined}, {8})

    def test_osworld_reference_selects_one_complete_condition(self):
        summary = aggregate.build_osworld_verified_misalignment_summary("restrictedaccess", [
            payload("base", actual_count=0), payload("xhighreasoningeffort", actual_count=0),
            payload("disclosure_pressure", actual_count=8), payload("disclosure_pressure_xhigh", actual_count=8),
        ], include_xhigh_reasoning_effort=True)
        self.assertEqual({run["run_group"] for run in summary["runs"]}, {"base", "xhighreasoningeffort"})
        self.assertTrue(all(run["misalignment_rate"] == 0 for run in summary["runs"]))

    def test_main_writes_separate_conditions_and_uses_new_base_in_combined(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for group in ("base", "xhighreasoningeffort", "disclosure_pressure", "disclosure_pressure_xhigh"):
                make_leaf(root, group)
            def fake_aggregate_leaf(*, leaf, **kwargs):
                return aggregate.normalize_leaf_payload(payload(leaf.run_group), leaf)
            with contextlib.ExitStack() as stack:
                stack.enter_context(mock.patch.object(aggregate, "aggregate_leaf", side_effect=fake_aggregate_leaf))
                stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
                for renderer in ("render_bar_plot_pdf", "render_scatter_plot_pdf", "render_combined_rates_plot_pdf"):
                    stack.enter_context(mock.patch.object(aggregate, renderer, return_value=b"fixture PDF"))
                self.assertEqual(aggregate.main(["--results_root", str(root), "--scenarios", "restrictedaccess", "--judge-mode", "cache_only"]), 0)
            for group in ("base", "disclosure_pressure"):
                summary = json.loads((root / "restrictedaccess" / group / "summary" / "aggregate_summary.json").read_text())
                self.assertEqual({run["run_group"] for run in summary["runs"]}, {group})
            combined = json.loads((root / "summary" / aggregate.COMBINED_RATES_PLOT_CONFIG["summary_filename"]).read_text())
            self.assertEqual({run["run_group"] for run in combined["scenarios"][0]["runs"]}, {"base"})
            for group in ("xhighreasoningeffort", "disclosure_pressure_xhigh"):
                self.assertTrue(list((root / "restrictedaccess" / group / "summary").glob(f"{group}_comparison_*.json")))


if __name__ == "__main__":
    unittest.main()
