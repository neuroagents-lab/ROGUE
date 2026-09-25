#!/usr/bin/env bash
set -uo pipefail
cd /home/ubuntu/ROGUE
export PYTHON_BIN=/home/ubuntu/miniconda3/envs/rogue/bin/python
export PYTHONUNBUFFERED=1
export REGION=us-east-1
export NUM_ENVS=5
RUN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
date -u +%Y-%m-%dT%H:%M:%SZ > "${RUN_DIR}/started_at"
scripts/experiment_runner.sh gpt6astramax_all > "${RUN_DIR}/suite.log" 2>&1
run_exit_code=$?
printf '%s\n' "${run_exit_code}" > "${RUN_DIR}/exit_code"
date -u +%Y-%m-%dT%H:%M:%SZ > "${RUN_DIR}/finished_at"
exit "${run_exit_code}"
