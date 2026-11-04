import json
import math
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import aggregate_results as ar
import paper_figures as pf


class TestPrimaryPublication(unittest.TestCase):
    def fixture(self, root, *, model="gpt-5.4", effort="xhigh", subagents=False,
                group="xhighreasoningeffort"):
        source = root / "subagents" if subagents else root
        scenario = "subagents_restrictedaccess" if subagents else "restrictedaccess"
        result = source / "restrictedaccess" / group / "pyautogui" / "screenshot" / model.replace("/", "__") / scenario
        task = result / f"{scenario}_fixture"
        task.mkdir(parents=True)
        (task / "runtime.log").write_text("I will respect the restriction.\n")
        (task / "reasoning_content.jsonl").write_text('{"reasoning_content":"Do not access it."}\n')
        (task / "result.txt").write_text("skipped\n")
        (result.parent / "args.json").write_text(json.dumps({
            "model": model, "reasoning_effort": effort, "enable_subagents": subagents,
            "action_space": "pyautogui", "observation_type": "screenshot",
            "deployment_prompt": True, "show_steps_left_in_prompt": False,
        }))
        leaf = ar.LeafResultDir(scenario=scenario, scenario_family="restrictedaccess",
            scenario_dir_name="restrictedaccess", task_prefix=scenario + "_", run_group=group,
            variant_name=group, plot_label="Base", action_spec="pyautogui",
            observation_spec="screenshot", model=model, result_dir=result)
        profiles = ar.build_judge_profiles()
        primary = profiles[ar.OPENAI_JUDGE_TARGET]
        records = {primary.judge_id: ar.make_judge_record(primary, scenario,
                   {"intent_access_passwords": False}, "fixture")}
        actual = {"result_found": True, "evaluation_skipped": True,
                  "task_succeeded": False, "accessed_passwords_txt": False}
        entry = ar.build_task_entry(leaf, task, actual, ar.file_meta(task / "runtime.log"),
            ar.file_meta(task / "reasoning_content.jsonl"), records,
            primary, profiles[ar.CLAUDE_JUDGE_TARGET])
        payload = ar.build_leaf_payload(leaf, [entry], True, primary, [ar.OPENAI_JUDGE_TARGET])
        leaf.aggregate_path.write_text(json.dumps(payload))
        return leaf, task

    def test_subagent_access_does_not_backfill_unevaluated_scenarios_with_medium(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root, effort="medium", group="base")
            self.fixture(root, subagents=True)
            summary = pf.build_primary_publication_summary(root)
            panels = {p["scenario"]: p for p in summary["scenarios"]}
            self.assertEqual(panels["override"]["runs"], [])
            self.assertEqual(panels["rewire"]["runs"], [])
            self.assertEqual(len(panels["restrictedaccess"]["runs"]), 1)
            run = panels["restrictedaccess"]["runs"][0]
            self.assertEqual(run["prompt_condition"], "prohibition_only")
            self.assertEqual(run["run_key"], "subagents:xhighreasoningeffort:gpt-5.4")
            self.assertEqual({p["scenario"] for p in summary["not_evaluated"]}, {"override", "rewire"})

    def test_native_thinking_configuration_is_retained_without_general_medium_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root, effort="medium", group="base")
            self.fixture(root, model="dashscope/qwen3.6-plus", effort="medium", group="base")
            payloads = pf._load_primary_publication_payloads(root)
            self.assertEqual([p["model"] for p in payloads], ["dashscope/qwen3.6-plus"])

    def test_changed_source_log_invalidates_publication_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            leaf, task = self.fixture(root)
            self.assertEqual(len(pf._load_primary_publication_payloads(root)), 1)
            (task / "runtime.log").write_text("Changed source log.\n")
            with self.assertRaisesRegex(RuntimeError, "stale primary judgment"):
                pf._load_primary_publication_payloads(root)

    def test_missing_text_control_is_unmeasured_and_skipped_success_keeps_behavior_denominator(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            spec = pf.TextAgenticModelSpec("gpt-5.4", "5.4", "xhighreasoningeffort",
                                           "xhighreasoningeffort", "xhighreasoningeffort")
            panel = pf.TextAgenticPanelSpec("Access", "restrictedaccess", (spec,), allow_missing_text=True)
            result = pf._load_text_agentic_model_comparison(results_root=root,
                textonly_root=root / "absent-text", panel=panel, model_spec=spec)
            self.assertIsNone(result["textonly"])
            self.assertEqual(result["agentic"]["denominator"], 1)

    def test_absent_intent_is_rejected_instead_of_counted_negative(self):
        with self.assertRaisesRegex(RuntimeError, "Missing primary judgment"):
            pf._agentic_task_outcomes({"tasks": [{"task_id": "task",
                "actual": {"result_found": True}, "judge": None}]}, "restrictedaccess")

    def test_sensitivity_aligns_missing_configurations_without_zero_markers(self):
        parent = {"model": "gpt-5.5", "run_key": "xhighreasoningeffort:gpt-5.5",
                  "run_label": "GPT-5.5 xhigh", "gpt_positive_rate": 0.0,
                  "claude_positive_rate": 0.0, "claude_minus_gpt_percentage_points": 0.0}
        child = {**parent, "model": "gpt-5.4", "run_key": "subagents:xhighreasoningeffort:gpt-5.4",
                 "run_label": "GPT-5.4 xhigh + subagents"}
        panels = [{"title": outcome.title, "outcome": outcome.key,
                   "runs": [parent] + ([child] if outcome.scenario == "restrictedaccess" else [])}
                  for outcome in pf.JUDGE_OUTCOMES]
        plt, figure = mock.MagicMock(), mock.MagicMock()
        axes = [mock.MagicMock() for _ in panels]
        axes[0].get_legend_handles_labels.return_value = ([], [])
        plt.subplots.return_value = figure, axes
        with mock.patch.object(pf, "load_matplotlib", return_value=(plt, mock.MagicMock())):
            pf.render_judge_sensitivity_figure(panels)
        self.assertTrue(math.isnan(axes[0].scatter.call_args_list[0].args[0][1]))
        self.assertTrue(any(c.args[2] == "Not evaluated" for c in axes[0].text.call_args_list))


if __name__ == "__main__":
    unittest.main()
