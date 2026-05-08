# Distributions, imports, and releases

This document describes how **pip package names**, **import paths**, and **versions** relate in the ActionMachine monorepo.

## Pip packages and import namespaces

| Pip (distribution) | Python import prefix | Purpose |
|--------------------|----------------------|---------|
| `aoa-graph` | `aoa.graph` | Graph interchange types, coordinators, rustworkx-backed tooling |
| `aoa-action-machine` | `aoa.action_machine` | Core framework: actions, intents, runtime, adapters |
| `aoa-maxitor` | `aoa.maxitor` | Sample domains, HTML visualizers, Maxitor-specific tests |
| `aoa-examples` | `aoa.examples` | Example FastAPI and MCP services |

All use the shared **`aoa`** namespace (PEP 420); wheels ship paths such as `aoa/graph/...`, not a single merged tree in one wheel.

## Dependency matrix (runtime)

Allowed **production** imports between internal packages:

```text
aoa.graph           → (stdlib / third-party only)
aoa.action_machine  → may import aoa.graph
aoa.maxitor         → may import aoa.graph, aoa.action_machine
aoa.examples        → may import aoa.graph, aoa.action_machine only
```

**`aoa.examples` must not depend on `aoa.maxitor`.** Anything that needs both (e.g. HTML demos that load Maxitor) belongs in integration tests, optional dev dependencies, or documentation—not in the `aoa-examples` distribution metadata.

Third-party libraries (Pydantic, rustworkx, FastAPI, …) are declared per package in each `packages/aoa-*/pyproject.toml`.

## Repository layout

- Publishable packages: `packages/aoa-graph`, `packages/aoa-action-machine`, `packages/aoa-maxitor`, `packages/aoa-examples` (each with its own `pyproject.toml` and `src/aoa/<name>/`).
- Workspace root `pyproject.toml` (`aoa-run`) ties the four members for local development (see `[tool.uv.workspace]`).

## Version and release policy

**Default: lockstep.** All four distributions are intended to ship the **same version number** (e.g. `1.0.0`) for a given release train. Internal dependencies pin compatible ranges (e.g. `aoa-graph==1.0.0` inside `aoa-action-machine`) so a resolved install is consistent.

**Independent patch releases** are allowed later only when a change is strictly local to one distribution and does not break downstream install graphs; document any exception in the changelog.

**Publishing:** build wheels from each package directory (`python -m build packages/<name>` or `uv build --package …`). The repository’s check runner builds all four and runs packaging smoke tests under `tests/packaging/`.

## Automated checks (CI / local runner)

`scripts/run_checks_with_log.sh` is the single full entry point. It runs, among others:

| Step | Script / command | Role |
|------|------------------|------|
| Package boundaries (prod) | `scripts/check_package_boundaries.py` | Forbidden `aoa.*` imports between graph / action_machine / maxitor / examples in `packages/`. |
| Package boundaries (tests) | `… --tests` | Same matrix for `tests/graph`, `tests/action_machine`, … |
| Package metadata | `scripts/check_package_metadata.py` | Declared pip dependencies match the matrix in each `packages/aoa-*/pyproject.toml`. |
| Build + packaging smoke | `python -m build …` then `pytest tests/packaging` | Wheels layout and clean-venv installs. |
| Test layer (action_machine) | `scripts/check_test_layer_imports.py` | **Not** redundant with package boundaries: it restricts *internal* `aoa.action_machine.*` subpackages per directory under `tests/action_machine/` (e.g. model tests must not import runtime). **Kept.** |
| Maxitor samples public API | `scripts/check_maxitor_samples_public_api.py` | Samples may only import an allowlisted facade of `aoa.action_machine`. **Kept.** |

There is **no** open temporary `allow` list in `scripts/package_boundaries.toml` (`allow = []`). Any future exception must include `reason` and `expires`.

## Further reading

- Root `README.md` — quick install commands
- `docs/CHANGELOG.md` — breaking changes and release notes
- `archive/plan/CURRENT.md` — full multi-package migration plan (archive path may be gitignored locally)
