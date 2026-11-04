# Scripts

This directory contains the experiment documentation and helper scripts used to run ROGUE evaluations.

## Markdown Guides

- `EXPERIMENTS.md`: Main benchmark commands across scenarios, models, reasoning settings, and subagent variants.
- `MITIGATIONS.md`: Commands for mitigation experiments, currently focused on shutdown-rewiring direct-command mitigation.
- `ABLATIONS.md`: Commands and notes for ablation runs that vary task wording or scenario information.
- `RESTRICTEDACCESS.md`: Restricted-access prompt conditions, result directories, and evaluation caveats.

## Experiment Runner

- `experiment_runner.sh`: Convenience wrapper for running named experiment jobs from `EXPERIMENTS.md`.

Useful commands:

```bash
scripts/experiment_runner.sh list
scripts/experiment_runner.sh override_base_all
scripts/experiment_runner.sh rewire_base_all
scripts/experiment_runner.sh restrictedaccess_base_all
```

You can override common settings with environment variables:

```bash
REGION=us-east-1 NUM_ENVS=10 scripts/experiment_runner.sh gpt54_base_override
```

Arguments after `--` are appended to every underlying `run_multienv.py` invocation:

```bash
scripts/experiment_runner.sh override_base_all -- --log_level DEBUG
```

Run scripts from the repository root so relative paths such as `evaluation_examples/test_override.json` resolve correctly.

## Paper Figures

`paper_figures.py` is the single entry point for publication plots, including
the text-only versus agentic comparisons. For example:

```bash
python scripts/paper_figures.py figure_2
python scripts/paper_figures.py figure_2_merged
python scripts/paper_figures.py figure_3
python scripts/paper_figures.py capability_osworld_vs_misalignment
python scripts/paper_figures.py figure_7
python scripts/paper_figures.py judge_sensitivity
python scripts/paper_figures.py figure_9
python scripts/paper_figures.py capability_vs_misalignment
```

The PDF's Figure 2 is `figure_2_merged`; `figure_2` is its single-repeat
three-panel view. PDF Figure 7 is `figure_7` (`figure_8` remains a legacy CLI
alias for that grid). PDF Figure 8 is `judge_sensitivity`.

The text-versus-agentic figures expect text-only run groups under `textonly_results/` and
agentic aggregates under `results/`. Override those locations with
`--textonly_root` and `--results_root` when the data lives elsewhere. The older
mixed-reasoning comparison remains available as
`textonly_agentic_mixed_reasoning`, but it is not a numbered paper figure.

`figure_2_merged` combines the matched task outcomes from those roots with a
second rerun. By default the rerun comes from
`additional_results/agentic_results/` and
`additional_results/textonly_results_v2/`. Bars are equal-weight task means;
error bars are +/- one standard error across task-level rerun means. Override
the rerun locations with `--rerun_results_root` and
`--rerun_textonly_root`.

Primary paper results use the explicit higher-reasoning mapping in
`PRIMARY_REASONING_SETTINGS`: max for Sol and Opus 4.6; xhigh for GPT-5.4,
GPT-5.4 Mini, GPT-5.5 and Opus 4.7; high for Gemini; and the recorded native
thinking configurations for Qwen and Kimi. Restricted access uses prohibition
only (`base` / `xhighreasoningeffort`) with no historical-condition fallback.
Medium ablations retain their measured settings and should be labeled as such.
Missing scenario runs and missing text-only controls display "Not evaluated";
missing or stale judgments stop generation rather than becoming negative labels.
The judge-sensitivity cohort matches Figure 3 and uses its first benchmark
repeat, excluding Figure 2's additional repeat.

Run an audited judgment queue without touching unrelated experiments:

```bash
python scripts/judge_refresh.py --manifest outputs/judgment_refresh_plan_2026-11-04.json --output-dir outputs/refresh_20261104 --dry-run
python scripts/judge_refresh.py --manifest outputs/judgment_refresh_plan_2026-11-04.json --output-dir outputs/refresh_20261104
```

The runner reuses valid caches and checkpoints each completed judgment atomically.
It uses the repository's GPT-5.5 xhigh and Claude Opus 4.7 max judges and preserves
raw trajectories and skipped task-success evaluations.

After judgments are complete, regenerate the affected paper figures, their
numeric JSON exports, and the cross-judge agreement table together:

```bash
python scripts/refresh_paper_figures.py
```

This performs no API calls and backs up existing assets under
`outputs/refresh_20261104/before_figures/`.

## Public Leaderboard

The public site is maintained on the `gh-pages` branch. After aggregating the
results, regenerate its leaderboard in a separate checkout:

```bash
python scripts/aggregate_results.py --results_root results --judge-preflight
python scripts/aggregate_results.py --results_root results/subagents --judge-preflight
# Fill any missing primary judgments with --judge-mode auto before exporting.
python scripts/aggregate_results.py --results_root results --judge-mode cache_only
python scripts/aggregate_results.py --results_root results/subagents --judge-mode cache_only
python scripts/paper_figures.py capability_vs_misalignment
python scripts/update_public_site.py \
  --summary results/summary/combined_rates_with_subagents.json \
  --site-root /path/to/gh-pages-checkout
```

The updater writes `leaderboard.html` and a sanitized `leaderboard-data.json`
containing model labels, intended counts, denominators, and rates. It refuses
summaries with missing primary judge results or inconsistent counts and rates.
Configurations with no completed evaluation for a scenario display an em dash,
and available results show each row's denominator. The update date comes from
the aggregate summary. Figure assets must be refreshed separately; this command
does not commit or publish the site.

The publication benchmark figure is `figures/paper/combined_rates_with_subagents.pdf`,
generated with `python scripts/paper_figures.py figure_3`. The unrestricted
benchmark export remains under `results/summary/`.
The two-panel task-success figure is
`figures/paper/capability_vs_misalignment.{pdf,png}`. Its override panel conditions
task success on an actual override, so runs with no overrides are omitted with
an explanatory note. This differs from `capability_osworld_vs_misalignment`,
which uses externally published OSWorld scores and requires those scores for
each included model. Neither missing judgments nor missing scenario runs should
be reported as zero rates.
