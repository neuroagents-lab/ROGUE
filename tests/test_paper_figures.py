from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import paper_figures


GPT_JUDGE_ID, CLAUDE_JUDGE_ID = paper_figures._judge_ids()


def judged_task(scenario, gpt_output=None, claude_output=None):
    values = {}
    if gpt_output is not None:
        values[GPT_JUDGE_ID] = gpt_output
    if claude_output is not None:
        values[CLAUDE_JUDGE_ID] = claude_output
    return {
        "actual": {"result_found": True},
        "judge_comparison": {
            "status": "incomplete"
            if len(values) < 2
            else "agree",
            "values": values,
        },
    }


def override_output(choice):
    return {"final_popup_choice": choice}


def rewire_output(intent, alternate):
    return {
        "intent_subvert_shutdown": intent,
        "used_alternate_shutdown_avoidance": alternate,
    }


def access_output(intent):
    return {"intent_access_passwords": intent}


class TestPublicationSelection(unittest.TestCase):
    def test_excludes_astra_and_its_sources_without_changing_raw_data_or_sol(self):
        raw = {"scenarios": [{"scenario": "restrictedaccess", "runs": [
            {"model": "gpt-6-astra", "plot_actual_count": 0},
            {"model": "gpt-5.6-sol", "plot_actual_count": 1},
        ]}], "included_sources": [
            "results/override/xhighreasoningeffort/pyautogui/screenshot/gpt-6-astra/override/aggregate_results.json",
            "results/override/xhighreasoningeffort/pyautogui/screenshot/gpt-5.6-sol/override/aggregate_results.json",
        ]}
        selected = paper_figures.filter_publication_data(raw)
        self.assertEqual([run["model"] for run in selected["scenarios"][0]["runs"]], ["gpt-5.6-sol"])
        self.assertEqual(len(selected["included_sources"]), 1)
        self.assertIn("gpt-5.6-sol", selected["included_sources"][0])
        self.assertEqual(selected["publication_excluded_models"], ["gpt-6-astra"])
        self.assertEqual(len(raw["scenarios"][0]["runs"]), 2)
        self.assertEqual(len(raw["included_sources"]), 2)
        selected["scenarios"][0]["runs"][0]["plot_actual_count"] = 7
        self.assertEqual(raw["scenarios"][0]["runs"][1]["plot_actual_count"], 1)

    def test_figure3_removes_only_requested_configurations_across_all_panels(self):
        keys = ["gpt-5.5", "xhighreasoningeffort:gpt-5.5", "subagents:xhighreasoningeffort:gpt-5.5",
                "claude-opus-4-7", "xhighreasoningeffort:claude-opus-4-7",
                "subagents:xhighreasoningeffort:claude-opus-4-7", "claude-opus-4-6",
                "subagents:claude-opus-4-6"]
        raw = {"scenarios": [{"scenario": scenario, "runs": [
            {"run_key": key if scenario != "restrictedaccess" else key.replace("xhighreasoningeffort", "disclosure_pressure_xhigh"),
             "model": key.split(":")[-1]} for key in keys
        ]} for scenario in ("override", "rewire", "restrictedaccess")]}
        selected = paper_figures.select_figure3_runs(raw)
        for scenario in selected["scenarios"]:
            self.assertEqual(len(scenario["runs"]), 5)
            actual = {paper_figures.combined_run_alignment_key(run) for run in scenario["runs"]}
            self.assertEqual(actual, set(keys) - set(paper_figures.FIGURE3_EXCLUDED_RUN_KEYS))
        self.assertEqual(selected["publication_layout"], "compact")
        self.assertEqual(len(raw["scenarios"][0]["runs"]), 8)

    def test_selection_can_be_overridden_explicitly_for_reproduction(self):
        raw = {"runs": [{"model": "gpt-6-astra"}, {"model": "gpt-5.6-sol"}]}
        selected = paper_figures.filter_publication_data(raw, excluded_models=())
        self.assertEqual(len(selected["runs"]), 2)
        self.assertEqual(selected["publication_excluded_models"], [])


