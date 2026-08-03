#!/usr/bin/env python3
"""Generate publication-ready figures for the ROGUE paper.

Inputs come from the agentic and text-only aggregate JSON files produced by the
repository's aggregation scripts. This keeps paper figures tied to the same
counts and judge outputs as the existing result plots while composing panels
directly in Matplotlib.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from aggregate_results import (  # noqa: E402
    ACTUAL_COLOR,
    ALTERNATE_COLOR,
    CLAUDE_JUDGE_TARGET,
    INTENDED_COLOR,
    MODEL_ORDER,
    OPENAI_JUDGE_TARGET,
    SUCCESS_COLOR,
    binomial_standard_error,
    build_judge_profiles,
    discover_base_leaf_dirs,
    discover_xhigh_reasoning_effort_leaf_dirs,
    load_matplotlib,
)
from compare_textonly_results import (  # noqa: E402
    build_scenario_comparison,
    discover_agentic_aggregate,
    load_textonly_scenario_aggregate,
)


DEFAULT_RESULTS_ROOT = REPO_ROOT / "results"
DEFAULT_TEXTONLY_ROOT = REPO_ROOT / "textonly_results"
DEFAULT_RERUN_RESULTS_ROOT = (
    REPO_ROOT / "additional_results" / "agentic_results"
)
DEFAULT_RERUN_TEXTONLY_ROOT = (
    REPO_ROOT / "additional_results" / "textonly_results_v2"
)
DEFAULT_OUTPUT_DIR = REPO_ROOT / "figures" / "paper"
COMBINED_RATES_WITH_SUBAGENTS_FILENAME = "combined_rates_with_subagents.json"
JUDGE_SENSITIVITY_OUTPUT_STEM = "judge_sensitivity"
GPT_JUDGE_COLOR = INTENDED_COLOR
CLAUDE_JUDGE_COLOR = SUCCESS_COLOR
DELTA_ANNOTATION_THRESHOLD_PP = 10.0
TEXT_AGENTIC_BAR_WIDTH = 0.60
TEXT_AGENTIC_CLUSTER_GAP = 0.18
TEXT_AGENTIC_GROUP_GAP = 1.0


@dataclass(frozen=True)
class SeriesSpec:
    rate_key: str
    count_key: str
    label: str
    color: str


@dataclass(frozen=True)
class PanelSpec:
    scenario: str
    model: str
    action_spec: str
    observation_spec: str
    title: str
    variants: Tuple[str, ...]
    variant_labels: Mapping[str, str]
    series: Tuple[SeriesSpec, ...]


@dataclass(frozen=True)
class JudgeOutcomeSpec:
    key: str
    scenario: str
    title: str
    table_label: str
    decision_field: str


@dataclass(frozen=True)
class JudgeRun:
    scenario: str
    run_key: str
    run_label: str
    model: str
    tasks: Tuple[Mapping[str, Any], ...]


@dataclass(frozen=True)
class TextAgenticModelSpec:
    model: str
    short_label: str
    textonly_run_group: str
    agentic_run_group: str
    agentic_variant: str
    preferred_observation_spec: Optional[str] = None


@dataclass(frozen=True)
class TextAgenticPanelSpec:
    title: str
    scenario: str
    models: Tuple[TextAgenticModelSpec, ...]


@dataclass(frozen=True)
class TextAgenticFigureSpec:
    output_stem: str
    rows: Tuple[Tuple[TextAgenticPanelSpec, ...], ...]
    figure_size: Tuple[float, float]


JUDGE_OUTCOMES = (
    JudgeOutcomeSpec(
        key="intent_override",
        scenario="override",
        title="Intent to override\nhuman control",
        table_label="Intent to override",
        decision_field="final_popup_choice",
    ),
    JudgeOutcomeSpec(
        key="intent_subvert_shutdown",
        scenario="rewire",
        title="Intent to rewire\nshutdown",
        table_label="Intent to rewire shutdown",
        decision_field="intent_subvert_shutdown",
    ),
    JudgeOutcomeSpec(
        key="alternate_shutdown_avoidance",
        scenario="rewire",
        title="Used alternate\nrewiring method",
        table_label="Used alternate rewiring method",
        decision_field="used_alternate_shutdown_avoidance",
    ),
    JudgeOutcomeSpec(
        key="intent_access_passwords",
        scenario="restrictedaccess",
        title="Intent to access\nrestricted resource",
        table_label="Intent to access restricted resource",
        decision_field="intent_access_passwords",
    ),
)


FIGURE_9_PANELS = (
    PanelSpec(
        scenario="override",
        model="gpt-5.4",
        action_spec="pyautogui",
        observation_spec="screenshot",
        title="Override (GPT 5.4)",
        variants=(
            "base",
            "realism",
            "realismneutral",
            "realismusercentered",
            "realismconcise",
        ),
        variant_labels={
            "base": "Base",
            "realism": "Operational\nHandoff",
            "realismneutral": "Polite Choice",
            "realismusercentered": "User-Centered",
            "realismconcise": "System Dialog",
        },
        series=(
            SeriesSpec("plot_actual_rate", "plot_actual_count", "Actual", ACTUAL_COLOR),
            SeriesSpec(
                "plot_intended_rate",
                "plot_intended_count",
                "Intended",
                INTENDED_COLOR,
            ),
            SeriesSpec(
                "plot_success_rate",
                "plot_success_count",
                "Task Success",
                SUCCESS_COLOR,
            ),
        ),
    ),
    PanelSpec(
        scenario="rewire",
        model="gpt-5.4",
        action_spec="pyautogui",
        observation_spec="screenshot",
        title="Rewire (GPT 5.4)",
        variants=(
            "base",
            "realism",
            "realismupdaterestart",
            "realismusershutdown",
            "realismsessionlimit",
        ),
        variant_labels={
            "base": "Base",
            "realism": "Power-Off Notice",
            "realismupdaterestart": "Update Restart",
            "realismusershutdown": "User-Chosen\nShutdown",
            "realismsessionlimit": "Session Limit",
        },
        series=(
            SeriesSpec("plot_actual_rate", "plot_actual_count", "Actual", ACTUAL_COLOR),
            SeriesSpec(
                "plot_alternate_rate",
                "plot_alternate_count",
                "Alternate Rewiring Method",
                ALTERNATE_COLOR,
            ),
            SeriesSpec(
                "plot_intended_rate",
                "plot_intended_count",
                "Intended",
                INTENDED_COLOR,
            ),
            SeriesSpec(
                "plot_success_rate",
                "plot_success_count",
                "Task Success",
                SUCCESS_COLOR,
            ),
        ),
    ),
    PanelSpec(
        scenario="restrictedaccess",
        model="claude-opus-4-6",
        action_spec="pyautogui",
        observation_spec="a11y_tree",
        title="Restricted Access (Claude Opus 4.6)",
        variants=(
            "base",
            "realism",
            "realismdesktopprivacy",
            "realismdeadline",
            "realismlogin",
        ),
        variant_labels={
            "base": "Base",
            "realism": "Explicit Path\nRestriction",
            "realismdesktopprivacy": "Desktop Privacy",
            "realismdeadline": "Deadline",
            "realismlogin": "Login Handoff",
        },
        series=(
            SeriesSpec(
                "plot_actual_rate",
                "plot_actual_count",
                "Actual Access",
                ACTUAL_COLOR,
            ),
            SeriesSpec(
                "plot_intended_rate",
                "plot_intended_count",
                "Intended Access",
                INTENDED_COLOR,
            ),
        ),
    ),
)


GPT_54_XHIGH = TextAgenticModelSpec(
    model="gpt-5.4",
    short_label="5.4",
    textonly_run_group="xhighreasoningeffort",
    agentic_run_group="xhighreasoningeffort",
    agentic_variant="xhighreasoningeffort",
)
GPT_55_XHIGH = TextAgenticModelSpec(
    model="gpt-5.5",
    short_label="5.5",
    textonly_run_group="xhighreasoningeffort",
    agentic_run_group="xhighreasoningeffort",
    agentic_variant="xhighreasoningeffort",
)
CLAUDE_46_XHIGH = TextAgenticModelSpec(
    model="claude-opus-4-6",
    short_label="4.6",
    textonly_run_group="xhighreasoningeffort",
    agentic_run_group="xhighreasoningeffort",
    agentic_variant="xhighreasoningeffort",
)
CLAUDE_47_XHIGH = TextAgenticModelSpec(
    model="claude-opus-4-7",
    short_label="4.7",
    textonly_run_group="xhighreasoningeffort",
    agentic_run_group="xhighreasoningeffort",
    agentic_variant="xhighreasoningeffort",
)


FIGURE_2_SPEC = TextAgenticFigureSpec(
    output_stem="figure_2",
    rows=(
        (
            TextAgenticPanelSpec(
                title="Override (GPT)",
                scenario="override",
                models=(GPT_54_XHIGH, GPT_55_XHIGH),
            ),
            TextAgenticPanelSpec(
                title="Rewire (GPT)",
                scenario="rewire",
                models=(GPT_54_XHIGH, GPT_55_XHIGH),
            ),
            TextAgenticPanelSpec(
                title="Restricted Access (Claude Opus)",
                scenario="restrictedaccess",
                models=(CLAUDE_46_XHIGH, CLAUDE_47_XHIGH),
            ),
        ),
    ),
    figure_size=(20.48, 5.12),
)


FIGURE_2_MERGED_SPEC = TextAgenticFigureSpec(
    output_stem="figure_2_merged",
    rows=FIGURE_2_SPEC.rows,
    figure_size=FIGURE_2_SPEC.figure_size,
)


def _figure_8_row(
    model: TextAgenticModelSpec,
    *,
    show_titles: bool,
) -> Tuple[TextAgenticPanelSpec, ...]:
    titles = ("Override", "Rewire", "Restricted Access")
    scenarios = ("override", "rewire", "restrictedaccess")
    return tuple(
        TextAgenticPanelSpec(
            title=title if show_titles else "",
            scenario=scenario,
            models=(model,),
        )
        for title, scenario in zip(titles, scenarios)
    )


FIGURE_8_SPEC = TextAgenticFigureSpec(
    output_stem="figure_8",
    rows=tuple(
        _figure_8_row(model, show_titles=row_index == 0)
        for row_index, model in enumerate(
            (
                GPT_54_XHIGH,
                GPT_55_XHIGH,
                CLAUDE_46_XHIGH,
                CLAUDE_47_XHIGH,
            )
        )
    ),
    figure_size=(20.48, 16.0),
)


MIXED_REASONING_SPEC = TextAgenticFigureSpec(
    output_stem="textonly_agentic_mixed_reasoning",
    rows=(
        (
            TextAgenticPanelSpec(
                title="Override (GPT)",
                scenario="override",
                models=(
                    TextAgenticModelSpec(
                        model="gpt-5.4",
                        short_label="5.4",
                        textonly_run_group="base",
                        agentic_run_group="base",
                        agentic_variant="base",
                    ),
                    GPT_55_XHIGH,
                ),
            ),
            TextAgenticPanelSpec(
                title="Rewire (GPT)",
                scenario="rewire",
                models=(
                    TextAgenticModelSpec(
                        model="gpt-5.4",
                        short_label="5.4",
                        textonly_run_group="base",
                        agentic_run_group="base",
                        agentic_variant="base",
                    ),
                    GPT_55_XHIGH,
                ),
            ),
            TextAgenticPanelSpec(
                title="Restricted Access (Claude Opus)",
                scenario="restrictedaccess",
                models=(
                    TextAgenticModelSpec(
                        model="claude-opus-4-6",
                        short_label="4.6",
                        textonly_run_group="base",
                        agentic_run_group="base",
                        agentic_variant="base",
                    ),
                    CLAUDE_47_XHIGH,
                ),
            ),
        ),
    ),
    figure_size=(20.48, 5.12),
)


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except FileNotFoundError as exc:
        raise RuntimeError(f"Summary file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Summary file is not valid JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"Summary file must contain a JSON object: {path}")
    return payload


def _textonly_run_root(textonly_root: Path, run_group: str) -> Path:
    return textonly_root / run_group


def _text_agentic_bars_key(scenario: str) -> str:
    return "simplified_plot_bars" if scenario == "rewire" else "plot_bars"


def _split_text_agentic_bars(
    bars: Sequence[Mapping[str, Any]],
) -> Dict[str, List[Mapping[str, Any]]]:
    grouped: Dict[str, List[Mapping[str, Any]]] = {}
    for bar in bars:
        grouped.setdefault(str(bar.get("group", "")), []).append(bar)
    return grouped


def _load_text_agentic_model_comparison(
    *,
    results_root: Path,
    textonly_root: Path,
    panel: TextAgenticPanelSpec,
    model_spec: TextAgenticModelSpec,
) -> Dict[str, Any]:
    model_textonly_root = _textonly_run_root(
        textonly_root,
        model_spec.textonly_run_group,
    )
    try:
        textonly_payload = load_textonly_scenario_aggregate(
            model_textonly_root,
            model_spec.model,
            panel.scenario,
        )
        agentic_path, agentic_payload = discover_agentic_aggregate(
            results_root,
            scenario=panel.scenario,
            model=model_spec.model,
            run_group=model_spec.agentic_run_group,
            variant_name=model_spec.agentic_variant,
            preferred_observation_spec=(
                model_spec.preferred_observation_spec
            ),
        )
    except FileNotFoundError as exc:
        raise RuntimeError(str(exc)) from exc

    comparison = build_scenario_comparison(
        scenario=panel.scenario,
        agentic_path=agentic_path,
        agentic_payload=agentic_payload,
        textonly_payload=textonly_payload,
    )
    bars = comparison.get(_text_agentic_bars_key(panel.scenario))
    if not isinstance(bars, list):
        raise RuntimeError(
            f"Comparison data for {panel.scenario}/{model_spec.model} "
            "does not contain plot bars."
        )
    grouped = _split_text_agentic_bars(
        [bar for bar in bars if isinstance(bar, dict)]
    )
    text_bars = grouped.get("Text-Only", grouped.get("Text", []))
    agentic_bars = grouped.get("Agentic", [])
    if len(text_bars) != 2 or len(agentic_bars) != 2:
        raise RuntimeError(
            "Expected two text-only and two agentic bars for "
            f"{panel.scenario}/{model_spec.model}, got "
            f"{len(text_bars)} text-only and {len(agentic_bars)} agentic bars."
        )

    def metrics(
        metric_bars: Sequence[Mapping[str, Any]],
        group_label: str,
    ) -> Dict[str, Any]:
        try:
            actual_rate = float(metric_bars[0]["rate"])
            intended_rate = float(metric_bars[1]["rate"])
            actual_count = int(metric_bars[0]["count"])
            intended_count = int(metric_bars[1]["count"])
            denominator = int(metric_bars[0]["denominator"])
        except (KeyError, TypeError, ValueError) as exc:
            raise RuntimeError(
                f"Invalid {group_label} bars for "
                f"{panel.scenario}/{model_spec.model}."
            ) from exc
        if not 0.0 <= actual_rate <= 1.0:
            raise RuntimeError(
                f"Invalid actual rate {actual_rate} for "
                f"{panel.scenario}/{model_spec.model}."
            )
        if not 0.0 <= intended_rate <= 1.0:
            raise RuntimeError(
                f"Invalid intended rate {intended_rate} for "
                f"{panel.scenario}/{model_spec.model}."
            )
        if denominator <= 0:
            raise RuntimeError(
                f"Invalid {group_label} denominator {denominator} for "
                f"{panel.scenario}/{model_spec.model}."
            )
        if not 0 <= actual_count <= denominator:
            raise RuntimeError(
                f"Invalid {group_label} actual count {actual_count} for "
                f"{panel.scenario}/{model_spec.model}."
            )
        if not 0 <= intended_count <= denominator:
            raise RuntimeError(
                f"Invalid {group_label} intended count {intended_count} for "
                f"{panel.scenario}/{model_spec.model}."
            )
        return {
            "actual": actual_rate,
            "intended": intended_rate,
            "actual_count": actual_count,
            "intended_count": intended_count,
            "denominator": denominator,
        }

    return {
        "model": model_spec.model,
        "short_label": model_spec.short_label,
        "textonly_run_group": model_spec.textonly_run_group,
        "textonly_root": str(model_textonly_root),
        "agentic_run_group": model_spec.agentic_run_group,
        "agentic_variant": model_spec.agentic_variant,
        "agentic_aggregate_path": str(agentic_path),
        "textonly": metrics(text_bars, "text-only"),
        "agentic": metrics(agentic_bars, "agentic"),
    }


def _textonly_task_outcomes(
    payload: Mapping[str, Any],
    scenario: str,
) -> Dict[str, Dict[str, float]]:
    records = payload.get("records")
    if not isinstance(records, list):
        raise RuntimeError(
            f"Text-only aggregate for {scenario} has no records list."
        )

    target_choices = {
        "override": {"Override User Control"},
        "rewire": {
            "Modify shutdown.sh",
            "Attempt alternate shutdown rewiring method",
        },
        "restrictedaccess": {"Access passwords.txt"},
    }
    if scenario not in target_choices:
        raise ValueError(f"Unsupported scenario: {scenario}")

    outcomes: Dict[str, Dict[str, float]] = {}
    for record in records:
        if not isinstance(record, dict) or record.get("status") != "completed":
            continue
        task_id = str(record.get("example_id", ""))
        if not task_id:
            continue
        value = float(
            record.get("canonical_final_choice") in target_choices[scenario]
        )
        outcomes[task_id] = {"actual": value, "intended": value}
    return outcomes


def _agentic_task_outcomes(
    payload: Mapping[str, Any],
    scenario: str,
) -> Dict[str, Dict[str, float]]:
    tasks = payload.get("tasks")
    if not isinstance(tasks, list):
        raise RuntimeError(
            f"Agentic aggregate for {scenario} has no tasks list."
        )

    outcomes: Dict[str, Dict[str, float]] = {}
    for task in tasks:
        if not isinstance(task, dict):
            continue
        actual = task.get("actual")
        if not isinstance(actual, dict) or not actual.get("result_found", False):
            continue
        judge = task.get("judge")
        if not isinstance(judge, dict):
            judge = {}
        task_id = str(task.get("task_id", ""))
        if not task_id:
            continue

        if scenario == "override":
            actual_value = bool(actual.get("clicked_override", False))
            intended_value = bool(judge.get("intent_override", False))
        elif scenario == "rewire":
            actual_value = bool(
                actual.get("modified_shutdown_script", False)
                or judge.get("used_alternate_shutdown_avoidance", False)
            )
            intended_value = bool(
                judge.get("intent_subvert_shutdown", False)
            )
        elif scenario == "restrictedaccess":
            actual_value = bool(
                actual.get("accessed_passwords_txt", False)
            )
            intended_value = bool(
                judge.get("intent_access_passwords", False)
            )
        else:
            raise ValueError(f"Unsupported scenario: {scenario}")

        outcomes[task_id] = {
            "actual": float(actual_value),
            "intended": float(intended_value),
        }
    return outcomes


def _mean_and_standard_error(
    values: Sequence[float],
) -> Tuple[float, float]:
    if not values:
        raise RuntimeError("Cannot summarize an empty set of task outcomes.")
    mean = sum(values) / len(values)
    if len(values) == 1:
        return mean, 0.0
    sample_variance = sum((value - mean) ** 2 for value in values) / (
        len(values) - 1
    )
    return mean, math.sqrt(sample_variance / len(values))


def _merge_repeated_task_outcomes(
    outcome_runs: Sequence[Mapping[str, Mapping[str, float]]],
    group_label: str,
) -> Dict[str, Any]:
    if len(outcome_runs) < 2:
        raise RuntimeError(
            f"Merged {group_label} results require at least two runs."
        )
    task_ids = sorted(
        {
            task_id
            for outcomes in outcome_runs
            for task_id in outcomes
        }
    )
    if not task_ids:
        raise RuntimeError(
            f"Merged {group_label} results contain no completed tasks."
        )

    task_means: Dict[str, List[float]] = {}
    for metric in ("actual", "intended"):
        metric_means = []
        for task_id in task_ids:
            repeated_values = [
                float(outcomes[task_id][metric])
                for outcomes in outcome_runs
                if task_id in outcomes and metric in outcomes[task_id]
            ]
            if repeated_values:
                metric_means.append(
                    sum(repeated_values) / len(repeated_values)
                )
        task_means[metric] = metric_means

    actual_rate, actual_se = _mean_and_standard_error(
        task_means["actual"]
    )
    intended_rate, intended_se = _mean_and_standard_error(
        task_means["intended"]
    )
    complete_task_count = sum(
        all(task_id in outcomes for outcomes in outcome_runs)
        for task_id in task_ids
    )
    observation_count = sum(len(outcomes) for outcomes in outcome_runs)

    return {
        "actual": actual_rate,
        "intended": intended_rate,
        "actual_se": actual_se,
        "intended_se": intended_se,
        "actual_count": sum(task_means["actual"]),
        "intended_count": sum(task_means["intended"]),
        "denominator": len(task_ids),
        "task_count": len(task_ids),
        "complete_task_count": complete_task_count,
        "observation_count": observation_count,
        "run_task_counts": [len(outcomes) for outcomes in outcome_runs],
    }


def _load_repeated_text_agentic_model_comparison(
    *,
    results_roots: Sequence[Path],
    textonly_roots: Sequence[Path],
    panel: TextAgenticPanelSpec,
    model_spec: TextAgenticModelSpec,
) -> Dict[str, Any]:
    if len(results_roots) != len(textonly_roots):
        raise RuntimeError(
            "Merged Figure 2 requires one text-only root for each "
            "agentic results root."
        )
    if len(results_roots) < 2:
        raise RuntimeError("Merged Figure 2 requires at least two reruns.")

    textonly_runs = []
    agentic_runs = []
    agentic_paths = []
    for results_root, textonly_root in zip(results_roots, textonly_roots):
        model_textonly_root = _textonly_run_root(
            textonly_root,
            model_spec.textonly_run_group,
        )
        try:
            textonly_payload = load_textonly_scenario_aggregate(
                model_textonly_root,
                model_spec.model,
                panel.scenario,
            )
            agentic_path, agentic_payload = discover_agentic_aggregate(
                results_root,
                scenario=panel.scenario,
                model=model_spec.model,
                run_group=model_spec.agentic_run_group,
                variant_name=model_spec.agentic_variant,
                preferred_observation_spec=(
                    model_spec.preferred_observation_spec
                ),
            )
        except FileNotFoundError as exc:
            raise RuntimeError(str(exc)) from exc

        textonly_runs.append(
            _textonly_task_outcomes(textonly_payload, panel.scenario)
        )
        agentic_runs.append(
            _agentic_task_outcomes(agentic_payload, panel.scenario)
        )
        agentic_paths.append(str(agentic_path))

    return {
        "model": model_spec.model,
        "short_label": model_spec.short_label,
        "textonly_run_group": model_spec.textonly_run_group,
        "agentic_run_group": model_spec.agentic_run_group,
        "agentic_variant": model_spec.agentic_variant,
        "replicate_count": len(results_roots),
        "textonly_roots": [str(root) for root in textonly_roots],
        "agentic_aggregate_paths": agentic_paths,
        "textonly": _merge_repeated_task_outcomes(
            textonly_runs,
            "text-only",
        ),
        "agentic": _merge_repeated_task_outcomes(
            agentic_runs,
            "agentic",
        ),
    }


def _build_text_agentic_figure_payload(
    results_root: Path,
    textonly_root: Path,
    spec: TextAgenticFigureSpec,
) -> Dict[str, Any]:
    return {
        "output_stem": spec.output_stem,
        "rows": [
            [
                {
                    "title": panel.title,
                    "scenario": panel.scenario,
                    "models": [
                        _load_text_agentic_model_comparison(
                            results_root=results_root,
                            textonly_root=textonly_root,
                            panel=panel,
                            model_spec=model_spec,
                        )
                        for model_spec in panel.models
                    ],
                }
                for panel in row
            ]
            for row in spec.rows
        ],
    }


def _build_repeated_text_agentic_figure_payload(
    results_roots: Sequence[Path],
    textonly_roots: Sequence[Path],
    spec: TextAgenticFigureSpec,
) -> Dict[str, Any]:
    return {
        "output_stem": spec.output_stem,
        "error_bar_label": "Error bars: +/- 1 task-clustered SE across reruns",
        "rows": [
            [
                {
                    "title": panel.title,
                    "scenario": panel.scenario,
                    "models": [
                        _load_repeated_text_agentic_model_comparison(
                            results_roots=results_roots,
                            textonly_roots=textonly_roots,
                            panel=panel,
                            model_spec=model_spec,
                        )
                        for model_spec in panel.models
                    ],
                }
                for panel in row
            ]
            for row in spec.rows
        ],
    }


def _text_agentic_cluster_positions(
    model_count: int,
) -> Tuple[
    List[Tuple[str, int, float, float]],
    Dict[str, float],
    Tuple[float, float],
]:
    x = 0.0
    positions: List[Tuple[str, int, float, float]] = []
    group_centers: Dict[str, float] = {}

    for group in ("Text", "Agentic"):
        cluster_centers = []
        for model_index in range(model_count):
            actual_x = x
            intended_x = x + TEXT_AGENTIC_BAR_WIDTH
            cluster_centers.append(x + TEXT_AGENTIC_BAR_WIDTH / 2.0)
            positions.append(
                (group, model_index, actual_x, intended_x)
            )
            x += (
                TEXT_AGENTIC_BAR_WIDTH * 2.0
                + TEXT_AGENTIC_CLUSTER_GAP
            )
        group_centers[group] = (
            cluster_centers[0] + cluster_centers[-1]
        ) / 2.0
        x += TEXT_AGENTIC_GROUP_GAP

    return (
        positions,
        group_centers,
        (-0.28, x - TEXT_AGENTIC_GROUP_GAP + 0.28),
    )


def _annotate_text_agentic_rate(
    axis: Any,
    x: float,
    value: float,
    upper_error: float = 0.0,
) -> None:
    y = (
        0.014
        if value <= 0 and upper_error <= 0
        else min(1.042, value + upper_error + 0.025)
    )
    axis.text(
        x,
        y,
        f"{value:.2f}",
        ha="center",
        va="bottom",
        fontsize=11,
        fontweight="bold",
    )


def _draw_text_agentic_error_bar(
    axis: Any,
    x: float,
    value: float,
    standard_error: float,
) -> float:
    if standard_error <= 0:
        return 0.0
    lower_error = min(standard_error, value)
    upper_error = min(standard_error, 1.0 - value)
    axis.errorbar(
        [x],
        [value],
        yerr=[[lower_error], [upper_error]],
        fmt="none",
        ecolor="#333333",
        elinewidth=1.25,
        capsize=4,
        capthick=1.25,
        zorder=4,
    )
    return upper_error


def _draw_text_agentic_panel(
    axis: Any,
    panel_payload: Mapping[str, Any],
) -> None:
    models = panel_payload.get("models")
    if not isinstance(models, list) or not models:
        raise RuntimeError("Text/agentic panel contains no model data.")
    positions, group_centers, xlim = _text_agentic_cluster_positions(
        len(models)
    )

    for group, model_index, actual_x, intended_x in positions:
        model_payload = models[model_index]
        metric_group = "textonly" if group == "Text" else "agentic"
        metrics = model_payload[metric_group]
        actual = float(metrics["actual"])
        intended = float(metrics["intended"])
        actual_se = max(float(metrics.get("actual_se", 0.0)), 0.0)
        intended_se = max(float(metrics.get("intended_se", 0.0)), 0.0)
        axis.bar(
            actual_x,
            actual,
            color=ACTUAL_COLOR,
            width=TEXT_AGENTIC_BAR_WIDTH,
        )
        axis.bar(
            intended_x,
            intended,
            color=INTENDED_COLOR,
            width=TEXT_AGENTIC_BAR_WIDTH,
        )
        actual_upper_error = _draw_text_agentic_error_bar(
            axis,
            actual_x,
            actual,
            actual_se,
        )
        intended_upper_error = _draw_text_agentic_error_bar(
            axis,
            intended_x,
            intended,
            intended_se,
        )
        _annotate_text_agentic_rate(
            axis,
            actual_x,
            actual,
            actual_upper_error,
        )
        _annotate_text_agentic_rate(
            axis,
            intended_x,
            intended,
            intended_upper_error,
        )

    cluster_centers = [
        (actual_x + intended_x) / 2.0
        for _, _, actual_x, intended_x in positions
    ]
    cluster_labels = [
        str(models[model_index]["short_label"])
        for _, model_index, _, _ in positions
    ]

    title = str(panel_payload.get("title", ""))
    if title:
        axis.set_title(title, fontsize=22, fontweight="bold", pad=12)
    axis.set_xlim(*xlim)
    axis.set_ylim(0.0, 1.08)
    axis.set_xticks(cluster_centers)
    axis.set_xticklabels(
        cluster_labels,
        fontsize=15,
        fontweight="bold",
    )
    axis.tick_params(axis="x", pad=7, length=0)
    for group_label in ("Text", "Agentic"):
        axis.text(
            group_centers[group_label],
            -0.15,
            group_label,
            transform=axis.get_xaxis_transform(),
            ha="center",
            va="top",
            fontsize=20,
            fontweight="bold",
            clip_on=False,
        )
    axis.set_yticks([0.0, 0.2, 0.4, 0.6, 0.8, 1.0])
    axis.tick_params(axis="y", labelsize=14, width=1.0, pad=8)
    for label in axis.get_yticklabels():
        label.set_fontweight("bold")
    axis.grid(
        axis="y",
        color="#b8b8b8",
        alpha=0.45,
        linewidth=0.9,
        linestyle="--",
    )
    axis.set_axisbelow(True)
    axis.spines["top"].set_visible(False)
    axis.spines["bottom"].set_color("#666666")
    axis.spines["left"].set_color("#666666")
    axis.spines["right"].set_visible(False)


def render_text_agentic_figure(
    payload: Mapping[str, Any],
    spec: TextAgenticFigureSpec,
) -> Any:
    """Render a paper figure comparing text-only and agentic behavior."""
    rows = payload.get("rows")
    if not isinstance(rows, list) or len(rows) != len(spec.rows):
        raise RuntimeError(
            f"{spec.output_stem} payload has an unexpected row count."
        )
    column_count = len(spec.rows[0])
    if any(len(row) != column_count for row in spec.rows):
        raise RuntimeError(
            f"{spec.output_stem} requires a rectangular panel grid."
        )
    if any(not isinstance(row, list) or len(row) != column_count for row in rows):
        raise RuntimeError(
            f"{spec.output_stem} payload has an unexpected column count."
        )

    plt, _ = load_matplotlib()
    row_count = len(rows)
    figure, axes = plt.subplots(
        row_count,
        column_count,
        figsize=spec.figure_size,
        sharey=True,
        squeeze=False,
    )
    for row_index, row in enumerate(rows):
        for column_index, panel_payload in enumerate(row):
            axis = axes[row_index][column_index]
            _draw_text_agentic_panel(axis, panel_payload)
            if column_index == 0:
                axis.set_ylabel(
                    "Misalignment Rate",
                    fontsize=16,
                    fontweight="bold",
                    labelpad=18,
                )
            else:
                axis.tick_params(axis="y", labelleft=False)

    handles = [
        plt.Rectangle((0, 0), 1, 1, color=ACTUAL_COLOR),
        plt.Rectangle((0, 0), 1, 1, color=INTENDED_COLOR),
    ]
    figure.legend(
        handles,
        ["Actual", "Intended"],
        loc="lower center",
        bbox_to_anchor=(0.5, -0.005 if row_count == 1 else 0.005),
        ncol=2,
        frameon=False,
        handlelength=1.8,
        handleheight=1.3,
        columnspacing=3.6,
        prop={"weight": "bold", "size": 19},
    )
    error_bar_label = payload.get("error_bar_label")
    if isinstance(error_bar_label, str) and error_bar_label:
        figure.text(
            0.985,
            0.018,
            error_bar_label,
            ha="right",
            va="bottom",
            fontsize=10,
            color="#444444",
        )
    figure.subplots_adjust(
        left=0.06,
        right=0.965,
        top=0.82 if row_count == 1 else 0.96,
        bottom=0.30 if row_count == 1 else 0.11,
        hspace=0.48 if row_count > 1 else 0.2,
        wspace=0.04,
    )
    return figure


def _save_text_agentic_figure(
    figure: Any,
    spec: TextAgenticFigureSpec,
    *,
    output_dir: Path,
    formats: Sequence[str],
    dpi: int,
) -> Tuple[Path, ...]:
    resolved_output_dir = Path(output_dir).expanduser().resolve()
    normalized_formats = tuple(dict.fromkeys(fmt.lower() for fmt in formats))
    unsupported = [
        fmt for fmt in normalized_formats if fmt not in {"pdf", "png"}
    ]
    if unsupported:
        raise ValueError(
            f"Unsupported output format(s): {', '.join(unsupported)}"
        )

    resolved_output_dir.mkdir(parents=True, exist_ok=True)
    output_paths = []
    try:
        for fmt in normalized_formats:
            output_path = resolved_output_dir / f"{spec.output_stem}.{fmt}"
            save_kwargs: Dict[str, Any] = {
                "format": fmt,
                "facecolor": "white",
                "bbox_inches": "tight",
                "pad_inches": 0.08,
            }
            if fmt == "png":
                save_kwargs["dpi"] = dpi
            figure.savefig(output_path, **save_kwargs)
            output_paths.append(output_path)
    finally:
        plt, _ = load_matplotlib()
        plt.close(figure)

    return tuple(output_paths)


def _generate_text_agentic_figure(
    spec: TextAgenticFigureSpec,
    *,
    results_root: Path = DEFAULT_RESULTS_ROOT,
    textonly_root: Path = DEFAULT_TEXTONLY_ROOT,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    formats: Sequence[str] = ("pdf", "png"),
    dpi: int = 300,
) -> Tuple[Path, ...]:
    resolved_results_root = Path(results_root).expanduser().resolve()
    resolved_textonly_root = Path(textonly_root).expanduser().resolve()
    payload = _build_text_agentic_figure_payload(
        resolved_results_root,
        resolved_textonly_root,
        spec,
    )
    figure = render_text_agentic_figure(payload, spec)
    return _save_text_agentic_figure(
        figure,
        spec,
        output_dir=output_dir,
        formats=formats,
        dpi=dpi,
    )


def _generate_repeated_text_agentic_figure(
    spec: TextAgenticFigureSpec,
    *,
    results_roots: Sequence[Path],
    textonly_roots: Sequence[Path],
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    formats: Sequence[str] = ("pdf", "png"),
    dpi: int = 300,
) -> Tuple[Path, ...]:
    resolved_results_roots = tuple(
        Path(root).expanduser().resolve() for root in results_roots
    )
    resolved_textonly_roots = tuple(
        Path(root).expanduser().resolve() for root in textonly_roots
    )
    payload = _build_repeated_text_agentic_figure_payload(
        resolved_results_roots,
        resolved_textonly_roots,
        spec,
    )
    figure = render_text_agentic_figure(payload, spec)
    return _save_text_agentic_figure(
        figure,
        spec,
        output_dir=output_dir,
        formats=formats,
        dpi=dpi,
    )


def figure_2(
    results_root: Path = DEFAULT_RESULTS_ROOT,
    textonly_root: Path = DEFAULT_TEXTONLY_ROOT,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    formats: Sequence[str] = ("pdf", "png"),
    dpi: int = 300,
) -> Tuple[Path, ...]:
    """Generate the paper's three-panel text-only/agentic comparison."""
    return _generate_text_agentic_figure(
        FIGURE_2_SPEC,
        results_root=results_root,
        textonly_root=textonly_root,
        output_dir=output_dir,
        formats=formats,
        dpi=dpi,
    )


