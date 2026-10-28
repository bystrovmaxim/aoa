<p align="center">
  <img src="https://raw.githubusercontent.com/bystrovmaxim/aoa/main/docs/assets/aoa-logo.png" alt="AOA" width="540"><br><br>
  <img src="https://img.shields.io/badge/version-1.1-informational" alt="Version 1.1">
  <img src="https://img.shields.io/badge/status-stable-brightgreen" alt="Stable">
  <a href="https://json-schema.org/draft/2020-12"><img src="https://img.shields.io/badge/JSON_Schema-2020--12-blue" alt="JSON Schema 2020-12"></a>
  <a href="https://github.com/bystrovmaxim/aoa/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-Apache_2.0-blue" alt="Apache-2.0"></a>
</p>

# Open Gnomon Protocol

**One open language for what a software project *is* — its domains, entities, actions and the dependencies between them — produced by the code itself, checked by a schema, and kept in the repository next to the code it describes.**

## Why

Every team carries a model of its system: which actions exist, what they depend on, which entities they touch, who may call them. Today that model lives in people's heads, in wiki pages and in diagrams drawn by hand — and all three drift from the code the day after they are written. Every tool that wants the model — a visualiser, an architecture check, a coding agent — has to reverse-engineer it from source again, each in its own way.

The Open Gnomon Protocol makes the model a first-class artifact:

- **The code produces it.** A service exports its own model; nobody draws or maintains it by hand, so it cannot drift.
- **Everyone reads the same thing.** A person, a viewer and an agent read one document and agree on what an entity, an action or a dependency is, because the protocol defines those words. None of them has to import or run the project.
- **It changes where the code changes.** The description is a file in the repository. A pull request that adds a dependency also adds an edge, and the reviewer sees both. Git holds the model's whole history.
- **It is checked, not trusted.** Every version has a JSON Schema. A document is a graph of that version if and only if it passes it.

## What it looks like

"Placing an order requires checking stock" — two actions and the dependency between them:

```json
{
  "schema_version": "1.1",
  "nodes": [
    {"id": "shop.PlaceOrder", "type": "Action", "label": "Place order",
     "properties": {"description": "Place a customer order."}},
    {"id": "shop.CheckStock", "type": "Action", "label": "Check stock",
     "properties": {"description": "Check that ordered items are available."}}
  ],
  "edges": [
    {"id": "shop.PlaceOrder|@depends|shop.CheckStock",
     "source_id": "shop.PlaceOrder", "target_id": "shop.CheckStock",
     "type": "@depends", "relationship": "Serving", "is_dag": true,
     "properties": {"description": "Check availability before placing the order."}}
  ]
}
```

A real service is the same document at scale: the AOA demo describes itself in 3 213 nodes and 4 841 edges. When its model changes, the difference between two revisions is precise and readable:

```text
nodes[id=aoa.demo.model.store.store_domain.StoreDomain].label: Shop → StoreDomain
edges[id=aoa.demo.model.telemetry_pipeline.telemetry_pipeline_domain.TelemetryPipelineDomain|application|aoa.action_machine.application.application.Application]: added
```

## Specification

| | |
|---|---|
| **Version** | `1.1` — [graph/1.1.json](graph/1.1.json) |
| **Status** | Stable. A published version never changes. |
| **Normative schema** | JSON Schema 2020-12, one file per version in [graph/](graph/) |

The key words **MUST**, **MUST NOT**, **SHOULD** and **MAY** are to be read as in [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119). The schema is normative; the tables below summarise it.

### 1. The graph document

One JSON object with exactly three members:

| Member | Requirement |
|---|---|
| `schema_version` | The protocol version the document follows. It MUST name a published version. |
| `nodes` | The model's elements. Each MUST have an `id` unique among the nodes. |
| `edges` | The relationships between them. From `1.1` on, each MUST have an `id` unique among the edges. |

| A node has | Meaning | | An edge has | Meaning |
|---|---|---|---|---|
| `id` | its stable identity | | `id` | its stable identity (from `1.1`) |
| `type` | its kind (§2) | | `source_id`, `target_id` | the nodes it joins |
| `label` | a human-readable name | | `type` | its kind (§2) |
| `properties` | facts about it, by `type` | | `relationship` | its nature (§2) |
| | | | `is_dag` | `true` for the acyclic slice: those edges MUST form no cycle |
| | | | `properties` | facts about it, by `type` |

