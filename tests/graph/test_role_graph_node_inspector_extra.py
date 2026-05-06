# tests/graph/test_role_graph_node_inspector_extra.py

"""Extra coverage for role interchange node inspectors."""

from __future__ import annotations

from action_machine.auth.base_role import BaseRole
from action_machine.graph_model.inspectors.role_graph_node_inspector import RoleGraphNodeInspector
from action_machine.intents.role_mode.role_mode_decorator import RoleMode, role_mode


@role_mode(RoleMode.ALIVE)
class _InspectFixtureRole(BaseRole):
    """Minimal role fixture for interchange role-node coverage."""

    name = "inspect_fixture"
    description = "Fixture role for inspector tests."


def test_role_graph_node_inspector_axes() -> None:
    insp = RoleGraphNodeInspector()
    assert insp._get_node(object) is None  # pylint: disable=protected-access
    rn = insp._get_node(_InspectFixtureRole)  # pylint: disable=protected-access
    assert rn is not None
    assert rn.node_obj is _InspectFixtureRole
    assert rn.properties["role_mode"] == RoleMode.ALIVE.value


def test_role_graph_node_inspector_skips_role_without_role_mode() -> None:
    """Undecorated ``BaseRole`` subclasses are omitted (interchange needs ``RoleMode``)."""

    class _NoDecoratedModeRole(BaseRole):
        name = "no_decorated_mode_fixture"
        description = "Fixture: valid body but no ``@role_mode``."

    assert RoleGraphNodeInspector()._get_node(_NoDecoratedModeRole) is None  # pylint: disable=protected-access
