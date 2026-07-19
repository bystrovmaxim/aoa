# packages/aoa-fastapi-adapter/src/aoa/fastapi/manifest.py
"""
Client manifest — projection of registered routes for ``GET /client-manifest.json``
(issue #130, chapter 3).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``build_manifest`` turns the adapter's registered routes (``self._routes``) into
a machine-readable catalog of endpoints. It is a **pure projection**: no graph
traversal, no ``Context``, no role filtering. Everything it needs already lives
on each ``FastApiRouteRecord`` (method, path, action class, request/response
models) — the same records ``build()`` uses to create the real endpoints.

═══════════════════════════════════════════════════════════════════════════════
ENDPOINTS, NOT ACTIONS
═══════════════════════════════════════════════════════════════════════════════

The manifest lists **endpoints**, keyed by ``operation = "{method} {path}"`` —
not action classes. One ``action_class`` registered on several routes (different
paths/methods, e.g. API versions via ``params_mapper``) yields several
independent entries; there is no dedup and no error on that. An action never
registered via ``.post/.get/.put/.delete/.patch(...)`` simply never appears —
it is not in ``routes``, so it cannot be in the manifest.

A *different* case — the exact same ``(method, path)`` registered twice — **is**
deduplicated, first-wins: Starlette's real router only ever reaches the first
registration (the second is unreachable), so the manifest must agree with it
instead of listing an endpoint no request can actually reach. This reuses
:func:`~aoa.fastapi.permissions.build_route_index` directly rather than
reimplementing the same rule a second time (audit finding 10) — one function
decides "first wins" for both the catalog and the resolver, not two
independently-written ones that merely agree today.
Deduplication happens *before* ``manifest_version`` is computed, so the hash
reflects the manifest's real, deduplicated content rather than some unstable
pre-dedup state — registering the same duplicate again in a different order
produces the same version. (Two *different* templates that could match the
same URL, e.g. ``/users/me`` alongside ``/users/{id}``, are not a duplicate —
``FastApiAdapter.build()`` fails the build for that case; see
``RouteShadowError``.)

Because the source is ``FastApiRouteRecord`` (method, path, class, request/
response models), the body of any access condition (``guard=``/``when=``/
``access_decide``) structurally cannot leak into the manifest: those function
bodies are not part of a route record, so there is nothing to serialize.

═══════════════════════════════════════════════════════════════════════════════
THREE NUMBERS, NOT ONE
═══════════════════════════════════════════════════════════════════════════════

``Manifest`` carries three separate version numbers, easy to conflate but
answering three different questions:

- ``version`` — the resolver wire-language version (``POST /permissions/resolve``
  speaks the same number — see ``aoa.fastapi.permissions_schema.SUPPORTED_VERSION``,
  the single source both this module and the resolver read).
- ``manifest_schema_version`` — the version of the manifest's own *shape* (this
  module's models). Bumps only when a field is added, removed, or its meaning
  changes here — independent of ``version`` and of how many routes happen to be
  registered right now.
- ``manifest_version`` — a content hash of *this* manifest's actual endpoints
  (see ``build_manifest``), the value the HTTP layer publishes as the ``ETag``.

Visibility — what ends up in the manifest at all — is not a flag on this
module: whatever is registered on the *public* ``FastApiAdapter`` instance ends
up here; an application keeps internal/service-only actions off the manifest by
registering them on a separate, non-public adapter instead. There is
deliberately no per-action "hide from manifest" switch to keep in sync with
anything else.

═══════════════════════════════════════════════════════════════════════════════
REFERENCE SCHEMAS (``schemas``)
═══════════════════════════════════════════════════════════════════════════════

A client that wants to *validate* what it sends and receives needs an
authoritative description of every fixed wire message's shape — not the
per-action ``params_schema``/``result_schema`` already on each
``ManifestEndpoint`` (those describe one action), but the small, closed set of
messages the protocol itself is built from: ``ResolveRequest``,
``ResolveResponse``, ``BaseVerdict``, the error envelope, and the catalog's
own shape. ``build_manifest`` publishes all five under one key, ``schemas``, so
a client never has to hand-derive or guess any of them.

Two details a client must not ignore:

- **Dialect**: every published schema is JSON Schema **Draft 2020-12**
  (``$schema`` says so explicitly), restricted to a small, agreed subset — plain
  types, lists, enums, and in-document ``$ref``s. No recursive types and no
  custom string formats; every model referenced here satisfies that by
  construction.
- **Mode**: the *same* pydantic model can produce a different schema for
  validating an incoming request than for describing an outgoing response (e.g.
  required-ness of a field with a default differs between the two). Each entry
  therefore carries its own ``mode`` — ``"validation"`` for the one request
  message (``ResolveRequest``), ``"serialization"`` for everything the server
  only ever emits — so a client always knows which pydantic mode produced the
  schema it is looking at.
- **``BaseVerdict`` is the guaranteed minimum, not a closed shape**: it is
  abstract, and its own published schema shows only ``{kind}`` —
  ``additionalProperties: false`` there really is the intersection of every
  possible item, not a lie. A real item is always one of its concrete
  subclasses: ``AllowedVerdict`` (``{kind}``, no ``reason`` at all),
  ``FailSecurityVerdict``/``FailErrorVerdict`` (``{kind, reason}``). This entry
  does not enumerate those subclasses as a discriminated union today — a client
  that wants the *reason* field's presence to be schema-checked needs to branch
  on ``kind`` itself rather than validate every item against this one entry.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from aoa.action_machine.intents.access_control import BaseVerdict
from aoa.action_machine.intents.meta.meta_intent_resolver import MetaIntentResolver
from aoa.fastapi.permissions import build_route_index
from aoa.fastapi.permissions_schema import (
    SUPPORTED_VERSION,
    ErrorEnvelope,
    ResolveRequest,
    ResolveResponse,
)
from aoa.fastapi.route_record import FastApiRouteRecord

# Version of the manifest's own shape (this module's models) — independent of
# SUPPORTED_VERSION and of manifest_version's content hash. Bumped to 2 when
# `schemas` was added (chapter 3.5, task 7). Draft until chapter 3.5's contract
# settles, same as SUPPORTED_VERSION.
_MANIFEST_SCHEMA_VERSION = 2

_JSON_SCHEMA_DIALECT = "https://json-schema.org/draft/2020-12/schema"


class RouteRef(BaseModel):
    """The ``method``/``path`` pair, echoed separately from the joined ``operation``."""

    model_config = ConfigDict(extra="forbid")

    method: str = Field(description='HTTP method, e.g. "POST".')
    path: str = Field(description='URL path template, e.g. "/actions/cancel-order".')


class ManifestEndpoint(BaseModel):
    """One catalog entry — an endpoint, not an action."""

    model_config = ConfigDict(extra="forbid")

    operation: str = Field(
        description='Endpoint identifier "{method} {path}", e.g. "POST /actions/cancel-order".',
    )
    name: str = Field(description="Action class name behind the endpoint (informational only).")
    domain: str = Field(description="Domain name from the action's @meta.")
    description: str = Field(description="Human-readable description from the action's @meta.")
    route: RouteRef = Field(description="method/path split out from operation.")
    params_schema: dict[str, Any] = Field(description="JSON Schema of the effective request model.")
    result_schema: dict[str, Any] = Field(description="JSON Schema of the effective response model.")


class SchemaEntry(BaseModel):
    """One published reference schema plus the pydantic mode that produced it — see the module docstring."""

    model_config = ConfigDict(extra="forbid")

    mode: Literal["validation", "serialization"] = Field(
        description="Which pydantic schema mode produced json_schema — the two can legitimately differ.",
    )
    json_schema: dict[str, Any] = Field(description="JSON Schema Draft 2020-12 document (carries its own $schema).")


class Manifest(BaseModel):
    """Body of ``GET /client-manifest.json``: a versioned list of endpoints (not actions).

    Three separate numbers — see the module docstring for what each answers:
    ``version`` (resolver wire language), ``manifest_schema_version`` (this
    manifest's own shape), ``manifest_version`` (content hash of this response).
    """

    model_config = ConfigDict(extra="forbid")

    manifest_version: str = Field(
        description='Content hash "sha256:<hex>" of the canonical body *without* this field '
        "(computed first, then inserted — see build_manifest). Not an app version or a build "
        "date — it changes only when the endpoint set actually changes, so clients may cache freely.",
    )
    version: int = Field(description="Resolver wire-language version the server speaks.")
    manifest_schema_version: int = Field(description="Version of this manifest's own shape (these models).")
    endpoints: list[ManifestEndpoint] = Field(
        description="One entry per registered route, in registration order.",
    )
    schemas: dict[str, SchemaEntry] = Field(
        description="Reference schemas for the fixed wire messages — see the module docstring's "
        '"REFERENCE SCHEMAS" section. Keyed by message name, e.g. "ResolveRequest".',
    )


def _json_schema(model: type) -> dict[str, Any]:
    """
    JSON Schema of a request/response model.

    ``BaseRouteRecord`` types the effective models as bare ``type``; narrow to a
    pydantic ``BaseModel`` before calling ``model_json_schema()``. Action params/
    result are always ``BaseSchema`` (hence ``BaseModel``) subclasses, so this
    guard documents the invariant rather than handling a real alternative.
    """
    if not issubclass(model, BaseModel):
        raise TypeError(f"expected a pydantic model for the manifest schema, got {model!r}.")
    return model.model_json_schema()


def _schema_entry(model: type[BaseModel], mode: Literal["validation", "serialization"]) -> SchemaEntry:
    """One ``schemas`` entry: ``model``'s JSON Schema in the given pydantic mode, tagged with its dialect."""
    schema = model.model_json_schema(mode=mode)
    schema["$schema"] = _JSON_SCHEMA_DIALECT
    return SchemaEntry(mode=mode, json_schema=schema)


def _build_schemas() -> dict[str, SchemaEntry]:
    """
    Reference schemas for the protocol's own fixed messages — see the module
    docstring's "REFERENCE SCHEMAS" section for the dialect/subset/mode rules.

    ``ResolveRequest`` is the one message the server *validates* (``mode=
    "validation"``); everything else here is a message only the server ever
    *emits*, hence ``mode="serialization"`` — including ``Manifest`` itself,
    "схему самого каталога": a client can validate the very catalog it just
    received against a schema published inside that same catalog.
    """
    return {
        "ResolveRequest": _schema_entry(ResolveRequest, "validation"),
        "ResolveResponse": _schema_entry(ResolveResponse, "serialization"),
        "BaseVerdict": _schema_entry(BaseVerdict, "serialization"),
        "ErrorEnvelope": _schema_entry(ErrorEnvelope, "serialization"),
        "Manifest": _schema_entry(Manifest, "serialization"),
    }


def _build_endpoint(record: FastApiRouteRecord) -> ManifestEndpoint:
    """Project one ``FastApiRouteRecord`` into one ``ManifestEndpoint``."""
    action_class = record.action_class
    return ManifestEndpoint(
        operation=f"{record.method} {record.path}",
        name=action_class.__name__,
        domain=MetaIntentResolver.resolve_domain_type(action_class).__name__,
        description=MetaIntentResolver.resolve_description(action_class),
        route=RouteRef(method=record.method, path=record.path),
        params_schema=_json_schema(record.effective_request_model),
        result_schema=_json_schema(record.effective_response_model),
    )


def build_manifest(routes: list[FastApiRouteRecord]) -> Manifest:
    """
    Project registered routes into a client manifest.

    A pure projection of the adapter's ``self._routes``: no graph traversal, no
    ``Context``, no role filtering. One entry per *distinct* ``(method, path)``,
    in first-registration order; several registrations of the same
    ``action_class`` on different routes still produce several independent
    entries (no dedup by class — see the module docstring), but an exact
    ``(method, path)`` duplicate collapses to its first registration, before
    ``manifest_version`` is computed, so the hash reflects the manifest's real,
    deduplicated content. First-wins dedup itself is
    :func:`~aoa.fastapi.permissions.build_route_index` — dict order preserves
    first-registration order, so ``.values()`` is exactly the list this needs.
    """
    endpoints = [_build_endpoint(record) for record in build_route_index(routes).values()]
    schemas = _build_schemas()
    # Canonical content *without* manifest_version — hashing the field that would
    # then have to contain its own hash is a circle with no fixed point. Every
    # other field goes in, including manifest_schema_version, version, and
    # schemas: a bump to any of them is a real content change and must move the
    # ETag too.
    body = {
        "version": SUPPORTED_VERSION,
        "manifest_schema_version": _MANIFEST_SCHEMA_VERSION,
        "endpoints": [endpoint.model_dump(mode="json") for endpoint in endpoints],
        "schemas": {name: entry.model_dump(mode="json") for name, entry in schemas.items()},
    }
    digest = hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8"),
    ).hexdigest()
    return Manifest(
        manifest_version=f"sha256:{digest}",
        version=SUPPORTED_VERSION,
        manifest_schema_version=_MANIFEST_SCHEMA_VERSION,
        endpoints=endpoints,
        schemas=schemas,
    )
