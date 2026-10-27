# Research: Maxitor Rooms Polish

Phase 0 of [plan.md](plan.md). Each decision starts from what the code does today (checked 2026-10-27).

## R1. Where a room's page settings come from

- **Today**: `usePageSetting` reads *room → own → default*; nothing sends the opener's own values to a new room, so opener and guest diverge (spec, Context).
- **Decision**: (a) Inside a room the client reads the room's value, else the default — never the person's own value. (b) Right after the welcome of a room it *opened* (`room=new`), the client sends one `seed` message per setting it holds an own value for: `{type: "seed", page, values: {name: value}}`, one setting per message; a value whose message would exceed 4 KB is not sent and that setting starts at its default. A new action, `SeedPageSettingsAction`, applies each value only where the room has none yet (so a change someone made meanwhile wins), accepts it only from the room's creator, and broadcasts each applied value as the ordinary `setting` event. (c) Leaving keeps the room's values as one's own (unchanged, spec 028 FR-019).
- **Rationale**: one setting per message keeps every message far below the 4 KB limit except a very long `disabled_entities` list, which is skipped rather than allowed to close the connection with `4413`; the "only where empty" rule makes seeding safe against a guest who changed something in the first second; the change goes through an action, so it is logged like every other setting.
- **Alternatives**: seed values in the join query (URL length, and a query is logged by proxies); the opener sends ordinary `setting` messages (would overwrite a guest's change, and a page with many values could hit the 40/s limit).

## R2. Sharing hover, tooltip, selection and panels with followers

- **Today**: only `pointer` and `viewport` are relayed (`_RELAYED_FIELDS`, `room_registry.py`), to every tab on the sender's page, never run as actions, never logged.
- **Decision**: a third relayed message, `focus`, carries what the sender is looking at: `{type: "focus", page, hover: ElementRef | null, tooltip: ElementRef | null, selection: ElementRef | null, panels: {sidebar: string[], filter: string | null, legend: boolean}}`, where `ElementRef = {kind: "node" | "row" | "edge" | "table", id: string}` names a diagram element by the id every viewer already uses. The server relays it **only to tabs of participants who follow the sender** (directly), newest only (`send_volatile("focus:<id>")`), with field validation like the other relayed types. The client sends it on change, at most 10 times a second. A follower applies it through a *focus surface* each viewer registers beside its diagram surface (`registerFocusSurface({ apply(focus), onLocal(listener) })`); while following, the follower's own hover and clicks on the diagram do not change what is shown.
- **Rationale**: relaying keeps the actions-and-logging rule of spec 028 (a hover is as private as a pointer); sending to followers only means a person not following never sees someone else's hover (FR-011); element ids are what each viewer already uses for highlighting, so `apply` reuses the viewer's own hover code.
- **Alternatives**: broadcast to the whole page and let clients drop it (wastes the follower-less majority's bandwidth and leaks hover); an action per hover (logs and lock contention for an event that happens 10 times a second).

## R3. Smooth following

- **Today**: the follower calls `surface.centreOn` on every received viewport (`useFollow`, `client/src/rooms/follow.ts`) at up to 10 per second: it jumps.
- **Decision**: the follower keeps the last two viewport samples with their arrival times and, on every animation frame, draws the view interpolated between them one sample interval behind real time (a small playback delay, 50–100 ms), interpolating the centre linearly and the zoom on a log scale; when no new sample arrives for one interval it settles exactly on the last one. The viewport rate rises from 10 to 20 per second. Pointer 20 + viewport 20 + focus 10 = 50 messages a second at most, so the rooms route's per-connection limit rises from 40 to 80 (`max_messages_per_second` on the route; the adapter's default stays 40).
- **Rationale**: interpolation removes the jumps without more traffic; 20 samples a second gives the interpolation a short delay; the server only relays, so the extra messages cost a dictionary update and a queue write each.
- **Alternatives**: rate alone (still jumps at 20/s, doubles traffic for no smoothness); extrapolation (overshoots when the leader stops).

## R4. Following in Firefox

- **Today**: reported broken, not reproduced; the cross-engine script opens Firefox for layout and pointers but has no follow case.
- **Decision**: first add a follow case to `client/scripts/check-layout-determinism.ts` for all six directed engine pairs, reproduce, then fix. Suspects, in order: `getScreenCTM` on an SVG inside a CSS-transformed container (Firefox computes it differently; `client/src/rooms/coordinates.ts`), `watchOwnPan` stopping the follow on pointer events Firefox fires while content moves under a still cursor, and the G6 surface's client-to-canvas mapping.
- **Rationale**: a fix without a reproduction cannot be proven; the case stays in the check run so it never breaks again.

## R5. Pointers that stay

- **Decision**: remove the client's idle fade (`POINTER_IDLE_MS`) and the server's ten-second window in `catch_up` (`POINTER_SHOWN_SECONDS`); a mouse pointer is shown while its participant is present (not away), on the same page, and showing pointers. Taps keep their brief mark.
- **Rationale**: FR-020/021; the conditions that already hide a pointer (left, away, other page, Hide pointers) remain.

## R6. Room controls: sizes and circles that never touch

- **Decision**: sizes from the clarification — icons 16 px, icon buttons 32 × 32 px (glyph ~18 px), room-bar circles 22 px. A circle's rings are drawn **inside a box that takes layout space**: the box is 29 px (22 + 2 × 3.5); your own ring is a border of that box; the focus ring is drawn inside the same box (`outline-offset` negative / inset shadow) instead of 5 px outside. Boxes stand 4 px apart.
- **Rationale**: FR-050/051; a ring that takes layout space cannot reach a neighbour.

## R7. Switching whom you follow

- **Decision**: reproduce in the browser first (follow A, open B's card, *Follow B instead*), record what overlaps, fix it; the follow case of R4 gains the switch.

## R8. The ERD card as in the mockup

- **Today**: a Graphviz HTML table with `STYLE="ROUNDED"` draws outline and header with Graphviz's own curve and a gap between them.
- **Decision**: Graphviz keeps laying out the table (cells, sizes, ports), but draws no outline (`BORDER="0"`, header cell with no fill); the post-pass (`client/src/lib/erdPostPass.ts`) draws the card from the table's bounding box exactly as the mockup does — one rounded rectangle (radius 9 px at 100 %, stroke 1.4) and the header as a path with the same top radius that fills to the outline — and puts it beneath the cells. Row tints keep their current colours and stop 1 px inside the outline.
- **Rationale**: Graphviz cannot draw a filled header flush with a rounded outline; drawing the card ourselves gives the mockup's geometry exactly and keeps Graphviz's layout (and the identical-layout proof of spec 028) untouched.

## R9. Icon and name on one axis

- **Decision**: in `placeKindIcons`, place the icon so its centre is at the name's visual centre line, `baseline − 0.36 × fontSize` (half the cap height of Helvetica, 0.718 em), and centre the pair in the header band. The ERD style check measures the icon's centre against the text's bounding-box centre.

## R10. Clean field types

- **Today**: `EntityFieldGraphNode.pretty_annotation` prints `origin[args]` with `__qualname__`, so `str | None` becomes `UnionType[str, NoneType]`.
- **Decision**: `aoa-action-machine` gains a pure function that renders an annotation by the table of FR-030; `field_type` becomes that clean label, and a new property `field_annotation` keeps today's full form for the tooltip. Maxitor carries `field_annotation` through `list-entities` and, on the client, passes every `field_type` through `cleanFieldType`, which parses the old forms (`UnionType[…]`, `Union[…]`, `Optional[…]`, `AssociationOne[…]`, `Generalization[…]`, `Specialization[…]`, `list[…]`, `Literal[…]`) and is idempotent on clean labels, so a service on an older `aoa-action-machine` looks the same. The tooltip shows `field_annotation`, else the raw string. The AI-CORE block on the method (a known violation, constitution IV) moves to the function.
- **Rationale**: FR-031 — the clean string is born where the type is known; the client rule covers services we do not control.

## R11. ERD line ends: optionality and direction

- **Today**: a relation edge carries `cardinality` `one` | `many` only; `list_entities_action.py` derives `one` / `zero_many` for the two ends; reference lines (`entity_reference_edges`) get `one` at the referring table and `zero_many` at the dictionary — reversed.
- **Decision**: the relation edge gains `optional: bool` — true when the relation field's annotation admits `None` or its default is `None`. `list_entities_action.py` returns four end values, `one`, `zero_one`, `zero_many`, `one_many` (the last only if the model declares a minimum — none does today), and reference lines become `zero_many` at the referring table and `one` at the dictionary. `buildDotSource.ts` draws Graphviz arrow shapes, first shape nearest the table: `one` → `teetee`, `zero_one` → `teeodot`, `zero_many` → `crowodot`, `one_many` → `crowtee`; arrow size and pen width are tuned so the ends stay readable at 100 %.
- **Rationale**: FR-043; the four shapes are the standard crow's-foot ends.

## R12. ERD hover over keys and lines

- **Decision**: `bindLineHover` collects, for the hovered line or for every line of the hovered row, the tables at both ends, and gives them the same class the hovered table gets, so the existing dimming keeps them bright.

## R13. Role labels on hover

- **Decision**: on the use-case diagram the role's label text is hidden by CSS and shown while the pointer is over the role's group (or the role is the follower's mirrored hover, R2).

## R14. Kinds present on the diagram

- **Decision**: the *Kinds* list is built from the tables the diagram shows before the kind filter (after domain and one-hop), intersected with `list-entity-kinds` for display names; a kind switched off stays listed.

## R15. Maxitor's own `graph-json`

- **Today**: Maxitor builds its machine with `create_node_graph_coordinator()`, which includes every imported AOA class — Maxitor's own actions among them — but serves no `graph-json`. `/examples/…` is outside `GraphSourceMiddleware` (it guards `/api/v1/*` and `/api/sidebar`).
- **Decision**: a resource `OwnModelGraphResource` holds Maxitor's coordinator and renders `to_json()` once per process; `GetOwnGraphJsonAction` returns it as `{"coordinator_json": …}` like the demo's; the app routes `GET /examples/model/graph-json` to it. The adapter's `ConditionalGetMiddleware` adds the `ETag` and the `304`.
- **Rationale**: "API only through actions, storage and services only through a resource" (project rule); the path is the one `load_aoa_service_action.normalize_url` adds to a bare address, so typing `maxitor.aoa.run` works with no change elsewhere.

## R16. The demo on the fresh adapter

- **Decision**: `aoa-demo` declares `aoa-fastapi-adapter>=1.3.0` and its version rises; publishing (a tag) and redeploying `demo.aoa.run` wait for the maintainer's command and are recorded as release steps after the changelog.

## R17. Local acceptance stand

- **Decision**: after every phase the agent rebuilds the local stand with `bash scripts/deploy_demonstrator_stand.sh --local` (Maxitor at `http://127.0.0.1:8101`, the demo service entered as `http://demo:8100`), checks the phase there itself, and only then hands the maintainer, in Russian, a short acceptance list: what to open, what to do, what must be seen. The phase's commit follows the maintainer's acceptance and instruction (constitution I).
- **Rationale**: most phases change what the eye sees; a stand built from the same images as production is what the maintainer accepts, and stepwise acceptance catches a wrong look before the next phase builds on it.
