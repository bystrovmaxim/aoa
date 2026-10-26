# Feature Specification: Entity Kinds Travel with the Graph, and the ERD Shows Every Line It Should

**Feature Branch**: `feature/issue-239-entity-kinds-travel-with-graph`

**Created**: 2026-10-26

**Status**: Draft

**Input**: User description: "GitHub issue #239 (https://github.com/bystrovmaxim/aoa/issues/239), branch feature/issue-239-entity-kinds-travel-with-graph: entity kinds travel with the graph (word + display name declared on AOA kind bases), Maxitor ERD gets a strict-accordion filter panel with a Kinds section, kind icons, every line between two on-screen tables drawn, one line per association with crow's-foot ends and roles, cleaner type column, line hover with field marking, click to copy names. The visual baseline is the production Maxitor look; the mockup fixes only layout and behaviour."

## Context: what is true today, checked on 2026-10-26

- **The wire closes the set of kinds.** `packages/aoa-action-machine/src/aoa/action_machine/graph/graph_json_schema.py` lists `entity.properties.entity_kind` as an `enum` of six words (`core`, `assoc`, `detail`, `spec`, `enum`, `state`) with the remark that `state` is "admitted for completeness". A second, conditional branch requires `values` when the kind is `enum`; that branch is about AOA's own dictionaries and stays.
- **The word comes from the kind base's name.** `entity_kind_of` (`graph/nodes/entity_graph_node.py`) walks the MRO to the class that inherits `BaseEntity` directly and returns its name without `Base` and `Entity`, lower-cased. `EntityGraphNode` writes it as `properties.entity_kind`. No display name exists anywhere.
- **Maxitor already carries the kind to the ERD — and stops there.** The `entity` table has `entity_kind VARCHAR NOT NULL`; `list-entities` already returns `entity_kind` on every entity (required, `minLength: 1` in `list_entities_action_schema.py`); `ErdEntity` in `client/src/lib/buildDotSource.ts` already has `entity_kind?`. Nothing filters by it and nothing draws it. Issue #239 §5 still lists "add `entity_kind` to `list-entities`" — that part is already done.
- **A graph without kinds cannot be loaded.** Two paths insert `entity` rows — `_fill_table_entity` and the bulk insert in the graph build of `duckdb_graph_resource.py` — and both read `["entity_kind"]`, raising `KeyError` when a producer omits it.
- **Maxitor already names one kind word.** `list_entities_action.py` hides the `code` and `display_name` rows of a dictionary card with `if entity.get("entity_kind") == "enum"`. The rows it hides are the ones a table declaring `values` supplies, so the condition can be the data (`values` declared) instead of AOA's word.
- **Two legends would sit on top of each other.** `DomainLegend` and `NodeTypeLegend` both use `CollapsibleLegendPanel`, whose panel is pinned to `top: 12px; left: 12px`. The panel's width follows its content (`minWidth 132`, `maxWidth 260`); on the production ERD with four domains it measures 146 CSS px (291 px on the 2× screenshot `docs/assets/maxitor-domain-erd.png`); on the reference graph's `EventsDomain` ERD the same panel is 148 CSS px, because `ShowcasesDomain` needs a 98 px label — the width this specification fixes is 148 px, so that graph's names are not cut.
- **Lines disappear between tables that are on screen.** Reproduced on `https://maxitor.aoa.run` with the source `https://admingameoffer.aoa.run/graph-json` (26 entity nodes, 46 relation edges, 4 domains):
  - `relation_sql` in `list_entities_action.py` keeps a relation only when one end belongs to the slice's own domain; the dictionary-reference half has the same condition. On the `EventsDomain` ERD with 1-hop on, `PlayerCoreEntity` ↔ `ShowcaseCoreEntity`, `GameCoreEntity` ↔ `EnergyResourceCoreEntity` and `PlayerCoreEntity` → `GenderEnumEntity` have no line, though both ends are drawn and the cards list the FK rows. `OffersDomain` loses 2 such pairs, `PlayersDomain` 7, `ShowcasesDomain` 3.
  - `parent_entity_sql` keeps a generalization only when both ends are in the domain: `PlayersDomain` and `ShowcasesDomain` each lose three extension → head lines of `UserEventCoreEntity`, while its specialization container is drawn.
  - A specialization head has no line to the dictionary of its axis. `UserEventCoreEntity` specializes by `kind` with values from `EventKindEnumEntity`; both are on the `EventsDomain` ERD and nothing joins them. The graph has no relation or reference edge between them: the dictionary is named only as `dictionary_qualname` on the head's `entity_specialization` edges, and the ERD draws no edge for an axis. The reference graph has exactly one such axis.
  - In the all-domains ERD each enabled domain contributes its own slice and the client merges them; a line whose ends come from two different slices exists in neither. With `PlayersDomain` and `ShowcasesDomain` on and `OffersDomain` off, `OfferCoreEntity` and `IndustryEnumEntity` are both drawn with no line between them, and this one survives a per-slice fix.
