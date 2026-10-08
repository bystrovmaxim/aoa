# Contract: the answer

The answer is data. A caller branches on `kind`, and on nothing else, to decide what to do next.

## The three words

| `kind` | Meaning | Extra fields the caller may rely on |
| --- | --- | --- |
| `allowed` | The call may proceed / would be allowed | — |
| `refused` | The call must not proceed | `gate` (what refused), `reason` (what the developer declared, when they declared one) |
| `undecided` | Nobody could tell | `gate` (the step that could not tell) |

- `kind` is a published word, not a class name: renaming a class never changes what a caller reads (FR-003).
- `refused` and `undecided` are different words so that a caller can tell a policy decision from an inability to decide — and must never be treated as the same thing (FR-006).

## The five words a caller branches on

| `gate` | What refused, or could not tell |
| --- | --- |
| `AUTH_COORDINATOR` | the credentials the caller presented were rejected — reserved to the transport: a transport that authenticates refuses before it asks the engine for a decision, so this word never appears in an answer the core produces |
| `CHECK_ROLES` | the caller holds none of the roles the operation lists |
| `WHEN` | a listed role is held, but the condition its grant declared refused |
| `GUARD` | the operation's shared condition refused |
| `ACCESS_DECIDE` | the object the call is about — "does not exist" and "not yours" are one answer on purpose |

The framework publishes these words and invents no reason text of its own. `reason` carries what a developer declared beside their condition, and it is absent when they declared none; a caller branches on `gate` and, where a reason is present, reads it as the developer's own words (FR-010, FR-012).

## What an answer never carries

- The text of a failure that happened inside a gate (FR-015).
- The cause of an `undecided` answer: it stays in memory for logging (D9).
- Anything about how a transport will present it (spec Assumptions).

## Guarantees a caller can test

1. A refusal always names its gate, and a declared reason arrives unchanged; nothing is invented where none was declared (FR-004, SC-002).
2. Two object-scoped refusals — "does not exist" and "belongs to someone else" — are identical in `kind`, `gate` and `reason` (FR-011, SC-003).
3. An `undecided` answer never reads as a refusal, and is never stored or reused as one (FR-006, SC-004).
4. The answer to a question about a call and the outcome of executing that call agree (FR-017, SC-006).

## How the answer reaches the caller

The same answer, delivered the way each path can deliver it (FR-020):

| Path | Delivery | Carries |
| --- | --- | --- |
| executing | raised as an exception | `AccessDenied(verdict)` when refused, `AccessUndecided(verdict)` when nobody could tell |
| asking in advance | returned | `Allowed()`, `Refused(gate=…)`, `Undecided(gate=…)` — no exception is ever raised on this path |

Both paths carry the same fields and nothing else. The failure's cause travels only inside an `Undecided` in memory: it is never published, never serialised and never handed to a caller (FR-005, FR-015).

### What each point hands over

| Point | Situation | Executing: exception and its parameters | Asking: returned |
| --- | --- | --- | --- |
| identity | passed | nothing raised | nothing (the decision continues) |
| | refused | `AccessDenied(Refused(gate=Gate.AUTH_COORDINATOR))` — no reason: rejected credentials are not explained | `Refused(gate=Gate.AUTH_COORDINATOR)` |
| | could not tell | `AccessUndecided(Undecided(gate=Gate.AUTH_COORDINATOR, cause=<failure>))` | `Undecided(gate=Gate.AUTH_COORDINATOR, cause=<failure>)` |
| roles | passed | nothing raised | nothing (the decision continues) |
| | refused: no listed role held | `AccessDenied(Refused(gate=Gate.CHECK_ROLES))` — no reason: the developer declared none | `Refused(gate=Gate.CHECK_ROLES)` |
| | refused: a matching grant's condition | `AccessDenied(Refused(gate=Gate.WHEN, reason=<declared or absent>))` | `Refused(gate=Gate.WHEN, reason=<declared or absent>)` |
| | could not tell | `AccessUndecided(Undecided(gate=Gate.CHECK_ROLES, cause=<failure>))` | `Undecided(gate=Gate.CHECK_ROLES, cause=<failure>)` |
| condition | passed | nothing raised | nothing (the decision continues) |
| | refused | `AccessDenied(Refused(gate=Gate.GUARD, reason=<declared or absent>))` | `Refused(gate=Gate.GUARD, reason=<declared or absent>)` |
| | could not tell | `AccessUndecided(Undecided(gate=Gate.GUARD, cause=<failure>))` | `Undecided(gate=Gate.GUARD, cause=<failure>)` |
| object | passed | nothing raised | `Allowed()` |
| | refused | `AccessDenied(Refused(gate=Gate.ACCESS_DECIDE, reason=<what the check answered, else absent>))` | `Refused(gate=Gate.ACCESS_DECIDE, reason=<what the check answered, else absent>)` |
| | could not tell | `AccessUndecided(Undecided(gate=Gate.ACCESS_DECIDE, cause=<failure>))` | `Undecided(gate=Gate.ACCESS_DECIDE, cause=<failure>)` |

`reason` is the developer's own text and appears only where they declared one (FR-010, FR-012): the framework names the gate and stops there. `gate` is always one of the five published words. An operation that declares no object check passes that point without raising anything, and that point's word is always `ACCESS_DECIDE`.
