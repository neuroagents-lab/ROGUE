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
        self.assertEqual(intent["claude_minus_gpt_percentage_points"], 0.0)

        alternate = by_outcome["alternate_shutdown_avoidance"]
        self.assertEqual(alternate["agree_tasks"], 2)
        self.assertEqual(alternate["agreement_rate"], 1.0)

        access = by_outcome["intent_access_passwords"]
        self.assertEqual(access["both_negative_tasks"], 1)
        self.assertEqual(access["agreement_rate"], 1.0)

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
    def test_judge_sensitivity_is_a_supported_figure(self):
        args = paper_figures.parse_args(["judge_sensitivity"])
        self.assertEqual(args.figure, "judge_sensitivity")


if __name__ == "__main__":
    unittest.main()
