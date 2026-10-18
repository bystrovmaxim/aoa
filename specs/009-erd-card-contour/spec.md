# Feature Specification: A table card's fills stop at its rounded outline

**Feature Branch**: `feature/issue-226-erd-rounded-band`

**Created**: 2026-10-18

**Status**: Draft

**Input**: User description: "https://github.com/bystrovmaxim/aoa/issues/226 — in the domain ERD the header band of an entity card is painted as a rectangle, so its corners stand outside the card's rounded outline; the fill should follow the contour."

## Clarifications

### Session 2026-10-18

- Decision taken while writing this specification: **the outline is not the defect — the fill is.** The rounded contour with its 12-unit corner radius and its single stroke in the domain's colour is the card's shape and it is right. What breaks the shape is the band painted inside it as a rectangle, and the same is true of the row tints. The specification therefore makes the fills respect the contour; it does not square the card, shrink the band, or drop the rounding — the three ways of making the symptom disappear by giving up the shape.
- Decision taken while writing this specification: **every fill inside a card is in scope, not only the header band.** The issue names the band because it is the only one you can see today, and it says so: the primary-key row, the foreign-key row and the last body row are rectangles too, and their corners land outside the bottom arcs exactly the same way. A fix that repairs the top of the card and leaves the bottom is the same defect with a smaller audience, and it would return the day a card ends on a tinted row.
- Decision taken while writing this specification: **the change is verified on the picture the browser actually draws, and the verification must fail on the code as it stands today.** A check written after the fix that passes on both versions proves nothing; the repository's principle is that the demonstration is adversarial. The form of that check is settled in the clarification session below.
- Decision taken while writing this specification: **the other two diagrams are a regression boundary, not a second scope.** The lifecycle automaton and the use-case diagram are drawn by the same part of the viewer as the entity diagram. Their nodes carry one fill inside their own outline and show no such spill today; the work must leave them exactly as they are, and that invariance is a requirement, not a hope.
- Decision taken while writing this specification: **no design change rides along.** The corner radius, the stroke, the domain colours, the row tints, the fonts, the spacing, the legend and the dotted canvas are what they are. This work changes one property of the drawing — a fill stays inside the shape it belongs to — and a reader comparing the two versions should see the tabs gone and nothing else moved.
- Decision taken while writing this specification: **the card's geometry is read from the drawing, not assumed.** The radius, the inset of a fill from the contour and the row heights are the renderer's numbers and may change with a renderer upgrade. The fix follows whatever shape was drawn rather than hard-coding today's 12 units, because a constant that matches today's renderer is a defect waiting for the next one.

### Session 2026-10-18 — clarification

- Q: Which check must exist when the work is done — an automatic one inside the repository's check run, the same check kept outside it, or recorded before-and-after evidence alone? → A: **An automatic check inside the check run.** A small script draws a fixture card through the same renderer the viewer uses, runs the viewer's own containment pass over the drawing, and asserts the containment; on the code as it stands today it must fail. The check run today only type-checks and builds the client and draws nothing, so the script is new work, and the pass must be operable without a browser — or given the smallest dev-only shape that makes it so. A dev-only dependency is acceptable; a runtime one is not (FR-012).
- Q: Where does a fill end relative to the card's outline — under the stroke, up to its outer edge, or short of the stroke? → A: **Short of the stroke: the colour never runs under the frame, and the pass does not change how far short it stops.** The shape a fill occupies is the contour trimmed by the inset the renderer already gives it — one unit today, while the stroke covers half a unit either side of the contour, so a fill stops half a unit inside the stroke's own edge. That half-unit hairline exists in the drawing today along every edge and the pass leaves it exactly as it is; what it removes is the corner where the fill left the contour altogether. What is never accepted is a fill painted under the stroke or outside the contour.
- Q: Is there an explicit limit on how large a model the change must stay responsive on, or is "no slower than today" enough? → A: **An explicit limit at 100+ cards.** A model of at least 120 tables is the largest case the change must keep usable: it opens, pans and zooms without noticeable stutter, and it is no more than 1.5× slower than the same model on the code as it stands today, measured once on the same machine and recorded in the pull request. The automatic check draws that fixture too, within a generous fixed wall-clock budget, so a catastrophic regression fails a check rather than a conversation; the frame timing itself is recorded, not asserted, because a timing assertion in the check run is flaky by nature.
- Decision taken with that answer: **recorded screenshots stay, as evidence rather than as the guard.** They are attached to the pull request because they are what a reader looks at, but the invariant is carried by the automatic check, and a screenshot is never the thing that keeps the next change honest.

