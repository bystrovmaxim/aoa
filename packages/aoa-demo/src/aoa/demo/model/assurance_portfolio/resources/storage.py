# packages/aoa-demo/src/aoa/demo/model/assurance_portfolio/resources/storage.py
"""AssurancePortfolioStorage — the store that holds the assurance portfolio domain's entities."""

from __future__ import annotations

from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.base_storage import BaseStorage
from aoa.demo.model.assurance_portfolio.domain import AssurancePortfolioDomain


@meta(description="Stores the assurance portfolio model (stub)", domain=AssurancePortfolioDomain)
class AssurancePortfolioStorage(BaseStorage):
    """Hold the assurance portfolio domain's entities; the demo never opens it."""
