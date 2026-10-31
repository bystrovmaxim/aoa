# Contract: the map's reads

Both are AOA actions, read for the active source, with `a` naming the older version in a comparison, as `/api/v1/compare` does. Keys and logs follow spec 037.

## `GET /api/v1/map/overview`

```json
{
  "state": "ready",
  "types": ["Action", "Entity", "EntityField"],
  "type_colours": {"Action": "#2563eb", "Entity": "#059669", "EntityField": "#94a3b8"},
  "chains": [[], ["Entity"]],
  "areas": [
    {"id": "shop.OrdersDomain", "name": "OrdersDomain", "colour": "#3b82f6", "x": 120.0, "y": -40.0, "radius": 770.0,
     "counts": {"Entity": 12, "EntityField": 90}}
  ],
  "bundles": [["shop.OrdersDomain", "shop.BillingDomain", 14]],
  "shared": [{"id": "shop.Money", "type": "Entity", "domains": ["shop.OrdersDomain", "shop.BillingDomain"]}]
}
```

- `state` is `laying-out` until the map is ready; then `areas` is empty, and the client asks again.
- In a comparison an area adds `status` and `changes`, and a bundle adds a last item, its changed links by status. The overview adds `links_changed`, how many drawn links changed.
- Each area carries `sketch`, `{"cell": 60.0, "cells": [[column, row, type index, count, chain index, status index]]}`, status counting in `unchanged`, `added`, `removed`, `changed`; each bundle carries its links by their ends, `"EntityField>Entity|Action"`: a type, then the types above it. So the outlines, the counts and the bundles follow a filter with no other read.

## `GET /api/v1/map/area?id=<area>&level=<2|3>`

```json
{
  "nodes": [{"id": "shop.Order", "label": "Order", "type": "Entity", "x": 10.5, "y": 20.0, "level": 2}],
  "edges": [{"id": "shop.Order|entity_relation|owner", "source": "shop.Order", "target": "shop.Customer", "type": "entity_relation"}],
  "across": [{"id": "shop.Order|@depends|shop.Pay", "source": "shop.Order", "target": "shop.Pay", "type": "@depends"}]
}
```

- `across` lists links to other areas, drawn once both ends are loaded.
- A contained node adds `chain`, its index in `chains`.
- In a comparison a node or edge adds `diff`, and a retargeted edge adds `was`, its target in A. A node that holds a change or ends a changed link adds `glance`: `changed`.

## `GET /api/v1/map/changes`

Only with `a`. Every changed node and drawn link, in the stepping order (FR-025b); a link stands at its middle and adds `span`, how far apart its ends are. `ends` says what a filter asks of the node or of both ends of the link: `[id, home area, type, chain index, status]`:

```json
{"changes": [{"id": "shop.Order", "label": "Order", "area": "shop.OrdersDomain", "type": "Entity", "status": "changed", "x": 10.5, "y": 20.0, "level": 2,
  "ends": [["shop.Order", "shop.OrdersDomain", "Entity", 0, "changed"]]}]}
```

The client steps through this list and skips what its filters hide, so stepping needs no other read until it arrives.

## Refusals

As for `/api/v1/compare`: a refused version or a pair that cannot be compared is refused with its reason; a wrong key reads as "not found".
