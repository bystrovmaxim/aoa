"""
Scenario: what the graph and its JSON say about events.

Demonstrates:
  1. a domain with no switch has no events in the graph, and an event nobody names has no node
  2. @emits gives an Event node and an @emits edge, with no vocabulary (typed_events is false)
  3. events gives domain_event edges and typed_events true, also for an event nobody emits
  4. every kind of method gives its @emits edge
  5. an empty vocabulary is still a vocabulary
  6. a child domain inherits a vocabulary, and declaring its own replaces it
  7. an event in two vocabularies is one node, and its fields carry their descriptions
  8. @emits outside the vocabulary stops the build
  9. comparing two graphs shows an event added and removed like any element

Tutorial: ../../docs/tutorials/step-11-object-events.md

Run:
    uv run --extra dev python examples/step_11_object_events/08_events_in_graph.py
"""
import json
from typing import Any

from maxitor.graph_compare import compare
from pydantic import Field

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.exceptions.event_contract_error import EventContractError
from aoa.action_machine.graph.node_graph_coordinator_factory import create_node_graph_coordinator
from aoa.action_machine.intents.access_control import Allowed, Verdict
from aoa.action_machine.intents.access_decide import access_decide
from aoa.action_machine.intents.aspects import regular_aspect, summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.compensate import compensate
from aoa.action_machine.intents.emits import emits
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.intents.on_error import on_error
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.model.base_event import BaseEvent
from aoa.action_machine.model.base_state import BaseState
from aoa.action_machine.resources import Connections
from aoa.action_machine.runtime.tools_box import ToolsBox


# -- The facts
class UnusedEvent(BaseEvent):
    """Loaded, and named by nobody."""


class StockCheckedEvent(BaseEvent):
    """Named only by @emits, in a domain with no vocabulary."""

    item: str = Field(description="What was checked")


class OrderCompletedEvent(BaseEvent):
    """In two vocabularies, emitted by every kind of method."""

    order_id: str = Field(description="The completed order")
    total: float


class CouponUsedEvent(BaseEvent):
    """In a vocabulary, and nobody emits it."""


class RefundIssuedEvent(BaseEvent):
    """In the vocabulary of a child domain that replaces its parent's."""


# -- The domains, one per case
class PlainDomain(BaseDomain):
    name = "plain"
    description = "No switch at all"


class ZoneDomain(BaseDomain):
    name = "zone"
    description = "A typed zone, no vocabulary"


class StoreDomain(BaseDomain):
    name = "store"
    description = "A vocabulary"
    events = (OrderCompletedEvent, CouponUsedEvent)


class BillingDomain(BaseDomain):
    name = "billing"
    description = "The same event in a second vocabulary"
    events = (OrderCompletedEvent,)


class SilentDomain(BaseDomain):
    name = "silent"
    description = "A vocabulary that allows nothing"
    events = ()


class OutletDomain(StoreDomain):
    name = "outlet"
    description = "Inherits the vocabulary"


class ReturnsDomain(StoreDomain):
    name = "returns"
    description = "Replaces the vocabulary"
    events = (RefundIssuedEvent,)


class Params(BaseParams):
    pass


class Result(BaseResult):
    pass


# -- The actions
@meta(description="Mode 1", domain=PlainDomain)
@check_roles(GuestRole)
class PlainAction(BaseAction[Params, Result]):
    @summary_aspect("Finish")
    async def finish_summary(self, params: Params, state: BaseState, box: ToolsBox, connections: Connections) -> Result:
        return Result()


@meta(description="Mode 2", domain=ZoneDomain)
@check_roles(GuestRole)
class ZoneAction(BaseAction[Params, Result]):
    @emits(StockCheckedEvent)
    @summary_aspect("Finish")
    async def finish_summary(self, params: Params, state: BaseState, box: ToolsBox, connections: Connections) -> Result:
        return Result()


