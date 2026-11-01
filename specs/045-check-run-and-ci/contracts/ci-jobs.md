# Contract — `.github/workflows/ci.yml` jobs

Triggered on `pull_request` to `main` and `feature/**` (unchanged). Three jobs, run in parallel.

## Job `checks`

`runs-on: ubuntu-latest`

1. `actions/checkout@v4`
2. `actions/setup-node@v4` — Node 22, npm cache on `packages/maxitor/front/client/package-lock.json`
3. `astral-sh/setup-uv@v5`
4. `uv sync --all-extras`
5. `bash scripts/run_checks_with_log.sh --where ci --skip-browser --skip-group packaging`
6. Fail if `git status --porcelain` is non-empty (the graph write must not occur in CI; a stale file is a failure)
7. Reject a pull request from `main`

Produces: static checks, client build and unit tests, ERD scripts, Python tests (minus benchmarks), graph check.

## Job `browser`

`runs-on: ubuntu-latest`

1. `actions/checkout@v4`
2. `actions/setup-node@v4` — Node 22, npm cache
3. `astral-sh/setup-uv@v5`
4. `uv sync --all-extras`
5. `actions/cache@v4` on `~/.cache/ms-playwright`, key `playwright-${{ runner.os }}-${{ hashFiles('packages/maxitor/front/client/package-lock.json') }}`
6. `bash scripts/run_checks_with_log.sh --where ci --only-browser`

Produces: the three-engine layout determinism check, with the client build it needs; browsers downloaded only on a cache miss.

## Job `packaging`

`runs-on: ubuntu-latest`

1. `actions/checkout@v4`
2. `actions/setup-node@v4` — Node 22, npm cache (Maxitor's sdist packs the client)
3. `astral-sh/setup-uv@v5`
4. `uv sync --all-extras`
5. `bash scripts/run_checks_with_log.sh --where ci --only-group packaging`

Produces: `uv build --package … --offline --out-dir packages/<pkg>/dist` for all eight packages, then the install smoke.

## Unchanged

`.github/workflows/publish.yml` — publishes from tags; not touched by this feature.
