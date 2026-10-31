# Data Model: Comparison on Use-Case Diagrams

## ChangedPart

One changed thing inside an action.

| Field | Meaning |
|---|---|
| `kind` | `node` or `edge` |
| `id` | The element's protocol id |
| `label` | A node's label; for an edge, its target's label |
| `type` | The node's or edge's type |
| `group` | The first step of the walk: `Params`, `Result`, the aspect's label, or `Links` |
| `status` | `added`, `removed` or `changed` |
| `differences` | For `changed`: as the comparison gives them |

## ChangedInside

`{action id: ChangedPart[]}`, for each action found in both versions with at least one changed part, in a defined order (group, then label, then id).

**Rules**

- An action added or removed is not in it.
- A part walked from either version: a part only in A is found by walking A.
- A shared `Result` appears under each action.
- A cycle cannot loop: a node is walked once per action.

## Use-case link

The existing edge gains `id`: its protocol id.

## Diagram marks (client)

`diff` on actions, roles and links: `added`, `removed`, `changed` or `unchanged`. An action is `changed` when the comparison says so or when it is in ChangedInside; `added` and `removed` always stand.

**Union order**: actions, roles and links sorted by id, so a pair has one DOT text however it was read.