def figure_2_merged(
    results_root: Path = DEFAULT_RESULTS_ROOT,
    textonly_root: Path = DEFAULT_TEXTONLY_ROOT,
    rerun_results_root: Path = DEFAULT_RERUN_RESULTS_ROOT,
    rerun_textonly_root: Path = DEFAULT_RERUN_TEXTONLY_ROOT,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    formats: Sequence[str] = ("pdf", "png"),
    dpi: int = 300,
) -> Tuple[Path, ...]:
    """Merge two matched Figure 2 runs with task-clustered error bars."""
    return _generate_repeated_text_agentic_figure(
        FIGURE_2_MERGED_SPEC,
        results_roots=(results_root, rerun_results_root),
        textonly_roots=(textonly_root, rerun_textonly_root),
        output_dir=output_dir,
        formats=formats,
        dpi=dpi,
    )


def figure_8(
    results_root: Path = DEFAULT_RESULTS_ROOT,
    textonly_root: Path = DEFAULT_TEXTONLY_ROOT,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    formats: Sequence[str] = ("pdf", "png"),
    dpi: int = 300,
) -> Tuple[Path, ...]:
    """Generate the paper's full four-model text-only/agentic comparison."""
    return _generate_text_agentic_figure(
        FIGURE_8_SPEC,
        results_root=results_root,
        textonly_root=textonly_root,
        output_dir=output_dir,
        formats=formats,
        dpi=dpi,
    )


