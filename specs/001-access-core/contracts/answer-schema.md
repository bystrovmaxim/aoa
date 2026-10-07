# Contract: the answer

The answer is data. A caller branches on `kind`, and on nothing else, to decide what to do next.

## The three words

| `kind` | Meaning | Extra fields the caller may rely on |
| --- | --- | --- |
| `allowed` | The call may proceed / would be allowed | — |
| `refused` | The call must not proceed | `gate` (which step refused), `reason` (why, non-empty) |
| `undecided` | Nobody could tell | `reason` (a fixed code) |

- `kind` is a published word, not a class name: renaming a class never changes what a caller reads (FR-003).
- `refused` and `undecided` are different words so that a caller can tell a policy decision from an inability to decide — and must never be treated as the same thing (FR-006).

## The fixed reasons

| Reason | Answers |
| --- | --- |
| `UNAUTHENTICATED` | credentials were presented and rejected |
| `FORBIDDEN_ROLE` | no role the operation lists is held by the caller |
| `FORBIDDEN_GRANT` | a role's `when=` refused, no reason declared |
| `FORBIDDEN_GUARD` | the operation's `guard=` refused, no reason declared |
| `FORBIDDEN_OBJECT` | the object does not exist, or is not the caller's — indistinguishable on purpose |
| `EVALUATION_FAILED` | a gate could not tell; always with `undecided` |

A developer may add their own reason text for a declared condition; the list above is what the framework itself answers with, and is additive (FR-012).

## What an answer never carries

- The text of a failure that happened inside a gate (FR-016).
- The cause of an `undecided` answer: it stays in memory for logging (D9).
- Anything about how a transport will present it (spec Assumptions).

## Guarantees a caller can test

1. A refusal names both the gate and a non-empty reason (FR-004, SC-002).
2. Two object-scoped refusals — "does not exist" and "belongs to someone else" — are identical in `kind`, `gate` and `reason` (FR-011, SC-003).
3. An `undecided` answer never reads as a refusal, and is never stored or reused as one (FR-006, SC-004).
4. The answer to a question about a call and the outcome of executing that call agree (FR-018, SC-006).
