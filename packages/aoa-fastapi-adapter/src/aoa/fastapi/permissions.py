# packages/aoa-fastapi-adapter/src/aoa/fastapi/permissions.py
"""
Resolver helpers for ``POST /permissions/resolve`` (issue #130).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Small, independent pieces of glue between the wire protocol
(:mod:`aoa.fastapi.permissions_schema`) and the machine's existing
``machine.check_access_decide`` primitive:

- :func:`build_route_index` / :func:`resolve_route` — map a wire ``operation``
  string to its registered route. ``operation`` is the endpoint identifier
  ``"{method} {path}"`` (e.g. ``"POST /actions/cancel-order"``), the same string
  the manifest (chapter 3) publishes. The index is a projection of the adapter's
  ``self._routes``, not a graph traversal; a duplicate (method, path) is
  first-wins like the router, not an error.

- :func:`to_wire` — project the internal ``AccessVerdict`` onto the wire
  ``ResolveItemResult`` shape. Both are the same flat ``{kind, reason}`` pair
  now, one layer apart, so this is a straight copy, not a recomputation: the
  wire ``kind`` is the access-control cascade's own ``ResolveItemKind``, and
  ``reason`` is whatever ``AccessVerdict.reason`` already holds (the fixed
  ``"FORBIDDEN_ROLE"``, a developer-declared ``reason=`` string from
  ``when=``/``guard=``, or — for the one gate that mandatory-companion
  mechanism does not reach yet, ``access_decide`` — the raw cascade text or an
  unexpected exception's class name; see ``check_access_decide``'s own
  docstring in ``aoa-action-machine``).

- :func:`resolve_verdicts` — the actual batch resolver: deduplicates identical
  ``(operation, params)`` items so each distinct question triggers exactly one
  real ``check_access_decide`` call (run concurrently across distinct questions
  via ``asyncio.gather``, never a sequential loop). Each item is checked under its
  own route's :class:`~aoa.fastapi.execution_plan.EndpointExecutionPlan` — its own
  auth coordinator's result and its own resolved ``connections``, prepared by the
  caller once per distinct operation and passed in as ``prepared_by_operation``
  (never a single context/connections pair shared across every route in the batch;
  see ``execution_plan.py``). If the matched route carries a ``params_mapper``, the
  incoming params are mapped through it first — the same converter the real call
  would use — before ``access_decide``. An unknown ``operation`` is isolated to
  that one item's result (``kind=CHECK_ERROR, reason="UNKNOWN_ENDPOINT"``) instead
  of failing the whole batch. Returns a :class:`ResolveOutcome` whose ``real_call_count`` lets
  tests assert on deduplication directly (by calling this function, not the HTTP
  endpoint) — ``real_call_count`` is never serialized onto the wire; the client has
  no business knowing which items were deduplicated internally.
"""

# Ruff/isort lists first-party ``action_machine`` before FastAPI (known-first-party).
# pylint: disable=wrong-import-order
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any, cast

from pydantic import BaseModel, ValidationError

from aoa.action_machine.exceptions.check_access_decide_batch_size_exceeded_error import (
    CheckAccessDecideBatchSizeExceededError,
)
from aoa.action_machine.intents.access_control import AccessVerdict, ResolveItemKind
from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.fastapi.execution_plan import EndpointExecutionPlan, PreparedEndpointContext
from aoa.fastapi.permissions_schema import ResolveItem, ResolveItemResult
from aoa.fastapi.route_record import FastApiRouteRecord
from fastapi import HTTPException

#: Dedup key: (operation, canonical JSON serialization of raw params).
_DedupKey = tuple[str, str]


def build_route_index(routes: list[FastApiRouteRecord]) -> dict[str, FastApiRouteRecord]:
    """
    Build an ``{operation: route record}`` index from the adapter's registered routes.

    ``operation`` is the endpoint identifier ``"{method} {path}"`` (e.g.
    ``"POST /actions/cancel-order"``) — the same string the manifest publishes and
    the client sends. Registering the identical (method, path) twice is
    **first-wins**, exactly like Starlette's router: the second registration is
    unreachable in HTTP routing anyway, so the index keeps the first and raises
    nothing. Several routes for one action class on different paths/methods are not
    a conflict — each has its own distinct ``operation`` (and its own
    ``params_mapper``).
    """
    index: dict[str, FastApiRouteRecord] = {}
    for record in routes:
        operation = f"{record.method} {record.path}"
        index.setdefault(operation, record)  # first-wins, mirroring the router
    return index


def resolve_route(operation: str, route_index: dict[str, FastApiRouteRecord]) -> FastApiRouteRecord:
    """
    Look up the route registered under a wire ``operation`` identifier.

    ``resolve_verdicts`` does not call this directly — it looks up
    ``EndpointExecutionPlan`` entries (built from the same route index, see
    :func:`~aoa.fastapi.execution_plan.build_execution_plan_index`) and isolates an
    unmatched operation itself. This helper remains the plain, adapter-agnostic
    lookup for anything that only needs the route record.

    Raises:
        LookupError: no endpoint is registered under ``operation``.
    """
    record = route_index.get(operation)
    if record is None:
        raise LookupError(f"Unknown operation {operation!r}: no endpoint is registered under this identifier.")
    return record


def to_wire(verdict: AccessVerdict) -> ResolveItemResult:
    """
    Project an internal ``AccessVerdict`` onto the wire ``ResolveItemResult`` shape.

    Both are the same flat ``{kind, reason}`` pair — this is a straight copy, no
    recomputation. See the module docstring for what ``reason`` holds per channel.
    """
    return ResolveItemResult(kind=verdict.kind, reason=verdict.reason)


