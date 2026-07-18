# packages/aoa-fastapi-adapter/src/aoa/fastapi/permissions_schema.py
"""
Wire-protocol schemas for ``POST /permissions/resolve`` (issue #130).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Pydantic models for the resolver's request/response bodies. The protocol is
list-shaped from day one (``items``/``results``) — a single question is simply
a batch of one, not a separate code path (FR-2).

One flat shape for every answer: ``ResolveItemResult`` is always at least
``{kind, reason}``, never a nested "decision" vs "error" union and never a
grab-bag of independently-settable fields. Imported from ``aoa-action-machine``
(:class:`~aoa.action_machine.intents.access_control.ResolveItemResult`), not
redefined here — same reasoning as ``ResolveItemKind`` below: both HTTP and MCP
adapters depend on ``aoa-action-machine``, so that is the one place a shared wire
shape can live without either adapter depending on the other's package.
``AccessVerdict`` (also ``aoa-action-machine``) *is* a ``ResolveItemResult`` —
a subclass adding one internal-only field (``action``, excluded from
serialization) plus one derived, client-visible diagnostic field
(``action_name``) — not a separate type copied over by a `to_wire()` step; a
real ``AccessVerdict`` instance can be put directly into
``ResolveResponse.results``. ``results`` is typed
``list[SerializeAsAny[ResolveItemResult]]``, not plain ``list[ResolveItemResult]``,
specifically so ``action_name`` (and any future subclass-only field) actually
reaches JSON: pydantic v2 otherwise serializes a field by its *declared*
container type, silently dropping subclass-only fields regardless of
``exclude`` (confirmed empirically). The two synthetic items that never reach
the cascade at all (unknown operation, route-level auth rejection — see below)
construct a plain ``ResolveItemResult`` directly, so they carry no
``action_name`` at all, not an empty one — they honestly have no action to name.
``kind`` is the closed, small set of *source channels* an answer can come
through — also imported, not redefined, since it is what an access check itself
decides, one layer below this wire schema. ``SUCCESS`` carries ``reason=""``;
every other channel carries a non-empty, explicitly-declared string — never raw
exception text leaked by accident (``CHECK_ERROR`` is the one deliberate
exception to that promise: its ``reason`` is a fixed code, e.g.
``"UNKNOWN_ENDPOINT"``, or the class name of whatever unexpected exception was
actually raised).

A ``SECURITY`` denial's ``reason`` is ``AccessVerdict.reason`` verbatim: the
fixed ``"FORBIDDEN_ROLE"`` when no role matched, or the mandatory,
developer-declared string that came with the ``when=``/``guard=`` that rejected
the request (``access_decide``'s own denial-reason mechanism is a separate,
not-yet-done change — its rejections still surface raw cascade text). Object-level
and role-level denials still collapse onto the same ``SECURITY`` channel today
(minimal oracle contract: a caller cannot tell "missing" from "forbidden" from
the channel alone).

One ``SECURITY`` reason is not an ``AccessVerdict.reason`` at all: the fixed
``"UNAUTHORIZED"``, added by the resolver itself (``aoa.fastapi.permissions``),
never by the access-control cascade. It marks one *operation* in a batch whose
own route-level ``auth_coordinator`` (an ``EndpointExecutionPlan.prepare``
override, not the resolver's whole-request entry gate) rejected the caller —
isolated to that operation's own positions in ``results``, exactly like an
unknown ``operation`` is isolated to ``CHECK_ERROR``, so one route's stricter
auth requirement never fails every other question in the same batch.

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
a normal ``200`` with a ``CHECK_ERROR`` element inside ``results``; only a request
that never got that far uses this envelope. See chapter 3.5 rule 7's "whole
request vs. partial response" boundary.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, SerializeAsAny

from aoa.action_machine.intents.access_control import ResolveItemResult

__all__ = [
    "SUPPORTED_VERSION",
    "ErrorDetail",
    "ErrorEnvelope",
    "PermissionNamespace",
    "ResolveItem",
    "ResolveItemResult",
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
    results: list[SerializeAsAny[ResolveItemResult]] = Field(
        description="One result per request item, in the same order. Items backed by a "
        "real access check also carry action_name (diagnostic only, not part of the "
        "stable contract); synthetic items (unknown operation, route-level auth "
        "rejection) do not."
    )


class ErrorDetail(BaseModel):
    """The single machine-readable reason a whole request was rejected."""

    model_config = ConfigDict(extra="forbid")

    code: str = Field(description='Machine-readable error code, e.g. "unsupported_version".')


class ErrorEnvelope(BaseModel):
    """Body of a whole-request failure (``400``/``401``/``403``/``5xx``) — see the module docstring.

    Never used for a per-item problem: a single bad item inside an otherwise-valid
    batch is a ``ResolveItemResult(kind=CHECK_ERROR, ...)`` inside a normal ``200``
    ``ResolveResponse`` instead.
    """

    model_config = ConfigDict(extra="forbid")

    error: ErrorDetail = Field(description="The single machine-readable reason the whole request was rejected.")


class PermissionNamespace(BaseModel):
    """Body of ``GET /permissions/namespace``: this caller's opaque cache-partition label."""

    model_config = ConfigDict(extra="forbid")

    cache_partition: str = Field(
        description="Opaque label — attach verbatim to every cached resolver answer; never parse or reconstruct it."
    )