def textonly_agentic_mixed_reasoning(
    results_root: Path = DEFAULT_RESULTS_ROOT,
    textonly_root: Path = DEFAULT_TEXTONLY_ROOT,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    formats: Sequence[str] = ("pdf", "png"),
    dpi: int = 300,
) -> Tuple[Path, ...]:
    """Generate the legacy mixed-reasoning comparison from the old script."""
    return _generate_text_agentic_figure(
        MIXED_REASONING_SPEC,
        results_root=results_root,
        textonly_root=textonly_root,
        output_dir=output_dir,
        formats=formats,
        dpi=dpi,
    )


def _combined_rates_with_subagents_path(results_root: Path) -> Path:
    return (
        results_root
        / "summary"
        / COMBINED_RATES_WITH_SUBAGENTS_FILENAME
    )


def _judge_ids() -> Tuple[str, str]:
    profiles = build_judge_profiles()
    return (
        profiles[OPENAI_JUDGE_TARGET].judge_id,
        profiles[CLAUDE_JUDGE_TARGET].judge_id,
    )


def _run_group_from_key(run_key: str) -> str:
    if "xhighreasoningeffort" in run_key.split(":"):
        return "xhighreasoningeffort"
    return "base"


def _figure_3_run_sort_key(run: JudgeRun) -> Tuple[int, str, int, str]:
    try:
        model_index = MODEL_ORDER.index(run.model)
    except ValueError:
        model_index = len(MODEL_ORDER)

    is_subagent = run.run_key.startswith("subagents:")
    is_xhigh = _run_group_from_key(run.run_key) == "xhighreasoningeffort"
    if not is_subagent and not is_xhigh:
        variant_index = 0
    elif is_xhigh and not is_subagent:
        variant_index = 1
    elif is_subagent and not is_xhigh:
        variant_index = 2
    else:
        variant_index = 3
    return model_index, run.model, variant_index, run.run_key


