# packages/aoa-fastapi-adapter/src/aoa/fastapi/permissions_schema.py
"""
Wire-protocol schemas for ``POST /permissions/resolve`` (issue #130, PR 1).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Pydantic models for the resolver's request/response bodies. The protocol is
list-shaped from day one (``items``/``verdicts``), even though this PR only
answers role-gate questions — a single question is simply a batch of one, not
a separate code path (FR-2).

Several ``Verdict`` fields are reserved here but not populated by ``to_wire()``
in this PR: ``scope`` never reports ``"object"`` (only ``"role"``/``None``),
``entities`` is always ``[]``, ``reason_code`` is always ``None``, ``expires_at``
is always ``None``. Populating them for real is later chapters' job (object-level
reporting + rate limiting: PR 8; reason-code taxonomy: PR 2; cache TTL: PR 6).
Reserving the field now and populating it later is not a breaking wire change;
changing the shape after clients depend on it would be.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ResolveItem(BaseModel):
    """One question in a resolve batch: an action name plus its raw parameters."""

    model_config = ConfigDict(extra="forbid")

    operation: str = Field(description='Endpoint identifier "{method} {path}", e.g. "POST /actions/cancel-order".')
    params: dict[str, Any] = Field(default_factory=dict, description="Raw action parameters (validated server-side).")
    context: dict[str, Any] | None = Field(
        default=None,
        description="Reserved for future client-supplied ABAC hints; ignored by the server in this PR.",
    )


class ResolveRequest(BaseModel):
    """Body of ``POST /permissions/resolve``: a versioned, non-empty batch of questions."""

    model_config = ConfigDict(extra="forbid")

    protocol: int = Field(description="Wire-protocol version known to the client at build time.")
    items: list[ResolveItem] = Field(min_length=1, description="Batch of questions, answered in the same order.")


class Verdict(BaseModel):
    """One answer in a resolve batch, positionally matched to its ``ResolveItem``."""

    model_config = ConfigDict(extra="forbid")

    allowed: bool = Field(description="Whether the action is permitted.")
    scope: Literal["role", "object"] | None = Field(
        default=None,
        description='"role" once a role-level check decided the outcome; null if no level rejected it (allowed).',
    )
    level: Literal[1, 2, 3] | None = Field(
        default=None,
        description="Cascade level that rejected the check (1 role, 2 guard, 3 access_decide); null when allowed.",
    )
    reason: str | None = Field(default=None, description="Developer-facing text, not meant for end-user display.")
    reason_code: str | None = Field(default=None, description="Stable machine-readable reason code (see PR 2).")
    entities: list[str] = Field(default_factory=list, description="Entity tags the verdict is scoped to (see PR 8).")
    expires_at: datetime | None = Field(default=None, description="How long the verdict may be cached (see PR 6).")


class ResolveResponse(BaseModel):
    """Body of the ``POST /permissions/resolve`` response: one verdict per request item, same order."""

    model_config = ConfigDict(extra="forbid")

    protocol: int = Field(description="Echoes the request's protocol version.")
    verdicts: list[Verdict] = Field(description="One verdict per request item, in the same order.")