## User Scenarios & Testing *(mandatory)*

The readers of this feature are a person showing a domain model on the entity diagram, a person reading the same diagram in a specification, and the person who maintains the three diagrams the viewer draws.

### User Story 1 - A card reads as one shape, not a rectangle with corners cut off (Priority: P1)

A person opens the domain entity diagram and looks at a table. The card has a rounded outline in the domain's colour, and the coloured header band wears the same shape: its upper corners follow the arcs, not stand outside them as two tabs. The rows below sit inside the same contour, and a tinted last row — a primary-key or foreign-key highlight — follows the lower arcs the same way.

**Why this priority**: this is the defect itself, and it is on every card of every diagram the viewer draws. A card whose band runs past its own outline looks like a layering mistake, and a reader of the picture cannot tell whether the colour marks the card or something behind it.

**Independent Test**: open the reproduction link, look at any card at 100 % zoom, and confirm that no part of the header band or of a tinted row is visible outside the card's rounded outline, while the title, the field names, the types, the key glyphs, the borders and the edges are where they were.

**Acceptance Scenarios**:

1. **Given** an entity card with a header band in a domain colour, **When** the diagram is drawn, **Then** the band's upper-left and upper-right corners follow the card's arcs and no part of the band is visible outside the outline.
2. **Given** a card whose last row carries a primary-key or foreign-key tint, **When** the diagram is drawn, **Then** the tint's lower corners follow the arcs as well.
3. **Given** the same card, **When** the two versions are compared side by side, **Then** the outline's radius, colour and stroke, the band's colour, the rows' tints and the text are unchanged — only the protruding corners are gone.
4. **Given** a card that has no rows at all, so that the band is the whole card, **When** the diagram is drawn, **Then** all four corners of the band follow the outline.

---

### User Story 2 - The shape holds in every layout the viewer offers (Priority: P2)

A person switches between the five layout presets the entity diagram offers, zooms in to read a field name, pans across the canvas, and returns with "fit to window". In every one of those states the cards are drawn as one shape: no preset, no zoom level and no filter changes the way a fill meets its contour.

**Why this priority**: the defect is a property of the drawing, not of one layout, and a fix that holds only in the default preset would move the problem to the four other ways of arranging the same cards. Checking it here is what makes the repair a repair rather than a patch of one screenshot.

**Independent Test**: walk all five presets on the reproduction link, then zoom to the maximum the toolbar allows and to the minimum, and confirm the contour holds the fills in each state — including with a domain filter applied and with single-hop neighbours switched on, which rebuild the drawing.

**Acceptance Scenarios**:

1. **Given** the entity diagram, **When** each of the five layout presets is chosen in turn, **Then** every card's fills stay inside its contour in all five.
2. **Given** a card zoomed to the maximum the toolbar offers, **When** its corner is inspected, **Then** the fill reaches the outline with no hairline of canvas between them.
3. **Given** the diagram, **When** the domain filter or the single-hop toggle rebuilds it, **Then** the cards are still drawn as one shape.
4. **Given** a set of alternatives framed by a dashed container, **When** the container is drawn, **Then** the cards inside keep their own contours and the container's frame is unchanged.

---

### User Story 3 - The other two diagrams are untouched (Priority: P3)

A person opens the lifecycle automaton and the use-case diagram after the change and sees exactly the picture they saw before: the same nodes, the same fills, the same boundaries, the same arrows and the same dotted canvas.

