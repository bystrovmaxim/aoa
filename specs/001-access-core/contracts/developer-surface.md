# Contract: the developer's surface

What a developer of an operation writes, and what the engine promises in return. Everything here is declaration-time or call-time behaviour of the core; nothing here is transport.

## Declaring who may run an operation

```python
@meta(name="cancel_order", description="Cancel an order")
@check_roles(roles=("manager", "support"))
async def cancel_order(self, params: CancelOrderParams) -> OrderResult: ...
```

- An operation **without** an access declaration must not reach a running service: the failure happens while the graph is assembled, not when a call arrives (FR-001).
- The declaration is the only place the rule is written. The same declaration produces the execution decision and the advance answer (FR-002).

## Declaring why a condition refuses

```python
@check_roles(roles=("manager",), when=lambda ctx: ctx.user.region == "eu",
             reason="REGION_NOT_SUPPORTED")
```

- `reason=` sits beside the condition it explains, and only there: a `reason=` with no `when=` and no `guard=` is a declaration error, and so is a condition without one — *a caller must not have to guess why the operation refused* (FR-010).
- Where no condition decided the refusal — the caller held none of the listed roles, or the object answer you wrote carries no reason — the answer carries the gate alone: the framework adds no text of its own (FR-012).
- A declared reason is any non-empty string, and it reaches the caller unchanged; nothing in the framework restates or renames it.

## Answering about a particular object

```python
@access_decide
async def cancel_order_access_decide(self, params, context, box, connections) -> Verdict:
    order = await connections["db"].get(params.order_id)
    if order is None or order.owner_id != context.user.user_id:
        return FORBIDDEN_OBJECT                       # one branch, one answer
    if order.status == "cancelled":
        return Refused("ORDER_ALREADY_CANCELLED")      # ownership proven, precise text is safe
    return Allowed()
```

- The check is **declared**, like every other behaviour of an operation: it is not a method an operation inherits, and a subclass does not inherit its parent's check. An operation that declares none has no object check (FR-018).
- **At most one** per operation: a second declaration is a declaration error, and so is a name that does not follow the declared suffix.
- The check is **visible in the assembled capability**, and it announces itself with its own before and after events, after the run is announced and before the aspect pipeline (FR-019).
- The check **answers with one of the three answers** and nothing else: `Allowed()`, `Refused(...)` or `Undecided(...)`. Anything else — a `bool`, a string, `None` — is a mistake, not an answer, and it is never read as "allowed": while the call executes it fails with that mistake, and a question about the call is answered `undecided` naming this step.

- `FORBIDDEN_OBJECT` is a ready-made refusal for "no such object" and "someone else's object" — the two must not be told apart (FR-011).
- Returning anything that is not one of the three answers is a defect and must not be read as "allowed" or as "refused".
- A gate that cannot tell may answer `Undecided(gate=Gate.ACCESS_DECIDE, cause=exc)`, naming itself; letting the failure escape produces the same answer for the gate that raised (FR-005).
- The engine does not inspect or restrict what a gate reads or writes (clarification Q4).

## The order the developer can rely on

| Position | Gate | Published name | Reads the call's parameters? |
| --- | --- | --- | --- |
| 1 | identity | `AUTH_COORDINATOR` | No |
| 2 | roles — no listed role is held | `CHECK_ROLES` | No |
| 2 | roles — a role matched but its `when=` refused | `WHEN` | No |
| 3 | the operation's shared `guard=` | `GUARD` | Yes |
| 4 | the object | `ACCESS_DECIDE` | Yes |

The first refusal ends the decision; later gates are never called (FR-007). Rejected credentials refuse even on an operation declared open to guests (FR-009).

## Asking in advance

- Asking runs no step of the operation and publishes no run lifecycle (FR-016).
- The advance answer and the executed outcome for the same circumstances must not diverge (FR-017).
- The core answers about one call; it has no batch form (D8).

## What is *not* part of this contract

Status codes, headers, wire names for the answer words, and where a caller sees them: none of that is decided here (spec Assumptions).
