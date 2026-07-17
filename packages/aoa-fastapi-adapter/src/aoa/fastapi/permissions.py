# packages/aoa-fastapi-adapter/src/aoa/fastapi/permissions.py
"""
Resolver helpers for ``POST /permissions/resolve`` (issue #130, PR 1 + PR 2).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Small, independent pieces of glue between the wire protocol
(:mod:`aoa.fastapi.permissions_schema`) and the machine's existing
``machine.check_access_decide`` primitive:

- :func:`build_action_index` / :func:`resolve_action_class` — map a wire
  ``operation`` string (an action class's bare ``__name__``, e.g.
  ``"CancelOrderAction"``) to its registered class via the graph, so the
  frontend never has to know a module path. A name shared by two different
  action classes is a configuration error, caught once at index-build time
  (adapter ``build()``), not repeated per request.

- :func:`to_wire` — project the internal ``AccessVerdict`` onto the wire
  ``Verdict`` shape. Deliberately conservative in this PR: ``scope`` only ever
  reports ``"role"`` or ``None`` (never ``"object"``, even when the machine
  really evaluated a level-3 ``access_decide``), and ``entities``/``reason_code``/
  ``expires_at`` stay at their reserved defaults. See PR 8 for why: reporting a
  real object-level verdict is only safe once a rate limit exists to stop it
  from becoming an ID-enumeration oracle.

- :func:`resolve_verdicts` (PR 2) — the actual batch resolver: deduplicates
  identical ``(operation, params)`` items so each distinct question triggers
  exactly one real ``check_access_decide`` call (run concurrently across
  distinct questions via ``asyncio.gather``, never a sequential loop), and
  isolates an unknown ``operation`` to that one item's verdict
  (``reason_code="UNKNOWN_ACTION"``) instead of failing the whole batch.
  Returns a :class:`ResolveOutcome` whose ``real_call_count`` lets tests assert
  on deduplication directly (by calling this function, not the HTTP endpoint) —
  ``real_call_count`` is never serialized onto the wire; the client has no
  business knowing which items were deduplicated internally (see chapter 2,
  "Кто на чём стоит: сервер и клиент в этой главе").
"""

# Ruff/isort lists first-party ``action_machine`` before FastAPI (known-first-party).
# pylint: disable=wrong-import-order
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from aoa.action_machine.context.context import Context
from aoa.action_machine.exceptions.check_access_decide_batch_size_exceeded_error import (
    CheckAccessDecideBatchSizeExceededError,
)
from aoa.action_machine.graph.core.node_graph_coordinator import NodeGraphCoordinator
from aoa.action_machine.graph.nodes.action_graph_node import ActionGraphNode
from aoa.action_machine.intents.access_control import AccessVerdict
from aoa.action_machine.intents.action_schema.action_schema_intent_resolver import ActionSchemaIntentResolver
from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.model.base_params import BaseParams
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.fastapi.permissions_schema import ResolveItem, Verdict
from fastapi import HTTPException

#: Dedup key: (operation name, canonical JSON serialization of raw params).
_DedupKey = tuple[str, str]


def build_action_index(graph_coordinator: NodeGraphCoordinator) -> dict[str, type[BaseAction]]:  # type: ignore[type-arg]
    """
    Build a ``{bare class name: action class}`` index from every registered action.

    Raises:
        ValueError: two different action classes share the same bare ``__name__``
            (``ActionGraphNode.label``) — a configuration error caught once here,
            at index-build time, rather than silently resolving to the wrong class
            on every matching request.
    """
    index: dict[str, type[BaseAction]] = {}  # type: ignore[type-arg]
    for node in graph_coordinator.get_nodes_by_type(ActionGraphNode.NODE_TYPE):
        name = node.label
        action_class = node.node_obj
        existing = index.get(name)
        if existing is not None and existing is not action_class:
            raise ValueError(
                f"Duplicate action name {name!r}: both {existing!r} and {action_class!r} are "
                "registered under the same operation name. Rename one of the action classes — "
                "the resolver cannot tell them apart on the wire."
            )
        index[name] = action_class
    return index


def resolve_action_class(
    operation: str,
    action_index: dict[str, type[BaseAction]],  # type: ignore[type-arg]
) -> type[BaseAction]:  # type: ignore[type-arg]
    """
    Look up the action class registered under a wire ``operation`` name.

    Raises:
        LookupError: no action is registered under ``operation``. Callers that
            want per-item isolation (a ``reason_code`` like ``UNKNOWN_ACTION``
            instead of failing the whole batch) catch this themselves — see
            :func:`resolve_verdicts`.
    """
    action_class = action_index.get(operation)
    if action_class is None:
        raise LookupError(f"Unknown operation {operation!r}: no action is registered under this name.")
    return action_class


