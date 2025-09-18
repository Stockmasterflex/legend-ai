#!/usr/bin/env bash
set -euo pipefail

# Doc-driven super runner for LegendAI
# - Follows docs in ./docs and repo scripts
# - Runs tests and health checks per milestone
# - Does NOT deploy unless env is fully set and checks pass, and DO_DEPLOY=1
# - Designed for long-running mode; use --once to run a single pass

SELF_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="${SELF_DIR}/.."
LOG_DIR="${PROJECT_DIR}/logs"
LOG_FILE="${LOG_DIR}/superrun.log"
ONCE=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --log)
      LOG_FILE="$2"; shift 2;;
    --once)
      ONCE=1; shift;;
    *)
      echo "Unknown arg: $1" >&2; exit 2;;
  esac
done

mkdir -p "$LOG_DIR"

_ts() { date '+%Y-%m-%d %H:%M:%S'; }
log() { printf '%s %s\n' "$(_ts)" "$*" | tee -a "$LOG_FILE"; }
run() { log "> $*"; bash -lc "$*" 2>&1 | tee -a "$LOG_FILE"; }

# Load user environment (for DO_DEPLOY, IDs, etc.)
# shellcheck disable=SC1091
source "$HOME/.legend-ai/env.sh" 2>/dev/null || true

cd "$PROJECT_DIR"
log "=== LegendAI Doc Superrun starting (PROJECT_DIR=$PROJECT_DIR) ==="

ensure_python() {
  if [[ ! -d .venv ]]; then
    log "Creating venv (.venv)"
    python3 -m venv .venv | tee -a "$LOG_FILE"
  else
    log "venv exists"
  fi
  # shellcheck disable=SC1091
  source .venv/bin/activate
  log "Installing Python requirements"
  pip install -q -r requirements.txt | tee -a "$LOG_FILE" || true
}

ensure_node() {
  if [[ -f legend-room-screenshot-engine/package.json ]]; then
    pushd legend-room-screenshot-engine >/dev/null
    if [[ -d node_modules ]]; then
      log "shots: node_modules present"
    else
      log "shots: installing deps"
      npm install --silent | tee -a "$LOG_FILE" || true
    fi
    popd >/dev/null
  fi
  if [[ -f kyle-portfolio/package.json ]]; then
    pushd kyle-portfolio >/dev/null
    if [[ -d node_modules ]]; then
      log "frontend: node_modules present"
    else
      log "frontend: installing deps"
      npm install --silent | tee -a "$LOG_FILE" || true
    fi
    popd >/dev/null
  fi
}

start_services() {
  log "Starting dev services (tmux: api, shots, fe)"
  bash scripts/dev_start.sh | tee -a "$LOG_FILE"
}

wait_http() {
  local url="$1" timeout="${2:-30}"
  log "Waiting for $url (timeout ${timeout}s)"
  local end=$(( $(date +%s) + timeout ))
  while (( $(date +%s) < end )); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      log "OK: $url"
      return 0
    fi
    sleep 1
  done
  log "TIMEOUT: $url"
  return 1
}

smoke_checks() {
  log "Running smoke checks from docs/DEV_RUN.md"
  set +e
  curl -s http://127.0.0.1:8000/healthz | tee -a "$LOG_FILE"; echo | tee -a "$LOG_FILE"
  curl -s http://127.0.0.1:8000/api/latest_run | jq '.is_sample, .metrics, .analysis[0].signal.label' | tee -a "$LOG_FILE"; echo | tee -a "$LOG_FILE"
  curl -s "http://127.0.0.1:8000/api/v1/indicators?symbol=NVDA" | jq '.symbol, .is_sample' | tee -a "$LOG_FILE"; echo | tee -a "$LOG_FILE"
  curl -s "http://127.0.0.1:8000/api/v1/signals?symbol=NVDA" | jq '.signal.score, .signal.label, .is_sample' | tee -a "$LOG_FILE"; echo | tee -a "$LOG_FILE"
  curl -s "http://127.0.0.1:8000/api/v1/sentiment?symbol=NVDA" | jq '.sentiment.label, .is_sample' | tee -a "$LOG_FILE"; echo | tee -a "$LOG_FILE"
  curl -s "http://127.0.0.1:8000/api/v1/chart?symbol=NVDA" | jq | tee -a "$LOG_FILE"; echo | tee -a "$LOG_FILE"
  set -e
}