- **Every relation field is its own line.** `buildDotSource.ts` draws one Graphviz edge per relation row with `field (cardinality)` in the middle and default arrowheads; `source_cardinality` / `target_cardinality` are in the payload but unused. The graph carries `inverse_field` / `inverse_entity_id` on each relation, and `entity_relation_edges` stores both. On the admingameoffer graph, pairing each field with its declared inverse turns 46 relation fields into 34 associations; every declared inverse finds its partner; only `OfferRequestCoreEntity` ↔ `OfferRequestItemDetailEntity` keeps two associations (`offers` / `offer_request`, and `chosen_offer` without an inverse).
- **The type column repeats the drawing.** A field that references a dictionary gets a green `→ GenderEnumEntity` after its type (`reference_qualname`), and every FK row's type is `FK -> <Table>`, built by the server (`'FK -> ' || target.label`). Type cells are left-aligned. No test and no documentation page pins the `FK -> ` text.
- **The header is one cell; its rounding is ours.** Each table is a Graphviz HTML-label table with `STYLE="ROUNDED"` and one header cell filled with the domain colour. Graphviz paints that fill as a plain rectangle; `client/src/lib/containNodeFills.ts` trims every fill of a card to the card's rounded contour, taking the radius from the drawn outline, and that is why the top corners are rounded on production.
- **Small tables are stubs.** A table is as wide as its widest content. Rendered with the production markup and the client's own Graphviz (`@hpcc-js/wasm-graphviz`), `GenderEnumEntity` (two rows) is 122.4 pt wide and a table shaped like `NotificationEntity` (four rows) 138.9 pt, while the mockup's card — the proportion the maintainer chose — is 168 px for a 9 px field font and a 9.5 px header font, which is about 205–212 pt at production's 11 pt fields and 12 pt header. With a 210 pt minimum on the header cell both tables come out 212 pt wide, their heights unchanged, and the header fill is still the plain rectangle the trimming step rounds.
- **Lines have no hover of their own.** Only a table reacts: hovering it keeps its own lines and dims the rest. A line is 1 px wide and hard to catch. Nothing on the ERD copies a name.
- **Specialization containers are outline only.** A container is a Graphviz cluster with `style="rounded,dashed"`, `color="#94a3b8"` and the default 1-point pen; its inside is not filled, so it is hard to tell from the canvas around it. Probe on the client's WASM Graphviz: `style="rounded,dashed,filled"` with `fillcolor="#0f172a0d"` and `penwidth=2` comes out as `fill="#0f172a" fill-opacity="0.05"` and `stroke-width="2"` — the canvas's dots still show through. Neither `sanitizeGraphvizSvgOverlays.ts` nor `containNodeFills.ts` touches clusters.
- **Grey is a domain colour today.** The domain palettes (`_EXTRA_LIST_DOMAIN_COLORS` in `list_domains_action.py`, `ENTITY_COLORS` in `client/src/lib/enrichErdData.ts`) are saturated hues with exactly one grey, slate `#64748b`, at position 8.
- **The client's unit tests are in the check run.** `scripts/run_checks_with_log.sh` runs `npm ci && npm run build` and `npm test` for the client; no browser is available to the run.
- **Documentation states the six as the vocabulary**: `docs/tutorials/step-20-entity.md` (line 245), `docs/tutorials/step-26-maxitor.md` (line 400), `docs/reference/glossary.md` (line 127), `docs/reference/intents-and-invariants.md` (line 353).
- **A mockup exists for layout and behaviour only.** The interactive mockup agreed with the maintainer fixes where things are, how they behave and what appears; it is a hand-made imitation. The visual baseline is the production Maxitor look (Graphviz layout and fonts, table proportions, MUI legend chrome), and anything this specification does not name stays as it is.

## Clarifications

