"""
05_testing.py — Three patterns for testing LangGraph controllers

Testing a LangGraphController doesn't require a running machine.
This example demonstrates three standalone test patterns:

  Pattern 1 — Structural: call .build() and assert it completes without error.
              Tests topology and data-contract validity.  No network, no box.

  Pattern 2 — Stub Action: replace a real Action with a lightweight stub that
              returns a fixed result.  Isolates the graph routing logic from
              real implementations.

  Pattern 3 — Mock box: call ctrl.ainvoke() with a MagicMock box.  Tests the
              full ainvoke path (params extraction, routing, output) against a
              controlled Action result.

What's new (vs 04):
  - unittest.mock.MagicMock / AsyncMock for a minimal box
  - box.run = AsyncMock(return_value=mock_result) — simulate Action execution
  - Stub Actions: BaseAction subclass with a hard-coded @summary_aspect result

Install:  pip install aoa-action-machine langgraph

Run:
    uv run python examples/step_14_langgraph/05_testing.py
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

from pydantic import Field

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.langgraph import LangGraphController

# ─── Domain ───────────────────────────────────────────────────────────────────


class SupportDomain(BaseDomain):
    name = "support"
    description = "Support ticket processing"


# ─── Params / Results ─────────────────────────────────────────────────────────


class ClassifyParams(BaseParams):
    ticket_id: str = Field(description="Ticket identifier")
    note: str = Field(default="", description="Ticket content")


class ClassifyResult(BaseResult):
    category: str = Field(description="Ticket category: bug | feature | billing")


class ResolveParams(BaseParams):
    ticket_id: str = Field(description="Ticket identifier")
    category: str = Field(description="Ticket category")


class ResolveResult(BaseResult):
    resolved: bool = Field(description="Resolution flag")
    resolution_note: str = Field(description="Resolution note")


# ─── Real Actions (used in patterns 1 and 3) ──────────────────────────────────


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


# ─── Stub Actions (used in pattern 2) ─────────────────────────────────────────
#
# Stubs use the same Params/Result types as the real Actions so the graph's
# data-contract validation still passes.  The @summary_aspect returns a
# fixed result without any real logic.


@meta(description="[Stub] Always classifies as bug", domain=SupportDomain)
@check_roles(GuestRole)
class StubClassifyAction(BaseAction[ClassifyParams, ClassifyResult]):
    @summary_aspect("Stub: classify as bug")
    async def classify_summary(self, params, state, box, connections):
        return ClassifyResult(category="bug")


@meta(description="[Stub] Always resolves", domain=SupportDomain)
@check_roles(GuestRole)
class StubEngineeringAction(BaseAction[ResolveParams, ResolveResult]):
    @summary_aspect("Stub: always resolved")
    async def resolve_summary(self, params, state, box, connections):
        return ResolveResult(resolved=True, resolution_note="[STUB] resolved")


# ─── Graph builder helper ──────────────────────────────────────────────────────


def _build_graph(
    classify_cls: type = ClassifyTicketAction,
    engineering_cls: type = EngineeringAction,
) -> LangGraphController:
    """Build ticket graph with pluggable Action classes for easy stub injection."""
    return (
        LangGraphController()
        .inp("ticket_id", str, "Ticket identifier")
        .inp("note", str, "Ticket content")
        .mid("category", str, "Ticket category: bug | feature | billing")
        .mid("resolved", bool, "Resolution flag")
        .mid("resolution_note", str, "Resolution note")
        .out("category")
        .out("resolved")
        .out("resolution_note")
        .node(classify_cls)
        .node(engineering_cls)
        .node(BillingAction)
        .start(classify_cls)
        .route(
            classify_cls,
            on=lambda s: s.category,
            paths={
                "bug": engineering_cls,
                "feature": engineering_cls,
                "billing": BillingAction,
            },
        )
        .finish(engineering_cls)
        .finish(BillingAction)
        .build()
    )


# ─── Pattern 1: Structural test ───────────────────────────────────────────────


def test_build_validates_topology() -> None:
    """build() completes without raising — topology and data-contract are valid."""
    ctrl = _build_graph()
    assert ctrl._built is True
    print("  Pattern 1 ✓  build() validates topology successfully")


# ─── Pattern 2: Stub Action ───────────────────────────────────────────────────


async def test_stub_always_routes_to_engineering() -> None:
    """Replace real Actions with stubs; check routing without real classification."""
    ctrl = _build_graph(
        classify_cls=StubClassifyAction,
        engineering_cls=StubEngineeringAction,
    )
    mock_result = MagicMock()
    mock_result.model_dump.return_value = {"resolved": True, "resolution_note": "[STUB] resolved"}
    box = MagicMock()
    box.run = AsyncMock(return_value=mock_result)

    result = await ctrl.ainvoke({"ticket_id": "T-9", "note": "anything"}, box)

    assert result["category"] == "bug"   # StubClassifyAction always → "bug"
    assert result["resolved"] is True
    print("  Pattern 2 ✓  stub Actions route correctly")


# ─── Pattern 3: Mock box ──────────────────────────────────────────────────────


async def test_mock_box_returns_expected_output() -> None:
    """Use a mock box to simulate Action execution; assert ainvoke output."""
    ctrl = _build_graph()

    classify_result = MagicMock()
    classify_result.model_dump.return_value = {"category": "billing"}

    billing_result = MagicMock()
    billing_result.model_dump.return_value = {
        "resolved": True,
        "resolution_note": "[BILLING] #T-5 → billing team",
    }

    call_count = 0

    async def fake_run(action_cls, params, connections=None):
        nonlocal call_count
        call_count += 1
        if action_cls is ClassifyTicketAction:
            return classify_result
        return billing_result

    box = MagicMock()
    box.run = fake_run

    result = await ctrl.ainvoke({"ticket_id": "T-5", "note": "invoice issue"}, box)

    assert result["category"] == "billing"
    assert result["resolved"] is True
    assert call_count == 2  # classify + billing
    print("  Pattern 3 ✓  mock box captures 2 Action calls and returns expected output")


# ─── Main ─────────────────────────────────────────────────────────────────────


async def main() -> None:
    print("=== Testing patterns for LangGraphController ===")

    test_build_validates_topology()
    await test_stub_always_routes_to_engineering()
    await test_mock_box_returns_expected_output()

    print("\nAll patterns passed.")


if __name__ == "__main__":
    asyncio.run(main())
