# Research: Lifecycle Diagram Comparison

All questions were settled from the code on 2026-11-01; none is open.

## R1. How a drawn element finds its status

- **Decision**: The lifecycle read adds `id` to each state (the node's id) and to each transition (the edge's id, read from the graph, not built by the client).
- **Rationale**: FR-002. A transition's id holds the state it leaves, the rule of #285, and that rule stays in one place. Today's read has neither id.
- **Alternatives**: Building ids in the client from `key` and `source`/`target`: a second copy of the rule, and wrong the day it changes.

## R2. How a version's lifecycle is read

- **Decision**: `fetchLifecycleFiniteAutomaton(id, read?)`, as `fetchDomainUseCaseDiagram` takes a read. `loadLifecycleDiff` reads the left panel of A and of B, and reads the lifecycle only from the versions that list it.
- **Rationale**: The read refuses an unknown lifecycle with an error. Asking first keeps a lifecycle of one version from being an error, the way `loadUseCaseDiff` asks `listDomains` first.
- **Alternatives**: Catching the refusal: a real failure would read as "not in this version".

## R3. What marks an element

- **Decision**: `compared.nodes[state.id]` and `compared.edges[transition.id]`, missing meaning unchanged. No "changed inside".
- **Rationale**: FR-005a; a state owns nothing undrawn. Every property counts (the maintainer's answer), and the comparison already works that way (spec 038, FR-003).

## R4. How DOT stays the same in One

- **Decision**: `buildLifecycleFsmDotSource` adds attributes only for an element that has `diff`; without `diff` the text is byte for byte today's, proved by a test against a recorded text.
- **Rationale**: FR-030, SC-008. A room compares layouts by that text.
- **Details**: A marked state uses `MARK_LOOK`'s colours; removed is dashed; the sign `+ − ~` stands in the label; the shape stays One's, with no second outline. Unchanged is grey and dim, not the declared colour (FR-005). Transitions get `id=` from `useCaseCellId`'s rule so that the stepper can reach them; only in Diff.

## R5. Entry and exit arrows

- **Decision**: Arrows are drawn from the union of initial and final keys. An arrow is green when its state is initial or final in B only, red in A only, otherwise grey. A dot is coloured only when every arrow on it has that one status. Kinds come from A's and B's states before they merge.
- **Rationale**: The mockup's green dot, and FR-009. They carry no id, so they stay out of `lifecycleChanges` and counts.

## R6. Hover

- **Decision**: `bindUseCaseHover` is generic already: it works on Graphviz titles. Reuse it unchanged; `litBy` treats the entry and exit dots as ordinary nodes.
- **Rationale**: FR-025. `useGraphvizFocus` stays for rooms, as on the use-case diagram.

## R7. The filter panel

- **Decision**: `ErdFilterPanel` with an Elements section of state kinds and, in Diff, Changes. `usePageSetting` holds the switches, as in `UseCaseDiagramViewer`. The kinds' disks take the palette of `paletteForStateType`. The gear shift stands in Diff between Elements and Changes, on Changes at first.
- **Rationale**: FR-020 – FR-024.
- **Details**: 1-hop uses the same walk as `withUseCaseOneHop`. Default keys stay out of the address, so One's untouched page keeps its address and its DOT.

## R8. `~` in the left panel

- **Decision**: `mergeSidebars` takes the comparison; a `lifecycle_state_diagram` row in both versions gets `changed: true` when a key of `compared.nodes` or `compared.edges` starts with `<lifecycle id>:`. The sidebar hook adds one read of the comparison, already held per pair.
- **Rationale**: FR-026a. A state's id and a transition's id both begin with the lifecycle's id and a colon, and the lifecycle node's own id does not, so a change of the node alone never marks it. Field names cannot collide because the colon ends the prefix.
- **Alternatives**: Reading every lifecycle: 201 reads for a mark.

## R9. A page with no lifecycle in the shown version

- **Decision**: In One, and in a pair where neither version lists it, the viewer shows the same message and way back as an absent domain, by asking the left panel before reading.
- **Rationale**: FR-028.

## R10. The stand

- **Decision**: New versions appended to `build_erd_full.py`'s list, last, on Inventory's lifecycles (12 there). The existing versions keep their commits, so the maintainer's links keep working.
- **Rationale**: The maintainer's decision. Every case of the spec's stand list is a change in one of those versions.
