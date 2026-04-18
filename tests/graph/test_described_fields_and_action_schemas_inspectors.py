# tests/graph/test_described_fields_and_action_schemas_inspectors.py
"""DescribedFieldsIntentInspector vs ActionTypedSchemasInspector split."""

from __future__ import annotations

import pytest
from pydantic import BaseModel, Field

from action_machine.domain import BaseEntity, entity
from action_machine.domain.base_domain import BaseDomain
from action_machine.intents.auth import check_roles
from action_machine.intents.auth.none_role import NoneRole
from action_machine.intents.described_fields import (
    DescribedFieldsIntent,
    validate_described_schema,
    validate_described_schemas_for_action,
)
from action_machine.intents.described_fields.described_fields_intent_inspector import DescribedFieldsIntentInspector
from action_machine.intents.meta.meta_decorator import meta
from action_machine.interchange_vertex_labels import ENTITY_VERTEX_TYPE
from action_machine.model.base_action import ActionTypedSchemasInspector, BaseAction
from action_machine.model.base_params import BaseParams
from action_machine.model.base_result import BaseResult


class _ProbeParams(BaseParams):
    probe_id: str = Field(description="Probe identifier")


class _LooseDescribedDTO(BaseModel, DescribedFieldsIntent):
    """Not BaseParams or BaseResult — stays on the generic ``described_fields`` host."""

    x: str = Field(description="x")


class _ProbeDomain(BaseDomain):
    name = "probe"
    description = "Probe domain"


@meta(description="Schema link probe", domain=_ProbeDomain)
@check_roles(NoneRole)
class _SchemaLinkProbeAction(BaseAction[BaseParams, BaseResult]):
    """Minimal action with concrete ``BaseAction[BaseParams, BaseResult]``."""

    pass


def test_described_fields_inspector_targets_described_fields_intent() -> None:
    assert DescribedFieldsIntentInspector._target_intent is DescribedFieldsIntent


def test_described_fields_inspector_inspects_schema_class_not_action() -> None:
    payload = DescribedFieldsIntentInspector.inspect(_ProbeParams)
    assert payload is not None
    assert payload.node_type == "params_schema"
    assert payload.node_class is _ProbeParams
    assert "schema_fields" in dict(payload.node_meta)


def test_loose_described_schema_uses_described_fields_vertex() -> None:
    payload = DescribedFieldsIntentInspector.inspect(_LooseDescribedDTO)
    assert payload is not None
    assert payload.node_type == "described_fields"
    assert payload.node_class is _LooseDescribedDTO


@entity(description="Probe entity for inspector skip", domain=_ProbeDomain)
class _ProbeEntity(BaseEntity):
    id: str = Field(description="Identifier")


_ProbeEntity.model_rebuild()


def test_described_fields_inspector_skips_entity_intent_classes() -> None:
    assert DescribedFieldsIntentInspector.inspect(_ProbeEntity) is None
    assert DescribedFieldsIntentInspector.facet_snapshot_for_class(_ProbeEntity) is None


def test_facet_host_for_schema_type_routes_entities_to_entity_vertex() -> None:
    nt, name = DescribedFieldsIntentInspector.facet_host_for_schema_type(_ProbeEntity)
    assert nt == ENTITY_VERTEX_TYPE
    assert name == DescribedFieldsIntentInspector._make_node_name(_ProbeEntity)


def test_validate_described_schema_no_op_for_none_and_empty_shell() -> None:
    validate_described_schema(None)
    validate_described_schema(BaseParams)  # no declared fields


def test_validate_described_schema_raises_on_missing_description() -> None:
    class _BadParams(BaseParams):
        x: str

    with pytest.raises(TypeError, match="do not have descriptions"):
        validate_described_schema(_BadParams)


def test_validate_described_schemas_for_action_delegates_to_extract() -> None:
    validate_described_schemas_for_action(_SchemaLinkProbeAction)


def test_action_typed_schemas_inspector_links_action_to_schema_nodes() -> None:
    payload = ActionTypedSchemasInspector.inspect(_SchemaLinkProbeAction)
    assert payload is not None
    assert payload.node_type == "Action"
    assert payload.node_class is _SchemaLinkProbeAction
    assert len(payload.edges) == 2
    types_ = {e.edge_type for e in payload.edges}
    assert types_ == {"uses_params", "uses_result"}
    assert {(e.edge_type, e.target_node_type) for e in payload.edges} == {
        ("uses_params", "params_schema"),
        ("uses_result", "result_schema"),
    }
    assert all(e.is_structural is False for e in payload.edges)
