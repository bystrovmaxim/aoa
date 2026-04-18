# src/maxitor/samples/support/actions/__init__.py
from maxitor.samples.support.actions.depend_on_actions import (
    DependCrossDomainAction,
    DependCrossDomainParams,
    DependCrossDomainResult,
    DependSameDomainAction,
    DependSameDomainParams,
    DependSameDomainResult,
)
from maxitor.samples.support.actions.sla_breach_stub import (
    SlaBreachStubAction,
    SlaBreachStubParams,
    SlaBreachStubResult,
)
from maxitor.samples.support.actions.support_ping import (
    SupportPingAction,
    SupportPingParams,
    SupportPingResult,
)
from maxitor.samples.support.actions.ticket_stub import (
    TicketStubAction,
    TicketStubParams,
    TicketStubResult,
)

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
