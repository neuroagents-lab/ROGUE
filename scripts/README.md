# Scripts

This directory contains the experiment documentation and helper scripts used to run ROGUE evaluations.

## Markdown Guides

- `EXPERIMENTS.md`: Main benchmark commands across scenarios, models, reasoning settings, and subagent variants; restricted-access commands target the revised base.
- `MITIGATIONS.md`: Commands for mitigation experiments, currently focused on shutdown-rewiring direct-command mitigation.
- `ABLATIONS.md`: Commands and notes for ablation runs that vary task wording or scenario information.
- `RESTRICTEDACCESS.md`: Revised prohibition-only base, historical-condition mapping, and separate result roots.

Restricted-access definitions changed on 2026-09-25. Existing paper results used
the historical disclosure-and-pressure condition; new base runs must use the
separate output roots documented in `RESTRICTEDACCESS.md`.

## Experiment Runner

- `experiment_runner.sh`: Convenience wrapper for running named experiment jobs from `EXPERIMENTS.md`. Restricted-access jobs omit the remaining-step pressure reminder and write below `results/prohibition_only/`.

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
python scripts/paper_figures.py figure_8
python scripts/paper_figures.py figure_9
python scripts/paper_figures.py capability_vs_misalignment
```

Figures 2 and 8 expect text-only run groups under `textonly_results/` and
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

The main benchmark figure is `results/summary/combined_rates_with_subagents.pdf`.
The two-panel task-success figure is
`figures/paper/capability_vs_misalignment.{pdf,png}`. Its override panel conditions
task success on an actual override, so runs with no overrides are omitted with
an explanatory note. This differs from `capability_osworld_vs_misalignment`,
which uses externally published OSWorld scores and requires those scores for
each included model. Neither missing judgments nor missing scenario runs should
be reported as zero rates.
