# Implementation Plan: Every Edge of the Graph Gets an Id

**Branch**: `feature/issue-285-edge-ids` | **Date**: 2026-10-28 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/031-edge-ids/spec.md` — issue #285, step 1 of 10 of #273.

## Summary

Give every edge of the graph export an identity, so two versions of a graph can be compared edge by edge. One public function, `edge_id(row)`, computes the id from an exported edge row: `<source_id>|<type>|<target_id>` by default; an `entity_relation` is named by its field instead of its target; a `lifecycle_transition` appends the state it leaves. The two special rules are declared on their edge classes and collected into one table, so the function also works for a reader of an old file. The coordinator writes the id on every edge, exports edges in id order under `schema_version` `"1.1"`, and refuses at build time a graph with two edges of one id (`DuplicateEdgeError`) or a `|` inside an id part. Approach and alternatives: [research.md](research.md).

## Technical Context

**Language/Version**: Python ≥ 3.12 (`aoa-action-machine`)

**Primary Dependencies**: none new; `jsonschema` (already a dependency) validates the published schema in tests

**Storage**: N/A — the export is a JSON string

**Testing**: pytest, in `packages/aoa-action-machine/tests/action_machine/graph/`; Maxitor's suite as the reader check

**Target Platform**: any platform the package supports

**Project Type**: library (monorepo package `aoa-action-machine`)

**Performance Goals**: building and exporting the demo graph (3213 nodes, 4841 edges) takes no noticeably longer — one id per edge, computed once at build and once at export

**Constraints**: ids computed only from exported fields; no change to the thirty edge `to_dict` methods; no change in Maxitor or in the MCP adapter

**Scale/Scope**: 2 edge classes, the coordinator, the exceptions module, the JSON schema, two new modules, tests; documentation in tutorial step 26

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | How this plan meets it | Pre | Post |
|---|---|---|---|
| I. The maintainer decides | No commit, push or pull request without an instruction in the conversation; tasks prepare changes and stop. | ✅ | ✅ |
| II. English | Code, docstrings, comments, commits and the issue in English; only `tasks.ru_draft.md` is in Russian, and it is not committed. | ✅ | ✅ |
| III. Module headers | The new `graph/edge_identity.py` opens with its path, a title line and `PURPOSE` / `ARCHITECTURE / DATA FLOW` sections; touched modules keep theirs, and the exceptions diagram gains the duplicate-edge branch. | ✅ | ✅ |
| IV. AI-CORE blocks | `EdgeIdRule`, `edge_id` and `DuplicateEdgeError` carry blocks (`ROLE`, `CONTRACT`, `INVARIANTS`, `FAILURES` where it applies); none in a module docstring or on a method. | ✅ | ✅ |
| V. Short docstrings | Every new class, function and method has a one-line docstring ending with a period. | ✅ | ✅ |
| VI. The tail | Three last tasks, in order: the check run taken to zero, the documentation (section of step 26 + `examples/step_26_maxitor/11_edge_ids.py` and its notebook, every case, executed), the changelog article. | ✅ | ✅ |

No violation; Complexity Tracking stays empty.

## Project Structure

### Documentation (this feature)

```text
specs/031-edge-ids/
├── spec.md
├── plan.md                  # this file
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── edge-identity.md
├── checklists/
│   └── requirements.md
└── tasks.md                 # /speckit-tasks (+ tasks.ru_draft.md, not committed)
```

### Source Code (repository root)

```text
packages/aoa-action-machine/src/aoa/action_machine/graph/
├── edge_identity.py                     # NEW: EDGE_ID_RULES, edge_id(); re-exports EdgeIdRule
├── graph_json_schema.json               # schema_version 1.1, id required on link_row (read by graph_json_schema.py)
├── core/
│   ├── edge_id_rule.py                  # NEW: EDGE_SEPARATOR, EdgeIdRule — a leaf the edge classes import
│   ├── exceptions.py                    # NEW DuplicateEdgeError
│   └── node_graph_coordinator.py        # _validate_edge_identity pass; to_json writes id, id order, 1.1
└── edges/
    ├── entity_graph_edge.py             # EDGE_TYPE, ID_RULE (member field_name)
    └── state_graph_edge.py              # EDGE_TYPE, ID_RULE (suffix from_state)

packages/aoa-action-machine/tests/action_machine/graph/
├── test_edge_identity.py                # NEW: the function, the rules, 1.0 rows, refusals, the guard over all edge classes
├── test_node_graph_coordinator_json.py  # export: id on every edge, id order, 1.1, demo graph uniqueness
└── test_graph_json_schema_*.py          # payloads move to 1.1, edges carry ids

docs/tutorials/step-26-maxitor.md        # new section on edge ids
examples/step_26_maxitor/11_edge_ids.py  # + 11_edge_ids.ipynb
docs/CHANGELOG.md                        # one article
```

**Structure Decision**: Everything lives in `aoa-action-machine`, where the export is made. `edge_identity.py` sits at the `graph/` level because it imports the two concrete edge classes; the rule type itself lives in the leaf `graph/core/edge_id_rule.py`, because the edge classes need it and importing it from `edge_identity.py` would be a cycle. The coordinator in `graph/core/` already imports domain-level code (`graph.validators`), so it may import it too.

## Complexity Tracking

None.
