"""
10_field_types.py — a field's type as one clean name, the full annotation beside it

A table row on the ERD has room for a short type, not for Python's internal spelling: ``str | None``
used to read ``UnionType[str, NoneType]`` and a relation ``AssociationOne[CurrencyEnumEntity]``.
``aoa-action-machine`` now writes each field's type into ``graph-json`` the way a reader would write
it (spec 029, FR-030) — ``field_type`` — and keeps the full annotation beside it —
``field_annotation`` — which the ERD shows in the row's tooltip.

The cases, with the real output at the bottom:

  1. the rule, annotation by annotation: an optional field, a relation by its target (``[]`` for
     many), a collection, literal values;
  2. the same two values on the wire, in rows of ``GET /api/v1/list-entities`` for demo tables: a
     reference to a dictionary, and a variant's reverse field to its specialization head.

A service built with an older ``aoa-action-machine`` sends the old spelling; the ERD cleans it by
the same rule before it draws the row.

Output:

    1. The rule
       str | None                                  -> str | None
       typing.Optional[int]                        -> int | None
       AssociationOne[Currency]                    -> Currency
       AggregateMany[Currency]                     -> Currency[]
       AssociationOne[Currency] | None             -> Currency | None
       list[str]                                   -> str[]
       tuple[int, ...]                             -> int[]
       typing.Literal['open', 'closed']            -> "open" | "closed"
    2. Rows on the wire
       ArbitrationBriefStubCoreEntity.currency_iso
          type:       CurrencyEnumEntity
          annotation: AssociationOne[CurrencyEnumEntity]
       GeneralizationVariantASpecEntity.head
          type:       GeneralizationHeadCoreEntity
          annotation: Generalization[GeneralizationHeadCoreEntity]

Tutorial: ../../docs/tutorials/step-26-maxitor.md  ·  topic: Maxitor (ERD)

Run:
    uv run python examples/step_26_maxitor/10_field_types.py
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any, Literal, Optional

from fastapi.testclient import TestClient

from aoa.action_machine.domain.relation_containers import AggregateMany, AssociationOne
from aoa.action_machine.graph.field_type_label import field_type_label
from aoa.demo.model.services.graph_json_service import ExampleModelGraphJsonService
from aoa.maxitor.api.app import create_app
from aoa.maxitor.api.graph_store import GraphEntry, GraphStore
from aoa.maxitor.model.diagrams.resources.duckdb_graph_resource import DuckDBGraphResource


class Currency:
    """A table a relation points at."""


ANNOTATIONS: list[tuple[str, Any]] = [
    ("str | None", str | None),
    ("typing.Optional[int]", Optional[int]),  # noqa: UP045 — the old spelling is what the rule reads
    ("AssociationOne[Currency]", AssociationOne[Currency]),
    ("AggregateMany[Currency]", AggregateMany[Currency]),
    ("AssociationOne[Currency] | None", AssociationOne[Currency] | None),
    ("list[str]", list[str]),
    ("tuple[int, ...]", tuple[int, ...]),
    ("typing.Literal['open', 'closed']", Literal["open", "closed"]),
]

# The demo model, served to Maxitor as any AOA service is.
_SOURCE = "https://demo.example/graph-json"
_GRAPH = json.loads(ExampleModelGraphJsonService().coordinator_json())


async def _builder(source: str) -> GraphEntry:
    """Build the demo model's graph for Maxitor."""
    sidebar = SimpleNamespace(level1_nodes=[], level2_diagrams=[], level2_nodes=[], level3_diagrams=[])
    return GraphEntry(source=source, graph=DuckDBGraphResource.build_from_json(_GRAPH), sidebar=sidebar, last_read=0.0)


app = create_app()
app.state.graph_store = GraphStore(_builder)
client = TestClient(app)


def row(table_name: str, field: str) -> tuple[str, dict[str, Any]]:
    """The row ``field`` of the demo table ``table_name``, as ``list-entities`` answers it."""
    table_id = next(n["id"] for n in _GRAPH["nodes"] if n["type"] == "Entity" and n["id"].endswith(f".{table_name}"))
    domain = next(e["target_id"] for e in _GRAPH["edges"] if e["type"] == "domain" and e["source_id"] == table_id)
    answer = client.get("/api/v1/list-entities", params={"source": _SOURCE, "domain_qualnames": domain}).json()
    table = next(e for e in answer["domain_slices"][0]["list_entities"]["entities"] if e["id"] == table_id)
    return table["label"], next(f for f in table["fields"] if f["name"] == field)


print("1. The rule")
for spelled, annotation in ANNOTATIONS:
    print(f"   {spelled:<43} -> {field_type_label(annotation)}")

print("2. Rows on the wire")
for table_name, field in [("ArbitrationBriefStubCoreEntity", "currency_iso"), ("GeneralizationVariantASpecEntity", "head")]:
    label, found = row(table_name, field)
    print(f"   {label}.{found['name']}")
    print(f"      type:       {found['type']}")
    print(f"      annotation: {found['annotation']}")
