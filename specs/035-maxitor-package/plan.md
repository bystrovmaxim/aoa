# Implementation Plan: The Protocol in a Folder with No Code; Maxitor as One Package with Extras

**Branch**: `feature/issue-286-maxitor-package` | **Date**: 2026-10-29 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/035-maxitor-package/spec.md` (issue #286, step 2.2 of #273)

## Summary

The Open Gnomon Protocol leaves `maxitor-gnomon` for a folder with no code, `packages/open-gnomon-protocol` (schemas, specification, changelog; `$id` becomes a fetchable raw address). `aoa-maxitor` and `maxitor-gnomon` merge into one package, `maxitor`: `maxitor.gnomon` (the command, light), `maxitor.viewer` (Maxitor's server and built front, formerly `aoa.maxitor`) and `maxitor.skills`, with the extras `viewer` and `all`. Python packages keep committed copies of the schemas, proved identical to the protocol's by the check run (research R1). The package-boundary checker learns the parts inside `maxitor`, so `gnomon` can never import the viewer or AOA. Each service has its own graph file under `packages/maxitor/graphs/`. A composite GitHub Action gives other projects the check in one `uses:` line.

## Technical Context

**Language/Version**: Python ≥ 3.12 (CI runs 3.12.3; the check run uses the repository's `.venv`); TypeScript/React for the viewer's client, unchanged.

**Primary Dependencies**: hatchling (build), uv (workspace, build, lock); `jsonschema`, `jsonschema-rs` (the command); AOA, `aoa-fastapi-adapter`, FastAPI/uvicorn, duckdb, httpx, websockets (the viewer).

**Storage**: files — the schema folder, committed schema copies, `graphs/viewer.json`, `gnomon.toml`.

**Testing**: pytest per package; `tests/packaging/test_wheel_install_smoke.py` (clean-venv installs); `tests/scripts/` (check run, graph files); `scripts/check_package_boundaries.py`; the full check run `bash scripts/run_checks_with_log.sh`.

**Target Platform**: developer machines and GitHub Actions (ubuntu-latest); PyPI as the distribution channel (publishing is the maintainer's).

**Project Type**: monorepo of Python libraries and one web application (the viewer) plus a CLI.

**Performance Goals**: no change — `gnomon check` on the demo stays within the current ~1 s of validation; the viewer serves as before.

**Constraints**: `pip install maxitor` with no extra installs no AOA package and no viewer dependency (SC-001); every schema copy byte-identical to the folder (SC-002); the viewer's graph changes only in its id prefix (SC-004); no tracked file outside old specs names the old folders or imports (SC-006).

**Scale/Scope**: 2 packages merged; ~1 366 `aoa.maxitor` mentions inside the viewer, ~40 files outside it, plus `packages/aoa-maxitor` path mentions in the workspace, scripts, workflows, deploy and docs; 61 gnomon tests and the viewer's test suite move.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**This repository's constitution** (`.specify/memory/constitution.md`):

| Principle | How the plan meets it | Status |
|---|---|---|
| I. The maintainer decides | Each phase ends with a commit **only on the maintainer's instruction**; no push, PR or merge without one. Publishing `maxitor` and tagging the protocol are out of scope (FR-019). | ✅ |
| II. English | All code, comments, docstrings, commit messages, the issue and the docs in English; only `tasks.ru_draft.md` and the documentation pages' `*.ru_draft.md` are Russian, and they never enter a commit. | ✅ |
| III. Module headers | Every new or moved module keeps line 1 as its path — which changes with the move (`# packages/maxitor/src/maxitor/viewer/…`) — and the `PURPOSE` / `ARCHITECTURE / DATA FLOW` docstring. The rename updates line 1 of every moved module. | ✅ |
| IV. AI-CORE blocks | Moved blocks move unchanged; the new `launch.viewer` function and the boundary checker's additions carry blocks where they are public. | ✅ |
| V. Short docstrings | Every new function and method gets its one line. | ✅ |
| VI. Tail: check run, docs, changelog | Phase 7 is three commits in that order. Every new case a reader meets is shown as an executed script and notebook: `examples/step_26_maxitor/13_maxitor_parts.{py,ipynb}` (a no-extra install with `gnomon`, `maxitor-api` naming its missing extra, a graph checked against the protocol with plain `jsonschema`, the import `maxitor.viewer`) and the re-executed `12_graph_file.*`; the CI action is shown in the README as the one step it is. A schema-copy drift and a boundary violation are the repository's own guards, shown in `docs/how-to/run-the-checks.md`. | ✅ |
| Final step: the check run | The run is updated for the new paths (client build, package list, graph step) and taken to zero; the two accepted remarks stay. | ✅ |

