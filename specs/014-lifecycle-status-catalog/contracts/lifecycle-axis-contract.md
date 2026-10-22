# Contract: the axis names its type and checks its whole vocabulary

**Feature**: `specs/014-lifecycle-status-catalog` | **Date**: 2026-10-22

This is the contract of the lifecycle axis. The state type contract is [state-declaration-contract.md](./state-declaration-contract.md).

## 1. The declaration

```python
class OrderLifecycle(Lifecycle[OrderStateEntity]):
    _template = (
        Lifecycle()
        .state(OrderStateEntity.DRAFT).to(OrderStateEntity.PAID, OrderStateEntity.CANCELLED).initial()
        .state(OrderStateEntity.PAID).final()
        .state(OrderStateEntity.CANCELLED).final()
    )
```

- The axis names the state type once, in the generic parameter.
- The axis owns `_template` and nothing else; the catalogue is on the type.
- The names in `_template` are the declared attributes, qualified by the type.

## 2. The resolved type

| Aspect | Contract |
| --- | --- |
| Source | `__orig_bases__` of the class, read in `Lifecycle.__init_subclass__` |
| Stored as | `_state_type` on the axis class |
| Inheritance | A subclass with no generic base of its own inherits `_state_type` |
| Plain axis | A `Lifecycle` subclass without a parameter has no `_state_type` and is unchecked |
| No template | An intermediate class with a parameter but no own `_template` stores the type and checks nothing yet |

## 3. The two refusals

Both run when the axis class is created (import time), before any graph is built.

### 3.1 Foreign status

Every status named in `.state()` and `.to()` must be a declared object of the axis's type, by identity.

| Case | Error | Message |
| --- | --- | --- |
| The code is not declared on the type | `ForeignStateError` | The axis, the code, the type of the object, and the allowed codes |
| The code is declared but this is another instance | `ForeignStateError` | The axis, the code, that it is a different instance, and the declared attribute to use (`OrderStateEntity.DRAFT`) |
| The template uses a status of another type | `ForeignStateError` | Same as the undeclared case, naming the other type |
| The state type has no statuses and the template has states | `ForeignStateError` | The state type declares no statuses |

The attribute name in the "different instance" message is resolved through the MRO, so an inherited status names the attribute on the parent where it lives.

### 3.2 Missing status

Every declared status of the type must appear as a state in the template.

| Case | Error | Message |
| --- | --- | --- |
| A member is never listed with `.state(...)` | `MissingStateError` | The axis, the type, and the missing codes |
| A member is used only in `.to(...)` | `MissingStateError` | Same; a transition target is not a state |
| A subclass with its own template omits one of its declarations | `MissingStateError` | Same |

Coverage counts only `get_state_entities()`. The transition targets are checked for foreign statuses, not for coverage.

## 4. The plain escape

```python
class PlainLifecycle(Lifecycle):
    _template = Lifecycle().state(SOME_STATUS).final()
```

- No type parameter, no catalogue check; the behaviour is today's.
- The DSL still accepts any `BaseStateEntity`; the eight build rules still run at graph build.

## 5. Runtime and graph

| Surface | Contract |
| --- | --- |
| `OrderLifecycle(current_state="draft")` | Unchanged: the runtime instance, `current_state`, `current_status`, `transition`, `available_transitions`. |
| Entity field | `lifecycle: OrderLifecycle` unchanged. |
| Graph state row | `status.model_dump()` as attributes, `status.display_name` as label, the template's transitions unchanged. |
| Maxitor | The same five presentation keys; no change. |

## 6. Errors

| Error | Base | Where |
| --- | --- | --- |
| `ForeignStateError` | `TypeError` | `Lifecycle.__init_subclass__` |
| `MissingStateError` | `ValueError` | `Lifecycle.__init_subclass__` |

Both are public names exported from `aoa.action_machine.domain`; they carry AI-CORE blocks and one-line docstrings.

## 7. Requirement map

| Contract | Requirement |
| --- | --- |
| The generic declaration and `_state_type` | FR-007 |
| The foreign refusal | FR-008, FR-009 |
| The coverage refusal | FR-010 |
| Class-creation timing | FR-011 |
| The plain escape | FR-012 |
| The unchanged runtime and graph | FR-014 |
| The generic typing | FR-015 |
| The state kind and the eight rules | FR-018 |
