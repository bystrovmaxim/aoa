# Contract: typed events

The public surface of this feature. Rules and modes are in [spec.md](../spec.md); the types are in [data-model.md](../data-model.md).

## Declaring an event

```python
from aoa.action_machine.model.base_event import BaseEvent

class OrderCompletedEvent(BaseEvent):
    order_id: str
    total: float
```

## Emitting it

```python
await box.info(channels, message, event=None, /, **kwargs)
await box.warning(channels, message, event=None, /, **kwargs)
await box.critical(channels, message, event=None, /, **kwargs)
```

| Call | Result |
|---|---|
| `box.info(ch, "Order {%var.order_id}", event)` | a line whose `var` is the event |
| `box.info(ch, "Saved {%var.x}", x=1)` | a line whose `var` is a dictionary |
| `box.info(ch, "text")` | a line with system fields only in its dictionary |
| `box.info(ch, "text", event, x=1)` | `EventContractError` |
| `box.info(ch, "text", OrderCompletedEvent)` | `EventContractError` |
| `box.info(ch, "text", {"x": 1})` | `EventContractError` |
| `box.info(ch, "text", BaseEvent())` | `EventContractError` |

`channels` and `message` stay required.

## Declaring what a method emits

```python
from aoa.action_machine.intents.emits import emits

@summary_aspect("Finalize the order")
@emits(OrderCompletedEvent)
async def finalize_summary(self, params, state, box, connections): ...
```

It has effect on `@regular_aspect`, `@summary_aspect`, `@compensate`, `@on_error` and `@access_decide`, above or below that decorator.

## Declaring a domain's vocabulary

```python
class OrdersDomain(BaseDomain):
    name = "orders"
    description = "Order lifecycle"
    events = (OrderCompletedEvent, OrderCancelledEvent)
```

## Receiving it

`BaseLogger` keeps its methods and parameters:

```python
async def write(self, scope, message, var, ctx, state, params, indent) -> None:
    if isinstance(var, OrderCompletedEvent):
        send(var.model_dump())
```

`var["level"]`, `var["channels"]`, `var.get("domain")` work on every line. A subclass declaring `var: dict[str, Any]` passes the type check.

## Errors

| When | Error |
|---|---|
| A refused emission, at runtime | `EventContractError`, on the path of the method that made it |
| `@emits` names an event outside the domain's `events`, at build | `EventContractError` naming the method, the event and the domain |
| A reserved field name, at class definition | `EventContractError` |
| A wrong suffix, at class definition | `NamingSuffixError` |
| `@emits` with bad arguments | `DecoratorArgumentValueError` or `DecoratorArgumentTypeError` |
| `@emits` applied twice to one method | `DuplicateDeclarationError` |
| Invalid `events`, at domain definition | `EventContractError` |
| The author sets a system field | `pydantic.ValidationError` |

What reaches the caller for each kind of method:

| Method that broke the rule | Outcome |
|---|---|
| regular or summary aspect | the saga rolls back; `@on_error` may catch it; otherwise `EventContractError` |
| compensator | a failed compensation; the rollback goes on |
| error handler | `OnErrorHandlerError` |
| `@access_decide` | `Undecided` from `check_access_decide`; `AccessUndecided` from a run |
| any, in a direct `TestBench` run | `EventContractError` |
