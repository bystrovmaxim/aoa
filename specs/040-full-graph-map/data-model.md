# Data Model: Maxitor's Full Graph as a Map

## Stored on the server

| Thing | Key | Holds |
|---|---|---|
| Area layout | hash of the area's content | each element's position inside the area, and the area's radius |
| Places | the history, or the source for a graph with no history | area id → centre and reserved radius |
| Map of a version | the version | its areas, bundles and counts |
| Map of a pair | A and B | the same, plus statuses, whole and per area |

Stored through a resource; what is stored survives a restart (FR-015). A layout refused by the rule below is not stored.

## Area

- `id`: the domain's id, or `(outside)`.
- `name`, `colour`, `x`, `y`, `radius`.
- `counts`: nodes by type.
- In a pair: `status` (`added`, `removed` or none) and `changes`: nodes by type and status.
- `sketch`: a coarse grid over the area, each cell counting its nodes by type and, in a pair, by status; outlines at the far level are drawn from it.

## Levels of a node

| Level | Types |
|---|---|
| 1 | the area itself |
| 2 | `Entity`, `Action`, `Role`, `Resource`, `Domain`, `Application` |
| 3 | everything else |

## Home of a node

A node's domains come from the rule the client uses today: linked to the domain, or contained by something that is. Its home is the first of them in the domains' order; a node in none is in `(outside)`. A node in several domains is listed in the overview's `shared` with all of them, so the filters can count it exactly.

## Rules

- Inside an area, positions depend only on the area's content (clarification).
- An area keeps its place across versions; it moves only when it outgrows its reserved radius.
- In a pair, positions are B's. An element only in A stands at A's position inside its area, or beside its neighbours when that place is taken.
- The panel's counts come from the overview, never from what the browser has loaded.

## State in the browser

| State | Rule |
|---|---|
| Area | folded, reading, unfolded to level 2, unfolded to level 3 |
| Loaded detail | near the view; the rest is let go, about 3 000 nodes in all |

## Page settings

`disabled_node_types`, `disabled_domains`, `disabled_changes` (all lists), `paint` and `paint_diff`, in the address and the room as on the ERD.
