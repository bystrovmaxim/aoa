"""Minimal self-contained scenario stub for aoa-ocel tests.

Faithful trim of ``tests/action_machine/scenarios/domain_model/entities.py``
keeping only the two symbols the ocel tests reference — ``TestDomain`` and
``SampleEntity`` — with original names and decorators preserved. Unused sibling
entities (DraftLifecycle, LifecycleEntity, RelatedEntity, ComplexEntity) and the
relation/lifecycle imports they required are dropped, since SampleEntity has no
relations or lifecycle.
"""

from pydantic import Field

from aoa.action_machine.domain import BaseEntity
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.intents.meta.meta_decorator import meta


class TestDomain(BaseDomain):
    """Test domain marker for exercising domain machinery."""

    name = "test"
    description = "Test domain"


@meta(description="Simple test entity", domain=TestDomain)
@entity(description="Simple test entity", domain=TestDomain)
class SampleEntity(BaseEntity):
    """Minimal entity for basic tests. No relations or lifecycle."""

    id: str = Field(description="Identifier")
    name: str = Field(description="Name")
    value: int = Field(description="Value", ge=0)
