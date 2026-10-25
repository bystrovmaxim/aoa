# Feature Specification: The ERD Card Draws No Dictionary Values

**Feature Branch**: `feature/issue-265-erd-without-dictionary-values`

**Created**: 2026-10-25

**Status**: Draft

**Input**: User description: "https://github.com/bystrovmaxim/aoa/issues/265 — Maxitor's ERD card draws no dictionary values, while the graph keeps carrying them."

## Context: what is true today, measured on 2026-10-25

- **A dictionary is drawn as a card of values.** A closed dictionary is an entity whose `entity_kind` is `enum`. The ERD draws it as one card: its own field rows first, then one row per declared value — the value's label, and the value's descriptive properties underneath it. The behaviour is written down as a contract (`specs/016-value-declaration-consistency/contracts/dictionary-card.md` §3) and as requirements (`specs/017-explicit-entity-relations/spec.md` US6, FR-037–FR-040).
- **Codes are already gone from the card; the values are not.** Since #249 the card prints no `code` cell and no `code` / `display_name` field rows; the code survives as a hover tooltip on the value's row and in the payload. The row itself — label plus properties — stayed.
- **On a real model the card is larger than the diagram.** Measured on `https://admingameoffer.aoa.run/graph-json`, the players domain declares three dictionaries:

  | Dictionary | Declared values | Property rows the card draws |
  | --- | --- | --- |
  | `RegionEnumEntity` | 93 | 93 × `is_obsolete`, plus `iso_code` / `parent_code` where declared |
  | `GenderEnumEntity` | 3 | 3 |
  | `PlatformEnumEntity` | 3 | 3 |

  The rendered drawing for that one domain measures **1698 × 6800 px** — about seven viewport heights — and 98 `is_obsolete: false` rows are painted into a single green column. Every other entity in the domain is pushed out of sight at 100 % zoom.
- **Nothing bounds the card.** The renderer maps every declared value unconditionally; there is no threshold, cap or truncation anywhere in the ERD path or in the payload that feeds it.
- **The same model carries seven dictionaries** in four domains, from 3 to 93 values each, so the defect is not one unusual class: it is what any dictionary with real-world reference data does to the view.

## Clarifications

### Session 2026-10-25 — decisions carried from issue #265

- **The value rows leave the card entirely.** A cap ("first N values plus a `+N` row") was considered and rejected: the card draws none. The dictionary stays an entity card with its own fields, its header and its incoming arrows.
- **The data does not leave the graph.** The graph export keeps `properties.values` for every dictionary — `code`, `display_name`, and the value's descriptive properties — and the interchange schema is unchanged. "Everything is passed in the JSON graph" is a requirement, not a concession.
- **The ERD payload keeps carrying the values.** The JSON API is a consumer document; it is not narrowed by a rendering decision. The card is the only layer that stops drawing them.
- **The code tooltip retires with the rows.** #249 attached the code to a tooltip on the value's row; with no row there is nothing to attach it to. The rule "a storage code is never printed on the card" remains true by construction.
- **This is a rendering change.** A graph saved before it renders without a rebuild; no migration, no compatibility flag.
- **The full graph is a separate question.** There a dictionary's `code` and `display_name` still appear as field nodes. Issue #265 does not touch that.
- **The card keeps only what it already had.** Its header, its own field rows and the arrows that reach it stay; nothing is added in place of the value rows — no badge, no count, no tint, no marker (see the clarification below).

### Session 2026-10-25 — clarify

- Q: Once the value rows are gone, how does a reader learn that a card is a dictionary and how many values it declares? → A: Neither. The card carries its fields, its header and the arrows that reach it; it adds no badge, no count and no marker, and is accepted as visually indistinguishable from an ordinary card. The dictionary's identity lives in the graph and in the payload, not in a drawing convention.
- Q: The ERD also shows codes in the hover tooltip of a specialization field ("logins → UserEventLoginSpecEntity"). Does this feature touch it? → A: No. That tooltip belongs to the specialization field, not to the dictionary card, and it stays as it is.
- Q: What happens to the tutorial section that promises values inside the dictionary card? → A: The section stays and loses only that promise — the sentences that say the card lists its values and carries a code tooltip. Its introduction to the ERD and its explanation of how a value's properties reach the payload remain, because they describe the diagram and the payload rather than the card.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Read a domain's ERD without a dictionary wall (Priority: P1)

A reader opens the entity diagram for a domain that contains a region dictionary with 93 declared values. The dictionary appears as a small entity card — its own fields and nothing else — and the other entities, their fields and their relations are readable on one screen.

**Why this priority**: This is the defect. Every other story protects what the fix must not break, but without this one the feature has no value.

**Independent Test**: Render the players domain of the measured model, capture the drawing and the value rows in it, and compare its height with the same domain drawn without dictionary values.

**Acceptance Scenarios**:

1. **Given** a dictionary declaring 93 values, **When** its domain's ERD is rendered, **Then** the card shows no value row — no label, no property, no code — and the drawing is no taller than the domain's entities require.
2. **Given** the same dictionary, **When** the card is inspected, **Then** its own field rows, its header and every incoming reference arrow are still there.
3. **Given** the same domain, **When** the ERD is rendered side by side with the previous build, **Then** every non-dictionary card is unchanged.

