# Quickstart: validating the feature

All commands from the repository root. The reference graph is `specs/025-graph-index-memory/data/ref-graph-2026-10-26.json.gz` (the admingameoffer graph, SHA-256 `a9d73e90…f84cf`).

## 1. Engine (US3)

```bash
uv run pytest packages/aoa-action-machine/tests/action_machine/domain/test_entity_kind.py packages/aoa-action-machine/tests/action_machine/graph -q
```

Expected: each of the six kinds exports its word and label; a kind base without `KIND_LABEL`, with `""`, or inheriting it from a mixin is refused at class creation; the schema accepts `aggregate`, rejects `""`, `"Core"`, `"core entity"`, a non-string, and an empty label.

## 2. Maxitor backend (US1, US3, US5)

```bash
uv run pytest packages/aoa-maxitor/tests -q -k "entity_kind or lines_on_screen or associations"
```

Expected: a graph without kinds loads with `unknown`; `list-entity-kinds` returns `aggregate`/Aggregate root, `event`/Event, `link`/Link for the hand-built graph; the reduced reference fixture has no table pair on screen without its line, per slice and request-wide; a field and its inverse give one row with `source_field` / `target_field`; `chosen_offer` stays its own row.

The counts on the full reference graph (34 association lines, the one pair with two) are asserted by the drawing check in step 3.

## 3. ERD drawing (US4, US5, US7)

```bash
cd packages/aoa-maxitor/client && node scripts/check-erd-kinds-and-lines.ts
```

Expected: every table ≥ 212 pt wide and wider tables unchanged; header fill still trimmed to a rounded contour; header slot and name cells addressable; no type cell containing `→` or `FK -> `, type cells right-aligned; specialization containers filled with the 5 % dark tint and a 2-point dashed outline; association edges with `crow`/`tee` ends and both roles; 34 association edges on the reference graph with all domains; two distinct edges between `OfferRequestCoreEntity` and `OfferRequestItemDetailEntity`.

## 4. Client logic (US2, US6, US8)

```bash
cd packages/aoa-maxitor/client && npm test
```

Expected: the filter panel is 148 px, strict accordion, Domains open on mount, ellipsis tooltips only when cut, "Filter" pill on narrow screens; switching a kind off hides its tables, lines and container members and survives a diagram switch; hovering an edge marks the right rows by text only; a click copies, a 5 px drag does not, a refused clipboard selects the text.

## 5. By eye, against production

```bash
uv run task maxitor-api
```

```bash
cd packages/aoa-maxitor/client && npm run dev
```

Open `http://localhost:5173/?source=https%3A%2F%2Fadmingameoffer.aoa.run%2Fgraph-json&view=domain-erd&domain=datamodel.events.events_domain.EventsDomain` next to the same URL on `https://maxitor.aoa.run`. Expected: `PlayerCoreEntity`–`ShowcaseCoreEntity` joined by one line with `showcase` (bar) and `players` (crow's foot); `GenderEnumEntity` 212 pt wide; icons before every name; fonts, sizes, outlines and header corners as on production.

## 6. Closing run

```bash
bash scripts/run_checks_with_log.sh
```

Expected: green, with only the two accepted remarks.