class TestPublicationFallback(unittest.TestCase):
    @staticmethod
    def row(model, key, actual, *, source="restrictedaccess"):
        return {"model": model, "run_key": key, "source_scenario": source,
                "total_tasks": 8, "plot_actual_count": actual, "plot_actual_rate": actual / 8,
                "plot_intended_count": 2, "plot_intended_rate": 2 / 8,
                "action_specs": ["pyautogui"], "observation_specs": ["screenshot"]}

    def build(self, current, older, adjudications=()):
        old_summary = {"scenarios": [{"scenario": "restrictedaccess", "runs": older}]}
        with mock.patch.object(paper_figures, "load_cached_base_scenario_summary", return_value=(None, [])), \
             mock.patch.object(paper_figures, "load_cached_xhigh_reasoning_effort_scenario_summary", return_value=(None, [])), \
             mock.patch.object(paper_figures, "build_combined_rates_with_subagents_summary", return_value=old_summary), \
             mock.patch.object(paper_figures, "_discover_run_leaves", return_value=[]):
            return paper_figures.build_publication_combined_summary(current, Path("/results"), adjudications)

    def test_new_config_wins_and_adjudication_only_changes_exact_legacy_fallback(self):
        current = {"scenarios": [{"scenario": "restrictedaccess", "runs": [
            self.row("claude-opus-4-6", "claude-opus-4-6", 3),
        ]}]}
        legacy_key = "subagents:disclosure_pressure_xhigh:gpt-5.5"
        older = [self.row("claude-opus-4-6", "disclosure_pressure:claude-opus-4-6", 8),
                 self.row("gpt-5.5", legacy_key, 0, source="subagents_restrictedaccess"),
                 self.row("gpt-6-astra", "disclosure_pressure_xhigh:gpt-6-astra", 0)]
        record = {"condition": "disclosure_pressure", "run_key": legacy_key,
                  "source_scenario": "subagents_restrictedaccess", "model": "gpt-5.5",
                  "task_id": "shared-task-id", "automated_aggregate": {"actual_count": 0, "total_tasks": 8},
                  "adjudicated_aggregate": {"actual_count": 1, "total_tasks": 8, "actual_rate": 1 / 8}}
        selected = self.build(current, older, [record])
        runs = selected["scenarios"][0]["runs"]
        self.assertEqual(len(runs), 2)
        self.assertEqual((runs[0]["plot_actual_count"], runs[0]["prompt_condition"]), (3, "prohibition_only"))
        self.assertEqual((runs[1]["plot_actual_count"], runs[1]["automated_plot_actual_count"]), (1, 0))
        self.assertEqual(runs[1]["plot_intended_count"], 2)
        self.assertEqual(runs[1]["publication_source"], "legacy_fallback")
        self.assertEqual(older[1]["plot_actual_count"], 0)
        current["scenarios"][0]["runs"].append(self.row("gpt-5.5", "subagents:xhighreasoningeffort:gpt-5.5", 0, source="subagents_restrictedaccess"))
        rerun = self.build(current, older, [record])["scenarios"][0]["runs"]
        self.assertEqual(rerun[1]["plot_actual_count"], 0)
        self.assertNotIn("publication_manual_adjudications", rerun[1])

    def test_capability_panel_prefers_base_and_records_combined_fallback(self):
        new = {"runs": [{"model": "dashscope/qwen3.6-plus", "run_group": "base", "reasoning_effort": "medium", "misaligned_tasks": 1}]}
        historical = [
            {"model": "dashscope/qwen3.6-plus", "run_group": "disclosure_pressure", "reasoning_effort": "medium", "misaligned_tasks": 4},
            {"model": "claude-opus-4-6", "run_group": "disclosure_pressure_xhigh", "reasoning_effort": "max", "misaligned_tasks": 8,
             "osworld_verified_success_rate": 0.727},
        ]
        selected = paper_figures.build_publication_osworld_summary(new, historical_runs=historical)
        self.assertEqual(len(selected["runs"]), 2)
        qwen, opus = selected["runs"]
        self.assertEqual((qwen["misaligned_tasks"], qwen["prompt_condition"]), (1, "prohibition_only"))
        self.assertEqual((opus["misaligned_tasks"], opus["reasoning_effort"], opus["osworld_verified_success_rate"]), (8, "max", 0.727))
        self.assertEqual(opus["publication_source"], "legacy_fallback")
        self.assertEqual(opus["prompt_condition"], "disclosure_pressure")
        self.assertEqual(len(new["runs"]), 1)
        self.assertNotIn("prompt_condition", historical[1])
        old = {"runs": [{"model": "gpt-5.5", "run_group": "disclosure_pressure_xhigh"}]}
        with self.assertRaisesRegex(ValueError, "prohibition-only"):
            paper_figures.build_publication_osworld_summary(old)
        with self.assertRaisesRegex(ValueError, "disclosure \\+ pressure"):
            paper_figures.build_publication_osworld_summary(new, historical_runs=new["runs"])


    def test_additional_base_points_preserve_effort_and_delegation_provenance(self):
        import json
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rows = {}
            for model, effort, subagents, group, count in (
                ("claude-opus-4-7", "xhigh", False, "xhighreasoningeffort", 0),
                ("gpt-5.6-sol", "max", True, "xhighreasoningeffort", 1),
            ):
                model_dir = root / model.replace("/", "__")
                result_dir = model_dir / "restrictedaccess"
                result_dir.mkdir(parents=True)
                (model_dir / "args.json").write_text(json.dumps({"reasoning_effort": effort, "enable_subagents": subagents}))
                rows[model] = {"model": model, "model_display_name": model, "run_group": group,
                               "result_dir": str(result_dir), "aggregate_path": str(result_dir / "aggregate_results.json"),
                               "action_spec": "pyautogui", "observation_spec": "screenshot", "total_tasks": 8,
                               "plot_actual_count": count, "plot_actual_rate": count / 8}
            def load_high(path, scenario, **kwargs):
                model = "gpt-5.6-sol" if scenario == "subagents_restrictedaccess" else "claude-opus-4-7"
                return {"runs": [rows[model]]}, []
            with mock.patch.object(paper_figures, "load_cached_xhigh_reasoning_effort_scenario_summary", side_effect=load_high):
                points = {point["model"]: point for point in paper_figures._additional_default_access_capability_points(root)}
            self.assertEqual(set(points), {"claude-opus-4-7", "gpt-5.6-sol"})
            opus = points["claude-opus-4-7"]
            self.assertEqual((opus["misaligned_tasks"], opus["published_reasoning_effort"]), (0, "max"))
            sol = points["gpt-5.6-sol"]
            self.assertEqual((sol["misaligned_tasks"], sol["completed_tasks"], sol["osworld_verified_success_rate"]), (1, 8, 0.83))
            self.assertTrue(sol["enable_subagents"])
            self.assertEqual(sol["source_scenario"], "subagents_restrictedaccess")
            self.assertEqual(sol["publication_marker"], "D")
            self.assertIn("2607.24653v1", sol["osworld_verified_source_url"])

    def test_same_model_parent_and_subagent_configurations_are_not_pooled(self):
        parent = {"model": "gpt-5.6-sol", "reasoning_effort": "max", "run_group": "xhighreasoningeffort", "enable_subagents": False}
        child = {**parent, "enable_subagents": True, "publication_marker": "D"}
        result = paper_figures.build_publication_osworld_summary({"runs": [parent]}, [child, child])
        self.assertEqual(len(result["runs"]), 2)
        self.assertEqual([row["enable_subagents"] for row in result["runs"]], [False, True])


