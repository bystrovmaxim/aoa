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

Because the source is ``FastApiRouteRecord`` (method, path, class, request/
response models), the body of any access condition (``guard=``/``when=``/
``access_decide``) structurally cannot leak into the manifest: those function
bodies are not part of a route record, so there is nothing to serialize.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from aoa.action_machine.intents.meta.meta_intent_resolver import MetaIntentResolver
from aoa.fastapi.route_record import FastApiRouteRecord

# Wire-protocol version the server speaks; matches ``POST /permissions/resolve``.
_PROTOCOL = 1


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


class Manifest(BaseModel):
    """Body of ``GET /client-manifest.json``: a versioned list of endpoints (not actions)."""

    model_config = ConfigDict(extra="forbid")

    manifest_version: str = Field(
        description='Content hash "sha256:<hex>". Not an app version or a build date — '
        "it changes only between process deploys, so clients may cache freely.",
    )
    protocol: int = Field(description="Wire-protocol version the server speaks.")
    endpoints: list[ManifestEndpoint] = Field(
        description="One entry per registered route, in registration order.",
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
    ``Context``, no role filtering. One entry per route, in registration order;
    several registrations of the same ``action_class`` produce several
    independent entries (no dedup). ``manifest_version`` is a content hash of the
    projected body, so identical routes always produce an identical version.
    """
    endpoints = [_build_endpoint(record) for record in routes]
    body = {
        "protocol": _PROTOCOL,
        "endpoints": [endpoint.model_dump(mode="json") for endpoint in endpoints],
    }
    digest = hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8"),
    ).hexdigest()
    return Manifest(
        manifest_version=f"sha256:{digest}",
        protocol=_PROTOCOL,
        endpoints=endpoints,
    )
