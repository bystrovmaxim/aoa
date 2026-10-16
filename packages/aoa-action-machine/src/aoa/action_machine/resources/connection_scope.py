# packages/aoa-action-machine/src/aoa/action_machine/resources/connection_scope.py
"""
connection_scope — the per-call lifecycle the boundary applies around a run.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A per-call declaration is a pair: a ``factory`` that creates the resource this
call needs, and a ``finalize`` that closes it and returns whatever it borrowed.
This module is the other half of that pair — the one place that applies it.

It walks the declaration itself, entry by entry, because it must know per entry
whether the framework created the resource: a ready resource is passed through
untouched and never opened or closed, while a ``PerCallConnection`` is created,
opened if it has something to open, and finalized exactly once.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    connection_scope(record.connections)
        │  walk the declaration, entry by entry
        ├── ready BaseResource   -> straight into the yielded mapping
        └── PerCallConnection    -> factory(), then open() when it has one
        │
        v  yield {key: resource}   ──>  machine.run(...)
        │
        finally: finalize() exactly once per created resource,
                 the opened ones first, then the rest, declaration order

    run failed, closing failed (operational) -> the run's error wins, the closing
                                                failure is recorded beside it
    any failure, a contract violation        -> the violation is raised, the run's
                                                error becomes its cause
    cancellation                             -> the cancellation propagates, the
                                                violation is recorded beside it

"""

from __future__ import annotations

import asyncio
import inspect
from collections.abc import AsyncIterator, Awaitable, Callable, Mapping
from contextlib import asynccontextmanager
from dataclasses import dataclass

from aoa.action_machine.exceptions.resource_contract_violation_error import ResourceContractViolationError
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.resources.per_call_connection import ConnectionValue, PerCallConnection


@dataclass
class _Created:
    """One resource this call created, and how it must be closed."""

    resource: BaseResource
    finalize: Callable[[BaseResource], Awaitable[None] | None]
    opened: bool = False


@asynccontextmanager
async def connection_scope(
    connections: Mapping[str, ConnectionValue] | None,
) -> AsyncIterator[dict[str, BaseResource] | None]:
    """
    AI-CORE-BEGIN
        ROLE: Apply the per-call lifecycle — open what this call created, yield it, finalize it once.
        CONTRACT: A ready resource is passed through untouched; a ``PerCallConnection`` has its factory called, its resource opened when it has an ``open``, and its finalizer called exactly once on every path.
        INVARIANTS: A contract violation raised while finalizing outranks the run's error, which becomes its cause; a cancellation outranks the violation and is recorded instead; an operational closing failure never hides the run's error.
    AI-CORE-END
    """
    if not connections:
        yield None
        return

    resolved: dict[str, BaseResource] = {}
    created: list[_Created] = []
    failure: BaseException | None = None

    try:
        for key, value in connections.items():
            if isinstance(value, BaseResource):
                resolved[key] = value
                continue
            if not isinstance(value, PerCallConnection):
                raise TypeError(
                    "Connection value must be a BaseResource or PerCallConnection, "
                    f"got {type(value).__name__!r} for key {key!r}."
                )
            resource = value.factory()
            record = _Created(resource=resource, finalize=value.finalize)
            created.append(record)
            if hasattr(resource, "open"):
                await resource.open()
                record.opened = True
            resolved[key] = resource

        yield resolved
    except BaseException as error:
        failure = error
        raise
    finally:
        # Finalization always runs, and always to completion: a second cancellation must not
        # cut it short, so it is shielded, and the cancellation is re-raised after it.
        cleanup = asyncio.ensure_future(_finalize_created(created, failure))
        try:
            await asyncio.shield(cleanup)
        except asyncio.CancelledError:
            if not cleanup.done():
                await cleanup
            raise


def _opened_first(created: list[_Created]) -> list[_Created]:
    """The resources that were opened come first; then the ones whose opening never ran."""
    return [record for record in created if record.opened] + [record for record in created if not record.opened]


async def _finalize_created(created: list[_Created], failure: BaseException | None) -> None:
    """
    Call every finalizer exactly once and apply the precedence rules.

    Runs in its own task, so the caller's cancellation cannot stop it halfway.
    """
    cancellation = failure if isinstance(failure, asyncio.CancelledError) else None
    violation: ResourceContractViolationError | None = None
    operational: BaseException | None = None

    for record in _opened_first(created):
        try:
            result = record.finalize(record.resource)
            if inspect.isawaitable(result):
                await result
        except ResourceContractViolationError as error:
            if violation is None:
                violation = error
        except BaseException as error:  # recorded, then applied by the precedence rules below
            if operational is None:
                operational = error

    if cancellation is not None:
        # The caller is being cancelled: that is what it must see. What went wrong while
        # finalizing is recorded beside it rather than replacing it.
        if violation is not None:
            cancellation.add_note(f"a closing contract violation was recorded: {violation!r}")
        if operational is not None:
            cancellation.add_note(f"a closing failure was recorded: {operational!r}")
        return

    if violation is not None:
        raise violation from failure

    if operational is not None:
        if failure is not None:
            failure.add_note(f"a closing failure was recorded: {operational!r}")
            return
        raise operational
