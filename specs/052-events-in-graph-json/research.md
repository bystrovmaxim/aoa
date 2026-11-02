# Research: Events in the graph and its JSON

## 1. Which events get a node

**Decision**: An inspector on the `BaseEvent` axis whose `_get_node` returns a node only for an event named in some `events` or `@emits` of a class in the graph.

**Rationale**: The mode table says mode 1 has no `Event` nodes. The other inspectors emit every loaded subclass, so a plain copy would give a node to an event nobody declares. Inspectors already run once per axis, so one event gets one node however many refer to it.

**Alternatives**: Companion nodes of methods and domains: rejected, because `_expand_and_collect` must then accept one node from many owners. All subclasses: rejected, it breaks the table.

## 2. System fields

**Decision**: `FieldGraphEdge.get_field_edges` is left alone; `EventGraphNode` drops the edges of the system fields by name, from a constant `base_event.py` exports.

**Rationale**: The builder reads `model_fields`, which holds `level`, `channels`, `domain` and `domain_name`, and it is shared with `Params` and `Result`.

**Alternatives**: Skip every `exclude=True` field in the shared builder: rejected, it could change `Params` and `Result` documents.

## 3. Edge natures and ids

**Decision**: `domain_event` is an Aggregation; `@emits` is an Association. Both have empty properties and `is_dag` false. Both use the default id `<source>|<type>|<target>`, so no rule in `EDGE_ID_RULES` is needed.

**Rationale**: A domain's vocabulary holds its events, as an application holds domains. A method names an event and does not own it, and one event has many emitters. The default id is stable, and the pair is unique because `@emits` lists are distinct per method.

**Consequence**: The map places a node by containment, so an event of mode 3 stands in its domain, and a mode 2 event with no vocabulary stands in `(outside)`. This is how the map treats anything without a domain; #335 decides how events are shown.

## 4. `typed_events`

**Decision**: `hasattr(domain_cls, "events")`, the same test the runtime and the validator use.

**Rationale**: It covers inherited and empty vocabularies with one rule. `getattr(domain_cls, "events", ())` gives the `domain_event` edges.

## 5. Maxitor needs real support

**Finding**: Maxitor does not ignore a new type. `_assert_no_unknown_graph_types` refuses it, and nodes go into typed DuckDB tables. So "no temporary code" means no filter and no styling, but the store needs an `event` table and the known-type lists, and `list_node_types_action.py` needs the slug. These stay for #335. The colour stays the default one.

**Unchecked until phase 3**: the ERD, lifecycle and use-case queries select their own tables, so they should be untouched; phase 3 confirms this with a test on a `1.3` document.

## 6. Build check

**Finding**: `emits_vocabulary_validator.py` from #333 covers the rule, for the five kinds, by exact class, and names action, method, event and domain. `test_emits_vocabulary_validator.py` already runs the five kinds. No code change; phase 2 adds the message, the subclass and mode 2 to that file.

## 7. Schema files live in three places

**Finding**: `aoa-action-machine` holds a copy of the current schema as `graph/graph_json_schema.json`, kept byte for byte by `tests/scripts/test_schema_copies.py`; it changes in phase 2, with the version the document writes. `graph_builder/schemas/` holds a copy of each schema; `1.3.json` is added there in phase 3 with `SCHEMA_VERSIONS`. `KNOWN_VERSIONS` in `compare.py` is a separate list.
