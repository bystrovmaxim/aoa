#!/usr/bin/env bash
# run_checks_with_log.sh - run the project checks and write archive/logs/check-all.txt (repo root).
# Usage: bash /path/to/repo/scripts/run_checks_with_log.sh
#        or from any directory: bash ~/.../run_checks_with_log.sh
#
# The steps, their order and the log are kept by scripts/check_run.py; this script finds the
# repository, holds the two shell guards and hands over. `--guard <name>` runs one guard and exits
# with its result; the runner uses it.

set -u

# Directory containing this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)" || exit 2

# Repository root (where pyproject.toml lives)
REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null)"
if [[ -z "$REPO_ROOT" ]]; then
  echo "Error: script directory is not inside a git repository."
  exit 2
fi
cd "$REPO_ROOT" || exit 2

# --- everything below is relative to repo root ---

RED='\033[0;31m'
NC='\033[0m'

check_no_lazy_init_getattr() {
  local matches

  matches="$(
    while IFS= read -r -d '' file; do
      grep -nH -E '^[[:space:]]*def[[:space:]]+__getattr__[[:space:]]*\(' "$file" || true
    done < <(git ls-files -z 'packages/**/__init__.py' 'tests/**/__init__.py')
  )"
  if [[ -n "$matches" ]]; then
    echo "Forbidden package-level lazy export found: __getattr__ in __init__.py"
    echo "$matches"
    return 1
  fi
}

# packages/aoa-maxitor/client — each components/<zone>/<Component>/ with index.ts must have README.md (plan 018 section 9.1).
check_maxitor_client_component_readmes() {
  local client_src="$REPO_ROOT/packages/aoa-maxitor/client/src"
  local dir
  local fail=0

  if [[ ! -d "$client_src" ]]; then
    echo "Missing directory: $client_src"
    return 1
  fi

  while IFS= read -r -d '' dir; do
    dir="${dir%/}/"
    if [[ -f "${dir}index.ts" && ! -f "${dir}README.md" ]]; then
      echo "Missing README.md in ${dir}"
      fail=1
    fi
  done < <(find "$client_src" -mindepth 3 -maxdepth 3 -type d -path "$client_src/components/*/*" -print0)

  return "$fail"
}

if [[ "${1:-}" == "--guard" ]]; then
  case "${2:-}" in
    lazy-init-getattr) check_no_lazy_init_getattr; exit $? ;;
    client-component-readmes) check_maxitor_client_component_readmes; exit $? ;;
    *) echo "Unknown guard: ${2:-}"; exit 2 ;;
  esac
fi

if [[ ! -f "$REPO_ROOT/pyproject.toml" ]]; then
  echo -e "${RED}FAIL pyproject.toml not found in $REPO_ROOT${NC}"
  exit 2
fi

exec uv run --extra dev python scripts/check_run.py "$@"
