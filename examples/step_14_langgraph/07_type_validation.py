"""
07_type_validation.py — Build-time type validation

LangGraphController.build() checks that the type each Action expects
matches the type declared in the graph state schema.  Two errors
help diagnose mismatches:

  FieldHasNoProducerError  — field name not found in state at all
  FieldTypeMismatchError   — field found, but types differ

This example shows three scenarios:

  Scenario A — Correct graph: types agree, build() succeeds.
  Scenario B — Params direction mismatch: state has str, Action.Params
                 expects int → FieldTypeMismatchError on 'params'.
  Scenario C — Result direction mismatch: Action.Result writes bool, but
                 state declares str → FieldTypeMismatchError on 'result'.

Nodes with params_mapper or response_mapper are excluded from all
type checks — the mapper owns the conversion contract.
"""


from pydantic import Field

from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.model.base_params import BaseParams
from aoa.action_machine.model.base_result import BaseResult
from aoa.langgraph.controller import LangGraphController
from aoa.langgraph.exceptions import FieldTypeMismatchError

# ─────────────────────────────────────────────────────────────────────────────
# Scenario A — correct types
# ─────────────────────────────────────────────────────────────────────────────


class ClassifyAction(BaseAction["ClassifyAction.Params", "ClassifyAction.Result"]):
    """Classify a ticket by its text."""

    class Params(BaseParams):
        text: str = Field(description="Raw ticket text")

    class Result(BaseResult):
        category: str = Field(description="Detected category")

    @summary_aspect("Classify ticket")
    async def _classify_summary(self, p: Params, s, b, c) -> "ClassifyAction.Result":
        return self.Result(category="billing")


def build_correct_graph() -> LangGraphController:
    """Types align: state str → Params str, Result str → state str."""
    ctrl = (
        LangGraphController()
        .inp("text", str, "Raw ticket text")
        .mid("category", str, "Detected category")
        .out("category")
        .node(ClassifyAction)
        .start(ClassifyAction)
        .finish(ClassifyAction)
    )
    built = ctrl.build()
    assert built is not None, "Expected successful build"
    print("Scenario A: build() succeeded — types are compatible.")
    return built


# ─────────────────────────────────────────────────────────────────────────────
# Scenario B — Params type mismatch
# ─────────────────────────────────────────────────────────────────────────────


class PriorityAction(BaseAction["PriorityAction.Params", "PriorityAction.Result"]):
    """Expects ticket_id as int, but state declares it as str."""

    class Params(BaseParams):
        ticket_id: int = Field(description="Numeric ticket ID")

    class Result(BaseResult):
        priority: str = Field(description="Resolved priority")

    @summary_aspect("Resolve priority")
    async def _resolve_summary(self, p: Params, s, b, c) -> "PriorityAction.Result":
        return self.Result(priority="high")


def demonstrate_params_mismatch() -> None:
    """State has ticket_id: str, but Action.Params expects int → FieldTypeMismatchError."""
    ctrl = (
        LangGraphController()
        .inp("ticket_id", str, "Ticket ID as string")
        .mid("priority", str, "Resolved priority")
        .out("priority")
        .node(PriorityAction)
        .start(PriorityAction)
        .finish(PriorityAction)
    )
    try:
        ctrl.build()
    except FieldTypeMismatchError as e:
        print("Scenario B — caught FieldTypeMismatchError:")
        print(f"  node      : {e.node_name}")
        print(f"  field     : {e.field_name}")
        print(f"  direction : {e.direction}")
        print(f"  state type: {e.state_type}")
        print(f"  action type: {e.action_type}")
        print()
        print("Fix: change .inp('ticket_id', str, ...) → .inp('ticket_id', int, ...)")
        print("     or use params_mapper=lambda s: PriorityAction.Params(ticket_id=int(s.ticket_id))")


# ─────────────────────────────────────────────────────────────────────────────
# Scenario C — Result type mismatch
# ─────────────────────────────────────────────────────────────────────────────


class ResolveAction(BaseAction["ResolveAction.Params", "ResolveAction.Result"]):
    """Returns resolved: bool, but state declares resolved: str."""

    class Params(BaseParams):
        pass

    class Result(BaseResult):
        resolved: bool = Field(description="True when ticket is closed")

    @summary_aspect("Resolve ticket")
    async def _resolve_summary(self, p: Params, s, b, c) -> "ResolveAction.Result":
        return self.Result(resolved=True)


def demonstrate_result_mismatch() -> None:
    """State has resolved: str, but Action.Result writes bool → FieldTypeMismatchError."""
    ctrl = (
        LangGraphController()
        .mid("resolved", str, "Resolution status")
        .out("resolved")
        .node(ResolveAction)
        .start(ResolveAction)
        .finish(ResolveAction)
    )
    try:
        ctrl.build()
    except FieldTypeMismatchError as e:
        print("Scenario C — caught FieldTypeMismatchError:")
        print(f"  node      : {e.node_name}")
        print(f"  field     : {e.field_name}")
        print(f"  direction : {e.direction}")
        print(f"  state type: {e.state_type}")
        print(f"  action type: {e.action_type}")
        print()
        print("Fix: change .mid('resolved', str, ...) → .mid('resolved', bool, ...)")
        print("     or use response_mapper=lambda r: {'resolved': str(r.resolved)}")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    build_correct_graph()
    print()
    demonstrate_params_mismatch()
    print()
    demonstrate_result_mismatch()
