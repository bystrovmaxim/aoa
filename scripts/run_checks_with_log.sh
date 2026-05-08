#!/usr/bin/env bash
# run_checks_with_log.sh — run project checks and append output to archive/logs/ (repo root).
# Usage: bash /path/to/repo/scripts/run_checks_with_log.sh
#        or from any directory: bash ~/.../run_checks_with_log.sh

set -u

# Directory containing this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)" || exit 1

# Repository root (where pyproject.toml lives)
REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null)"
if [[ -z "$REPO_ROOT" ]]; then
  echo "Error: script directory is not inside a git repository."
  exit 1
fi
cd "$REPO_ROOT" || exit 1

# --- everything below is relative to repo root ---

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

mkdir -p archive/logs
LOG_FILE="$REPO_ROOT/archive/logs/check-all.txt"
FAILED=0

echo -e "${YELLOW}Log file: ${LOG_FILE}${NC}"
echo ""

{
  echo "=================================================="
  echo "ActionMachine project checks"
  echo "Date: $(date)"
  echo "Time: $(date +%H:%M:%S)"
  echo "Repository: $REPO_ROOT"
  echo "=================================================="
  echo ""
} > "$LOG_FILE"

run_and_log() {
  local cmd="$1"
  local name="$2"

  echo -e "${YELLOW}▶ ${name}${NC}"

  {
    echo "=== $name ==="
    echo "\$ $cmd"
    echo ""
  } >> "$LOG_FILE"

  # shellcheck disable=SC2086
  eval "$cmd" >>"$LOG_FILE" 2>&1
  local exit_code=$?
  echo "" >>"$LOG_FILE"

  if [[ $exit_code -eq 0 ]]; then
    echo -e "${GREEN}OK ${name} (exit 0)${NC}"
    echo "OK ${name} (exit 0)" >>"$LOG_FILE"
  else
    echo -e "${RED}FAIL ${name} (exit $exit_code)${NC}"
    echo "FAIL ${name} (exit $exit_code)" >>"$LOG_FILE"
    FAILED=1
  fi
  echo "" >>"$LOG_FILE"
}

check_no_lazy_init_getattr() {
  local matches

  matches="$(
    while IFS= read -r -d '' file; do
      grep -nH -E '^[[:space:]]*def[[:space:]]+__getattr__[[:space:]]*\(' "$file" || true
    done < <(git ls-files -z 'src/**/__init__.py' 'tests/**/__init__.py')
  )"
  if [[ -n "$matches" ]]; then
    echo "Forbidden package-level lazy export found: __getattr__ in __init__.py"
    echo "$matches"
    return 1
  fi
}

if [[ ! -f "$REPO_ROOT/pyproject.toml" ]]; then
  echo -e "${RED}FAIL pyproject.toml not found in $REPO_ROOT${NC}"
  exit 1
fi

echo -e "${YELLOW}Full check run (cwd=$REPO_ROOT)...${NC}"
echo ""

run_and_log "check_no_lazy_init_getattr" "Ban __getattr__ in package __init__.py"
run_and_log "uv run ruff check --fix ." "Ruff auto-fix"
run_and_log "uv run task lint" "Ruff lint"
run_and_log "uv run task typecheck" "Mypy typecheck"
run_and_log "uv run task pylint" "Pylint"
run_and_log "uv run python scripts/check_package_boundaries.py" "Package import boundaries"
run_and_log "uv run task dead" "Vulture dead code"
run_and_log "uv run task test-layer-imports" "Test import boundaries (tests/ ↔ action_machine)"
run_and_log "uv run task samples-public-api" "Maxitor samples: action_machine public API"
run_and_log "uv run task test" "Pytest"
run_and_log "uv run task cc" "Radon cyclomatic complexity"
run_and_log "uv run task mi" "Radon maintainability index"

{
  echo "=================================================="
  echo "All steps finished (see FAIL lines above or in the log if anything failed)"
  echo "Log: $LOG_FILE"
  echo "=================================================="
} >>"$LOG_FILE"

echo ""
echo -e "${GREEN}Log: ${LOG_FILE}${NC}"
exit "$FAILED"
