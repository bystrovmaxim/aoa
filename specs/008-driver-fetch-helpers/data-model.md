# Phase 1 — Data model: the helpers, their answers and the rules they hold

**Feature**: `specs/008-driver-fetch-helpers/spec.md` · **Date**: 2026-10-18

This feature adds no stored data of its own. What it defines are the *shapes* a domain sees: four protected members,
the four answers of the driver behind them, the two new answers, and the two demo reads that make them real. The
rules below are the ones the plan and the checks are written from.

## 1. The helper set on `PostgresResource`

| Member | Signature | Driver call | Answer on match | Answer on no match |
| --- | --- | --- | --- | --- |
| `_execute` | `(query: str, params: tuple[Any, ...] \| None = None) -> str` | `execute` | the command status, e.g. `"INSERT 0 1"` | not applicable |
| `_fetchrow` | `(query: str, params: tuple[Any, ...] \| None = None) -> Any` | `fetchrow` | the first row | `None` |
| **`_fetch`** | `(query: str, params: tuple[Any, ...] \| None = None) -> list[Any]` | `fetch` | every row, in the driver's order; one row as a list of one | `[]` |
| **`_fetchval`** | `(query: str, params: tuple[Any, ...] \| None = None) -> Any` | `fetchval` | the first value of the first row | `None` |

The two bold rows are what this feature adds. The first two are unchanged in shape and behaviour.

**Rules that hold for all four**

- The connection comes only from `_require_connection()`; a resource that never opened and one closed after opening
  both refuse with `HandleError("Connection is not open")`, and no `AttributeError` reaches the caller.
- A driver failure is turned into `HandleError(f"SQL execution failed: {e}")` with `__cause__` set to the original.
  No helper composes a message of its own.
- `params` is a positional tuple or `None`; `None` and `()` produce the same call, `conn.<method>(query)`.
- No helper opens a transaction, converts a row into a mapping, or decides an ordering.

## 2. The driver's answers and their ambiguity

| Query result | `_fetch` | `_fetchval` | `_fetchrow` |
| --- | --- | --- | --- |
| several rows | all of them, driver order | first value of the first row | first row |
| one row | `[row]` | the first value | the row |
| no row | `[]` | `None` | `None` |
| one row whose first value is `NULL` | `[row]` | `None` — indistinguishable from "no row" | the row |

The last row of that table is the pair's one irreducible ambiguity, inherited from the driver's `fetchval`. It is
stated in the helper's docstring and on both pages, and a caller that must distinguish the two asks for the row and
checks it — `_fetchrow` — rather than being given a sentinel or a second value helper.

## 3. The resource's state, and what each state answers

`PostgresResource` holds at most one connection for its unit of work, so a helper has exactly two reachable states:

```
built ──open()──▶ open ──close()──▶ closed
  │                 │                 │
  └──── helper ─────┴── helper ───────┘
       HandleError("Connection is not open")
```

- **built**: no connection; every helper refuses with the named failure.
- **open**: one connection; every helper runs on it, inside this unit of work's transaction when one is open.
- **closed**: no connection; every helper refuses with the same named failure as `built`.

The two new helpers introduce no third state and no transition of their own.

## 4. The demo's two reads

| Read | Reaches storage through | Answers | Statement shape |
| --- | --- | --- | --- |
| `_list_persons(limit: int = 20, offset: int = 0)` | `_fetch` | `list[dict[str, Any]]` — plain mappings, driver order preserved as stated by the statement | `SELECT id, email, display_name … ORDER BY display_name, id LIMIT $1 OFFSET $2` |
| `_count_persons()` | `_fetchval` | `int` — `0` when the helper answers `None` | `SELECT count(*) FROM identity_person_hub` |

Both are private, both live on the PostgreSQL store only, and the demo's suite is their caller. The driver-free base
(`IdentityStoreBase`) and the in-memory store (`IdentityStoreStub`) do not change: they keep `read_person` and
`record_login`, and neither grows a page or a count.

## 5. The two reads' edge states

| State | `_list_persons` | `_count_persons` |
| --- | --- | --- |
| nobody matches | `[]` | `0` (the driver answers `0`, not `None`, for a count over an empty table) |
| page past the end | `[]` | `0` only if the table is empty; a count is unaffected by the page |
| limit of zero | `[]` | a count is unaffected |
| driver refuses | `HandleError("SQL execution failed: …")`, chained | same |
| resource not open | `HandleError("Connection is not open")` | same |

The demo does not convert a refusal into a domain error of its own: the two reads are the demonstration of the
helpers' policy, and adding a second wrapping would hide the policy the reader came to see.

## 6. Validation rules carried from the requirements

- **FR-001 … FR-004**: the answer column of §1 is exact — `[]` is not `None`; a value is not a row or a tuple.
- **FR-005, FR-006**: §1's rules on the check and the wrapping; the closed-resource case is a named failure, and the
  driver's error is never raw.
- **FR-007**: `params` is a positional tuple; `None` and `()` are the same call; a mapping is outside the annotation
  and gets no runtime guard.
- **FR-008**: `_fetch` answers `list[Any]`; no driver type appears in either new signature.
- **FR-009**: exactly four members in §1 — no `_fetchmany`, `_executemany`, `_fetchval_or`, `_fetchrow_or`.
- **FR-010**: both helpers carry the multi-line docstring in the existing style, and `_fetchval`'s states the
  `NULL`/no-row ambiguity.
- **FR-015 … FR-020**: §4 and §5 of this document are the demo's contract, including the order, the bound and the
  untouched base and stub.
- **FR-024**: every shape here is checked with in-memory fakes; no state in this document requires a database.
