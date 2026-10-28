# Contract: The Check Run

What a person or an agent can rely on when running the checks. Everything not named here is internal.

## Starting it

```bash
bash scripts/run_checks_with_log.sh
AOA_CHECK_JOBS=1 bash scripts/run_checks_with_log.sh
```

- Runs from any directory; works from the repository root found through git, as today.
- `AOA_CHECK_JOBS`: how many steps may run at once. Unset → the number of cores. `1` → the steps run one after another, in the table's order.
- `bash scripts/run_checks_with_log.sh --guard <name>` runs one shell guard and exits with its result; the runner uses it, a person does not need it. Names: `lazy-init-getattr`, `client-component-readmes`.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | every step passed |
| 1 | at least one step failed; every step still ran and reported |
| 2 | the run did not start: `AOA_CHECK_JOBS` is not a positive whole number, or the repository root has no `pyproject.toml` |
| 130 | interrupted (Ctrl+C or a termination signal); no step is left running |

## Console

- `> <name>` when a step starts.
- `OK <name> (exit 0, <seconds> s)` or `FAIL <name> (exit <N>, <seconds> s)` when it ends — in the order steps end.
- At the end: the total wall time and the path of the log.

## The log, `archive/logs/check-all.txt`

Written when the run ends, replacing the previous one:

```text
==================================================
ActionMachine project checks
Date: <date>
Time: <time>
Repository: <root>
==================================================

=== <step name> ===
$ <command>

<the step's complete output>

OK <step name> (exit 0, <seconds> s)

… one block per step, in the table's fixed order …

==================================================
All steps finished (see FAIL lines above or in the log if anything failed)
Wall time: <seconds> s
Log: <path>
==================================================
```

- Every step has exactly one block, in the same place whatever ran at the same time; a block holds only its step's output.
- A run interrupted halfway writes the blocks of the steps that ended, then `Run interrupted` in place of `All steps finished`.
- Compared with the log before this change, the only differences are the durations on the `OK`/`FAIL` lines and the `Wall time` line.