@meta(description="Mode 3, one method of every kind", domain=StoreDomain)
@check_roles(GuestRole)
class CompleteOrderAction(BaseAction[Params, Result]):
    @emits(OrderCompletedEvent)
    @regular_aspect("Reserve")
    async def reserve_aspect(
        self, params: Params, state: BaseState, box: ToolsBox, connections: Connections
    ) -> dict[str, Any]:
        return {}

    @emits(OrderCompletedEvent)
    @summary_aspect("Finish")
    async def finish_summary(self, params: Params, state: BaseState, box: ToolsBox, connections: Connections) -> Result:
        return Result()

    @emits(OrderCompletedEvent)
    @compensate(reserve_aspect, "Release")
    async def release_compensate(
        self,
        params: Params,
        state_before: BaseState,
        state_after: BaseState | None,
        box: ToolsBox,
        connections: Connections,
        error: Exception,
    ) -> None:
        return None

    @emits(OrderCompletedEvent)
    @on_error(ValueError, description="Answer anyway")
    async def answer_on_error(
        self, params: Params, state: BaseState, box: ToolsBox, connections: Connections, error: Exception
    ) -> Result:
        return Result()

    @emits(OrderCompletedEvent)
    @access_decide("Decide")
    async def decide_access_decide(self, params: Params, box: ToolsBox, connections: Connections) -> Verdict:
        return Allowed()


# -- Read the document, as any consumer would
document: dict[str, Any] = json.loads(create_node_graph_coordinator().to_json())


def short(node_id: str) -> str:
    """Drop the module path of an id, for reading."""
    return node_id.split(".")[-1]


nodes = {node["id"]: node for node in document["nodes"]}
events = sorted(node["label"] for node in nodes.values() if node["type"] == "Event")
print("schema_version:", document["schema_version"])
print("Event nodes:", events)


def domain_row(label: str) -> tuple[bool, list[str]]:
    """Return a domain's ``typed_events`` and the events of its vocabulary."""
    domain = next(node for node in nodes.values() if node["type"] == "Domain" and node["label"] == label)
    vocabulary = sorted(
        short(edge["target_id"])
        for edge in document["edges"]
        if edge["type"] == "domain_event" and edge["source_id"] == domain["id"]
    )
    return domain["properties"]["typed_events"], vocabulary


# -- Each domain: typed_events and its vocabulary
for label in ("PlainDomain", "ZoneDomain", "StoreDomain", "SilentDomain", "OutletDomain", "ReturnsDomain"):
    print(f"{label}:", *domain_row(label))

# -- Every @emits edge
for edge in sorted(document["edges"], key=lambda row: row["id"]):
    if edge["type"] == "@emits":
        print(short(edge["source_id"]), "->", short(edge["target_id"]), f"({nodes[edge['source_id']]['type']})")

# -- One node, two vocabularies, and the fields
order_event = next(node for node in nodes.values() if node["label"] == "OrderCompletedEvent")
print("domains:", sorted(short(e["source_id"]) for e in document["edges"] if e["type"] == "domain_event" and e["target_id"] == order_event["id"]))
for edge in document["edges"]:
    if edge["type"] == "field" and edge["source_id"] == order_event["id"]:
        field_node = nodes[edge["target_id"]]
        print(f"{field_node['label']}: {field_node['properties']['description']!r}")


# -- Outside the vocabulary: the build stops
def declare_outside() -> None:
    """Declare an event the domain does not allow, build, and forget the class."""

    @meta(description="Wrong", domain=StoreDomain)
    @check_roles(GuestRole)
    class WrongAction(BaseAction[Params, Result]):
        @emits(StockCheckedEvent)
        @summary_aspect("Finish")
        async def finish_summary(
            self, params: Params, state: BaseState, box: ToolsBox, connections: Connections
        ) -> Result:
            return Result()

    try:
        create_node_graph_coordinator()
    except EventContractError as error:
        print("EventContractError:", error)


declare_outside()


# -- Two versions of a graph
def without_event(graph: dict[str, Any], label: str) -> dict[str, Any]:
    """Return a copy of ``graph`` with no ``label`` node and none of its edges."""
    gone = {node["id"] for node in graph["nodes"] if node["label"] == label}
    return {
        "schema_version": graph["schema_version"],
        "nodes": [node for node in graph["nodes"] if node["id"] not in gone],
        "edges": [e for e in graph["edges"] if e["source_id"] not in gone and e["target_id"] not in gone],
    }


older = without_event(document, "CouponUsedEvent")
comparison = compare(older, document)
print("added nodes:", [short(key) for key, item in comparison.nodes.items() if item.status == "added"])
print("added edges:", [short(key) for key, item in comparison.edges.items() if item.status == "added"])
