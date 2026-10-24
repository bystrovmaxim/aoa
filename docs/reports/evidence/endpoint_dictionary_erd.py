"""Reproduce duplicate dictionary field rows in the public ERD summary.
Run: .venv/bin/python docs/reports/evidence/endpoint_dictionary_erd.py
"""

import asyncio
import json
import runpy
from pathlib import Path

from aoa.action_machine.model import BaseState
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.maxitor.model.diagrams.actions.list_entities_action import ListEntitiesAction
from aoa.maxitor.model.diagrams.resources.duckdb_graph_resource import DUCKDB_GRAPH_CONNECTION_KEY, DuckDBGraphResource


def main() -> None:
    """Project all six dictionary roles through the graph and public summary."""
    root = Path(__file__).resolve().parents[3]
    runpy.run_path(str(root / "examples/step_21_relations/72_role_dictionary.py"))
    machine = ActionProductMachine(loggers=[])
    domain = next(
        node.node_id for node in machine.graph_coordinator.get_all_nodes() if node.label == "DictionaryDomain"
    )
    store = DuckDBGraphResource.build_from_json(json.loads(machine.graph_coordinator.to_json()))
    result = asyncio.run(
        ListEntitiesAction().build_domain_payload_summary(
            ListEntitiesAction.Params(domain_qualnames=[domain], include_one_hop_neighbors=False),
            BaseState(),
            None,
            {DUCKDB_GRAPH_CONNECTION_KEY: store},
        )
    )
    diagram = result.model_dump(mode="json")["domain_slices"][0]["list_entities"]
    host = next(item for item in diagram["entities"] if item["label"] == "PriceListCoreEntity")
    counts = {
        name: sum(field["name"] == name for field in host["fields"])
        for name in ("primary", "quoted", "snapshot", "alternatives", "available", "bundled")
    }
    assert counts == dict.fromkeys(counts, 2)
    print("Rows per declared field:", counts)
    print("Relation families:", sorted({edge["relationship_kind"] for edge in diagram["relations"]}))


if __name__ == "__main__":
    main()
