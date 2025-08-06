#!/usr/bin/env bash

set -euo pipefail

# Exit with a helpful message on any error
trap 'echo "Error: command failed: $BASH_COMMAND" >&2' ERR

TOTAL_START=$(date +%s)
TIME_LOG=()

# helper to time a synchronous step
time_step() {
  local name="$1"; shift
  local start=$(date +%s)
  "$@"
  local end=$(date +%s)
  TIME_LOG+=("$name: $((end-start))s")
}

# Restore or create the virtual environment
setup_venv() {
  if [ -d .venv ]; then
    echo "Using existing virtual environment"
  elif [ -f .venv.tar.gz ]; then
    echo "Restoring virtualenv from cache"
    tar -xzf .venv.tar.gz
  else
    echo "Creating virtualenv"
    python3.12 -m venv .venv
  fi
  # shellcheck disable=SC1091
  source .venv/bin/activate
}

# Upgrade pip only when an older version is installed
upgrade_pip_if_needed() {
  local current required=24.0
  current=$(python -m pip --version | awk '{print $2}')
  if [ "$(printf '%s\n' "$required" "$current" | sort -V | head -n1)" != "$required" ]; then
    echo "Upgrading pip to $required or newer"
    python -m pip install --upgrade pip >/dev/null
  else
    echo "pip $current is up to date"
  fi
}

# Install Python dependencies
install_python_deps() {
  upgrade_pip_if_needed
  python -m pip install --exists-action=i -r requirements.txt >/dev/null
  # Update cache for next run
  tar -czf .venv.tar.gz .venv
}

# Set up Node.js quietly via mise
setup_node() {
  mise use -q node@20 >/dev/null 2>&1
}

# Run pytest in parallel and capture summary
run_tests() {
  local output
  output=$(pytest -n auto)
  echo "$output"
  TESTS_PASSED=$(echo "$output" | grep -Eo '[0-9]+ passed' | head -n1 | awk '{print $1}')
  TEST_DURATION=$(echo "$output" | tail -n1 | grep -Eo '[0-9.]+s')
}

time_step "Virtualenv" setup_venv

# Start Node setup in parallel with Python dependency installation
NODE_START=$(date +%s)
setup_node &
NODE_PID=$!

time_step "Python deps" install_python_deps

wait $NODE_PID
NODE_END=$(date +%s)
TIME_LOG+=("Node setup: $((NODE_END - NODE_START))s")

time_step "Tests" run_tests

FLASK_VERSION=$(python - <<'PY'
import flask
print(flask.__version__)
PY
)

TOTAL_END=$(date +%s)

echo "Flask version: $FLASK_VERSION"
echo "$TESTS_PASSED tests passed in $TEST_DURATION"

# Print timing summary
for line in "${TIME_LOG[@]}"; do
  echo "$line"
done
echo "Total duration: $((TOTAL_END - TOTAL_START))s"
