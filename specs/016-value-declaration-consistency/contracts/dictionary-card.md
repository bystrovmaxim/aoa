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

| Rule | Statement |
| --- | --- |
| Placement | property rows inside the dictionary's value row — never nodes, never a second card |
| Escaping | name and value are HTML-escaped once; `<`, `>`, `&` display literally and the SVG stays valid |
| Vocabulary | no dictionary name, kind or field is named by the renderer; `symbol` and `note` are examples only |
| Degradation | a value with no properties shows code and label and no empty row; a model with no dictionaries renders as today |
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
| Degradation | no label → the group id; never `(by )` |

## 5. The proof

| Check | What it proves |
| --- | --- |
| `packages/aoa-maxitor/tests/test_list_entities_payload_dictionary.py` | the payload shape, the text forms, the schema validation |
| `packages/aoa-maxitor/tests/test_list_entities_specialization_contract.py` | the group's key set after `dictionary_label` leaves, and the label text |
| `packages/aoa-maxitor/client/scripts/check-erd-dictionary-values.ts` | escaping and the rendered SVG |
| `packages/aoa-maxitor/client/scripts/check-erd-group-label.ts` (new) | the server payload driven through the client renderer, dictionary named once |
| `packages/aoa-action-machine/tests/action_machine/graph/test_dictionary_reference_json.py` (new) | the actual graph document, JSON-parsed, carrying the serializer's text |

The adversarial case for this contract is a property dropped between the graph and the card: the payload test must fail when the conversion skips a member, and the client check must fail when the renderer skips a row.
