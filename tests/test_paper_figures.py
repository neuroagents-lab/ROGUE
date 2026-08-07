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

    def test_zoomed_ticks_are_thinned_to_four_readable_labels(self):
        ticks = paper_figures._capability_osworld_x_ticks((0.61, 0.8))

        self.assertEqual(len(ticks), 4)
        for actual, expected in zip(
            ticks,
            (0.625, 0.675, 0.725, 0.775),
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
        self.assertTrue(
            all(
                model.textonly_run_group == "xhighreasoningeffort"
                and model.agentic_run_group == "xhighreasoningeffort"
                and model.agentic_variant == "xhighreasoningeffort"
                for panel in spec.rows[0]
                for model in panel.models
            )
        )

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
