# packages/aoa-examples/src/aoa/examples/model/settlement_desks/settlement_desks_domain.py
"""SettlementDesksDomain — clearing liquidity with dual venue desks."""

from __future__ import annotations

from aoa.action_machine.domain import BaseDomain


class SettlementDesksDomain(BaseDomain):
    """Atlantic vs Pacific treasury-adjacent clearing lanes with arbitrator oversight."""

    name = "settlement_desks"
    description = "Multi-desk liquidity clearing: mirrored venue forks and reconciliation bridge"