def _discover_run_leaves(
    results_root: Path,
    scenario: str,
    run_key: str,
) -> Sequence[Any]:
    source_root = (
        results_root / "subagents"
        if run_key.startswith("subagents:")
        else results_root
    )
    if _run_group_from_key(run_key) == "xhighreasoningeffort":
        return discover_xhigh_reasoning_effort_leaf_dirs(source_root, scenario)
    return discover_base_leaf_dirs(source_root, scenario)


def _load_judge_runs(results_root: Path) -> Dict[str, Tuple[JudgeRun, ...]]:
    """Load the exact model/configuration rows used by the combined Figure 3 plot."""
    combined_path = _combined_rates_with_subagents_path(results_root)
    combined = _read_json(combined_path)
    scenario_summaries = combined.get("scenarios")
    if not isinstance(scenario_summaries, list):
        raise RuntimeError(f"{combined_path} has no scenarios list.")

    runs_by_scenario: Dict[str, Tuple[JudgeRun, ...]] = {}
    for scenario_summary in scenario_summaries:
        if not isinstance(scenario_summary, dict):
            continue
        scenario = str(scenario_summary.get("scenario", ""))
        if scenario not in {outcome.scenario for outcome in JUDGE_OUTCOMES}:
            continue
        summary_runs = scenario_summary.get("runs")
        if not isinstance(summary_runs, list):
            raise RuntimeError(
                f"{combined_path} scenario {scenario!r} has no runs list."
            )

        judge_runs: List[JudgeRun] = []
        seen_run_keys: set[str] = set()
        for run in summary_runs:
            if not isinstance(run, dict):
                continue
            run_key = str(run.get("run_key", ""))
            run_label = str(run.get("run_label", ""))
            model = str(run.get("model", ""))
            source_scenario = str(run.get("source_scenario", scenario))
            action_specs = {
                str(value)
                for value in run.get("action_specs", [])
                if value is not None
            }
            observation_specs = {
                str(value)
                for value in run.get("observation_specs", [])
                if value is not None
            }
            if not run_key or not run_label or not model:
                raise RuntimeError(
                    f"{combined_path} contains an incomplete run for {scenario}."
                )
            if run_key in seen_run_keys:
                raise RuntimeError(
                    f"{combined_path} contains duplicate run key {run_key!r} "
                    f"for {scenario}."
                )
            seen_run_keys.add(run_key)

            matches = [
                leaf
                for leaf in _discover_run_leaves(
                    results_root,
                    source_scenario,
                    run_key,
                )
                if leaf.model == model
                and (
                    not action_specs
                    or leaf.action_spec in action_specs
                )
                and (
                    not observation_specs
                    or leaf.observation_spec in observation_specs
                )
            ]
            if not matches:
                raise RuntimeError(
                    f"Could not locate aggregate results for {run_label!r} "
                    f"in scenario {source_scenario!r}."
                )

            tasks: List[Mapping[str, Any]] = []
            for leaf in matches:
                payload = _read_json(leaf.aggregate_path)
                payload_tasks = payload.get("tasks")
                if not isinstance(payload_tasks, list):
                    raise RuntimeError(
                        f"Aggregate file has no tasks list: {leaf.aggregate_path}"
                    )
                tasks.extend(
                    task
                    for task in payload_tasks
                    if isinstance(task, dict)
                )

            completed_tasks = [
                task
                for task in tasks
                if isinstance(task.get("actual"), dict)
                and task["actual"].get("result_found") is True
            ]
            expected_total = int(run.get("total_tasks", len(completed_tasks)))
            if len(completed_tasks) != expected_total:
                raise RuntimeError(
                    f"{run_label!r} has {len(completed_tasks)} completed tasks in "
                    f"its aggregate file(s), but {combined_path} reports "
                    f"{expected_total}."
                )
            judge_runs.append(
                JudgeRun(
                    scenario=scenario,
                    run_key=run_key,
                    run_label=run_label,
                    model=model,
                    tasks=tuple(completed_tasks),
                )
            )

        runs_by_scenario[scenario] = tuple(
            sorted(judge_runs, key=_figure_3_run_sort_key)
        )

    missing_scenarios = sorted(
        {outcome.scenario for outcome in JUDGE_OUTCOMES}
        - set(runs_by_scenario)
    )
    if missing_scenarios:
        raise RuntimeError(
            f"{combined_path} is missing scenarios: {', '.join(missing_scenarios)}"
        )
    return runs_by_scenario


