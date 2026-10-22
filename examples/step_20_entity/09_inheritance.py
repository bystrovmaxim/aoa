"""Inherit the kind through an intermediate class.

Shared fields can live between the marker and a concrete entity. Every class in this chain keeps the CoreEntity suffix.

Run: uv run python examples/step_20_entity/09_inheritance.py
"""

from abc import ABC, abstractmethod

from pydantic import Field

from aoa.action_machine.domain import BaseCoreEntity
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
from aoa.action_machine.intents.entity import entity


class ShopDomain(BaseDomain):
    """Group the shop model declarations."""

    name = "shop"
    description = "Shop model"


@exclude_graph_model
class BaseDocumentCoreEntity(BaseCoreEntity, ABC):
    """Share document identity without becoming a graph entity."""

    id: str = Field(description="Document identifier")

    @abstractmethod
    def label(self) -> str:
        """Return the document's human label."""
        raise NotImplementedError


@entity(description="Customer invoice", domain=ShopDomain)
class InvoiceCoreEntity(BaseDocumentCoreEntity):
    """Describe one invoice using the shared document fields."""

    def label(self) -> str:
        """Return the invoice label."""
        return f"Invoice {self.id}"

invoice = InvoiceCoreEntity(id="inv-1")
assert isinstance(invoice, BaseCoreEntity)
print(invoice.label())
