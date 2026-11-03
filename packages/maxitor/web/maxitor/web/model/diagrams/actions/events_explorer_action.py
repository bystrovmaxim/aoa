# packages/maxitor/web/maxitor/web/model/diagrams/actions/events_explorer_action.py
"""
GetEventsExplorerAction — the whole events graph, for the explorer to open step by step (spec 055).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The explorer opens and closes ports with no round trip, so it reads every fact at once: every
domain with its vocabulary flag (an empty vocabulary is still one), every action with its domain,
the pairs of each vocabulary, every method of the five kinds that emits with the events it emits,
and the events with their fields.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    GET /api/v1/events-explorer ──► DuckDB ──► events_explorer(duck)
"""

from __future__ import annotations

from typing import Any, cast

from maxitor.web.model.diagrams.actions.domain_use_case_diagram_action import (
    _accent_by_domain,
    _action_domain_map,
    _short_qualname,
)
from maxitor.web.model.diagrams.actions.events_explorer_action_schema import EventsExplorerJson
from maxitor.web.model.diagrams.diagrams_domain import DiagramsDomain
from maxitor.web.model.diagrams.resources.duckdb_graph_resource import (
    DUCKDB_GRAPH_CONNECTION_KEY,
    DuckDBGraphResource,
)
from pydantic import Field

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.connection import connection
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseResult, BaseState, ParamsStub
from aoa.action_machine.resources import Connections
from aoa.action_machine.runtime.tools_box import ToolsBox

#: The five kinds of method: the node's type, its table, and the table of the edges from its action.
METHOD_KINDS = (
    ("RegularAspect", "regular_aspect", "regular_aspect_edges"),
    ("SummaryAspect", "summary_aspect", "summary_aspect_edges"),
    ("Compensator", "compensator", "compensate_edges"),
    ("ErrorHandler", "error_handler", "on_error_edges"),
    ("AccessDecide", "access_decide", "access_decide_edges"),
)


def _methods(duck: DuckDBGraphResource) -> dict[str, dict[str, str]]:
    """Every method of every kind by id, with its label, kind and action."""
    out: dict[str, dict[str, str]] = {}
    for kind, table, edges in METHOD_KINDS:
        for row in duck.execute_fetch_dicts(f"SELECT m.id, m.label, e.source_id AS action_id FROM {table} m JOIN {edges} e ON e.target_id = m.id"):
            out[str(row["id"])] = {"label": str(row["label"]), "kind": kind, "action_id": str(row["action_id"])}
    return out


def _event_fields(duck: DuckDBGraphResource) -> dict[str, list[dict[str, str]]]:
    """Each event's fields, sorted by name; the type is the JSON schema's, when the document gives one."""
    rows = duck.execute_fetch_dicts(
        """
        SELECT e.source_id, f.label, f.description, f.json_schema_name
        FROM field_edges e JOIN field f ON f.id = e.target_id JOIN event v ON v.id = e.source_id
        ORDER BY e.source_id, f.label
        """,
    )
    out: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        out.setdefault(str(row["source_id"]), []).append({"name": str(row["label"]), "type": str(row["json_schema_name"] or ""), "description": str(row["description"] or "")})
    return out


def _pairs(duck: DuckDBGraphResource, table: str) -> list[tuple[str, str]]:
    """An edge table's (source, target) pairs, sorted."""
    return sorted((str(r["source_id"]), str(r["target_id"])) for r in duck.execute_fetch_dicts(f"SELECT source_id, target_id FROM {table}"))


def events_explorer(duck: DuckDBGraphResource) -> dict[str, Any]:
    """
    AI-CORE-BEGIN
    ROLE: Read the whole events graph the explorer opens: domains, actions, events, vocabularies and emitting methods.
    CONTRACT: Every domain and every action, with or without events; each ``emits`` row names its action, method, kind and event.
    INVARIANTS: Read-only; every list sorted, so one graph gives one answer; a document older than events gives empty events, holds and emits.
    AI-CORE-END
    """
    accents = _accent_by_domain(duck)
    domain_of_action = _action_domain_map(duck)
    methods = _methods(duck)
    domains = duck.execute_fetch_dicts("SELECT id, label, name, typed_events FROM domain ORDER BY id")
    actions = duck.execute_fetch_dicts("SELECT id, label FROM action ORDER BY id")
    events = duck.execute_fetch_dicts("SELECT id, label FROM event ORDER BY id")
    fields = _event_fields(duck)
    emits = [
        {"action_id": methods[method]["action_id"], "method_id": method, "method": methods[method]["label"], "kind": methods[method]["kind"], "event_id": event}
        for method, event in _pairs(duck, "emits_edges")
        if method in methods
    ]
    return {
        "domains": [
            {
                "id": str(row["id"]),
                "label": str(row["label"] or row["id"]),
                "short_label": str(row["name"] or "").strip() or _short_qualname(str(row["id"])),
                "accent_color": accents.get(str(row["id"]), "#64748b"),
                "vocabulary": bool(row["typed_events"]),
            }
            for row in domains
        ],
        "actions": [
            {"id": str(row["id"]), "label": str(row["label"] or row["id"]), "short_label": _short_qualname(str(row["label"] or row["id"])), "domain_id": domain_of_action.get(str(row["id"]), "")}
            for row in actions
        ],
        "events": [{"id": str(row["id"]), "label": str(row["label"] or _short_qualname(str(row["id"]))), "fields": fields.get(str(row["id"]), [])} for row in events],
        "holds": [{"domain_id": domain, "event_id": event} for domain, event in _pairs(duck, "domain_event_edges")],
        "emits": sorted(emits, key=lambda row: (row["action_id"], row["method_id"], row["event_id"])),
    }


class EventsExplorerResult(BaseResult):
    """The events graph of the explorer."""

    events_explorer: EventsExplorerJson = Field(description="Domains, actions, events, vocabulary pairs and emitting methods.")


@meta(description="Return the whole events graph for the explorer", domain=DiagramsDomain)
@check_roles(GuestRole)
@connection(DuckDBGraphResource, key=DUCKDB_GRAPH_CONNECTION_KEY, description="Coordinator graph in DuckDB")
class GetEventsExplorerAction(BaseAction[ParamsStub, EventsExplorerResult]):
    """
    AI-CORE-BEGIN
    ROLE: Materialize the events graph the SPA's explorer opens through ports.
    CONTRACT: The shape of ``events_explorer``; the client computes layers, ports and lines from it.
    AI-CORE-END
    """

    @summary_aspect("Build the events graph of the explorer")
    async def events_explorer_summary(
        self,
        params: ParamsStub,
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
    ) -> EventsExplorerResult:
        """Read the whole events graph."""
        _ = (params, state, box)
        duck = cast(DuckDBGraphResource, connections[DUCKDB_GRAPH_CONNECTION_KEY])
        return EventsExplorerResult(events_explorer=events_explorer(duck))
