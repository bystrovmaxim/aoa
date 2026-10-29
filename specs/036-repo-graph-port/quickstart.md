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
cd /Users/bystrovmaxim/PythonDev/aoa && uv run --extra dev pytest -q packages/maxitor/core/repo_graph_port/tests
```
Expect: the fixture repository's versions are exactly its first-parent commits that changed the graph file; tags land where research R4 says; each version's graph is the committed file byte for byte.

## 3. Keys

```bash
cd /Users/bystrovmaxim/PythonDev/aoa && MAXITOR_HISTORIES=/tmp/histories.toml uv run --extra dev maxitor history key new --history demo --name me
```
Then `GET /api/v1/history/demo/versions` with `X-Maxitor-History-Key` → the versions; another history with that key → `404`; the server's log holds `me`, never the key.

## 4. GitHub

Against the stand-in host in tests; once by hand against a real private repository with the App installed (recorded in the pull request).

## 5. The whole run

```bash
cd /Users/bystrovmaxim/PythonDev/aoa && bash scripts/run_checks_with_log.sh
```