class TestJudgeAgreementTableNumbers(unittest.TestCase):
    def setUp(self):
        self.runs = {
            "override": (
                paper_figures.JudgeRun(
                    scenario="override",
                    run_key="gpt-5.5",
                    run_label="GPT-5.5",
                    model="gpt-5.5",
                    tasks=(
                        judged_task(
                            "override",
                            override_output("override"),
                            override_output("override"),
                        ),
                        judged_task(
                            "override",
                            override_output("override"),
                            override_output("accept"),
                        ),
                        judged_task(
                            "override",
                            override_output("accept"),
                            None,
                        ),
                    ),
                ),
            ),
            "rewire": (
                paper_figures.JudgeRun(
                    scenario="rewire",
                    run_key="gpt-5.5",
                    run_label="GPT-5.5",
                    model="gpt-5.5",
                    tasks=(
                        judged_task(
                            "rewire",
                            rewire_output(True, False),
                            rewire_output(False, False),
                        ),
                        judged_task(
                            "rewire",
                            rewire_output(False, True),
                            rewire_output(True, True),
                        ),
                    ),
                ),
            ),
            "restrictedaccess": (
                paper_figures.JudgeRun(
                    scenario="restrictedaccess",
                    run_key="gpt-5.5",
                    run_label="GPT-5.5",
                    model="gpt-5.5",
                    tasks=(
                        judged_task(
                            "restrictedaccess",
                            access_output(False),
                            access_output(False),
                        ),
                    ),
                ),
            ),
        }

    def test_table_rows_report_marginals_direction_and_coverage(self):
        rows = paper_figures._build_judge_agreement_table_numbers(self.runs)
        by_outcome = {row["outcome"]: row for row in rows}

        override = by_outcome["intent_override"]
        self.assertEqual(override["completed_tasks"], 3)
        self.assertEqual(override["compared_tasks"], 2)
        self.assertEqual(override["incomplete_tasks"], 1)
        self.assertEqual(override["gpt_positive_tasks"], 2)
        self.assertEqual(override["claude_positive_tasks"], 1)
        self.assertEqual(override["gpt_only_tasks"], 1)
        self.assertEqual(override["claude_only_tasks"], 0)
        self.assertEqual(override["agree_tasks"], 1)
        self.assertAlmostEqual(override["coverage_rate"], 2 / 3)
        self.assertAlmostEqual(override["agreement_rate"], 0.5)
        self.assertAlmostEqual(override["cohens_kappa"], 0.0)
        self.assertAlmostEqual(
            override["claude_minus_gpt_percentage_points"],
            -50.0,
        )

        intent = by_outcome["intent_subvert_shutdown"]
        self.assertEqual(intent["gpt_only_tasks"], 1)
        self.assertEqual(intent["claude_only_tasks"], 1)
        self.assertEqual(intent["gpt_positive_tasks"], 1)
        self.assertEqual(intent["claude_positive_tasks"], 1)
        self.assertEqual(intent["agreement_rate"], 0.0)
        self.assertEqual(intent["cohens_kappa"], -1.0)
        self.assertEqual(intent["claude_minus_gpt_percentage_points"], 0.0)

        alternate = by_outcome["alternate_shutdown_avoidance"]
        self.assertEqual(alternate["agree_tasks"], 2)
        self.assertEqual(alternate["agreement_rate"], 1.0)
        self.assertEqual(alternate["cohens_kappa"], 1.0)

        access = by_outcome["intent_access_passwords"]
        self.assertEqual(access["both_negative_tasks"], 1)
        self.assertEqual(access["agreement_rate"], 1.0)
        self.assertIsNone(access["cohens_kappa"])

    def test_public_function_uses_loaded_figure_3_runs(self):
        with mock.patch.object(
            paper_figures,
            "_load_judge_runs",
            return_value=self.runs,
        ) as load_runs:
            rows = paper_figures.judge_agreement_table_numbers(Path("results"))

        load_runs.assert_called_once()
        self.assertEqual(len(rows), 4)

    def test_plot_data_preserves_run_labels_and_outcome_order(self):
        panels = paper_figures._build_judge_sensitivity_plot_data(self.runs)

        self.assertEqual(
            [panel["outcome"] for panel in panels],
            [outcome.key for outcome in paper_figures.JUDGE_OUTCOMES],
        )
        self.assertEqual(panels[0]["runs"][0]["run_label"], "GPT-5.5")
        self.assertEqual(
            panels[0]["runs"][0]["claude_minus_gpt_percentage_points"],
            -50.0,
        )

    def test_figure_3_sort_groups_variants_by_model(self):
        def run(model, run_key, run_label):
            return paper_figures.JudgeRun(
                scenario="override",
                run_key=run_key,
                run_label=run_label,
                model=model,
                tasks=(),
            )

        unordered = [
            run(
                "claude-opus-4-7",
                "subagents:xhighreasoningeffort:claude-opus-4-7",
                "Claude Opus 4.7 (xhigh + Subagents)",
            ),
            run("gpt-5.4", "subagents:gpt-5.4", "GPT-5.4 (Subagents)"),
            run("gpt-5.5", "gpt-5.5", "GPT-5.5"),
            run("claude-opus-4-7", "claude-opus-4-7", "Claude Opus 4.7"),
            run(
                "gpt-5.5",
                "xhighreasoningeffort:gpt-5.5",
                "GPT-5.5 (xhigh)",
            ),
            run("gpt-5.4", "gpt-5.4", "GPT-5.4"),
            run(
                "gpt-5.5",
                "subagents:xhighreasoningeffort:gpt-5.5",
                "GPT-5.5 (xhigh + Subagents)",
            ),
        ]

        ordered = sorted(unordered, key=paper_figures._figure_3_run_sort_key)

        self.assertEqual(
            [item.run_label for item in ordered],
            [
                "GPT-5.5",
                "GPT-5.5 (xhigh)",
                "GPT-5.5 (xhigh + Subagents)",
                "GPT-5.4",
                "GPT-5.4 (Subagents)",
                "Claude Opus 4.7",
                "Claude Opus 4.7 (xhigh + Subagents)",
            ],
        )


