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
| | `reason` | `str` | A fixed code; `EVALUATION_FAILED` is the only one the core produces (FR-005) |
| | `_cause` | `BaseException \| None` | Private: never in `model_dump()`, never in an event, never in an answer (FR-016, D9) |

**Validation rules**

- An invalid answer fails as a validation error naming the field — no constructor guards, no custom exception classes.
- `kind` is the contract word: a class may be renamed without changing it (D1).
- A refusal is identical in `kind`, `gate` and `reason` whether the object does not exist or belongs to another caller (FR-011).

## Gate

An ordered step of the decision.

| Field | Type | Rules |
| --- | --- | --- |
| name | one of `AUTH_COORDINATOR`, `CHECK_ROLES`, `WHEN_OR_GUARD`, `ACCESS_DECIDE` | Published; travels on a refusal (FR-004) |
| order | fixed tuple position | who is calling → which roles → declared conditions → the object (FR-007) |
| answer | `Refused \| Undecided \| None` | `None` means the call may continue; the first non-`None` ends the decision |

**Rules**

- The first two gates never read the call's parameters and run before they are examined (FR-008).
- A gate that fails and a gate that answers undecided produce the same answer, with the same fixed reason (FR-005).
- Nothing in the engine inspects or restricts what a gate does with data it reads (clarification Q4).

## Reason vocabulary

| Constant | Produced by | Meaning |
| --- | --- | --- |
| `UNAUTHENTICATED` | the identity gate | Credentials were presented and rejected (FR-009) |
| `FORBIDDEN_ROLE` | the roles gate | No role the operation lists is held by the caller |
| `FORBIDDEN_GRANT` | the condition gate | A role's `when=` refused and no `reason=` was declared |
| `FORBIDDEN_GUARD` | the condition gate | The operation's `guard=` refused and no `reason=` was declared |
| `FORBIDDEN_OBJECT` | the object gate | One shared answer for "no such object" and "someone else's object" (FR-011) |
| `EVALUATION_FAILED` | the cascade | A gate could not tell — always `Undecided`, never `Refused` (FR-005) |

**Rules**: the list is fixed and published; a developer-declared reason is an addition to it, never a redefinition (FR-012). `FORBIDDEN_OBJECT` is one shared instance, and both cases must be answered from one branch (D5).

## Events (two new types)

| Entity | Field | Rules |
| --- | --- | --- |
| **AccessDecidedEvent** | the answer | The whole verdict, including `gate` and `reason` when refused (FR-013) |
| | which path | Whether the call asked in advance or executed |
| | request identity | Taken from the context when present; never invented (FR-013, SC-008) |
| **AccessGateFailedEvent** | the failure kind | The type of the failure, never its text (FR-014, FR-016) |
| | request identity | The same source and the same rule (FR-014) |

**Rules**

- Every decision publishes exactly one decision event, on both paths (FR-013, SC-001).
- A failed gate publishes the failed-gate event in addition to the decision event for the resulting undecided answer (FR-014).
- No event carries the text of a failure (FR-016, SC-007).
- Both are additions: every existing event keeps its name and what it carries (FR-015).
- The question path publishes no run-lifecycle event, because nothing was run (FR-017).

## Relationships

```text
call ──▶ decision ──▶ exactly one answer ──▶ exactly one decision event
              │
              ├─ refused ──▶ names its gate and its reason
              └─ undecided ──▶ keeps its cause in memory, publishes a failed-gate event
```

## What this model does not contain

- No storage, no cache, no persisted state: a decision exists for the duration of a call (FR-017).
- No batch or list shape: one call, one answer (D8).
- No transport fields: no status codes, no headers, no response bodies (spec Assumptions).
