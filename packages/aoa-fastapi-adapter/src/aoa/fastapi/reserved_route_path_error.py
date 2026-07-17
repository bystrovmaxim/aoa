# packages/aoa-fastapi-adapter/src/aoa/fastapi/reserved_route_path_error.py
"""
``ReservedRoutePathError`` — an app registered a route on a path the adapter itself owns.

═══════════════════════════════════════════════════════════════════════════════
WHY THIS EXISTS
═══════════════════════════════════════════════════════════════════════════════

``FastApiAdapter.build()`` registers its own bespoke routes (``/health``, and
since issue #130 PR 1, ``/permissions/resolve``) *before* looping over
``self._routes`` to register app-registered actions. Starlette resolves a
path/method collision by using whichever route was added to the router first —
it does not raise. Without this check, an app that accidentally calls
``adapter.post("/permissions/resolve", SomeAction)`` would get no error at all:
its action would simply never be reachable, silently shadowed by the resolver.
"""

from __future__ import annotations


class ReservedRoutePathError(ValueError):
    """Raised when an app-registered route's path collides with an adapter-owned bespoke route."""

    def __init__(self, path: str, method: str) -> None:
        super().__init__(
            f"{method} {path!r} is reserved by FastApiAdapter for its own bespoke route and cannot "
            "be registered via .post/.get/.put/.delete/.patch(...)."
        )
        self.path = path
        self.method = method