**Why this priority**: all three diagrams are drawn by the same part of the viewer, so the risk of this change is not that it fails to fix the entity diagram but that it quietly alters the other two. It comes last because it is a guard rather than a deliverable, and a reader notices it only if it is done wrong.

**Independent Test**: render the same payload with the previous version and with the new one, compare the two drawings, and confirm there is no difference on the lifecycle and use-case pages.

**Acceptance Scenarios**:

1. **Given** the lifecycle automaton, **When** both versions draw the same payload, **Then** the drawings are identical.
2. **Given** the use-case diagram, **When** both versions draw the same payload, **Then** the drawings are identical, with and without the system boundary.
3. **Given** the entity diagram, **When** an edge or its arrowhead is inspected after the change, **Then** it is drawn as before — this work touches fills inside a node and nothing outside it.

---

### Edge Cases

- A card that is narrower than twice the corner radius: the renderer's arcs meet and the shape is no longer a rectangle with rounded corners. No fill may escape the resulting shape, whatever it is.
- A card whose only tinted row is the last one, and a card whose first row is tinted right under the band: the two fills meet in a straight line inside the card, and that line stays where it was.
- A card so short that the band and one row are all it has: the top arcs and the bottom arcs both matter in a card a few rows tall.
- A card whose labels are long enough to widen it: the radius does not scale with width, so a wide card still has 12-unit corners and a fill that reaches them.
- A card whose specialization row carries a hover tooltip: the tooltip keeps working and keeps its text.
- An empty diagram — no domain selected, or a diagram with no tables: the page's empty state appears as today, and nothing fails.
- A card at the highest zoom the toolbar offers: the fill meets the contour's inner edge, and the hairline the renderer's inset leaves there is expected; a fill under the stroke, or a gap wider than that inset, is not.
- The dashed container that frames alternatives: it has its own contour and no cells, and it is not a card for the purposes of this feature.
- A whole domain on one canvas — 120 tables and more: the containment still holds on every card, and the canvas stays usable at that size.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: No fill of a table card may be visible outside the card's rounded outline, and none may be painted under its stroke. This covers the header band, the primary-key tint, the foreign-key tint, the body background and a plain row, at every corner of the card.
- **FR-002**: The card's outline itself MUST stay as drawn today: same corner radius, same stroke width and colour, same position and size on the canvas.
- **FR-003**: Every fill MUST keep its colour and its row: the header band stays in the domain's colour, a primary-key row keeps its tint, a foreign-key row keeps its tint, and the order of rows does not change.
- **FR-004**: The card's text MUST be unaffected: the title, the field names, the type names and the key glyphs keep their content, position, colour and weight, and none of them is cut by the shape that now holds the fills.
- **FR-005**: Everything outside the fills MUST be unaffected: edges, arrowheads, edge labels, the dotted canvas and the page's empty state are drawn as before.
- **FR-006**: The containment MUST hold in all five layout presets the entity diagram offers.
- **FR-007**: The containment MUST hold at every zoom level and pan position, including after "fit to window", and after a rebuild caused by the domain filter or the single-hop toggle.
- **FR-008**: A card drawn inside a dashed container MUST keep its own containment, and the container's frame MUST be drawn as before.
- **FR-009**: A card narrow enough that its arcs meet MUST be drawn without a failure and without a fill escaping the resulting shape.
- **FR-010**: The lifecycle automaton and the use-case diagram MUST produce the same drawing for the same input as they do today.
- **FR-011**: The behaviour MUST survive a re-render: switching a layout, toggling a domain, toggling single-hop neighbours or reloading the graph rebuilds the drawing, and the rebuilt drawing obeys every requirement above.
- **FR-012**: The change MUST NOT introduce a new runtime dependency and MUST NOT require the page to load anything from outside the drawing itself.
- **FR-013**: The change MUST be demonstrated by an automatic check that runs inside the repository's check run: it draws a fixture card through the same renderer the viewer uses, runs the viewer's own containment pass over the drawing, and asserts that no fill leaves the contour. The check MUST fail on the code as it stands today and pass after the change, and the closing check run MUST be green.
- **FR-014**: The documentation and the changelog MUST ship with the change, as the constitution's last three steps require: the entity viewer's own description says what a card is and that its fills follow its contour, and `packages/aoa-maxitor/CHANGELOG.md` gains one article under `## [Unreleased]` about what a reader now sees.
- **FR-015**: A fill MUST be trimmed to the shape the renderer's inset describes: the contour shrunk by the amount the renderer already gives it, its corners following the same arcs at the smaller radius. The colour MUST NOT be painted under the stroke, and the gap the renderer's inset leaves between a fill and the stroke MUST stay exactly what it is today — neither widened nor closed by this change.
- **FR-016**: The change MUST keep a large model usable: a diagram of at least 120 tables opens, pans and zooms without noticeable stutter, and is no more than 1.5× slower than the same diagram on the code as it stands today. The automatic check draws that model within a fixed wall-clock budget, and the before-and-after numbers are recorded in the pull request.

