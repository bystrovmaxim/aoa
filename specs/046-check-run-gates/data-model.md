# Data Model: Check run — Radon as a real gate, one Ruff step, package builds confirmed

There is no stored data. Three small shapes live in `scripts/`.

## Finding

One thing over the limit, or one thing wrong with the report or the exceptions.

| Field | Meaning |
|---|---|
| `file` | Path as Radon reports it |
| `name` | Function or method name; empty for a module. A method reads `Class.method` |
| `grade` | Radon's letter, or empty for a broken report or a stale exception |
| `detail` | Complexity or index, or what is wrong |

The step fails if there is at least one finding, and prints all of them.

## Exception

| Field | Meaning | Rule |
|---|---|---|
| file | Path as Radon reports it | Must exist in the report |
| name | Function or method name (function table only) | Must be over the limit today |
| reason | Why it stays | Must not be empty |

An exception that breaks a rule is itself a finding (FR-006).

## Limits

| Step | Fails on | Radon's scale |
|---|---|---|
| `cc` | Rank `D`, `E` or `F` (complexity 21 and above) | A to F |
| `mi` | Rank `B` or `C` (index 19 and below) | A to C |

## `Step` (existing, `scripts/check_run.py`)

One new field:

| Field | Default | Meaning |
|---|---|---|
| `fast_keeps_command` | `False` | Under `--fast` the row keeps `command` instead of taking `ci_command` |

| Row | `command` | `ci_command` | `home` | `fast_keeps_command` |
|---|---|---|---|---|
| Ruff auto-fix | `ruff check --fix packages/ tests/ scripts/` | `ruff check packages/ tests/ scripts/` | `both` | `True` |
| Ruff lint | removed | | | |

Each run's command for the Ruff step:

| Run | Command | Fixes files |
|---|---|---|
| Full local | `command` | Yes |
| `check_before_commit.sh` (`--fast`) | `command` | Yes |
| CI | `ci_command` | No |
