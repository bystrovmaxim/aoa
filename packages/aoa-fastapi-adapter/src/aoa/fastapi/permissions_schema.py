# packages/aoa-fastapi-adapter/src/aoa/fastapi/permissions_schema.py
"""
Wire-protocol schemas for ``POST /permissions/resolve`` (issue #130).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Pydantic models for the resolver's request/response bodies. The protocol is
list-shaped from day one (``items``/``results``) — a single question is simply
a batch of one, not a separate code path (FR-2).

One class per answer, not one flag per answer: every result is a
``BaseVerdict`` subclass — ``AllowedVerdict`` (success, no ``reason`` field at
all) or ``FailSecurityVerdict``/``FailErrorVerdict`` (both carry a mandatory,
non-empty ``reason``). Imported from ``aoa-action-machine``
(:class:`~aoa.action_machine.intents.access_control.BaseVerdict` and its
subclasses), not redefined here — both HTTP and MCP adapters depend on
``aoa-action-machine``, so that is the one place a shared wire shape can live
without either adapter depending on the other's package. ``kind`` is not a
free-standing enum field a caller could set to a mismatched value — ``BaseVerdict.__init__``
fills it in from ``type(self).__name__`` when omitted and rejects a mismatched
explicit value; the set of possible ``kind`` values is exactly the set of
``BaseVerdict`` subclasses that exist, not a central list to keep in sync.
``results`` is typed ``list[SerializeAsAny[BaseVerdict]]``, not plain
``list[BaseVerdict]``, so each item serializes by its actual runtime class:
pydantic v2 otherwise serializes a field by its *declared* container type,
silently dropping subclass-only fields (confirmed empirically).

``FailSecurityVerdict`` is a real access-control denial: ``FORBIDDEN_ROLE``
(no role matched at all), ``FORBIDDEN_GRANT``/``FORBIDDEN_GUARD`` (a
``when=``/``guard=`` condition rejected and the developer gave no ``reason=``),
a developer-declared reason on ``grant()``/``check_roles(guard=...)``, or
whatever ``access_decide()`` itself returns. ``UNAUTHORIZED`` is the one
``FailSecurityVerdict`` that is not a cascade decision at all — added by the
resolver itself (``aoa.fastapi.permissions``), it marks one *operation* in a
batch whose own route-level ``auth_coordinator`` (an
``EndpointExecutionPlan.prepare`` override, not the resolver's whole-request
entry gate) rejected the caller, isolated to that operation's own positions in
``results`` so one route's stricter auth requirement never fails every other
question in the same batch. Object-level and role-level denials still collapse
onto the same ``FailSecurityVerdict`` class today (minimal oracle contract: a
caller cannot tell "missing" from "forbidden" from the class alone).

``FailErrorVerdict`` is not a denial and must never be cached as one — the
check itself could not be answered. ``UNKNOWN_ENDPOINT`` (an ``operation`` that
names no registered route) is the resolver's own fixed code; any other
``FailErrorVerdict`` carries the crashing exception's class name as ``reason``.

``PermissionNamespace`` — the opaque ``cache_partition`` label a client attaches
to every cached resolver answer, so a cache entry can never be mistakenly shared
across two identities. It is issued by ``GET /permissions/namespace`` (see
``adapter.py``), never by the manifest (which must be identical for every
caller to stay cacheable and code-generatable) and never by ``ResolveResponse``
itself (that would be too late — the client needs the label *before* it can even
look an answer up in its cache). The label is computed fresh from the caller's
current identity on every call (see
:func:`~aoa.action_machine.auth.compute_cache_partition`), so it changes
automatically whenever that identity does — a different ``user_id``, or the same
user with a different set of roles — with no session store required.

═══════════════════════════════════════════════════════════════════════════════
VERSIONING AND THE ERROR ENVELOPE
═══════════════════════════════════════════════════════════════════════════════

``SUPPORTED_VERSION`` is the wire-language version this server speaks — the same
number ``aoa.fastapi.manifest.Manifest.version`` publishes, so a client can read
it from the catalog before ever calling the resolver. ``ResolveRequest.version``
is the version the client built its request for; the resolver checks it *first*,
before authentication, and rejects a mismatch with ``UnsupportedVersionError``
(``aoa.fastapi.unsupported_version_error``) rather than guessing at a request
shaped for a contract it does not speak — see chapter 3.5 rule 8.

``ErrorEnvelope`` (``{"error": {"code": "..."}}``) is the body of a *whole-request*
failure — unsupported version, failed authentication, an uncaught server error —
never a per-item problem. A single bad item inside an otherwise-valid batch stays
a normal ``200`` with a ``FailErrorVerdict`` element inside ``results``; only a
request that never got that far uses this envelope. See chapter 3.5 rule 7's
"whole request vs. partial response" boundary.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, SerializeAsAny

from aoa.action_machine.intents.access_control import BaseVerdict

__all__ = [
    "SUPPORTED_VERSION",
    "BaseVerdict",
    "ErrorDetail",
    "ErrorEnvelope",
    "PermissionNamespace",
    "ResolveItem",
    "ResolveRequest",
    "ResolveResponse",
]

# Wire-language version this server speaks. Draft until chapter 3.5's contract
# settles, then becomes v1 — see rule 8. Echoed by ResolveResponse.version and
# published as Manifest.version, so both live sources agree by construction.
SUPPORTED_VERSION = 1


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

    version: int = Field(description="Wire-language version this request was built for.")
    items: list[ResolveItem] = Field(min_length=1, description="Batch of questions, answered in the same order.")


class ResolveResponse(BaseModel):
    """Body of the ``POST /permissions/resolve`` response: one result per request item, same order."""

    model_config = ConfigDict(extra="forbid")

    version: int = Field(description="Echoes the request's wire-language version.")
    results: list[SerializeAsAny[BaseVerdict]] = Field(
        description="One result per request item, in the same order. kind names which "
        "BaseVerdict subclass answered: AllowedVerdict (success, no reason field), "
        "FailSecurityVerdict (a real denial, reason mandatory), or FailErrorVerdict "
        "(the check could not be answered, never a denial, never cached as one)."
    )


class ErrorDetail(BaseModel):
    """The single machine-readable reason a whole request was rejected."""

    model_config = ConfigDict(extra="forbid")

    code: str = Field(description='Machine-readable error code, e.g. "unsupported_version".')


class ErrorEnvelope(BaseModel):
    """Body of a whole-request failure (``400``/``401``/``403``/``5xx``) — see the module docstring.

    Never used for a per-item problem: a single bad item inside an otherwise-valid
    batch is a ``FailErrorVerdict`` inside a normal ``200`` ``ResolveResponse``
    instead.
    """

    model_config = ConfigDict(extra="forbid")

    error: ErrorDetail = Field(description="The single machine-readable reason the whole request was rejected.")


class PermissionNamespace(BaseModel):
    """Body of ``GET /permissions/namespace``: this caller's opaque cache-partition label."""

    model_config = ConfigDict(extra="forbid")

    cache_partition: str = Field(
        description="Opaque label — attach verbatim to every cached resolver answer; never parse or reconstruct it."
    )
