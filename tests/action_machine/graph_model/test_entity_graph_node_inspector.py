# tests/action_machine/graph_model/test_entity_graph_node_inspector.py
"""
EntityGraphNodeInspector — omission of stray ``BaseEntity`` subclasses.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Ensures ephemeral or test-local ``BaseEntity`` subclasses without ``@entity`` do not produce
nodes and therefore cannot crash ``NodeGraphCoordinator.build`` after they remain registered in
Python’s subtype tree.
"""

from __future__ import annotations

from pydantic import Field

from action_machine.domain.entity import BaseEntity
from action_machine.graph_model.inspectors.entity_graph_node_inspector import (
    EntityGraphNodeInspector,
)
from action_machine.system_core import TypeIntrospection


class UndecoratedFixtureEntity(BaseEntity):
    marker: str = Field(description="Fixture field for inspector skip test.")


def test_entity_graph_node_inspector_skips_host_without_entity_metadata() -> None:
    orphaned_id = TypeIntrospection.full_qualname(UndecoratedFixtureEntity)
    node_ids = {n.node_id for n in EntityGraphNodeInspector().get_graph_nodes()}
    assert orphaned_id not in node_ids
