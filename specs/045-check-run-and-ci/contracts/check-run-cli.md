# Contract — `scripts/check_run.py` command line

The runner is invoked by `scripts/run_checks_with_log.sh`, which forwards `"$@"`. This is the interface a caller may rely on.

## Flags

| Flag | Values | Default | Effect |
|---|---|---|---|
| `--where` | `local` \| `ci` \| `both` | `local` | Keeps rows whose `home` is in the set. `--where ci` keeps `ci` and `both`. |
| `--fast` | flag | off | Local only; keeps rows with `fast == True`, with the Python suites as in CI (no speed tests). |
| `--only-browser` | flag | off | Keeps the `browser` rows and the client build they need. Ignores `home`. |
| `--only-group` | group name | none | Keeps rows of that `group`. Ignores `home`. |
| `--skip-group` | group name | none | Drops rows of that `group`. |
| `--sign-off` | flag | off | Runs nothing: reports the receipt to GitHub as the status `Local check run`. |
| `--await-sign-off` | commit | none | Runs nothing: for CI, waits up to 15 minutes for that status on the commit. |

`AOA_CHECK_JOBS` keeps its meaning: the parallelism limit. Selectors and the job limit are independent.

## Behaviour

- The run exits `0` when every selected step passed, `1` when any failed, `130` when interrupted.
- The log is written to `archive/logs/check-all.txt` from the selected steps, in table order.
- `only_if_all_passed` still applies among the *selected* steps: `Graph files (graph-builder write)` runs only when every selected step passed, and only under `--where local`. The steps that wait for it do not count.
- `Graph files (graph-builder check)` is selected under every `--where`, has no `only_if_all_passed` and waits for the write, so it runs even when another step failed, and a stale file is rewritten on a green run instead of failing it.
- The whole local run drops the receipt when it starts and, on green, leaves one when the tree was one commit from start to end; otherwise it says why not. The exit code does not depend on the receipt.
- `--sign-off` exits `0` when GitHub took the status, `1` when the tree has uncommitted changes, when no receipt names this commit, or when GitHub refused. It calls GitHub only after the first two checks.
- `--await-sign-off` exits `0` once the status is `success`, `1` when the wait ends without it.

## The two scripts

| Script | When | What |
|---|---|---|
| `scripts/check_before_commit.sh` | during the work, before every commit | `--fast`; further flags pass on |
| `scripts/check_before_pr.sh` | on the pushed commit, before a pull request | refuses a dirty or unpushed tree, then the whole local run, then `--sign-off`; never commits or pushes |

## Examples

```bash
bash scripts/run_checks_with_log.sh                       # local full run
bash scripts/run_checks_with_log.sh --fast                # local fast mode
bash scripts/run_checks_with_log.sh --only-browser                    # the browsers alone, after a failure there
bash scripts/run_checks_with_log.sh --where ci --skip-group packaging  # CI checks job
bash scripts/run_checks_with_log.sh --where ci --only-group packaging  # CI packaging job
```
