# Contract: a declared value's properties on the way to the ERD card

**Feature**: `specs/016-value-declaration-consistency` | **Plan**: [../plan.md](../plan.md) | **Data model**: [../data-model.md](../data-model.md) | **Research**: [../research.md](../research.md)

One value crosses four boundaries: the graph's reference form, the stored graph, the ERD payload and the diagram. This contract fixes what each boundary may carry, so a property cannot disappear between two layers that are each individually correct.

## 1. The graph's reference form

The dictionary node keeps `properties.values` as an array of references, and a reference keeps three members:

```json
{
  "code": "eur",
  "display_name": "Euro",
  "properties": {"symbol": "€", "note": "<safe> & readable"}
}
```

| Rule | Statement |
| --- | --- |
| Shape | `{code, display_name, properties}` — unchanged by this feature |
| Leaves | JSON values only, because the reference is the value's JSON export |
| Values are not nodes | a value keeps no identity, domain or edges of its own |
| Rebuild | a graph saved with the properties displays without a rebuild; this feature adds no migration |

## 2. The ERD payload

`ListEntitiesAction` converts the mapping into a typed list, so the payload satisfies `JsonSchemaValue`:

```json
{
  "code": "eur",
  "display_name": "Euro",
  "properties": [
    {"name": "symbol", "value": "€"},
    {"name": "note", "value": "<safe> & readable"}
  ]
}
```

| Rule | Statement |
| --- | --- |
| Item shape | exactly `{name, value}`; both are strings; `additionalProperties: false` |
| Order | the declaration order of the fields, as the mapping carries it |
| Empty | a value with no extra properties carries `properties: []` |
| Text | a string property is its text; a number, boolean or array is `json.dumps(value, ensure_ascii=False)` — `42`, `true`, `["a", "b"]` |
| Serializer output | a custom serializer's string arrives as that string, because it is already the reference's leaf |
| Escaping | not the payload's job; it arrives as text and is escaped once in the renderer |

## 3. The rendered card

Amended by #249: the card printed labels instead of codes. Amended again by #265: the card draws
no row for a value at all, and nothing takes its place. The rules below are the current behaviour;
the earlier version is not kept as an alternative. The requirement that replaced the second
amendment lives in `specs/022-erd-without-dictionary-values/spec.md` (FR-001 to FR-012), and the
field-row rule of #249 (FR-037) still holds.

| Rule | Statement |
| --- | --- |
| Placement | no row is drawn for a value — not under the fields, not as a node, not as a second card |
| Printed text | the dictionary's own field rows, its header and the arrows that reach it; no value label, no value property and no code |
| Code | stays in the graph document, in `properties.values` and in the ERD payload; the card neither prints it nor attaches a tooltip, because there is no row to attach one to |
| Replacement | nothing is put in a value's place — no badge, no count, no tint, no marker |
| Independence | the card's DOT is identical for 0, 1, 3, 26 or 93 declared values |
| Escaping | applies to the field text the card still draws; nothing of a value reaches the SVG, so there is nothing to escape there |
| Vocabulary | no dictionary name, kind or field is named by the renderer; `symbol` and `note` are examples only |
| Degradation | a dictionary that arrives with no `values` renders its fields, without an error and without an empty row |
| Old payload | a payload that still carries `values` renders as it is: the card ignores the field, and no rebuild is needed |
| Rendering | the check runs the real layout (`@hpcc-js/wasm-graphviz`), not a string comparison of DOT alone |

## 4. The specialization group label

```json
{
  "group_id": "axis",
  "label": "kind (by EditionKindEnumEntity)",
  "classifier_field": null,
  "members": ["first", "repress"]
}
```

| Rule | Statement |
| --- | --- |
| Owner | the server composes the label; the client renders it |
| Occurrences | the dictionary name appears exactly once |
| Removed member | `dictionary_label` leaves the group shape — payload, JSON schema and `ErdGroup` |
| Kept member | `classifier_field` stays, because it is a fact and not the label |
| Escaping | once, in the renderer |
| Label contract | The server supplies a complete label; the client renders it as received. A missing-label fallback is not part of the current renderer contract. |

## 5. The proof

| Check | What it proves |
| --- | --- |
| `packages/aoa-maxitor/tests/test_list_entities_payload_dictionary.py` | the payload shape, the text forms, the schema validation |
| `packages/aoa-maxitor/tests/test_list_entities_specialization_contract.py` | the group's key set after `dictionary_label` leaves, and the label text |
| `packages/aoa-maxitor/client/scripts/check-erd-dictionary-values.ts` | no value text and no code tooltip in the DOT or the SVG; an identical DOT for 0, 1, 3, 26 and 93 values; a non-dictionary card matching its recorded golden |
| `packages/aoa-maxitor/client/scripts/check-erd-group-label.ts` (new) | the server payload driven through the client renderer, dictionary named once |
| `packages/aoa-action-machine/tests/action_machine/graph/test_dictionary_reference_json.py` (new) | the actual graph document, JSON-parsed, carrying the serializer's text |

The adversarial case for this contract is a value returning to the card through any path: restoring a value row must fail the drawn-SVG assertion while the payload and graph tests stay green, and dropping `values` from either data layer must fail that layer's test while the card check stays green.
