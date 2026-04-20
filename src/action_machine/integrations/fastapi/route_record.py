# src/action_machine/integrations/fastapi/route_record.py
"""
FastApiRouteRecord — frozen route record for FastAPI adapter.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Concrete ``BaseRouteRecord`` subtype for HTTP transport metadata.
It stores one endpoint contract consumed by ``FastApiAdapter.build()``.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    Protocol registration
            |
            v
    FastApiAdapter.post/get/...(...)
            |
            v
    FastApiRouteRecord(
        action_class + mappers + HTTP metadata
    )
            |
            v
    FastApiAdapter.build()
            |
            v
    FastAPI route + OpenAPI operation

═══════════════════════════════════════════════════════════════════════════════
HTTP-SPECIFIC FIELDS
═══════════════════════════════════════════════════════════════════════════════

- ``method``: HTTP method, default ``"POST"``.
- ``path``: endpoint URL path, default ``"/"``.
- ``tags``: OpenAPI tags, default ``()``.
- ``summary``: short OpenAPI summary, default ``""``.
- ``description``: detailed OpenAPI description, default ``""``.
- ``operation_id``: optional operation identifier, default ``None``.
- ``deprecated``: deprecation flag, default ``False``.

"""

from __future__ import annotations

from dataclasses import dataclass

from action_machine.adapters.base_route_record import BaseRouteRecord

# Allowed HTTP methods.
_ALLOWED_METHODS: frozenset[str] = frozenset({
    "GET",
    "POST",
    "PUT",
    "DELETE",
    "PATCH",
})


@dataclass(frozen=True)
class FastApiRouteRecord(BaseRouteRecord):
    """
AI-CORE-BEGIN
    ROLE: Binds one action contract to one HTTP/OpenAPI endpoint declaration.
    CONTRACT: Extends BaseRouteRecord with method/path/tags/docs metadata.
    INVARIANTS: Frozen instance, validated method, validated path.
    AI-CORE-END
"""

    # ── HTTP-specific fields ───────────────────────────────────────────

    method: str = "POST"
    path: str = "/"
    tags: tuple[str, ...] = ()
    summary: str = ""
    description: str = ""
    operation_id: str | None = None
    deprecated: bool = False

    # ── Validation ──────────────────────────────────────────────────────

    def __post_init__(self) -> None:
        """
        Validate HTTP-specific invariants after instance construction.

        Order:

        1. Call ``super().__post_init__()`` to validate BaseRouteRecord
           invariants (action class, mapper contracts, generic extraction).

        2. Normalize method to uppercase.
           Because this is a frozen dataclass, ``object.__setattr__`` is used.

        3. Validate method against allowed set.

        4. Validate non-empty path starting with ``/``.

        Raises:
            TypeError: from BaseRouteRecord when base invariants fail.
            ValueError: from BaseRouteRecord mapper invariants, unsupported
                method, empty path, or missing leading slash.
        """
        # ── 1. BaseRouteRecord invariants ──
        super().__post_init__()

        # ── 2. Method normalization ──
        normalized_method = self.method.upper()
        object.__setattr__(self, "method", normalized_method)

        # ── 3. Method validation ──
        if normalized_method not in _ALLOWED_METHODS:
            allowed = ", ".join(sorted(_ALLOWED_METHODS))
            raise ValueError(
                f"method must be one of: {allowed}. "
                f"Got: '{self.method}'."
            )

        # ── 4. Path validation ──
        if not self.path or not self.path.strip():
            raise ValueError(
                "path cannot be empty. "
                "Provide an endpoint path, for example '/api/v1/orders'."
            )

        if not self.path.startswith("/"):
            raise ValueError(
                f"path must start with '/'. "
                f"Got: '{self.path}'. "
                f"Use a path like '/{self.path}'."
            )