---

### User Story 2 - Keep every value in the graph export (Priority: P1)

A consumer that never opens Maxitor reads the graph JSON and finds every declared value of every dictionary, with its code, its label and its descriptive properties, exactly as before.

**Why this priority**: The display decision must not become a data loss. The graph is the interchange document; a value that disappears there is gone for every consumer, not just for one view.

**Independent Test**: Parse the graph export of the measured model and count the values of each dictionary against its declaration.

**Acceptance Scenarios**:

1. **Given** the graph export, **When** a dictionary node is read, **Then** `properties.values` carries every declared value with `code`, `display_name` and the value's `properties`.
2. **Given** the same export, **When** it is validated against the interchange schema, **Then** it is unchanged in shape and still valid.
3. **Given** a value whose property contains `<`, `>` or `&`, **When** the export is read, **Then** the value is carried verbatim.

---

### User Story 3 - Read the same ERD data as before (Priority: P2)

An API consumer calls the entity endpoint and receives the same document it received before the change: the slice, the entities, the field rows, the relations, the groups — and the dictionaries' values, typed and ordered.

**Why this priority**: The payload is a published contract; a rendering change that quietly narrows it would break consumers outside this repository.

**Independent Test**: Call the entity endpoint for a domain with a dictionary and compare the response with the recorded one, field by field.

**Acceptance Scenarios**:

1. **Given** a dictionary in a requested domain, **When** the endpoint answers, **Then** its `values` list is present, typed as `{code, display_name, properties: [{name, value}]}` and in declaration order.
2. **Given** the same response, **When** it is validated against the payload schema, **Then** it still validates.
3. **Given** a dictionary whose values carry no extra properties, **When** the endpoint answers, **Then** each value carries an empty property list, not an absent one.

---

### User Story 4 - Read the card's contract as it now stands (Priority: P3)

A maintainer reading the card contract, the tutorial and the package documentation finds the behaviour the product actually has: a dictionary card of fields with no values, a graph that still carries them and a payload that still serves them.

**Why this priority**: The documents currently describe value rows as required behaviour. Left as they are, the next reader would restore the defect as a correction.

**Independent Test**: Read the three documents and check each statement about dictionary values against a rendered card, a graph export and an endpoint response.

**Acceptance Scenarios**:

1. **Given** the card contract, **When** it is read, **Then** it states that no value row is drawn and that the graph and the payload keep the values.
2. **Given** the tutorial chapter on dictionaries, **When** it is read, **Then** it no longer promises values inside the card.
3. **Given** a specification that previously required the value row, **When** it is read, **Then** the requirement is superseded in place rather than contradicted elsewhere.

---

### Edge Cases

- **A dictionary with one value.** The card must look exactly like the card of a dictionary with 93 values: same fields, same height. The count may influence nothing.
- **A dictionary of a domain reached only as a one-hop neighbour.** Turning the neighbour toggle on must not reintroduce value rows for a dictionary that belongs to another domain.
- **A graph export that predates the change.** It carries values in the same shape; the card must render without a rebuild and without an error.
- **A graph export that carries no values at all.** The card must render, with its fields, and must not fail or draw an empty row.
- **A dictionary whose values carry properties with markup characters.** Nothing is printed for them now; the SVG must stay valid and the field rows must still escape their own text once.
- **A dictionary selected from two different hosts, one of them out of the current slice.** Both arrows must still be drawn; no value rows appear for either.
- **A dictionary used only as a specialization vocabulary.** It has no incoming selection arrow; its card must still be drawn, with its fields — and it is identified as a dictionary by the graph and the payload, not by anything on the card.
- **A non-dictionary entity whose field is named `value` or `code`.** Its rows must be unchanged: the rule is about the kind, not about names.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The ERD card MUST draw no row for a dictionary's declared values — no value label, no value property and no storage code.
- **FR-002**: The card MUST keep drawing the dictionary's own field rows, its header and its incoming reference arrows, and MUST add nothing in place of the value rows — no badge, no count, no tint, no marker.
- **FR-003**: The graph export MUST keep every declared value with its `code`, its `display_name` and its descriptive properties; no value, code or property may be dropped on the way into the export.
- **FR-004**: The ERD payload MUST keep `values` in its present shape and order — one typed item per declared value, `{code, display_name, properties: [{name, value}]}`, an empty property list when a value declares none.
- **FR-005**: Rendering MUST NOT depend on the number of declared values: a dictionary with one value and a dictionary with ninety-three MUST draw the same card given the same fields.
- **FR-006**: The renderer MUST name no dictionary, no kind and no field, and MUST introduce no threshold, cap, count or "first N" rule.
- **FR-007**: A non-dictionary entity's card MUST be unchanged — the same field rows, keys, types and reference markers as before the change.
- **FR-008**: A dictionary that arrives with no values — an older export, an excluded model — MUST render its fields without an error and without an empty row.
- **FR-009**: The per-value code tooltip introduced by #249 MUST retire together with the value rows; no storage code may be printed or attached to a row the card no longer draws.
- **FR-010**: The card contract and the earlier requirement that mandated the value row MUST be superseded in place, so the repository states one behaviour rather than two.
- **FR-011**: Every document that shows or promises values inside the card MUST be reconciled in the same change — the card contract, the dictionary chapter of the Maxitor tutorial, the package README and the client README. The tutorial chapter keeps its introduction to the ERD and its explanation of the payload's property shape, and loses only the sentences that promise value rows and a code tooltip on the card.
- **FR-012**: A graph saved before this change MUST render without a rebuild, and no migration or compatibility flag may be introduced.

