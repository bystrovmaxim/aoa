# Contract — The Answer and the Order It Comes From

**Feature**: [spec.md](../spec.md) | **Plan**: [plan.md](../plan.md) | **Data model**: [data-model.md](../data-model.md)

Three answers, three published words, three ordered steps. This contract is what a transport, a
plugin and a stored-record reader can rely on.

## The vocabulary

```python
class Gate(StrEnum):
    AUTH_COORDINATOR = "AUTH_COORDINATOR"   # who is calling
    CHECK_ROLES = "CHECK_ROLES"             # the roles they hold
    ACCESS_DECIDE = "ACCESS_DECIDE"         # the object they touch
```

| Property | Contract |
| --- | --- |
| Member count | exactly three; the name and its value never diverge |
| Where it travels | `Refused.gate`, `Undecided.gate`, and the decision event that carries the answer |
| Removed members | `WHEN` and `GUARD` do not exist — not as members, not as reserved values, not as deprecated aliases |
| A stored answer naming a removed member | refused by validation as an unknown value; never coerced into a valid answer |

## The order

```text
decide(context, action, params, box, connections)
  ├─ auth_gate     → AUTH_COORDINATOR     (never answers in this build; a transport does)
  ├─ roles_gate    → CHECK_ROLES
  └─ object_gate   → ACCESS_DECIDE        (optional; absent rule passes)
```

| Phase | Steps | Answers |
| --- | --- | --- |
| `GATES_BEFORE_RUN` | `AUTH_COORDINATOR`, `CHECK_ROLES` | may a run start at all |
| `GATES_AT_OBJECT` | `ACCESS_DECIDE` | may this object be touched, inside the run |

A step that raises becomes `Undecided` naming its own word, with the failure kept as its private
cause. A step that has nothing to say answers `None` and the next one is asked. The first answer
ends the decision; every step passing answers `Allowed`.

There is no fourth step. `guard_gate` and `guard_answer` are gone from the module, from its
`__all__`, and from the step map.

## What each word tells a caller

| Word | The call was refused because |
| --- | --- |
| `AUTH_COORDINATOR` | the credentials were presented and rejected (a transport decides this today) |
| `CHECK_ROLES` | the caller holds none of the roles the operation lists — and, since no condition can refuse any more, this is the only answer the role step gives |
| `ACCESS_DECIDE` | the object rule refused: the author's `Refused("REASON")`, or the shared `FORBIDDEN_OBJECT` |

A refusal carries a reason only when a declared rule produced one. The framework still invents no
reason text: `FORBIDDEN_OBJECT` is the one shared refusal, and it deliberately says the same thing
for "no such object" and "not yours".

## The timing that changed

| Before | After |
| --- | --- |
| a matched role's condition and the shared `guard=` refused **before** the run existed | the object rule refuses **inside** the run, after connection validation |
| no start event was published for such a refusal | the run starts, the refusal is published, the run ends |
| the words were `WHEN` and `GUARD` | the word is `ACCESS_DECIDE` |

This is a consequence of the decision, not an accident: the documentation states it, and no pre-run
hook is reintroduced to preserve the old timing.

## Where the contract is asserted

- `packages/aoa-action-machine/tests/action_machine/intents/access_control/test_gate_order.py` —
  the phase split and the order.
- `.../test_cascade.py`, `.../test_cascade_decide.py` — a failing step becomes `Undecided`; the
  first answer wins.
- `.../test_verdict.py`, `.../exceptions/test_access_denied.py`,
  `.../exceptions/test_access_undecided.py` — the answers and their wire forms, including the
  rejection of a stored removed word.
- `packages/aoa-demo/tests/fastapi_mcp_services/test_cancel_order.py` — a refusal reaching a
  transport as a refusal.
