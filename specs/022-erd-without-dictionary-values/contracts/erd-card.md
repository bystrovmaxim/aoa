# Contract — a dictionary card, from the graph to the drawing

**Feature**: [spec.md](../spec.md) | **Plan**: [plan.md](../plan.md) | **Data model**: [data-model.md](../data-model.md)

This contract fixes what each of the three layers must carry for a dictionary. It supersedes the value-row part of `specs/016-value-declaration-consistency/contracts/dictionary-card.md` §3 and the value-row requirement of `specs/017-explicit-entity-relations/spec.md` FR-038, both amended in the documentation task of this change.

## 1. The graph document keeps every value

```json
{"code": "eur", "display_name": "Euro", "properties": {"symbol": "€"}}
```

| Rule | Statement |
| --- | --- |
| Presence | every declared value appears in `properties.values` of its dictionary node |
| Shape | `{code, display_name, properties}` — unchanged by this feature |
| Leaves | JSON values only, because the reference is the value's JSON export |
| Rebuild | no migration: a graph saved before the change renders as it is |

Proven by `packages/aoa-action-machine/tests/action_machine/graph/test_dictionary_reference_json.py`, which runs unchanged. That test proves the JSON-compatibility rule by a `json.dumps` round-trip; the escaped-text case (`<safe> & readable`) is asserted one layer down in the payload test, because a markup string is an ordinary JSON leaf that the round-trip carries by construction rather than by a dedicated fixture.

## 2. The ERD payload keeps every value

```json
{"code": "eur", "display_name": "Euro", "properties": [{"name": "symbol", "value": "€"}]}
```

| Rule | Statement |
| --- | --- |
| Presence | `values` is part of the entity payload, in declaration order |
| Item shape | exactly `{code, display_name, properties}`, both property members strings |
| Empty | a value with no extra properties carries `properties: []` |
| Schema | the payload schema is not edited by this feature |
| Field rows | the two rows the dictionary kind supplies (`code`, `display_name`) stay absent from `fields` |

Proven by `packages/aoa-maxitor/tests/test_list_entities_payload_dictionary.py`, which runs unchanged.

## 3. The card draws no value

| Rule | Statement |
| --- | --- |
| Rows | no row is drawn for a value: no label, no property, no code |
| Replacement | nothing is put in its place — no badge, no count, no tint, no marker |
| Fields | the dictionary's own field rows, its header and the arrows that reach it are drawn as before |
| Independence | the card's DOT is identical whether the payload carries one value, ninety-three, or none |
| Vocabulary | the renderer names no dictionary, kind or field, and applies no threshold |
| Escaping | nothing of the value reaches the SVG, so there is nothing to escape |
| Legacy | a payload produced before the change renders, and a payload whose entity carries no `values` at all also renders |

Proven by `packages/aoa-maxitor/client/scripts/check-erd-dictionary-values.ts`, with `check-erd-card-containment.ts` and `check-erd-group-label.ts` running unchanged as controls.

## 4. What the layers must not do

| Layer | Must not |
| --- | --- |
| Graph | drop a value, a code or a property to make the drawing smaller |
| Payload | narrow `values` because the card stopped reading it |
| Card | grow a substitute convention for a value it no longer draws |
| Documentation | promise a row the card does not draw, or claim the values are gone from the graph |

## 5. The proof

| Check | What it proves |
| --- | --- |
| `client/scripts/check-erd-dictionary-values.ts` | no value text or tooltip in the DOT and the SVG; the same DOT with and without values; non-dictionary rows unchanged; a legacy graph renders |
| `tests/test_list_entities_payload_dictionary.py` | the payload shape, the text forms, the schema |
| `graph/test_dictionary_reference_json.py` | the graph document, JSON-parsed, still carrying every value |
| `client/scripts/check-erd-card-containment.ts` | the card's fills still stop at its contour |
| `client/scripts/check-erd-group-label.ts` | the specialization group still names its dictionary once |

The adversarial case for this contract is a value row returning through any path: restoring the renderer block must fail the drawn-SVG assertion while the payload and graph checks still pass; dropping `values` from the export must fail the graph check while the drawn-SVG assertion still passes.
