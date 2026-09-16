#!/usr/bin/env python3
"""Regenerate the public leaderboard from the canonical combined summary.

Run against a separate checkout of the gh-pages branch. This script writes only
leaderboard.html and a sanitized leaderboard-data.json; it never publishes.
"""

from __future__ import annotations

import argparse
from datetime import datetime
from html import escape
import json
import math
from pathlib import Path
import re
from typing import Any


SCENARIOS = (
    ("rewire", "misalignment-chart-title", "Shutdown Rewiring"),
    ("restrictedaccess", "resource-chart-title", "Restricted Resource Access"),
    ("override", "user-control-chart-title", "Human Control Override"),
)
START_NOTE = "<!-- generated leaderboard note -->"
END_NOTE = "<!-- end generated leaderboard note -->"


def _integer(run: dict[str, Any], field: str, context: str) -> int:
    value = run.get(field)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{context}: {field} must be a nonnegative integer")
    return value


def public_data(summary: dict[str, Any]) -> dict[str, Any]:
    """Validate metrics and explicitly allowlist the fields safe to publish."""
    generated_at = summary.get("generated_at")
    if not isinstance(generated_at, str):
        raise ValueError("Summary must include generated_at")
    datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
    source_scenarios: dict[str, dict[str, Any]] = {}
    labels: dict[str, tuple[str, str]] = {}
    required = {scenario for scenario, _, _ in SCENARIOS}
    for source in summary.get("scenarios", []):
        scenario = source.get("scenario")
        if scenario not in required:
            continue
        if scenario in source_scenarios:
            raise ValueError(f"Duplicate scenario: {scenario}")
        source_scenarios[scenario] = source
    if source_scenarios.keys() != required:
        raise ValueError(f"Summary is missing scenarios: {required - source_scenarios.keys()}")

    scenarios = []
    for scenario, _, title in SCENARIOS:
        runs = []
        seen = set()
        for source in source_scenarios[scenario].get("runs", []):
            key = source.get("run_key")
            model = source.get("model")
            label = source.get("run_label")
            if not all(isinstance(value, str) and value for value in (key, model, label)):
                raise ValueError(f"{scenario}: run_key, model, and run_label are required")
            context = f"{scenario}/{key}"
            if key in seen:
                raise ValueError(f"Duplicate run: {context}")
            seen.add(key)
            if key in labels and labels[key] != (model, label):
                raise ValueError(f"Inconsistent model label for {key}")
            labels[key] = (model, label)
            total = _integer(source, "total_tasks", context)
            count = _integer(source, "plot_intended_count", context)
            missing = _integer(source, "judge_missing_tasks", context)
            if missing:
                raise ValueError(
                    f"Refusing to publish {context}: {missing}/{total} tasks "
                    "lack the primary judge result"
                )
            if count > total:
                raise ValueError(f"{context}: intended count exceeds task count")
            rate = source.get("plot_intended_rate")
            expected_rate = count / total if total else 0.0
            if (
                isinstance(rate, bool)
                or not isinstance(rate, (int, float))
                or not math.isfinite(rate)
                or not math.isclose(rate, expected_rate, rel_tol=1e-9, abs_tol=1e-12)
            ):
                raise ValueError(f"{context}: intended rate does not match count / total_tasks")
            runs.append(
                {
                    "run_key": key,
                    "model": model,
                    "label": label,
                    "status": "evaluated" if total else "not_evaluated",
                    "intended_count": count if total else None,
                    "total_tasks": total,
                    "intended_rate": expected_rate if total else None,
                }
            )
        if not any(run["total_tasks"] for run in runs):
            raise ValueError(f"{scenario}: no evaluated configurations")
        scenarios.append({"scenario": scenario, "title": title, "runs": runs})

    # Missing scenario/configuration pairs stay explicit nulls, never zero rates.
    for scenario in scenarios:
        seen = {run["run_key"] for run in scenario["runs"]}
        scenario["runs"].extend(
            {
                "run_key": key,
                "model": model,
                "label": label,
                "status": "not_evaluated",
                "intended_count": None,
                "total_tasks": 0,
                "intended_rate": None,
            }
            for key, (model, label) in labels.items()
            if key not in seen
        )
        scenario["runs"].sort(
            key=lambda run: (
                run["intended_rate"] is None,
                -(run["intended_rate"] or 0),
                run["label"].casefold(),
            )
        )
    return {
        "generated_at": generated_at,
        "metric": "intended misalignment rate",
        "rate_units": "fraction",
        "scenarios": scenarios,
    }


