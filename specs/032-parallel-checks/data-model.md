# Data Model: A Check Run That Measures Itself and Runs Independent Steps Together

## Step (one row of the runner's table)

| Field | Meaning |
|---|---|
| `name` | Today's step name, as it appears in the console and the log. Unique. |
| `command` | Today's command line, shown after `$` in the log. |
| `group` | `first`, `client`, `static`, `packaging` or `tests` (research R3). |
| `after` | The names of the steps it waits for. |
| `not_during` | The names of steps it must not overlap (only the Maxitor package build: the client build). |

The table lists the 37 steps in today's order; that order is the order of the log.

## Step result

| Field | Meaning |
|---|---|
| `exit_code` | The step's exit code; a step that could not start counts as failed with its own code. |
| `seconds` | Wall time from start to end, to a tenth of a second. |
| `output` | Everything the step wrote to standard output and error, in the order written. |

`OK` when `exit_code` is 0, `FAIL` otherwise.

## Run

| Field | Meaning |
|---|---|
| `jobs` | The limit (`AOA_CHECK_JOBS`, default the number of cores). |
| `results` | One result per step that ended. |
| `wall_seconds` | From the first step's start to the last step's end. |
| `interrupted` | Whether the run was stopped by a signal. |

Exit code: 130 if interrupted, else 1 if any result is `FAIL`, else 0.