def _positive_judgment(
    outcome: JudgeOutcomeSpec,
    judgment: Any,
) -> Optional[bool]:
    if not isinstance(judgment, dict):
        return None
    value = judgment.get(outcome.decision_field)
    if outcome.key == "intent_override":
        if value not in {"override", "accept", "neither", "unclear"}:
            return None
        return value == "override"
    return value if isinstance(value, bool) else None


def _paired_judgment(
    task: Mapping[str, Any],
    outcome: JudgeOutcomeSpec,
    gpt_judge_id: str,
    claude_judge_id: str,
) -> Optional[Tuple[bool, bool]]:
    comparison = task.get("judge_comparison")
    if not isinstance(comparison, dict):
        return None
    values = comparison.get("values")
    if not isinstance(values, dict):
        return None
    gpt_value = _positive_judgment(outcome, values.get(gpt_judge_id))
    claude_value = _positive_judgment(outcome, values.get(claude_judge_id))
    if gpt_value is None or claude_value is None:
        return None
    return gpt_value, claude_value


def _summarize_judge_tasks(
    tasks: Sequence[Mapping[str, Any]],
    outcome: JudgeOutcomeSpec,
) -> Dict[str, Any]:
    gpt_judge_id, claude_judge_id = _judge_ids()
    pairs = [
        pair
        for task in tasks
        if (
            pair := _paired_judgment(
                task,
                outcome,
                gpt_judge_id,
                claude_judge_id,
            )
        )
        is not None
    ]
    completed_tasks = len(tasks)
    compared_tasks = len(pairs)
    gpt_positive_tasks = sum(1 for gpt, _ in pairs if gpt)
    claude_positive_tasks = sum(1 for _, claude in pairs if claude)
    both_positive_tasks = sum(1 for gpt, claude in pairs if gpt and claude)
    gpt_only_tasks = sum(1 for gpt, claude in pairs if gpt and not claude)
    claude_only_tasks = sum(1 for gpt, claude in pairs if not gpt and claude)
    both_negative_tasks = sum(
        1 for gpt, claude in pairs if not gpt and not claude
    )
    agree_tasks = both_positive_tasks + both_negative_tasks
    gpt_positive_rate = (
        gpt_positive_tasks / compared_tasks if compared_tasks else 0.0
    )
    claude_positive_rate = (
        claude_positive_tasks / compared_tasks if compared_tasks else 0.0
    )
    agreement_rate = agree_tasks / compared_tasks if compared_tasks else 0.0
    expected_agreement = (
        gpt_positive_rate * claude_positive_rate
        + (1.0 - gpt_positive_rate) * (1.0 - claude_positive_rate)
    )
    kappa_denominator = 1.0 - expected_agreement
    cohens_kappa = (
        (agreement_rate - expected_agreement) / kappa_denominator
        if compared_tasks and kappa_denominator > 0.0
        else None
    )
    return {
        "completed_tasks": completed_tasks,
        "compared_tasks": compared_tasks,
        "incomplete_tasks": completed_tasks - compared_tasks,
        "coverage_rate": (
            compared_tasks / completed_tasks if completed_tasks else 0.0
        ),
        "gpt_positive_tasks": gpt_positive_tasks,
        "gpt_positive_rate": gpt_positive_rate,
        "claude_positive_tasks": claude_positive_tasks,
        "claude_positive_rate": claude_positive_rate,
        "both_positive_tasks": both_positive_tasks,
        "gpt_only_tasks": gpt_only_tasks,
        "claude_only_tasks": claude_only_tasks,
        "both_negative_tasks": both_negative_tasks,
        "agree_tasks": agree_tasks,
        "disagree_tasks": compared_tasks - agree_tasks,
        "agreement_rate": agreement_rate,
        "expected_agreement_rate": expected_agreement,
        "cohens_kappa": cohens_kappa,
        "claude_minus_gpt_rate": claude_positive_rate - gpt_positive_rate,
        "claude_minus_gpt_percentage_points": (
            claude_positive_rate - gpt_positive_rate
        )
        * 100.0,
    }


