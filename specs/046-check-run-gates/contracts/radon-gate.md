# Contract: `scripts/check_radon.py`

## Command line

```bash
uv run --extra dev python scripts/check_radon.py cc
uv run --extra dev python scripts/check_radon.py mi
```

The tasks `task cc` and `task mi` run these. The check-run steps keep their commands.

## Answers

| Case | Exit | Prints |
|---|---|---|
| Nothing over the limit | 0 | One line: how many functions or modules were read, and that none is over |
| Over the limit | 1 | One line per offender: `file:line name — grade D (complexity 24)` or `file — grade B (index 11.45)`, then the count |
| Over the limit but excepted | 0 | As passing, plus one line per exception with its reason |
| Exception's target is gone or no longer over the limit | 1 | The exception, and that it is stale |
| Exception without a reason | 1 | The exception, and that it has no reason |
| Radon reports `error` for a file | 1 | The file and Radon's error |
| Radon exits non-zero, prints nothing, or prints something that is not JSON | 1 | That the report could not be read, and Radon's stderr |
| Unknown argument | 2 | Usage |

All offenders are listed; the script never stops at the first.

## Guarantees

- It reads `packages/`, as today's steps do, tests included.
- It writes nothing.
- It adds no dependency; `radon` is already in the `dev` extra.
