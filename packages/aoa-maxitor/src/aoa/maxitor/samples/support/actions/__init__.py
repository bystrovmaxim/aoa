# packages/aoa-maxitor/src/aoa/maxitor/samples/support/actions/__init__.py
from aoa.action_machine.intents.depends import depends
from aoa.maxitor.samples.support.actions.depend_cross_domain import DependCrossDomainAction
from aoa.maxitor.samples.support.actions.depend_same_domain import DependSameDomainAction
from aoa.maxitor.samples.support.actions.sla_breach_stub import SlaBreachStubAction
from aoa.maxitor.samples.support.actions.support_ping import SupportPingAction
from aoa.maxitor.samples.support.actions.ticket_stub import TicketStubAction

# Maxitor debug sample: creates an Action -> Action @depends cycle so the graph visualizer can show forbidden DAG edges.
depends(
    DependSameDomainAction,
    description="Maxitor debug sample: reverse action dependency that creates a visible DAG cycle",
)(SupportPingAction)

DependCrossDomainParams = DependCrossDomainAction.Params
DependCrossDomainResult = DependCrossDomainAction.Result
DependSameDomainParams = DependSameDomainAction.Params
DependSameDomainResult = DependSameDomainAction.Result
SlaBreachStubParams = SlaBreachStubAction.Params
SlaBreachStubResult = SlaBreachStubAction.Result
SupportPingParams = SupportPingAction.Params
SupportPingResult = SupportPingAction.Result
TicketStubParams = TicketStubAction.Params
TicketStubResult = TicketStubAction.Result

__all__ = [
    "DependCrossDomainAction",
    "DependCrossDomainParams",
    "DependCrossDomainResult",
    "DependSameDomainAction",
    "DependSameDomainParams",
    "DependSameDomainResult",
    "SlaBreachStubAction",
    "SlaBreachStubParams",
    "SlaBreachStubResult",
    "SupportPingAction",
    "SupportPingParams",
    "SupportPingResult",
    "TicketStubAction",
    "TicketStubParams",
    "TicketStubResult",
]
