# packages/aoa-action-machine/src/aoa/action_machine/graph/edges/role_graph_edge.py
"""
RoleGraphEdge — ASSOCIATION from Action → Role interchange graph node (@check_roles).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Structural sibling to callable attachments (aspects): ``is_dag=False``, keyed by ``@check_roles``,
:class:`~aoa.action_machine.graph.core.association_graph_edge.AssociationGraphEdge` semantics (association to declared role classes),
materializing ``RoleGraphNode`` only after interchange resolution (targets start as stubs by ``target_node_id``).

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    ActionGraphNode  ──@check_roles──►  RoleGraphNode  (wired by coordinator)

One edge per declared ``grant(...)`` (or bare role, normalized to a grant with
``when=None``) — not deduplicated by role, since two grants for the same role
with different ``when=`` conditions are structurally distinct. Each edge carries
its grant's ``when`` condition in ``properties["when"]`` (runtime-only, like
``DependsGraphEdge``'s ``factory`` — never exported by :meth:`to_dict`) for
:class:`~aoa.action_machine.runtime.role_checker.RoleChecker` to evaluate, plus
that same grant's ``reason`` (a ``FailSecurityVerdict``) in
``properties["when_reason"]`` — ``when=``'s companion (see
:func:`~aoa.action_machine.intents.check_roles.grant.grant`; defaults to
``FailSecurityVerdict("FORBIDDEN_GRANT")`` when not given), carried alongside it
so ``RoleChecker`` can report *why* a ``when=`` rejection happened, not just that
it did. ``when=None`` grants carry ``when_reason=None`` too — there is nothing to
explain when there is no condition to reject anything.

Why ``when`` lives here and not on :class:`~aoa.action_machine.graph.nodes.role_graph_node.RoleGraphNode`:
``RoleGraphNode`` is built once **per role** and shared/deduplicated across every
action that references that role (``AdminRole`` used by both ``CancelOrderAction``
and ``RefundOrderAction`` wires to the *same* node instance). ``when=`` is a
per-action, per-grant fact — the same role can carry a different condition (or
none) for each action — so it cannot live on a node shared by actions with
conflicting conditions. ``RoleGraphEdge``, by contrast, is rebuilt fresh for every
``ActionGraphNode`` (see ``get_role_edges`` below) and never shared, making it the
correct — and only correct — home for this data. ``guard=`` (one condition shared
by *every* grant of one action) lives on
:class:`~aoa.action_machine.graph.nodes.action_graph_node.ActionGraphNode`
instead, for the same reason in reverse: storing it here too would duplicate the
same value across every grant-edge of that action instead of keeping it in one place.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from aoa.action_machine.auth.base_role import BaseRole
from aoa.action_machine.graph.core.association_graph_edge import AssociationGraphEdge
from aoa.action_machine.intents.check_roles.check_roles_intent_resolver import CheckRolesIntentResolver
from aoa.action_machine.system_core.type_introspection import TypeIntrospection

if TYPE_CHECKING:
    # Deferred: same transitive-cycle reason as check_roles_intent_resolver.py.
    # Only ever used as a type annotation below, never constructed here.
    from aoa.action_machine.intents.access_control import FailSecurityVerdict


class RoleGraphEdge(AssociationGraphEdge):
    """
    AI-CORE-BEGIN
    ROLE: Typed association edge Action host → ``@check_roles`` role class graph node.
    CONTRACT: ``edge_name`` ``@check_roles``; ``target_node_id`` dotted role class path; coordinator wires ``target_node``.
    PROPERTIES: optional ``when`` callable and its companion ``when_reason`` (a ``FailSecurityVerdict``, present whenever ``when`` is, runtime-only, from the source ``grant(...)``); never exported by :meth:`to_dict`.
    INVARIANTS: Frozen via ``AssociationGraphEdge``; ``is_dag`` False.
    AI-CORE-END
    """

    def __init__(
        self,
        *,
        role_cls: type[BaseRole],
        when: Callable[..., bool] | None = None,
        when_reason: FailSecurityVerdict | None = None,
    ) -> None:
        super().__init__(
            edge_name="@check_roles",
            is_dag=False,
            target_node_id=TypeIntrospection.full_qualname(role_cls),
            target_node=None,
            properties={"when": when, "when_reason": when_reason},
        )

    def to_dict(self, *, source_id: str) -> dict[str, Any]:
        return {
            "source_id": source_id,
            "target_id": self.target_node_id,
            "type": self.edge_name,
            "relationship": self.edge_relationship.archimate_name,
            "is_dag": self.is_dag,
            "properties": {},
        }

    @staticmethod
    def get_role_edges(
        action_cls: type[Any],
    ) -> list[RoleGraphEdge]:
        """Return one association stub per declared ``@check_roles`` grant, in declaration order."""
        grants = CheckRolesIntentResolver.resolve_grants(action_cls)
        return [RoleGraphEdge(role_cls=g.role, when=g.when, when_reason=g.reason) for g in grants]
