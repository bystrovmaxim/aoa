# packages/aoa-maxitor/src/aoa/maxitor/model/diagrams/actions/domain_use_case_diagram_action.py
"""
GetDomainUseCaseDiagramAction — UML-style use-case slice for one interchange Domain id.

Builds a closed set of Action / Role vertices (plus edges) for Graphviz / SPA viewers:
actions declared in the domain, their superclass chain, @depends peers (``include`` / ``extend``),
every ``@check_roles`` association (including engine sentinels), and role generalizations.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, cast

from pydantic import Field

from aoa.action_machine.auth import NoneRole
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.connection import connection
from aoa.action_machine.intents.depends.use_case import VALID_USE_CASE_MODES
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult, BaseState
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.runtime.tools_box import ToolsBox
from aoa.maxitor.model.diagrams.actions.domain_use_case_diagram_action_schema import DomainUseCaseDiagramJson
from aoa.maxitor.model.diagrams.actions.list_domains_action import ListDomainsAction
from aoa.maxitor.model.diagrams.diagrams_domain import DiagramsDomain
from aoa.maxitor.model.diagrams.resources.duckdb_graph_resource import (
    DUCKDB_GRAPH_CONNECTION_KEY,
    DuckDBGraphResource,
)


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


@meta(
    description="Return Action/Role use-case diagram JSON for one interchange Domain id (DuckDB graph)",
    domain=DiagramsDomain,
)
@check_roles(NoneRole)
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

    @staticmethod
    def _action_domain_map(duck: DuckDBGraphResource) -> dict[str, str]:
        rows = duck.execute_fetch_dicts("SELECT source_id, target_id FROM domain_edges")
        return {str(r["source_id"]): str(r["target_id"]) for r in rows}

    @staticmethod
    def _accent_by_domain(duck: DuckDBGraphResource) -> dict[str, str]:
        out: dict[str, str] = {}
        for row in ListDomainsAction.domain_accent_rows(duck):
            out[str(row["qualname"])] = str(row["color"])
        return out

    @summary_aspect("Build domain use-case diagram JSON from DuckDB")
    async def build_use_case_summary(
        self,
        params: GetDomainUseCaseDiagramAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> GetDomainUseCaseDiagramAction.Result:
        _ = (state, box)
        duck = cast(DuckDBGraphResource, connections[DUCKDB_GRAPH_CONNECTION_KEY])
        domain_id = params.domain_id.strip()
        domain_row = GetDomainUseCaseDiagramAction._domain_row(duck, domain_id)
        if domain_row is None:
            msg = f"Unknown domain id {domain_id!r}"
            raise ValueError(msg)

        accent_by_domain = GetDomainUseCaseDiagramAction._accent_by_domain(duck)
        dom_accent = accent_by_domain.get(domain_id, "#64748b")
        domain_label = str(domain_row.get("label") or domain_id)
        domain_short = str(domain_row.get("name") or "").strip() or _short_qualname(domain_id)

        # ``domain_edges`` links *any* member vertex to a Domain (Actions, Entities, …).
        # Use-case slice must include only interchange Action ids (``action`` table).
        action_ids_all = {str(r["id"]) for r in duck.execute_fetch_dicts("SELECT id FROM action")}

        seed_rows = duck.execute_fetch_dicts(
            "SELECT source_id FROM domain_edges WHERE target_id = ?",
            [domain_id],
        )
        seed_actions = {str(r["source_id"]) for r in seed_rows} & action_ids_all

        with_parents = _transitive_action_parents(duck, seed_actions)

        dep_targets: set[str] = set()
        if seed_actions:
            placeholders = ", ".join(["?"] * len(seed_actions))
            sql_dep = f"SELECT target_id, mode FROM depends_edges WHERE source_id IN ({placeholders})"
            for r in duck.execute_fetch_dicts(sql_dep, list(seed_actions)):
                tid = str(r["target_id"])
                if tid in action_ids_all:
                    dep_targets.add(tid)

        actions_final = _transitive_action_parents(duck, with_parents | dep_targets) & action_ids_all

        role_edges_by_action: dict[str, list[str]] = defaultdict(list)
        if actions_final:
            ph = ", ".join(["?"] * len(actions_final))
            cr_rows = duck.execute_fetch_dicts(
                f"SELECT source_id, target_id FROM check_roles_edges WHERE source_id IN ({ph})",
                list(actions_final),
            )
            for r in cr_rows:
                role_edges_by_action[str(r["source_id"])].append(str(r["target_id"]))

        role_seed: set[str] = set()
        for targets in role_edges_by_action.values():
            role_seed.update(targets)

        roles_final = _transitive_role_parents(duck, role_seed)
        role_labels = {
            str(r["id"]): str(r["label"])
            for r in duck.execute_fetch_dicts(
                "SELECT id, label FROM role WHERE id IN ({})".format(
                    ", ".join(["?"] * len(roles_final)),
                ),
                list(roles_final),
            )
        } if roles_final else {}

        action_labels = {
            str(r["id"]): str(r["label"])
            for r in duck.execute_fetch_dicts(
                "SELECT id, label FROM action WHERE id IN ({})".format(
                    ", ".join(["?"] * len(actions_final)),
                ),
                list(actions_final),
            )
        } if actions_final else {}

        action_domain_by_id = GetDomainUseCaseDiagramAction._action_domain_map(duck)

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
                    "domain_short_label": _short_qualname(dom_a),
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

        if actions_final:
            pa_rows = duck.execute_fetch_dicts(
                "SELECT source_id, target_id FROM parent_action_edges WHERE source_id IN ({0}) AND target_id IN ({0})".format(
                    ", ".join(["?"] * len(actions_final)),
                ),
                list(actions_final) + list(actions_final),
            )
            for r in pa_rows:
                edges_out.append(
                    {
                        "edge_kind": "action_generalization",
                        "source_id": str(r["source_id"]),
                        "target_id": str(r["target_id"]),
                        "stereotype": None,
                    },
                )

        if roles_final:
            pr_rows = duck.execute_fetch_dicts(
                "SELECT source_id, target_id FROM parent_role_edges WHERE source_id IN ({0}) AND target_id IN ({0})".format(
                    ", ".join(["?"] * len(roles_final)),
                ),
                list(roles_final) + list(roles_final),
            )
            for r in pr_rows:
                edges_out.append(
                    {
                        "edge_kind": "role_generalization",
                        "source_id": str(r["source_id"]),
                        "target_id": str(r["target_id"]),
                        "stereotype": None,
                    },
                )

        for aid, targets in sorted(role_edges_by_action.items()):
            for tid in sorted(frozenset(targets)):
                edges_out.append(
                    {
                        "edge_kind": "association",
                        "source_id": aid,
                        "target_id": tid,
                        "stereotype": None,
                    },
                )

        if actions_final:
            ph = ", ".join(["?"] * len(actions_final))
            drows = duck.execute_fetch_dicts(
                f"""
                SELECT source_id, target_id, mode FROM depends_edges
                WHERE source_id IN ({ph}) AND target_id IN ({ph})
                """,
                list(actions_final) + list(actions_final),
            )
            for r in drows:
                mode_raw = r.get("mode")
                mode = str(mode_raw).strip() if mode_raw is not None else ""
                if mode in VALID_USE_CASE_MODES:
                    edges_out.append(
                        {
                            "edge_kind": mode,
                            "source_id": str(r["source_id"]),
                            "target_id": str(r["target_id"]),
                            "stereotype": f"«{mode}»",
                        },
                    )
                else:
                    edges_out.append(
                        {
                            "edge_kind": "depends",
                            "source_id": str(r["source_id"]),
                            "target_id": str(r["target_id"]),
                            "stereotype": None,
                        },
                    )

        edges_out.sort(
            key=lambda e: (
                e["edge_kind"],
                e["source_id"],
                e["target_id"],
            ),
        )

        payload: dict[str, Any] = {
            "domain": {
                "id": domain_id,
                "label": domain_label,
                "short_label": domain_short,
                "accent_color": dom_accent,
            },
            "actions": actions_json,
            "roles": roles_json,
            "edges": edges_out,
        }

        return GetDomainUseCaseDiagramAction.Result(domain_use_case_diagram=payload)