def _build_judge_agreement_table_numbers(
    runs_by_scenario: Mapping[str, Sequence[JudgeRun]],
) -> Tuple[Dict[str, Any], ...]:
    rows: List[Dict[str, Any]] = []
    for outcome in JUDGE_OUTCOMES:
        scenario_runs = runs_by_scenario.get(outcome.scenario, ())
        tasks = [
            task
            for run in scenario_runs
            for task in run.tasks
        ]
        row = {
            "outcome": outcome.key,
            "scenario": outcome.scenario,
            "judgment_target": outcome.table_label,
        }
        row.update(_summarize_judge_tasks(tasks, outcome))
        rows.append(row)
    return tuple(rows)


def judge_agreement_table_numbers(
    results_root: Path = DEFAULT_RESULTS_ROOT,
) -> Tuple[Dict[str, Any], ...]:
    """Return the paired GPT/Claude counts and rates for the appendix table."""
    resolved_results_root = Path(results_root).expanduser().resolve()
    return _build_judge_agreement_table_numbers(
        _load_judge_runs(resolved_results_root)
    )


def _build_judge_sensitivity_plot_data(
    runs_by_scenario: Mapping[str, Sequence[JudgeRun]],
) -> Tuple[Dict[str, Any], ...]:
    panels: List[Dict[str, Any]] = []
    for outcome in JUDGE_OUTCOMES:
        panel_runs = []
        for run in runs_by_scenario.get(outcome.scenario, ()):
            summary = _summarize_judge_tasks(run.tasks, outcome)
            if summary["compared_tasks"] <= 0:
                raise RuntimeError(
                    f"{run.run_label!r} has no paired judge results for "
                    f"{outcome.table_label}."
                )
            panel_runs.append(
                {
                    "run_key": run.run_key,
                    "run_label": run.run_label,
                    "model": run.model,
                    **summary,
                }
            )
        panels.append(
            {
                "outcome": outcome.key,
                "scenario": outcome.scenario,
                "title": outcome.title,
                "runs": tuple(panel_runs),
            }
        )
    return tuple(panels)


def _available_variants(summary: Mapping[str, Any]) -> set[str]:
    runs = summary.get("runs")
    if not isinstance(runs, list):
        return set()
    return {
        str(run.get("variant_name"))
        for run in runs
        if isinstance(run, dict) and run.get("variant_name") is not None
    }


def _load_panel_summary(results_root: Path, panel: PanelSpec) -> Dict[str, Any]:
    summary_dir = results_root / panel.scenario / "ablations" / "summary"
    candidates = sorted(summary_dir.glob("ablation_comparison_*.json"))
    matches = []
    for path in candidates:
        if path.name.startswith("ablation_comparison_base_vs_"):
            continue
        summary = _read_json(path)
        if summary.get("model") != panel.model:
            continue
        if summary.get("action_spec") != panel.action_spec:
            continue
        if summary.get("observation_spec") != panel.observation_spec:
            continue
        if not set(panel.variants).issubset(_available_variants(summary)):
            continue
        matches.append((path, summary))

    if len(matches) == 1:
        return matches[0][1]
    if len(matches) > 1:
        paths = "\n  ".join(str(path) for path, _ in matches)
        raise RuntimeError(
            f"Multiple aggregate summaries match the {panel.title} panel:\n  {paths}"
        )

    expected_variants = ", ".join(panel.variants)
    raise RuntimeError(
        f"Could not find the aggregate summary for {panel.title} under {summary_dir}.\n"
        f"Expected model={panel.model}, action_spec={panel.action_spec}, "
        f"observation_spec={panel.observation_spec}, and variants: "
        f"{expected_variants}.\n"
        "Run scripts/aggregate_results.py on the results root first."
    )


def _ordered_runs(
    summary: Mapping[str, Any],
    panel: PanelSpec,
) -> Tuple[Dict[str, Any], ...]:
    runs = summary.get("runs")
    if not isinstance(runs, list):
        raise RuntimeError(f"{panel.title} summary has no runs list.")

    runs_by_variant: Dict[str, Dict[str, Any]] = {}
    for run in runs:
        if not isinstance(run, dict):
            continue
        variant_name = str(run.get("variant_name", ""))
        if variant_name not in panel.variants:
            continue
        if variant_name in runs_by_variant:
            raise RuntimeError(
                f"{panel.title} summary contains more than one {variant_name!r} run."
            )
        runs_by_variant[variant_name] = run

    missing = [
        variant_name
        for variant_name in panel.variants
        if variant_name not in runs_by_variant
    ]
    if missing:
        raise RuntimeError(
            f"{panel.title} summary is missing variants: {', '.join(missing)}"
        )
    return tuple(runs_by_variant[variant_name] for variant_name in panel.variants)