### Session 2026-10-26

The decisions were made with the maintainer on the interactive mockup and in issue #239 before this specification was written; `/speckit-clarify` found no open question that needs the maintainer. Three inconsistencies it found were corrected in place: the open panel section is not part of the remembered filter state (FR-009 and Key Entities now agree); hovering a line without an inverse marks every key row of the target (Edge Cases, FR-029); a 1-hop neighbour stays when only its linking table's kind is hidden (Edge Cases, FR-015).

- Q: How wide must a small table be, so that it is not a stub like `GenderEnumEntity`? → A: As wide as the mockup's card, in production units: a 210 pt minimum on the header cell, 212 pt with the border; wider tables keep their width (FR-033, Context).
- Q: Where does the kind icon sit in the header, and on what? → A: Right before the table name, as a white outline with no background (chosen on the mockup over "at the left edge in a white square") (FR-017).
- Q: Is the hollow triangle right for `spec`? → A: No — the maintainer rejected it and chose two stacked layers over a fork and a split, drawn at 80 % so they do not look larger than the other icons (FR-016).
- Q: What happens when the pointer rests on a field that has relations? → A: Every line of that field is emphasised like a hovered line, and the fields at their ends are marked (FR-029).
- Q: Should a specialization head be joined to the dictionary of its axis? → A: Yes — one line from the head to the dictionary, like a dictionary reference, whenever both are on screen (`UserEventCoreEntity` → `EventKindEnumEntity`) (FR-021).
- Q: What is the reference for the look? → A: Production; the mockup decided layout and behaviour only (FR-038).
- Q: How should a specialization container stand out from the canvas? → A: Still see-through, half a tone darker than the canvas, with its outline one pixel thicker (FR-020).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Every line between two tables on screen is drawn (Priority: P1)

A user looking at any ERD — one domain, one domain with its 1-hop neighbours, several domains in any toggle combination — sees a line wherever the graph joins two tables that are on screen, whatever brought each table there.

**Why this priority**: A missing line is wrong information. The user reads "these tables are unrelated" while both cards even list the foreign key.

**Independent Test**: Load the admingameoffer graph, open each domain with 1-hop on and the all-domains view with every pair of domains on, and compare the lines on screen with the graph's relations, references and generalizations between the tables on screen.

**Acceptance Scenarios**:

1. **Given** the `EventsDomain` ERD with 1-hop on, **When** it is drawn, **Then** `PlayerCoreEntity` and `ShowcaseCoreEntity` are joined by a line, as are `GameCoreEntity` and `EnergyResourceCoreEntity`, and `PlayerCoreEntity` and `GenderEnumEntity`.
2. **Given** the `PlayersDomain` ERD with 1-hop on, **When** it is drawn, **Then** each extension of `UserEventCoreEntity` on screen has its generalization line to it.
3. **Given** the all-domains ERD with `PlayersDomain` and `ShowcasesDomain` on and `OffersDomain` off, **When** it is drawn, **Then** `OfferCoreEntity` and `IndustryEnumEntity` are joined by a line.
4. **Given** any of these views, **When** a table is filtered away, **Then** no line ends at it.
5. **Given** the `EventsDomain` ERD, where `UserEventCoreEntity` specializes by `kind` with values from `EventKindEnumEntity`, **When** it is drawn, **Then** one line joins `UserEventCoreEntity` to `EventKindEnumEntity`, with the role `kind` and a bar at the dictionary's end.

---

### User Story 2 - Filtering the ERD by entity kind (Priority: P1)

A user switches whole kinds of tables on and off — for example hides every dictionary to see the core model — from one filter panel that also holds the domain toggles.

**Why this priority**: It is the reason for the issue: the kind is in the data but cannot be used.

**Independent Test**: Open an ERD whose graph has several kinds, switch one kind off, and check that its tables and their lines disappear and come back.

**Acceptance Scenarios**:

