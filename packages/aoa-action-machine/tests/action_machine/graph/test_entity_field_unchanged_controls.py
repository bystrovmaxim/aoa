# tests/action_machine/graph/test_entity_field_unchanged_controls.py
"""
Controls that stay untouched by the complete-declaration rule.

Scalars, schema types, lifecycle fields and the abstract kind bases are not the rule's
business; a bare state entity keeps its existing refusal. These tests pin that boundary so
the completeness gate does not silently widen into fields it must never judge.
"""

from __future__ import annotations

import textwrap

from aoa.action_machine.domain import (
    BaseAssocEntity,
    BaseCoreEntity,
    BaseDetailEntity,
    BaseEnumEntity,
    BaseSpecEntity,
    BaseStateEntity,
)
from aoa.action_machine.intents.entity.entity_intent import entity_info_is_set

from ...support.isolated_entity_models import run_isolated_model

_IMPORTS = textwrap.dedent(
    """
    from typing import Annotated

    from pydantic import Field

    from aoa.action_machine.domain import (
        AssociationOne,
        BaseCoreEntity,
        BaseDomain,
        BaseStateEntity,
        Lifecycle,
        NoInverse,
        value,
    )
    from aoa.action_machine.domain.exceptions import EntityFieldDeclarationError
    from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
    from aoa.action_machine.graph.validators.entity_field_validator import validate_entity_fields
    from aoa.action_machine.intents.entity import entity
    from aoa.action_machine.model.base_schema import BaseSchema


    def probe(cls):
        try:
            validate_entity_fields([cls])
            print("ACCEPT " + cls.__name__)
        except EntityFieldDeclarationError as exc:
            print("REFUSE " + cls.__name__ + " " + exc.field_name + " " + exc.details)
    """
)


def _run(body: str) -> str:
    result = run_isolated_model(_IMPORTS + "\n" + textwrap.dedent(body))
    assert result.returncode == 0, result.stderr
    return result.stdout


def test_scalar_schema_and_lifecycle_fields_pass() -> None:
    """Scalars, a schema type and a lifecycle field are not the rule's business."""
    out = _run(
        """
        class ControlsDomain(BaseDomain):
            name = "controls"
            description = "Controls"

        class DraftStateEntity(BaseStateEntity):
            DRAFT = value(code="draft", display_name="Draft")

        class DraftLifecycle(Lifecycle[DraftStateEntity]):
            pass

        @exclude_graph_model
        @entity(description="Schema host", domain=ControlsDomain)
        class HostParams(BaseSchema):
            order_id: str = Field(description="Order identifier")

        @exclude_graph_model
        @entity(description="Untouched host", domain=ControlsDomain)
        class OrdinaryCoreEntity(BaseCoreEntity):
            id: str = Field(description="Identifier")
            age: int | None = Field(default=None, description="Age")
            lifecycle: DraftLifecycle = Field(description="Lifecycle")
            params: HostParams = Field(description="Parameters")

        probe(OrdinaryCoreEntity)
        """
    )

    assert "ACCEPT OrdinaryCoreEntity" in out


def test_a_bare_state_field_keeps_its_refusal() -> None:
    """A state entity written as a field is still refused with the lifecycle correction."""
    out = _run(
        """
        class ControlsDomain(BaseDomain):
            name = "controls"
            description = "Controls"

        class DraftStateEntity(BaseStateEntity):
            DRAFT = value(code="draft", display_name="Draft")

        @exclude_graph_model
        @entity(description="State host", domain=ControlsDomain)
        class StateFieldCoreEntity(BaseCoreEntity):
            stage: DraftStateEntity = Field(description="Stage")

        probe(StateFieldCoreEntity)
        """
    )

    assert "REFUSE StateFieldCoreEntity stage" in out
    assert "Lifecycle[...]" in out


def test_abstract_kind_bases_are_not_user_declarations() -> None:
    """The six kind bases are framework axes, not declared hosts the rule judges."""
    for base in (
        BaseCoreEntity,
        BaseAssocEntity,
        BaseDetailEntity,
        BaseSpecEntity,
        BaseEnumEntity,
        BaseStateEntity,
    ):
        assert not entity_info_is_set(base)
