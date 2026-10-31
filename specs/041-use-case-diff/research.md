# Research: Comparison on Use-Case Diagrams

## R1. What counts as a part

- **Decision**: from an action, follow its outgoing edges the diagram does not draw. Every such edge counts. The walk goes on through an edge only if its `relationship` is `Composition`, or it is `generic:params` or `generic:result`. Drawn and therefore not followed: `@check_roles`, `@depends` to an action, `parent_action`.
- **Rationale**: the protocol's own `relationship` says what is owned, so no list of node types is kept: a new kind of aspect is covered by itself. `generic:*` are `Aggregation` because a result may be shared, yet the issue names them. `domain`, `@connection` and `@depends` to a resource count as links and stop at the target. `entity_schema` is `Aggregation`, so entities are not entered.
- **Alternatives**: a list of node types (goes stale); every reachable node (crosses into entities and other actions).

## R2. Where the walk runs

- **Decision**: a pure function in `graph_compare` over both documents and the `Comparison`, called by `ComparisonStore` once per pair, in the thread that compares.
- **Rationale**: the store already holds pairs by content, so a rebuilt Live is a new pair (FR-014), and marks, counts, card and stepper read one answer (FR-024).
- **Alternatives**: in the client (spec forbids: FR-024); a second store (two caches of one pair).

## R3. Where the union is made

- **Decision**: in the client: read the diagram of A and of B, merge. The same as `loadErdDiffBundle`.
- **Rationale**: the action builds a diagram from one version's DuckDB graph, and its closure over parents and dependencies differs per version. The union of two closures is the union of two answers. A domain found in one version answers "unknown" from the other, and that side counts as empty.
- **Alternatives**: a server action reading two DuckDB graphs (a second way to build a diagram).

## R4. Matching links

- **Decision**: the diagram's answer gives each link its protocol id, `<source>|<type>|<target>`, the rule of #285 for these types. A test proves it against the graph file's ids for every use-case edge.
- **Rationale**: the demo's graph has no exception (checked 2026-10-31, `@depends` included).

## R5. Counts and stepper order

- **Decision**: counted and listed in the client from the drawn union, as on the ERD: actions and roles sorted by label, then links by kind and ends.
- **Rationale**: the whole diagram is always loaded, unlike the map, which is why spec 040 needed a server list.

## R6. Reuse of the viewer logic

- **Decision**: the ERD's stepping logic lives inside `ErdGraphvizCanvas`. Extract it into one hook, `useGraphvizChangeStepping`, used by both.
- **Rationale**: two copies of positions, mirroring and centring would drift; room behaviour (FR-019) comes along for free. The extraction is a refactor of the ERD, so SC-005 and the existing tests guard it.

## R7. The panel without kinds

- **Decision**: `ErdFilterPanel` with an empty `kindRows`, its section not rendered; `paint` over `domains` and `changes`.
- **Rationale**: FR-020. Whether the panel can hide its kinds section is checked at implementation; if not, a small prop.
