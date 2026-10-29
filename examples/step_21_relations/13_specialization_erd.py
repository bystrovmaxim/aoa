"""Generate the specialization diagram.

Inspect the payload produced by Maxitor from the complete model.
Run: uv run python examples/step_21_relations/13_specialization_erd.py
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
    REPRESS = value(code="repress", display_name="Repress")
    TEST = value(code="test", display_name="Test")


@entity(description="Vinyl record", domain=MusicDomain)
class VinylRecordCoreEntity(BaseCoreEntity):
    """Describe the information shared by all pressings."""

    id: str = Field(description="Record identifier")
    title: str = Field(description="Album title")
    pressing: Annotated[
        Specialization[FirstPressSpecEntity | RepressSpecEntity | TestPressSpecEntity, VinylRecordKindEnumEntity],
        Inverse(field_name="record"),
    ] = Field(description="Details of this pressing")


@entity(description="First pressing", domain=MusicDomain)
class FirstPressSpecEntity(BaseSpecEntity):
    """Describe the stamper used for a first pressing."""

    id: str = Field(description="The head record identifier")
    stamper: str = Field(description="Stamper code")
    record: Annotated[
        Generalization[VinylRecordCoreEntity],
        Classifier(variant=VinylRecordKindEnumEntity.FIRST),
        Inverse(VinylRecordCoreEntity, "pressing"),
    ] = Field(description="Record described by this pressing")


@entity(description="Re-pressing", domain=MusicDomain)
class RepressSpecEntity(BaseSpecEntity):
    """Describe when an album was pressed again."""

    id: str = Field(description="The head record identifier")
    year: int = Field(description="Re-pressing year")
    record: Annotated[
        Generalization[VinylRecordCoreEntity],
        Classifier(variant=VinylRecordKindEnumEntity.REPRESS),
        Inverse(VinylRecordCoreEntity, "pressing"),
    ] = Field(description="Record described by this pressing")


@entity(description="Test pressing", domain=MusicDomain)
class TestPressSpecEntity(BaseSpecEntity):
    """Describe who approved a test pressing."""

    id: str = Field(description="The head record identifier")
    approved_by: str = Field(description="Reviewer name")
    record: Annotated[
        Generalization[VinylRecordCoreEntity],
        Classifier(variant=VinylRecordKindEnumEntity.TEST),
        Inverse(VinylRecordCoreEntity, "pressing"),
    ] = Field(description="Record described by this pressing")


for model in (VinylRecordCoreEntity, FirstPressSpecEntity, RepressSpecEntity, TestPressSpecEntity):
    model.model_rebuild()


def main() -> None:
    """Run this one learning experiment."""
    import json
    from pathlib import Path

    from maxitor.front.model.diagrams.actions.list_entities_action import ListEntitiesAction
    from maxitor.front.model.diagrams.resources.duckdb_graph_resource import DuckDBGraphResource

    machine = ActionProductMachine(loggers=[])
    graph = json.loads(machine.graph_coordinator.to_json())
    store = DuckDBGraphResource.build_from_json(graph)
    domain_id = next(node.node_id for node in machine.graph_coordinator.get_all_nodes() if node.label == "MusicDomain")
    diagram = ListEntitiesAction._slice_payload(store, domain_id, include_neighbors=False)
    head = next(item for item in diagram["entities"] if item["label"] == "VinylRecordCoreEntity")
    field = next(item for item in head["fields"] if item["name"] == "pressing")
    print(field["name"])
    print(field["type"])
    print("Groups:", len(diagram["groups"]))
    print("Alternatives:", len(diagram["groups"][0]["members"]))
    print("Group links:", sum(item.get("relationship_kind") == "specialization" for item in diagram["relations"]))
    output = Path("examples/step_21_relations/02_specialization_erd.json")
    output.write_text(json.dumps(diagram, indent=2) + "\n")
    print("Saved:", output.as_posix())


if __name__ == "__main__":
    main()
