# tests/examples/model/test_examples_generalization_edges.py
"""PR-6: sample model emits ``parent_*`` generalization edges in interchange export (plan §PR-6)."""

from __future__ import annotations

import json
from typing import Any

from aoa.action_machine.domain import BaseDomain
from aoa.action_machine.system_core.type_introspection import TypeIntrospection
from aoa.demo.model.interchange_demo_coordinator import (
    build_registered_interchange_coordinator,
    import_sample_registration_modules,
)
from aoa.demo.model.roles import EditorRole, ViewerRole
from aoa.demo.model.store.actions.order_lookup import OrderLookupAction
from aoa.demo.model.store.actions.store_read import StoreReadAction
from aoa.demo.model.store.marketplace_operations_domain import MarketplaceOperationsDomain
from aoa.demo.model.store.store_domain import StoreDomain


def _the_parent_edge(payload: dict[str, Any], edge_type: str, child: type, parent: type) -> dict[str, Any]:
    """Assert ``child`` has one ``edge_type`` edge, to ``parent``, which is a node of the graph; return that edge."""
    child_id = TypeIntrospection.full_qualname(child)
    parent_id = TypeIntrospection.full_qualname(parent)
    found = [e for e in payload["edges"] if e["type"] == edge_type and e["source_id"] == child_id]
    assert len(found) == 1
    assert found[0]["target_id"] == parent_id
    assert parent_id in {n["id"] for n in payload["nodes"]}
    return found[0]


def test_examples_model_interchange_includes_parent_generalization_edges() -> None:
    import_sample_registration_modules()
    coord = build_registered_interchange_coordinator()
    payload = json.loads(coord.to_json())

    assert issubclass(StoreDomain, BaseDomain)

    assert _the_parent_edge(payload, "parent_role", EditorRole, ViewerRole)["relationship"] == "Generalization"
    _the_parent_edge(payload, "parent_domain", StoreDomain, MarketplaceOperationsDomain)
    _the_parent_edge(payload, "parent_action", OrderLookupAction, StoreReadAction)