def to_wire(verdict: AccessVerdict) -> Verdict:
    """
    Project an internal ``AccessVerdict`` onto the wire ``Verdict`` shape.

    ``scope`` is ``"role"`` whenever some cascade level rejected the check
    (``level`` is 1, 2, or 3), and ``None`` when the check passed outright
    (``AccessVerdict`` sets ``level=None`` exactly when ``allowed=True``).
    This PR never reports ``scope: "object"`` even for a real level-3 rejection
    — see the module docstring and PR 8.
    """
    return Verdict(
        allowed=verdict.allowed,
        scope="role" if verdict.level is not None else None,
        level=verdict.level,  # type: ignore[arg-type]
        reason=verdict.reason,
        reason_code=None,
        entities=[],
        expires_at=None,
    )


def canonical_key(params: dict[str, Any]) -> str:
    """
    Stable, field-order-independent serialization of raw ``params`` for dedup keying.

    Two items with the same field values in a different order must produce the same
    key. Full canonicalization (nested collection normalization beyond key order) is
    chapter 6's (cache) job — a sorted-keys JSON dump is enough for this PR's items,
    which are plain JSON objects decoded straight off the request body.
    """
    return json.dumps(params, sort_keys=True)


def _unknown_action_verdict() -> Verdict:
    return Verdict(allowed=False, scope=None, level=None, reason_code="UNKNOWN_ACTION")


@dataclass
class ResolveOutcome:
    """
    Result of :func:`resolve_verdicts`: the wire-shaped verdicts plus an internal count.

    ``real_call_count`` is the number of distinct ``(operation, params)`` keys that
    triggered an actual ``machine.check_access_decide`` call — i.e. the batch size
    *after* deduplication. It is not part of the wire protocol (see the module
    docstring): tests assert on it directly by calling ``resolve_verdicts``, the HTTP
    endpoint only ever reads ``verdicts``.
    """

    verdicts: list[Verdict]
    real_call_count: int


async def resolve_verdicts(
    context: Context,
    items: list[ResolveItem],
    action_index: dict[str, type[BaseAction]],  # type: ignore[type-arg]
    machine: ActionProductMachine,
) -> ResolveOutcome:
    """
    Resolve one verdict per ``items`` entry, deduplicating and isolating per-item errors.

    Two independent things happen in one pass over ``items`` (FR-3 and FR-4 of chapter 2):

    1. **Deduplication (FR-3).** Items are grouped by ``(operation, canonical_key(params))``.
       Only the *first* occurrence of a key (in request order) is resolved and checked;
       every later occurrence of the same key copies that same result onto its own
       position in the returned ``verdicts`` — the list is never shortened, only the
       amount of real work is. The real ``check_access_decide`` calls for distinct keys
       run concurrently via ``asyncio.gather``, not a sequential loop, so a batch of many
       *different* questions does not pay for one network round trip per question.
    2. **Per-item error isolation (FR-4).** An ``operation`` that names no registered
       action fails only its own key's positions with ``reason_code="UNKNOWN_ACTION"``,
       not the whole request. A ``ValidationError`` on a known action's params (malformed
       params, not an unknown action) still fails the whole request with HTTP 400 — this
       chapter introduces exactly one ``reason_code`` (``UNKNOWN_ACTION``); isolating other
       error classes is not in scope here.

    Raises:
        CheckAccessDecideBatchSizeExceededError: the number of *distinct* keys exceeds
            ``machine.max_check_access_decide_batch_size`` — checked up front, before touching
            any item. The list form's own built-in check (same exception type) never runs here,
            since deduplicated keys are dispatched one real call at a time via ``asyncio.gather``,
            not as one list passed to the list form — so this endpoint must enforce the same cap
            itself, against the size that actually matters post-dedup.
        HTTPException: 400, when a known action's params fail pydantic validation.
        TypeError: a registered action has no resolvable ``Params`` type — a server-side
            configuration bug, not a client input problem; left uncaught (-> HTTP 500).
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

    pending: dict[_DedupKey, tuple[type[BaseAction[Any, Any]], BaseParams | None]] = {}
    unknown_keys: set[_DedupKey] = set()

    for item, key in zip(items, item_keys, strict=True):
        if key in pending or key in unknown_keys:
            continue

        try:
            action_class = resolve_action_class(item.operation, action_index)
        except LookupError:
            unknown_keys.add(key)
            continue

        params_type = ActionSchemaIntentResolver.resolve_params_type(action_class)
        if params_type is None:
            # Action registered without a resolvable BaseAction[Params, Result] —
            # a server-side configuration bug, not a client input problem.
            raise TypeError(f"{action_class!r} has no resolvable Params type.")
        try:
            params: BaseParams | None = params_type.model_validate(item.params)
        except ValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        pending[key] = (action_class, params)

    pending_keys = list(pending.keys())
    real_verdicts: list[AccessVerdict] = (
        list(
            await asyncio.gather(
                *(machine.check_access_decide(context, action_class, params) for action_class, params in pending.values())
            )
        )
        if pending_keys
        else []
    )
    verdict_by_key = dict(zip(pending_keys, real_verdicts, strict=True))

    verdicts = [
        _unknown_action_verdict() if key in unknown_keys else to_wire(verdict_by_key[key]) for key in item_keys
    ]
    return ResolveOutcome(verdicts=verdicts, real_call_count=len(pending_keys))
