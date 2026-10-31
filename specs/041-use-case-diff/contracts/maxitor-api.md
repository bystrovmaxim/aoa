# Contract: Maxitor API

## GET /api/v1/compare/changed-inside

Named like the other comparison reads: `source` = B, `a` = A, A's key in the header. An AOA action.

```json
{
  "actions": {
    "shop.ReadOfferRequestAction": [
      { "kind": "node", "id": "shop.ReadOfferRequestAction.Result:chosen_offer", "label": "chosen_offer",
        "type": "Field", "group": "Result", "status": "added", "differences": [] }
    ]
  }
}
```

Refusals are those of `GET /api/v1/compare`. Nothing else in the read names an address or a key.

## GET /api/v1/domain-use-case-diagram

Unchanged but one field: every entry of `edges` carries `id`, its protocol id.