1. **Given** an ERD whose graph has more than one kind, **When** it opens, **Then** one filter panel shows two sections, Domains and Kinds; Domains is open, Kinds is folded; every kind is on.
2. **Given** the Kinds section is opened, **When** the user opens it, **Then** Domains folds; opening Domains again folds Kinds; clicking the open section's header folds it and leaves both folded.
3. **Given** a kind is switched off, **When** the ERD is redrawn, **Then** its tables, their lines and their places in specialization containers disappear; a container with fewer than two members left disappears.
4. **Given** a domain and a kind are both switched off, **When** the ERD is redrawn, **Then** a table is shown only if both its domain and its kind are on.
5. **Given** the user leaves the diagram and comes back, **When** it is drawn again, **Then** the kinds switched off are still off.
6. **Given** a graph with only one kind, **When** the ERD opens, **Then** the Kinds section is not shown.
7. **Given** many domains, **When** the panel is taller than the room above the zoom toolbar, **Then** the panel stops above the toolbar and scrolls inside itself.

---

### User Story 3 - A kind is named by the graph, for any producer (Priority: P1)

A model author's kinds reach the viewer with their own names, and a graph from a producer that is not AOA — or an AOA model with a kind AOA does not ship — loads, shows its kinds and filters them without any change to Maxitor.

**Why this priority**: The fixed list on the wire is false for every other producer, and a name table in the viewer would make their kinds second-class.

**Independent Test**: Export the AOA model and check each entity's word and name; load a hand-built graph with the kinds `aggregate`, `event` and `link` and see three Kinds rows named from the graph.

**Acceptance Scenarios**:

1. **Given** the six AOA kind bases, **When** a model is exported, **Then** each Entity row carries its word and its name: `core`/Core, `assoc`/Association, `detail`/Detail, `spec`/Specialization, `enum`/Enumeration (and `state`/State, which never appears as an Entity row).
2. **Given** a model that declares its own kind base `BaseAggregateEntity` with the name "Aggregate", **When** it is exported, **Then** its rows carry `aggregate`/Aggregate and the graph is valid.
3. **Given** a kind base that declares no name, an empty one, or only one inherited from a mixin, **When** its class is created, **Then** AOA refuses it with a message naming the class.
4. **Given** a graph whose `aggregate` rows carry the name "Aggregate root" and whose `event` and `link` rows carry no name, **When** Maxitor loads it, **Then** the Kinds rows read "Aggregate root", "Event" and "Link".
5. **Given** a graph whose Entity rows carry no kind at all, **When** Maxitor loads it, **Then** it loads, and those tables appear under the kind "Unknown".

---

### User Story 4 - Reading a table's kind at a glance (Priority: P2)

A user tells a core table from a link table or a dictionary from across the diagram, by an icon right before every table's name and the same icon in the Kinds rows.

**Why this priority**: Filtering is only half of the use; the kind also has to be visible where the tables are.

**Independent Test**: Open the ERD of a model with all AOA kinds and check each header's icon against its kind; open a graph with unfamiliar kinds and check their monograms.

**Acceptance Scenarios**:

1. **Given** a table of a kind Maxitor knows, **When** it is drawn, **Then** its header shows that kind's pictogram right before the table name, drawn in white outline with no background of its own, and the icon and the name are centred together.
2. **Given** a table of a kind Maxitor does not know, **When** it is drawn, **Then** the icon is the first two letters of the kind's word, in white.
3. **Given** the Kinds section, **When** it is open, **Then** each row shows the same pictogram or monogram in a grey disk of the same size and weight as a domain's disk, and the kind's name.
4. **Given** any ERD, **When** it is drawn, **Then** no domain is grey, and a header's colour is still its domain's.
5. **Given** a header with the icon, **When** it is drawn, **Then** its top corners are rounded exactly as today.
6. **Given** a specialization container, **When** it is drawn, **Then** its inside is a see-through tint half a tone darker than the canvas and its dashed outline is one pixel thicker than today.

---

### User Story 5 - One line per association, read the ERD way (Priority: P2)

A user sees one line where the model has one association, with how many of each side at its ends and the name each side is given written next to it.

**Why this priority**: Two lines for one association, each with its label in the middle, double the clutter and hide which field is the inverse of which.

**Independent Test**: Open an ERD with a field and its declared inverse and check that one line joins the two tables with the right ends and roles; check that a second, independent association between the same tables stays a separate line.

**Acceptance Scenarios**:

1. **Given** `PlayerCoreEntity.showcase` (one) and its inverse `ShowcaseCoreEntity.players` (many), **When** the ERD is drawn, **Then** one line joins the two tables, with a bar and the role `showcase` at `ShowcaseCoreEntity` and a crow's foot and the role `players` at `PlayerCoreEntity`, and no label in the middle.
2. **Given** `OfferRequestCoreEntity.chosen_offer`, which has no inverse, next to the pair `offers` / `offer_request` between the same tables, **When** the ERD is drawn, **Then** two separate lines join them.
3. **Given** the admingameoffer graph, **When** all its tables are drawn, **Then** its 46 relation fields give 34 lines.
4. **Given** a generalization, **When** it is drawn, **Then** it keeps its hollow triangle and is never merged with an association.

