# Quickstart: Run every check once

1. `git ls-files scripts/check_before_commit.sh` prints nothing.
2. `bash scripts/run_checks_with_log.sh --fast` is refused as an unknown argument.
3. `uv run --extra dev pytest tests/scripts/test_check_run.py` passes.
4. Open a pull request into `main` without running the browsers: CI runs, and merging is blocked with `Local check run` expected.
5. Run `bash scripts/check_before_pr.sh` on that commit: the status appears, no job is rerun, and merging is allowed once CI is green.
6. Push a new commit: `Local check run` is expected again.
7. `bash scripts/run_checks_with_log.sh` still runs everything.
