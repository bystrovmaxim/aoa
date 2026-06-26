# packages/aoa-demo/src/aoa/demo/model/support/actions/__init__.py
from aoa.demo.model.support.actions.depend_cross_domain_action import DependCrossDomainAction
from aoa.demo.model.support.actions.depend_cross_domain_include_action import DependCrossDomainIncludeAction
from aoa.demo.model.support.actions.depend_same_domain_action import DependSameDomainAction
from aoa.demo.model.support.actions.depend_same_domain_include_action import DependSameDomainIncludeAction
from aoa.demo.model.support.actions.sla_breach_stub import SlaBreachStubAction
from aoa.demo.model.support.actions.support_ping import SupportPingAction
from aoa.demo.model.support.actions.ticket_stub import TicketStubAction

DependCrossDomainParams = DependCrossDomainAction.Params
DependCrossDomainResult = DependCrossDomainAction.Result
DependCrossDomainIncludeParams = DependCrossDomainIncludeAction.Params
DependCrossDomainIncludeResult = DependCrossDomainIncludeAction.Result
DependSameDomainParams = DependSameDomainAction.Params
DependSameDomainResult = DependSameDomainAction.Result
DependSameDomainIncludeParams = DependSameDomainIncludeAction.Params
DependSameDomainIncludeResult = DependSameDomainIncludeAction.Result
SlaBreachStubParams = SlaBreachStubAction.Params
SlaBreachStubResult = SlaBreachStubAction.Result
SupportPingParams = SupportPingAction.Params
SupportPingResult = SupportPingAction.Result
TicketStubParams = TicketStubAction.Params
TicketStubResult = TicketStubAction.Result

__all__ = [
    "DependCrossDomainAction",
    "DependCrossDomainIncludeAction",
    "DependCrossDomainIncludeParams",
    "DependCrossDomainIncludeResult",
    "DependCrossDomainParams",
    "DependCrossDomainResult",
    "DependSameDomainAction",
    "DependSameDomainIncludeAction",
    "DependSameDomainIncludeParams",
    "DependSameDomainIncludeResult",
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
