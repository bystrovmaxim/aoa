# packages/maxitor/web/maxitor/web/model/diagrams/actions/domain_events_diagram_action.py
"""
GetDomainEventsDiagramAction, GetAllEventsDiagramAction — which method emits what (spec 053).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A domain's answer to "which facts come out of here": its actions, those of their methods
that emit, and the events, standing in bands by the domain's vocabulary. An event also
carries what its card shows: fields, every method producing it, and its domains.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    GET /api/v1/domain-events-diagram ──► DuckDB ──► events_diagram(duck, domain_row)
    GET /api/v1/events-diagram        ──► DuckDB ──► events_diagram(duck, None)
"""

from __future__ import annotations

from typing import Any, cast

from maxitor.web.model.diagrams.actions.domain_events_diagram_action_schema import DomainEventsDiagramJson
from maxitor.web.model.diagrams.actions.domain_use_case_diagram_action import (
    ALL_DOMAINS,
    _accent_by_domain,
    _action_domain_map,
    _short_qualname,
)
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
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult, BaseState, ParamsStub
from aoa.action_machine.resources import Connections
from aoa.action_machine.runtime.tools_box import ToolsBox

#: The five kinds of method: the node's type, its table, and the table of the edges from its action.
_METHOD_KINDS = (
    ("RegularAspect", "regular_aspect", "regular_aspect_edges", "@regular_aspect"),
    ("SummaryAspect", "summary_aspect", "summary_aspect_edges", "@summary_aspect"),
    ("Compensator", "compensator", "compensate_edges", "@compensate"),
    ("ErrorHandler", "error_handler", "on_error_edges", "@on_error"),
    ("AccessDecide", "access_decide", "access_decide_edges", "@access_decide"),
)


def _methods(duck: DuckDBGraphResource) -> dict[str, dict[str, str]]:
    """Every method of every kind by id, with its action and the type of the edge from it."""
    out: dict[str, dict[str, str]] = {}
    for kind, table, edges, edge_type in _METHOD_KINDS:
        rows = duck.execute_fetch_dicts(f"SELECT m.id, m.label, e.source_id AS action_id FROM {table} m JOIN {edges} e ON e.target_id = m.id")
        for row in rows:
            out[str(row["id"])] = {"id": str(row["id"]), "label": str(row["label"]), "kind": kind, "action_id": str(row["action_id"]), "edge_type": edge_type}
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
        out.setdefault(str(row["source_id"]), []).append({"name": str(row["label"]), "type": str(row["json_schema_name"] or ""), "description": str(row["description"])})
    return out


def _band(typed: bool | None, in_vocabulary: bool, emitted: bool) -> str:
    """The band of an event on this diagram (spec 053, Clarifications)."""
    if not emitted:
        return "not_emitted"
    return "in_vocabulary" if typed and in_vocabulary else "emitted"


def _domain_json(domain_row: dict[str, Any] | None, accents: dict[str, str]) -> dict[str, Any]:
    """The diagram's domain; every domain together has no one vocabulary, so ``typed_events`` is ``None``."""
    if domain_row is None:
        return {**ALL_DOMAINS, "typed_events": None}
    domain_id = str(domain_row["id"])
    return {
        "id": domain_id,
        "label": str(domain_row.get("label") or domain_id),
        "short_label": str(domain_row.get("name") or "").strip() or _short_qualname(domain_id),
        "accent_color": accents.get(domain_id, "#64748b"),
        "typed_events": bool(domain_row["typed_events"]),
    }


def _action_json(aid: str, label: str | None, dom: str, accents: dict[str, str]) -> dict[str, Any]:
    """One action box, coloured by its domain."""
    return {
        "id": aid,
        "label": label or _short_qualname(aid),
        "short_label": _short_qualname(label or aid),
        "domain_id": dom,
        "domain_short_label": _short_qualname(dom) if dom else "No domain",
        "accent_color": accents.get(dom, "#94a3b8"),
    }


def _producer_json(method: dict[str, str], action_labels: dict[str, str]) -> dict[str, str]:
    """One method that produces an event, as its card lists it."""
    action_id = method["action_id"]
    return {"id": method["id"], "label": method["label"], "kind": method["kind"], "action_id": action_id, "action_label": action_labels.get(action_id, action_id)}


def _event_domains(holding: set[str], emitting: set[str], domain_labels: dict[str, str]) -> list[dict[str, Any]]:
    """An event's domains: those whose vocabulary holds it first, then those that only emit it."""
    ordered = sorted(holding | emitting, key=lambda each: (each not in holding, each))
    return [{"id": d, "label": domain_labels.get(d, _short_qualname(d)), "in_vocabulary": d in holding} for d in ordered]


def _labels(duck: DuckDBGraphResource, table: str) -> dict[str, str]:
    """Each row's label by id."""
    return {str(r["id"]): str(r["label"]) for r in duck.execute_fetch_dicts(f"SELECT id, label FROM {table}")}


def _pairs(duck: DuckDBGraphResource, table: str) -> list[tuple[str, str]]:
    """An edge table's (source, target) pairs, sorted."""
    return sorted((str(r["source_id"]), str(r["target_id"])) for r in duck.execute_fetch_dicts(f"SELECT source_id, target_id FROM {table}"))


def _edges(methods: dict[str, dict[str, str]], method_ids: list[str], in_scope: list[tuple[str, str]]) -> list[dict[str, Any]]:
    """The links: each action to its methods, then each method to the events it emits."""
    edges: list[dict[str, Any]] = []
    for method in method_ids:
        row = methods[method]
        edges.append({"id": f"{row['action_id']}|{row['edge_type']}|{method}", "edge_kind": "method", "source_id": row["action_id"], "target_id": method})
    for method, event in in_scope:
        edges.append({"id": f"{method}|@emits|{event}", "edge_kind": "emits", "source_id": method, "target_id": event})
    return edges


