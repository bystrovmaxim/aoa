# Contract — `.github/workflows/ci.yml` jobs

Triggered on `pull_request` to `main` and `feature/**` (unchanged). Three jobs, run in parallel.

## Job `checks`

`runs-on: ubuntu-latest`

1. `actions/checkout@v4`
2. `actions/setup-node@v4` — Node 22, npm cache on `packages/maxitor/front/client/package-lock.json`
3. `astral-sh/setup-uv@v5`
4. `uv sync --all-extras`
5. `bash scripts/run_checks_with_log.sh --where ci --skip-group packaging`
6. `uses: ./packages/maxitor/tools/graph_builder`: maxitor's own action, the one other projects use
7. Fail if `git status --porcelain` is non-empty (the graph write must not occur in CI; a stale file is a failure)
8. Reject a pull request from `main`

Produces: static checks, client build and unit tests, ERD scripts, Python tests (minus benchmarks), graph check.

## Job `local-run`, named `Proof of the local run`

`runs-on: ubuntu-latest`, `timeout-minutes: 20`, permissions `contents: read` and `statuses: read`

1. `actions/checkout@v4`
2. `python3 scripts/check_run.py --await-sign-off "$COMMIT"`, with `GH_TOKEN` and `COMMIT` = `github.event.pull_request.head.sha`

Passes when the commit carries the status `Local check run` as `success`; fails after 15 minutes without it. The head of the pull request, not `github.sha`: that is GitHub's merge commit, which nobody ran. Nothing is installed: the runner is the standard library alone.

## Job `packaging`

`runs-on: ubuntu-latest`

1. `actions/checkout@v4`
2. `astral-sh/setup-uv@v5`
3. `uv sync --all-extras`
4. `bash scripts/run_checks_with_log.sh --where ci --only-group packaging`

Produces: `uv build --package … --out-dir packages/<pkg>/dist` for all eight packages, the command `publish.yml` runs, then the install smoke. Maxitor's sdist packs the client's source folder, so no client build is needed here; its wheel carries no built client, as it never did in this check.

## The merge rule

The ruleset `main` requires the jobs `Checks`, `Packaging` and `Proof of the local run`, with the branch up to date. It is a repository setting, set by the maintainer; it has no bypass actors.

## Unchanged

`.github/workflows/publish.yml` — publishes from tags; not touched by this feature.
