# Contract — `scripts/check_run.py` command line

The runner is invoked by `scripts/run_checks_with_log.sh`, which forwards `"$@"`. This is the interface a caller may rely on.

## Flags

| Flag | Values | Default | Effect |
|---|---|---|---|
| `--where` | `local` \| `ci` \| `both` | `local` | Keeps rows whose `home` is in the set. `--where ci` keeps `ci` and `both`. |
| `--fast` | flag | off | Local only; keeps rows with `fast == True`. Composes with `--where local`. |
| `--only-browser` | flag | off | Keeps the `browser` rows and the client build they need. Ignores `home`. |
| `--skip-browser` | flag | off | Drops the `browser` rows. |
| `--only-group` | group name | none | Keeps rows of that `group`. Ignores `home`. |
| `--skip-group` | group name | none | Drops rows of that `group`. |

`AOA_CHECK_JOBS` keeps its meaning: the parallelism limit. Selectors and the job limit are independent.

## Behaviour

- The run exits `0` when every selected step passed, `1` when any failed, `130` when interrupted.
- The log is written to `archive/logs/check-all.txt` from the selected steps, in table order.
- `only_if_all_passed` still applies among the *selected* steps: `Graph files (graph-builder write)` runs only when every selected step passed, and only under `--where local`.
- `Graph files (graph-builder check)` is selected under every `--where` and has no `only_if_all_passed`, so it runs even when another step failed.

## Examples

```bash
bash scripts/run_checks_with_log.sh                       # local full run
bash scripts/run_checks_with_log.sh --fast                # local fast mode
bash scripts/run_checks_with_log.sh --where ci --skip-browser --skip-group packaging  # CI checks job
bash scripts/run_checks_with_log.sh --where ci --only-browser                         # CI browser job
bash scripts/run_checks_with_log.sh --where ci --only-group packaging                 # CI packaging job
```
