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

**Decision**: `actions/cache@v4` on `~/.cache/ms-playwright`, keyed `playwright-${{ runner.os }}-${{ hashFiles('packages/maxitor/front/client/package-lock.json') }}`, restored before `npx playwright install --with-deps chromium firefox webkit`.

**Rationale**: `playwright install` is incremental — it checks the required browser version and downloads only what is missing. Keying on the lockfile means the cache misses only when Playwright's version changes, which is exactly "update only when it needs updating". System libraries are largely present on `ubuntu-latest`; `--with-deps` tops up the rest.

**Alternatives considered**: the `microsoft/playwright` container image (no download, but a container job loses caching semantics and the repo's step table); no cache (hundreds of MB every run). Rejected.

## R4. Speed-sensitive tests: mark and widen

**Decision**: add `pytestmark = pytest.mark.benchmark` to the three unmarked files (`test_graph_compare_speed.py`, `test_pool_bounds.py`, `test_websocket_route.py`); CI runs `pytest -m "not benchmark"`; widen the tightest throughput budgets (×2) and the falsy ratio (2.0 → 3.0); keep every correctness assertion exact (counts, named failures, close codes).

**Rationale**: the marker is already registered in `pyproject.toml` and described as "optional selective runs"; the semantics (counts, codes) are what the tests are for, and only the wall-clock budget is a machine-noise proxy. The rate-limit test in `test_websocket_route.py` cannot be widened without changing behaviour, so it is excluded from the fast path by the marker.

## R5. One table for local and CI

**Decision**: `Step` gains `home` (`"local" | "ci" | "both"`), `fast: bool`, `browser: bool`; the runner gains `--where local|ci`, `--fast`, `--only-browser`, `--skip-browser`, `--only-group NAME`, `--skip-group NAME`. `run_checks_with_log.sh` already forwards `"$@"`.

**Rationale**: local and CI run the *same* commands from one table, so they cannot drift; the spec's "one stated home" becomes a property of the table, not of two files.

**Alternatives considered**: duplicate commands in `ci.yml` (two tables, drift); a second CI script (same problem). Rejected.

## R6. Graph files always checked

**Decision**: split the graph step into `Graph files (graph-builder check)` (no `only_if_all_passed`, runs in every where) and `Graph files (graph-builder write)` (`only_if_all_passed=True`, local only). The check step must run even when other steps failed.

**Rationale**: acceptance criterion 5 — no failure in an unrelated step may skip both. `graph-builder check` already exists as the CLI verb and as the CI composite action.

## R7. CI job layout

**Decision**: three jobs, in parallel — `checks` (static checks, client build/vitest/ERD, Python tests, graph check), `browser` (three engines, cached browsers), `packaging` (build + install smoke). Each invokes the same runner with a selector: `--where ci --skip-browser --skip-group packaging`, `--where ci --only-browser`, `--where ci --only-group packaging`.

**Rationale**: the browser job is heavy and its cache is specific; packaging needs the `dist/` archives; running them as separate jobs keeps the fast `checks` feedback early and lets the slow jobs run in parallel.
