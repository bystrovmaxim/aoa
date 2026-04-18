# src/maxitor/samples/support/actions/__init__.py
from maxitor.samples.support.actions.depend_cross_domain import DependCrossDomainAction
from maxitor.samples.support.actions.depend_same_domain import DependSameDomainAction
from maxitor.samples.support.actions.sla_breach_stub import SlaBreachStubAction
from maxitor.samples.support.actions.support_ping import SupportPingAction
from maxitor.samples.support.actions.ticket_stub import TicketStubAction

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