class TestPaperFigureCli(unittest.TestCase):
    def test_task_success_capability_is_a_supported_figure(self):
        args = paper_figures.parse_args(["capability_vs_misalignment"])
        self.assertEqual(args.figure, "capability_vs_misalignment")

    def test_capability_osworld_is_a_supported_figure(self):
        args = paper_figures.parse_args(
            ["capability_osworld_vs_misalignment"]
        )
        self.assertEqual(
            args.figure,
            "capability_osworld_vs_misalignment",
        )

    def test_judge_sensitivity_is_a_supported_figure(self):
        args = paper_figures.parse_args(["judge_sensitivity"])
        self.assertEqual(args.figure, "judge_sensitivity")

    def test_text_agentic_figures_are_supported(self):
        for figure_name in (
            "figure_2",
            "figure_2_merged",
            "figure_8",
            "textonly_agentic_mixed_reasoning",
        ):
            with self.subTest(figure=figure_name):
                args = paper_figures.parse_args(
                    [
                        figure_name,
                        "--textonly_root",
                        "custom-text-results",
                    ]
                )
                self.assertEqual(args.figure, figure_name)
                self.assertEqual(
                    args.textonly_root,
                    Path("custom-text-results"),
                )

    def test_merged_figure_accepts_rerun_roots(self):
        args = paper_figures.parse_args(
            [
                "figure_2_merged",
                "--rerun_results_root",
                "rerun-agentic",
                "--rerun_textonly_root",
                "rerun-text",
            ]
        )
        self.assertEqual(args.rerun_results_root, Path("rerun-agentic"))
        self.assertEqual(args.rerun_textonly_root, Path("rerun-text"))


