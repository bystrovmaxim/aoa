# Quickstart — validate the check run and CI decision

Runnable checks that prove the feature works end to end. Run from the repository root.

## Prerequisites

- `uv` installed; the project environment prepared once with `uv sync --all-extras`.
- Node 22 and the client dependencies installed once: `cd packages/maxitor/front/client && npm ci`.
- For the browser check: `npx playwright install chromium firefox webkit` run once, and Graphviz's `sfdp` on the path.

## 1. Local full run, network off

**Command**: turn the network off, then
```bash
bash scripts/run_checks_with_log.sh
```
**Expected**: every selected step ends `OK`, the run exits `0`, and no step waits on a download from pypi.org. The log is `archive/logs/check-all.txt`.

## 2. Local fast mode

**Command**:
```bash
bash scripts/check_before_commit.sh
```
**Expected**: the guards, the static checks and the Python suites without the speed tests run; the client build, the client unit tests, the ERD scripts, the three-engine check, the packaging steps and the graph rows are absent from the log. The run exits `0` on a healthy tree.

## 3. CI checks job selection

**Command**:
```bash
bash scripts/run_checks_with_log.sh --where ci --skip-group packaging
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

The other way round: make a graph file stale on an otherwise green run, then `bash scripts/run_checks_with_log.sh --only-group graphs`. **Expected**: the write and the check both end `OK`, and `git status` no longer shows the file.

## 6. Benchmarks are outside the fast CI path

**Command**:
```bash
bash scripts/run_checks_with_log.sh --where ci --skip-group packaging
```
**Expected**: no benchmark or timing test in the log; the same suites run with `pytest -m benchmark` on demand and in the full local run.

## 7. The full run proves one commit, and CI reads the proof

**Command**: on a clean, pushed commit,
```bash
bash scripts/check_before_pr.sh
```
**Expected**: the full run ends with `Receipt: 35 steps green on <commit>` and `OK Local check run on <commit>`. On a pull request from that commit the job `Proof of the local run` passes on its first read. On a commit with no full run it waits 15 minutes and fails, naming the script to run. With uncommitted changes, or on an unpushed commit, the script refuses before the run.

## 8. Acceptance criteria

| Criterion | Proven by |
|---|---|
| Local run ends at zero with the network off | (1) |
| A broken package build is caught | (4) |
| Every step has one home | (2), (3), [data-model.md](./data-model.md) |
| A pull request gets an independent CI result | (3), (4) |
| Graph files always written or checked | (5) |
| Fast mode selects only the cheap steps | (2), (6) |
| A commit nobody ran fails in CI | (7) |
