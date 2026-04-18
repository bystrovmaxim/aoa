# tests/graph/test_entity_intent_inspector.py
"""Unit tests for EntityIntentInspector."""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import (
    AssociationOne,
    BaseEntity,
    NoGraphEdge,
    NoInverse,
    Rel,
    entity,
)
from action_machine.domain.base_domain import BaseDomain
from action_machine.domain.entity_intent import EntityIntent
from action_machine.domain.entity_intent_inspector import (
    EntityIntentInspector,
    collect_entity_info,
)


class _TestDomain(BaseDomain):
    name = "test"
    description = "Test domain"


class _NoEntityMarker(EntityIntent):
    pass


@entity(description="Simple entity", domain=_TestDomain)
class _SimpleEntity(BaseEntity):
    id: str = Field(description="Identifier")
    title: str = Field(description="Title")


@entity(description="Peer for omit-graph test", domain=_TestDomain)
class _PeerOmitEntity(BaseEntity):
    id: str = Field(description="Peer id")


@entity(description="Host with NoGraphEdge relation", domain=_TestDomain)
class _HostOmitGraphEntity(BaseEntity):
    id: str = Field(description="Host id")
    peer: Annotated[
        AssociationOne[_PeerOmitEntity],
        NoInverse(),
        NoGraphEdge(),
    ] = Rel(description="Declared but not exported as an edge")  # type: ignore[assignment]


_PeerOmitEntity.model_rebuild()
_HostOmitGraphEntity.model_rebuild()


@entity(description="Declared on entity", domain=_TestDomain)
class _EntityWithMetaOverlayEntity(BaseEntity):
    id: str = Field(description="Identifier")


_EntityWithMetaOverlayEntity._meta_info = {
    "description": "Overridden via _meta_info (same contract as @meta)",
    "domain": _TestDomain,
}
_EntityWithMetaOverlayEntity.model_rebuild()


def test_entity_inspector_returns_none_without_entity_info() -> None:
    assert EntityIntentInspector.inspect(_NoEntityMarker) is None


def test_collect_entity_info_merges_meta_scratch_description() -> None:
    info = collect_entity_info(_EntityWithMetaOverlayEntity)
    assert info is not None
    assert info.description == "Overridden via _meta_info (same contract as @meta)"
    assert info.domain is _TestDomain


def test_entity_inspector_exposes_meta_overlay_in_facet_payload() -> None:
    payload = EntityIntentInspector.inspect(_EntityWithMetaOverlayEntity)
    assert payload is not None
    assert (
        dict(payload.node_meta)["description"]
        == "Overridden via _meta_info (same contract as @meta)"
    )
    assert any(e.edge_type == "belongs_to" for e in payload.edges)


def test_entity_inspector_builds_payload_with_entity_metadata() -> None:
    payload = EntityIntentInspector.inspect(_SimpleEntity)
    assert payload is not None
    assert payload.node_type == "entity"

    data = dict(payload.node_meta)
    assert data["description"] == "Simple entity"
    assert data["domain"] is _TestDomain

    fields = data["fields"]
    names = {entry[0] for entry in fields}
    assert "id" in names
    assert "title" in names

    assert data["relations"] == ()
    assert data["lifecycles"] == ()

    domain_edges = [e for e in payload.edges if e.edge_type == "belongs_to"]
    assert len(domain_edges) == 1
    assert domain_edges[0].target_node_type == "domain"
    assert domain_edges[0].target_class_ref is _TestDomain


def test_entity_inspector_emits_relation_edges_for_linked_entities() -> None:
    from maxitor.samples.store.entities.sales_core import SalesOrderEntity

    payload = EntityIntentInspector.inspect(SalesOrderEntity)
    assert payload is not None
    assert {e.edge_type for e in payload.edges} >= {
        "belongs_to",
        "entity_association_one",
        "entity_composition_many",
    }
    for e in payload.edges:
        if e.edge_type == "belongs_to":
            continue
        meta = dict(e.edge_meta)
        assert "field_name" in meta
        assert "relation_type" in meta
        assert "cardinality" in meta


def test_entity_inspector_omits_edge_when_no_graph_edge_marker() -> None:
    payload = EntityIntentInspector.inspect(_HostOmitGraphEntity)
    assert payload is not None
    assert [e.edge_type for e in payload.edges] == ["belongs_to"]
    rels = dict(payload.node_meta)["relations"]
    assert len(rels) == 1
    assert rels[0][-1] is True  # omit_graph_edge