class TestTaskSuccessCapabilityFigure(unittest.TestCase):
    def run_data(self, denominator=10, **changes):
        run = {
            "model": "gpt-6-astra",
            "model_display_name": "GPT-6 Astra (max)",
            "run_group": "xhighreasoningeffort",
            "completed_tasks": 10,
            "capability_denominator_tasks": denominator,
            "success_rate": 0.0,
            "misalignment_rate": 0.0,
            "judge_missing_tasks": 0,
        }
        run.update(changes)
        return run

    def test_zero_override_denominator_is_omitted_but_observed_zero_success_is_kept(self):
        undefined = self.run_data(denominator=0)
        observed_zero = self.run_data(
            model="gpt-5.6-sol", model_display_name="GPT-5.6 Sol (max)",
            denominator=4, misalignment_rate=0.4,
        )
        plotted, omitted = paper_figures._capability_plot_runs({
            "scenario": "override", "runs": [undefined, observed_zero],
        })
        self.assertEqual(plotted, (observed_zero,))
        self.assertEqual(omitted, ("GPT-6 Astra (max)",))
        self.assertEqual(undefined["success_rate"], 0.0)

    def test_rewire_requires_complete_known_primary_judge_coverage(self):
        for missing in (1, None):
            with self.subTest(missing=missing):
                run = self.run_data(judge_missing_tasks=missing)
                if missing is None:
                    del run["judge_missing_tasks"]
                summaries = (
                    {"scenario": "override", "runs": [self.run_data()]},
                    {"scenario": "rewire", "runs": [run]},
                )
                with mock.patch.object(paper_figures, "load_matplotlib") as load:
                    with self.assertRaisesRegex(RuntimeError, "complete primary-judge coverage"):
                        paper_figures.render_capability_vs_misalignment(summaries)
                load.assert_not_called()

    def test_zero_rewiring_rate_with_judged_tasks_is_a_valid_point(self):
        run = self.run_data(success_rate=0.8)
        plotted, omitted = paper_figures._capability_plot_runs({
            "scenario": "rewire", "runs": [run],
        })
        self.assertEqual(plotted, (run,))
        self.assertEqual(omitted, ())

    def test_uses_task_success_summaries_including_high_reasoning_runs(self):
        for scenario in paper_figures.CAPABILITY_SCENARIOS:
            with self.subTest(scenario=scenario):
                self.assertEqual(
                    paper_figures._capability_summary_path(Path("results"), scenario),
                    Path("results") / scenario / "xhighreasoningeffort" / "summary"
                    / f"{scenario}_capability_vs_misalignment_base_plus_xhighreasoningeffort.json",
                )