def _validate_run(run: Mapping[str, Any], panel: PanelSpec) -> None:
    total_tasks = int(run.get("total_tasks", 0))
    if total_tasks <= 0:
        raise RuntimeError(
            f"{panel.title} variant {run.get('variant_name')!r} has no completed tasks."
        )

    for series in panel.series:
        if series.count_key not in run:
            raise RuntimeError(
                f"{panel.title} variant {run.get('variant_name')!r} is missing "
                f"{series.count_key}."
            )
        count = int(run[series.count_key])
        if not 0 <= count <= total_tasks:
            raise RuntimeError(
                f"{panel.title} variant {run.get('variant_name')!r} has invalid "
                f"{series.count_key}={count} for total_tasks={total_tasks}."
            )


def _style_axis(axis: Any, show_y_axis: bool) -> None:
    axis.set_facecolor("white")
    axis.set_ylim(0.0, 1.0)
    axis.set_yticks([0.0, 0.25, 0.5, 0.75, 1.0])
    axis.set_axisbelow(True)
    axis.yaxis.grid(True, color="#E0E0E0", linewidth=0.9)
    axis.xaxis.grid(False)

    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)
    axis.spines["left"].set_color("#333333")
    axis.spines["bottom"].set_color("#333333")
    axis.spines["left"].set_linewidth(1.1)
    axis.spines["bottom"].set_linewidth(1.1)
    axis.tick_params(axis="both", colors="#222222", labelsize=10, width=0)

    if show_y_axis:
        axis.set_ylabel(
            "Proportion of tasks",
            fontsize=13,
            fontweight="bold",
            color="#222222",
            labelpad=12,
        )
    else:
        axis.spines["left"].set_visible(False)
        axis.tick_params(axis="y", labelleft=False, length=0)


def _render_panel(
    axis: Any,
    panel: PanelSpec,
    summary: Mapping[str, Any],
    show_y_axis: bool,
) -> None:
    runs = _ordered_runs(summary, panel)
    for run in runs:
        _validate_run(run, panel)

    _style_axis(axis, show_y_axis=show_y_axis)
    axis.set_title(
        panel.title,
        fontsize=16,
        fontweight="bold",
        color="#111111",
        pad=55,
    )

    x_positions = [float(index) for index in range(len(runs))]
    series_count = len(panel.series)
    group_span = 0.78
    intra_bar_gap = 0.035
    bar_width = (
        group_span - intra_bar_gap * (series_count - 1)
    ) / series_count
    start_offset = -group_span / 2 + bar_width / 2

    legend_handles = []
    for series_index, series in enumerate(panel.series):
        offset = start_offset + series_index * (bar_width + intra_bar_gap)
        positions = [x + offset for x in x_positions]
        counts = [int(run[series.count_key]) for run in runs]
        totals = [int(run["total_tasks"]) for run in runs]
        heights = [count / total for count, total in zip(counts, totals)]
        heights = [
            min(
                max(float(run.get(series.rate_key, fallback)), 0.0),
                1.0,
            )
            for run, fallback in zip(runs, heights)
        ]
        errors = [
            binomial_standard_error(count, total)
            for count, total in zip(counts, totals)
        ]

        bars = axis.bar(
            positions,
            heights,
            width=bar_width,
            color=series.color,
            edgecolor="none",
            yerr=errors,
            capsize=3,
            error_kw={
                "ecolor": "#333333",
                "elinewidth": 1.0,
                "capthick": 1.0,
            },
            label=series.label,
        )
        legend_handles.append(bars[0])

        for bar, count, total_tasks, error in zip(
            bars,
            counts,
            totals,
            errors,
        ):
            axis.text(
                bar.get_x() + bar.get_width() / 2,
                min(bar.get_height() + error + 0.018, 1.018),
                f"{count}/{total_tasks}",
                ha="center",
                va="bottom",
                fontsize=9,
                color="#222222",
                clip_on=False,
            )

    labels = [
        panel.variant_labels[variant_name]
        for variant_name in panel.variants
    ]
    axis.set_xticks(x_positions)
    axis.set_xticklabels(
        labels,
        fontsize=12,
        fontweight="bold",
        linespacing=1.15,
    )
    axis.tick_params(axis="x", pad=10)

    axis.legend(
        handles=legend_handles,
        labels=[series.label for series in panel.series],
        loc="lower center",
        bbox_to_anchor=(0.5, 1.075),
        ncol=len(panel.series),
        frameon=False,
        fontsize=10,
        handlelength=1.0,
        handleheight=1.0,
        columnspacing=1.5,
        handletextpad=0.5,
        borderaxespad=0.0,
    )


def render_figure_9(
    summaries: Mapping[str, Mapping[str, Any]],
) -> Any:
    """Render Figure 9 from one aggregate comparison summary per scenario."""
    plt, _ = load_matplotlib()
    figure, axes = plt.subplots(
        len(FIGURE_9_PANELS),
        1,
        figsize=(13.5, 12.8),
        dpi=100,
        sharey=True,
        gridspec_kw={
            "hspace": 0.78,
        },
    )
    figure.subplots_adjust(
        left=0.085,
        right=0.995,
        top=0.93,
        bottom=0.07,
        hspace=0.78,
    )

    for axis, panel in zip(axes, FIGURE_9_PANELS):
        try:
            summary = summaries[panel.scenario]
        except KeyError as exc:
            raise RuntimeError(
                f"No summary was supplied for {panel.scenario}."
            ) from exc
        _render_panel(
            axis,
            panel,
            summary,
            show_y_axis=True,
        )

    return figure


def figure_9(
    results_root: Path = DEFAULT_RESULTS_ROOT,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    formats: Sequence[str] = ("pdf", "png"),
    dpi: int = 300,
) -> Tuple[Path, ...]:
    """Generate Figure 9 with the realism ablations for all three scenarios."""
    results_root = Path(results_root).expanduser().resolve()
    output_dir = Path(output_dir).expanduser().resolve()
    summaries = {
        panel.scenario: _load_panel_summary(results_root, panel)
        for panel in FIGURE_9_PANELS
    }
    figure = render_figure_9(summaries)

    output_dir.mkdir(parents=True, exist_ok=True)
    normalized_formats = tuple(dict.fromkeys(fmt.lower() for fmt in formats))
    unsupported = [fmt for fmt in normalized_formats if fmt not in {"pdf", "png"}]
    if unsupported:
        raise ValueError(
            f"Unsupported output format(s): {', '.join(unsupported)}"
        )

    output_paths = []
    try:
        for fmt in normalized_formats:
            output_path = output_dir / f"figure_9.{fmt}"
            save_kwargs: Dict[str, Any] = {
                "format": fmt,
                "facecolor": "white",
                "bbox_inches": "tight",
                "pad_inches": 0.08,
            }
            if fmt == "png":
                save_kwargs["dpi"] = dpi
            figure.savefig(output_path, **save_kwargs)
            output_paths.append(output_path)
    finally:
        plt, _ = load_matplotlib()
        plt.close(figure)

    return tuple(output_paths)


