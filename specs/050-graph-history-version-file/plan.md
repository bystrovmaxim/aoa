# Implementation Plan: A graph's history joined with its version file

**Branch**: `feature/issue-344-graph-history-version-file` | **Date**: 2026-11-02 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/050-graph-history-version-file/spec.md`

## Summary

A history may name a second file. The port lists the commits that changed either file, keeps those where the graph or the number really changed, and says so on each point with `graph_changed`, `version` and `version_changed`. A link it cannot use becomes `version_problem`, and the graph stays open. The cache learns the graph's path, so two graphs of one repository stop overwriting each other.

## Technical Context

**Language/Version**: Python 3.12 and 3.14

**Primary Dependencies**: the action machine, `tomllib`, `json`, git through `GitMirror`. Nothing new.

**Storage**: the port's cache folder on disk (`MAXITOR_HISTORY_CACHE`), with a new layout

**Testing**: pytest on small real git repositories (`tests/repo_builder.py`), and the stand-in GitHub (`tests/stand_in_github.py`)

**Target Platform**: the `repo-graph-port` service

**Project Type**: web service

**Performance Goals**: a version-only point reads no graph file and stores no copy of one

**Constraints**: a bad link never refuses the config or stops the history. A history with no version file answers with the same points as today.

**Scale/Scope**: histories of hundreds of commits, with more points where a version file is named; the pull request reports the measured count

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | How this plan keeps it |
|---|---|
| I. The maintainer decides | Nothing is committed, pushed or opened without an instruction |
| II. English in code and history | All code, comments and commits are in English |
| III–V. Headers, AI-CORE, docstrings | Every new module has its header; public functions have blocks, methods the one line |
| VI. The tail | Three reserved tasks: check run, documentation, changelog. Each case gets a script and a notebook under `examples/` |
| API only through actions | The routes stay; only their parameters and answers grow |

Passed before research and after design. No violations.

## Project Structure

### Documentation (this feature)

```text
specs/050-graph-history-version-file/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/history-answers.md
└── tasks.md
```

### Source Code (repository root)

```text
packages/maxitor/tools/repo_graph_port/
├── maxitor/repo_graph_port/
│   ├── history.py                  # History grows; public_history takes the second link
│   ├── version_source.py           # new: read a number, say what is wrong with a link
│   ├── history_versions.py         # new pure rules: graph_differs, join_points
│   ├── history_reading.py          # points_of, version_problem_of; the detail of a version-only point
│   ├── version_record.py           # the three fields
│   ├── actions/                    # history, describe, version, webhook
│   └── resources/
│       ├── git_mirror.py           # versions over several paths; first_file_at
│       ├── histories_config.py     # the new keys
│       └── version_cache.py        # keyed by graph file; a new root
└── tests/
    └── fixtures/version_gate/      # samples copied from version-gate v0.1.1
```

**Structure Decision**: the feature stays inside `repo_graph_port`. Maxitor's server and client change in #345, and unknown fields already pass through them.

## Complexity Tracking

No violations.
