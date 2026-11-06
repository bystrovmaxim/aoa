# packages/aoa-demo/src/aoa/demo/model/assurance_portfolio/resources/storage.py
"""AssurancePortfolioStorage — the store that holds the assurance portfolio domain's entities."""

from __future__ import annotations

from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources import BaseResource, BaseStorage
from aoa.demo.model.assurance_portfolio.domain import AssurancePortfolioDomain
from aoa.demo.model.data_sources.assurance_portfolio_data_source import AssurancePortfolioDataSource


@meta(description="Stores the assurance portfolio model (stub)", domain=AssurancePortfolioDomain)
class AssurancePortfolioStorage(BaseStorage[AssurancePortfolioDataSource]):
    """Hold the assurance portfolio domain's entities; the demo never opens it."""

    def get_wrapper_class(self) -> type[BaseResource] | None:
        """No wrapper: a nested action may use this resource as it is."""
        return None
