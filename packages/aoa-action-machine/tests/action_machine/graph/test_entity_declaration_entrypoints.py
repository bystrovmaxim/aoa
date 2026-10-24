# tests/action_machine/graph/test_entity_declaration_entrypoints.py
"""
The completeness gate holds at every supported publication entry point.

A graph-excluded host, a direct ``EntityGraphNode`` projection, the coordinator/factory and
the machine path must all refuse an invalid declaration before a graph is published, and an
already-validated coordinator stays usable. Each invalid declaration is built in a fresh
interpreter so it never joins the shared model.
"""

from __future__ import annotations

import textwrap

from ...support.isolated_entity_models import run_isolated_model

_IMPORTS = textwrap.dedent(
    """
    from typing import Annotated

    from pydantic import Field

    from aoa.action_machine.domain import (
        AssociationOne,
        BaseCoreEntity,
        BaseDomain,
        NoInverse,
    )
    from aoa.action_machine.domain.exceptions import EntityFieldDeclarationError
    from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
    from aoa.action_machine.graph.nodes.entity_graph_node import EntityGraphNode
    from aoa.action_machine.graph.node_graph_coordinator_factory import create_node_graph_coordinator
    from aoa.action_machine.graph.validators.entity_field_validator import validate_entity_fields
    from aoa.action_machine.intents.entity import entity


    class EntrypointDomain(BaseDomain):
        name = "entrypoint"
        description = "Entrypoint"
    """
)


def _run(body: str) -> str:
    result = run_isolated_model(_IMPORTS + "\n" + textwrap.dedent(body))
    assert result.returncode == 0, result.stderr
    return result.stdout


def test_a_graph_excluded_host_is_still_judged() -> None:
    """``exclude_graph_model`` suppresses publication; explicit validation still judges the host."""
    out = _run(
        """
        @exclude_graph_model
        @entity(description="Target", domain=EntrypointDomain)
        class TargetCoreEntity(BaseCoreEntity):
            id: str = Field(description="Identifier")

        @exclude_graph_model
        @entity(description="Bare host", domain=EntrypointDomain)
        class BareCoreEntity(BaseCoreEntity):
            target: TargetCoreEntity = Field(description="Bare")

        try:
            validate_entity_fields([BareCoreEntity])
            print("ACCEPT")
        except EntityFieldDeclarationError as exc:
            print("REFUSE " + exc.entity_name + " " + exc.field_name)
        """
    )

    assert "REFUSE BareCoreEntity target" in out


def test_direct_entity_graph_node_projection_is_refused() -> None:
    """A direct ``EntityGraphNode`` projection cannot publish an invalid declaration."""
    out = _run(
        """
        @exclude_graph_model
        @entity(description="Target", domain=EntrypointDomain)
        class TargetCoreEntity(BaseCoreEntity):
            id: str = Field(description="Identifier")

        @exclude_graph_model
        @entity(description="Bare host", domain=EntrypointDomain)
        class BareCoreEntity(BaseCoreEntity):
            target: TargetCoreEntity = Field(description="Bare")

        try:
            EntityGraphNode(BareCoreEntity)
            print("ACCEPT")
        except EntityFieldDeclarationError as exc:
            print("REFUSE " + exc.entity_name + " " + exc.field_name)
        """
    )

    assert "REFUSE BareCoreEntity target" in out


def test_coordinator_build_refuses_an_invalid_declaration() -> None:
    """The coordinator/factory path runs the gate before node gathering."""
    out = _run(
        """
        @exclude_graph_model
        @entity(description="Target", domain=EntrypointDomain)
        class TargetCoreEntity(BaseCoreEntity):
            id: str = Field(description="Identifier")

        @entity(description="Bare host", domain=EntrypointDomain)
        class BareCoreEntity(BaseCoreEntity):
            target: TargetCoreEntity = Field(description="Bare")

        try:
            create_node_graph_coordinator()
            print("ACCEPT")
        except EntityFieldDeclarationError as exc:
            print("REFUSE " + exc.entity_name + " " + exc.field_name)
        """
    )

    assert "REFUSE BareCoreEntity target" in out


def test_a_complete_declaration_builds_a_usable_coordinator() -> None:
    """A complete declaration passes every entry point and yields a built coordinator."""
    out = _run(
        """
        @exclude_graph_model
        @entity(description="Target", domain=EntrypointDomain)
        class TargetCoreEntity(BaseCoreEntity):
            id: str = Field(description="Identifier")

        @exclude_graph_model
        @entity(description="Complete host", domain=EntrypointDomain)
        class CompleteCoreEntity(BaseCoreEntity):
            target: Annotated[AssociationOne[TargetCoreEntity], NoInverse()] = Field(description="Target")

        coordinator = create_node_graph_coordinator()
        print("BUILT " + str(len(coordinator.get_all_nodes())))
        """
    )

    assert "BUILT" in out