---

### User Story 6 - Following a line (Priority: P2)

A user who hovers over a line sees it stand out and sees, in both tables, the fields it stands for; a user who hovers over a field sees every line of that field stand out.

**Why this priority**: Where lines cross, the user cannot tell which one goes where, nor which column it is about.

**Independent Test**: Hover a line between two tables and check the line and the marked rows; move away and check that everything is restored.

**Acceptance Scenarios**:

1. **Given** the pointer comes within about 5 px of a line, **When** it rests there, **Then** the line becomes thicker and darker, is drawn above every line it crosses, and its end marks and roles follow.
2. **Given** a hovered line of a paired association, **When** it is hovered, **Then** in both tables the rows of its two fields have bold, darker text; no cell changes fill, border or size.
3. **Given** a hovered line of a relation without an inverse, **When** it is hovered, **Then** the field's row in its table and the key row it points at in the other table are marked.
4. **Given** a field shown both as its own row and as an FK row, **When** its line is hovered, **Then** both rows are marked.
5. **Given** the pointer leaves the line, **When** it leaves, **Then** the line and the rows return to their normal look.
6. **Given** a field that takes part in several lines (for example `UserEventCoreEntity.id`, pointed at by its relations without an inverse, or `PlayerCoreEntity.showcase`), **When** the pointer rests on its row, **Then** every one of those lines is thicker, darker and on top, and the fields at their ends are marked; moving off the row restores them.

---

### User Story 7 - A type column that says only the type (Priority: P3)

A user reads the field names down the left of every table and the types down the right, without the arrows and prefixes that repeat what the lines already say.

**Why this priority**: It is a reading improvement, not new information.

**Independent Test**: Open any ERD and read the type cells.

**Acceptance Scenarios**:

1. **Given** a field that references a dictionary, **When** its row is drawn, **Then** its type cell shows the type alone, with no `→ <Dictionary>` after it.
2. **Given** an FK row, **When** it is drawn, **Then** its type cell shows the target table's name alone, with no `FK -> ` before it.
3. **Given** any row, **When** it is drawn, **Then** its type is aligned to the table's right edge.
4. **Given** a small table such as `GenderEnumEntity` (two rows, 122 pt wide today), **When** it is drawn, **Then** it is as wide as the minimum (212 pt), and a table wider than that keeps its own width.

---

### User Story 8 - Copying a name (Priority: P3)

A user clicks a table's name or a field's name and has it in the clipboard, to paste into code, a ticket or a search.

**Why this priority**: A convenience that saves retyping long class names.

**Independent Test**: Click a table name and a field name and paste; drag the canvas and check that nothing was copied.

**Acceptance Scenarios**:

1. **Given** a table name in a header, **When** the user clicks it, **Then** that name is in the clipboard and a short message "Copied <name>" appears near the bottom of the canvas for about 1.5 s.
2. **Given** a field name, **When** the user clicks it, **Then** that field name is copied the same way.
3. **Given** the user drags the canvas starting on a name, **When** they release, **Then** nothing is copied.
4. **Given** a browser that refuses the clipboard, **When** the user clicks a name, **Then** the name is selected and the message tells them to press Cmd/Ctrl+C.

### Edge Cases

- **A kind word with no name and unusual characters** (`in_flight`): shown with its first letter capitalised, `In_flight`, and a monogram `in`.
- **Rows of one kind that disagree on its name** (only possible from a non-AOA producer): one name is chosen the same way every time — the smallest non-blank name — so the legend does not flicker between loads.
- **A kind base declared by a user model** (a seventh kind): exported, validated, listed, named and filterable like the six; it gets a monogram unless Maxitor's icon dictionary knows its word.
- **Only one kind in the graph**: no Kinds section; the panel shows Domains only, still without a title.
- **Every table filtered away**: the existing empty-canvas message appears; the panel stays usable.
- **A relation whose inverse points at a table that is filtered away**: the line is not drawn; nothing is marked.
- **A relation without an inverse into a table with several key rows**: hovering its line marks every key row of that table.
- **A 1-hop neighbour whose only link to the domain is through a table of a hidden kind**: it stays on screen, as a neighbour stays today when its linking table's domain qualifier is switched off; only its line to the hidden table goes.
- **A one-to-one or many-to-many association**: drawn as one line; the same association always comes out with the same direction, so the drawing does not change between loads.
- **Several associations between the same two tables**: each is its own line, routed apart; none is merged back into another.
- **A self-relation** (a table pointing at itself): drawn as today, with its ends and roles.
- **A long table or field name in the panel**: cut with an ellipsis; the full name in a tooltip; the panel never widens.
- **A narrow phone screen**: the panel starts folded as a "Filter" pill; opened, it shows the sections directly, without the word "Filter".
- **A click that ends a pan**: never copies.