### Key Entities

- **Dictionary**: A closed dictionary — an entity whose kind is `enum` — that declares every value the model accepts. It keeps its identity, its domain, its fields and its references.
- **Declared value**: One member of a dictionary: an authoritative `code`, a `display_name` and optional descriptive properties. It is carried by the graph and by the payload; it is no longer drawn.
- **Dictionary card**: The ERD node that represents a dictionary. After this change it consists of the header, the dictionary's own field rows and the arrows that reach it.
- **ERD payload**: The per-domain document the entity endpoint returns: slices, entities, field rows, relations and groups. It keeps the values it carries today.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In the measured model's players domain, the ERD drawing falls from 1698 × 6800 px to 1698 × 2075 px — under a third of its former height, and no longer set by a single card. Measured after the same change, the other three domains are 1815 × 1423, 2283 × 1242 and 3383 × 1667, and the all-domains view is 4400 × 2777, so every projection is laid out by its entities rather than by its largest dictionary.
- **SC-002**: 100 % of the dictionaries in the measured model — seven of seven, from 3 to 93 values — draw zero value rows.
- **SC-003**: 100 % of declared values remain in the graph export: 93 of 93 for the region dictionary, 26 of 26 for the industry dictionary, and so on for all seven.
- **SC-004**: 100 % of dictionaries keep their `values` list in the entity endpoint's response, in declaration order, with the typed property shape.
- **SC-005**: Every non-dictionary card in the measured model renders identically to the previous build — same rows, same markers, same arrows.
- **SC-006**: A dictionary card's height equals the height of an ordinary card with the same fields, for dictionaries of 1, 3, 26 and 93 values alike.
- **SC-007**: A reader who is shown the domain before and after names the dictionary as the change and reports no missing entity, field or relation.

## Assumptions

- The removal is complete rather than partial; the maintainer rejected the cap variant in the conversation that produced #265.
- The maintainer accepts that a dictionary card becomes visually indistinguishable from an ordinary entity card; the dictionary's identity is carried by the graph payload, not by a drawing convention.
- No one consumes the rendered card programmatically; the graph export and the entity endpoint are the consumer surfaces, and both keep the values.
- The payload's `values` becomes unused by the card but used by others — an unused field in the payload is acceptable and is not "dead data".
- The reference arrows to a dictionary are unaffected: a selection still shows where it points.
- The measured model (`admingameoffer.aoa.run`) is representative; the corpus's smaller dictionaries (3, 5, 8, 26 values) behave the same way.

## Out of scope

- **The full graph.** A dictionary's `code` and `display_name` still appear there as field nodes; that display question is separate and remains open.
- **The specialization field's tooltip.** It lists the codes of the axis's alternatives and stays as it is: it belongs to the field, not to the dictionary card.
- **The payload schema, the interchange schema and the graph format.** None of them changes.
- **Truncation, collapse and pagination variants.** Rejected for this feature; the card draws no values.
- **Any dictionary-specific vocabulary in the renderer or its checks** — no dictionary name, kind name, field name or threshold may appear there. Documents name dictionaries because they are documentation; the drawing code must not.
- **Rebuilding existing exports.** The change renders saved graphs as they are.

## Dependencies

- The card as it stands was delivered by #241, #244 and #249; this feature removes the last of what #244 introduced and keeps what #249 fixed.
- The relationship work of #259 and #261 is orthogonal: it changes how selections reach a dictionary, not how a dictionary's card is drawn.
- The evidence in #265 is the measured model and the recorded drawing height; both are reproduced by the domain used in the first user story.

## Verification

- The check that today asserts the printed value rows is inverted: the rendered drawing must contain no value row, while the payload that drives it still carries the values.
- A graph-level check asserts that a real graph export still carries every value with its code, its label and its properties — the requirement that "everything is passed in the JSON graph".
- Adversarial pairs: restoring one value row must fail the drawing check while the graph check still passes; dropping values from the export must fail the graph check while the drawing check still passes. Each is reintroduced in isolation and restored.
- The existing card-containment check runs unchanged, so the card's fills still stop at its rounded contour.
- The success criteria that name the measured model are verified against that model in one walk: all four domains and the all-domains view render with zero value rows across the seven dictionaries, the entity endpoint still answers 93, 26, 8, 5, 5, 3 and 3 values for them, the players-domain drawing measures 1698 × 2075 px against 1698 × 6800 before the change, and a non-dictionary card is compared against a golden captured before the change.
- The documentation, the check run taken to zero and the changelog article follow the usual tail; the two accepted remarks of the check run are not acted on.
