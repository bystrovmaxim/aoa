# Data Model: Maxitor Compares Two Versions on the ERD

## The comparison (`maxitor.graph_compare`, standard library only)

| Entity | Fields | Rules |
|---|---|---|
| **Status** | `added` · `removed` · `changed` · `unchanged` (a `StrEnum`) | Exactly one per element of the union (FR-002). |
| **Change** | `added` · `removed` · `changed` | The kind of one difference. |
| **Difference** | `path: tuple[str, ...]`, `change: Change`, `before: JSON`, `after: JSON` | `path` starts at the element's top (`("label",)`, `("target_id",)`, `("properties", "json_schema", …)`); `before` is meaningful unless `change` is `added`, `after` unless `removed`. Objects are walked key by key; anything else, lists included, is one value. |
| **ElementComparison** | `status: Status`, `differences: tuple[Difference, ...]` | `differences` is non-empty exactly when `status` is `changed`. |
| **Counts** | `added`, `removed`, `changed` (ints) | Unchanged is not counted. |
| **Comparison** | `nodes: Mapping[str, ElementComparison]`, `edges: Mapping[str, ElementComparison]`, `node_counts: Counts`, `edge_counts: Counts` | Frozen; the keys of `nodes` are every node id of A and B, the keys of `edges` every edge id (computed for `1.0`, R5). |
| **GraphNotComparableError** | message naming the cause | Raised for an unknown `schema_version`, a document without `nodes`/`edges` lists, an element without a string `id`, two elements of one kind with one id, or a `1.0` edge whose id cannot be computed. |

`compare(a, b) -> Comparison` — A older, B newer, both parsed documents. Element fields compared: every field but `id`.

### Edge id rule (copied from #285)

| Edge `type` | Id |
|---|---|
| any | `<source_id>|<type>|<target_id>` |
| `entity_relation` | `<source_id>|entity_relation|<properties.field_name>` |
| `lifecycle_transition` | `<source_id>|lifecycle_transition|<target_id>|<properties.from_state>` |

## On Maxitor's server

| Entity | Fields | Rules |
|---|---|---|
| **GraphEntry** (existing) | + `document: str` | The graph's JSON text the entry was built from (R7). |
| **ComparisonStore** (new resource) | pairs `(sha_a, sha_b) → Comparison`, `last_read` | At most 32 pairs; computed once per pair under a lock; keyed by content, so a rebuilt Live gets a new pair (R9). |
| **Room** (existing) | + `version_a: str | None` | `None` in One. With `version` (B) it is the room's range; A older than B, never equal, never Live (R14). |

## On the client

| Entity | Fields | Rules |
|---|---|---|
| **HistoryRange** | `mode: "one" | "diff"`, `a: string | null`, `b: string` | In Diff, `a` is older than `b` by track order, `a ≠ b`, `a ≠ "live"`. Restored from `mode`, `a`, `b` in the address and from the room. |
| **CompareResult** | `counts`, `nodes: Record<id, Status>`, `edges: Record<id, Status>` | Only elements that are not unchanged are listed. |
| **ErdMark** | `diff?: Status` on `ErdEntity` and `ErdField`; on `ErdRelation`: `diff?`, `previous_target?` | `previous_target` is set when the edge's differences include `target_id` (R11). `ErdField` also gets `previous_type?` for `~~old~~ → new`. |
| **DiagramCounts** | `added`, `removed`, `changed` | Counted from the drawn ERD's marks, each element once. All zero → "no changes". |
| **SidebarMark** | `only?: "a" | "b"` on a sidebar page | `+` for `b`, `−` for `a` (R15). |

## State transitions of the range

```text
One(V) ──Diff──► Diff(A = previous(V), B = V)       (V oldest: A = V, B = next(V))
Diff(A, B) ──One──► One(B)
Diff(A, B) ──drag/step a handle to X──► Diff(min(X, other), max(X, other))   X = other ⇒ X moves one more in its direction
Diff(A, B) ──Shift+→──► Diff(next(A), next(B))      only when next(B) exists
Diff(A, B) ──A or B leaves the list──► the missing end moves toward the other; meeting ⇒ One(remaining)
```
