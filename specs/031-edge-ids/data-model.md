# Data Model: Every Edge of the Graph Gets an Id

## Edge row (graph export, format 1.1)

| Field | Type | Meaning |
|---|---|---|
| `id` | non-empty string | **New.** The edge's identity within the graph, computed by `edge_id` from the other fields. |
| `source_id` | non-empty string | The node the edge leaves. |
| `target_id` | non-empty string | The node the edge points at. |
| `type` | non-empty string | The edge type, such as `entity_relation`. |
| `relationship` | string | ArchiMate relationship name. |
| `is_dag` | boolean | Whether the edge takes part in the acyclicity check. |
| `properties` | object | Per-type properties, as today. |

The export lists edges in `id` order and writes `schema_version` `"1.1"`. A row of format 1.0 is the same without `id`.

## Edge id

`<source_id>|<type>|<target>` followed by an optional `|<suffix>`, where:

- `<target>` is the `target_id`, or, for a type whose rule names a **member**, the value of that property;
- `<suffix>` is present only for a type whose rule names a **suffix** property.

Every part is a non-empty string without `|`. Two edges of one graph never share an id.

| Type | Rule | Example |
|---|---|---|
| (default) | — | `actions.admins.sign_in_admin_action.SignInAdminAction\|@check_roles\|aoa.action_machine.auth.guest_role.GuestRole` |
| `entity_relation` | member `field_name` | `datamodel.offers.offer_request_core_entity.OfferRequestCoreEntity\|entity_relation\|chosen_offer` |
| `lifecycle_transition` | suffix `from_state` | `datamodel.offers.offer_core_entity.OfferCoreEntity:lifecycle:lifecycle\|lifecycle_transition\|datamodel.offers.offer_core_entity.OfferCoreEntity:lifecycle:lifecycle:active\|draft` |

## Edge id rule (`EdgeIdRule`)

| Attribute | Meaning |
|---|---|
| `member` | A property that names the edge in place of its target, or none. |
| `suffix` | A property appended to the id, or none. |

At most one of the two is set. Declared on the edge class as `ID_RULE`, together with `EDGE_TYPE`; collected into `EDGE_ID_RULES`, keyed by type.

## Refusals

| When | What | Message names |
|---|---|---|
| Two edges of one graph get the same id | `DuplicateEdgeError` (a `ValueError`), at build | the id and both edges |
| A node id contains `\|` | `InvalidGraphError`, at build | the node |
| An edge's rule property is missing, empty, not a string, or contains `\|` | `InvalidGraphError` at build; `ValueError` from `edge_id` for a reader | the edge (or the type) and the property |
