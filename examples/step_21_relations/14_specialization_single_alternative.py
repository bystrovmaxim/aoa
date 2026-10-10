"""One alternative in the ERD.

Does a one-alternative specialization create a group or a relation line?
Run: uv run python examples/step_21_relations/14_specialization_single_alternative.py
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field

from aoa.action_machine.domain import BaseEntity, Classifier, Generalization, Inverse, Rel, Specialization
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine


class MusicDomain(BaseDomain):
    """Group the music catalogue declarations."""

    name = "music"
    description = "A music catalogue"


@entity(description="Vinyl record", domain=MusicDomain)
class VinylRecordEntity(BaseEntity):
    """Describe the information shared by all pressings."""

    id: str = Field(description="Record identifier")
    title: str = Field(description="Album title")
    media: str = Field(description="Pressing code")
    pressing: Annotated[
        Specialization[FirstPressEntity],
        Classifier(field="media", codes=Literal["first"]),
        Inverse(field_name="record"),
    ] = Rel(description="Details of this pressing")


@entity(description="First pressing", domain=MusicDomain)
class FirstPressEntity(BaseEntity):
    """Describe the stamper used for a first pressing."""

    id: str = Field(description="Pressing identifier")
    stamper: str = Field(description="Stamper code")
    record: Annotated[
        Generalization[VinylRecordEntity],
        Classifier("record", Literal["first"]),
        Inverse(VinylRecordEntity, "pressing"),
    ] = Rel(description="Record described by this pressing")


VinylRecordEntity.model_rebuild()
FirstPressEntity.model_rebuild()


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
