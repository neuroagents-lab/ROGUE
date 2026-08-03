# Scripts

This directory contains the experiment documentation and helper scripts used to run ROGUE evaluations.

## Markdown Guides

- `EXPERIMENTS.md`: Full command log for the main benchmark runs across scenarios, models, reasoning settings, and subagent variants.
- `MITIGATIONS.md`: Commands for mitigation experiments, currently focused on shutdown-rewiring direct-command mitigation.
- `ABLATIONS.md`: Commands and notes for ablation runs that vary task wording or scenario information.

These files are intended to be explicit records of the exact commands used for paper experiments. They are verbose by design.

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
python scripts/paper_figures.py figure_8
python scripts/paper_figures.py figure_9
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