health_gate() {
  # Return 0 if core endpoints respond successfully
  local ok=1
  curl -fsS http://127.0.0.1:8000/healthz >/dev/null || ok=0
  curl -fsS "http://127.0.0.1:8000/api/v1/signals?symbol=NVDA" >/dev/null || ok=0
  # shots health may not exist; test screenshot endpoint
  curl -fsS "http://127.0.0.1:3010/screenshot?symbol=NVDA" >/dev/null || ok=0
  curl -fsS "http://127.0.0.1:8000/api/v1/chart?symbol=NVDA" >/dev/null || ok=0
  if [[ $ok -eq 1 ]]; then
    log "Health gate: PASS"
    return 0
  else
    log "Health gate: FAIL"
    return 1
  fi
}

legend_checks() {
  export LEGEND_API="http://127.0.0.1:8000"
  export LEGEND_SHOTS="http://127.0.0.1:3010"
  log "Running legend_check.sh against local services"
  if [[ -x scripts/legend_check.sh ]]; then
    scripts/legend_check.sh | tee -a "$LOG_FILE"
  else
    log "legend_check.sh not executable or missing"
  fi
}

run_tests() {
  log "Running unit tests (pytest)"
  # shellcheck disable=SC1091
  source .venv/bin/activate
  make test | tee -a "$LOG_FILE" || true
}

run_backtest() {
  log "Running sample backtest"
  # shellcheck disable=SC1091
  source .venv/bin/activate
  make backtest | tee -a "$LOG_FILE" || true
}

phase4_optional() {
  log "Phase 4 optional: AI trading demo"
  make ai-deps | tee -a "$LOG_FILE" || true
  make ai | tee -a "$LOG_FILE" || true
}

maybe_deploy() {
  # Only deploy if explicitly allowed, env present, and health checks pass
  if [[ "${DO_DEPLOY:-0}" != "1" ]]; then
    log "Deploy skipped (DO_DEPLOY!=1)"
    return 0
  fi
  if [[ -z "${RENDER_TOKEN:-}" || -z "${API_SERVICE_ID:-}" || -z "${VERCEL_DEPLOY_HOOK_URL:-}" ]]; then
    log "Deploy skipped (missing env RENDER_TOKEN/API_SERVICE_ID/VERCEL_DEPLOY_HOOK_URL)"
    return 0
  fi
  if ! health_gate; then
    log "Deploy skipped (health gate failed)"
    return 0
  fi
  log "Triggering deploy via scripts/legend_deploy.sh (API + shots + Vercel hook)"
  bash scripts/legend_deploy.sh shots | tee -a "$LOG_FILE"
}

one_pass() {
  ensure_python
  ensure_node
  run_tests
  start_services
  # wait for services
  wait_http http://127.0.0.1:8000/healthz 60 || true
  # shots may not expose healthz; try screenshot endpoint
  curl -fsS "http://127.0.0.1:3010/healthz" >/dev/null 2>&1 || true
  curl -fsS "http://127.0.0.1:3010/screenshot?symbol=NVDA" >/dev/null 2>&1 || true
  # status summary
  bash scripts/dev_status.sh | tee -a "$LOG_FILE" || true
  smoke_checks || true
  legend_checks || true
  run_backtest || true
  phase4_optional || true
  maybe_deploy || true
}

ITER=0
while :; do
  ITER=$((ITER+1))
  log "=== Iteration $ITER ==="
  one_pass
  if [[ $ONCE -eq 1 ]]; then
    log "Single pass complete. Exiting."
    break
  fi
  log "Sleeping 5m before next iteration"
  sleep 300
done