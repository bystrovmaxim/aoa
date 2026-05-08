# packages/aoa-maxitor/src/aoa/maxitor/samples/assurance_portfolio/domain.py
"""Bounded-context marker for QA / governance topology demo."""

from aoa.action_machine.domain import BaseDomain


class AssurancePortfolioDomain(BaseDomain):
    name = "assurance_portfolio"
    description = (
        "Portfolio-scoped principals, catalogs, traced work items versus scenario choreography, "
        "execution waves, and delegated evidence (structural analogue of multi-domain QA meshes)"
    )
