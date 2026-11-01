# Implementation Plan: Maxitor parts one level shallower, and `front` named `web`

**Branch**: `feature/issue-305-maxitor-one-level-less-drop-src` | **Date**: 2026-11-01 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/047-maxitor-flat-parts/spec.md`

## Summary

Drop the `src/` level from all five parts of `packages/maxitor`, then rename the part `front` to `web` in its folder, import path and extra. The moves must leave behaviour and both graphs byte for byte unchanged, and the rename must change the graph only by the module name. The work lands as the four phases of issue #305, one commit each.

## Technical Context

**Language/Version**: Python 3.12, TypeScript for the client

**Primary Dependencies**: hatchling (wheel), uv (workspace and lock), Vite (client build)

**Storage**: N/A; `graph.json` files are the only saved artefacts touched

**Testing**: pytest per part, `scripts/check_before_commit.sh`, `scripts/check_before_pr.sh`, `graph-builder check`

**Target Platform**: PyPI wheel, container images, the stand

**Project Type**: repository layout change across one Python distribution

**Performance Goals**: N/A

**Constraints**: both graphs byte for byte unchanged through phase 2; the distribution name and the commands never change; old specs and past changelog entries keep their words

**Scale/Scope**: 167 files moved, 158 first lines rewritten; the rename touches about 193 files and 588 lines outside old specs and graph files

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | How it is met |
|---|---|---|
| I. Maintainer decides | Pass | Each of the four commits waits for its own instruction. Nothing is pushed or opened on the agent's initiative. |
| II. English | Pass | All artefacts and commit text are in English. Only `tasks.ru_draft.md` is Russian, and it is ignored by git. |
| III. Module headers | Pass, with a note | Line 1 follows every move. The principle's wording says `packages/*/src`, which Maxitor's modules leave (R9). The wording is the maintainer's. |
| IV. AI-CORE blocks | Pass | Not touched. |
| V. Short docstrings | Pass | No new functions. |
| VI. Tail of a change | Pass | Phase 4 carries exactly three tasks in order: check run, documentation, changelog. Item 5 is met by the existing examples, updated and re-run; there is no new scenario to show, apart from the changed message, which the existing `13_maxitor_parts` example covers. |
| Final check run | Pass | `check_before_commit.sh` on each phase; `check_before_pr.sh` on the pushed commit. |

Re-check after design: no violations. R2 records a cost, not a violation.

## Project Structure

### Documentation (this feature)

```text
specs/047-maxitor-flat-parts/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/names.md
└── tasks.md             # /speckit-tasks
```

### Source Code (repository root)

```text
packages/maxitor/
├── core/
│   ├── graph_compare/{maxitor/graph_compare/, tests/}
│   └── graph_map/{maxitor/graph_map/, tests/}
├── web/
│   ├── maxitor/web/
│   ├── client/
│   └── tests/  graph.json  pytest.ini  Dockerfile  README.md
├── tools/
│   ├── graph_builder/{maxitor/graph_builder/, tests/}
│   └── repo_graph_port/{maxitor/repo_graph_port/, tests/}
└── skills/
```

**Structure Decision**: as the issue states. `maxitor` stays a namespace with no `__init__.py`. The `aoa-*` packages are out of scope.

## Phases

Each phase ends with `check_before_commit.sh` green and one commit, on the maintainer's instruction. `uv sync --all-extras` follows every move. The list of what follows each path is [contracts/names.md](contracts/names.md).

1. **Move `front`.** `git mv` the code and rewrite line 1, then update configuration. The graph is unchanged by `cmp`.
2. **Move the other four parts.** The same, with the `$id` of `config_schema.json`. `mypy` targets end at `/maxitor` (R3).
3. **Rename `front` to `web`.** Folder, import, extra, entry point, `uv.lock`, CI, stand, message. Identifiers only (R6). `ruff --fix` reorders imports (R7). `graph-builder write` regenerates `web/graph.json`, and the `sed | cmp` proves it.
4. **Closing.** Three tasks in order: the check run taken to zero, the documentation, one changelog article in `docs/CHANGELOG.md` about `maxitor[web]`.

## Risks

| Risk | Guard |
|---|---|
| A blind `s#/src##` widens mypy to tests and the client (R3) | the task names mypy targets separately |
| The published wheel lacks the client | quickstart's wheel count; adversarial break 1 |
| The browser check's `uvicorn` target is missed, and only `check_before_pr.sh` runs it (R4) | the search of SC-001 |
| A docstring edit breaks the graph proof (R5, R6) | identifiers only in phase 3 |
| A stale `uv.lock` fails `uv sync --frozen` in the images | phase 3 regenerates the lock; quickstart's image build |
| A stray `maxitor/__init__.py` breaks the namespace | data model's rule; adversarial break 2 |
| The worktree of #296 changes `pyproject.toml` or `scripts/check_run.py` in parallel | merge whichever lands second; no shared design |

## Complexity Tracking

No violations to justify.
