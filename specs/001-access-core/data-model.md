# Phase 1 Data Model: Access decisions

The capability adds no storage. Everything below is data that exists for the duration of one call: an answer, the names that travel with it, and the events published from it.

## Answer

The result of a decision. Exactly one of three shapes, never a base instance and never a fourth word.

| Entity | Field | Type | Rules |
| --- | --- | --- | --- |
| **Verdict** (abstract base) | `kind` | `str` | No default, so `Verdict()` cannot be built: an answer of no particular kind is unrepresentable |
| **Allowed** | `kind` | `Literal["allowed"]` | The answer that lets the call continue (FR-003) |
| **Refused** | `kind` | `Literal["refused"]` | — |
| | `gate` | `Gate` | Always set; names the gate that refused (FR-004). Defaults to `ACCESS_DECIDE`, the one gate a developer writes |
| | `reason` | `str` | Non-empty, no whitespace-only value (FR-004). Either a fixed code or the developer's declared reason (FR-010, FR-012) |
| **Undecided** | `kind` | `Literal["undecided"]` | The answer a gate gives when it cannot tell (FR-003, FR-005) |
| | `gate` | `Gate` | Names the step that could not tell; the answer says where it stopped, not why (FR-005) |
| | `_cause` | `BaseException \| None` | Private: never in `model_dump()`, never in an event, never in an answer (FR-015, D9) |

**Validation rules**

- An invalid answer fails as a validation error naming the field — no constructor guards, no custom exception classes.
- `kind` is the contract word: a class may be renamed without changing it (D1).
- A refusal is identical in `kind`, `gate` and `reason` whether the object does not exist or belongs to another caller (FR-011).

## Gate

An ordered step of the decision.

| Field | Type | Rules |
| --- | --- | --- |
| name | one of `AUTH_COORDINATOR`, `CHECK_ROLES`, `WHEN`, `GUARD`, `ACCESS_DECIDE` | Published; travels on a refusal and on an undecided answer (FR-004, FR-005) |
| order | fixed tuple position | who is calling → the roles and each matching grant's condition (answering `CHECK_ROLES` or `WHEN`) → the operation's shared condition → the object (FR-007) |
| answer | `Refused \| Undecided \| None` | `None` means the call may continue; the first non-`None` ends the decision |

**Rules**

- The first two gates never read the call's parameters and run before they are examined (FR-008).
- A gate that fails and a gate that answers undecided produce the same answer, naming the step that could not tell (FR-005).
- Nothing in the engine inspects or restricts what a gate does with data it reads (clarification Q4).

## No framework vocabulary

The framework publishes the gate words and invents no reason text of its own (FR-012). A refusal names what refused; a reason appears only where a developer declared one beside their condition, and then it is their text, carried unchanged (FR-010).

| Word | What it means |
| --- | --- |
| `AUTH_COORDINATOR` | The credentials the caller presented were rejected (FR-009) |
| `CHECK_ROLES` | The caller holds none of the roles the operation lists |
| `WHEN` | A listed role is held, but the condition its grant declared refused |
| `GUARD` | The operation's shared condition refused |
| `ACCESS_DECIDE` | The object may not be touched; "no such object" and "someone else's object" are one shared answer, from one branch (FR-011, D5) |

**Rules**: the five words are the whole vocabulary; a `FORBIDDEN_OBJECT`-style shared refusal is one instance, and both of its cases must be answered from one branch.

## Object check (declared)

The operation's own answer about the object it is called on. Declared, never inherited, at most one; an operation that declares none has no object check (FR-018).

| Field | Rules |
| --- | --- |
| the declared callable | Reachable from the assembled capability as a node of its own, joined to the operation by a composition edge, the way the other declared behaviours are (FR-018) |
| its answer | One of the three answers; anything else, and any failure, becomes `Undecided` naming `ACCESS_DECIDE` (FR-005, FR-011) |
| its events | A before event whenever it starts and an after event whenever it finishes, whatever it answered — executing and asking in advance alike; a check that fails publishes no after event (FR-019) |

## The new event (one type)

| Entity | Field | Rules |
| --- | --- | --- |
| **AccessGateFailedEvent** | the gate | Which step could not tell (FR-013) |
| | the failure kind | The type of the failure, never its text (FR-013, FR-015) |
| | request identity | Taken from the context when present; never invented (FR-013, SC-008) |

A decision itself is not an entity of this model: it is an answer, delivered to one
caller at a time — raised as an exception when the call executes, returned when
someone asks in advance (FR-020).

**Rules**

- A gate that cannot complete publishes the failed-gate event while the call executes, and the decision itself is undecided (FR-013). Asking in advance publishes nothing of the kind.
- A refusal is published nowhere: the caller receives it, and a run that ends in one shows its `GlobalStart` without a `GlobalFinish`.
- No access decision reaches the operation's own failure handling: the engine builds no such logic in this capability (scope, not a requirement).
- No event carries the text of a failure (FR-014, SC-007).
- The event is an addition: every existing event keeps its name and what it carries (FR-013).
- The question path publishes no run-lifecycle event, because nothing was run (FR-015).

## Relationships

```text
call ──▶ decision ──▶ exactly one answer ──▶ the caller (exception or answer)
              │
              ├─ refused ──▶ names its gate and its reason
              └─ undecided ──▶ keeps its cause in memory, publishes a failed-gate event
```

## What this model does not contain

- No storage, no cache, no persisted state: a decision exists for the duration of a call (FR-016).
- No batch or list shape: one call, one answer (D8).
- No transport fields: no status codes, no headers, no response bodies (spec Assumptions).
