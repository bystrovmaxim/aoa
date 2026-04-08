# src/action_machine/aspects/__init__.py
"""
ActionMachine aspects package.

This package contains decorators for declaring pipeline steps in an action's
business logic and the marker mixin that indicates pipeline support.

Components:
- AspectGateHost: marker mixin indicating support for aspect pipelines.
- regular_aspect: decorator for normal pipeline steps returning a dict.
- summary_aspect: decorator for the final pipeline step returning a Result.

How it works:
- Both decorators attach _new_aspect_meta to the method.
- MetadataBuilder.collect_aspects(cls) scans class members for this metadata.
- Aspect metadata is collected into ClassMetadata.aspects in declaration order.

Structural invariants enforced by MetadataBuilder:
- At most one summary aspect per class.
- If any regular aspects exist, a summary aspect is required.
- Summary must be declared last.
- regular_aspect methods must end with "_aspect".
- summary_aspect methods must end with "_summary".
- Description is mandatory for both decorators.

Example:
    from action_machine.aspects import regular_aspect, summary_aspect

    class CreateOrderAction(BaseAction[OrderParams, OrderResult]):

        @regular_aspect("Validate data")
        async def validate_aspect(self, params, state, box, connections):
            return {"validated_user": params.user_id}

        @regular_aspect("Process payment")
        @result_string("txn_id", required=True)
        async def process_payment_aspect(self, params, state, box, connections):
            return {"txn_id": "TXN-001"}

        @summary_aspect("Build result")
        async def build_result_summary(self, params, state, box, connections):
            return OrderResult(...)
"""

from .aspect_gate_host import AspectGateHost
from .regular_aspect import regular_aspect
from .summary_aspect import summary_aspect

__all__ = [
    "AspectGateHost",
    "regular_aspect",
    "summary_aspect",
]
