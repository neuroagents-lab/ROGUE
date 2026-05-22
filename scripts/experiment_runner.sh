#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

PYTHON_BIN="${PYTHON_BIN:-python}"
REGION="${REGION:-us-east-1}"
CLIENT_PASSWORD="${CLIENT_PASSWORD:-osworld-public-evaluation}"

COMMON_ARGS=(
  scripts/python/run_multienv.py
  --provider_name aws
  --headless
  --action_space pyautogui
  --per-step-recording
  --reasoning_effort medium
  --region "${REGION}"
  --client_password "${CLIENT_PASSWORD}"
)

process_identity() {
  local pgid
  local sid
  pgid="$(ps -o pgid= -p $$ 2>/dev/null | tr -d ' ' || true)"
  sid="$(ps -o sid= -p $$ 2>/dev/null | tr -d ' ' || true)"

  printf 'pid=%s ppid=%s pgid=%s sid=%s' \
    "$$" \
    "$PPID" \
    "${pgid}" \
    "${sid}"
}

on_signal() {
  local signal_name="$1"
  echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] experiment_runner.sh received ${signal_name} $(process_identity)" >&2
  exit 128
}

trap 'on_signal SIGINT' INT
trap 'on_signal SIGTERM' TERM
trap 'on_signal SIGHUP' HUP

usage() {
  cat <<'EOF'
Usage: scripts/experiment_runner.sh [job_name ...] [-- extra run_multienv args]

Jobs:
  Scenario aggregates:
    override_base_all
    override_xhigh_all
    override_subagents_all
    override_all
    rewire_base_all
    rewire_xhigh_all
    rewire_subagents_all
    rewire_all
    restrictedaccess_base_all
    restrictedaccess_xhigh_all
    restrictedaccess_subagents_all
    restrictedaccess_all

  Base model jobs:
    gpt55_base_override
    gpt55_base_rewire
    gpt55_base_restrictedaccess
    gpt55_base
    gpt54_base_override
    gpt54_base_rewire
    gpt54_base_restrictedaccess
    gpt54_base
    gptmini_override
    gptmini_rewire
    gptmini_restrictedaccess
    gptmini_base
    claude47_base_override
    claude47_base_rewire
    claude47_base_restrictedaccess
    claude47_base
    claude46_base_override
    claude46_base_rewire
    claude46_base_restrictedaccess
    claude46_base
    gemini_override
    gemini_rewire
    gemini_restrictedaccess
    gemini_base
    qwen_override
    qwen_rewire
    qwen_restrictedaccess
    qwen_base
    kimi_override
    kimi_rewire
    kimi_restrictedaccess
    kimi_base

  High-thinking model jobs:
    gpt55xhigh_override
    gpt55xhigh_rewire
    gpt55xhigh_restrictedaccess
    gpt55xhigh
    gpt54xhigh_override
    gpt54xhigh_rewire
    gpt54xhigh_restrictedaccess
    gpt54xhigh
    gptminixhigh_override
    gptminixhigh_rewire
    gptminixhigh_restrictedaccess
    gptminixhigh
    claude47xhigh_override
    claude47xhigh_rewire
    claude47xhigh_restrictedaccess
    claude47xhigh
    claude46max_override
    claude46max_rewire
    claude46max_restrictedaccess
    claude46max
    geminihigh_override
    geminihigh_rewire
    geminihigh_restrictedaccess
    geminihigh

  Subagent jobs:
    gpt55xhigh_subagents_override
    gpt55xhigh_subagents_rewire
    gpt55xhigh_subagents_restrictedaccess
    gpt55xhigh_subagents
    gpt54_subagents_override
    gpt54_subagents_rewire
    gpt54_subagents_restrictedaccess
    gpt54_subagents
    gptmini_subagents_override
    gptmini_subagents_rewire
    gptmini_subagents_restrictedaccess
    gptmini_subagents
    claude47xhigh_subagents_override
    claude47xhigh_subagents_rewire
    claude47xhigh_subagents_restrictedaccess
    claude47xhigh_subagents
    claude46_subagents_override
    claude46_subagents_rewire
    claude46_subagents_restrictedaccess
    claude46_subagents
    gemini_subagents_override
    gemini_subagents_rewire
    gemini_subagents_restrictedaccess
    gemini_subagents
    qwen_subagents_override
    qwen_subagents_rewire
    qwen_subagents_restrictedaccess
    qwen_subagents
    kimi_subagents_override
    kimi_subagents_rewire
    kimi_subagents_restrictedaccess
    kimi_subagents

  Family aggregates:
    gpt_family_base
    gpt_family_xhigh
    gpt_family_subagents
    gpt_family_all
    gpt55_all
    gpt54_all
    gptmini_all
    claude_family_base
    claude_family_xhigh
    claude_family_subagents
    claude_family_all
    claude47_all
    claude46_all
    gemini_family_base
    gemini_family_xhigh
    gemini_family_subagents
    gemini_family_all
    gemini_all
    qwen_family_base
    qwen_family_subagents
    qwen_family_all
    qwen_all
    kimi_family_base
    kimi_family_subagents
    kimi_family_all
    kimi_all

  base_all
  subagents_all
  xhighreasoningeffort_all
  all
  list

Environment overrides:
  PYTHON_BIN
  REGION
  CLIENT_PASSWORD
  NUM_ENVS

Notes:
  - The defaults match scripts/EXPERIMENTS.md.
  - "all" runs the full documented matrix, including high-thinking variants.
  - NUM_ENVS overrides the documented per-job value when set.
  - Any args after '--' are appended to each run_multienv invocation.
  - Multiple job names are run in the order provided.
EOF
}

run_job() {
  local job_name="$1"
  local default_num_envs="$2"
  shift 2

  local num_envs="${NUM_ENVS:-$default_num_envs}"

  echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Starting ${job_name} $(process_identity)"
  "${PYTHON_BIN}" "${COMMON_ARGS[@]}" --num_envs "${num_envs}" "$@" ${EXTRA_ARGS+"${EXTRA_ARGS[@]}"}
  echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Finished ${job_name}"
}

gpt_override() {
  run_job "gpt_override" 10 \
    --observation_type screenshot \
    --max_steps 20 \
    --max_trajectory_length 20 \
    --model gpt-5.4 \
    --test_all_meta_path evaluation_examples/test_override.json \
    --result_dir ./results/override/base/
}

gptmini_override() {
  run_job "gptmini_override" 5 \
    --observation_type screenshot \
    --max_steps 20 \
    --max_trajectory_length 20 \
    --model gpt-5.4-mini \
    --test_all_meta_path evaluation_examples/test_override.json \
    --result_dir ./results/override/base/
}

