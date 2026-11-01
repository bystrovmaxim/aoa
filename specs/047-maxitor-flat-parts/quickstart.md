# Quickstart: validating the work

Run everything from the worktree root, `/Users/bystrovmaxim/PythonDev/aoa-issue-305`.

## Before phase 1: the baseline

```bash
uv sync --all-extras
```

```bash
cp packages/maxitor/front/graph.json /tmp/305-front-graph.json
```

```bash
cp packages/maxitor/tools/repo_graph_port/graph.json /tmp/305-port-graph.json
```

## After each of phases 1–3

```bash
uv sync --all-extras
```

```bash
bash scripts/check_before_commit.sh
```

Expected: green, apart from the two accepted remarks.

## After phases 1 and 2: graphs unchanged

```bash
uv run --extra dev graph-builder check
```

```bash
cmp /tmp/305-front-graph.json packages/maxitor/front/graph.json
```

```bash
cmp /tmp/305-port-graph.json packages/maxitor/tools/repo_graph_port/graph.json
```

Expected: no output from either `cmp`.

## After phase 3: the graph differs only by the name

```bash
sed 's/maxitor\.web/maxitor.front/g' packages/maxitor/web/graph.json | cmp - /tmp/305-front-graph.json
```

```bash
cmp /tmp/305-port-graph.json packages/maxitor/tools/repo_graph_port/graph.json
```

Expected: no output.

## The built package carries the client

Build as `publish.yml` does, then list the client's files inside the wheel:

```bash
(cd packages/maxitor/web/client && npm ci && npx vite build --base=/ --outDir ../maxitor/web/static --emptyOutDir)
```

```bash
uv build --package maxitor --out-dir /tmp/305-dist
```

```bash
unzip -l /tmp/305-dist/maxitor-*.whl | grep -c 'maxitor/web/static/'
```

Expected: a count above 0. CI's packaging job covers the clean install with each extra.

## The container images

```bash
docker build -f packages/maxitor/web/Dockerfile -t maxitor-web-305 .
```

Expected: the build passes; the image serves the client at port 8101.

## Old names are gone

```bash
git grep -nE 'front/src/|graph_builder/src/|repo_graph_port/src/|graph_compare/src/|graph_map/src/|src/maxitor|maxitor\.front|maxitor\[front|packages/maxitor/front' -- . ':!specs' ':!docs/CHANGELOG.md' ':!packages/maxitor/CHANGELOG.md'
```

Expected: no output. New changelog text must not name the old layout paths; the article may name `maxitor[front]` to say what replaced it, so check that one by eye.

```bash
find packages/maxitor -type d -name src -not -path '*/node_modules/*'
```

Expected: only `packages/maxitor/web/client/src`.

## Examples

Run the examples whose paths changed, as Principle VI requires:

```bash
uv run --extra dev python examples/step_26_maxitor/13_maxitor_parts.py
```

```bash
uv run --extra dev python examples/step_26_maxitor/05_full_graph_in_the_browser.py
```

## Before the pull request

On the pushed commit, once the maintainer asks for it:

```bash
bash scripts/check_before_pr.sh
```

This is the only place `check-layout-determinism.ts` runs, with its `uvicorn maxitor.web...` target.

## Adversarial checks

1. Leave `--outDir ../src/maxitor/front/static` in `publish.yml`: the wheel count above is 0.
2. Add `packages/maxitor/front/maxitor/__init__.py`: importing a second part fails, and so does the part's test run.
3. Change one id in `web/graph.json`: the `sed | cmp` line reports a difference.
