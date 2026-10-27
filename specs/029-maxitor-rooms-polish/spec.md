# Feature Specification: Maxitor Rooms Polish — One Picture, Faithful Following, the Finer Look

**Feature Branch**: `feature/issue-282-maxitor-rooms-polish`

**Created**: 2026-10-27

**Status**: Draft

**Input**: User description: "https://github.com/bystrovmaxim/aoa/issues/282 — Maxitor rooms polish: one shared picture, faithful following, the finer look, Maxitor's own graph and freshness everywhere. Use the issue body as the source of truth. Builds on spec 028 (specs/028-maxitor-rooms)."

**Builds on**: [spec 028 — Maxitor rooms](../028-maxitor-rooms/spec.md), released as `aoa-maxitor` 2.3.0. Its design mockup, [028 mockup/index.html](../028-maxitor-rooms/mockup/index.html), stays the reference for every visual detail this text does not settle.

## Context: what is true today, checked on 2026-10-27

- **A room shows the room's value of a setting only once someone has set it.** A page setting is read as *the room's value → else the person's own value → else the default* (`client/src/lib/pageSettings.ts`, `usePageSetting`). Nobody's own values are sent to a room when it opens. The person who opened the room therefore keeps the filters and layout mode they had set before, while a guest sees the defaults.
- **Following copies the viewport and the page only.** Spec 028 FR-032 made zoom, scroll, hover cards, highlights, collapsed panels and the left panel personal. A follower sees where the followed person looks, but not the tooltip they read, the node they selected, the highlighting under their mouse or the accordion sections they opened.
- **The followed person's viewport is sent at most 10 times a second** (`VIEWPORT_RATE`, `client/src/rooms/throttle.ts`), and the follower jumps to each one. Pointers are sent at most 20 times a second. The room server relays both without running an action; every connection may send at most 40 messages a second (`max_messages_per_second`, `aoa-fastapi-adapter`), larger bursts close it with `4429`.
- **A pointer that has not moved for 10 seconds disappears** (`POINTER_IDLE_MS`, `client/src/rooms/PointerLayer/PointerLayer.tsx`), and a newcomer only receives pointers that moved in the last 10 seconds (`POINTER_SHOWN_SECONDS`, `room_registry.py`).
- **Following does not work in Firefox** — reported on the live stand, not yet reproduced. The cross-engine check (`client/scripts/check-layout-determinism.ts`) already opens Firefox for layouts and pointers, but has no follow case.
- **Participant circles overlap.** Rings are drawn outside a circle with `box-shadow` (your own ring, 3.5 px) and `outline` (the focus ring, 5 px in all), which take no room in the layout; the circles stand 4 px apart (`client/src/rooms/Circles/Circles.tsx`). The room bar's menu button is 44 × 44 px.
- **Switching whom you follow makes elements overlap** — reported, not yet reproduced.
- **The ERD card differs from the mockup.** The card is a Graphviz HTML table with `STYLE="ROUNDED"` (`client/src/lib/buildDotSource.ts`): a white gap runs between the coloured header and the outline, and the corner curve is Graphviz's, not the mockup's radius 9 shared by outline and header.
- **The kind icon and the table name are not on one axis.** `placeKindIcons` (`client/src/lib/erdPostPass.ts`) puts the icon at the top of the cell Graphviz reserves for it, while the name stands on the baseline Graphviz gives the text; measured on the reference fixture, the middle of the name's capitals stands 1.2 units above the icon's centre (corrected 2026-10-27 — the issue first said the icon sat higher).
- **ERD hover.** Hovering a table dims the rest. Hovering a line or a row with lines marks the line and the rows it joins (`bindLineHover`, `erdPostPass.ts`), but the tables at both ends are not brought forward as the hovered table is.
- **ERD line ends do not show cardinality fully, and reference lines point the wrong way.** A relation in the graph states only `one` or `many` (`EntityRelationIntentResolver.cardinality`); whether it may be empty is not recorded, so `erdEnd` (`client/src/lib/buildDotSource.ts`) can draw only a bar or a crow's foot and an optional end looks like a mandatory one. Reference lines to a dictionary (`entity_reference_edges` in `list_entities_action.py`) get `one` at the referring table and `zero_many` at the dictionary — the reverse of the truth, since many rows refer to one dictionary value. Field labels follow the UML convention: a field's name stands at the far end, beside the table that plays that role.
- **Field types are printed in Python's internal form.** A row's type is the `field_type` string the service puts in `graph-json`, built by `EntityFieldGraphNode.pretty_annotation` (`aoa-action-machine`) and shown as it comes: `str | None` becomes `UnionType[str, NoneType]`, `Optional[str]` becomes `Union[str, NoneType]`. The demo model alone carries 39 distinct types, among them `AssociationOne[CurrencyEnumEntity]` (26 fields), `Generalization[GeneralizationHeadCoreEntity]` and `Specialization[Union[GeneralizationVariantASpecEntity, GeneralizationVariantBSpecEntity], GeneralizationShapesKindEnumEntity]`.
- **The *Kinds* filter lists every kind of the graph** (`list-entity-kinds`, `client/src/lib/loadErdDomainsBundle.ts`), while the *Domains* filter lists only the domains present on the diagram.
- **ERD line labels are always shown.** The field names at each end of a relation line (its UML role names, `headlabel` / `taillabel`) are drawn all the time, run over the tables they meet and cannot be read (corrected 2026-10-27: remark 10 is about these, not the use-case diagram's actor names).
- **Maxitor serves no `graph-json` of its own.** Typing `maxitor.aoa.run` into the service field ends in `AOA service returned HTTP 404 at 'https://maxitor.aoa.run/examples/model/graph-json'`. The demo serves its graph at `/examples/model/graph-json` through `GetExampleModelGraphJsonAction`.
- **Only one demo says whether its graph changed.** `dev.demo.aoa.run` (built from `main`, adapter 1.3.0) answers `graph-json` with an `ETag` and `304` to `If-None-Match`; `demo.aoa.run` (`aoa-demo` 3.0.0, an older adapter) sends no `ETag`, so Maxitor downloads its whole body every two minutes to compare hashes.

## Clarifications

### Session 2026-10-27

- Q: Which lines are "connectors drawn badly"? → A: The ERD's relation lines only: arrows point the wrong way, the ends are drawn poorly, and the cardinality cannot be seen.
- Q: What size are the room controls? → A: The sizes Maxitor used before rooms: a menu or row icon is 16 px (the left panel's rows), an icon button is 32 × 32 px with a glyph of about 18 px (the *Reload* button); a participant circle is 22 px, so that circle and ring (29 px) fit the same 32 px height as the buttons with a gap to spare.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - One room, one picture (Priority: P1)

Anna has set the ERD's layout to Neato and turned off two domains. She opens a room and sends Boris the link. Boris sees exactly Anna's diagram: Neato, the same two domains off. When either of them opens another diagram, both see the same settings there too.

**Why this priority**: The room promises one shared picture; two different pictures in one room make every conversation about the diagram wrong.

**Independent Test**: Set filters and a layout mode outside a room, open a room, join it from a second browser with no settings of its own; both show the same diagram on every page.

**Acceptance Scenarios**:

1. **Given** Anna has her own filters and layout mode on a page, **When** she opens a room, **Then** those values become the room's values for that page and Boris, joining, sees them.
2. **Given** a room whose value for a setting nobody has set, **When** Anna and Boris both look at that page, **Then** both see the same value, whatever each had set before joining.
3. **Given** Boris had his own filters before joining Anna's room, **When** he joins, **Then** he sees the room's settings, not his own.
4. **Given** a room in use, **When** a person opens a page nobody in the room has opened yet, **Then** every person who opens that page afterwards sees the same settings.

---

### User Story 2 - The follower sees what the followed person sees (Priority: P1)

Boris follows Anna to discuss a table. Anna hovers over a row, reads its tooltip, selects a node, opens the *Kinds* section of the filter panel and collapses a branch of the left panel. Boris sees each of these as Anna does, at the same moment, and everyone's pointers stay on his screen for as long as they are in the room.

**Why this priority**: A conversation about a diagram needs both people to see the same detail, not only the same area.

**Independent Test**: Two browsers, one following the other; every hover, tooltip, selection, highlight and accordion change of the followed browser appears in the follower; pointers that stop moving stay.

**Acceptance Scenarios**:

1. **Given** Boris follows Anna, **When** Anna hovers a node, a row or a line, **Then** Boris sees the same highlighting and the same tooltip.
2. **Given** Boris follows Anna, **When** Anna selects a node or clears the selection, **Then** Boris's selection follows.
3. **Given** Boris follows Anna, **When** Anna opens or closes a section of the filter panel or a branch of the left panel, **Then** the same section or branch opens or closes for Boris.
4. **Given** Boris stops following, **When** he hovers, selects or opens panels, **Then** nobody else sees it and his own state is his again.
5. **Given** Vera is in the room and her pointer has not moved for minutes, **When** Boris looks at the page she is on, **Then** her pointer is still shown.
6. **Given** Vera leaves the room, loses her connection, goes to another page or turns off her pointer, **When** Boris looks, **Then** her pointer is gone.

---

### User Story 3 - Following is smooth and works in every browser (Priority: P2)

Boris follows Anna while she pans and zooms quickly. His view glides with hers, without jumps, in Chrome, Safari and Firefox, whichever of them each person uses.

**Why this priority**: Jerky following tires the follower; following that does not work in one browser excludes everyone who uses it.

**Independent Test**: Follow a continuously panning person in each pair of the three engines; the follower's view moves continuously and arrives where the followed view stops.

**Acceptance Scenarios**:

1. **Given** Boris follows Anna, **When** Anna pans continuously, **Then** Boris's view moves continuously, with no visible jump between positions.
2. **Given** Anna stops moving, **When** a moment passes, **Then** Boris's view stands exactly where Anna's does.
3. **Given** any pair of Chrome, Safari and Firefox, **When** one follows the other, **Then** following works in both directions.

---

### User Story 4 - Maxitor's own graph, and graphs that say they changed (Priority: P2)

Someone types `maxitor.aoa.run` into the service field and sees Maxitor's own diagram — its rooms, its diagram reads, its actions — like any other AOA service. Maxitor and both demos tell Maxitor cheaply whether their graph changed.

**Why this priority**: Maxitor is an AOA service and should show itself; the error it gives today looks like a broken site. Cheap freshness keeps held graphs current at little cost.

**Independent Test**: Open `maxitor.aoa.run` as a source; ask Maxitor and both demos for `graph-json` twice, the second time with the tag from the first.

**Acceptance Scenarios**:

1. **Given** the service field holds Maxitor's own address, **When** the diagram opens, **Then** it shows Maxitor's own model.
2. **Given** Maxitor, `demo.aoa.run` or `dev.demo.aoa.run`, **When** `graph-json` is asked for again with the tag of the previous answer and nothing changed, **Then** the answer is "not modified" with no body.

---

### User Story 5 - Room controls in Maxitor's style (Priority: P3)

The room bar, its menu, the participant circles and the participant card are as fine and quiet as the rest of Maxitor. Circles never touch each other, whatever ring they carry, and switching whom you follow is as clean as the first follow.

**Why this priority**: Visual consistency; nothing breaks, but the room controls look out of place.

**Independent Test**: Compare the room controls with the mockup's sizes; open a room with several people, ring your own circle, focus another, follow one person and switch to another.

**Acceptance Scenarios**:

1. **Given** a room with several people, **When** any circle carries your ring or a focus ring, **Then** no ring touches a neighbouring circle or its ring.
2. **Given** Boris follows Anna, **When** he picks Vera in her card, **Then** nothing on screen overlaps during or after the switch.
3. **Given** the room controls, **When** measured, **Then** icons are 16 px, icon buttons 32 × 32 px and circles 22 px, as in the rest of Maxitor.

---

### User Story 6 - The ERD card as designed (Priority: P3)

An ERD table looks exactly like the mockup: the coloured header reaches the outline, outline and header share one corner curve, the kind icon and the name stand on one axis, and each field's type reads as one clean name.

**Why this priority**: Readability and polish of the diagram people look at most.

**Independent Test**: Render the reference ERD and measure the card against the mockup; read every field type of the demo model.

**Acceptance Scenarios**:

1. **Given** an ERD table, **When** rendered, **Then** no gap shows between the header and the outline, and the corner curve of outline and header matches the mockup.
2. **Given** a table's header, **When** rendered, **Then** the centre of the kind icon is on the visual centre line of the name.
3. **Given** a field of any type the demo model uses, **When** shown, **Then** its type follows the table of FR-030 and the full annotation is in its tooltip.

---

### User Story 7 - Diagrams that read easily (Priority: P3)

Hovering a key row or a line lights up every table it joins. A line's end labels appear only while it is hovered, on a plate that keeps them readable. Every ERD line shows the cardinality of both ends, and its ends sit where they belong. The *Kinds* filter offers only the kinds on this diagram.

**Why this priority**: Each item removes noise from a diagram people read for a long time.

**Independent Test**: Hover a PK row, an FK row and a line on the reference ERD; open a use-case diagram; open the *Kinds* filter on a diagram that lacks some kinds.

**Acceptance Scenarios**:

1. **Given** the ERD, **When** a table is hovered, **Then** the other tables dim (as today).
2. **Given** the ERD, **When** a PK row, an FK row or a line is hovered, **Then** every table joined by that row's lines or by that line is highlighted with the hovered table, and the rest dim.
3. **Given** the ERD, **When** nothing is hovered, **Then** no line label shows; **When** a line (or a key row with lines) is hovered, **Then** its end labels show on white plates over whatever they cross.
4. **Given** a relation that is optional on one end and mandatory on the other, **When** its line is drawn, **Then** the two ends look different and each shows the cardinality of its own side.
5. **Given** a table that refers to a dictionary, **When** the line is drawn, **Then** the many-end is at the referring table and the one-end at the dictionary.
6. **Given** a diagram on which some kinds have no entity, **When** the *Kinds* filter opens, **Then** only the kinds with at least one entity on this diagram are listed.

### Edge Cases

- A room opened by someone with no own settings: the room starts with the defaults, which are then the same for everyone.
- Two people change the same setting at once: the last change wins for everyone (spec 028 FR-031 stands).
- The followed person hovers something the follower's page does not show (the follower is still loading the page): the hover applies once the page is drawn, or is dropped if it already ended.
- The followed person's tooltip would fall outside the follower's smaller screen: it is kept inside the follower's screen.
- A follower on a phone follows someone on a monitor: the follower keeps the same centre and zoom as today; hover and tooltips are shown even though the phone cannot hover itself.
- A person's pointer sits still for an hour: it stays.
- A person turns their pointer off ("Hide pointers"): nobody sees it, as today.
- A field type that matches no rule of FR-030: it is shown as the service gives it, shortened with `…` if too long, full in the tooltip.
- A service on an older `aoa-action-machine` sends `UnionType[str, NoneType]`: Maxitor shows `str | None` all the same.
- Maxitor's own graph changes when Maxitor is updated: its tag changes and held copies are rebuilt as for any service.
- A diagram on which every kind is turned off: the *Kinds* list still lists those kinds, so they can be turned back on.

## Requirements *(mandatory)*

### Functional Requirements

**One picture in a room**

- **FR-001**: When a room opens, the opener's own value of every page setting MUST become the room's value for that page; a single value too large to send (over the room's message limit) starts at its default instead.
- **FR-002**: Inside a room, a page setting MUST be read from the room only; a person's own value MUST NOT show inside a room. A setting the room has no value for MUST show its default for everyone.
- **FR-003**: Leaving a room MUST keep every page as it was in the room (spec 028 FR-019 stands).

**Following**

- **FR-010**: While following, the follower MUST see the followed person's hover highlighting, tooltip, selection, and the open or closed state of every filter-panel section and left-panel branch, as the followed person sees them.
- **FR-011**: The followed person's hover, tooltip, selection and panel state MUST reach only the people following them; people not following MUST NOT see them.
- **FR-012**: When a person stops following, their own hover, selection and panel state MUST be theirs again, starting from what they saw while following.
- **FR-013**: Spec 028 FR-032 changes accordingly: zoom, scroll, hover cards, highlights, collapsed panels and the left panel stay personal *except while following*.
- **FR-014**: The follower's view MUST move continuously between the positions it receives, with no visible jump, and MUST stand exactly where the followed view stands once it stops.
- **FR-015**: Following MUST work in both directions between every pair of Chrome, Safari and Firefox, and the cross-engine check MUST include a follow case in each engine.
- **FR-016**: Any change of message rates MUST stay within the per-connection limit, or raise that limit with it.

**Pointers**

- **FR-020**: A person's pointer MUST be shown for as long as they are in the room, on the same page and showing their pointer, however long it stays still.
- **FR-021**: A newcomer MUST receive the last position of every pointer shown on their page, however old.
- **FR-022**: A tap on a touch screen MUST keep its brief mark (spec 028), not a lasting pointer.

**ERD card**

- **FR-030**: A field's type MUST be shown as one clean name, by this table; the full annotation MUST be in the row's tooltip:

  | annotation | shown |
  |---|---|
  | a plain type, an enum, a lifecycle (`str`, `PlayerLifecycle`) | unchanged |
  | `str \| None`, `Optional[str]`, `Union[str, None]` | `str \| None` (`None` last) |
  | `A \| B` | `A \| B` |
  | a relation container (`AssociationOne[X]`, `Generalization[X]`) | `X` |
  | `Specialization[A \| B, Kind]` | `A \| B` |
  | `list[X]`, `set[X]`, `tuple[X, ...]` | `X[]` |
  | `dict[K, V]` | `dict[K, V]` |
  | `Literal["a", "b"]` | `"a" \| "b"` |
  | `Annotated[X, …]` | `X` |
  | longer than the type column | cut with `…` |

- **FR-031**: Services MUST produce the clean string of FR-030, with the full annotation beside it; Maxitor MUST clean the old forms itself so a service on an older version looks the same.
- **FR-032**: An ERD card's coloured header MUST reach the outline with no gap, and the outline and the header MUST share the mockup's corner curve (radius 9 at the mockup's scale).
- **FR-033**: The centre of a table's kind icon MUST be on the visual centre line of the table name, and both MUST be centred in the header band.

**Reading diagrams**

- **FR-040**: Hovering an ERD table MUST dim every other table (as today).
- **FR-041**: Hovering a PK or FK row MUST make that field's lines bold, keep bright every table those lines join, dim every other table, leave the hovered table's other lines as they are (neither bold nor dimmed) and dim every line not touching the hovered table. Hovering a table anywhere else (FR-040) dims the other tables and every line not touching it. Hovering a line keeps bright the two tables it joins and dims the rest. (Refined by the maintainer 2026-10-27.)
- **FR-042**: The labels at the ends of ERD relation lines (field names) MUST be hidden by default and shown, on a plate that keeps them readable over a table, while the line is hovered — by the mouse on the line, on a key row it starts from, or by a followed person's hover.
- **FR-043**: Every ERD relation line MUST show the true cardinality of both ends with crow's-foot ends — exactly one, zero or one, zero or many (and one or many where the model declares a minimum) — so that optional and mandatory ends differ and no end sits at the wrong table; the model MUST record whether a relation may be empty for this to be drawn. Field labels keep the UML convention (the field's name at the far end) and stay readable beside their end. Lines MUST be smooth, meet the table outline and carry ends in proportion to the line. Generalization lines keep their dashed style and filled arrowhead (spec 027).
- **FR-044**: The *Kinds* filter MUST list only the kinds with at least one entity on the diagram before kinds are filtered, as the *Domains* filter does for domains.
- **FR-045**: An ERD table MUST always list every field it declares, relation fields included, whether or not the table at the other end is on the diagram; the 1-hop switch decides only which extra tables come onto the diagram (with their lines), never which fields a table lists. (Maintainer, 2026-10-27.)
- **FR-046**: A specialization head and its variants are joined through two declared fields — the head's axis field and each variant's reverse field — and hover MUST treat them as any other relation: hovering either field, or the line between them, makes those lines bold and keeps the head and its variants bright (FR-041). The variant's reverse field is a key and MUST carry the FK mark. (Maintainer, 2026-10-27.)

**Room controls**

- **FR-050**: The room controls MUST use the sizes Maxitor used before rooms: icons in menus and rows 16 px; icon buttons 32 × 32 px with a glyph of about 18 px; participant circles 22 px (in the room bar; the participant card and lists may use a smaller circle). The room bar's 44 × 44 px menu button and 18 px banner icons come down to these sizes.
- **FR-051**: Participant circles MUST never touch each other or each other's rings; every ring MUST fit inside the space its circle takes, leaving a visible gap between neighbours.
- **FR-052**: Switching whom you follow MUST leave no element overlapping another, during or after the switch.

**Maxitor's own graph and freshness**

- **FR-060**: Maxitor MUST serve its own model's `graph-json` through an AOA action at `/examples/model/graph-json`, so its own address opens its own diagram like any service's.
- **FR-061**: Maxitor's and both demos' `graph-json` MUST carry a tag of their content and answer "not modified", with no body, to a request that names the current tag.
- **FR-062**: `aoa-demo` MUST be released on `aoa-fastapi-adapter` 1.3.0 or later, and `demo.aoa.run` redeployed with it; the release and the deployment happen on the maintainer's command (constitution I).

### Key Entities

- **Page settings of a room**: the filters and layout mode of each page, now seeded by the opener and read only from the room while inside it.
- **What a followed person shares**: their viewport and page (as before), now also their hover, tooltip, selection and open panels — sent only to those who follow them, and personal again when nobody follows.
- **Pointer**: a person's last position on a page, shown while they are in the room and on that page, with no idle timeout.
- **Field type label**: the clean display name of a field's type, with the full annotation kept for the tooltip.
- **Maxitor's own graph**: Maxitor's model, served as `graph-json` with a content tag like any AOA service.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In 10 of 10 trials, a person who joins a room sees the same filters and layout mode as the person who opened it, on every page, including when either had their own settings before.
- **SC-002**: While following, the follower shows the followed person's hover, tooltip, selection and panel changes within half a second, in 10 of 10 trials.
- **SC-003**: While following a continuously panning person, the follower's view moves on every displayed frame and never jumps more than a tenth of the screen at once; within half a second of the followed person stopping, both views agree to the pixel.
- **SC-004**: Following works in all six directed pairs of Chrome, Safari and Firefox, proven by the check run.
- **SC-005**: A pointer that stays still for 10 minutes is still shown to everyone on its page.
- **SC-006**: Every room-control icon measures 16 px, every room-control icon button 32 × 32 px and every room-bar circle 22 px; no two participant circles or their rings touch, at any room size up to the circle limit, with any combination of rings.
- **SC-007**: The ERD card matches the mockup: no gap between header and outline, the corner curve within half a pixel of the mockup's at the same scale, the icon's centre within half a pixel of the name's centre line — measured by the ERD style check.
- **SC-008**: Every one of the 39 field types of the demo model is shown by the table of FR-030; none shows `UnionType`, `NoneType`, `Union[`, `AssociationOne[` or `Generalization[`.
- **SC-009**: Typing `maxitor.aoa.run` into the service field opens Maxitor's own diagram.
- **SC-010**: Maxitor, `demo.aoa.run` and `dev.demo.aoa.run` each answer a repeated `graph-json` request with "not modified" and no body (`demo.aoa.run` once it is redeployed on the maintainer's command).
- **SC-011**: On a diagram missing some kinds, the *Kinds* filter lists exactly the kinds present on it.
- **SC-012**: On the reference ERD, every line's two ends match the cardinality and optionality of its relation, and every reference line has its many-end at the referring table — checked by the ERD style check.

## Assumptions

- "Icons too large" covers the room bar, its menu, the banners, the participant circles and the participant card. Where the mockup of spec 028 is larger than FR-050, FR-050 wins.
- The lines of the use-case diagram, the lifecycle diagram and the full graph are out of scope for FR-043.
- "Role labels" means the field names at the ends of ERD relation lines (UML role names); the use-case diagram's actor names stay as they are.
- Smoothness is reached first by drawing the follower's movement between received positions; the message rate rises only if measurement shows it is still not smooth enough. The room server only relays these messages, so a higher rate costs it almost nothing.
- Followed hover, tooltips and panels travel the same way as the viewport: relayed by the room server, never run as actions and never logged (spec 028).
- The follower on a touch device sees the followed person's hover and tooltip even though the device cannot hover itself.
- The clean type rule lives in `aoa-action-machine`, which builds `graph-json`; services on older versions are cleaned by Maxitor.
- Releasing `aoa-demo` and `aoa-action-machine` and redeploying `demo.aoa.run` and `maxitor.aoa.run` need the maintainer's command; planning reserves the steps, nothing is published without it.
- The shared-settings rule of spec 028 (FR-030, FR-031, FR-033) stands; this feature fixes where values come from, not what is shared.
