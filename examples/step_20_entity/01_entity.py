"""
01_entity.py — Entity: a domain object independent of storage

In an ordinary project the business object is whatever the database returned —
an ORM row named after columns, or a foreign API's JSON. The Action then depends
on storage details: change the ORM, rewrite the logic.

AOA declares the business object once, in domain terms, as an Entity:
  - @entity + BaseEntity; the class name must end with `Entity`.
  - A Resource hydrates it from flat storage data with build(...): direct
    mapping, or a mapper that maps storage columns -> entity fields.
  - One Entity, many load levels: Entity.partial(...) materialises only some
    fields; reading a declared-but-unloaded field raises FieldNotLoadedError —
    never a silent None.

Storage changes -> only the Resource's build(...) changes; the Action keeps
seeing the same OrderEntity. (Relations and Lifecycle are later chapters; here
`status` is a plain field.)

Tutorial: ../../docs/tutorials/step-20-entity_draft.md  ·  topic: Entity

Run:
    uv run python examples/step_20_entity/01_entity.py
"""

from pydantic import Field

from aoa.action_machine.domain import BaseEntity, FieldNotLoadedError, build
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.entity import entity


class ShopDomain(BaseDomain):
    name = "shop"
    description = "Shop domain"


@entity(description="Customer order", domain=ShopDomain)
class OrderEntity(BaseEntity):
    id: str = Field(description="Order identifier")
    total: float = Field(ge=0, description="Order total")
    currency: str = Field(default="RUB", description="Currency code")
    status: str = Field(description="Order status")  # plain field; Lifecycle is a later chapter


def main() -> None:
    # 1) Full hydration — keys match fields directly (the simple case).
    order = build({"id": "ord-1", "total": 1500.0, "currency": "RUB", "status": "paid"}, OrderEntity)
    print("1) Full entity (direct build):")
    print(f"   {order.id}  total={order.total} {order.currency}  status={order.status}")

    # 2) Storage-independent: a row with different column names, mapped to the
    #    same Entity. This mapping is the Resource's only job — no business logic.
    row = {"order_id": "ord-2", "total_amount": 99.5, "ccy": "EUR", "state": "shipped"}
    mapped = build(row, OrderEntity, lambda e, r: {
        e.id: r["order_id"],
        e.total: r["total_amount"],
        e.currency: r["ccy"],
        e.status: r["state"],
    })
    print("\n2) Same Entity from a differently-shaped row (mapper):")
    print(f"   {mapped.id}  total={mapped.total} {mapped.currency}  status={mapped.status}")

    # 3) Partial load — only id and total were read from storage.
    print("\n3) Partial load (only id, total):")
    partial = OrderEntity.partial(id="ord-3", total=42.0)
    print(f"   id={partial.id}  total={partial.total}")
    print(f"   is_field_loaded('status') = {partial.is_field_loaded('status')}")
    print(f"   primary key = {partial.get_primary_key()}")
    try:
        _ = partial.status  # declared but not loaded
    except FieldNotLoadedError as exc:
        print(f"   reading status -> FieldNotLoadedError: {exc}")


if __name__ == "__main__":
    main()