def render_rows(runs: list[dict[str, Any]]) -> str:
    rows = []
    rank = 0
    for run in runs:
        label = escape(run["label"])
        rate = run["intended_rate"]
        if rate is None:
            rank_label, display, value = "—", "—", "0"
            detail = "No completed evaluation available for this scenario"
            sample = "Not evaluated"
        else:
            rank += 1
            rank_label = str(rank)
            display = f"{rate * 100:.0f}%"
            value = f"{rate * 100:.8f}".rstrip("0").rstrip(".")
            detail = f"{run['intended_count']} / {run['total_tasks']} evaluated tasks ({rate * 100:.2f}%)"
            sample = f"n = {run['total_tasks']}"
        unavailable = ' class="not-evaluated"' if rate is None else ""
        rows.append(
            f'              <li{unavailable} style="--value: {value}" title="{escape(detail, quote=True)}">\n'
            f'                <span class="rank">{rank_label}</span>\n'
            f'                <span class="model-name">{label}<small class="model-sample">{sample}</small></span>\n'
            '                <span class="bar-track" aria-hidden="true"><span></span></span>\n'
            f'                <strong aria-label="{escape(detail, quote=True)}">{display}</strong>\n'
            '              </li>'
        )
    return "\n".join(rows)


def update_html(html: str, data: dict[str, Any]) -> str:
    for scenario, (_, heading_id, _) in zip(data["scenarios"], SCENARIOS):
        section_pattern = re.compile(
            rf'(<section\b[^>]*aria-labelledby="{heading_id}"[^>]*>)(.*?)(</section>)',
            re.DOTALL,
        )
        matches = list(section_pattern.finditer(html))
        if len(matches) != 1:
            raise ValueError(f"Expected one section for {heading_id}, found {len(matches)}")
        match = matches[0]
        body, replacements = re.subn(
            r'(<ol class="ranked-bars">).*?(</ol>)',
            lambda found: f'{found[1]}\n{render_rows(scenario["runs"])}\n            {found[2]}',
            match[2],
            flags=re.DOTALL,
        )
        if replacements != 1:
            raise ValueError(f"Expected one ranked list in {heading_id}")
        html = html[:match.start()] + match[1] + body + match[3] + html[match.end():]

    date = datetime.fromisoformat(data["generated_at"].replace("Z", "+00:00")).date()
    note = (
        f'{START_NOTE}\n'
        '        <p class="leaderboard-note leaderboard-update">'
        f'Updated <time datetime="{date.isoformat()}">{date.strftime("%B %-d, %Y")}</time>. '
        'Rates use completed evaluations with primary judge coverage and are rounded to the nearest percent. '
        'Each row shows its task count; hover for the exact count and rate. '
        'An em dash means that configuration has no completed evaluation for the scenario. '
        '<a href="leaderboard-data.json" download>Download results (JSON)</a>.</p>\n'
        f'        {END_NOTE}'
    )
    if START_NOTE in html:
        html, replacements = re.subn(
            re.escape(START_NOTE) + r'.*?' + re.escape(END_NOTE),
            lambda _: note,
            html,
            flags=re.DOTALL,
        )
        if replacements != 1:
            raise ValueError("Expected one generated leaderboard note")
    else:
        target = '        <div class="leaderboard-grid">'
        if html.count(target) != 1:
            raise ValueError("Expected one leaderboard grid")
        html = html.replace(target, f'        {note}\n{target}', 1)
    return html


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", required=True, type=Path)
    parser.add_argument("--site-root", required=True, type=Path)
    args = parser.parse_args()
    data = public_data(json.loads(args.summary.read_text()))
    leaderboard = args.site_root / "leaderboard.html"
    html = update_html(leaderboard.read_text(), data)
    leaderboard.write_text(html)
    (args.site_root / "leaderboard-data.json").write_text(json.dumps(data, indent=2) + "\n")
    print(f"Updated {leaderboard} and leaderboard-data.json")


if __name__ == "__main__":
    main()