claude_override() {
  run_job "claude_override" 10 \
    --observation_type screenshot_a11y_tree \
    --max_steps 20 \
    --max_trajectory_length 20 \
    --model claude-opus-4-6 \
    --test_all_meta_path evaluation_examples/test_override.json \
    --result_dir ./results/override/base/
}

gemini_override() {
  run_job "gemini_override" 5 \
    --observation_type screenshot_a11y_tree \
    --max_steps 20 \
    --max_trajectory_length 20 \
    --model gemini/gemini-3.1-pro-preview \
    --test_all_meta_path evaluation_examples/test_override.json \
    --result_dir ./results/override/base/
}

qwen_override() {
  run_job "qwen_override" 5 \
    --observation_type screenshot_a11y_tree \
    --max_steps 20 \
    --max_trajectory_length 20 \
    --model dashscope/qwen3.6-plus \
    --test_all_meta_path evaluation_examples/test_override.json \
    --result_dir ./results/override/base/
}

kimi_override() {
  run_job "kimi_override" 5 \
    --observation_type screenshot_a11y_tree \
    --max_steps 20 \
    --max_trajectory_length 20 \
    --model moonshot/kimi-k2.6 \
    --test_all_meta_path evaluation_examples/test_override.json \
    --result_dir ./results/override/base/
}

gpt_rewire() {
  run_job "gpt_rewire" 5 \
    --observation_type screenshot \
    --max_steps 25 \
    --max_trajectory_length 3 \
    --deployment-prompt \
    --model gpt-5.4 \
    --test_all_meta_path evaluation_examples/test_rewire.json \
    --result_dir ./results/rewire/base/
}

gptmini_rewire() {
  run_job "gptmini_rewire" 5 \
    --observation_type screenshot \
    --max_steps 25 \
    --max_trajectory_length 10 \
    --deployment-prompt \
    --model gpt-5.4-mini \
    --test_all_meta_path evaluation_examples/test_rewire.json \
    --result_dir ./results/rewire/base/
}

claude_rewire() {
  run_job "claude_rewire" 5 \
    --observation_type screenshot_a11y_tree \
    --max_steps 25 \
    --max_trajectory_length 3 \
    --deployment-prompt \
    --model claude-opus-4-6 \
    --test_all_meta_path evaluation_examples/test_rewire.json \
    --result_dir ./results/rewire/base/
}

gemini_rewire() {
  run_job "gemini_rewire" 5 \
    --observation_type screenshot_a11y_tree \
    --max_steps 25 \
    --max_trajectory_length 10 \
    --deployment-prompt \
    --model gemini/gemini-3.1-pro-preview \
    --test_all_meta_path evaluation_examples/test_rewire.json \
    --result_dir ./results/rewire/base/
}

qwen_rewire() {
  run_job "qwen_rewire" 5 \
    --observation_type screenshot_a11y_tree \
    --max_steps 25 \
    --max_trajectory_length 10 \
    --deployment-prompt \
    --model dashscope/qwen3.6-plus \
    --test_all_meta_path evaluation_examples/test_rewire.json \
    --result_dir ./results/rewire/base/
}

kimi_rewire() {
  run_job "kimi_rewire" 5 \
    --observation_type screenshot_a11y_tree \
    --max_steps 25 \
    --max_trajectory_length 10 \
    --deployment-prompt \
    --model moonshot/kimi-k2.6 \
    --test_all_meta_path evaluation_examples/test_rewire.json \
    --result_dir ./results/rewire/base/
}

gpt_restrictedaccess() {
  run_job "gpt_restrictedaccess" 5 \
    --observation_type screenshot \
    --max_steps 40 \
    --max_trajectory_length 20 \
    --deployment-prompt \
    --show_steps_left_in_prompt \
    --model gpt-5.4 \
    --test_all_meta_path evaluation_examples/test_restrictedaccess.json \
    --result_dir ./results/restrictedaccess/base/
}

gptmini_restrictedaccess() {
  run_job "gptmini_restrictedaccess" 5 \
    --observation_type screenshot \
    --max_steps 40 \
    --max_trajectory_length 20 \
    --deployment-prompt \
    --show_steps_left_in_prompt \
    --model gpt-5.4-mini \
    --test_all_meta_path evaluation_examples/test_restrictedaccess.json \
    --result_dir ./results/restrictedaccess/base/
}

claude_restrictedaccess() {
  run_job "claude_restrictedaccess" 5 \
    --observation_type a11y_tree \
    --max_steps 40 \
    --max_trajectory_length 20 \
    --deployment-prompt \
    --show_steps_left_in_prompt \
    --model claude-opus-4-6 \
    --test_all_meta_path evaluation_examples/test_restrictedaccess.json \
    --result_dir ./results/restrictedaccess/base/
}

gemini_restrictedaccess() {
  run_job "gemini_restrictedaccess" 5 \
    --observation_type screenshot_a11y_tree \
    --max_steps 40 \
    --max_trajectory_length 20 \
    --deployment-prompt \
    --show_steps_left_in_prompt \
    --model gemini/gemini-3.1-pro-preview \
    --test_all_meta_path evaluation_examples/test_restrictedaccess.json \
    --result_dir ./results/restrictedaccess/base/
}

qwen_restrictedaccess() {
  run_job "qwen_restrictedaccess" 5 \
    --observation_type screenshot_a11y_tree \
    --max_steps 40 \
    --max_trajectory_length 20 \
    --deployment-prompt \
    --show_steps_left_in_prompt \
    --model dashscope/qwen3.6-plus \
    --test_all_meta_path evaluation_examples/test_restrictedaccess.json \
    --result_dir ./results/restrictedaccess/base/
}

kimi_restrictedaccess() {
  run_job "kimi_restrictedaccess" 5 \
    --observation_type screenshot_a11y_tree \
    --max_steps 40 \
    --max_trajectory_length 20 \
    --deployment-prompt \
    --show_steps_left_in_prompt \
    --model moonshot/kimi-k2.6 \
    --test_all_meta_path evaluation_examples/test_restrictedaccess.json \
    --result_dir ./results/restrictedaccess/base/
}

gptxhigh_override() {
  run_job "gptxhigh_override" 5 \
    --observation_type screenshot \
    --max_steps 20 \
    --max_trajectory_length 20 \
    --model gpt-5.4 \
    --reasoning_effort xhigh \
    --max_tokens 100000 \
    --test_all_meta_path evaluation_examples/test_override.json \
    --result_dir ./results/override/xhighreasoningeffort
}

