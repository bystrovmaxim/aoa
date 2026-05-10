# tests/maxitor/test_sample_graph_json_fields.py
"""
Maxitor sample interchange graph — ``JsonSchemaValue`` fields on sample ``Result`` models.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

After sample modules register actions, :func:`aoa.maxitor.samples.interchange_demo_coordinator.build_registered_interchange_coordinator`
must build without error and emit ``Field`` nodes with ``json_schema_value`` metadata
for ``sample_audit`` columns on selected sample results.
"""

from __future__ import annotations

from aoa.maxitor.samples.interchange_demo_coordinator import (
    build_registered_interchange_coordinator,
    import_sample_registration_modules,
)


def _sample_coordinator() -> object:
    import_sample_registration_modules()
    return build_registered_interchange_coordinator()


def test_sample_graph_builds_without_error() -> None:
    coordinator = _sample_coordinator()
    nodes = coordinator.get_all_nodes()
    assert any(getattr(n, "node_type", None) == "Action" for n in nodes)


def test_sample_graph_has_at_least_five_json_schema_field_nodes() -> None:
    coordinator = _sample_coordinator()
    audit_fields = [
        n
        for n in coordinator.get_all_nodes()
        if getattr(n, "node_type", None) == "Field"
        and getattr(n.node_obj, "field_name", None) == "sample_audit"
        and n.properties.get("json_schema_value") is True
    ]
    assert len(audit_fields) >= 5


def test_json_field_metadata_on_sample_audit_fields() -> None:
    coordinator = _sample_coordinator()
    audit_fields = [
        n
        for n in coordinator.get_all_nodes()
        if getattr(n, "node_type", None) == "Field"
        and getattr(n.node_obj, "field_name", None) == "sample_audit"
        and n.properties.get("json_schema_value") is True
    ]
    assert audit_fields
    for node in audit_fields:
        assert "json_schema_name" in node.properties
        assert "json_schema" in node.properties
        assert isinstance(node.properties["json_schema"], dict)
        assert node.properties["json_schema"].get("type") == "object"
