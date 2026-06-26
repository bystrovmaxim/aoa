"""
06_field_mapping.py — Three field-mapping scenarios

Covers all three ways params_mapper and response_mapper interact:

  Scenario A — Input renaming only (params_mapper):
    Graph state uses ``user_query``; Action expects ``note``.
    params_mapper converts state → Params; response_mapper is absent
    (automatic name matching for outputs).

  Scenario B — Output renaming only (response_mapper):
    Graph state uses ``ticket_class``; Action returns ``category``.
    response_mapper converts Result → state dict; params_mapper is absent
    (automatic name matching for inputs).

  Scenario C — Side-effect node (response_mapper=lambda r: {}):
    Node runs an Action for its side effects (logging, notification, etc.)
    and writes nothing back to state.  The graph continues on the same state.

What's new (vs 05):
  - Combines both mappers in one graph
  - response_mapper=lambda r: {}  — explicit zero-write node

Install:  pip install aoa-action-machine langgraph

Run:
    uv run python examples/step_14_langgraph/06_field_mapping.py
"""

import asyncio

from pydantic import Field

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.context import Context
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.langgraph import LangGraphController

# ─── Domain ───────────────────────────────────────────────────────────────────


class SupportDomain(BaseDomain):
    name = "support"
    description = "Support ticket processing"


# ─── Params / Results ─────────────────────────────────────────────────────────


class ClassifyParams(BaseParams):
    ticket_id: str = Field(description="Ticket identifier")
    note: str = Field(description="Ticket text to classify")


class ClassifyResult(BaseResult):
    category: str = Field(description="Ticket category: bug | feature | billing")


class ResolveParams(BaseParams):
    ticket_id: str = Field(description="Ticket identifier")
    category: str = Field(description="Ticket category")


class ResolveResult(BaseResult):
    resolved: bool = Field(description="Resolution flag")
    resolution_note: str = Field(description="Resolution note")


class AuditParams(BaseParams):
    ticket_id: str = Field(description="Ticket identifier")
    resolution_note: str = Field(default="", description="Final resolution note")


class AuditResult(BaseResult):
    pass  # No output fields — this Action runs for side effects only


# ─── Actions ──────────────────────────────────────────────────────────────────


@meta(description="Classify ticket by content", domain=SupportDomain)
@check_roles(GuestRole)
class ClassifyTicketAction(BaseAction[ClassifyParams, ClassifyResult]):
    @summary_aspect("Classify ticket")
    async def classify_summary(self, params, state, box, connections):
        text = params.note.lower()
        if "billing" in text or "invoice" in text or "payment" in text:
            cat = "billing"
        elif "crash" in text or "error" in text or "bug" in text:
            cat = "bug"
        else:
            cat = "feature"
        return ClassifyResult(category=cat)


@meta(description="Route ticket to engineering", domain=SupportDomain)
@check_roles(GuestRole)
class EngineeringAction(BaseAction[ResolveParams, ResolveResult]):
    @summary_aspect("Assign to engineering")
    async def resolve_summary(self, params, state, box, connections):
        tag = params.category.upper()
        return ResolveResult(
            resolved=True,
            resolution_note=f"[{tag}] #{params.ticket_id} → engineering",
        )


@meta(description="Route ticket to billing team", domain=SupportDomain)
@check_roles(GuestRole)
class BillingAction(BaseAction[ResolveParams, ResolveResult]):
    @summary_aspect("Assign to billing")
    async def resolve_summary(self, params, state, box, connections):
        return ResolveResult(
            resolved=True,
            resolution_note=f"[BILLING] #{params.ticket_id} → billing team",
        )


@meta(description="Audit log — runs for side effects, writes nothing to state", domain=SupportDomain)
@check_roles(GuestRole)
class AuditLogAction(BaseAction[AuditParams, AuditResult]):
    @summary_aspect("Audit log")
    async def audit_summary(self, params, state, box, connections):
        print(f"    [AUDIT] #{params.ticket_id}: {params.resolution_note}")
        return AuditResult()


