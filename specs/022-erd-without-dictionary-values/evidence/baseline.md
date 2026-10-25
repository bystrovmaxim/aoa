# Baseline — the state the specification quotes, before any edit

**Feature**: [../spec.md](../spec.md) | **Plan**: [../plan.md](../plan.md) | **Tasks**: [../tasks.md](../tasks.md) (T001)
**Captured**: 2026-10-25 04:33 MSK

```
branch   feature/issue-265-erd-without-dictionary-values
commit   f61364f0  (specification, plan and task list only — no code yet)
node     v25.8.2
python   3.12.12 (repository venv)
model    https://admingameoffer.aoa.run/graph-json
```

## 1. The three client checks, before the change

Run from `packages/aoa-maxitor/client`:

```
$ node scripts/check-erd-dictionary-values.ts
Dictionary card: labels printed, codes carried as tooltips, everything escaped
exit 0

$ node scripts/check-erd-card-containment.ts
ok    A-11 no new imports  neither drawing module imports anything at all, let alone a package
all assertions passed
exit 0

$ node scripts/check-erd-group-label.ts
Group label: composed once, rendered as received
exit 0
```

The first check passes against the **old** contract — that is the point of T002: it must be inverted and must then fail.

## 2. The two Python proofs, before the change

```
$ .venv/bin/python -m pytest packages/aoa-action-machine/tests/action_machine/graph/test_dictionary_reference_json.py -q
3 passed in 0.02s

$ .venv/bin/python -m pytest packages/aoa-maxitor/tests/test_list_entities_payload_dictionary.py -q
15 passed in 0.60s
```

Both are run unedited and must stay green after the change (T008, T010).

## 3. The drawing, measured on the model

Ran the built client against the model and read the Graphviz SVG's `viewBox` and the painted value rows out of the DOM.

| What | Command | Result |
| --- | --- | --- |
| players domain size | `--dump-dom` on `?source=…&view=domain-erd&domain=datamodel.players.players_domain.PlayersDomain`, then `grep 'viewBox='` | `viewBox="0.00 0.00 1698.00 6800.00"` |
| value property rows painted | same DOM, `grep -c 'is_obsolete: false'` | `98` |
| events domain size (scale reference) | same, `domain=datamodel.events.events_domain.EventsDomain` | `1815 × 1593` |

## 4. The seven dictionaries and their value counts

Read from the model's `coordinator_json`, nodes with `properties.entity_kind == "enum"`:

| Dictionary | Domain | Values |
| --- | --- | --- |
| `EventKindEnumEntity` | events | 5 |
| `GenderEnumEntity` | events, players | 3 |
| `PlatformEnumEntity` | events, players | 3 |
| `BarrierEnumEntity` | offers | 5 |
| `IndustryEnumEntity` | offers, showcases | 26 |
| `RegionEnumEntity` | offers, players | 93 |
| `GenreEnumEntity` | showcases | 8 |

Seven distinct dictionaries in four domains; the players domain alone carries 93 + 3 + 3.

## 5. The golden: a non-dictionary card's DOT, recorded before the change

Payload: one entity only — `shop.PriceTagCoreEntity` with the single `amount` field, no relations — rendered with layout `gv-dot-lr`. This exact string is what T003 asserts after the change, so "a non-dictionary card is unchanged" is a comparison rather than an impression.

Length: 719 characters.

```text
digraph ERD {
  graph [rankdir=LR fontname="Helvetica" bgcolor=transparent pad="0.5" nodesep="0.8" ranksep="1.2"]
  node  [shape=none fontname="Helvetica" fontsize=11 margin="0"]
  edge  [fontname="Helvetica" fontsize=9 color="#94a3b8" arrowsize=0.7]

  "shop.PriceTagCoreEntity" [label=<<TABLE BGCOLOR="white" BORDER="1" CELLBORDER="0" CELLSPACING="0" CELLPADDING="4" STYLE="ROUNDED" COLOR="#3b82f6"><TR><TD COLSPAN="3" BGCOLOR="#3b82f6" ALIGN="CENTER"><FONT COLOR="white" POINT-SIZE="12"><B>PriceTagCoreEntity</B></FONT></TD></TR><TR><TD BGCOLOR="#ffffff" WIDTH="28"></TD><TD BGCOLOR="#ffffff" ALIGN="LEFT">amount</TD><TD BGCOLOR="#ffffff" ALIGN="LEFT"><FONT COLOR="#64748b"><I>float</I></FONT></TD></TR></TABLE>>]

}
```

## 6. After the change — the same measurements

Captured with the renderer changed (T004) and the client rebuilt, against the same model.

### 6.1 The check, inverted and green

```
$ node scripts/check-erd-dictionary-values.ts
Dictionary card: no value row, its own fields and the reference intact
exit 0
```

Before the renderer change the same file failed at its first assertion —
`AssertionError [ERR_ASSERTION]: A value label is printed on the card` — which is the red state
T002 and T003 require.

### 6.2 The adversarial pass (T006)

One value row was restored in `buildDotSource` — `nd.values` mapped into a `<TR>` again — and the
same check was run:

```
AssertionError [ERR_ASSERTION]: A value label is printed on the card
exit 1
```

`check-erd-card-containment.ts` and `check-erd-group-label.ts` stayed green in the same run, so the
failure is the value row and not a broken drawing. The edit was then reverted and the check passed
again.

### 6.3 The drawing, measured after the change

| What | Before | After |
| --- | --- | --- |
| players domain | `1698 × 6800` | `1698 × 2075` |
| events domain | `1815 × 1593` | `1815 × 1423` |
| offers domain | not measured | `2283 × 1242` |
| showcases domain | not measured | `3383 × 1667` |
| all-domains view | not measured | `4400 × 2777` |
| value property rows (`is_obsolete: false`) | 98 in players | `0` in all four domains and in the all-domains view |

Every declared value label was also searched for and found nowhere: `Весь мир`, `Мужской`,
`Вход в игру`, `Доставка готовой еды`, `Головоломка`, `Android`.

The `is_obsolete` *field* rows remain — three of them in the players domain, one per dictionary —
because a dictionary keeps its own fields; only the values are gone.

### 6.4 The correction this measurement forced

The specification first predicted the players domain would land near 1593 px, the events domain's
height. It landed at 2075 px: the players domain carries more entities, and those entities set the
height, not the dictionary. SC-001, the plan's performance goal, the quickstart table and T007 were
corrected to the measured numbers; the causal criterion (SC-006, identical card for 0/1/3/26/93
values) never depended on the prediction. Recorded in full in `research.md`.

### 6.5 Visual record

Screenshots were taken at 1800 × 1100, 100 % zoom, one per domain. They are working artefacts under
`.tmp-shot/` (`after-events.png`, `after-players.png`) and are not part of the repository: the
numbers above and the DOM searches are the evidence, the images are for a human to look at.

The events domain shows the three dictionaries as ordinary cards — `id` and `is_obsolete`, a
`PK` marker, no green block. The players domain shows `RegionEnumEntity`, `GenderEnumEntity` and
`PlatformEnumEntity` the same way, where a single column of 93 rows used to dominate the canvas.

## 7. Environment note

The headless binary used for the measurements is `chromium_headless_shell` from the local Playwright cache; any Chromium build works — what matters is the `viewBox` of the Graphviz SVG inside the rendered page.
