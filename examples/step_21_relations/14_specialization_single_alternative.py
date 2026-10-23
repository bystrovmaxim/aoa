"""A single alternative needs no frame.

Use a dictionary with one value and an axis with one alternative.
Run: uv run python examples/step_21_relations/14_specialization_single_alternative.py
"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import (
    BaseCoreEntity,
    BaseEnumEntity,
    BaseSpecEntity,
    Classifier,
    Generalization,
    Inverse,
    Rel,
    Specialization,
    value,
)
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine


class MusicDomain(BaseDomain):
    """Group the music catalogue declarations."""

    name = "music"
    description = "A music catalogue"


@entity(description="Kind of VinylRecordCoreEntity", domain=MusicDomain)
class VinylRecordKindEnumEntity(BaseEnumEntity):
    """Declare the codes the axis borrows."""

    FIRST = value(code="first", display_name="First")


@entity(description="Vinyl record", domain=MusicDomain)
class VinylRecordCoreEntity(BaseCoreEntity):
    """Describe the information shared by all pressings."""

    id: str = Field(description="Record identifier")
    title: str = Field(description="Album title")
    pressing: Annotated[
        Specialization[FirstPressSpecEntity, VinylRecordKindEnumEntity],
        Inverse(field_name="record"),
    ] = Rel(description="Details of this pressing")


@entity(description="First pressing", domain=MusicDomain)
class FirstPressSpecEntity(BaseSpecEntity):
    """Describe the stamper used for a first pressing."""

    id: str = Field(description="The head record identifier")
    stamper: str = Field(description="Stamper code")
    record: Annotated[
        Generalization[VinylRecordCoreEntity],
        Classifier(variant=VinylRecordKindEnumEntity.FIRST),
        Inverse(VinylRecordCoreEntity, "pressing"),
    ] = Rel(description="Record described by this pressing")


VinylRecordCoreEntity.model_rebuild()
FirstPressSpecEntity.model_rebuild()


def main() -> None:
    """Run this one learning experiment."""
    import json

    from aoa.maxitor.model.diagrams.actions.list_entities_action import ListEntitiesAction
    from aoa.maxitor.model.diagrams.resources.duckdb_graph_resource import DuckDBGraphResource

    machine = ActionProductMachine(loggers=[])
    store = DuckDBGraphResource.build_from_json(json.loads(machine.graph_coordinator.to_json()))
    domain_id = next(node.node_id for node in machine.graph_coordinator.get_all_nodes() if node.label == "MusicDomain")
    diagram = ListEntitiesAction._slice_payload(store, domain_id, include_neighbors=False)
    print("Groups:", len(diagram["groups"]))
    print("Relation lines:", len(diagram["relations"]))


if __name__ == "__main__":
    main()
