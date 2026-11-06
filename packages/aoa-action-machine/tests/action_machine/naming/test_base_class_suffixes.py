# packages/aoa-action-machine/tests/action_machine/naming/test_base_class_suffixes.py
"""Each base class refuses a descendant whose name lacks its suffix, and accepts one that has it."""

from __future__ import annotations

import pytest

from aoa.action_machine.adapters.base_adapter import BaseAdapter
from aoa.action_machine.adapters.base_route_record import BaseRouteRecord
from aoa.action_machine.domain.lifecycle import Lifecycle
from aoa.action_machine.exceptions import NamingSuffixError
from aoa.action_machine.graph.core.base_graph_edge import BaseGraphEdge
from aoa.action_machine.graph.core.base_graph_node import BaseGraphNode
from aoa.action_machine.graph.core.base_graph_node_inspector import BaseGraphNodeInspector
from aoa.action_machine.plugin.core.events import BasePluginEvent
from aoa.action_machine.runtime.base_action_machine import BaseActionMachine
from aoa.action_machine.runtime.base_coordinator import BaseCoordinator

# base class, the name it reports, the suffix its descendants carry
BASES: list[tuple[type, str, str]] = [
    (Lifecycle, "Lifecycle", "Lifecycle"),
    (BaseAdapter, "BaseAdapter", "Adapter"),
    (BaseCoordinator, "BaseCoordinator", "Coordinator"),
    (BasePluginEvent, "BasePluginEvent", "Event"),
    (BaseGraphNode, "BaseGraphNode", "GraphNode"),
    (BaseGraphEdge, "BaseGraphEdge", "GraphEdge"),
    (BaseGraphNodeInspector, "BaseGraphNodeInspector", "Inspector"),
    (BaseActionMachine, "BaseActionMachine", "Machine"),
    (BaseRouteRecord, "BaseRouteRecord", "RouteRecord"),
]
IDS = [suffix for _, _, suffix in BASES]


@pytest.mark.parametrize(("base", "base_name", "suffix"), BASES, ids=IDS)
def test_a_name_without_the_suffix_is_refused(base: type, base_name: str, suffix: str) -> None:
    """The refusal names the class, its base, the suffix and the name to use."""
    with pytest.raises(NamingSuffixError) as refused:
        type("Orders", (base,), {})
    assert str(refused.value) == (
        f"Class 'Orders' inherits {base_name} but lacks the '{suffix}' suffix. Rename to 'Orders{suffix}'."
    )


@pytest.mark.parametrize(("base", "base_name", "suffix"), BASES, ids=IDS)
def test_a_name_with_the_suffix_is_accepted(base: type, base_name: str, suffix: str) -> None:
    """A descendant named with the suffix is declared as before."""
    assert issubclass(type(f"Orders{suffix}", (base,), {}), base)


@pytest.mark.parametrize(("base", "base_name", "suffix"), BASES, ids=IDS)
def test_the_suffix_must_end_the_name(base: type, base_name: str, suffix: str) -> None:
    """The suffix in the middle of a name does not count."""
    with pytest.raises(NamingSuffixError):
        type(f"{suffix}Orders", (base,), {})


@pytest.mark.parametrize(("base", "base_name", "suffix"), BASES, ids=IDS)
def test_an_indirect_descendant_is_checked_too(base: type, base_name: str, suffix: str) -> None:
    """The rule follows the hierarchy: a descendant of a descendant keeps the suffix."""
    parent = type(f"Shared{suffix}", (base,), {})
    with pytest.raises(NamingSuffixError):
        type("Orders", (parent,), {})