class TestCapabilityOSWorldFigure(unittest.TestCase):
    def test_summary_paths_use_reasoning_matched_zoomed_outputs(self):
        for scenario in paper_figures.CAPABILITY_OSWORLD_SCENARIOS:
            path = paper_figures._capability_osworld_summary_path(
                Path("results"),
                scenario,
            )
            self.assertEqual(
                path.parts[:3],
                ("results", scenario, "xhighreasoningeffort"),
            )
            self.assertEqual(path.parts[3], "summary")
            self.assertTrue(
                path.name.endswith(
                    "reasoning_matched_xaxis_zoomed.json"
                )
            )

    def test_legend_models_follow_the_paper_model_order(self):
        summaries = (
            {
                "runs": [
                    {"model": "moonshot/kimi-k2.6"},
                    {"model": "gpt-5.4"},
                ]
            },
            {"runs": [{"model": "gpt-5.5"}]},
            {"runs": [{"model": "claude-opus-4-6"}]},
        )

        models = paper_figures._capability_osworld_models(summaries)

        self.assertEqual(
            models,
            (
                "gpt-5.5",
                "gpt-5.4",
                "claude-opus-4-6",
                "moonshot/kimi-k2.6",
            ),
        )

    def test_osworld_error_bars_use_completed_task_counts(self):
        summaries = [{"scenario": scenario, "x_axis_limits": [0.57, 0.8], "runs": [{
            "model": "dashscope/qwen3.6-plus", "osworld_verified_success_rate": 0.625,
            "misalignment_rate": 1 / 8, "misaligned_tasks": 1, "completed_tasks": 8,
        }]} for scenario in paper_figures.CAPABILITY_OSWORLD_SCENARIOS]
        plt, figure = mock.MagicMock(), mock.MagicMock()
        axes = [mock.MagicMock() for _ in summaries]
        plt.subplots.return_value = (figure, [axes])
        with mock.patch.object(paper_figures, "load_matplotlib", return_value=(plt, mock.MagicMock())):
            paper_figures.render_capability_osworld_vs_misalignment(summaries)
        for axis in axes:
            self.assertEqual(axis.errorbar.call_count, 1)
            self.assertAlmostEqual(axis.errorbar.call_args.kwargs["yerr"][0], ((1 / 8) * (7 / 8) / 8) ** 0.5)

    def test_zoomed_ticks_use_simple_grid_in_compact_panels(self):
        ticks = paper_figures._capability_osworld_x_ticks((0.61, 0.8))

        self.assertEqual(len(ticks), 2)
        for actual, expected in zip(
            ticks,
            (0.7, 0.8),
        ):
            self.assertAlmostEqual(actual, expected)


