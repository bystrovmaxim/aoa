# Quickstart: checking #288 by hand

From the repository root.

## 1. The rename

```bash
cd /Users/bystrovmaxim/PythonDev/aoa && uv run --extra dev pytest -q tests/scripts/test_no_old_names.py
```
```bash
cd /Users/bystrovmaxim/PythonDev/aoa && uv run --extra dev maxitor --help
```

## 2. A history from a local repository

```bash
cd /Users/bystrovmaxim/PythonDev/aoa && uv run --extra dev pytest -q packages/maxitor/tools/repo_graph_port/tests
```
Expect: the fixture repository's versions are exactly its first-parent commits that changed the graph file; tags land where research R4 says; each version's graph is the committed file byte for byte.

## 3. The port's server and keys

```bash
cd /Users/bystrovmaxim/PythonDev/aoa && MAXITOR_HISTORIES=/tmp/histories.toml uv run --extra dev repo-graph-port history key new --history demo --name me
```
```bash
cd /Users/bystrovmaxim/PythonDev/aoa && MAXITOR_HISTORIES=/tmp/histories.toml uv run --extra dev repo-graph-port
```
Then `GET http://127.0.0.1:8102/api/v1/history/demo/versions` with `X-Maxitor-History-Key` → the versions; again with its `ETag` in `If-None-Match` → `304`; another history with that key → `404`; a public link on `/api/v1/history/public/versions?link=…` with no key → its versions; the port's log holds `me`, never the key.

## 4. GitHub and webhooks

Against the stand-in host in tests: a push that changes one graph file of a repository with two gives a new version to that history only; a push that touches no graph file, and a pull request whose merge commit is not a version, change nothing.

## 5. On the stand

`https://repo-graph-port.aoa.run/api/v1/history/<id>/versions` with the history's key, and `…/public/versions?link=…` for a public repository; a merge into one of them shows at once.

## 6. The whole run

```bash
cd /Users/bystrovmaxim/PythonDev/aoa && bash scripts/run_checks_with_log.sh
```
