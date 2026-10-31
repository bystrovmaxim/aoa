# Contract: the map's reads

Both are AOA actions, read for the active source, with `a` naming the older version in a comparison, as `/api/v1/compare` does. Keys and logs follow spec 037.

## `GET /api/v1/map/overview`

```json
{
  "state": "ready",
  "types": ["Action", "Entity", "EntityField"],
  "areas": [
    {"id": "shop.OrdersDomain", "name": "OrdersDomain", "colour": "#3b82f6", "x": 120.0, "y": -40.0, "radius": 770.0,
     "counts": {"Entity": 12, "EntityField": 90}}
  ],
  "bundles": [["shop.OrdersDomain", "shop.BillingDomain", 14]],
  "shared": [{"id": "shop.Money", "type": "Entity", "domains": ["shop.OrdersDomain", "shop.BillingDomain"]}]
}
```

- `state` is `laying-out` until the map is ready; then `areas` is empty, and the client asks again.
- In a comparison an area adds `status` and `changes`, and a bundle adds a fourth item, its changed links.
- Each area carries `sketch`, and each bundle its links by the types of their ends, so the outlines, the counts and the bundles follow a filter with no other read.

## `GET /api/v1/map/area?id=<area>&level=<2|3>`

```json
{
  "nodes": [{"id": "shop.Order", "label": "Order", "type": "Entity", "x": 10.5, "y": 20.0, "level": 2}],
  "edges": [{"id": "shop.Order|entity_relation|owner", "source": "shop.Order", "target": "shop.Customer", "type": "entity_relation"}],
  "across": [{"id": "shop.Order|@depends|shop.Pay", "source": "shop.Order", "target": "shop.Pay", "type": "@depends"}]
}
```

- `across` lists links to other areas, drawn once both ends are loaded.
- In a comparison a node or edge adds `diff`, and a retargeted edge adds `was`, its target in A.

## `GET /api/v1/map/changes`

Only with `a`. Every changed node, in the stepping order (FR-025b):

```json
{"changes": [{"id": "shop.Order", "area": "shop.OrdersDomain", "type": "Entity", "status": "changed", "x": 10.5, "y": 20.0, "level": 2}]}
```

The client steps through this list and skips what its filters hide, so stepping needs no other read until it arrives.

## Refusals

As for `/api/v1/compare`: a refused version or a pair that cannot be compared is refused with its reason; a wrong key reads as "not found".
