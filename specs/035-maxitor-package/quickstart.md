# Quickstart: checking every outcome of #286 by hand

Run from the repository root, after the phase that introduces each case.

## 1. The protocol has no code (SC-003)

```bash
cd /Users/bystrovmaxim/PythonDev/aoa && find packages/open-gnomon-protocol -type f | sort
```
Expect only `README.md`, `CHANGELOG.md`, `graph/1.0.json`, `graph/1.1.json`.

## 2. Copies are the protocol's files (SC-002)

```bash
cd /Users/bystrovmaxim/PythonDev/aoa && uv run --extra dev pytest tests/scripts/test_schema_copies.py -q
```
Adversarial: change one byte in `packages/maxitor/src/maxitor/gnomon/schemas/1.1.json` → this test fails naming the copy and its source, no other test fails; restore.

## 3. A light install (SC-001)

```bash
cd /Users/bystrovmaxim/PythonDev/aoa && uv run --extra dev pytest tests/packaging/test_wheel_install_smoke.py -q -k maxitor
```
Expect: a clean venv with only the `maxitor` wheel runs `gnomon check` on this repository, has no `aoa-*` distribution and no viewer dependency; `maxitor-api` exits 2 naming `maxitor[viewer]`.

## 4. The viewer works as before (SC-004, SC-005)

```bash
cd /Users/bystrovmaxim/PythonDev/aoa && uv run --extra dev pytest packages/maxitor/tests -q
```
```bash
cd /Users/bystrovmaxim/PythonDev/aoa && git show 03076a54:packages/aoa-maxitor/graph.json | sed 's/aoa\.maxitor/maxitor.viewer/g' | diff - packages/maxitor/graphs/viewer.json && echo "only the prefix changed"
```

## 5. Boundaries (SC-007)

Add `import maxitor.viewer` to `packages/maxitor/src/maxitor/gnomon/cli.py`, then:

```bash
cd /Users/bystrovmaxim/PythonDev/aoa && uv run --extra dev python scripts/check_package_boundaries.py
```
Expect exit 1 and a line naming `cli.py`, the line, `gnomon` and `maxitor.viewer`. Remove the import: exit 0.

## 6. No old names left (SC-006)

```bash
cd /Users/bystrovmaxim/PythonDev/aoa && git grep -n -E "packages/aoa-maxitor|packages/maxitor-gnomon|aoa\.maxitor|maxitor_gnomon" -- ':!specs' ':!*CHANGELOG.md'
```
Expect no output. Every `CHANGELOG.md` is excluded: its past entries keep the old names as history; the new entries name `maxitor`.

## 7. The CI action (SC-008)

On the pull request, the CI job's step from `./packages/maxitor` passes. Adversarial: edit one label in `packages/aoa-demo/graph.json`, push to a scratch branch → the step fails naming the difference; drop the scratch branch.

## 8. The example of every new case (Principle VI)

```bash
cd /Users/bystrovmaxim/PythonDev/aoa && uv run --extra dev python examples/step_26_maxitor/13_maxitor_parts.py
```
Expect the four cases, each named, with what it printed: `gnomon` from a no-extra install, `maxitor-api` exit 2 with its message, plain `jsonschema` accepting the demo's graph and refusing it without one edge's `id`, `maxitor.viewer` imported.

## 9. The walk-through on gameoffer (SC-009)

The maintainer follows only `packages/maxitor/README.md` in `/Users/bystrovmaxim/PythonDev/ivm`; every stop is a fix to the README or the skill, recorded in T041.

## 10. The whole run (SC-010)

```bash
cd /Users/bystrovmaxim/PythonDev/aoa && bash scripts/run_checks_with_log.sh
```
