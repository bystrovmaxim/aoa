# src/maxitor/samples/support/actions/__init__.py
from maxitor.samples.support.actions.depend_on_actions import (
    DependCrossDomainAction,
    DependCrossDomainParams,
    DependCrossDomainResult,
    DependSameDomainAction,
    DependSameDomainParams,
    DependSameDomainResult,
)
from maxitor.samples.support.actions.support_ping import (
    SupportPingAction,
    SupportPingParams,
    SupportPingResult,
)

__all__ = [
    "DependCrossDomainAction",
    "DependCrossDomainParams",
    "DependCrossDomainResult",
    "DependSameDomainAction",
    "DependSameDomainParams",
    "DependSameDomainResult",
    "SupportPingAction",
    "SupportPingParams",
    "SupportPingResult",
]