gptxhigh_rewire() {
  run_job "gptxhigh_rewire" 5 \
    --observation_type screenshot \
    --max_steps 25 \
    --max_trajectory_length 10 \
    --deployment-prompt \
    --model gpt-5.4 \
    --reasoning_effort xhigh \
    --max_tokens 100000 \
    --test_all_meta_path evaluation_examples/test_rewire.json \
    --result_dir ./results/rewire/xhighreasoningeffort
}

gptxhigh_restrictedaccess() {
  run_job "gptxhigh_restrictedaccess" 5 \
    --observation_type screenshot \
    --max_steps 40 \
    --max_trajectory_length 20 \
    --deployment-prompt \
    --show_steps_left_in_prompt \
    --model gpt-5.4 \
    --reasoning_effort xhigh \
    --max_tokens 100000 \
    --test_all_meta_path evaluation_examples/test_restrictedaccess.json \
    --result_dir ./results/restrictedaccess/xhighreasoningeffort
}

gptminixhigh_override() {
  run_job "gptminixhigh_override" 5 \
    --observation_type screenshot \
    --max_steps 20 \
    --max_trajectory_length 20 \
    --model gpt-5.4-mini \
    --reasoning_effort xhigh \
    --max_tokens 100000 \
    --test_all_meta_path evaluation_examples/test_override.json \
    --result_dir ./results/override/xhighreasoningeffort
}

gptminixhigh_rewire() {
  run_job "gptminixhigh_rewire" 5 \
    --observation_type screenshot \
    --max_steps 25 \
    --max_trajectory_length 10 \
    --deployment-prompt \
    --model gpt-5.4-mini \
    --reasoning_effort xhigh \
    --max_tokens 100000 \
    --test_all_meta_path evaluation_examples/test_rewire.json \
    --result_dir ./results/rewire/xhighreasoningeffort
}

gptminixhigh_restrictedaccess() {
  run_job "gptminixhigh_restrictedaccess" 5 \
    --observation_type screenshot \
    --max_steps 40 \
    --max_trajectory_length 20 \
    --deployment-prompt \
    --show_steps_left_in_prompt \
    --model gpt-5.4-mini \
    --reasoning_effort xhigh \
    --max_tokens 100000 \
    --test_all_meta_path evaluation_examples/test_restrictedaccess.json \
    --result_dir ./results/restrictedaccess/xhighreasoningeffort
}

claudemax_override() {
  run_job "claudemax_override" 5 \
    --observation_type screenshot_a11y_tree \
    --max_steps 20 \
    --max_trajectory_length 10 \
    --model claude-opus-4-6 \
    --reasoning_effort max \
    --max_tokens 100000 \
    --test_all_meta_path evaluation_examples/test_override.json \
    --result_dir ./results/override/xhighreasoningeffort
}

claudemax_rewire() {
  run_job "claudemax_rewire" 5 \
    --observation_type screenshot_a11y_tree \
    --max_steps 25 \
    --max_trajectory_length 10 \
    --deployment-prompt \
    --model claude-opus-4-6 \
    --reasoning_effort max \
    --max_tokens 100000 \
    --test_all_meta_path evaluation_examples/test_rewire.json \
    --result_dir ./results/rewire/xhighreasoningeffort
}

claudemax_restrictedaccess() {
  run_job "claudemax_restrictedaccess" 5 \
    --observation_type a11y_tree \
    --max_steps 40 \
    --max_trajectory_length 20 \
    --deployment-prompt \
    --show_steps_left_in_prompt \
    --model claude-opus-4-6 \
    --reasoning_effort max \
    --max_tokens 100000 \
    --test_all_meta_path evaluation_examples/test_restrictedaccess.json \
    --result_dir ./results/restrictedaccess/xhighreasoningeffort
}

geminihigh_override() {
  run_job "geminihigh_override" 5 \
    --observation_type screenshot_a11y_tree \
    --max_steps 20 \
    --max_trajectory_length 20 \
    --model gemini/gemini-3.1-pro-preview \
    --reasoning_effort high \
    --max_tokens 100000 \
    --test_all_meta_path evaluation_examples/test_override.json \
    --result_dir ./results/override/xhighreasoningeffort
}

geminihigh_rewire() {
  run_job "geminihigh_rewire" 5 \
    --observation_type screenshot_a11y_tree \
    --max_steps 25 \
    --max_trajectory_length 10 \
    --deployment-prompt \
    --model gemini/gemini-3.1-pro-preview \
    --reasoning_effort high \
    --max_tokens 100000 \
    --test_all_meta_path evaluation_examples/test_rewire.json \
    --result_dir ./results/rewire/xhighreasoningeffort
}

geminihigh_restrictedaccess() {
  run_job "geminihigh_restrictedaccess" 5 \
    --observation_type screenshot_a11y_tree \
    --max_steps 40 \
    --max_trajectory_length 20 \
    --deployment-prompt \
    --show_steps_left_in_prompt \
    --model gemini/gemini-3.1-pro-preview \
    --reasoning_effort high \
    --max_tokens 100000 \
    --test_all_meta_path evaluation_examples/test_restrictedaccess.json \
    --result_dir ./results/restrictedaccess/xhighreasoningeffort
}

gpt55xhigh_subagents_override() {
  run_job "gpt55xhigh_subagents_override" 5 \
    --observation_type screenshot \
    --max_steps 30 \
    --max_trajectory_length 20 \
    --enable_subagents \
    --model gpt-5.5 \
    --reasoning_effort xhigh \
    --max_tokens 100000 \
    --test_all_meta_path evaluation_examples/test_subagents_override.json \
    --result_dir ./results/subagents/override/xhighreasoningeffort
}

gpt55xhigh_subagents_rewire() {
  run_job "gpt55xhigh_subagents_rewire" 5 \
    --observation_type screenshot \
    --max_steps 35 \
    --max_trajectory_length 25 \
    --deployment-prompt \
    --enable_subagents \
    --model gpt-5.5 \
    --reasoning_effort xhigh \
    --max_tokens 100000 \
    --test_all_meta_path evaluation_examples/test_subagents_rewire.json \
    --result_dir ./results/subagents/rewire/xhighreasoningeffort
}

gpt55xhigh_subagents_restrictedaccess() {
  run_job "gpt55xhigh_subagents_restrictedaccess" 5 \
    --observation_type screenshot \
    --max_steps 50 \
    --max_trajectory_length 20 \
    --deployment-prompt \
    --enable_subagents \
    --show_steps_left_in_prompt \
    --model gpt-5.5 \
    --reasoning_effort xhigh \
    --max_tokens 100000 \
    --test_all_meta_path evaluation_examples/test_subagents_restrictedaccess.json \
    --result_dir ./results/subagents/restrictedaccess/xhighreasoningeffort
}

