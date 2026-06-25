# tests/action_machine/graph/test_node_graph_coordinator_generalization_integration.py
"""PR-5 integration: real axis nodes + default coordinator export (plan §PR-5)."""

from __future__ import annotations

import json

import tests.action_machine.graph_host.test_graph_node_generalization_edges as pr3_actions
import tests.action_machine.graph_host.test_parent_generalization_edges as pr2_fixtures
from aoa.action_machine.graph.node_graph_coordinator_factory import create_node_graph_coordinator
from aoa.action_machine.system_core.type_introspection import TypeIntrospection


def test_create_node_graph_coordinator_includes_parent_action_in_json() -> None:
    coord = create_node_graph_coordinator()
    payload = json.loads(coord.to_json())
    child_id = TypeIntrospection.full_qualname(pr3_actions._Pr3ChildAction)
    parent_id = TypeIntrospection.full_qualname(pr3_actions._Pr3ParentAction)
    matches = [
        e
        for e in payload["edges"]
        if e["type"] == "parent_action" and e["source_id"] == child_id and e["target_id"] == parent_id
    ]
    assert len(matches) == 1
    assert matches[0]["relationship"] == "Generalization"

    triples = coord.get_edges_by_type("parent_action")
    assert any(s == child_id and t == parent_id for s, t, _e in triples)


def test_create_node_graph_coordinator_includes_parent_role_and_domain_in_json() -> None:
    coord = create_node_graph_coordinator()
    payload = json.loads(coord.to_json())

    child_role = TypeIntrospection.full_qualname(pr2_fixtures._ChildGenRole)
    parent_role = TypeIntrospection.full_qualname(pr2_fixtures._ParentGenRole)
    pr = [e for e in payload["edges"] if e["type"] == "parent_role" and e["source_id"] == child_role]
    assert len(pr) == 1
    assert pr[0]["target_id"] == parent_role

    child_dom = TypeIntrospection.full_qualname(pr2_fixtures._ChildGenDomain)
    parent_dom = TypeIntrospection.full_qualname(pr2_fixtures._ParentGenDomain)
    pd = [e for e in payload["edges"] if e["type"] == "parent_domain" and e["source_id"] == child_dom]
    assert len(pd) == 1
    assert pd[0]["target_id"] == parent_dom

    assert coord.get_edges_by_type("parent_role")
    assert coord.get_edges_by_type("parent_domain")
