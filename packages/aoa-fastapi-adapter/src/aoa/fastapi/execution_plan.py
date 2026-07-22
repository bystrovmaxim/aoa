# packages/aoa-fastapi-adapter/src/aoa/fastapi/execution_plan.py
"""
EndpointExecutionPlan / PreparedEndpointContext — one recipe for ``.can()`` and ``.run()`` (issue #130).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Before this module, the real endpoint handlers (:mod:`aoa.fastapi.adapter`) and the
permissions resolver (:mod:`aoa.fastapi.permissions`) authenticated requests two
different ways: real handlers ran each route's own
``BaseAdapter.effective_auth_coordinator(record)`` and resolved that route's own
``connections``; the resolver ran one fixed adapter-level ``auth_coordinator`` for
every item in a batch and never resolved ``connections`` at all. Any route with a
route-level ``auth_coordinator`` override, or an ``access_decide`` that reads
``connections``, could answer "can I?" differently from what "do it" would actually
enforce — the exact divergence the resolver exists to prevent.

``EndpointExecutionPlan`` is the fix: one immutable per-route recipe (which auth
coordinator, which connections), built once when routes are registered. Both the
real endpoint and the resolver call :meth:`EndpointExecutionPlan.prepare` to turn
one HTTP request into a :class:`PreparedEndpointContext` — there is no second way to
get a ``Context``/``connections`` pair for a route.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    FastApiRouteRecord + effective_auth_coordinator
            │
            ▼
    EndpointExecutionPlan (frozen, built once per route at build() time)
            │  .prepare(request)
            ▼
    PreparedEndpointContext (request-scoped: this request's Context + connections)

Real endpoint handlers call ``plan.prepare(request)`` once per call. The resolver
calls it once per *distinct operation* in a batch (not once per item — auth and
connections do not depend on ``params``), via
:func:`build_execution_plan_index` + :meth:`EndpointExecutionPlan.prepare`.
"""

# Ruff/isort lists first-party ``action_machine`` before FastAPI (known-first-party).
# pylint: disable=wrong-import-order
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from aoa.action_machine.auth.auth_coordinator_protocol import AuthCoordinatorProtocol
from aoa.action_machine.context.context import Context
from aoa.action_machine.exceptions.authorization_error import AuthorizationError
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.resources.per_call_connection import resolve_connections
from aoa.fastapi.route_record import FastApiRouteRecord
from fastapi import Request


@dataclass(frozen=True)
class PreparedEndpointContext:
    """Request-scoped half of an :class:`EndpointExecutionPlan`: this call's auth result and connections."""

    context: Context
    connections: dict[str, BaseResource] | None


@dataclass(frozen=True)
class EndpointExecutionPlan:
    """
    Immutable per-route recipe: which auth coordinator to run and which connections
    to resolve for one route. Built once (route registration is fixed by the time
    ``FastApiAdapter.build()`` runs); never mutated or rebuilt per request.
    """

    record: FastApiRouteRecord
    auth_coordinator: AuthCoordinatorProtocol

    async def prepare(self, request: Request, *, reuse_context: Context | None = None) -> PreparedEndpointContext:
        """
        Run this route's own auth check and resolve this route's own connections.

        ``reuse_context``, when given, skips calling ``auth_coordinator.process(request)``
        again and uses that context directly — for the common case where a route does
        not override the adapter's default coordinator, the caller (the resolver) has
        typically already run that same default coordinator once for its own entry
        gate and can pass the result straight through instead of processing the same
        request twice. Callers must only pass a context that was itself produced by
        this exact ``auth_coordinator`` (see ``resolve_verdicts``' caller in ``adapter.py``).

        Raises:
            AuthorizationError: ``auth_coordinator.process(request)`` returned ``None``.
        """
        context = reuse_context if reuse_context is not None else await self.auth_coordinator.process(request)
        if context is None:
            raise AuthorizationError("Authentication required")
        connections = resolve_connections(self.record.connections)
        return PreparedEndpointContext(context=context, connections=connections)


def build_execution_plan_index(
    route_index: dict[str, FastApiRouteRecord],
    effective_auth_coordinator: Callable[[FastApiRouteRecord], AuthCoordinatorProtocol],
) -> dict[str, EndpointExecutionPlan]:
    """One :class:`EndpointExecutionPlan` per entry of an already-deduplicated route index."""
    return {
        operation: EndpointExecutionPlan(record=record, auth_coordinator=effective_auth_coordinator(record))
        for operation, record in route_index.items()
    }
