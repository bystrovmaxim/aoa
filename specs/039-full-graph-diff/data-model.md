# Data Model: Maxitor Compares Two Versions on the Full Graph

## Full graph answer (changed)

| Element | Field | Change |
|---|---|---|
| node | `data.type_slug` | new: DuckDB's `type` (R3) |
| edge | `id` | now the protocol's id, was `e-<index>` (R1) |

## Union payload (client)

`InterchangeGraphG6Payload` with:

- `nodes`: B's nodes, then the nodes only A has, sorted (R3); `data.diff?: "added" | "removed" | "changed"`.
- `edges`: the drawn edges of both by id, B's taking precedence, sorted; `data.diff?`; a retargeted edge's companion `<id>#was` has `data.was: true`.
- `legend_items`, `node_type_map`, `domain_color_map`: merged, B winning.
- `bubble_plugins`: rebuilt from the union.

An element with no `diff` is unchanged. An element's status comes from `CompareResult` only.

## Rules

- Every id occurs once; `#was` companions exist only for a changed edge whose target differs.
- A node in both takes B's `data`.
- An edge whose end is missing from its version's nodes is already dropped by the action.

## Filter set (page settings)

| Setting | Type | Default |
|---|---|---|
| `disabled_node_types` | `string[]` | `[]` |
| `disabled_domains` | `string[]` | `[]` |
| `disabled_changes` | `string[]` | `[]` (Diff only) |

A node is shown when its type is on, its change is on, and it is in no domain or in at least one domain that is on. An edge is shown when both ends are.

## Diagram counts

`{added, removed, changed, edgesMarked}`: the shown nodes per status, and whether a shown edge is marked. "No changes" is all three zero and `edgesMarked` false.
