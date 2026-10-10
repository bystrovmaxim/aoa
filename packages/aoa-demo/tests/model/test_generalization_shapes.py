# packages/aoa-demo/tests/model/test_generalization_shapes.py
"""
Generalization-shapes demonstrator — the fixtures draw inheritance edges.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

After the sample modules register the generalization fixtures, the built
interchange graph must carry the inheritance edges the diagrams draw:
``parent_action`` edges from both child actions into the parent, and a
``parent_entity`` edge from the child entity into the parent (issue #202).
"""

from __future__ import annotations

from aoa.demo.model.interchange_demo_coordinator import (
    build_registered_interchange_coordinator,
    import_sample_registration_modules,
)


def _coordinator() -> object:
    import_sample_registration_modules()
    return build_registered_interchange_coordinator()


def _links(coordinator: object, edge_name: str) -> set[tuple[str, str]]:
    return {
        (source_id.rsplit(".", 1)[-1], target_id.rsplit(".", 1)[-1])
        for source_id, target_id, _edge in coordinator.get_edges_by_type(edge_name)
    }


def test_generalization_parent_action_edges() -> None:
    """Both children carry a parent_action edge into the parent."""
    links = _links(_coordinator(), "parent_action")
    assert ("GeneralizationFirstChildAction", "GeneralizationParentAction") in links
    assert ("GeneralizationSecondChildAction", "GeneralizationParentAction") in links


def test_generalization_parent_entity_edges() -> None:
    """Both extensions carry a parent_entity edge into the head."""
    links = _links(_coordinator(), "parent_entity")
    assert ("GeneralizationVariantAEntity", "GeneralizationHeadEntity") in links
    assert ("GeneralizationVariantBEntity", "GeneralizationHeadEntity") in links


def test_generalization_specialization_axis() -> None:
    """The head declares its axis — entity_specialization edges into the variants."""
    links = _links(_coordinator(), "entity_specialization")
    assert ("GeneralizationHeadEntity", "GeneralizationVariantAEntity") in links
    assert ("GeneralizationHeadEntity", "GeneralizationVariantBEntity") in links
