"""
Tests for ``build_manifest`` — the client-manifest projection (issue #130, chapter 3).

Covers the invariants of chapter 3's implementation task 1: a pure projection of
registered routes, keyed by endpoint (``"{method} {path}"``) rather than by action
class, with a deterministic content-hash version.
"""

from __future__ import annotations

import pytest

from aoa.fastapi import manifest as manifest_module
from aoa.fastapi.manifest import Manifest, build_manifest
from aoa.fastapi.route_record import FastApiRouteRecord

from .support import PingAction, SimpleAction


class TestBuildManifestBasics:
    """One route → one endpoint, with fields projected from the route record and @meta."""

    def test_single_route_projects_to_one_endpoint(self) -> None:
        record = FastApiRouteRecord(action_class=PingAction, method="get", path="/ping")

        manifest = build_manifest([record])

        assert isinstance(manifest, Manifest)
        assert manifest.version == 1
        assert manifest.manifest_schema_version == 2
        assert len(manifest.endpoints) == 1

        endpoint = manifest.endpoints[0]
        assert endpoint.operation == "GET /ping"
        assert endpoint.name == "PingAction"
        assert endpoint.domain == "SystemDomain"
        assert endpoint.description == "Service health check"
        assert endpoint.route.method == "GET"
        assert endpoint.route.path == "/ping"

    def test_operation_is_method_space_path(self) -> None:
        record = FastApiRouteRecord(action_class=SimpleAction, method="post", path="/actions/simple")

        endpoint = build_manifest([record]).endpoints[0]

        assert endpoint.operation == "POST /actions/simple"

    def test_schemas_come_from_effective_models(self) -> None:
        record = FastApiRouteRecord(action_class=PingAction, path="/ping")

        endpoint = build_manifest([record]).endpoints[0]

        assert endpoint.params_schema == record.effective_request_model.model_json_schema()
        assert endpoint.result_schema == record.effective_response_model.model_json_schema()

    def test_top_level_field_is_endpoints_not_actions(self) -> None:
        record = FastApiRouteRecord(action_class=PingAction, path="/ping")

        dumped = build_manifest([record]).model_dump()

        assert "endpoints" in dumped
        assert "actions" not in dumped

    def test_empty_routes_yield_empty_manifest(self) -> None:
        manifest = build_manifest([])

        assert manifest.endpoints == []
        assert manifest.version == 1
        assert manifest.manifest_schema_version == 2
        assert manifest.manifest_version.startswith("sha256:")


class TestEndpointsNotActions:
    """The manifest lists endpoints; one class on several routes → several entries."""

    def test_same_action_on_two_routes_yields_two_independent_entries(self) -> None:
        routes = [
            FastApiRouteRecord(action_class=SimpleAction, method="post", path="/a"),
            FastApiRouteRecord(action_class=SimpleAction, method="get", path="/a"),
        ]

        manifest = build_manifest(routes)

        operations = [endpoint.operation for endpoint in manifest.endpoints]
        assert operations == ["POST /a", "GET /a"]
        # No dedup and no error: both entries point at the same class.
        assert {endpoint.name for endpoint in manifest.endpoints} == {"SimpleAction"}

    def test_registration_order_is_preserved(self) -> None:
        routes = [
            FastApiRouteRecord(action_class=PingAction, path="/ping"),
            FastApiRouteRecord(action_class=SimpleAction, path="/simple"),
        ]

        operations = [endpoint.operation for endpoint in build_manifest(routes).endpoints]

        assert operations == ["POST /ping", "POST /simple"]


class TestExactDuplicateIsFirstWins:
    """An exact (method, path) duplicate collapses to its first registration."""

    def test_duplicate_operation_yields_one_entry(self) -> None:
        routes = [
            FastApiRouteRecord(action_class=PingAction, method="post", path="/a"),
            FastApiRouteRecord(action_class=SimpleAction, method="post", path="/a"),
        ]

        manifest = build_manifest(routes)

        assert len(manifest.endpoints) == 1
        assert manifest.endpoints[0].name == "PingAction"

    def test_a_third_distinct_route_still_appears(self) -> None:
        routes = [
            FastApiRouteRecord(action_class=PingAction, method="post", path="/a"),
            FastApiRouteRecord(action_class=SimpleAction, method="post", path="/a"),
            FastApiRouteRecord(action_class=SimpleAction, method="get", path="/b"),
        ]

        operations = [endpoint.operation for endpoint in build_manifest(routes).endpoints]

        assert operations == ["POST /a", "GET /b"]

    def test_same_action_on_different_methods_is_not_a_duplicate(self) -> None:
        """(method, path) is the identity — same path, different method, is two real endpoints."""
        routes = [
            FastApiRouteRecord(action_class=SimpleAction, method="post", path="/a"),
            FastApiRouteRecord(action_class=SimpleAction, method="get", path="/a"),
        ]

        operations = [endpoint.operation for endpoint in build_manifest(routes).endpoints]

        assert operations == ["POST /a", "GET /a"]

    def test_version_reflects_the_deduplicated_content_not_the_duplicate(self) -> None:
        """A duplicate registration must not perturb the hash — it contributes nothing new."""
        without_duplicate = build_manifest([FastApiRouteRecord(action_class=PingAction, method="post", path="/a")])
        with_duplicate = build_manifest(
            [
                FastApiRouteRecord(action_class=PingAction, method="post", path="/a"),
                FastApiRouteRecord(action_class=SimpleAction, method="post", path="/a"),
            ]
        )

        assert without_duplicate.manifest_version == with_duplicate.manifest_version


