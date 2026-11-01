# Research: Side by Side

## R1. How a viewer learns it is a half

- **Decision**: a React context `HalfContext` (`null` outside Side by side), with `side`, `read` and the pair. `graphFetch` already accepts a source, so readers take the half's read explicitly.
- **Rationale**: `activeSource` and `activeBase` are module values; two viewers reading at once would race.
- **Alternatives**: swapping the active source around each read (a race); iframes (no shared hover, double memory).

## R2. What a half draws

- **Decision**: the comparison already builds a merged drawing with a status per element. A half projects it: A drops `added`, B drops `removed`, and every changed element takes its own version's value. Invariant, tested: a half's layout equals One's layout of that version with the same settings.
- **Rationale**: marks, cards and counts stay one code path; the invariant keeps FR-002 honest.
- **Alternatives**: read each version alone and paint from the comparison's ids: loses field-level marks already computed.

## R3. Settings of a half

- **Decision**: `usePageSetting` under a half maps `layout` to `layout_a` or `layout_b`; every other name stays shared. Each starts from the page's `layout`.
- **Rationale**: rooms, seeding and the address then work unchanged, once the names are allowed by `setting_error`.

## R4. Selection

- **Decision**: a page setting `selected` (an element ref or null), not in the address.
- **Rationale**: absolute values, last wins, newcomers get it, shared with everyone: exactly FR-032, with no new action. The `focus` selection stays what it is.
- **Alternatives**: a room field and action: a second copy of the same mechanics.

## R5. Hover across halves

- **Decision**: a half's hover goes through the path that already replays a followed person's hover (`useGraphvizFocus`, `MapEngine`). The other half replays it as a followed hover.
- **Rationale**: spec 043 made own and followed hover one path; no card opens from a replay (FR-015).

## R6. Counts and the stepper

- **Decision**: half B owns `diffCounts` and the stepper, with the pair's full list of changes, removed included. A step sets `selected`.
- **Rationale**: the stores hold one value by design, and a pair has one.

## R7. Surfaces, pointers, positions

- **Decision**: surfaces are registered per side. `useDiagramSurface` keeps returning the single surface outside Side by side. `pointer`, `click` and `viewport` carry an optional `half`.
- **Rationale**: diagram coordinates differ between halves, so a point means nothing without its half.

## R8. The room's check

- **Decision**: in Side by side the tab reports `layout_hash` = hash(hash A + hash B) and `settings_digest` = hash(digest A + digest B + sha A + sha B). In Diff the digest takes in the two sha as well. The comparison answer gains `sha_a` and `sha_b`, which the server's comparison store already knows.
- **Rationale**: the server keeps comparing two strings per page.

## R9. The view of a room

- **Decision**: `Room.view` is `one`, `diff` or `split`; the existing `version` message and `SetRoomVersionAction` carry it, and `JoinRoomAction` takes it. `split` needs `a`. A message without `view` means `diff` with `a`, `one` without.
- **Rationale**: A, B and the view move together, so one message keeps them consistent.

## R10. Filter panel and toolbar

- **Decision**: one filter panel for the workspace; each half has a head with its version, layout mode and zoom, as in the mockup.

## R11. Full graph drawn twice

- **Decision**: each half has its own `MapEngine`; `keptView` becomes one per side, and the map data of each version is read once. Half A's work starts after half B has drawn.
- **Rationale**: FR-002 needs two maps; SC-005 is measured with `measure-map.ts`.
