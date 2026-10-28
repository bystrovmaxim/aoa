# Implementation Plan: A Service Keeps Its Current Graph in One File, by the Format of maxitor-gnomon

**Branch**: `feature/issue-301-gnomon-graph-file` | **Date**: 2026-10-28 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/034-gnomon-graph-file/spec.md` — issue #301 (step 2.1 of #273).

## Summary

A new package, `maxitor-gnomon`, gives the graph's format a home that knows nothing about AOA: the graph JSON schema by version (`1.0` recovered from git, `1.1` moved unchanged from AOA), the config `gnomon.toml`, the commands `gnomon write`, `gnomon check`, `gnomon validate` and `gnomon skill`, and a skill for coding agents, `gnomon-setup`, whose one command Setup finds, proves and configures a project's graphs and audits them later. `gnomon write` and `gnomon check` run each graph's build command in a process of its own, check what it prints against the schema of its declared version, and write or compare the graph file. AOA takes its schema from the package and changes nothing else. The demo and Maxitor save their graphs; this repository's check run writes them as its last step, only when every other step passed. The package's README explains how a graph travels with a pull request and gives three ways to start — by hand, from the command line, with a one-sentence prompt — which the maintainer tries on gameoffer. Approach and alternatives: [research.md](research.md).

## Technical Context

**Language/Version**: Python ≥ 3.12

**Primary Dependencies**: `jsonschema` (already used by `aoa-action-machine`); `tomllib` and `importlib.resources` from the standard library; nothing from AOA

**Storage**: files — the schemas inside the package, the graph files in the repository

**Testing**: pytest in `packages/maxitor-gnomon/tests`; the existing suites of `aoa-action-machine`, `aoa-maxitor` and `aoa-demo` unchanged; the check run

**Target Platform**: any platform the packages support; CI on GitHub Actions for projects that adopt it

**Project Type**: library with a console script (a new package in the monorepo)

**Performance Goals**: building and writing both graphs adds a few seconds to a green check run (the demo builds in about 2 s with its imports)

**Constraints**: the package imports nothing from `aoa` (enforced); a published schema version never changes; the graph file holds only the graph; two writes of an unchanged graph give the same bytes; each graph built in a process of its own

**Scale/Scope**: one new package (schemas, config reader, writer, differences), AOA's schema module reading from it, two small modules printing the demo's and Maxitor's graphs, the boundary checker, the packaging smoke test, `publish.yml`, the check run's steps, `gnomon.toml` and two graph files

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | How this plan meets it | Pre | Post |
|---|---|---|---|
| I. The maintainer decides | No commit, push, pull request or issue comment without an instruction in the conversation. | ✅ | ✅ |
| II. English | Code, comments, commits, issues in English; only `tasks.ru_draft.md` and the README's draft are Russian, not committed. | ✅ | ✅ |
| III. Module headers | Every new module (`schemas`, `config`, `writer`, `differences`, `cli`, and the two graph-printing modules) opens with its path, a title line and `PURPOSE` / `ARCHITECTURE / DATA FLOW`. | ✅ | ✅ |
| IV. AI-CORE blocks | The public types and functions of the contract (`check_graph`, `graph_schema`, `read_config`, `Graph`, `GraphRefused`, `ConfigRefused`, the writer's entry points) carry AI-CORE blocks. | ✅ | ✅ |
| V. Short docstrings | Every class, function and method has a one-line docstring. | ✅ | ✅ |
| VI. The tail | Three last tasks in order: check run, documentation (the package's README; step 00 and a section of step 26 in AOA's guide; the root README's table; `docs/index.md`; `examples/step_26_maxitor/12_graph_file.py` with its notebook), changelog. | ✅ | ✅ |
| Final step: the check run | The run keeps every step and gains the package's build and tests, its boundary rule, and the graph step that runs last and only on a green run. | ✅ | ✅ |

**VI.5 — script and notebook.** Unlike #279, most cases are library calls worth seeing step by step, so `examples/step_26_maxitor/12_graph_file.py` and its executed notebook show every case (research R9).

## Project Structure

### Documentation (this feature)

```text
specs/034-gnomon-graph-file/
├── spec.md
├── plan.md                  # this file
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── gnomon.md
├── checklists/
│   └── requirements.md
└── tasks.md                 # + tasks.ru_draft.md, not committed
```

### Source Code (repository root)

```text
packages/maxitor-gnomon/                         # NEW package
├── pyproject.toml                               # console script `gnomon`; dependency: jsonschema
├── README.md                                    # format, versions, gnomon.toml, PR flow, three ways to start (by hand, command line, short prompt) (+ README.ru_draft.md)
├── LICENSE, NOTICE, CHANGELOG.md
├── src/maxitor_gnomon/
│   ├── __init__.py
│   ├── schemas/graph/1.0.json, 1.1.json         # never changed once published
│   ├── schemas/config/1.0.json
│   ├── schemas.py                               # graph_schema, check_graph, SCHEMA_VERSIONS, GraphRefused
│   ├── config.py                                # read_config, Graph, ConfigRefused
│   ├── differences.py                           # differences by id
│   ├── writer.py                                # build, check, write
│   ├── skills/gnomon-setup/SKILL.md             # the skill: Setup, for first and later setup; self-install from a link
│   └── cli.py                                   # `gnomon write` / `check` / `validate` / `skill`
└── tests/

packages/aoa-action-machine/
├── pyproject.toml                               # depends on maxitor-gnomon
└── src/aoa/action_machine/graph/
    ├── graph_json_schema.py                     # GRAPH_JSON_SCHEMA = graph_schema("1.1")
    └── graph_json_schema.json                   # DELETED (moved)

packages/aoa-demo/src/aoa/demo/graph_json.py     # NEW: prints the demo's graph
packages/aoa-maxitor/src/aoa/maxitor/graph_json.py  # NEW: prints Maxitor's own graph
packages/aoa-demo/graph.json, packages/aoa-maxitor/graph.json   # NEW: first graph files (excluded from sdists)
gnomon.toml                                      # NEW: the repository's two graphs

pyproject.toml                                   # workspace member, sources, mypy and vulture paths
scripts/package_boundaries.toml, scripts/check_package_boundaries.py   # maxitor_gnomon imports nothing from aoa
scripts/check_run.py                             # package build + tests; last step `Graph files (gnomon write)`
tests/packaging/test_wheel_install_smoke.py      # a wheel outside the aoa namespace
.github/workflows/publish.yml                    # job for maxitor-gnomon
docs/how-to/run-the-checks.md                    # one line on the graph step
docs/tutorials/step-00-get-started.md            # "Save your graph from day one"; maxitor-gnomon in the repository map
docs/tutorials/step-26-maxitor.md                # "The graph saved with every change"
docs/index.md, README.md                         # a line under Maxitor; the packages table
examples/step_26_maxitor/12_graph_file.py        # + 12_graph_file.ipynb, every case
docs/CHANGELOG.md                                # one article
```

**Structure Decision**: the package sits beside the others in `packages/` and in the uv workspace, but outside the `aoa` namespace, so its independence shows in its import name and is enforced by the boundary checker.

## Complexity Tracking

None.