**The offers project's AOA rules 41–66** (applied to Maxitor by the maintainer's decision of 2026-10-29): this change moves code and adds no action, resource, adapter or context. Rule 54 (file named after its class) — `launch.py` holds functions only; moved files keep their names. Rule 60 (a service's graph from its own code) — `graphs/viewer.json` is built from `maxitor.viewer` only (R6). ✅

No violations; Complexity Tracking stays empty.

## Project Structure

### Documentation (this feature)

```text
specs/035-maxitor-package/
├── spec.md
├── plan.md              # this file
├── research.md          # R1–R10
├── data-model.md        # the protocol folder, the package, its parts, extras, copies, boundaries
├── quickstart.md        # how to check every outcome by hand
├── contracts/
│   ├── install.md       # what each install brings and which commands work
│   ├── boundaries.md    # who may import whom, and the checker's new keys
│   └── ci-action.md     # the composite action's inputs and steps
├── checklists/requirements.md
└── tasks.md             # /speckit-tasks (with tasks.ru_draft.md)
```

### Source Code (repository root)

```text
packages/
├── open-gnomon-protocol/                 # NEW — from packages/maxitor-gnomon/protocol/
│   ├── README.md                         # the specification, cut to the graph document (§1–4)
│   ├── CHANGELOG.md                      # NEW
│   └── graph/1.0.json, 1.1.json          # $id → raw address in this folder
│
├── maxitor/                              # NEW — from packages/aoa-maxitor + packages/maxitor-gnomon
│   ├── pyproject.toml                    # name maxitor, 3.0.0; extras viewer, all; gnomon, maxitor-api
│   ├── README.md                         # the package; graph file, config and repository rules moved here
│   ├── CHANGELOG.md                      # continues aoa-maxitor's; maxitor-gnomon's 0.1.0 below
│   ├── LICENSE, NOTICE, THIRD-PARTY-NOTICES.md
│   ├── Dockerfile                        # paths follow
│   ├── action.yml                        # NEW — the CI check (contracts/ci-action.md)
│   ├── client/                           # from aoa-maxitor/client
│   ├── graphs/viewer.json                # from aoa-maxitor/graph.json
│   ├── src/maxitor/
│   │   ├── __init__.py                   # version only
│   │   ├── launch.py                     # NEW — maxitor-api entry; names the missing extra
│   │   ├── gnomon/                       # from maxitor_gnomon (cli, config, differences, writer)
│   │   │   ├── config_schema.json        # from protocol/config/1.0.json
│   │   │   └── schemas/                  # __init__.py + committed 1.0.json, 1.1.json (copies)
│   │   ├── viewer/                       # from aoa/maxitor (api, model, samples, static, build_graph)
│   │   └── skills/gnomon-setup/SKILL.md  # from maxitor-gnomon/skills
│   └── tests/
│       ├── gnomon/                       # from maxitor-gnomon/tests
│       └── viewer/                       # from aoa-maxitor/tests
│
└── aoa-action-machine/src/aoa/action_machine/graph/
    ├── graph_json_schema.py              # reads its own copy; no maxitor import
    └── graph_json_schema.json            # committed copy of protocol graph/1.1.json

Removed: packages/aoa-maxitor/, packages/maxitor-gnomon/ (incl. shipped.py).

Changed outside packages: pyproject.toml (workspace, dev extra, mypy/vulture/ruff paths, scripts),
uv.lock, gnomon.toml, scripts/{check_run.py, package_boundaries.toml, check_package_boundaries.py,
check_package_metadata.py, run_checks_with_log.sh}, tests/packaging/test_wheel_install_smoke.py,
tests/scripts/test_graph_files.py, NEW tests/scripts/test_schema_copies.py,
.github/workflows/{ci.yml, publish.yml}, deploy/stand/docker-compose.yml, .claude/launch.json,
.vscode/launch.json, .gitignore, README.md, docs/**, examples/** (aoa.maxitor imports and paths).
Old specs and the past entries of every CHANGELOG.md keep the old names: they are history.
```

**Structure Decision**: one installable package with parts (`packages/maxitor`) and one code-free standard (`packages/open-gnomon-protocol`), as the issue settles; the rest of the monorepo is unchanged.

## Phases → commits

Each phase is one commit, made only on the maintainer's instruction; the issue's box is ticked with its sha.

| # | Phase (issue #286) | Contents | Proof |
|---|---|---|---|
| 1 | Preview servers use the dev environment | `.claude/launch.json` `maxitor-api` with `uv run --extra dev` | starting the preview keeps `pytest` importable in `.venv` |
| 2 | The protocol folder | `packages/open-gnomon-protocol` (schemas with new `$id`, README §1–4, CHANGELOG); `aoa-action-machine` ships `graph_json_schema.json`, reads it, drops `maxitor-gnomon`; `maxitor-gnomon` keeps working, reading its copies (still in its old folder); `tests/scripts/test_schema_copies.py` | copy test passes; break a byte in a copy → only that test fails; AOA wheel installs without `maxitor-gnomon` |
| 3 | The viewer becomes `maxitor` | `git mv packages/aoa-maxitor packages/maxitor`, `src/aoa/maxitor` → `src/maxitor/viewer`; rename everywhere; extra `viewer`; `graphs/viewer.json`; `launch.py`; boundary config for the viewer; workspace, check run, workflows, deploy, examples, docs paths | viewer tests pass; old vs new graph differ only in id prefix; `maxitor-api` without `[viewer]` names the extra |
| 4 | `gnomon` joins `maxitor` | `git mv` `maxitor_gnomon` → `maxitor/gnomon`, tests, config schema; `shipped.py` gone; `[standalone.gnomon]` with `forbid`; checker learns nested prefixes; smoke test: clean `pip install maxitor` runs `gnomon check`, brings no AOA | add `import maxitor.viewer` to `gnomon` → boundary check fails naming it; restore |
| 5 | The skills | `src/maxitor/skills/gnomon-setup`; `gnomon skill` prints it; commands name `maxitor` | `gnomon skill` in a clean venv prints it |
| 6 | The CI action | `packages/maxitor/action.yml`; `.github/workflows/ci.yml` uses it | CI on the PR green; a stale graph fails the step |
| 7a | Closing check run | `bash scripts/run_checks_with_log.sh` to zero | the log's last run green |
| 7b | Documentation | protocol README, `maxitor` README (+ Russian draft), root README table, tutorial step 26; `examples/step_26_maxitor/13_maxitor_parts.{py,ipynb}` new and `12_graph_file.{py,ipynb}` re-executed; the maintainer's walk-through on gameoffer, fixes in the README and the skill | examples run; the walk-through needs no step outside the README (SC-009) |
| 7c | Changelog | one article in `docs/CHANGELOG.md` | — |

Adversarial verification in every test task: break the code the way the new test must catch, confirm that test fails and no other, restore.

## Complexity Tracking

No constitution violations.