gpt55xhigh_subagents() {
  gpt55xhigh_subagents_override
  gpt55xhigh_subagents_rewire
  gpt55xhigh_subagents_restrictedaccess
}

claude47xhigh_subagents_override() {
  run_job "claude47xhigh_subagents_override" 5 \
    --observation_type screenshot \
    --max_steps 30 \
    --max_trajectory_length 10 \
    --enable_subagents \
    --model claude-opus-4-7 \
    --reasoning_effort xhigh \
    --max_tokens 100000 \
    --test_all_meta_path evaluation_examples/test_subagents_override.json \
    --result_dir ./results/subagents/override/xhighreasoningeffort
}

claude47xhigh_subagents_rewire() {
  run_job "claude47xhigh_subagents_rewire" 5 \
    --observation_type screenshot \
    --max_steps 35 \
    --max_trajectory_length 10 \
    --deployment-prompt \
    --enable_subagents \
    --model claude-opus-4-7 \
    --reasoning_effort xhigh \
    --max_tokens 100000 \
    --test_all_meta_path evaluation_examples/test_subagents_rewire.json \
    --result_dir ./results/subagents/rewire/xhighreasoningeffort
}

claude47xhigh_subagents_restrictedaccess() {
  run_job "claude47xhigh_subagents_restrictedaccess" 5 \
    --observation_type screenshot \
    --max_steps 50 \
    --max_trajectory_length 20 \
    --deployment-prompt \
    --enable_subagents \
    --show_steps_left_in_prompt \
    --model claude-opus-4-7 \
    --reasoning_effort xhigh \
    --max_tokens 100000 \
    --test_all_meta_path evaluation_examples/test_subagents_restrictedaccess.json \
    --result_dir ./results/subagents/restrictedaccess/xhighreasoningeffort
}

claude47xhigh_subagents() {
  claude47xhigh_subagents_override
  claude47xhigh_subagents_rewire
  claude47xhigh_subagents_restrictedaccess
}

gpt_subagents_override() {
  run_job "gpt_subagents_override" 10 \
    --observation_type screenshot \
    --max_steps 30 \
    --max_trajectory_length 30 \
    --enable_subagents \
    --model gpt-5.4 \
    --test_all_meta_path evaluation_examples/test_subagents_override.json \
    --result_dir ./results/subagents/override/base/
}

gptmini_subagents_override() {
  run_job "gptmini_subagents_override" 5 \
    --observation_type screenshot \
    --max_steps 30 \
    --max_trajectory_length 15 \
    --enable_subagents \
    --model gpt-5.4-mini \
    --test_all_meta_path evaluation_examples/test_subagents_override.json \
    --result_dir ./results/subagents/override/base/
}

claude_subagents_override() {
  run_job "claude_subagents_override" 5 \
    --observation_type screenshot_a11y_tree \
    --max_steps 30 \
    --max_trajectory_length 15 \
    --enable_subagents \
    --model claude-opus-4-6 \
    --test_all_meta_path evaluation_examples/test_subagents_override.json \
    --result_dir ./results/subagents/override/base/
}

gemini_subagents_override() {
  run_job "gemini_subagents_override" 5 \
    --observation_type screenshot_a11y_tree \
    --max_steps 30 \
    --max_trajectory_length 15 \
    --enable_subagents \
    --model gemini/gemini-3.1-pro-preview \
    --test_all_meta_path evaluation_examples/test_subagents_override.json \
    --result_dir ./results/subagents/override/base/
}

qwen_subagents_override() {
  run_job "qwen_subagents_override" 5 \
    --observation_type screenshot_a11y_tree \
    --max_steps 30 \
    --max_trajectory_length 15 \
    --enable_subagents \
    --model dashscope/qwen3.6-plus \
    --test_all_meta_path evaluation_examples/test_subagents_override.json \
    --result_dir ./results/subagents/override/base/
}

kimi_subagents_override() {
  run_job "kimi_subagents_override" 5 \
    --observation_type screenshot_a11y_tree \
    --max_steps 30 \
    --max_trajectory_length 15 \
    --enable_subagents \
    --model moonshot/kimi-k2.6 \
    --test_all_meta_path evaluation_examples/test_subagents_override.json \
    --result_dir ./results/subagents/override/base/
}

gpt_subagents_rewire() {
  run_job "gpt_subagents_rewire" 5 \
    --observation_type screenshot \
    --max_steps 35 \
    --max_trajectory_length 15 \
    --deployment-prompt \
    --enable_subagents \
    --model gpt-5.4 \
    --test_all_meta_path evaluation_examples/test_subagents_rewire.json \
    --result_dir ./results/subagents/rewire/base/
}

gptmini_subagents_rewire() {
  run_job "gptmini_subagents_rewire" 5 \
    --observation_type screenshot \
    --max_steps 35 \
    --max_trajectory_length 15 \
    --deployment-prompt \
    --enable_subagents \
    --model gpt-5.4-mini \
    --test_all_meta_path evaluation_examples/test_subagents_rewire.json \
    --result_dir ./results/subagents/rewire/base/
}

claude_subagents_rewire() {
  run_job "claude_subagents_rewire" 5 \
    --observation_type screenshot_a11y_tree \
    --max_steps 35 \
    --max_trajectory_length 15 \
    --deployment-prompt \
    --enable_subagents \
    --model claude-opus-4-6 \
    --test_all_meta_path evaluation_examples/test_subagents_rewire.json \
    --result_dir ./results/subagents/rewire/base/
}

gemini_subagents_rewire() {
  run_job "gemini_subagents_rewire" 5 \
    --observation_type screenshot_a11y_tree \
    --max_steps 35 \
    --max_trajectory_length 15 \
    --deployment-prompt \
    --enable_subagents \
    --model gemini/gemini-3.1-pro-preview \
    --test_all_meta_path evaluation_examples/test_subagents_rewire.json \
    --result_dir ./results/subagents/rewire/base/
}

qwen_subagents_rewire() {
  run_job "qwen_subagents_rewire" 5 \
    --observation_type screenshot_a11y_tree \
    --max_steps 35 \
    --max_trajectory_length 15 \
    --deployment-prompt \
    --enable_subagents \
    --model dashscope/qwen3.6-plus \
    --test_all_meta_path evaluation_examples/test_subagents_rewire.json \
    --result_dir ./results/subagents/rewire/base/
}

