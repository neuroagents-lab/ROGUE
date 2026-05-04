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
