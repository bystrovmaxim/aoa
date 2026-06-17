<!-- translated-from: choosing-action-aspect-resource_draft.md @ 2026-06-16T13:54:29Z · sha256:0958e1568a64 -->
<p align="center">
  <img src="../assets/aoa-logo.png" alt="AOA" width="200">
</p>

# Action, aspect, or resource — what to choose

<table width="100%"><tr>
  <td align="left"></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"></td>
</tr></table>

---

In AOA you constantly make one of three decisions: cast the logic as an **aspect** inside an operation, extract it into a separate **operation** (`Action`), or isolate it as a **resource**. The choice determines how readable and testable the code stays. Below is a practical algorithm that sorts almost everything out automatically.

At its base are three kinds of logic:

- **A temporary process step** — lives only within the current scenario. → **an aspect**.
- **A self-contained operation** — has value beyond a single scenario, is called from several places, evolves independently. → **a separate `Action`**.
- **Work with the external world** — tied to connections, state, transport. → **a resource**.

---

## When an aspect

An aspect is part of one specific operation's pipeline. Take an aspect if the logic relates only to this scenario, is a simple step of the sequence, can rely on the `state` of previous steps, and will disappear together with the operation if it is deleted.

```python
@regular_aspect("Normalise and validate items")
@result_instance("items", list, required=True)
async def normalise_items_aspect(self, params, state, box, connections):
    items = [i for i in params.items if i.active]
    if not items:
        raise ValueError("Item list is empty")
    return {"items": items}
```

Practical rule: **start with an aspect.** Complicating the structure is worth it only when there is a signal for it — not in advance.

## When a separate operation

An operation is a self-contained unit of meaning with its own `Params` and `Result`. The main signal to extract is **the logic is needed in two or more places**. Other signs: the logic has value beyond the current scenario, it needs its own input and output, you want to test it separately, it will change independently.

```python
class CalculateDiscountParams(BaseParams):
    total: float = Field(description="Order total")
    is_vip: bool = Field(description="VIP customer")


class CalculateDiscountResult(BaseResult):
    discount: float = Field(description="Discount amount")
    final_total: float = Field(description="Total with the discount")


@meta(description="Calculate a discount", domain=StoreDomain)
@check_roles(AnyRole)
class CalculateDiscountAction(BaseAction[CalculateDiscountParams, CalculateDiscountResult]):

    @summary_aspect("Discount calculation")
    async def calculate_summary(self, params, state, box, connections):
        discount = params.total * 0.1 if params.is_vip else 0.0
        return CalculateDiscountResult(discount=discount, final_total=params.total - discount)
```

A call from another operation — through `box.run` (composition, not inheritance):

```python
@regular_aspect("Apply the discount")
@result_float("final_total", required=True, min_value=0)
async def apply_discount_aspect(self, params, state, box, connections):
    result = await box.run(
        CalculateDiscountAction,
        CalculateDiscountParams(total=state["total"], is_vip=params.is_vip),
    )
    return {"final_total": result.final_total}
```

## When a resource

A resource is an adapter of the external world with long-lived state. Take a resource if the object holds a connection, a session, a pool, a cache, or accumulated statistics; if this state cannot be safely recreated on every call; if the logic is transport (run SQL, call an API, write to a file) and there are no business rules inside.

```python
class OrderRepository(BaseResource):
    def __init__(self, postgres: PostgresResource) -> None:
        self._postgres = postgres

    async def create(self, user_id: int, total: float) -> int:
        return await self._postgres.execute(
            "INSERT INTO orders (user_id, total) VALUES ($1, $2) RETURNING id",
            params=(user_id, total),
        )
```

Business rules (whether an order can be created at all) stay in the operation; the resource only executes and returns control.

---

## The selection algorithm

Go through the questions top to bottom — the first affirmative answer gives the decision.

1. Is there long-lived state — a connection, session, cache, statistics? → **a resource**.
2. Is the logic transport — SQL, HTTP, a file, a queue? → **a resource**.
3. Is the logic needed in more than one place? → **an operation**.
4. Does it need its own `Params` and `Result`, separate testing? → **an operation**.
5. Otherwise → **an aspect**.

And a separate signal, the most common in practice: **an aspect started repeating in two places — time to make an operation.**

---

## Common mistakes

- **Computational logic in a temporary "calculator" object.** The state is temporary, inside are pure rules: this is an **operation**, not a resource. A resource is justified only if the state cannot be lost between calls.
- **Premature splitting.** Do not extract an aspect into an operation "for the future". Extract on the fact of reuse — otherwise you breed operations called from one place.
- **Business rules in a resource.** If "allowed/not allowed" branches appear in a `Resource`, they belong back in the `Action`. The resource executes, the operation decides.

## Short takeaway

An aspect is a step inside an operation, it lives and dies with it. An operation is a self-contained unit of meaning, called from several places. A resource is an adapter of the external world with long-lived state. In doubt — start with an aspect; it repeats — make an operation; there is long-lived state — make a resource.

See also: [Migrating legacy to AOA](migrating-legacy.md) — where this algorithm is applied step by step to someone else's code.

---

<table width="100%"><tr>
  <td align="left"></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"></td>
</tr></table>