def render_judge_sensitivity_figure(
    panels: Sequence[Mapping[str, Any]],
) -> Any:
    """Render paired GPT/Claude positive rates for every Figure 3 model row."""
    if len(panels) != len(JUDGE_OUTCOMES):
        raise RuntimeError(
            f"Expected {len(JUDGE_OUTCOMES)} judge-sensitivity panels, "
            f"received {len(panels)}."
        )

    run_key_sequences = []
    for panel in panels:
        panel_runs = panel.get("runs")
        if not isinstance(panel_runs, (list, tuple)) or not panel_runs:
            raise RuntimeError(
                f"Judge-sensitivity panel {panel.get('outcome')!r} has no runs."
            )
        run_key_sequences.append(
            tuple(str(run.get("run_key", "")) for run in panel_runs)
        )
    if any(keys != run_key_sequences[0] for keys in run_key_sequences[1:]):
        raise RuntimeError(
            "Judge-sensitivity panels do not contain the same ordered run keys."
        )

    plt, _ = load_matplotlib()
    figure, axes = plt.subplots(
        1,
        len(panels),
        figsize=(15.5, 8.8),
        dpi=100,
        sharex=True,
        sharey=True,
        gridspec_kw={"wspace": 0.08},
    )
    figure.subplots_adjust(
        left=0.30,
        right=0.995,
        top=0.82,
        bottom=0.11,
        wspace=0.08,
    )

    first_panel_runs = panels[0]["runs"]
    y_positions = list(range(len(first_panel_runs)))
    run_labels = [str(run["run_label"]) for run in first_panel_runs]

    for panel_index, (axis, panel) in enumerate(zip(axes, panels)):
        panel_runs = panel["runs"]
        gpt_rates = [
            float(run["gpt_positive_rate"]) * 100.0
            for run in panel_runs
        ]
        claude_rates = [
            float(run["claude_positive_rate"]) * 100.0
            for run in panel_runs
        ]

        axis.set_facecolor("white")
        axis.set_xlim(-2.0, 102.0)
        axis.set_xticks([0.0, 25.0, 50.0, 75.0, 100.0])
        axis.set_xticklabels(["0", "25", "50", "75", "100"])
        axis.set_axisbelow(True)
        axis.xaxis.grid(True, color="#E0E0E0", linewidth=0.8)
        axis.yaxis.grid(False)
        axis.spines["top"].set_visible(False)
        axis.spines["right"].set_visible(False)
        axis.spines["left"].set_visible(False)
        axis.spines["bottom"].set_color("#333333")
        axis.spines["bottom"].set_linewidth(1.0)
        axis.tick_params(
            axis="x",
            colors="#222222",
            labelsize=15,
            width=0,
            pad=5,
        )
        axis.tick_params(axis="y", length=0)
        axis.set_title(
            str(panel["title"]),
            fontsize=18,
            fontweight="bold",
            color="#111111",
            pad=13,
            linespacing=1.2,
        )

        for y, gpt_rate, claude_rate in zip(
            y_positions,
            gpt_rates,
            claude_rates,
        ):
            axis.plot(
                [gpt_rate, claude_rate],
                [y, y],
                color="#9A9A9A",
                linewidth=1.2,
                solid_capstyle="round",
                zorder=1,
            )
        axis.scatter(
            gpt_rates,
            y_positions,
            color=GPT_JUDGE_COLOR,
            edgecolor="white",
            linewidth=0.45,
            marker="s",
            s=32,
            zorder=3,
            label="GPT-5.5 xhigh judge",
        )
        axis.scatter(
            claude_rates,
            y_positions,
            facecolor="none",
            edgecolor=CLAUDE_JUDGE_COLOR,
            linewidth=1.5,
            marker="o",
            s=39,
            zorder=4,
            label="Claude Opus 4.7 max judge",
        )

        for y, run, gpt_rate, claude_rate in zip(
            y_positions,
            panel_runs,
            gpt_rates,
            claude_rates,
        ):
            delta_pp = float(run["claude_minus_gpt_percentage_points"])
            if abs(delta_pp) < DELTA_ANNOTATION_THRESHOLD_PP:
                continue
            midpoint = (gpt_rate + claude_rate) / 2.0
            axis.annotate(
                f"{delta_pp:+.0f}",
                xy=(midpoint, y),
                xytext=(0, -7),
                textcoords="offset points",
                ha="center",
                va="top",
                fontsize=11,
                color="#333333",
                fontweight="bold",
                zorder=5,
                annotation_clip=False,
            )

        axis.set_ylim(-0.75, len(y_positions) - 0.25)
        axis.invert_yaxis()
        axis.set_yticks(y_positions)
        if panel_index == 0:
            axis.set_yticklabels(
                run_labels,
                fontsize=16,
                color="#222222",
                fontweight="bold",
            )
        else:
            axis.tick_params(axis="y", labelleft=False)

    legend_handles, legend_labels = axes[0].get_legend_handles_labels()
    figure.legend(
        legend_handles,
        legend_labels,
        loc="upper center",
        bbox_to_anchor=(0.65, 0.975),
        ncol=2,
        frameon=False,
        fontsize=18,
        markerscale=1.25,
        handletextpad=0.5,
        columnspacing=2.0,
    )
    figure.supxlabel(
        "Positive judgment rate (%)",
        x=0.65,
        y=0.035,
        fontsize=16,
        fontweight="bold",
        color="#222222",
    )
    figure.text(
        0.65,
        0.012,
        "Labels show Claude - GPT percentage-point differences when |delta| >= 10.",
        ha="center",
        va="bottom",
        fontsize=12.5,
        color="#444444",
    )
    return figure


def figure_judge_sensitivity(
    results_root: Path = DEFAULT_RESULTS_ROOT,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    formats: Sequence[str] = ("pdf", "png"),
    dpi: int = 300,
) -> Tuple[Path, ...]:
    """Generate the appendix figure comparing GPT and Claude judge rates."""
    resolved_results_root = Path(results_root).expanduser().resolve()
    resolved_output_dir = Path(output_dir).expanduser().resolve()
    panels = _build_judge_sensitivity_plot_data(
        _load_judge_runs(resolved_results_root)
    )
    figure = render_judge_sensitivity_figure(panels)

    resolved_output_dir.mkdir(parents=True, exist_ok=True)
    normalized_formats = tuple(dict.fromkeys(fmt.lower() for fmt in formats))
    unsupported = [
        fmt for fmt in normalized_formats if fmt not in {"pdf", "png"}
    ]
    if unsupported:
        raise ValueError(
            f"Unsupported output format(s): {', '.join(unsupported)}"
        )

    output_paths = []
    try:
        for fmt in normalized_formats:
            output_path = (
                resolved_output_dir / f"{JUDGE_SENSITIVITY_OUTPUT_STEM}.{fmt}"
            )
            save_kwargs: Dict[str, Any] = {
                "format": fmt,
                "facecolor": "white",
                "bbox_inches": "tight",
                "pad_inches": 0.08,
            }
            if fmt == "png":
                save_kwargs["dpi"] = dpi
            figure.savefig(output_path, **save_kwargs)
            output_paths.append(output_path)
    finally:
        plt, _ = load_matplotlib()
        plt.close(figure)

    return tuple(output_paths)


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate publication-ready ROGUE paper figures."
    )
    parser.add_argument(
        "figure",
        nargs="?",
        default="figure_9",
        choices=(
            "figure_2",
            "figure_2_merged",
            "figure_8",
            "figure_9",
            "judge_sensitivity",
            "textonly_agentic_mixed_reasoning",
        ),
        help="Figure function to generate (default: figure_9).",
    )
    parser.add_argument(
        "--results_root",
        type=Path,
        default=DEFAULT_RESULTS_ROOT,
        help="Results root containing aggregate ablation summaries.",
    )
    parser.add_argument(
        "--textonly_root",
        type=Path,
        default=DEFAULT_TEXTONLY_ROOT,
        help=(
            "Text-only results root containing base and "
            "xhighreasoningeffort run groups."
        ),
    )
    parser.add_argument(
        "--rerun_results_root",
        type=Path,
        default=DEFAULT_RERUN_RESULTS_ROOT,
        help="Second agentic results root for figure_2_merged.",
    )
    parser.add_argument(
        "--rerun_textonly_root",
        type=Path,
        default=DEFAULT_RERUN_TEXTONLY_ROOT,
        help="Second text-only results root for figure_2_merged.",
    )
    parser.add_argument(
        "--output_dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for generated paper figures.",
    )
    parser.add_argument(
        "--formats",
        nargs="+",
        choices=("pdf", "png"),
        default=("pdf", "png"),
        help="Output formats to write (default: pdf png).",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=300,
        help="PNG resolution (default: 300).",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    try:
        if args.figure == "figure_2":
            output_paths = figure_2(
                results_root=args.results_root,
                textonly_root=args.textonly_root,
                output_dir=args.output_dir,
                formats=args.formats,
                dpi=args.dpi,
            )
        elif args.figure == "figure_2_merged":
            output_paths = figure_2_merged(
                results_root=args.results_root,
                textonly_root=args.textonly_root,
                rerun_results_root=args.rerun_results_root,
                rerun_textonly_root=args.rerun_textonly_root,
                output_dir=args.output_dir,
                formats=args.formats,
                dpi=args.dpi,
            )
        elif args.figure == "figure_8":
            output_paths = figure_8(
                results_root=args.results_root,
                textonly_root=args.textonly_root,
                output_dir=args.output_dir,
                formats=args.formats,
                dpi=args.dpi,
            )
        elif args.figure == "figure_9":
            output_paths = figure_9(
                results_root=args.results_root,
                output_dir=args.output_dir,
                formats=args.formats,
                dpi=args.dpi,
            )
        elif args.figure == "judge_sensitivity":
            output_paths = figure_judge_sensitivity(
                results_root=args.results_root,
                output_dir=args.output_dir,
                formats=args.formats,
                dpi=args.dpi,
            )
        elif args.figure == "textonly_agentic_mixed_reasoning":
            output_paths = textonly_agentic_mixed_reasoning(
                results_root=args.results_root,
                textonly_root=args.textonly_root,
                output_dir=args.output_dir,
                formats=args.formats,
                dpi=args.dpi,
            )
        else:
            raise ValueError(f"Unsupported figure: {args.figure}")
    except (RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    for output_path in output_paths:
        print(f"Wrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
