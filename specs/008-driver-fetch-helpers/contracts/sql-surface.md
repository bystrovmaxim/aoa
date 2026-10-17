# Contract: the SQL surface that does not move

**Feature**: `specs/008-driver-fetch-helpers/spec.md` · **Date**: 2026-10-18

This contract is a negative one: it fixes what this feature must leave exactly as 1.0.1a4 has it. It exists because
the cheapest way to give a domain rows and a value is to add a query member to the contract — and that is the one
thing the issue forbids, because it would undo [#216](https://github.com/bystrovmaxim/aoa/issues/216) and rebuild the
reach-through for every nested action.

## 1. The three shapes

| Shape | Member set after this feature | Change |
| --- | --- | --- |
| `ProtocolSqlResource` | lifecycle: `open`, `begin`, `commit`, `rollback`, `close`, `rollup`, `get_wrapper_class`, `check_rollup_support` | none |
| `SqlResource` | the same lifecycle, with `commit` from the base | none |
| `WrapperSqlResource` | `rollup`, `check_rollup_support`, the lifecycle refusals | none |

**SS-1.1** No member MUST be added to `ProtocolSqlResource`, `SqlResource` or `WrapperSqlResource`, public or
protected.

**SS-1.2** `WrapperSqlResource` MUST NOT expose `_fetch` or `_fetchval` in any form — not by delegation, not by
inheritance. It does not inherit from `PostgresResource`, and this feature MUST NOT change that.

**SS-1.3** A nested action receives the wrapper and therefore has no query surface at all. This is by construction,
not by a refusal: there is nothing to call.

**SS-1.4** `isinstance(wrapper, ProtocolSqlResource)` MUST stay true, as it is in 1.0.1a4, since neither the protocol
nor the wrapper changes.

## 2. The unchanged behaviour

**SS-2.1** `_execute` and `_fetchrow` MUST keep their signatures, their answers, their one check and their one
message.

**SS-2.2** `_require_connection`, `open`, `begin`, `commit`, `rollback`, `close` and the rollup behaviour MUST keep
the behaviour [#215](https://github.com/bystrovmaxim/aoa/issues/215) gave them, including the
`TransactionLeftOpenError` on closing with a transaction open.

**SS-2.3** No existing check MUST change meaning. New checks are additive, and the existing suites run unedited.

## 3. The searches that prove it

Run from the repository root; each must produce the stated result after the change.

```bash
# 1. No query member grew on the contract, the base or the wrapper.
grep -n "def _\?fetch\|def _\?execute" \
  packages/aoa-action-machine/src/aoa/action_machine/resources/sql/*.py
# expect: no hit

# 2. The four members exist on the driver, and no fifth query member does.
grep -n "async def _execute\|async def _fetchrow\|async def _fetch\b\|async def _fetchval\b" \
  packages/aoa-action-machine/src/aoa/action_machine/resources/postgres/postgres_resource.py
# expect: exactly four lines

# 3. The wrapper carries no query member, inherited or delegated.
uv run --extra dev python -c "
from aoa.action_machine.resources.sql import WrapperSqlResource as W
assert not hasattr(W, '_fetch') and not hasattr(W, '_fetchval')
print('the wrapper has no query member')
"
# expect: the one line

# 4. The protocol check is the suite's, because constructing a wrapper needs a real owner.
uv run --extra dev pytest \
  packages/aoa-action-machine/tests/action_machine/resources/test_wrapper_sql_resource.py -q
# expect: all cases pass, including the `isinstance` and the double and triple wrap
```

## 4. The compatibility promise

**SS-4.1** A consumer on `1.0.1a4` MUST NOT need an edit: nothing is removed, no abstract member appears, no
signature changes, and no name is repurposed.

**SS-4.2** The changelog article MUST claim no breaking change, and MUST NOT carry a `### Breaking changes` section.

**SS-4.3** The four members are an addition to the driver's protected surface, which the SQL contract's own
documentation has called the extension point since #216. Being protected, they are outside the promise a public
member gets — but adding them takes nothing away from anyone.
