# Research — Check run and CI: decide what runs where

Phase 0 of `/speckit-plan`. Each decision below answers a question the spec left to the plan: the mechanism, not the requirement.

## R1. How packages are built without pypi.org in the local run

**Decision**: the build leaves the local run entirely and runs only in CI as `uv build --package <name> --out-dir packages/<name>/dist`; the local run no longer builds. A local build stays possible with `uv build --package <name> --offline --out-dir packages/<name>/dist` when the cache is warm (the issue measured 0.57 s).

**Rationale**: the local run must need no network at all, and the only step that reached pypi.org was this one. CI has a network, so it builds there, in a clean environment, before a release. `--out-dir` writes the archives where the smoke test already looks (`packages/<pkg>/dist/`).

**Alternatives considered**: `python -m build --no-isolation` — needs `hatchling` importable in the active environment and bypasses isolation in a way that hides a missing build requirement; `uv run --group dev python -m build` (the current command) — isolation still downloads the backend. Rejected.

## R2. Where the packaging smoke finds the archives

**Decision**: the smoke keeps reading `packages/<pkg>/dist/<dist>-*.whl`, which `--out-dir` produces.

**Rationale**: `tests/packaging/test_wheel_install_smoke.py` globs exactly that path (`_latest_wheel`), so the build output must match it.

## R3. How the browser job avoids downloading browsers every run

**Superseded by R8**: there is no browser job. What follows is kept as the record of the first answer.

**Decision**: `actions/cache@v4` on `~/.cache/ms-playwright`, keyed `playwright-${{ runner.os }}-${{ hashFiles('packages/maxitor/front/client/package-lock.json') }}`, restored before `npx playwright install --with-deps chromium firefox webkit`.

**Rationale**: `playwright install` is incremental — it checks the required browser version and downloads only what is missing. Keying on the lockfile means the cache misses only when Playwright's version changes, which is exactly "update only when it needs updating". System libraries are largely present on `ubuntu-latest`; `--with-deps` tops up the rest.

**Alternatives considered**: the `microsoft/playwright` container image (no download, but a container job loses caching semantics and the repo's step table); no cache (hundreds of MB every run). Rejected.

## R4. Speed-sensitive tests: mark and widen

**Decision**: add `pytestmark = pytest.mark.benchmark` to the three unmarked files (`test_graph_compare_speed.py`, `test_pool_bounds.py`, `test_websocket_route.py`); CI runs `pytest -m "not benchmark"`; widen the tightest throughput budgets (×2) and the falsy ratio (2.0 → 3.0); keep every correctness assertion exact (counts, named failures, close codes).

**Rationale**: the marker is already registered in `pyproject.toml` and described as "optional selective runs"; the semantics (counts, codes) are what the tests are for, and only the wall-clock budget is a machine-noise proxy. The rate-limit test in `test_websocket_route.py` cannot be widened without changing behaviour, so it is excluded from the fast path by the marker.

## R5. One table for local and CI

**Decision**: `Step` gains `home` (`"local" | "ci" | "both"`), `fast: bool`, `browser: bool`; the runner gains `--where local|ci`, `--fast`, `--only-browser`, `--only-group NAME`, `--skip-group NAME`. `run_checks_with_log.sh` already forwards `"$@"`.

**Rationale**: local and CI run the *same* commands from one table, so they cannot drift; the spec's "one stated home" becomes a property of the table, not of two files.

**Alternatives considered**: duplicate commands in `ci.yml` (two tables, drift); a second CI script (same problem). Rejected.

## R6. Graph files always checked

**Decision**: split the graph step into `Graph files (graph-builder write)` (`only_if_all_passed=True`, local only) and, after it, `Graph files (graph-builder check)` (no `only_if_all_passed`, runs in every where). The check step must run even when other steps failed, and it must come after the write: run beside the others, a stale file failed the check, and that failure then skipped the write that would have fixed it, so the file stayed stale on a green run.

**Rationale**: acceptance criterion 5 — no failure in an unrelated step may skip both. `graph-builder check` already exists as the CLI verb and as the CI composite action.

## R7. CI job layout

**Decision**: three jobs, in parallel — `checks` (static checks, client build/vitest/ERD, Python tests, graph check), `packaging` (build + install smoke), `local-run` (the proof of the full local run). Each invokes the same runner: `--where ci --skip-group packaging`, `--where ci --only-group packaging`, `--await-sign-off <commit>`.

**Rationale**: packaging needs the `dist/` archives; running it apart keeps the `checks` feedback early. The proof job needs nothing installed, because the runner is the standard library alone.

## R8. Where the browsers run

**Decision**: in the full local run only. CI does not run them; it reads their proof (R9).

**Rationale**: the browser job failed with no console error and no failing request, and the cause was reproduced in a Linux container with the CI job's limits (4 cores, Ubuntu 24.04, arm64 rather than GitHub's x86): a machine with no graphics card gives Firefox no WebGL, so the map says "This browser cannot draw the map: WebGL is off" and no layout hash ever appears. Chromium and WebKit draw in software. `webgl.force-enabled` with Mesa did not help (`Exhausted GL driver options`). Firefox with a window on Xvfb did get WebGL through `llvmpipe`, and under it all 61 page-modes agreed in all three engines, but the same run gave 30 differences in 240 on following and on frames, and took 329 s. Those parts measure cameras and frames, so chasing them would tune the check to a software renderer no user has, and the real Safari run can only happen on the maintainer's machine anyway.

**Alternatives considered**: Firefox under Xvfb in CI (above); dropping the map from Firefox in CI (a hole in the gate); a self-hosted runner on the maintainer's Mac (the repository is public, so a pull request would run foreign code on that machine). Rejected.

## R9. How CI controls a run it does not perform

**Decision**: the trace is a commit status, `Local check run`. A green full run on one commit leaves a receipt in `archive/logs/check-run-receipt.json`; `--sign-off` reports it through `gh api`; the job `Proof of the local run` reads it with `--await-sign-off`, waiting up to 15 minutes, and fails when none comes. The merge rule of `main` requires that job.

**Rationale**: a status is tied to the exact commit, so a new commit has none; it needs no file in the tree, so it adds no commit and no merge conflict; the local run stays free of the network, because only `--sign-off` talks to GitHub. The wait exists because a commit pushed to an open pull request starts CI at once, and failing then would turn every such push red and leave it red after its run. A commit that had its run before the pull request answers on the first read.

**Alternatives considered**: a git hook (not controlled: `--no-verify`, another machine); a file committed with the proof (a commit that proves itself needs a second commit, and every pull request conflicts on it); requiring the bare status with no job (works, but CI shows it only as "Expected", never as a failure). Rejected.

**Limit**: anyone with write access can post a status, so this is an attestation, not a proof. With one maintainer it is enough, and the ruleset has no bypass actors, so the job cannot be skipped.
