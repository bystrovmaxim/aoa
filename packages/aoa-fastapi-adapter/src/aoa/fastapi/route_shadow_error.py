# packages/aoa-fastapi-adapter/src/aoa/fastapi/route_shadow_error.py
"""
``RouteShadowError`` — two different path templates, same method, can match the same URL.

═══════════════════════════════════════════════════════════════════════════════
WHY THIS EXISTS
═══════════════════════════════════════════════════════════════════════════════

An exact ``(method, path)`` duplicate is harmless — Starlette's router (and, since
issue #130 chapter 3.5, both the manifest and the resolver) already agree on
"first registration wins", exactly like a real ``APIRouter`` would. But two
*different* templates whose matched URL sets overlap — ``/users/me`` registered
alongside ``/users/{id}``, or ``/users/{id}`` alongside ``/users/{name}`` — are a
genuine trap: Starlette still resolves every real request to whichever was
registered first, but the manifest would list *both* as if a client could reach
either one by choosing a path. A client that checked ``/users/me``'s permissions
and then actually called ``/users/{id}`` (because that is what the router sends
some or all matching requests to) would have asked the wrong question — the
button would lie, silently, for a routing reason no permissions check can see.

``FastApiAdapter.build()`` raises this eagerly, at build time, rather than let an
app start with a shadowed route already live.
"""

from __future__ import annotations


class RouteShadowError(ValueError):
    """Raised when two registered routes, same method, have overlapping path templates."""

    def __init__(self, method: str, path_a: str, path_b: str) -> None:
        super().__init__(
            f"{method} {path_a!r} and {method} {path_b!r} are different path templates that can "
            "match the same URL. Starlette would still route every real request to whichever was "
            "registered first, silently shadowing the other — the manifest and the resolver would "
            "disagree with the router about which endpoint a client can actually reach. Rename or "
            "rescope one of them so their paths cannot overlap."
        )
        self.method = method
        self.path_a = path_a
        self.path_b = path_b
