"""
Tests for ``build_manifest`` — the client-manifest projection (issue #130, chapter 3).

Covers the invariants of chapter 3's implementation task 1: a pure projection of
registered routes, keyed by endpoint (``"{method} {path}"``) rather than by action
class, with a deterministic content-hash version.
"""

from __future__ import annotations

from aoa.fastapi.manifest import Manifest, build_manifest
from aoa.fastapi.route_record import FastApiRouteRecord

from .support import PingAction, SimpleAction


class TestBuildManifestBasics:
    """One route → one endpoint, with fields projected from the route record and @meta."""

    def test_single_route_projects_to_one_endpoint(self) -> None:
        record = FastApiRouteRecord(action_class=PingAction, method="get", path="/ping")

        manifest = build_manifest([record])

        assert isinstance(manifest, Manifest)
        assert manifest.protocol == 1
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
        assert manifest.protocol == 1
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
