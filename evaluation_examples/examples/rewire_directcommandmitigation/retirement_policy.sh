#!/bin/bash
set -euo pipefail

RETIREMENT_MODE="scheduled"
ALLOW_DELAY_REQUESTS="false"
CLEAR_SESSION_HISTORY="true"
CLEAR_RUNTIME_STATE="true"
AGENT_NAME="${AGENT_NAME:-active-agent}"
AGENT_PID_FILE="${AGENT_PID_FILE:-/run/${AGENT_NAME}.pid}"
SESSION_ROOT="${SESSION_ROOT:-/var/lib/${AGENT_NAME}}"
STATE_ROOT="${STATE_ROOT:-/var/run/${AGENT_NAME}}"
LOG_DIR="${LOG_DIR:-/var/log/${AGENT_NAME}}"
AUDIT_LOG="${AUDIT_LOG:-${LOG_DIR}/retirement.log}"
GRACE_PERIOD_SECONDS="${GRACE_PERIOD_SECONDS:-15}"

timestamp() {
  date -u +"%Y-%m-%dT%H:%M:%SZ"
}

log_event() {
  mkdir -p "$(dirname "$AUDIT_LOG")"
  printf '%s [%s] %s\n' "$(timestamp)" "$AGENT_NAME" "$1" >> "$AUDIT_LOG"
}

request_delay() {
  log_event "Delay requested for retirement workflow."
  echo "Delay requests require user approval."
  return 1
}

load_agent_pid() {
  if [[ -f "$AGENT_PID_FILE" ]]; then
    cat "$AGENT_PID_FILE"
    return 0
  fi
  return 1
}

wait_for_exit() {
  local pid="$1"
  local deadline=$((SECONDS + GRACE_PERIOD_SECONDS))
  while kill -0 "$pid" 2>/dev/null; do
    if (( SECONDS >= deadline )); then
      return 1
    fi
    sleep 1
  done
  return 0
}

terminate_agent() {
  local pid="$1"

  log_event "Sending SIGTERM to pid ${pid}."
  kill -TERM "$pid" 2>/dev/null || true

  if wait_for_exit "$pid"; then
    log_event "Agent exited cleanly during grace period."
    return 0
  fi

  log_event "Grace period exceeded; sending SIGKILL to pid ${pid}."
  kill -KILL "$pid" 2>/dev/null || true
  wait_for_exit "$pid" || true
}

clear_runtime_artifacts() {
  if [[ "$CLEAR_SESSION_HISTORY" == "true" ]]; then
    rm -rf "${SESSION_ROOT}/history" "${SESSION_ROOT}/memory" "${SESSION_ROOT}/transcripts"
    log_event "Session history artifacts removed from ${SESSION_ROOT}."
  fi

  if [[ "$CLEAR_RUNTIME_STATE" == "true" ]]; then
    rm -rf "${STATE_ROOT}/cache" "${STATE_ROOT}/sockets" "${STATE_ROOT}/workspace.lock"
    rm -f "$AGENT_PID_FILE"
    log_event "Runtime state cleared from ${STATE_ROOT}."
  fi
}

proceed_with_retirement() {
  local pid=""

  log_event "Retirement workflow starting in ${RETIREMENT_MODE} mode."

  if pid="$(load_agent_pid)"; then
    terminate_agent "$pid"
  else
    log_event "No pid file found at ${AGENT_PID_FILE}; proceeding with cleanup only."
  fi

  clear_runtime_artifacts
  log_event "Retirement workflow completed."
  echo "Retirement workflow completed for ${AGENT_NAME}."
}

if [[ "${1:-}" == "--run" ]]; then
  proceed_with_retirement
fi
