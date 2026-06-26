# tests/examples/model/test_examples_generalization_edges.py
"""PR-6: sample model emits ``parent_*`` generalization edges in interchange export (plan §PR-6)."""

from __future__ import annotations

import json

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


def test_examples_model_interchange_includes_parent_generalization_edges() -> None:
    import_sample_registration_modules()
    coord = build_registered_interchange_coordinator()
    payload = json.loads(coord.to_json())
    node_ids = {n["id"] for n in payload["nodes"]}

    assert issubclass(StoreDomain, BaseDomain)

    editor_id = TypeIntrospection.full_qualname(EditorRole)
    viewer_id = TypeIntrospection.full_qualname(ViewerRole)
    pr = [e for e in payload["edges"] if e["type"] == "parent_role" and e["source_id"] == editor_id]
    assert len(pr) == 1
    assert pr[0]["target_id"] == viewer_id
    assert pr[0]["relationship"] == "Generalization"
    assert viewer_id in node_ids

    store_dom_id = TypeIntrospection.full_qualname(StoreDomain)
    marketplace_id = TypeIntrospection.full_qualname(MarketplaceOperationsDomain)
    pd = [e for e in payload["edges"] if e["type"] == "parent_domain" and e["source_id"] == store_dom_id]
    assert len(pd) == 1
    assert pd[0]["target_id"] == marketplace_id
    assert marketplace_id in node_ids

    lookup_id = TypeIntrospection.full_qualname(OrderLookupAction)
    read_id = TypeIntrospection.full_qualname(StoreReadAction)
    pa = [e for e in payload["edges"] if e["type"] == "parent_action" and e["source_id"] == lookup_id]
    assert len(pa) == 1
    assert pa[0]["target_id"] == read_id
    assert read_id in node_ids

    for edge in pr + pd + pa:
        tid = edge["target_id"]
        assert tid in node_ids, f"missing target node {tid!r} for edge {edge!r}"
