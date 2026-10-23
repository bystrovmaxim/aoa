# Contract: the reference reaches the graph and the ERD

**Feature**: `specs/018-dictionary-reference` | **Plan**: [../plan.md](../plan.md) | **Data model**: [../data-model.md](../data-model.md) | **Research**: [../research.md](../research.md)

The model declares a reference; this contract fixes what the published graph and the ERD carry, and how the two stay one fact projected twice.

## 1. The graph edge

| Aspect | Rule |
| --- | --- |
| Type | `entity_reference` |
| Relationship | `association` |
| Source | the host entity |
| Target | the dictionary entity |
| `is_dag` | `false` |
| Properties | `field_name` (the field that declares the reference), `cardinality` (`one`) |
| Count | exactly one edge per accepted dictionary reference |
| Carrier | the reference is found by walking edges; a column property alone is not the carrier |

The edge's target is always a node of the same published graph: a dictionary without a node is refused by the declaration rule before the graph is wired.

## 2. The field row

| Aspect | Rule |
| --- | --- |
| Row | one `entity_field` per accepted reference, as today |
| `reference_qualname` | present, naming the same dictionary the edge targets |
| `field_type` | the annotation, rendered as today |
| Coexistence | the row and the edge describe the code column and the link; neither replaces the other |

## 3. The ERD payload

One entry in the slice's `relations`, beside the relation and generalization entries:

```json
{
  "source": "shop.OfferCoreEntity",
  "target": "shop.RegionEnumEntity",
  "label": "region",
  "relationship_kind": "reference",
  "source_cardinality": "one",
  "target_cardinality": "zero_many"
}
```

| Rule | Statement |
| --- | --- |
| Payload schema | unchanged: `relationship_kind` is a free string and both cardinals are already enumerated values |
| Renderer | unchanged: any kind other than `specialization` becomes an arrow with its label |
| Printed text | the row prints `→ RegionEnumEntity`; the arrow label is `region`; the same text is not printed twice |
| Dictionary card | keeps #249's shape — no `code` row, no `display_name` row, no code cell in a value row, the code in a tooltip |
| Non-dictionary cards | unchanged |

## 4. Slices and neighbours

| Rule | Statement |
| --- | --- |
| Same domain | the dictionary is selected with its domain; the arrow resolves |
| Other domain | with `include_one_hop_neighbors`, the referenced dictionary joins the slice through the reference table; without it, the reference stays unresolved rather than pointing at a card the slice did not include |
| Legacy graph | a graph that carries the reference only as `reference_qualname` still renders; no rebuild is required |

## 5. The Maxitor resource

| Rule | Statement |
| --- | --- |
| Table | `entity_reference_edges(source_id, target_id, relationship, is_dag, field_name, cardinality)` |
| Registry | `entity_reference` is a known edge type; an unknown one still raises `KeyError` |
| Union view | the edges view includes the table |
| Why it ships with the edge | `DuckDBGraphResource.build_from_json()` refuses an edge type it does not know, and the demo graph already carries dictionary references |

## 6. What the graph does not carry

| Not carried | Why |
| --- | --- |
| `description` on the edge | the field carries its own description; a relation's description is a relation concept |
| `inverse`, `has_inverse`, `deprecated` | a reference declares neither an inverse nor a lifecycle |
| `relation_type` | the edge type is the relation type |
| A second node for the value | values stay inside the dictionary node's `properties.values`, as #244 decided |
