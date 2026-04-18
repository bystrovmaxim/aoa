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
from action_machine.domain.lifecycle import Lifecycle
from action_machine.graph.base_intent_inspector import BaseIntentInspector
from action_machine.interchange_vertex_labels import ENTITY_VERTEX_TYPE


def _entity_payload(inspect_result: object):
    """First ``FacetPayload`` from ``inspect`` (tuple or single)."""
    if inspect_result is None:
        return None
    if isinstance(inspect_result, tuple):
        return inspect_result[0]
    return inspect_result


class _TestDomain(BaseDomain):
    name = "test"
    description = "Test domain"


class _SimpleEntityLifecycle(Lifecycle):
    """Три состояния по тому же приёму, что ``SalesOrderLifecycle``: initial → intermediate → final."""

    _template = (
        Lifecycle()
        .state("draft", "Draft").to("active").initial()
        .state("active", "Active").to("archived").intermediate()
        .state("archived", "Archived").final()
    )


class _PeerOmitEntityLifecycle(Lifecycle):
    _template = (
        Lifecycle()
        .state("idle", "Idle").to("linked").initial()
        .state("linked", "Linked").to("closed").intermediate()
        .state("closed", "Closed").final()
    )


class _MetaOverlayEntityLifecycle(Lifecycle):
    _template = (
        Lifecycle()
        .state("pending", "Pending").to("ready").initial()
        .state("ready", "Ready").to("done").intermediate()
        .state("done", "Done").final()
    )


class _NoEntityMarker(EntityIntent):
    pass


@entity(description="Simple entity", domain=_TestDomain)
class _SimpleEntity(BaseEntity):
    id: str = Field(description="Identifier")
    title: str = Field(description="Title")
    doc_status: _SimpleEntityLifecycle = Field(description="Document status")


@entity(description="Peer for omit-graph test", domain=_TestDomain)
class _PeerOmitEntity(BaseEntity):
    id: str = Field(description="Peer id")
    peer_link: _PeerOmitEntityLifecycle = Field(description="Peer link state")


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
    phase: _MetaOverlayEntityLifecycle = Field(description="Phase")


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
    payload = _entity_payload(EntityIntentInspector.inspect(_EntityWithMetaOverlayEntity))
    assert payload is not None
    assert (
        dict(payload.node_meta)["description"]
        == "Overridden via _meta_info (same contract as @meta)"
    )
    assert any(e.edge_type == "belongs_to" for e in payload.edges)


def test_entity_inspector_builds_payload_with_entity_metadata() -> None:
    payload = _entity_payload(EntityIntentInspector.inspect(_SimpleEntity))
    assert payload is not None
    assert payload.node_type == ENTITY_VERTEX_TYPE

    data = dict(payload.node_meta)
    assert data["description"] == "Simple entity"
    assert data["domain"] is _TestDomain

    fields = data["fields"]
    names = {entry[0] for entry in fields}
    assert "id" in names
    assert "title" in names

    assert data["relations"] == ()
    lifecycles = data["lifecycles"]
    assert len(lifecycles) == 1
    assert lifecycles[0][0] == "doc_status"
    assert lifecycles[0][3] == 3  # state_count (draft → active → archived)

    assert any(e.edge_type == "entity_has_lifecycle" for e in payload.edges)

    domain_edges = [e for e in payload.edges if e.edge_type == "belongs_to"]
    assert len(domain_edges) == 1
    assert domain_edges[0].target_node_type == "Domain"
    assert domain_edges[0].target_class_ref is _TestDomain


def test_entity_inspector_emits_relation_edges_for_linked_entities() -> None:
    from maxitor.samples.store.entities.sales_core import SalesOrderEntity

    payload = _entity_payload(EntityIntentInspector.inspect(SalesOrderEntity))
    assert payload is not None
    assert {e.edge_type for e in payload.edges} >= {
        "belongs_to",
        "entity_association_one",
        "entity_composition_many",
    }
    for e in payload.edges:
        if e.edge_type in ("belongs_to", "entity_has_lifecycle"):
            continue
        meta = dict(e.edge_meta)
        assert "field_name" in meta
        assert "relation_type" in meta
        assert "cardinality" in meta


def test_entity_inspector_omits_edge_when_no_graph_edge_marker() -> None:
    payload = _entity_payload(EntityIntentInspector.inspect(_HostOmitGraphEntity))
    assert payload is not None
    assert [e.edge_type for e in payload.edges] == ["belongs_to"]
    rels = dict(payload.node_meta)["relations"]
    assert len(rels) == 1
    assert rels[0][-1] is True  # omit_graph_edge


class _DualInitialLifecycle(Lifecycle):
    """Two initial states to exercise ``lifecycle_initial`` edges."""

    _template = (
        Lifecycle()
        .state("a", "A").to("m").initial()
        .state("b", "B").to("m").initial()
        .state("m", "M").final()
    )


@entity(description="Entity with lifecycle field", domain=_TestDomain)
class _EntityWithLifecycleEntity(BaseEntity):
    id: str = Field(description="Identifier")
    order_status: _DualInitialLifecycle = Field(description="Order status")


def test_entity_inspector_emits_lifecycle_graph_facets() -> None:
    raw = EntityIntentInspector.inspect(_EntityWithLifecycleEntity)
    assert raw is not None
    assert isinstance(raw, tuple)
    payloads = list(raw)
    assert payloads[0].node_type == ENTITY_VERTEX_TYPE
    types = [p.node_type for p in payloads]
    assert types.count("lifecycle") == 1
    assert sum(1 for t in types if t.startswith("lifecycle_state")) == 3
    assert sum(1 for t in types if t == "lifecycle_state_initial") == 2
    assert sum(1 for t in types if t == "lifecycle_state_final") == 1

    entity = payloads[0]
    assert any(e.edge_type == "entity_has_lifecycle" for e in entity.edges)
    lc = next(p for p in payloads if p.node_type == "lifecycle")
    assert not any(e.edge_type == "belongs_to" for e in lc.edges)
    assert sum(1 for e in lc.edges if e.edge_type == "lifecycle_contains_state") == 3
    assert sum(1 for e in lc.edges if e.edge_type == "lifecycle_initial") == 2

    st_a = next(
        p for p in payloads
        if p.node_type == "lifecycle_state_initial" and dict(p.node_meta)["state_key"] == "a"
    )
    assert st_a.node_name == BaseIntentInspector._make_node_name(
        _EntityWithLifecycleEntity,
        "order_status:_DualInitialLifecycle:a",
    )
    assert "_EntityWithLifecycleEntity" in st_a.node_name
    assert not any(e.edge_type == "belongs_to" for e in st_a.edges)
    assert any(e.edge_type == "lifecycle_transition" for e in st_a.edges)
    assert any(
        dict(e.edge_meta).get("to_state") == "m"
        for e in st_a.edges
        if e.edge_type == "lifecycle_transition"
    )


def test_single_initial_has_no_lifecycle_initial_edges() -> None:
    class _SingleLc(Lifecycle):
        _template = (
            Lifecycle()
            .state("new", "New").to("done").initial()
            .state("done", "Done").final()
        )

    @entity(description="One initial", domain=_TestDomain)
    class _SingleInitialEntity(BaseEntity):
        id: str = Field(description="id")
        st: _SingleLc = Field(description="st")

    raw = EntityIntentInspector.inspect(_SingleInitialEntity)
    assert isinstance(raw, tuple)
    lc = next(p for p in raw if p.node_type == "lifecycle")
    assert not any(e.edge_type == "lifecycle_initial" for e in lc.edges)