A document is a graph of version *V* if and only if it declares `"schema_version": "V"` and is valid against [graph/*V*.json](graph/).

### 2. Vocabulary of version 1.1

| | Kinds |
|---|---|
| **Node types** (23) | Structure: `Application` `Domain` `Resource` `Role` · Behaviour: `Action` `Params` `Result` `Field` `PropertyField` `RegularAspect` `SummaryAspect` `Compensator` `AccessDecide` `ErrorHandler` `Checker` `RequiredContext` · Data: `Entity` `EntityField` `Sensitive` · Lifecycle: `Lifecycle` `StateInitial` `StateIntermediate` `StateFinal` |
| **Edge types** (31) | Containment: `application` `domain` `field` `property` `entity_field` `entity_schema` `generic:params` `generic:result` `state` `sensitive` · Behaviour: `@regular_aspect` `@summary_aspect` `@compensate` `@access_decide` `@on_error` `@result_checker` `@check_roles` `@required_context` · Dependencies: `@depends` `@connection` · Data: `entity_relation` `entity_reference` `entity_specialization` `entity_view` · Generalization: `parent_action` `parent_role` `parent_domain` `parent_entity` · Lifecycle: `lifecycle` `lifecycle_contains_state` `lifecycle_transition` |
| **Relationships** (11) | `Access` `Aggregation` `Assignment` `Association` `Composition` `Flow` `Generalization` `Realization` `Serving` `Specialization` `Triggering` |

The 1.x vocabulary comes from [AOA](https://github.com/bystrovmaxim/aoa)'s model, the protocol's first producer. A producer built on another framework conforms by mapping its elements onto these kinds; a model that needs new kinds is a new version.

### 3. Versions and compatibility

| Version | Change |
|---|---|
| [`1.0`](graph/1.0.json) | The first shape: nodes have an `id`; edges do not. |
| [`1.1`](graph/1.1.json) | Every edge has an `id`, so two revisions compare edge by edge. |

- A published version MUST NOT change. A new shape is a new version and a new schema file; each schema's `$id` is its address in this folder.
- A consumer MUST check a document against the version it declares and MUST refuse a version it does not know, rather than guess. It SHOULD read every published version.

### 4. Identity

- A producer SHOULD derive every `id` from the code that declares the element, so the same model always yields the same ids and a changed element keeps its id.
- Two revisions MUST be compared by `id`, never by position: an element that only moved within its array is unchanged. Their difference is the elements added, removed, and changed under the same `id`.
- An `id` is opaque to consumers; the protocol does not prescribe its format.

### 5. The graph file

- A service keeps its graph in one file, conventionally `graph.json` in the service's folder.
- The file MUST hold the document and nothing else, in UTF-8, with object keys sorted, an indent of two spaces, non-ASCII characters as they are, and one newline at the end — `json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2) + "\n"`. The same document therefore always gives the same bytes. The formatting MUST NOT reorder `nodes` or `edges`.
- The file MUST be written by the service's build, never edited by hand. It SHOULD change in the same pull request as the code that changed the model, and CI SHOULD check that it is current.

### 6. The project configuration

A repository lists its graphs in `gnomon.toml` at its root ([config/1.0.json](config/1.0.json)):

```toml
gnomon = "1.0"                         # the configuration's own version

[[graph]]
name  = "shop"                         # unique
cwd   = "."                            # optional, default "."
build = "python -m shop.build_graph"   # prints the graph document, and only it
file  = "shop/graph.json"              # unique
```

- Relative paths start at the configuration's folder; absolute paths are allowed.
- A build MUST exit with 0 and print exactly one graph document; otherwise it produced no graph and nothing is written. Each graph MUST be built in a process of its own, so that two services' models never mix.
- The configuration's version is independent of the graph's.

### 7. Conformance

| Role | Conforms when it… |
|---|---|
| **Producer** | prints valid graphs of the version it declares, with ids derived from the model (§4). |
| **Consumer** | checks each document against its declared version, refuses unknown versions, and compares revisions by `id`. |
| **Repository** | lists its graphs in `gnomon.toml`, keeps each as §5 requires, and checks in CI that every file is current. |

## Implementations

| | Role |
|---|---|
| **[maxitor-gnomon](../README.md)** | Reference implementation: the `gnomon` command that writes and checks a repository's graph files, and the `gnomon-setup` skill that connects a project to the protocol. **Start here to use the protocol in your project.** |
| **[AOA](https://github.com/bystrovmaxim/aoa)** | Producer: every AOA service exports its model in this format. |
| **[Maxitor](../../aoa-maxitor/README.md)** | Consumer: draws the graph, its entity diagrams and lifecycles. |