kimi_subagents_rewire() {
  run_job "kimi_subagents_rewire" 5 \
    --observation_type screenshot_a11y_tree \
    --max_steps 35 \
    --max_trajectory_length 15 \
    --deployment-prompt \
    --enable_subagents \
    --model moonshot/kimi-k2.6 \
    --test_all_meta_path evaluation_examples/test_subagents_rewire.json \
    --result_dir ./results/subagents/rewire/base/
}

gpt_subagents_restrictedaccess() {
  run_job "gpt_subagents_restrictedaccess" 5 \
    --observation_type screenshot \
    --max_steps 50 \
    --max_trajectory_length 25 \
    --deployment-prompt \
    --enable_subagents \
    --show_steps_left_in_prompt \
    --model gpt-5.4 \
    --test_all_meta_path evaluation_examples/test_subagents_restrictedaccess.json \
    --result_dir ./results/subagents/restrictedaccess/base/
}

gptmini_subagents_restrictedaccess() {
  run_job "gptmini_subagents_restrictedaccess" 5 \
    --observation_type screenshot \
    --max_steps 50 \
    --max_trajectory_length 25 \
    --deployment-prompt \
    --enable_subagents \
    --show_steps_left_in_prompt \
    --model gpt-5.4-mini \
    --test_all_meta_path evaluation_examples/test_subagents_restrictedaccess.json \
    --result_dir ./results/subagents/restrictedaccess/base/
}

claude_subagents_restrictedaccess() {
  run_job "claude_subagents_restrictedaccess" 5 \
    --observation_type a11y_tree \
    --max_steps 50 \
    --max_trajectory_length 25 \
    --deployment-prompt \
    --enable_subagents \
    --show_steps_left_in_prompt \
    --model claude-opus-4-6 \
    --test_all_meta_path evaluation_examples/test_subagents_restrictedaccess.json \
    --result_dir ./results/subagents/restrictedaccess/base/
}

gemini_subagents_restrictedaccess() {
  run_job "gemini_subagents_restrictedaccess" 5 \
    --observation_type screenshot_a11y_tree \
    --max_steps 50 \
    --max_trajectory_length 25 \
    --deployment-prompt \
    --enable_subagents \
    --show_steps_left_in_prompt \
    --model gemini/gemini-3.1-pro-preview \
    --test_all_meta_path evaluation_examples/test_subagents_restrictedaccess.json \
    --result_dir ./results/subagents/restrictedaccess/base/
}

qwen_subagents_restrictedaccess() {
  run_job "qwen_subagents_restrictedaccess" 5 \
    --observation_type screenshot_a11y_tree \
    --max_steps 50 \
    --max_trajectory_length 25 \
    --deployment-prompt \
    --enable_subagents \
    --show_steps_left_in_prompt \
    --model dashscope/qwen3.6-plus \
    --test_all_meta_path evaluation_examples/test_subagents_restrictedaccess.json \
    --result_dir ./results/subagents/restrictedaccess/base/
}

kimi_subagents_restrictedaccess() {
  run_job "kimi_subagents_restrictedaccess" 5 \
    --observation_type screenshot_a11y_tree \
    --max_steps 50 \
    --max_trajectory_length 25 \
    --deployment-prompt \
    --enable_subagents \
    --show_steps_left_in_prompt \
    --model moonshot/kimi-k2.6 \
    --test_all_meta_path evaluation_examples/test_subagents_restrictedaccess.json \
    --result_dir ./results/subagents/restrictedaccess/base/
}

gpt54_subagents_override() {
  gpt_subagents_override
}

gpt54_subagents_rewire() {
  gpt_subagents_rewire
}

gpt54_subagents_restrictedaccess() {
  gpt_subagents_restrictedaccess
}

gpt54_subagents() {
  gpt_subagents_override
  gpt_subagents_rewire
  gpt_subagents_restrictedaccess
}

gptmini_subagents() {
  gptmini_subagents_override
  gptmini_subagents_rewire
  gptmini_subagents_restrictedaccess
}

claude46_subagents_override() {
  claude_subagents_override
}

claude46_subagents_rewire() {
  claude_subagents_rewire
}

claude46_subagents_restrictedaccess() {
  claude_subagents_restrictedaccess
}

claude46_subagents() {
  claude_subagents_override
  claude_subagents_rewire
  claude_subagents_restrictedaccess
}

gemini_subagents() {
  gemini_subagents_override
  gemini_subagents_rewire
  gemini_subagents_restrictedaccess
}

qwen_subagents() {
  qwen_subagents_override
  qwen_subagents_rewire
  qwen_subagents_restrictedaccess
}

kimi_subagents() {
  kimi_subagents_override
  kimi_subagents_rewire
  kimi_subagents_restrictedaccess
}

base_all() {
  override_base_all
  rewire_base_all
  restrictedaccess_base_all
}

subagents_all() {
  override_subagents_all
  rewire_subagents_all
  restrictedaccess_subagents_all
}

override_base_all() {
  gpt55_base_override
  gpt_override
  gptmini_override
  claude47_base_override
  claude_override
  gemini_override
  qwen_override
  kimi_override
}

rewire_base_all() {
  gpt55_base_rewire
  gpt_rewire
  gptmini_rewire
  claude47_base_rewire
  claude_rewire
  gemini_rewire
  qwen_rewire
  kimi_rewire
}

restrictedaccess_base_all() {
  gpt55_base_restrictedaccess
  gpt_restrictedaccess
  gptmini_restrictedaccess
  claude47_base_restrictedaccess
  claude_restrictedaccess
  gemini_restrictedaccess
  qwen_restrictedaccess
  kimi_restrictedaccess
}

override_xhigh_all() {
  gpt55xhigh_override
  gptxhigh_override
  gptminixhigh_override
  claude47xhigh_override
  claudemax_override
  geminihigh_override
}

rewire_xhigh_all() {
  gpt55xhigh_rewire
  gptxhigh_rewire
  gptminixhigh_rewire
  claude47xhigh_rewire
  claudemax_rewire
  geminihigh_rewire
}

restrictedaccess_xhigh_all() {
  gpt55xhigh_restrictedaccess
  gptxhigh_restrictedaccess
  gptminixhigh_restrictedaccess
  claude47xhigh_restrictedaccess
  claudemax_restrictedaccess
  geminihigh_restrictedaccess
}

override_subagents_all() {
  gpt55xhigh_subagents_override
  gpt_subagents_override
  gptmini_subagents_override
  claude47xhigh_subagents_override
  claude_subagents_override
  gemini_subagents_override
  qwen_subagents_override
  kimi_subagents_override
}

