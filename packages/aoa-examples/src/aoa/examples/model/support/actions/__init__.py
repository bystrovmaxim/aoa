# packages/aoa-examples/src/aoa/examples/model/support/actions/__init__.py
from aoa.examples.model.support.actions.depend_cross_domain import DependCrossDomainAction
from aoa.examples.model.support.actions.depend_same_domain import DependSameDomainAction
from aoa.examples.model.support.actions.sla_breach_stub import SlaBreachStubAction
from aoa.examples.model.support.actions.support_ping import SupportPingAction
from aoa.examples.model.support.actions.ticket_stub import TicketStubAction

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