def events_diagram(duck: DuckDBGraphResource, domain_row: dict[str, Any] | None) -> dict[str, Any]:
    """
    AI-CORE-BEGIN
    ROLE: Build the events diagram of one domain, or of every domain when ``domain_row`` is ``None``.
    CONTRACT: Actions with an emitting method, those methods, the events of the scope in bands, and the links, each with its protocol id.
    INVARIANTS: Read-only; an event stands once; the lists are sorted, so one graph gives one diagram.
    AI-CORE-END
    """
    accents = _accent_by_domain(duck)
    domain_of_action = _action_domain_map(duck)
    methods = _methods(duck)
    action_labels = _labels(duck, "action")
    domain_labels = _labels(duck, "domain")
    events = _labels(duck, "event")
    emits = [(method, event) for method, event in _pairs(duck, "emits_edges") if method in methods]
    vocabulary = set(_pairs(duck, "domain_event_edges"))
    fields = _event_fields(duck)
    domain_json = _domain_json(domain_row, accents)
    domain_id = None if domain_row is None else domain_json["id"]
    typed: bool | None = domain_json["typed_events"]

    def domain_of_method(method: str) -> str:
        return domain_of_action.get(methods[method]["action_id"], "")

    in_scope = [(m, e) for m, e in emits if domain_id is None or domain_of_method(m) == domain_id]
    emitted = {event for _, event in in_scope}
    held = {event for owner, event in vocabulary if owner == domain_id} if domain_id else set(events)
    method_ids = sorted({method for method, _ in in_scope})
    action_ids = sorted({methods[method]["action_id"] for method in method_ids})

    def event_json(eid: str) -> dict[str, Any]:
        producers = sorted({m for m, e in emits if e == eid})
        holding = {owner for owner, event in vocabulary if event == eid}
        emitting = {domain_of_method(m) for m in producers} - {""}
        return {
            "id": eid,
            "label": events.get(eid, _short_qualname(eid)),
            "band": _band(typed, eid in held, eid in emitted),
            "fields": fields.get(eid, []),
            "methods": [_producer_json(methods[m], action_labels) for m in producers],
            "domains": _event_domains(holding, emitting, domain_labels),
        }

    events_json = [event_json(eid) for eid in sorted(emitted | held)]

    return {
        "domain": domain_json,
        "actions": [_action_json(aid, action_labels.get(aid), domain_of_action.get(aid, domain_id or ""), accents) for aid in action_ids],
        "methods": [{key: methods[m][key] for key in ("id", "label", "kind", "action_id")} for m in method_ids],
        "events": events_json,
        "edges": _edges(methods, method_ids, in_scope),
    }


class EventsDiagramResult(BaseResult):
    """An events diagram."""

    domain_events_diagram: DomainEventsDiagramJson = Field(description="Actions, emitting methods, events in bands and their links.")


@meta(description="Return the events diagram of one domain", domain=DiagramsDomain)
@check_roles(GuestRole)
@connection(DuckDBGraphResource, key=DUCKDB_GRAPH_CONNECTION_KEY, description="Coordinator graph in DuckDB")
class GetDomainEventsDiagramAction(BaseAction["GetDomainEventsDiagramAction.Params", EventsDiagramResult]):
    """
    AI-CORE-BEGIN
    ROLE: Materialize one domain's events diagram for the SPA.
    CONTRACT: ``domain_id`` is the interchange domain vertex id; a domain with no events gives empty lists.
    AI-CORE-END
    """

    class Params(BaseParams):
        domain_id: str = Field(min_length=1, description="Interchange Domain vertex id (full type qualname)")

    @summary_aspect("Build a domain's events diagram")
    async def build_events_summary(
        self,
        params: GetDomainEventsDiagramAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
    ) -> EventsDiagramResult:
        """Read the domain and build its diagram."""
        _ = (state, box)
        duck = cast(DuckDBGraphResource, connections[DUCKDB_GRAPH_CONNECTION_KEY])
        domain_id = params.domain_id.strip()
        rows = duck.execute_fetch_dicts("SELECT id, label, name, typed_events FROM domain WHERE id = ? LIMIT 1", [domain_id])
        if not rows:
            msg = f"Unknown domain id {domain_id!r}"
            raise ValueError(msg)
        return EventsDiagramResult(domain_events_diagram=events_diagram(duck, dict(rows[0])))


@meta(description="Return the events diagram of every domain together", domain=DiagramsDomain)
@check_roles(GuestRole)
@connection(DuckDBGraphResource, key=DUCKDB_GRAPH_CONNECTION_KEY, description="Coordinator graph in DuckDB")
class GetAllEventsDiagramAction(BaseAction[ParamsStub, EventsDiagramResult]):
    """
    AI-CORE-BEGIN
    ROLE: Materialize the whole application's events diagram for the SPA.
    CONTRACT: The shape of one domain's diagram; ``typed_events`` is ``None``, as no one vocabulary applies.
    AI-CORE-END
    """

    @summary_aspect("Build the events diagram of every domain")
    async def all_events_summary(
        self,
        params: ParamsStub,
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
    ) -> EventsDiagramResult:
        """Build the diagram with no domain to narrow it."""
        _ = (params, state, box)
        duck = cast(DuckDBGraphResource, connections[DUCKDB_GRAPH_CONNECTION_KEY])
        return EventsDiagramResult(domain_events_diagram=events_diagram(duck, None))
