# Quickstart — validate the check run and CI decision

Runnable checks that prove the feature works end to end. Run from the repository root.

## Prerequisites

- `uv` installed; the project environment prepared once with `uv sync --all-extras`.
- Node 22 and the client dependencies installed once: `cd packages/maxitor/front/client && npm ci`.
- For the browser check: `npx playwright install chromium firefox webkit` run once.

## 1. Local full run, network off

**Command**: turn the network off, then
```bash
bash scripts/run_checks_with_log.sh
```
**Expected**: every selected step ends `OK` (or `SKIPPED` only for the graph write after a failure), the run exits `0`, and no step waits on a download from pypi.org. The log is `archive/logs/check-all.txt`.

## 2. Local fast mode

**Command**:
```bash
bash scripts/run_checks_with_log.sh --fast
```
**Expected**: the guards, the static checks and the Python suites run; the client build, the client unit tests, the ERD scripts, the three-engine job, the packaging steps and the graph write are absent from the log. The run exits `0` on a healthy tree.

## 3. CI checks job selection

**Command**:
```bash
bash scripts/run_checks_with_log.sh --where ci --skip-browser --skip-group packaging
```
**Expected**: the browser step and the packaging steps are absent; everything else (static, client build and unit tests, ERD, Python tests, graph check) is present.

## 4. A broken package build is caught

**Command**: break one package's build definition (for example, a bad path in its `pyproject.toml`), then
```bash
bash scripts/run_checks_with_log.sh --where ci --only-group packaging
```
**Expected**: the `Build wheel/sdist (<package>)` step ends `FAIL` and the run exits `1`; the install smoke does not pass. Restore the file afterwards.

## 5. The graph files are always checked

**Command**: force an unrelated step to fail (for example, `false` as a first step in a scratch run), then
```bash
bash scripts/run_checks_with_log.sh
```
**Expected**: `Graph files (graph-builder check)` still runs and reports `OK` or `FAIL`; it is never absent. `Graph files (graph-builder write)` is `SKIPPED` when another step failed.

## 6. Benchmarks are outside the fast CI path

**Command**:
```bash
bash scripts/run_checks_with_log.sh --where ci --skip-browser --skip-group packaging
```
**Expected**: no benchmark or timing test in the log; the same suites run with `pytest -m benchmark` on demand and in the full local run.

## 7. Browsers are not downloaded twice

**Expected**: on the second run of the CI `browser` job with an unchanged `package-lock.json`, the `actions/cache` step reports a cache hit and `npx playwright install` downloads nothing.

## 8. Acceptance criteria

| Criterion | Proven by |
|---|---|
| Local run ends at zero with the network off | (1) |
| A broken package build is caught | (4) |
| Every step has one home | (2), (3), [data-model.md](./data-model.md) |
| A pull request gets an independent CI result | (3), (4) |
| Graph files always written or checked | (5) |
| Fast mode selects only the cheap steps | (2), (6) |