# ─── Graph with all three scenarios ───────────────────────────────────────────
#
# State field names (left) vs Action field names (right):
#
#   user_query  →  ClassifyParams.note      (Scenario A: params_mapper)
#   category    ←  ClassifyResult.category  (automatic: same name)
#   ticket_class is produced from category  (Scenario B: response_mapper)
#   AuditLogAction runs after finish        (Scenario C: response_mapper={})


def build_mapped_graph() -> LangGraphController:
    return (
        LangGraphController()
        # State fields
        .inp("ticket_id", str, "Ticket identifier")
        .inp("user_query", str, "Raw user query (state name)")
        .mid("ticket_class", str, "Classified ticket type")
        .mid("resolved", bool, "Resolution flag")
        .mid("resolution_note", str, "Resolution note")
        .out("ticket_class")
        .out("resolved")
        .out("resolution_note")
        # Scenario A: params_mapper renames user_query → note
        # Scenario B: response_mapper renames category → ticket_class
        .node(
            ClassifyTicketAction,
            params_mapper=lambda s: ClassifyParams(
                ticket_id=s.ticket_id,
                note=s.user_query,          # A: state.user_query → params.note
            ),
            response_mapper=lambda r: {"ticket_class": r.category},  # B: result.category → state.ticket_class
        )
        # EngineeringAction: params_mapper for ticket_class → category
        .node(
            EngineeringAction,
            params_mapper=lambda s: ResolveParams(
                ticket_id=s.ticket_id,
                category=s.ticket_class,
            ),
        )
        # BillingAction: same params_mapper pattern
        .node(
            BillingAction,
            params_mapper=lambda s: ResolveParams(
                ticket_id=s.ticket_id,
                category=s.ticket_class,
            ),
        )
        # Scenario C: AuditLogAction writes nothing to state
        .node(
            AuditLogAction,
            params_mapper=lambda s: AuditParams(
                ticket_id=s.ticket_id,
                resolution_note=getattr(s, "resolution_note", ""),
            ),
            response_mapper=lambda r: {},  # C: no state updates
        )
        # Topology: classify → route → resolve → audit → finish
        .start(ClassifyTicketAction)
        .route(
            ClassifyTicketAction,
            on=lambda s: s.ticket_class,
            paths={
                "bug": EngineeringAction,
                "feature": EngineeringAction,
                "billing": BillingAction,
            },
        )
        .edge(EngineeringAction, AuditLogAction)
        .edge(BillingAction, AuditLogAction)
        .finish(AuditLogAction)
        .build()
    )


# ─── Host Action ──────────────────────────────────────────────────────────────


class ProcessParams(BaseParams):
    ticket_id: str = Field(description="Ticket identifier")
    user_query: str = Field(description="Raw user query")


class ProcessResult(BaseResult):
    ticket_class: str = Field(description="Classified ticket type")
    resolved: bool = Field(description="Resolution flag")
    resolution_note: str = Field(description="Resolution note")


@meta(description="Process ticket with full field mapping", domain=SupportDomain)
@check_roles(GuestRole)
class ProcessTicketAction(BaseAction[ProcessParams, ProcessResult]):
    @summary_aspect("Run mapped ticket graph")
    async def run_summary(self, params, state, box, connections):
        ctrl = build_mapped_graph()
        result = await ctrl.ainvoke(
            {"ticket_id": params.ticket_id, "user_query": params.user_query},
            box,
        )
        return ProcessResult(
            ticket_class=result["ticket_class"],
            resolved=result["resolved"],
            resolution_note=result["resolution_note"],
        )


# ─── Main ─────────────────────────────────────────────────────────────────────


async def main() -> None:
    machine = ActionProductMachine()

    tickets = [
        ("T-1", "App crashes on login"),
        ("T-2", "Wrong invoice total"),
        ("T-3", "Add dark mode to the UI"),
    ]

    print("=== Field mapping: A (params), B (response), C (side-effect) ===")
    for ticket_id, user_query in tickets:
        result = await machine.run(
            Context(),
            ProcessTicketAction(),
            ProcessParams(ticket_id=ticket_id, user_query=user_query),
        )
        flag = "✓" if result.resolved else "✗"
        print(f"  {ticket_id}  [{result.ticket_class:8}]  {flag}  {result.resolution_note}")


if __name__ == "__main__":
    asyncio.run(main())