class TestManifestVersion:
    """``manifest_version`` is a deterministic content hash of the projected body."""

    def test_identical_routes_yield_identical_version(self) -> None:
        first = build_manifest([FastApiRouteRecord(action_class=PingAction, path="/ping")])
        second = build_manifest([FastApiRouteRecord(action_class=PingAction, path="/ping")])

        assert first.manifest_version == second.manifest_version

    def test_different_routes_yield_different_version(self) -> None:
        one = build_manifest([FastApiRouteRecord(action_class=PingAction, path="/ping")])
        other = build_manifest([FastApiRouteRecord(action_class=PingAction, path="/health")])

        assert one.manifest_version != other.manifest_version

    def test_version_is_sha256_prefixed_hex(self) -> None:
        version = build_manifest([FastApiRouteRecord(action_class=PingAction, path="/ping")]).manifest_version

        assert version.startswith("sha256:")
        assert len(version) == len("sha256:") + 64


class TestThreeNumbers:
    """``version`` / ``manifest_schema_version`` / ``manifest_version`` answer different questions."""

    def test_bumping_resolver_version_changes_the_hash(self, monkeypatch: pytest.MonkeyPatch) -> None:
        routes = [FastApiRouteRecord(action_class=PingAction, path="/ping")]
        before = build_manifest(routes)

        monkeypatch.setattr(manifest_module, "SUPPORTED_VERSION", 2)
        after = build_manifest(routes)

        assert after.version == 2
        assert after.manifest_version != before.manifest_version

    def test_bumping_manifest_schema_version_changes_the_hash(self, monkeypatch: pytest.MonkeyPatch) -> None:
        routes = [FastApiRouteRecord(action_class=PingAction, path="/ping")]
        before = build_manifest(routes)

        monkeypatch.setattr(manifest_module, "_MANIFEST_SCHEMA_VERSION", 3)
        after = build_manifest(routes)

        assert after.manifest_schema_version == 3
        assert after.manifest_version != before.manifest_version


class TestReferenceSchemas:
    """``schemas`` publishes the fixed wire messages' JSON Schemas (chapter 3.5, task 7)."""

    _EXPECTED_KEYS = {"ResolveRequest", "ResolveResponse", "ResolveItemResult", "ErrorEnvelope", "Manifest"}

    def test_schemas_key_has_exactly_the_five_documented_messages(self) -> None:
        manifest = build_manifest([FastApiRouteRecord(action_class=PingAction, path="/ping")])

        assert set(manifest.schemas.keys()) == self._EXPECTED_KEYS

    def test_every_schema_carries_the_2020_12_dialect(self) -> None:
        manifest = build_manifest([FastApiRouteRecord(action_class=PingAction, path="/ping")])

        for entry in manifest.schemas.values():
            assert entry.json_schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"

    def test_request_message_is_validation_mode_everything_else_is_serialization(self) -> None:
        manifest = build_manifest([FastApiRouteRecord(action_class=PingAction, path="/ping")])

        assert manifest.schemas["ResolveRequest"].mode == "validation"
        for key in self._EXPECTED_KEYS - {"ResolveRequest"}:
            assert manifest.schemas[key].mode == "serialization"

    def test_resolve_item_result_schema_lists_kind_and_reason(self) -> None:
        manifest = build_manifest([FastApiRouteRecord(action_class=PingAction, path="/ping")])

        properties = manifest.schemas["ResolveItemResult"].json_schema["properties"]
        assert set(properties.keys()) == {"kind", "reason"}

    def test_empty_routes_still_publish_schemas(self) -> None:
        """``schemas`` describes the protocol itself, independent of which routes are registered."""
        manifest = build_manifest([])

        assert set(manifest.schemas.keys()) == self._EXPECTED_KEYS

    def test_adding_a_schema_key_would_change_the_hash(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """``schemas`` is part of the hashed body, like every other top-level field."""
        routes = [FastApiRouteRecord(action_class=PingAction, path="/ping")]
        before = build_manifest(routes)

        original_build_schemas = manifest_module._build_schemas

        def _build_schemas_with_extra_entry() -> dict[str, object]:
            schemas = original_build_schemas()
            schemas["Extra"] = schemas["Manifest"]
            return schemas

        monkeypatch.setattr(manifest_module, "_build_schemas", _build_schemas_with_extra_entry)
        after = build_manifest(routes)

        assert after.manifest_version != before.manifest_version
