# packages/maxitor/front/src/maxitor/front/model/diagrams/actions/domain_use_case_diagram_action.py
"""
GetDomainUseCaseDiagramAction — UML-style use-case slice for one interchange Domain id.

Builds a closed set of Action / Role vertices (plus edges) for Graphviz / SPA viewers:
actions declared in the domain, their superclass chain, @depends peers (``include`` / ``extend``),
every ``@check_roles`` association (including engine sentinels), and role generalizations.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Literal, cast

from maxitor.front.model.diagrams.actions.domain_use_case_diagram_action_schema import DomainUseCaseDiagramJson
from maxitor.front.model.diagrams.actions.list_domains_action import ListDomainsAction
from maxitor.front.model.diagrams.diagrams_domain import DiagramsDomain
from maxitor.front.model.diagrams.resources.duckdb_graph_resource import (
    DUCKDB_GRAPH_CONNECTION_KEY,
    DuckDBGraphResource,
)
from pydantic import Field

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.connection import connection
from aoa.action_machine.intents.depends.use_case import VALID_USE_CASE_MODES
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult, BaseState
from aoa.action_machine.resources import Connections
from aoa.action_machine.runtime.tools_box import ToolsBox


def _short_qualname(raw: str) -> str:
    value = str(raw or "").strip()
    if not value:
        return "?"
    return value.rsplit(".", 1)[-1] if "." in value else value


def _transitive_action_parents(duck: DuckDBGraphResource, seeds: set[str]) -> set[str]:
    """Union ``seeds`` with all targets reachable via ``parent_action_edges`` (child → parent)."""
    out = set(seeds)
    rows = duck.execute_fetch_dicts("SELECT source_id, target_id FROM parent_action_edges")
    by_child: dict[str, list[str]] = {}
    for row in rows:
        ch = str(row["source_id"])
        par = str(row["target_id"])
        by_child.setdefault(ch, []).append(par)
    frontier = set(seeds)
    while frontier:
        nxt: set[str] = set()
        for aid in frontier:
            for par in by_child.get(aid, ()):
                if par not in out:
                    out.add(par)
                    nxt.add(par)
        frontier = nxt
    return out


def _transitive_role_parents(duck: DuckDBGraphResource, seeds: set[str]) -> set[str]:
    out = set(seeds)
    rows = duck.execute_fetch_dicts("SELECT source_id, target_id FROM parent_role_edges")
    by_child: dict[str, list[str]] = {}
    for row in rows:
        ch = str(row["source_id"])
        par = str(row["target_id"])
        by_child.setdefault(ch, []).append(par)
    frontier = set(seeds)
    while frontier:
        nxt: set[str] = set()
        for rid in frontier:
            for par in by_child.get(rid, ()):
                if par not in out:
                    out.add(par)
                    nxt.add(par)
        frontier = nxt
    return out


def _comma_question_placeholders(length: int) -> str:
    return ", ".join(["?"] * length)


def _fetch_id_labels(
    duck: DuckDBGraphResource,
    table: Literal["role", "action"],
    entity_ids: set[str],
) -> dict[str, str]:
    if not entity_ids:
        return {}
    ids = sorted(entity_ids)
    sql = f"SELECT id, label FROM {table} " f"WHERE id IN ({_comma_question_placeholders(len(ids))})"
    rows = duck.execute_fetch_dicts(sql, ids)
    return {str(r["id"]): str(r["label"]) for r in rows}


def _action_generalizations_within_actions(
    duck: DuckDBGraphResource,
    action_ids: set[str],
) -> list[dict[str, Any]]:
    if not action_ids:
        return []
    ids = sorted(action_ids)
    ph = _comma_question_placeholders(len(ids))
    sql = "SELECT source_id, target_id FROM parent_action_edges " f"WHERE source_id IN ({ph}) AND target_id IN ({ph})"
    return duck.execute_fetch_dicts(sql, ids + ids)


def _role_generalizations_within_roles(
    duck: DuckDBGraphResource,
    role_ids: set[str],
) -> list[dict[str, Any]]:
    if not role_ids:
        return []
    ids = sorted(role_ids)
    ph = _comma_question_placeholders(len(ids))
    sql = "SELECT source_id, target_id FROM parent_role_edges " f"WHERE source_id IN ({ph}) AND target_id IN ({ph})"
    return duck.execute_fetch_dicts(sql, ids + ids)


def _depends_rows_for_action_closure(
    duck: DuckDBGraphResource,
    action_ids: set[str],
) -> list[dict[str, Any]]:
    if not action_ids:
        return []
    ids = sorted(action_ids)
    ph = _comma_question_placeholders(len(ids))
    sql = f"""
    SELECT source_id, target_id, mode FROM depends_edges
    WHERE source_id IN ({ph}) AND target_id IN ({ph})
    """
    return duck.execute_fetch_dicts(sql.strip(), ids + ids)


def _link(edge_kind: str, edge_type: str, source_id: str, target_id: str, stereotype: str | None = None) -> dict[str, Any]:
    """One drawn link, with the protocol ``id`` of the graph edge it stands for (#285's rule)."""
    return {
        "id": f"{source_id}|{edge_type}|{target_id}",
        "edge_kind": edge_kind,
        "source_id": source_id,
        "target_id": target_id,
        "stereotype": stereotype,
    }


def _append_depends_edges(edges_out: list[dict[str, Any]], drows: list[dict[str, Any]]) -> None:
    for r in drows:
        mode_raw = r.get("mode")
        mode = str(mode_raw).strip() if mode_raw is not None else ""
        if mode in VALID_USE_CASE_MODES:
            edges_out.append(_link(mode, "@depends", str(r["source_id"]), str(r["target_id"]), f"«{mode}»"))
        else:
            edges_out.append(_link("depends", "@depends", str(r["source_id"]), str(r["target_id"])))


def _depends_targets_in_actions(
    duck: DuckDBGraphResource,
    seed_actions: set[str],
    action_ids_all: set[str],
) -> set[str]:
    if not seed_actions:
        return set()
    ids = sorted(seed_actions)
    ph = _comma_question_placeholders(len(ids))
    sql_dep = f"SELECT target_id, mode FROM depends_edges WHERE source_id IN ({ph})"
    out: set[str] = set()
    for r in duck.execute_fetch_dicts(sql_dep, ids):
        tid = str(r["target_id"])
        if tid in action_ids_all:
            out.add(tid)
    return out


def _group_check_roles_targets_by_action(
    duck: DuckDBGraphResource,
    actions_final: set[str],
) -> dict[str, list[str]]:
    role_edges_by_action: dict[str, list[str]] = defaultdict(list)
    if not actions_final:
        return role_edges_by_action
    ids = sorted(actions_final)
    ph = _comma_question_placeholders(len(ids))
    cr_rows = duck.execute_fetch_dicts(
        f"SELECT source_id, target_id FROM check_roles_edges WHERE source_id IN ({ph})",
        ids,
    )
    for r in cr_rows:
        role_edges_by_action[str(r["source_id"])].append(str(r["target_id"]))
    return role_edges_by_action


def _action_domain_map(duck: DuckDBGraphResource) -> dict[str, str]:
    rows = duck.execute_fetch_dicts("SELECT source_id, target_id FROM domain_edges")
    return {str(r["source_id"]): str(r["target_id"]) for r in rows}


def _accent_by_domain(duck: DuckDBGraphResource) -> dict[str, str]:
    out: dict[str, str] = {}
    for row in ListDomainsAction.domain_accent_rows(duck):
        out[str(row["qualname"])] = str(row["color"])
    return out


#: The diagram's ``domain`` when it draws every domain together.
ALL_DOMAINS = {"id": "all", "label": "All domains", "short_label": "All domains", "accent_color": "#64748b"}


def use_case_diagram(duck: DuckDBGraphResource, domain_row: dict[str, Any] | None) -> dict[str, Any]:
    """
    AI-CORE-BEGIN
    ROLE: Build the use-case diagram of one domain, or of every domain when ``domain_row`` is ``None``.
    CONTRACT: Actions declared in the scope, their parents and ``@depends`` targets, every ``@check_roles`` role with its parents, and the links between them, each with its protocol id.
    INVARIANTS: Read-only; the lists are sorted, so one graph gives one diagram.
    AI-CORE-END
    """
    accent_by_domain = _accent_by_domain(duck)
    action_domain_by_id = _action_domain_map(duck)

    # ``domain_edges`` links *any* member vertex to a Domain (Actions, Entities, …).
    # Use-case slice must include only interchange Action ids (``action`` table).
    action_ids_all = {str(r["id"]) for r in duck.execute_fetch_dicts("SELECT id FROM action")}

    if domain_row is None:
        domain_id = ""
        domain_json: dict[str, Any] = ALL_DOMAINS
        seed_actions = action_ids_all
    else:
        domain_id = str(domain_row["id"])
        domain_json = {
            "id": domain_id,
            "label": str(domain_row.get("label") or domain_id),
            "short_label": str(domain_row.get("name") or "").strip() or _short_qualname(domain_id),
            "accent_color": accent_by_domain.get(domain_id, "#64748b"),
        }
        seed_rows = duck.execute_fetch_dicts("SELECT source_id FROM domain_edges WHERE target_id = ?", [domain_id])
        seed_actions = {str(r["source_id"]) for r in seed_rows} & action_ids_all

    with_parents = _transitive_action_parents(duck, seed_actions)

    dep_targets = _depends_targets_in_actions(duck, seed_actions, action_ids_all)

    actions_final = _transitive_action_parents(duck, with_parents | dep_targets) & action_ids_all

    role_edges_by_action = _group_check_roles_targets_by_action(duck, actions_final)
    role_seed: set[str] = set()
    for targets in role_edges_by_action.values():
        role_seed.update(targets)

    roles_final = _transitive_role_parents(duck, role_seed)
    role_labels = _fetch_id_labels(duck, "role", roles_final)
    action_labels = _fetch_id_labels(duck, "action", actions_final)

    actions_json: list[dict[str, Any]] = []
    for aid in sorted(actions_final):
        dom_a = action_domain_by_id.get(aid, domain_id)
        rids = sorted(frozenset(role_edges_by_action.get(aid, [])))
        actions_json.append(
            {
                "id": aid,
                "label": action_labels.get(aid, _short_qualname(aid)),
                "short_label": _short_qualname(action_labels.get(aid, aid)),
                "domain_id": dom_a,
                "domain_short_label": _short_qualname(dom_a) if dom_a else "No domain",
                "accent_color": accent_by_domain.get(dom_a, "#94a3b8"),
                "role_ids": rids,
            },
        )

    roles_json: list[dict[str, Any]] = []
    for rid in sorted(roles_final):
        roles_json.append(
            {
                "id": rid,
                "label": role_labels.get(rid, _short_qualname(rid)),
                "short_label": _short_qualname(role_labels.get(rid, rid)),
            },
        )

    edges_out: list[dict[str, Any]] = []

    for r in _action_generalizations_within_actions(duck, actions_final):
        edges_out.append(_link("action_generalization", "parent_action", str(r["source_id"]), str(r["target_id"])))

    for r in _role_generalizations_within_roles(duck, roles_final):
        edges_out.append(_link("role_generalization", "parent_role", str(r["source_id"]), str(r["target_id"])))

    for aid, targets in sorted(role_edges_by_action.items()):
        for tid in sorted(frozenset(targets)):
            edges_out.append(_link("association", "@check_roles", aid, tid))

    _append_depends_edges(edges_out, _depends_rows_for_action_closure(duck, actions_final))

    edges_out.sort(key=lambda e: (e["edge_kind"], e["source_id"], e["target_id"]))

    return {"domain": domain_json, "actions": actions_json, "roles": roles_json, "edges": edges_out}


@meta(
    description="Return Action/Role use-case diagram JSON for one interchange Domain id (DuckDB graph)",
    domain=DiagramsDomain,
)
@check_roles(GuestRole)
@connection(
    DuckDBGraphResource,
    key=DUCKDB_GRAPH_CONNECTION_KEY,
    description="Coordinator graph in DuckDB",
)
class GetDomainUseCaseDiagramAction(
    BaseAction["GetDomainUseCaseDiagramAction.Params", "GetDomainUseCaseDiagramAction.Result"],
):
    """
    AI-CORE-BEGIN
    ROLE: Materialize a domain-scoped use-case graph for SPA / Graphviz.
    CONTRACT: ``domain_id`` is the interchange domain vertex id (type qualname); empty actions when the domain has no members.
    AI-CORE-END
    """

    class Params(BaseParams):
        domain_id: str = Field(min_length=1, description="Interchange Domain vertex id (full type qualname)")

    class Result(BaseResult):
        domain_use_case_diagram: DomainUseCaseDiagramJson = Field(
            description="Domain boundary + actions + roles + typed edges for use-case rendering.",
        )

    @staticmethod
    def _domain_row(duck: DuckDBGraphResource, domain_id: str) -> dict[str, Any] | None:
        rows = duck.execute_fetch_dicts(
            "SELECT id, label, name FROM domain WHERE id = ? LIMIT 1",
            [domain_id],
        )
        return dict(rows[0]) if rows else None



    @summary_aspect("Build domain use-case diagram JSON from DuckDB")
    async def build_use_case_summary(
        self,
        params: GetDomainUseCaseDiagramAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
    ) -> GetDomainUseCaseDiagramAction.Result:
        _ = (state, box)
        duck = cast(DuckDBGraphResource, connections[DUCKDB_GRAPH_CONNECTION_KEY])
        domain_id = params.domain_id.strip()
        domain_row = GetDomainUseCaseDiagramAction._domain_row(duck, domain_id)
        if domain_row is None:
            msg = f"Unknown domain id {domain_id!r}"
            raise ValueError(msg)
        return GetDomainUseCaseDiagramAction.Result(domain_use_case_diagram=use_case_diagram(duck, domain_row))
