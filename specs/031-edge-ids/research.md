# Research: Every Edge of the Graph Gets an Id

Decisions for [spec.md](spec.md), checked against the code on 2026-10-28.

## R1. Where an edge type declares its rule

- **Decision**: The two edge classes with a special rule declare it as class attributes: `EDGE_TYPE` (the type name the class exports, also used in its `__init__`) and `ID_RULE` (an `EdgeIdRule`). One table, `EDGE_ID_RULES`, in a new module `aoa/action_machine/graph/edge_identity.py`, is built from exactly those class attributes, and the public function reads the table. A test imports every edge module and fails when a `BaseGraphEdge` subclass declares an `ID_RULE` that the table does not carry. `EdgeIdRule` and `EDGE_SEPARATOR` are defined in a leaf module, `graph/core/edge_id_rule.py`, and re-exported by `edge_identity.py`: the table imports the edge classes, and the edge classes need the rule type, so defining it in `edge_identity.py` would be an import cycle.
- **Rationale**: FR-005 wants the rule to live with the type; FR-006 and FR-007 want one function that works from a row alone, including for a reader that never imported the edge classes. The table is importable on its own and the rule is written once, on the class.
- **Alternatives considered**:
  - A registry filled by `BaseGraphEdge.__init_subclass__`. Rejected: `graph/edges/__init__.py` says to import edge types from their leaf modules, so which classes are loaded depends on the caller; a reader of an old file could silently get the default rule.
  - A table only, with nothing on the classes. Rejected: a developer adding an edge type reads the class, not a distant table (FR-005).

## R2. Where the id enters the export

- **Decision**: `NodeGraphCoordinator.to_json()` builds each row with the edge's own `to_dict(source_id=…)`, then sets `row["id"] = edge_id(row)`. The thirty `to_dict` methods are not touched.
- **Rationale**: One place computes the id, with the same function readers use (FR-006); the row it reads is exactly what the export writes, so the computed id and the written id cannot drift (SC-002).
- **Alternatives considered**: Adding the id inside each `to_dict`. Rejected: thirty edits for one rule, and a new edge type could forget it.

## R3. When the build refuses

- **Decision**: A new build pass, `_validate_edge_identity`, runs right after `_single_pass_validate_and_wire` (every edge is wired and every target exists by then). It refuses a node id containing `|` and, for every edge, computes its id from its row; a property value containing `|` or a missing property becomes `InvalidGraphError` naming the edge; a second edge with an id already seen raises the new `DuplicateEdgeError`.
- **Rationale**: Refusing at build time, like duplicate nodes, keeps a broken graph from being served at all (User Story 2). Every node id is checked, not only those used by edges, because any node can gain an edge in the next version.
- **Alternatives considered**: Checking during `to_json()`. Rejected: a service would start and only fail when someone reads its graph.

## R4. The duplicate-edge error

- **Decision**: `DuplicateEdgeError(ValueError)` in `graph/core/exceptions.py`, next to `DuplicateNodeError`, with `edge_id`, `first` and `second` on the instance; each edge is described as `<source_id> -[<type>]-> <target_id>` plus the properties its rule uses, and `str()` names both.
- **Rationale**: Mirrors `DuplicateNodeError` (a `ValueError`, attributes for tests, a message that names both sides); the exceptions module's diagram gains one branch.

## R5. What `edge_id` accepts and refuses

- **Decision**: `edge_id(row: Mapping[str, Any]) -> str` reads `source_id`, `type`, `target_id` and, for a type in the table, the property its rule names. It ignores any `id` already present, so it accepts 1.0 and 1.1 rows alike. A missing or empty property, or one whose value is not a string, raises `ValueError` naming the type and the property; a part containing `|` raises `ValueError` naming the part.
- **Rationale**: FR-007 — a reader of an old file gets the same id, or a loud error, never a guess.

## R6. Order, version and the published schema

- **Decision**: `to_json()` sorts edge rows by `id` and writes `schema_version` `"1.1"`. The coordinator's in-memory indexes keep their current order, so `get_edges_by_type` and the other readers of the built graph do not change. In `graph_json_schema.json` (read by `graph_json_schema.py`), `schema_version` becomes `"1.1"`, and `link_row` gains a required `id` (non-empty string) while keeping `additionalProperties: false`. Tests that build `"1.0"` payloads for the schema move to `"1.1"` and give their edges ids.
- **Rationale**: FR-010 and FR-011; the published schema describes the format the code writes. A 1.0 file is read by computing ids (R5), not by validating it against the schema.

## R7. Readers in this repository

- **Decision**: Nothing changes in Maxitor or in the MCP adapter. Maxitor's graph build reads named edge fields and ignores the rest; its test suite and an answer-by-answer comparison of the demo graph's diagrams before and after prove FR-012 / SC-005. The MCP adapter's `_build_graph_json` is its own simplified format for MCP clients.

## R8. Documentation and the hand check

- **Decision**: The documentation is a new section of `docs/tutorials/step-26-maxitor.md` — the page where the graph export is already explained — with `examples/step_26_maxitor/11_edge_ids.py` and its notebook showing every case: the default id, a relation named by its field (and keeping its id when its target changes), a transition with its `from_state`, the duplicate refusal, the `|` refusal, and computing ids for a 1.0 row. The gameoffer comparison of SC-003 is run by hand on the two snapshot files (see [quickstart.md](quickstart.md)); its result goes into the pull request, and the files are not committed.
