#!/usr/bin/env bash
# check_before_pr.sh - the full local run on the pushed commit, and its proof on GitHub, before a pull request.
# Usage: bash /path/to/repo/scripts/check_before_pr.sh
#        or from any directory: bash ~/.../check_before_pr.sh
#
# It leaves the commit status CI's job `Proof of the local run` looks for, and a new commit has none,
# so what merges is what passed here. It refuses a tree that is not a pushed commit before spending
# the run on it. It never commits or pushes.

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)" || exit 2

REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null)"
if [[ -z "$REPO_ROOT" ]]; then
  echo "Error: script directory is not inside a git repository."
  exit 2
fi

if [[ -n "$(git -C "$REPO_ROOT" status --porcelain)" ]]; then
  echo "FAIL the tree has uncommitted changes: a pull request is a commit, so commit them first."
  exit 1
fi
if [[ -z "$(git -C "$REPO_ROOT" branch -r --contains HEAD)" ]]; then
  echo "FAIL this commit is not pushed: GitHub can only mark a commit it has, so push it first."
  exit 1
fi

bash "$SCRIPT_DIR/run_checks_with_log.sh" || exit $?
exec bash "$SCRIPT_DIR/run_checks_with_log.sh" --sign-off
