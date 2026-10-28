# Quickstart: Checking the Check Run

Validation scenarios for [spec.md](spec.md). Run from the repository root on a clean tree, on the machine of the baseline.

## 1. Times and the baseline (User Story 1, phase 1)

```bash
bash scripts/run_checks_with_log.sh
bash scripts/run_checks_with_log.sh
grep -E "^(OK|FAIL) |^Wall time" archive/logs/check-all.txt
```

**Expected**: 37 `OK` lines, each with a duration, and a `Wall time` line. Both runs' times are posted on #279 as the baseline.

## 2. The log reads as before (User Story 2, phases 1–2)

Keep a log from `main` before the change (`check-all.before.txt`, outside the repository), then compare after removing durations and dates:

```bash
strip() { sed -E 's/ \(exit ([0-9]+), [0-9.]+ s\)/ (exit \1)/; /^(Date|Time|Wall time):/d' "$1"; }
diff <(strip "$SCRATCH/check-all.before.txt") <(strip archive/logs/check-all.txt)
```

**Expected**: no difference apart from output that varies by itself between runs (test timings, build ids).

## 3. The limit (User Story 3, phase 3)

```bash
AOA_CHECK_JOBS=1 bash scripts/run_checks_with_log.sh; cp archive/logs/check-all.txt "$SCRATCH/one.txt"
bash scripts/run_checks_with_log.sh;                  cp archive/logs/check-all.txt "$SCRATCH/many.txt"
diff <(strip "$SCRATCH/one.txt") <(strip "$SCRATCH/many.txt")
AOA_CHECK_JOBS=0 bash scripts/run_checks_with_log.sh; echo "exit $?"
```

**Expected**: the two logs read the same apart from times; the last command stops before any step with a message naming `AOA_CHECK_JOBS`, `exit 2`.

## 4. One break in each group (User Story 3, SC-004)

One at a time, then restored: a failing client unit test; a mypy error in a package; a broken `pyproject.toml` in one package (its build fails); a failing test in one package.

**Expected**: each time, exactly the broken step (and the steps that read its result, such as the smoke test after a failed build) is `FAIL`; every other step reports `OK`; exit code 1.

## 5. Interrupt (FR-010)

Start the run, press Ctrl+C while the tests run, then:

```bash
echo "exit $?"; pgrep -fl "pytest|mypy|pylint|vite|playwright|uvicorn" || echo "nothing left"
tail -3 archive/logs/check-all.txt
```

**Expected**: `exit 130`, `nothing left`, the log ends with `Run interrupted`.

## 6. Tests side by side (User Story 4, phase 4)

Ten parallel runs in a row on a clean tree.

**Expected**: ten green runs.

## 7. Faster (SC-002, phase 5)

Two parallel runs beside the baseline of §1.

**Expected**: both green and both faster than the baseline; the numbers go on #279 and into the pull request.
