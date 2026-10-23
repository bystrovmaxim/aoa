# Implementation Plan: a dictionary-typed field is a declared reference, and the graph carries it as an edge

**Branch**: `feature/issue-256-dictionary-reference` | **Date**: 2026-10-23 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/018-dictionary-reference/spec.md`

## Summary

A field typed by a `BaseEnumEntity` descendant passes the entity-field rule unjudged: the model declares a reference, the graph publishes a column, and no edge connects the two. For a collection of dictionary values the column does not even carry `reference_qualname`. This is the defect #249 removed for structural entities, still open for the dictionary kind.

Four work items, then the three reserved tail steps:

1. **The dictionary kind enters the rule.** The classifier learns the Enum kind; the bare type and its optional form are accepted as the declared reference; a collection, a relation container, `NoRelation`, an empty catalogue and a reference to a dictionary outside the graph are refused at the declaration boundary with a message that names the form.
2. **The graph carries the reference.** A typed `entity_reference` edge is emitted for every accepted reference, the graph schema declares it, the field row keeps `reference_qualname`, and the declaration pass runs before referential integrity so a refused target never becomes a dangling edge. The Maxitor resource registers the new edge type in the same phase, because it refuses an unknown edge type.
3. **The ERD shows the reference.** The payload gains a `reference` relation row, the neighbour clause includes a referenced dictionary from another domain, and the renderer's existing relation path draws the arrow.
4. **A refusal names the shape that is wrong.** The union, heterogeneous-collection and mapping messages stop calling every shape a collection and stop offering a many-relation where it does not fit.

Phases 5, 6 and 7 are the tail the constitution reserves: the check run, the documentation, the changelog.

## Technical Context

**Language/Version**: Python 3.12 (`requires-python = ">=3.12"`); Pydantic 2.12.5 supplies `model_fields` and the resolved annotations the rule reads; TypeScript with Vite for the Maxitor client; DuckDB in `aoa-maxitor` materializes the graph JSON.

**Primary Dependencies**: no new dependency. `pytest`, `jsonschema`, `mypy --strict`, `pylint`, `radon`, `vulture`, the package-boundary and package-metadata checkers, and `@hpcc-js/wasm-graphviz` for the SVG checks are already in use.

**Storage**: no storage change. The graph JSON gains one edge type; the Maxitor in-memory DuckDB gains one table. The dictionary code column is untouched.

**Testing**: `pytest` per package; the client build and the Node checks; the closing `bash scripts/run_checks_with_log.sh`. Verification is adversarial per `AGENTS.md`: reintroduce each refusal and each corrected message in isolation, confirm its test fails and no unrelated test does, restore.

**Target Platform**: `aoa-action-machine` (the validator, the graph edge, the node, the graph JSON schema, the coordinator), `aoa-maxitor` (the DuckDB resource, the payload action, the client check), `examples/`, `docs/`.

**Project Type**: library monorepo plus one viewer; the change is one declaration rule, one graph edge, one payload projection and three refusal texts.

**Performance Goals**: no measurable cost. The declaration pass already walks `model_fields` once per build; the reference edge is built while the entity node is constructed; the ERD query gains one `UNION ALL` over a table whose row count equals the number of dictionary-typed fields.

**Constraints**: one commit per phase, each leaving the tree green; the Maxitor resource raises `KeyError` on an unknown edge type, so the graph edge and the resource registration cannot be split across phases; the edge name and the payload field names are proposals (spec D-11) and are fixed here; English throughout (II); nothing is committed without instruction (I).

**Scale/Scope**: 9 dictionary-typed fields in the reporting model, 60 in the repository (26 demo, 23 examples, 11 tests); 1 classifier entry for the Enum kind; 1 new edge module; 1 new graph-schema definition; 1 new DuckDB table; 3 refusal texts; 4 documentation pages; 2 package changelogs; 1 client check.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | How this plan satisfies it |
| --- | --- | --- |
| I. The maintainer decides | No commit, push, PR or merge unless instructed in the current conversation | Seven phases, each a commit only on instruction; the branch exists on the maintainer's word. |
| II. English in commits and code | Every message, comment, docstring, refusal and page in English | Refusal texts, tests, pages and the changelog are English. |
| III. Module headers | Path on line 1, title docstring, ruled sections | The new edge module opens with its path and its purpose; every edited module keeps its header and is changed inside it. |
| IV. AI-CORE blocks | A public class or module-level function carries `ROLE`/`CONTRACT`/`INVARIANTS` | The new `EntityReferenceGraphEdge` gains one; `EntityGraphNode`'s block gains the reference edge; `validate_entity_fields`'s block gains the dictionary forms. |
| V. Short docstrings | One line with a period on every class, function, method | Every new symbol and every new test case. |
| VI. The last three steps | Check run to zero, then documentation, then changelog — exactly three reserved tasks | Phases 5, 6 and 7 are those three, in that order; no earlier phase absorbs them. |
| VI.4–VI.6 each case shown, twice, and executed | Every case as a script under `examples/` and as a notebook, and the examples run | Phase 6 adds the accepted reference, the refused collection, the refused container, the refused marker, the empty catalogue and the three diagnostics as scripts and notebooks, and executes each while writing. |
| Final step: the check run | `bash scripts/run_checks_with_log.sh` green, only the two accepted remarks | Phase 5 runs it, fixes every remark it reports, and records the tail. |

**Violations requiring justification**: none. Complexity Tracking records the new edge type, the moved boundary, and the dictionary-specific messages as deliberate costs.

**Re-checked after Phase 1 design**: unchanged. The design adds one kind to an existing classifier, one edge type, one table and three messages; it removes the empty-catalogue check from the graph edge and keeps every existing form intact.

## Project Structure

### Documentation (this feature)

```text
specs/018-dictionary-reference/
├── plan.md                          # this file
├── spec.md                          # the specification
├── research.md                      # Phase 0: measured baseline, D1–D9
├── data-model.md                    # Phase 1: the reference, the edge, the row, the message
├── quickstart.md                    # Phase 1: the runnable proofs
├── evidence/baseline_probe.py       # the probe research.md quotes
├── contracts/
│   ├── dictionary-reference-field.md  # the form table and the refusals
│   ├── reference-edge.md              # the graph edge, the row, the payload relation
│   └── refusal-diagnostics.md         # the three corrected messages
└── tasks.md                         # Phase 2 output (/speckit-tasks — not created here)
```

### Source Code (repository root)

```text
packages/aoa-action-machine/src/aoa/action_machine/
├── graph/
│   ├── edges/
│   │   ├── entity_reference_graph_edge.py   # new: entity_reference, field_name, cardinality
│   │   └── entity_field_graph_edge.py       # the empty-catalogue check leaves for the validator
│   ├── nodes/entity_graph_node.py           # references built and returned by get_all_edges
│   ├── validators/entity_field_validator.py # the Enum kind, its forms, the shape classifier
│   ├── graph_json_schema.py                 # $defs/entity_reference and link.oneOf
│   └── core/node_graph_coordinator.py       # the declaration pass runs before the wiring pass
└── domain/enum_entity.py                    # docstring: the reference is an edge

