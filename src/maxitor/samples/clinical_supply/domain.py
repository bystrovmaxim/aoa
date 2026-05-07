# src/maxitor/samples/clinical_supply/domain.py
"""Bounded-context marker for clinical consumable intake and ward distribution demo."""

from action_machine.domain import BaseDomain


class ClinicalSupplyDomain(BaseDomain):
    name = "clinical_supply"
    description = (
        "Partner-governed medical consumable intake, transport coupling, and ward dispatch lines "
        "(structural analogue of supply → detail → delivery line-item graphs)"
    )
