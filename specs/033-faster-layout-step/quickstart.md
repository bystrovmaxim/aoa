# Quickstart: Checking the Layout Step

Validation scenarios for [spec.md](spec.md), on the maintainer's M3 Max. The client must be built (`npm run build` in `packages/aoa-maxitor/client`).

## 1. The step alone, with part times

```bash
cd packages/aoa-maxitor/client && node scripts/check-layout-determinism.ts | tail -6
```

**Expected**: three `part …` lines and the summary line; exit 0.

## 2. The same lines as before

Keep the step's output from `main` (`$SCRATCH/layout.before.txt`), then compare without times and self-varying figures:

```bash
strip() { sed -E 's/[0-9]+(\.[0-9]+)? (s|ms|px)/N \2/g; /^part /d; s/ in N s$//' "$1"; }
diff <(strip "$SCRATCH/layout.before.txt") <(strip "$SCRATCH/layout.after.txt")
```

**Expected**: no difference.

## 3. Inside the check run

```bash
bash scripts/run_checks_with_log.sh
grep -E "^(OK|FAIL) Maxitor client: the same layout|^Wall time" archive/logs/check-all.txt
```

**Expected**: the step `OK`, faster than the baseline; the run's wall time below 85 s.

## 4. The three breaks (one at a time, restored)

Firefox's hash for one page-mode gets a suffix; WebKit's pointer offsets get 3 px; one pair's distance gets 3 px.

**Expected**: each time exit 1 and exactly the broken line is `DIFF`; every other line as before.

## 5. Ten in a row

Ten check runs in a row on a clean tree.

**Expected**: ten green runs; the step's time recorded for each.