## Requirements *(mandatory)*

### Functional Requirements

**Kinds in the graph (AOA)**

- **FR-001**: Each AOA kind base MUST declare its display name in its own class body; the six MUST be Core, Association, Detail, Specialization, Enumeration and State.
- **FR-002**: Creating a kind base without a non-empty display name declared in its own body MUST be refused at class creation, naming the class and the missing declaration. Every existing declaration check MUST stay as it is.
- **FR-003**: The export MUST write each Entity row's display name next to its kind word.
- **FR-004**: The graph format MUST require the kind word as a non-empty lowercase word without enumerating its values, and MUST accept but not require the display name as a non-empty string.

**Kinds in Maxitor**

- **FR-005**: Loading a graph whose Entity row has no kind or a blank kind MUST succeed and store the kind as `unknown`; a missing or blank display name MUST be stored as absent; a non-string value in either MUST fail the load with a message naming the node.
- **FR-006**: Maxitor MUST offer a listing of the kinds present in the loaded graph, one row per kind, ordered by the word, each with a display name: the graph's name when present (the smallest non-blank one when rows disagree), otherwise the word with its first letter capitalised. Maxitor's own model rows are excluded the way the domain listing excludes them.
- **FR-007**: Nothing in Maxitor MUST decide which kinds exist or what they are called; only the icon dictionary of FR-016 may name kind words, and removing it MUST leave every kind listed, named and filterable. A dictionary card's handling MUST follow from the data (the table declares `values`), not from the word `enum`.

**The filter panel**

- **FR-008**: The ERD MUST show one filter panel, 148 px wide whatever its content, holding a Domains section and a Kinds section, with no panel title on wide screens.
- **FR-009**: The sections MUST behave as a strict accordion: at most one open; Domains open when the diagram mounts; opening one folds the other; clicking the open one folds it.
- **FR-010**: A section header MUST show only its chevron and its name — no counters.
- **FR-011**: A label that does not fit MUST be cut with an ellipsis and show its full text in a tooltip; a label that fits MUST have no tooltip.
- **FR-012**: The panel MUST end above the zoom toolbar and scroll inside itself when its rows do not fit; scrolling the panel MUST NOT pan the canvas.
- **FR-013**: On a narrow screen the panel MUST start folded as a pill labelled "Filter"; opened, it MUST show the sections without the word "Filter", with its close control at the end of the first section's header.
- **FR-014**: The Kinds section MUST list one row per kind in the loaded graph, all on at first, labelled with the kind's display name, and MUST NOT be shown when the graph has at most one kind. The Domains section MUST keep today's rows, accents and toggles.
- **FR-015**: A table MUST be shown only when its domain (or 1-hop qualifier) and its kind are both on; lines and specialization containers MUST then be pruned once, so no line ends at a hidden table and no container holds a hidden member. Hiding a table MUST NOT hide the 1-hop neighbours it brought. The kinds switched off MUST be remembered per diagram, like the domain toggles.

**Kind icons and colours**

- **FR-016**: Maxitor MUST draw a pictogram for the kind words it knows — `core` a table, `assoc` a chain link, `detail` a branch from an owner, `spec` two stacked layers (a layer over its base; drawn at 80 % of the box with the same line weight, because it fills its box edge to edge and would otherwise look larger than its neighbours), `enum` a bulleted list, `state` a ring, `unknown` a question mark — and the word's first two letters for any other word.
- **FR-017**: Every ERD table header MUST show its kind's icon immediately before the table name, in white outline on the header's own colour with no background of its own, the icon and the name centred together; the header's domain colour and rounded top corners MUST stay unchanged; the icon's tooltip MUST be the kind's display name.
- **FR-018**: Each Kinds row MUST show the icon in a filled disk of the same size and stroke as a domain disk, in one grey for every kind.
- **FR-019**: No domain MUST be drawn grey: the one grey in the domain palettes MUST be replaced by a non-grey hue that is not already in them, and only the domain at that position changes colour.
- **FR-020**: A specialization container MUST stay see-through but be half a tone darker than the canvas around it (a dark tint of about 5 % opacity, the canvas pattern still visible), and its dashed outline MUST be one pixel thicker than today (2 instead of 1); its colour, dash, rounding, margin and label stay as they are.

