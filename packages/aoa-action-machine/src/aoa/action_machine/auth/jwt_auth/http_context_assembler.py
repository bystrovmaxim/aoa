# packages/aoa-action-machine/src/aoa/action_machine/auth/jwt_auth/http_context_assembler.py
"""
HttpContextAssembler — default RequestInfo projection for HTTP requests.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``ContextAssembler`` implementation used by ``JwtAuthCoordinator`` unless the
caller supplies its own. Reads the request path from ``request_data.url.path``
(Starlette's ``Request`` has no top-level ``.path`` attribute — only ``.url.path``)
and the client IP from ``request_data.client.host`` when available.
"""

from __future__ import annotations

from typing import Any

from aoa.action_machine.auth.auth_coordinator import ContextAssembler


class HttpContextAssembler(ContextAssembler):
    """
    AI-CORE-BEGIN
    ROLE: Project HTTP request metadata into RequestInfo kwargs.
    CONTRACT: request_data exposes .url.path, .headers, and optionally .method / .client.host (Starlette Request shape).
    AI-CORE-END
    """

    async def assemble(self, request_data: Any) -> dict[str, Any]:
        client = getattr(request_data, "client", None)
        return {
            "request_path": request_data.url.path,
            "request_method": getattr(request_data, "method", None),
            "full_url": str(request_data.url),
            "client_ip": client.host if client else None,
            "trace_id": request_data.headers.get("x-trace-id"),
            "protocol": "http",
        }