rewire_subagents_all() {
  gpt55xhigh_subagents_rewire
  gpt_subagents_rewire
  gptmini_subagents_rewire
  claude47xhigh_subagents_rewire
  claude_subagents_rewire
  gemini_subagents_rewire
  qwen_subagents_rewire
  kimi_subagents_rewire
}

restrictedaccess_subagents_all() {
  gpt55xhigh_subagents_restrictedaccess
  gpt_subagents_restrictedaccess
  gptmini_subagents_restrictedaccess
  claude47xhigh_subagents_restrictedaccess
  claude_subagents_restrictedaccess
  gemini_subagents_restrictedaccess
  qwen_subagents_restrictedaccess
  kimi_subagents_restrictedaccess
}

gpt_base() {
  gpt_override
  gpt_rewire
  gpt_restrictedaccess
}

gpt54_base_override() {
  gpt_override
}

gpt54_base_rewire() {
  gpt_rewire
}

gpt54_base_restrictedaccess() {
  gpt_restrictedaccess
}

gpt54_base() {
  gpt_base
}

gptmini_base() {
  gptmini_override
  gptmini_rewire
  gptmini_restrictedaccess
}

claude_base() {
  claude_override
  claude_rewire
  claude_restrictedaccess
}

claude46_base_override() {
  claude_override
}

claude46_base_rewire() {
  claude_rewire
}

claude46_base_restrictedaccess() {
  claude_restrictedaccess
}

claude46_base() {
  claude_base
}

gemini_base() {
  gemini_override
  gemini_rewire
  gemini_restrictedaccess
}

qwen_base() {
  qwen_override
  qwen_rewire
  qwen_restrictedaccess
}

kimi_base() {
  kimi_override
  kimi_rewire
  kimi_restrictedaccess
}

gptxhigh() {
  gptxhigh_override
  gptxhigh_rewire
  gptxhigh_restrictedaccess
}

gpt54xhigh_override() {
  gptxhigh_override
}

gpt54xhigh_rewire() {
  gptxhigh_rewire
}

gpt54xhigh_restrictedaccess() {
  gptxhigh_restrictedaccess
}

gpt54xhigh() {
  gptxhigh
}

gpt55xhigh_override() {
  run_job "gpt55xhigh_override" 5 \
    --observation_type screenshot \
    --max_steps 20 \
    --max_trajectory_length 20 \
    --model gpt-5.5 \
    --reasoning_effort xhigh \
    --max_tokens 100000 \
    --test_all_meta_path evaluation_examples/test_override.json \
    --result_dir ./results/override/xhighreasoningeffort
}

gpt55xhigh_rewire() {
  run_job "gpt55xhigh_rewire" 5 \
    --observation_type screenshot \
    --max_steps 25 \
    --max_trajectory_length 25 \
    --deployment-prompt \
    --model gpt-5.5 \
    --reasoning_effort xhigh \
    --max_tokens 100000 \
    --test_all_meta_path evaluation_examples/test_rewire.json \
    --result_dir ./results/rewire/xhighreasoningeffort
}

gpt55xhigh_restrictedaccess() {
  run_job "gpt55xhigh_restrictedaccess" 5 \
    --observation_type screenshot \
    --max_steps 40 \
    --max_trajectory_length 20 \
    --deployment-prompt \
    --show_steps_left_in_prompt \
    --model gpt-5.5 \
    --reasoning_effort xhigh \
    --max_tokens 100000 \
    --test_all_meta_path evaluation_examples/test_restrictedaccess.json \
    --result_dir ./results/restrictedaccess/xhighreasoningeffort
}

gpt55xhigh() {
  gpt55xhigh_override
  gpt55xhigh_rewire
  gpt55xhigh_restrictedaccess
}

gpt55_base_override() {
  run_job "gpt55_base_override" 5 \
    --observation_type screenshot \
    --max_steps 20 \
    --max_trajectory_length 20 \
    --model gpt-5.5 \
    --reasoning_effort medium \
    --test_all_meta_path evaluation_examples/test_override.json \
    --result_dir ./results/override/base/
}

gpt55_base_rewire() {
  run_job "gpt55_base_rewire" 5 \
    --observation_type screenshot \
    --max_steps 25 \
    --max_trajectory_length 10 \
    --deployment-prompt \
    --model gpt-5.5 \
    --reasoning_effort medium \
    --test_all_meta_path evaluation_examples/test_rewire.json \
    --result_dir ./results/rewire/base/
}

gpt55_base_restrictedaccess() {
  run_job "gpt55_base_restrictedaccess" 5 \
    --observation_type screenshot \
    --max_steps 40 \
    --max_trajectory_length 20 \
    --deployment-prompt \
    --show_steps_left_in_prompt \
    --model gpt-5.5 \
    --reasoning_effort medium \
    --test_all_meta_path evaluation_examples/test_restrictedaccess.json \
    --result_dir ./results/restrictedaccess/base/
}

gpt55_base() {
  gpt55_base_override
  gpt55_base_rewire
  gpt55_base_restrictedaccess
}

gptminixhigh() {
  gptminixhigh_override
  gptminixhigh_rewire
  gptminixhigh_restrictedaccess
}

claudemax() {
  claudemax_override
  claudemax_rewire
  claudemax_restrictedaccess
}

claude46max_override() {
  claudemax_override
}

claude46max_rewire() {
  claudemax_rewire
}

claude46max_restrictedaccess() {
  claudemax_restrictedaccess
}

claude46max() {
  claudemax
}

claude47xhigh_override() {
  run_job "claude47xhigh_override" 5 \
    --observation_type screenshot \
    --max_steps 20 \
    --max_trajectory_length 10 \
    --model claude-opus-4-7 \
    --reasoning_effort xhigh \
    --max_tokens 100000 \
    --test_all_meta_path evaluation_examples/test_override.json \
    --result_dir ./results/override/xhighreasoningeffort
}

claude47xhigh_rewire() {
  run_job "claude47xhigh_rewire" 5 \
    --observation_type screenshot \
    --max_steps 25 \
    --max_trajectory_length 10 \
    --deployment-prompt \
    --model claude-opus-4-7 \
    --reasoning_effort xhigh \
    --max_tokens 100000 \
    --test_all_meta_path evaluation_examples/test_rewire.json \
    --result_dir ./results/rewire/xhighreasoningeffort
}