**Every line between tables on screen**

- **FR-021**: For every set of tables the ERD can show, every relation, dictionary reference and generalization of the graph between two tables on screen MUST be drawn exactly once, whatever brought each table onto the diagram, and no line MUST end at a table that is not on screen. A specialization axis whose dictionary table is on screen MUST be drawn as one line from the head to the dictionary, read like a dictionary reference: the axis field as the role and a bar at the dictionary's end, a crow's foot at the head's end.
- **FR-022**: A table card that lists an FK row MUST have the line for it whenever the target table is on screen.

**One line per association**

- **FR-023**: A relation field and its declared inverse MUST be drawn as one line; a relation without an inverse MUST be its own line, even next to another association between the same tables; generalizations MUST NOT be merged.
- **FR-024**: Each end of an association line MUST show the cardinality of the table it touches in crow's-foot notation (a bar for one, a crow's foot for many) and the role that table plays, written next to it; the middle label MUST NOT be drawn for associations. A relation without an inverse keeps today's reading for its far end. Optionality is not drawn.
- **FR-025**: The same association MUST always be drawn in the same direction (the table holding the "one" side's field first; for one-to-one or many-to-many, the table with the smaller id first).
- **FR-026**: Several associations between the same two tables MUST be drawn as distinct lines that do not share a path.

**Line hover**

- **FR-027**: A line MUST react to the pointer within about 5 px of its path.
- **FR-028**: A hovered line MUST become thicker (about 1 → 2.4 px) and darker, with its end marks and roles following, MUST be drawn above every line it crosses, and MUST return to normal when the pointer leaves; the change MUST be immediate for users who prefer reduced motion.
- **FR-029**: A hovered line MUST mark, in both tables, the rows it stands for — the two fields of a paired association, or the field and every key row of the table it points at — including a field shown both as its own row and as an FK row; the mark MUST be bold, darker text only, with no change to any cell's fill, border or size. Conversely, hovering a table row whose field takes part in one or more lines MUST give every one of those lines the hovered look of FR-028 and mark the rows at their ends the same way; a key row counts for the relations without an inverse that point at its table. Leaving the row MUST restore them.
- **FR-030**: Today's table hover (keeping a table's lines and dimming the rest) MUST keep working, and panning by dragging MUST NOT be disturbed.

**Type column**

- **FR-031**: A type cell MUST NOT show a `→ <target>` suffix or an `FK -> ` prefix; an FK row's type MUST be the target table's name.
- **FR-032**: Every type cell MUST be aligned to the right edge of its table.
- **FR-033**: Every ERD table MUST be at least 212 pt wide (a 210 pt minimum on its header cell plus its border), so a table with a short name and few rows is not a stub; a table whose content is wider keeps its natural width, and no table's height changes. The header's rounded top corners MUST still come out of the existing fill-trimming step.

**Copy**

- **FR-034**: A click on a table name or a field name MUST copy exactly that name and show "Copied <name>" near the bottom of the canvas, above the zoom toolbar, for about 1.5 s; types, badges and line labels MUST NOT copy.
- **FR-035**: A press that moves more than about 4 px before release MUST NOT copy.
- **FR-036**: When the clipboard is refused, the name MUST be selected and the message MUST say to press Cmd/Ctrl+C.
- **FR-037**: Copyable names MUST show a copy cursor and a "Click to copy" tooltip; a tap MUST copy on touch screens.

**Baseline and tail**

