# tests/action_machine/graph/test_dead_classes_in_the_walk.py
"""
A class that no longer exists never reaches the graph.

``__subclasses__()`` keeps listing a dead class until the garbage collector clears it,
and when that happens differs between Python versions. The build must not depend on it.
"""

from __future__ import annotations

import pytest

from aoa.action_machine.domain import BaseEntity
from aoa.action_machine.exceptions.declaration_structure_error import DeclarationStructureError
from aoa.action_machine.graph.node_graph_coordinator_factory import create_node_graph_coordinator


def test_an_entity_refused_at_declaration_does_not_break_the_build() -> None:
    """The refused class was never finished, so it has no ``@entity`` and must not be read."""
    with pytest.raises(DeclarationStructureError, match="BaseRefusedEntity"):
        type(
            "BaseRefusedEntity",
            (BaseEntity,),
            {"__init_subclass__": classmethod(lambda cls, **kwargs: None), "__module__": __name__},
        )

    create_node_graph_coordinator()
