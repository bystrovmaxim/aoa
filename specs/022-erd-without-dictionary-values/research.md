# Research — the dictionary card without value rows

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Date**: 2026-10-25

## The measurements this feature rests on

| What | How it was measured | Value |
| --- | --- | --- |
| Declared values per dictionary in a real model | Fetched `https://admingameoffer.aoa.run/graph-json`, parsed `coordinator_json`, read `properties.values` of every node whose `properties.entity_kind` is `enum` | 7 dictionaries: 93, 26, 8, 5, 5, 3, 3 |
| Property rows painted into one card | Rendered the players domain in a headless browser and counted `is_obsolete: false` in the DOM | 98 rows (93 region values plus 5 from two small dictionaries) |
| Size of the drawing for one domain | The rendered Graphviz SVG's `viewBox` | players `1698 × 6800`, events `1815 × 1593` |
| Where the rows come from | Reading the renderer | one `<TR>` per value plus one per property, built by `valueRows` and interpolated into the card's label |

The second number is the calibration for the success criterion: a domain that only has small dictionaries is 1593 px tall, so a domain whose largest dictionary declares 93 values must land in the same range, not at 6800.

## D1 — The removal lives in the renderer, not in the data

**Decision**: `buildDotSource` stops building value rows. The payload action, its SQL, its schema and the graph export are untouched.

**Rationale**: the specification makes the graph and the payload a promise to consumers (FR-003, FR-004). Filtering at the payload would have been a one-line change in Python, but it would have narrowed a published API to fix a drawing — and every consumer that reads the payload would lose data it never asked to lose. The renderer is the only layer whose contract is "what the card shows".

**Alternatives considered**:
- *Drop `values` from the ERD payload.* Rejected: it makes a rendering decision into an API change, and the payload schema and its tests would have to change with it.
- *Drop `values` from the graph export.* Rejected: the export is the interchange document; the issue explicitly requires that everything is passed in it.
- *Hide the rows in CSS / clip the card.* Rejected: the drawing is an SVG produced by Graphviz, not a DOM tree to style; and a clipped card still costs the layout its height.

## D2 — Nothing replaces the rows

**Decision**: the card keeps its header, its own fields and the arrows that reach it. No badge, no value count, no tint, no marker.

**Rationale**: the maintainer's answer to the clarification question of 2026-10-25. It also keeps FR-006 honest — a count would be a dependency on the number of values and a piece of vocabulary the renderer names.

**Alternatives considered**:
- *A badge with the count ("93 values").* Rejected by the maintainer: it reintroduces exactly the coupling the rule forbids, and it is information the payload already carries for whoever needs it.
- *A marker that the card is a dictionary (icon, tint).* Rejected for the same reason: the card is not required to advertise its kind, and the maintainer accepted that it becomes visually indistinguishable.

## D3 — The payload and the client type keep `values`

**Decision**: `ErdValue` and `ErdEntity.values` stay in the client's type for the ERD payload; the renderer simply does not read them. The field carries a comment saying so.

**Rationale**: the type describes the server's document, not the renderer's appetite. Removing the field would make the type lie about the payload and would invite the next change to remove it from the payload too.

**Alternatives considered**:
- *Remove `values` from the type to prove it is unused.* Rejected: it deletes the description of a field the server still sends, and `noUnusedLocals` does not fire on unused type members anyway.

## D4 — The check is inverted, and it also pins the real rule

**Decision**: `client/scripts/check-erd-dictionary-values.ts` keeps its fixtures and asserts the opposite: no label text, no property text and no code tooltip in DOT or SVG; the dictionary's own fields present; a non-dictionary card unchanged; the reference arrow and its single printed name preserved; a legacy graph still rendered. A new assertion renders the same dictionary twice — once with its four values, once with `values: []` — and requires the two DOT strings to be identical.

**Rationale**: the old assertions were the specification's acceptance test; deleting them would leave the new contract unproven. The equality assertion is the strongest statement of FR-005: if a value leaks back into the drawing, the two strings differ.

**Alternatives considered**:
- *Delete the script and rely on the payload test.* Rejected: the payload test proves data, not drawing, and the closing check run would lose its only assertion about the card.
- *Count `<TR>` elements against an expected number.* Rejected as brittle: it encodes the card's row count rather than the rule.

## D5 — A saved graph renders without a rebuild

**Decision**: no migration, no flag, no schema version bump.

**Rationale**: the renderer ignores a field it never required; a graph that carries values and one that does not both render the same card.

**Alternatives considered**: a `graph schema version` to force rebuilds — rejected: it would invalidate exports to change a drawing.

## D6 — The documents say where the values live

**Decision**: the card contract, the tutorial chapter, the package README and the two earlier requirement pages are amended in place. The tutorial keeps its ERD introduction and its explanation of how a value's properties reach the payload; it loses only the sentences that promise rows and a code tooltip.

**Rationale**: the maintainer's answer to the third clarification question, after the boundary was made explicit: the chapter's other two parts describe the diagram and the payload, both of which are still true.

**Alternatives considered**: deleting the whole chapter — rejected by the maintainer once the content it would take with it was named.

## D7 — The check script keeps its name

**Decision**: `check-erd-dictionary-values.ts` keeps its filename even though it now asserts the absence of value rows.

**Rationale**: the file still checks the handling of dictionary values end to end — graph payload to drawn SVG. Renaming it would churn the check-run script and every page that cites it for no behavioural gain; the file's header comment states the new contract.

**Alternatives considered**: renaming to `check-erd-dictionary-card.ts` — rejected: churn without a rule to enforce.