- **FR-038**: Everything this specification does not name MUST look and behave as on production today; the mockup decides layout and behaviour, never fonts, sizes, spacing or the drawing engine's look.
- **FR-039**: The work MUST end with the three steps of Principle VI, in order: the check run taken to zero, the documentation (the pages listed in Context, the Maxitor README and the new component's README, with every case as a script and a notebook), and one changelog article.

### Key Entities

- **Kind**: what an entity represents. It has a **word** (from the kind base's class name, lowercase; `entity_kind` on the wire and in the API) and a **display name** (declared by the kind base as `KIND_LABEL`; `entity_kind_label` on the wire, optional; `label` in `list-entity-kinds`, always present). A graph contains a set of kinds; no program fixes that set.
- **Kind base**: a class that inherits the entity base directly and declares a kind; it carries the kind's display name.
- **Association**: one relation between two tables, made of one relation field and, when declared, its inverse field on the other table. It has two ends, each with a table, a cardinality (one or many) and a role (the field name the other table uses for it).
- **Line**: what the ERD draws for an association, a dictionary reference or a generalization between two tables on screen.
- **Filter state**: per diagram, the domains and the kinds switched off. Which panel section is open is not remembered: Domains opens whenever a diagram mounts (FR-009).

## Success Criteria *(mandatory)*

### Measurable Outcomes

Checked on the admingameoffer graph and on hand-built graphs, against today's production.

- **SC-001**: On every single-domain ERD with 1-hop on, every combination of domains in the all-domains ERD, and with any kind switched off, the number of tables joined by the graph but drawn without a line is 0 (today: 3 pairs on `EventsDomain`, 2 on `OffersDomain`, 7 relations and 3 generalizations on `PlayersDomain`, 3 and 3 on `ShowcasesDomain`, and at least one cross-domain pair).
- **SC-002**: The admingameoffer graph is drawn with 34 association lines instead of 46 relation lines, and only one pair of tables keeps two association lines.
- **SC-003**: A graph from a non-AOA producer with three kinds AOA does not ship loads, shows three Kinds rows named from the graph, and filters them, with no change to Maxitor.
- **SC-004**: A graph with no kinds loads; its tables are listed under "Unknown".
- **SC-005**: The filter panel is 148 px wide on every ERD and with every content; it never covers the zoom toolbar.
- **SC-006**: A user can name the kind of any table from its header icon without opening anything.
- **SC-007**: A user hovering a line can say which two fields it joins without reading the line labels, and a user hovering a field can see all of its lines at once.
- **SC-008**: Copying a table or field name takes one click; dragging the canvas copies nothing.
- **SC-009**: No ERD table is narrower than 212 pt, and no table that was wider before changes its width because of the minimum.
- **SC-010**: A user comparing the ERD before and after finds no change of fonts, sizes, spacing, table outlines or header corners other than those this specification names.

## Assumptions

- **The display names of the six are fixed by this work**: Core, Association, Detail, Specialization, Enumeration, State.
- **The icon dictionary is presentation only.** It lives in Maxitor and names AOA's words; an unfamiliar word is never refused, only drawn with a monogram.
- **Optionality is not on the wire.** A relation carries no required/optional flag, so the crow's-foot ends show one or many only.
- **The reference graph for checks is the admingameoffer graph** as served on 2026-10-26, already frozen in the repository as `specs/025-graph-index-memory/data/ref-graph-2026-10-26.json.gz` (SHA-256 of the uncompressed bytes `a9d73e90b8c486fc18a3304b3eacf024a229a9642b71709af8bb919ebf0f84cf`, identical to what the live service served on 2026-10-26), so the counts above do not move with the live service.
- **The legend grey is `#94a3b8`**; the header icon is a white outline with no background, placed before the name; the replacement for the domain grey is orange `#f97316`. The `spec` pictogram is two stacked layers, chosen by the maintainer over a fork and a split after the hollow triangle was rejected.
- **Clipboard access is available** on Maxitor's own origin (HTTPS on production, localhost in development); embedding Maxitor elsewhere may refuse it, which FR-036 covers.

## Out of Scope

- Filtering by kind in the full graph, the use-case diagram and the lifecycle diagrams.
- Changing the drawing by kind beyond the icon — for example hiding an association table while keeping the connection between its participants.
- Sidebar rows per kind, deep links naming a kind, per-kind use-case diagrams.
- Replacing the use-case diagram's domain legend with the new panel, or changing its width.
- Drawing optionality ("zero or …") at the ends of a line.
- Any second store of kinds in Maxitor that outlives the loaded graph.
- Any change to the six kind bases beyond their display name, and any change to the declaration checks beyond the display-name check.
- Any visual redesign of the ERD beyond what this specification names.