packages/aoa-maxitor/src/aoa/maxitor/model/diagrams/
├── resources/duckdb_graph_resource.py       # entity_reference_edges: table, fill, view, registry
├── actions/list_entities_action.py          # the reference relation and the neighbour clause
└── actions/list_entities_action_schema.py   # unchanged: relationship_kind is a free string

packages/aoa-maxitor/client/src/lib/buildDotSource.ts  # unchanged; the relation path draws it
packages/aoa-maxitor/client/scripts/check-erd-dictionary-values.ts  # asserts the arrow and label

packages/*/tests/                            # the form table, the edge, the payload, the messages
examples/step_20_dictionaries/               # the new cases as scripts and notebooks
docs/                                        # the four pages the old behaviour states
```

**Structure Decision**: the change follows the repository's existing split — declaration rules in `graph/validators/`, graph emission in `graph/edges/` and `graph/nodes/`, the display in `packages/aoa-maxitor`, and the corpus under `packages/`, `examples/` and `docs/`. No new package and no new layer.

## Phases

Each phase is one commit on instruction, leaves the tree green, and carries its own regression evidence.

### Phase 1 — The dictionary kind enters the rule

In `entity_field_validator.py`, turn `_STRUCTURAL_BASES` into `_ENTITY_BASES` with the Enum entry, and make `_kind_of` return `"Enum"`. In `_check_field`, accept `D` and `D | None` as the declared reference; refuse a collection of `D` with a message naming the two accepted forms; refuse a relation container whose target is a dictionary; refuse `NoRelation` on a dictionary with the corrected text; refuse a dictionary whose catalogue is empty in every form; refuse a dictionary that is not a graph model (`entity_info_is_set` and not `excluded_from_graph_model`). Move the empty-catalogue refusal out of `EntityFieldGraphEdge._refuse_empty_dictionary` so the rule lives in one place, and keep the graph-edge test's message as the validator's.

Exit: one test per row of the form table passes; the 60 corpus fields build unchanged; the two reporting-model collections are refused with the collection message; the empty-catalogue test now fails at the validator.

### Phase 2 — The graph carries the reference

Add `EntityReferenceGraphEdge` (`AssociationGraphEdge`, `edge_name` `entity_reference`, properties `field_name` and `cardinality`), build `references` in `EntityGraphNode.__init__` from the accepted dictionary fields, return them from `get_all_edges()` and update the class contract. Declare the edge in `graph_json_schema.py` (`$defs/entity_reference` plus `link.oneOf`). Move `validate_entity_fields()` to the start of `NodeGraphCoordinator.build()`, so a refused target is named before the wiring pass can report a dangling edge. Register `entity_reference` in the Maxitor resource in the same commit — a `CREATE TABLE entity_reference_edges`, its fill function, the union view entry and `known_edges` — because the resource raises `KeyError` on an unknown edge type and the demo graph already carries dictionary references.

Exit: the reproducer graph has one `entity_reference` edge to the dictionary; the graph document validates against `GRAPH_JSON_SCHEMA`; the visible corpus graph still builds through `DuckDBGraphResource`; a reference to an excluded dictionary is refused by the validator, not by referential integrity.

### Phase 3 — The ERD shows the reference

Append the reference rows to `relation_sql` in `list_entities_action.py` (`relationship_kind` `reference`, label the field name, cardinals `one` / `zero_many`) and extend `neighbor_clause` to union `entity_reference_edges`, so a dictionary in another domain joins the slice when neighbours are requested. No renderer change: the relation loop already draws any non-specialization kind with its label. Add the payload assertion to `test_list_entities_payload_dictionary.py`, extend `test_demo_dictionary_graph.py`, and extend the client check to assert the arrow and the label beside the dictionary card.

Exit: the payload carries one reference relation per accepted field; the SVG has the arrow and the field label; the dictionary card keeps the #249 rows; a cross-domain dictionary is present with neighbours and absent without them.

### Phase 4 — A refusal names the shape that is wrong

Add a shape classification to the validator — union of entities, homogeneous collection, heterogeneous collection, mapping — and derive the message from it. The union names every entity and asks for separate fields; the heterogeneous collection names the collection and every member; the mapping says mapping. None becomes accepted.

Exit: the three messages assert their shape, and a control test proves the bare structural entity and the dictionary collection keep their current refusals.

### Phase 5 — The closing check run

`bash scripts/run_checks_with_log.sh` to zero, including the client build, the Node checks, mypy, pylint, radon, vulture, packaging and every package's tests. Only the chunk-size advisory and the pending-deprecation warning remain, and the tail is reported.

### Phase 6 — The documentation

`docs/how-to/explicit-entity-fields.md` (the boundaries paragraph and the dictionary form table), `docs/reference/intents-and-invariants.md` (the dictionary graph row), `docs/tutorials/step-20-dictionaries.md` and the ERD case. Each new case appears as a script under `examples/step_20_dictionaries/` and as a notebook, executed while written: the accepted reference, the refused collection, the refused container, the refused marker, the empty catalogue, the excluded dictionary and the three diagnostics. No Russian draft is created.

### Phase 7 — The changelog

One article per affected package in `docs/CHANGELOG.md` — what a reader can now do: a dictionary reference is judged and drawn as a link, a collection of dictionary values is refused with the form that works, and a refusal names the shape that is wrong — without a per-file account.

## Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| The new refusals break a declaration the corpus really uses | The corpus was measured: 49 non-test fields, all bare or optional; phase 1 runs every package suite and the demo before it is committed. |
| The new edge type makes the Maxitor build fail on an unknown type | Phase 2 registers the table, the fill, the union view and `known_edges` in the same commit; a test builds the demo graph through `DuckDBGraphResource`. |
| Moving the declaration pass changes which refusal surfaces first | The move is one line; a test asserts the field refusal wins over a dangling target, and the existing validator and specialization tests keep their order. |
| The reference edge is mistaken for a relation | The edge has its own name and its own table; `AssociationOne[D]` is refused in phase 1, so the only way to get a reference edge is the bare type. |
| A collection of dictionary values is a legitimate need | The refusal names the accepted forms and the issue records the decision (D-2); the reporting model's two fields are the cost, and a later issue can add a many-form if the maintainer wants one. |
| The ERD prints the reference twice | The row keeps `→ Dict`; the edge label is the field name, exactly as a relation row and its edge label differ; the client check asserts both texts once. |
| A cross-domain dictionary is missing from the slice | The neighbour clause unions the reference table and the payload test covers both `include_one_hop_neighbors` values. |

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
| --- | --- | --- |
| A fourth entity kind in the classifier | The rule must see the kind before it can judge the field (FR-001) | Keeping the kind out preserves the silent column the issue exists to remove |
| A new edge type and table | A column property is not a relation, and the ERD draws edges from relations (FR-010, FR-017) | Reusing `entity_relation` would claim a relation the model never declared and would duplicate the field row |
| The declaration pass ahead of the wiring pass | A refused target must be named by the rule, not by referential integrity (FR-014) | Leaving the order makes an unhelpful `InvalidGraphError` the author's first answer |
| Moving the empty-catalogue check out of the graph edge | One rule, one boundary (FR-006) | Two copies drift, as the two description helpers did in #249 |

## Re-checked after Phase 1 design

The design keeps every gate green. It adds one kind, one edge type, one table and three messages, and removes one duplicate check. No gate moves to a violation, and Complexity Tracking's four entries are the deliberate costs above.
