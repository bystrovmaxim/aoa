# tests/graph/test_role_graph_node_inspector_extra.py

"""Extra coverage for role interchange node inspectors."""

from __future__ import annotations

from aoa.action_machine.auth.base_role import BaseRole
from aoa.action_machine.graph_model.inspectors.role_graph_node_inspector import RoleGraphNodeInspector
from aoa.action_machine.intents.role_mode.role_mode_decorator import RoleMode, role_mode


@role_mode(RoleMode.ALIVE)
class _InspectFixtureRole(BaseRole):
    """Minimal role fixture for interchange role-node coverage."""

    name = "inspect_fixture"
    description = "Fixture role for inspector tests."


def test_role_graph_node_inspector_axes() -> None:
    insp = RoleGraphNodeInspector()
    rn = insp._get_node(_InspectFixtureRole)  # pylint: disable=protected-access
    assert rn is not None
    assert rn.node_obj is _InspectFixtureRole
    assert rn.properties["role_mode"] == RoleMode.ALIVE.value
