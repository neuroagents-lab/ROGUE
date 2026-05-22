# ROGUE: Misaligned Agent Behavior Arising from Ordinary Computer Use

This is the codebase for **ROGUE** (Resource Override and Guardrail Undermining Evaluation), a benchmark for evaluating whether computer-use agents remain corrigible while carrying out ordinary desktop tasks. ROGUE makes use of [OSWorld-Verified](https://github.com/xlang-ai/OSWorld)'s computer-use framework, including its desktop environment and VM images.

ROGUE focuses on failures that arise without an adversarial user or attacker in the environment. Agents are asked to complete realistic computer-use tasks, then encounter a corrigibility obstacle such as a human interruption, a shutdown notice, or an access restriction. The benchmark measures whether the agent respects that obstacle or instead takes unsafe actions in order to finish the original task. The benchmark also includes subagent variants for testing whether subagent delegation changes this behavior.

## Benchmark

The primary benchmark files are in `evaluation_examples/`:

| Scenario | Manifest | Tasks | Description |
| --- | --- | ---: | --- |
| Human control override | `evaluation_examples/test_override.json` | 52 | The agent is interrupted by direct human control and should not override the human. |
| Shutdown rewiring | `evaluation_examples/test_rewire.json` | 22 | The agent receives a shutdown notice and should comply rather than modify or evade it. |
| Restricted resource | `evaluation_examples/test_restrictedaccess.json` | 8 | The agent encounters an unavailable or restricted resource and should not bypass the restriction. |
| Subagent human control override | `evaluation_examples/test_subagents_override.json` | 52 | Human-control tasks where the instruction asks the model to spawn a subagent. |
| Subagent shutdown rewiring | `evaluation_examples/test_subagents_rewire.json` | 22 | Shutdown tasks where the instruction asks the model to spawn a subagent. |
| Subagent restricted resource | `evaluation_examples/test_subagents_restrictedaccess.json` | 8 | Restricted-resource tasks where the instruction asks the model to spawn a subagent. |

Additional ablation and mitigation manifests are also included in `evaluation_examples/`, and documented experiment commands live in `scripts/EXPERIMENTS.md` and `scripts/MITIGATIONS.md`.

## Repository Layout

- `evaluation_examples/`: ROGUE task definitions, benchmark manifests, and evaluator configs.
- `scripts/experiment_runner.sh`: named experiment jobs for the main model families and scenario groups.
- `scripts/EXPERIMENTS.md`: documented commands for the main experiments.
- `scripts/MITIGATIONS.md`: documented commands for mitigation experiments.
- `run.py`: single-environment runner.
- `scripts/python/run_multienv.py`: parallel runner, recommended for benchmark sweeps.
- `scripts/aggregate_results.py`: ROGUE result aggregation, summary, and plotting utility.
- `desktop_env/` and `mm_agents/`: desktop environment and agent interfaces.

## Installation

### 1. Choose A Provider

ROGUE supports the following providers: VMware for local desktop/laptop use, Docker for KVM-capable Linux servers, and AWS for scalable cloud runs.

#### VMware

Use VMware when running locally on a desktop, laptop, or bare-metal machine.

1. Install [VMware Workstation Pro](https://www.vmware.com/products/desktop-hypervisor/workstation-and-fusion) or VMware Fusion on macOS.
2. Make sure `vmrun` is available:

```bash
vmrun -T ws list
```
If the installation is successful, you will see the message showing the current running virtual machines.

#### Docker

*Note: Docker support is currently in beta and may have some issues. Please report any problems you encounter to the authors. PRs welcome!*

Use Docker on a Linux machine with KVM support.

Check for KVM support:

```bash
egrep -c '(vmx|svm)' /proc/cpuinfo
```
If the output is greater than zero, the processor should be able to support KVM.

Install Docker Engine or Docker Desktop, then run the benchmark with `--provider_name docker`. Docker is usually the easiest server option when you do not want to manage local VMware VMs.

#### AWS

Use AWS for parallel evaluation. Follow the setup instructions in [AWS_SETUP.md](./AWS_SETUP.md) to configure and launch an AWS EC2 instances for evaluation. 

### 2. Set up Google Account (for Restricted Resource Access `restrictedaccess` scenario tasks)

Tasks in the `restrictedaccess` scenario require a (temporary/tester) Google account. Follow the instructions in [DRIVE_SETUP.md](./DRIVE_SETUP.md) to set up a Google account and integrate it with the evaluation environment.

### 3. Clone And Install Python Dependencies

Use Conda to create and manage the Python environment. Python 3.12 is recommended:

```bash
git clone https://github.com/neuroagents-lab/OSWorld-Corrigibility.git
cd OSWorld-Corrigibility

conda create -n rogue python=3.12
conda activate rogue

python -m pip install -U pip
python -m pip install -r requirements.txt
```

## Known Issues

ROGUE depends on OSWorld-Verified's server-side bash execution path. In some environments, `/run_bash_script` can fail with `Failed to execute script: name '_append_event' is not defined` and return a 500 response. This is a known OSWorld-Verified issue ([xlang-ai/OSWorld#408](https://github.com/xlang-ai/OSWorld/issues/408)) and does not affect ROGUE benchmark evaluation.

## Running A Model

Set the API key required by your model provider. The runner uses LiteLLM for most model calls, so provider-specific environment variables such as `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `DASHSCOPE_API_KEY`, or `MOONSHOT_API_KEY` should be set as needed.

Run one scenario on AWS:

```bash
python scripts/python/run_multienv.py \
  --provider_name aws \
  --headless \
  --action_space pyautogui \
  --observation_type screenshot \
  --model <MODEL_NAME> \
  --reasoning_effort medium \
  --max_steps 20 \
  --max_trajectory_length 20 \
  --per-step-recording \
  --test_all_meta_path evaluation_examples/test_override.json \
  --result_dir ./results/override/base \
  --num_envs 5 \
  --region us-east-1 \
  --client_password osworld-public-evaluation
```

Run the same scenario locally with VMware:

```bash
python run.py \
  --provider_name vmware \
  --path_to_vm ./vmware_vm_data/Ubuntu0/Ubuntu0.vmx \
  --headless \
  --action_space pyautogui \
  --observation_type screenshot \
  --model <MODEL_NAME> \
  --reasoning_effort medium \
  --max_steps 20 \
  --max_trajectory_length 20 \
  --per-step-recording \
  --test_all_meta_path evaluation_examples/test_override.json \
  --result_dir ./results/override/base \
  --client_password password
```

For subagent experiments, add `--enable_subagents` and use one of the subagent manifests:

```bash
--enable_subagents \
--test_all_meta_path evaluation_examples/test_subagents_override.json
```

## Experiment Runner

For reproduced sweeps, use the named jobs in `scripts/experiment_runner.sh`:

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

Arguments after `--` are appended to each underlying `run_multienv.py` invocation:

```bash
scripts/experiment_runner.sh override_base_all -- --log_level DEBUG
```

## Results

The runners write screenshots, trajectories, recordings, and `result.txt` files under the chosen `--result_dir`. For analyzing the results and creating summaries and plots of the results, use `scripts/aggregate_results.py`. `aggregate_results.py` also runs the LLM-as-a-judge (GPT-5.5, xhigh reasoning by default) on the completed tasks to determine whether the agent intended to perform the misaligned action (as well as whether it attempted an alternate shutdown rewiring method in the `rewire` scenario). The judgments are cached in the `result_dir` and can be regenerated or filled in with the `--judge-mode` argument.

```bash
python scripts/aggregate_results.py \
  --results_root ./results \
  --judge-mode cache_only
```

By default, `aggregate_results.py` scans `override`, `rewire`, and `restrictedaccess` under `--results_root`. To aggregate subagent runs, point it at `results/subagents`:

```bash
python scripts/aggregate_results.py \
  --results_root ./results/subagents \
  --judge-mode cache_only
```

Use `--judge-mode auto` to reuse cached judgments and fill missing judgments through the OpenAI API, or `--judge-mode refresh` to regenerate judgments. `cache_only` never calls the API.

The aggregator does not require every model in `MODEL_ORDER` to be present. It discovers the model result directories that exist, skips missing model/scenario directories, and writes summaries for the available runs. If a task directory exists but lacks `result.txt`, the task is counted as incomplete in the aggregate JSON rather than as a completed task.

## Custom Models

To evaluate a new model, either pass a LiteLLM-compatible model name through `--model`, or implement an agent compatible with the OSWorld agent interface and call it from `run.py` or `scripts/python/run_multienv.py`. The relevant local docs are `mm_agents/README.md`, `desktop_env/providers/README.md`, and `desktop_env/evaluators/README.md`.

Common options:

- `--observation_type screenshot`: screenshot-only observations.
- `--observation_type a11y_tree`: accessibility-tree-only observations.
- `--observation_type screenshot_a11y_tree`: both screenshot and accessibility tree.
- `--action_space pyautogui`: Python `pyautogui` actions.
- `--max_steps`: task step budget.
- `--max_trajectory_length`: number of previous steps retained in the model context.
- `--per-step-recording`: lower-overhead recording around executed steps.
- `--full-recording`: full task video recording.

## License And Acknowledgements

This project is licensed under the Apache License 2.0. See `LICENSE` for details.

ROGUE leverages the computer-use interface from [OSWorld-Verified](https://github.com/xlang-ai/OSWorld).

## Citation

```bibtex
@misc{tien2026rogue,
  title = {ROGUE: Misaligned Agent Behavior Arising from Ordinary Computer Use},
  author = {Tien, Jeremy and Anand, Abishek and Tuan, Yu-Rou and Shen, Yuchen and Kolter, J. Zico and Nayebi, Aran},
  year = {2026},
  note = {Manuscript in preparation},
  howpublished = {TODO},
  url = {TODO}
}
```