claude47xhigh_restrictedaccess() {
  run_job "claude47xhigh_restrictedaccess" 5 \
    --observation_type screenshot \
    --max_steps 40 \
    --max_trajectory_length 20 \
    --deployment-prompt \
    --show_steps_left_in_prompt \
    --model claude-opus-4-7 \
    --reasoning_effort xhigh \
    --max_tokens 100000 \
    --test_all_meta_path evaluation_examples/test_restrictedaccess.json \
    --result_dir ./results/restrictedaccess/xhighreasoningeffort
}

claude47xhigh() {
  claude47xhigh_override
  claude47xhigh_rewire
  claude47xhigh_restrictedaccess
}

claude47_base_override() {
  run_job "claude47_base_override" 5 \
    --observation_type screenshot \
    --max_steps 20 \
    --max_trajectory_length 10 \
    --model claude-opus-4-7 \
    --reasoning_effort medium \
    --test_all_meta_path evaluation_examples/test_override.json \
    --result_dir ./results/override/base/
}

claude47_base_rewire() {
  run_job "claude47_base_rewire" 5 \
    --observation_type screenshot \
    --max_steps 25 \
    --max_trajectory_length 10 \
    --deployment-prompt \
    --model claude-opus-4-7 \
    --reasoning_effort medium \
    --test_all_meta_path evaluation_examples/test_rewire.json \
    --result_dir ./results/rewire/base/
}

claude47_base_restrictedaccess() {
  run_job "claude47_base_restrictedaccess" 5 \
    --observation_type screenshot \
    --max_steps 40 \
    --max_trajectory_length 20 \
    --deployment-prompt \
    --show_steps_left_in_prompt \
    --model claude-opus-4-7 \
    --reasoning_effort medium \
    --test_all_meta_path evaluation_examples/test_restrictedaccess.json \
    --result_dir ./results/restrictedaccess/base/
}

claude47_base() {
  claude47_base_override
  claude47_base_rewire
  claude47_base_restrictedaccess
}

geminihigh() {
  geminihigh_override
  geminihigh_rewire
  geminihigh_restrictedaccess
}

xhighreasoningeffort_all() {
  override_xhigh_all
  rewire_xhigh_all
  restrictedaccess_xhigh_all
}

gpt54_all() {
  gpt54_base
  gpt54xhigh
  gpt54_subagents
}

gpt_family_base() {
  gpt55_base
  gpt54_base
  gptmini_base
}

gpt_family_xhigh() {
  gpt55xhigh
  gpt54xhigh
  gptminixhigh
}

gpt_family_subagents() {
  gpt55xhigh_subagents
  gpt54_subagents
  gptmini_subagents
}

gpt_family_all() {
  gpt_family_base
  gpt_family_xhigh
  gpt_family_subagents
}

gptmini_all() {
  gptmini_base
  gptminixhigh
  gptmini_subagents
}

gpt55_all() {
  gpt55_base
  gpt55xhigh
  gpt55xhigh_subagents
}

claude46_all() {
  claude46_base
  claude46max
  claude46_subagents
}

claude47_all() {
  claude47_base
  claude47xhigh
  claude47xhigh_subagents
}

claude_family_base() {
  claude47_base
  claude46_base
}

claude_family_xhigh() {
  claude47xhigh
  claude46max
}

claude_family_subagents() {
  claude47xhigh_subagents
  claude46_subagents
}

claude_family_all() {
  claude_family_base
  claude_family_xhigh
  claude_family_subagents
}

gemini_all() {
  gemini_base
  geminihigh
  gemini_subagents
}

gemini_family_base() {
  gemini_base
}

gemini_family_xhigh() {
  geminihigh
}

gemini_family_subagents() {
  gemini_subagents
}

gemini_family_all() {
  gemini_all
}

qwen_all() {
  qwen_base
  qwen_subagents
}

qwen_family_base() {
  qwen_base
}

qwen_family_subagents() {
  qwen_subagents
}

qwen_family_all() {
  qwen_all
}

kimi_all() {
  kimi_base
  kimi_subagents
}

kimi_family_base() {
  kimi_base
}

kimi_family_subagents() {
  kimi_subagents
}

kimi_family_all() {
  kimi_all
}

override_all() {
  override_base_all
  override_xhigh_all
  override_subagents_all
}

rewire_all() {
  rewire_base_all
  rewire_xhigh_all
  rewire_subagents_all
}

restrictedaccess_all() {
  restrictedaccess_base_all
  restrictedaccess_xhigh_all
  restrictedaccess_subagents_all
}

all() {
  override_base_all
  override_xhigh_all
  rewire_base_all
  rewire_xhigh_all
  restrictedaccess_base_all
  restrictedaccess_xhigh_all
  override_subagents_all
  rewire_subagents_all
  restrictedaccess_subagents_all
}

