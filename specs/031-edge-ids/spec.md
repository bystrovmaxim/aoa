# Feature Specification: Every Edge of the Graph Gets an Id

**Feature Branch**: `feature/issue-285-edge-ids`

**Created**: 2026-10-28

**Status**: Draft

**Input**: User description: "https://github.com/bystrovmaxim/aoa/issues/285 — Graph history 1/10: every edge of the graph gets an id. Sub-issue of #273 (graph history). Use the issue body as the source of truth."

## Context: what is true today, checked on 2026-10-28

- **Nodes have an identity; edges do not.** `NodeGraphCoordinator.to_json()` writes `schema_version` `"1.0"`, nodes sorted by `id`, and edges with `source_id`, `target_id`, `type`, `relationship`, `is_dag` and `properties` — no `id`. A node's `id` is the qualified name of the code that declares it, computed at every build, and the build refuses two nodes with one `id` (`DuplicateNodeError`).
- **Edges are sorted by `(source_id, type, target_id)`**; edges that share all three keep the order in which they were emitted.
- **Source, type and target do not identify an edge.** In this repository's demo graph (3213 nodes, 4841 edges, 28 edge types) two edge types repeat between the same two nodes: `entity_relation` in 2 pairs and `lifecycle_transition` in 59 pairs. In gameoffer's release 0.9.0, three pairs repeat:

  | `type` | from → to | what tells the two apart |
  |---|---|---|
  | `lifecycle_transition` | the `OfferCoreEntity` lifecycle → state `active` | `from_state`: `draft` / `paused` |
  | `lifecycle_transition` | the `OfferCoreEntity` lifecycle → state `archived` | `from_state`: `active` / `paused` |
  | `entity_relation` | `OfferRequestCoreEntity` → `OfferRequestItemDetailEntity` | `field_name`: `offers` / `chosen_offer` |

- **A relation is its field.** AOA emits exactly one `entity_relation` edge per declared relation field, with one target (`EntityGraphEdge.get_entity_relation_edges`: "one typed edge per non-omitted entity relation declaration").
- **The rule of #285 holds on real graphs.** With the ids of this specification, the demo graph has no two edges with one id, and no node id in it or in gameoffer's graphs contains `|`. Comparing gameoffer's 0.8.0 and 0.9.0 by these ids gives edges **+34 −1 ~9**; without ids the same edges look like +43 −10, because nine `entity_field` edges that only changed their `ordinal` appear as removed and added.
- **Who reads the export in this repository.** Maxitor's graph build reads named fields of each edge and ignores the rest. The JSON schema in `graph_json_schema.json` (read by `graph_json_schema.py`) pins `schema_version` to `"1.0"` and forbids any edge field it does not list (`link_row`: `additionalProperties: false`), and several tests validate payloads written as `"1.0"`. The MCP adapter writes its own simplified graph for MCP clients (`_build_graph_json`: `from`, `to`, `type`), which is not this export.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The same edge is recognised in two versions of a graph (Priority: P1)

Whoever compares two exports of a graph — the comparison of #287, the history gateway, Maxitor — matches every edge of one with the same edge of the other by its id. An edge whose properties changed keeps its id, so it shows as changed, not as one edge removed and another added. A relation field that starts pointing at another entity is still the same relation.

**Why this priority**: This is the reason the issue exists: without an identity, a comparison of edges is guesswork, and every later step of #273 builds on it.

**Independent Test**: Export the demo graph; check that every edge has an id and that no two share one. Build two graphs that differ only in an edge's properties, and two that differ only in a relation's target entity; the edge keeps its id across each pair.

**Acceptance Scenarios**:

1. **Given** any built graph, **When** it is exported, **Then** every edge carries an `id` and no two edges share one.
2. **Given** two lifecycle transitions into one state from two different states, **When** the graph is exported, **Then** their ids differ.
3. **Given** two relation fields of one entity that point at the same other entity, **When** the graph is exported, **Then** their ids differ.
4. **Given** a relation field whose target entity is different in two builds, **When** both are exported, **Then** the relation has the same id in both.
5. **Given** an edge whose properties differ between two builds (for example a field's position), **When** both are exported, **Then** the edge has the same id in both.

---

### User Story 2 - A graph whose edges cannot be told apart is refused (Priority: P1)

A developer adds an edge type that can repeat between the same two nodes but forgets to say what tells the repeats apart. The build fails at once, and the message names both edges, instead of producing a graph whose versions can no longer be compared.

**Why this priority**: The id is only an identity if it is unique; a silent duplicate would make every later comparison wrong without anyone noticing.

**Independent Test**: Build a graph in which two edges get the same id; the build is refused with an error that names both. Build a graph with a node id containing `|`; the build is refused with an error that names the node.

**Acceptance Scenarios**:

1. **Given** a graph in which two edges get the same id, **When** it is built, **Then** the build is refused with a duplicate-edge error that names both edges.
2. **Given** a node id or a value used in an id that contains `|`, **When** the graph is built, **Then** the build is refused and the error names the node or the edge.
3. **Given** a graph with no such problem, **When** it is built, **Then** it builds as before.

---

### User Story 3 - Files written before the change still compare (Priority: P2)

Someone holds graph files exported before this change, such as gameoffer's six saved snapshots. Their edges have no `id`. A reader computes, from each edge as it is written, exactly the id the new export would give it, so old and new files compare edge by edge.

**Why this priority**: The history of #273 starts from snapshots taken before ids existed; without this, the oldest versions could not be compared with the newer ones.

**Independent Test**: For every edge of the demo graph, compute the id from the exported row with its `id` removed, and compare it with the `id` the export wrote.

**Acceptance Scenarios**:

1. **Given** an exported edge row without `id`, **When** the public function computes its id, **Then** the result equals the `id` the export writes for that edge.
2. **Given** a row of a type whose id needs a property that the row lacks, **When** its id is computed, **Then** the computation fails with an error that names the type and the missing property.

---

### User Story 4 - A stable, self-describing export (Priority: P3)

The export says which format it is in, and the same code always exports the same bytes, so a graph file under version control changes only when the graph does.

**Why this priority**: It makes the graph file of #286 diffable and the format checkable, but nothing is lost if it lands after the ids themselves.

**Independent Test**: Export the demo graph twice and compare the bytes; validate the export against the published JSON schema.

**Acceptance Scenarios**:

1. **Given** the same code, **When** the graph is exported twice, **Then** the two exports are byte for byte the same.
2. **Given** an export, **When** its edges are read in order, **Then** they come in the order of their ids.
3. **Given** an export, **When** it is validated against the published JSON schema, **Then** it passes, `schema_version` is `"1.1"`, and an edge without `id` would fail.

### Edge Cases

- A new edge type that can repeat between the same two nodes but declares nothing extra: the duplicate check refuses the build (User Story 2).
- The same source, target and properties under two different types: the type is part of the id, so the ids differ.
- A graph with no edges: the export is valid and empty.
- Generalization edges (`parent_action`, `parent_role`, `parent_domain`, `parent_entity`) and every other type without a special rule: the default rule applies.
- A lifecycle transition is exported both from its lifecycle and from the state it leaves: the two have different sources, so different ids.
- A 1.0 row of a type with a special rule that lacks the property the rule needs: the computation fails loudly rather than guessing (User Story 3, scenario 2).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Every edge in the graph export MUST carry an `id`.
- **FR-002**: By default an edge's id MUST be `<source_id>|<type>|<target_id>`.
- **FR-003**: An `entity_relation` edge MUST be identified by its field instead of its target: `<source_id>|entity_relation|<field_name>`. A relation whose target entity changes keeps its id.
- **FR-004**: A `lifecycle_transition` edge MUST append its `from_state` to the default id: `<source_id>|lifecycle_transition|<target_id>|<from_state>`.
- **FR-005**: Each edge type MUST declare its rule together with the way it exports itself, so the rule for a type lives with that type.
- **FR-006**: The id MUST be computed only from fields the edge already exports, by one public function that takes an exported edge row and returns its id; the export MUST use that same function.
- **FR-007**: The function MUST accept a row written before this change (no `id`, `schema_version` `"1.0"`) and return the id the new export would write; a row that lacks a property its type's rule needs MUST raise an error naming the type and the property.
- **FR-008**: The build MUST refuse a graph in which two edges have the same id, with a new error type for duplicate edges whose message names both edges, the way duplicate nodes are refused today.
- **FR-009**: The build MUST refuse a node id, or a property value used in an id, that contains `|`, naming the node or the edge.
- **FR-010**: Edges MUST be exported in the order of their ids, and two exports of the same graph MUST be byte for byte the same.
- **FR-011**: The export MUST write `schema_version` `"1.1"`, and the published JSON schema MUST describe it: `id` required on every edge, unknown fields still forbidden.
- **FR-012**: The readers of the export in this repository MUST keep working unchanged on a 1.1 export: Maxitor builds the same diagrams from it.
- **FR-013**: The change MUST end with the check run taken to zero, the documentation and the changelog, in that order (Principle VI): the documentation shows the id rule, each special rule, both refusals and how a reader computes ids for an older file, each as a runnable script and a notebook.

### Key Entities *(include if feature involves data)*

- **Edge id**: a readable string that names an edge uniquely within one graph and stays the same for the same edge across builds and versions. It is made of the edge's source, its type and either its target or a member that names it, separated by `|`.
- **Edge rule**: what an edge type adds to or puts in place of the default id — none for most types, the field name for `entity_relation`, the state it leaves for `lifecycle_transition`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The demo graph exports with an id on 100 % of its 4841 edges and no id used twice; each of the 61 repeating pairs (2 `entity_relation`, 59 `lifecycle_transition`) gets two different ids.
- **SC-002**: For 100 % of the demo graph's edges, the id computed from the exported row without `id` equals the written `id`.
- **SC-003**: Comparing gameoffer's 0.8.0 and 0.9.0 snapshots by these ids gives edges +34 −1 ~9 (checked by hand; the result goes into the pull request).
- **SC-004**: Two exports of the same code are byte for byte the same.
- **SC-005**: Every diagram Maxitor builds from the demo graph is the same before and after the change.
- **SC-006**: A graph with two edges of one id fails to build, and the message names both edges.

## Assumptions

- The ids are meant to be read by people, in a comparison and in an error message; their length is not limited.
- `|` is a safe separator: no node id in this repository's demo graph or in gameoffer's graphs contains it, and the build refuses one that does (FR-009).
- Only `entity_relation` and `lifecycle_transition` need a special rule today (checked on the demo graph and on gameoffer); any other type that turns out to repeat is caught by the duplicate check and gets its rule then.
- The MCP adapter's own simplified graph for MCP clients is a different format and is not changed here.
- Comparing two graphs — statuses and differences — is #287; this issue only gives edges their identity.
- A file of format 1.0 is read by computing ids (FR-007); the published JSON schema describes the current format, 1.1.
