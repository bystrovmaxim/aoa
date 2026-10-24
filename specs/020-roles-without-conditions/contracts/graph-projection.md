# Contract — Graph Projection

**Feature**: [spec.md](../spec.md) | **Plan**: [plan.md](../plan.md) | **Data model**: [data-model.md](../data-model.md)

What the interchange graph says about access after this change, and what it no longer says.

## Role edges

| Item | Contract |
| --- | --- |
| Edge name | `@check_roles` (unchanged) |
| Direction | `Action → Role`, `is_dag=False` (unchanged) |
| Cardinality | one edge per **distinct** declared role, in declaration order |
| Duplicate declaration | `@check_roles((A, A))` produces one edge, and no duplicate-node failure |
| Condition data | none: no `when`, no `when_reason`, no callable anywhere on the edge |
| Exported `properties` | `{}` (unchanged from today's wire form) |
| Role node | one node per role, shared across actions, carrying its `role_mode` |

## Action node

| Property | Before | After |
| --- | --- | --- |
| `description` | from `@meta` | unchanged |
| `guard` | the removed shared condition | absent |
| `guard_reason` | the removed shared reason | absent |

Nothing replaces them. An operation's access rule beyond the roles is a separate node, not a
property of the action.

## AccessDecide node

| Item | Contract |
| --- | --- |
| Presence | the operation declares an object rule; absent otherwise, and the absence is the statement that there is none |
| Content | the declared description, and the `RequiredContext` companions naming the fields the rule reads (`user.user_id`, `user.roles`, …) |
| Edges | the existing `@access_decide` edge from the action (unchanged) |
| New marker | none is added; this node is the graph's way of saying where authorization lives |

## Maxitor

No change is required and none is made. Maxitor already models `AccessDecide` as its own node type
with its own table and edges, reads node properties generically, and names no gate word anywhere in
its Python or TypeScript sources. The one thing to keep true is that removing `guard` and
`guard_reason` from the action node leaves the payload valid: no schema in Maxitor requires them.

## Where the contract is asserted

- `packages/aoa-action-machine/tests/action_machine/graph/edges/test_role_graph_edge.py` — one edge
  per distinct role, no condition data, exported properties empty.
- `packages/aoa-action-machine/tests/action_machine/graph/nodes/test_action_graph_node.py` — the
  action node carries no condition and exposes the `AccessDecide` node when one exists.
- `packages/aoa-maxitor/tests/test_duckdb_access_decide_type.py` — the `AccessDecide` node still
  reaches DuckDB and the payload still validates.
