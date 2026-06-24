"""Tests for :class:`~aoa.maxitor.model.diagrams.actions.domain_use_case_diagram_action.GetDomainUseCaseDiagramAction`."""

from __future__ import annotations

import pytest

from aoa.action_machine.graph.core.edge_relationship import GENERALIZATION
from aoa.action_machine.graph.node_graph_coordinator_factory import create_node_graph_coordinator
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.maxitor.model.diagrams.actions.domain_use_case_diagram_action import GetDomainUseCaseDiagramAction
from aoa.maxitor.model.diagrams.resources.duckdb_graph_resource import DUCKDB_GRAPH_CONNECTION_KEY, DuckDBGraphResource

_GEN = GENERALIZATION.archimate_name
_DOM_ID = "d.sample.StoreDom"


def _sample_payload() -> dict:
    return {
        "schema_version": "1.0",
        "nodes": [
            {
                "id": _DOM_ID,
                "label": "Store slice",
                "type": "Domain",
                "properties": {"name": "Store", "description": ""},
            },
            {
                "id": "a.child.Action",
                "label": "Child action",
                "type": "Action",
                "properties": {"description": "c"},
            },
            {
                "id": "a.parent.Action",
                "label": "Parent action",
                "type": "Action",
                "properties": {"description": "p"},
            },
            {
                "id": "a.peer.Action",
                "label": "Peer action",
                "type": "Action",
                "properties": {"description": ""},
            },
            {
                "id": "e.stub.Entity",
                "label": "Stub entity",
                "type": "Entity",
                "properties": {"description": ""},
            },
            {
                "id": "r.child.Role",
                "label": "Child role",
                "type": "Role",
                "properties": {"role_mode": "check"},
            },
            {
                "id": "r.base.Role",
                "label": "Base role",
                "type": "Role",
                "properties": {"role_mode": "check"},
            },
        ],
        "edges": [
            {
                "source_id": "a.child.Action",
                "target_id": _DOM_ID,
                "type": "domain",
                "relationship": "Aggregation",
                "is_dag": True,
                "properties": {},
            },
            {
                "source_id": "a.parent.Action",
                "target_id": _DOM_ID,
                "type": "domain",
                "relationship": "Aggregation",
                "is_dag": True,
                "properties": {},
            },
            {
                "source_id": "a.peer.Action",
                "target_id": _DOM_ID,
                "type": "domain",
                "relationship": "Aggregation",
                "is_dag": True,
                "properties": {},
            },
            {
                "source_id": "e.stub.Entity",
                "target_id": _DOM_ID,
                "type": "domain",
                "relationship": "Aggregation",
                "is_dag": True,
                "properties": {},
            },
            {
                "source_id": "a.child.Action",
                "target_id": "a.parent.Action",
                "type": "parent_action",
                "relationship": _GEN,
                "is_dag": False,
                "properties": {},
            },
            {
                "source_id": "a.child.Action",
                "target_id": "r.child.Role",
                "type": "@check_roles",
                "relationship": "Association",
                "is_dag": False,
                "properties": {},
            },
            {
                "source_id": "r.child.Role",
                "target_id": "r.base.Role",
                "type": "parent_role",
                "relationship": _GEN,
                "is_dag": False,
                "properties": {},
            },
            {
                "source_id": "a.child.Action",
                "target_id": "a.peer.Action",
                "type": "@depends",
                "relationship": "Association",
                "is_dag": True,
                "properties": {"description": "", "mode": "include"},
            },
        ],
    }


@pytest.mark.asyncio
async def test_domain_use_case_diagram_closure_and_edges() -> None:
    from aoa.action_machine.context.context import Context

    duck = DuckDBGraphResource.build_from_json(_sample_payload())
    machine = ActionProductMachine(graph_coordinator=create_node_graph_coordinator())
    result = await machine.run(
        Context(),
        GetDomainUseCaseDiagramAction(),
        GetDomainUseCaseDiagramAction.Params(domain_id=_DOM_ID),
        {DUCKDB_GRAPH_CONNECTION_KEY: duck},
    )
    j = result.model_dump(mode="json")["domain_use_case_diagram"]
    assert j["domain"]["id"] == _DOM_ID
    ids = {a["id"] for a in j["actions"]}
    assert ids == {"a.child.Action", "a.parent.Action", "a.peer.Action"}
    by_action = {a["id"]: a for a in j["actions"]}
    assert by_action["a.child.Action"]["role_ids"] == ["r.child.Role"]
    assert by_action["a.parent.Action"]["role_ids"] == []
    assert by_action["a.peer.Action"]["role_ids"] == []
    rids = {r["id"] for r in j["roles"]}
    assert rids == {"r.child.Role", "r.base.Role"}

    kinds = {(e["edge_kind"], e["source_id"], e["target_id"]) for e in j["edges"]}
    assert ("action_generalization", "a.child.Action", "a.parent.Action") in kinds
    assert ("role_generalization", "r.child.Role", "r.base.Role") in kinds
    assert ("association", "a.child.Action", "r.child.Role") in kinds
    assert ("include", "a.child.Action", "a.peer.Action") in kinds
    inc = next(e for e in j["edges"] if e["edge_kind"] == "include")
    assert inc.get("stereotype") == "«include»"


@pytest.mark.asyncio
async def test_domain_use_case_diagram_unknown_domain() -> None:
    from aoa.action_machine.context.context import Context

    duck = DuckDBGraphResource.build_from_json(_sample_payload())
    machine = ActionProductMachine(graph_coordinator=create_node_graph_coordinator())
    with pytest.raises(ValueError, match="Unknown domain"):
        await machine.run(
            Context(),
            GetDomainUseCaseDiagramAction(),
            GetDomainUseCaseDiagramAction.Params(domain_id="d.missing.X"),
            {DUCKDB_GRAPH_CONNECTION_KEY: duck},
        )
