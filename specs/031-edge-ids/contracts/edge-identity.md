# Contract: Edge Identity

The public surface this feature adds to `aoa-action-machine`. Everything else stays as it is.

## `aoa.action_machine.graph.edge_identity`

```python
EDGE_SEPARATOR: str  # "|"

@dataclass(frozen=True)
class EdgeIdRule:
    member: str | None = None   # property that names the edge in place of its target
    suffix: str | None = None   # property appended to the id

EDGE_ID_RULES: Mapping[str, EdgeIdRule]   # edge type → its rule; types not listed use the default

def edge_id(row: Mapping[str, Any]) -> str: ...
```

`EDGE_SEPARATOR` and `EdgeIdRule` are defined in `aoa.action_machine.graph.core.edge_id_rule` and re-exported here.

### `edge_id(row)`

- **Input**: one edge row as the graph export writes it — format 1.0 (no `id`) or 1.1 (an `id` present, which is ignored).
- **Output**: `<source_id>|<type>|<target>[|<suffix>]`, as described in [data-model.md](../data-model.md).
- **Raises `ValueError`** when the row lacks `source_id`, `type` or `target_id`; when the property its type's rule needs is missing, empty or not a string; or when any part of the id contains `|`. The message names the type and the field.
- **Pure**: the same row always gives the same id; nothing is read beyond the row and `EDGE_ID_RULES`.

## Edge classes

```python
class EntityGraphEdge(AssociationGraphEdge):
    EDGE_TYPE: ClassVar[str] = "entity_relation"
    ID_RULE: ClassVar[EdgeIdRule] = EdgeIdRule(member="field_name")

class StateGraphEdge(CompositionGraphEdge):
    EDGE_TYPE: ClassVar[str] = "lifecycle_transition"
    ID_RULE: ClassVar[EdgeIdRule] = EdgeIdRule(suffix="from_state")
```

Each passes `edge_name=self.EDGE_TYPE` to its base. No other edge class declares a rule.

## `aoa.action_machine.graph.core.exceptions.DuplicateEdgeError`

```python
class DuplicateEdgeError(ValueError):
    edge_id: str
    first: str    # "<source_id> -[<type>]-> <target_id>" plus the rule's property
    second: str
```

Raised by `NodeGraphCoordinator.build()` when two edges of one graph get the same id.

## `NodeGraphCoordinator`

- `build()` also raises `DuplicateEdgeError` (above) and `InvalidGraphError` for a node id containing `|` or an edge whose rule property is missing, empty, not a string or contains `|`.
- `to_json()` writes `schema_version` `"1.1"`, an `id` on every edge, edges in `id` order. Everything else in the export is unchanged.

## `GRAPH_JSON_SCHEMA`

- `schema_version`: `"1.1"`.
- `link_row`: `id` added — `{"type": "string", "minLength": 1}`, required; `additionalProperties: false` kept.