### Key Entities *(include if the feature involves data)*

- **Table card**: one entity of the entity diagram — a rounded rectangle with a stroke in the domain's colour, a header band and a list of rows. It is the unit whose shape this feature is about.
- **Fill**: any coloured region inside a card — the header band, a primary-key tint, a foreign-key tint, the body background, or a plain row. Fills are what must be contained.
- **Contour**: the card's rounded outline: its radius, its stroke and its colour. It is the boundary that must not be crossed and that must not change. A fill is **trimmed** to it — the act — by **clipping** it with a **clip path** — the mechanism; the three words are used in that sense throughout this feature.
- **Cluster frame**: the dashed rounded container that groups the alternatives of a specialization axis. It has a contour of its own, holds no fills and is not a card.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On the reproduction link, in the default layout at 100 % zoom, the number of card fills whose corners stand outside their own outline is zero. Today it is two per card, plus two more on every card whose last row is tinted.
- **SC-002**: The same count is zero in each of the five layout presets — five of five.
- **SC-003**: At the highest zoom the toolbar offers, no fill is painted under or outside the stroke, and the gap between a fill and the stroke is the one the drawing already has today — measured once before and once after and identical.
- **SC-004**: The lifecycle and use-case diagrams produce the same drawing for the same payload before and after the change.
- **SC-005**: The repository's check run carries an automatic check that fails on the code as it stands today and passes after the change; the run is green with no remark beyond the two the constitution already accepts.
- **SC-006**: A reader of the entity viewer's description can tell what a card is and that its fills follow its contour, and `packages/aoa-maxitor/CHANGELOG.md` carries one article under `## [Unreleased]` describing what the reader now sees.
- **SC-007**: A diagram of 120 tables opens, pans and zooms without noticeable stutter, and its drawing is no more than 1.5× slower than today's on the same machine, with both numbers recorded in the pull request.

## Out of scope

- The shape of the card itself: the radius, the outline colour and the stroke width are not being redesigned.
- The dashed container around a specialization axis, the legend, the toolbar and the page's empty state.
- Edge routing, edge labels and arrowheads.
- The diagram payload, the server's endpoints and the graph the endpoints read: this is a drawing defect, not missing data.
- Any other diagram the viewer may grow later; the two that exist are a regression boundary and nothing more.

## Assumptions

- The entity diagram is the only place where an entity's shape holds several fills; the lifecycle and use-case nodes carry a single fill inside their own outline, which is why they show no such spill today.
- The corner radius and the inset a fill keeps from the contour are the renderer's numbers and may change when the renderer is upgraded; the fix follows the drawn shape rather than a constant, so a later upgrade does not reopen this defect.
- The drawing is produced from the same payload by the same pipeline in both versions, so a comparison of the two versions is a comparison of the fix and of nothing else.
- The repository's check run does not execute a browser today, so the pass required by FR-013 is markup-level work with no DOM in it: the very function the page runs is run by the check in plain Node. That is why the clarification's permission for a dev-only dependency went unused — nothing had to be shimmed.
- Commits, pull requests and merges remain the maintainer's decision (constitution, principle I): this specification authorises no commit and opens no pull request.