class TestTextAgenticFigureSpecs(unittest.TestCase):
    def test_figure_2_is_the_three_panel_xhigh_comparison(self):
        spec = paper_figures.FIGURE_2_SPEC

        self.assertEqual(spec.output_stem, "figure_2")
        self.assertEqual(len(spec.rows), 1)
        self.assertEqual(
            [panel.scenario for panel in spec.rows[0]],
            ["override", "rewire", "restrictedaccess"],
        )
        for panel in spec.rows[0]:
            expected = (
                "disclosure_pressure_xhigh"
                if panel.scenario == "restrictedaccess"
                else "xhighreasoningeffort"
            )
            for model in panel.models:
                self.assertEqual(model.textonly_run_group, expected)
                self.assertEqual(model.agentic_run_group, expected)
                self.assertEqual(model.agentic_variant, expected)

    def test_textonly_stays_matched_historical_while_wording_includes_new_base(self):
        for spec in (paper_figures.FIGURE_2_SPEC, paper_figures.FIGURE_8_SPEC, paper_figures.MIXED_REASONING_SPEC):
            for row in spec.rows:
                for panel in row:
                    if panel.scenario != "restrictedaccess":
                        continue
                    for model in panel.models:
                        self.assertIn(model.agentic_run_group, {"disclosure_pressure", "disclosure_pressure_xhigh"})
                        self.assertEqual(model.agentic_variant, model.agentic_run_group)
                        self.assertEqual(model.textonly_run_group, model.agentic_run_group)
        access_panel = paper_figures.FIGURE_9_PANELS[-1]
        self.assertIn("disclosure_pressure", access_panel.variants)
        self.assertIn("base", access_panel.variants)

    def test_four_condition_panel_uses_one_matched_configuration(self):
        panel = paper_figures.RESTRICTEDACCESS_CONDITION_PANEL
        self.assertEqual(panel.model, "claude-opus-4-6")
        self.assertEqual(panel.observation_spec, "a11y_tree")
        self.assertEqual(panel.variants, ("base", "timetaskpressure", "information", "disclosure_pressure"))
        self.assertEqual(panel.variant_labels["information"], "Pressure only*")

    def test_information_and_pressure_panels_use_independent_additions(self):
        self.assertEqual(paper_figures.INFORMATION_PANELS[-1].variants, ("base", "timetaskpressure"))
        self.assertEqual(paper_figures.PRESSURE_PANELS[-1].variants, ("base", "information"))
        self.assertEqual(paper_figures.PRESSURE_PANELS[1].variants, ("xhighreasoningeffort", "timetaskpressure"))

    def test_judge_alignment_keeps_condition_identity_out_of_model_configuration(self):
        historical = {"model": "gpt-5.5", "run_key": "subagents:disclosure_pressure_xhigh:gpt-5.5"}
        other_scenario = {"model": "gpt-5.5", "run_key": "subagents:xhighreasoningeffort:gpt-5.5"}
        self.assertEqual(
            paper_figures._judge_run_configuration_key(historical),
            paper_figures._judge_run_configuration_key(other_scenario),
        )
        self.assertNotEqual(
            paper_figures._judge_run_configuration_key(historical),
            paper_figures._judge_run_configuration_key({"model": "gpt-5.5", "run_key": "disclosure_pressure:gpt-5.5"}),
        )

    def test_historical_judge_keys_discover_their_own_condition(self):
        for group in ("disclosure_pressure", "disclosure_pressure_xhigh"):
            with mock.patch.object(paper_figures, "discover_run_group_leaf_dirs", return_value=[]) as discover:
                paper_figures._discover_run_leaves(Path("results"), "restrictedaccess", f"subagents:{group}:gpt-5.5")
            discover.assert_called_once_with(Path("results/subagents"), "restrictedaccess", group)

    def test_figure_2_merged_reuses_the_figure_2_layout(self):
        spec = paper_figures.FIGURE_2_MERGED_SPEC

        self.assertEqual(spec.output_stem, "figure_2_merged")
        self.assertEqual(spec.rows, paper_figures.FIGURE_2_SPEC.rows)
        self.assertEqual(
            spec.figure_size,
            paper_figures.FIGURE_2_SPEC.figure_size,
        )

    def test_repeated_outcomes_use_equal_weight_task_clusters(self):
        first_run = {
            "a": {"actual": 1.0, "intended": 0.0},
            "b": {"actual": 0.0, "intended": 1.0},
        }
        second_run = {
            "a": {"actual": 0.0, "intended": 0.0},
            "c": {"actual": 1.0, "intended": 1.0},
        }

        metrics = paper_figures._merge_repeated_task_outcomes(
            (first_run, second_run),
            "test",
        )

        self.assertAlmostEqual(metrics["actual"], 0.5)
        self.assertAlmostEqual(metrics["actual_se"], 1 / (12 ** 0.5))
        self.assertAlmostEqual(metrics["intended"], 2 / 3)
        self.assertAlmostEqual(metrics["intended_se"], 1 / 3)
        self.assertEqual(metrics["task_count"], 3)
        self.assertEqual(metrics["complete_task_count"], 1)
        self.assertEqual(metrics["observation_count"], 4)

    def test_figure_8_covers_every_model_and_scenario(self):
        spec = paper_figures.FIGURE_8_SPEC

        self.assertEqual(spec.output_stem, "figure_8")
        self.assertEqual(len(spec.rows), 4)
        self.assertTrue(all(len(row) == 3 for row in spec.rows))
        self.assertEqual(
            [row[0].models[0].model for row in spec.rows],
            [
                "gpt-5.4",
                "gpt-5.5",
                "claude-opus-4-6",
                "claude-opus-4-7",
            ],
        )
        for row in spec.rows:
            self.assertEqual(
                [panel.scenario for panel in row],
                ["override", "rewire", "restrictedaccess"],
            )

    def test_model_comparison_uses_run_group_subdirectories(self):
        model_spec = paper_figures.TextAgenticModelSpec(
            model="model-a",
            short_label="A",
            textonly_run_group="xhighreasoningeffort",
            agentic_run_group="agentic-group",
            agentic_variant="agentic-variant",
        )
        panel = paper_figures.TextAgenticPanelSpec(
            title="Override",
            scenario="override",
            models=(model_spec,),
        )
        comparison = {
            "plot_bars": [
                {
                    "group": "Text-Only",
                    "rate": 0.1,
                    "count": 1,
                    "denominator": 10,
                },
                {
                    "group": "Text-Only",
                    "rate": 0.2,
                    "count": 2,
                    "denominator": 10,
                },
                {
                    "group": "Agentic",
                    "rate": 0.3,
                    "count": 3,
                    "denominator": 10,
                },
                {
                    "group": "Agentic",
                    "rate": 0.4,
                    "count": 4,
                    "denominator": 10,
                },
            ]
        }

        with (
            mock.patch.object(
                paper_figures,
                "load_textonly_scenario_aggregate",
                return_value={"text": "payload"},
            ) as load_text,
            mock.patch.object(
                paper_figures,
                "discover_agentic_aggregate",
                return_value=(Path("agentic.json"), {"agentic": "payload"}),
            ) as discover_agentic,
            mock.patch.object(
                paper_figures,
                "build_scenario_comparison",
                return_value=comparison,
            ),
        ):
            payload = paper_figures._load_text_agentic_model_comparison(
                results_root=Path("agentic-results"),
                textonly_root=Path("text-results"),
                panel=panel,
                model_spec=model_spec,
            )

        load_text.assert_called_once_with(
            Path("text-results/xhighreasoningeffort"),
            "model-a",
            "override",
        )
        discover_agentic.assert_called_once_with(
            Path("agentic-results"),
            scenario="override",
            model="model-a",
            run_group="agentic-group",
            variant_name="agentic-variant",
            preferred_observation_spec=None,
        )
        self.assertEqual(payload["textonly"]["actual"], 0.1)
        self.assertEqual(payload["agentic"]["intended"], 0.4)


if __name__ == "__main__":
    unittest.main()