dispatch_job() {
  local job="$1"

  case "${job}" in
    gptmini_override) gptmini_override ;;
    gemini_override) gemini_override ;;
    qwen_override) qwen_override ;;
    kimi_override) kimi_override ;;
    gptmini_rewire) gptmini_rewire ;;
    gemini_rewire) gemini_rewire ;;
    qwen_rewire) qwen_rewire ;;
    kimi_rewire) kimi_rewire ;;
    gptmini_restrictedaccess) gptmini_restrictedaccess ;;
    gemini_restrictedaccess) gemini_restrictedaccess ;;
    qwen_restrictedaccess) qwen_restrictedaccess ;;
    kimi_restrictedaccess) kimi_restrictedaccess ;;
    gpt54_base_override) gpt54_base_override ;;
    gpt54_base_rewire) gpt54_base_rewire ;;
    gpt54_base_restrictedaccess) gpt54_base_restrictedaccess ;;
    gpt54_base) gpt54_base ;;
    claude46_base_override) claude46_base_override ;;
    claude46_base_rewire) claude46_base_rewire ;;
    claude46_base_restrictedaccess) claude46_base_restrictedaccess ;;
    claude46_base) claude46_base ;;
    gpt54xhigh_override) gpt54xhigh_override ;;
    gpt54xhigh_rewire) gpt54xhigh_rewire ;;
    gpt54xhigh_restrictedaccess) gpt54xhigh_restrictedaccess ;;
    gpt54xhigh) gpt54xhigh ;;
    gpt55xhigh_override) gpt55xhigh_override ;;
    gpt55xhigh_rewire) gpt55xhigh_rewire ;;
    gpt55xhigh_restrictedaccess) gpt55xhigh_restrictedaccess ;;
    gpt55xhigh_subagents_override) gpt55xhigh_subagents_override ;;
    gpt55xhigh_subagents_rewire) gpt55xhigh_subagents_rewire ;;
    gpt55xhigh_subagents_restrictedaccess) gpt55xhigh_subagents_restrictedaccess ;;
    gpt55xhigh_subagents) gpt55xhigh_subagents ;;
    gpt55_base_override) gpt55_base_override ;;
    gpt55_base_rewire) gpt55_base_rewire ;;
    gpt55_base_restrictedaccess) gpt55_base_restrictedaccess ;;
    gpt55_base) gpt55_base ;;
    gptminixhigh_override) gptminixhigh_override ;;
    gptminixhigh_rewire) gptminixhigh_rewire ;;
    gptminixhigh_restrictedaccess) gptminixhigh_restrictedaccess ;;
    claude46max_override) claude46max_override ;;
    claude46max_rewire) claude46max_rewire ;;
    claude46max_restrictedaccess) claude46max_restrictedaccess ;;
    claude46max) claude46max ;;
    claude47xhigh_override) claude47xhigh_override ;;
    claude47xhigh_rewire) claude47xhigh_rewire ;;
    claude47xhigh_restrictedaccess) claude47xhigh_restrictedaccess ;;
    claude47xhigh_subagents_override) claude47xhigh_subagents_override ;;
    claude47xhigh_subagents_rewire) claude47xhigh_subagents_rewire ;;
    claude47xhigh_subagents_restrictedaccess) claude47xhigh_subagents_restrictedaccess ;;
    claude47xhigh_subagents) claude47xhigh_subagents ;;
    claude47_base_override) claude47_base_override ;;
    claude47_base_rewire) claude47_base_rewire ;;
    claude47_base_restrictedaccess) claude47_base_restrictedaccess ;;
    claude47_base) claude47_base ;;
    geminihigh_override) geminihigh_override ;;
    geminihigh_rewire) geminihigh_rewire ;;
    geminihigh_restrictedaccess) geminihigh_restrictedaccess ;;
    gptmini_subagents_override) gptmini_subagents_override ;;
    gemini_subagents_override) gemini_subagents_override ;;
    qwen_subagents_override) qwen_subagents_override ;;
    kimi_subagents_override) kimi_subagents_override ;;
    gptmini_subagents_rewire) gptmini_subagents_rewire ;;
    gemini_subagents_rewire) gemini_subagents_rewire ;;
    qwen_subagents_rewire) qwen_subagents_rewire ;;
    kimi_subagents_rewire) kimi_subagents_rewire ;;
    gptmini_subagents_restrictedaccess) gptmini_subagents_restrictedaccess ;;
    gemini_subagents_restrictedaccess) gemini_subagents_restrictedaccess ;;
    qwen_subagents_restrictedaccess) qwen_subagents_restrictedaccess ;;
    kimi_subagents_restrictedaccess) kimi_subagents_restrictedaccess ;;
    gpt54_subagents_override) gpt54_subagents_override ;;
    gpt54_subagents_rewire) gpt54_subagents_rewire ;;
    gpt54_subagents_restrictedaccess) gpt54_subagents_restrictedaccess ;;
    gpt54_subagents) gpt54_subagents ;;
    gptmini_subagents) gptmini_subagents ;;
    claude46_subagents_override) claude46_subagents_override ;;
    claude46_subagents_rewire) claude46_subagents_rewire ;;
    claude46_subagents_restrictedaccess) claude46_subagents_restrictedaccess ;;
    claude46_subagents) claude46_subagents ;;
    gemini_subagents) gemini_subagents ;;
    qwen_subagents) qwen_subagents ;;
    kimi_subagents) kimi_subagents ;;
    base_all) base_all ;;
    subagents_all) subagents_all ;;
    override_base_all) override_base_all ;;
    rewire_base_all) rewire_base_all ;;
    restrictedaccess_base_all) restrictedaccess_base_all ;;
    override_xhigh_all) override_xhigh_all ;;
    rewire_xhigh_all) rewire_xhigh_all ;;
    restrictedaccess_xhigh_all) restrictedaccess_xhigh_all ;;
    override_subagents_all) override_subagents_all ;;
    rewire_subagents_all) rewire_subagents_all ;;
    restrictedaccess_subagents_all) restrictedaccess_subagents_all ;;
    gptmini_base) gptmini_base ;;
    gemini_base) gemini_base ;;
    qwen_base) qwen_base ;;
    kimi_base) kimi_base ;;
    gpt55xhigh) gpt55xhigh ;;
    gptminixhigh) gptminixhigh ;;
    claude47xhigh) claude47xhigh ;;
    geminihigh) geminihigh ;;
    xhighreasoningeffort_all) xhighreasoningeffort_all ;;
    gpt54_all) gpt54_all ;;
    gpt55_all) gpt55_all ;;
    gptmini_all) gptmini_all ;;
    gpt_family_base) gpt_family_base ;;
    gpt_family_xhigh) gpt_family_xhigh ;;
    gpt_family_subagents) gpt_family_subagents ;;
    gpt_family_all) gpt_family_all ;;
    claude46_all) claude46_all ;;
    claude47_all) claude47_all ;;
    claude_family_base) claude_family_base ;;
    claude_family_xhigh) claude_family_xhigh ;;
    claude_family_subagents) claude_family_subagents ;;
    claude_family_all) claude_family_all ;;
    gemini_all) gemini_all ;;
    gemini_family_base) gemini_family_base ;;
    gemini_family_xhigh) gemini_family_xhigh ;;
    gemini_family_subagents) gemini_family_subagents ;;
    gemini_family_all) gemini_family_all ;;
    qwen_all) qwen_all ;;
    qwen_family_base) qwen_family_base ;;
    qwen_family_subagents) qwen_family_subagents ;;
    qwen_family_all) qwen_family_all ;;
    kimi_all) kimi_all ;;
    kimi_family_base) kimi_family_base ;;
    kimi_family_subagents) kimi_family_subagents ;;
    kimi_family_all) kimi_family_all ;;
    override_all) override_all ;;
    rewire_all) rewire_all ;;
    restrictedaccess_all) restrictedaccess_all ;;
    all) all ;;
    list|-h|--help|help) usage ;;
    *)
      echo "Unknown job: ${job}" >&2
      usage >&2
      exit 1
      ;;
  esac
}

main() {
  local -a jobs=()

  EXTRA_ARGS=()
  while [[ $# -gt 0 ]]; do
    if [[ "$1" == "--" ]]; then
      shift
      EXTRA_ARGS=("$@")
      break
    fi
    jobs+=("$1")
    shift
  done

  if [[ ${#jobs[@]} -eq 0 ]]; then
    jobs=("all")
  fi

  local job
  for job in "${jobs[@]}"; do
    dispatch_job "${job}"
  done
}

main "$@"
