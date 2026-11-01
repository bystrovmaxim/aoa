#!/usr/bin/env bash
# check_before_commit.sh - the cheap deterministic checks, for use during the work and before every commit.
# Usage: bash /path/to/repo/scripts/check_before_commit.sh
#        or from any directory: bash ~/.../check_before_commit.sh
#
# The guards, the static checks and the Python tests without the speed tests. Anything after it in
# the command line goes on to the run.

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)" || exit 2

exec bash "$SCRIPT_DIR/run_checks_with_log.sh" --fast "$@"