def canonical_key(params: dict[str, Any]) -> str:
    """
    Stable, field-order-independent serialization of raw ``params`` for dedup keying.

    Two items with the same field values in a different order must produce the same
    key. Full canonicalization (nested collection normalization beyond key order) is
    the cache chapter's job — a sorted-keys JSON dump is enough for these items,
    which are plain JSON objects decoded straight off the request body.
    """
    return json.dumps(params, sort_keys=True)


def _unknown_endpoint_verdict() -> ResolveItemResult:
    return ResolveItemResult(kind=ResolveItemKind.CHECK_ERROR, reason="UNKNOWN_ENDPOINT")


@dataclass
class ResolveOutcome:
    """
    Result of :func:`resolve_verdicts`: the wire-shaped results plus an internal count.

    ``real_call_count`` is the number of distinct ``(operation, params)`` keys that
    triggered an actual ``machine.check_access_decide`` call — i.e. the batch size
    *after* deduplication. It is not part of the wire protocol (see the module
    docstring): tests assert on it directly by calling ``resolve_verdicts``, the HTTP
    endpoint only ever reads ``results``.
    """

    results: list[ResolveItemResult]
    real_call_count: int


async def resolve_verdicts(
    items: list[ResolveItem],
    plan_index: dict[str, EndpointExecutionPlan],
    prepared_by_operation: dict[str, PreparedEndpointContext],
    machine: ActionProductMachine,
) -> ResolveOutcome:
    """
    Resolve one verdict per ``items`` entry, deduplicating and isolating per-item errors.

    Three things happen in one pass over ``items``:

    1. **Deduplication.** Items are grouped by ``(operation, canonical_key(params))``.
       Only the *first* occurrence of a key (in request order) is resolved and checked;
       every later occurrence copies that same result onto its own position in the
       returned ``results`` — the list is never shortened, only the amount of real
       work is. The real ``check_access_decide`` calls for distinct keys run
       concurrently via ``asyncio.gather``, not a sequential loop.
    2. **params_mapper reuse.** The wire ``params`` arrive in the route's request shape
       (``effective_request_model``). If the route has a ``params_mapper``, the resolver
       runs the validated request through it — the same converter the real call would
       use — and only the result goes to ``access_decide``. With no mapper the request
       shape *is* the action's ``Params``, so nothing changes.
    3. **Per-item error isolation.** An ``operation`` that names no registered endpoint
       fails only its own key's positions with ``kind=CHECK_ERROR, reason="UNKNOWN_ENDPOINT"``,
       not the whole request. A ``ValidationError`` on a known endpoint's params (malformed
       params, not an unknown endpoint) still fails the whole request with HTTP 400.

    Each item's real ``check_access_decide`` call runs under its own route's context
    and connections: ``prepared_by_operation[item.operation]``, prepared by the caller
    (see ``adapter.py``) once per distinct operation via
    ``EndpointExecutionPlan.prepare`` — never a single shared context/connections pair
    for the whole batch. Every operation reachable from ``items`` that has a matching
    entry in ``plan_index`` is expected to already have an entry in
    ``prepared_by_operation``; this function only looks it up, it never calls
    ``prepare`` itself (it has no ``Request`` to call it with).

    Raises:
        CheckAccessDecideBatchSizeExceededError: the number of *distinct* keys exceeds
            ``machine.max_check_access_decide_batch_size`` — checked up front, before
            touching any item.
        HTTPException: 400, when a known endpoint's params fail pydantic validation.
    """
    item_keys: list[_DedupKey] = [(item.operation, canonical_key(item.params)) for item in items]

    distinct_key_count = len(set(item_keys))
    if distinct_key_count > machine.max_check_access_decide_batch_size:
        raise CheckAccessDecideBatchSizeExceededError(
            f"POST /permissions/resolve received {distinct_key_count} distinct (operation, params) "
            f"items after deduplication, exceeding "
            f"max_check_access_decide_batch_size={machine.max_check_access_decide_batch_size}.",
            item_count=distinct_key_count,
            max_check_access_decide_batch_size=machine.max_check_access_decide_batch_size,
        )

    pending: dict[_DedupKey, tuple[type[BaseAction[Any, Any]], Any, PreparedEndpointContext]] = {}
    unknown_keys: set[_DedupKey] = set()

    for item, key in zip(items, item_keys, strict=True):
        if key in pending or key in unknown_keys:
            continue

        plan = plan_index.get(item.operation)
        if plan is None:
            unknown_keys.add(key)
            continue

        req_model = cast(type[BaseModel], plan.record.effective_request_model)
        try:
            body = req_model.model_validate(item.params)
        except ValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        mapper = plan.record.params_mapper
        params = mapper(body) if mapper is not None else body
        pending[key] = (plan.record.action_class, params, prepared_by_operation[item.operation])

    pending_keys = list(pending.keys())
    real_verdicts: list[AccessVerdict] = (
        list(
            await asyncio.gather(
                *(
                    machine.check_access_decide(prepared.context, action_class, params, connections=prepared.connections)
                    for action_class, params, prepared in pending.values()
                )
            )
        )
        if pending_keys
        else []
    )
    verdict_by_key = dict(zip(pending_keys, real_verdicts, strict=True))

    results = [
        _unknown_endpoint_verdict() if key in unknown_keys else to_wire(verdict_by_key[key]) for key in item_keys
    ]
    return ResolveOutcome(results=results, real_call_count=len(pending_keys))
