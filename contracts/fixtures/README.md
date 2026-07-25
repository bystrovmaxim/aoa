# Contract fixtures

One JSON file = one complete `POST /permissions/resolve` response body. Each file is read
by **both** halves of the system, and both must agree about it:

| Reader | File |
| --- | --- |
| Python (`ResolveResponse`, pydantic) | `packages/aoa-fastapi-adapter/tests/test_resolve_contract.py` |
| TypeScript (`ResolveResponseSchema`, generated zod) | `packages/aoa-client-js/src/codegen/resolve-contract.test.ts` |

If someone changes the shape of a verdict on one side and not the other, one of the two
test files goes red. That is the entire point: the fixtures are the shared, executable
definition of "the same shape", not documentation about it.

## The valid ones — both sides must PARSE these

- **`resolve_response_basic.json`** — the original pair: allowed, plus a role-level denial
  carrying a human-readable reason.
- **`resolve_response_all_kinds_mixed.json`** — all three outcome classes in one response,
  proving a single batch can mix them and that order is positional.
- **`resolve_response_object_forbidden.json`** — oracle safety, on the wire. Two questions:
  one about an object that does not exist, one about an object belonging to someone else.
  Both answer **byte-identically** with `FORBIDDEN_OBJECT`. A future change that makes these
  two distinguishable would let anyone probe which IDs exist for other users, and this
  fixture is what fails first.
- **`resolve_response_unknown_endpoint.json`** — a `FailErrorVerdict` for an operation
  naming no registered route, next to a normal answer. Not a denial: the check never ran.
- **`resolve_response_evaluation_failed.json`** — a `FailErrorVerdict` for a check that
  crashed. Also not a denial. The reason is the fixed `EVALUATION_FAILED`, never the
  exception's own type or message.

## The broken ones — both sides must REJECT these

A test that accepts every file, however bad, is not a test. Each of these violates exactly
one rule:

- **`..._invalid_missing_reason.json`** — a failure verdict with no `reason` at all.
- **`..._invalid_empty_reason.json`** — `reason` present but empty.
- **`..._invalid_unknown_kind.json`** — a `kind` outside the closed set of three classes.
- **`..._invalid_extra_field.json`** — a field nobody declared. Both models forbid extras;
  silently dropping it would hide a server/client version mismatch instead of surfacing it.
- **`..._invalid_allowed_with_reason.json`** — `AllowedVerdict` carrying a `reason`.
  Success has no `reason` field *at all* — not an empty one. This is the invariant that
  keeps "allowed" and "denied" from being two settings of one type.
